# 心理智库内容结构（CMS 升级预留）

正文只写在本目录的 Markdown 里，不手改 `insights/*.html`。

生成器：`python insights/build.py`  
公开输出：`insights/index.html`、`insights/<slug>.html`  
仅 `status: published` **且** `sample` 不为 true。样稿（如 `yangao-lanmu-shuoming`）可留在本目录供本地核对，但不得进入生产页面、列表、sitemap。

本地审核（不改正式状态）：

```
python insights/build.py --preview
```

写出 `insights/preview/`（gitignore / vercelignore），含样稿与草稿，带 noindex。

默认署名：`SeeSoul 编辑部`。有真实撰写/审核人时再填 `author` / `reviewer`，不得虚构。

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

`id`（稳定内容 ID，禁止重复导入）、`issue_number`、`issue_date`（稿件日期，不等于上线日）、`published_at`（实际上线日，未发布保持空）、`subtitle`, `article_type` (`research_digest` \| `research_explainer` \| `psychology_guide` \| `editorial`), `tags`, `featured`, `sample`, `reviewer`, `seo_title`, `seo_description`, `canonical_url`, `related_slugs`, `related_daily_ids`, `evidence_summary`, `limitations`, `safety_note`、`editorial_decision`（仅内部编辑记录，如 `approved`。不得据此改 `status`、填写 `reviewer`、生成公开页或写成具名专业审核）

草稿的 `date` 使用稿件日期便于预览排序；`published_at` / 空的 `updated_at` 表示尚未正式上线。

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
