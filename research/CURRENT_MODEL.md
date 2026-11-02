# Current-round CatBoost ranking

Run from the repository root:

    python -m pip install -r scripts/requirements-current-model.txt
    python -m scripts.rank_current_catboost
    node tests/test_current_model.cjs
    node tests/test_model_render.cjs

The expanded ATG collection provides **1,047 eligible races / 12,247 starters across 145 dates**, from 6 January 2024 through 31 October 2026: 634 V75 races (7,441 starts) and 413 V85 races (4,806 starts). It includes 81 races at Bergsåker. All 148 Saturdays were checked through ATG's calendar; three midsummer Saturdays had no V75/V85 game. Every previously eligible race is retained, with 851 additional eligible races. See [collection evidence](history_expansion_2026.json), [expanded evaluation](expanded_model_evaluation_2026.json) and [data quality](training_data_quality_2026.json).

CatBoost parameters are unchanged, with no tuning against these tests. Each fold trains on strictly earlier V75 and V85 dates; **all evaluation races are V85**. Expanding-date tests cover 413 races on 53 dates: top-3 winner coverage 222/413 (53.75%), top-1 92/413 (22.28%). On the identical 164 races from the archived 196-race experiment, top-three coverage changes from 83 to 91 and top-one wins from 29 to 41. These are observed counts, not proof of a lasting improvement. The [baseline](baseline_196_races_2026.json) retains its predictions and fixed parameters.

A separate later-period check fits once through 25 July 2026, then tests 108 V85 races from 1 August through 31 October: top three 54/108, top one 21/108. No fitting or parameter tuning uses that period in this run. Some dates were examined in earlier experiments, so it is not an untouched prospective test. Top-three candidates are candidates to win, not a prediction of finishing order.

Only dated earlier starts and the target race's post, distance, field and start method enter features. Current outcomes, final market shares, names, drivers, trainers and career aggregates are excluded. Gallop remains disabled in BOTH training and prediction to preserve the baseline feature policy during data expansion. Numeric race-relative features use the same transformation on both sides. The separate historical final-pool benchmark is retrospective and is not a timestamped prestart market.

On 405 identical V85 races with usable final market shares: CatBoost top three 217/405 (top one 90), XGBoost top three 229/405 (top one 101), final-pool ranking top three 290/405 (top one 155). Both models use the same feature policy and strictly earlier training data. Neither outperforms the retrospective final-pool benchmark. XGBoost is a comparison; the published current-round ranking continues to use the fixed CatBoost model.

The expanded collection retains 1,361 raw responses with retrieval timestamps and hashes. New raw responses use lossless gzip compression; the earlier plain JSON cache remains readable. Rebuild and verify the expanded historical corpus without network access:

    python -m scripts.expand_historical --offline
    python -m scripts.audit_historical_asof --expanded
    python -m scripts.data_quality

Without `--offline`, missing sources are fetched at most once per second, with bounded retries and backoff for transient errors. Game IDs come from the calendar, with seven legs required for V75 and eight for V85. The old 196-race corpus remains unchanged as recovery evidence. The expanded corpus is preferred by the current model and data-quality summary; older explicitly selected v2 experiments retain their original source.

Of 1,068 collected races, 21 are excluded: 14 with unknown results, three dead heats, three monté races and one field with only five active runners (the model's supported range is 6–20). No unknown result becomes a negative training label. The expanded as-of audit found consistent career start/win increments in 3,089 of 3,093 comparable consecutive-start pairs, with four mismatches. No same-day or future history entered features, and career statistics remain excluded.

Inference fetches each extended ATG race, checks the complete active field, identities, post and distance against the current snapshot, and fails on changes. Update the round first if the field has changed. model.json retains source hashes, exact features, software, training dates, folds, all scores and top three. The UI rejects a different snapshot or mismatched active horses. It does not convert model rankings into reviewed spikes or outsiders.
