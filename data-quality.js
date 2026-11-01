(()=>{
  const targets=[...document.querySelectorAll('[data-training-quality]')];
  if(!targets.length)return;
  const base=new URL('.',document.currentScript.src);
  fetch(new URL('research/training_data_quality_2026.json',base),{cache:'no-store'})
    .then(r=>{if(!r.ok)throw Error();return r.json();})
    .then(q=>{
      const fields=['sourceRaces','eligibleRaces','eligibleStarts','excludedRaces','legacyEligibleRaces'];
      if(fields.some(k=>!Number.isInteger(q[k])||q[k]<0)||q.eligibleRaces+q.excludedRaces!==q.sourceRaces)throw Error();
      for(const target of targets){
        const summary=document.createElement('p');
        summary.textContent=q.eligibleRaces+' av '+q.sourceRaces+' historiska lopp ('+q.eligibleStarts+' häststarter) klarar kontrollen av fullständiga startfält och resultat. '+q.excludedRaces+' lopp hålls utanför modellträningen tills underlaget har verifierats.';
        const risk=document.createElement('p');
        risk.textContent=q.legacyEligibleRaces?'Galoppvärden från det äldre underlaget används inte, eftersom de saknar verifierbar källa. Okänd galopprisk räknas inte som låg risk.':'Galopprisk beräknas enbart från uttryckliga observationer. Saknade uppgifter räknas inte som noll.';
        const link=document.createElement('a');link.href=new URL('research/training_data_quality_2026.json',base);link.textContent='Se datakontrollen';
        target.replaceChildren(summary,risk,link);
      }
    }).catch(()=>{for(const target of targets)target.textContent='Datakontrollen kunde inte läsas. Modellernas aktuella underlag kan därför inte bekräftas här.';});
})();
