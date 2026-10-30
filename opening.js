(() => {
  if (document.body.dataset.page !== 'index' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const key = 'zs-opening-seen-v2';
  try { if (localStorage.getItem(key)) return; } catch (_) { return; }
  const shell = document.createElement('div');
  shell.className = 'opening-overlay';
  shell.setAttribute('role', 'dialog');
  shell.setAttribute('aria-label', 'オープニング');
  shell.setAttribute('aria-modal', 'true');
  shell.innerHTML = '<video class="opening-video" playsinline preload="auto" aria-hidden="true"><source src="assets/opening.mp4" type="video/mp4"></video><button class="opening-start" type="button" style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);padding:16px 24px;border:1px solid white;background:#d91830;color:white;font:inherit;font-weight:bold;cursor:pointer">音声付きでオープニングを見る ▶</button><button class="opening-skip" type="button">スキップ <span aria-hidden="true">↗</span></button>';
  document.body.appendChild(shell);
  const video = shell.querySelector('video'), start = shell.querySelector('.opening-start'), skip = shell.querySelector('.opening-skip');
  const previous = document.activeElement;
  let timer, done = false;
  function finish() {
    if (done) return;
    done = true; clearTimeout(timer); video.pause(); shell.remove();
    try { localStorage.setItem(key, '1'); } catch (_) {}
    if (previous && typeof previous.focus === 'function') previous.focus({preventScroll:true});
  }
  start.addEventListener('click', () => {
    video.muted = false;
    const playing = video.play();
    if (playing && playing.then) playing.then(() => { start.hidden = true; timer = setTimeout(finish, 6500); skip.focus(); }).catch(() => { start.textContent = '再生できません。スキップしてサイトへ'; });
  });
  skip.addEventListener('click', finish);
  shell.addEventListener('keydown', e => { if (e.key === 'Escape') finish(); });
  video.addEventListener('ended', finish, {once:true});
  video.addEventListener('error', finish, {once:true});
  start.focus({preventScroll:true});
})();
