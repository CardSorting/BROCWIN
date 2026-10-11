"""Record native baseline hashes and verify the source installation stays intact."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / 'theseus' / 'reports' / 'initial-files.json'
TREES = ('Elsword', 'client', 'scripts', 'tests', 'config', 'database', 'launcher', 'web')
SKIP = {'node_modules', '.next', 'dist', 'build', '__pycache__', 'snapshots', 'crashes', 'log'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record():
    if REPORT.exists():
        raise RuntimeError('Initial baseline is already recorded; refusing to replace it')
    provenance = json.loads((ROOT / 'theseus' / 'provenance.json').read_text())
    source = Path(provenance['sourceDirectory']).resolve()
    if ROOT == source or ROOT.is_relative_to(source) or source.is_relative_to(ROOT):
        raise RuntimeError('Source and reconstruction must be separate directories')
    paths = sorted(path for tree in TREES for path in (ROOT / tree).rglob('*')
                   if path.is_file() and not SKIP.intersection(path.relative_to(ROOT).parts)
                   and path.name not in ('offline.env', '.env') and path.suffix not in ('.log', '.pyc'))
    def entry(path):
        relative = path.relative_to(ROOT)
        original = source / relative
        copied_hash = sha(path)
        source_hash = sha(original) if original.is_file() else None
        return {'path': relative.as_posix(), 'size': path.stat().st_size,
                'copySha256': copied_hash, 'sourceSha256': source_hash, 'equal': copied_hash == source_hash}
    with ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(entry, paths))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {'source': str(source), 'copy': str(ROOT), 'sourceCommit': provenance['sourceCommit'], 'files': rows}
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    mismatches = [row['path'] for row in rows if not row['equal']]
    print(json.dumps({'files': len(rows), 'bytes': sum(row['size'] for row in rows), 'mismatches': mismatches}))
    return bool(mismatches)


def verify_source():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    source = Path(report['source'])
    def unchanged(row):
        path = source / row['path']
        return path.is_file() and sha(path) == row['sourceSha256']
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(unchanged, report['files']))
    changed = [row['path'] for row, match in zip(report['files'], results) if not match]
    print(json.dumps({'checked': len(results), 'originalFilesChanged': changed}))
    return bool(changed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('record', 'verify-source'))
    args = parser.parse_args()
    sys.exit(record() if args.action == 'record' else verify_source())
