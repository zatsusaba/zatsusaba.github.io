"""Check generated links, SEO, legacy content preservation, and article rendering."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
from build_blog import ROOT, OUT, BASE, load, build
from site_info import FOOTER
import json, re
from html import escape
from urllib.parse import urljoin

class Document(HTMLParser):
    def __init__(self,text):
        super().__init__(); self.links=[]; self.canon=[]; self.h1=0
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("a","link","script","img","iframe"):
            u=a.get("href",a.get("src",""))
            if u: self.links.append(u)
        if tag=="link" and a.get("rel")=="canonical": self.canon.append(a["href"])
        if tag=="h1": self.h1+=1

def main():
    build()
    for p in OUT.rglob("*.html"):
        text=p.read_text(encoding="utf-8"); doc=Document(text)
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
    home=(OUT/"index.html").read_text(encoding="utf-8")
    assert home.index('id="blog-title"') < home.index('class="blog-home daily-home"')
    if 'class="blog-home comic-home"' in home:
        assert home.index('class="blog-home daily-home"') < home.index('class="blog-home comic-home"')
    # Removing only our insertions must recover the original page body exactly.
    for name in ("index.html","story.html","characters.html","videos.html","video.html"):
        original=(ROOT/name).read_text(encoding="utf-8").split("<body",1)[1]
        built=(OUT/name).read_text(encoding="utf-8").split("<body",1)[1]
        assert FOOTER in built
        built=built.replace(FOOTER,'')
        built=built.replace('<a href="/blog/">雑学大百科</a><a href="/today/">今日の雑学</a><a href="/comics/">4コマ</a>',"")
        if name=="index.html":
            original=re.sub(r'<section class="section light home-section home-videos-section">.*?</section>',"",original,flags=re.S)
            original=re.sub(r'<section class="home-comic-strip".*?</section>',"",original,flags=re.S)
        built=re.sub(r'<!--media:start-->.*?<!--media:end-->',"",built,flags=re.S)
        assert original==built, f"Legacy content changed: {name}"
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
    for a in load():
        url=a["url"]
        html=(OUT/url.strip("/")/"index.html").read_text(encoding="utf-8")
        assert url in visited and dates[BASE+url]==a["updated"]
        assert Document(html).canon==[BASE+url] and "noindex" not in html.split("</head>")[0]
        schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',html).group(1))
        assert f'<title>{escape(a["title"])} | 雑学サバイバル</title>' in html
        assert f'<meta name="description" content="{escape(a["description"])}">' in html
        assert f'alt="{escape(a["image_alt"])}"' in html
        assert schema["@type"]=="BlogPosting" and schema["headline"]==a["title"]
        assert schema["datePublished"]==a["date"] and schema["dateModified"]==a["updated"]
        assert schema["mainEntityOfPage"]==BASE+url and a["image_alt"].strip()
    assert 'content="noindex"' in (OUT/"404.html").read_text(encoding="utf-8")
    print("PASS: internal links, canonical, sitemap, article HTML, and all 5 legacy page bodies")
if __name__=="__main__": main()
