#!/usr/bin/env python3
"""Research-only comparison of fixed XGBoost baselines with extra prestart features.

Exactly the same expanding-date test folds for both models. NO winner, odds,
pool percentages or future race outcomes ever enter the feature matrices.
Results are exploratory; do not select the winning feature set using holdout.
"""
from __future__ import annotations
import datetime as dt
import json
import math
import pathlib
import statistics
import sys
try:
    from scripts.walkforward_evaluation import enriched_matrix, clean_paired, MIN_TRAIN_STARTERS, MIN_TRAIN_DATES
    from scripts.train_historical_pilot import evaluate
except ModuleNotFoundError:
    from walkforward_evaluation import enriched_matrix, clean_paired, MIN_TRAIN_STARTERS, MIN_TRAIN_DATES
    from train_historical_pilot import evaluate

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research/historical_pilot_2026.json"
OUT=ROOT/"research/feature_trial_2026.json"

FEATURE_NAMES=(
    "relative_past_purse_and_form",  # not actual opponent ratings
    "race_relative_recent_placings",
    "past_win_fraction",
    "post_inside_auto",
    "post_outer_auto",
    "sprint_inside_draw",
    "distance_sprint_flag",
    "distance_stayer_flag",
    "rest_short_flag",
    "rest_long_flag",
    "has_two_comparable_kilometre_times",
    "has_past_purse_evidence",
)

def enhanced_matrix(rows):
    import numpy as np
    base=enriched_matrix(rows)
    extra=[]
    for row in rows:
        f=row["prestartFeatures"]
        # These field-relative percentiles are computed by enriched_matrix
        # ONLY from each upcoming opponent's own earlier performances.
        # Notably NOT retrospectively inferred strength of past opponents.
        # Base layout: 12 absolute + post ratio, form rank, wins rank,
        # km rank and purse rank.
        i=len(extra)
        v=base[i]
        purse_rank=v[16] if len(v)>16 and math.isfinite(v[16]) else float("nan")
        form_rank=v[13] if len(v)>13 and math.isfinite(v[13]) else float("nan")
        strength=purse_rank*form_rank if math.isfinite(purse_rank) and math.isfinite(form_rank) else float("nan")
        post=f.get("post");distance=f.get("distance");field=f.get("field")
        auto=f.get("auto")==1
        good_position=isinstance(post,(int,float)) and isinstance(field,(int,float)) and field>0
        post_ratio=post/field if good_position else None
        win=f.get("win5");starts=f.get("starts5")
        win_fraction=win/starts if win is not None and starts and starts>0 else float("nan")
        short=distance is not None and distance<=1700
        long=distance is not None and distance>=2600
        gap=f.get("days_off")
        vals=[
            strength,
            form_rank,
            win_fraction,
            float(post_ratio<=0.45) if auto and post_ratio is not None else float("nan"),
            float(post_ratio>=0.75) if auto and post_ratio is not None else float("nan"),
            float(post_ratio<=0.45) if auto and post_ratio is not None and short else float("nan"),
            float(short) if distance is not None else float("nan"),
            float(long) if distance is not None else float("nan"),
            float(gap<=14) if gap is not None else float("nan"),
            float(gap>=80) if gap is not None else float("nan"),
            float(f.get("km_median") is not None),
            float(f.get("past_purse_log") is not None),
        ]
        extra.append(vals)
    return np.concatenate([base,np.asarray(extra,dtype="float64")],axis=1)


def estimator():
    from xgboost import XGBClassifier
    return XGBClassifier(n_estimators=120,max_depth=3,learning_rate=.055,
       subsample=.85,colsample_bytree=.85,reg_lambda=5,
       objective="binary:logistic",eval_metric="logloss",tree_method="hist",
       random_state=214,n_jobs=2)


def evaluate_trial(doc):
    import numpy as np
    rows=doc["rows"]
    dates=sorted({r["date"] for r in rows})
    groups_v1={};groups_v2={};folds=[]
    for idx,date in enumerate(dates):
        if idx<MIN_TRAIN_DATES:continue
        prior=[r for r in rows if r["date"]<date]
        upcoming=[r for r in rows if r["date"]==date]
        if len(prior)<MIN_TRAIN_STARTERS or len(upcoming)<6:continue
        if not all(r["date"]<date for r in prior):
            raise AssertionError("Detected temporal training leakage")
        labels=np.asarray([r["winner"] for r in prior],dtype="int32")
        left=estimator()
        right=estimator()
        left.fit(enriched_matrix(prior),labels)
        right.fit(enhanced_matrix(prior),labels)
        lprobs=left.predict_proba(enriched_matrix(upcoming))[:,1]
        rprobs=right.predict_proba(enhanced_matrix(upcoming))[:,1]
        day_a={};day_b={}
        for row,a,b in zip(upcoming,lprobs,rprobs):
            day_a.setdefault(row["raceId"],[]).append({**row,"pred":float(a)})
            day_b.setdefault(row["raceId"],[]).append({**row,"pred":float(b)})
        groups_v1.update(day_a);groups_v2.update(day_b)
        folds.append({"date":date,"trainingStarts":len(prior),"testedRaces":len(day_a)})
    if len(folds)<5 or len(groups_v1)<30:
        raise RuntimeError("Too little history for an honest feature comparison")
    matched=clean_paired(groups_v1)
    m_ids=set(matched)
    paired_a={id:groups_v1[id] for id in m_ids}
    paired_b={id:groups_v2[id] for id in m_ids}
    result={
        "schemaVersion":1,"reportType":"EXPLORATORY_FIXED_FEATURE_ABLATION",
        "generatedAt":dt.datetime.now(dt.timezone.utc).isoformat(),
        "raceCount":doc["raceCount"],"sourceStarts":doc["starterCount"],
        "evaluatedDates":len(folds),"evaluatedRaces":len(groups_v1),
        "comparisonPolicy":"Same dates, same training size, same XGBoost hyperparameters, strict time order. No model selection using the held-out results.",
        "newFeatureNames":list(FEATURE_NAMES),
        "featureCaveat":"Past-race prize and form are only indirect class proxies, NOT measured opponent strength. Per-track ability and verified early speed still unavailable.",
        "baselineAll":evaluate(groups_v1,"pred"),
        "candidateAll":evaluate(groups_v2,"pred"),
        "pairedRaceCount":len(paired_a),
        "baselinePaired":evaluate(paired_a,"pred"),
        "candidatePaired":evaluate(paired_b,"pred"),
        "atgFinalPoolPaired":evaluate(paired_a,"marketFinalPct",market=True),
        "dataCaveat":"Paired ATG benchmark is retrospective FINAL pool, and only for full-result races. Small selected sample; no proven betting profitability.",
        "folds":folds,
    }
    return result


def run():
    data=json.loads(SOURCE.read_text(encoding="utf8"))
    result=evaluate_trial(data)
    current=json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {}
    cmp=lambda x:{k:v for k,v in x.items() if k!="generatedAt"}
    if cmp(current)==cmp(result):
        print("No changes in feature trial.");return 0
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("FEATURE_TRIAL",result["evaluatedRaces"],"races; baseline",result["baselineAll"],
          "candidate",result["candidateAll"],flush=True)
    return 0


if __name__=="__main__":
    try:
        sys.exit(run())
    except (ImportError,ValueError,RuntimeError,AssertionError) as e:
        print("Feature trial unready:",type(e).__name__,str(e),file=sys.stderr)
        sys.exit(1)
