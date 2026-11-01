(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.V85Domain=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const finite=n=>typeof n==='number'&&Number.isFinite(n);
  const key=(leg,number)=>leg+'-'+number;
  const instant=s=>typeof s==='string'&&/[TZ]/.test(s)&&/(Z|[+-]\d{2}:\d{2})$/.test(s)&&Number.isFinite(Date.parse(s));
  function validate(data,round){
    if(data?.schemaVersion!==1||data.roundId!==round.id||data.date!==round.date||data.track!==round.track)throw Error('Datakällan gäller en annan omgång.');
    if(data.status==='awaiting_data'&&Array.isArray(data.races)&&data.races.length===0)return data;
    if(data.status!=='verified'||!data.gameId?.startsWith('V85_'+round.date+'_')||!instant(data.sourceAt)||!instant(data.retrievedAt)||!instant(data.startTime)||!data.snapshotId)throw Error('Omgångens identitet eller källtid kunde inte verifieras.');
    if(!Array.isArray(data.races)||data.races.length!==8)throw Error('Startlistan måste innehålla åtta avdelningar.');
    const legs=new Set();
    for(const race of data.races){
      if(!Number.isInteger(race.leg)||race.leg<1||race.leg>8||legs.has(race.leg)||!Array.isArray(race.starts)||!race.starts.length)throw Error('Ogiltig avdelning.');
      legs.add(race.leg);const numbers=new Set();
      for(const horse of race.starts){
        if(!Number.isInteger(horse.number)||horse.number<1||numbers.has(horse.number)||typeof horse.name!=='string'||!horse.name.trim()||typeof horse.scratched!=='boolean')throw Error('Ogiltig häst i startlistan.');
        numbers.add(horse.number);
        if(horse.pct!==null&&(!finite(horse.pct)||horse.pct<0||horse.pct>100))throw Error('Ogiltig streckandel.');
      }
    }
    return data;
  }
  function phase(data,now=Date.now()){
    if(data.status!=='verified')return 'awaiting';
    if(now>=Date.parse(data.startTime))return 'closed';
    return now-Date.parse(data.sourceAt)>6*3600e3?'stale':'open';
  }
  function runners(data){return (data.races||[]).flatMap(r=>r.starts.map(h=>({...h,leg:r.leg,key:key(r.leg,h.number)})));}
  function picks(data,analysis){
    if(data.status!=='verified'||analysis?.roundId!==data.roundId||analysis.gameId!==data.gameId||analysis.snapshotId!==data.snapshotId||!instant(analysis.reviewedAt)||Date.parse(analysis.reviewedAt)>=Date.parse(data.startTime))return [];
    const horses=runners(data),seen=new Set();
    return (Array.isArray(analysis.picks)?analysis.picks:[]).flatMap(p=>{
      if(!p||typeof p!=='object')return [];
      const h=horses.find(h=>h.leg===p.leg&&h.number===p.number&&h.name===p.name);
      if(!h||h.scratched||seen.has(h.key)||!['outsider','spike'].includes(p.type)||typeof p.reason!=='string'||!p.reason.trim()||typeof p.risk!=='string'||!p.risk.trim()||!Array.isArray(p.sources)||!p.sources.length||!p.sources.every(url=>typeof url==='string'&&/^https:\/\//.test(url)))return [];
      if(p.type==='spike'){
        const alternatives=horses.filter(x=>x.leg===h.leg&&x.number!==h.number&&!x.scratched);
        const challengers=Array.isArray(p.challengers)?new Set(p.challengers):new Set();
        if(alternatives.filter(x=>challengers.has(x.name)).length<Math.min(2,alternatives.length))return [];
      }
      seen.add(h.key);return [{...h,...p}];
    });
  }
  function cleanSelection(data,input){
    const valid=new Set(runners(data).filter(h=>!h.scratched).map(h=>h.key)),out={};
    if(!input||typeof input!=='object')return out;
    for(const [k,v] of Object.entries(input))if(valid.has(k)&&v&&typeof v==='object')out[k]={note:typeof v.note==='string'?v.note.slice(0,2000):'',role:v.role==='spike'?'spike':'include'};
    for(const race of data.races||[]){
      const keys=Object.keys(out).filter(k=>k.startsWith(race.leg+'-'));
      if(keys.length>1)for(const k of keys)out[k].role='include';
    }
    return out;
  }
  function select(data,selection,horseKey,action){
    const out=cleanSelection(data,selection),h=runners(data).find(x=>x.key===horseKey&&!x.scratched);
    if(!h)return out;
    if(action==='remove')delete out[horseKey];
    else{
      const note=out[horseKey]?.note||'';
      if(action==='spike'){for(const k of Object.keys(out))if(k.startsWith(h.leg+'-'))delete out[k];}
      else{for(const k of Object.keys(out))if(k.startsWith(h.leg+'-'))out[k].role='include';}
      out[horseKey]={note,role:action==='spike'?'spike':'include'};
    }
    return out;
  }
  function totals(data,selection,stake){
    const clean=cleanSelection(data,selection),counts=Array.from({length:8},(_,i)=>Object.keys(clean).filter(k=>k.startsWith((i+1)+'-')).length);
    const rows=counts.every(n=>n>0)?counts.reduce((a,b)=>a*b,1):0;
    return {counts,rows,cost:rows&&finite(stake)&&stake>0?Math.round(rows*stake*100)/100:null,selected:Object.keys(clean).length};
  }
  function freeze(data,analysis,selection,stake,now=Date.now()){
    if(data.status!=='verified'||!instant(data.startTime)||now>=Date.parse(data.startTime))throw Error('Urval kan bara frysas med verifierad starttid och före spelstopp.');
    const clean=cleanSelection(data,selection);
    if(!Object.keys(clean).length)throw Error('Välj minst en häst först.');
    return {schemaVersion:1,kind:'LOCAL_PRESTART_SELECTION',roundId:data.roundId,gameId:data.gameId,frozenAt:new Date(now).toISOString(),sourceAt:data.sourceAt,snapshotId:data.snapshotId,analysisVersion:analysis?.version??null,selections:clean,unitStakeSEK:finite(stake)&&stake>0?stake:null,totals:totals(data,clean,stake),marketSnapshot:JSON.parse(JSON.stringify(data)),analysisSnapshot:JSON.parse(JSON.stringify(analysis||{})),timestampNote:'Lokalt skapad kopia; tidpunkten är inte verifierad av en server. Detta är inte ett inlämningskvitto.'};
  }
  return {finite,key,instant,validate,phase,runners,picks,cleanSelection,select,totals,freeze};
});
