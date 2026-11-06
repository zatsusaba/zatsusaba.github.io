const input = document.querySelector('#blog-search');
if (input) {
  const cards = [...document.querySelectorAll('[data-search]')];
  input.addEventListener('input', () => {
    const words = input.value.normalize('NFKC').toLocaleLowerCase('ja').trim().split(/\s+/).filter(Boolean);
    let count = 0;
    cards.forEach(card => {
      const text = card.dataset.search.normalize('NFKC').toLocaleLowerCase('ja');
      card.hidden = !words.every(word => text.includes(word));
      if (!card.hidden) count++;
    });
    document.querySelector('#blog-count').textContent = count + '件';
    document.querySelector('#blog-empty').hidden = count !== 0;
  });
}
