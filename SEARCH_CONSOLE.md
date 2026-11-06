# 公開後の登録
1. 作者のGoogleアカウントで [Search Console](https://search.google.com/search-console/) にログインし、「プロパティを追加」→「URL プレフィックス」に https://zatsusaba.github.io/ を登録する。
2. 「HTMLタグ」を選ぶ。発行された meta タグの content の値だけをリポジトリの config/google-verification に1行で保存する。これは公開用の所有権確認値。Googleのパスワードやアクセストークンは保存しない。
3. 承認後にサイトを公開し、HOMEのHTMLソースで google-site-verification があることを確かめてから「確認」を押す。確認後もファイルを保持する。
4. https://zatsusaba.github.io/robots.txt と https://zatsusaba.github.io/sitemap.xml がHTTP 200であることを確認。「サイトマップ」から sitemap.xml を送信し、処理状況を確認する。
5. 「URL検査」でHOMEと /blog/pineapple/ の公開URLをテストし、必要に応じてインデックス登録をリクエストする。Googleが選んだcanonicalやインデックス状況は処理後に同画面で確認する。

記事の lastmod は本文・出典・重要なリンクを最後に改訂した updated の日付を使う。初出時は date と一致させる。再ビルドだけで updated を変更しない。

## 判断に使った公式資料
- [所有権確認](https://support.google.com/webmasters/answer/9008080)
- [サイトマップとlastmod](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [canonicalとJavaScript](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Article構造化データ](https://developers.google.com/search/docs/appearance/structured-data/article)
- [AI検索機能とサイト](https://developers.google.com/search/docs/appearance/ai-features)

