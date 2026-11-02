"""Game identity, compressed evidence and chronological mixed-pool validation."""
import datetime as dt
import gzip
import json
import pathlib
import tempfile
import unittest
from unittest import mock
from scripts import historical_pilot as h
from scripts.expand_historical import calendar_games, saturdays
from scripts.historical_validation import v85_folds, later_v85_split


class ExpansionTests(unittest.TestCase):
    def test_calendar_selects_observed_v75_and_v85_ids_only(self):
        day = '2025-10-25'
        calendar = {'date': day, 'games': {'V75': [{'id': 'V75_2025-10-25_6_5'}],
                    'V85': [{'id': 'V85_2025-10-25_7_3'}], 'V64': [{'id': 'V64_2025-10-25_1_1'}]}}
        self.assertEqual(calendar_games(calendar, day), ['V75_2025-10-25_6_5', 'V85_2025-10-25_7_3'])
        calendar['date'] = '2025-10-24'
        with self.assertRaises(ValueError):
            calendar_games(calendar, day)
        self.assertEqual(calendar_games({'date': day, 'games': {}}, day), [])

    def test_each_game_requires_its_own_leg_count(self):
        for kind, count in [('V75', 7), ('V85', 8)]:
            gid = kind + '_2024-01-06_23_5'
            h.check_source_payload('/games/' + gid, {'id': gid, 'races': [{}] * count})
            with self.assertRaises(ValueError):
                h.check_source_payload('/games/' + gid, {'id': gid, 'races': [{}] * (15 - count)})

    def test_v75_fields_and_market_are_distinct_from_v85(self):
        rid, gid = '2024-01-06_23_5', 'V75_2024-01-06_23_5'
        race = {'id': rid, 'status': 'results', 'sport': 'trot', 'distance': 2140,
                'starts': [{'number': n, 'horse': {'id': 100+n, 'name': str(n)},
                            'result': {'place': n}, 'pools': {'V75': {'betDistribution': 1000}, 'V85': {'betDistribution': 5000}}} for n in range(1, 9)]}
        rows = h.parse_historical_race(race, {'id': gid, 'races': [race]}, '2024-01-06')
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r['gameType'] == 'V75' and r['marketFinalPct'] == 10 for r in rows))
        race['sport'] = 'gallop'
        self.assertIsNone(h.parse_historical_race(race, {'id': gid}, '2024-01-06'))

    def test_saturday_range_is_inclusive_and_not_every_day(self):
        self.assertEqual(list(saturdays(dt.date(2024, 1, 1), dt.date(2024, 1, 13))), ['2024-01-06', '2024-01-13'])

    def test_gzip_raw_sources_can_rebuild_offline_and_detect_corruption(self):
        path = '/races/2024-01-06_23_5/extended'
        payload = {'id': '2024-01-06_23_5', 'starts': [], 'marker': 'Bergsåker'}
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(h, 'CACHE', pathlib.Path(directory)), mock.patch.object(h, 'COMPRESS_CACHE', True), mock.patch.object(h, 'OFFLINE', False), mock.patch.object(h.time, 'sleep'):
            with mock.patch.object(h.urllib.request, 'urlopen', return_value=response):
                self.assertEqual(h.get_json(path), payload)
            saved = h.cache_path(path)
            self.assertEqual(saved.suffix, '.gz')
            with mock.patch.object(h, 'OFFLINE', True), mock.patch.object(h.urllib.request, 'urlopen', side_effect=AssertionError('No network')):
                self.assertEqual(h.get_json(path), payload)
                corrupted = json.loads(gzip.decompress(saved.read_bytes()))
                corrupted['payload']['marker'] = 'changed'
                saved.write_bytes(gzip.compress(json.dumps(corrupted).encode()))
                with self.assertRaisesRegex(ValueError, 'hash validation'):
                    h.get_json(path)

    def test_v75_is_training_only_and_same_day_cannot_train(self):
        rows = [{'date': '2025-10-04', 'gameId': 'V75_a', 'raceId': 'old'},
                {'date': '2025-10-25', 'gameId': 'V75_b', 'raceId': 'same-day-v75'},
                {'date': '2025-10-25', 'gameId': 'V85_c', 'raceId': 'test'},
                {'date': '2025-11-01', 'gameId': 'V85_d', 'raceId': 'future'}]
        day, train, test = next(v85_folds(rows, min_dates=1, min_starts=1))
        self.assertEqual(day, '2025-10-25')
        self.assertEqual([r['raceId'] for r in train], ['old'])
        self.assertEqual([r['raceId'] for r in test], ['test'])

    def test_later_period_has_no_overlap_or_v75_test_races(self):
        rows = [{'date': '2026-07-31', 'gameType': 'V75'}, {'date': '2026-08-01', 'gameType': 'V85'}, {'date': '2026-08-01', 'gameType': 'V75'}]
        train, test = later_v85_split(rows)
        self.assertEqual(train, rows[:1])
        self.assertEqual(test, rows[1:2])


if __name__ == '__main__':
    unittest.main()
