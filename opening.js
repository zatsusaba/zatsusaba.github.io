(() => {
  if (document.body.dataset.page !== 'index' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const key='zs-opening-seen-v3';
  try { if (localStorage.getItem(key)) return; } catch (_) { return; }
  const shell=document.createElement('div');
  shell.className='opening-overlay'; shell.setAttribute('role','dialog'); shell.setAttribute('aria-label','オープニング'); shell.setAttribute('aria-modal','true');
  shell.innerHTML='<video class="opening-video" playsinline preload="auto" aria-hidden="true"><source src="assets/opening.mp4" type="video/mp4"></video><button class="opening-sound" type="button" hidden>音声ありでOPを再生 ▶</button><button class="opening-skip" type="button">スキップ <span aria-hidden="true">↗</span></button>';
  document.body.appendChild(shell);
  const video=shell.querySelector('video'), sound=shell.querySelector('.opening-sound'), skip=shell.querySelector('.opening-skip'), previous=document.activeElement;
  let timer, done=false;
  function finish(){if(done)return;done=true;clearTimeout(timer);video.pause();shell.remove();try{localStorage.setItem(key,'1')}catch(_){}if(previous&&typeof previous.focus==='function')previous.focus({preventScroll:true})}
  function started(){timer=setTimeout(finish,6500);skip.focus({preventScroll:true})}
  async function playOpening(automatic) {
    sound.hidden=true;
    video.muted=false;
    try {
      await video.play();
      if (!done) started();
    } catch (error) {
      if (done) return;
      if (automatic && error.name==='NotAllowedError') {
        sound.hidden=false;
        sound.focus({preventScroll:true});
      } else {
        finish();
      }
    }
  }
  sound.addEventListener('click',()=>playOpening(false));
  skip.addEventListener('click',finish); shell.addEventListener('keydown',e=>{if(e.key==='Escape')finish()});
  video.addEventListener('ended',finish,{once:true}); video.addEventListener('error',finish,{once:true});
  playOpening(true);
})();
