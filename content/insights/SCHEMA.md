# 心理智库内容结构（CMS 升级预留）

正文只写在本目录的 Markdown 里，不手改 `insights/*.html`。

生成器：`python insights/build.py`  
公开输出：`insights/index.html`、`insights/<slug>.html`（仅 `status: published`）  
`content/` 由 `.vercelignore` 排除，草稿 Markdown 不会出现在正式域名上。

## 必填元数据（YAML front matter）

| 字段 | 类型 | 说明 |
|---|---|---|
| title | string | 标题 |
| slug | string | 稳定 URL 段，小写拉丁/连字符，发布后不改 |
| date | YYYY-MM-DD | 首次发布日（列表排序） |
| updated_at | YYYY-MM-DD | 最后更新 |
| category | string | 五个主分类之一，每篇仅一个 |
| summary | string | 列表与 SEO 摘要 |
| author | string | 公开署名 |
| status | `draft` \| `published` | draft 不生成页面、不进首页、不进 sitemap |
| references | list | 可为空 `[]`。不得自动补全 |

## 建议字段（便于日后 Decap / Tina 映射）

`subtitle`, `article_type` (`research_digest` \| `research_explainer` \| `psychology_guide` \| `editorial`), `tags`, `featured`, `sample`, `reviewer`, `seo_title`, `seo_description`, `canonical_url`, `related_slugs`, `related_daily_ids`, `evidence_summary`, `limitations`, `safety_note`

## references 项

`title`, `source_url`（可点链接）, `source_name`, `year`, `doi`（仅核实后填写）, `source_type`

`source_type`: `systematic_review` \| `meta_analysis` \| `randomized_trial` \| `observational` \| `guideline` \| `theoretical` \| `commentary` \| `other`

禁止生成器根据标题猜测 DOI 或作者。

## 主分类

- 心理学与日常生活
- 心理咨询与治疗研究
- 情绪与自我觉察
- 关系与成长
- 研究周报

## 日后 CMS（Phase 2 候选）

Decap / Tina 只需指向 `content/insights/*.md` 的同一套 front matter，不必迁移正文。不要在 Phase 1 启用 `/admin`。
