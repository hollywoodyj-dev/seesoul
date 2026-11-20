# -*- coding: utf-8 -*-
"""Generate public HTML for published insights only. Does not invent references."""
from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "insights"
OUT = ROOT / "insights"
SITE = "https://seesoul.com.au"
CATEGORIES = [
    "心理学与日常生活",
    "心理咨询与治疗研究",
    "情绪与自我觉察",
    "关系与成长",
    "研究周报",
]
REQUIRED = ("title", "slug", "date", "category", "summary", "author", "status", "updated_at")

NAV = """          <a href="{p}index.html">首页</a>
          <a href="{p}counselling.html">心理咨询</a>
          <a href="{p}life-theme.html">生命课题</a>
          <a href="{p}compass-start.html">SeeSoul Compass</a>
          <a href="{p}explore.html">自我探索</a>
          <a href="{here}" {cur}>心理智库</a>
          <a href="{p}philosophy.html">Our Philosophy</a>
          <a href="{p}founder.html">认识容熙</a>
          <a class="btn btn--gold" href="{p}booking.html">预约咨询</a>"""


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError("missing YAML front matter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("unterminated front matter")
    raw, body = parts[1], parts[2].lstrip("\n")
    data = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if line.startswith("  "):
            raise ValueError("orphaned indent: " + line)
        if ":" not in line:
            raise ValueError("bad line: " + line)
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if rest == "|":
            block = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                block.append(lines[i][2:] if lines[i].startswith("  ") else "")
                i += 1
            data[key] = "\n".join(block).strip()
            continue
        if rest in ("[]",):
            data[key] = []
            i += 1
            continue
        if rest == "":
            items = []
            i += 1
            current = None
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].startswith("- ")):
                ln = lines[i]
                if ln.startswith("- "):
                    val = ln[2:].strip()
                    if current:
                        items.append(current)
                        current = None
                    if ":" in val and not val.startswith("http"):
                        k, v = val.split(":", 1)
                        current = {k.strip(): _scalar(v.strip())}
                    else:
                        items.append(_scalar(val))
                elif ln.startswith("    ") and current is not None:
                    if ":" in ln:
                        k, v = ln.strip().split(":", 1)
                        current[k.strip()] = _scalar(v.strip())
                elif ln.startswith("  - "):
                    val = ln[4:].strip()
                    if current:
                        items.append(current)
                        current = None
                    if ":" in val:
                        k, v = val.split(":", 1)
                        current = {k.strip(): _scalar(v.strip())}
                    else:
                        items.append(_scalar(val))
                elif ln.startswith("  ") and current is not None and ":" in ln:
                    k, v = ln.strip().split(":", 1)
                    current[k.strip()] = _scalar(v.strip())
                i += 1
            if current:
                items.append(current)
            data[key] = items
            continue
        data[key] = _scalar(rest)
        i += 1
    return data, body


def _scalar(val: str):
    if val in ("true", "True"):
        return True
    if val in ("false", "False"):
        return False
    if val in ("null", "Null", "NULL", "~", "none", "None"):
        return None
    if val in ("[]",):
        return []
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val


