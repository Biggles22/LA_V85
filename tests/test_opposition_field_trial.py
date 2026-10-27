"""Verify field-rival features are from previous form, never current results."""
import inspect
import unittest
from scripts import opposition_field_trial as o

def horse(rid,n,win,top,place,winner=0):
    return {"date":"2026-10-10","raceId":rid,"number":n,"winner":winner,
            "marketFinalPct":12.5,"prestartFeatures":{
                "win5":win,"top3_5":top,"form_place_mean":place,
                "post":n,"distance":2140,"field":8,"auto":1,"starts5":5,
                "days_off":18,"gallop5":None,"km_median":None,"past_purse_log":None}}

class Tests(unittest.TestCase):
    def test_rival_average_does_not_include_the_horse(self):
        group=[horse("r",1,5,5,1,winner=1)]+[
            horse("r",n,0,0,9) for n in range(2,9)]
        x=o.rival_form_features(group)
        self.assertEqual(x[0][0],0)
        self.assertEqual(x[1][0],5/7)
        self.assertEqual(x[0][3],5)

    def test_missing_history_stays_missing(self):
        group=[horse("r",n,None,None,None) for n in range(1,9)]
        for sample in o.rival_form_features(group):
            self.assertTrue(all(value is None for value in sample))

    def test_no_result_or_market_access_in_feature_generation(self):
        src=inspect.getsource(o.rival_form_features)+inspect.getsource(o.augmented_matrix)
        self.assertNotIn('["winner"]',src)
        self.assertNotIn("marketFinalPct",src)
        self.assertEqual(len(o.COLUMNS),6)

    def test_different_races_never_mix(self):
        a=[horse("a",n,5,5,1) for n in range(1,9)]
        b=[horse("b",n,0,0,9) for n in range(1,9)]
        scores=o.rival_form_features(a+b)
        self.assertEqual(scores[0][0],5)
        self.assertEqual(scores[8][0],0)

if __name__=="__main__":
    unittest.main()
