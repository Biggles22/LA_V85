import unittest
from scripts.score_frozen_report import score
class FrozenReportTests(unittest.TestCase):
    def test_dead_heat_counts_once_and_pending_excluded(self):
        records=[{'raceId':'a','leg':1,'horses':[{'number':1},{'number':2},{'number':3}]},{'raceId':'b','leg':2,'horses':[{'number':1},{'number':2},{'number':3}]}]
        self.assertEqual(score(records,{'a':[1,2]},3),{'hits':1,'races':1,'legs':[1]})
    def test_ambiguous_or_duplicate_rejected(self):
        r={'raceId':'a','leg':1,'horses':[{'number':1},{'number':1},{'number':3}]}
        with self.assertRaises(ValueError): score([r],{'a':[1]},3)
        r['horses']=[{'number':1}]
        with self.assertRaises(ValueError): score([r,r],{'a':[1]},1)
