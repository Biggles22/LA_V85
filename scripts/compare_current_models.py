"""Exploratory comparison. Historical final markets are NOT prestart validation."""
import sys, pathlib, json, gzip, datetime as dt, math, hashlib, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'.model-deps'))
import numpy as np
from scripts.data_quality import load_training_data
from scripts.rank_current_catboost import estimator, matrix
from scripts.historical_pilot import features_from_history
from scripts.train_historical_pilot import evaluate
from scripts.update_current_round import normalize, TZ
NOW=dt.datetime.now(dt.timezone.utc)
CONFIG=json.loads((ROOT/'rounds.json').read_text(encoding='utf8'))
ROUND=next(r for r in CONFIG['rounds'] if r['id']==CONFIG['current'])
OUT=ROOT/'research/comparison'/ROUND['date']/NOW.strftime('%Y%m%dT%H%M%SZ')
WORK=OUT/'raw'; WORK.mkdir(parents=True,exist_ok=False)
BASE='https://www.atg.se/services/racinginfo/v1/api'
def fetch(path):
    with urllib.request.urlopen(urllib.request.Request(BASE+path,headers={'User-Agent':'LA_V85/research-comparison','Accept':'application/json'}),timeout=40) as r:return json.load(r)
def equipment(h):
    horse=h.get('horse',{}); shoes=horse.get('shoes',{}); sulky=horse.get('sulky',{})
    def flag(v):return float(v) if type(v) is bool else None
    return {'age':horse.get('age'),'front_shoe':flag(shoes.get('front',{}).get('hasShoe')) if shoes.get('reported') else None,
      'back_shoe':flag(shoes.get('back',{}).get('hasShoe')) if shoes.get('reported') else None,
      'front_changed':flag(shoes.get('front',{}).get('changed')) if shoes.get('reported') else None,
      'back_changed':flag(shoes.get('back',{}).get('changed')) if shoes.get('reported') else None,
      'american':float(sulky.get('type',{}).get('code')=='AM') if sulky.get('reported') else None,
      'sulky_changed':flag(sulky.get('type',{}).get('changed')) if sulky.get('reported') else None}
EXTRA=['marketPct','logOdds','inverseOdds','oddsFieldShare','marketRank','oddsRank','age','front_shoe','back_shoe','front_changed','back_changed','american','sulky_changed']
def augmented(rows,omit_odds=False):
    groups=defaultdict(list)
    for r in rows:groups[r['raceId']].append(r)
    xx=[]
    for r in rows:
        peers=groups[r['raceId']]; odds=r.get('odds'); pct=r.get('marketPct')
        valid=[p['odds'] for p in peers if p.get('odds') and p['odds']>0]
        extras={**r.get('equipment',{}),'marketPct':pct,
          'logOdds':math.log(odds) if odds and odds>0 else None,'inverseOdds':1/odds if odds and odds>0 else None,
          'oddsFieldShare':(1/odds)/sum(1/o for o in valid) if odds and odds>0 and len(valid)==len(peers) else None,
          'marketRank':1+sum(p.get('marketPct',-1)>pct for p in peers) if pct is not None else None,
          'oddsRank':1+sum(o<odds for o in valid) if odds and odds>0 else None}
        xx.append([float('nan') if extras.get(k) is None or (omit_odds and k in ['logOdds','inverseOdds','oddsFieldShare','oddsRank']) else float(extras[k]) for k in EXTRA])
    return np.concatenate([matrix(rows),np.asarray(xx)],axis=1)
