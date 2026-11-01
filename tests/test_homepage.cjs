/* Browser regression check. Synthetic responses stay in this test context only.
 * Requires Playwright and a local static server. Run:
 * node tests/test_homepage.cjs
 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.LA_V85_TEST_URL||'http://127.0.0.1:8001/';
const round={id:'2026-11-07-bergsaker',date:'2026-11-07',track:'Bergsåker'};
const data={schemaVersion:1,roundId:round.id,date:round.date,track:round.track,status:'verified',gameId:'V85_2026-11-07_9_5',snapshotId:'synthetic-test-only',sourceAt:'2026-11-02T11:00:00+01:00',retrievedAt:'2026-11-02T11:01:00+01:00',startTime:'2026-11-07T15:00:00+01:00',races:Array.from({length:8},(_,i)=>({leg:i+1,raceNumber:i+5,distance:2140,startMethod:'auto',starts:[{number:1,name:'Testhäst '+(i+1),driver:'Testkusk',scratched:false,pct:15,postPosition:1,history:[]},{number:2,name:'Testfavorit '+(i+1),driver:'Testkusk',scratched:false,pct:85,postPosition:2,history:[]}]}))};
const analysis={schemaVersion:1,roundId:round.id,gameId:data.gameId,snapshotId:data.snapshotId,version:1,reviewedAt:'2026-11-02T11:05:00+01:00',picks:[{leg:1,number:1,name:'Testhäst 1',type:'outsider',reason:'Syntetiskt vinnarargument för webbläsartest.',risk:'Syntetisk risk.',sources:['https://www.atg.se/']},{leg:2,number:2,name:'Testfavorit 2',type:'spike',reason:'Syntetisk granskning av testfavoriten.',risk:'Syntetisk risk.',challengers:['Testhäst 2'],sources:['https://www.atg.se/']}]};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.LA_V85_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  // First verify the actual published inputs, without substituting any horses.
  const real=await browser.newContext({viewport:{width:390,height:844},timezoneId:'Europe/Stockholm'});
  const realPage=await real.newPage(),realErrors=[];
  realPage.on('pageerror',e=>realErrors.push(e.message));
  await realPage.goto(base,{waitUntil:'networkidle'});
  assert.match(await realPage.locator('h1').innerText(),/Bergsåker/);
  assert.equal(await realPage.locator('h2#outsiders-title').innerText(),'Skrällförslag');
  assert.equal(await realPage.locator('h2#spikes-title').innerText(),'Spikförslag');
  assert.equal(await realPage.evaluate(()=>document.documentElement.scrollWidth),390);
  assert.deepEqual(realErrors,[]);
  console.log('PASS: actual Bergsåker page, clear proposal sections, mobile width, no runtime errors');
  await real.close();
  const context=await browser.newContext({viewport:{width:390,height:844},timezoneId:'Europe/Stockholm'});
  let currentData=structuredClone(data),currentAnalysis=structuredClone(analysis);
  await context.route('**/rounds/2026-11-07-bergsaker/data.json',route=>route.fulfill({json:currentData}));
  await context.route('**/rounds/2026-11-07-bergsaker/analysis.json',route=>route.fulfill({json:currentAnalysis}));
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install({time:new Date('2026-11-02T11:10:00+01:00')});
  await page.goto(base,{waitUntil:'networkidle'});
  assert.equal(await page.locator('#outsider-list .proposal-card').count(),1);
  assert.equal(await page.locator('#spike-list .proposal-card').count(),1);
  await page.selectOption('#outsider-limit','10');
  assert.equal(await page.locator('#outsider-list .proposal-card').count(),0);
  await page.selectOption('#outsider-limit','20');
  await page.locator('#outsider-list [data-action="include"]').click();
  assert.equal(await page.locator('#selected-count').textContent(),'1');
  await page.locator('#race-tabs [data-leg="1"]').click();
  await page.locator('[data-select="1-2"]').check();
  await page.locator('[data-horse="1-2"] summary').click();
  await page.locator('[data-action="spike"][data-key="1-2"]').click();
  assert.equal(await page.locator('[data-select="1-1"]').isChecked(),false);
  assert.equal(await page.locator('[data-select="1-2"]').isChecked(),true);
  for(let leg=2;leg<=8;leg++){
    await page.locator('#race-tabs [data-leg="'+leg+'"]').click();
    await page.locator('[data-select="'+leg+'-1"]').check();
  }
  await page.fill('#row-price','0.50');
  assert.match(await page.locator('#system-summary').innerText(),/1 rader · 0,5 kr/);
  await page.fill('[data-note="1-2"]','Sparad testmotivering');
  await page.reload({waitUntil:'networkidle'});
  assert.equal(await page.locator('[data-note="1-2"]').inputValue(),'Sparad testmotivering');
  assert.equal(await page.locator('#selected-count').textContent(),'8');
  let downloadPromise=page.waitForEvent('download');
  await page.click('#freeze-selection');
  const download=await downloadPromise;
  const frozen=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  assert.equal(frozen.kind,'LOCAL_PRESTART_SELECTION');assert.equal(frozen.snapshotId,data.snapshotId);
  assert.equal(frozen.selections['1-2'].note,'Sparad testmotivering');
  assert.equal(frozen.totals.rows,1);
  await page.fill('[data-note="1-2"]','Ändrad arbetskopia');
  downloadPromise=page.waitForEvent('download');
  await page.locator('[data-download="0"]').click();
  assert.equal(JSON.parse(fs.readFileSync(await (await downloadPromise).path(),'utf8')).selections['1-2'].note,'Sparad testmotivering');
  console.log('PASS: proposals, streck filter, exclusive spike, eight-leg cost, persisted notes and immutable downloaded freeze');
  currentData.races[0].starts[1].scratched=true;currentData.snapshotId='new-snapshot';
  await page.reload({waitUntil:'networkidle'});
  assert.equal(await page.locator('#selected-count').textContent(),'7');
  assert.equal(await page.locator('#frozen-list .frozen-entry').count(),1);
  assert.equal(await page.locator('.proposal-card').count(),0);
  assert.match(await page.locator('#action-status').innerText(),/Strukna/);
  await page.clock.setFixedTime(new Date(data.startTime));
  await page.reload({waitUntil:'networkidle'});
  assert.equal(await page.locator('#freeze-selection').isDisabled(),true);
  assert.match(await page.locator('#round-phase').innerText(),/Spelstopp/);
  console.log('PASS: changed snapshots invalidate proposals, scratches update working selections, old freezes survive, post-start freezing blocked');
  currentData={...data,roundId:'wrong-round'};
  await page.reload({waitUntil:'networkidle'});
  assert.match(await page.locator('#data-status').innerText(),/annan omgång/);
  assert.equal(await page.locator('.proposal-card').count(),0);
  assert.equal(await page.locator('#freeze-selection').isDisabled(),true);
  assert.deepEqual(errors,[]);
  console.log('PASS: wrong-round data fails closed without JavaScript errors');
  await context.close();
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
