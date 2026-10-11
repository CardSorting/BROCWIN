"""Loopback-only static/range host for the integrated browser runtime."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from prepare import HERE, ROOT, UPSTREAM
from network import NetworkService


def routes():
    manifest_path = HERE / 'generated/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    paths = {'/': HERE / 'index.html', '/index.html': HERE / 'index.html',
             '/main.js': HERE / 'main.js', '/local_server_wire.js': HERE / 'local_server_wire.js',
             '/manifest.json': manifest_path, '/runtime_cache.js': HERE / 'runtime_cache.js'}
    # Runtime workers resolve their companion scripts relative to their own URL.
    for folder, suffixes in (('lib', {'.js', '.json', '.wasm'}),
                              ('fonts', {'.fon', '.ttf', '.otf', '.woff', '.woff2', '.json'}),
                              ('src', {'.json'}), ('build', {'.wasm'})):
        for path in (UPSTREAM / folder).rglob('*'):
            if path.is_file() and path.suffix.lower() in suffixes:
                paths['/' + path.relative_to(UPSTREAM).as_posix()] = path
    paths['/host.js'] = UPSTREAM / 'host.js'
    for item in manifest['files']:
        paths['/' + item['url']] = ROOT / item['source']
    return paths


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_HEAD(self):
        self.serve(False)

    def do_GET(self):
        self.serve(True)

    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', getattr(self, 'cache_policy', 'no-store'))
        super().end_headers()

    def serve(self, body):
        self.cache_policy = 'no-store'
        expected = {'127.0.0.1', 'localhost'}
        host = self.headers.get('Host', '').split(':')[0]
        if host not in expected or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.send_error(403)
            return
        name = unquote(urlsplit(self.path).path)
        if name == '/network.json':
            data = (json.dumps(self.server.network.configuration()) + '\n').encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            if body:
                self.wfile.write(data)
            return
        path = self.server.paths.get(name)
        if path is None or not path.is_file():
            self.send_error(404)
            return
        size = path.stat().st_size
        start, end, code = 0, size - 1, 200
        # Runtime code uses content identities; mutable configuration and
        # ranged archives retain no-store. Do not cache network configuration.
        etag = None
        if not self.headers.get('Range') and path.suffix.lower() in {'.js', '.wasm', '.ttf', '.otf', '.fon'}:
            stat = path.stat()
            identities = getattr(self.server, 'cache_identities', None)
            if identities is None:
                identities = self.server.cache_identities = {}
            signature = (stat.st_mtime_ns, stat.st_size)
            previous = identities.get(str(path))
            if previous is None or previous[0] != signature:
                with path.open('rb') as stream:
                    value = hashlib.file_digest(stream, 'sha256').hexdigest()
                identities[str(path)] = (signature, value)
            else:
                value = previous[1]
            etag = '"' + value + '"'
            from urllib.parse import parse_qs
            fingerprint = parse_qs(urlsplit(self.path).query).get('sha256', [None])[0]
            self.cache_policy = ('private, max-age=31536000, immutable' if fingerprint == value
                                 else 'private, no-cache')
            if self.headers.get('If-None-Match') == etag:
                self.send_response(304)
                self.send_header('ETag', etag)
                self.end_headers()
                return
        value = self.headers.get('Range')
        if value:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
            valid = match and any(match.groups()) and size > 0
            if valid:
                lo, hi = match.groups()
                if lo:
                    start = int(lo)
                    end = min(int(hi), size - 1) if hi else size - 1
                else:
                    start = max(0, size - int(hi))
                valid = start <= end and start < size and (lo or int(hi) > 0)
            if not valid:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        if etag:
            self.send_header('ETag', etag)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if code == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if body:
            try:
                with path.open('rb') as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        data = stream.read(min(1024 * 1024, remaining))
                        if not data:
                            break
                        self.wfile.write(data)
                        remaining -= len(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    def log_message(self, fmt, *args):
        if len(args) > 1 and str(args[1]) not in ('200', '206'):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    mimetypes.add_type('application/wasm', '.wasm')
    mimetypes.add_type('text/javascript', '.js')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.paths = routes()
    server.network = NetworkService(server.server_port).start()
    print(f'Theseus browser runtime: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.network.close()


if __name__ == '__main__':
    main()
