"""Scoped launch adapter for the inherited JoySword native runtime.

Reuses start-offline.py's server order, arguments and readiness checks.
Owns only processes whose executable path AND creation time match its receipt.
"""
from __future__ import annotations
import argparse
import contextlib
import csv
import ctypes
from ctypes import wintypes
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from isolate import ROOT, ENV, CONTAINER, read_env, check_container, sql
STATE = ROOT / 'theseus' / 'runtime' / 'processes.json'


def inherited_start():
    spec = importlib.util.spec_from_file_location('theseus_inherited_start', ROOT / 'scripts' / 'start-offline.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def inspect_process(pid, terminate=None):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    handle = kernel.OpenProcess(0x1000 | (1 if terminate else 0), False, pid)
    if not handle:
        return None
    try:
        path = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(path))
        times = [wintypes.FILETIME() for _ in range(4)]
        code = wintypes.DWORD()
        if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)) or not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        if code.value != 259:
            return None
        identity = {'pid': pid, 'path': str(Path(path.value).resolve()),
                    'created': (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime}
        if terminate:
            if identity != terminate or not Path(identity['path']).is_relative_to(ROOT):
                raise RuntimeError(f'Refusing to stop unowned PID {pid}')
            if not kernel.TerminateProcess(handle, 0):
                raise ctypes.WinError(ctypes.get_last_error())
        return identity
    finally:
        kernel.CloseHandle(handle)


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    temp.replace(STATE)


def receipt():
    return json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'processes': {}}


def alive(state):
    return {name: identity for name, identity in state['processes'].items()
            if inspect_process(identity['pid']) == identity}


