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
# Related videos preserve the primary embed and link every daily-card surface.
from datetime import datetime
related_ids=["related0001","related0002"]
today=datetime.now(daily.JST).date().isoformat()
extra_videos=[dict(video,id=related_ids[0],title='正式 <追加> & 動画',
                   publishedAt=today+"T00:00:00+09:00",date=today),
              {"id":related_ids[1],"title":"日付未確認の追加動画"}]
(root/"youtube-videos.js").write_text("window.YOUTUBE_VIDEOS = "+json.dumps([video]+extra_videos)+";",encoding="utf-8")
primary_html=read("blog/subject/index.html")
src["youtube_related"]=related_ids
article(src)
b.build()
html=read("blog/subject/index.html")
assert html.count('<iframe')==1
primary_section=primary_html.split('<section><h2>動画はこちら</h2>',1)[1].split('</section>',1)[0]
assert '<section><h2>動画はこちら</h2>'+primary_section+'</section>' in html
assert '正式 &lt;追加&gt; &amp; 動画</a>' in html
for target in ("today/"+today+"/index.html","today/undated/index.html","today/index.html","index.html"):
    assert '詳しく読む：独立記事の検証' in read(target),target
for vid_id in [vid]+related_ids:
    assert html.count('href="https://www.youtube.com/watch?v='+vid_id+'"')==1
    assert json.loads(read("video-links.json"))[vid_id].count(["/blog/subject/",src["title"]])==1
# Disabling comics must leave all article links, but no comic links or pages.
(root/"config").mkdir(exist_ok=True)
(root/"config/comics-enabled.json").write_text("false")
b.build()
assert not (b.OUT/"comics/episode/index.html").exists()
assert '/comics/' not in read("video-links.json")
for vid_id in [vid]+related_ids:
    assert json.loads(read("video-links.json"))[vid_id]==[["/blog/subject/",src["title"]]]
for invalid, error in (("related0001","must be a list"),(None,"must be a list"),
                       ([123],"invalid video ID"),([None],"invalid video ID"),
                       (["あ"*11],"invalid video ID"),(["bad"],"invalid video ID"),
                       ([vid],"duplicate video ID"),(related_ids*2,"duplicate video ID")):
    article(dict(src,youtube_related=invalid))
    fails(b.load,error)
for invalid_primary in (True,123,[vid],"あ"*11):
    article(dict(src,youtube=invalid_primary,youtube_related=[]))
    fails(b.load,"invalid video ID")
article(dict(src,youtube_related=["missing0000"]))
fails(b.build,"unknown public video ID")
without_primary=dict(src);without_primary.pop("youtube")
article(without_primary)
fails(b.load,"youtube_related requires youtube")
article(dict(without_primary,youtube_related=[]))
assert not b.media.article_video_ids(b.load()[0])
article(src)
print("PASS: related ID validation, single unchanged embed, escaped official titles, all daily surfaces, comic pause")
comic["status"]="pending";save_comic()
src["status"]="draft";article(src)
b.build()
for name in ("comics/episode/index.html","comic-media/episode/panel1.png","blog/subject/index.html"):
    assert not (b.OUT/name).exists()
assert json.loads(read("search/index.json"))==[] and "詳しく読む" not in read("today/2021-01-01/index.html")
assert json.loads(read("video-links.json"))=={}
for target in ("today/"+today+"/index.html","today/undated/index.html","today/index.html","index.html"):
    assert "詳しく読む" not in read(target)
# Publishing again, then deleting, must remove all related reverse links too.
src["status"]="published";article(src);b.build()
(root/"articles/subject.md").unlink()
b.build()
assert json.loads(read("video-links.json"))=={}
assert not (b.OUT/"blog/subject/index.html").exists()
(root/"config/comics-enabled.json").write_text("true")
src.pop("youtube_related")
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
