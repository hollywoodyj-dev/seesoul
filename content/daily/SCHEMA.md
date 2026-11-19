# 心理学日签内容结构（CMS 升级预留）

每张卡一个 JSON 文件：`content/daily/<slug>.json`。  
生成器：`python daily/build.py`  
公开输出：仅 `status=published` 且 `published_at` ≤ 构建当日（Australia/Sydney）的卡片。

`content/` 已在 `.vercelignore`，草稿 JSON 不会出现在正式域名。

## 必填

| 字段 | 说明 |
|---|---|
| id | 稳定内部 ID，如 `daily-01` |
| slug | URL 段，发布后不改 |
| title_zh | 中文标题 |
| term_en | 英文术语，可空字符串 |
| published_at | `YYYY-MM-DD` |
| one_liner | 一句话解释 |
| manifestations | 字符串数组，生活中的常见表现 |
| mechanism | 心理机制简述 |
| suggestion | 觉察建议 |
| reflection | SeeSoul Reflection |
| status | `draft` \| `published` |
| category | 主题，用于往期筛选 |

## 可选

`image`（9:16 资源路径，无则网页只出文字卡，**不显示保存图片**）、`image_alt`、`related_insight_slug`（对应 `content/insights` 的 slug；目标页不存在则隐藏延伸阅读）、`seo_title`、`seo_description`

## 定时发布（静态站限制）

过滤发生在 **build 时**，不是浏览器里藏起来。GitHub → Vercel 不会每天自动重跑构建。要把「未来日期」变成当天可见，需要到日期之后再次运行 `daily/build.py` 并部署，或另批 GitHub Action 定时构建。详见 `SCHEDULE.md`。
