"""Build static blog in an isolated Pages artifact."""
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from html import escape as e
import json, re, shutil
import markdown
import daily, editorial
import site_info
from xml.etree import ElementTree as ET
import media

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"_site"
BASE="https://zatsusaba.github.io"
# Current Japanese civil time (UTC+09:00), independent of the runner timezone.
JST=timezone(timedelta(hours=9), "Asia/Tokyo")
CATS=dict(zip(["食べ物","人体","動物","自然","宇宙","歴史","心理","お金","身近なモノ"],["food","body","animals","nature","space","history","psychology","money","everyday"]))
CATS.update({"科学":"science","文化":"culture","世界":"world"})
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
        for key in ("title","description","date","updated","category","sources"):
            check(a.get(key),f"{p}: missing {key}")
        check(a["category"] in CATS,f"{p}: unknown category")
        for key in ("date","updated"): a[key]=date.fromisoformat(str(a[key])).isoformat()
        check(a["date"]<=a["updated"]<=today,f"{p}: invalid dates")
        check(not a.get("youtube") or re.fullmatch(r"[\w-]{11}",a["youtube"]),f"{p}: invalid video ID")
        editorial.sources(a,date.fromisoformat(today),p)
        if not a.get("image"):
            a["image"]=f'/assets/covers/{CATS[a["category"]]}.svg'
            a["image_alt"]=a["category"]+"の雑学"
        check(isinstance(a.get("image_alt"),str) and a["image_alt"].strip(),f"{p}: missing image_alt")
        check(a["image"].startswith(("/assets/","https://i.ytimg.com/")),f"{p}: invalid image")
        if a["image"].startswith("/"): check(".." not in a["image"].split("/") and "\\" not in a["image"] and (ROOT/a["image"].lstrip("/")).is_file(),f"{p}: missing image")
        check(not re.search(r"<\s*/?\s*[a-zA-Z!]|^# ",body,re.M),f"{p}: raw HTML/h1 unsupported")
        check(not re.search(r"\]\(\s*(javascript|data):",body,re.I),f"{p}: unsafe URL")
        check(body.strip(),f"{p}: empty article")
        a.update(slug=p.stem,url=f"/blog/{p.stem}/",body=body,html=markdown.markdown(body,extensions=["extra","sane_lists"]))
        result.append(a)
    return sorted(result,key=lambda a:(a["date"],a["slug"]),reverse=True)
def nav(url):
    return ''.join(f'<a href="{u}"'+(' aria-current="page"' if u in ("/blog/","/today/","/comics/") and url.startswith(u) else '')+f'>{t}</a>' for u,t in [("/","HOME"),("/story.html","STORY"),("/characters.html","CHARACTERS"),("/comics/","Comic"),("/blog/","雑学Blog"),("/today/","今日の雑学"),("/videos.html","VIDEOS")])
