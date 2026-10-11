"""Record graphics debug export/caller disassembly without executing either DLL."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/python'))
import pefile
import capstone

source = Path('C:/Windows/SysWOW64/d3d9.dll')
pe = pefile.PE(str(source))
symbol = next(s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name == b'DebugSetMute')
decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
instructions = []
for op in decoder.disasm(pe.get_data(symbol.address, 128), pe.OPTIONAL_HEADER.ImageBase + symbol.address):
    instructions.append({'address': hex(op.address), 'operation': op.mnemonic + ' ' + op.op_str})
    if op.mnemonic == 'ret':
        assert op.op_str == '', 'reference now consumes arguments; review the compatibility binding'
        break
else:
    raise RuntimeError('Reference export changed; no return in the inspected span')
original = HERE.parents[1] / 'client/data/d3dx9_43.dll'
caller = pefile.PE(str(original))
call_site = [{'address': hex(op.address), 'operation': op.mnemonic + ' ' + op.op_str}
             for op in decoder.disasm(caller.get_data(0x19453, 4), 0x10019453)]
assert [row['operation'] for row in call_site] == ['push esi', 'call eax', 'pop ecx']
report = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'export': 'DebugSetMute', 'ordinal': symbol.ordinal, 'instructions': instructions,
          'callerSource': str(original), 'callerSha256': hashlib.sha256(original.read_bytes()).hexdigest(),
          'callerInstructions': call_site,
          'interpretation': 'The inspected release export changes only its private stack scratch and volatile ECX; no return value or shared state is written. Original D3DX passes a BOOL and performs caller cleanup. Debug-driver behavior is outside this verified scope.'}
(HERE / 'reference/graphics-debug.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('Recorded release DebugSetMute and original D3DX caller ABI')
