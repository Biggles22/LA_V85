/* One current round, reviewed proposals and independent local selections. */
(async function(){
  'use strict';
  const D=window.V85Domain,$=s=>document.querySelector(s);
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(n,d=1)=>D.finite(n)?n.toLocaleString('sv-SE',{maximumFractionDigits:d}):'–';
  const stamp=s=>D.instant(s)?new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Stockholm',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(s)):'Inte verifierad';
  const get=async url=>{const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('Underlaget kunde inte hämtas ('+r.status+').');return r.json();};
  let form=null,model=null;
  let data,analysis,round,storageKey,leg=1,state={selections:{},frozen:[],stake:null},analysisUnavailable=false;
  const empty=(title,body)=>'<div class="empty-state"><h3>'+esc(title)+'</h3><p>'+esc(body)+'</p></div>';
  function save(){
    try{localStorage.setItem(storageKey,JSON.stringify(state));$('#save-status').textContent='Sparat på den här enheten';return true;}
    catch{$('#save-status').textContent='Kunde inte spara – exportera urvalet';return false;}
  }
  function exportJSON(value,name){
    const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function renderStatus(){
    const phase=D.phase(data),notice=$('#data-status');
    $('#round-phase').textContent={awaiting:'Underlag inväntas',open:'Förhandsarbete',stale:'Äldre marknadsdata',closed:'Spelstopp passerat'}[phase];
    $('#start-time').textContent=data.startTime?stamp(data.startTime):'Inväntar verifierad tid';
    $('#source-time').textContent=data.sourceAt?stamp(data.sourceAt):'Inväntar startlista';
    notice.className='data-notice'+(['stale','closed'].includes(phase)?' warning':'');
    if(phase==='awaiting')notice.textContent='Vi inväntar verifierade startlistor och streck för '+round.track+'. Skräll- och spikförslag publiceras när underlaget har granskats.';
    else if(phase==='closed')notice.textContent='Spelstopp har passerat. Här visas det bevarade förhandsunderlaget. Nya förhandsfrysningar är stängda.';
    else if(phase==='stale')notice.textContent='Marknadsuppgifterna är äldre än sex timmar ('+stamp(data.sourceAt)+'). Kontrollera aktuella streck och strykningar hos ATG före ett beslut.';
    else notice.textContent='Marknad kontrollerad '+stamp(data.sourceAt)+' · '+D.runners(data).filter(h=>!h.scratched).length+' aktiva hästar. Uppgifterna är en sparad ögonblicksbild.';
    if(data.status==='verified'&&!D.runners(data).some(h=>D.finite(h.pct)))notice.textContent+=' Streck saknas: ATG redovisar ännu ingen omsättning. Nollvärden används inte som spelprocent.';
    if(analysisUnavailable&&phase!=='awaiting')notice.textContent+=' Analysunderlaget kunde inte hämtas. Startlistan kan fortfarande granskas.';
    $('#freeze-selection').disabled=phase==='closed'||phase==='awaiting'||!D.totals(data,state.selections,state.stake).selected;
  }
  function renderProposals(){
    const verified=D.picks(data,analysis),limit=Number($('#outsider-limit').value);
    function cards(type){
      const all=verified.filter(p=>p.type===type),list=all.filter(p=>type==='spike'||limit===100||(D.finite(p.pct)&&p.pct<=limit));
      if(!list.length){
        const title=all.length?'Inga förslag inom valt streckintervall':type==='outsider'?'Skrällförslagen inväntar granskning':'Spikförslagen inväntar granskning';
        const body=data.status!=='verified'?'Bergsåkers startlista och speluppgifter behöver först verifieras. Inga hästar från en äldre omgång används som förslag.':all.length?'Välj en högre streckgräns för att visa fler granskade motbud.':'Startlistan finns att granska nedan. Förslag publiceras först med motivering, risk och källor för det aktuella underlaget.';
        return empty(title,body);
      }
      return list.map(p=>'<article class="proposal-card '+(type==='spike'?'spike':'')+'"><div class="card-top"><span>V85-'+p.leg+' · '+(type==='spike'?'SPIKFÖRSLAG':'SKRÄLLFÖRSLAG')+'</span><span class="percentage">'+fmt(p.pct)+' %</span></div><h3>'+p.number+' '+esc(p.name)+'</h3><p>'+esc(p.reason)+'</p><p class="risk"><strong>Risk:</strong> '+esc(p.risk)+'</p>'+(Array.isArray(p.challengers)&&p.challengers.length?'<p><strong>Motbud:</strong> '+esc(p.challengers.join(', '))+'</p>':'')+'<p class="source-note">Granskad '+esc(stamp(analysis.reviewedAt))+' · '+p.sources.map((s,i)=>'<a href="'+esc(s)+'" target="_blank" rel="noopener noreferrer">Källa '+(i+1)+'</a>').join(' · ')+'</p><div class="card-actions"><button class="button secondary" data-leg="'+p.leg+'">Granska loppet</button><button class="button primary" data-action="include" data-key="'+p.key+'">'+(state.selections[p.key]?'✓ Vald':'+ Mitt urval')+'</button></div></article>').join('');
    }
    $('#outsider-list').innerHTML=cards('outsider');$('#spike-list').innerHTML=cards('spike');
  }
  function renderModel(){
    const target=$('#model-list'),note=$('#model-status');
    if(!model){target.innerHTML=empty('Modellranking inväntas','En tränad ranking visas när den stämmer med den aktuella startlistan.');note.textContent='Ingen verifierad modellranking för detta underlag.';return;}
    const t=model.training,m=model.validation.metrics;
    note.textContent='CatBoost · '+t.starts+' historiska starter i '+t.races+' lopp på '+t.dates+' tävlingsdagar. Träningsperiod '+t.from+'–'+t.until+'. Test på senare V85-dagar: vinnaren fanns bland de tre högst rankade i '+m.top3Count+' av '+m.races+' lopp ('+fmt(m.top3Rate*100)+' %). Förstahästen vann '+m.top1Count+' av '+m.races+' lopp. Beräknad '+stamp(model.generatedAt)+'. Historiskt lördagsurval; modellpoäng är inte kalibrerad vinstchans.';
    if(t.byGameType?.V75?.races)note.textContent+=' Träningen omfattar '+t.byGameType.V75.races+' V75-lopp och '+t.byGameType.V85.races+' V85-lopp; testmåtten avser enbart V85.';
    const market=model.validation.retrospectiveFinalPool,paired=model.validation.pairedModel;
    if(market?.races>0&&market.races===paired?.races)note.textContent+=' På samma '+market.races+' jämförelselopp: CatBoost topp 3 '+paired.top3Count+' träffar, slutstreckens topp 3 '+market.top3Count+' träffar. Slutstreck är retrospektiva och visar inte lönsamhet.';
    target.innerHTML=model.races.map(r=>'<article class="proposal-card"><div class="card-top"><strong>V85-'+r.leg+'</strong><span>CATBOOST</span></div><ol>'+r.top3.map(h=>'<li><strong>'+h.number+' '+esc(h.name)+'</strong></li>').join('')+'</ol><button class="button secondary" data-leg="'+r.leg+'">Granska loppet</button></article>').join('');
  }
  function renderRaces(){
    $('#race-tabs').innerHTML=Array.from({length:8},(_,i)=>'<button type="button" data-leg="'+(i+1)+'" aria-pressed="'+(leg===i+1)+'" '+(data.status!=='verified'?'disabled':'')+'>V85-'+(i+1)+'</button>').join('');
    for(const id of ['#horse-search','#horse-sort','#show-scratched'])$(id).disabled=data.status!=='verified';
    if(data.status!=='verified')return;
    const race=data.races.find(r=>r.leg===leg),query=$('#horse-search').value.trim().toLocaleLowerCase('sv-SE'),sort=$('#horse-sort').value;
    const horses=D.runners(data).filter(h=>h.leg===leg),ranked=horses.filter(h=>!h.scratched&&D.finite(h.pct)).sort((a,b)=>b.pct-a.pct);
    let rows=horses.filter(h=>(!h.scratched||$('#show-scratched').checked)&&(!query||[h.name,h.driver,String(h.number)].join(' ').toLocaleLowerCase('sv-SE').includes(query)));
    rows.sort((a,b)=>sort==='market'?(b.pct??-1)-(a.pct??-1):sort==='low'?(a.pct??101)-(b.pct??101):a.number-b.number);
    const proposals=D.picks(data,analysis);
    const formRace=form?.snapshotId===data.snapshotId?form.races.find(r=>r.leg===leg):null;
    const formHorses=(formRace?.horses||[]).filter(h=>!h.scratched&&D.finite(h.evidence?.partialRankScore)).sort((a,b)=>b.evidence.partialRankScore-a.evidence.partialRankScore);
    const modelRace=model?.races.find(r=>r.leg===leg);
    const modelSummary=modelRace?'<div class="data-notice"><strong>CatBoost · topp 3 kandidater</strong><p>'+modelRace.top3.map(h=>h.rank+'. '+h.number+' '+esc(h.name)).join(' → ')+'</p><p>Tränad på kompletta historiska lopp. Ranking, inte kalibrerad vinstchans. <a href="#modellranking">Se alla åtta lopp och testutfall</a>.</p></div>':'';
    const formSummary=formRace?'<div class="data-notice"><strong>Preliminär formranking</strong><p>'+esc(formHorses.map(h=>h.number+' '+h.name+' ('+fmt(h.evidence.partialRankScore)+' poäng, '+h.evidence.modelCoverageWeight+' % underlag)').join(' → ')||'Otillräckligt underlag för delranking')+'</p><p>Historisk delpoäng, inte vinstchans. Utrustning och faktisk spetschans är inte bedömda. Olika datatäckning gör poängen mindre jämförbara. Streck krävs för spelvärde.</p></div>':'';
    $('#race-panel').innerHTML='<div class="race-intro"><div><h3>V85-'+leg+(race.raceNumber?' · lopp '+esc(race.raceNumber):'')+'</h3><p>'+esc(race.distance?race.distance+' m':'Distans inväntas')+' · '+esc(race.startMethod==='auto'?'Autostart':race.startMethod==='volte'?'Voltstart':race.startMethod||'Startmetod inväntas')+' · '+horses.filter(h=>!h.scratched).length+' aktiva</p></div><p>Marknadens förstahäst: '+(ranked[0]?esc(ranked[0].number+' '+ranked[0].name)+' · '+fmt(ranked[0].pct)+' %':'Streck saknas')+'</p></div>'+modelSummary+formSummary+'<div class="horse-list">'+(rows.length?rows.map(h=>{
      const selected=state.selections[h.key],pick=proposals.find(p=>p.key===h.key),marketRank=ranked.findIndex(x=>x.key===h.key)+1;
      const assessment=formRace?.horses.find(x=>x.number===h.number&&x.name===h.name);
      const history=assessment?assessment.lastFive.map(x=>({date:x.date,description:(x.place===0?'Oplacerad':x.place===null?'Placering saknas':'Placering '+x.place)+(x.galloped===true?' · galopp':'')})):(Array.isArray(h.history)?h.history:[]);
      return '<article class="horse-card '+(selected?'is-selected ':'')+(h.scratched?'scratched':'')+'" data-horse="'+h.key+'"><div class="horse-main"><div class="horse-identity"><span class="horse-number">'+h.number+'</span><div><h4>'+esc(h.name)+(h.scratched?' · STRUKEN':'')+'</h4><p>'+esc(h.driver||'Kusk saknas')+' · Spår '+esc(h.postPosition??'–')+'</p>'+(pick?'<span class="pick-tag">'+(pick.type==='spike'?'Spikförslag':'Skrällförslag')+'</span>':'')+'</div></div><div class="horse-market"><b>'+fmt(h.pct)+' %</b><span>'+ (marketRank?'Marknadsrank '+marketRank:'Streck saknas')+'</span></div><label class="select-control"><input type="checkbox" data-select="'+h.key+'" '+(selected?'checked ':'')+(h.scratched?'disabled':'')+'> '+(selected?.role==='spike'?'Din spik':'Mitt urval')+'</label></div><details><summary>Form, uppgifter och bedömning</summary><dl><div><dt>Tränare</dt><dd>'+esc(h.trainer||'Uppgift saknas')+'</dd></div><div><dt>Vinnarodds</dt><dd>'+(h.oddsCapped?'Minst 99,99':fmt(h.odds,2))+'</dd></div><div><dt>Streckförändring</dt><dd>'+(D.finite(h.trend)?(h.trend>0?'+':'')+fmt(h.trend,2)+' procentenheter':'Uppgift saknas')+'</dd></div><div><dt>Historisk delranking</dt><dd>'+(D.finite(assessment?.evidence?.partialRankScore)?fmt(assessment.evidence.partialRankScore)+' poäng · '+assessment.evidence.modelCoverageWeight+' % av modellvikten · inte vinstchans':'Otillräckligt underlag')+'</dd></div></dl><p><strong>Historisk form:</strong> '+(history.length?history.map(x=>esc(x.date)+' · '+esc(x.description)).join('<br>'):'Inte verifierad i detta underlag.')+'</p><p>'+(pick?esc(pick.reason)+' Risk: '+esc(pick.risk):'Egen bedömning återstår. Streckandel och marknadsrank är inte en uppskattad vinstchans.')+'</p>'+(h.scratched?'':'<button class="small-button" data-action="spike" data-key="'+h.key+'">Gör till spik · ersätter övriga val i loppet</button>')+'</details></article>';
    }).join(''):empty('Inga hästar matchar filtret','Ändra sökningen eller visa strukna hästar.'))+'</div>';
  }
  function renderSelection(){
    const horses=D.runners(data),clean=D.cleanSelection(data,state.selections),total=D.totals(data,clean,state.stake);
    $('#selected-count').textContent=String(total.selected);
    $('#selection-list').innerHTML=total.selected?Array.from({length:8},(_,i)=>{
      const entries=horses.filter(h=>h.leg===i+1&&clean[h.key]);if(!entries.length)return '';
      return '<article class="selection-race"><h3>V85-'+(i+1)+' · '+entries.length+' vald'+(entries.length===1?' häst':'a hästar')+'</h3>'+entries.map(h=>'<div class="selection-horse"><div><strong>'+h.number+' '+esc(h.name)+'</strong>'+(clean[h.key].role==='spike'?'<br><span class="pick-tag">DIN SPIK</span>':'')+'</div><textarea maxlength="2000" rows="1" data-note="'+h.key+'" aria-label="Egen motivering för '+esc(h.name)+'" placeholder="Din motivering och viktigaste risk">'+esc(clean[h.key].note)+'</textarea><button class="small-button" data-action="remove" data-key="'+h.key+'" aria-label="Ta bort '+esc(h.name)+'">Ta bort</button></div>').join('')+'</article>';
    }).join(''):empty('Ditt urval börjar i loppen','Lägg till en häst från förslagen eller loppanalysen. Du kan sedan skriva egna motiveringar, välja spikar och exportera urvalet.');
    $('#system-summary').textContent=total.selected?(total.rows?fmt(total.rows,0)+' rader'+(total.cost!==null?' · '+fmt(total.cost,2)+' kr':' · ange radpris för kostnad'):total.counts.filter(n=>n>0).length+' av 8 avdelningar valda · radantal beräknas när alla lopp är täckta'):'Välj hästar för att bygga ditt urval.';
    $('#export-selection').disabled=!total.selected;
    $('#frozen-list').innerHTML=state.frozen.map((f,i)=>'<div class="frozen-entry"><span><strong>Fryst urval '+(i+1)+'</strong> · '+esc(stamp(f.frozenAt))+'<br><small>Bevarat underlag: '+esc(stamp(f.sourceAt))+'</small></span><button class="small-button" data-download="'+i+'">Ladda ner fryst kopia</button></div>').join('');
    renderStatus();
  }
  function renderAll(){renderModel();renderStatus();renderProposals();renderRaces();renderSelection();}
  try{
    const config=await get('./rounds.json');round=config.rounds.find(r=>r.id===config.current);if(!round)throw Error('Aktuell omgång saknas.');
    data=D.validate(await get('./'+round.data),round);
    try{analysis=await get('./'+round.analysis);}catch{analysis=null;analysisUnavailable=true;}
    try{form=await get('./rounds/'+round.id+'/form.json');}catch{form=null;}
    try{model=window.V85Model.validate(await get('./rounds/'+round.id+'/model.json'),data);}catch{model=null;}
    const day=new Date(round.date+'T12:00:00+01:00');
    $('#round-track').textContent=round.track+'.';$('#hero-date').textContent=day.toLocaleDateString('sv-SE',{timeZone:'Europe/Stockholm',day:'numeric',month:'long',year:'numeric'}).toUpperCase();
    $('#round-date').textContent=day.toLocaleDateString('sv-SE',{timeZone:'Europe/Stockholm',weekday:'long',day:'numeric',month:'long'});
    document.title=round.track+' '+$('#round-date').textContent+' · Skrällar & spikar | LA_V85';
    if(/^https:\/\/www\.atg\.se\//.test(round.sourceUrl))$('#official-link').href=round.sourceUrl;
    storageKey='LA_V85_SELECTION_'+round.id;
    try{const stored=JSON.parse(localStorage.getItem(storageKey)||'null');if(stored&&typeof stored==='object')state={selections:stored.selections||{},stake:D.finite(stored.stake)&&stored.stake>0?stored.stake:null,frozen:Array.isArray(stored.frozen)?stored.frozen.filter(f=>f?.kind==='LOCAL_PRESTART_SELECTION'&&f.roundId===round.id&&D.instant(f.frozenAt)):[]};}catch{}
    if(data.status==='verified'){
      const clean=D.cleanSelection(data,state.selections);
      if(Object.keys(clean).length!==Object.keys(state.selections).length)$('#action-status').textContent='Strukna eller borttagna hästar har tagits bort ur arbetsurvalet. Frysta kopior bevaras.';
      state.selections=clean;save();
    }
    $('#row-price').value=state.stake??'';
    renderAll();
    document.addEventListener('click',e=>{
      const target=e.target.closest('button');if(!target)return;
      if(target.dataset.leg){leg=Number(target.dataset.leg);$('#horse-search').value='';renderRaces();if(!target.closest('#race-tabs'))$('#loppen').scrollIntoView({behavior:'smooth'});}
      if(target.dataset.action){state.selections=D.select(data,state.selections,target.dataset.key,target.dataset.action);save();renderAll();}
      if(target.dataset.download!==undefined){const f=state.frozen[Number(target.dataset.download)];if(f)exportJSON(f,round.id+'-fryst-'+f.frozenAt.replace(/[:.]/g,'-')+'.json');}
    });
    document.addEventListener('change',e=>{if(e.target.dataset.select){state.selections=D.select(data,state.selections,e.target.dataset.select,e.target.checked?'include':'remove');save();renderAll();}});
    document.addEventListener('input',e=>{if(e.target.dataset.note&&state.selections[e.target.dataset.note]){state.selections[e.target.dataset.note].note=e.target.value.slice(0,2000);save();}});
    $('#outsider-limit').addEventListener('change',renderProposals);
    $('#horse-search').addEventListener('input',renderRaces);
    $('#horse-sort').addEventListener('change',renderRaces);
    $('#show-scratched').addEventListener('change',renderRaces);
    $('#row-price').addEventListener('input',e=>{const n=Number(e.target.value);state.stake=n>0&&D.finite(n)?n:null;save();renderSelection();});
    $('#export-selection').addEventListener('click',()=>exportJSON({schemaVersion:1,kind:'WORKING_SELECTION',roundId:round.id,exportedAt:new Date().toISOString(),sourceAt:data.sourceAt,snapshotId:data.snapshotId,selections:D.cleanSelection(data,state.selections),unitStakeSEK:state.stake,totals:D.totals(data,state.selections,state.stake)},round.id+'-urval.json'));
    $('#freeze-selection').addEventListener('click',()=>{
      try{
        const frozen=D.freeze(data,analysis,state.selections,state.stake);
        state.frozen.push(frozen);const persisted=save();renderSelection();
        exportJSON(frozen,round.id+'-fryst-'+frozen.frozenAt.replace(/[:.]/g,'-')+'.json');
        $('#action-status').textContent=persisted?'Urvalet är fryst och nedladdat. Senare ändringar påverkar inte kopian.':'Fryst kopia har laddats ner. Lokal lagring misslyckades; behåll filen.';
      }catch(err){$('#action-status').textContent=err.message;}
    });
    setInterval(renderStatus,30000);
    if(location.hash==='#tvastegsmodell')location.replace('./metod/#egen-bedomning');
  }catch(err){
    $('#data-status').className='data-notice error';
    $('#data-status').textContent=err.message+' Förslag visas först när rätt omgång kan verifieras. Försök ladda om sidan.';
    $('#round-phase').textContent='Data kunde inte verifieras';
    for(const id of ['#outsider-limit','#horse-search','#horse-sort','#show-scratched','#row-price'])$(id).disabled=true;
    $('#outsider-list').innerHTML=empty('Förslagen kan inte verifieras','Ladda om sidan eller kontrollera omgången hos ATG.');
    $('#spike-list').innerHTML=empty('Förslagen kan inte verifieras','Ingen spik visas utan verifierat underlag för rätt omgång.');
  }
})();
