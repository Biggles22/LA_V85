(function WalkforwardView(){
  const root=document.getElementById("walkforward-report");if(!root)return;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct=x=>typeof x==="number"?(100*x).toLocaleString("sv-SE",{maximumFractionDigits:1})+" %":"–";
  const count=x=>typeof x==="number"?x.toLocaleString("sv-SE"):"–";
  const tile=(label,stats)=>`<article class="card"><small>${esc(label)}</small><strong>${pct(stats?.top3Rate)}</strong><small>Topp 1: ${pct(stats?.top1Rate)} · ${count(stats?.races)} testlopp</small></article>`;
  fetch("./walkforward_report_2026.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Report not found");return r.json()}).then(d=>{
    if(d.reportType!=="EXPANDING_CHRONOLOGICAL_BACKTEST_NOT_VALIDATED"||!Array.isArray(d.folds))throw Error("Invalid report");
    const a=d.testMetrics||{},m=d.strictPairedModel||{},b=d.strictPairedMarket||{};
    root.innerHTML=`<h2>Utökad historik och upprepade testperioder</h2>
      <p class="muted"><strong>${count(d.sourceRaceCount)} lopp · ${count(d.sourceStarts)} häststarter · ${count(d.sourceDates)} tävlingsdatum</strong> i historiken. Modellen tränas om enbart på äldre datum inför vart och ett av de ${count(d.folds.length)} senare testdatumen.</p>
      <div class="cards">${tile("AI – alla walk-forward-test",a)}${tile("AI – samma komplett verifierade lopp",m)}${tile("ATG – samma komplett verifierade lopp",b)}</div>
      <p><strong>${count(d.strictPairedCount)} lopp</strong> med både tillräckligt fullständigt resultat och slutlig ATG-pool kunde jämföras direkt. ${count(d.excludedFromMarketComparison)} andra AI-testlopp fick inte användas i marknadsjämförelsen.</p>
      <p class="muted">Observera att detta gäller retrospektiva ATG-slutstreck, inte verifierade snapshots före start. Testresultat är inte prognostiserad avkastning, och poängen är inte kalibrerade vinstchanser.</p>
      <h2>Alla kronologiska testfönster</h2>
      <div class="table-scroll"><table><thead><tr><th>Testdatum</th><th>Träning t.o.m.</th><th>Testlopp</th><th>AI topp 1</th><th>AI topp 3</th><th>Strikt ATG-jämförelse</th></tr></thead><tbody>
      ${d.folds.map(x=>`<tr><td>${esc(x.date)}</td><td>${esc(x.trainUntil)}</td><td>${count(x.testMetrics?.races)}</td><td>${pct(x.testMetrics?.top1Rate)}</td><td>${pct(x.testMetrics?.top3Rate)}</td><td>${count(x.pairedRaces)} lopp${x.pairedRaces?` · ATG topp 3: ${pct(x.pairedMarket?.top3Rate)}`:""}</td></tr>`).join("")}</tbody></table></div>`;
  }).catch(()=>{
    root.innerHTML='<div class="notice"><strong>Inget fullständigt walk-forward-test publicerat ännu.</strong> Se <a href="https://github.com/Biggles22/LA_V85/actions/workflows/historical-pilot.yml">GitHub Actions</a> för senaste kontroll.</div>';
  });
})();
