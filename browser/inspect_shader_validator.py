"""Record the installed OS shader validator's interface and token contracts.

No device, window or game is created. This is a local Windows reference, not
the original fork's implementation and not a browser acceptance test.
"""
import ctypes as C
import hashlib
import json
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
PTR = C.c_void_p
U32 = C.c_uint32
HRESULT = C.c_long
CALLBACK = C.WINFUNCTYPE(HRESULT, PTR, C.c_int32, C.c_size_t, C.c_size_t, PTR, PTR)
dll = C.WinDLL('d3d9')
factory = dll.Direct3DShaderValidatorCreate9
factory.argtypes, factory.restype = [], PTR

def inspect(name, actions):
    obj = factory()
    if not obj:
        raise RuntimeError('Native validator unavailable')
    vt = C.cast(obj, C.POINTER(C.POINTER(PTR))).contents
    methods = [C.WINFUNCTYPE(HRESULT, PTR, PTR, C.POINTER(PTR))(vt[0]),
               C.WINFUNCTYPE(U32, PTR)(vt[1]), C.WINFUNCTYPE(U32, PTR)(vt[2]),
               C.WINFUNCTYPE(HRESULT, PTR, PTR, PTR, C.c_size_t)(vt[3]),
               C.WINFUNCTYPE(HRESULT, PTR, PTR, C.c_int32, C.POINTER(U32), U32)(vt[4]),
               C.WINFUNCTYPE(HRESULT, PTR)(vt[5])]
    messages = []
    @CALLBACK
    def diagnostic(file, line, severity, message_id, message, context):
        messages.append({'file': C.string_at(file).decode(errors='replace') if file else None,
                         'line': line, 'severity': severity, 'id': message_id,
                         'message': C.string_at(message).decode(errors='replace') if message else None,
                         'context': context})
        return 0
    rows = []
    try:
        for action in actions:
            messages.clear()
            op = action[0]
            row = {'op': op, 'args': action[1:]}
            if op == 'begin':
                hr = methods[3](obj, C.cast(diagnostic, PTR) if action[1] else None, PTR(0x1234), action[2])
            elif op == 'instruction':
                tokens = (U32 * len(action[1]))(*action[1])
                filename = C.create_string_buffer(b'fixture.fx')
                hr = methods[4](obj, filename, 17, tokens, len(tokens))
            elif op == 'query':
                iid = C.create_string_buffer(uuid.UUID(action[1]).bytes_le)
                out = PTR(0x1234)
                hr = methods[0](obj, iid, C.byref(out))
                row['outputNull'] = out.value is None
                row['sameIdentity'] = out.value == obj
                if hr == 0:
                    row['release'] = methods[2](out)
            elif op == 'addref':
                hr = methods[1](obj)
                row['release'] = methods[2](obj)
            else:
                hr = methods[5](obj)
            row.update(result=hr & 0xffffffff, diagnostics=messages.copy())
            rows.append(row)
    finally:
        refs = methods[2](obj)
    return {'name': name, 'actions': rows, 'finalReferences': refs}

if __name__ == '__main__':
    vs=[['instruction',[0xfffe0200]], ['instruction',[0x02000001,0xc00f0000,0x90e40000]], ['instruction',[0xffff]]]
    cases = [
        ('interface',[['query','00000000-0000-0000-c000-000000000046'],['query','81bdcbca-64d4-426d-ae8d-ad0147f4275c'],['addref']]),
        ('undeclared-vs2-input',[['begin',True,0],*vs,['end'],['begin',True,1],*vs,['end']]),
        ('uninitialized-vs1-input',[['begin',True,0],['instruction',[0xfffe0101]],['instruction',[1,0xc00f0000,0x90e40000]],['instruction',[0xffff]],['end']]),
        ('valid-vs2-constant',[['begin',True,0],vs[0],['instruction',[0x02000001,0xc00f0000,0xa0e40000]],vs[-1],['end']]),
        ('valid-vs1-constant',[['begin',True,0],['instruction',[0xfffe0101]],['instruction',[1,0xc00f0000,0xa0e40000]],vs[-1],['end']]),
        ('empty-ps3',[['begin',True,0],['instruction',[0xffff0300]],['instruction',[0xffff]],['end']]),
        ('no-begin',[['instruction',[0xfffe0200]],['end']]),
        ('double-begin',[['begin',True,0],['begin',True,0],['end']]),
        ('empty',[['begin',True,0],['end'],['begin',True,0],['end']]),
        ('bad-header',[['begin',True,0],['instruction',[0]],['end'],['begin',True,0]]),
        ('missing-end',[['begin',True,0],*vs[:-1],['end']]),
        ('truncated',[['begin',True,0],vs[0],['instruction',[0x02000001,0xc00f0000]],['end']]),
        ('bad-register',[['begin',True,0],vs[0],['instruction',[0x02000001,0x800f0064,0x90e40000]],vs[-1],['end']]),
        ('after-end',[['begin',True,0],*vs,['instruction',[0]],['end']]),
        ('null-callback',[['begin',False,0],*vs,['end']]),
    ]
    source=Path('C:/Windows/System32/d3d9.dll')
    report={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'pointerBits':C.sizeof(PTR)*8,'scope':__doc__,'cases':[inspect(*c) for c in cases]}
    dest=HERE/'reference/shader-validator.json'
    dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
