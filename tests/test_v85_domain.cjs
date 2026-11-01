const test=require('node:test'),assert=require('node:assert/strict');
const D=require('../v85-domain.js');
const round={id:'2026-11-07-bergsaker',date:'2026-11-07',track:'Bergsåker'};
function snapshot(){
 return {schemaVersion:1,roundId:round.id,date:round.date,track:round.track,status:'verified',gameId:'V85_2026-11-07_9_5',snapshotId:'synthetic-test-snapshot',sourceAt:'2026-11-02T11:00:00+01:00',retrievedAt:'2026-11-02T11:01:00+01:00',startTime:'2026-11-07T15:00:00+01:00',races:Array.from({length:8},(_,i)=>({leg:i+1,starts:[{number:1,name:'Testhäst '+(i+1),scratched:false,pct:15},{number:2,name:'Testfavorit '+(i+1),scratched:false,pct:85}]}))};
}
function analysis(d){return {roundId:round.id,gameId:d.gameId,snapshotId:d.snapshotId,version:1,reviewedAt:'2026-11-02T11:05:00+01:00',picks:[{leg:1,number:1,name:'Testhäst 1',type:'outsider',reason:'Syntetisk testmotivering.',risk:'Syntetisk testrisk.',sources:['https://www.atg.se/']}]};}
test('validate complete round, reject wrong track or duplicate runners',()=>{
 const d=snapshot();assert.equal(D.validate(d,round),d);
 assert.throws(()=>D.validate({...d,track:'Bjerke'},round));
 d.races[0].starts.push(d.races[0].starts[0]);assert.throws(()=>D.validate(d,round));
});
test('absent data cannot produce runners or proposals',()=>{
 const d={...snapshot(),status:'awaiting_data',races:[]};
 assert.equal(D.validate(d,round),d);assert.equal(D.phase(d),'awaiting');assert.deepEqual(D.picks(d,analysis(d)),[]);
});
test('closed and stale data are visibly distinguishable',()=>{
 const d=snapshot();assert.equal(D.phase(d,Date.parse(d.sourceAt)+5*3600e3),'open');
 assert.equal(D.phase(d,Date.parse(d.sourceAt)+7*3600e3),'stale');assert.equal(D.phase(d,Date.parse(d.startTime)),'closed');
});
test('proposals require matching reviewed snapshot, horse identity and evidence',()=>{
 const d=snapshot(),a=analysis(d);assert.equal(D.picks(d,a).length,1);
 for(const change of [{snapshotId:'old'},{gameId:'other'},{reviewedAt:d.startTime}])assert.equal(D.picks(d,{...a,...change}).length,0);
 a.picks[0].risk='';assert.equal(D.picks(d,a).length,0);
 a.picks[0].risk='test';a.picks[0].name='Different';assert.equal(D.picks(d,a).length,0);
});
test('scratched horses are removed from proposals and editable selections',()=>{
 const d=snapshot(),a=analysis(d);d.races[0].starts[0].scratched=true;
 assert.deepEqual(D.picks(d,a),[]);assert.deepEqual(D.cleanSelection(d,{'1-1':{note:'old'},'2-1':{note:'keep'}}),{'2-1':{note:'keep',role:'include'}});
});
test('spikes require reviewed active challengers; malformed picks are ignored',()=>{
 const d=snapshot(),a=analysis(d);a.picks[0].type='spike';
 assert.equal(D.picks(d,a).length,0);
 a.picks[0].challengers=['Testfavorit 1'];assert.equal(D.picks(d,a).length,1);
 d.races[0].starts.push({number:3,name:'Tredje testhästen',pct:5,scratched:false});
 assert.equal(D.picks(d,a).length,0);
 a.picks[0].challengers.push('Tredje testhästen');assert.equal(D.picks(d,a).length,1);
 a.picks.push(null,{reason:42});assert.equal(D.picks(d,a).length,1);
 a.picks[0].risk=42;assert.equal(D.picks(d,a).length,0);
});
test('spiking replaces other runners in that race and preserves other races',()=>{
 const d=snapshot();let s=D.select(d,{},'1-1','include');s=D.select(d,s,'2-1','include');s=D.select(d,s,'1-2','spike');
 assert.equal(s['1-1'],undefined);assert.equal(s['1-2'].role,'spike');assert.ok(s['2-1']);
 s=D.select(d,s,'1-1','include');assert.equal(s['1-2'].role,'include');
});
test('system row count is product of eight legs, no fabricated price',()=>{
 const d=snapshot();let s={};for(let leg=1;leg<=8;leg++)s=D.select(d,s,leg+'-1','include');
 s=D.select(d,s,'1-2','include');assert.equal(D.totals(d,s,null).rows,2);assert.equal(D.totals(d,s,null).cost,null);
 assert.equal(D.totals(d,s,.5).cost,1);delete s['8-1'];assert.equal(D.totals(d,s,.5).rows,0);
});
test('prestart freeze is immutable and preserves the actual market snapshot',()=>{
 const d=snapshot(),a=analysis(d),s={'1-1':{note:'Original',role:'include'}};
 const frozen=D.freeze(d,a,s,.5,Date.parse('2026-11-02T12:00:00+01:00'));
 s['1-1'].note='Changed';d.races[0].starts[0].pct=99;a.picks[0].reason='Changed';
 assert.equal(frozen.selections['1-1'].note,'Original');assert.equal(frozen.marketSnapshot.races[0].starts[0].pct,15);assert.notEqual(frozen.analysisSnapshot.picks[0].reason,'Changed');
});
test('freeze refuses empty selections, unverified time and elapsed start',()=>{
 const d=snapshot(),a=analysis(d),s={'1-1':{}};
 assert.throws(()=>D.freeze(d,a,{},.5,Date.parse(d.sourceAt)));
 assert.throws(()=>D.freeze(d,a,s,.5,Date.parse(d.startTime)));
 assert.throws(()=>D.freeze({...d,startTime:null},a,s,.5,Date.parse(d.sourceAt)));
});
module.exports={snapshot,analysis,round};