def load_articles() -> list[dict]:
    articles = []
    for path in sorted(CONTENT.glob("*.md")):
        if path.name.upper() in ("SCHEMA.MD", "CMS_UPGRADE.MD", "SCHEDULE.MD"):
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        meta, body = parse_frontmatter(text)
        missing = []
        for k in REQUIRED:
            val = meta.get(k)
            if k == "updated_at" and meta.get("status") == "draft" and val in ("", None):
                meta["updated_at"] = meta.get("date") or ""
                continue
            if k not in meta or meta[k] in ("", None):
                missing.append(k)
        if missing:
            raise ValueError(f"{path.name} missing {missing}")
        if meta["category"] not in CATEGORIES:
            raise ValueError(f"{path.name} bad category {meta['category']}")
        if meta["status"] not in ("draft", "published"):
            raise ValueError(f"{path.name} bad status")
        author = str(meta.get("author") or "").strip()
        if not author:
            raise ValueError(f"{path.name} author required")
        banned_author = ("chatgpt", "gpt-4", "anonymous expert", "匿名专家", "auto", "todo")
        if author.lower() in banned_author:
            raise ValueError(f"{path.name} fictional or placeholder author")
        slug = meta["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"bad slug {slug}")
        refs = meta.get("references") or []
        if not isinstance(refs, list):
            raise ValueError("references must be a list")
        for ref in refs:
            if not isinstance(ref, dict) or not ref.get("title") or not ref.get("source_url"):
                raise ValueError(f"{path.name} reference needs title and source_url")
            if "doi" in ref and ref["doi"] in ("auto", "TODO", "tbd"):
                raise ValueError("unverified doi placeholder")
        meta["body"] = body
        meta["path"] = path.name
        articles.append(meta)
    slugs = [a["slug"] for a in articles]
    if len(slugs) != len(set(slugs)):
        raise ValueError("duplicate slug")
    ids = [a.get("id") for a in articles if a.get("id")]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate id")
    return articles


def production_articles(articles: list[dict]) -> list[dict]:
    """Published, non-sample only. Sample pages stay local/preview.
    editorial_decision is internal only and never maps to public status."""
    out = [a for a in articles if a["status"] == "published" and not a.get("sample")]
    out.sort(key=lambda a: (a["date"], 1 if a.get("featured") else 0), reverse=True)
    return out


def md_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+|/[^\)]+)\)", r'<a href="\2" rel="noopener noreferrer">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def md_to_html(src: str) -> str:
    lines = src.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("### "):
            out.append("<h3>" + md_inline(line[4:]) + "</h3>")
        elif line.startswith("## "):
            out.append("<h2>" + md_inline(line[3:]) + "</h2>")
        elif line.startswith("# "):
            out.append("<h2>" + md_inline(line[2:]) + "</h2>")
        elif line.startswith("- ") or line.startswith("1. "):
            tag = "ol" if line[:3] == "1. " else "ul"
            out.append(f"<{tag}>")
            while i < len(lines) and (lines[i].startswith("- ") or re.match(r"\d+\. ", lines[i])):
                item = re.sub(r"^(?:- |\d+\. )", "", lines[i])
                out.append("<li>" + md_inline(item) + "</li>")
                i += 1
            out.append(f"</{tag}>")
            continue
        else:
            para = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].startswith("- ") and not re.match(r"\d+\. ", lines[i]):
                para.append(lines[i])
                i += 1
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            continue
        i += 1
    return "\n".join(out)


def shell(title, description, canonical, extra_head, main, current="insights", depth=1, preview=False):
    p = "../" * depth
    here = "./"
    cur = 'aria-current="page"' if current == "insights" else ""
    nav = NAV.format(p=p, here=here, cur=cur)
    robots = '<meta name="robots" content="noindex,nofollow,noarchive" />\n    ' if preview else ""
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)}</title>
    {robots}<meta name="description" content="{html.escape(description)}" />
    <link rel="canonical" href="{html.escape(canonical)}" />
    <meta property="og:title" content="{html.escape(title)}" />
    <meta property="og:description" content="{html.escape(description)}" />
    <meta property="og:url" content="{html.escape(canonical)}" />
    <meta property="og:locale" content="zh_CN" />
    <link rel="stylesheet" href="{p}theme.css?v=sys5" />
    <link rel="alternate" hreflang="en" href="https://seesoul.com.au/en/insights.html" />
    <link rel="alternate" hreflang="zh-CN" href="{html.escape(canonical)}" />
    {extra_head}
  </head>
  <body data-page-id="insights">
    <a class="skip-link" href="#main-content">跳转到主要内容</a>
    <header class="site-header">
      <div class="site-header__inner">
        <a class="brand brand--logo" href="{p}index.html"><img class="brand-logo" src="{p}assets/seesoul-logo-gold.png" alt="SEESOUL 熙愈心空间"></a>
        <nav class="lang-switch" aria-label="语言">
          <span lang="zh-CN" aria-current="true">中文</span>
          <a href="{p}en/insights.html" hreflang="en" lang="en">English</a>
        </nav>
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
        <div style="display:grid;gap:0.5rem"><a href="{p}index.html">首页</a><a href="{p}counselling.html">心理咨询</a><a href="{p}explore.html">自我探索</a><a href="./">心理智库</a></div>
        <div style="display:grid;gap:0.5rem"><a href="{p}compass-start.html">SeeSoul Compass</a><a href="{p}booking.html">预约咨询</a><a href="{p}index.html#trust">隐私 · 专业边界 · 免责声明</a></div>
      </div>
    </footer>
    <script src="{p}nav.js" defer></script>
  </body>
