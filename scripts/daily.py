"""Build the daily video calendar exclusively from the public sync catalog."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
import json
import re

from media import link, pages

JST = timezone(timedelta(hours=9))


def calendar(videos, root):
    migration = root / "config/youtube-published.json"
    verified = json.loads(migration.read_text(encoding="utf-8-sig")) if migration.exists() else {}
    format_path=root/"config/youtube-formats.json"
    formats=json.loads(format_path.read_text(encoding="utf-8-sig")) if format_path.exists() else {}
    groups = defaultdict(list)
    seen = set()
    for video in videos:
        vid = video["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) or vid in seen:
            raise ValueError(f"youtube-videos.js: invalid or duplicate ID {vid}")
        seen.add(vid)
        stamp = video.get("publishedAt") or verified.get(vid)
        day = ""
        if stamp:
            instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if instant.tzinfo is None:
                raise ValueError(f"{vid}: publishedAt needs timezone")
            if instant > datetime.now(JST):
                raise ValueError(f"{vid}: future public timestamp")
            day = instant.astimezone(JST).date().isoformat()
            stamp = instant.astimezone(timezone.utc).isoformat()
            if video.get("publishedAt") and day != video["date"]:
                raise ValueError(f"{vid}: date disagrees with JST publishedAt")
        # Old sync classified duration >=60 seconds as long; never reuse that label.
        kind = video["format"] if video.get("formatEvidence") else formats.get(vid,{}).get("format","未確認")
        groups[day].append((stamp or "", vid, video["title"], kind))
    for day, entries in groups.items():
        if day:
            entries.sort(reverse=True)
    return groups


def render(videos, articles, root, page, write, urls):
    groups = calendar(videos, root)
    days = sorted((day for day in groups if day), reverse=True)
    deep = defaultdict(list)
    for article in articles:
        if article.get("youtube"):
            deep[article["youtube"]].append(article)

    def cards(dated_entries):
        result = []
        for day, (_, vid, title, kind) in dated_entries:
            href = "/video.html?id="+vid
            label = "種別未確認" if kind == "未確認" else kind
            extra = "".join(link(a["url"], "詳しく読む："+a["title"]) for a in deep[vid])
            result.append(f'<article class="daily-card"><a href="{href}"><img loading="lazy" width="320" height="180" src="https://i.ytimg.com/vi/{vid}/mqdefault.jpg" alt=""><small>{escape(day or "公開日時を確認中")} · {escape(label)}</small><h3>{escape(title)}</h3></a>{extra}</article>')
        return '<div class="daily-grid">'+"".join(result)+'</div>'

    for day, entries in groups.items():
        base = "/today/"+(day or "undated")+"/"
        title = day+" の雑学" if day else "公開日時を確認中の動画"
        for url, chunk, pager, number in pages(entries, base):
            heading = title if number==1 else f"{title}（{number}ページ）"
            body = '<section class="blog-shell daily-archive">'+link("/today/","← 今日の雑学")+'<h1>'+heading+'</h1>'+cards((day, row) for row in chunk)+pager+'</section>'
            write(url,page(heading,"雑学サバイバルの公開動画。",url,body)); urls.append(url)

    today=datetime.now(JST).date().isoformat()
    rows=groups.get(today,[])
    empty='<p>本日の公開動画はまだありません。</p>'
    grid=(f'<div data-daily-date="{today}">'+cards((today,row) for row in rows)+'</div>'
          +'<p data-daily-empty hidden>本日の公開動画はまだありません。</p>' if rows else empty)
    grid += '<script defer src="/daily-date.js"></script>'
    dates = "".join(link("/today/"+d+"/",d) for d in days)
    if "" in groups:
        dates += link("/today/undated/","公開日時を確認中の動画")
    archive = '<section class="blog-shell daily-archive"><h1>今日の雑学</h1>'
    archive += grid+'<h2>過去の更新</h2><div class="daily-dates">'+dates+'</div></section>'
    write("/today/",page("今日の雑学","公開済み動画を日本時間の公開日から探せます。","/today/",archive))
    urls.append("/today/")
    return '<section class="blog-home daily-home"><div class="blog-home-head"><div><p class="eyebrow">YOUTUBE</p><h2>今日の雑学</h2></div></div>'+grid+'<p>'+link('/videos.html','動画一覧へ →')+'</p></section>'
