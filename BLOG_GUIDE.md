# 雑学サバイバル公式サイト｜Dots更新手順

3.0公開後は最新mainから作品専用ブランチを作り、以下のデータだけを追加する。公開前の動作試験は feat/content-platform-v3 を起点にする。PRを作者に渡し、作者が内容・権利・出典を確認してからマージする。ビルドはSNSへ投稿しない。

## 雑学大百科
1. articles/英数字スラッグ.md を追加する。ファイル名が作品ID・URLになる。既存記事の改訂は同じファイルで行う。page と category は予約語。
2. メタ情報と本文を入力する。下記は形式見本。角括弧で示す値は実際に確認した内容に置き換える。本文は Markdown の段落・二段目以降の見出しで書く。
3. 初稿は status: draft。公開用の出典・日付・根拠を揃えたら status: published にしてPRにする。従来の draft: true も非公開が優先される。

~~~yaml
---
status: draft
title: "［記事のタイトル］"
description: "［読者の疑問と記事の概要］"
date: 2026-11-06
updated: 2026-11-06
category: 科学
topic: "［既存記事と照合するテーマ名］"
tags: [科学]
conditions: "［対象・成立条件・例外。必要に応じて本文でも説明］"
sources:
  - title: "［一次資料の発行元・資料名］"
    url: "［実在するHTTPSの資料URL］"
    checked: 2026-11-06
---
~~~

カテゴリーは食べ物・人体・動物・自然・宇宙・歴史・心理・お金・身近なモノ・科学・文化・世界。実画像を使う場合は image と image_alt をセットにする。画像省略時はカテゴリー文字カバー、youtube 省略時は記事単独になる。動画を結ぶときだけ公開済みの11文字の動画IDを記入する。featured: true は特集指定。日付は日本時間。重要な修正をしたら updated、実際に確認し直した出典だけ checked を更新する。本文にHTMLを直接書かない。

**重複と再確認**　python scripts/editorial.py は、公開対象のタイトルと topic を全半角・大文字小文字・記号を正規化して照合し、重複候補を列挙する。別の言い回しや意味の重複はDotsが既存記事を検索して確認する。出典の最古の checked から365日以上経過した記事を再確認対象として出す。候補は編集用であり、機械的に削除しない。下書き中は既存台帳を検索し、公開候補に変えた時点でこのコマンドを再実行する。

## 4コマ漫画
1. 作品IDを英小文字・数字・ハイフンで決める。comics/作品ID.yml と comic-media/作品ID/ に画像を用意する。既存の公開作品 ai-official-site は元の panels-v2 の画像をそのまま使う。
2. panels は読み順でちょうど4件。各項目に src（例 /comic-media/作品ID/01.png）、alt（場面説明）、text（作者の正式なセリフ・表示文字、無言は空文字）を置く。PNG/JPEG/WebP/AVIFが対象。セリフ・絵をDotsが補完しない。
3. title、date、characters（キャラ名の配列）、themes（分類名の配列）を入力。tags は任意。articles は記事ID配列、videos は同期済みの公開動画ID配列。関係が確認できた作品だけを指定する。
4. status は draft → pending → approved の順。approved にする前に作者本人の承認を得て、approval に承認日と確認した原稿・版を記す。承認欄は運用記録であり、本人確認は作者のPRレビューで行う。
5. 未承認作品はHTML・検索・サイトマップ・配信画像に含めない。GitHubリポジトリは公開のため、秘密の未公開原稿はローカルで管理し、実ファイルをGitHubに送るのは作者が許可した後にする。新作画像を共通の assets に置かない。ページ公開後はURL維持のためIDを固定する。

## 今日の雑学
既存のYouTube同期がチャンネルの公開動画だけを取得する。publishedAtをUTCで保存し、日本時間の日付ごとに /today/YYYY-MM-DD/ を作る。日付の根拠が取れていない旧動画は /today/undated/ から閲覧できる。config/youtube-published.json は初回移行用。旧データ14件についてYouTubeの公開watchページで動画ID・チャンネルとタイムゾーン付きの公開日時を照合したもの。新形式の同期値を優先する。

config/youtube-formats.json は確かめた動画ID・種別・根拠の対応表。未判定動画はそのまま掲載する。長さだけを根拠に種別を記入しない。「詳しく読む」は記事の youtube が一致したときだけ自動生成。動画説明から科学記事を自動作成しない。更新のない日付ページは作らない。

## 検証・試験・失敗時の復旧
Python 3.12 以上で次を実行する。
~~~
python -m pip install -r requirements-blog.txt
python scripts/check_site.py
python scripts/test_blog_updates.py
python scripts/test_platform.py
python scripts/test_youtube_sync.py
python scripts/test_media.py
python scripts/editorial.py
python -m http.server 8766 --directory _site
~~~

Dotsの初回操作試験は独立記事を画像・動画なしで下書き → 公開候補にし、出典・文字カバー・検索・カテゴリー・サイトマップを確認する。漫画は隔離した確認用4枚を使い、pendingでページと画像が出ないことを確認してから、試験用の承認記録でapprovedにして表示・読み順・前後作を確認する。実運用での承認を代行しない。同期・日付境界・リンクは上記のオフラインテストで確認できる。テスト原稿や cleanup-temp/ と _site/ はコミットしない。

検証で失敗したら、ログのファイル名・項目を修正し、同じブランチで再実行する。問題の漫画はpendingへ戻し、記事はdraftへ戻せる。削除時は公開漫画の明示リンクも同じPRで更新する。同期取得に失敗した場合は既存カタログを維持し、API状態・割当・Actionsの設定を確認して再実行する。失敗ビルドはPagesに送らない。公開後に問題が判明した場合は、原因の変更を戻すPRを作り、直前の正常版との差分を確認して作者承認後に再配信する。
