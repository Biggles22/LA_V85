"""Checks for strict paired benchmark and leakage-safe relative features."""
import unittest
from scripts import walkforward_evaluation as w


class WalkforwardTests(unittest.TestCase):
    def test_paired_refuses_incomplete_result_card(self):
        base=[{"raceId":"R","date":"2026-09-01","winner":int(i==1),
               "number":i,"resultCoverage":0.83,"marketFinalPct":100/8,
               "pred":0.1} for i in range(1,9)]
        self.assertEqual(len(w.clean_paired({"R":base})),0)
        for x in base:x["resultCoverage"]=1.0
        self.assertEqual(len(w.clean_paired({"R":base})),1)

    def test_paired_refuses_incomplete_pool_even_for_complete_results(self):
        base=[{"raceId":"R","winner":int(i==1),"resultCoverage":1.,
               "marketFinalPct":2.0} for i in range(1,9)]
        self.assertEqual(len(w.clean_paired({"R":base})),0)
        base[0]["marketFinalPct"]=None
        self.assertEqual(len(w.clean_paired({"R":base})),0)

    def test_relative_features_use_no_betting_or_outcome(self):
        import inspect
        source=inspect.getsource(w.enriched_matrix)
        self.assertNotIn("marketFinalPct",source)
        self.assertNotIn('["winner"]',source)
        self.assertEqual(w.rank_pct(2,[1,2,3]),0.5)
        self.assertAlmostEqual(w.rank_pct(1,[1,2,3],True),0.8333,places=3)

    def test_no_market_benchmark_biased_by_dropped_horses(self):
        incomplete=[{"raceId":"R","winner":int(i==1),"resultCoverage":.9,
                     "marketFinalPct":100/9} for i in range(1,10)]
        # Sum is 100, but result card missing runners: still reject.
        self.assertEqual(len(w.clean_paired({"R":incomplete})),0)


if __name__=="__main__":
    unittest.main()
