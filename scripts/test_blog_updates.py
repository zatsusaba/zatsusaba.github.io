"""Exercise article additions and updates with isolated fixtures."""
import json
import tempfile
from pathlib import Path
import build_blog as b
from check_site import RegionLinks
from media import PAGE_SIZE
original_root, original_out = b.ROOT, b.OUT
job=original_root/"cleanup-temp"/"blog-verification"
job.mkdir(parents=True,exist_ok=True)
root=Path(tempfile.mkdtemp(prefix="fixture-",dir=job))
for name in ("articles","assets","panels-v2"): (root/name).mkdir()
(root/"index.html").write_text((original_root/"index.html").read_text(encoding="utf-8"),encoding="utf-8")
# Keep fixtures independent of revisions to a real published article.
sample="""---
title: パイナップルの検証記事
description: 隔離環境で記事の追加と更新を確認します。
date: 2026-11-06
updated: 2026-11-06
status: published
category: 食べ物
image: https://i.ytimg.com/vi/q5FluB5f-b8/hqdefault.jpg
image_alt: 検証用画像
youtube: q5FluB5f-b8
youtube_title: パイナップルの木は
youtube_format: short
sources:
  - checked: 2020-01-01
    title: 検証用資料
    url: https://example.org/source
---
## パイナップルの正体

検証用の本文です。
"""
(root/"youtube-videos.js").write_bytes((original_root/"youtube-videos.js").read_bytes())
b.ROOT=root
b.OUT=root/"_site"
(root/"articles/pineapple.md").write_text(sample,encoding="utf-8")
second=root/"articles/second.md"
second.write_text(sample.replace("title: パイナップル","title: 追加検証パイナップル",1),encoding="utf-8")
from unittest.mock import patch
from types import SimpleNamespace
with patch.object(b.subprocess, "run", return_value=SimpleNamespace(stdout="COMMIT:2026-11-06T08:00:00+09:00\narticles/second.md\nCOMMIT:2026-11-06T09:00:00+09:00\narticles/pineapple.md\n")):
    assert b.load()[0]["slug"] == "pineapple"
second.write_text(sample.replace("date: 2026-11-06", 'published_at: "2026-11-06T10:00:00+09:00"\ndate: 2026-11-06', 1),encoding="utf-8")
assert b.load()[0]["slug"] == "second"
# Legacy articles without a section stay in the lower blog. A newer blog entry
# must never fill an empty news front page.
first_article=root/"articles/pineapple.md"
home_path=b.OUT/"index.html"
def read(path):
    return (b.OUT / path).read_text(encoding="utf-8")

def cards(path):
    return RegionLinks(read(path), ".blog-card").links

b.build()
home=read("index.html")
assert "/blog/second/" not in RegionLinks(home, "#news").links
assert cards("index.html") == ["/blog/second/", "/blog/pineapple/"]
assert json.loads(read("news/search.json")) == []

# Same date, subject, category and video on both sides exercise feed ordering,
# search body shards, and article recommendations without relying on live data.
def article_sample(section, hour, title, body):
    return (sample.replace("title: パイナップルの検証記事", "title: "+title, 1)
            .replace("status: published", f'status: published\nsection: {section}\npublished_at: "2026-11-06T{hour}:00:00+09:00"')
            .replace("検証用の本文です。", body))

bulletin=root/"articles/bulletin.md"
evening=root/"articles/evening.md"
bulletin.write_text(article_sample("news","09","朝の発表","ニュース朝刊の固有本文"),encoding="utf-8")
evening.write_text(article_sample("news","18","夜の発表","ニュース夜刊の固有本文")
                   .replace("section: news", "section: news\nedition: 夜刊"),encoding="utf-8")
