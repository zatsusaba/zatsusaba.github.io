const sheet = document.querySelector('.comic-sheet');
const viewer = document.querySelector('#comic-viewer');
const panels = [...sheet.querySelectorAll('a')];
const photo = viewer.querySelector('img');
const prev = viewer.querySelector('[data-prev]');
const next = viewer.querySelector('[data-next]');
let current = 0;
function show(index) {
  current = Math.max(0, Math.min(panels.length - 1, index));
  photo.src = panels[current].href;
  photo.alt = panels[current].querySelector('img').alt;
  viewer.querySelector('output').textContent = (current + 1) + ' / ' + panels.length;
  prev.disabled = current === 0;
  next.disabled = current === panels.length - 1;
}
panels.forEach((panel, index) => panel.addEventListener('click', event => {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !viewer.showModal) return;
  event.preventDefault();
  show(index);
  viewer.showModal();
}));
prev.onclick = () => show(current - 1);
next.onclick = () => show(current + 1);
viewer.querySelector('[data-close]').onclick = () => viewer.close();
viewer.addEventListener('keydown', event => {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
  event.preventDefault();
  show(current + (event.key === 'ArrowRight' ? 1 : -1));
});
let start;
photo.addEventListener('touchstart', e => {
  start = e.touches.length === 1 ? [e.touches[0].clientX,e.touches[0].clientY] : null;
}, {passive:true});
photo.addEventListener('touchcancel', () => { start = null; });
photo.addEventListener('touchend', e => {
  if (!start) return;
  const dx = e.changedTouches[0].clientX - start[0];
  const dy = e.changedTouches[0].clientY - start[1];
  start = null;
  if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy)*1.5) show(current + (dx < 0 ? 1 : -1));
}, {passive:true});
