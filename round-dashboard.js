(() => {
  'use strict';
  const root = new URL(document.currentScript.dataset.root, location.href);
  const ROUND = '2026-10-10', GAME = 'V85_2026-10-10_5_6', RULE = '2.0-preparation';
  let startlist = window.roundStartlist, data = window.publishedSnapshot;
  const storeKey = 'la-v85-solvalla-' + ROUND;
  const emptyState = { reviews: {}, priority: {}, system: {}, frozen: null };
  let state;
  try { state = { ...emptyState, ...JSON.parse(localStorage.getItem(storeKey) || '{}') }; }
  catch { state = { ...emptyState }; }
  const $ = s => document.querySelector(s);
  const esc = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
  const num = v => typeof v === 'number' && Number.isFinite(v);
  const fmt = v => num(v) ? v.toLocaleString('sv-SE',{maximumFractionDigits:2}) : '—';
  const time = v => v ? new Date(v).toLocaleString('sv-SE',{timeZone:'Europe/Stockholm',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Inväntas';
  const latest = history => { const days = Object.keys(history || {}).filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d)).sort(); return days.length ? history[days.at(-1)] : null; };
  function save() { try { localStorage.setItem(storeKey, JSON.stringify(state)); } catch { toast('Webbläsaren kunde inte spara dina val.'); } }
  let toastTimer;
  function toast(message) { $('#toast').textContent=message;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),4500); }
  function horses() { return startlist.races.flatMap(r=>r.starts.map(h=>({...h,leg:r.leg,race:r}))); }
  function review(h) {
    const editorial=data.scoring?.expert?.horses?.[h.key];
    const verified=editorial?.name===h.name ? editorial : null;
    return { form: verified?.signals?.form ?? null, pace: verified?.signals?.pace ?? null, note: verified?.note ?? '', ...state.reviews[h.key] };
  }
  const rating = v => v===true || v===1 ? 1 : v===false || v===0 ? 0 : null;
  function metrics(h) {
    const odds=latest(data.horses?.[h.key]),pct=data.percentages?.[h.key],trend=latest(data.trends?.[h.key]);
    const withdrawn=h.scratched || odds==='EJ';
    const exact=num(odds)&&odds>0&&odds<99.99;
    const r=review(h),sh=h.shoes,su=h.sulky;
    const shoeChanged=!!(sh?.reported && (sh.front?.changed || sh.back?.changed));
    const wagonChanged=!!(su?.reported && su.type?.changed);
    const signals={
      market:exact&&num(pct)&&pct>0 ? Number(odds<85/pct) : null,
      trend:num(trend) ? Number(trend>0) : null,
      form:rating(r.form),pace:rating(r.pace),
      shoes:sh?.reported ? Number(!!((sh.front?.changed&&sh.front.hasShoe===false)||(sh.back?.changed&&sh.back.hasShoe===false))) : null,
      wagon:su?.reported ? Number(su.type?.changed===true&&su.type?.code==='AM') : null
    };
    const known=Object.values(signals).filter(v=>v!==null).length;
    const score=Object.values(signals).reduce((s,v)=>s+(v??0),0);
    return {odds,pct,trend,withdrawn,signals,known,score,exact,shoeChanged,wagonChanged,watch:!withdrawn&&num(pct)&&pct>0&&pct<=10&&known===6&&score>=3};
  }
  function compare(a,b) { const x=metrics(a),y=metrics(b);return y.score-x.score || (x.exact?x.odds:Infinity)-(y.exact?y.odds:Infinity) || a.leg-b.leg || a.number-b.number; }
  function shoeLabel(h) { const s=h.shoes;if(!s?.reported)return 'Ej anmäld';return s.front?.hasShoe===false&&s.back?.hasShoe===false ? 'Barfota runt om' : s.front?.hasShoe===false ? 'Barfota fram' : s.back?.hasShoe===false ? 'Barfota bak' : 'Skor runt om'; }
  function options(v) { return [['','Ej bedömd'],['1','Styrkt plus'],['0','Inget styrkt plus']].map(([k,t])=>`<option value="${k}" ${String(v??'')===k?'selected':''}>${t}</option>`).join(''); }
  function details(h,m) {
    const r=review(h),season=h.season;
    const names={market:'Marknad',trend:'V85-trend',form:'Form',pace:'Loppbild',shoes:'Balansändring',wagon:'Vagnändring'};
    const history=Object.entries(data.horses?.[h.key]||{}).sort(([a],[b])=>a.localeCompare(b));
    const comment=data.comments?.horses?.[h.key];
    return `<tr class="details-row" id="detail-${h.key}" hidden><td colspan="10"><h3>${h.number} ${esc(h.name)} · bedömning</h3><ul class="signal-list">${Object.entries(m.signals).map(([key,v])=>`<li>${names[key]}: <strong>${v===null?'saknas':v===1?'styrkt plus':'inget plus'}</strong></li>`).join('')}</ul><p>Årsstatistik 2026: ${fmt(season?.starts)} starter, ${fmt(season?.wins)} segrar, ${fmt(season?.seconds)} andraplatser och ${fmt(season?.thirds)} tredjeplatser. Visas som bakgrund och ger inte automatisk formpoäng.</p><div class="assessment-grid"><label>Aktuell form<select data-review="form" data-key="${h.key}">${options(r.form)}</select></label><label>Bedömd loppbild<select data-review="pace" data-key="${h.key}">${options(r.pace)}</select></label><label>Motivering och källa<textarea data-review="note" data-key="${h.key}" placeholder="Vad talar för eller emot? Ange källa och datum.">${esc(r.note)}</textarea></label></div><div class="detail-actions"><button class="button secondary" data-save="${h.key}">Spara bedömning</button><button class="button" data-prioritize="${h.key}" ${m.withdrawn?'disabled':''}>Prioritera i sluturval</button><a class="button secondary" href="https://www.atg.se/spel/${ROUND}/V85/solvalla/avd/${h.leg}" target="_blank" rel="noopener noreferrer">Avdelningen hos ATG ↗</a></div><p class="source">${comment?.name===h.name ? 'Publicerad kommentar: '+esc(comment.text||comment.summary||'Ej verifierad') : 'Ingen verifierad ATG-kommentar importerad för denna häst ännu.'}</p><p><strong>Oddshistorik:</strong> ${history.length ? history.map(([day,v])=>esc(day)+': '+(v==='EJ'?'EJ':fmt(v))).join(' · ') : 'Ingen verifierad notering ännu.'}</p></td></tr>`;
  }
  function render() {
    const all=horses(),active=all.filter(h=>!metrics(h).withdrawn),watch=all.filter(h=>metrics(h).watch);
    $('#starter-count').textContent=`${all.length} hästar · ${active.length} aktiva · 8 avdelningar`;
    const marketCount=active.filter(h=>num(metrics(h).odds)&&num(metrics(h).pct)&&num(metrics(h).trend)).length;
    $('#market-status').textContent=marketCount ? `${marketCount}/${active.length} har odds, streck och Trend%` : 'Odds, streck och Trend% inväntas';
    $('#source-status').innerHTML=`Startlista: <a href="${esc(startlist.sourceUrl)}" target="_blank" rel="noopener noreferrer">ATG ↗</a> · källversion ${esc(time(startlist.sourceAt))} · kontrollerad ${esc(time(startlist.checkedAt))}. Marknadsnotering: ${esc(time(data.updatedAt))}. Tidiga anmälningar kan ändras.`;
    const leg=$('#leg-filter').value,view=$('#view-filter').value,search=$('#horse-search').value.toLocaleLowerCase('sv-SE');
    let visible=all.filter(h=>(leg==='all'||h.leg===Number(leg))&&(!search||`${h.name} ${h.driver.name} ${h.trainer.name}`.toLocaleLowerCase('sv-SE').includes(search))&&(!$('#home-filter').checked||h.trainerHome==='Solvalla')&&(!$('#same-filter').checked||h.sameTrainerDriver===true));
    visible=visible.filter(h=>view==='all'||view==='watch'&&metrics(h).watch||view==='priority'&&state.priority[h.key]||view==='changes'&&(metrics(h).shoeChanged||metrics(h).wagonChanged));
    if(view==='watch')visible.sort(compare);else visible.sort((a,b)=>a.leg-b.leg||a.number-b.number);
    $('#visible-count').textContent=`${visible.length} visas · ${watch.length} i bevakning`;
    $('#horse-body').innerHTML=visible.map(h=>{const m=metrics(h);return `<tr class="${m.withdrawn?'withdrawn':''}"><td><strong>V85-${h.leg}</strong><small>Nr ${h.number}</small></td><td><strong class="horse-name">${esc(h.name)}${m.withdrawn?' · STRUKEN':''}</strong><small>Kusk: ${esc(h.driver.name)}</small><small>Tränare: ${esc(h.trainer.name)}</small><button class="row-open" data-open="${h.key}" aria-controls="detail-${h.key}" aria-expanded="false">Bedömning &amp; historik</button></td><td>${esc(h.trainerHome||'Ej angiven')}${h.trainerHome==='Solvalla'?' <span class="badge">HEMMA</span>':''}<small>${h.sameTrainerDriver===null?'Kusk/tränare: ej verifierat':h.sameTrainerDriver?'Tränaren kör själv':'Olika kusk och tränare'}</small></td><td>Spår ${fmt(h.postPosition)}<small>${fmt(h.distance)} m · ${h.race.startMethod==='auto'?'Auto':'Volt'}</small></td><td>${m.withdrawn?'EJ':fmt(m.odds)}${num(m.odds)&&m.odds>=99.99?'<small>Visningstak · ingen marknadspoäng</small>':''}</td><td>${num(m.pct)?fmt(m.pct)+' %':'—'}</td><td>${num(m.trend)?(m.trend>0?'+':'')+fmt(m.trend):'—'}</td><td><span class="badge ${m.watch?'signal-positive':''}">${m.score}/6 styrkta</span><small>${m.withdrawn?'Struken':m.known<6?(6-m.known)+' signaler saknas':m.watch?'Skrällbevakning':'Utanför skrällbevakning'}</small></td><td>${esc(shoeLabel(h))}<small>${esc(h.sulky?.reported?h.sulky.type?.text:'Vagn ej anmäld')}</small>${m.shoeChanged?'<span class="change-label">Balansändring anmäld</span>':''}${m.wagonChanged?'<span class="change-label">Vagnändring anmäld</span>':''}</td><td><label><input type="checkbox" data-system="${h.key}" ${state.system[h.key]?'checked':''} ${m.withdrawn?'disabled':''} aria-label="Välj ${esc(h.name)} i systemet"> Välj</label>${state.priority[h.key]?'<small>Prioriterad skräll</small>':''}</td></tr>`+details(h,m);}).join('');
    $('#empty-state').hidden=visible.length>0;$('#empty-state').textContent=view==='watch'?'Ingen häst har ännu komplett underlag för skrällbevakning. Saknade marknadsvärden eller bedömningar ersätts inte med gissningar.':'Inga hästar matchar filtren.';
    $('#division-grid').innerHTML=startlist.races.map(r=>`<button class="division-card" data-leg="${r.leg}"><b>V85-${r.leg} · lopp ${r.number}</b><strong>${esc(r.name)}</strong><small>${r.distance} m · ${r.startMethod==='auto'?'Autostart':'Voltstart'} · ${new Date(r.startTime).toLocaleTimeString('sv-SE',{timeZone:'Europe/Stockholm',hour:'2-digit',minute:'2-digit'})}</small><small>${r.starts.length} hästar · ${watch.filter(h=>h.leg===r.leg).length} i bevakning · ${all.filter(h=>h.leg===r.leg&&state.priority[h.key]).length} prioriterade</small></button>`).join('');
    $('#priority-grid').innerHTML=startlist.races.map(r=>{const chosen=all.filter(h=>h.leg===r.leg&&state.priority[h.key]);return `<article class="priority-card"><h3>V85-${r.leg} · ${chosen.length}/3</h3>${chosen.length?'<ul>'+chosen.map(h=>`<li><strong>${h.number} ${esc(h.name)}</strong>${metrics(h).withdrawn?' · STRUKEN':''}<p>${esc(state.priority[h.key].note)}</p><button class="priority-remove" data-remove="${h.key}">Ta bort ur sluturval</button></li>`).join('')+'</ul>':'<p class="muted">Inget motiverat sluturval ännu.</p>'}</article>`;}).join('');
    const counts=startlist.races.map(r=>all.filter(h=>h.leg===r.leg&&state.system[h.key]&&!metrics(h).withdrawn).length);
    const rowCount=counts.every(n=>n>0)?counts.reduce((a,b)=>a*b,1):0;
    $('#system-summary').textContent=`${counts.map((n,i)=>'Avd '+(i+1)+': '+n).join(' · ')}. ${rowCount.toLocaleString('sv-SE')} rader${rowCount===0?' (välj minst en aktiv häst i varje avdelning)':''}.`;
    const chosen=all.filter(h=>state.priority[h.key]);
    const ready=chosen.length>0&&chosen.every(h=>metrics(h).known===6&&metrics(h).watch&&review(h).note.trim())&&!!data.updatedAt;
    const beforeStart=Date.now()<Date.parse(startlist.races[0].startTime);
    $('#freeze-selection').disabled=!!state.frozen||!ready||!beforeStart;
    $('#export-selection').disabled=!state.frozen;
    $('#freeze-status').textContent=state.frozen?'Fryst '+time(state.frozen.frozenAt)+'. Efterföljande ändringar påverkar inte den sparade jämförelsen.':!beforeStart?'Frysning är stängd efter första avdelningens planerade start.':ready?'Underlag och motiveringar finns. Frys när sluturvalet är klart.':'Verifierade marknadsdata och motiverade, kompletta skrällbedömningar krävs före frysning.';
  }
  function getReviewFromInputs(key) { const value=s=>document.querySelector(`[data-review="${s}"][data-key="${key}"]`).value;return {form:value('form')===''?null:Number(value('form')),pace:value('pace')===''?null:Number(value('pace')),note:value('note').trim()}; }
  $('#horse-body').addEventListener('click',e=>{
    const open=e.target.closest('[data-open]');if(open){const detail=$('#detail-'+open.dataset.open);detail.hidden=!detail.hidden;open.setAttribute('aria-expanded',String(!detail.hidden));return;}
    const saveButton=e.target.closest('[data-save]'),priority=e.target.closest('[data-prioritize]');
    if(saveButton||priority){const key=(saveButton||priority).dataset[priority?'prioritize':'save'];const r=getReviewFromInputs(key);if(!r.note&&(r.form!==null||r.pace!==null||priority)){toast('Skriv en motivering och källa innan bedömningen sparas.');return;}
      if(priority){const h=horses().find(h=>h.key===key);if(h.scratched||metrics(h).withdrawn){toast('En struken häst kan inte prioriteras.');return;}const count=horses().filter(x=>x.leg===h.leg&&state.priority[x.key]&&x.key!==key).length;if(count>=3){toast('Högst tre prioriterade skrällar per avdelning. Ta bort en först.');return;}if(num(metrics(h).pct)&&metrics(h).pct>10){toast('Sluturvalet avser skrällar på högst 10 %. Lägg favoriten i systemvalen i stället.');return;}state.priority[key]={note:r.note,selectedAt:new Date().toISOString()};}
      state.reviews[key]=r;if(state.priority[key])state.priority[key].note=r.note;save();render();toast(priority?'Hästen är prioriterad. Underlaget kontrolleras igen före frysning.':'Bedömningen är sparad.');}
  });
  $('#horse-body').addEventListener('change',e=>{if(e.target.matches('[data-system]')){state.system[e.target.dataset.system]=e.target.checked;save();render();}});
  $('#priority-grid').addEventListener('click',e=>{const b=e.target.closest('[data-remove]');if(b){delete state.priority[b.dataset.remove];save();render();}});
  $('#division-grid').addEventListener('click',e=>{const b=e.target.closest('[data-leg]');if(b){$('#leg-filter').value=b.dataset.leg;$('#view-filter').value='all';render();$('#horse-data').scrollIntoView({behavior:'smooth'});}});
  ['#leg-filter','#view-filter','#home-filter','#same-filter'].forEach(s=>$(s).addEventListener('change',render));$('#horse-search').addEventListener('input',render);
  $('#freeze-selection').addEventListener('click',()=>{if($('#freeze-selection').disabled)return;state.frozen={round:ROUND,gameId:GAME,ruleVersion:RULE,frozenAt:new Date().toISOString(),sourceAt:data.updatedAt,startlistSourceAt:startlist.sourceAt,oddsPoolTimestamps:data.oddsPoolTimestamps,priority:JSON.parse(JSON.stringify(state.priority)),reviews:JSON.parse(JSON.stringify(state.reviews)),watch:horses().filter(h=>metrics(h).watch).sort(compare).map(h=>({key:h.key,name:h.name,leg:h.leg,metrics:metrics(h)})),startlist:JSON.parse(JSON.stringify(startlist)),market:JSON.parse(JSON.stringify(data))};save();render();toast('Sluturval och underlag är frysta i denna webbläsare. Exportera för att bevara jämförelsen.');});
  $('#export-selection').addEventListener('click',()=>{if(!state.frozen)return;const url=URL.createObjectURL(new Blob([JSON.stringify(state.frozen,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='solvalla-2026-10-10-fryst-urval.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  for(const r of startlist.races){const option=document.createElement('option');option.value=r.leg;option.textContent='V85-'+r.leg;$('#leg-filter').append(option);}
  async function refresh() {
    const paths=['startlist.json','odds.json','turnover.json'];
    const results=await Promise.allSettled(paths.map(async path=>{const res=await fetch(new URL(path,root),{cache:'no-store'});if(!res.ok)throw Error('HTTP '+res.status);return res.json();}));
    for(let i=0;i<results.length;i++){
      const result=results[i];if(result.status!=='fulfilled')continue;const incoming=result.value;
      if(incoming.round!==ROUND||incoming.track!=='Solvalla')continue;
      if(i===0&&incoming.gameId===GAME&&incoming.sourceVersion>=startlist.sourceVersion&&incoming.races?.length===8&&incoming.races.every((r,n)=>r.id===`2026-10-10_5_${n+6}`&&r.leg===n+1)&&new Set(incoming.races.flatMap(r=>r.starts.map(h=>h.key))).size===incoming.races.reduce((n,r)=>n+r.starts.length,0))startlist=incoming;
      if(i===1&&incoming.gameId===GAME&&horses().every(h=>Object.hasOwn(incoming.horses||{},h.key))&&(!data.updatedAt||Date.parse(incoming.updatedAt)>=Date.parse(data.updatedAt)))data=incoming;
      if(i===2&&num(incoming.amountSek)&&incoming.observedAt){$('#turnover-amount').textContent=fmt(incoming.amountSek)+' kr';$('#turnover-status').textContent='Källnotering '+time(incoming.observedAt);}
    }
    render();
  }
  render();refresh();setInterval(refresh,300000);
  window.LA85={metrics,compare,horses,getState:()=>state,ruleVersion:RULE};
})();
