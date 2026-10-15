(()=>{'use strict';
const q=x=>document.querySelector(x);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('sv-SE',{maximumFractionDigits:2}):'–';
const roleClass=x=>({'Huvudskräll':'head','Motbud':'counter','Högoddsare':'longshot','Marknadsavvikelse':'anomaly'})[x]||'normal';
const roleLabel=pct=>pct<=5?'Storskräll 0–5 %':pct<=10?'Skräll 5–10 %':pct<=20?'Outsider 10–20 %':'Betrodd över 20 %';
let start,market,analysis,all=[];
let state={};try{state=JSON.parse(localStorage.getItem('la-v85-gavle-20261017')||'{}')}catch{}
const save=()=>{try{localStorage.setItem('la-v85-gavle-20261017',JSON.stringify(state))}catch{}};
const oddsView=h=>h.scratched?'EJ':h.odds===null?'–':h.odds>=99.99?'99,99+':fmt(h.odds);
const oddsHint=h=>h.scratched?'Struken':h.odds===null?'Saknas':h.odds>=99.99?'Visningstak – inte exakt':'Tidigt V-odds';
const trendView=h=>!Number.isFinite(h.change)?'Trend saknas':(h.change>0?'+':'')+fmt(h.change)+' pp';
const rLink=(url,text)=>url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(text||'Källa')+' ↗</a>':'';
const raceData=leg=>start.races.find(r=>r.leg===leg);
function renderPicks(){
 const heads=analysis.picks.filter(p=>p.role==='Huvudskräll');
 q('#tips-grid').innerHTML=heads.map(p=>{
  const h=all.find(x=>x.key===p.key);
  return '<article class="tip-card"><div class="tip-top"><span>V85-'+p.leg+'</span><span class="tip-pill">Min huvudskräll</span></div><h3>'+esc(p.number+' '+p.name)+'</h3><p class="tip-data">'+fmt(h?.pct)+' % V85 · V-odds '+oddsView(h)+'</p><p>'+esc(p.why)+'</p><p class="risk"><strong>Risk:</strong> '+esc(p.risk)+'</p><button data-addpick="'+esc(p.key)+'" '+(h.scratched?'disabled':'')+'>'+(state[p.key]?.selected?'✓ Redan vald':'+ Lägg till i system')+'</button></article>';
 }).join('');
 const others=analysis.picks.filter(p=>p.role!=='Huvudskräll');
 q('#other-tips').innerHTML='<h3>Övriga skrällar och motbud</h3><div class="secondary-picks">'+others.map(p=>'<article class="secondary-pick"><div><b>V85-'+p.leg+' · '+esc(p.number+' '+p.name)+'</b><span class="tip-tag '+roleClass(p.role)+'">'+esc(p.role)+'</span><small>'+fmt(p.pct)+' % V85 · V-odds '+(p.odds===null?'–':p.odds>=99.99?'99,99+':fmt(p.odds))+'</small></div><p>'+esc(p.why)+'</p><p class="risk">'+esc(p.risk)+'</p><button data-addpick="'+esc(p.key)+'">'+(state[p.key]?.selected?'✓ Vald':'+ Lägg till')+'</button></article>').join('')+'</div>';
}
function render(){
 const leg=q('#leg').value,view=q('#type').value,search=q('#search').value.toLocaleLowerCase('sv-SE');
 let rows=all.filter(h=>
  (leg==='all'||String(h.leg)===leg)&&
  (view==='all'||view==='headline'&&h.pick?.role==='Huvudskräll'||view==='priority'&&h.pick||view==='underdogs'&&!h.scratched&&h.pct<=20||view==='selected'&&state[h.key]?.selected||view==='scratched'&&h.scratched)&&
  (!search||[h.name,h.driver.name,h.comment.comment,h.pick?.role].join(' ').toLocaleLowerCase('sv-SE').includes(search))
 );
 const sort=q('#sort').value;
 if(sort==='rising')rows.sort((a,b)=>(b.change??-999)-(a.change??-999));
 else if(sort==='falling')rows.sort((a,b)=>(a.change??999)-(b.change??999));
 else if(sort==='lowodds')rows.sort((a,b)=>(a.odds===null||a.odds>=99.99?999:a.odds)-(b.odds===null||b.odds>=99.99?999:b.odds));
 else if(sort==='ai')rows.sort((a,b)=>b.ai-a.ai);
 else if(sort==='lowpct')rows.sort((a,b)=>a.pct-b.pct);
 else rows.sort((a,b)=>a.leg-b.leg||a.number-b.number);
 q('#visible').textContent=rows.length+' hästar visas. Totalt 98 anmälda, '+all.filter(h=>h.scratched).length+' strukna. Marknadsdata 15 oktober.';
 q('#tbody').innerHTML=rows.map(h=>{
  const c=h.comment;
  const note=(state[h.key]?.note||'');
  const tag=h.pick?'<span class="tip-tag '+roleClass(h.pick.role)+'">'+esc(h.pick.role)+'</span>':'';
  return '<tr class="'+(h.scratched?'scratched':'')+'"><td><strong>V85-'+h.leg+'</strong><small>Nr '+h.number+'</small></td><td><strong>'+esc(h.name)+'</strong><small>'+esc(h.driver.name)+'</small></td><td>'+h.postPosition+'<small>'+h.race.distance+' m · '+(h.race.startMethod==='auto'?'Auto':'Volt')+'</small></td><td><strong>'+fmt(h.pct)+' %</strong><small>'+roleLabel(h.pct)+'</small><small class="'+(h.change>0?'up':h.change<0?'down':'')+'">'+trendView(h)+'</small></td><td><strong>'+oddsView(h)+'</strong><small>'+oddsHint(h)+'</small></td><td><b>'+fmt(h.ai)+'</b><small>Index, ej vinst%</small></td><td class="comment-cell">'+tag+'<p>'+esc(c.comment)+'</p><small>'+esc(c.author)+'</small>'+rLink(c.sourceUrl,'Underlag')+(note?'<p><strong>Min notering:</strong> '+esc(note)+'</p>':'')+'<button class="note-button" data-note="'+esc(h.key)+'">'+(note?'Redigera egen notering':'+ Egen notering')+'</button></td><td><label><input type="checkbox" data-select="'+esc(h.key)+'" '+(state[h.key]?.selected&&!h.scratched?'checked':'')+' '+(h.scratched?'disabled':'')+'> Välj</label></td></tr>';
 }).join('');
 q('#counts').innerHTML=start.races.map(r=>{
  const fav=r.starts.filter(h=>!h.scratched).map(h=>all.find(x=>x.key===h.key)).sort((a,b)=>b.pct-a.pct).slice(0,2);
  const picks=analysis.picks.filter(p=>p.leg===r.leg&&p.role==='Huvudskräll');
  const count=r.starts.filter(h=>state[h.key]?.selected&&!h.scratched).length;
  return '<article class="race-card"><div class="race-title">V85-'+r.leg+' · Lopp '+r.number+'</div><h3>'+r.distance+' m · '+(r.startMethod==='auto'?'Autostart':'Voltstart')+'</h3><small>'+r.starts.length+' anmälda · '+r.starts.filter(h=>h.scratched).length+' strukna</small><p><strong>Favorit:</strong> '+fav.map(h=>esc(h.number+' '+h.name)+' '+fmt(h.pct)+' %').join(' / ')+'</p><p><strong>Min skräll:</strong> '+esc(picks[0]?.name||'–')+'</p><p>'+count+' valda i systemet</p><button data-filterleg="'+r.leg+'">Visa avdelning →</button></article>';
 }).join('');
 const valid=all.filter(h=>!h.scratched);
 const risers=valid.filter(h=>Number.isFinite(h.change)).sort((a,b)=>b.change-a.change);
 q('#market-movers').innerHTML='<div class="move-column"><h3>Störst ökning</h3>'+risers.slice(0,5).map(h=>'<p>V85-'+h.leg+' · '+esc(h.name)+' <b class="up">+'+fmt(h.change)+' pp</b></p>').join('')+'</div><div class="move-column"><h3>Störst minskning</h3>'+risers.slice(-5).reverse().map(h=>'<p>V85-'+h.leg+' · '+esc(h.name)+' <b class="down">'+fmt(h.change)+' pp</b></p>').join('')+'</div>';
 q('#active-count').textContent=valid.length+' / '+all.length;
 q('#headline-count').textContent=analysis.picks.filter(p=>p.role==='Huvudskräll').length;
 q('#watch-count').textContent=analysis.picks.length;
 q('#chosen-count').textContent=valid.filter(h=>state[h.key]?.selected).length;
 const selectedCounts=start.races.map(r=>r.starts.filter(h=>state[h.key]?.selected&&!h.scratched).length);
 const nrows=selectedCounts.every(n=>n>0)?selectedCounts.reduce((a,b)=>a*b,1):0;
 q('#system').textContent=selectedCounts.map((n,i)=>'Avd '+(i+1)+': '+n).join(' · ')+' · '+nrows.toLocaleString('sv-SE')+' rader';
 renderPicks();
}
Promise.all(['startlist.json','odds.json','gavle-analysis.json'].map(file=>fetch('./'+file+'?v=20261015').then(r=>{if(!r.ok)throw Error('HTTP '+r.status+' för '+file);return r.json()})))
.then(([s,m,a])=>{
 if(s.round!=='2026-10-17'||m.round!==s.round||a.round!==s.round)throw Error('Fel omgång på filer');
 start=s;market=m;analysis=a;
 const prev=market.percentagesHistory?.['2026-10-13T18:52:00+02:00']||{};
 all=s.races.flatMap(r=>r.starts.map(h=>{
  const pct=market.percentages[h.key],rawPrice=market.winnerOdds[h.key],ai=market.tipperAI[h.key],comment=a.commentary[h.key];
  if(!comment||!Number.isFinite(pct)||!Number.isFinite(ai))throw Error('Saknar verifierad hästkoppling för '+h.key);
  const old=prev[h.key];
  return {...h,leg:r.leg,race:r,pct,odds:rawPrice??null,ai,comment,change:Number.isFinite(old)?Math.round((pct-old)*10)/10:null,pick:a.picks.find(p=>p.key===h.key)||null};
 }));
 if(all.length!==98)throw Error('Förväntade 98 hästar – hittade '+all.length);
 q('#load-status').hidden=true;render();
}).catch(error=>{q('#load-status').hidden=false;q('#load-status').textContent='Kunde inte läsa omgångsdata: '+error.message});
document.addEventListener('change',e=>{
 if(e.target.matches('#leg,#type,#sort')){if(all.length)render();}
 if(e.target.matches('[data-select]')){const k=e.target.dataset.select;state[k]={...(state[k]||{}),selected:e.target.checked};save();render();}
});
q('#search').addEventListener('input',()=>{if(all.length)render()});
document.addEventListener('click',e=>{
 const btn=e.target.closest('button');if(!btn||!all.length)return;
 if(btn.dataset.addpick){
  const k=btn.dataset.addpick,h=all.find(x=>x.key===k);if(h&&!h.scratched){state[k]={...(state[k]||{}),selected:true};save();render();}
 }
 if(btn.dataset.filterleg){q('#leg').value=btn.dataset.filterleg;q('#type').value='all';render();q('#horses').scrollIntoView({behavior:'smooth'});}
 if(btn.dataset.note){
  const k=btn.dataset.note,h=all.find(x=>x.key===k);
  if(h){const val=prompt('Egen notering: '+h.name,state[k]?.note||'');if(val!==null){state[k]={...(state[k]||{}),note:val};save();render();}}
 }
 if(btn.id==='clear'&&confirm('Rensa alla dina val och noteringar för Gävle?')){state={};save();render();}
 if(btn.id==='export'){
  const marked=all.filter(h=>!h.scratched&&state[h.key]?.selected);
  const str=['LA_V85 · Gävle 17 oktober','Valda hästar: '+marked.length+' (förhandsbild 15 oktober)','',...marked.map(h=>'V85-'+h.leg+' · '+h.number+' '+h.name+' · '+fmt(h.pct)+' % · Odds '+oddsView(h)+' · '+(state[h.key]?.note||''))].join('\n');
  if(navigator.clipboard?.writeText)navigator.clipboard.writeText(str).then(()=>{btn.textContent='✓ Kopierat'},()=>{btn.textContent='Kopiering misslyckades'});
  else btn.textContent='Kopiering stöds inte i webbläsaren';
 }
});
})();