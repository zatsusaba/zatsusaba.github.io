"""Check generated links, SEO, legacy content preservation, and article rendering."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
from build_blog import ROOT, OUT, load, build

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
        assert len(doc.canon)==1, f"canonical: {p}"
        for u in doc.links:
            bits=urlsplit(u)
            if bits.scheme or bits.netloc or not bits.path: continue
            target=OUT/unquote(bits.path).lstrip("/") if bits.path.startswith("/") else p.parent/unquote(bits.path)
            if target.is_dir(): target=target/"index.html"
            assert target.is_file(), f"Broken link: {p}: {u}"
    home=(OUT/"index.html").read_text(encoding="utf-8")
    assert home.index('id="blog-title"') < home.index('id="home-videos"')
    # Removing only our insertions must recover the original page body exactly.
    import re
    for name in ("index.html","story.html","characters.html","videos.html","video.html"):
        original=(ROOT/name).read_text(encoding="utf-8").split("<body",1)[1]
        built=(OUT/name).read_text(encoding="utf-8").split("<body",1)[1]
        built=built.replace('<a href="/blog/">雑学Blog</a><a href="/comics/">4コマ</a>',"")
        if name=="index.html":
            original=re.sub(r'<section class="home-comic-strip".*?</section>',"",original,flags=re.S)
        built=re.sub(r'<!--media:start-->.*?<!--media:end-->',"",built,flags=re.S)
        assert original==built, f"Legacy content changed: {name}"
    for a in load():
        text=(OUT/a["url"].lstrip("/")/"index.html").read_text(encoding="utf-8")
        assert a["html"] in text and Document(text).h1==1
        assert 'application/ld+json' in text and 'og:image' in text
    ET.parse(OUT/"sitemap.xml")
    print("PASS: internal links, canonical, sitemap, article HTML, and all 5 legacy page bodies")
if __name__=="__main__": main()
