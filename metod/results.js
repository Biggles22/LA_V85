(async()=>{
  const target=document.getElementById('model-results');
  try{
    const docs=await Promise.all(['../research/walkforward_report_2026.json','../research/catboost_trial_2026.json'].map(async path=>{const r=await fetch(path);if(!r.ok)throw Error();return r.json();}));
    const [base,cat]=docs,rows=[['Grundmodell (XGBoost)',base.strictPairedModel],['CatBoost',cat.strictPairedCatBoost],['ATG:s slutstreck',base.strictPairedMarket]];
    if(rows.some(([,m])=>!m||m.races!==base.strictPairedCount)||cat.strictPairedCount!==base.strictPairedCount)throw Error();
    target.innerHTML='<table class="metric-table"><caption>Samma '+base.strictPairedCount+' historiska testlopp</caption><thead><tr><th scope="col">Bedömning</th><th scope="col">Vinnare rank 1</th><th scope="col">Vinnare topp 3</th></tr></thead><tbody>'+rows.map(([name,m])=>'<tr><th scope="row">'+name+'</th><td>'+m.top1Count+' / '+m.races+'</td><td>'+m.top3Count+' / '+m.races+'</td></tr>').join('')+'</tbody></table>';
  }catch{target.textContent='Testresultaten kunde inte läsas. Originalrapporterna finns på forskningssidan.';}
})();
