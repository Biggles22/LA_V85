(() => {
  'use strict';
  const root=new URL('.',document.currentScript.src),path=location.pathname,header=document.querySelector('.sidebar');
  if(!header)return;
  const url=value=>new URL(value,root).href;
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const relative=path.startsWith(root.pathname)?path.slice(root.pathname.length):path;
  const onCurrent=relative===''||relative==='index.html',onMethod=relative.startsWith('metod/')||relative.startsWith('research/');
  header.classList.add('site-header');
  header.innerHTML='<a class="brand" href="'+root.href+'"><span class="brand-mark">LA</span><span>LA_V85</span></a><nav aria-label="Huvudnavigering"><div class="site-primary-nav"><a href="'+root.href+'" '+(onCurrent?'aria-current="page"':'')+'>Lördagens V85</a><a href="'+url('history/')+'" '+(!onCurrent&&!onMethod?'aria-current="page"':'')+'>Historik</a><a href="'+url('metod/')+'" '+(onMethod?'aria-current="page"':'')+'>Metod & resultat</a></div></nav>';
  document.body.classList.toggle('is-current-round',onCurrent);
  document.body.classList.toggle('is-history',!onCurrent&&!onMethod);
  fetch(url('rounds.json'),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(config=>{
    const current=config.rounds.find(r=>r.id===config.current);
    if(current)header.querySelector('.site-primary-nav a').title=current.track+' · '+current.date;
    const round=config.rounds.find(r=>r.status==='completed'&&(relative.includes(r.id)||(relative.startsWith('resultatanalys/')&&r.id==='2026-10-10-solvalla')));
    const main=document.querySelector('main');if(!round||!main)return;
    const analysisActive=round.review&&(new URL(round.review,root).pathname===path||relative.includes('/analys/')||relative.startsWith('resultatanalys/'));
    const context=document.createElement('section');context.className='round-context';context.setAttribute('aria-label','Omgångsnavigering');
    context.innerHTML='<div class="round-context__identity"><a href="'+url('history/')+'">Historik</a><span aria-hidden="true">/</span><div><strong>'+esc(round.track)+'</strong><small>'+esc(round.date)+' · Avslutad</small></div></div><nav class="round-context__tabs" aria-label="Sidor för '+esc(round.track)+'"><a href="'+url(round.overview)+'" '+(!analysisActive?'aria-current="page"':'')+'>Förhandsarkiv</a><a href="'+url(round.review)+'" '+(analysisActive?'aria-current="page"':'')+'>Efteranalys</a></nav>';
    main.prepend(context);
    function markTabs(){
      const analysis=round.review.includes('#')?location.hash===new URL(round.review,root).hash:analysisActive;
      const tabs=context.querySelectorAll('nav a');tabs.forEach(a=>a.removeAttribute('aria-current'));tabs[analysis?1:0].setAttribute('aria-current','page');
    }
    markTabs();addEventListener('hashchange',markTabs);
  }).catch(()=>{/* Base navigation remains usable when metadata cannot be loaded. */});
})();