</html>
"""


def json_ld(article: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": article["title"],
        "datePublished": article.get("published_at") or article["date"],
        "dateModified": article.get("updated_at") or article.get("published_at") or article["date"],
        "author": (
            {"@type": "Organization", "name": article["author"]}
            if article["author"] == "SeeSoul 编辑部"
            else {"@type": "Person", "name": article["author"]}
        ),
        "inLanguage": "zh-CN",
        "url": f"{SITE}/insights/{article['slug']}.html",
        "description": article.get("seo_description") or article["summary"],
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def render_index(published: list[dict], preview: bool = False) -> str:
    featured = [a for a in published if a.get("featured")]
    cards = []
    for a in published:
        sample = '<span class="tag">样稿</span>' if a.get("sample") else f'<span class="tag">{html.escape(a["category"])}</span>'
        cards.append(
            f'<a class="content-card" href="{html.escape(a["slug"])}.html">'
            f"{sample}<h3>{html.escape(a['title'])}</h3>"
            f"<p>{html.escape(a['summary'])}</p>"
            f'<p class="insights-date">{html.escape(a["date"])}</p></a>'
        )
    feat_html = ""
    if featured:
        f = featured[0]
        feat_html = f"""
        <article class="insights-feature">
          <span class="eyebrow">精选</span>
          <h2><a href="{html.escape(f['slug'])}.html">{html.escape(f['title'])}</a></h2>
          <p>{html.escape(f['summary'])}</p>
        </article>"""
    cats = "".join(f'<a class="chip" href="#{html.escape(c)}">{html.escape(c)}</a>' for c in CATEGORIES)
    by_cat = []
    for c in CATEGORIES:
        items = [a for a in published if a["category"] == c]
        if not items:
            continue
        lis = "".join(
            f'<li><a href="{html.escape(a["slug"])}.html">{html.escape(a["title"])}</a> <span>{html.escape(a["date"])}</span></li>'
            for a in items
        )
        by_cat.append(f'<section id="{html.escape(c)}" class="insights-cat"><h2>{html.escape(c)}</h2><ul>{lis}</ul></section>')
    main = f"""
      <section class="page-hero">
        <div class="page-hero__inner">
          <span class="eyebrow">心理智库 Blog</span>
          <h1>把值得关注的心理学知识，写成普通人用得上的说明。</h1>
          <p>SeeSoul Psychology Insights。我们先讲这件事和日常生活有什么关系，再说研究能支持到哪一步，以及哪些地方还不确定。</p>
          <p class="insights-note">本栏目不是诊断，也不替代一对一咨询。紧急情况请拨打 000，或联系 Lifeline 13 11 14。</p>
        </div>
      </section>
      <section class="section section--ivory">
        <div class="container">
          {'<p class="insights-sample-banner" role="note">本地预览 · 含样稿与草稿核对页 · 禁止收录</p>' if preview else ""}
          {feat_html}
          <header class="section-header">
            <h2>最新文章</h2>
          </header>
          {('<div class="content-grid">' + "".join(cards) + "</div>") if cards else "<p>正式文章准备中。Founder 审核通过前，这里不会放样稿或占位研究。</p>"}
          <p class="insights-cats-label">按主题查看</p>
          <div class="chips">{cats}</div>
          {"".join(by_cat) if by_cat else "<p>这一类还没有正式文章。</p>"}
          <p class="insights-cross"><a class="text-link" href="../explore.html">自我探索仍是独立栏目，九篇文章网址不变 →</a></p>
        </div>
      </section>
    """
    return shell(
        "心理智库 · SeeSoul 熙愈心空间",
        "SeeSoul 心理智库：把心理学写成普通人看得懂、用得上的中文说明。",
        f"{SITE}/insights/",
        "",
        main,
        depth=2 if preview else 1,
        preview=preview,
    )


def render_article(a: dict, preview: bool = False) -> str:
    banner = ""
    if preview:
        banner = '<p class="insights-sample-banner" role="note">草稿预览｜尚未发布</p>'
    elif a.get("sample"):
        banner = '<p class="insights-sample-banner" role="note">样稿 · 用于核对页面</p>'
    refs = a.get("references") or []
    ref_html = ""
    if refs:
        lis = []
        for r in refs:
            label = html.escape(r["title"])
            url = html.escape(r["source_url"])
            extra = []
            if r.get("source_name"):
                extra.append(html.escape(str(r["source_name"])))
            if r.get("year"):
                extra.append(html.escape(str(r["year"])))
            if r.get("doi"):
                extra.append("DOI: " + html.escape(str(r["doi"])))
            if r.get("verification_scope"):
                extra.append("核查范围: " + html.escape(str(r["verification_scope"])))
            meta = (" · ".join(extra) + " · ") if extra else ""
            lis.append(f'<li>{meta}<a href="{url}" rel="noopener noreferrer">{label}</a></li>')
        ref_html = "<h2>参考资料</h2><ol class=\"insights-refs\">" + "".join(lis) + "</ol>"
    ev = a.get("evidence_summary")
    lim = a.get("limitations")
    extra_sections = ""
    if ev:
        extra_sections += f"<h2>证据说明</h2><p>{html.escape(str(ev))}</p>"
    if lim:
        extra_sections += f"<h2>局限</h2><p>{html.escape(str(lim))}</p>"
    invite = """
          <div class="article-invite">
            <h2>了解 SeeSoul 的心理支持服务</h2>
            <p>阅读不能替代针对你个人情况的咨询。若你希望有人一起看正在经历的事情，可以了解一对一咨询如何进行。</p>
            <a class="btn btn--ghost-ivory" href="../counselling.html">了解咨询服务</a>
          </div>"""
    safety = a.get("safety_note") or "本页仅用于教育，不替代个人化诊断与治疗。紧急情况请拨打 000，或联系 Lifeline 13 11 14。"
    desc = a.get("seo_description") or a["summary"]
    title = a.get("seo_title") or (a["title"] + " · 心理智库")
    updated = "" if a["updated_at"] == a["date"] else f" · 更新 {html.escape(a['updated_at'])}"
    reviewer = str(a.get("reviewer") or "").strip()
    reviewed = f" · 审核 {html.escape(reviewer)}" if reviewer else ""
    sub = f"<p class=\"article-byline\">{html.escape(a.get('subtitle'))}</p>" if a.get("subtitle") else ""
    main = f"""
      <div class="container insights-article">
        <div class="article-head">
          <span class="eyebrow">心理智库 · {html.escape(a['category'])}</span>
          <h1>{html.escape(a['title'])}</h1>
          {sub}
          <p class="insights-by">{html.escape(a['author'])} · {html.escape(a['date'])}{updated}{reviewed}</p>
        </div>
        <article class="prose">
          {banner}
          <p class="prose-lead">{html.escape(a['summary'])}</p>
          {md_to_html(a['body'])}
          {extra_sections}
          {ref_html}
          <p class="insights-disclaimer">{html.escape(str(safety))}</p>
          {invite}
          <a class="prose-back" href="./">← 回到心理智库</a>
        </article>
      </div>
    """
    return shell(
        title,
        desc,
        f"{SITE}/insights/{a['slug']}.html",
        json_ld(a),
        main,
        depth=2 if preview else 1,
        preview=preview or bool(a.get("sample")),
    )


def write_sitemap(published: list[dict]) -> None:
    urls = [f"{SITE}/insights/"] + [f"{SITE}/insights/{a['slug']}.html" for a in published]
    body = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body
        + "\n</urlset>\n",
        encoding="utf-8",
    )


def clean_generated() -> None:
    OUT.mkdir(exist_ok=True)
    for p in OUT.glob("*.html"):
        p.unlink()
    sm = OUT / "sitemap.xml"
    if sm.exists():
        sm.unlink()


def build(preview: bool = False) -> list[dict]:
    all_articles = load_articles()
    if preview:
        visible = [a for a in all_articles if a["status"] in ("draft", "published")]
        visible.sort(key=lambda a: a["date"], reverse=True)
        dest = OUT / "preview"
        dest.mkdir(parents=True, exist_ok=True)
        for p in dest.glob("*.html"):
            p.unlink()
        (dest / "index.html").write_text(render_index(visible, preview=True), encoding="utf-8")
        for a in visible:
            (dest / f"{a['slug']}.html").write_text(render_article(a, preview=True), encoding="utf-8")
        print("preview", len(visible), "not for production")
        return visible
    published = production_articles(all_articles)
    clean_generated()
    (OUT / "index.html").write_text(render_index(published), encoding="utf-8")
    for a in published:
        (OUT / f"{a['slug']}.html").write_text(render_article(a), encoding="utf-8")
    write_sitemap(published)
    print("published", len(published), "excluded_sample_or_draft", len(all_articles) - len(published))
    return published


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="local sample/draft review; writes insights/preview/")
    args = parser.parse_args()
    build(preview=args.preview)
