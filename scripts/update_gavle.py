#!/usr/bin/env python3
"""Pre-start, verified ATG V85 snapshot for Gävle 2026-10-17.

Maintains old market data and personal user selections (stored only in browser).
Never treats odds=9999 as a numerical exact price. Does not fetch after first start.
"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import copy
import json
import sys
import urllib.request
import time

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("Europe/Stockholm")
START = datetime(2026, 10, 17, 15, 0, tzinfo=TZ)
URL = "https://www.atg.se/services/racinginfo/v1/api/games/V85_2026-10-17_16_5"
GAME_ID = "V85_2026-10-17_16_5"

def read(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def write_if_changed(name: str, value) -> None:
    path = ROOT / name
    new = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != new:
        path.write_text(new, encoding="utf-8")
        print("Updated", name)

def norm(name):
    return " ".join(str(name).casefold().split())

def local_stamp(text):
    # ATG pool timestamp is Swedish local clock-time without offset.
    return datetime.fromisoformat(text.replace(" ", "T")).replace(tzinfo=TZ).isoformat()

def main():
    now = datetime.now(TZ)
    if now >= START or now.date() != START.date():
        print("No update: outside pre-start period", now.isoformat())
        return 0

    req = urllib.request.Request(
        URL,
        headers={"User-Agent":"Mozilla/5.0 (compatible; LA-V85-analys/1.0)",
                 "Accept":"application/json"})
    last_error = None
    for trial in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
            game = json.loads(body.decode("utf-8"))
            break
        except Exception as e:
            last_error = e
            if trial != 2: time.sleep(3*(trial+1))
    else:
        raise RuntimeError("ATG could not be reached: "+str(last_error))
    if game.get("id") != GAME_ID or game.get("status") not in ("bettable","open"):
        raise RuntimeError("Game or status unexpected. No data was saved.")

    market = read("odds.json")
    start = read("startlist.json")
    analysis = read("gavle-analysis.json")
    pool = game["pools"]["V85"]
    if pool.get("betType") != "V85":
        raise RuntimeError("Wrong market")
    atg_stamp = local_stamp(pool["timestamp"])
    if datetime.fromisoformat(atg_stamp) >= START:
        raise RuntimeError("Source timestamp is after start")
    if datetime.fromisoformat(atg_stamp) > now:
        raise RuntimeError("Source timestamp is in the future")
    if market.get("gameId") != GAME_ID or start.get("gameId") != GAME_ID:
        raise RuntimeError("Local game ID mismatch")
    latest_source=datetime.fromisoformat(market["updatedAt"])
    current_source=datetime.fromisoformat(atg_stamp)
    metadata_complete=all("trainer" in h and "homeTrackGavle" in h and "sameTrainerDriver" in h for r in start["races"] for h in r["starts"])
    if latest_source > current_source or (latest_source == current_source and metadata_complete):
        print("Already recorded and metadata complete, or older ATG timestamp", atg_stamp)
        return 0

    official_races = game.get("races") or []
    if len(official_races) != 8 or len(start.get("races",[])) != 8:
        raise RuntimeError("Wrong number of races")
    fresh_pct, fresh_odds, fresh_trends = {}, {}, {}
    updates = []
    scratch_names = []
    for i, (our_race, atg_race) in enumerate(zip(start["races"],official_races)):
        if atg_race.get("number") != our_race.get("number") or len(atg_race.get("starts", [])) != len(our_race["starts"]):
            raise RuntimeError("Race alignment failed in leg "+str(i+1))
        by_number = {h["number"]:h for h in atg_race["starts"]}
        if len(by_number)!=len(our_race["starts"]):
            raise RuntimeError("Duplicate number in official source")
        for horse in our_race["starts"]:
            k=horse["key"]
            source=by_number.get(horse["number"])
            if not source or norm(source["horse"]["name"]) != norm(horse["name"]):
                raise RuntimeError("Horse identity mismatch: "+k+" "+horse["name"])
            pools=source.get("pools",{})
            wp=pools.get("vinnare",{}).get("odds")
            share=pools.get("V85",{}).get("betDistribution")
            if share is None:
                raise RuntimeError("Missing V85 bet distribution for "+k)
            scratched=bool(source.get("scratched",False))
            fresh_pct[k]=round(float(share)/100,2)
            fresh_odds[k]=None if scratched or wp is None or wp == 0 else round(float(wp)/100,2)
            val=pools.get("V85",{}).get("trend")
            fresh_trends[k]=None if val is None else round(float(val)*100,4)
            trainer=source["horse"].get("trainer") or {}
            driver=source.get("driver") or {}
            trainer_name=" ".join(filter(None,[trainer.get("firstName"),trainer.get("lastName")]))
            driver_name=" ".join(filter(None,[driver.get("firstName"),driver.get("lastName")]))
            # Use ID equality; never compare driver's home track to the race venue.
            same=(trainer.get("id")==driver.get("id") if trainer.get("id") and driver.get("id") else None)
            trainer_track=trainer.get("homeTrack") or {}
            home=(trainer_track.get("id")==16 if trainer_track.get("id") is not None else None)
            updates.append((k, scratched, trainer_name, driver_name, trainer.get("id"),
                            driver.get("id"),trainer_track.get("name"),home,same))
            if scratched: scratch_names.append(k+" "+horse["name"])
    if len(fresh_pct)!=98:
        raise RuntimeError("Expected 98 horses")

    # Do not mutate any local data until all 98 horses pass identity checks.
    market=copy.deepcopy(market)
    start=copy.deepcopy(start)
    analysis=copy.deepcopy(analysis)
    prev_pct=market.get("percentages") or {}
    prev_odds=market.get("winnerOdds") or {}
    market.setdefault("percentagesHistory",{})
    market.setdefault("winnerOddsHistory",{})
    if market.get("updatedAt"):
        market["percentagesHistory"].setdefault(market["updatedAt"],prev_pct)
        market["winnerOddsHistory"].setdefault(market["updatedAt"],prev_odds)
    market["percentagesHistory"][atg_stamp]=fresh_pct
    market["winnerOddsHistory"][atg_stamp]=fresh_odds
    market["percentages"]=fresh_pct
    market["winnerOdds"]=fresh_odds
    market["trends"]=fresh_trends
    market["updatedAt"]=atg_stamp
    market["sourceUrl"]=URL
    market["oddsSourceUrl"]=URL
    market["oddsSourceLabel"]="ATG officiellt racinginfo-API"
    market["sourceLabel"]="ATG"
    market["status"]="official-prestart-snapshot"
    market["dataQuality"]={
        "total":98,"active":98-len(scratch_names),"scratched":len(scratch_names),
        "numericOddsBelowCeiling":sum(v is not None and v < 99.99 for v in fresh_odds.values()),
        "displayCappedOdds":sum(v is not None and v >=99.99 for v in fresh_odds.values()),
        "missingOdds":sum(v is None for v in fresh_odds.values()),
        "ceiling":99.99,
        "warning":"99,99 är ett censurerat visningstak, aldrig ett exakt vinnarodds."
    }
    old_stamp=market.get("capturedAt")
    market["capturedAt"]=now.isoformat()
    market["oddsSourceRetrievedAt"]=now.isoformat()
    horse_by_key={h["key"]:h for r in start["races"] for h in r["starts"]}
    for key, scratched, trainer_name, driver_name, tid, did, trk, home, same in updates:
        horse=horse_by_key[key]
        horse["scratched"]=scratched
        horse["trainer"]={"name":trainer_name,"id":tid,"homeTrack":trk,
                          "homeTrackId":16 if home else (None if home is None else -1)}
        horse["driver"]={"name":driver_name,"id":did}
        horse["sameTrainerDriver"]=same
        horse["trainerHome"]=trk
        horse["homeTrackGavle"]=home
    start["lastMarketCheck"]=atg_stamp
    start["scratchedCount"]=len(scratch_names)
    start["activeCount"]=98-len(scratch_names)
    start["officialSourceUrl"]=URL
    start["metadataVerifiedAt"]=atg_stamp

    amt=pool.get("turnover")
    if not isinstance(amt,(int,float)) or amt<0: raise RuntimeError("Invalid ATG turnover")
    turnover_sek=round(amt/100,2)
    turnover_file=ROOT/"turnover.json"
    turnover=(read("turnover.json") if turnover_file.exists() else
             {"round":"2026-10-17","gameId":GAME_ID,"track":"Gävle","history":[]})
    turnover["sourceUrl"]=URL
    turnover["sourceLabel"]="ATG V85-pool"
    turnover["updatedAt"]=atg_stamp
    turnover["latestTurnoverSEK"]=turnover_sek
    turnover["systemCount"]=pool.get("systemCount")
    if not any(e.get("sourceAt")==atg_stamp for e in turnover["history"]):
        turnover["history"].append({"sourceAt":atg_stamp,"turnoverSEK":turnover_sek,"systemCount":pool.get("systemCount")})
    turnover["history"].sort(key=lambda h:h["sourceAt"])

    # Preserve the editorial record and source. Add factual dynamic notes; never pretend they are expert quotes.
    for k,com in analysis.get("commentary",{}).items():
        if k not in fresh_pct: continue
        delta=round(fresh_pct[k]-prev_pct.get(k,fresh_pct[k]),2)
        price=fresh_odds[k]
        suffix=("ej exakt (≥99,99)" if price is not None and price>=99.99 else
                "saknas" if price is None else f"{price:.2f}")
        com["latestMarketNote"]=f"ATG {atg_stamp}: V85 {fresh_pct[k]:.2f} % ({delta:+.2f} procentenheter), vinnarodds {suffix}."
        com["marketUpdateAt"]=atg_stamp
        com["percentage"]=fresh_pct[k]
        com["odds"]=price
        com["scratched"]=any(s.startswith(k+" ") for s in scratch_names)
    for p in analysis.get("picks",[]):
        k=p["key"]
        if k not in fresh_pct: continue
        p["pct"]=fresh_pct[k]
        p["odds"]=fresh_odds[k]
        if any(s.startswith(k+" ") for s in scratch_names):
            p["marketWarning"]="STRUKEN – välj inte"
        elif p["role"]=="Huvudskräll" and fresh_pct[k]>20:
            p["marketWarning"]="Nu över 20 % streck – ompröva skrällvärdet"
        elif fresh_pct[k]-prev_pct.get(k,fresh_pct[k]) >= 5:
            p["marketWarning"]="Streckningen har ökat minst 5 procentenheter sedan senaste noteringen"
        else:
            p.pop("marketWarning",None)
    analysis["dataSnapshot"]=atg_stamp
    analysis["lastReviewedAt"]=atg_stamp
    analysis["latestAutomaticCheck"]="Marknad/strykning och metadata kontrollerade från ATG. Äldre expertomdömen oförändrade."

    write_if_changed("startlist.json",start)
    write_if_changed("odds.json",market)
    write_if_changed("turnover.json",turnover)
    write_if_changed("gavle-analysis.json",analysis)
    print("ATG snapshot:",atg_stamp,"turnover:",turnover_sek,"SEK",
          "scratches:",scratch_names, "same_driver_and_trainer:",
          sum(same is True for *_,home,same in updates), "trainer_home_gavle:",
          sum(home is True for *_,home,same in updates))
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("No files written because validation/fetch failed:",exc,file=sys.stderr)
        sys.exit(1)
