(function(){
  "use strict";
  const root=document.getElementById("feature-trial");
  if(!root)return;
  const safe=x=>String(x??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const pct=x=>typeof x==="number"?(100*x).toLocaleString("sv-SE",{maximumFractionDigits:1})+" %":"–";
  const val=x=>typeof x==="number"?x.toLocaleString("sv-SE",{maximumFractionDigits:4}):"–";
  function row(title,a,b,c){
    return "<tr><td><strong>"+safe(title)+"</strong></td><td>"+safe(a)+"</td><td>"+safe(b)+"</td><td>"+safe(c)+"</td></tr>";
  }
  fetch("./feature_trial_2026.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw Error("Missing feature trial");
    return r.json();
  }).then(d=>{
    if(d.reportType!=="EXPLORATORY_FIXED_FEATURE_ABLATION"||!d.baselineAll||!d.candidateAll)throw Error("Wrong experiment");
    const n=d.evaluatedRaces;
    let html="<h2>Experiment: tillför nya form- och klassfaktorer något?</h2>";
    html+="<p class=\"muted\">12 nya indikatorer jämförda över <strong>"+n+" osedda lopp</strong>, med samma tidigare träningsdatum och inställningar.</p>";
    html+="<div class=\"table-scroll\"><table><thead><tr><th>Mått</th><th>Grundmodell</th><th>Utökad modell</th><th>ATG</th></tr></thead><tbody>";
    html+=row("Topp 1 – alla "+n+" lopp",pct(d.baselineAll.top1Rate),pct(d.candidateAll.top1Rate),"–");
    html+=row("Topp 3 – alla "+n+" lopp",pct(d.baselineAll.top3Rate),pct(d.candidateAll.top3Rate),"–");
    html+=row("Log loss – alla "+n+" lopp",val(d.baselineAll.raceLogLoss),val(d.candidateAll.raceLogLoss),"–");
    const m=d.pairedRaceCount;
    html+=row("Topp 1 – samma "+m+" lopp",pct(d.baselinePaired.top1Rate),pct(d.candidatePaired.top1Rate),pct(d.atgFinalPoolPaired.top1Rate));
    html+=row("Topp 3 – samma "+m+" lopp",pct(d.baselinePaired.top3Rate),pct(d.candidatePaired.top3Rate),pct(d.atgFinalPoolPaired.top3Rate));
    html+="</tbody></table></div>";
    html+="<p class=\"notice\"><strong>Beslut:</strong> Ingen automatisk uppgradering. Det nya försöket förbättrar några sannolikhetsmått marginellt, men inte träffsäkerheten för topp 1 och topp 3 på alla testlopp. ATG:s slutstreck var fortfarande starkare i det strikt jämförbara urvalet.</p>";
    html+="<p class=\"muted\">Historiskt förstapris är en indirekt klassindikator – inte en rating av verkliga motståndare. Vi har ännu ingen verifierad banprofil eller faktisk spetsstatistik för dessa lopp.</p>";
    root.innerHTML=html;
  }).catch(()=>{root.innerHTML="<p class=\"muted\">Försöksrapporten är ännu inte tillgänglig.</p>";});
})();
