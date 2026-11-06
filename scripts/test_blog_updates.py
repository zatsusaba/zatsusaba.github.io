"""Exercise article additions and updates with isolated fixtures."""
import tempfile
from pathlib import Path
import build_blog as b
original_root, original_out = b.ROOT, b.OUT
job=original_root/"cleanup-temp"/"blog-verification"
job.mkdir(parents=True,exist_ok=True)
root=Path(tempfile.mkdtemp(prefix="fixture-",dir=job))
for name in ("articles","assets","panels-v2"): (root/name).mkdir()
(root/"index.html").write_text((original_root/"index.html").read_text(encoding="utf-8"),encoding="utf-8")
sample=(original_root/"articles/pineapple.md").read_text(encoding="utf-8")
b.ROOT=root
b.OUT=root/"_site"
(root/"articles/pineapple.md").write_text(sample,encoding="utf-8")
second=root/"articles/second.md"
second.write_text(sample.replace("title: パイナップル","title: 追加検証パイナップル",1),encoding="utf-8")
b.build()
assert '/blog/second/' in (b.OUT/"blog/pineapple/index.html").read_text(encoding="utf-8")
assert '/blog/second/' in (b.OUT/"blog/category/food/index.html").read_text(encoding="utf-8")
second.write_text(second.read_text(encoding="utf-8").replace("## パイナップルの正体","## 更新確認の正体"),encoding="utf-8")
b.build()
assert "更新確認の正体" in (b.OUT/"blog/second/index.html").read_text(encoding="utf-8")
second.write_text(second.read_text(encoding="utf-8").replace("---\n","---\ndraft: true\n",1),encoding="utf-8")
b.build()
assert not (b.OUT/"blog/second/index.html").exists()
assert '/blog/second/' not in (b.OUT/"blog/index.html").read_text(encoding="utf-8")
second.write_text(sample.replace("category: 食べ物","category: 不明"),encoding="utf-8")
try:
    b.load()
except ValueError:
    pass
else:
    raise AssertionError("Unknown category accepted")
print("PASS: additions, related/category links, revisions, draft exclusion, stale-page removal, metadata rejection")
b.ROOT,b.OUT=original_root,original_out
