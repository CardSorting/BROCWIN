"""Inventory and ZIP the completed presentation; never touch the experiment."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / 'brocwin-poster-session-package-1.0.0.zip'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    verification = json.loads((HERE / 'verification-record.json').read_text(encoding='utf-8'))
    assert verification['status'] == 'passed'
    excluded_names = {'delivery-manifest.json', 'archive-record.json', ARCHIVE.name, 'narration-raw.wav', 'encode-progress.txt', 'caption-check.png', 'caption-check-fixed.png'}
    files = sorted(p for p in HERE.rglob('*') if p.is_file() and p.name not in excluded_names and 'audio' not in p.relative_to(HERE).parts and '__pycache__' not in p.parts)
    manifest = {'schema': 'heav3ns.brocwin.poster-delivery/v1', 'version': '1.0.0', 'createdUtc': datetime.now(timezone.utc).isoformat(), 'primarySourceVersion': '1.0.1', 'knowledgeBaseline': '1.4.1', 'videoDurationSeconds': verification['videoDurationSeconds'], 'engineeringState': 'closed-frozen', 'signatureStatus': 'Unsigned local hash inventory', 'archiveExclusions': 'Regenerable utterance WAV clips, raw audio mix, encoding progress and temporary caption checks. The mixed narration master, final media, scripts, timeline, sources and assets are included.', 'files': [{'path': p.relative_to(HERE).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files]}
    manifest_path = HERE / 'delivery-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for p in files + [manifest_path]:
            out.write(p, p.relative_to(HERE).as_posix())
    with zipfile.ZipFile(ARCHIVE) as check:
        assert check.testzip() is None
        for r in manifest['files']:
            assert hashlib.sha256(check.read(r['path'])).hexdigest() == r['sha256']
    record = {'schema': 'heav3ns.brocwin.poster-archive/v1', 'archive': ARCHIVE.name, 'bytes': ARCHIVE.stat().st_size, 'sha256': sha(ARCHIVE), 'archivedFiles': len(files) + 1, 'zipAndPayloadHashes': 'passed', 'manifestSha256': sha(manifest_path), 'externalReceipt': True, 'unsigned': True}
    (HERE / 'archive-record.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
