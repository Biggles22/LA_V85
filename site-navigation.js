(() => {
  'use strict';
  const script = document.currentScript;
  const root = new URL('.', script.src);
  const path = location.pathname;
  const onCurrent = path === root.pathname || path === root.pathname + 'index.html';
  const onHistory = !onCurrent;
  const header = document.querySelector('.sidebar');
  if (!header) return;

  header.classList.add('site-header');
  header.innerHTML = `
    <a class="brand" href="${root.href}"><span class="brand-mark">LA</span><span>LA_V85</span></a>
    <nav aria-label="Huvudnavigering">
      <div class="site-primary-nav">
        <a href="${root.href}" ${onCurrent ? 'aria-current="page"' : ''}>Aktuell omgång <small>Jägersro · 24 okt</small></a>
        <a href="${new URL('history/', root).href}" ${onHistory ? 'aria-current="page"' : ''}>Historik <small>Omgångar &amp; analyser</small></a>
      </div>
    </nav>`;
})();
