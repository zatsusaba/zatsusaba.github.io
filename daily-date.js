// A static Pages build may span midnight before the next YouTube sync.
(() => {
  const group = document.querySelector('[data-daily-date]');
  if (!group) return;
  const empty = document.querySelector('[data-daily-empty]');
  const jst = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit' });
  function refresh() {
    group.hidden = group.dataset.dailyDate !== jst.format(new Date());
    empty.hidden = !group.hidden;
  }
  refresh();
  document.addEventListener('visibilitychange', refresh);
  window.addEventListener('pageshow', refresh);
  const now = Date.now();
  setTimeout(refresh, 86400000 - (now + 9 * 3600000) % 86400000);
})();
