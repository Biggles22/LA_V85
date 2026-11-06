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
                    'Bjerke': (648, 8, 1338)}
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

    def test_totals_and_home_navigation(self):
        rounds = self.data['rounds']
        self.assertEqual(sum(r['costSEK'] for r in rounds), 2880)
        self.assertEqual(sum(r['prizeSEK'] for r in rounds), 2097.5)
        self.assertEqual(sum(r['netSEK'] for r in rounds), -782.5)
        self.assertEqual(sum(r['netSEK'] > 0 for r in rounds), 2)
        for value in ['2 880', '2 097,50', '−782,50', '72,8']:
            self.assertIn(value, self.html)
        self.assertIn('href="./resultat/"', (ROOT / 'index.html').read_text())
        self.assertIn("url('resultat/')", (ROOT / 'site-navigation.js').read_text())

    def test_dead_heats_and_jackpot(self):
        jagersro = next(r for r in self.data['rounds'] if r['track'] == 'Jägersro')
        self.assertEqual([w['number'] for w in jagersro['legs'][2]['winners']], [2, 9])
        self.assertEqual([w['number'] for w in jagersro['legs'][6]['winners']], [5, 6])
        bjerke = self.data['rounds'][0]
        self.assertEqual(bjerke['winningRows']['7'], 15)
        self.assertTrue(bjerke['payouts']['6']['jackpot'])
        self.assertEqual(bjerke['payouts']['6']['amountSEK'], 0)


if __name__ == '__main__':
    unittest.main()
