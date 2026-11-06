(() => {
  'use strict';
  const filter = document.querySelector('#result-filter');
  const rounds = [...document.querySelectorAll('.round-card')];
  filter.addEventListener('change', () => {
    for (const round of rounds) round.hidden = filter.value !== 'all' && round.dataset.net !== filter.value;
    document.querySelector('#filter-status').textContent = `${rounds.filter(round => !round.hidden).length} av ${rounds.length} omgångar visas. Sammanställningen överst avser alla fem kuponger.`;
  });
})();
