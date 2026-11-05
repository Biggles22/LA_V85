// Credentials arrive over stdin, never command-line arguments or browser storage.
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const config=JSON.parse(fs.readFileSync(0,'utf8'));
 const origin='https://v75travet.se';
 if(new URL(config.url).origin!==origin)throw Error('Unapproved origin');
 const browser=await chromium.launch({headless:true,executablePath:process.env.LA_V85_CHROMIUM||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  fs.mkdirSync(config.outputDir,{recursive:true});
  for(const width of [390,1280]){
   const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
   await context.route('**/*',async route=>{
    const request=route.request(),headers={...request.headers()};
    for(const key of Object.keys(headers))if(/^cf-access-client-(id|secret)$/i.test(key))delete headers[key];
    if(new URL(request.url()).origin===origin&&['GET','HEAD'].includes(request.method())){
     headers['CF-Access-Client-Id']=config.clientId;
     headers['CF-Access-Client-Secret']=config.clientSecret;
    }
    await route.continue({headers});
   });
   const page=await context.newPage(),errors=[];
   page.on('pageerror',()=>errors.push('runtime error'));
   const response=await page.goto(config.url,{waitUntil:'networkidle'});
   if(!response||response.status()!==200||new URL(page.url()).origin!==origin)throw Error('Access failed');
   if(!(await page.locator('body').innerText()).includes(config.expect))throw Error('Wrong publication');
   if(await page.evaluate(()=>document.documentElement.scrollWidth)>width)throw Error('Overflow');
   if(errors.length)throw Error('Runtime error');
   const links=await page.locator('main a[href]').evaluateAll(as=>as.map(a=>a.href));
   for(const link of [...new Set(links)].filter(x=>new URL(x).origin===origin).slice(0,30)){
    const r=await context.request.get(link,{headers:{'CF-Access-Client-Id':config.clientId,'CF-Access-Client-Secret':config.clientSecret},maxRedirects:0});
    if(r.status()!==200)throw Error('Broken internal link');
   }
   await page.screenshot({path:path.join(config.outputDir,`production-${width}.png`),fullPage:true});
   await context.close();
  }
 }finally{await browser.close();}
})().catch(()=>{process.stderr.write('Private site verification failed.\n');process.exitCode=1;});
