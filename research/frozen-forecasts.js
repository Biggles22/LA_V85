(function(){
  "use strict";
  const node=document.getElementById("frozen-v85-forecasts");
  if(!node)return;
  const esc=v=>String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  const slots=[["preview","Tisdag – första förhandsprovet"],["friday","Fredag 30 okt – prognos kl. 18"],["saturday","Lördag 31 okt – slutfrysning kl. 14.15"]];
  function read(path){return fetch(path,{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null)}
  const path="./frozen/2026-10-31/";
  const pct=x=>typeof x==="number"?x.toLocaleString("sv-SE",{maximumFractionDigits:1})+" %":"–";
  function entry(r,n){
    const h=r.runners.find(x=>x.number===n);
    return h?esc(n+" "+h.horse):esc(n);
  }
  function table(doc){
    let html="<div class=\"table-scroll\"><table><thead><tr><th>Lopp</th><th>Grundmodell topp 3</th><th>Motståndsmodell topp 3</th><th>ATG topp 3</th><th>Motståndsunderlag</th></tr></thead><tbody>";
    for(const race of doc.races){
      html+="<tr><td>V85-"+esc(race.leg)+"</td><td>"+race.baseTop3.map(n=>entry(race,n)).join("<br>")+
            "</td><td>"+race.opponentTop3.map(n=>entry(race,n)).join("<br>")+
            "</td><td>"+race.marketTop3.map(n=>entry(race,n)).join("<br>")+
            "</td><td>"+esc(race.opponentDataCoverage)+"/"+esc(race.runners.length)+"</td></tr>";
    }
    return html+"</tbody></table></div>";
  }
  function status(name,display,doc,result){
    if(!doc){
      return "<p class=\"muted\"><strong>"+esc(display)+":</strong> Ingen verifierad förhandsfil publicerad ännu. Prognosen får inte skapas efter start.</p>";
    }
    if(doc.kind!=="FROZEN_PROSPECTIVE_RESEARCH_NOT_BETTING_ADVICE"||doc.races?.length!==8){
      return "<p class=\"notice\">Felaktigt prognosformat för "+esc(name)+"; visas inte.</p>";
    }
    let html="<h3>"+esc(display)+"</h3>";
    html+="<p class=\"muted\">Fryst: <strong>"+esc(doc.frozenAt.replace("T"," ").slice(0,16))+
          "</strong> · ATG-källtid: <strong>"+esc(doc.marketSourceAt.replace("T"," ").slice(0,16))+
          "</strong> · Källa äldre än observationen med "+Math.round(doc.marketLagSeconds/60)+
          " minuter. Träningsunderlag: "+esc(doc.trainingStarts)+" historiska starter.</p>";
    html+=table(doc);
    html+="<p class=\"muted\"><a href=\""+path+esc(name)+".json\">Se originalfilens fullständiga poäng och källuppgifter</a></p>";
    if(result){
      const m=result.metrics;
      html+="<p class=\"notice\"><strong>Resultat (8 lopp):</strong> Grundmodell "+
        esc(m.base.top1)+"/8 förstahäst, "+esc(m.base.top3)+"/8 topp 3. Motståndsmodell "+
        esc(m.opponents.top1)+"/8 förstahäst, "+esc(m.opponents.top3)+"/8 topp 3. ATG "+
        esc(m.atg.top1)+"/8 förstahäst, "+esc(m.atg.top3)+"/8 topp 3.</p>";
    }
    return html;
  }
  Promise.all([...slots.map(([key])=>read(path+key+".json")),read(path+"evaluation.json")])
    .then(files=>{
      const final=files[3];
      let html="<h2>Frysta förhandsprognoser inför Bjerke den 31 oktober</h2>"+
        "<p class=\"muted\">Grundmodell, modell med historiska motståndare och ATG:s marknadsranking. Samma startlista och ATG-källtid i varje enskilt fryst dokument. Prognosfiler ändras aldrig efter publicering.</p>"+
        "<div class=\"notice\"><strong>Forskningsprognoser – inga spiktips.</strong> Modellandelarna i JSON är normaliserade klassificeringspoäng, <em>inte kalibrerade vinstsannolikheter</em>. ATG-procenten är hästarnas andel av V85-strecken.</div>";
      slots.forEach(([key,label],i)=>{html+=status(key,label,files[i],final?.slotComparisons?.[key])});
      if(final){
        html+="<p class=\"muted\">Facit hämtat från verifierade ATG-resultat efter start: <a href=\""+path+"evaluation.json\">Läs söndagens utvärdering</a>. En enda V85-omgång räcker inte för att bevisa träffsäkerhet eller spelvärde.</p>";
      }else{
        html+="<p class=\"muted\">Söndagens facit skapas först när alla åtta ATG-resultat finns. Saknade prognoser backdateras inte.</p>";
      }
      node.innerHTML=html;
    }).catch(()=>{
      node.innerHTML="<p class=\"muted\">Kunde inte kontrollera forskningsfilerna just nu.</p>";
    });
})();