(function(){
  "use strict";
  const root=document.getElementById("historical-actual-opponent");
  if(!root)return;
  const esc=v=>String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const decimal=v=>typeof v==="number"?v.toLocaleString("sv-SE",{maximumFractionDigits:5}):"–";
  fetch("./historical_opponent_test_2026.json",{cache:"no-store"}).then(response=>{
    if(!response.ok)throw Error("No verified historical opponent report");
    return response.json();
  }).then(r=>{
    if(r.reportType!=="ACTUAL_PAST_OPPONENT_FORM_EXPLORATORY_NOT_VALIDATED" ||
       !r.baselineOnRatedRaces || !r.withHistoricalOpponentsOnRatedRaces)throw Error("Unexpected model results");
    const before=r.baselineOnRatedRaces;
    const after=r.withHistoricalOpponentsOnRatedRaces;
    const line=(label,oldValue,newValue)=>"<tr><td>"+esc(label)+"</td><td>"+esc(oldValue)+
      "</td><td>"+esc(newValue)+"</td></tr>";
    let html="<h2>Historiskt test: verkliga tidigare motståndare</h2>";
    html+="<p class=\"muted\">För "+esc(r.datedFeatureRows)+" matchade häststarter försökte vi följa "+
          "deras tidigare motståndares prestationer med två separata historiska datumgränser. "+
          "<strong>"+esc(r.ratedAllStarts)+"</strong> fick användbart underlag. "+
          "Vi jämför modellerna på <strong>"+esc(r.ratedHeldOutRaces)+
          " senare lopp</strong> där minst 60 % av startfältet hade motståndaruppgifter.</p>";
    html+="<div class=\"table-scroll\"><table><thead><tr><th>Mått – samma "+esc(r.ratedHeldOutRaces)+
          " lopp</th><th>Grundmodell</th><th>Med tidigare motståndare</th></tr></thead><tbody>";
    html+=line("Förstahästen vann",before.top1Count+"/"+before.races,
               after.top1Count+"/"+after.races);
    html+=line("Vinnaren bland tre främsta",before.top3Count+"/"+before.races,
               after.top3Count+"/"+after.races);
    html+=line("Log loss – lägre är bättre",decimal(before.raceLogLoss),decimal(after.raceLogLoss));
    html+=line("Brier – lägre är bättre",decimal(before.horseBrier),decimal(after.horseBrier));
    html+="</tbody></table></div>";
    html+="<p class=\"notice\"><strong>Forskningsresultat, inte spelråd:</strong> Med motståndarhistorik blev "+
         "topp 3 något bättre medan förstahästen blev sämre. Endast "+
         esc(r.strictPairedMarketRaces)+" av de täckta testloppen hade fullständiga "+
         "ATG-slutstreck för en strikt marknadsjämförelse. Vi får därför inte dra slutsatser "+
         "om underspelade skrällar, vinstprocent eller lönsamhet. "+
         "Inga automatiska spikar har ändrats.</p>";
    html+="<p class=\"muted\">Vi har redan prövat flera modeller på överlappande historik. "+
          "Nya förhandsfrysta omgångar behövs för ett oberoende sluttest. "+
          "<a href=\"./historical_opponent_test_2026.json\">Läs den fullständiga experimentrapporten</a>.</p>";
    root.innerHTML=html;
  }).catch(()=>{
    root.innerHTML="<p class=\"muted\">Det kronologiska testet av tidigare motståndare är inte verifierat eller publicerat ännu.</p>";
  });
})();