"""Check generated links, SEO, legacy content preservation, and article rendering."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
from build_blog import ROOT, OUT, BASE, load, build, article_cover
from site_info import FOOTER
import json, re
from html import escape
from urllib.parse import urljoin

class Document(HTMLParser):
    def __init__(self,text):
        super().__init__(); self.links=[]; self.canon=[]; self.h1=0; self.images=[]
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("a","link","script","img","iframe"):
            u=a.get("href",a.get("src",""))
            if u: self.links.append(u)
        if tag=="link" and a.get("rel")=="canonical": self.canon.append(a["href"])
        if tag=="h1": self.h1+=1
        if tag=="img": self.images.append((a.get("src"),a.get("alt")))

def main():
    build()
    rendered_images=set()
    for p in OUT.rglob("*.html"):
        text=p.read_text(encoding="utf-8"); doc=Document(text)
        rendered_images.update(doc.images)
        assert len(doc.canon)==(0 if p==OUT/"video.html" else 1), f"canonical: {p}"
        assert FOOTER in text, f"Missing operator/privacy links: {p}"
        head=text.split("</head>",1)[0].lower()
        if p!=OUT/"404.html":
            assert "noindex" not in head, f"Unexpected noindex: {p}"
        for u in doc.links:
            bits=urlsplit(u)
            if bits.scheme or bits.netloc or not bits.path: continue
            target=OUT/unquote(bits.path).lstrip("/") if bits.path.startswith("/") else p.parent/unquote(bits.path)
            if target.is_dir(): target=target/"index.html"
            assert target.is_file(), f"Broken link: {p}: {u}"
    if (ROOT/"config/comics-enabled.json").exists() and (ROOT/"config/comics-enabled.json").read_text().strip() == "false":
        assert not list((OUT/"comics").rglob("*.html")), "Comic pages published while paused"
        assert not list((OUT/"comic-media").rglob("*.png")), "Comic panels published while paused"
        assert "/comics/" not in (OUT/"sitemap.xml").read_text(encoding="utf-8")
    home=(OUT/"index.html").read_text(encoding="utf-8")
    generated=home.split('<!--media:start-->',1)[1].split('<!--media:end-->',1)[0]
    articles=load()
    first_page=articles[:4]
    if first_page:
        stories=generated.split('class="news-categories"',1)[0]
        links=Document(stories).links
        article_urls={a["url"] for a in articles}
        assert [url for url in links if url in article_urls]==[a["url"] for a in first_page], "Lead and recent article links must be unique and newest first"
        assert Document(stories).h1==1, "Latest article needs one visible h1"
        assert escape(first_page[0]["title"]) in stories.split('</h1>',1)[0]
    categories=generated.index('class="news-categories"')
    videos=generated.index('id="today"')
    assert categories < videos and '<h2>今日の動画</h2>' in generated[videos:]
    if 'class="blog-home comic-home comic-archive"' in generated:
        assert videos < generated.index('class="blog-home comic-home comic-archive"')
    # Removing only generated content must recover each original page body exactly.
    for name in ("index.html","story.html","characters.html","videos.html","video.html"):
        original=(ROOT/name).read_text(encoding="utf-8").split("<body",1)[1]
        built=(OUT/name).read_text(encoding="utf-8").split("<body",1)[1]
        assert FOOTER in built
        built=built.replace(FOOTER,'')
        if name=="index.html":
            built=re.sub(r'<header class="news-masthead">.*?</header>','<!--news:masthead-->',built,count=1,flags=re.S)
            built=re.sub(r'<!--media:start-->.*?<!--media:end-->','<!--news:content-->',built,flags=re.S)
        else:
            built=built.replace('<a href="/comics/">Comic</a><a href="/blog/">雑学Blog</a><a href="/#today">今日の動画</a>',"")
            built=built.replace('<a href="/blog/">雑学Blog</a><a href="/#today">今日の動画</a>', "")
        assert original==built, f"Unexpected template change: {name}"
    for a in load():
        text=(OUT/a["url"].lstrip("/")/"index.html").read_text(encoding="utf-8")
        assert a["html"] in text and Document(text).h1==1
        assert 'application/ld+json' in text and 'og:image' in text
    ns={"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries=ET.parse(OUT/"sitemap.xml").findall("s:url",ns)
    dates={n.findtext("s:loc",namespaces=ns):n.findtext("s:lastmod",namespaces=ns) for n in entries}
    assert len(entries)==len(dates) and BASE+"/video.html" not in dates
    assert "Sitemap: "+BASE+"/sitemap.xml" in (OUT/"robots.txt").read_text()
    # Follow only real HTML anchors from HOME, without executing JavaScript.
    visited=set()
    pending=["/"]
    while pending:
        url=pending.pop()
        if url in visited: continue
        visited.add(url)
        path=OUT/url.lstrip("/")
        if path.is_dir(): path=path/"index.html"
        if not path.is_file() or path.suffix!=".html": continue
        html=path.read_text(encoding="utf-8")
        for href in re.findall(r'<a\s+[^>]*?href="([^"]+)"',html):
            target=urlsplit(urljoin(BASE+url,href))
            if target.netloc=="zatsusaba.github.io": pending.append(target.path)
    policy="/editorial-policy/"
    assert policy in visited and BASE+policy in dates
    assert Document((OUT/"editorial-policy/index.html").read_text(encoding="utf-8")).canon==[BASE+policy]
    for a in load():
        url=a["url"]
        html=(OUT/url.strip("/")/"index.html").read_text(encoding="utf-8")
        assert url in visited and dates[BASE+url]==a["updated"]
        assert Document(html).canon==[BASE+url] and "noindex" not in html.split("</head>")[0]
        schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',html).group(1))
        assert f'<title>{escape(a["title"])} | 雑学サバイバル</title>' in html
        assert f'<meta name="description" content="{escape(a["description"])}">' in html
        assert (a["image"],a["image_alt"]) in rendered_images
        cover=article_cover(a)
        assert cover in html if cover else 'class="blog-cover"' not in html
        share_image=a["image"] if a["image"].startswith("https://") else BASE+a["image"]
        assert f'<meta property="og:image" content="{escape(share_image)}">' in html
        assert schema["image"]==share_image
        assert schema["@type"]=="BlogPosting" and schema["headline"]==a["title"]
        assert schema["datePublished"]==a["date"] and schema["dateModified"]==a["updated"]
        assert schema["mainEntityOfPage"]==BASE+url and a["image_alt"].strip()
    assert 'content="noindex"' in (OUT/"404.html").read_text(encoding="utf-8")
    print("PASS: internal links, canonical, sitemap, article HTML, and all 5 legacy page bodies")
if __name__=="__main__": main()
