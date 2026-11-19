# -*- coding: utf-8 -*-
"""Generate public HTML for dated, published daily cards only."""
from __future__ import annotations

import html
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "daily"
OUT = ROOT / "daily"
INSIGHTS = ROOT / "insights"
SITE = "https://seesoul.com.au"
REQUIRED = (
    "id", "slug", "title_zh", "term_en", "published_at", "one_liner",
    "manifestations", "mechanism", "suggestion", "reflection", "status", "category",
)

NAV = """          <a href="{p}index.html">首页</a>
          <a href="{p}counselling.html">心理咨询</a>
          <a href="{p}life-theme.html">生命课题</a>
          <a href="{p}compass-start.html">SeeSoul Compass</a>
          <a href="{p}explore.html">自我探索</a>
          <a href="{p}insights/">心理智库</a>
          <a href="{here}" {cur}>心理学日签</a>
          <a href="{p}philosophy.html">Our Philosophy</a>
          <a href="{p}founder.html">认识容熙</a>
          <a class="btn btn--gold" href="{p}booking.html">预约咨询</a>"""


def sydney_today() -> date:
    env = os.environ.get("DAILY_TODAY")
    if env:
        return date.fromisoformat(env)
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Australia/Sydney")).date()
    except Exception:
        return date.today()


def load_cards() -> list[dict]:
    cards = []
    for path in sorted(CONTENT.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = [k for k in REQUIRED if k not in data]
        if missing:
            raise ValueError(f"{path.name} missing {missing}")
        if data["status"] not in ("draft", "published"):
            raise ValueError(f"{path.name} bad status")
        slug = data["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"bad slug {slug}")
        date.fromisoformat(data["published_at"])
        if not isinstance(data["manifestations"], list) or not data["manifestations"]:
            raise ValueError(f"{path.name} manifestations")
        cards.append(data)
    slugs = [c["slug"] for c in cards]
    if len(slugs) != len(set(slugs)):
        raise ValueError("duplicate slug")
    return cards


def public_cards(cards: list[dict], today: date) -> list[dict]:
    visible = []
    for c in cards:
        if c["status"] != "published":
            continue
        if date.fromisoformat(c["published_at"]) > today:
            continue
        visible.append(c)
    visible.sort(key=lambda c: (c["published_at"], c["id"]), reverse=True)
    return visible


def insight_href(slug: Optional[str]) -> Optional[str]:
    if not slug:
        return None
    page = INSIGHTS / f"{slug}.html"
    if page.exists():
        return f"../insights/{slug}.html"
    return None


def card_html(c: dict, related: str | None) -> str:
    term = f'<p class="daily-card__term">{html.escape(c["term_en"])}</p>' if c.get("term_en") else ""
    items = "".join(f"<li>{html.escape(x)}</li>" for x in c["manifestations"])
    related_block = ""
    if related:
        related_block = (
            '<section class="daily-card__related">'
            "<h2>延伸阅读</h2>"
            f'<p><a href="{html.escape(related)}">心理智库相关说明</a></p>'
            "</section>"
        )
    return f"""
      <article class="daily-card">
        <p class="daily-card__kicker">心理学日签 · {html.escape(c["published_at"])}</p>
        <h1 class="daily-card__title">{html.escape(c["title_zh"])}</h1>
        {term}
        <p class="daily-card__line">{html.escape(c["one_liner"])}</p>
        <section>
          <h2>生活中的常见表现</h2>
          <ul>{items}</ul>
        </section>
        <section>
          <h2>心理机制</h2>
          <p>{html.escape(c["mechanism"])}</p>
        </section>
        <section>
          <h2>觉察建议</h2>
          <p>{html.escape(c["suggestion"])}</p>
        </section>
        <section>
          <h2>SeeSoul Reflection</h2>
          <p>{html.escape(c["reflection"])}</p>
        </section>
        {related_block}
        <p class="daily-card__note">网页文字卡片 · 教育说明，不是诊断。紧急情况请拨打 000，或联系 Lifeline 13 11 14。</p>
      </article>
    """


def shell(title, description, canonical, main, extra_js=""):
    p = "../"
    nav = NAV.format(p=p, here="./", cur='aria-current="page"')
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description)}" />
    <link rel="canonical" href="{html.escape(canonical)}" />
    <meta property="og:title" content="{html.escape(title)}" />
    <meta property="og:description" content="{html.escape(description)}" />
    <meta property="og:url" content="{html.escape(canonical)}" />
    <meta property="og:type" content="article" />
    <meta property="og:locale" content="zh_CN" />
    <meta name="twitter:card" content="summary" />
    <link rel="stylesheet" href="../theme.css?v=sys1" />
  </head>
  <body data-page-id="daily">
    <a class="skip-link" href="#main-content">跳转到主要内容</a>
    <header class="site-header">
      <div class="site-header__inner">
        <a class="brand brand--logo" href="../index.html"><img class="brand-logo" src="../assets/seesoul-logo-gold.png" alt="SEESOUL 熙愈心空间"></a>
        <button class="nav-toggle" id="navToggle" type="button" aria-controls="siteNav" aria-expanded="false" aria-label="打开导航菜单"><span class="nav-toggle__bars" aria-hidden="true"></span></button>
        <nav class="site-nav" id="siteNav">
{nav}
        </nav>
      </div>
    </header>
    <main id="main-content" tabindex="-1">
{main}
    </main>
    <footer class="site-footer">
      <div class="site-footer__inner">
        <div><div class="brand" style="color:var(--color-gold-soft)">SEESOUL<small>熙愈心空间</small></div><p class="footer-tagline"><small>Seeing Before Being™</small></p></div>
        <div style="display:grid;gap:0.5rem"><a href="../index.html">首页</a><a href="../explore.html">自我探索</a><a href="../insights/">心理智库</a><a href="./">心理学日签</a></div>
        <div style="display:grid;gap:0.5rem"><a href="../compass-start.html">SeeSoul Compass</a><a href="../booking.html">预约咨询</a><a href="../index.html#trust">隐私 · 专业边界 · 免责声明</a></div>
      </div>
    </footer>
    <script src="../nav.js" defer></script>
    {extra_js}
  </body>
