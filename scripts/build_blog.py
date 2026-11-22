"""Build static blog in an isolated Pages artifact."""
import subprocess
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from html import escape as e
from html.parser import HTMLParser
from urllib.parse import urljoin
import json, re, shutil
import markdown
import daily, editorial
import site_info
from xml.etree import ElementTree as ET
import media

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"_site"
BASE="https://zatsusaba.github.io"
NEWS_SHARE_IMAGE = "/assets/kyu-frontpage.webp"
# Current Japanese civil time (UTC+09:00), independent of the runner timezone.
JST=timezone(timedelta(hours=9), "Asia/Tokyo")
CATS=dict(zip(["食べ物","人体","動物","自然","宇宙","歴史","心理","お金","身近なモノ"],["food","body","animals","nature","space","history","psychology","money","everyday"]))
CATS.update({"科学":"science","文化":"culture","世界":"world"})
SECTION_NAMES = {"blog": "雑学Blog", "news": "ニュース一覧"}
SEARCH_PATHS = {"blog": ("/search/index.json", "/search/body-"),
                "news": ("/news/search.json", "/news/search-body-")}
def check(ok,msg):
    if not ok: raise ValueError(msg)
def load():
    today=datetime.now(JST).date().isoformat()
    result=[]
    for p in sorted((ROOT/"articles").glob("*.md")):
        check(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",p.stem),f"Invalid slug: {p}")
        check(p.stem not in {"page","category"},f"{p}: reserved archive slug")
        raw=p.read_text(encoding="utf-8")
        check(raw.startswith("---\n"),f"Missing metadata: {p}")
        _,meta,body=raw.split("---",2)
        a=editorial.metadata(meta,p)
        if not isinstance(a,dict): raise ValueError(f"{p}: missing YAML mapping")
        check(a.get("id",p.stem)==p.stem,f"{p}: id must match filename")
        if editorial.state(a,{"draft","published"},"draft",p)!="published": continue
        section = a.setdefault("section", "blog")
        check(section in ("blog", "news"), f"{p}: section must be blog or news")
        for key in ("title","description","date","updated","category","sources"):
            check(a.get(key),f"{p}: missing {key}")
        check(a["category"] in CATS,f"{p}: unknown category")
        if "edition" in a:
            check(a["edition"] in ("朝刊", "夜刊", "号外"), f"{p}: unknown edition")
        for key in ("date","updated"): a[key]=date.fromisoformat(str(a[key])).isoformat()
        check(a["date"]<=a["updated"]<=today,f"{p}: invalid dates")
        try:
            media.article_video_ids(a)
        except ValueError as exc:
            raise ValueError(f"{p}: {exc}") from exc
        editorial.sources(a,date.fromisoformat(today),p)
        if not a.get("image"):
            if section == "news":
                # The legacy category covers carry the printed 雑学Blog masthead.
                # Use the newspaper's masthead artwork for sharing and leave the story text-led.
                a.update(image=NEWS_SHARE_IMAGE, image_alt="雑サバ新聞のキュウちゃん", category_cover=True)
            else:
                a["image"]=f'/assets/covers/{CATS[a["category"]]}.svg'
                a["image_alt"]=a["category"]+"の雑学"
        check(isinstance(a.get("image_alt"),str) and a["image_alt"].strip(),f"{p}: missing image_alt")
        check(type(a.get("show_cover",True)) is bool,f"{p}: show_cover must be boolean")
        check(a.get("thumbnail_fit","cover") in {"cover","contain"},f"{p}: thumbnail_fit must be cover or contain")
        check(a["image"].startswith(("/assets/","https://i.ytimg.com/")),f"{p}: invalid image")
        if a["image"].startswith("/"): check(".." not in a["image"].split("/") and "\\" not in a["image"] and (ROOT/a["image"].lstrip("/")).is_file(),f"{p}: missing image")
        check(not re.search(r"<\s*/?\s*[a-zA-Z!]|^# ",body,re.M),f"{p}: raw HTML/h1 unsupported")
        check(not re.search(r"\]\(\s*(javascript|data):",body,re.I),f"{p}: unsafe URL")
        check(body.strip(),f"{p}: empty article")
        a.update(slug=p.stem,url=f"/{section}/{p.stem}/",body=body,html=markdown.markdown(body,extensions=["extra","sane_lists"]))
        result.append(a)
    # Date remains primary; same-day articles follow their first repository addition.
    added = {}
    try:
        history = subprocess.run(["git", "log", "--reverse", "--format=COMMIT:%cI", "--name-only", "--diff-filter=A", "--", "articles"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
        stamp = ""
        for line in history.splitlines():
            if line.startswith("COMMIT:"): stamp = line[7:]
            elif line.startswith("articles/") and line.endswith(".md"):
                added.setdefault(Path(line).stem, stamp)
    except (OSError, subprocess.CalledProcessError):
        pass
    for a in result:
        stamp = a.get("published_at")
        if stamp:
            instant = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
            check(instant.tzinfo is not None, f"{a['slug']}: published_at needs timezone")
            check(instant.astimezone(JST).date().isoformat() == a["date"], f"{a['slug']}: published_at disagrees with date")
            check(instant <= datetime.now(JST), f"{a['slug']}: future published_at")
            a["published_at"] = instant.astimezone(JST).isoformat()
            a["_order"] = instant.timestamp()
        else:
            a["_order"] = datetime.fromisoformat(added[a["slug"]]).timestamp() if a["slug"] in added else 0
    return sorted(result,key=lambda a:(a["date"],a["_order"],a["slug"]),reverse=True)
def comics_enabled():
    path = ROOT / "config/comics-enabled.json"
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else True
    check(type(value) is bool, "comics-enabled.json must be boolean")
    return value

def news_masthead(url):
    sections = [("/", "一面"), ("/news/", "ニュース一覧"), ("/#zatsusaba", "雑サバ・雑学Blog")]
    anchors = []
    for href, label in sections:
        current = ""
        if href == url:
            current = ' aria-current="page"'
        elif href != "/" and url.startswith(href):
            current = ' aria-current="location"'
        anchors.append(f'<a href="{href}"{current}>{label}</a>')
    return ('<header class="news-masthead"><a class="brand" href="/">'
            '<img src="/assets/logo-cut.png" alt="" width="44" height="44"><span>雑サバ新聞</span></a>'
            '<nav class="news-nav" aria-label="メインナビゲーション">' + ''.join(anchors) + '</nav></header>')

def classic_navigation(url):
    sections = [("/", "ニュース"), ("/story.html", "STORY"), ("/characters.html", "CHARACTERS")]
    if comics_enabled():
        sections.append(("/comics/", "Comic"))
    sections.extend([("/blog/", "雑学Blog"), ("/today/", "今日の動画"), ("/videos.html", "VIDEOS")])
    links = []
    for href, label in sections:
        current = ""
        if url == href:
            current = ' aria-current="page"'
        elif href != "/" and url.startswith(href):
            current = ' aria-current="location"'
        links.append(f'<a href="{href}"{current}>{label}</a>')
    return ''.join(links)

def page(title,desc,url,body,image=None,article=False):
    if image is None:
        image = NEWS_SHARE_IMAGE if url.startswith("/news/") else "/assets/hero-duo-v2.png"
    image=image if image.startswith("https://") else BASE+image
    classic = url.startswith(("/blog/", "/comics/", "/today/"))
    if classic:
        nav = classic_navigation(url)
        header = ('<header><a class="brand" href="/#zatsusaba"><img src="/assets/logo-cut.png" alt="雑学サバイバル">'
                  '<span>ZATSUGAKU<br>SURVIVAL</span></a><nav aria-label="メインナビゲーション">'+nav+'</nav></header>')
        mobile = '<nav class="mobile-nav" aria-label="モバイルナビゲーション">'+nav+'</nav>'
    else:
        header = news_masthead(url)
        mobile = ""
    theme = "classic-inner" if classic else "news-inner"
    view = "article-view" if article else "archive-view"
    brand = "雑サバ新聞" if url.startswith("/news/") else "雑学サバイバル"
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | {brand}</title><meta name="description" content="{e(desc,quote=True)}"><link rel="canonical" href="{BASE}{url}">
<meta property="og:site_name" content="{brand}">
<meta property="og:title" content="{e(title,quote=True)}"><meta property="og:description" content="{e(desc,quote=True)}"><meta property="og:url" content="{BASE}{url}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:image" content="{e(image,quote=True)}"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/logo-cut.png"><link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/blog.css"><link rel="stylesheet" href="/media.css"><link rel="stylesheet" href="/news-home.css"></head><body class="blog-page {theme} {view}"><a class="skip" href="#main">本文へ</a>{header}<main id="main">{body}</main><footer>{site_info.FOOTER}</footer>{mobile}</body></html>'''
def write(url,text):
    p=OUT/url.lstrip("/")
    if url.endswith("/"): p=p/"index.html"
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")
def card(a):
    fit_class=' class="thumbnail-contain"' if a.get("thumbnail_fit")=="contain" else ""
    image = "" if a.get("category_cover") else f'<img{fit_class} src="{e(a["image"],quote=True)}" alt="{e(a["image_alt"],quote=True)}" width="480" height="270" loading="lazy">'
    stamp = a.get("published_at", a["date"])
    printed = stamp[:16].replace("T", " ")
    return f'<article class="blog-card"><a href="{a["url"]}">{image}<div class="blog-card-copy"><span class="blog-label">{a["category"]}</span><h3>{e(a["title"])}</h3><p>{e(a["description"])}</p><time datetime="{stamp}">{printed}</time></div></a></article>'
class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources=set()
    def handle_starttag(self,tag,attrs):
        if tag=="img":
            src=dict(attrs).get("src")
            if src: self.sources.add(src)
def article_cover(a):
    if not a.get("show_cover",True) or a.get("category_cover"): return ""
    # Keep the card/share image, but do not repeat an image already in the prose.
    images=ImageSources()
    images.feed(a["html"])
    article_url=BASE+a["url"]
    image_url=urljoin(article_url,a["image"])
    if any(urljoin(article_url,src)==image_url for src in images.sources): return ""
    return f'<img class="blog-cover" src="{e(a["image"],quote=True)}" alt="{e(a["image_alt"],quote=True)}" width="800" height="450">'
def categories(section="blog", names=CATS):
    return (f'<nav class="blog-categories" aria-label="記事カテゴリー"><a href="/{section}/">すべて</a>'
            + ''.join(f'<a href="/{section}/category/{CATS[name]}/">{name}</a>' for name in names)
            + '</nav>')

def listing(items, title, url, total, pager, category, section, names):
    index_url, body_prefix = SEARCH_PATHS[section]
    news = section == "news"
    desc = ("科学や暮らしの新しい話題を、発表元の資料とともに紹介します。" if news
            else "身近な疑問を出典から読み解く、雑学サバイバルの雑学Blog。")
    intro = desc if news else "世界の雑学を、あなたにお届け。"
    label = "ニュースをキーワードで探す" if news else "記事をキーワードで探す"
    placeholder = "キーワードを入力" if news else "例：パイナップル、植物"
    archive = '<div class="blog-grid">'+''.join(map(card, items))+'</div>'+pager
    if not total and news:
        archive = '<p>公開されたニュースはまだありません。</p>'
    body = (f'<section class="blog-shell"><h1>{e(title)}</h1><p>{intro}</p>{categories(section, names)}'
            f'<div class="blog-tools"><label for="blog-search">{label}</label>'
            f'<input id="blog-search" type="search" placeholder="{placeholder}" data-category="{e(category)}" '
            f'data-index="{index_url}" data-body-prefix="{body_prefix}">'
            '<label><input type="checkbox" id="body-search"> 本文も検索</label>'
            f'<p>新着順 · <span id="blog-count" role="status">{total}件</span></p></div>'
            f'<div id="archive-list">{archive}</div><div id="matches" class="search-results"></div>'
            '<p id="blog-empty"'+(' hidden' if items or news else '')+'>記事が見つかりません。別のキーワードやカテゴリーをお試しください。</p>'
            '</section><script src="/blog-search.js?v=2" defer></script>')
    return page(title, desc, url, body)

def build_archives(items, section, urls):
    media.search_files(items, write, *SEARCH_PATHS[section])
    published_categories = {a["category"] for a in items}
    names = [name for name in CATS if section == "blog" or name in published_categories]
    archives = [(f"/{section}/", SECTION_NAMES[section], "", items)]
    suffix = "のニュース" if section == "news" else "の雑学"
    for name in names:
        entries = [a for a in items if a["category"] == name]
        archives.append((f"/{section}/category/{CATS[name]}/", name+suffix, name, entries))
    for base, title, category, entries in archives:
        for url, chunk, pager, num in media.pages(entries, base):
            heading = title if num == 1 else f"{title}（{num}ページ）"
            write(url, listing(chunk, heading, url, len(entries), pager, category, section, names))
            urls.append(url)

def build():
    items=load()
    news_items = [a for a in items if a["section"] == "news"]
    blog_items = [a for a in items if a["section"] == "blog"]
    OUT.mkdir(exist_ok=True)
    manifest=OUT/".blog-generated.json"
    if manifest.exists():
        for rel in json.loads(manifest.read_text()):
            target=(OUT/rel).resolve()
            check(target.is_relative_to(OUT.resolve()) and (target.suffix in (".html",".xml",".json") or target.is_relative_to((OUT/"comic-media").resolve())),"Invalid build manifest")
            if target.is_file(): target.unlink()
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in (".html",".css",".js",".txt") and p.name!="requirements-blog.txt": shutil.copy2(p,OUT/p.name)
    for folder in ("assets","panels-v2"):
        if folder == "panels-v2" and not comics_enabled():
            for source in (ROOT/folder).rglob("*"):
                target = OUT / source.relative_to(ROOT)
                if source.is_file() and target.is_file():
                    target.unlink()  # Generated copy only; original artwork stays in ROOT.
            continue
        shutil.copytree(ROOT/folder,OUT/folder,dirs_exist_ok=True)
    urls=["/","/story.html","/characters.html","/videos.html"]
    build_archives(blog_items, "blog", urls)
    build_archives(news_items, "news", urls)
    catalog=ROOT/"youtube-videos.js"
    videos=json.loads(catalog.read_text(encoding="utf-8").split("=",1)[1].strip().rstrip(";")) if catalog.exists() else []
    known_videos={v["id"]:v["title"] for v in videos}
    urls.extend("/video.html?id="+vid for vid in known_videos if re.fullmatch(r"[A-Za-z0-9_-]{11}",vid))
    today_home=daily.render(videos,blog_items,ROOT,page,write,urls)
    comics=media.load_comics(ROOT,datetime.now(JST).date()) if comics_enabled() else []
    article_ids={p.stem for p in (ROOT/"articles").glob("*.md")}
    for a in items:
        for vid in media.article_video_ids(a):
            check(vid in known_videos,f'articles/{a["slug"]}.md: unknown public video ID {vid}')
    for c in comics:
        for slug in c["articles"]:
            check(slug in article_ids,f'{c["url"]}: unknown article {slug}')
        for vid in c["videos"]:
            check(vid in known_videos,f'{c["url"]}: unknown video ID {vid}')
    copied_panels=[]
    for comic in comics:
        for panel in comic["panels"]:
            rel=panel["src"].lstrip("/")
            if rel.startswith("comic-media/"):
                target=OUT/rel
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/rel,target)
                copied_panels.append(rel)
    comic_links=media.render_comics(comics,blog_items,page,write,urls,known_videos,enabled=comics_enabled())
    suggestions=media.recommendations(blog_items) | media.recommendations(news_items)
    for a in items:
        related=suggestions[a["slug"]]
        section = a["section"]
        news = section == "news"
        archive_url = f"/{section}/"
        archive_label = SECTION_NAMES[section]
        video=""
        if a.get("youtube"):
            video_title=a.get("youtube_title") or known_videos[a["youtube"]]
            # Keep the article's final video invitation to one formal-title link.
            # Embedded players belong on video pages, not in blog prose.
            primary_video=f'<section><h2>動画はこちら</h2><p><a href="https://www.youtube.com/watch?v={a["youtube"]}">{e(video_title)}</a></p></section>'
            additional = media.article_video_ids(a)[1:]
            if additional:
                links = ''.join('<li>'+media.link("https://www.youtube.com/watch?v="+vid,known_videos[vid])+'</li>' for vid in additional)
                video = '<section><h2>関連動画</h2><ul>'+links+'</ul></section>'
            video += primary_video
        related_comics=""
        if comic_links[a["slug"]]:
            related_comics='<h2>関連する4コマ漫画</h2><ul>'+''.join('<li>'+l+'</li>' for l in comic_links[a["slug"]])+'</ul>'
        reference_items = []
        for source in a["sources"]:
            label = e(source["title"])
            url = e(source["url"], quote=True)
            checked = source["checked"]
            checked_text = f'（確認日 <time datetime="{checked}">{checked}</time>）' if news else ""
            reference_items.append(f'<li><a href="{url}">{label} ↗</a>{checked_text}</li>')
        refs = '<section><h2>出典・参考資料</h2><ul>' + ''.join(reference_items) + '</ul></section>'
        if a.get("conditions"):
            refs += "<h2>条件・例外</h2><p>"+e(a["conditions"])+"</p>"
        stamp = a.get("published_at", a["date"])
        edition = f' <span class="news-edition">{a["edition"]}</span>' if news and a.get("edition") else ""
        author = {"@type":"Organization","name":"雑サバ新聞" if news else "雑学サバイバル"}
        byline = '雑サバ新聞　' if news else ""
        home = media.link("/", "一面") if news else media.link("/#zatsusaba", "雑サバ")
        breadcrumb = " / ".join([home, media.link(archive_url, archive_label),
                                 media.link(archive_url+"category/"+CATS[a["category"]]+"/", a["category"])])
        related_html = '<h2>あわせて読みたい</h2><div class="blog-grid">'+''.join(map(card,related))+'</div>' if related else ""
        cta = "ニュース一覧へ" if news else "雑学Blogの記事一覧へ"
        body = (f'<article class="blog-article"><p class="blog-breadcrumb">{breadcrumb}</p>'
                f'<span class="blog-label">{a["category"]}</span>{edition}<h1>{e(a["title"])}</h1>'
                f'<p class="blog-deck">{e(a["description"])}</p><p class="blog-date">{byline}公開 '
                f'<time datetime="{stamp}">{stamp[:16].replace("T", " ")}</time> · 更新 '
                f'<time datetime="{a["updated"]}">{a["updated"]}</time></p>{article_cover(a)}'
                f'<div class="blog-prose">{a["html"]}{related_comics}{refs}{video}</div>'
                f'<section>{related_html}<p><a class="blog-cta" href="{archive_url}">{cta} →</a></p></section></article>')
        schema={"@context":"https://schema.org","@type":"NewsArticle" if news else "BlogPosting",
                "headline":a["title"],"description":a["description"],"datePublished":stamp,"dateModified":a["updated"],
                "articleSection":a["category"],"isPartOf":{"@type":"CollectionPage","url":BASE+archive_url},
                "image":urljoin(BASE,a["image"]),"mainEntityOfPage":BASE+a["url"],
                "author":author}
        body+='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace("<","\\u003c")+'</script>'
        write(a["url"],page(a["title"],a["description"],a["url"],body,a["image"],True)); urls.append(a["url"])
    for p in OUT.glob("*.html"):
        html=p.read_text(encoding="utf-8")
        html=re.sub(r'(<a href="characters.html"[^>]*>CHARACTERS</a>)',lambda m:m[0]+'<a href="/comics/">Comic</a><a href="/blog/">雑学Blog</a><a href="/#today">今日の動画</a>',html)
        if not comics_enabled():
            html=html.replace('<a href="/comics/">Comic</a>', "")
        html=html.replace("</footer>",site_info.FOOTER+"</footer>")
        if p.name=="index.html":
            token_path=ROOT/"config"/"google-verification"
            if token_path.is_file():
                token=token_path.read_text(encoding="utf-8-sig").strip()
                check(re.fullmatch(r"[A-Za-z0-9_-]+",token),"Invalid public Google verification value")
                html=html.replace("</head>",f'<meta name="google-site-verification" content="{token}"></head>')
            share_image = news_items[0]["image"] if news_items else NEWS_SHARE_IMAGE
            html=html.replace("<!--news:share-image-->", f'<meta property="og:image" content="{e(urljoin(BASE, share_image))}">')
            front = media.news_front(news_items)
            classic = media.home_sections(blog_items, comics, card, categories, today_home)
            html=html.replace("<!--news:masthead-->", news_masthead("/"))
            html=html.replace("<!--news:content-->", "<!--news:start-->"+front+"<!--news:end-->")
            html=html.replace("<!--classic:content-->", "<!--classic:start-->"+classic+"<!--classic:end-->")

        u="/" if p.name=="index.html" else "/"+p.name
        if p.name!="video.html" and 'rel="canonical"' not in html: html=html.replace("</head>",f'<link rel="canonical" href="{BASE}{u}"></head>')
        if '/blog.css' not in html: html=html.replace("</head>",'<link rel="stylesheet" href="/blog.css"><link rel="stylesheet" href="/media.css"></head>')
        if 'property="og:url"' not in html:
            html=html.replace("</head>",f'<meta property="og:url" content="{BASE}{u}"><meta property="og:image" content="{BASE}/assets/hero-duo-v2.png"></head>')
        p.write_text(html,encoding="utf-8")
    write("/404.html",page("ページが見つかりません","記事一覧やホームからお探しください。","/404.html",'<section class="blog-shell"><h1>404</h1><p>ページが見つかりません。</p><a class="blog-cta" href="/blog/">雑学Blogへ →</a><p><a href="/">HOMEへ戻る</a></p></section>').replace("</head>",'<meta name="robots" content="noindex"></head>'))
    for url,title,content,desc in [
        ("/editorial-policy/","編集方針・情報の信頼性について",site_info.EDITORIAL_POLICY,"雑サバ新聞と雑学Blogの事実確認やAI活用、出典と確認日の読み方、記事の更新・訂正の方針をご案内します。"),
        ("/privacy/","プライバシーポリシー",site_info.PRIVACY,"ページ配信、YouTube、Cookie、検索、お問い合わせ時の情報の取り扱いについて。"),
        ("/about/","運営者情報",site_info.ABOUT,"雑学サバイバルの作者・緋色牡丹と公式のお問い合わせ先。"),
    ]:
        if not comics_enabled():
            content=content.replace(' ／ <a href="/comics/">公式4コマ漫画</a>', "")
        write(url,page(title,desc,url,f'<article class="blog-article"><h1>{title}</h1><div class="blog-prose">{content}</div></article>'))
        urls.append(url)
    check(len(urls)==len(set(urls)), "Duplicate public URL")
    modified={a["url"]:a["updated"] for a in items}
    sitemap=ET.Element("urlset",xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in urls:
        entry=ET.SubElement(sitemap,"url")
        ET.SubElement(entry,"loc").text=BASE+url
        if url in modified:
            ET.SubElement(entry,"lastmod").text=modified[url]
    write("/sitemap.xml",ET.tostring(sitemap,encoding="unicode"))
    write("/robots.txt",f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    generated = [*OUT.rglob("*.html"), *(OUT/"search").glob("*.json"), *(OUT/"news").glob("search*.json")]
    manifest.write_text(json.dumps(copied_panels + ["sitemap.xml", "video-links.json"] + [str(p.relative_to(OUT)) for p in generated]))
    print(f"Built {len(items)} articles into {OUT}")
if __name__=="__main__": build()
