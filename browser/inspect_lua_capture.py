"""Compare Lua state observed in the integrated client with recovered bytecode.

Reads data only. It does not execute or modify a game script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct


class Chunk:
    def __init__(self, data):
        if data[:12] != bytes.fromhex('1b4c75615100010404040800'):
            raise ValueError('Expected Lua 5.1 little-endian x86/double chunk')
        self.data, self.pos = data, 12

    def read(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError('Truncated Lua chunk')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def byte(self):
        return self.read(1)[0]

    def integer(self):
        return struct.unpack('<I', self.read(4))[0]

    def string(self):
        n = self.integer()
        if not n:
            return None
        raw = self.read(n)
        if raw[-1]:
            raise ValueError('Lua string has no trailing NUL')
        return raw[:-1].decode('utf-8', errors='replace')

    def prototype(self, parent_source=None, depth=0):
        if depth > 100:
            raise ValueError('Excessive prototype nesting')
        source = self.string() or parent_source
        lines = [self.integer(), self.integer()]
        signature = list(self.read(4))
        code_count = self.integer()
        code = struct.unpack('<' + str(code_count) + 'I', self.read(code_count * 4))
        constants = []
        for _ in range(self.integer()):
            tag = self.byte()
            if tag == 0:
                value = None
            elif tag == 1:
                value = bool(self.byte())
            elif tag == 3:
                value = struct.unpack('<d', self.read(8))[0]
            elif tag == 4:
                value = self.string()
            else:
                raise ValueError(f'Unsupported constant tag {tag}')
            constants.append(value)
        children = [self.prototype(source, depth + 1) for _ in range(self.integer())]
        self.read(self.integer() * 4)  # line table
        for _ in range(self.integer()):
            self.string()
            self.read(8)  # local variable PC range
        for _ in range(self.integer()):
            self.string()
        return {'source': source, 'definedLines': lines, 'signature': signature,
                'codeWords': code_count, 'firstCode': list(code[:12]), 'code': list(code),
                'constants': constants, 'children': children}


def compare(asset, capture):
    raw = asset.read_bytes()
    chunk = Chunk(raw)
    prototype = chunk.prototype()
    if chunk.pos != len(raw):
        raise ValueError('Unconsumed Lua chunk bytes')
    evidence = json.loads(capture.read_text(encoding='utf-8'))
    records = evidence.get('records', [])
    observations = [json.loads(row['message'][len('[capture exception] '):])
                    for row in records if row.get('message', '').startswith('[capture exception] ')]
    comparisons = []
    for observation in observations:
        state = observation.get('lua') or {}
        for call in state.get('calls', []):
            if call.get('source') != prototype['source']:
                continue
            comparisons.append({'source': call['source'],
                'codeWordCountMatches': call.get('codeWords') == prototype['codeWords'],
                'firstInstructionsMatch': call.get('firstCode') == prototype['firstCode'],
                'observedError': state.get('topValue', {}).get('text')})
    return {'schema': 'theseus.lua-capture-comparison/v1', 'asset': str(asset),
            'assetSha256': hashlib.sha256(raw).hexdigest(), 'capture': str(capture),
            'source': prototype['source'], 'codeWords': prototype['codeWords'],
            'constantCount': len(prototype['constants']), 'comparisons': comparisons,
            'constantsWithAdjacentDecimals': [s for s in prototype['constants']
                 if isinstance(s, str) and '0.8 0.8' in s],
            'scope': 'Recovered data and observed original interpreter state only; not gameplay verification'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(compare(args.asset, args.capture), indent=2) + '\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8', newline='\n')
    print(result)
