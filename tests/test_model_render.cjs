const assert=require('node:assert/strict'),fs=require('node:fs');
const scriptVersion=require('node:crypto').createHash('sha256').update(fs.readFileSync('v85.js')).digest('hex').slice(0,12);
assert.ok(fs.readFileSync('index.html','utf8').includes('v85.js?v='+scriptVersion),'Homepage must change the script URL when rendering code changes');
const config=JSON.parse(fs.readFileSync('rounds.json','utf8'));
const current=config.rounds.find(r=>r.id===config.current);
const model=JSON.parse(fs.readFileSync('rounds/'+current.id+'/model.json','utf8'));
const vm=require('node:vm'),D=require('../v85-domain.js'),M=require('../v85-model.js');
const elements=new Map(),events={};
function element(id){if(!elements.has(id))elements.set(id,{value:id==='#outsider-limit'?'20':id==='#horse-sort'?'number':'',checked:false,innerHTML:'',textContent:'',className:'',addEventListener(){},scrollIntoView(){}});return elements.get(id);}
const context={window:{V85Domain:D,V85Model:M},document:{querySelector:element,addEventListener:(type,fn)=>events[type]=fn},fetch:async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(String(url).replace(/^\.\//,''),'utf8'))}),localStorage:{getItem(){return null},setItem(){}},location:{hash:''},setInterval(){},setTimeout,Date,URL,Blob,console};
(async()=>{
await vm.runInNewContext(fs.readFileSync('v85.js','utf8'),context);
assert.ok(!element('#data-status').className.includes('error'));
assert.equal((element('#model-list').innerHTML.match(/<article /g)||[]).length,8);
assert.equal((element('#model-list').innerHTML.match(/<li>/g)||[]).length,24);
const metrics=model.validation.metrics;
assert.ok(element('#model-status').textContent.includes(`${metrics.top3Count} av ${metrics.races}`));
assert.ok(element('#model-status').textContent.includes(`${metrics.top1Count} av ${metrics.races}`));
assert.ok(element('#model-status').textContent.includes(`slutstreckens topp 3 ${model.validation.retrospectiveFinalPool.top3Count} träffar`));
assert.match(element('#race-panel').innerHTML,/CatBoost · topp 3/);
for(let leg=1;leg<=8;leg++){
events.click({target:{closest:()=>({dataset:{leg:String(leg)},closest:()=>true})}});
for(const h of model.races.find(r=>r.leg===leg).top3)assert.ok(element('#race-panel').innerHTML.includes(h.name.replaceAll('&','&amp;').replaceAll("'",'&#39;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;')));
}
console.log('PASS: real app renders eight model cards, 24 candidates, both test metrics and all race tabs');
})().catch(e=>{console.error(e);process.exitCode=1;});
