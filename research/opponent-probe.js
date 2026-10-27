(function(){
"use strict";
const root=document.getElementById("opponent-probe");
if(!root)return;
const esc=x=>String(x??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
fetch("./opponent_probe_2026.json",{cache:"no-store"}).then(r=>{
  if(!r.ok)throw Error("Missing probe report");
  return r.json();
}).then(d=>{
  if(d.schemaVersion!==1||!Array.isArray(d.rows))throw Error("Unexpected report structure");
  const rows=d.rows.map(x=>{
    const score=typeof x.opponentRecentFormMean==="number"
      ?x.opponentRecentFormMean.toLocaleString("sv-SE",{maximumFractionDigits:3}):"–";
    const cover=x.coverageSufficient?"Tillräckligt":"Otillräckligt";
    return "<tr><td>V85-"+esc(x.leg)+"</td><td>"+esc(x.number+" "+x.name)+"</td><td>"+esc(x.previousRaceId)+"</td><td>"+esc(x.ratedOpponents)+"/"+esc(x.otherStarters??"–")+"</td><td>"+esc(score)+"</td><td>"+cover+"</td></tr>";
  }).join("");
  root.innerHTML="<h2>Pilot: hur starka var de faktiska tidigare motståndarna?</h2>"+
    "<p class=\"muted\">"+d.readableRaces+" av "+d.sampledPreviousRaces+" äldre lopp kunde läsas. "+d.sufficientCoverage+" av "+d.observedFocusStarts+
    " hästreferenser hade tillräcklig historik. För varje äldre lopp använder vi bara motståndarnas resultat före just den tävlingsdagen.</p>"+
    "<div class=\"table-scroll\"><table><thead><tr><th>Avdelning</th><th>Häst</th><th>Tidigare lopp</th><th>Bedömda rivaler</th><th>Formproxy 0–1</th><th>Datatäckning</th></tr></thead><tbody>"+
    rows+"</tbody></table></div>"+
    "<p class=\"muted\">Poängen är rivalernas genomsnittliga historiska andel topp-3/segrar, inte vinstprocent för hästen. Ingen fullständig klassranking eller automatisk tipsändring har gjorts. Källan är ett begränsat ATG-test och viss historik saknas.</p>";
}).catch(()=>{
  root.innerHTML="<p class=\"muted\">Ingen verifierad motståndsrapport kunde läsas.</p>";
});
})();
