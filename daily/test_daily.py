# -*- coding: utf-8 -*-
from datetime import date
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "daily"))
os.environ["DAILY_TODAY"] = "2026-11-19"
import build  # noqa: E402

class DailyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visible = build.build(date(2026, 11, 19))
        cls.index = (build.OUT / "index.html").read_text(encoding="utf-8")
        cls.d1 = (build.OUT / "psychological-defense.html").read_text(encoding="utf-8")
        cls.d2 = (build.OUT / "emotional-avoidance.html").read_text(encoding="utf-8")

    def test_two_public_cards(self):
        slugs = [c["slug"] for c in self.visible]
        self.assertEqual(slugs, ["emotional-avoidance", "psychological-defense"])

    def test_draft_not_public(self):
        self.assertFalse((build.OUT / "draft-must-not-publish.html").exists())
        self.assertNotIn("draft-must-not-publish", self.index)
        sm = (build.OUT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("draft-must-not-publish", sm)

    def test_future_not_public_at_build(self):
        self.assertFalse((build.OUT / "future-must-not-publish.html").exists())
        self.assertNotIn("future-must-not-publish", self.index)
        later = build.public_cards(build.load_cards(), date(2029, 1, 2))
        self.assertTrue(any(c["slug"] == "future-must-not-publish" for c in later))

    def test_no_save_image_without_file(self):
        self.assertNotIn("保存图片", self.index + self.d1)
        self.assertNotIn('id="dailySave"', self.index + self.d1)
        self.assertIn("网页文字卡片", self.d1)

    def test_no_dead_insights_link(self):
        self.assertNotIn("延伸阅读", self.d1)
        self.assertNotIn("yangao-lanmu-shuoming", self.d1)

    def test_share_and_seo(self):
        self.assertIn("dailyShare", self.d2)
        self.assertIn("rel=\"canonical\"", self.d2)
        self.assertIn("og:title", self.d2)

    def test_no_subscribe_or_booking_confirmed(self):
        blob = self.index + self.d1 + self.d2
        self.assertNotIn("订阅成功", blob)
        self.assertNotIn("预约已确认", blob)

    def test_crisis(self):
        self.assertIn("000", self.d1)
        self.assertIn("13 11 14", self.d1)

if __name__ == "__main__":
    unittest.main()
