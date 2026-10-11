import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

spec = importlib.util.spec_from_file_location('assets', Path(__file__).with_name('assets.py'))
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class RecoveryTests(unittest.TestCase):
    def test_rejects_windows_path_escape_and_aliases(self):
        for name in ('../escape', 'C:\\escape', '\\server\\share', 'file:stream', 'CON', 'folder/file.', 'folder/../escape'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                assets.safe_name(name)

    def test_reads_complete_archive_and_rejects_corruption(self):
        payload = b'preserved native asset'
        compressed = zlib.compress(payload)
        table = f'<?xml version="1.0"?><Files><File Name="image.dds" Size="{len(payload)}" CompressedSize="{len(compressed)}"/></Files>'.encode()
        archive = b'KOM ' + struct.pack('<I', len(table)) + table + compressed
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.kom'
            path.write_bytes(archive)
            self.assertEqual(list(assets.archive_entries(path))[0][3], payload)
            for malformed in (archive[:-1], archive + b'junk', archive.replace(b'Size="22"', b'Size="01"', 1)):
                if malformed == archive:
                    continue
                path.write_bytes(malformed)
                with self.assertRaises(ValueError):
                    list(assets.archive_entries(path))


if __name__ == '__main__':
    unittest.main()
