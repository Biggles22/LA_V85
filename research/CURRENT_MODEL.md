# Current-round CatBoost ranking

Run from the repository root:

    python -m pip install -r scripts/requirements-current-model.txt
    python -m scripts.rank_current_catboost
    node tests/test_current_model.cjs
    node tests/test_model_render.cjs

The 2 November raw-source rebuild provides 196 eligible races / 2,307 starters across 25 dates, from 22 November 2025 through 24 October 2026. It recovered 145 of 147 previously quarantined races, retained all 31 previously eligible races and added 20 complete races. Two fields with unknown results and two dead heats are excluded. See [recovery evidence](history_recovery_2026.json) and [data quality](training_data_quality_2026.json).

Fixed CatBoost parameters follow the existing trial; no tuning against these tests. Expanding-date tests cover 164 races on 21 dates: top-3 winner coverage 83/164 (50.61%), top-1 29/164 (17.68%). Each fold trains on strictly earlier dates; the first four dates initialize training. The former 11/16 and 1/16 figures came from a much smaller selected test set and are not directly comparable. This retrospective, selected sample does not establish calibrated probabilities or profitability. Top-3 means three candidates to win, not a prediction of finishing order.

Only dated earlier starts and the target race's post, distance, field and start method enter features. Current outcomes, final market shares, names, drivers, trainers and career aggregates are excluded. Gallop remains disabled in BOTH training and prediction to preserve the baseline feature policy during data expansion. Numeric race-relative features use the same transformation on both sides. The separate historical final-pool benchmark is retrospective and is not a timestamped prestart market.

On the 161 identical races with usable final market shares, CatBoost covers 82 winners in its top three (29 first-ranked); final-pool ranking covers 110 (61 first-ranked). The model does not outperform this retrospective benchmark.

All 225 raw responses are retained with retrieval timestamps and hashes. Rebuild and verify the historical corpus without network access:

    python -m scripts.recover_historical --offline
    python -m scripts.audit_historical_asof
    python -m scripts.data_quality

Without `--offline`, missing raw sources are fetched at most once per second, with bounded retries and backoff for transient errors. The old aggregate supplies verified game identities only; its rows are never mixed into the new training corpus. The as-of audit finds consistent career start/win increments in 385 pairs of consecutive starts, but this is not proof that every historical field was frozen. Career statistics remain excluded.

Inference fetches each extended ATG race, checks the complete active field, identities, post and distance against the current snapshot, and fails on changes. Update the round first if the field has changed. model.json retains source hashes, exact features, software, training dates, folds, all scores and top three. The UI rejects a different snapshot or mismatched active horses. It does not convert model rankings into reviewed spikes or outsiders.
