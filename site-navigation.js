(() => {
  'use strict';
  const script = document.currentScript;
  const root = new URL('.', script.src);
  const path = location.pathname;
  const onCurrent = path === root.pathname || path === root.pathname + 'index.html';
  const onHistory = !onCurrent;
  const header = document.querySelector('.sidebar');
  if (!header) return;

  const url = value => new URL(value, root).href;

  header.classList.add('site-header');
  header.innerHTML = `
    <a class="brand" href="${root.href}"><span class="brand-mark">LA</span><span>LA_V85</span></a>
    <nav aria-label="Huvudnavigering">
      <div class="site-primary-nav">
        <a href="${root.href}" ${onCurrent ? 'aria-current="page"' : ''}>Aktuell omgång <small>Bjerke · 31 okt</small></a>
        <a href="${url('index.html#tvastegsmodell')}">AI-testmodell <small>Ranking &amp; spelvärde</small></a>
        <a href="${url('history/')}" ${onHistory ? 'aria-current="page"' : ''}>Historik <small>Omgångar &amp; analyser</small></a>
      </div>
    </nav>`;

  const main = document.querySelector('main');
  if (!main) return;
  document.body.classList.toggle('is-current-round', onCurrent);
  document.body.classList.toggle('is-history', onHistory);

  const rounds = [
    {
      match: '2026-10-24-jagersro',
      track: 'Jägersro', date: '24 oktober 2026', status: 'Avslutad',
      overview: 'archive/2026-10-24-jagersro/', analysis: 'archive/2026-10-24-jagersro/#efteranalys'
    },
    {
      match: '2026-10-17-gavle',
      track: 'Gävle', date: '17 oktober 2026', status: 'Avslutad',
      overview: 'archive/2026-10-17-gavle/', analysis: 'archive/2026-10-17-gavle/analys/'
    },
    {
      match: ['2026-10-10-solvalla', 'resultatanalys'],
      track: 'Solvalla', date: '10 oktober 2026', status: 'Avslutad',
      overview: 'archive/2026-10-10-solvalla/', analysis: 'resultatanalys/'
    },
    {
      match: '2026-10-03-boden',
      track: 'Boden', date: '3 oktober 2026', status: 'Avslutad',
      overview: 'archive/2026-10-03-boden/', analysis: 'archive/2026-10-03-boden/#boden-analysis'
    }
  ];
  const round = rounds.find(item => (Array.isArray(item.match) ? item.match : [item.match]).some(token => path.includes(token)));
  if (!round) return;

  const analysisActive = path.includes('/analys/') || path.includes('/resultatanalys/') || location.hash.startsWith('#boden-analysis');
  const context = document.createElement('section');
  context.className = 'round-context';
  context.setAttribute('aria-label', 'Omgångsnavigering');
  context.innerHTML = `
    <div class="round-context__identity">
      <a href="${url('history/')}">Historik</a><span aria-hidden="true">/</span>
      <div><strong>${round.track}</strong><small>${round.date} · ${round.status}</small></div>
    </div>
    <nav class="round-context__tabs" aria-label="Sidor för ${round.track}">
      <a href="${url(round.overview)}" ${!analysisActive ? 'aria-current="page"' : ''}>Förhandsarkiv</a>
      <a href="${url(round.analysis)}" ${analysisActive ? 'aria-current="page"' : ''}>Efteranalys</a>
    </nav>`;
  main.prepend(context);
})();
