"""Regressions for label leakage, missing risk and recoverable source evidence."""
import copy
import datetime as dt
import hashlib
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

from scripts import data_quality as q
from scripts import historical_pilot as h
from scripts import update_bjerke_form as form


def card():
    return {'id': '2026-06-01_5_1', 'status': 'results', 'distance': 2140,
            'startMethod': 'auto', 'track': {'name': 'Test', 'countryCode': 'SE'},
            'starts': [{'number': i, 'postPosition': i, 'horse': {'name': f'Horse {i}'},
                        'result': {'place': i}} for i in range(1, 9)]}


def parsed(race=None):
    return h.parse_historical_race(race or card(), {'id': 'V85_2026-06-01_5_1', 'races': []}, '2026-06-01')


def legacy():
    rows = parsed()
    for row in rows:
        row.pop('dataContractVersion')
        row.pop('raceCounts')
        row.pop('featureCoverage')
        row.pop('resultStatus')
        row['prestartFeatures']['gallop5'] = 0
    return {'schemaVersion': 1, 'raceCount': 1, 'starterCount': 8, 'rows': rows}


class GallopTests(unittest.TestCase):
    def test_disqualification_does_not_establish_gallop(self):
        for record in [{}, {'disqualified': False}, {'disqualified': True}, {'galloped': 'false'}, {'galloped': 0}]:
            self.assertIsNone(q.gallop_status(record))
        self.assertIs(q.gallop_status({'galloped': False, 'disqualified': True}), False)
        self.assertIs(q.gallop_status({'galloped': True, 'place': 1}), True)

    def test_historical_risk_uses_only_observed_flags(self):
        records = [{'date': f'2026-05-{day:02}', 'race': {'id': f'old-{day}'}, **flags}
                   for day, flags in [(30, {'galloped': True}), (29, {'galloped': False}),
                                      (28, {'disqualified': False}), (27, {'disqualified': True})]]
        start = {'horse': {'results': {'records': records}}}
        self.assertEqual(h.features_from_history(start, card(), dt.date(2026, 6, 1), 8)['gallop5'], .5)
        records[0].pop('galloped')
        self.assertIsNone(h.features_from_history(start, card(), dt.date(2026, 6, 1), 8)['gallop5'])

    def test_bjerke_form_uses_same_three_state_semantics(self):
        self.assertIsNone(form.parse_record({'date': '2026-10-20', 'place': 2, 'disqualified': False})['galloped'])
        self.assertIsNone(form.parse_record({'date': '2026-10-20', 'disqualified': True})['galloped'])
        self.assertGreater(form.performance(1, True), form.performance(0, False))
        self.assertLess(form.performance(0, False), form.performance(8, False) + .01)

    def test_disqualification_cannot_be_used_as_a_confirmed_past_win(self):
        record = {'date': '2026-05-30', 'place': 1, 'disqualified': True}
        history = h.past_records({'horse': {'results': {'records': [record]}}}, dt.date(2026, 6, 1))
        self.assertIsNone(history[0]['place'])
        self.assertIsNone(history[0]['gallop'])
        self.assertIsNone(form.parse_record(record)['place'])


class CompleteFieldTests(unittest.TestCase):
    def test_wrong_race_or_game_date_is_rejected(self):
        race = card(); race['id'] = '2026-06-02_5_1'
        self.assertIsNone(parsed(race))
        self.assertIsNone(h.parse_historical_race(card(), {'id': 'V85_2026-06-02_5_1'}, '2026-06-01'))

    def test_unknown_result_never_changes_prestart_field(self):
        race = card(); before = parsed(race)
        race['starts'][-1]['result'] = {}
        after = parsed(race)
        self.assertEqual(len(after), 8)
        self.assertEqual([r['prestartFeatures'] for r in before], [r['prestartFeatures'] for r in after])
        self.assertIsNone(after[-1]['winner'])
        self.assertEqual(after[-1]['raceCounts']['unknownResults'], 1)
        self.assertEqual(q.prepare_training_data({'rows': after})['rows'], [])

    def test_scratches_do_not_reduce_result_coverage(self):
        race = card(); race['starts'].append({'number': 9, 'horse': {'name': 'Scratched'}, 'scratched': True})
        rows = parsed(race)
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]['raceCounts'], {'registered': 9, 'active': 8, 'scratched': 1, 'knownResults': 8, 'unknownResults': 0})
        self.assertEqual(rows[0]['resultCoverage'], 1)
        self.assertEqual(q.prepare_training_data({'rows': rows})['raceCount'], 1)

    def test_explicit_unplaced_and_disqualified_are_known_nonwinners(self):
        race = card(); race['starts'][6]['result'] = {'place': 0}
        race['starts'][7]['result'] = {'disqualified': True}
        rows = parsed(race)
        self.assertEqual([r['winner'] for r in rows[-2:]], [0, 0])
        self.assertEqual([r['resultStatus'] for r in rows[-2:]], ['unplaced', 'disqualified'])
        self.assertEqual(q.prepare_training_data({'rows': rows})['raceCount'], 1)

    def test_all_unknowns_remain_unknown(self):
        race = card()
        for start in race['starts']: start['result'] = {}
        rows = parsed(race)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r['winner'] is None for r in rows))
        self.assertEqual(q.prepare_training_data({'rows': rows})['starterCount'], 0)

    def test_conflicting_results_and_dead_heat_cannot_train(self):
        race = card(); race['starts'][0]['result']['disqualified'] = True
        self.assertEqual(q.prepare_training_data({'rows': parsed(race)})['raceCount'], 0)
        race = card(); race['starts'][1]['result']['place'] = 1
        self.assertIsNone(parsed(race))

    def test_unknown_or_duplicate_identity_rejects_entire_field(self):
        race = card(); race['starts'][1]['number'] = 1
        self.assertIsNone(parsed(race))
        race = card(); race['starts'][1]['horse']['name'] = ''
        self.assertIsNone(parsed(race))

    def test_fractional_and_boolean_placings_are_unknown(self):
        for value in [True, 1.5, '1.5', 'unknown', None, -1, float('nan')]:
            self.assertIsNone(q.result_label({'place': value})[0])


