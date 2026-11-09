"""Build an isolated 3,001-article archive and exercise media relationships."""
import json
import shutil
import tempfile
import time
from pathlib import Path

import yaml

import build_blog as blog

source = blog.ROOT
jobs = source / "cleanup-temp" / "media-verification"
jobs.mkdir(parents=True, exist_ok=True)
root = Path(tempfile.mkdtemp(dir=jobs))
blog.ROOT, blog.OUT = root, root / "_site"
for name in ("articles", "comics", "assets", "panels-v2"):
    (root / name).mkdir()
for name in ("index.html", "youtube-videos.js", "blog-search.js", "blog.css", "media.css", "style.css"):
    shutil.copyfile(source / name, root / name)
for panel in range(1, 5):
    (root / "panels-v2" / f"panel{panel}.png").touch()
comic = yaml.safe_load((source/"comics/ai-official-site.yml").read_text(encoding="utf-8"))
comic["articles"] = ["entry-0000"]
comic["videos"] = ["q5FluB5f-b8"]
for slug in ("first", "second"):
    (root/"comics"/(slug+".yml")).write_text(yaml.safe_dump(comic, allow_unicode=True),encoding="utf-8")
for i in range(3001):
    category = "自然" if i % 2 else "食べ物"
    data = {"status":"published","title":f"検索試験 {i:04}", "date":"2020-01-01", "updated":"2020-01-01",
            "description":"索引検証", "category":category, "tags":["植物"],
            "image":"https://i.ytimg.com/vi/q5FluB5f-b8/hqdefault.jpg","image_alt":"テスト",
            "sources":[{"checked":"2020-01-01","title":"資料","url":"https://example.org/"}]}
    if i==0:
        data["youtube"]="q5FluB5f-b8"
    content="---\n"+yaml.safe_dump(data,allow_unicode=True)+"---\n## 本文\n\n"+("観察記録。" * 120)+f"本文専用{i:04}"
    (root/"articles"/f"entry-{i:04}.md").write_text(content,encoding="utf-8")

started=time.perf_counter()
blog.build()
out=blog.OUT
def read(path): return (out/path).read_text(encoding="utf-8")
index=json.loads(read("search/index.json"))
assert len(index)==3001
assert len(list((out/"blog"/"page").glob("*/index.html")))==125
assert read("blog/page/126/index.html").count('class="blog-card"')==1
assert read("blog/category/food/page/63/index.html").count('class="blog-card"')==13
assert "本文専用" not in read("blog/index.html") and "本文専用" not in read("search/index.json")
assert len(read("blog/index.html").encode()) < 40000
assert 'href="/comics/first/"' in read("comics/second/index.html")
assert 'href="/comics/second/"' in read("comics/first/index.html")
assert 'href="/comics/second/"' in read("index.html")
assert 'href="/blog/entry-0000/"' in read("comics/first/index.html")
assert 'href="/comics/first/"' in read("blog/entry-0000/index.html")
assert 'https://www.youtube.com/watch?v=q5FluB5f-b8' in read("blog/entry-0000/index.html")
assert '<h2>漫画はこちら</h2>' in read("blog/entry-0000/index.html")
assert len(json.loads(read("video-links.json"))["q5FluB5f-b8"])==3
print(f"3001 articles built in {time.perf_counter()-started:.2f}s; archive HTML {len(read('blog/index.html').encode())} bytes; metadata index {len(read('search/index.json').encode())} bytes")
# Delete only the synthetic sources that this test created.
(root/"articles/entry-0000.md").unlink()
(root/"comics/second.yml").unlink()
comic["articles"]=[]
(root/"comics/first.yml").write_text(yaml.safe_dump(comic, allow_unicode=True),encoding="utf-8")
blog.build()
assert not (out/"blog/entry-0000/index.html").exists()
assert not (out/"comics/second/index.html").exists()
assert "/blog/entry-0000/" not in read("comics/first/index.html")+read("sitemap.xml")+read("search/index.json")
assert "/comics/second/" not in read("index.html")+read("video-links.json")
print("PASS: pagination, taxonomy, additions/deletions and explicit reciprocal links")
print("Isolated 3000-article preview:",out)
