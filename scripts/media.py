"""Static archives, reading views and explicit relationships for the media site."""
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from html import escape
from pathlib import PurePosixPath

import yaml

PAGE_SIZE = 24


def compact(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def link(url, title):
    return f'<a href="{escape(url, quote=True)}">{escape(title)}</a>'


def page_url(base, number):
    return base if number == 1 else f"{base}page/{number}/"


def pages(items, base):
    count = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    for number in range(1, count + 1):
        start = (number - 1) * PAGE_SIZE
        controls = []
        if number > 1:
            controls.append(link(page_url(base, number - 1), "← 前へ"))
        controls.append(f'<span>{number} / {count}</span>')
        if number < count:
            controls.append(link(page_url(base, number + 1), "次へ →"))
        pager = '<nav class="pager" aria-label="ページ移動">' + "".join(controls) + '</nav>' if count > 1 else ""
        yield page_url(base, number), items[start:start + PAGE_SIZE], pager, number


def recommendations(items):
    """Rank once per distinct category/tag profile, retaining one spare for self."""
    cached = {}
    profiles = [(a, set(a.get("tags", []))) for a in items]
    result = {}
    for article, tags in profiles:
        key = (article["category"], frozenset(tags))
        if key not in cached:
            ranked = []
            for other, other_tags in profiles:
                shared = len(tags & other_tags)
                same = other["category"] == article["category"]
                if same or shared:
                    ranked.append(((same, shared), other))
            ranked.sort(key=lambda row: row[0], reverse=True)
            cached[key] = [other for _, other in ranked[:4]]
        result[article["slug"]] = [a for a in cached[key] if a is not article][:3]
    return result


def search_files(items, write):
    index = []
    for start in range(0, len(items), 32):
        chunk = items[start:start + 32]
        shard = start // 32
        write(f"/search/body-{shard}.json", compact([a["body"] for a in chunk]))
        for a in chunk:
            index.append([a["url"], a["title"], a["description"], a["category"], a.get("tags", []), a["date"]])
    write("/search/index.json", compact(index))


def load_comics(root, today):
    entries = []
    for path in sorted((root / "comics").glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("draft"):
            continue
        def require(ok, field):
            if not ok:
                raise ValueError(f"{path}: invalid {field}")
        require(re.fullmatch("[a-z0-9]+(?:-[a-z0-9]+)*", path.stem) and path.stem not in {"page","character","theme"}, "slug")
        require(isinstance(data.get("title"), str) and data["title"].strip(), "title")
        published = date.fromisoformat(str(data["date"]))
        require(published <= today, "date")
        require(isinstance(data["panels"], list) and len(data["panels"]) == 4, "panels")
        for panel in data["panels"]:
            src = panel["src"]
            require(src.startswith(("/assets/", "/panels-v2/")) and ".." not in PurePosixPath(src).parts
                    and "\\" not in src and (root / src[1:]).is_file() and panel.get("alt"), "panel")
        for key in ("characters","themes","articles","videos"):
            values = data.setdefault(key, [])
            require(isinstance(values, list) and all(isinstance(v,str) and v for v in values), key)
        require(all(re.fullmatch(r"[A-Za-z0-9_-]{11}", v) for v in data["videos"]), "videos")
        data.update(url=f"/comics/{path.stem}/", date=published.isoformat())
        entries.append(data)
    return sorted(entries, key=lambda c:(c["date"], c["url"]), reverse=True)


def group_url(kind, value):
    return f'/comics/{kind}/{hashlib.sha256(value.encode()).hexdigest()[:12]}/'


def comic_card(c):
    panel = c["panels"][0]
    return (f'<article class="blog-card"><a href="{c["url"]}"><img loading="lazy" src="{escape(panel["src"])}" '
            f'alt="{escape(panel["alt"])}"><div class="blog-card-copy"><time>{c["date"]}</time>'
            f'<h3>{escape(c["title"])}</h3><p>{escape("・".join(c["characters"]))}</p></div></a></article>')


def render_comics(comics, articles, page, write, urls, known_videos):
    by_slug = {a["slug"]: a for a in articles}
    reverse = defaultdict(list)
    video_map = defaultdict(list)
    for a in articles:
        if a.get("youtube") in known_videos:
            video_map[a["youtube"]].append([a["url"],a["title"]])
    groups = {"/comics/": ("4コマ漫画", comics)}
    facets = []
    for key,kind,label in (("characters","character","登場キャラ"),("themes","theme","テーマ")):
        values = sorted({v for c in comics for v in c[key]})
        if values:
            facets.append('<div class="comic-tags"><strong>'+label+'</strong> ')
        for v in values:
            url = group_url(kind,v)
            groups[url] = (v+"の4コマ", [c for c in comics if v in c[key]])
            facets.append(link(url,v))
        if values:
            facets.append('</div>')
    for url,(title,entries) in groups.items():
        for path,chunk,pager,num in pages(entries,url):
            heading = title if num == 1 else f"{title}（{num}ページ）"
            body = ('<section class="blog-shell comic-archive"><p class="eyebrow">COMICS</p>'
                    f'<h1>{escape(heading)}</h1>'+link("/comics/","全作品") + "".join(facets)
                    + '<div class="blog-grid">'+''.join(map(comic_card,chunk))+'</div>'+pager+'</section>')
            write(path,page(heading,title+"を読む。登場キャラとテーマから作品を探せます。",path,body))
            urls.append(path)
    for i,c in enumerate(comics):
        panels = ''.join(f'<img src="{escape(p["src"])}" loading="lazy" alt="{escape(p["alt"])}">' for p in c["panels"])
        refs = []
        for slug in c["articles"]:
            if slug in by_slug:  # Draft/deleted articles have no public URL.
                a = by_slug[slug]
                refs.append(link(a["url"],a["title"]))
                reverse[slug].append(link(c["url"],c["title"]))
        for vid in c["videos"]:
            if vid in known_videos:
                refs.append(link("/video.html?id="+vid,known_videos[vid]))
                video_map[vid].append([c["url"],c["title"]])
        neighbors = []
        if i + 1 < len(comics):
            neighbors.append(link(comics[i+1]["url"],"← 前作："+comics[i+1]["title"]))
        if i:
            neighbors.append(link(comics[i-1]["url"],"次作："+comics[i-1]["title"]+" →"))
        tags = [link(group_url(kind,v),v) for key,kind in (("characters","character"),("themes","theme")) for v in c[key]]
        body = ('<article class="blog-article">'+link("/comics/","← 4コマ漫画一覧")+
                f'<p class="eyebrow">COMICS · {c["date"]}</p><h1>{escape(c["title"])}</h1>'
                +'<div class="comic-tags">'+''.join(tags)+'</div><div class="comic-reader">'+panels+'</div>'
                + ('<h2>関連する記事・動画</h2><ul>'+''.join('<li>'+r+'</li>' for r in refs)+'</ul>' if refs else '')
                + ('<nav class="pager" aria-label="前後の作品">'+''.join(neighbors)+'</nav>' if neighbors else '')
                +link("/comics/","4コマ漫画一覧へ")+'</article>')
        write(c["url"],page(c["title"],"・".join(c["characters"])+"が登場する4コマ漫画「"+c["title"]+"」。",c["url"],body,c["panels"][0]["src"]))
        urls.append(c["url"])
    write("/video-links.json",compact(video_map))
    return reverse


def home_sections(items, comics, card, categories):
    featured = next((a for a in items if a.get("featured")), items[0] if items else None)
    recent = [a for a in items if a is not featured][:3]
    html = '<section class="blog-home media-home"><div class="blog-home-head"><div><p class="eyebrow">ENCYCLOPEDIA</p><h2 id="blog-title">雑学大百科<span>雑学Blog</span></h2></div><a class="blog-cta" href="/blog/">記事一覧へ →</a></div>'
    if featured:
        html += '<h3>特集記事</h3><div class="media-feature">'+card(featured)+'</div>'
    if recent:
        html += '<h3>新着記事</h3><div class="blog-grid">'+''.join(map(card,recent))+'</div>'
    elif featured:
        html = html.replace('<h3>特集記事</h3>', '<h3>特集・新着記事</h3>')
    html += '<div class="media-categories"><h3>カテゴリーから探す</h3>'+categories()+'</div></section>'
    if comics:
        c = comics[0]
        html += ('<section class="blog-home comic-home"><div class="blog-home-head"><div><p class="eyebrow">COMICS</p>'
                 '<h2>新着4コマ漫画</h2></div><a class="blog-cta" href="/comics/">漫画一覧へ →</a></div>'
                 f'<h3>{link(c["url"],c["title"])}</h3><p class="comic-swipe-hint">横にスライドして読む →</p>'
                 '<div class="home-comic-panels" tabindex="0" aria-label="左から順に読む4コマ漫画">'+
                 ''.join(f'<div class="comic-panel"><img src="{escape(p["src"])}" alt="{escape(p["alt"])}" loading="lazy"></div>' for p in c["panels"])+
                 '</div>'+link(c["url"],"縦読みで開く →")+'</section>')
    return html