class TrainingGateTests(unittest.TestCase):
    def test_legacy_complete_field_retained_with_unverified_risk_disabled(self):
        source = legacy(); original = copy.deepcopy(source)
        clean = q.prepare_training_data(source)
        self.assertEqual(clean['raceCount'], 1)
        self.assertTrue(all(r['prestartFeatures']['gallop5'] is None for r in clean['rows']))
        self.assertEqual(clean['dataQuality']['maskedLegacyGallopValues'], 8)
        self.assertEqual(source, original)

    def test_legacy_ambiguous_coverage_quarantines_whole_race(self):
        source = legacy()
        for row in source['rows']: row['resultCoverage'] = .8
        clean = q.prepare_training_data(source)
        self.assertEqual(clean['starterCount'], 0)
        self.assertEqual(clean['dataQuality']['quarantine'][0]['reason'], 'legacy_field_requires_raw_refetch')

    def test_claimed_coverage_does_not_bypass_identity_and_size(self):
        source = legacy(); source['rows'][1]['number'] = 1
        self.assertFalse(q.prepare_training_data(source)['rows'])
        source = legacy(); source['rows'][0]['prestartFeatures']['field'] = 9
        self.assertFalse(q.prepare_training_data(source)['rows'])

    def test_v2_cannot_invent_zero_gallop_without_observations(self):
        rows = parsed(); rows[0]['prestartFeatures']['gallop5'] = 0
        self.assertFalse(q.prepare_training_data({'rows': rows})['rows'])
        rows[0]['featureCoverage'] = {'gallopObservedStarts': 2, 'historyStarts': 5}
        self.assertEqual(q.prepare_training_data({'rows': rows})['raceCount'], 1)

    def test_revalidation_preserves_quarantine_and_provenance(self):
        source = legacy(); second = copy.deepcopy(source['rows'])
        for row in second:
            row['raceId'] = 'other'; row['resultCoverage'] = .8
        source['rows'] += second
        once = q.prepare_training_data(source)
        twice = q.prepare_training_data(once)
        self.assertEqual(once, twice)
        self.assertEqual(twice['rawSourceRaceCount'], 2)

    def test_raw_and_legacy_contracts_cannot_be_mixed(self):
        with self.assertRaisesRegex(ValueError, 'Legacy'):
            h.collect([], legacy()['rows'])

    def test_source_hash_and_unavailable_report_replace_stale_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)/'source.json'; path.write_text(json.dumps(legacy()))
            doc = q.load_training_data(path)
            self.assertEqual(doc['dataQuality']['sourceSha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            out = pathlib.Path(directory)/'result.json'; out.write_text('{"testMetrics":{"races":151}}')
            q.publish_unavailable(out, q.InsufficientHistory('Too few dates'), path)
            report = json.loads(out.read_text())
            self.assertEqual(report['status'], 'insufficient_data')
            self.assertNotIn('testMetrics', report)


class SourceCacheTests(unittest.TestCase):
    def test_api_error_objects_and_wrong_identity_are_not_cached(self):
        for payload in [{'error': 'temporary'}, {**card(), 'id': 'wrong-race'}]:
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
            with tempfile.TemporaryDirectory() as directory, mock.patch.object(h, 'CACHE', pathlib.Path(directory)), mock.patch.object(h, 'OFFLINE', False):
                with mock.patch.object(h.urllib.request, 'urlopen', return_value=response):
                    with self.assertRaises(ValueError): h.get_json('/races/2026-06-01_5_1/extended')
                self.assertEqual(list(pathlib.Path(directory).iterdir()), [])

    def test_cache_preserves_raw_flags_and_allows_verified_offline_rebuild(self):
        response = mock.MagicMock()
        payload = card(); payload['starts'][0]['horse']['results'] = {'records': [{'galloped': True, 'disqualified': False}]}
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(h, 'CACHE', pathlib.Path(directory)), mock.patch.object(h, 'OFFLINE', False):
            with mock.patch.object(h.urllib.request, 'urlopen', return_value=response) as fetch:
                first = h.get_json('/races/2026-06-01_5_1/extended')
                self.assertEqual(fetch.call_count, 1)
            with mock.patch.object(h, 'OFFLINE', True), mock.patch.object(h.urllib.request, 'urlopen', side_effect=AssertionError('No network')):
                self.assertEqual(h.get_json('/races/2026-06-01_5_1/extended'), first)
            saved_path = next(pathlib.Path(directory).glob('*.json'))
            saved = json.loads(saved_path.read_text()); saved['payload']['id'] = 'tampered'
            saved_path.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, 'hash validation'):
                h.get_json('/races/2026-06-01_5_1/extended')

    def test_missing_offline_source_never_attempts_network(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(h, 'CACHE', pathlib.Path(directory)), mock.patch.object(h, 'OFFLINE', True):
            with mock.patch.object(h.urllib.request, 'urlopen', side_effect=AssertionError('No network')):
                with self.assertRaises(urllib.error.URLError): h.get_json('/races/2026-06-01_5_1/extended')


if __name__ == '__main__':
    unittest.main()
