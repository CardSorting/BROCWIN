"""Exercise actual HTTP range delivery and the explicit input boundary."""
import http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from serve import Handler


class RangeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'archive.kom'
        self.path.write_bytes(bytes(range(256)) * 32)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.paths = {'/payload/archive.kom': self.path}
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, path='/payload/archive.kom', headers=None, method='GET'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def test_ranges_reassemble_original_bytes(self):
        result = bytearray()
        for start in range(0, 8192, 1000):
            status, headers, body = self.request(headers={'Range': f'bytes={start}-{start+999}'})
            self.assertEqual(status, 206)
            self.assertEqual(int(headers['Content-Length']), len(body))
            self.assertEqual(headers['Cross-Origin-Embedder-Policy'], 'require-corp')
            result.extend(body)
        self.assertEqual(bytes(result), self.path.read_bytes())
        self.assertEqual(self.request(headers={'Range': 'bytes=-32'})[2], self.path.read_bytes()[-32:])
        self.assertEqual(self.request(headers={'Range': 'bytes=8100-'})[2], self.path.read_bytes()[8100:])
        self.assertEqual(self.request(method='HEAD')[2], b'')

    def test_rejects_invalid_ranges_and_unlisted_files(self):
        for value in ('bytes=8192-', 'bytes=-0', 'bytes=20-10', 'bytes=0-4,8-10', 'broken'):
            self.assertEqual(self.request(headers={'Range': value})[0], 416)
        for path in ('/../.env', '/payload/%2e%2e/.env', '/serve.py', '/system/kernel32.dll'):
            self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request(headers={'Host': 'attacker.invalid'})[0], 403)
        self.assertEqual(self.request(headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)

    def test_runtime_content_identity_revalidates(self):
        path=Path(self.directory.name)/'helper.js'
        path.write_bytes(b'let value=1;')
        self.server.paths['/helper.js']=path
        status,headers,body=self.request('/helper.js')
        self.assertEqual(status,200)
        self.assertEqual(headers['Cache-Control'],'private, no-cache')
        identity=headers['ETag']
        status,headers,body=self.request('/helper.js',headers={'If-None-Match':identity})
        self.assertEqual(status,304)
        self.assertEqual(body,b'')
        self.assertEqual(headers['Cross-Origin-Embedder-Policy'],'require-corp')
        fingerprint=identity.strip('"')
        self.assertIn('immutable',self.request('/helper.js?sha256='+fingerprint)[1]['Cache-Control'])
        self.assertNotIn('immutable',self.request('/helper.js?sha256='+'0'*64)[1]['Cache-Control'])
        path.write_bytes(b'let value=changed;')
        status,headers,body=self.request('/helper.js',headers={'If-None-Match':identity})
        self.assertEqual(status,200)
        self.assertNotEqual(headers['ETag'],identity)
        self.assertEqual(body,path.read_bytes())


if __name__ == '__main__':
    unittest.main()
