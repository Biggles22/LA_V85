"""Fixed-feature experiment: avoid using market / winners in horse features."""
import inspect
import unittest
from scripts import feature_trial as f


class FeatureTrialTests(unittest.TestCase):
    def test_explanatory_feature_count(self):
        self.assertEqual(len(f.FEATURE_NAMES),12)

    def test_no_outcomes_or_market_in_matrix(self):
        code=inspect.getsource(f.enhanced_matrix)
        self.assertNotIn('["winner"]',code)
        self.assertNotIn("marketFinalPct",code)
        self.assertNotIn("finalOdds",code)

    def test_constant_hyperparameters_for_both_models(self):
        code=inspect.getsource(f.evaluate_trial)
        self.assertIn("left=estimator()",code)
        self.assertIn("right=estimator()",code)

    def test_all_train_dates_strictly_older(self):
        source=inspect.getsource(f.evaluate_trial)
        self.assertIn('r["date"]<date',source)
        self.assertIn('Detected temporal training leakage',source)


if __name__=="__main__":
    unittest.main()
