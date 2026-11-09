"""Offline contract tests for public-only, atomic YouTube sync."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sync_youtube as sync


class YouTubeSyncTest(unittest.TestCase):
    def test_duration_classification(self):
        item={"id":"a1234567890","status":{"privacyStatus":"public"},
              "snippet":{"title":"test","channelId":sync.CHANNEL,"publishedAt":"2026-01-01T00:00:00Z"}}
        for duration, expected in [("PT3M1S","長尺動画"),("PT20M","長尺動画"),("PT3M","未確認"),("PT59S","未確認")]:
            item["contentDetails"]={"duration":duration}
            result=sync.public_video(item,[],{})
            self.assertEqual(result["format"],expected)
        self.assertEqual(sync.public_video(item,["科学の雑学【Shorts】"],{})["format"],"Shorts")
        self.assertEqual(sync.duration_seconds("P1DT1H1M1S"),90061)
        self.assertIsNone(sync.duration_seconds("invalid"))

    def test_display_title(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from daily import display_title
        self.assertEqual(display_title("指の不思議 #雑学 #指"), "指の不思議")
        self.assertEqual(display_title("船の観覧車＃雑学"), "船の観覧車")
        self.assertEqual(display_title("C# の話"), "C# の話")
        self.assertEqual(display_title("普通のタイトル"), "普通のタイトル")

    def test_japan_calendar_day(self):
        self.assertEqual(sync.publication_time("2026-12-31T14:59:59Z")[1], "2026-12-31")
        self.assertEqual(sync.publication_time("2026-12-31T15:00:00Z")[1], "2027-01-01")
        self.assertEqual(sync.publication_time("2026-12-31T23:59:59Z")[1], "2027-01-01")
        self.assertEqual(sync.publication_time("2027-01-01T00:00:01+09:00")[0],
                         "2026-12-31T15:00:01Z")
        with self.assertRaises(ValueError):
            sync.publication_time("2027-01-01")

    def test_sync_snapshot_and_failure(self):
        def item(vid, privacy):
            return {"id": vid, "snippet": {"channelId": sync.CHANNEL, "title": vid,
                    "publishedAt": "2026-12-31T15:00:00Z"},
                    "status": {"privacyStatus": privacy},
                    "contentDetails": {"duration": "PT2M"}}
        public = item("a1234567890", "public")
        short = item("b1234567890", "public")
        known = item("c1234567890", "public")
        hidden = item("d1234567890", "unlisted")
        private = item("e1234567890", "private")
        returned = [public, public, short, known, hidden, private]
        def response(endpoint, **params):
            if endpoint == "channels":
                return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "uploads"}}}]}
            if endpoint == "playlistItems":
                self.assertNotEqual(params["playlistId"], "private")
                rows = [short] if params["playlistId"] == "shorts" else returned
                return {"items": [{"contentDetails": {"videoId": v["id"]}} for v in rows]}
            if endpoint == "playlists":
                return {"items": [{"id": "shorts", "status": {"privacyStatus":"public"}, "snippet": {"title": "ショート漫画【1話完結】"}}, {"id":"new", "status":{"privacyStatus":"public"}, "snippet":{"title":"新しい公開ジャンル"}}, {"id":"private", "status":{"privacyStatus":"private"}, "snippet":{"title":"非公開"}}]}
            if endpoint == "videos":
                self.assertIn("contentDetails", params["part"].split(","))
                ids = params["id"].split(",")
                self.assertEqual(len(ids), len(set(ids)))
                return {"items": returned}
            raise AssertionError(endpoint)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config/youtube-formats.json").write_text(json.dumps({
                known["id"]: {"format": "長尺動画", "evidence": "test catalog"}
            }), encoding="utf-8")
            with patch.object(sync, "ROOT", root), patch.object(sync, "call", response), \
                    patch.dict(sync.os.environ, {"YOUTUBE_API_KEY": "offline-fixture"}):
                sync.main()
                output = root / "youtube-videos.js"
                snapshot = output.read_bytes()
                records = json.loads(snapshot.decode().split("=", 1)[1].strip().rstrip(";"))
                self.assertEqual([r["id"] for r in records], [v["id"] for v in [public, short, known]])
                self.assertEqual([r["format"] for r in records], ["未確認","ショート漫画","長尺動画"])
                self.assertEqual(records[0]["genres"], ["新しい公開ジャンル"])
                self.assertNotIn("formatEvidence", records[0])
                self.assertTrue(records[1]["formatEvidence"])
                self.assertEqual(records[0]["date"], "2027-01-01")
                self.assertEqual(records[0]["publishedAt"], "2026-12-31T15:00:00Z")
                public["snippet"]["publishedAt"] = "invalid"
                with self.assertRaisesRegex(ValueError, public["id"]):
                    sync.main()
                self.assertEqual(output.read_bytes(), snapshot)


if __name__ == "__main__":
    unittest.main()
