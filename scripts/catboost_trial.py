#!/usr/bin/env python3
"""CatBoost benchmark on the same leakage-safe, chronological V85 pilot data.

Research only: CatBoost is evaluated against held-out future dates. No market
or outcome information enters the feature matrix. This does not publish a
betting strategy or calibrated probabilities.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

try:
    from scripts.walkforward_evaluation import (
        enriched_matrix, clean_paired, MIN_TRAIN_STARTERS, MIN_TRAIN_DATES,
        MIN_HELDOUT_DATES,
    )
    from scripts.train_historical_pilot import evaluate
except ModuleNotFoundError:
    from walkforward_evaluation import (
        enriched_matrix, clean_paired, MIN_TRAIN_STARTERS, MIN_TRAIN_DATES,
        MIN_HELDOUT_DATES,
    )
    from train_historical_pilot import evaluate

try:
    from scripts.data_quality import load_training_data, prepare_training_data, CURRENT, LEGACY, InsufficientHistory, publish_unavailable
except ModuleNotFoundError:
    from data_quality import load_training_data, prepare_training_data, CURRENT, LEGACY, InsufficientHistory, publish_unavailable

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = CURRENT if CURRENT.exists() else LEGACY
OUT = ROOT / "research" / "catboost_trial_v2.json"


def estimator():
    from catboost import CatBoostClassifier
    return CatBoostClassifier(
        iterations=220,
        depth=5,
        learning_rate=0.045,
        loss_function="Logloss",
        eval_metric="Logloss",
        l2_leaf_reg=6.0,
        random_seed=214,
        verbose=False,
        allow_writing_files=False,
        thread_count=2,
    )


def matrix(rows):
    # Same fixed feature policy as the published current-round model.
    clean = [{**r, 'prestartFeatures': {**r['prestartFeatures'], 'gallop5': None}} for r in rows]
    return enriched_matrix(clean)


def main():
    import numpy as np

    doc = load_training_data(SOURCE)
    rows = doc.get("rows", [])
    dates = sorted({r["date"] for r in rows})
    if len(dates) < MIN_TRAIN_DATES + MIN_HELDOUT_DATES:
        raise InsufficientHistory("Too few independent dates for CatBoost evaluation")

    all_groups, folds = {}, []
    for index, date in enumerate(dates):
        if index < MIN_TRAIN_DATES:
            continue
        training = [r for r in rows if r["date"] < date]
        holdout = [r for r in rows if r["date"] == date]
        if len(training) < MIN_TRAIN_STARTERS or len(holdout) < 6:
            continue
        if not all(r["date"] < date for r in training):
            raise AssertionError("Temporal leakage detected")

        model = estimator()
        model.fit(
            matrix(training),
            np.asarray([r["winner"] for r in training], dtype="int32"),
        )
        predictions = model.predict_proba(matrix(holdout))[:, 1]
        groups = {}
        for row, probability in zip(holdout, predictions):
            item = {**row, "catboostProb": float(probability)}
            groups.setdefault(row["raceId"], []).append(item)

        metrics = evaluate(groups, "catboostProb")
        paired = clean_paired(groups)
        folds.append({
            "date": date,
            "trainUntil": max(r["date"] for r in training),
            "trainedDates": len({r["date"] for r in training}),
            "trainStarts": len(training),
            "testMetrics": metrics,
            "pairedRaces": len(paired),
            "pairedCatBoost": evaluate(paired, "catboostProb"),
            "pairedMarket": evaluate(paired, "marketFinalPct", market=True),
        })
        all_groups.update(groups)

    tested = sum(f["testMetrics"]["races"] for f in folds)
    if len(folds) < MIN_HELDOUT_DATES or tested < 12:
        raise InsufficientHistory("Insufficient tested dates or races; no report published")

    paired = clean_paired(all_groups)
    report = {
        "trainingDataQuality":doc.get("dataQuality"),
        "reportType": "CATBOOST_EXPANDING_CHRONOLOGICAL_BACKTEST_NOT_VALIDATED",
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sourceRaceCount": doc.get("raceCount"),
        "sourceStarts": doc.get("starterCount"),
        "sourceDates": len(dates),
        "folds": folds,
        "testMetrics": evaluate(all_groups, "catboostProb"),
        "strictPairedCatBoost": evaluate(paired, "catboostProb"),
        "strictPairedMarket": evaluate(paired, "marketFinalPct", market=True),
        "strictPairedCount": len(paired),
        "disabledFeatures": ["gallop5"],
        "features": [
            "prestart numeric form, class, post/distance and race-relative features",
        ],
        "model": "CatBoostClassifier, 220 iterations, depth 5, time-ordered expanding-origin folds",
        "calibrationState": "NOT_CALIBRATED",
        "method": "Every held-out date is predicted by a model fitted only on strictly earlier dates. Market data is excluded from model features.",
        "limitations": "Exploratory benchmark with selected historical rounds. The current historical pilot does not yet contain sufficiently broad, validated categorical horse/kusk/tränare fields for production use. This report is not a profitability or betting recommendation.",
    }
    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    comparable = lambda value: {k: v for k, v in value.items() if k != "generatedAt"}
    if comparable(previous) == comparable(report):
        print("CATBOOST unchanged: no new report")
        return
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("CATBOOST", len(folds), "folds", tested, "tested races", flush=True)


if __name__ == "__main__":
    try:
        main()
    except InsufficientHistory as error:
        publish_unavailable(OUT, error, SOURCE)
    except (ImportError, RuntimeError, ValueError, AssertionError) as exc:
        print("CATBOOST NOT READY:", type(exc).__name__, str(exc), flush=True)
        sys.exit(1)
