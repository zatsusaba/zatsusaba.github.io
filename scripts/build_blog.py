"""Build static blog in an isolated Pages artifact."""
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from html import escape as e
import json, re, shutil
import markdown, yaml

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"_site"
BASE="https://zatsusaba.github.io"
# Current Japanese civil time (UTC+09:00), independent of the runner timezone.
JST=timezone(timedelta(hours=9), "Asia/Tokyo")
CATS=dict(zip(["食べ物","人体","動物","自然","宇宙","歴史","心理","お金","身近なモノ"],["food","body","animals","nature","space","history","psychology","money","everyday"]))
def check(ok,msg):
    if not ok: raise ValueError(msg)
def load():
    today=datetime.now(JST).date().isoformat()
    result=[]
    for p in sorted((ROOT/"articles").glob("*.md")):
        check(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",p.stem),f"Invalid slug: {p}")
        raw=p.read_text(encoding="utf-8")
        check(raw.startswith("---\n"),f"Missing metadata: {p}")
        _,meta,body=raw.split("---",2)
        a=yaml.safe_load(meta)
        if a.get("draft",False): continue
        for key in ("title","description","date","updated","category","image","image_alt","sources"):
            check(a.get(key),f"{p}: missing {key}")
        check(a["category"] in CATS,f"{p}: unknown category")
        for key in ("date","updated"): a[key]=date.fromisoformat(str(a[key])).isoformat()
        check(a["date"]<=a["updated"]<=today,f"{p}: invalid dates")
        check(not a.get("youtube") or re.fullmatch(r"[\w-]{11}",a["youtube"]),f"{p}: invalid video ID")
        for s in a["sources"]: check(s.get("title") and s.get("url","").startswith("https://"),f"{p}: invalid source")
        check(a["image"].startswith(("/assets/","https://i.ytimg.com/")),f"{p}: invalid image")
        if a["image"].startswith("/"): check((ROOT/a["image"].lstrip("/")).is_file(),f"{p}: missing image")
        check(not re.search(r"<\s*/?\s*[a-zA-Z!]|^# ",body,re.M),f"{p}: raw HTML/h1 unsupported")
        check(not re.search(r"\]\(\s*(javascript|data):",body,re.I),f"{p}: unsafe URL")
        a.update(slug=p.stem,url=f"/blog/{p.stem}/",body=body,html=markdown.markdown(body,extensions=["extra","sane_lists"]))
        result.append(a)
    return sorted(result,key=lambda a:(a["date"],a["slug"]),reverse=True)
def nav():
    return ''.join(f'<a href="{u}"'+(' aria-current="page"' if u=="/blog/" else '')+f'>{t}</a>' for u,t in [("/","HOME"),("/blog/","雑学Blog"),("/story.html","STORY"),("/characters.html","CHARACTERS"),("/videos.html","VIDEOS")])
def page(title,desc,url,body,image="/assets/hero-duo-v2.png",article=False):
    image=image if image.startswith("https://") else BASE+image
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | 雑学サバイバル</title><meta name="description" content="{e(desc,quote=True)}"><link rel="canonical" href="{BASE}{url}">
<meta property="og:title" content="{e(title,quote=True)}"><meta property="og:description" content="{e(desc,quote=True)}"><meta property="og:url" content="{BASE}{url}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:image" content="{e(image,quote=True)}"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/logo-cut.png"><link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/blog.css"></head><body class="blog-page"><a class="skip" href="#main">本文へ</a><header><a class="brand" href="/"><img src="/assets/logo-cut.png" alt="雑学サバイバル"><span>ZATSUGAKU<br>SURVIVAL</span></a><nav aria-label="メインナビゲーション">{nav()}</nav></header><main id="main">{body}</main><footer><a href="/">HOME</a><a href="/blog/">雑学Blog</a><a href="https://www.youtube.com/@zatsusaba">YouTube ↗</a></footer><nav class="mobile-nav" aria-label="モバイルナビゲーション">{nav()}</nav></body></html>'''
def write(url,text):
    p=OUT/url.lstrip("/")
    if url.endswith("/"): p=p/"index.html"
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")
def card(a):
    search=" ".join([a["title"],a["description"],a["body"],*a.get("tags",[])])
    return f'<article class="blog-card" data-search="{e(search,quote=True)}"><a href="{a["url"]}"><img src="{e(a["image"],quote=True)}" alt="{e(a["image_alt"],quote=True)}" width="480" height="270" loading="lazy"><div class="blog-card-copy"><span class="blog-label">{a["category"]}</span><h3>{e(a["title"])}</h3><p>{e(a["description"])}</p><time datetime="{a["date"]}">{a["date"]}</time></div></a></article>'
def categories():
    return '<nav class="blog-categories" aria-label="記事カテゴリー"><a href="/blog/">すべて</a>'+''.join(f'<a href="/blog/category/{slug}/">{name}</a>' for name,slug in CATS.items())+'</nav>'
def listing(items,title="雑学Blog",url="/blog/"):
    body=f'<section class="blog-shell"><p class="eyebrow">ZATSUSABA ENCYCLOPEDIA</p><h1>{title}<span>日常の「なぜ？」を、もっと深く。</span></h1><p>マンガで出会った不思議を、出典といっしょに読み解く雑学大百科。</p>{categories()}<div class="blog-tools"><label for="blog-search">記事をキーワードで探す</label><input id="blog-search" type="search" placeholder="例：パイナップル、植物"><p>新着順 · <span id="blog-count" role="status">{len(items)}件</span></p></div><div class="blog-grid">'+''.join(map(card,items))+'</div><p id="blog-empty"'+(' hidden' if items else '')+'>記事が見つかりません。別のキーワードやカテゴリーをお試しください。</p></section><script src="/blog-search.js" defer></script>'
    return page(title,"身近な疑問を出典から読み解く、雑学サバイバルの雑学大百科。",url,body)
def build():
    items=load()
    OUT.mkdir(exist_ok=True)
    manifest=OUT/".blog-generated.json"
    if manifest.exists():
        for rel in json.loads(manifest.read_text()):
            target=(OUT/rel).resolve()
            check(target.is_relative_to(OUT.resolve()) and target.suffix in (".html",".xml"),"Invalid build manifest")
            if target.is_file(): target.unlink()
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in (".html",".css",".js",".txt") and p.name!="requirements-blog.txt": shutil.copy2(p,OUT/p.name)
    for folder in ("assets","panels-v2"):
        shutil.copytree(ROOT/folder,OUT/folder,dirs_exist_ok=True)
    urls=["/","/story.html","/characters.html","/videos.html","/video.html","/blog/"]
    write("/blog/",listing(items))
    for name,slug in CATS.items():
        u=f"/blog/category/{slug}/"; write(u,listing([a for a in items if a["category"]==name],name+"の雑学",u)); urls.append(u)
    for a in items:
        related=sorted([b for b in items if b!=a],key=lambda b:(b["category"]==a["category"],len(set(b.get("tags",[]))&set(a.get("tags",[])))),reverse=True)[:3]
        video=(f'<section><h2>漫画動画で楽しむ</h2><iframe class="blog-video" src="https://www.youtube-nocookie.com/embed/{a["youtube"]}" title="関連する漫画動画" loading="lazy" allowfullscreen></iframe><p><a href="https://www.youtube.com/watch?v={a["youtube"]}">YouTubeで見る ↗</a></p></section>' if a.get("youtube") else "")
        refs='<section><h2>出典・参考資料</h2><ul>'+''.join(f'<li><a href="{e(s["url"],quote=True)}">{e(s["title"])} ↗</a></li>' for s in a["sources"])+'</ul></section>'
        body=f'<article class="blog-article"><p class="blog-breadcrumb"><a href="/">HOME</a> / <a href="/blog/">雑学Blog</a> / <a href="/blog/category/{CATS[a["category"]]}/">{a["category"]}</a></p><span class="blog-label">{a["category"]}</span><h1>{e(a["title"])}</h1><p class="blog-deck">{e(a["description"])}</p><p class="blog-date">公開 {a["date"]} · 更新 <time datetime="{a["updated"]}">{a["updated"]}</time></p><img class="blog-cover" src="{e(a["image"],quote=True)}" alt="{e(a["image_alt"],quote=True)}" width="800" height="450"><div class="blog-prose">{a["html"]}{video}{refs}</div><section><h2>あわせて読みたい</h2><div class="blog-grid">'+''.join(map(card,related))+'</div><p><a class="blog-cta" href="/blog/">雑学Blogの記事一覧へ →</a></p></section></article>'
        schema={"@context":"https://schema.org","@type":"BlogPosting","headline":a["title"],"description":a["description"],"datePublished":a["date"],"dateModified":a["updated"],"image":a["image"] if a["image"].startswith("https://") else BASE+a["image"],"mainEntityOfPage":BASE+a["url"],"author":{"@type":"Organization","name":"雑学サバイバル"}}
        body+='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace("<","\\u003c")+'</script>'
        write(a["url"],page(a["title"],a["description"],a["url"],body,a["image"],True)); urls.append(a["url"])
    for p in OUT.glob("*.html"):
        html=p.read_text(encoding="utf-8")
        html=re.sub(r'(<a href="index.html"[^>]*>HOME</a>)',lambda m:m[0]+'<a href="/blog/">雑学Blog</a>',html)
        if p.name=="index.html":
            section='<section class="blog-home" aria-labelledby="blog-title"><div class="blog-home-head"><div><p class="eyebrow">ZATSUSABA ENCYCLOPEDIA</p><h2 id="blog-title">雑学Blog<span>読む、雑学大百科。</span></h2><p>マンガの先にある「なぜ？」を、出典からもっと深く。</p></div><a class="blog-cta" href="/blog/">記事一覧へ ↗</a></div>'+categories()+'<h3>新着記事</h3><div class="blog-grid">'+''.join(map(card,items[:3]))+'</div></section>'
            html=html.replace('<section class="section light home-section home-videos-section">',section+'<section class="section light home-section home-videos-section">')
        u="/" if p.name=="index.html" else "/"+p.name
        if 'rel="canonical"' not in html: html=html.replace("</head>",f'<link rel="canonical" href="{BASE}{u}"></head>')
        if '/blog.css' not in html: html=html.replace("</head>",'<link rel="stylesheet" href="/blog.css"></head>')
        p.write_text(html,encoding="utf-8")
    write("/404.html",page("ページが見つかりません","記事一覧やホームからお探しください。","/404.html",'<section class="blog-shell"><h1>404</h1><p>ページが見つかりません。</p><a class="blog-cta" href="/blog/">雑学Blogへ →</a><p><a href="/">HOMEへ戻る</a></p></section>').replace("</head>",'<meta name="robots" content="noindex"></head>'))
    write("/sitemap.xml",'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}{u}</loc></url>' for u in urls)+'</urlset>')
    write("/robots.txt",f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    (OUT/".blog-generated.json").write_text(json.dumps([str(p.relative_to(OUT)) for p in OUT.rglob("*.html")]+["sitemap.xml"]))
    print(f"Built {len(items)} articles into {OUT}")
if __name__=="__main__": build()
