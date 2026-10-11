"""Read-only, standard-library checks for the prepared repository scaffold.

No runtime imports, dependency downloads, game launches, or service actions.
Historical evidence links require custody holdings and are outside this check.
"""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    '.gitignore', '.gitattributes', '.editorconfig', 'README.md', 'LICENSE',
    'NOTICE', 'LICENSES/README.md', 'LICENSES/inventory.json', 'CONTRIBUTING.md',
    'CODE_OF_CONDUCT.md', 'SECURITY.md', 'SUPPORT.md', 'GOVERNANCE.md',
    'CITATION.cff', 'CHANGELOG.md', 'docs/walkthrough.md',
    'docs/open-source-release.md', '.github/PULL_REQUEST_TEMPLATE.md',
    '.github/ISSUE_TEMPLATE/config.yml',
    '.github/ISSUE_TEMPLATE/evidence_correction.yml',
    '.github/ISSUE_TEMPLATE/documentation_question.yml',
    '.github/workflows/documentation.yml',
)

def main():
    for name in REQUIRED:
        path = ROOT/name
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f'Missing/empty community file: {name}')
        if '*** Add File:' in path.read_text(encoding='utf-8'):
            raise ValueError(f'Unexpected patch marker: {name}')
    inventory = json.loads((ROOT/'LICENSES/inventory.json').read_text(encoding='utf-8'))
    for item in inventory['copiedNotices']:
        path = (ROOT/item['copy']).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('License notice path escapes repository')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Copied license notice changed: {item["copy"]}')
    links = 0
    for name in REQUIRED:
        if not name.endswith('.md'):
            continue
        page = ROOT/name
        for match in re.finditer(r'\[[^\]\n]+\]\(([^\s]+?)\)', page.read_text(encoding='utf-8')):
            target = match[1]
            if target.startswith(('http:', 'https:', 'mailto:')):
                continue
            filename = unquote(target.split('#', 1)[0])
            path = (page.parent/filename).resolve()
            if not path.is_relative_to(ROOT) or not path.exists():
                raise ValueError(f'Broken community link: {name} -> {target}')
            links += 1
    print(json.dumps({'status':'passed','communityFiles':len(REQUIRED),
        'localCommunityLinks':links,'copiedLicenseNotices':len(inventory['copiedNotices']),
        'runtimeActions':0,'scope':'Prepared community files; not license clearance, full wiki verification or runtime acceptance.'}))

if __name__ == '__main__':
    main()
