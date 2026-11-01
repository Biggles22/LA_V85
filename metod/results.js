(async()=>{
  const target=document.getElementById('model-results');
  try{
    const docs=await Promise.all(['../research/walkforward_report_v2.json','../research/catboost_trial_v2.json'].map(async path=>{const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw Error();return r.json();}));
    if(docs.some(d=>d.status==='insufficient_data')){target.textContent='Det finns ännu för få kontrollerbara lopp för en gemensam modelljämförelse. Äldre testresultat finns bevarade på forskningssidan.';return;}
    const [base,cat]=docs,rows=[['Grundmodell (XGBoost)',base.strictPairedModel],['CatBoost',cat.strictPairedCatBoost],['ATG:s slutstreck',base.strictPairedMarket]];
    if(rows.some(([,m])=>!m||m.races!==base.strictPairedCount)||cat.strictPairedCount!==base.strictPairedCount||!base.trainingDataQuality?.sourceSha256||base.trainingDataQuality.sourceSha256!==cat.trainingDataQuality?.sourceSha256)throw Error();
    target.innerHTML='<table class="metric-table"><caption>Samma '+base.strictPairedCount+' historiska testlopp efter datarättningen</caption><thead><tr><th scope="col">Bedömning</th><th scope="col">Vinnare rank 1</th><th scope="col">Vinnare topp 3</th></tr></thead><tbody>'+rows.map(([name,m])=>'<tr><th scope="row">'+name+'</th><td>'+m.top1Count+' / '+m.races+'</td><td>'+m.top3Count+' / '+m.races+'</td></tr>').join('')+'</tbody></table>';
  }catch{target.textContent='Testresultaten kunde inte läsas. Originalrapporterna finns på forskningssidan.';}
})();
