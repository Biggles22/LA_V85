#!/usr/bin/env python3
"""Exploratory walk-forward ablation using ACTUAL previous race opponents.

Missing original opponent data remains NaN; both models use exactly the same
dated V85 start fields, train dates, and held-out race dates. This experiment
must never automatically influence live spik/skrall recommendations.
"""
from __future__ import annotations
import json
import pathlib
import sys

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
EVIDENCE=ROOT/"research/historical_opponent_asof_2026.json"
OUT=ROOT/"research/historical_opponent_test_2026.json"


def evidence_index(doc):
    """Identity-safe map; never identify a horse by number alone."""
    found={}
    for x in doc.get("rows",[]):
        key=(x["raceId"],x["number"],x["horse"])
        if key in found:
            raise ValueError("Duplicate historical opponent identity")
        found[key]=x
    return found


def opponent_matrix(rows,index):
    import numpy as np
    original=enriched_matrix(rows)
    extra=[]
    for x in rows:
        r=index.get((x["raceId"],x["number"],x["horse"]))
        score=r.get("opponentForm") if r is not None else None
        extra.append([score if type(score) in (float,int) and 0<=score<=1 else float("nan")])
    return np.concatenate([original,np.asarray(extra,dtype="float64")],axis=1)


def marked_groups(groups,index,min_rated=6,min_fraction=.6):
    """A race is sufficiently observed only when at least 60% of runners are rated."""
    accepted={}
    for rid,items in groups.items():
        rated=sum(type((index.get((x["raceId"],x["number"],x["horse"])) or {}).get("opponentForm")) in
                  (int,float) for x in items)
        if len(items)>=6 and rated>=min_rated and rated/len(items)>=min_fraction:
            accepted[rid]=items
    return accepted


def run():
    import numpy as np
    history=json.loads(SOURCE.read_text(encoding="utf8"))
    evidence=json.loads(EVIDENCE.read_text(encoding="utf8"))
    if evidence.get("schemaVersion")!=1 or evidence.get("sourceRaceCount")!=history.get("raceCount"):
        raise ValueError("Historical opponent join not verified for this historical corpus")
    index=evidence_index(evidence)
    allrows=history["rows"]
    days=sorted({r["date"] for r in allrows})
    baseline={};experimental={};folds=[]
    for k,day in enumerate(days):
        if k<MIN_TRAIN_DATES:
            continue
        train=[x for x in allrows if x["date"]<day]
        test=[x for x in allrows if x["date"]==day]
        if len(train)<MIN_TRAIN_STARTERS or len(test)<6:continue
        if any(x["date"]>=day for x in train):
            raise AssertionError("Training includes future results")
        labels=np.array([x["winner"] for x in train],dtype="int32")
        model_a=estimator()
        model_b=estimator()
        model_a.fit(enriched_matrix(train),labels)
        model_b.fit(opponent_matrix(train,index),labels)
        p1=model_a.predict_proba(enriched_matrix(test))[:,1]
        p2=model_b.predict_proba(opponent_matrix(test,index))[:,1]
        for row,a,b in zip(test,p1,p2):
            rid=row["raceId"]
            baseline.setdefault(rid,[]).append({**row,"pred":float(a)})
            experimental.setdefault(rid,[]).append({**row,"pred":float(b)})
        folds.append({"date":day,"trainStarters":len(train),"testRaces":len({r["raceId"] for r in test})})
    if len(folds)<6:
        raise RuntimeError("Insufficient independent dates for evaluation")
    selected=marked_groups(baseline,index)
    matched_a={k:baseline[k] for k in selected}
    matched_b={k:experimental[k] for k in selected}
    paired_market=clean_paired(selected)
    keys=set(paired_market)
    covered_dates=sorted({x[0]["date"] for x in selected.values()})
    all_rated=sum(type((index.get((x["raceId"],x["number"],x["horse"])) or {}).get("opponentForm")) in
                 (int,float) for x in allrows)
    result={
        "schemaVersion":1,"reportType":"ACTUAL_PAST_OPPONENT_FORM_EXPLORATORY_NOT_VALIDATED",
        "historicalRaceCount":history["raceCount"],
        "historicalStarterCount":history["starterCount"],
        "datedFeatureRows":len(index),
        "ratedAllStarts":all_rated,
        "heldOutRaces":len(baseline),
        "ratedHeldOutRaces":len(selected),
        "ratedHeldOutDates":len(covered_dates),
        "strictPairedMarketRaces":len(keys),
        "baselineAll":evaluate(baseline,"pred"),
        "withHistoricalOpponentsAll":evaluate(experimental,"pred"),
        "baselineOnRatedRaces":evaluate(matched_a,"pred"),
        "withHistoricalOpponentsOnRatedRaces":evaluate(matched_b,"pred"),
        "baselineOnRatedAndCompleteMarket":evaluate({k:baseline[k] for k in keys},"pred"),
        "withHistoricalOpponentsOnRatedAndCompleteMarket":evaluate({k:experimental[k] for k in keys},"pred"),
        "marketFinalPoolOnRatedAndCompleteMarket":evaluate(paired_market,"marketFinalPct",market=True),
        "folds":folds,
        "method":"Each runner's ACTUAL previous race opponents are rated strictly BEFORE that previous race. Models trained on earlier V85 dates only. Scores missing on unmatched runner remain NaN.",
        "limitations":"Researcher has already tested alternatives on overlapping historical periods; these metrics are hypothesis-generating, not untouched final validation. Many historical starts lack opponent fields, and selection coverage may bias the subset. Betting baseline uses retrospective final market, not archived prestart snapshots.",
        "decision":"No change to live Bjerke tips or production model regardless of result; require independent future dated holdout."
    }
    previous=json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else None
    if previous==result:
        print("ACTUAL-OPPONENT-TEST unchanged");return
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("ACTUAL-OPPONENT-TEST",len(index),"dated rows; rated",all_rated,
          "heldout rated races",len(selected),"on",len(covered_dates),"dates;",
          "baseline",result["baselineOnRatedRaces"],
          "challenger",result["withHistoricalOpponentsOnRatedRaces"],flush=True)


if __name__=="__main__":
    try:run()
    except (ValueError,RuntimeError,ImportError,KeyError,AssertionError) as error:
        print("ACTUAL-OPPONENT EVALUATION NOT READY:",error,file=sys.stderr)
        sys.exit(1)
