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
        cls.sitemap = (build.OUT / "sitemap.xml").read_text(encoding="utf-8")
        cls.previewed = build.build(preview=True)
        cls.preview_sample = (build.OUT / "preview" / "yangao-lanmu-shuoming.html").read_text(encoding="utf-8")

    def test_draft_has_no_public_html(self):
        self.assertFalse((build.OUT / "draft-must-not-publish.html").exists())
        self.assertNotIn("draft-must-not-publish", self.index)
        self.assertNotIn("draft-must-not-publish", self.sitemap)

    def test_sample_not_in_production(self):
        self.assertFalse((build.OUT / "yangao-lanmu-shuoming.html").exists())
        self.assertNotIn("yangao-lanmu-shuoming", self.index)
        self.assertNotIn("yangao-lanmu-shuoming", self.sitemap)
        self.assertEqual(
            [a["slug"] for a in self.published],
            ["when-mistakes-become-self-judgment", "weekly-2026-10-23"],
        )

    def test_preview_keeps_sample_without_status_flip(self):
        self.assertIn("样稿", self.preview_sample)
        self.assertIn("noindex", self.preview_sample)
        self.assertIn("dictionary.apa.org/cognitive-dissonance", self.preview_sample)
        self.assertIn("SeeSoul 编辑部", self.preview_sample)
        md = (ROOT / "content" / "insights" / "yangao-lanmu-shuoming.md").read_text(encoding="utf-8")
        self.assertIn("sample: true", md)
        self.assertNotIn("yangao-lanmu-shuoming", self.index)

    def test_hub_seo_without_sample(self):
        self.assertIn('rel="canonical"', self.index)
        self.assertIn("og:title", self.index)
        self.assertIn("SeeSoul Psychology Insights", self.index)
        self.assertIn("https://seesoul.com.au/insights/", self.sitemap)
        self.assertNotIn("doi.org", self.index.lower())

    def test_no_fake_subscribe(self):
        self.assertNotIn("订阅成功", self.index)
        self.assertNotIn('type="email"', self.index)

    def test_no_booking_confirmed_phrase(self):
        self.assertNotIn("预约已确认", self.index + self.preview_sample)

    def test_crisis_numbers(self):
        self.assertIn("000", self.preview_sample)
        self.assertIn("13 11 14", self.preview_sample)
        self.assertNotIn("400-161-9995", self.preview_sample)

    def test_schema_file_exists(self):
        self.assertTrue((ROOT / "content" / "insights" / "SCHEMA.md").exists())

    def test_published_sorted(self):
        dates = [a["date"] for a in self.published]
        self.assertEqual(dates, sorted(dates, reverse=True))

    ISSUE_01 = (
        "when-mistakes-become-self-judgment",
        "weekly-2026-10-23",
    )
    STILL_DRAFT = (
        "finding-the-right-psychological-support",
        "weekly-2026-10-30",
        "teen-recovery-small-social-steps",
        "weekly-2026-11-06",
        "noticing-premenstrual-mood-patterns",
        "weekly-2026-11-13",
    )

    def test_issue_01_published_without_reviewer_or_noindex(self):
        by_slug = {c["slug"]: c for c in build.load_articles()}
        for slug in self.ISSUE_01:
            self.assertEqual(by_slug[slug]["status"], "published", slug)
            self.assertEqual(by_slug[slug].get("published_at"), "2026-11-20")
            self.assertEqual(by_slug[slug].get("editorial_decision"), "approved")
            self.assertFalse(by_slug[slug].get("reviewer"))
            html = (build.OUT / f"{slug}.html").read_text(encoding="utf-8")
            self.assertNotIn("noindex", html)
            self.assertNotIn("草稿预览", html)
            self.assertNotIn("editorial_decision", html)
            self.assertNotIn("审核", html)
            self.assertIn("SeeSoul 编辑部", html)
            self.assertIn(slug, self.index)
            self.assertIn(slug, self.sitemap)
            preview = (build.OUT / "preview" / f"{slug}.html").read_text(encoding="utf-8")
            self.assertIn("noindex", preview)
            self.assertIn("草稿预览｜尚未发布", preview)

    def test_issue_02_04_stay_draft(self):
        by_slug = {c["slug"]: c for c in build.load_articles()}
        for slug in self.STILL_DRAFT:
            self.assertEqual(by_slug[slug]["status"], "draft", slug)
            self.assertFalse(by_slug[slug].get("published_at"))
            self.assertFalse((build.OUT / f"{slug}.html").exists())
            self.assertNotIn(slug, self.index)
            self.assertNotIn(slug, self.sitemap)

if __name__ == "__main__":
    unittest.main()
