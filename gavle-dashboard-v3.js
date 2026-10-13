(()=>{'use strict';
const $$=s=>document.querySelector(s);
const $=$$;
const format=v=>typeof v==='number'?v.toLocaleString('sv-SE',{maximumFractionDigits:2}):'—';
const safe=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
let data=null,choice={};try{choice=JSON.parse(localStorage.getItem('la-v85-gavle-20261017')||'{}')}catch{}
const save=()=>{try{localStorage.setItem('la-v85-gavle-20261017',JSON.stringify(choice))}catch{}};
function tier(p){return p<5?'Storskräll (≤5 %)':p<=10?'Skräll (5–10 %)':p<=20?'Outsider (10–20 %)':'Betrodd (>20 %)'}
function paint(){
 const all=data.races.flatMap(r=>r.starts.map(h=>({...h,leg:r.leg,race:r}))),active=all.filter(h=>!h.scratched),leg=$$('#leg').value,view=$$('#type').value,q=$$('#search').value.toLocaleLowerCase('sv-SE');
 const visible=all.filter(h=>(leg==='all'||String(h.leg)===leg)&&(view==='all'||view==='selected'&&choice[h.key]?.selected||view==='underdogs'&&!h.scratched&&h.percentage<=20||view==='scratched'&&h.scratched)&&(`${h.name} ${h.driver.name}`.toLocaleLowerCase('sv-SE').includes(q)));
 const sorting=$$('#sort').value;
 if(sorting==='increasing')visible.sort((a,b)=>(b.change??-999)-(a.change??-999)||a.leg-b.leg||a.number-b.number);
 else if(sorting==='decreasing')visible.sort((a,b)=>(a.change??999)-(b.change??999)||a.leg-b.leg||a.number-b.number);
 else if(sorting==='odds')visible.sort((a,b)=>(a.odds!==null&&a.odds<99.99?a.odds:999)-(b.odds!==null&&b.odds<99.99?b.odds:999)||a.leg-b.leg||a.number-b.number);
 $$('#visible').textContent=visible.length+' hästar visas';
 $$('#tbody').innerHTML=visible.map(h=>`<tr class="${h.scratched?'scratched':''}"><td>V85-${h.leg}<small>Nr ${h.number}</small></td><td><strong>${safe(h.name)}</strong><small>${safe(h.driver.name)}</small></td><td>${h.postPosition}<small>${h.distance.toLocaleString('sv-SE')} m · ${h.race.startMethod==='auto'?'Auto':'Volt'}</small></td><td><strong>${format(h.percentage)} %</strong><small>${tier(h.percentage)}</small><small title="Förändring från föregående notering">Sedan morgonen: <b class="${h.change>0.05?'up':h.change<-.05?'down':''}">${h.change>0?'+':''}${format(h.change)} procentenheter</b></small></td><td>${h.scratched?'<strong>Struken</strong>':h.odds===null?'—':h.odds>=99.99?'<strong>99,99+</strong>':'<strong>'+format(h.odds)+'</strong>'}<small>${h.scratched?'Ej valbar':h.odds===null?'Saknas':h.odds>=99.99?'Visningstak – ej exakt':'Tidig marknadsnotering'}</small></td><td><label><input type="checkbox" data-select="${h.key}" ${choice[h.key]?.selected&&!h.scratched?'checked':''} ${h.scratched?'disabled':''}> Välj</label><button class="note-button" data-note="${h.key}">${choice[h.key]?.note?'Ändra notering':'+ Notering'}</button></td></tr>`).join('');
 $$('#counts').innerHTML=data.races.map(r=>{let chosen=r.starts.filter(h=>choice[h.key]?.selected&&!h.scratched),favs=r.starts.filter(h=>!h.scratched).sort((a,b)=>b.percentage-a.percentage).slice(0,2);
 return `<article class="race-card"><div class="race-title">V85-${r.leg} · Lopp ${r.number}</div><h3>${r.distance.toLocaleString('sv-SE')} m · ${r.startMethod==='auto'?'Autostart':'Voltstart'}</h3><p>${r.starts.length} anmälda${r.starts.some(h=>h.scratched)?' · 1 struken':''}</p><small>Mest streckade: ${favs.map(h=>safe(h.number+' '+h.name)+' '+format(h.percentage)+' %').join(' · ')}</small><p><strong>${chosen.length} markerade</strong></p><button data-filterleg="${r.leg}">Visa loppet →</button></article>`}).join('');
 const movers=active.filter(h=>Number.isFinite(h.change)&&h.percentage>0).sort((a,b)=>b.change-a.change);
 $$('#market-movers').innerHTML='<div class="move-column"><h3>Störst ökning</h3>'+movers.slice(0,5).map(h=>'<p>V85-'+h.leg+' · '+safe(h.name)+' <b class="up">+'+format(h.change)+' pp</b></p>').join('')+'</div><div class="move-column"><h3>Störst minskning</h3>'+movers.slice(-5).reverse().map(h=>'<p>V85-'+h.leg+' · '+safe(h.name)+' <b class="down">'+format(h.change)+' pp</b></p>').join('')+'</div>';
 const per=data.races.map(r=>r.starts.filter(h=>choice[h.key]?.selected&&!h.scratched).length);
 const rows=per.every(x=>x>0)?per.reduce((a,b)=>a*b,1):0;
 $$('#system').textContent=per.map((n,i)=>'Avd '+(i+1)+': '+n).join(' · ')+' · '+rows.toLocaleString('sv-SE')+' rader';
 const top=active.filter(h=>h.percentage>10&&h.percentage<=20).sort((a,b)=>b.percentage-a.percentage);
 $$('#outsider-count').textContent=top.length+' hästar i intervallet 10–20 %';
 $$('#active-count').textContent=active.length;
 $$('#chosen-count').textContent=active.filter(h=>choice[h.key]?.selected).length;
}
Promise.all([fetch('./startlist.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}),fetch('./odds.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()})]).then(([start,odds])=>{
 if(start.gameId!=='V85_2026-10-17_16_5'||start.round!==odds.round)throw Error('Fel omgång');
 data=start;
 data.races.forEach(r=>r.starts.forEach(h=>{
 const previous=odds.percentagesHistory?.['2026-10-13T08:04:00+02:00']?.[h.key];
 h.percentage=odds.percentages[h.key]??h.percentage;
 h.change=Number.isFinite(previous)?Math.round((h.percentage-previous)*10)/10:null;
 h.odds=odds.winnerOdds?.[h.key]??null;
}));
 $$('#source-time').textContent='Notering: 13 okt kväll · Tipper Trav · jämfört med 13 okt morgon (inte live)';
 paint();
}).catch(err=>{ $$('#load-status').hidden=false; $$('#load-status').textContent='Kunde inte läsa omgångsdata: '+err.message; });
document.addEventListener('change',e=>{if(e.target.matches('#leg,#type,#sort,#search'))paint();if(e.target.matches('[data-select]')){const k=e.target.dataset.select;choice[k]={...(choice[k]||{}),selected:e.target.checked};save();paint()}});
$$('#search').addEventListener('input',()=>{if(data)paint()});
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b||!data)return;
 if(b.dataset.filterleg){$$('#leg').value=b.dataset.filterleg;$$('#type').value='all';paint();$$('#horses').scrollIntoView({behavior:'smooth'})}
 if(b.dataset.note){const k=b.dataset.note;const h=data.races.flatMap(r=>r.starts).find(h=>h.key===k);if(!h)return;
 const v=prompt('Egen notering för '+h.name+' (sparas bara i denna webbläsare):',choice[k]?.note||'');if(v!==null){choice[k]={...(choice[k]||{}),note:v};save();paint()}}
 if(b.id==='export'){const selected=data.races.flatMap(r=>r.starts.map(h=>({leg:r.leg,...h}))).filter(h=>choice[h.key]?.selected&&!h.scratched);
 const lines=['LA_V85 · Gävle 17 oktober 2026','Valda hästar (V85-procent och vinnarodds 13 okt kväll; ej färdig ranking)','',...selected.map(h=>'V85-'+h.leg+' · '+h.number+' '+h.name+' · '+format(h.percentage)+' % · odds '+(h.odds!==null&&h.odds<99.99?format(h.odds):'ej exakt/ej tillgängligt')+(choice[h.key]?.note?' · '+choice[h.key].note:''))];
 navigator.clipboard?.writeText(lines.join('\n')).then(()=>{$$('#export').textContent='Kopierat!'},()=>{$$('#export').textContent='Kunde inte kopiera'})}
 if(b.id==='clear'){if(confirm('Rensa dina markeringar och noteringar för Gävle?')){choice={};save();paint()}}
});
})();