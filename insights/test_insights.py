# -*- coding: utf-8 -*-
"""Insights Phase 1 checks. No network, no deploy."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "insights"))
import build  # noqa: E402

class InsightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.published = build.build()
        cls.index = (build.OUT / "index.html").read_text(encoding="utf-8")
        cls.sample = (build.OUT / "yangao-lanmu-shuoming.html").read_text(encoding="utf-8")

    def test_draft_has_no_public_html(self):
        self.assertFalse((build.OUT / "draft-must-not-publish.html").exists())
        self.assertNotIn("draft-must-not-publish", self.index)
        sitemap = (build.OUT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("draft-must-not-publish", sitemap)

    def test_sample_is_labelled(self):
        self.assertIn("样稿", self.sample)
        self.assertIn("不是研究周报", self.sample)
        self.assertNotIn("doi.org", self.sample.lower())
        self.assertNotIn("10.1111", self.sample)

    def test_required_seo(self):
        self.assertIn('rel="canonical"', self.sample)
        self.assertIn("og:title", self.sample)
        self.assertIn("BlogPosting", self.sample)

    def test_no_fake_subscribe(self):
        self.assertNotIn("订阅成功", self.index)
        self.assertNotIn('type="email"', self.index)

    def test_no_booking_confirmed_phrase(self):
        self.assertNotIn("预约已确认", self.index + self.sample)

    def test_crisis_numbers(self):
        self.assertIn("000", self.sample)
        self.assertIn("13 11 14", self.sample)
        self.assertNotIn("400-161-9995", self.sample)

    def test_schema_file_exists(self):
        self.assertTrue((ROOT / "content" / "insights" / "SCHEMA.md").exists())

    def test_published_sorted(self):
        dates = [a["date"] for a in self.published]
        self.assertEqual(dates, sorted(dates, reverse=True))

if __name__ == "__main__":
    unittest.main()
