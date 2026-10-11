"""Reuse the inherited Lua constant patcher and KOM writer for loopback play.

Verifies every non-configuration payload is unchanged by this replacement.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
from assets import ROOT, archive_entries, digest, inherited_kom


def main():
    archive = ROOT / 'client' / 'data' / 'data036.kom'
    checkpoint = ROOT / 'theseus' / 'checkpoints' / 'pre-local-client-data036.kom'
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if not checkpoint.exists():
        shutil.copy2(archive, checkpoint)
    spec = importlib.util.spec_from_file_location('inherited_client_connect', ROOT / 'scripts' / 'client_connect.py')
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    kom = inherited_kom()
    before = {attrs['Name']: payload for attrs, _, _, payload in archive_entries(archive)}
    replacements = {}
    for name, payload in before.items():
        if name.startswith('Config') and name.endswith('.lua'):
            bytecode = client.xor_payload(payload)
            if not bytecode.startswith(b'\x1bLua'):
                raise RuntimeError(f'Unknown config bytecode format: {name}')
            changed, old_ips = client.patch_lua_bytecode_ip_constants(bytecode, '127.0.0.1')
            if old_ips:
                replacements[name] = client.xor_payload(changed)
    previous_hash = digest(archive)
    if replacements:
        kom.replace_kom_entries(archive, replacements)
        kom.verify_kom_entries(archive, replacements)
    after = {attrs['Name']: payload for attrs, _, _, payload in archive_entries(archive)}
    expected = dict(before)
    expected.update(replacements)
    if after != expected:
        raise RuntimeError('Client archive comparison failed; do not launch this version')
    report = {'beforeSha256': previous_hash, 'afterSha256': digest(archive),
              'changedEntries': list(replacements), 'unchangedEntries': len(before) - len(replacements),
              'payloadComparison': 'passed', 'checkpoint': str(checkpoint)}
    target = ROOT / 'theseus' / 'reports' / 'client-localization.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
