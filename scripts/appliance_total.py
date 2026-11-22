"""Render the washing-machine quote comparison as a standalone, indexable page."""

URL = "/tools/appliance-total/"
TITLE = "洗濯機の買い替え総額比較"
DESCRIPTION = "2店の洗濯機の見積もりを入力して、本体代・配送設置費・古い洗濯機の回収費・追加費用を含む支払総額と差額を比較できます。"
FEES = (
    ("price", "本体価格"),
    ("delivery", "配送・設置費"),
    ("collection", "回収費"),
    ("extra", "追加費用"),
)


def fee_row(key, label):
    cells = []
    for shop in ("a", "b"):
        cells.append(
            f'<td><div class="estimate-input"><input type="text" inputmode="numeric" '
            f'id="{shop}-{key}" data-shop="{shop}" aria-labelledby="shop-{shop} fee-{key}" '
            'aria-describedby="entry-hint" autocomplete="off" spellcheck="false">'
            '<span aria-hidden="true">円</span></div></td>'
        )
    return f'<tr><th scope="row" id="fee-{key}">{label}</th>{"".join(cells)}</tr>'


def build(page, write, urls):
    rows = "".join(fee_row(key, label) for key, label in FEES)
    body = f'''<article class="appliance-tool">
  <div class="estimate-intro">
    <a class="estimate-back" href="/">← 雑学サバイバル</a>
    <h1>{TITLE}</h1>
    <p>本体が安い店と、設置まで頼むと安い店は同じでしょうか。2店の見積もりを並べて、実際に支払う金額を比べられます。</p>
  </div>
  <section id="estimate" class="estimate-sheet" aria-labelledby="estimate-title">
    <h2 id="estimate-title">2店の見積もりを入力</h2>
    <p id="entry-hint">税込の金額を円単位で入力してください。金額が分からない項目は空欄に、無料・不要・本体価格に含まれる項目は0を入れます。</p>
    <table class="estimate-table" aria-labelledby="estimate-title">
      <thead><tr><th scope="col">内訳</th><th scope="col" id="shop-a">A店</th><th scope="col" id="shop-b">B店</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="estimate-note">回収費には、古い洗濯機のリサイクル料金と収集運搬料金の合計を入れます。階段搬入や部品など、ほかの欄に含まれない費用は「追加費用」へ。</p>
    <div class="estimate-result" role="status" aria-live="polite" aria-atomic="true">
      <dl class="estimate-totals">
        <div><dt>A店の支払総額</dt><dd id="shop-a-total">未入力</dd></div>
        <div><dt>B店の支払総額</dt><dd id="shop-b-total">未入力</dd></div>
      </dl>
      <p id="estimate-difference">両店の4項目がそろうと差額が表示されます。</p>
    </div>
    <noscript><p>自動計算にはJavaScriptを有効にしてください。各店の支払総額は4項目の合計です。</p></noscript>
  </section>
  <section class="estimate-checks" aria-labelledby="estimate-checks-title">
    <h2 id="estimate-checks-title">見積もりを取る前に</h2>
    <dl>
      <div><dt>設置場所までの開口寸法</dt><dd>玄関や脱衣所の入口の幅と、曲がり角の余裕を確認します。購入候補の機種について、搬入に必要な寸法を販売店に照会してください。</dd></div>
      <div><dt>本体の真下にある排水口</dt><dd>設置後に排水口が本体で隠れる場合は、その位置と高さを伝え、別売部品が必要か、設置費に含まれるかを確認します。 <a href="https://panasonic.jp/life/housework/100068.html">パナソニックの搬入・排水チェック</a></dd></div>
      <div><dt>古い洗濯機の引き取り</dt><dd>買い替え時に販売店へ引き取りを頼む場合は、リサイクル料金と収集運搬料金の両方を見積もりに入れてもらいます。 <a href="https://www.meti.go.jp/policy/it_policy/kaden_recycle/shiryousyu/recycle_moving_2024.pdf">経済産業省の家電リサイクル案内（PDF）</a></dd></div>
    </dl>
  </section>
</article><script defer src="/appliance-total.js"></script>'''
    html = page(TITLE, DESCRIPTION, URL, body)
    write(URL, html.replace("</head>", '<link rel="stylesheet" href="/appliance-total.css"></head>'))
    urls.append(URL)
