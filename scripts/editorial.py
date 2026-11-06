"""Editorial metadata validation and a non-public maintenance report."""
import re
import unicodedata
import yaml
from collections import defaultdict
from datetime import date, timedelta
from urllib.parse import urlsplit


class UniqueKeys(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen=set()
        for key_node, _ in node.value:
            key=self.construct_object(key_node,deep=deep)
            if not isinstance(key,str) or key in seen:
                raise ValueError(f"invalid or duplicate YAML key {key!r}")
            seen.add(key)
        return super().construct_mapping(node,deep=deep)


def metadata(raw,path):
    try:
        return yaml.load(raw,Loader=UniqueKeys)
    except (ValueError,yaml.YAMLError) as error:
        raise ValueError(f"{path}: {error}") from error


def state(data, allowed, default, path):
    value = data.get("status", default)
    if value not in allowed or ("draft" in data and type(data["draft"]) is not bool):
        raise ValueError(f"{path}: invalid status or draft")
    return "draft" if data.get("draft") else value


def sources(article, today, path):
    entries = article["sources"]
    if not isinstance(entries,list) or not entries:
        raise ValueError(f"{path}: sources must be a nonempty list")
    for source in entries:
        if not isinstance(source,dict) or not isinstance(source.get("title"),str) or not source["title"].strip():
            raise ValueError(f"{path}: missing source title")
        address=urlsplit(str(source.get("url","")))
        if address.scheme!="https" or not address.hostname or address.username or any(c.isspace() for c in address.geturl()):
            raise ValueError(f"{path}: invalid source URL")
        try:
            checked=date.fromisoformat(str(source["checked"]))
            if checked>today: raise ValueError()
        except (KeyError,ValueError) as error:
            raise ValueError(f"{path}: sources[].checked needs a valid non-future date") from error
        source["checked"]=checked.isoformat()
    if not isinstance(article.get("conditions",""),str):
        raise ValueError(f"{path}: conditions must be text")
    for key in ("title","description","category"):
        if not isinstance(article.get(key),str) or not article[key].strip():
            raise ValueError(f"{path}: invalid {key}")
    if not isinstance(article.get("tags",[]),list) or not all(isinstance(tag,str) for tag in article.get("tags",[])):
        raise ValueError(f"{path}: tags must be a list of text")
    if not isinstance(article.get("topic",article["title"]),str):
        raise ValueError(f"{path}: topic must be text")


def audit(articles, today, days=365):
    topics=defaultdict(list)
    stale=[]
    for a in articles:
        for text in {a["title"],a.get("topic",a["title"])}:
            key=re.sub(r"[\W_]+","",unicodedata.normalize("NFKC",text).casefold())
            if key and a["slug"] not in topics[key]: topics[key].append(a["slug"])
        oldest=min(s["checked"] for s in a["sources"])
        if date.fromisoformat(oldest)<=today-timedelta(days=days):
            stale.append((a["slug"],oldest))
    return {k:v for k,v in topics.items() if len(v)>1},stale


if __name__=="__main__":
    from build_blog import load, JST
    from datetime import datetime
    duplicates, stale=audit(load(),datetime.now(JST).date())
    for key,slugs in duplicates.items(): print("重複候補", key, ", ".join(slugs))
    for slug,checked in stale: print("要再確認",slug,checked)
    print(f"重複候補 {len(duplicates)} グループ / 要再確認 {len(stale)} 記事")

