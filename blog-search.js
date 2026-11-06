// Static archives work without JS. Fetch search data only after a reader types.
const query = document.querySelector('#blog-search');
const fullText = document.querySelector('#body-search');
const archive = document.querySelector('#archive-list');
const results = document.querySelector('#matches');
const count = document.querySelector('#blog-count');
const empty = document.querySelector('#blog-empty');
const initialCount = count.textContent;
const cache = new Map();
const normalize = text => text.normalize('NFKC').toLocaleLowerCase('ja');
let revision = 0;
let timer;

function read(url) {
  if (!cache.has(url)) {
    cache.set(url, fetch(url).then(response => {
      if (!response.ok) throw Error('search index unavailable');
      return response.json();
    }).catch(error => { cache.delete(url); throw error; }));
  }
  return cache.get(url);
}

function show(rows, page = 0) {
  results.replaceChildren();
  const list = document.createElement('ul');
  for (const [url, title, description, category] of rows.slice(page * 24, (page + 1) * 24)) {
    const item = document.createElement('li');
    const a = document.createElement('a');
    a.href = url;
    a.textContent = title;
    const summary = document.createElement('p');
    summary.textContent = category + ' ｜ ' + description;
    item.append(a, summary);
    list.append(item);
  }
  results.append(list);
  for (const [label, next] of [['← 前へ', page - 1], ['次へ →', page + 1]]) {
    if (next < 0 || next * 24 >= rows.length) continue;
    const button = document.createElement('button');
    button.textContent = label;
    button.onclick = () => { show(rows, next); query.focus(); };
    results.append(button);
  }
  count.textContent = rows.length + '件';
  empty.hidden = rows.length > 0;
}

async function search(id) {
  const words = normalize(query.value.trim()).split(/\s+/).filter(Boolean);
  results.replaceChildren();
  archive.hidden = !!words.length;
  if (!words.length) {
    count.textContent = initialCount;
    empty.hidden = initialCount !== '0件';
    return;
  }
  empty.hidden = true;
  count.textContent = '検索中…';
  try {
    const index = await read('/search/index.json');
    const found = [];
    for (let start = 0; start < index.length; start += 32) {
      if (id !== revision) return;
      const chunk = index.slice(start, start + 32);
      const eligible = row => !query.dataset.category || row[3] === query.dataset.category;
      if (!chunk.some(eligible)) continue;
      const bodies = fullText.checked ? await read('/search/body-' + start / 32 + '.json') : [];
      chunk.forEach((row, i) => {
        if (!eligible(row)) return;
        const text = normalize([row[1], row[2], row[3], ...row[4], bodies[i] || ''].join(' '));
        if (words.every(word => text.includes(word))) found.push(row);
      });
    }
    if (id === revision) show(found);
  } catch {
    if (id === revision) count.textContent = '読み込めませんでした。入力し直してください。';
  }
}
function schedule() {
  const id = ++revision;
  clearTimeout(timer);
  timer = setTimeout(() => search(id), 120);
}
query.addEventListener('input', schedule);
fullText.addEventListener('change', schedule);