def page(title,desc,url,body,image="/assets/hero-duo-v2.png",article=False):
    image=image if image.startswith("https://") else BASE+image
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | 雑学サバイバル</title><meta name="description" content="{e(desc,quote=True)}"><link rel="canonical" href="{BASE}{url}">
<meta property="og:title" content="{e(title,quote=True)}"><meta property="og:description" content="{e(desc,quote=True)}"><meta property="og:url" content="{BASE}{url}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:image" content="{e(image,quote=True)}"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/logo-cut.png"><link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/blog.css"><link rel="stylesheet" href="/media.css"></head><body class="blog-page"><a class="skip" href="#main">本文へ</a><header><a class="brand" href="/"><img src="/assets/logo-cut.png" alt="雑学サバイバル"><span>ZATSUGAKU<br>SURVIVAL</span></a><nav aria-label="メインナビゲーション">{nav(url)}</nav></header><main id="main">{body}</main><footer>{site_info.FOOTER}</footer><nav class="mobile-nav" aria-label="モバイルナビゲーション">{nav(url)}</nav></body></html>'''
def write(url,text):
    p=OUT/url.lstrip("/")
    if url.endswith("/"): p=p/"index.html"
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")
def card(a):
    return f'<article class="blog-card"><a href="{a["url"]}"><img src="{e(a["image"],quote=True)}" alt="{e(a["image_alt"],quote=True)}" width="480" height="270" loading="lazy"><div class="blog-card-copy"><span class="blog-label">{a["category"]}</span><h3>{e(a["title"])}</h3><p>{e(a["description"])}</p><time datetime="{a["date"]}">{a["date"]}</time></div></a></article>'
def categories():
    return '<nav class="blog-categories" aria-label="記事カテゴリー"><a href="/blog/">すべて</a>'+''.join(f'<a href="/blog/category/{slug}/">{name}</a>' for name,slug in CATS.items())+'</nav>'
def listing(items,title,url,total,pager,category):
    body=f'<section class="blog-shell"><h1>{title}</h1><p>世界の雑学を、あなたにお届け。</p>{categories()}<div class="blog-tools"><label for="blog-search">記事をキーワードで探す</label><input id="blog-search" type="search" placeholder="例：パイナップル、植物" data-category="{e(category)}"><label><input type="checkbox" id="body-search"> 本文も検索</label><p>新着順 · <span id="blog-count" role="status">{total}件</span></p></div><div id="archive-list"><div class="blog-grid">'+''.join(map(card,items))+'</div>'+pager+'</div><div id="matches" class="search-results"></div><p id="blog-empty"'+(' hidden' if items else '')+'>記事が見つかりません。別のキーワードやカテゴリーをお試しください。</p></section><script src="/blog-search.js" defer></script>'
    return page(title,"身近な疑問を出典から読み解く、雑学サバイバルの雑学Blog。",url,body)
def build():
    items=load()
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
        shutil.copytree(ROOT/folder,OUT/folder,dirs_exist_ok=True)
    urls=["/","/story.html","/characters.html","/videos.html"]
    media.search_files(items,write)
    archives=[("/blog/","雑学Blog","",items)]
    for name,slug in CATS.items():
        archives.append((f"/blog/category/{slug}/",name+"の雑学",name,[a for a in items if a["category"]==name]))
    for base,title,category,entries in archives:
        for url,chunk,pager,num in media.pages(entries,base):
            heading=title if num==1 else f"{title}（{num}ページ）"
            write(url,listing(chunk,heading,url,len(entries),pager,category))
            urls.append(url)
    catalog=ROOT/"youtube-videos.js"
    videos=json.loads(catalog.read_text(encoding="utf-8").split("=",1)[1].strip().rstrip(";")) if catalog.exists() else []
    known_videos={v["id"]:v["title"] for v in videos}
    urls.extend("/video.html?id="+vid for vid in known_videos if re.fullmatch(r"[A-Za-z0-9_-]{11}",vid))
    today_home=daily.render(videos,items,ROOT,page,write,urls)
    comics=media.load_comics(ROOT,datetime.now(JST).date())
    article_ids={p.stem for p in (ROOT/"articles").glob("*.md")}
    for a in items:
        if a.get("youtube"):
            check(a["youtube"] in known_videos,f'articles/{a["slug"]}.md: unknown public video ID {a["youtube"]}')
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
    comic_links=media.render_comics(comics,items,page,write,urls,known_videos)
    suggestions=media.recommendations(items)
    for a in items:
        related=suggestions[a["slug"]]
        video=""
        if a.get("youtube"):
            video_title=a.get("youtube_title") or known_videos[a["youtube"]]
            video_class="blog-video blog-video-short" if a.get("youtube_format")=="short" else "blog-video"
            video=f'<section><h2>動画はこちら</h2><iframe class="{video_class}" src="https://www.youtube-nocookie.com/embed/{a["youtube"]}" title="{e(video_title,quote=True)}" loading="lazy" allow="encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe><p><a href="https://www.youtube.com/watch?v={a["youtube"]}">{e(video_title)}</a></p></section>'
        related_comics=""
        if comic_links[a["slug"]]:
            related_comics='<h2>関連する4コマ漫画</h2><ul>'+''.join('<li>'+l+'</li>' for l in comic_links[a["slug"]])+'</ul>'
        refs='<section><h2>出典・参考資料</h2><ul>'+''.join(f'<li><a href="{e(s["url"],quote=True)}">{e(s["title"])} ↗</a></li>' for s in a["sources"])+'</ul></section>'
        if a.get("conditions"):
            refs += "<h2>条件・例外</h2><p>"+e(a["conditions"])+"</p>"
        body=f'<article class="blog-article"><p class="blog-breadcrumb"><a href="/">HOME</a> / <a href="/blog/">雑学Blog</a> / <a href="/blog/category/{CATS[a["category"]]}/">{a["category"]}</a></p><span class="blog-label">{a["category"]}</span><h1>{e(a["title"])}</h1><p class="blog-deck">{e(a["description"])}</p><p class="blog-date">公開 {a["date"]} · 更新 <time datetime="{a["updated"]}">{a["updated"]}</time></p><img class="blog-cover" src="{e(a["image"],quote=True)}" alt="{e(a["image_alt"],quote=True)}" width="800" height="450"><div class="blog-prose">{a["html"]}{related_comics}{refs}{video}</div><section><h2>あわせて読みたい</h2><div class="blog-grid">'+''.join(map(card,related))+'</div><p><a class="blog-cta" href="/blog/">雑学Blogの記事一覧へ →</a></p></section></article>'
        if not related:
            body=body.replace('<h2>あわせて読みたい</h2><div class="blog-grid"></div>',"")
        schema={"@context":"https://schema.org","@type":"BlogPosting","headline":a["title"],"description":a["description"],"datePublished":a["date"],"dateModified":a["updated"],"image":a["image"] if a["image"].startswith("https://") else BASE+a["image"],"mainEntityOfPage":BASE+a["url"],"author":{"@type":"Organization","name":"雑学サバイバル"}}
        body+='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace("<","\\u003c")+'</script>'
        write(a["url"],page(a["title"],a["description"],a["url"],body,a["image"],True)); urls.append(a["url"])
    for p in OUT.glob("*.html"):
        html=p.read_text(encoding="utf-8")
        html=re.sub(r'(<a href="characters.html"[^>]*>CHARACTERS</a>)',lambda m:m[0]+'<a href="/comics/">Comic</a><a href="/blog/">雑学Blog</a><a href="/today/">今日の雑学</a>',html)
        html=html.replace("</footer>",site_info.FOOTER+"</footer>")
        if p.name=="index.html":
            token_path=ROOT/"config"/"google-verification"
            if token_path.is_file():
                token=token_path.read_text(encoding="utf-8-sig").strip()
                check(re.fullmatch(r"[A-Za-z0-9_-]+",token),"Invalid public Google verification value")
                html=html.replace("</head>",f'<meta name="google-site-verification" content="{token}"></head>')
            section=media.home_sections(items,comics,card,categories,today_home)
            html=re.sub(r'<section class="home-comic-strip".*?</section>',"",html,flags=re.S)
            html=re.sub(r'<section class="section light home-section home-videos-section">.*?</section>',
                        lambda _: '<!--media:start-->'+section+'<!--media:end-->',html,count=1,flags=re.S)
        u="/" if p.name=="index.html" else "/"+p.name
        if p.name!="video.html" and 'rel="canonical"' not in html: html=html.replace("</head>",f'<link rel="canonical" href="{BASE}{u}"></head>')
        if '/blog.css' not in html: html=html.replace("</head>",'<link rel="stylesheet" href="/blog.css"><link rel="stylesheet" href="/media.css"></head>')
        if 'property="og:url"' not in html:
            html=html.replace("</head>",f'<meta property="og:url" content="{BASE}{u}"><meta property="og:image" content="{BASE}/assets/hero-duo-v2.png"></head>')
        p.write_text(html,encoding="utf-8")
    write("/404.html",page("ページが見つかりません","記事一覧やホームからお探しください。","/404.html",'<section class="blog-shell"><h1>404</h1><p>ページが見つかりません。</p><a class="blog-cta" href="/blog/">雑学Blogへ →</a><p><a href="/">HOMEへ戻る</a></p></section>').replace("</head>",'<meta name="robots" content="noindex"></head>'))
    for url,title,content,desc in [
        ("/editorial-policy/","編集方針・情報の信頼性について",site_info.EDITORIAL_POLICY,"雑学Blogの事実確認とAI活用、出典と確認日の読み方、記事の更新・訂正の方針をご案内します。"),
        ("/privacy/","プライバシーポリシー",site_info.PRIVACY,"ページ配信、YouTube、Cookie、検索、お問い合わせ時の情報の取り扱いについて。"),
        ("/about/","運営者情報",site_info.ABOUT,"雑学サバイバルの作者・緋色牡丹と公式のお問い合わせ先。"),
    ]:
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
    (OUT/".blog-generated.json").write_text(json.dumps(copied_panels+[str(p.relative_to(OUT)) for p in OUT.rglob("*.html")]+["sitemap.xml","video-links.json"]+[str(p.relative_to(OUT)) for p in (OUT/"search").glob("*.json")]))
    print(f"Built {len(items)} articles into {OUT}")
if __name__=="__main__": build()
