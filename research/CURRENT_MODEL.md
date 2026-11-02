# Current-round CatBoost ranking

Run from the repository root:

    python -m pip install -r scripts/requirements-current-model.txt
    python -m scripts.rank_current_catboost
    node tests/test_current_model.cjs
    node tests/test_model_render.cjs

The script uses the shared historical data-quality filter, whole fields only, and strictly earlier dates. The current legacy corpus has 31 eligible races / 354 starters across 16 dates; 147 incomplete fields are quarantined. No outcome or market fields enter the feature matrix. Unverified historical gallop values are masked in training AND prediction. Numeric race-relative features use the same transformation on both sides.

Fixed CatBoost parameters follow the existing trial; no tuning against this holdout. Expanding-date tests cover 16 races: top-3 winner coverage 11/16, top-1 1/16. This selected, small sample does not establish calibrated probabilities or profitability. Top-3 means three candidates to win, not a prediction of finishing order.

Inference fetches each extended ATG race, checks the complete active field, identities, post and distance against the current snapshot, and fails on changes. Update the round first if the field has changed. model.json retains source hashes, exact features, software, training dates, folds, all scores and top three. The UI rejects a different snapshot or mismatched active horses. It does not convert model rankings into reviewed spikes or outsiders.
