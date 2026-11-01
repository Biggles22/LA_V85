(() => {
  const el = document.querySelector('#catboost-report');
  if (!el) return;
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct = x => typeof x === 'number' ? (x * 100).toFixed(1).replace('.', ',') + ' %' : 'Ej beräknat';
  const metric = (name, data) =>
    '<article class="card"><small>' + esc(name) + '</small><strong>' + pct(data?.top3Rate) +
    '</strong><small>Förstahäst: ' + pct(data?.top1Rate) + ' · ' + (data?.races ?? 0) + ' testlopp</small></article>';

  fetch('./catboost_trial_2026.json', {cache: 'no-store'})
    .then(r => { if (!r.ok) throw new Error('No CatBoost report'); return r.json(); })
    .then(d => {
      if (d.reportType !== 'CATBOOST_EXPANDING_CHRONOLOGICAL_BACKTEST_NOT_VALIDATED') throw new Error('Invalid report');
      el.innerHTML =
        '<h2>CatBoost – tidsordnat jämförelsetest</h2>' +
        '<p class="muted">Modellen tränas om inför varje osedd tävlingsdag och använder endast tidigare startdata. ' +
        'Detta är en jämförelse med XGBoost, inte en produktionsmodell eller ett spelråd.</p>' +
        '<div class="cards">' +
          metric('CatBoost – topp 3 (samma lopp)', d.strictPairedCatBoost || d.testMetrics) +
          metric('ATG:s slutstreck – topp 3 (samma lopp)', d.strictPairedMarket) +
          '<article class="card"><small>Utvärdering</small><strong>' + (d.strictPairedCount ?? 0) +
          '</strong><small>lopp med jämförbar marknadsdata</small></article>' +
        '</div>' +
        '<p class="notice"><strong>Status: experiment.</strong> ' + esc(d.calibrationState === 'NOT_CALIBRATED'
          ? 'Vinstchanserna är ännu inte kalibrerade och får inte användas som färdiga sannolikheter.'
          : 'Se rapportens metod och begränsningar.') + '</p>' +
        '<p class="muted">' + esc(d.limitations) + '</p>';
    })
    .catch(() => {
      el.innerHTML = '<div class="notice"><strong>CatBoost-rapporten är inte klar ännu.</strong> ' +
        'Körningen behöver först samla tillräckligt många tidsordnade testlopp. ' +
        '<a href="https://github.com/Biggles22/LA_V85/actions/workflows/catboost-trial.yml">Öppna körningen i GitHub Actions</a>.</div>';
    });
})();