/* Bind model rankings to the exact verified startlist snapshot. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.V85Model=api;})(typeof globalThis!=='undefined'?globalThis:this,()=>{
'use strict';
function validate(model,data){
  if(!model||data.status!=='verified'||model.kind!=='CATBOOST_PRESTART_RANKING'||model.roundId!==data.roundId||model.gameId!==data.gameId||model.snapshotId!==data.snapshotId)return null;
  const made=Date.parse(model.generatedAt),start=Date.parse(data.startTime);
  if(!Number.isFinite(made)||!Number.isFinite(start)||made>=start||made>Date.now()+300000||!model.training||model.training.until>=data.date)return null;
  if(!Array.isArray(model.races)||model.races.length!==8||new Set(model.races.map(r=>r.leg)).size!==8)return null;
  for(const race of data.races){
    const ranked=model.races.find(r=>r.leg===race.leg),active=race.starts.filter(h=>!h.scratched);
    if(!ranked||ranked.raceId!==race.raceId||!Array.isArray(ranked.horses)||ranked.horses.length!==active.length||new Set(ranked.horses.map(h=>h.number)).size!==active.length)return null;
    if(!ranked.horses.every((h,i)=>h.rank===i+1&&Number.isFinite(h.modelScore)&&h.modelScore>=0&&h.modelScore<=1&&(!i||ranked.horses[i-1].modelScore>=h.modelScore)&&active.some(a=>a.number===h.number&&a.name===h.name)))return null;
    if(!Array.isArray(ranked.top3)||ranked.top3.length!==3||!ranked.top3.every((h,i)=>h.number===ranked.horses[i].number&&h.name===ranked.horses[i].name))return null;
  }
  return model;
}
return {validate};
});
