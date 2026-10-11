"""Create an independent, immutable-on-rerun native checkpoint and SQL backups."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from isolate import ROOT, CONTAINER, sql


def create(name):
    if not name or any(char not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for char in name):
        raise ValueError('Use a lowercase checkpoint name')
    destination = ROOT / 'theseus' / 'checkpoints' / name
    destination.mkdir(parents=True, exist_ok=False)
    initial = json.loads((ROOT / 'theseus' / 'reports' / 'initial-files.json').read_text())
    paths = {ROOT / item['path'] for item in initial['files']}
    paths.update(path for path in (ROOT / 'theseus').iterdir() if path.is_file())
    paths.update((ROOT / 'Elsword' / 'offline' / 'offline.env', ROOT / 'Start-Theseus.ps1', ROOT / 'Start-Theseus.bat'))
    paths = sorted(path for path in paths if path.is_file() and path.name != 'asset-catalog.json')

    def copy(path):
        relative = path.relative_to(ROOT)
        target = destination / 'files' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        with target.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        return {'path': relative.as_posix(), 'sha256': digest, 'bytes': target.stat().st_size}

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(copy, paths))
    for database in ('Account', 'Game01', 'ES_BILLING', 'Statistics'):
        remote = f'/var/opt/mssql/data/theseus-{name}-{database}.bak'
        sql(f"BACKUP DATABASE [{database}] TO DISK=N'{remote}' WITH COPY_ONLY, INIT, CHECKSUM;")
        subprocess.run(['docker', 'cp', f'{CONTAINER}:{remote}', str(destination / f'{database}.bak')], check=True)
    (destination / 'manifest.json').write_text(json.dumps({'name': name, 'files': rows}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'checkpoint': name, 'files': len(rows), 'bytes': sum(row['bytes'] for row in rows), 'databases': 4}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    create(parser.parse_args().name)
