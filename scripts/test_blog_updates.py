"""Exercise article additions and updates with isolated fixtures."""
import tempfile
from pathlib import Path
import build_blog as b
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
b.build()
article_html=(b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
assert '<iframe' not in article_html
assert '確認日' not in article_html
assert '漫画動画で楽しむ' not in article_html
assert '<h2>漫画はこちら</h2>' in article_html
assert '<a href="https://www.youtube.com/watch?v=q5FluB5f-b8">パイナップルの木は</a>' in article_html
assert article_html.index('<h2>出典・参考資料</h2>') < article_html.index('<h2>漫画はこちら</h2>')
assert '/blog/second/' in (b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
assert '/blog/second/' in (b.OUT/"blog/category/food/index.html").read_text(encoding="utf-8")
second.write_text(second.read_text(encoding="utf-8").replace("## パイナップルの正体","## 更新確認の正体"),encoding="utf-8")
b.build()
assert "更新確認の正体" in (b.OUT/"blog/second/index.html").read_text(encoding="utf-8")
second.write_text(second.read_text(encoding="utf-8").replace("---\n","---\ndraft: true\n",1),encoding="utf-8")
b.build()
assert not (b.OUT/"blog/second/index.html").exists()
assert '/blog/second/' not in (b.OUT/"blog/index.html").read_text(encoding="utf-8")
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
