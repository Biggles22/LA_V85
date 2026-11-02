(async()=>{
  const target=document.getElementById('model-results');
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  try{
    const response=await fetch('../research/expanded_model_evaluation_2026.json',{cache:'no-store'});
    if(!response.ok)throw Error();
    const report=await response.json(),v=report.validation;
    if(v.scope!=='V85_ONLY'||report.training.sha256!==report.trainingDataQuality.sourceSha256)throw Error();
    const n=v.pairedModel.races,rows=[['XGBoost',v.pairedXGBoost],['CatBoost',v.pairedModel],['ATG:s slutstreck',v.retrospectiveFinalPool]];
    if(!n||rows.some(([,m])=>!m||m.races!==n))throw Error();
    target.innerHTML='<table class="metric-table"><caption>Samma '+n+' historiska V85-lopp; modellerna tränas på tidigare V75- och V85-lopp</caption><thead><tr><th scope="col">Bedömning</th><th scope="col">Vinnare rank 1</th><th scope="col">Vinnare topp 3</th></tr></thead><tbody>'+rows.map(([name,m])=>'<tr><th scope="row">'+name+'</th><td>'+m.top1Count+' / '+m.races+'</td><td>'+m.top3Count+' / '+m.races+'</td></tr>').join('')+'</tbody></table>';
    const h=v.laterHoldout;
    if(h)target.innerHTML+='<p>Separat senare period: '+esc(h.testFrom)+'–'+esc(h.testUntil)+'. Modellen tränas en gång på data till '+esc(h.trainUntil)+'. Vinnaren finns i CatBoosts topp tre i '+h.metrics.top3Count+' av '+h.metrics.races+' lopp; förstahästen vinner '+h.metrics.top1Count+' gånger. Perioden har delvis granskats i tidigare experiment och är därför inte ett orört framtidstest.</p>';
    const c=v.sameRaceHistoryComparison;
    if(c)target.innerHTML+='<p>På samma '+c.sameRaces+' lopp som i det tidigare försöket: '+c.baseline.top3Count+' topp-tre-träffar med det mindre underlaget och '+c.expanded.top3Count+' med den utökade historiken. Modellens inställningar är oförändrade.</p>';
  }catch{target.textContent='Den utökade modelljämförelsen kunde inte läsas. Originalrapporterna finns på forskningssidan.';}
})();