</html>
"""


SHARE_JS = """<script>
(function () {
  var btn = document.getElementById("dailyShare");
  if (!btn) return;
  var url = btn.getAttribute("data-url") || window.location.href;
  btn.addEventListener("click", function () {
    if (navigator.share) {
      navigator.share({ title: document.title, url: url }).catch(function () {});
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        btn.textContent = "链接已复制";
      });
      return;
    }
    window.prompt("复制这张日签的链接", url);
  });
})();
</script>"""


def render_index(visible: list[dict]) -> str:
    if not visible:
        inner = "<p>暂时还没有已发布的日签。</p>"
    else:
        today_card = visible[0]
        related = insight_href(today_card.get("related_insight_slug"))
        archive = visible[1:]
        cats = sorted({c["category"] for c in visible})
        chips = "".join(f'<button class="chip" type="button" data-daily-filter="{html.escape(c)}" aria-pressed="false">{html.escape(c)}</button>' for c in cats)
        rows = []
        for c in archive:
            rows.append(
                f'<a class="content-card" href="{html.escape(c["slug"])}.html" data-daily-cat="{html.escape(c["category"])}" data-daily-q="{html.escape(c["title_zh"] + " " + (c.get("term_en") or ""))}">'
                f'<span class="tag">{html.escape(c["category"])}</span>'
                f"<h3>{html.escape(c['title_zh'])}</h3>"
                f"<p>{html.escape(c['published_at'])}</p></a>"
            )
        archive_html = ""
        if archive:
            archive_html = f"""
          <header class="section-header">
            <h2>往期日签</h2>
            <p class="sub">按日期排列。可按主题筛选，或输入标题、英文术语查找。</p>
          </header>
          <div class="chips" role="toolbar" aria-label="按主题查看">
            <button class="chip" type="button" data-daily-filter="all" aria-pressed="true">全部</button>
            {chips}
          </div>
          <p><label for="dailySearch">关键词</label>
          <input id="dailySearch" type="search" maxlength="80" style="width:100%;max-width:20rem;margin-top:0.35rem;padding:0.45rem 0.6rem"></p>
          <div class="content-grid" id="dailyArchive">{"".join(rows)}</div>
          <p id="dailyEmpty" hidden>没有符合的往期日签。</p>
            """
        inner = card_html(today_card, related) + archive_html
        inner += f'<p class="daily-web-note">这是网页文字卡片。目前没有经过验证的 9:16 图片文件，因此没有图片下载。</p>'
    main = f"""
      <section class="section section--ivory daily-page">
        <div class="container">
          <span class="eyebrow">心理学日签</span>
          <p class="daily-lead">每天一张短卡片，用来认识日常生活里的心理现象。它不是长文章，也不是诊断。</p>
          {inner}
        </div>
      </section>
    """
    extra = """<script>
