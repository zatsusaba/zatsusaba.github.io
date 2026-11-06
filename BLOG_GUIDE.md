# 雑学Blog 更新ガイド

記事追加は articles/ に Markdown を1本追加するだけです。生成された _site/ はコミットしません。
既存HTML・動画同期データは編集不要。公開は main に承認済みPRがマージされた後です。

## 手順
1. 最新 main から記事専用ブランチを作る。
2. articles/pineapple.md を参考に articles/short-english-slug.md を追加する。
3. メタ情報を書き、本文は ## 見出しから構成する。本文のHTMLは禁止。
4. 出典の実物と公開済みYouTube動画を確認。出典の条件・対象・限界を本文に残す。
5. PRを作成。Validate and preview blog の成功を確認し、承認を待つ。

~~~yaml
---
title: 記事タイトル
description: 検索結果とカードに使う概要
date: 2026-11-06
updated: 2026-11-06
category: 食べ物
tags: [キーワード]
image: https://i.ytimg.com/vi/q5FluB5f-b8/hqdefault.jpg
image_alt: 画像の説明
youtube: q5FluB5f-b8
sources:
  - title: 出典名
    url: https://www.rinya.maff.go.jp/kyusyu/iriomote_fc/iriomote_syokubutusi/attach/pdf/syokubutusi_1-176.pdf
---
本文。上の画像・動画・出典は書き方の例。新記事の実内容に置き換える。
~~~

カテゴリー：食べ物、人体、動物、自然、宇宙、歴史、心理、お金、身近なモノ。
youtube は省略可。image は /assets/ 内の実在ファイルも可。sources は1件以上必須。
draft: true は非公開。日付は未来不可。date は初回公開日、updated は改訂日。
URLは /blog/ファイル名/。公開後はファイル名を変更しない。同じ記事を別名で複製しない。
関連記事は同カテゴリー・タグの一致を優先し、新着順を補助として最大3件。記事1本の間は一覧へ案内する。
新着順は date、同日の場合はファイル名の降順。
記事削除後のURLは404となるため、公開記事の削除や改名は要相談。

## プレビューと検証
~~~
python -m pip install -r requirements-blog.txt
python scripts/check_site.py
python -m http.server 8766 --directory _site
~~~
ブラウザーで http://localhost:8766/ と /blog/ を確認する。
GitHubのPRチェックの Actions 実行画面から blog-preview アーティファクトを取得しても確認可能。
ダウンロードしたサイトもHTTPサーバーで開く。HTMLを直接ダブルクリックしない。

PR用ワークフローはビルドと検証・アーティファクト保存だけで、Pagesへデプロイしない。
既存のYouTube同期は従来どおり youtube-videos.js だけコミットし、その後Blogを生成して _site/ を公開する。
4コマ漫画の既存表示は維持。将来の自動生成は独立工程として追加できる。

## Dotsへ渡す更新命令
このリポジトリの BLOG_GUIDE.md を読み、最新mainから記事専用ブランチを作成してください。
公開済みの雑学サバイバル動画を題材に、一次資料の実物で事実を確認し、articles/ に独立したMarkdownを追加してください。
メタ情報にタイトル、概要、公開日、更新日、既定カテゴリー、タグ、アイキャッチと代替文、関連動画ID、出典名とHTTPS URLを設定してください。
根拠の条件・不確実性を本文に残し、未検証の主張は書かないでください。
既存記事・キャラ設定・台詞・HTML・同期処理は無断変更しないでください。
python scripts/check_site.py とPRチェックを通し、記事URLと確認した出典を記したPRにまとめてください。
mainへのマージ・本番公開は作者の承認を待ってください。
