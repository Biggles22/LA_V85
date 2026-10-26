(function modelApp() {
  'use strict';
  const mount=document.getElementById('bjerke-model-workspace');
  if(!mount)return;
  const CATS=[
    {key:'form',label:'Form',weight:30},
    {key:'pace',label:'Loppbild',weight:25},
    {key:'class',label:'Distans/klass',weight:20},
    {key:'gear',label:'Kusk/utrustning',weight:15},
    {key:'risk',label:'Dagsform/risk',weight:10}
  ];
  const STORE='LA_V85_BJERKE_20261031_TWO_STEP_V1';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('sv-SE',{minimumFractionDigits:1,maximumFractionDigits:1}):'–';
  let data=null,leg=1,answers={},formData=null;
  try{const stored=JSON.parse(localStorage.getItem(STORE)||'{}');if(stored&&typeof stored==='object'&&!Array.isArray(stored))answers=stored}catch(e){}
  function save(){try{localStorage.setItem(STORE,JSON.stringify(answers))}catch(e){}}
  const key=(r,h)=>`${r.leg}-${h.number}`;
  function validScore(v){return typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=5}
  function validProbability(v){return typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=100}
  function automatic(r,h){
    const rr=formData?.races?.find(x=>x.leg===r.leg);
    const item=rr?.horses?.find(x=>x.number===h.number&&x.name===h.name);
    if(!item||item.scratched)return {};
    const found={};
    for(const cat of ['form','risk'])if(validScore(item.scores?.[cat]))found[cat]=item.scores[cat];
    return found;
  }
  function effective(r,h){return {...automatic(r,h),...(answers[key(r,h)]||{})};}
  function score(a){
    if(!a||!CATS.every(c=>validScore(a[c.key])))return null;
    return CATS.reduce((sum,c)=>sum+a[c.key]*c.weight/5,0);
  }
  function race(){return data.races.find(r=>r.leg===leg)}
  function rankRows(r){
    const active=r.starts.filter(h=>!h.scratched);
    const result=active.map(h=>({h,a:effective(r,h),s:score(effective(r,h))}));
    const complete=result.every(x=>x.s!=null);
    const sorted=[...result].filter(x=>x.s!=null).sort((a,b)=>b.s-a.s);
    const ranks=new Map();
    if(complete)sorted.forEach((x,i)=>ranks.set(x.h.number,1+sorted.findIndex(y=>y.s===x.s)));
    return {result,complete,ranks};
  }
  function probabilityReady(r){
    const horses=r.starts.filter(h=>!h.scratched);
    const assessed=horses.map(h=>({h,a:answers[key(r,h)]||{}}));
    const complete=assessed.every(x=>validProbability(x.a.probability));
    const sum=assessed.reduce((v,x)=>v+(validProbability(x.a.probability)?x.a.probability:0),0);
    return {complete,sum,ready:complete&&Math.abs(sum-100)<=0.5,count:assessed.filter(x=>validProbability(x.a.probability)).length};
  }
  function valueLabel(pct,p,ready){
    if(!ready||typeof pct!=='number'||!validProbability(p))return 'Ej bedömt';
    const diff=p-pct;
    if(pct>0&&diff>=2&&p>=pct*1.2)return 'Möjligt spelvärde';
    if(diff<=-3&&p<=pct*0.85)return 'Risk för överstreckning';
    return 'Ungefär neutral';
  }
  function scoreField(h,r,a,c){
    return `<input class="model-score-input${validScore(automatic(r,h)[c.key])&&!Object.hasOwn(answers[key(r,h)]||{},c.key)?' model-auto-score':''}" type="number" min="0" max="5" step="0.1" inputmode="decimal" data-key="${esc(key(r,h))}" data-field="${c.key}" value="${validScore(a[c.key])?a[c.key]:''}" aria-label="V85-${r.leg} ${esc(h.name)}: ${c.label} 0–5" title="${c.label}: 0–5 (tomt om underlag saknas)">`;
  }
  function table(){
    const r=race(), ranking=rankRows(r),prob=probabilityReady(r);
    const done=ranking.result.filter(x=>x.s!=null).length;
    const status=`<p class="model-status"><strong>Steg A:</strong> ${done} av ${ranking.result.length} hästar poängsatta. ${ranking.complete?'Fullständig inbördes poängranking kan visas.':'Ingen fullständig ranking innan alla aktiva hästar bedömts.'}</p>
      <p class="model-status"><strong>Steg B:</strong> ${prob.count} av ${ranking.result.length} har egen uppskattad vinstchans; summa ${fmt(prob.sum)} %. ${prob.ready?'Spelvärdesskillnaden kan visas.':'För jämförbart spelvärde krävs uppskattningar för alla aktiva hästar och totalt 100 % (±0,5 procentenheter).'}</p>`;
    const rows=r.starts.map(h=>{
      const a=effective(r,h),s=score(a),p=a.probability;
      const rawDiff=prob.ready&&typeof h.pct==='number'&&validProbability(p)?p-h.pct:null;
      return `<tr${h.scratched?' class="withdrawn"':''}>
        <td class="model-horse"><strong>${h.number} ${esc(h.name)}</strong><small>${h.scratched?'STRUKEN':`Spår ${h.postPosition??'–'}`}</small></td>
        <td class="number-cell">${typeof h.pct==='number'?fmt(h.pct)+' %':'–'}</td>
        ${CATS.map(c=>`<td>${h.scratched?'–':scoreField(h,r,a,c)}</td>`).join('')}
        <td class="number-cell">${s==null?'–':fmt(s)+' / 100'}${ranking.ranks.has(h.number)?`<small>Rank ${ranking.ranks.get(h.number)}</small>`:''}</td>
        <td>${h.scratched?'–':`<input class="model-prob-input" type="number" min="0" max="100" step="0.1" inputmode="decimal" data-key="${esc(key(r,h))}" data-field="probability" value="${validProbability(p)?p:''}" aria-label="V85-${r.leg} ${esc(h.name)}: egen uppskattad vinstchans i procent" title="Egen uppskattning 0–100 %, separat från poäng">`}</td>
        <td class="model-value">${rawDiff==null?'–':(rawDiff>=0?'+':'')+fmt(rawDiff)+' p.e.'}<small>${valueLabel(h.pct,p,prob.ready)}</small></td>
      </tr>`;
    }).join('');
    document.getElementById('bjerke-model-body').innerHTML=rows;
    document.getElementById('bjerke-model-summary').innerHTML=status;
  }
  function render(){
    mount.innerHTML=`<div class="model-toolbar"><label for="bjerke-model-leg">Välj avdelning</label>
      <select id="bjerke-model-leg">${data.races.map(r=>`<option value="${r.leg}"${r.leg===leg?' selected':''}>V85-${r.leg} (${r.starts.filter(h=>!h.scratched).length} aktiva)</option>`).join('')}</select>
      <button type="button" id="bjerke-model-clear" class="model-clear">Rensa enbart V85-${leg}</button></div>
      <div id="bjerke-model-summary" role="status" aria-live="polite"></div>
      <div class="model-table-scroll"><table class="model-table"><thead><tr><th>Häst</th><th>V85 %</th>
      ${CATS.map(c=>`<th title="Vikt ${c.weight} %">${c.label}<small>${c.weight} %</small></th>`).join('')}
      <th>Vägd poäng</th><th>Egen vinstchans %</th><th>Skillnad mot streck</th></tr></thead><tbody id="bjerke-model-body"></tbody></table></div>
      <p class="model-footnote">0–5 poäng per kategori (5 = starkast, för risk 5 = lägst risk). Vägd poäng är endast ett rangordningsstöd – <strong>inte</strong> en statistiskt kalibrerad vinstchans. Den egna procentbedömningen fylls separat. Alla egna noteringar lagras endast i den här webbläsaren, inte på GitHub. Värdeetiketterna är en arbetsregel som behöver utvärderas mot flera omgångar.</p>`;
    document.getElementById('bjerke-model-leg').addEventListener('change',e=>{leg=Number(e.target.value);render()});
    document.getElementById('bjerke-model-clear').addEventListener('click',()=>{
      if(!confirm(`Rensa alla egna bedömningar för V85-${leg}?`))return;
      for(const h of race().starts)delete answers[key(race(),h)];
      save();table();
    });
    mount.querySelector('table').addEventListener('change',e=>{
      const inp=e.target;
      if(!inp.matches('input[data-key][data-field]'))return;
      const k=inp.dataset.key,f=inp.dataset.field,v=inp.value.trim().replace(',','.');
      if(!answers[k]||typeof answers[k]!=='object')answers[k]={};
      if(v===''){delete answers[k][f]}
      else {
        const n=Number(v);
        if(f==='probability'?validProbability(n):validScore(n))answers[k][f]=n;
        else {alert(f==='probability'?'Ange en procent mellan 0 och 100.':'Ange en poäng mellan 0 och 5.');return;}
      }
      save();table();
    });
    table();
  }
  fetch('./bjerke-form-20261031.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{
    if(d?.gameId!=='V85_2026-10-31_78_5'||!Array.isArray(d?.races)||d.races.length!==8)return;
    formData=d;
    if(data) table();
  }).catch(()=>{});
  fetch('./bjerke-20261031.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Kan inte hämta ATG-filen');return r.json()}).then(d=>{
    if(d.gameId!=='V85_2026-10-31_78_5'||!Array.isArray(d.races)||d.races.length!==8)throw Error('Fel omgång');
    data=d;render();
  }).catch(e=>{mount.innerHTML='<p class="work-note">Arbetsmodellen kunde inte läsa Bjerkes senaste ATG-snapshot. Försök ladda om sidan.</p>';console.warn(e)});
})();
