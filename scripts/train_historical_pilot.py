#!/usr/bin/env python3
"""Time-split exploratory XGBoost backtest, NOT a validated betting strategy."""
from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
import statistics
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
INPUT=ROOT/"research/historical_pilot_2026.json"
OUTPUT=ROOT/"research/model_report_2026.json"
FEATURES=("post","distance","field","auto","starts5","form_place_mean",
          "win5","top3_5","days_off","gallop5","km_median","past_purse_log")


def normalized_per_race(probs):
    valid=[float(p) if p is not None and math.isfinite(float(p)) and float(p)>=0 else 0 for p in probs]
    total=sum(valid)
    return [max(1e-9,p/total) for p in valid] if total>0 else [1/len(valid)]*len(valid)


def evaluate(races, prediction_key, market=False):
    matched=0;top1=0;top3=0;losses=[];briers=[]
    for rows in races.values():
        if len(rows)<6 or sum(r["winner"] for r in rows)!=1:
            continue
        values=[r.get(prediction_key) for r in rows]
        if market and (any(v is None for v in values) or not 90<=sum(values)<=110):
            continue
        if any(v is None for v in values):
            continue
        probs=normalized_per_race(values)
        ranked=sorted(range(len(rows)),key=lambda i:probs[i],reverse=True)
        winner=next(i for i,r in enumerate(rows) if r["winner"])
        matched+=1
        top1+=winner==ranked[0]
        top3+=winner in ranked[:3]
        losses.append(-math.log(max(probs[winner],1e-9)))
        briers.append(sum((p-r["winner"])**2 for p,r in zip(probs,rows))/len(rows))
    return {"races":matched,
            "top1Count":top1,"top3Count":top3,
            "top1Rate":round(top1/matched,4) if matched else None,
            "top3Rate":round(top3/matched,4) if matched else None,
            "raceLogLoss":round(statistics.mean(losses),4) if losses else None,
            "horseBrier":round(statistics.mean(briers),5) if briers else None}


def train():
    import numpy as np
    from xgboost import XGBClassifier

    data=json.loads(INPUT.read_text())
    rows=data.get("rows",[])
    dates=sorted({x["date"] for x in rows})
    if len(dates)<6:
        raise RuntimeError("Need >=6 distinct historical dates for time-split exploratory evaluation")
    boundary=max(3,int(len(dates)*0.7))
    if len(dates)-boundary<2:
        raise RuntimeError("Need at least 2 held-out dates")
    train_dates=set(dates[:boundary]);test_dates=set(dates[boundary:])
    train_rows=[x for x in rows if x["date"] in train_dates]
    test_rows=[x for x in rows if x["date"] in test_dates]
    if len(train_rows)<200 or len(test_rows)<60:
        raise RuntimeError("Insufficient training/test starters")
    def matrix(items):
        return np.array([[float(row["prestartFeatures"][k]) if row["prestartFeatures"].get(k) is not None
                          else np.nan for k in FEATURES] for row in items],dtype="float64")
    y_train=np.array([r["winner"] for r in train_rows],dtype="int32")
    model=XGBClassifier(n_estimators=135,max_depth=3,learning_rate=.06,
        subsample=.85,colsample_bytree=.88,reg_lambda=4,
        objective="binary:logistic",eval_metric="logloss",tree_method="hist",
        random_state=214,n_jobs=2)
    model.fit(matrix(train_rows),y_train)
    preds=model.predict_proba(matrix(test_rows))[:,1]
    groups={}
    for row,pred in zip(test_rows,preds):
        x={**row,"pred":float(pred)}
        groups.setdefault(x["raceId"],[]).append(x)
    metrics=evaluate(groups,"pred")
    baseline=evaluate(groups,"marketFinalPct",market=True)
    if metrics["races"]<12:
        raise RuntimeError("Test contains fewer than 12 eligible races")
    ranked=[]
    for rid,items in groups.items():
        probabilities=normalized_per_race([r["pred"] for r in items])
        top=sorted(range(len(items)),key=lambda i:probabilities[i],reverse=True)
        winners=[r["number"] for r in items if r["winner"]]
        ranked.append({"raceId":rid,"date":items[0]["date"],
            "topModel":[{"number":items[i]["number"],"horse":items[i]["horse"],
                         "modelProb":round(probabilities[i],4)} for i in top[:3]],
            "winnerNumbers":winners,
            "winnerInTop3":items[top[0]]["winner"]==1 or any(items[i]["winner"] for i in top[1:3])})
    report={
        "reportType":"EXPLORATORY_BACKTEST_NOT_VALIDATED",
        "createdAt":dt.datetime.now(dt.timezone.utc).isoformat(),
        "trainDates":[dates[0],dates[boundary-1]],
        "heldOutDates":[dates[boundary],dates[-1]],
        "trainStarts":len(train_rows),"testStarts":len(test_rows),
        "trainRaces":len({r["raceId"] for r in train_rows}),
        "testRaces":len(groups),
        "model":"XGBClassifier, 135 trees, depth 3, time-ordered date holdout",
        "features":list(FEATURES),
        "modelMetrics":metrics,
        "marketFinalPoolBaseline":baseline,
        "baselineCaveat":"Market uses retrospective final V85 pool percentages, NOT independently archived prestart snapshots. Cross-pool timing may not be independently verified.",
        "validationCaveat":"Small pilot, one chronological holdout, no hyperparameter search or robust confidence intervals. Do not interpret as profit, actionable spik/skrall recommendations or proven independent probabilities.",
        "racePredictions":ranked,
    }
    previous=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else None
    if previous is not None:
        comparison=lambda d:{k:v for k,v in d.items() if k!="createdAt"}
        if comparison(previous)==comparison(report):
            print("Model unchanged; no new report.");return
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("MODEL",metrics,"FINAL_POOL_BASELINE",baseline,flush=True)


if __name__=="__main__":
    try:
        train()
    except (ImportError,ValueError,RuntimeError) as error:
        print("Pilot not ready:",error,flush=True)
        sys.exit(1)
