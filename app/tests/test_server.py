import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import server

FEED = b'''<airport name="OSL"><flights lastUpdate="2026-09-21T04:00:00Z">
<flight uniqueID="123"><flight_id>SK123</flight_id><arr_dep>D</arr_dep><airport>LHR</airport><schedule_time>2026-09-21T05:00:00Z</schedule_time><status code="E" time="2026-09-21T05:30:00Z"/><gate>E2</gate></flight>
<flight uniqueID="124"><flight_id>SK124</flight_id><arr_dep>A</arr_dep><airport>BGO</airport><schedule_time>2026-09-21T04:00:00Z</schedule_time><status code="A" time="2026-09-21T04:05:00Z"/></flight>
<flight uniqueID="125"><flight_id>SK125</flight_id><arr_dep>D</arr_dep><airport>BGO</airport><schedule_time>2026-09-21T05:00:00Z</schedule_time><status code="E" time="2026-09-21T05:00:00Z"/></flight>
<flight uniqueID="126"><flight_id>SK126</flight_id><arr_dep>D</arr_dep><airport>BGO</airport><schedule_time>2026-09-21T05:00:00Z</schedule_time><status code="C"/></flight>
<flight><schedule_time>bad</schedule_time><arr_dep>D</arr_dep></flight>
</flights></airport>'''

class FeedTests(unittest.TestCase):
    def test_real_schema_and_statuses(self):
        flights = server.normalize(FEED, 'OSL')['flights']
        self.assertEqual(len(flights), 4)
        self.assertEqual(flights[0]['id'], 'OSL:123')
        self.assertEqual(flights[0]['status'], 'DELAYED')
        self.assertEqual(flights[0]['estimated'], '2026-09-21T05:30:00Z')
        self.assertEqual(flights[0]['gate'], 'E2')
        self.assertTrue(flights[1]['complete'])
        self.assertEqual(flights[1]['status'], 'ARRIVED')
        self.assertEqual(flights[2]['status'], 'ON TIME')
        self.assertEqual(flights[3]['status'], 'CANCELLED')

    def test_failed_feed_is_not_an_empty_success(self):
        with self.assertRaises(ValueError):
            server.normalize(b'<error>Unavailable</error>', 'OSL')

    def test_cache_interval_and_stale_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(server, 'CACHE', Path(directory)), patch.object(server.time, 'time', return_value=1000) as clock:
            with patch.object(server, 'urlopen', return_value=io.BytesIO(FEED)) as fetch:
                self.assertFalse(server.airport_feed('OSL')['stale'])
                server.airport_feed('OSL')
                self.assertEqual(fetch.call_count, 1)
            clock.return_value = 1181
            with patch.object(server, 'urlopen', side_effect=OSError('offline')) as fetch:
                stale = server.airport_feed('OSL')
                self.assertTrue(stale['stale'])
                self.assertEqual(len(stale['flights']), 4)
                self.assertEqual(stale['fetchedAt'], 1000)
                server.airport_feed('OSL')
                self.assertEqual(fetch.call_count, 1)

    def test_settings_validation(self):
        self.assertEqual(server.validate_settings({})['rows'], 10)
        self.assertEqual(server.validate_settings({})['refreshMinutes'], 3)
        for bad in ({'rows':100}, {'rows':True}, {'airports':[]}, {'airports':['JFK']}, {'airports':['../../tmp']}, {'letters':'red'}, {'mode':'bad'}, {'demo':'yes'}, {'refreshMinutes':0}, {'refreshMinutes':11}, {'refreshMinutes':True}, {'refreshMinutes':1.5}, {'refreshMinutes':'5'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                server.validate_settings(bad)

    def test_atomic_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(server, 'CONFIG', Path(directory)):
            custom = server.validate_settings({**server.DEFAULTS, 'rows':18, 'letters':'#ffffff', 'refreshMinutes':10})
            server.atomic_json(server.CONFIG / 'settings.json', custom)
            self.assertEqual(server.settings(), custom)

    def test_configured_refresh_and_provider_minimum(self):
        for selected, effective in [(60, 180), (120, 180), (180, 180), (600, 600)]:
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as directory, patch.object(server, 'CACHE', Path(directory)), patch.object(server.time, 'time', return_value=1000) as clock, patch.object(server, 'urlopen', side_effect=lambda *a, **kw: io.BytesIO(FEED)) as fetch:
                server.airport_feed('OSL', selected)
                clock.return_value = 1000 + effective - 1
                cached = server.airport_feed('OSL', selected)
                self.assertEqual(fetch.call_count, 1)
                self.assertFalse(cached['stale'])
                self.assertEqual(cached['nextRefreshAt'], 1000 + effective)
                clock.return_value += 1
                server.airport_feed('OSL', selected)
                self.assertEqual(fetch.call_count, 2)

if __name__ == '__main__':
    unittest.main()

class TimingTests(unittest.TestCase):
    def test_defaults_and_round_trip(self):
        defaults = server.validate_settings({})
        self.assertEqual([defaults[k] for k in ('screensaverMinutes', 'lockMinutes', 'screenOffMinutes')], [5, 7, 20])
        with tempfile.TemporaryDirectory() as directory, patch.object(server, 'CONFIG', Path(directory)):
            settings = server.validate_settings({'screensaverMinutes': 2, 'lockMinutes': 4, 'screenOffMinutes': 30})
            server.atomic_json(server.CONFIG / 'settings.json', settings)
            self.assertEqual(server.settings(), settings)

    def test_rejects_invalid_or_out_of_order_times(self):
        for values in ((0,7,20),(5,5,20),(8,7,20),(5,20,20),(5,21,20),(5,7,241),(True,7,20),(5.5,7,20),('5',7,20)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                server.validate_settings(dict(zip(('screensaverMinutes','lockMinutes','screenOffMinutes'),values)))
