# 日签自动发布方案（草案 · 未批准 · 未启用）

Founder 已明确：**暂不批准 GitHub Actions 自动发布。** 本文只供后续决策，仓库中没有对应 workflow。

## 每日构建时间

建议：`cron: "15 13 * * *"`（GitHub 为 UTC）。

- 夏令时 AEDT（UTC+11）：悉尼当天 00:15  
- 冬令时 AEST（UTC+10）：悉尼当天 23:15（前一日）  

若要求**全年都在悉尼日历日开始后不久**运行，不能只用一条固定 UTC cron。可选：

1. 两条 cron（10 月–4 月 13:15 UTC；4 月–10 月 14:15 UTC），每年核对 NSW 夏令时切换日；或  
2. 每小时跑一次，脚本内用 Australia/Sydney 判断「今天是否已 build 过」。

推荐先用方案 2 的「每小时 + 脚本内判断」，避免漏掉切换日；成本仍接近免费额度。

## 悉尼时区及夏令时

- 发布日 = `published_at` 的 Sydney 日历日。  
- 实现：`daily/build.py` 的 `sydney_date_from_utc`（NSW：10 月第一个周日 02:00 AEST 开始 DST，4 月第一个周日 03:00 AEDT 结束）。  
- Action 环境应安装 `tzdata` 作为双保险，但仍不依赖它才能算对日期。

## GitHub Actions 权限

最小权限（须另批后才写入）：

- `contents: write`：仅允许提交 `daily/*.html`、`daily/sitemap.xml`（及必要时 insights 生成物）  
- 禁止 `secrets` 用于邮件、Stripe、CMS  
- 保护 `main`：Action **不要**直接 push `main`；应开 bot PR，仍由人工合并  

不批准「定时直接部署生产」。

## 构建失败通知

- GitHub 原生：workflow 失败邮件给仓库管理员  
- 可选：失败时只留 GitHub Issue，不接新的第三方告警服务（本阶段不引入付费）

## 内容审核与发布边界

自动构建 **只重新生成已审核 JSON 的可见性**（日期到了就出现），**不得**：

- 调用模型写心理学正文  
- 把 `draft` 改成 `published`  
- 补 DOI 或参考文献  
- 在未设 `related_insight_slug` 或目标页不存在时制造智库链接  

`draft` 与未来日期仍只在 build 时过滤。

## 运行成本与维护

- 公开仓库分钟额度内通常为 $0；私有仓库按 GitHub 计费，每小时一次也远低于付费阈值。  
- 维护：NSW 夏令时规则若立法变更需改脚本；每年检查一次即可。  
- 失败时回退：关掉 workflow，网站保持上一次成功生成的 HTML。
