(() => {
  if (document.body.dataset.page !== 'index' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const key='zs-opening-seen-v3';
  try { if (localStorage.getItem(key)) return; } catch (_) { return; }
  const shell=document.createElement('div');
  shell.className='opening-overlay'; shell.setAttribute('role','dialog'); shell.setAttribute('aria-label','オープニング'); shell.setAttribute('aria-modal','true');
  shell.innerHTML='<video class="opening-video" playsinline preload="auto" aria-hidden="true"><source src="assets/opening.mp4" type="video/mp4"></video><button class="opening-sound" type="button" hidden style="position:absolute;left:24px;bottom:24px;padding:12px 20px;border:1px solid #fff;background:#111;color:#fff;cursor:pointer;font:inherit">音をオンにする 🔊</button><button class="opening-skip" type="button">スキップ <span aria-hidden="true">↗</span></button>';
  document.body.appendChild(shell);
  const video=shell.querySelector('video'), sound=shell.querySelector('.opening-sound'), skip=shell.querySelector('.opening-skip'), previous=document.activeElement;
  let timer, done=false;
  function finish(){if(done)return;done=true;clearTimeout(timer);video.pause();shell.remove();try{localStorage.setItem(key,'1')}catch(_){}if(previous&&typeof previous.focus==='function')previous.focus({preventScroll:true})}
  function started(){timer=setTimeout(finish,6500);skip.focus({preventScroll:true})}
  sound.addEventListener('click',()=>{video.muted=false;sound.hidden=true});
  skip.addEventListener('click',finish); shell.addEventListener('keydown',e=>{if(e.key==='Escape')finish()});
  video.addEventListener('ended',finish,{once:true}); video.addEventListener('error',finish,{once:true});
  const play=video.play();
  if(play&&play.then)play.then(started).catch(()=>{video.muted=true;sound.hidden=false;const fallback=video.play();if(fallback&&fallback.then)fallback.then(started).catch(finish)});
})();
