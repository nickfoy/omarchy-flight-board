#!/usr/bin/env python3
"""Read-only JSON stream for the secure lock surface; shares the board's API cache."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import concurrent.futures
import contextlib
import json
import signal
import sys
import threading
import time
import server


def cached_feeds(config):
    if config['demo']:
        # Explicit demo mode only: never substitute samples for a failed live feed.
        now = time.time()
        routes = [('LONDON HEATHROW', 'SK805'), ('COPENHAGEN', 'SK1462'), ('AMSTERDAM', 'KL1198'), ('PARIS CDG', 'AF1275'), ('BERGEN', 'DY601')]
        flights = []
        zone = timezone.utc if config['timezone'] == 'utc' else ZoneInfo('Europe/Oslo') if config['timezone'] == 'airport' else None
        for i in range(20):
            stamp = now + (i + 1) * 180
            destination, flight = routes[i % len(routes)]
            flights.append({'id': 'lock-demo-' + str(i), 'airport': config['airports'][i % len(config['airports'])],
                            'direction': 'A' if i % 2 else 'D', 'flight': flight, 'destination': destination,
                            'gate': 'E' + str(i + 1), 'status': 'ON TIME',
                            'estimated': datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                            'boardTime': datetime.fromtimestamp(stamp, zone).strftime('%H:%M')})
        return [{'flights': flights, 'fetchedAt': now}]
    feeds = []
    for code in config['airports']:
        value = server.read_json(server.CACHE / (code + '.json'), {})
        flights = value.get('flights', [])
        for flight in flights:
            stamp = server.epoch(flight.get('estimated'))
            if stamp is not None:
                zone = timezone.utc if config['timezone'] == 'utc' else ZoneInfo(flight.get('timezone', 'Europe/Oslo')) if config['timezone'] == 'airport' else None
                flight['boardTime'] = datetime.fromtimestamp(stamp, zone).strftime('%H:%M')
        feeds.append({**value, 'airport': code, 'flights': flights})
    return feeds


def refresh(config):
    # Provider diagnostics must not corrupt the JSON stream.
    with contextlib.redirect_stdout(sys.stderr):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(lambda code: server.airport_feed(code, config['refreshMinutes'] * 60), config['airports']))


def main():
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    next_refresh = 0
    next_emit = 0
    pending = None
    # A single coordinator runs API work while cached data remains available.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as worker:
        while not stop.is_set():
            now = time.monotonic()
            config = server.settings()
            if pending is not None and pending.done():
                try:
                    pending.result()
                except Exception as error:
                    print(error, file=sys.stderr)
                pending = None
                next_refresh = now + config['refreshMinutes'] * 60
                next_emit = 0
            if now >= next_emit:
                packet = {'config': config, 'feeds': cached_feeds(config)}
                # Write directly: redirect_stdout in the fetch thread is process-wide.
                sys.__stdout__.write(json.dumps(packet) + '\n')
                sys.__stdout__.flush()
                next_emit = now + 15
            if pending is None and now >= next_refresh and not config['demo']:
                pending = worker.submit(refresh, config)
            stop.wait(1)


if __name__ == '__main__':
    main()
