"""Build, verify and seal the local BROCWIN maintainer reference.

No services, game processes, credential files or databases are opened.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / 'theseus/wiki'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def contained(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes root: {name}')
    return path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_catalog(catalog, root=ROOT, wiki=WIKI):
    if catalog.get('schema') != 'brocwin.knowledge-catalog/v1':
        raise ValueError('Unsupported knowledge schema')
    ids = [item['id'] for item in catalog['evidence']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate evidence ID')
    subsystem_ids = [s['id'] for s in catalog['subsystems']]
    if len(subsystem_ids) != len(set(subsystem_ids)):
        raise ValueError('Duplicate subsystem ID')
    if catalog['gameplayBaselineEvidence'] not in ids:
        raise ValueError('Unknown gameplay baseline evidence')
    if catalog.get('currentBuildEvidence') and catalog['currentBuildEvidence'] not in ids:
        raise ValueError('Unknown current build evidence')
    for item in catalog['evidence']:
        if not re.fullmatch(r'[a-z0-9-]+', item['id']):
            raise ValueError('Invalid evidence ID')
        if not contained(root, item['path']).is_file():
            raise ValueError(f'Missing original evidence: {item["path"]}')
    for system in catalog['subsystems']:
        if not contained(wiki, system['page']).is_file():
            raise ValueError(f'Missing subsystem page: {system["page"]}')
        if not set(system['evidence']).issubset(ids):
            raise ValueError(f'Unknown evidence in {system["id"]}')
        for name in system['implementation'] + system['tests']:
            if not contained(root, name).is_file():
                raise ValueError(f'Missing implementation/test: {name}')


def checked_frozen_state(catalog, root=ROOT):
    item = catalog.get('frozenState')
    if not item:
        return None
    data = contained(root, item['path']).read_bytes()
    if digest(data) != item['sha256']:
        raise ValueError('Frozen state record changed')
    record = json.loads(data)
    if record.get('schema') != 'brocwin.frozen-state/v1':
        raise ValueError('Unsupported frozen state schema')
    for name, expected in record['files'].items():
        if digest(contained(root, name).read_bytes()) != expected:
            raise ValueError(f'Frozen file changed: {name}')
    return record


def checked_manifest(root=ROOT, frozen=None):
    manifest = read_json(root / 'theseus/browser/generated/manifest.json')
    runtime = manifest['runtime']
    dependency = root / 'theseus/tools/wine-assembly'
    checked = []
    drift = frozen['preparedSourceDrift'] if frozen else {}
    observed_drift = set()
    for group, base in (('sourceFiles', dependency), ('integration', root / 'theseus/browser')):
        for name, expected in sorted(runtime[group].items()):
            source = base / name
            if group == 'sourceFiles' and name in ('main.js', 'local_server_wire.js'):
                source = root / 'theseus/browser' / name
            actual = digest(source.read_bytes())
            name_in_root = source.relative_to(root).as_posix()
            if actual != expected:
                entry = drift.get(name_in_root)
                if entry != {'preparedSha256': expected, 'frozenSha256': actual}:
                    raise ValueError(f'Manifest source mismatch: {source.relative_to(root)}')
                observed_drift.add(name_in_root)
            checked.append(source.relative_to(root).as_posix())
    for kind in ('wasm', 'compat'):
        item = runtime[kind]
        if digest((dependency / item['url']).read_bytes()) != item['sha256']:
            raise ValueError(f'Manifest {kind} mismatch')
    for name in ('generated/runtime.patch', 'patches/wine-assembly.patch'):
        if digest((root / 'theseus/browser' / name).read_bytes()) != runtime['patchSha256']:
            raise ValueError(f'Manifest patch mismatch: {name}')
    if observed_drift != set(drift):
        raise ValueError('Frozen source drift no longer matches prepared manifest')
    return manifest, sorted(set(checked))


def checked_current_evidence(catalog, runtime, root=ROOT):
    evidence_id = catalog.get('currentBuildEvidence')
    if not evidence_id:
        return None
    item = next(item for item in catalog['evidence'] if item['id'] == evidence_id)
    record = read_json(contained(root, item['path']))
    for field in ('wasm', 'compat', 'patchSha256'):
        if record.get(field) != runtime[field]:
            raise ValueError(f'Current build evidence belongs to a different candidate: {evidence_id} ({field})')
    return evidence_id


def build_outputs(root=ROOT, wiki=WIKI):
    catalog = read_json(wiki / 'catalog.json')
    validate_catalog(catalog, root, wiki)
    frozen = checked_frozen_state(catalog, root)
    manifest, checked = checked_manifest(root, frozen)
    runtime = manifest['runtime']
    frozen_drift = frozen['preparedSourceDrift'] if frozen else {}
    prepared_matches = [name for name in checked if name not in frozen_drift]
    current_evidence = checked_current_evidence(catalog, runtime, root)
    files = sorted({name for system in catalog['subsystems']
                    for name in system['implementation'] + system['tests']})
    source_index = {name: {'sha256': digest((root / name).read_bytes()),
                           'bytes': (root / name).stat().st_size} for name in files}
    outputs = {}
    evidence = []
    for item in catalog['evidence']:
        data = (root / item['path']).read_bytes()
        local = f'evidence/{item["id"]}.json'
        outputs['generated/' + local] = data
        record = json.loads(data)
        evidence.append({**item, 'copy': local, 'sha256': digest(data),
                         'schema': record.get('schema'),
                         'wasm': record.get('wasm'),
                         'verifiedGameplay': record.get('verifiedGameplay'),
                         'acceptance': record.get('acceptance')})
    identity = {
        'schema': 'brocwin.knowledge-identity/v1', 'version': catalog['version'],
        'protocol': catalog['protocol'], 'client': catalog['client'],
        'acceptance': catalog['acceptance'],
        'currentBuild': {'commit': runtime['commit'], 'wasm': runtime['wasm'],
                         'compat': runtime['compat'], 'patchSha256': runtime['patchSha256'],
                         'manifestSha256': digest((root / 'theseus/browser/generated/manifest.json').read_bytes()),
                         'sourceIdentitiesChecked': checked,
                         'sourceIdentitiesMatchingPreparedManifest': prepared_matches,
                         'sourceDriftVerifiedByFrozenInventory': frozen_drift},
        'originalModules': [{'name': m['name'], 'sha256': m['sha256'],
                             'imageBase': m['imageBase']} for m in manifest['modules']],
        'gameplayBaselineEvidence': catalog['gameplayBaselineEvidence'],
        'currentBuildEvidence': current_evidence,
        'frozenState': catalog.get('frozenState'),
        'limits': ['Prepared module/patch identity and frozen working-source identity are separate; '
                   'sourceIdentitiesChecked includes explicitly recorded frozen drift.',
                   'Current build identity does not inherit an older capture\'s gameplay verification.',
                   'API import presence and test enumeration are not compatibility success claims.',
                   'Copied JSON records retain references relative to their original report folders.'],
    }
    outputs['generated/identity.json'] = encoded(identity)
    outputs['generated/sources.json'] = encoded(source_index)
    outputs['generated/evidence.json'] = encoded(evidence)
    references = [{'path':p.relative_to(root).as_posix(), 'sha256':digest(p.read_bytes()),
                   'bytes':p.stat().st_size} for p in sorted((root/'theseus/browser/reference').glob('*.json'))]
    outputs['generated/native-references.json'] = encoded(references)
    lines = ['# Generated source and evidence index', '',
             '[Wiki home](../README.md) · [Identity](identity.json) · [Source hashes](sources.json)', '',
             'Generated by `python theseus/knowledge.py --write`; do not edit this page manually.', '',
             f'Edition **{catalog["version"]}**. Prepared Wasm: `{runtime["wasm"]["sha256"]}`.', '',
             f'Patch: `{runtime["patchSha256"]}`. Dependency: `{runtime["commit"]}`.', '',
             f'{len(checked)} manifest-listed source paths verified: '
             f'{len(prepared_matches)} match the prepared manifest; '
             f'{len(frozen_drift)} differ and match the separate frozen inventory. '
             'Prepared binaries and frozen working sources are distinct identities; '
             'neither establishes application acceptance.', '',
             '## Evidence', '', '| ID | Kind | Preserved record | Original record |',
             '| --- | --- | --- | --- |']
    for item in evidence:
        lines.append(f'| {item["id"]} | {item["kind"]} | '
                     f'[JSON]({item["copy"]}) | [original](../../../{item["path"]}) |')
    lines += ['', 'JSON copies are byte-exact records. Their images, logs and frozen sources '
              'remain in the original folders; the copies do not relocate those references.', '']
    if frozen:
        lines += ['## Frozen closeout', '',
                  '[Closeout](../closeout.md). Prepared module/patch identities remain unchanged. '
                  'The frozen inventory separately verifies source-only work and explicitly recorded '
                  'observer drift; it does not certify a freshly prepared application.', '',
                  f'Frozen inventory: {len(frozen["files"])} files; '
                  f'{len(frozen["preparedSourceDrift"])} prepared integration source differences.', '']
    if current_evidence:
        lines += [f'Current candidate: [{current_evidence}](evidence/{current_evidence}.json). '
                  'Both module identities and the patch match the prepared build. '
                  'Use that review\'s explicit bounds; matching identities do not imply full acceptance.', '']
    else:
        lines += ['No application review is assigned to the current candidate.', '']
    for system in catalog['subsystems']:
        lines += [f'## {system["id"]}', '', f'[Maintainer page](../{system["page"]})', '',
                  '| Role | File |', '| --- | --- |']
        for role in ('implementation', 'tests'):
            for name in system[role]:
                lines.append(f'| {role} | [{name}](../../../{name}) |')
        lines += ['', 'Evidence: ' + ', '.join(f'[{name}](evidence/{name}.json)' for name in system['evidence']) + '.', '']
    lines += ['## Native and original reference inventory', '',
              'These are reference records, not an assertion that every case passes the current runtime.', '',
              '| Record | SHA-256 |', '| --- | --- |']
    for item in references:
        lines.append(f'| [{Path(item["path"]).name}](../../../{item["path"]}) | `{item["sha256"]}` |')
    lines.append('')
    outputs['generated/INDEX.md'] = ('\n'.join(lines) + '\n').encode('utf-8')
    return outputs


def sync_outputs(outputs, write=False, wiki=WIKI):
    problems = []
    # Check everything before mutation; evidence changes are never silently blessed.
    for name, data in outputs.items():
        path = contained(wiki, name)
        if path.exists() and path.read_bytes() != data and name.startswith('generated/evidence/'):
            raise ValueError(f'Preserved evidence changed: {name}; add a correction with a new ID')
        if not path.exists() or path.read_bytes() != data:
            problems.append(name)
    if not write and problems:
        raise ValueError('Stale/missing generated files: ' + ', '.join(problems))
    if write:
        for name in problems:
            path = contained(wiki, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(outputs[name])
    return len(problems)


def check_links(wiki=WIKI, root=ROOT):
    checked = 0
    failures = []
    for page in wiki.rglob('*.md'):
        for match in re.finditer(r'\[[^\]\n]+\]\(([^\s]+?)\)', page.read_text(encoding='utf-8')):
            target = match[1].strip('<>')
            if target.startswith(('http:', 'https:', 'mailto:')):
                continue
            filename, _, anchor = unquote(target).partition('#')
            path = (page.parent / filename).resolve() if filename else page
            if not path.is_relative_to(root.resolve()) or not path.exists():
                failures.append(f'{page.relative_to(wiki)} -> {target}')
            elif anchor and path.suffix == '.md':
                headings = re.findall(r'^#+\s+(.+?)\s*#*$', path.read_text(encoding='utf-8'), re.M)
                slugs = {re.sub(r'[^\w\- ]', '', h.lower()).replace(' ', '-') for h in headings}
                if anchor not in slugs:
                    failures.append(f'{page.relative_to(wiki)} -> unknown anchor {target}')
            checked += 1
    if failures:
        raise ValueError('Broken local links:\n' + '\n'.join(failures))
    return checked


def seal_release(version, wiki=WIKI, root=ROOT):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Release must be a three-part numeric version')
    if read_json(wiki / 'catalog.json')['version'] != version:
        raise ValueError('Catalog version must match release')
    target = wiki / 'releases' / f'{version}.json'
    archive = root / 'theseus/checkpoints' / f'brocwin-knowledge-{version}.zip'
    if target.exists() or archive.exists():
        raise ValueError('Release already exists; choose a new version')
    paths = [p for p in wiki.rglob('*') if p.is_file() and 'releases' not in p.relative_to(wiki).parts]
    paths += [root / f'theseus/{name}' for name in
              ('knowledge.py', 'test_knowledge.py', 'AGENTS.md', 'README.md', 'provenance.json')]
    browser = root / 'theseus/browser'
    paths += [p for p in browser.iterdir() if p.is_file() and p.suffix in ('.py','.js','.cjs','.json','.md','.html','.ps1')]
    paths += list((browser / 'reference').glob('*.json'))
    paths += [browser / 'patches/wine-assembly.patch']
    paths = sorted(set(paths))
    record = {'schema':'brocwin.knowledge-release/v1','version':version,
              'sealedAt':datetime.now(timezone.utc).isoformat(),
              'files':{p.relative_to(root).as_posix():digest(p.read_bytes()) for p in paths},
              'excludes':['original game/platform binaries','credentials','database contents',
                          'large original report artifacts; retained in local reports',
                          'dependency checkout; recover from pin and included patch'],
              'gitCommitCreated':False}
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in paths:
            bundle.write(path, path.relative_to(root).as_posix())
        bundle.writestr('release.json', encoded(record))
    record['archive'] = {'path':archive.relative_to(root).as_posix(),
                         'sha256':digest(archive.read_bytes())}
    target.parent.mkdir(exist_ok=True)
    with target.open('xb') as stream:
        stream.write(encoded(record))
    return record['archive']


def verify_release(version, wiki=WIKI, root=ROOT):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Release must be a three-part numeric version')
    record = read_json(wiki / 'releases' / f'{version}.json')
    archive = contained(root, record['archive']['path'])
    if digest(archive.read_bytes()) != record['archive']['sha256']:
        raise ValueError('Release archive hash mismatch')
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or set(names) != set(record['files']) | {'release.json'}:
            raise ValueError('Release archive inventory mismatch')
        for name, expected in record['files'].items():
            if digest(bundle.read(name)) != expected:
                raise ValueError(f'Release artifact hash mismatch: {name}')
        embedded = {key:value for key,value in record.items() if key != 'archive'}
        if json.loads(bundle.read('release.json')) != embedded:
            raise ValueError('Embedded release record mismatch')
    return {'version':version, 'verifiedArtifacts':len(record['files']), 'archive':record['archive']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--write', action='store_true')
    action.add_argument('--check', action='store_true')
    action.add_argument('--seal-release', metavar='VERSION')
    action.add_argument('--verify-release', metavar='VERSION')
    args = parser.parse_args()
    if args.verify_release:
        print(json.dumps({'status':'passed', **verify_release(args.verify_release)}))
        return
    outputs = build_outputs()
    changed = sync_outputs(outputs, args.write)
    links = check_links()
    result = {'status':'passed','generatedFiles':len(outputs),'updated':changed,'localLinks':links}
    if args.seal_release:
        result['release'] = seal_release(args.seal_release)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        raise SystemExit(1)