def listeners():
    output = subprocess.check_output(['netstat', '-ano', '-p', 'tcp'], text=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
    return {(int(fields[1].rsplit(':', 1)[1]), int(fields[4]))
            for line in output.splitlines() if len(fields := line.split()) >= 5
            and fields[0] == 'TCP' and fields[3] == 'LISTENING'}


def clients():
    output = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq x2.exe', '/FO', 'CSV', '/NH'],
                                     text=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
    target = (ROOT / 'client' / 'data' / 'x2.exe').resolve()
    result = []
    for row in csv.reader(output.splitlines()):
        if len(row) > 1 and row[1].isdigit():
            identity = inspect_process(int(row[1]))
            if identity and Path(identity['path']) == target:
                result.append(identity)
    return result


def status():
    current = receipt()
    owned = alive(current)
    sockets = listeners()
    values = read_env(ENV)
    services = [{'id': spec.name, 'name': spec.name.removesuffix('Server'), 'host': '127.0.0.1',
                 'port': int(values.get(spec.port_env, spec.default_port)),
                 'online': spec.name in owned and
                 (int(values.get(spec.port_env, spec.default_port)), owned[spec.name]['pid']) in sockets}
                for spec in inherited_start().SERVERS]
    return {'ok': True, 'ready': bool(current.get('ready')) and all(item['online'] for item in services),
            'services': services, 'clientRunning': bool(clients()), 'owned': owned}


def database_ready():
    check_container()
    running = subprocess.check_output(['docker', 'inspect', '--format', '{{.State.Running}}', CONTAINER], text=True).strip()
    if running != 'true':
        subprocess.run(['docker', 'start', CONTAINER], check=True, stdout=subprocess.DEVNULL)
    for attempt in range(30):
        try:
            sql('SELECT 1;')
            return
        except RuntimeError:
            if attempt == 29:
                raise
            time.sleep(1)


def application_ready(started):
    for path in (ROOT / 'Elsword' / 'GameServer' / 'log').glob('log_*.htm'):
        if path.stat().st_mtime >= started:
            with path.open('rb') as stream:
                stream.seek(max(0, path.stat().st_size - 512 * 1024))
                if b'KGameServer::OnServerReadyComplete()' in stream.read():
                    return True
    return False


def preflight():
    check_container()
    values = read_env(ENV)
    if values.get('DB_PORT') != '15433' or values.get('DB_HOST') != '127.0.0.1' or Path(values['ELSWORD_ROOT']).resolve() != ROOT / 'Elsword':
        raise RuntimeError('Theseus runtime is not isolated')
    sql("IF (SELECT COUNT(*) FROM sys.databases WHERE name IN ('Account','Game01','ES_BILLING','Statistics') AND state_desc='ONLINE') <> 4 THROW 51000, 'Four recovered databases are required', 1;")
    inherited = inherited_start()
    for spec in inherited.SERVERS:
        executable = ROOT / 'Elsword' / spec.directory / spec.executable
        if not executable.is_file():
            raise RuntimeError(f'Missing native executable: {executable}')
        port = int(values.get(spec.port_env, spec.default_port))
        for number in (port, spec.secondary_port):
            if number is None:
                continue
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                try:
                    probe.bind(('0.0.0.0', number))
                except OSError as error:
                    raise RuntimeError(f'Port {number} is occupied; no existing process will be stopped') from error
    return inherited, values


def start():
    current = receipt()
    owned = alive(current)
    if owned:
        if status()['ready']:
            print('The Theseus native stack is already running.')
            return
        raise RuntimeError('A partial Theseus stack is running; stop it before retrying')
    database_ready()
    inherited, values = preflight()
    state = {'workspace': str(ROOT), 'started': time.time(), 'processes': {}, 'ready': False}
    processes = {}
    def owned_listener(host, port, timeout=0.75, exe_name=None):
        # The inherited probe accepts a live process without a listening socket.
        # Keep its wait loop, but require the actual socket to belong to our PID.
        owners = {process.pid for name, process in processes.items()
                  if exe_name is None or name.casefold() + '.exe' == exe_name.casefold()}
        output = subprocess.check_output(['netstat', '-ano', '-p', 'tcp'], text=True,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
        for line in output.splitlines():
            fields = line.split()
            if len(fields) >= 5 and fields[3] == 'LISTENING' and fields[1].endswith(f':{port}'):
                if int(fields[4]) in owners:
                    return True
        return False
    inherited.tcp_open = owned_listener
    try:
        for spec in inherited.SERVERS:
            directory = ROOT / 'Elsword' / spec.directory
            executable = directory / spec.executable
            print(f'Starting inherited {spec.name}', flush=True)
            process = subprocess.Popen([str(executable), values['SERVER_PROFILE'], '0'], cwd=directory,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            processes[spec.name] = process
            identity = inspect_process(process.pid)
            if identity is None or Path(identity['path']) != executable.resolve():
                raise RuntimeError(f'Could not verify {spec.name} ownership')
            state['processes'][spec.name] = identity
            save(state)
            inherited.wait_for_readiness(spec, values, processes, 60)
        deadline = time.monotonic() + 90
        while not application_ready(state['started']):
            inherited.wait_for_processes(processes, 1)
            if time.monotonic() >= deadline:
                raise RuntimeError('GameServer did not finish loading the combat runtime; inspect its log')
        state['ready'] = True
        save(state)
        print('Local combat runtime ready.', flush=True)
    except BaseException:
        for identity in reversed(list(state['processes'].values())):
            inspect_process(identity['pid'], terminate=identity)
        state['ready'] = False
        save(state)
        raise


def stop():
    if clients():
        raise RuntimeError('Exit the Theseus game normally before stopping its services, so progress can save')
    state = receipt()
    for name, identity in reversed(list(state['processes'].items())):
        result = inspect_process(identity['pid'], terminate=identity)
        if result:
            print(f'Stopped owned {name} (PID {identity["pid"]})')
    state['ready'] = False
    state['processes'] = {}
    save(state)


def client():
    existing = clients()
    if existing:
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.IsWindowVisible.argtypes = [wintypes.HWND]
        focused = False
        def visit(window, unused):
            nonlocal focused
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(window, ctypes.byref(pid))
            if pid.value == existing[0]['pid'] and user.IsWindowVisible(window):
                user.ShowWindow(window, 9)
                focused = bool(user.SetForegroundWindow(window))
                return False
            return True
        user.EnumWindows(callback_type(visit), 0)
        return {'ok': True, 'focused': focused, 'message': 'Theseus is already running.'}
    if not status()['ready']:
        raise RuntimeError('Start and verify the Theseus native stack first')
    environment = os.environ.copy()
    environment['__COMPAT_LAYER'] = 'RunAsInvoker'
    directory = ROOT / 'client' / 'data'
    process = subprocess.Popen([str(directory / 'x2.exe'), 'pxk19slammsu286nfha02kpqnf729ck'],
                               cwd=directory, env=environment)
    print(f'Launched the copied native client (PID {process.pid}).')
    return {'ok': True, 'focused': False, 'message': 'Local game launched. Profile: theseus / combo.'}


def display(resolution, fullscreen):
    if clients():
        raise RuntimeError('Exit the game before changing its display configuration')
    path = ROOT / 'client' / 'data' / 'GameOptions.lua'
    original = path.read_bytes()
    width, height = resolution.split('x')
    changed = original
    for key, value in [('RESOLUTION_X', width), ('RESOLUTION_Y', height), ('FULLSCREEN', fullscreen.upper())]:
        changed, count = re.subn(key.encode() + rb'\s*=\s*(?:\d+|TRUE|FALSE)',
                                key.encode() + b' = ' + value.encode(), changed, count=1, flags=re.I)
        if count != 1:
            raise RuntimeError(f'Missing display setting {key}; configuration was not changed')
    if changed != original:
        backup = path.with_suffix('.lua.theseus-backup')
        if not backup.exists():
            backup.write_bytes(original)
        temporary = path.with_suffix('.lua.tmp')
        temporary.write_bytes(changed)
        temporary.replace(path)
    return {'ok': True, 'message': 'Local display settings saved.'}


@contextlib.contextmanager
def operation_lock():
    import msvcrt
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with (STATE.parent / 'operation.lock').open('a+b') as stream:
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('Another Theseus launch or stop is in progress; wait for it to finish') from None
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'start', 'stop', 'status', 'client', 'play', 'display'))
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--resolution', choices=('1024x768', '1280x720', '1600x900', '1920x1080', '2560x1440'), default='1280x720')
    parser.add_argument('--fullscreen', choices=('true', 'false'), default='false')
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('The preserved native runtime requires Windows')
    captured = io.StringIO()
    result = None
    code = 0
    try:
        with contextlib.redirect_stdout(captured) if args.json else contextlib.nullcontext():
            with operation_lock() if args.command != 'status' else contextlib.nullcontext():
                if args.command == 'play':
                    if not clients():
                        start()
                        display(args.resolution, args.fullscreen)
                    result = client()
                elif args.command == 'display':
                    result = display(args.resolution, args.fullscreen)
                elif args.command == 'status':
                    result = status()
                elif args.command == 'preflight':
                    preflight()
                else:
                    result = globals()[args.command]()
    except Exception as error:
        code = 1
        result = {'ok': False, 'focused': False, 'message': str(error)}
    if args.json or result is not None:
        print(json.dumps(result or {'ok': True, 'focused': False, 'message': captured.getvalue().strip()}))
    sys.exit(code)