first_article.write_text(article_sample("blog","20","夜の雑学","雑学ブログのみの固有本文"),encoding="utf-8")
b.build()
home=read("index.html")
upper=RegionLinks(home, "#news").links
news_urls=["/news/evening/", "/news/bulletin/"]
blog_urls=["/blog/pineapple/", "/blog/second/"]
assert [url for url in upper if url in news_urls + blog_urls] == news_urls
assert "夜刊" in home[:home.index('id="zatsusaba"')]
assert cards("index.html") == blog_urls
for stream, urls, index, shard, key in (
    ("news", news_urls, "news/search.json", "news/search-body-0.json", "ニュース夜刊の固有本文"),
    ("blog", blog_urls, "search/index.json", "search/body-0.json", "雑学ブログのみの固有本文"),
):
    archive=read(stream+"/index.html")
    for path in (stream+"/index.html", stream+"/category/food/index.html"):
        assert cards(path) == urls, path
    for index_in_stream, url in enumerate(urls):
        assert cards(url.strip("/")+"/index.html") == [urls[1 - index_in_stream]], url
    assert [row[0] for row in json.loads(read(index))] == urls
    assert key in json.loads(read(shard))[0]
    assert f'data-index="/{index}"' in archive and f'data-body-prefix="/{shard.removesuffix("0.json")}"' in archive
linked_entries = json.loads(read("video-links.json"))["q5FluB5f-b8"]
assert {entry[0] for entry in linked_entries} == set(blog_urls)
# Cross both the archive-page and search-shard boundaries with news alone.
extra_news=[]
for number in range(32):
    path=root/"articles"/f"bulletin-{number:02d}.md"
    path.write_text(article_sample("news","08",f"検証ニュース {number:02d}",f"検証ニュース本文 {number:02d}"),
                    encoding="utf-8")
    extra_news.append(path)
b.build()
all_news=[a["url"] for a in b.load() if a["section"]=="news"]
for archive in ("news", "news/category/food"):
    assert cards(archive+"/index.html") == all_news[:PAGE_SIZE]
    assert cards(archive+"/page/2/index.html") == all_news[PAGE_SIZE:]
assert len(json.loads(read("news/search-body-1.json"))) == 2
assert not (b.OUT/"blog/page/2/index.html").exists()
for path in [bulletin, evening, *extra_news]:
    path.unlink()
b.build()
assert not (b.OUT/"news/evening/index.html").exists()
assert not list((b.OUT/"news").glob("search-body-*.json"))
assert not (b.OUT/"news/page/2/index.html").exists()
assert not (b.OUT/"news/category/food/index.html").exists()
assert json.loads(read("news/search.json")) == []
assert cards("blog/category/food/index.html") == blog_urls
first_article.write_text(article_sample("newspaper", "20", "誤分類", "検証"), encoding="utf-8")
try:
    b.load()
except ValueError as error:
    assert "section" in str(error)
else:
    raise AssertionError("Unrecognized article section accepted")
