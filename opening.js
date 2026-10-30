(() => {
  if (document.body.dataset.page !== 'index' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const key='zs-opening-seen-v1';
  try { if (localStorage.getItem(key)) return; localStorage.setItem(key,'1'); } catch (_) { return; }
  const shell=document.createElement('div');
  shell.className='opening-overlay'; shell.setAttribute('role','dialog'); shell.setAttribute('aria-label','オープニング'); shell.setAttribute('aria-modal','true');
  shell.innerHTML='<video class="opening-video" muted playsinline preload="auto" aria-hidden="true"><source src="assets/opening.mp4" type="video/mp4"></video><button class="opening-skip" type="button">スキップ <span aria-hidden="true">↗</span></button>';
  document.body.appendChild(shell);
  const video=shell.querySelector('video'), skip=shell.querySelector('button'), main=document.querySelector('#main');
  const previous=document.activeElement;
  let timer; let done=false;
  function finish(){ if(done)return; done=true; clearTimeout(timer); video.pause(); shell.remove(); if(previous&&typeof previous.focus==='function') previous.focus({preventScroll:true}); }
  skip.addEventListener('click',finish); shell.addEventListener('keydown',e=>{if(e.key==='Escape')finish(); if(e.key==='Tab'){e.preventDefault();skip.focus();}});
  video.addEventListener('ended',finish,{once:true}); video.addEventListener('error',finish,{once:true});
  timer=setTimeout(finish,6500); skip.focus({preventScroll:true});
  const play=video.play(); if(play&&play.catch)play.catch(finish);
})();
