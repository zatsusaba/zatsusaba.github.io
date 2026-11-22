(() => {
  const calculator = document.querySelector('#estimate');
  if (!calculator) return;

  const format = new Intl.NumberFormat('ja-JP');
  const result = calculator.querySelector('#estimate-difference');
  const shops = ['a', 'b'].map(id => ({
    inputs: [...calculator.querySelectorAll('[data-shop="' + id + '"]')],
    output: calculator.querySelector('#shop-' + id + '-total')
  }));

  function parseAmount(raw) {
    const text = raw.normalize('NFKC').trim();
    if (!text) return { state: 'blank' };
    if (!/^(?:\d+|\d{1,3}(?:,\d{3})+)$/.test(text)) return { state: 'invalid' };
    return { state: 'valid', amount: BigInt(text.replaceAll(',', '')) };
  }

  function calculateShop(shop) {
    const fields = shop.inputs.map(input => {
      const value = parseAmount(input.value);
      input.setAttribute('aria-invalid', String(value.state === 'invalid'));
      return value;
    });
    if (fields.some(field => field.state === 'invalid')) {
      shop.output.textContent = '0以上の整数を入力';
      return null;
    }
    const missing = fields.filter(field => field.state === 'blank').length;
    if (missing) {
      shop.output.textContent = missing === fields.length ? '未入力' : 'あと' + missing + '項目';
      return null;
    }
    const total = fields.reduce((sum, field) => sum + field.amount, 0n);
    shop.output.textContent = format.format(total) + '円';
    return total;
  }

  function update() {
    const [a, b] = shops.map(calculateShop);
    if (a === null || b === null) {
      result.textContent = '両店の4項目がそろうと差額が表示されます。';
    } else if (a === b) {
      result.textContent = '差額は0円。両店の支払総額は同じです。';
    } else {
      const cheaper = a < b ? 'A店' : 'B店';
      const difference = a < b ? b - a : a - b;
      result.textContent = cheaper + 'のほうが ' + format.format(difference) + '円 安くなります。';
    }
  }

  calculator.addEventListener('input', update);
  window.addEventListener('pageshow', update);
  update();
})();
