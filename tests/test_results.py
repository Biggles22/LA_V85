"""Verify receipt transcription, row settlement and the published results page."""
import itertools
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ResultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'resultat/data.json').read_text())
        cls.html = (ROOT / 'resultat/index.html').read_text()

    def test_receipt_costs_and_independent_row_enumeration(self):
        expected = {'Boden': (486, 6, 595.5), 'Solvalla': (720, 5, 56),
                    'Gävle': (540, 2, 0), 'Jägersro': (486, 5, 108),
                    'Bjerke': (648, 8, 1338), 'Bergsåker': (1000, 7, 12.5)}
        for round_ in self.data['rounds']:
            with self.subTest(track=round_['track']):
                choices = [[h['number'] for h in leg['selected']] for leg in round_['legs']]
                winners = [{h['number'] for h in leg['winners']} for leg in round_['legs']]
                counts = {str(k): 0 for k in range(5, 9)}
                rows = list(itertools.product(*choices))
                for row in rows:
                    correct = sum(n in valid for n, valid in zip(row, winners))
                    if correct >= 5:
                        counts[str(correct)] += 1
                self.assertEqual(counts, round_['winningRows'])
                self.assertEqual(len(rows) * .25, round_['costSEK'])
                prize = sum(counts[k] * p['amountSEK'] * .5 for k, p in round_['payouts'].items())
                self.assertEqual(prize, round_['prizeSEK'])
                self.assertEqual((round_['costSEK'], round_['hits'], prize), expected[round_['track']])
                self.assertIn('omgang-' + round_['date'], self.html)

    def test_bergsaker_receipt_and_unused_reserve(self):
        r = next(r for r in self.data['rounds'] if r['date'] == '2026-11-07')
        self.assertEqual([[h['number'] for h in leg['selected']] for leg in r['legs']],
                         [[1,5,6,9], [1,2,3,4,5], [1,6,7,8,9], [6], [1,4,12,14], [5,6], [6], [5,6,8,9,14]])
        self.assertEqual([leg['reserves'] for leg in r['legs']],
                         [[2,4], [10,11], [11,5], [1,8], [10,6], [1,2], [7,4], [1,2]])
        self.assertEqual(r['submittedAt'], '2026-11-07 13:22')
        self.assertEqual(r['rows'], 4000)
        self.assertEqual(r['winningRows'], {'5':147, '6':19, '7':1, '8':0})
        self.assertFalse(r['legs'][3]['hit'])
        self.assertFalse(any(leg['scratchedSelected'] for leg in r['legs']))
        self.assertIn('13:22', self.html)
        self.assertIn('−987,50 kr', self.html)

    def test_totals_and_home_navigation(self):
        rounds = self.data['rounds']
        self.assertEqual(sum(r['costSEK'] for r in rounds), 3880)
        self.assertEqual(sum(r['prizeSEK'] for r in rounds), 2110)
        self.assertEqual(sum(r['netSEK'] for r in rounds), -1770)
        self.assertEqual(sum(r['netSEK'] > 0 for r in rounds), 2)
        for value in ['3 880', '2 110', '−1 770', '54,4']:
            self.assertIn(value, self.html)
        self.assertIn('href="./resultat/"', (ROOT / 'index.html').read_text())
        self.assertIn("url('resultat/')", (ROOT / 'site-navigation.js').read_text())

    def test_dead_heats_and_jackpot(self):
        jagersro = next(r for r in self.data['rounds'] if r['track'] == 'Jägersro')
        self.assertEqual([w['number'] for w in jagersro['legs'][2]['winners']], [2, 9])
        self.assertEqual([w['number'] for w in jagersro['legs'][6]['winners']], [5, 6])
        bjerke = next(r for r in self.data['rounds'] if r['track'] == 'Bjerke')
        self.assertEqual(bjerke['winningRows']['7'], 15)
        self.assertTrue(bjerke['payouts']['6']['jackpot'])
        self.assertEqual(bjerke['payouts']['6']['amountSEK'], 0)


if __name__ == '__main__':
    unittest.main()
