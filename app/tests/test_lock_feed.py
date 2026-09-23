import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import server
import lock_feed

class LockFeedTests(unittest.TestCase):
    def test_uses_cached_flights_and_selected_timezone(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(server, 'CACHE', Path(directory)), patch.object(server, 'urlopen', side_effect=AssertionError('Unexpected network request')):
            server.atomic_json(server.CACHE / 'OSL.json', {'flights': [{'estimated': '2026-09-21T12:30:00Z', 'timezone': 'Europe/Oslo'}], 'fetchedAt': 100})
            config = {**server.DEFAULTS, 'airports': ['OSL'], 'timezone': 'utc'}
            self.assertEqual(lock_feed.cached_feeds(config)[0]['flights'][0]['boardTime'], '12:30')
            config['timezone'] = 'airport'
            self.assertEqual(lock_feed.cached_feeds(config)[0]['flights'][0]['boardTime'], '14:30')

    def test_missing_cache_is_not_demo_data(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(server, 'CACHE', Path(directory)):
            self.assertEqual(lock_feed.cached_feeds(server.DEFAULTS)[0]['flights'], [])

    def test_explicit_demo_uses_simulated_flights(self):
        config = {**server.DEFAULTS, 'demo': True}
        flights = lock_feed.cached_feeds(config)[0]['flights']
        self.assertEqual(len(flights), 20)
        self.assertTrue(all(f['id'].startswith('lock-demo-') for f in flights))

if __name__ == '__main__':
    unittest.main()
