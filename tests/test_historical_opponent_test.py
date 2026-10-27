"""Regression checks for actual historical previous-opponent features."""
import unittest
from scripts import historical_opponent_test as m

def row(num,score=None):
    return {"raceId":"2026-09-10_1_1","number":num,"horse":f"Runner{num}",
            "winner":1 if num==1 else 0,
            "date":"2026-09-10",
            "prestartFeatures":{"post":num,"field":8,"auto":1,"distance":2140,
                "starts5":5,"form_place_mean":4,"win5":1,"top3_5":2,
                "days_off":16,"gallop5":None,"km_median":75,"past_purse_log":15.2},
            "marketFinalPct":12.5}

class ActualOpponentTests(unittest.TestCase):
    def test_three_part_identity_and_duplicate_rejection(self):
        report={"rows":[{"raceId":"R","number":2,"horse":"A","opponentForm":.4},
                        {"raceId":"R","number":3,"horse":"B","opponentForm":.5}]}
        index=m.evidence_index(report)
        self.assertEqual(len(index),2)
        report["rows"].append(report["rows"][0])
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            m.evidence_index(report)

    def test_unknown_score_is_nan_not_zero(self):
        report={"rows":[{"raceId":"2026-09-10_1_1","number":2,
                         "horse":"Runner2","opponentForm":.25}]}
        matrix=m.opponent_matrix([row(1),row(2)],m.evidence_index(report))
        import math
        self.assertTrue(math.isnan(matrix[0,-1]))
        self.assertAlmostEqual(matrix[1,-1],.25)

    def test_coverage_filter_requires_six_and_sixty_percent(self):
        group=[row(n) for n in range(1,9)]
        index={(r["raceId"],r["number"],r["horse"]):{"opponentForm":.4} for r in group[:5]}
        self.assertFalse(m.marked_groups({"race":group},index))
        sixth=group[5];index[(sixth["raceId"],sixth["number"],sixth["horse"])]={"opponentForm":.4}
        self.assertTrue(m.marked_groups({"race":group},index))

    def test_no_same_race_result_in_opponent_feature(self):
        import inspect
        source=inspect.getsource(m.opponent_matrix)+inspect.getsource(m.evidence_index)
        self.assertNotIn('["winner"]',source)
        self.assertNotIn("marketFinalPct",source)

if __name__=="__main__":
    unittest.main()
