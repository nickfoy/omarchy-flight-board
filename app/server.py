#!/usr/bin/env python3
"""Local split-flap board. Standard library only; Avinor is the live provider."""
from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
from subprocess import SubprocessError
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import integration

ROOT = Path(__file__).resolve().parent
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'split-flap-board'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'split-flap-board'
REFRESH = 180
# Airport operators outside Avinor (e.g. TRF) are deliberately excluded.
LIVE_CODES = set('ALF ANX BDU BGO BJF BNN BOO BVG EVE FDE FRO HAA HFT HOV HVG KKN KRS KSU LKL LKN LYR MEH MJF MOL MQN OSL OSY OZH RET RRS RVK SDN SKE SKN SOJ SRP SSJ SVG SVJ SOG TOS TRD VAW VDB VDS'.split()) - {'OZH', 'SKE', 'VDB', 'SRP'}
AIRPORTS = json.loads((ROOT / 'data/airports.json').read_text())
NAMES = {a['code']: a['name'] for a in AIRPORTS}
DEFAULTS = {'airports': ['OSL', 'BGO', 'TOS'], 'rows': 10, 'background': '#10120f',
            'grid': '#282b25', 'letters': '#efc477', 'mode': 'both', 'demo': False,
            'timezone': 'airport', 'refreshMinutes': 3, 'constantTurning': False,
            'screensaverMinutes': 5, 'lockMinutes': 7, 'screenOffMinutes': 20}


def epoch(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, AttributeError):
        return None


def normalize(raw: bytes, code: str):
    root = ET.fromstring(raw)
    container = root.find('flights')
    if container is None:
        raise ValueError('Flight feed did not contain a flights element')
    flights = []
    for node in container.findall('flight'):
        scheduled = node.findtext('schedule_time')
        direction = node.findtext('arr_dep')
        if epoch(scheduled) is None or direction not in ('A', 'D'):
            continue
        status = node.find('status')
        status_code = status.get('code', '') if status is not None else ''
        status_time = status.get('time') if status is not None else None
        effective = status_time if epoch(status_time) is not None and status_code in ('A', 'D', 'E') else scheduled
        delayed = node.findtext('delayed') == 'Y' or (status_code == 'E' and epoch(effective) > epoch(scheduled) + 60)
        label = {'A': 'ARRIVED', 'D': 'DEPARTED', 'C': 'CANCELLED', 'N': 'NEW INFO'}.get(status_code, 'DELAYED' if delayed else 'ON TIME')
        other = node.findtext('airport', '')
        flight = node.findtext('flight_id') or node.findtext('flightId', '')
        flights.append({'id': code + ':' + (node.get('uniqueID') or node.get('uniqueId') or flight + ':' + scheduled + ':' + direction),
                        'airport': code, 'direction': direction, 'flight': flight,
                        'destination': NAMES.get(other, other), 'otherAirport': other,
                        'scheduled': scheduled, 'estimated': effective,
                        'statusTime': status_time, 'status': label,
                        'complete': status_code in ('A', 'D'), 'gate': node.findtext('gate', ''),
                        'timezone': 'Europe/Oslo'})
    return {'flights': flights, 'sourceUpdatedAt': container.get('lastUpdate')}


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + secrets.token_hex(5) + '.tmp')
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False))
        temp.chmod(0o600)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path, fallback):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return fallback


def validate_settings(data):
    if not isinstance(data, dict):
        raise ValueError('Settings must be an object')
    result = dict(DEFAULTS)
    codes = data.get('airports', result['airports'])
    if not isinstance(codes, list) or not 1 <= len(codes) <= 12 or any(c not in LIVE_CODES for c in codes):
        raise ValueError('Select between 1 and 12 airports with free live coverage')
    result['airports'] = list(dict.fromkeys(codes))
    rows = data.get('rows', result['rows'])
    if type(rows) is not int or not 4 <= rows <= 18:
        raise ValueError('Rows must be between 4 and 18')
    result['rows'] = rows
    result['refreshMinutes'] = validate_refresh_minutes(data.get('refreshMinutes', result['refreshMinutes']))
    for key in ('background', 'grid', 'letters'):
        value = data.get(key, result[key])
        if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            raise ValueError('Choose a valid color')
        result[key] = value
    for key, options in [('mode', ('both', 'arrivals', 'departures')), ('timezone', ('airport', 'local', 'utc'))]:
        value = data.get(key, result[key])
        if value not in options:
            raise ValueError('Invalid ' + key)
        result[key] = value
    if type(data.get('demo', False)) is not bool:
        raise ValueError('Demo must be a boolean')
    result['demo'] = data.get('demo', False)
    if type(data.get('constantTurning', False)) is not bool:
        raise ValueError('Constant turning must be a boolean')
    result['constantTurning'] = data.get('constantTurning', False)
    for key in ('screensaverMinutes', 'lockMinutes', 'screenOffMinutes'):
        value = data.get(key, DEFAULTS[key])
        if type(value) is not int or not 1 <= value <= 240:
            raise ValueError('Use whole minutes from 1 to 240 for screensaver timing')
        result[key] = value
    if not result['screensaverMinutes'] < result['lockMinutes'] < result['screenOffMinutes']:
        raise ValueError('Choose screensaver first, then lock, then screen off')
    return result


def settings():
    try:
        return validate_settings(read_json(CONFIG / 'settings.json', DEFAULTS))
    except ValueError:
        return dict(DEFAULTS)


