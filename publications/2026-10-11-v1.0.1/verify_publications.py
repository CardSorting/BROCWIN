"""Read-only publication inventory, archive and cited-source verification."""
from pathlib import Path
import hashlib
import json
import zipfile
import argparse

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def contained(base,name):
    path=(base/name).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError('Inventory path escapes root')
    return path
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-only',action='store_true',help='Verify delivered publication holdings without requiring the original repository evidence')
    args=parser.parse_args()
    manifest_path=HERE/'archival-manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    record=json.loads((HERE/'archive-record.json').read_text(encoding='utf-8'))
    assert sha(manifest_path.read_bytes())==record['manifestSha256'],'Manifest changed'
    for name,expected in manifest['files'].items():
        data=contained(HERE,name).read_bytes()
        assert len(data)==expected['bytes'] and sha(data)==expected['sha256'],f'Publication changed: {name}'
    archive=contained(HERE,record['path'])
    assert sha(archive.read_bytes())==record['sha256'],'Archive changed'
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        assert len(names)==len(set(names)),'Duplicate archive member'
        assert set(names)==set(manifest['files'])|{'archival-manifest.json'},'Archive inventory differs'
        assert z.read('archival-manifest.json')==manifest_path.read_bytes(),'Embedded manifest differs'
        for name,expected in manifest['files'].items():
            assert sha(z.read(name))==expected['sha256'],f'Archive member changed: {name}'
    if not args.archive_only:
        for name,expected in manifest['citedEvidence'].items():
            assert sha(contained(ROOT,name).read_bytes())==expected,f'Cited source changed: {name}'
    print(json.dumps({'status':'passed','version':manifest['version'],
        'publicationFiles':len(manifest['files']),'citedSourceFiles':0 if args.archive_only else len(manifest['citedEvidence']),
        'archiveSha256':record['sha256'],'engineeringActions':0}))
if __name__=='__main__':
    main()
