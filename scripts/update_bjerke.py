#!/usr/bin/env python3
"""Capture and validate the current Bjerke V85 snapshot from ATG."""
import json,urllib.request,datetime,pathlib,sys
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
ID="V85_2026-10-31_78_5"
URL="https://www.atg.se/services/racinginfo/v1/api/games/"+ID
DEST=ROOT/"bjerke-20261031.json"
tz=ZoneInfo("Europe/Stockholm")
def person(p):
    return " ".join(x for x in [p.get("firstName"),p.get("lastName")] if x)
def market_recommendations(races,source_at):
    """Create transparent market signals; these are not form-based betting advice."""
    leaders=[]
    outsiders=[]
    for race in races:
        active=[h for h in race["starts"] if not h["scratched"] and isinstance(h["pct"],(int,float))]
        if not active: continue
        leader=max(active,key=lambda h:h["pct"])
        leaders.append({"leg":race["leg"],"number":leader["number"],"name":leader["name"],
            "pct":leader["pct"],"trend":leader["trend"],"odds":leader["odds"],
            "level":"Stark marknadsfavorit" if leader["pct"]>=50 else "Spik att utreda",
            "reason":"Avdelningens mest streckade häst i aktuell snapshot."})
        for horse in active:
            if 2<=horse["pct"]<=10 and isinstance(horse["trend"],(int,float)) and horse["trend"]>0:
                outsiders.append({"leg":race["leg"],"number":horse["number"],"name":horse["name"],
                    "pct":horse["pct"],"trend":horse["trend"],"odds":horse["odds"],
                    "level":"Stigande lågprocentare","reason":"2–10 procent och positiv strecktrend i aktuell snapshot."})
    leaders.sort(key=lambda x:x["pct"],reverse=True)
    outsiders.sort(key=lambda x:(x["trend"],-x["pct"]),reverse=True)
    return {"updatedAt":source_at,"method":"Automatiska marknadssignaler från V85-procent och trend; ingen formanalys.",
        "spikes":leaders[:3],"outsiders":outsiders[:5]}
def main():
    now=datetime.datetime.now(tz)
    if now>=datetime.datetime(2026,10,31,15,tzinfo=tz):
        print("Round started; do not overwrite historical snapshot");return
    req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as r: game=json.load(r)
    if game.get("id")!=ID: raise ValueError("Wrong game id")
    races=game.get("races",[])
    if len(races)!=8:raise ValueError("Expected 8 races")
    previous=json.loads(DEST.read_text()) if DEST.exists() else {}
    track=(races[0].get("track") or {}).get("name")
    if track != "Bjerke": raise ValueError("Wrong track: "+str(track))
    v85pool=game.get("pools",{}).get("V85",{})
    turnover=v85pool.get("turnover")
    turnover_sek=round(turnover/100,2) if isinstance(turnover,(int,float)) else None
    record={"gameId":ID,"track":track,"retrievedAt":now.isoformat(),"source":URL,
            "sourceAt":v85pool.get("timestamp"),"turnoverSEK":turnover_sek,
            "systemCount":v85pool.get("systemCount"),"races":[]}
    total=0
    for i,r in enumerate(races,1):
        entries=[]
        for s in r.get("starts",[]):
            horse=s.get("horse") or {}
            d=s.get("driver") or {}
            t=horse.get("trainer") or {}
            hp=t.get("homeTrack") or {}
            pool=s.get("pools") or {}
            pct=(pool.get("V85") or {}).get("betDistribution")
            odd=(pool.get("vinnare") or {}).get("odds")
            trend=(pool.get("V85") or {}).get("trend")
            if not horse.get("name") or not isinstance(s.get("number"),int):raise ValueError("Invalid start")
            entries.append({"number":s["number"],"name":horse["name"],"driver":person(d),
                "trainer":person(t),"trainerHome":hp.get("name") or None,
                "sameTrainerDriver": t.get("id")==d.get("id") if t.get("id") and d.get("id") else None,
                "pct":round(pct/100,2) if isinstance(pct,(int,float)) else None,
                "odds":round(odd/100,2) if isinstance(odd,(int,float)) and odd>0 and odd<9999 else None,
                "oddsCapped":odd==9999,"trend":round(trend*100,2) if isinstance(trend,(int,float)) else None,
                "scratched":bool(s.get("scratched")),"postPosition":s.get("postPosition"),
                "distance":s.get("distance")})
        if not entries:raise ValueError("Empty leg "+str(i))
        total+=len(entries)
        record["races"].append({"leg":i,"raceNumber":r.get("number"),"starts":entries})
    if total<90 or total>120:raise ValueError("Unexpected runner count "+str(total))
    record["recommendations"]=market_recommendations(record["races"],record["sourceAt"])
    if previous.get("sourceAt") and record["sourceAt"] and str(record["sourceAt"])<str(previous["sourceAt"]):
        print("Older snapshot; skipped");return
    if (previous.get("sourceAt")==record["sourceAt"] and previous.get("turnoverSEK")==record["turnoverSEK"]
            and previous.get("systemCount")==record["systemCount"] and previous.get("races")==record["races"]
            and previous.get("recommendations")==record["recommendations"]):
        print("No new ATG source data");return
    DEST.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    print("Updated",total,"horses",record["sourceAt"])
if __name__=="__main__":
    try:main()
    except Exception as e: print("Validation/fetch failed: "+str(e),file=sys.stderr);sys.exit(1)
