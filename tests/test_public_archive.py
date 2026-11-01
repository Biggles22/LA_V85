"""Complete-field and provenance checks for the separate public result ledger."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts import audit_public_archive as a


def race():
    return {
        'id': '2026-06-01_5_1', 'date': '2026-06-01', 'status': 'results',
        'sport': 'trot', 'track': {'countryCode': 'SE'},
        'starts': [{'number': n, 'horse': {'id': n, 'name': f'Horse {n}'},
                    'result': {'place': n}} for n in range(1, 9)],
    }


class PublicArchiveTests(unittest.TestCase):
    def test_unknown_result_keeps_runner_and_excludes_whole_race(self):
        r = race()
        r['starts'][-1]['result'] = {}
        reason, active = a.check_race(r)
        self.assertEqual(reason, 'unknown_result')
        self.assertEqual(len(active), 8)

    def test_only_explicit_scratch_removes_runner(self):
        r = race()
        r['starts'][-1]['out'] = True
        r['starts'][-1]['result'] = {'disqualified': True}
        self.assertEqual(len(a.check_race(r)[1]), 8)
        r['starts'][-1]['result'] = {'scratched': True}
        self.assertEqual(a.check_race(r)[0], 'eligible_result_field')
        self.assertEqual(len(a.check_race(r)[1]), 7)

    def test_dead_heat_and_duplicate_identity_are_excluded(self):
        r = race()
        r['starts'][1]['result']['place'] = 1
        self.assertEqual(a.check_race(r)[0], 'winner_not_unique')
        r = race()
        r['starts'][1]['horse'] = copy.deepcopy(r['starts'][0]['horse'])
        self.assertEqual(a.check_race(r)[0], 'invalid_or_duplicate_starter')

    def test_country_sport_and_dates_are_checked(self):
        r = race()
        r['track']['countryCode'] = 'NO'
        self.assertEqual(a.check_race(r)[0], 'other_sport_or_country')
        r = race()
        r['sport'] = 'monté'
        self.assertEqual(a.check_race(r)[0], 'other_sport_or_country')
        r = race()
        r['date'] = '2026-06-02'
        self.assertEqual(a.check_race(r)[0], 'invalid_identity_or_status')

    def test_csv_self_reported_field_size_does_not_prove_completeness(self):
        r = race()
        rows = [{'start_number': str(n), 'horse_id': str(n), 'won': str(int(n == 1)),
                 'field_size': '7'} for n in range(1, 8)]
        comparison = a.compare_csv(r['id'], r['starts'], rows)
        self.assertEqual(comparison['missingNumbers'], [8])
        self.assertEqual(comparison['identityOrWinnerConflicts'], [])
        rows[0]['horse_id'] = '999'
        self.assertEqual(a.compare_csv(r['id'], r['starts'], rows)['identityOrWinnerConflicts'], [1])

    def test_changed_source_bytes_fail_before_parsing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.json'
            path.write_bytes(b'{}')
            source = {'sha256': hashlib.sha256(b'{}').hexdigest()}
            self.assertEqual(a.verified_bytes(path, source), b'{}')
            path.write_bytes(b'{"changed": true}')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                a.verified_bytes(path, source)


if __name__ == '__main__':
    unittest.main()