print("PASS: distinct editions, same-day priority, archives, category and related links, search indexes and removed news")
first_article.write_text(sample,encoding="utf-8")
second.write_text(sample,encoding="utf-8")
b.build()
article_html=(b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
assert 'class="blog-cover"' in article_html  # Articles without a duplicate keep their cover.
# Inspect rendered image tags, not image URLs mentioned in text, links, or code.
cover={"url":"/blog/subject/", "image":"/assets/example.png", "image_alt":"Cover"}
for html in (
    '<p><img src="/assets/example.png" alt="Body"></p>',
    '<p><img src="https://zatsusaba.github.io/assets/example.png" alt="Body"></p>',
    '<p><img src="../../assets/example.png" alt="Body" /></p>',
):
    assert b.article_cover(dict(cover,html=html))==""
for html in (
    '<p>No image</p>',
    '<p><a href="/assets/example.png">Image link only</a></p>',
    '<pre><code>&lt;img src="/assets/example.png"&gt;</code></pre>',
    '<p><img src="/assets/another.png" alt="/assets/example.png"></p>',
    '<p><img src="/assets/example.png?different=1"></p>',
):
    assert 'class="blog-cover"' in b.article_cover(dict(cover,html=html))
assert b.article_cover(dict(cover,image="/assets/example.png?a=1&b=2",
                           html='<img src="/assets/example.png?a=1&amp;b=2">'))==""
# A repeated build removes only the automatic cover, preserving the full prose,
# captions, source links, cards, and share metadata. Reference-style images work too.
cover_url="https://i.ytimg.com/vi/q5FluB5f-b8/hqdefault.jpg"
duplicate_sample=sample+f'\n![本文画像][cover]\n\n画像の説明と[出典](https://example.org/image)。\n\n![別の画像](https://i.ytimg.com/vi/second/hqdefault.jpg)\n\n[cover]: {cover_url}\n'
article_path=root/"articles/pineapple.md"
article_path.write_text(duplicate_sample,encoding="utf-8")
b.build()
duplicate_html=(b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
loaded=next(a for a in b.load() if a["slug"]=="pineapple")
assert 'class="blog-cover"' not in duplicate_html
assert '<div class="blog-prose">'+loaded["html"] in duplicate_html
assert loaded["html"].count(f'src="{cover_url}"')==1
assert '別の画像' in duplicate_html and '画像の説明' in duplicate_html
assert '<a href="https://example.org/image">出典</a>' in duplicate_html
assert '<a href="https://example.org/source">検証用資料 ↗</a>' in duplicate_html
assert f'<meta property="og:image" content="{cover_url}">' in duplicate_html
assert f'"image": "{cover_url}"' in duplicate_html
assert f'<img src="{cover_url}"' in b.card(loaded)
assert f'<img src="{cover_url}"' in (b.OUT/"blog/index.html").read_text(encoding="utf-8")
# A dedicated thumbnail stays in cards/share metadata, never ahead of the prose.
thumbnail_url="https://i.ytimg.com/vi/dedicated/hqdefault.jpg"
dedicated_sample=duplicate_sample.replace(f'image: {cover_url}',f'image: {thumbnail_url}\nshow_cover: false')
article_path.write_text(dedicated_sample,encoding="utf-8")
b.build()
dedicated_html=(b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
dedicated=next(a for a in b.load() if a["slug"]=="pineapple")
assert dedicated["html"]==loaded["html"]
assert 'class="blog-cover"' not in dedicated_html
assert f'src="{thumbnail_url}"' not in dedicated_html
assert f'<meta property="og:image" content="{thumbnail_url}">' in dedicated_html
assert f'"image": "{thumbnail_url}"' in dedicated_html
assert f'<img src="{thumbnail_url}"' in b.card(dedicated)
assert f'<img src="{thumbnail_url}"' in (b.OUT/"blog/index.html").read_text(encoding="utf-8")
article_path.write_text(dedicated_sample.replace('show_cover: false','show_cover: "false"'),encoding="utf-8")
try:
    b.load()
except ValueError as error:
    assert 'show_cover must be boolean' in str(error)
else:
    raise AssertionError('Non-boolean show_cover accepted')
print("PASS: dedicated thumbnail differs from body images, is never repeated above prose, and validates its cover flag")
article_path.write_text(sample,encoding="utf-8")
b.build()
article_html=(b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
assert 'class="blog-cover"' in article_html
print("PASS: duplicate cover omitted; nonduplicate cover, prose, captions, sources, cards and share images preserved")
assert b.media.article_video_ids({})==[]
assert b.media.article_video_ids({"youtube":"q5FluB5f-b8"})==["q5FluB5f-b8"]
assert b.media.article_video_ids({"youtube":"q5FluB5f-b8","youtube_related":[]})==["q5FluB5f-b8"]
assert '<h2>関連動画</h2>' not in article_html
assert '<iframe' not in article_html
assert 'youtube-nocookie.com/embed/' not in article_html
primary_video='<section><h2>動画はこちら</h2><p><a href="https://www.youtube.com/watch?v=q5FluB5f-b8">パイナップルの木は</a></p></section>'
assert primary_video+'</div>' in article_html
assert '確認日' not in article_html
assert '漫画動画で楽しむ' not in article_html
assert '<h2>動画はこちら</h2>' in article_html
assert '<h2>漫画はこちら</h2>' not in article_html
assert '<a href="https://www.youtube.com/watch?v=q5FluB5f-b8">パイナップルの木は</a>' in article_html
assert article_html.index('<h2>出典・参考資料</h2>') < article_html.index('<h2>動画はこちら</h2>')
assert '/blog/second/' in (b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
assert '/blog/second/' in (b.OUT/"blog/category/food/index.html").read_text(encoding="utf-8")
second.write_text(second.read_text(encoding="utf-8").replace("## パイナップルの正体","## 更新確認の正体"),encoding="utf-8")
b.build()
assert "更新確認の正体" in (b.OUT/"blog/second/index.html").read_text(encoding="utf-8")
second.write_text(second.read_text(encoding="utf-8").replace("---\n","---\ndraft: true\n",1),encoding="utf-8")
b.build()
assert not (b.OUT/"blog/second/index.html").exists()
assert '/blog/second/' not in (b.OUT/"blog/index.html").read_text(encoding="utf-8")
assert '/blog/second/' not in home_path.read_text(encoding="utf-8")
second.write_text(sample.replace("category: 食べ物","category: 不明"),encoding="utf-8")
try:
    b.load()
except ValueError:
    pass
else:
    raise AssertionError("Unknown category accepted")
print("PASS: additions, related/category links, revisions, draft exclusion, stale-page removal, metadata rejection")
# Freeze UTC instants, then exercise the real metadata loader across JST boundaries.
from datetime import date, datetime, timedelta
from unittest.mock import patch
second.write_text(sample.replace("---\n", "---\ndraft: true\n", 1), encoding="utf-8")
article=root/"articles/pineapple.md"
for instant, expected_today in (
    ("2026-11-05T14:59:59+00:00", "2026-11-05"),  # JST 23:59:59
    ("2026-11-05T15:00:00+00:00", "2026-11-06"),  # JST 00:00
    ("2026-11-05T23:59:59+00:00", "2026-11-06"),  # JST 08:59:59
    ("2026-11-06T00:00:00+00:00", "2026-11-06"),  # JST 09:00
    ("2026-11-06T14:59:59+00:00", "2026-11-06"),  # JST 23:59:59
    ("2026-12-31T15:00:00+00:00", "2027-01-01"),  # year boundary
):
    frozen=datetime.fromisoformat(instant)
    with patch.object(b, "datetime") as clock, patch.object(b, "date", wraps=date) as host_date:
        host_date.today.return_value=frozen.date()  # Simulate a UTC GitHub runner.
        clock.now.side_effect=lambda tz: frozen.astimezone(tz)
        # Both a new publication and an update to an older article are allowed today.
        for published in (expected_today, "2026-11-01"):
            article.write_text(sample.replace("\ndate: 2026-11-06", "\ndate: "+published)
                               .replace("updated: 2026-11-06", "updated: "+expected_today), encoding="utf-8")
            assert b.load()[0]["updated"] == expected_today
        # Future publication/update and update-before-publication remain invalid.
        tomorrow=(date.fromisoformat(expected_today)+timedelta(days=1)).isoformat()
        for published, updated in (
            (tomorrow, tomorrow),
            ("2026-11-01", tomorrow),
            (expected_today, "2026-11-01"),
        ):
            article.write_text(sample.replace("\ndate: 2026-11-06", "\ndate: "+published)
                               .replace("updated: 2026-11-06", "updated: "+updated), encoding="utf-8")
            try:
                b.load()
            except ValueError as error:
                assert "invalid dates" in str(error)
            else:
                raise AssertionError((instant, published, updated))
print("PASS: JST midnight/09:00/year boundaries, same-day publications/updates, invalid dates")
b.ROOT,b.OUT=original_root,original_out

# Dedicated thumbnails may preserve the complete artwork rather than crop it.
card_fixture=dict(cover,title="Test",category="食べ物",description="Test",date="2026-11-10")
assert 'class="thumbnail-contain"' in b.card(dict(card_fixture,thumbnail_fit="contain"))
assert 'class="thumbnail-contain"' not in b.card(card_fixture)
print("PASS: thumbnail contain mode is opt-in and leaves default cards unchanged")