def validate_refresh_minutes(value):
    if type(value) is not int or not 1 <= value <= 10:
        raise ValueError('Refresh interval must be between 1 and 10 minutes')
    return value


def airport_feed(code, refresh_seconds=REFRESH):
    """Lock and cache across windows/processes; never poll an airport faster than 3 min."""
    refresh_seconds = max(REFRESH, refresh_seconds)
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (code + '.json')
    with (CACHE / (code + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cached = read_json(path, {})
        now = time.time()
        if now - cached.get('attemptedAt', 0) >= refresh_seconds:
            try:
                req = Request(f'https://asrv.avinor.no/XmlFeed/v1.0?airport={code}&TimeFrom=1&TimeTo=12',
                              headers={'User-Agent': 'SplitFlapBoard/1.0 (personal desktop display)', 'Accept': 'application/xml'})
                with urlopen(req, timeout=18) as response:
                    raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise ValueError('Flight feed was unexpectedly large')
                cached = {**normalize(raw, code), 'fetchedAt': time.time(), 'attemptedAt': now, 'error': None}
            except Exception as exc:
                cached = {**cached, 'attemptedAt': now, 'error': 'Live feed unavailable; retrying at the selected refresh interval.'}
                print(f'{code}: {type(exc).__name__}: {exc}', flush=True)
            atomic_json(path, cached)
        return {'airport': code, 'flights': cached.get('flights', []),
                'fetchedAt': cached.get('fetchedAt'), 'sourceUpdatedAt': cached.get('sourceUpdatedAt'),
                'stale': bool(cached.get('error')) or now - cached.get('fetchedAt', 0) > refresh_seconds * 2,
                'error': cached.get('error'), 'nextRefreshAt': cached.get('attemptedAt', now) + refresh_seconds}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def authorized_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def send(self, data, status=200, content_type='application/json; charset=utf-8', cookie=False):
        payload = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        if cookie:
            self.send_header('Set-Cookie', f'board_session_{self.server.server_port}={self.server.token}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.authorized_host():
            return self.send({'error': 'Invalid host'}, 403)
        parsed = urlparse(self.path)
        if parsed.path == '/api/settings':
            return self.send(settings())
        if parsed.path == '/api/integration':
            try:
                return self.send(integration.status())
            except (ValueError, OSError, AttributeError):
                return self.send({'error': 'Could not read screensaver setup status'}, 409)
        if parsed.path == '/api/airports':
            return self.send([{**a, 'live': a['code'] in LIVE_CODES} for a in AIRPORTS])
        if parsed.path == '/api/flights':
            query = parse_qs(parsed.query)
            codes = list(dict.fromkeys(query.get('airports', ['OSL'])[0].split(',')))
            try:
                refresh_seconds = validate_refresh_minutes(int(query.get('refreshMinutes', ['3'])[0])) * 60
            except ValueError as exc:
                return self.send({'error': str(exc)}, 400)
            if not 1 <= len(codes) <= 12 or any(c not in LIVE_CODES for c in codes):
                return self.send({'error': 'Airport is not supported by the free feed'}, 400)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                feeds = list(pool.map(lambda code: airport_feed(code, refresh_seconds), codes))
            return self.send({'feeds': feeds, 'refreshSeconds': refresh_seconds,
                              'providerRefreshSeconds': max(REFRESH, refresh_seconds), 'serverTime': time.time()})
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'), '/timing.js': ('timing.js', 'text/javascript; charset=utf-8'), '/icon.svg': ('icon.svg', 'image/svg+xml'),
                 '/board-font.ttf': ('board-font.ttf', 'font/ttf')}
        if parsed.path not in files:
            return self.send({'error': 'Not found'}, 404)
        filename, content_type = files[parsed.path]
        return self.send((ROOT / 'static' / filename).read_bytes(), content_type=content_type, cookie=parsed.path == '/')

    def do_POST(self):
        if not self.authorized_host():
            return self.send({'error': 'Invalid host'}, 403)
        origin = self.headers.get('Origin')
        if origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            return self.send({'error': 'Invalid origin'}, 403)
        cookie = self.headers.get('Cookie', '').split('; ')
        if f'board_session_{self.server.server_port}={self.server.token}' not in cookie:
            return self.send({'error': 'Invalid session'}, 403)
        if self.path not in ('/api/settings', '/api/integration'):
            return self.send({'error': 'Not found'}, 404)
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 8192:
                raise ValueError('Invalid settings size')
            payload = json.loads(self.rfile.read(size))
            if self.path == '/api/integration':
                if not isinstance(payload, dict) or payload.get('action') not in ('enable', 'restore'):
                    raise ValueError('Choose enable or restore')
                integration.change(payload['action'])
                return self.send(integration.status())
            data = validate_settings(payload)
            integration.save_preferences(data)
            self.send(data)
        except (ValueError, TypeError) as exc:
            self.send({'error': str(exc)}, 400)
        except (OSError, RuntimeError, SubprocessError) as exc:
            self.send({'error': 'Could not save settings: ' + str(exc)}, 409)


def make_server(port=0):
    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    httpd.token = secrets.token_urlsafe(32)
    httpd.daemon_threads = True
    return httpd


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=47831)
    args = parser.parse_args()
    httpd = make_server(args.port)
    print(f'Split-Flap Board: http://127.0.0.1:{httpd.server_port}', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
