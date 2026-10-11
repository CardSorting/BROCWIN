"""Read local Winsock export metadata and format IPv4 values in scratch memory."""
import ctypes
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/python'))
import pefile

exports = {}
for name in ('ws2_32.dll', 'wsock32.dll'):
    source = Path('C:/Windows/SysWOW64') / name
    pe = pefile.PE(str(source))
    exports[name] = {
        'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'ordinals': {str(s.ordinal): s.name.decode('ascii') for s in pe.DIRECTORY_ENTRY_EXPORT.symbols
                     if s.name and s.ordinal in range(1, 24)},
    }
socket = ctypes.WinDLL('ws2_32')
socket.inet_ntoa.argtypes = [ctypes.c_uint32]
socket.inet_ntoa.restype = ctypes.c_char_p
socket.inet_addr.argtypes = [ctypes.c_char_p]
socket.inet_addr.restype = ctypes.c_uint32
cases = []
for text in ('0.0.0.0', '0.0.0.1', '10.0.0.1', '127.0.0.1', '128.0.0.1',
             '192.168.16.0', '224.0.0.1', '255.255.255.254', '255.255.255.255'):
    value = int.from_bytes(bytes(map(int, text.split('.'))), 'little')
    cases.append({'networkOrder': value, 'text': socket.inet_ntoa(value).decode('ascii'),
                  'parsedNetworkOrder': socket.inet_addr(text.encode('ascii'))})
source = Path('C:/Windows/System32/ws2_32.dll')
report = {'exports': exports, 'formatSource': str(source),
          'formatSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'scope': 'No network operations; read-only PE metadata and inet_ntoa/inet_addr numeric conversion.',
          'cases': cases}
(HERE / 'reference/winsock.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'Recorded two native ordinal tables and {len(cases)} IPv4 formatting cases')
