"""Record IP Helper buffer contracts without retaining host network identity."""
import ctypes as c
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
api = c.WinDLL('iphlpapi', use_last_error=True).GetAdaptersInfo
api.argtypes = [c.c_void_p, c.POINTER(c.c_uint32)]
api.restype = c.c_uint32

# The guest is x86: pointers and legacy IP Helper time_t members are 32 bits.
class Address32(c.Structure):
    _fields_ = [('Next', c.c_uint32), ('IpAddress', c.c_char * 16),
                ('IpMask', c.c_char * 16), ('Context', c.c_uint32)]

class Adapter32(c.Structure):
    _fields_ = [('Next', c.c_uint32), ('ComboIndex', c.c_uint32),
                ('AdapterName', c.c_char * 260), ('Description', c.c_char * 132),
                ('AddressLength', c.c_uint32), ('Address', c.c_ubyte * 8),
                ('Index', c.c_uint32), ('Type', c.c_uint32), ('DhcpEnabled', c.c_uint32),
                ('CurrentIpAddress', c.c_uint32), ('IpAddressList', Address32),
                ('GatewayList', Address32), ('DhcpServer', Address32),
                ('HaveWins', c.c_uint32), ('PrimaryWinsServer', Address32),
                ('SecondaryWinsServer', Address32), ('LeaseObtained', c.c_uint32),
                ('LeaseExpires', c.c_uint32)]

needed = c.c_uint32(0)
assert api(None, c.byref(needed)) == 111 and needed.value > 0
required = needed.value
cases = []
for label, null_buffer, capacity in [('query-zero', True, 0), ('query-large', True, required + 64),
        ('short-zero', False, 0), ('short-one', False, 1), ('short-last', False, required - 1),
        ('exact', False, required), ('larger', False, required + 64)]:
    storage = (c.c_ubyte * (required + 80))(*([0xa5] * (required + 80)))
    size = c.c_uint32(capacity)
    c.set_last_error(0x1234)
    result = api(None if null_buffer else storage, c.byref(size))
    cases.append({'case': label, 'result': result, 'lastError': c.get_last_error(),
                  'sizeIsRequired': size.value == required, 'sizeUnchanged': size.value == capacity,
                  'bufferUntouched': bytes(storage) == b'\xa5' * len(storage),
                  'tailUntouched': bytes(storage)[required:] == b'\xa5' * (len(storage) - required),
                  'unusedCapacityZeroed': bytes(storage)[required:capacity] == b'\0' * max(0, capacity - required),
                  'beyondCapacityUntouched': bytes(storage)[capacity:] == b'\xa5' * (len(storage) - capacity)})
c.set_last_error(0x1234)
cases.append({'case': 'null-size', 'result': api(None, None), 'lastError': c.get_last_error()})
source = Path('C:/Windows/System32/iphlpapi.dll')
report = {'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'scope': 'Read-only local API buffer contract; no host addresses, names or MACs retained. Native sizes are not guest sizes.',
          'guestLayout': {'size': c.sizeof(Adapter32), 'addressSize': c.sizeof(Address32),
              'offsets': {name: getattr(Adapter32, name).offset for name, _ in Adapter32._fields_}},
          'cases': cases}
(HERE / 'reference/network-adapters.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
