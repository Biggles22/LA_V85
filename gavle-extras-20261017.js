(()=>{'use strict';
const q=s=>document.querySelector(s);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=v=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('sv-SE',{maximumFractionDigits:2}):'–';
const ts=v=>v?new Date(v).toLocaleString('sv-SE',{timeZone:'Europe/Stockholm',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'–';
let byKey={},heads=[],busy=false;
function flag(h){
 if(!h)return '<small>Ej verifierad från ATG</small>';
 const home=h.homeTrackGavle===true?'<span class="local-flag">HEMMA GÄVLE</span>':h.homeTrackGavle===null||h.homeTrackGavle===undefined?'<span>Hemmabana ej verifierad</span>':'';
 const same=h.sameTrainerDriver===true?'<span class="driver-flag">KUSK = TRÄNARE</span>':'';
 return home+same;
}
function visibleByExtra(h){
 const f=q('#extra-filter')?.value||'all';
 return f==='all'||f==='home'&&h?.homeTrackGavle===true||f==='same'&&h?.sameTrainerDriver===true||f==='both'&&h?.sameTrainerDriver===true&&h?.homeTrackGavle===true;
}
function fillRows(){
 const body=q('#tbody');if(!body||!Object.keys(byKey).length||busy)return;
 busy=true;
 try{
  let shown=0;
  body.querySelectorAll('tr').forEach(tr=>{
   const first=tr.cells[0]?.textContent||'';
   const leg=first.match(/V85-(\d+)/),number=first.match(/Nr\s*(\d+)/);
   if(!leg||!number)return;
   const h=byKey[leg[1]+'-'+number[1]];
   if(!tr.querySelector('.gv-trainer-cell')){
    const td=document.createElement('td');
    td.className='gv-trainer-cell';
    td.innerHTML='<strong>'+esc(h?.trainer?.name||'Ej verifierad')+'</strong><small>Hemmabana: '+esc(h?.trainerHome||'Ej verifierad')+'</small><div>'+flag(h)+'</div>';
    tr.cells[1]?.after(td);
   }
   const show=visibleByExtra(h);
   tr.style.display=show?'':'none';
   if(show)shown++;
  });
  let summary=q('#extra-filter-info');
  if(summary)summary.textContent=shown+' synliga hästar efter tränarfilter.';
 }finally{busy=false;}
}
function addPickFlags(){
 const grid=q('#tips-grid');if(!grid||!Object.keys(byKey).length)return;
 const cards=grid.querySelectorAll('.tip-card');
 cards.forEach((card,i)=>{
   const pick=heads[i];if(!pick||card.querySelector('.gv-pick-meta'))return;
   const h=byKey[pick.key];const div=document.createElement('div');
   div.className='gv-pick-meta';
   div.innerHTML=flag(h)+(pick.marketWarning?'<p class="gv-warning">'+esc(pick.marketWarning)+'</p>':'');
   card.appendChild(div);
 });
}
function showTurnover(t){
 const history=(t?.history||[]).slice().sort((a,b)=>a.sourceAt.localeCompare(b.sourceAt));
 const total=q('#turnover-total'),at=q('#turnover-time'),panel=q('#turnover-entries');
 if(!history.length){
   total.textContent='Inväntas';at.textContent='ATG-data saknas ännu';
   panel.textContent='Ingen verifierad ATG-omsättning har sparats.';
   return;
 }
 const last=history.at(-1),prev=history.length>1?history.at(-2):null;
 total.textContent=fmt(last.turnoverSEK)+' kr';
 at.textContent='ATG '+ts(last.sourceAt);
 panel.innerHTML='<p><strong>Senaste notering: '+fmt(last.turnoverSEK)+' kr</strong> · '+ts(last.sourceAt)+(prev?' · Förändring '+(last.turnoverSEK-prev.turnoverSEK>=0?'+':'')+fmt(last.turnoverSEK-prev.turnoverSEK)+' kr':' · första mätpunkten')+'</p>'+
   '<div class="gv-turnover-items">'+history.slice(-8).reverse().map(v=>'<div><span>'+ts(v.sourceAt)+'</span><strong>'+fmt(v.turnoverSEK)+' kr</strong></div>').join('')+'</div>'+
   '<small>Källa: <a target="_blank" rel="noopener" href="'+esc(t.sourceUrl||'https://www.atg.se/spel/2026-10-17/V85/gavle')+'">ATG:s V85-pool</a>. Uppgifterna är historiska, inte live.</small>';
}
function startObservers(){
 const body=q('#tbody'),grid=q('#tips-grid');
 if(body)new MutationObserver(fillRows).observe(body,{childList:true});
 if(grid)new MutationObserver(addPickFlags).observe(grid,{childList:true});
 q('#extra-filter')?.addEventListener('change',fillRows);
 fillRows();addPickFlags();
}
Promise.all(['startlist.json','turnover.json','gavle-analysis.json'].map(file=>fetch('./'+file+'?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status+' '+file);return r.json()})))
.then(([start,turnover,analysis])=>{
 if(start.round!=='2026-10-17'||turnover.round!==start.round||analysis.round!==start.round)throw Error('Fel omgång');
 byKey=Object.fromEntries(start.races.flatMap(r=>r.starts.map(h=>[h.key,h])));
 const active=start.races.flatMap(r=>r.starts).filter(h=>!h.scratched);
 q('#gavle-homes').textContent=active.filter(h=>h.homeTrackGavle===true).length+' hästar';
 q('#same-trainers').textContent=active.filter(h=>h.sameTrainerDriver===true).length+' hästar';
 heads=analysis.picks.filter(p=>p.role==='Huvudskräll');
 showTurnover(turnover);
 const filter=q('#extra-filter');if(filter){
  const label=document.createElement('small');label.id='extra-filter-info';label.className='notice';
  filter.after(label);
 }
 startObservers();
}).catch(err=>{
 const total=q('#turnover-total');if(total)total.textContent='Ej tillgängligt';
 const area=q('#turnover-entries');if(area)area.textContent='Kunde inte hämta tränar- eller omsättningsdata: '+err.message;
});
})();