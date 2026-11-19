# 心理智库接入轻量 CMS 的预留方案（Phase 2，未启用）

Phase 1 把每篇文章收敛为 `content/insights/<slug>.md` + YAML front matter。这是以后 CMS 的同一事实源。

## 建议顺序

1. **现在：** Markdown + `insights/build.py` + GitHub 审阅后合并。  
2. **Phase 2：** 评估 Decap CMS 或 TinaCMS，collection 指向 `content/insights/`，字段与 `content/insights/SCHEMA.md` 对齐。编辑在后台改 status / 正文；CI 跑 `python insights/build.py`。仍不自动写研究、不自动填 DOI。  
3. **Phase 3：** 同一套元数据再连日签、Newsletter（另批邮件服务商）。

## 不要在 Phase 1 做的事

- 不挂 `/admin`
- 不接 GitHub OAuth / 新数据库
- 不把草稿 Markdown 部署到 Vercel（`.vercelignore` 已排除 `content/`）

## 编辑周报（在 CMS 到来之前）

1. 复制一篇 published Markdown，改 slug。  
2. `status: draft`，写正文与核实过的 `references`。  
3. Founder 把 status 改为 `published`。  
4. 运行 `python insights/build.py` 并检查测试。  
5. 另开 PR；**不直接进 main，除非 Founder 批准上线。**
