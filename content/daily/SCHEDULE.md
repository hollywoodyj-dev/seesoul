# 日签定时发布：静态部署能做什么

## 结论

当前模式（把生成好的 HTML 推进 Git，Vercel 只托管静态文件）**不能**在不重新构建的情况下，于某个日期自动「长出」新页面。

本栏目的日期规则是：

- `status: draft` → 不生成 HTML、不进首页、不进 sitemap、不进任何公开 JSON
- `status: published` 且 `published_at` 晚于构建当天（悉尼）→ 同样不生成公开页
- 仅用 CSS/`hidden` 在浏览器里藏未来内容 **不算** 草稿保护，生成器不会这么做

`published_at` 是 **Australia/Sydney 的日历日**，不是 UTC 日。边界是当天 00:00 悉尼时间：

- 夏令时 AEDT（约 10 月第一个星期日至 4 月第一个星期日）：UTC+11。UTC 13:00 才进入次日。
- 冬令时 AEST：UTC+10。UTC 14:00 才进入次日。

生成器优先用 `zoneinfo`；没有 `tzdata` 时用上述 NSW 夏令时规则计算，**不会**再用运行机器的本地时区冒充悉尼。

因此：把 `published_at` 写成明天，只有在明天（悉尼）之后的某一次 build + 部署之后，卡片才会出现。

**生产注意：** 当前 Vercel **不会**运行 `daily/build.py`。线上看到的是仓库里已经生成的 HTML。日期过滤发生在提交这些 HTML 的那一次本地/CI 构建。

## 可选后续（须 Founder 另批，Phase 2 未启用）

1. 每天悉尼时间 00:10 用 GitHub Action 跑 `python daily/build.py` 与 `python insights/build.py`，若有新文件则提交并让 Vercel 部署。  
2. 或改为构建时生成、Vercel 在请求时渲染（那会改变技术栈，超出本阶段）。

未批准 Action 前，每日发布流程仍是：审核 JSON → 将日期设为当天或过去 → 本地 build → PR。
