(function(){
"use strict";
const root=document.getElementById("expanded-opponent-results");
if(!root)return;
const safe=x=>String(x??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const pct=x=>typeof x==="number"?(x*100).toLocaleString("sv-SE",{maximumFractionDigits:1})+" %":"–";
const metric=(x,key)=>x?.[key]??null;
Promise.all(["./opponent_coverage_2026.json","./opposition_field_trial_2026.json"].map(path=>
    fetch(path,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error(path);return r.json()})
)).then(([coverage,trial])=>{
    if(coverage.schemaVersion!==2||trial.reportType!=="HISTORIC_UPCOMING_FIELD_OPPOSITION_ABLATION_NOT_VALIDATED")
       throw Error("Unexpected experimental data version");
    let html="<h2>Utökad motståndsanalys inför Bjerke</h2>";
    html+="<p class=\"muted\">Vi har undersökt <strong>"+safe(coverage.plannedDistinctRaces)+
        " tidigare lopp</strong>. "+safe(coverage.readableDistinctRaces)+" gav användbar historik. "+
        "<strong>"+safe(coverage.horsesWithValidForm)+" av "+safe(coverage.activeHorses)+
        " hästar</strong> fick ett underbyggt mått på sina tidigare motståndare.</p>";
    html+="<div class=\"table-scroll\"><table><thead><tr><th>V85</th><th>Aktiva hästar</th><th>Med tillräckligt motståndarunderlag</th><th>Saknar underlag</th></tr></thead><tbody>";
    for(let leg=1;leg<=8;leg++){
      const members=coverage.horses.filter(x=>x.leg===leg);
      const ready=members.filter(x=>x.opponentFormMean!==null).length;
      html+="<tr><td>V85-"+leg+"</td><td>"+members.length+"</td><td>"+ready+"</td><td>"+(members.length-ready)+"</td></tr>";
    }
    html+="</tbody></table></div>";
    html+="<p class=\"muted\">Alla värden har spårbara tidigare lopp. Ett saknat mått förblir tomt; ingen häst får automatiskt noll. "+
         "Detta är inte en kalibrerad klassrating eller vinstchans. <a href=\"./opponent_coverage_2026.json\">Insamlingsrapport och källspår</a>.</p>";
    const a=trial.baselineAll,b=trial.oppositionAll;
    html+="<h2>Historiskt test av konkurrenternas förhandsform</h2>"+
      "<p class=\"muted\">Två XGBoost-modeller jämförs över exakt samma "+safe(trial.heldOutRaces)+
      " utvärderingslopp. Den ena får tillgång till tidigare form för de andra startande i <em>det aktuella</em> historiska loppet. "+
      "Detta är ännu inte ett backtest av Bjerkes insamlade tidigare möten.</p>";
    html+="<div class=\"table-scroll\"><table><thead><tr><th>Mått</th><th>Grundmodell</th><th>Med övriga hästars form</th></tr></thead><tbody>"+
      "<tr><td>Topp 1, antal rätt</td><td>"+a.top1Count+"/"+a.races+"</td><td>"+b.top1Count+"/"+b.races+"</td></tr>"+
      "<tr><td>Topp 3, antal rätt</td><td>"+a.top3Count+"/"+a.races+"</td><td>"+b.top3Count+"/"+b.races+"</td></tr>"+
      "<tr><td>Log loss (lägre bättre)</td><td>"+safe(a.raceLogLoss)+"</td><td>"+safe(b.raceLogLoss)+"</td></tr>"+
      "<tr><td>Brier (lägre bättre)</td><td>"+safe(a.horseBrier)+"</td><td>"+safe(b.horseBrier)+"</td></tr>"+
      "</tbody></table></div>";
    html+="<p class=\"notice\"><strong>Beslut: ingen automatisk modelländring.</strong> Log loss förbättrades, "+
      "men topp 1 och topp 3 försämrades i de 151 testloppen. Resultaten är experimentella och kan påverkas av "+
      "upprepad metodutveckling på samma historiska datum. De påverkar inte Bjerkes liveanalys.</p>";
    html+="<p class=\"muted\"><a href=\"./opposition_field_trial_2026.json\">Läs fullständig resultatfil för testet</a>.</p>";
    root.innerHTML=html;
}).catch(()=>{
    root.innerHTML="<p class=\"muted\">Utökad motståndsdata finns ännu inte i en verifierad publicerad rapport.</p>";
});
})();