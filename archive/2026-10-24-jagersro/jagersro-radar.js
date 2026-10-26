(()=>{
"use strict";
const slot=document.getElementById("jagersro-radar-live");if(!slot)return;
const source="./jagersro-20261024.json?atg="+Date.now();
const config=[
 {
  "main": 3,
  "alt": [
   1,
   2
  ],
  "outs": [],
  "longshots": [
   10
  ],
  "why": "Egen värdering: Nilla Lane har ett tydligt tänkbart spetslopp och högst segerchans i avdelningen. Panthere d'Inverne och Fantastica Doda är mer realistiska garderingar än en slumpmässig lågprocentare. Nikki Lane är endast chansskräll, inte huvuddrag.",
  "risk": "Mycket hög streckandel: spiken kan vara sportsligt stark utan att ge bra spelvärde."
 },
 {
  "main": 2,
  "alt": [
   7,
   9,
   5
  ],
  "outs": [
   8
  ],
  "longshots": [
   15
  ],
  "why": "Egen värdering: Polly Vici och Hawk Eyed Girl är jämna förstahästar; Hawk Eyed Girl kan nå en bra position tidigt. Mahakala och Job Girl är rimliga garderingar. Love Express W.F. är lågstreckad outsider, men pausen drar ned säkerheten. Anna K.J. är chansskräll från svårt läge.",
  "risk": "Spår 15 för Anna K.J. och obekräftad barfotauppgift för Hawk Eyed Girl. Ingen given spik."
 },
 {
  "main": 3,
  "alt": [
   1,
   4
  ],
  "outs": [
   7,
   6
  ],
  "longshots": [
   5
  ],
  "why": "Egen värdering: Veritas är förstahäst men Helan Går och Paleo Boko är starka motbud. Charmant Dream har ett konkret segerupplägg om hästen når ledningen. Rip Wheeler kan gynnas av aviserade utrustningsändringar. Forest Wood kräver mer klaff och räknas som chansskräll.",
  "risk": "Spetsstrid och tempo avgör mycket. Uppgivna utrustningsändringar är inte verifierade som genomförda."
 },
 {
  "main": 12,
  "alt": [
   5,
   13
  ],
  "outs": [
   3,
   14,
   8
  ],
  "longshots": [
   11
  ],
  "why": "Egen värdering: Chat Room har hög kapacitet men tillägg och voltstart skapar osäkerhet. Prince of Euro och Barkley är tidiga motbud. Ulix Turner har tänkbart spetsläge men galopprisk; Geiles Leben Home och Indian är lågstreckade alternativ. Special Ale är en mer spekulativ voltstartsidé.",
  "risk": "Voltstart, tillägg och galopprisk. Utrustningsuppgifter från intervjuer är inte slutligt bekräftade."
 },
 {
  "main": 1,
  "alt": [
   3,
   12
  ],
  "outs": [
   6,
   5
  ],
  "longshots": [
   8
  ],
  "why": "Egen värdering: V85-5 är främsta skrälljakten. Richmond riskerar trafikproblem från innerspåret; Elroy Face och Hard Rock är riktiga motbud. Barkov prioriteras som huvudskräll tack vare möjlig spets och låg streckandel. Xture Rols har form men kan behöva tempo. Konstapel Sisu är endast chansskräll.",
  "risk": "Barkov har galopprisk; huvudlagsuppgift obekräftad. Xture Rols kan hamna långt bak."
 },
 {
  "main": 7,
  "alt": [
   10
  ],
  "outs": [
   2,
   1
  ],
  "longshots": [],
  "why": "Egen värdering: Tvingens Calippo är kapabel men spår 7 och hög streckandel motiverar gardering. Datos Rainbow har ett gynnsamt startläge och är ett intressant motbud; Wannabe Zaz kan också få en bättre resa än favoriten. Global Federation är ett starkt garderingsbud.",
  "risk": "Vinnarodds kommer från annan pool än V85-streck och är ingen direkt sannolikhetsmodell."
 },
 {
  "main": 3,
  "alt": [
   12,
   5
  ],
  "outs": [],
  "longshots": [
   11,
   4
  ],
  "why": "Egen värdering: Diva Ek är en rimlig spikprövning men A Fair Day och Kentucky River är betydligt mer realistiska motbud än de allra lägst streckade. Här finns ingen tillräckligt underbyggd huvudskräll just nu. Fighter Kronos och Harpy får endast chansskrällstatus.",
  "risk": "A Fair Day har styrka för distansen; Diva Eks långdistansform behöver vägas in. Nummer 8 Kaxig In är struken i senast verifierade snapshot."
 },
 {
  "main": 6,
  "alt": [
   4
  ],
  "outs": [
   5,
   3
  ],
  "longshots": [],
  "why": "Egen värdering: Nickel Occagnes är förstahäst, men på kort distans kan spetsstriden bli avgörande. Gustav Simoni har dokumenterad bantrivsel och är ett prioriterat motbud trots att han inte är extremt lågt streckad. Blixt Lane har bra utgångsläge; Look at Me Sisu är en mer lågstreckad utmanare.",
  "risk": "Spetsstrid och kort distans ger små marginaler. Senare utrustning och odds måste kontrolleras."
 }
];
const finalRanking=[
 {
  "a": [
   3
  ],
  "b": [
   1,
   2
  ],
  "note": "Spikförslag: Nilla Lane. Störst sportslig tilltro, men omkring tre fjärdedelar av strecken ger låg utdelningshävstång och stor systemrisk om hon förlorar."
 },
 {
  "a": [
   2,
   7
  ],
  "b": [
   9,
   5,
   8
  ],
  "note": "Öppet lopp. Polly Vici och Hawk Eyed Girl jämbördiga förstahästar. Gardera; Love Express W.F. är ett riskfyllt värdedrag."
 },
 {
  "a": [
   3,
   1,
   4
  ],
  "b": [
   7,
   6
  ],
  "note": "Veritas först, men Helan Går och Paleo Boko är reella hot. Charmant Dream är främsta lågprocentaren vid ledning; Rip Wheeler behöver utrustnings- och loppklaff."
 },
 {
  "a": [
   12,
   5,
   13
  ],
  "b": [
   3,
   8,
   14,
   11
  ],
  "note": "Chat Room kapabel men tillägg och voltstart gör spik osäker. Prince of Euro och Barkley tidiga; Ulix Turner och Indian som värdedrag. Special Ale chansskräll."
 },
 {
  "a": [
   1,
   3,
   12
  ],
  "b": [
   6,
   5,
   7
  ],
  "note": "Omgångens främsta skrälljakt. Richmond kan bli fast; Barkov är vårt bästa värdedrag om han når spets utan galopp, Xture Rols kräver rätt tempo."
 },
 {
  "a": [
   7,
   2,
   10
  ],
  "b": [
   1
  ],
  "note": "Tvingens Calippo stark favorit men svårt spår och hög streckandel. Datos Rainbow och Global Federation viktiga garderingar; Wannabe Zaz möjlig överraskning."
 },
 {
  "a": [
   3,
   12
  ],
  "b": [
   5,
   10
  ],
  "note": "Diva Ek möjlig andra spik men lång distans, resa och A Fair Day som tungt motbud gör henne mindre trygg. Inga välgrundade huvudskrällar."
 },
 {
  "a": [
   6,
   5,
   4
  ],
  "b": [
   3
  ],
  "note": "Nickel Occagnes först, men kort distans och spetsstrid ger risk. Gustav Simoni är ett prioriterat motbud med bantrivsel; Blixt Lane måste med på större system."
 }
];
const baseline=[{n:3,p:75.42},{n:2,p:29.47},{n:3,p:40.92},{n:12,p:34.69},{n:1,p:31.13},{n:7,p:51.25},{n:3,p:49.99},{n:6,p:47.19}];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=v=>v==null?"–":Number(v).toLocaleString("sv-SE",{minimumFractionDigits:2,maximumFractionDigits:2});
fetch(source,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("ATG-filen inte tillgänglig");return r.json()}).then(d=>{
 if(d.gameId!=="V85_2026-10-24_7_5"||d.races?.length!==8)throw Error("Fel omgång");
 const all=d.races.flatMap(x=>x.starts);
 const scratched=all.filter(x=>x.scratched);
 const now=d.sourceAt||"okänt";
 const renderHorse=(r,n)=>{const h=r.starts.find(x=>x.number===n);if(!h)return esc(n)+" (ej verifierad)";return esc(n)+" "+esc(h.name)+" <span style='white-space:nowrap;color:#41698d'>("+fmt(h.pct)+" %, "+(h.oddsCapped?"≥99,99":fmt(h.odds))+" odds)</span>"+(h.scratched?" <strong>STRUKEN</strong>":"")};
 slot.innerHTML="<h2>Spik- och skrällradar med egen värdering · Jägersro 24 oktober</h2>"
 +"<p class='warn'><strong>ATG:s senast publicerade källnotering: "+esc(now)+".</strong> Hämtad till GitHub: "+esc(d.retrievedAt)+". Tabellen uppdateras automatiskt när nästa verifierade ATG-fil publiceras. Odds från små pooler är preliminära och kan vara missvisande. Egen spik- och skrällbedömning slutligt preliminärt bedömd 24 oktober kl. 14.04 utifrån startlägen, tänkbar loppbild, streck och risk; tidningstips är endast bakgrund. Ingen nyare fullständig tidsstämplad ATG-notering än 09.39 har kunnat verifieras vid slutkontrollen kl. 14.04. Ändra inte streck eller odds utifrån odaterade webbutdrag. Kusk-/tränaruppgifter och strykningar gäller den snapshoten; sena ändringar, omsättning och slutlig utrustning är inte verifierade. Det är bedömningar, inte personliga spelval eller garanterad vinstchans.</p>"
 +"<p class='metric'>Lägesförändring jämförs med verifierad ATG-notering <strong>24 oktober kl. 04.21</strong> (föregående verifierade jämförelsenotering), inte automatiskt med föregående timme. V85-procent är marknadsstreck, inte uppskattad segerchans. ATG:s 99,99-visning är ett tak och ska inte tolkas som exakt vinnarodds.</p>"
 +"<div class='cards'><article><small>ATG-startande</small><strong>"+(all.length-scratched.length)+" / "+all.length+"</strong></article><article><small>Registrerade strykningar</small><strong>"+scratched.length+"</strong></article><article><small>Lopp analyserade</small><strong>8 / 8</strong></article></div>"
 +"<section class='panel'><h2>Slutlig preliminär ranking inför V85-start kl. 15.00</h2><p class='warn'><strong>Slutkontroll 24 oktober kl. 14.04.</strong> Senaste verifierade fullständiga ATG-källnotering: "+esc(now)+" (hämtad "+esc(d.retrievedAt)+"). Ingen nyare komplett tidsstämplad ATG-snapshot har kunnat verifieras. Alla streck och odds nedan är därför preliminära. Kontrollera sena strykningar, skor, vagn, kuskändringar och odds direkt hos ATG innan inlämning.</p><p><strong>Prioriterade spikprövningar:</strong> V85-1 nr 3 Nilla Lane och V85-7 nr 3 Diva Ek (högre risk). <strong>Främsta värdedrag:</strong> V85-5 nr 6 Barkov, V85-3 nr 7 Charmant Dream, V85-8 nr 5 Gustav Simoni, V85-5 nr 5 Xture Rols och V85-6 nr 2 Datos Rainbow. V85-streck är inte vår beräknade segerchans.</p><div class='panes'>"+d.races.map((r,i)=>{const f=finalRanking[i];return "<article class='race'><h3>V85-"+(i+1)+" · slutranking</h3><p><strong>A:</strong> "+f.a.map(n=>renderHorse(r,n)).join("; ")+"</p><p><strong>B:</strong> "+f.b.map(n=>renderHorse(r,n)).join("; ")+"</p><p>"+esc(f.note)+"</p></article>"}).join("")+"</div></section>"
+"<div class='panes'>"+d.races.map((r,i)=>{const c=config[i];const m=r.starts.find(h=>h.number===c.main);
 const diff=m&&baseline[i].n===c.main?(m.pct-baseline[i].p):null;
 return "<article class='race'><h3>V85-"+(i+1)+"</h3><p><strong>Förstahäst / spikprövning:</strong> "+renderHorse(r,c.main)+"</p><p class='metric'>Förändring i streck sedan 24/10 kl. 04.21: <strong>"+(diff==null?"–":(diff>=0?"+":"")+fmt(diff)+" procentenheter")+"</strong></p><p><strong>Motbud:</strong> "+c.alt.map(n=>renderHorse(r,n)).join("; ")+"</p><p><strong>Prioriterade värdedrag:</strong> "+(c.outs.length?c.outs.map(n=>renderHorse(r,n)).join("; "):"Inget tillräckligt underbyggt huvuddrag i detta lopp")+"</p>"+(c.longshots.length?"<p class='metric'><strong>Chansskrällar (hög risk):</strong> "+c.longshots.map(n=>renderHorse(r,n)).join("; ")+"</p>":"")+"<p>"+esc(c.why)+"</p><p class='warn'><strong>Risk:</strong> "+esc(c.risk)+"</p></article>"}).join("")+"</div>"
 +"<p class='source'>Källor: <a target='_blank' rel='noopener' href='https://www.atg.se/spel/2026-10-24/V85/jagersro'>ATG:s spel och marknadsdata</a> · <a target='_blank' rel='noopener' href='https://www.atg.se/V85/tips/261020-lordag-2410-tips-till-v85-pa-jagersro'>TR Media/ATG, expertanalys 21 oktober</a> · <a target='_blank' rel='noopener' href='https://www.aftonbladet.se/sportbladet/trav365/a/ElA39o/v85-tips-jagersro-lordag-24-oktober-basta-skrallarna-andelssystem'>Sportbladets skrällkoll 23 oktober</a> · <a target='_blank' rel='noopener' href='https://svenskatrav.n.nu/v85-tips-jagersro-24-oktober-2026'>SvenskaTrav, ranking 23 oktober</a> · <a target='_blank' rel='noopener' href='https://travia.se/v85/jagersro-2026-10-24'>Travia, modellranking</a> · <a target='_blank' rel='noopener' href='https://www.guiden.se/artiklar/guiden-expressv75/20261023/guiden-express-v85-jagersro-24-oktober/'>Guiden Express, expertanalys och tränarintervjuer 23 oktober</a>. Utrustningsuppgifter från tipskällor måste bekräftas med aktuell startinformation före spel.</p>";
}).catch(e=>{slot.innerHTML="<h2>Senaste spik- och skrällradar</h2><p class='warn'>ATG-underlaget kunde inte läsas just nu. Tidigare publicerade startlistor finns nedan; inga nya procenttal kan bekräftas.</p>";console.warn(e)});
})();