def main():
    doc=load_training_data(); rows=doc['rows']; racecache={}
    needed={r['raceId'] for r in rows}
    for p in (ROOT/'research/raw-history').glob('*.json*'):
        with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:raw=json.load(f)
        payload=raw.get('payload',{}); rid=payload.get('id')
        if rid in needed and '/extended' in raw.get('sourceUrl',''):racecache[rid]=payload
    for r in rows:
        raw=racecache.get(r['raceId'],{}); h=next((h for h in raw.get('starts',[]) if h['number']==r['number']),{})
        r['odds']=(h.get('result') or {}).get('finalOdds'); r['marketPct']=r.get('marketFinalPct');r['equipment']=equipment(h)
    groups=defaultdict(list)
    for r in rows:groups[r['raceId']].append(r)
    good={rid for rid,rs in groups.items() if all(r.get('marketPct') is not None and r.get('odds') and r['odds']>0 for r in rs) and 95<=sum(r['marketPct'] for r in rs)<=105}
    rows=[r for r in rows if r['raceId'] in good]
    train=[r for r in rows if r['date']<'2026-08-01']; test=[r for r in rows if r['date']>='2026-08-01' and r.get('gameType')=='V85']
    assert train and test and max(r['date'] for r in train)<min(r['date'] for r in test)
    metrics={}
    for key,fn in [('history',matrix),('expanded_final_market',augmented)]:
        model=estimator(); model.fit(fn(train),[r['winner'] for r in train]); pred=model.predict_proba(fn(test))[:,1]
        g=defaultdict(list)
        for r,p in zip(test,pred):g[r['raceId']].append({**r,'score':float(p)})
        metrics[key]=evaluate(g,'score')
    print('HOLDOUT',json.dumps(metrics),flush=True)
    cfg=json.loads((ROOT/'rounds.json').read_text(encoding='utf8')); info=next(r for r in cfg['rounds'] if r['id']==cfg['current'])
    saved=json.loads((ROOT/info['data']).read_text(encoding='utf8')); game=fetch('/games/'+saved['gameId'])
    assert game['id']==saved['gameId'] and len(game['races'])==8
    assert NOW < dt.datetime.fromisoformat(saved['startTime']) and all(r.get('status')!='results' for r in game['races'])
    # The market can change during fitting. Identify the actual captured game,
    # rather than assigning the older input snapshot ID to newer odds/shares.
    captured_at = dt.datetime.now(dt.timezone.utc)
    captured = normalize(game, info, captured_at.astimezone(TZ))
    (OUT/'data.json').write_text(json.dumps(captured,ensure_ascii=False,indent=2),encoding='utf8')
    stamp=NOW.strftime('%Y%m%dT%H%M%SZ');(WORK/(stamp+'_game.json')).write_text(json.dumps(game,ensure_ascii=False),encoding='utf8')
    extended=list(ThreadPoolExecutor(max_workers=3).map(lambda r:fetch('/races/'+r['id']+'/extended'),game['races']))
    current=[]; pool_info=[]
    for leg,(race,ext) in enumerate(zip(game['races'],extended),1):
        assert race['id']==ext['id']; (WORK/(stamp+'_'+race['id']+'.json')).write_text(json.dumps(ext,ensure_ascii=False),encoding='utf8')
        active=[h for h in race['starts'] if not h.get('scratched')]; exth={h['number']:h for h in ext['starts'] if not h.get('scratched')};assert set(exth)=={h['number'] for h in active}
        pool_info.append({'leg':leg,'pools':race.get('pools',{}),'name':race.get('name'),'distance':race.get('distance'),'startMethod':race.get('startMethod')})
        for h in active:
            o=(h.get('pools',{}).get('vinnare') or {}).get('odds'); p=(h.get('pools',{}).get('V85') or {}).get('betDistribution')
            horse=h['horse']; eh=exth[h['number']]
            current.append({'raceId':race['id'],'leg':leg,'number':h['number'],'name':horse['name'],
              'prestartFeatures':features_from_history(eh,ext,dt.date.fromisoformat(saved['date']),len(active)),
              'odds':o/100 if isinstance(o,(int,float)) and 0<o<9999 else None,'oddsCapped':o==9999,
              'marketPct':p/100 if isinstance(p,(int,float)) else None,'equipment':equipment(h),'post':h.get('postPosition'),
              'driver':h.get('driver',{}),'trainer':horse.get('trainer',{}),'history':horse.get('results',{}).get('records',[]) or eh.get('horse',{}).get('results',{}).get('records',[])})
    full=doc['rows']; base=estimator();base.fit(matrix(full),[r['winner'] for r in full])
    exp=estimator();exp.fit(augmented(rows),[r['winner'] for r in rows])
    for key,model,fn in [('historyScore',base,matrix),('expandedScore',exp,augmented),('expandedWithoutOddsScore',exp,lambda rs:augmented(rs,True))]:
        for r,p in zip(current,model.predict_proba(fn(current))[:,1]):r[key]=float(p)
    races=[]
    for leg in range(1,9):
        rs=[r for r in current if r['leg']==leg];rankings={}
        for key in ['historyScore','expandedScore','expandedWithoutOddsScore']:
            ordered=sorted(rs,key=lambda r:(-r[key],r['number']));rankings[key]=[r['number'] for r in ordered[:3]]
            for rank,r in enumerate(ordered,1):r[key+'Rank']=rank
        races.append({'leg':leg,'top3':rankings,'horses':rs})
    report={'kind':'EXPERIMENTAL_FINAL_MARKET_TRAINED_COMPARISON_NOT_PRESTART_VALIDATION','roundId':saved['roundId'],'gameId':saved['gameId'],'inputSnapshotId':saved['snapshotId'],'snapshotId':captured['snapshotId'],'runStartedAt':NOW.isoformat(),'observedAt':captured_at.isoformat(),
      'sourceAt':game.get('pools',{}).get('V85',{}).get('timestamp'),'sourceUrl':BASE+'/games/'+game['id'],
      'limitations':['Expanded model is trained on final market odds/shares and recorded equipment; historical timing of equipment is not independently verified.',
      'Current prestart markets are incomplete and do not match historical final markets. No calibration or >50% win-probability claims.',
      'Masking odds is a sensitivity check of the SAME model, not a separately trained third model. No automatic publishing or model replacement.'],
      'training':{'historicalSource':'research/historical_expanded_2024_2026.json','historicalSourceSha256':hashlib.sha256((ROOT/'research/historical_expanded_2024_2026.json').read_bytes()).hexdigest(),'historyStarts':len(full),'expandedStarts':len(rows),'expandedRaces':len(good),'testFrom':'2026-08-01','holdoutMetrics':metrics},
      'extraFeatures':EXTRA,'raceInfo':pool_info,'races':races}
    OUT.mkdir(exist_ok=True);(OUT/'models.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('CURRENT',json.dumps([{'leg':r['leg'],'top3':r['top3'],'horses':[{'n':h['number'],'name':h['name'],'pct':h['marketPct'],'odds':h['odds'],'equip':h['equipment'],'base':h['historyScoreRank'],'expanded':h['expandedScoreRank'],'form':h['prestartFeatures']} for h in r['horses']]} for r in races],ensure_ascii=False),flush=True)
if __name__=='__main__':main()
