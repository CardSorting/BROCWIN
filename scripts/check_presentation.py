"""Read-only integrity checks for the distributed poster-session edition.

Uses only the Python standard library; no runtime, rendering or service actions.
The unsigned hash inventory checks preserved bytes, not experimental acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EDITION = ROOT / 'presentations/2026-10-11-poster-session-v1.0.0'


def selected_path(name):
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe delivery path: {name}')
    path = (EDITION / name).resolve()
    if not path.is_relative_to(EDITION.resolve()):
        raise ValueError(f'Delivery path escapes edition: {name}')
    return path


def digest_stream(stream):
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
        size += len(block)
    return size, digest.hexdigest()


def check_file(record):
    with selected_path(record['path']).open('rb') as stream:
        size, digest = digest_stream(stream)
    if 'bytes' in record and size != record['bytes']:
        raise ValueError(f'Size mismatch: {record["path"]}')
    if digest != record['sha256']:
        raise ValueError(f'Hash mismatch: {record["path"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='Also check every ZIP payload')
    args = parser.parse_args()
    receipt = json.loads(selected_path('archive-record.json').read_text(encoding='utf-8'))
    manifest_record = {'path': 'delivery-manifest.json', 'sha256': receipt['manifestSha256']}
    check_file(manifest_record)
    manifest = json.loads(selected_path('delivery-manifest.json').read_text(encoding='utf-8'))
    records = manifest['files']
    names = [record['path'] for record in records]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate manifest paths')
    for record in records:
        check_file(record)
    archive_record = {'path': receipt['archive'], 'bytes': receipt['bytes'], 'sha256': receipt['sha256']}
    check_file(archive_record)
    if receipt['archivedFiles'] != len(records) + 1:
        raise ValueError('Archive receipt file count differs from manifest')
    payload_records = records + [manifest_record]
    if args.archive:
        with zipfile.ZipFile(selected_path(receipt['archive'])) as archive:
            members = archive.namelist()
            expected = {record['path'] for record in payload_records}
            if len(members) != len(expected) or set(members) != expected:
                raise ValueError('ZIP members differ from the delivery manifest')
            for record in payload_records:
                with archive.open(record['path']) as stream:
                    size, digest = digest_stream(stream)
                if 'bytes' in record and size != record['bytes']:
                    raise ValueError(f'ZIP payload size mismatch: {record["path"]}')
                if digest != record['sha256']:
                    raise ValueError(f'ZIP payload hash mismatch: {record["path"]}')
    print(json.dumps({'status': 'passed', 'manifestFiles': len(records),
        'manifestReceipt': 'passed', 'archiveHash': 'passed',
        'zipPayloads': len(payload_records) if args.archive else 'not requested',
        'videoDurationSeconds': manifest['videoDurationSeconds'], 'unsigned': True,
        'runtimeActions': 0, 'scope': 'Preserved delivery bytes; not runtime acceptance or independent replication.'}))


if __name__ == '__main__':
    main()
