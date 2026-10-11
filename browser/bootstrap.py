"""Reproduce the pinned browser runtime locally, without changing game files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare import HERE, ROOT, UPSTREAM


def run(args, cwd=ROOT, **kwargs):
    print(' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=cwd, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify pinned checkout and applied patch without installing or building')
    args = parser.parse_args()
    lock = json.loads((HERE / 'dependencies.json').read_text())
    spec = lock['wineAssembly']
    patch = HERE / 'patches/wine-assembly.patch'
    if not (UPSTREAM / '.git').is_dir():
        if args.check:
            raise RuntimeError('Pinned runtime checkout is missing')
        if UPSTREAM.exists():
            raise RuntimeError(f'Refusing to replace an existing non-Git directory: {UPSTREAM}')
        UPSTREAM.parent.mkdir(parents=True, exist_ok=True)
        run(['git', '-c', 'core.autocrlf=false', 'clone', '--filter=blob:none',
             '--no-checkout', spec['repository'], UPSTREAM])
        run(['git', 'config', 'core.autocrlf', 'false'], UPSTREAM)
        run(['git', 'config', 'core.eol', 'lf'], UPSTREAM)
        run(['git', 'checkout', '--detach', spec['commit']], UPSTREAM)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=UPSTREAM, text=True).strip()
    if actual != spec['commit']:
        raise RuntimeError(f'Existing checkout is {actual}; expected {spec["commit"]}. No files changed.')
    applied = subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)],
                             cwd=UPSTREAM, capture_output=True).returncode == 0
    if not applied:
        if args.check:
            raise RuntimeError('The preserved Theseus patch does not match this checkout')
        # A conflict stops here; never reset a checkout containing someone's work.
        run(['git', 'apply', '--check', patch], UPSTREAM)
        run(['git', 'apply', patch], UPSTREAM)
    if args.check:
        print('PASS: pinned dependency and preserved source patch match')
        return
    packages = ['pefile', 'capstone', 'playwright']
    run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
         '--target', ROOT / 'theseus/tools/python', '--upgrade',
         *[f'{name}=={lock["researchTools"][name]}' for name in packages],
         *[f'{name}=={version}' for name, version in lock['runtimeTools'].items()]])
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js is required to build the compatibility runtime')
    npm_cli = Path(node).parent / 'node_modules/npm/bin/npm-cli.js'
    npm = [node, str(npm_cli)] if npm_cli.is_file() else [shutil.which('npm') or 'npm']
    run([*npm, 'ci', '--omit=dev', '--omit=optional', '--ignore-scripts'], UPSTREAM)
    git_bash = Path('C:/Program Files/Git/bin/bash.exe')
    bash = str(git_bash) if git_bash.is_file() else shutil.which('bash')
    if not bash:
        raise RuntimeError('Bash (Git for Windows includes it) is required for the build gates')
    run([bash, 'tools/build.sh'], UPSTREAM)
    run([node, UPSTREAM / 'test/test-directsound-enumerate.js'], timeout=120)
    run([node, UPSTREAM / 'test/test-directsound-ordinals.js'], timeout=120)
    run([node, HERE / 'test_runtime.cjs'], timeout=90)
    run([node, HERE / 'test_wininet.cjs'], timeout=90)
    run([sys.executable, HERE / 'prepare.py'])
    run([node, HERE / 'test_platform.cjs'], timeout=90)
    run([node, HERE / 'test_shader_validator.cjs'], timeout=120)
    run([node, HERE / 'test_fonts.cjs'], timeout=90)
    run([node, HERE / 'test_font_modes.cjs'], timeout=120)
    run([node, HERE / 'test_font_cells.cjs'], timeout=120)
    run([node, HERE / 'test_d3d.cjs'], timeout=90)
    run([node, HERE / 'test_winsock_events.cjs'], timeout=90)
    run([node, HERE / 'test_sparse_resources.cjs'], timeout=120)
    run([node, HERE / 'test_sparse_textures.cjs'], timeout=90)
    run([node, HERE / 'test_sparse_color_transfers.cjs'], timeout=90)
    run([node, HERE / 'test_swapchain.cjs'], timeout=120)
    run([node, HERE / 'test_d3d9_composition.cjs'], timeout=90)
    run([node, HERE / 'test_crypto.cjs'], timeout=90)
    run([node, HERE / 'test_wsasocket.cjs'], timeout=90)
    run([node, HERE / 'test_winsock_overlapped.cjs'], timeout=120)
    run([node, HERE / 'test_update_texture.cjs'], timeout=120)
    run([node, HERE / 'test_stretch_rect.cjs'], timeout=120)
    run([sys.executable, HERE / 'test_server.py'])
    run([sys.executable, HERE / 'test_network.py'])
    run([sys.executable, HERE / 'test_network_wasm.py'])
    print('Browser runtime prepared. Run: python theseus/browser/serve.py')


if __name__ == '__main__':
    main()
