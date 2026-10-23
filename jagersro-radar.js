(()=>{
"use strict";
const slot=document.getElementById("jagersro-radar-live");if(!slot)return;
const source="./jagersro-20261024.json?atg="+Date.now();
const config=[
 {main:3,alt:[1,2],outs:[10],why:"Nilla Lane har mycket starkt expertstöd och spetsargument, men den höga streckandelen gör spiken dyr. Nikki Lane kan gynnas om det blir högt tempo.",risk:"Stor favorit och risk för överstreckning; kontrollera spetsstriden."},
 {main:2,alt:[7,5,14],outs:[8,14],why:"Öppet stolopp: Polly Vici och Hawk Eyed Girl är tidiga bud, medan Bella Yankee har hög kapacitet. Love Express W.F. nämns som skräll av Sportbladet den 23 oktober.",risk:"Stor spridning av tänkbara vinnare – gardering prioriteras."},
 {main:3,alt:[4,1,7],outs:[6],why:"Veritas har form och anmälda balans-/vagnförändringar enligt TR Media. Paleo Boko och Helan Går är starka motbud. Rip Wheeler bevakas som outsider.",risk:"Utrustning måste kontrolleras nära start; ingen säker spik."},
 {main:12,alt:[5,13,3],outs:[3,14],why:"Chat Room och Prince of Euro är toppbud, men voltstart och tillägg ökar osäkerheten. Ulix Turner har kapacitet; Geiles Leben Home är ett mycket osäkert lågprocentigt alternativ.",risk:"Bredda hellre än spika i voltstart med tillägg."},
 {main:1,alt:[3,12],outs:[5,6],why:"Richmond har attraktivt läge och planerad barfotabalans enligt TR Media. Xture Rols är TR Medias utpekade skräll; Barkov lyfts av Sportbladet.",risk:"Både utmanare och flera lågprocentare har rimliga loppbildsscenarier."},
 {main:7,alt:[10,1,2],outs:[1],why:"Tvingens Calippo är segervan och tydligt förstahäst i TR Medias ranking. Wannabe Zaz kan utmana från bra läge och Global Federation är ett starkt motbud.",risk:"Streckprocenten är hög; lås inte innan du vägt motbudens chans."},
 {main:3,alt:[12,5],outs:[4],why:"Diva Ek är TR Medias bästa spik. A Fair Day och Kentucky River är huvudmotbud. Harpy är extremt lågstreckad men svagt expertstöd: endast högriskbevakning.",risk:"A Fair Day kan slå favoriten vid passande resa. Harpy är inte ett huvudtips."},
 {main:6,alt:[4,5],outs:[3],why:"Nickel Occagnes får stort stöd av TR Media. Blixt Lane och Gustav Simoni kan utmana; Look at Me Sisu är en lågprocentare att granska vidare.",risk:"Kort distans och tidig spetsposition kan fälla storfavoriten."}
];
const baseline=[{n:3,p:70.09},{n:2,p:35.53},{n:3,p:43.37},{n:12,p:36.46},{n:1,p:37.30},{n:7,p:52.03},{n:3,p:47.44},{n:6,p:43.25}];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=v=>v==null?"–":Number(v).toLocaleString("sv-SE",{minimumFractionDigits:2,maximumFractionDigits:2});
fetch(source,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("ATG-filen inte tillgänglig");return r.json()}).then(d=>{
 if(d.gameId!=="V85_2026-10-24_7_5"||d.races?.length!==8)throw Error("Fel omgång");
 const all=d.races.flatMap(x=>x.starts);
 const scratched=all.filter(x=>x.scratched);
 const now=d.sourceAt||"okänt";
 const renderHorse=(r,n)=>{const h=r.starts.find(x=>x.number===n);if(!h)return esc(n)+" (ej verifierad)";return esc(n)+" "+esc(h.name)+" <span style='white-space:nowrap;color:#41698d'>("+fmt(h.pct)+" %, "+(h.oddsCapped?"≥99,99":fmt(h.odds))+" odds)</span>"+(h.scratched?" <strong>STRUKEN</strong>":"")};
 slot.innerHTML="<h2>Senaste spik- och skrällradar · Jägersro 24 oktober</h2>"
 +"<p class='warn'><strong>ATG:s senast publicerade källnotering: "+esc(now)+".</strong> Hämtad till GitHub: "+esc(d.retrievedAt)+". Tabellen uppdateras automatiskt när nästa verifierade ATG-fil publiceras. Odds från små pooler är preliminära och kan vara missvisande. Analyserna är redaktionella bedömningar från 23 oktober, inte personliga spelval eller garanterad vinstchans.</p>"
 +"<p class='metric'>Lägesförändring jämförs med <strong>22 oktober kl. 22.50</strong>, inte automatiskt med föregående timme. V85-procent är marknadsstreck, inte uppskattad segerchans. ATG:s 99,99-visning är ett tak och ska inte tolkas som exakt vinnarodds.</p>"
 +"<div class='cards'><article><small>ATG-startande</small><strong>"+(all.length-scratched.length)+" / "+all.length+"</strong></article><article><small>Registrerade strykningar</small><strong>"+scratched.length+"</strong></article><article><small>Lopp analyserade</small><strong>8 / 8</strong></article></div>"
 +"<div class='panes'>"+d.races.map((r,i)=>{const c=config[i];const m=r.starts.find(h=>h.number===c.main);
 const diff=m&&baseline[i].n===c.main?(m.pct-baseline[i].p):null;
 return "<article class='race'><h3>V85-"+(i+1)+"</h3><p><strong>Förstahäst / spikprövning:</strong> "+renderHorse(r,c.main)+"</p><p class='metric'>Förändring i streck sedan 22/10: <strong>"+(diff==null?"–":(diff>=0?"+":"")+fmt(diff)+" procentenheter")+"</strong></p><p><strong>Motbud:</strong> "+c.alt.map(n=>renderHorse(r,n)).join("; ")+"</p><p><strong>Skrällradar:</strong> "+c.outs.map(n=>renderHorse(r,n)).join("; ")+"</p><p>"+esc(c.why)+"</p><p class='warn'><strong>Risk:</strong> "+esc(c.risk)+"</p></article>"}).join("")+"</div>"
 +"<p class='source'>Källor: <a target='_blank' rel='noopener' href='https://www.atg.se/spel/2026-10-24/V85/jagersro'>ATG:s spel och marknadsdata</a> · <a target='_blank' rel='noopener' href='https://www.atg.se/V85/tips/261020-lordag-2410-tips-till-v85-pa-jagersro'>TR Media/ATG, expertanalys 21 oktober</a> · <a target='_blank' rel='noopener' href='https://www.aftonbladet.se/sportbladet/trav365/a/ElA39o/v85-tips-jagersro-lordag-24-oktober-basta-skrallarna-andelssystem'>Sportbladets skrällkoll 23 oktober</a>. Utrustningsuppgifter från tipskällor måste bekräftas med aktuell startinformation före spel.</p>";
}).catch(e=>{slot.innerHTML="<h2>Senaste spik- och skrällradar</h2><p class='warn'>ATG-underlaget kunde inte läsas just nu. Tidigare publicerade startlistor finns nedan; inga nya procenttal kan bekräftas.</p>";console.warn(e)});
})();