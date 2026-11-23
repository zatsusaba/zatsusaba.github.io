"""Check generated links, SEO, legacy content preservation, and article rendering."""
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
from build_blog import ROOT, OUT, BASE, CATS, NEWS_NAME, load, build, article_cover
from media import PAGE_SIZE
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


class RegionLinks(HTMLParser):
    """Read anchor destinations inside one named ID or class, including nested markup."""
    void = set("area base br col embed hr img input link meta param source track wbr".split())

    def __init__(self, html, selector):
        super().__init__()
        self.selector = selector
        self.depth = 0
        self.links = []
        self.labels = []
        self.link_text = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        matches = (attrs.get("id") == self.selector[1:] if self.selector.startswith("#")
                   else self.selector[1:] in attrs.get("class", "").split())
        if tag not in self.void and (self.depth or matches):
            self.depth += 1
        if self.depth and tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            self.link_text = []

    def handle_data(self, data):
        if self.link_text is not None:
            self.link_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.link_text is not None:
            self.labels.append("".join(self.link_text).strip())
            self.link_text = None
        if tag not in self.void and self.depth:
            self.depth -= 1


def check_homes(home, classic, streams):
    news_page = Document(home)
    classic_page = Document(classic)
    assert news_page.h1 == classic_page.h1 == 1
    assert news_page.canon == [BASE + "/"]
    assert classic_page.canon == [BASE + "/zatsusaba/"]
    assert not (OUT / "zatsusaba.html").exists()
    assert "<title>トレンド前線｜いま海外で話題のニュース</title>" in home
    assert '<meta property="og:site_name" content="トレンド前線">' in home
    assert home.count('<meta name="robots" content="max-image-preview:large">') == 1
    schemas = [json.loads(s) for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', home, re.S)]
    websites = [s for s in schemas if s.get("@type") == "WebSite"]
    assert len(websites) == 1
    assert websites[0]["name"] == "トレンド前線" and websites[0]["url"] == BASE + "/"

    article_urls = {a["url"] for group in streams.values() for a in group}
    news_links = RegionLinks(home, "#news").links
    assert "/news/" in news_links
    assert "/tools/appliance-total/" not in news_page.links
    assert {"/news/", "/news/#categories", "/news/#blog-search"} <= set(RegionLinks(home, ".news-masthead").links)
    eligible = [a for a in streams["news"] if not a.get("archive_only")]
    front_articles = sorted(eligible, key=lambda a: (a["date"], bool(a.get("featured"))), reverse=True)[:4]
    assert [url for url in news_links if url in article_urls] == [a["url"] for a in front_articles]
    assert not set(news_page.links).intersection(a["url"] for a in streams["blog"])
    assert '<h1 id="news-title">世界の<em>今</em>がわかる！</h1>' in home
    cover_path = "/assets/news/frontline-kyu-at-desk.webp"
    assert any(src == cover_path and alt for src, alt in news_page.images)
    assert f'<meta property="og:image" content="{BASE}{cover_path}">' in home
    assert '<p class="news-desk-description">話題の海外ニュースをお届けします</p>' in home
    assert not RegionLinks(home, ".news-desk").links
    trends = RegionLinks(home, "#trends")
    assert trends.labels == ["エンタメ", "スポーツ", "ゲーム", "グルメ", "テクノロジー"]
    assert trends.links == [f"https://trends.google.com/trending?geo=JP&hl=ja&category={code}"
                            for code in (4, 17, 6, 5, 18)]
    channel = RegionLinks(home, ".channel-strip")
    assert channel.links == ["/zatsusaba/"] and news_page.links.count("/zatsusaba/") == 1
    assert "雑学サバイバル" in channel.labels[0] and "YouTube" in channel.labels[0]
    assert 'id="zatsusaba"' in home, "Existing /#zatsusaba links should reach the channel entrance"

    assert RegionLinks(classic, ".home-copy").links.count("/") == 1
    assert "オープニング動画" not in classic
    assert not set(classic_page.links).intersection(a["url"] for a in streams["news"])
    featured_blog = [url for url in RegionLinks(classic, ".media-home").links if url in article_urls]
    assert featured_blog == [a["url"] for a in streams["blog"][:4]]
    nav = RegionLinks(classic, ".classic-nav")
    destinations = {label: urljoin(BASE + "/zatsusaba/", href) for label, href in zip(nav.labels, nav.links)}
    for label, path in (("HOME", "/zatsusaba/"), ("STORY", "/story.html"), ("CHARACTERS", "/characters.html"),
                        ("雑学Blog", "/blog/"), ("今日の動画", "/zatsusaba/#today"), ("VIDEOS", "/videos.html")):
        assert destinations.get(label) == BASE + path, f"Classic navigation: {label} → {path}"
    for marker in ('id="hero-title"', 'id="home-teaser"', 'id="today"', 'id="about"', 'fantasia-section'):
        assert marker in classic and marker not in home, f"Classic section belongs on /zatsusaba/: {marker}"


def check_archives(streams):
    for section, group in streams.items():
        search_path = "search/index.json" if section == "blog" else "news/search.json"
        rows = json.loads((OUT / search_path).read_text(encoding="utf-8"))
        assert [row[0] for row in rows] == [a["url"] for a in group], f"Wrong {section} search index"
        archives = [(f"/{section}/", group)]
        for category, slug in CATS.items():
            items = [a for a in group if a["category"] == category]
            if items or section == "blog":
                archives.append((f"/{section}/category/{slug}/", items))
        for base, items in archives:
            for start in range(0, max(1, len(items)), PAGE_SIZE):
                page_url = base if start == 0 else f"{base}page/{start // PAGE_SIZE + 1}/"
                html = (OUT / page_url.strip("/") / "index.html").read_text(encoding="utf-8")
                cards = RegionLinks(html, ".blog-card").links
                assert cards == [a["url"] for a in items[start:start + PAGE_SIZE]], page_url
                categories = RegionLinks(html, ".blog-categories").links
                assert categories and all(url.startswith(f"/{section}/") for url in categories), page_url

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
    articles = load()
    streams = {section: [a for a in articles if a["section"] == section] for section in ("news", "blog")}
    classic = (OUT / "zatsusaba/index.html").read_text(encoding="utf-8")
    check_homes(home, classic, streams)
    check_archives(streams)
    news_archive = (OUT / "news/index.html").read_text(encoding="utf-8")
    assert 'id="categories"' in news_archive and 'id="blog-search"' in news_archive
    # Removing only generated content must recover each original page body exactly.
    for name in ("story.html","characters.html","videos.html","video.html"):
        original=(ROOT/name).read_text(encoding="utf-8").split("<body",1)[1]
        built=(OUT/name).read_text(encoding="utf-8").split("<body",1)[1]
        assert FOOTER in built
        built=built.replace(FOOTER,'')
        built=built.replace('<a href="/comics/">Comic</a><a href="/blog/">雑学Blog</a><a href="/zatsusaba/#today">今日の動画</a>',"")
        built=built.replace('<a href="/blog/">雑学Blog</a><a href="/zatsusaba/#today">今日の動画</a>', "")
        assert original==built, f"Unexpected template change: {name}"
    for a in articles:
        text=(OUT/a["url"].lstrip("/")/"index.html").read_text(encoding="utf-8")
        assert a["html"] in text and Document(text).h1==1
        related = RegionLinks(text, ".blog-card").links
        assert all(url.startswith(f'/{a["section"]}/') and url != a["url"] for url in related), a["url"]
        breadcrumb = RegionLinks(text, ".blog-breadcrumb").links
        assert f'/{a["section"]}/category/{CATS[a["category"]]}/' in breadcrumb, a["url"]
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
    assert "/zatsusaba/" in visited and BASE + "/zatsusaba/" in dates
    utility_url = "/tools/appliance-total/"
    assert BASE + utility_url in dates
    utility_html = (OUT / "tools/appliance-total/index.html").read_text(encoding="utf-8")
    assert Document(utility_html).canon == [BASE + utility_url] and 'id="estimate"' in utility_html
    guide = "/news/washing-machine-delivery-fit/"
    if guide in {a["url"] for a in articles}:
        assert guide in visited and utility_url in visited
        assert utility_url in Document((OUT / "news/washing-machine-delivery-fit/index.html").read_text(encoding="utf-8")).links
    assert policy in visited and BASE+policy in dates
    assert Document((OUT/"editorial-policy/index.html").read_text(encoding="utf-8")).canon==[BASE+policy]
    for a in articles:
        url=a["url"]
        html=(OUT/url.strip("/")/"index.html").read_text(encoding="utf-8")
        assert url in visited and dates[BASE+url]==a["updated"]
        assert Document(html).canon==[BASE+url] and "noindex" not in html.split("</head>")[0]
        schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',html).group(1))
        news = a["section"] == "news"
        brand = NEWS_NAME if news else "雑学サバイバル"
        if news:
            assert not a.get("category_cover"), f"{url}: specify a topic-specific news illustration"
            story_images = Document(article_cover(a) + a["html"]).images
            assert any(src and alt and alt.strip() for src, alt in story_images), f"{url}: missing illustration in the article"
            author = "雑学サバイバル" if a.get("archive_only") else brand
            assert schema["author"]["name"] == author and schema["publisher"]["name"] == "雑学サバイバル"
            assert f'<p class="blog-date">{author}' in html
            assert html.count('<meta name="robots" content="max-image-preview:large">') == 1
            assert f'<meta property="og:site_name" content="{brand}">' in html
        assert f'<title>{escape(a["title"])} | {brand}</title>' in html
        assert f'<meta name="description" content="{escape(a["description"])}">' in html
        if not (a["section"] == "news" and a.get("category_cover")):
            assert (a["image"], a["image_alt"]) in rendered_images
        cover=article_cover(a)
        assert cover in html if cover else 'class="blog-cover"' not in html
        share_image=a["image"] if a["image"].startswith("https://") else BASE+a["image"]
        assert f'<meta property="og:image" content="{escape(share_image)}">' in html
        assert schema["image"]==share_image
        assert schema["@type"]=={"blog":"BlogPosting","news":"NewsArticle"}[a["section"]] and schema["headline"]==a["title"]
        assert schema["datePublished"]==a.get("published_at",a["date"]) and schema["dateModified"]==a["updated"]
        assert schema["mainEntityOfPage"]==BASE+url and a["image_alt"].strip()
    assert 'content="noindex"' in (OUT/"404.html").read_text(encoding="utf-8")
    print("PASS: internal links, canonical, sitemap, article HTML, separate news/blog archives, classic homepage, and 4 legacy page bodies")
if __name__=="__main__": main()
