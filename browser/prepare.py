"""Build the browser's one manifest from the actual local installation.

Does not start a native executable or alter any game file. Payloads are served
from their original paths; no multi-gigabyte duplicate of the game is needed.
"""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from platform_dlls import prepare_adapters

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UPSTREAM = ROOT / 'theseus/tools/wine-assembly'
DATA = ROOT / 'client/data'
GENERATED = HERE / 'generated'
sys.path.insert(0, str(ROOT / 'theseus/tools/python'))


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def prepare(runtime_only=False):
    import pefile

    lock = json.loads((HERE / 'dependencies.json').read_text())
    expected = lock['wineAssembly']['commit']
    actual = subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != expected:
        raise RuntimeError(f'Unexpected compatibility dependency: {actual}; expected {expected}')
    GENERATED.mkdir(exist_ok=True)
    platform = prepare_adapters(GENERATED / 'platform', ROOT)
    # Use the dependency's own browser load order, not a second hand-maintained list.
    html = (UPSTREAM / 'index.html').read_text(encoding='utf-8')
    block = html.split('const WINE_RUNTIME_SCRIPTS = Object.freeze([', 1)[1].split(']);', 1)[0]
    runtime_scripts = re.findall(r'^\s*"([^"\n]+\.js)"', block, re.M)
    if not runtime_scripts or runtime_scripts[0] != 'lib/region-map.generated.js':
        raise RuntimeError('Compatibility dependency script manifest changed')
    runtime = []
    for name in runtime_scripts:
        path = UPSTREAM / name
        runtime.append({'url': name, 'sha256': sha256(path)})
    wasm = UPSTREAM / 'build/wine-assembly.wasm'
    compat = UPSTREAM / 'build/wine-assembly.compat.wasm'
    for path in (wasm, compat):
        if not path.is_file():
            raise RuntimeError('Build Wine-Assembly before preparing the application')

    runtime_info = {'commit': actual, 'scripts': runtime,
                    'wasm': {'url': 'build/wine-assembly.wasm', 'sha256': sha256(wasm)},
                    'compat': {'url': 'build/wine-assembly.compat.wasm', 'sha256': sha256(compat)}}
    # Workers import scripts outside the page's script list. Preserve the full
    # local JS identity so captures can verify the bytes the browser received.
    runtime_info['sourceFiles'] = {p.relative_to(UPSTREAM).as_posix(): sha256(p)
        for p in sorted((UPSTREAM / 'lib').glob('*.js'))}
    runtime_info['sourceFiles']['host.js'] = sha256(UPSTREAM / 'host.js')
    for name in ('main.js', 'local_server_wire.js'):
        runtime_info['sourceFiles'][name] = sha256(HERE / name)
    runtime_info['integration'] = {name: sha256(HERE / name)
        for name in ('main.js', 'index.html', 'prepare.py', 'serve.py', 'runtime_cache.js', 'startup_telemetry.js', 'benchmark_startup.py', 'benchmark_artifacts.cjs', 'test_runtime_cache.py', 'test_artifact_cache.cjs', 'test_startup_telemetry.cjs', 'test_benchmark_observation.py', 'capture.py', 'capture_probe.js',
                     'test_capture_draws.cjs', 'test_wire_diagnostics.cjs', 'test_shader_relative_web.py', 'test_worker_wall_clock.cjs', 'test_worker_sse.cjs', 'test_heap_arena_locality.cjs',
                     'inspect_skinning.py', 'test_skinning.cjs', 'reference/skinning.json', 'test_movhlps.cjs',
                     'inspect_vp_mode.py', 'test_vp_mode.cjs', 'reference/software-vertex-processing.json',
                     'network.py', 'local_server_wire.js', 'test_network.py', 'test_network_wasm.py', 'test_network_wasm.cjs', 'test_breakpoint_snapshots.cjs', 'test_capture_input.py', 'test_capture_threads.cjs', 'test_d3dx_mesh.cjs', 'inspect_mesh_adjacency.py', 'reference/mesh-adjacency.json', 'dependencies.json',
                      'bootstrap.py', 'test_runtime.cjs', 'test_wininet.cjs', 'test_fonts.cjs', 'test_font_modes.cjs', 'test_font_cells.cjs', 'reference/font-cells.json', 'test_font_phantoms.cjs', 'reference/font-phantoms.json', 'font_reference.py', 'compare_font_reference.cjs', 'test_d3d.cjs', 'test_winsock_events.cjs', 'test_sparse_resources.cjs', 'test_sparse_textures.cjs', 'test_sparse_color_transfers.cjs', 'test_swapchain.cjs', 'test_swapchain_web.py', 'test_server.py', 'inspect_activation_contexts.py', 'inspect_lua_capture.py',
                     'inspect_windows_paths.py', 'inspect_windows_strings.py', 'inspect_process_modules.py', 'inspect_winsock.py', 'inspect_winsock_events.py', 'inspect_graphics_debug.py', 'inspect_d3d_interfaces.py', 'inspect_network_adapters.py', 'platform_dlls.py', 'test_platform.cjs',
                     'shader_validator.py', 'inspect_shader_validator.py', 'test_shader_validator.cjs', 'reference/shader-validator.json',
                      'inspect_texture_update.py', 'test_update_texture.cjs', 'reference/texture-update.json',
                      'inspect_stretch_rect.py', 'test_stretch_rect.cjs', 'test_stretch_rect_web.py', 'reference/stretch-rect.json',
                      'inspect_processes.py', 'test_processes.cjs', 'reference/processes.json',
                     'inspect_shader_address.py', 'reference/shader-address.json',
                     'inspect_shader_link.py', 'test_shader_link_web.py', 'reference/shader-link.json', 'reference/start-game-shader-link.json',
                     'inspect_reset_parameters.py', 'inspect_reset_parameters_x86.ps1',
                     'test_d3d9_composition.cjs', 'test_input_web.py',
                     'test_keyboard_modifiers.cjs', 'inspect_keyboard_modifiers.py', 'reference/keyboard-modifiers.json',
                     'inspect_crypto.py', 'inspect_crypto_x86.ps1', 'test_crypto.cjs',
                     'reference/crypto.json', 'reference/crypto-x86.json', 'reference/crypto-pinvoke-x64.json',
                     'inspect_winsock_overlapped.py', 'test_wsasocket.cjs', 'reference/winsock-overlapped.json',
                     'test_winsock_overlapped.cjs', 'inspect_winsock_overlapped_x86.ps1',
                     'inspect_wsasendto.py', 'reference/wsasendto.json',
                     'inspect_socket_iocp.py', 'reference/socket-iocp.json', 'reference/original-socket-calls.json', 'reference/client-import-coverage.json',
                     'reference/winsock-overlapped-x86.json', 'reference/winsock-overlapped-pinvoke-x64.json',
                     'reference/reset-parameters.json', 'reference/reset-parameters-x86.json',
                     'reference/file-attribute-errors.json', 'reference/string-comparison.json',
                     'reference/shell-strings.json', 'reference/process-modules.json', 'reference/windows-paths.json', 'reference/winsock.json', 'reference/winsock-events.json', 'reference/graphics-debug.json', 'reference/d3d-interfaces.json', 'reference/network-adapters.json')}
    runtime_info['platformDlls'] = platform
    # Preserve the exact source changes alongside the executable identity.
    diff = subprocess.check_output(['git', '-C', str(UPSTREAM), 'diff', '--binary', 'HEAD'])
    untracked = subprocess.check_output(['git', '-C', str(UPSTREAM), 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    for name in sorted(untracked):
        # The TLS/thread/audio regressions and their PE fixture builder are
        # part of the repair. A fresh checkout needs them for maintenance.
        if not name.startswith(('src/', 'lib/', 'test/')) or Path(name).suffix not in ('.wat', '.js', '.json'):
            continue
        source = (UPSTREAM / name).read_text(encoding='utf-8')
        lines = source.splitlines()
        diff += (f'diff --git a/{name} b/{name}\nnew file mode 100644\n--- /dev/null\n+++ b/{name}\n'
                 f'@@ -0,0 +1,{len(lines)} @@\n' + ''.join('+' + line + '\n' for line in lines)).encode('utf-8')
    (GENERATED / 'runtime.patch').write_bytes(diff)
    (HERE / 'patches').mkdir(exist_ok=True)
    (HERE / 'patches/wine-assembly.patch').write_bytes(diff)
    runtime_info['patchSha256'] = hashlib.sha256(diff).hexdigest()
    if runtime_only:
        manifest = json.loads((GENERATED / 'manifest.json').read_text(encoding='utf-8'))
        manifest['title'] = 'HEAV3NS-COMBO'
        manifest['protocol'] = 'BROCWIN'
        manifest['runtime'] = runtime_info
        manifest['files'] = [f for f in manifest['files'] if not f['url'].startswith('platform/')] + platform
        # Read-only media use the existing sized range provider, like archives.
        # Their original names, sizes, contents and API behavior remain intact;
        # startup no longer downloads every unused music track before entry.
        for file in manifest['files']:
            if Path(file['url']).suffix.lower() in {'.ogg', '.wav', '.mp3'}:
                file['loadMode'] = 'lazy'
        api_names = {a['name'] for a in json.loads((UPSTREAM / 'src/api_table.json').read_text())}
        for module in manifest['modules']:
            for lib in module['imports']:
                if lib['implementation'] == 'wasm-host':
                    lib['unresolvedNames'] = [s for s in lib['symbols'] if s not in api_names]
        write_json(GENERATED / 'manifest.json', manifest)
        print(json.dumps({'runtime': runtime_info['wasm'], 'patchSha256': runtime_info['patchSha256']}))
        return

    files = []
    # This is an explicit resource set, not a workspace/static-directory export.
    # Exclude captures, logs, saved credentials, and management scripts.
    suffixes = {'.kom', '.dll', '.ttf', '.ttc', '.otf', '.x', '.y', '.tet', '.xet',
                '.dds', '.tga', '.bmp', '.ogg', '.wav', '.mp3', '.fx', '.ess', '.dat', '.des'}
    config_names = {'elswordkr.ini', 'gameoptions.lua', 'gamepadconfig.lua',
                    'selectedservergroup.lua', 'tutorsystem.lua'}
    sources = [p for p in DATA.rglob('*') if p.is_file() and
               (p.suffix.lower() in suffixes or p.name.lower() in config_names | {'x2.exe'})]
    for path in sorted(sources):
        relative = path.relative_to(DATA).as_posix()
        files.append({'url': 'payload/' + relative, 'source': path.relative_to(ROOT).as_posix(),
                      'vfsPath': 'c:\\joysword\\' + relative.replace('/', '\\'),
                      'size': path.stat().st_size, 'sha256': sha256(path),
                  'loadMode': 'lazy' if path.suffix.lower() in {'.kom', '.ogg', '.wav', '.mp3'} else 'required'})
        if len(files) % 40 == 0:
            print(f'Hashed {len(files)}/{len(sources)} game inputs', flush=True)
    api = json.loads((UPSTREAM / 'src/api_table.json').read_text())
    api_names = {a['name'] for a in api}
    local_dlls = {p.name.lower(): p for p in sources if p.suffix.lower() == '.dll'}
    # The installed 32-bit Microsoft runtime is a local input with its own hash.
    # It is not fetched from a third-party binary site or shipped in source control.
    for name in ('mfc42.dll', 'msvcrt.dll'):
        if name not in local_dlls:
            path = Path('C:/Windows/SysWOW64') / name
            if path.exists():
                local_dlls[name] = path
                files.append({'url': 'system/' + name, 'source': str(path),
                              'vfsPath': 'c:\\windows\\system\\' + name,
                              'size': path.stat().st_size, 'sha256': sha256(path), 'loadMode': 'required'})

    by_leaf = {Path(f['source']).name.lower(): f for f in files}
    queue = [DATA / 'x2.exe']
    seen = set()
    modules = []
    native_dlls = []
    while queue:
        path = queue.pop(0)
        if path.name.lower() in seen:
            continue
        seen.add(path.name.lower())
        pe = pefile.PE(str(path), fast_load=True)
        pe.parse_data_directories(directories=[1])
        imports = []
        for lib in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
            name = lib.dll.decode('ascii')
            symbols = [i.name.decode('ascii') if i.name else '#' + str(i.ordinal) for i in lib.imports]
            local = local_dlls.get(name.lower())
            # Prefer native app libraries and the matching CRT, so their C++ ABI
            # and algorithms are supplied by the actual binary, not API-name guesses.
            use_native = local is not None
            if use_native:
                queue.append(local)
            imports.append({'dll': name, 'symbols': symbols,
                            'implementation': 'original-pe' if use_native else 'wasm-host',
                            'unresolvedNames': [] if use_native else [s for s in symbols if s not in api_names]})
        modules.append({'name': path.name, 'sha256': sha256(path),
                        'imageBase': pe.OPTIONAL_HEADER.ImageBase,
                        'entryPoint': pe.OPTIONAL_HEADER.ImageBase + pe.OPTIONAL_HEADER.AddressOfEntryPoint,
                        'imports': imports})
        if path.suffix.lower() == '.dll':
            native_dlls.append(by_leaf[path.name.lower()]['url'])
    # DLL loader sorts dependencies before DllMain. The list itself remains stable.
    manifest = {
        'schema': 'theseus.browser-runtime/v1',
        'title': 'HEAV3NS-COMBO',
        'protocol': 'BROCWIN',
        'execution': 'original-x86-in-webassembly',
        'acceptance': 'incomplete',
        'exe': 'payload/x2.exe', 'exeGuestPath': 'c:\\joysword\\x2.exe',
        'args': 'pxk19slammsu286nfha02kpqnf729ck',
        'runtime': runtime_info,
        'dlls': native_dlls,
        'files': files + platform,
        'modules': modules,
        'verified': [],
        'unverified': ['client startup', 'login', 'character selection', 'world loading',
                       'combat', 'audio', 'networking', 'saving', 'behavioral parity'],
    }
    write_json(GENERATED / 'manifest.json', manifest)
    print(json.dumps({'files': len(files), 'bytes': sum(f['size'] for f in files),
                      'nativeModules': len(modules), 'wasm': manifest['runtime']['wasm']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-only', action='store_true', help='Refresh compatibility build identity, retaining the game-input manifest')
    prepare(parser.parse_args().runtime_only)
