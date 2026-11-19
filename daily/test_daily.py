# -*- coding: utf-8 -*-
from datetime import date, datetime
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

    def test_no_public_json_feed(self):
        self.assertFalse((build.OUT / "cards.json").exists())
        self.assertFalse((build.OUT / "index.json").exists())

    def test_nov19_boundary_vs_utc(self):
        # AEDT (UTC+11): 18 Nov 12:59 UTC is still 18 Nov in Sydney;
        # 18 Nov 13:00 UTC is 19 Nov 00:00 in Sydney.
        self.assertEqual(build.sydney_date_from_utc(datetime(2026, 11, 18, 12, 59)), date(2026, 11, 18))
        self.assertEqual(build.sydney_date_from_utc(datetime(2026, 11, 18, 13, 0)), date(2026, 11, 19))

    def test_winter_aest_boundary(self):
        # AEST (UTC+10): 15 Jun 13:59 UTC is 15 Jun 23:59 Sydney;
        # 15 Jun 14:00 UTC is 16 Jun 00:00 Sydney.
        self.assertEqual(build.sydney_date_from_utc(datetime(2026, 6, 15, 13, 59)), date(2026, 6, 15))
        self.assertEqual(build.sydney_date_from_utc(datetime(2026, 6, 15, 14, 0)), date(2026, 6, 16))

    def test_card_visibility_follows_sydney_date(self):
        cards = build.load_cards()
        on_18 = [c["slug"] for c in build.public_cards(cards, date(2026, 11, 18))]
        on_19 = [c["slug"] for c in build.public_cards(cards, date(2026, 11, 19))]
        self.assertEqual(on_18, ["psychological-defense"])
        self.assertIn("emotional-avoidance", on_19)
        self.assertNotIn("future-must-not-publish", on_19)

if __name__ == "__main__":
    unittest.main()
