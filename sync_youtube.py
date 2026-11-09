#!/usr/bin/env python3
"""YouTube Data API v3: public channel uploads and named playlists -> local JS."""
import json, os, pathlib, re, sys, urllib.parse, urllib.request

from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
CHANNEL = "UCr1ZBUGj3GHgBrgaHI-o5Yg"
ROOT = pathlib.Path(__file__).resolve().parent


def call(endpoint, **params):
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    url = "https://www.googleapis.com/youtube/v3/" + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)

def pages(endpoint, **params):
    while True:
        result = call(endpoint, **params)
        yield from result.get("items", [])
        if not result.get("nextPageToken"):
            return
        params["pageToken"] = result["nextPageToken"]

def publication_time(value):
    """Return an unambiguous UTC instant and its Japanese calendar date."""
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None:
        raise ValueError("publishedAt requires an explicit timezone")
    return (instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            instant.astimezone(JST).date().isoformat())


def duration_seconds(value):
    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", value or "")
    if not match:
        return None
    return sum(float(n or 0)*factor for n,factor in zip(match.groups(), [86400,3600,60,1]))


def public_video(item, genres, formats):
    if item.get("status", {}).get("privacyStatus") != "public":
        return None
    vid = item["id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        raise ValueError(f"Invalid YouTube video ID: {vid!r}")
    snippet = item["snippet"]
    if snippet.get("liveBroadcastContent")=="upcoming":
        return None
    if snippet.get("channelId") != CHANNEL:
        raise ValueError(f"Unexpected channel for {vid}")
    try:
        published, day = publication_time(snippet["publishedAt"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid publishedAt for {vid}") from error
    duration = duration_seconds(item.get("contentDetails", {}).get("duration"))
    classification = formats.get(vid)
    # Shorts are at most three minutes; short duration alone does not prove Shorts.
    if classification is None and duration is not None and duration > 180:
        classification = {"format": "長尺動画", "evidence": "YouTube公開再生時間：180秒超"}
    if classification is None and any(re.search(r"【Shorts】", g, re.I) for g in genres):
        classification = {"format": "Shorts", "evidence": "公式Shorts再生リスト"}
    if classification is None and "ショート漫画【1話完結】" in genres:
        classification = {"format": "ショート漫画", "evidence": "公式プレイリスト：ショート漫画【1話完結】"}
    record = dict(id=vid, title=snippet["title"], publishedAt=published, date=day,
                  format=classification["format"] if classification else "未確認",
                  genres=genres, characters=[], description=snippet.get("description", "")[:500])
    if duration is not None:
        record["durationSeconds"] = duration
    if classification:
        record["formatEvidence"] = classification["evidence"]
    return record


def main():
    if not os.environ.get("YOUTUBE_API_KEY"):
        raise RuntimeError("YOUTUBE_API_KEY is not set")

    channels = call("channels", part="contentDetails", id=CHANNEL).get("items", [])
    if not channels:
        raise RuntimeError("channel not found; preserving old data")

    uploads = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = {}
    for item in pages("playlistItems", part="contentDetails", playlistId=uploads, maxResults=50):
        vid = item.get("contentDetails", {}).get("videoId")
        if vid:
            ids[vid] = None

    if not ids:
        raise RuntimeError("empty upload list; preserving old data")

    genres = {}
    for playlist in pages("playlists", part="snippet,status", channelId=CHANNEL, maxResults=50):
        label = playlist["snippet"]["title"]
        if playlist.get("status", {}).get("privacyStatus") != "public":
            continue
        for item in pages("playlistItems", part="contentDetails", playlistId=playlist["id"], maxResults=50):
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                bucket = genres.setdefault(vid, [])
                if label not in bucket:
                    bucket.append(label)

    formats = json.loads((ROOT / 'config/youtube-formats.json').read_text(encoding='utf-8'))
    videos = {}
    ids = list(ids)
    for start in range(0, len(ids), 50):
        result = call(
            "videos", part="snippet,status",
            id=",".join(ids[start:start + 50]), maxResults=50
        )
        for v in result.get("items", []):
            record = public_video(v, genres.get(v["id"], []), formats)
            if record:
                videos[record["id"]] = record

    if not videos:
        raise RuntimeError("no public videos returned; preserving old data")

    dest = ROOT / "youtube-videos.js"
    tmp = ROOT / "youtube-videos.tmp"
    tmp.write_text(
        "window.YOUTUBE_VIDEOS = " + json.dumps(list(videos.values()), ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8"
    )
    os.replace(tmp, dest)
    print(f"Saved {len(videos)} public videos.")

if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"Update failed; existing data kept: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("Update failed; existing data kept:", type(e).__name__, file=sys.stderr)
        sys.exit(1)