(function () {
  var chips = document.querySelectorAll("[data-daily-filter]");
  var cards = document.querySelectorAll("#dailyArchive [data-daily-cat]");
  var empty = document.getElementById("dailyEmpty");
  var search = document.getElementById("dailySearch");
  if (!chips.length) return;
  function apply() {
    var cat = "all";
    chips.forEach(function (c) { if (c.getAttribute("aria-pressed") === "true") cat = c.getAttribute("data-daily-filter"); });
    var q = (search && search.value || "").trim().toLowerCase();
    var n = 0;
    cards.forEach(function (card) {
      var okCat = cat === "all" || card.getAttribute("data-daily-cat") === cat;
      var okQ = !q || (card.getAttribute("data-daily-q") || "").toLowerCase().indexOf(q) !== -1;
      var show = okCat && okQ;
      card.hidden = !show;
      if (show) n += 1;
    });
    if (empty) empty.hidden = n !== 0;
  }
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      chips.forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
      apply();
    });
  });
  if (search) search.addEventListener("input", apply);
})();
</script>"""
    return shell("心理学日签 · SeeSoul 熙愈心空间", "SeeSoul 心理学日签：用一张短卡片认识日常生活中的心理现象。", f"{SITE}/daily/", main, extra)


def render_detail(c: dict) -> str:
    related = insight_href(c.get("related_insight_slug"))
    url = f"{SITE}/daily/{c['slug']}.html"
    share = (
        f'<p class="daily-share"><button type="button" class="btn btn--ghost-ivory" id="dailyShare" data-url="{html.escape(url)}">分享这张日签</button> '
        f'<span class="daily-web-note">可复制独立链接。没有正式图片时，没有图片下载。</span></p>'
    )
    main = f"""
      <section class="section section--ivory daily-page">
        <div class="container">
          {card_html(c, related)}
          {share}
          <p><a class="prose-back" href="./">← 全部日签</a></p>
        </div>
      </section>
    """
    title = c.get("seo_title") or (c["title_zh"] + "｜心理学日签 · SeeSoul")
    desc = c.get("seo_description") or c["one_liner"]
    return shell(title, desc, url, main, SHARE_JS)


def write_sitemap(visible: list[dict]) -> None:
    urls = [f"{SITE}/daily/"] + [f"{SITE}/daily/{c['slug']}.html" for c in visible]
    body = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body
        + "\n</urlset>\n",
        encoding="utf-8",
    )


def build(today: Optional[date] = None) -> list:
    today = today or sydney_today()
    visible = public_cards(load_cards(), today)
    OUT.mkdir(exist_ok=True)
    for p in OUT.glob("*.html"):
        p.unlink()
    sm = OUT / "sitemap.xml"
    if sm.exists():
        sm.unlink()
    (OUT / "index.html").write_text(render_index(visible), encoding="utf-8")
    for c in visible:
        (OUT / f"{c['slug']}.html").write_text(render_detail(c), encoding="utf-8")
    write_sitemap(visible)
    print("visible", len(visible), "today", today.isoformat())
    return visible


if __name__ == "__main__":
    build()
