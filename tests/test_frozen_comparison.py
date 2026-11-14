import unittest
from scripts.score_frozen_comparison import metric, paired, score

class FrozenComparisonTest(unittest.TestCase):
    def test_dead_heat_is_one_race(self):
        result = metric({'r':[2,9,4]}, {'r':{2,9}}, 3)
        self.assertEqual((result['hits'],result['races']), (1,1))

    def test_incomplete_or_duplicate_trio_is_not_top_three(self):
        for choices in [[1,2],[1,1,2],[1,2,3,4]]:
            with self.assertRaises(ValueError):metric({'r':choices},{'r':{1}},3)

    def test_missing_result_and_missing_prediction_are_not_failures(self):
        self.assertEqual(metric({'r':[1]}, {}, 1)['races'],0)
        self.assertEqual(metric({}, {'r':{1}}, 1)['races'],0)
        self.assertEqual(metric({'r':[1]}, {'r':{2}}, 1)['hits'],0)

    def test_pair_uses_intersection_for_each_metric(self):
        left={'first':{'a':[1],'b':[2]},'top3':{'a':[1,2,3],'b':[2,3,4]}}
        right={'first':{'b':[1]},'top3':{'a':[4,5,6]}}
        result=paired(left,right,{'a':{1},'b':{2}})
        self.assertEqual(result['first']['left']['raceIds'],['b'])
        self.assertEqual(result['first']['left']['hits'],1)
        self.assertEqual(result['top3']['left']['raceIds'],['a'])
        self.assertEqual(result['top3']['right']['hits'],0)

if __name__=='__main__':unittest.main()
