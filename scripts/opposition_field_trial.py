#!/usr/bin/env python3
"""Test leave-one-out prestart OPPOSITION form on dated historical V85 starts.

This test uses the OTHER RUNNERS IN THE UPCOMING HISTORICAL RACE, calculated
strictly from their own prestartFeatures. This is DIFFERENT from the separate
Bjerke historic-opponents database, which has no historical backtest yet.

Research only. Same XGBoost settings, fold dates, and hyperparameters for both.
Never use outcomes/odds/market as input. Holdouts are exploratory, not final.
"""
from __future__ import annotations
import datetime as dt
import json
import pathlib
import sys
from collections import defaultdict

try:
    from scripts.walkforward_evaluation import enriched_matrix,clean_paired,MIN_TRAIN_DATES,MIN_TRAIN_STARTERS
    from scripts.feature_trial import estimator
    from scripts.train_historical_pilot import evaluate
except ModuleNotFoundError:
    from walkforward_evaluation import enriched_matrix,clean_paired,MIN_TRAIN_DATES,MIN_TRAIN_STARTERS
    from feature_trial import estimator
    from train_historical_pilot import evaluate

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research/historical_pilot_2026.json"
DEST=ROOT/"research/opposition_field_trial_2026.json"
COLUMNS=("rival_win5_mean","rival_top3_5_mean","rival_place_mean",
         "horse_vs_rival_win5","horse_vs_rival_top3_5","rated_rivals")


def rival_form_features(rows):
    """Return features per row, excluding THIS horse's own form as a rival.

    A prior form is unknown if fewer than 2 dated placements. We do not
    treat null historical results as 0; require at least four rated rivals.
    """
    groups=defaultdict(list)
    for idx,row in enumerate(rows):
        groups[row["raceId"]].append(idx)
    output=[None]*len(rows)
    for positions in groups.values():
        for i in positions:
            other=[rows[j]["prestartFeatures"] for j in positions if j!=i]
            def measured(key):
                return [float(r[key]) for r in other if type(r.get(key)) in (int,float)]
            wins=measured("win5");tops=measured("top3_5");places=measured("form_place_mean")
            if min(len(wins),len(tops),len(places))<4:
                output[i]=[None]*len(COLUMNS)
                continue
            avg_win=sum(wins)/len(wins)
            avg_top=sum(tops)/len(tops)
            avg_place=sum(places)/len(places)
            focus=rows[i]["prestartFeatures"]
            own_win=focus.get("win5")
            own_top=focus.get("top3_5")
            output[i]=[
                avg_win,avg_top,avg_place,
                float(own_win)-avg_win if own_win is not None else None,
                float(own_top)-avg_top if own_top is not None else None,
                float(min(len(wins),len(tops),len(places))),
            ]
    return output


def augmented_matrix(rows):
    import numpy as np
    base=enriched_matrix(rows)
    extra=rival_form_features(rows)
    return np.concatenate((base,np.array([[float(v) if v is not None else float("nan")
                                         for v in row] for row in extra],dtype="float64")),axis=1)


def backtest(document):
    import numpy as np
    data=document["rows"]
    dates=sorted({x["date"] for x in data})
    base_groups={};opponent_groups={};folds=[]
    for idx,date in enumerate(dates):
        if idx<MIN_TRAIN_DATES:continue
        training=[r for r in data if r["date"]<date]
        held=[r for r in data if r["date"]==date]
        if len(training)<MIN_TRAIN_STARTERS or not held:
            continue
        if any(r["date"]>=date for r in training):
            raise AssertionError("Chronological leak")
        y=np.array([r["winner"] for r in training],dtype="int32")
        regular=estimator()
        challenger=estimator()
        regular.fit(enriched_matrix(training),y)
        challenger.fit(augmented_matrix(training),y)
        p1=regular.predict_proba(enriched_matrix(held))[:,1]
        p2=challenger.predict_proba(augmented_matrix(held))[:,1]
        for row,a,b in zip(held,p1,p2):
            rid=row["raceId"]
            base_groups.setdefault(rid,[]).append({**row,"pred":float(a)})
            opponent_groups.setdefault(rid,[]).append({**row,"pred":float(b)})
        folds.append({"testDate":date,"trainedBefore":date,"trainRunners":len(training),
                      "testRaces":len({r["raceId"] for r in held})})
    if len(folds)<6 or len(base_groups)<30:
        raise RuntimeError("Insufficient historical out-of-time test dates")
    paired=clean_paired(base_groups)
    ids=set(paired)
    base_paired={rid:base_groups[rid] for rid in ids}
    ch_paired={rid:opponent_groups[rid] for rid in ids}
    coverage=rival_form_features(data)
    measured=sum(row[0] is not None for row in coverage)
    return {
        "schemaVersion":1,
        "reportType":"HISTORIC_UPCOMING_FIELD_OPPOSITION_ABLATION_NOT_VALIDATED",
        "sourceRaces":document.get("raceCount"),"sourceStarts":document.get("starterCount"),
        "foldCount":len(folds),"heldOutRaces":len(base_groups),
        "oppositionFeatures":list(COLUMNS),
        "runnersWithRatedRivals":measured,
        "measureDefinition":"Rivals are other horses in the SAME upcoming historical race, rated solely from their previous starts. This is NOT previous races' opponent strength.",
        "baselineAll":evaluate(base_groups,"pred"),
        "oppositionAll":evaluate(opponent_groups,"pred"),
        "pairedCount":len(ids),
        "baselinePaired":evaluate(base_paired,"pred"),
        "oppositionPaired":evaluate(ch_paired,"pred"),
        "atgFinalPoolPaired":evaluate(base_paired,"marketFinalPct",market=True),
        "caveats":"Same historical dates repeatedly reused during feature development; possible researcher overfitting. End-of-pool ATG comparisons are retrospective, not verified prestart market. Incomplete-result races can bias evaluation. No validated profit or win chances.",
        "folds":folds,
    }


def main():
    document=json.loads(SOURCE.read_text(encoding="utf8"))
    result=backtest(document)
    old=json.loads(DEST.read_text(encoding="utf8")) if DEST.exists() else None
    if result==old:
        print("FIELD-OPPOSITION unchanged");return
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("FIELD-OPPOSITION",result["heldOutRaces"],"races,",
          result["runnersWithRatedRivals"],"feature-complete runners;",
          "baseline",result["baselineAll"],"opposition",result["oppositionAll"],flush=True)

if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,RuntimeError,ImportError,AssertionError) as e:
        print("FIELD OPPOSITION NOT READY:",str(e),file=sys.stderr)
        sys.exit(1)
