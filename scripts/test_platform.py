"""Exercise the Dots handoff and approval gates using isolated input and output."""
import json
from pathlib import Path
import shutil
import tempfile
import yaml

import build_blog as b
import daily
import editorial

source=b.ROOT
jobs=source/"cleanup-temp"/"platform-verification"
jobs.mkdir(parents=True,exist_ok=True)
root=Path(tempfile.mkdtemp(dir=jobs))
b.ROOT,b.OUT=root,root/"_site"
for folder in ("articles","comics","panels-v2","assets/covers","comic-media/episode"):
    (root/folder).mkdir(parents=True)
shutil.copy(source/"index.html",root)
shutil.copy(source/"assets/covers/science.svg",root/"assets/covers")
src={"title":"独立記事の検証","status":"published","date":"2020-01-01","updated":"2020-01-02",
     "category":"科学","description":"隔離環境のテスト","topic":"確認対象",
     "sources":[{"title":"検証用","url":"https://example.org/","checked":"2020-01-01"}],
     "conditions":"検証環境のみ"}
def article(data):
    (root/"articles/subject.md").write_text("---\n"+yaml.safe_dump(data,allow_unicode=True)+"---\n本文",encoding="utf-8")
article(src)
vid="q5FluB5f-b8"
video={"id":vid,"title":"テスト動画","publishedAt":"2020-12-31T15:00:00Z","date":"2021-01-01","format":"未確認"}
(root/"youtube-videos.js").write_text("window.YOUTUBE_VIDEOS = "+json.dumps([video])+";",encoding="utf-8")
comic={"id":"episode","title":"隔離漫画","date":"2020-01-01","status":"pending",
       "articles":["subject"],"videos":[vid],"characters":["太郎"],"themes":["制作"],"panels":[]}
for i in range(1,5):
    path=f"comic-media/episode/panel{i}.png"
    shutil.copy(source/f"panels-v2/panel{i}.png",root/path)
    comic["panels"].append({"src":"/"+path,"alt":f"{i}コマ目","text":f"検証用セリフ{i}"})
def save_comic():
    (root/"comics/episode.yml").write_text(yaml.safe_dump(comic,allow_unicode=True),encoding="utf-8")
def read(name): return (b.OUT/name).read_text(encoding="utf-8")
def fails(fn,expected):
    try: fn()
    except ValueError as exc: assert expected in str(exc),str(exc)
    else: raise AssertionError("Expected rejection: "+expected)

save_comic()
b.build()
assert not (b.OUT/"comics/episode/index.html").exists() and not (b.OUT/"comic-media/episode/panel1.png").exists()
assert "/comics/episode/" not in read("index.html")+read("sitemap.xml")
assert "blog-video" not in read("blog/subject/index.html") and "science.svg" in read("blog/subject/index.html")
assert "詳しく読む" not in read("today/2021-01-01/index.html")
comic["status"]="approved"
save_comic()
fails(b.build,"approval")
comic["approval"]="synthetic test approval"
save_comic()
src["youtube"]=vid
article(src)
b.build()
assert "/comics/episode/" in read("index.html")+read("comics/index.html")
assert "テスト動画" not in read("index.html") and "テスト動画" not in read("today/index.html")
assert "テスト動画" in read("today/2021-01-01/index.html")
for location in ("comics/episode/index.html",):
    html=read(location)
    assert 'class="comic-sheet"' in html and "セリフ・表示文字" not in html
    assert all(f'href="/comic-media/episode/panel{i}.png"' in html for i in range(1,5))
assert (b.OUT/"comic-media/episode/panel4.png").is_file()
assert "詳しく読む" in read("today/2021-01-01/index.html")
assert "/today/2020-12-31/" not in read("sitemap.xml")
assert "/blog/subject/" in read("sitemap.xml") and "/today/2021-01-01/" in read("sitemap.xml")
comic["status"]="pending";save_comic()
src["status"]="draft";article(src)
b.build()
for name in ("comics/episode/index.html","comic-media/episode/panel1.png","blog/subject/index.html"):
    assert not (b.OUT/name).exists()
assert json.loads(read("search/index.json"))==[] and "詳しく読む" not in read("today/2021-01-01/index.html")
src["status"]="published";article(src)
items=b.load()
duplicates, stale=editorial.audit(items+[dict(items[0],slug="another")],b.date(2022,1,1))
assert duplicates and len(stale)==2
del src["sources"][0]["checked"];article(src)
fails(b.load,"sources[].checked")
fails(lambda:daily.calendar([video,video],root),"duplicate ID")
fails(lambda:editorial.metadata("status: pending\nstatus: approved","duplicate.yml"),"duplicate YAML key")
(root/"comics/episode.yaml").write_bytes((root/"comics/episode.yml").read_bytes())
fails(lambda:b.media.load_comics(root,b.date(2022,1,1)),"duplicate comic ID")
(root/"comics/episode.yaml").unlink()  # isolated duplicate-ID fixture
src["sources"][0]["checked"]="2020-01-01"
src["youtube"]="missing0000";article(src)
fails(b.build,"unknown public video ID")
src.pop("youtube");article(src)
comic["status"]="approved";comic["articles"]=["missing"];save_comic()
fails(b.build,"unknown article")
comic["articles"]=["subject"];save_comic()
(root/"comic-media/episode/panel2.png").unlink()
fails(b.build,"invalid panel")
print("PASS: independent article, fallback cover, private pending panels, approved comic, date archive, explicit deep link, revocation, stale/duplicate reports")
