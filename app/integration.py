"""Explicit Flight Board setup and restoration; no privileged writes or migration."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time

PLUGIN = 'nickfoy.flight-board'
ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
STATE = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'flight-board'
SHELL = CONFIG / 'omarchy/shell.json'
SETTINGS = CONFIG / 'split-flap-board/settings.json'
RECORD = STATE / 'integration.json'


def read(path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return deepcopy(default)


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with temp.open('xb') as stream:
            os.chmod(temp, 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def snapshot(path):
    if path.is_symlink():
        raise ValueError(f'Refusing to replace a symlink: {path}')
    return path.read_bytes() if path.exists() else None


@contextmanager
def serialized():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'setup.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


class Transaction:
    """Optimistic file transaction; never clobber edits made during verification."""
    def __init__(self, values, expected=None):
        self.values = {path: encode(value) for path, value in values.items()}
        self.before = {path: (expected[path] if expected is not None else snapshot(path)) for path in values}
        self.written = []
        self.backup = STATE / 'backups' / (time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(4))

    def apply(self):
        self.backup.mkdir(parents=True, mode=0o700)
        for index, (path, data) in enumerate(self.before.items()):
            if data is not None:
                atomic(self.backup / f'{index}-{path.name}', data)
        atomic(self.backup / 'files.json', encode([{'path': str(p), 'existed': b is not None} for p, b in self.before.items()]))
        for path, data in self.values.items():
            if snapshot(path) != self.before[path]:
                raise RuntimeError(f'Configuration changed during setup: {path}; retry after other settings finish saving')
            atomic(path, data)
            self.written.append(path)

    def rollback(self):
        conflicts = []
        for path in reversed(self.written):
            if snapshot(path) != self.values[path]:
                conflicts.append(str(path))
                continue
            before = self.before[path]
            if before is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, before)
        if conflicts:
            raise RuntimeError('Kept newer user edits during rollback: ' + ', '.join(conflicts) + f'. Original files: {self.backup}')


def slot(obj, key):
    return {'present': key in obj, 'value': obj.get(key)}


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError('shell.json must contain an object')
    for key in ('plugins', 'disabledPlugins', 'cloneSourceRestores'):
        if key in config and not isinstance(config[key], list):
            raise ValueError(f'shell.json {key} must be an array')
    if 'idle' in config and not isinstance(config['idle'], dict):
        raise ValueError('shell.json idle must be an object')


def plan_enable(config, preferences, record=None):
    validate_config(config)
    config = deepcopy(config)
    record = deepcopy(record or {})
    if record and (record.get('plugin') != PLUGIN or record.get('schemaVersion') != 1):
        raise ValueError('Unknown integration record; refusing to overwrite it')
    if 'omarchy.idle' in config.get('disabledPlugins', []):
        raise ValueError('Enable the stock Omarchy idle service before setup; custom idle migration is not automatic')
    idle = config.setdefault('idle', {})
    if record.get('active'):
        for key, value in record['appliedIdle'].items():
            if idle.get(key) != value:
                raise ValueError('Idle settings changed outside Flight Board. Restore integration before setting it up again.')
    else:
        record = {'schemaVersion': 1, 'plugin': PLUGIN, 'active': True,
                  'pluginEntry': record.get('pluginEntry', {'id': PLUGIN}),
                  'originalIdle': {key: slot(idle, key) for key in ('screensaver', 'lock')}}
    # Stock idle remains a lock fallback, but never starts the terminal saver
    # ahead of its lock deadline. Our independent cycle owns the flight board.
    seconds = preferences['lockMinutes'] * 60
    applied = {'screensaver': seconds + 1, 'lock': seconds}
    idle.update(applied)
    entries = config.setdefault('plugins', [])
    if not any(isinstance(e, dict) and e.get('id') == PLUGIN for e in entries):
        entries.append({**record.get('pluginEntry', {}), 'id': PLUGIN})
    record['pluginEntry'] = next(deepcopy(e) for e in entries if isinstance(e, dict) and e.get('id') == PLUGIN)
    disabled = [p for p in config.get('disabledPlugins', []) if p != PLUGIN]
    if 'omarchy.lock' not in disabled:
        disabled.append('omarchy.lock')
    config['disabledPlugins'] = disabled
    restores = config.setdefault('cloneSourceRestores', [])
    if PLUGIN not in restores:
        restores.append(PLUGIN)
    record.update(active=True, appliedIdle=applied)
    return config, record


def plan_restore(config, record):
    validate_config(config)
    if not record or record.get('plugin') != PLUGIN or record.get('schemaVersion') != 1:
        raise ValueError('No recognized Flight Board integration record')
    config, record = deepcopy(config), deepcopy(record)
    if record.get('active') is not True:
        return config, record
    for entry in config.get('plugins', []):
        if isinstance(entry, dict) and entry.get('id') == PLUGIN:
            record['pluginEntry'] = deepcopy(entry)
    idle = config.get('idle', {})
    # Compare-and-restore each owned key. Keep unrelated or later user edits.
    for key, value in record.get('appliedIdle', {}).items():
        if key not in ('screensaver', 'lock') or idle.get(key) != value:
            continue
        before = record['originalIdle'][key]
        if before['present']:
            idle[key] = before['value']
        else:
            idle.pop(key, None)
    if not idle:
        config.pop('idle', None)
    config['plugins'] = [e for e in config.get('plugins', []) if not isinstance(e, dict) or e.get('id') != PLUGIN]
    if PLUGIN in config.get('cloneSourceRestores', []):
        config['disabledPlugins'] = [p for p in config.get('disabledPlugins', []) if p != 'omarchy.lock']
    config['cloneSourceRestores'] = [p for p in config.get('cloneSourceRestores', []) if p != PLUGIN]
    record['active'] = False
    return config, record


def ipc(target):
    result = subprocess.run(['omarchy-shell', target, 'status'], capture_output=True, text=True, check=True, timeout=10)
    return json.loads(result.stdout)


def providers_match(expected_lock):
    result = subprocess.run(['omarchy-shell', 'shell', 'listPlugins'], capture_output=True, text=True, check=True, timeout=10)
    enabled = {p['id']: p for p in json.loads(result.stdout) if p.get('enabled')}
    if 'omarchy.idle' not in enabled or expected_lock not in enabled:
        return False
    for plugin_id, entry in enabled.items():
        if entry.get('clonedFrom') in ('omarchy.idle', 'omarchy.lock') and plugin_id != expected_lock:
            return False
    return expected_lock == 'omarchy.lock' or 'omarchy.lock' not in enabled


def preflight(action):
    expected = CONFIG / 'omarchy/plugins' / PLUGIN
    if ROOT != expected or ROOT.is_symlink():
        raise ValueError(f'Install the repository at {expected} before applying setup; plan is available from a checkout')
    for command in ('omarchy', 'omarchy-shell', 'python', 'hyprctl', 'jq', 'flock'):
        if shutil.which(command) is None:
            raise ValueError(f'Missing dependency: {command}')
    lock, idle = ipc('lock'), ipc('idle')
    if lock.get('locked') or lock.get('requested') or lock.get('secure'):
        raise ValueError('Unlock the session before changing Flight Board integration')
    provider = lock.get('plugin', 'omarchy.lock')
    if provider not in ('omarchy.lock', PLUGIN) or not providers_match(provider):
        raise ValueError('Another lock plugin is active. Restore the stock locker before setup or restoration.')
    if idle.get('plugin', 'omarchy.idle') != 'omarchy.idle':
        raise ValueError('Another idle plugin is active. Restore the stock idle service before setup.')
    if not lock.get('passwordPam'):
        raise ValueError('Working password PAM is required')
    if action == 'enable':
        subprocess.run(['python', '-c', "import gi; gi.require_version('Gtk','3.0'); gi.require_version('WebKit2','4.1'); from gi.repository import Gtk, WebKit2"], check=True, timeout=10)


def restart_and_verify(action):
    subprocess.run(['omarchy', 'restart', 'shell'], check=True, timeout=45)
    expected = PLUGIN if action == 'enable' else 'omarchy.lock'
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            lock, idle = ipc('lock'), ipc('idle')
            if lock.get('plugin', 'omarchy.lock') == expected and lock.get('passwordPam') and idle.get('plugin', 'omarchy.idle') == 'omarchy.idle' and providers_match(expected):
                if action != 'enable' or ipc('flight-board-idle').get('enabled') or ipc('flight-board-idle').get('stayAwake'):
                    return
        except (subprocess.SubprocessError, ValueError):
            pass
        time.sleep(0.2)
    raise RuntimeError(f'Could not verify {expected} and the stock idle service after restart')


def change(action):
    from server import settings
    with serialized():
        preflight(action)
        expected = {p: snapshot(p) for p in (SHELL, RECORD, SETTINGS)}
        config = json.loads(expected[SHELL]) if expected[SHELL] is not None else {}
        record = json.loads(expected[RECORD]) if expected[RECORD] is not None else None
        preferences = settings()
        if action == 'enable':
            config, record = plan_enable(config, preferences, record)
        else:
            config, record = plan_restore(config, record)
        values = {SHELL: config, RECORD: record}
        if action == 'enable':
            values = {SETTINGS: preferences, **values}
        transaction = Transaction(values, expected)
        try:
            transaction.apply()
            restart_and_verify(action)
        except Exception:
            transaction.rollback()
            subprocess.run(['omarchy', 'restart', 'shell'], timeout=45, check=False)
            raise
        return {'action': action, 'plugin': PLUGIN, 'backup': str(transaction.backup)}


def save_preferences(preferences):
    """Keep fallback lock timing synchronized when integrated; standalone is local."""
    with serialized():
        expected = {p: snapshot(p) for p in (SHELL, RECORD, SETTINGS)}
        record = json.loads(expected[RECORD]) if expected[RECORD] is not None else None
        values = {SETTINGS: preferences}
        if record and record.get('active') and record.get('plugin') == PLUGIN:
            # Saving settings must never re-enable a plugin the user disabled.
            current = json.loads(expected[SHELL]) if expected[SHELL] is not None else {}
            active = any(isinstance(e, dict) and e.get('id') == PLUGIN for e in current.get('plugins', [])) and PLUGIN not in current.get('disabledPlugins', [])
            if active:
                config, record = plan_enable(current, preferences, record)
                values = {SETTINGS: preferences, SHELL: config, RECORD: record}
        transaction = Transaction(values, expected)
        try:
            transaction.apply()
        except Exception:
            transaction.rollback()
            raise


def status():
    record, config = read(RECORD, {}), read(SHELL, {})
    configured = record.get('active') is True and record.get('plugin') == PLUGIN
    enabled = any(isinstance(e, dict) and e.get('id') == PLUGIN for e in config.get('plugins', [])) and PLUGIN not in config.get('disabledPlugins', [])
    minutes = read(SETTINGS, {}).get('lockMinutes', 7)
    synchronized = isinstance(minutes, int) and record.get('appliedIdle', {}).get('lock') == minutes * 60
    return {'configured': configured, 'active': configured and enabled and synchronized}
