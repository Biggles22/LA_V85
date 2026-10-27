(function FormFrontend() {
  'use strict';
  const root=document.getElementById('bjerke-form-live');if(!root)return;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const f=x=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString('sv-SE',{maximumFractionDigits:2}):'–';
  const safeDate=d=>d?esc(String(d).replace('T',' ').slice(0,16)):'Okänt';
  let report=null,leg=1;
  function render(){
    const c=report.coverage||{};
    const selected=report.races.find(x=>x.leg===leg);
    if(!selected)return;
    const ranked=selected.horses.filter(x=>!x.scratched).sort((a,b)=>{
      const ap=a.evidence?.partialRankScore,bp=b.evidence?.partialRankScore;
      if(typeof ap==='number'&&typeof bp==='number'){
        return bp-ap || (b.evidence?.modelCoverageWeight||0)-(a.evidence?.modelCoverageWeight||0);
      }
      if(typeof ap==='number')return -1;
      if(typeof bp==='number')return 1;
      return a.number-b.number;
    });
    const rows=ranked.map(h=>{
      const partial=h.evidence?.partialRankScore,weight=h.evidence?.modelCoverageWeight||0;
      const classCountries=(h.evidence?.classCountries||[]).join(', ');
      const why=`${h.evidence?.classStarts||0} jämförda klasslopp${classCountries?' ('+classCountries+')':''}; ${h.evidence?.paceStarts||0} jämförbara tempolopp`;
      return `<tr><td><strong>${h.number} ${esc(h.name)}</strong><small>${h.previousStarts??0} tidigare starter</small></td>
      <td class="number-cell"><strong>${f(partial)}</strong><small>${weight} % av faktorerna</small></td>
      <td>${f(h.scores?.form)}</td><td>${f(h.scores?.class)}</td><td>${f(h.scores?.pace)}</td><td>${f(h.scores?.risk)}</td>
      <td><small>${esc(why)}</small></td>
      <td>${(h.lastFive||[]).map(x=>`${esc(x.date)}: ${x.galloped===true?'galopp / ':''}${x.place==null?'placering okänd':x.place===0?'oplacerad':x.place+':a'}`).join(' · ')||'Ingen tillförlitlig historik'}</td></tr>`;
    }).join('');
    root.innerHTML=`<div class="model-form-status"><strong>Historik: ${c.horsesWithHistory??0}/${c.activeHorses??0} · Form: ${c.formRated??0} · Klassproxy: ${c.classRated??0} · Tempo/spårproxy: ${c.paceRated??0} · Indikativ delranking: ${c.partialRanked??0}</strong>
      <small>ATG:s marknadstid: ${safeDate(report.atgSourceAt)} · Historik hämtad: ${safeDate(report.retrievedAt)} · ${c.failedRaces??0} lopp med API-fel</small></div>
      <p class="model-form-help">Tabellen sorteras efter <strong>indikativ delpoäng</strong> där minst två faktorer har tillräckligt underlag. Faktortäckningen visas för varje häst. Klass = tidigare lopps prisnivå inom respektive land, kombinerad med historiska placeringar. Tempo/spår = tidigare kilometertider på liknande distans samt aktuellt startspår vid autostart. <strong>Ingen faktisk spetsprognos eller vinstsannolikhet.</strong></p>
      <div class="model-toolbar"><label for="bjerke-form-race">Välj avdelning</label><select id="bjerke-form-race">${report.races.map(r=>`<option value="${r.leg}"${r.leg===leg?' selected':''}>V85-${r.leg}</option>`).join('')}</select>
      <span class="model-form-note"><a href="${esc(selected.sourceUrl)}" target="_blank" rel="noopener">ATG:s källdata</a></span></div>
      <div class="model-table-scroll"><table class="model-table model-form-table"><thead><tr><th>Häst</th><th>Delpoäng / 100</th><th>Form / 5</th><th>Klass / 5</th><th>Tempo/spår / 5</th><th>Risk / 5</th><th>Underlag</th><th>Fem senaste resultat</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="model-footnote">Placeringar avser endast lopp före 31 oktober 2026. Saknade fält markeras – och ger inte noll. Fler kända faktorer ger säkrare bedömning men garanterar inte högre träffsäkerhet. Utrustning och faktisk spets-/loppbildsanalys behöver fortfarande verifieras manuellt. Ingen vinnare, spik eller skräll utses enbart av denna tabell.</p>`;
    document.getElementById('bjerke-form-race').addEventListener('change',e=>{leg=Number(e.target.value);render()});
  }
  fetch('./bjerke-form-20261031.json',{cache:'no-store'}).then(r=>{
    if(!r.ok)throw Error('Ingen verifierad formfil ännu');
    return r.json();
  }).then(d=>{
    if(d.gameId!=='V85_2026-10-31_78_5'||!Array.isArray(d.races)||d.races.length!==8)throw Error('Fel omgång');
    report=d;render();
  }).catch(e=>{
    root.innerHTML='<p class="work-note"><strong>Modellen väntar på verifierad ATG-historik.</strong> Inga automatpoäng visas om de utökade loppuppgifterna saknas.</p>';
    console.info(e.message);
  });
})();
