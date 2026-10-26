(function FormFrontend() {
  'use strict';
  const root=document.getElementById('bjerke-form-live');if(!root)return;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const f=x=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString('sv-SE',{maximumFractionDigits:2}):'–';
  const safeDate=d=>d?esc(String(d).replace('T',' ').slice(0,16)):'Okänt';
  let report=null,leg=1;
  function render(){
    const c=report.coverage||{};
    const rate=c.activeHorses?Math.round(100*(c.formRated||0)/c.activeHorses):0;
    const selected=report.races.find(x=>x.leg===leg);
    if(!selected)return;
    const rows=selected.horses.filter(x=>!x.scratched).sort((a,b)=>{
      const aa=a.scores?.form,bb=b.scores?.form;
      if(typeof aa==='number'&&typeof bb==='number')return bb-aa;
      if(typeof aa==='number')return -1;
      if(typeof bb==='number')return 1;
      return a.number-b.number;
    }).map(h=>`<tr><td><strong>${h.number} ${esc(h.name)}</strong></td><td>${h.previousStarts??0}</td>
    <td>${f(h.scores?.form)} / 5</td><td>${f(h.distanceOnlyScore)} / 5</td><td>${f(h.scores?.risk)} / 5</td>
    <td>${(h.lastFive||[]).map(x=>`${esc(x.date)}: ${x.galloped===true?'galopp':x.place==null?'plac. okänd':x.place===0?'oplacerad':x.place+':a'}`).join(' · ')||'Ingen tillförlitlig historik'}</td></tr>`).join('');
    root.innerHTML=`<div class="model-form-status"><strong>Historik: ${c.horsesWithHistory??0}/${c.activeHorses??0} hästar · Formbetyg: ${c.formRated??0}/${c.activeHorses??0} (${rate} %) · Riskbetyg: ${c.riskRated??0}/${c.activeHorses??0}</strong>
      <small>ATG:s spelnotering: ${safeDate(report.atgSourceAt)} · Historikinsamling: ${safeDate(report.retrievedAt)} · ${c.failedRaces??0} lopp med API-fel</small></div>
      <p class="model-form-help">Formbetyget använder tidigare placeringar och galopper – aldrig spelprocent eller odds. Distansprovet redovisas separat; vi gissar inte klass, spetschans eller utrustning. Det finns <strong>ingen kalibrerad vinstprocent</strong> eller automatiskt spikbeslut.</p>
      <div class="model-toolbar"><label for="bjerke-form-race">Analyserad avdelning</label><select id="bjerke-form-race">${report.races.map(r=>`<option value="${r.leg}"${r.leg===leg?' selected':''}>V85-${r.leg}</option>`).join('')}</select>
      <span class="model-form-note"><a href="${esc(selected.sourceUrl)}" target="_blank" rel="noopener">ATG:s källdata</a></span></div>
      <div class="model-table-scroll"><table class="model-table model-form-table"><thead><tr><th>Häst</th><th>Historiska starter</th><th>Form</th><th>Distansprov</th><th>Låg risk = högt betyg</th><th>Senaste resultat</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="model-footnote">Endast lopp före 31 oktober används. Saknade formrader anges med streck (–) och ger inte noll poäng. Poängreglerna är nya arbetsantaganden, inte testade prognosvärden. Källa: ATG:s utökade loppinformation där den är tillgänglig.</p>`;
    document.getElementById('bjerke-form-race').addEventListener('change',e=>{leg=Number(e.target.value);render()});
  }
  fetch('./bjerke-form-20261031.json',{cache:'no-store'}).then(r=>{
    if(!r.ok)throw Error('Ingen verifierad formfil ännu');
    return r.json();
  }).then(d=>{
    if(d.gameId!=='V85_2026-10-31_78_5'||!Array.isArray(d.races)||d.races.length!==8)throw Error('Fel omgång');
    report=d;render();
  }).catch(e=>{
    root.innerHTML='<p class="work-note"><strong>Formanalysen inväntar verifierad historik.</strong> GitHub Actions försöker hämta hästarnas tidigare starter från ATG. Vi visar inga automatiska formbetyg innan data har kontrollerats. Marknadsdata och den manuella arbetsytan fungerar fortfarande.</p>';
    console.info(e.message);
  });
})();
