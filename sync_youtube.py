#!/usr/bin/env python3
"""YouTube Data API v3: public channel uploads and named playlists -> local JS."""
import json, os, pathlib, re, sys, urllib.parse, urllib.request

KEY = os.environ.get("YOUTUBE_API_KEY")
CHANNEL = "UCr1ZBUGj3GHgBrgaHI-o5Yg"
ROOT = pathlib.Path(__file__).resolve().parent
GENRES = {
    "食事の秘密", "自然の秘密", "科学の秘密", "人間の秘密",
    "お金の秘密", "世界の秘密", "ゲームの秘密", "話題の秘密",
    "ショート漫画【1話完結】"
}

def call(endpoint, **params):
    params["key"] = KEY
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

def main():
    if not KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not set")

    channels = call("channels", part="contentDetails", id=CHANNEL).get("items", [])
    if not channels:
        raise RuntimeError("channel not found; preserving old data")

    uploads = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = []
    for item in pages("playlistItems", part="contentDetails", playlistId=uploads, maxResults=50):
        vid = item.get("contentDetails", {}).get("videoId")
        if vid and vid not in ids:
            ids.append(vid)

    if not ids:
        raise RuntimeError("empty upload list; preserving old data")

    genres = {}
    for playlist in pages("playlists", part="snippet", channelId=CHANNEL, maxResults=50):
        label = playlist["snippet"]["title"]
        if label not in GENRES:
            continue
        for item in pages("playlistItems", part="contentDetails", playlistId=playlist["id"], maxResults=50):
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                genres.setdefault(vid, []).append(label)

    videos = []
    for start in range(0, len(ids), 50):
        result = call(
            "videos", part="snippet,status,contentDetails",
            id=",".join(ids[start:start + 50]), maxResults=50
        )
        for v in result.get("items", []):
            if v.get("status", {}).get("privacyStatus") != "public":
                continue
            sn = v["snippet"]
            duration = v.get("contentDetails", {}).get("duration", "")
            match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
            seconds = sum(
                int(value or 0) * unit
                for value, unit in zip(match.groups(), (3600, 60, 1))
            ) if match else 0
            videos.append(dict(
                id=v["id"],
                title=sn["title"],
                date=sn.get("publishedAt", "")[:10],
                format="長尺動画" if seconds > 180 else "未確認",
                genres=genres.get(v["id"], []),
                characters=[],
                description=sn.get("description", "")[:500]
            ))

    if not videos:
        raise RuntimeError("no public videos returned; preserving old data")

    dest = ROOT / "youtube-videos.js"
    tmp = ROOT / "youtube-videos.tmp"
    tmp.write_text(
        "window.YOUTUBE_VIDEOS = " + json.dumps(videos, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8"
    )
    os.replace(tmp, dest)
    print(f"Saved {len(videos)} public videos.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Update failed; existing data kept:", type(e).__name__, file=sys.stderr)
        sys.exit(1)
