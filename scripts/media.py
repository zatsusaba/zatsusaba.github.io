"""Static archives, reading views and explicit relationships for the media site."""
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from html import escape
from pathlib import PurePosixPath

from editorial import metadata, state

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
    ids=set()
    folder=root / "comics"
    for path in sorted([*folder.glob("*.yml"),*folder.glob("*.yaml")]):
        if path.stem in ids:
            raise ValueError(f"{path}: duplicate comic ID")
        ids.add(path.stem)
        data = metadata(path.read_text(encoding="utf-8"),path)
        if not isinstance(data,dict): raise ValueError(f"{path}: expected YAML mapping")
        if data.get("id",path.stem)!=path.stem: raise ValueError(f"{path}: id must match filename")
        if state(data,{"draft","pending","approved"},"draft",path)!="approved":
            for panel in data.get("panels",[]):
                if not isinstance(panel,dict) or not str(panel.get("src","")).startswith(f"/comic-media/{path.stem}/"):
                    raise ValueError(f"{path}: unpublished panels belong under comic-media/{path.stem}/")
            continue
        if not isinstance(data.get("approval"),str) or not data["approval"].strip():
            raise ValueError(f"{path}: record the author's approval before publishing")
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
            require(PurePosixPath(src).suffix.lower() in {".jpg",".jpeg",".png",".webp",".avif"} and src.startswith(("/panels-v2/", f"/comic-media/{path.stem}/")) and ".." not in PurePosixPath(src).parts
                    and "\\" not in src and (root / src[1:]).is_file() and panel.get("alt"), "panel")
            require(isinstance(panel.get("text"),str),"panels[].text (empty string for silent panel)")
        require(len({p["src"] for p in data["panels"]})==4,"four distinct panels")
        for key in ("characters","themes","tags","articles","videos"):
            values = data.setdefault(key, [])
            require(isinstance(values, list) and all(isinstance(v,str) and v for v in values), key)
        require(all(re.fullmatch(r"[A-Za-z0-9_-]{11}", v) for v in data["videos"]), "videos")
        if "trivia" in data:
            require(isinstance(data["trivia"], str) and data["trivia"].strip(), "trivia")
        if "sources" in data:
            require(isinstance(data["sources"], list) and all(
                isinstance(source, dict)
                and isinstance(source.get("citation"), str) and source["citation"].strip()
                and isinstance(source.get("url"), str) and source["url"].startswith("https://doi.org/")
                for source in data["sources"]), "sources")
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


def comic_sheet(comic):
    cells=[]
    for number,panel in enumerate(comic["panels"],1):
        src=escape(panel["src"],quote=True)
        alt=panel["alt"]
        if panel["text"] and panel["text"] not in alt:
            alt += " "+panel["text"]
        cells.append(f'<a href="{src}" title="{number}コマ目を拡大"><img src="{src}" alt="{escape(alt,quote=True)}" loading="lazy"></a>')
    viewer = ('<dialog id="comic-viewer" aria-label="拡大した漫画"><div class="viewer-tools">'
              '<output aria-live="polite"></output><button type="button" data-close autofocus>閉じる ×</button></div>'
              '<img alt=""><button type="button" data-prev aria-label="前のコマ">‹</button>'
              '<button type="button" data-next aria-label="次のコマ">›</button></dialog>'
              '<script type="module" src="/comic-viewer.js"></script>')
    return '<div class="comic-sheet" role="group" aria-label="上から順に読む4コマ">'+''.join(cells)+'</div>'+viewer


def render_comics(comics, articles, page, write, urls, known_videos, enabled=True):
    by_slug = {a["slug"]: a for a in articles}
    reverse = defaultdict(list)
    video_map = defaultdict(list)
    for a in articles:
        if a.get("youtube") in known_videos:
            video_map[a["youtube"]].append([a["url"],a["title"]])
    if not enabled:
        write("/video-links.json",compact(video_map))
        return reverse
    groups = {"/comics/": ("Comic", comics)}
    facets = []
    for key,kind,label in (("characters","character","登場キャラ"),("themes","theme","テーマ")):
        values = sorted({v for c in comics for v in c[key]})
        if values:
            facets.append('<div class="comic-tags"><strong>'+label+'</strong> ')
        for v in values:
            url = group_url(kind,v)
            groups[url] = (v+"の漫画", [c for c in comics if v in c[key]])
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
        trivia = ('<section class="comic-trivia"><h2>雑学</h2><p>'+escape(c["trivia"])+"</p>"
                  + ('<h2>出典</h2><ul>'+''.join('<li>'+link(s["url"],s["citation"])+"</li>" for s in c.get("sources",[]))+"</ul>" if c.get("sources") else '')
                  + '</section>') if c.get("trivia") else ''
        body = ('<article class="blog-article comic-detail">'+comic_sheet(c)+'<div class="comic-info">'+link("/comics/","← Comic一覧")+
                f'<p class="eyebrow">COMICS · {c["date"]}</p><h1>{escape(c["title"])}</h1>'
                +'<div class="comic-tags">'+''.join(tags)+'</div>'
                + ("<p>"+escape("・".join(c["tags"]))+"</p>" if c["tags"] else "")
                + trivia
                + ('<h2>関連する記事・動画</h2><ul>'+''.join('<li>'+r+'</li>' for r in refs)+'</ul>' if refs else '')
                + ('<nav class="pager" aria-label="前後の作品">'+''.join(neighbors)+'</nav>' if neighbors else '')
                +link("/comics/","Comic一覧へ")+'</div></article>')
        write(c["url"],page(c["title"],"・".join(c["characters"])+"が登場する4コマ漫画「"+c["title"]+"」。",c["url"],body,c["panels"][0]["src"]))
        urls.append(c["url"])
    write("/video-links.json",compact(video_map))
    return reverse


def home_sections(items, comics, card, categories, today_home):
    latest = items[0] if items else None
    previous = items[1:4]
    html = '<section class="blog-home media-home"><div class="blog-home-head"><div><h2 id="blog-title">雑学Blog</h2></div><a class="blog-cta" href="/blog/">記事一覧へ →</a></div>'
    html += '<div class="media-categories"><h3>カテゴリーから探す</h3>'+categories()+'</div>'
    if latest:
        html += '<h3>新着記事</h3><div class="media-feature">'+card(latest)+'</div>'
    if previous:
        html += '<h3>記事一覧</h3><div class="blog-grid">'+''.join(map(card,previous))+'</div>'
    html += '</section>'
    shelf = ('<section class="blog-home comic-home comic-archive"><div class="blog-home-head">'
             '<h2>Comic</h2><a class="blog-cta" href="/comics/">漫画一覧へ →</a></div>'
             '<div class="blog-grid">'+''.join(comic_card(c) for c in comics[:6])+'</div></section>')
    return (shelf if comics else "") + html + today_home
