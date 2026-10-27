#!/usr/bin/env python3
"""Freeze independent Bjerke V85 model forecasts with SAME observed prestart ATG market.

EXPERIMENT ONLY, no AI spik/skrall recommendations, not calibrated win odds.
Designed for GitHub Actions on 2026-10-30 18:00 and 2026-10-31 14:15 CET.
No backdating: freeze timestamp and race cards observed live, BEFORE start.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import pathlib
import sys
import urllib.request
from zoneinfo import ZoneInfo

try:
    from scripts.historical_pilot import features_from_history
    from scripts.walkforward_evaluation import enriched_matrix
    from scripts.feature_trial import estimator
    from scripts.historical_opponent_test import opponent_matrix,evidence_index
    from scripts.capture_prestart_market import checked_snapshot,ID,CUTOFF
    from scripts.opponent_coverage import fetch_card,assess_card
except ModuleNotFoundError:
    from historical_pilot import features_from_history
    from walkforward_evaluation import enriched_matrix
    from feature_trial import estimator
    from historical_opponent_test import opponent_matrix,evidence_index
    from capture_prestart_market import checked_snapshot,ID,CUTOFF
    from opponent_coverage import fetch_card,assess_card

ROOT=pathlib.Path(__file__).resolve().parents[1]
HIST=ROOT/"research/historical_pilot_2026.json"
OPPONENT_HIST=ROOT/"research/historical_opponent_asof_2026.json"
OLD_CURRENT=ROOT/"research/opponent_coverage_2026.json"
DEST=ROOT/"research/frozen/2026-10-31"
DATE=dt.date(2026,10,31)
TZ=ZoneInfo("Europe/Stockholm")
BASE="https://www.atg.se/services/racinginfo/v1/api"
TIMES={
    "preview":(dt.datetime(2026,10,27,10,0,tzinfo=TZ),
               dt.datetime(2026,10,30,18,0,tzinfo=TZ)),
    "friday":(dt.datetime(2026,10,30,18,0,tzinfo=TZ),
              dt.datetime(2026,10,31,0,0,tzinfo=TZ)),
    "saturday":(dt.datetime(2026,10,31,14,15,tzinfo=TZ),
                CUTOFF)
}
MIN_MARKET_FRESHNESS_HOURS=6
MIN_MATCHED_OPPONENTS=5


def get_json(url):
    request=urllib.request.Request(url,headers={
        "Accept":"application/json",
        "User-Agent":"LA_V85/frozen-research-2026-10-31"})
    with urllib.request.urlopen(request,timeout=28) as response:
        value=json.load(response)
    if not isinstance(value,dict):
        raise ValueError("Source did not return an object")
    return value


def in_slot(now,slot):
    if now.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    start,stop=TIMES[slot]
    local=now.astimezone(TZ)
    return start<=local<stop and local<CUTOFF


def current_rows(game,extended_by_race,market):
    """Identical 8 races and full active field, matched by number AND name."""
    if market.get("gameId")!=ID or len(market.get("races",[]))!=8:
        raise ValueError("Incorrect market meeting")
    byid={r.get("id"):r for r in game["races"]}
    output=[]
    for market_race in market["races"]:
        rid=market_race.get("raceId")
        g_race=byid.get(rid)
        e_race=extended_by_race.get(rid)
        if not isinstance(rid,str) or not g_race or not isinstance(e_race,dict) or e_race.get("id")!=rid:
            raise ValueError("Missing identical game/extended race cards")
        all_starts=e_race.get("starts")
        if not isinstance(all_starts,list):
            raise ValueError("Extended race lacks starters")
        indexed={}
        for x in all_starts:
            if isinstance(x,dict) and type(x.get("number")) is int:
                if x["number"] in indexed:
                    raise ValueError("Duplicate extended race number")
                indexed[x["number"]]=x
        active=[s for s in market_race["starts"] if not s["scratched"]]
        if len(active)<6:
            raise ValueError("Too few verified active starters")
        for current in active:
            number=current["number"]
            st=indexed.get(number)
            horse=st.get("horse") if isinstance(st,dict) else None
            if not isinstance(horse,dict) or horse.get("name")!=current["horse"]:
                raise ValueError(f"Name/number mismatch in {rid}: {number}")
            if st.get("scratched") is True:
                raise ValueError("Race snapshot scratched mismatch")
            features=features_from_history(st,e_race,DATE,len(active))
            if features.get("distance") is None or features.get("post") is None:
                raise ValueError("Missing key prestart distance/post feature")
            if not 1<=features["post"]<=20:
                raise ValueError("Invalid post number")
            output.append({"raceId":rid,"date":DATE.isoformat(),
                          "leg":market_race["leg"],"number":number,
                          "horse":current["horse"],"prestartFeatures":features,
                          "marketPct":current["pct"]})
    if len(output)<70 or len({(x["raceId"],x["number"]) for x in output})!=len(output):
        raise ValueError("Truncated current field")
    return output


def current_opponent_values(rows,coverage):
    if coverage.get("gameId")!=ID:
        raise ValueError("Wrong opponent coverage meeting")
    ref={(h["leg"],h["number"],h["name"]):h for h in coverage.get("horses",[])}
    indexed={}
    for r in rows:
        reference=ref.get((r["leg"],r["number"],r["horse"]))
        value=reference.get("opponentFormMean") if reference else None
        if type(value) in (float,int) and 0<=value<=1:
            indexed[(r["raceId"],r["number"],r["horse"])]={
                "opponentForm":float(value)}
    return indexed


def race_distribution(rows,scores):
    """Normalize raw classifier scores within each leg: NOT calibrated probabilities."""
    grouped={}
    for row,pred in zip(rows,scores):
        if not math.isfinite(float(pred)) or pred<0:
            raise ValueError("Invalid classifier output")
        grouped.setdefault(row["leg"],[]).append((row,float(pred)))
    if len(grouped)!=8:
        raise ValueError("Incomplete model race coverage")
    out={}
    for leg,records in grouped.items():
        total=sum(score for _,score in records)
        if total<=0:
            raise ValueError("All raw classifier scores are zero")
        for row,score in records:
            out[(leg,row["number"])]=round(100*score/total,4)
    return out


def compute_predictions(rows,history,opponent_history,coverage):
    import numpy as np
    older=[r for r in history["rows"] if r["date"]<DATE.isoformat()]
    if len(older)<1000 or len({r["raceId"] for r in older})<80:
        raise ValueError("Historical training too small")
    if any(r["date"]>=DATE.isoformat() for r in older):
        raise AssertionError("Future records in training")
    if opponent_history.get("sourceRaceCount")!=history.get("raceCount"):
        raise ValueError("Historical rival evidence not matched to training corpus")
    labels=np.array([x["winner"] for x in older],dtype="int32")
    if len(set(labels))!=2:
        raise ValueError("Training data has no valid winning/losing classes")
    model_a=estimator()
    model_b=estimator()
    model_a.fit(enriched_matrix(older),labels)
    model_b.fit(opponent_matrix(older,evidence_index(opponent_history)),labels)
    raw_a=model_a.predict_proba(enriched_matrix(rows))[:,1]
    raw_b=model_b.predict_proba(opponent_matrix(rows,current_opponent_values(rows,coverage)))[:,1]
    a=race_distribution(rows,raw_a)
    b=race_distribution(rows,raw_b)
    output=[]
    for leg in range(1,9):
        runners=[r for r in rows if r["leg"]==leg]
        active=[]
        for r in runners:
            key=(leg,r["number"])
            active.append({
                "number":r["number"],"horse":r["horse"],
                "marketPct":r["marketPct"],
                "baseModelShare":a[key],
                "previousOpponentsModelShare":b[key],
                "hasOpponentEvidence":(r["raceId"],r["number"],r["horse"]) in
                   current_opponent_values(rows,coverage),
                "prestartFeatures":r["prestartFeatures"]
            })
        if len(active)<6:raise ValueError("Missing active starters in prediction")
        ordered_a=sorted(active,key=lambda x:x["baseModelShare"],reverse=True)
        ordered_b=sorted(active,key=lambda x:x["previousOpponentsModelShare"],reverse=True)
        ordered_m=sorted(active,key=lambda x:x["marketPct"],reverse=True)
        output.append({"leg":leg,"raceId":runners[0]["raceId"],
                       "runners":active,
                       "baseTop3":[h["number"] for h in ordered_a[:3]],
                       "opponentTop3":[h["number"] for h in ordered_b[:3]],
                       "marketTop3":[h["number"] for h in ordered_m[:3]],
                       "opponentDataCoverage":sum(h["hasOpponentEvidence"] for h in active)})
    return output


def build(slot,now=None,game=None,extended=None,historical=None,opponent_historical=None,coverage=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if not in_slot(now,slot):
        raise ValueError("Forecast not within allowed prestart observation slot")
    game=game or get_json(BASE+"/games/"+ID)
    market=checked_snapshot(game,now)  # Strict original API timestamp validation.
    source=dt.datetime.fromisoformat(market["sourceAt"])
    if (now.astimezone(TZ)-source).total_seconds()>MIN_MARKET_FRESHNESS_HOURS*3600:
        raise ValueError("ATG market source older than six hours")
    if extended is None:
        extended={r["raceId"]:get_json(BASE+"/races/"+r["raceId"]+"/extended")
                  for r in market["races"]}
    rows=current_rows(game,extended,market)
    historical=historical or json.loads(HIST.read_text(encoding="utf8"))
    opponent_historical=opponent_historical or json.loads(OPPONENT_HIST.read_text(encoding="utf8"))
    coverage=coverage or json.loads(OLD_CURRENT.read_text(encoding="utf8"))
    report=compute_predictions(rows,historical,opponent_historical,coverage)
    observed=now.astimezone(TZ).isoformat()
    return {
        "schemaVersion":1,"kind":"FROZEN_PROSPECTIVE_RESEARCH_NOT_BETTING_ADVICE",
        "gameId":ID,"date":DATE.isoformat(),"slot":slot,
        "frozenAt":observed,"marketSourceAt":market["sourceAt"],
        "marketObservedAt":market["observedAt"],"marketLagSeconds":market["lagSeconds"],
        "marketSource":market["source"],
        "trainingRaces":len({x["raceId"] for x in historical["rows"] if x["date"]<DATE.isoformat()}),
        "trainingStarts":sum(x["date"]<DATE.isoformat() for x in historical["rows"]),
        "dataProvenance":"Both XGBoost models were trained on historic starts strictly before 2026-10-31. All Bjerke inputs were obtained live BEFORE start; both share identical horse list and ATG source time.",
        "statisticalWarning":"Percentages are within-race normalized UNCALIBRATED classifier scores, NOT estimated probabilities, spik odds, or predicted return.",
        "researchDisclaimer":"No recommendation to bet based on these forecasts; model scores have underperformed ATG top-three ranking in historical comparison.",
        "races":report
    }


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--slot",choices=tuple(TIMES),required=True)
    args=parser.parse_args(argv)
    now=dt.datetime.now(dt.timezone.utc)
    if not in_slot(now,args.slot):
        print("Outside protected prospective window, no snapshot created.")
        return 0
    target=DEST/(args.slot+".json")
    if target.exists():
        print("Immutable forecast already published, will not overwrite",target)
        return 0
    report=build(args.slot,now)
    DEST.mkdir(parents=True,exist_ok=True)
    # Atomic local write; existing committed file must never be replaced.
    with target.open("x",encoding="utf8") as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    print("FROZEN",args.slot,report["frozenAt"],
          report["marketSourceAt"],report["trainingStarts"],
          "training starters",sum(len(r["runners"]) for r in report["races"]),
          "current runners",flush=True)
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError,AssertionError) as error:
        print("FREEZE REFUSED:",type(error).__name__,str(error),file=sys.stderr)
        sys.exit(1)
