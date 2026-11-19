# SeeSoul Consent & E-Signature — 本地沙盒（Gate C 预备）

**状态：** LOCAL PLANNING ONLY · 未连接签署供应商 · 未授权 Production  
**规格：** `04_CURSOR_完整设计与技术执行规范_v2.1.md`

## 推荐第一阶段（人工）

1. 客户了解服务并发送预约邮件（现有 `booking.html`）。
2. SeeSoul 人工确认时间与形式，生成不含个人资料的 `booking_reference`（`SSC-YYYY-XXXXXX`）。
3. 仅在协议**正式生效**后发送专属一次性签署邀请（禁止发送 DRAFT）。
4. 客户阅读、提问、自愿电子签署。
5. 供应商 PDF + 审计轨迹；管理员人工把 `consent_status` 标为 SIGNED。
6. 会谈前分别核对：BOOKING=CONFIRMED / PAYMENT=VERIFIED / CONSENT=SIGNED。任一未满足则不视为准备就绪。

## 本目录做什么

| 文件 | 作用 |
|---|---|
| `states.js` | 三个独立状态机；SIGNED 拒绝 DRAFT 版本 |
| `states.test.js` | 合成客户组合测试 |
| `synthetic-ledger.json` | 假预约编号台账，无真实健康资料 |

**不包含：** DocuSign/Adobe/Dropbox Sign 密钥、webhook、真实邮箱、Stripe secret、PDF 存储。

## 运行

```powershell
node consent/sandbox/states.test.js
```

## Gate

- **A** 执业身份、ABN、生效取消政策、投诉渠道 — 未完成  
- **B** 供应商、数据区域、存储 — 未完成  
- **C** 合成客户全流程 — 本沙盒仅覆盖状态机，不含真实 PDF  
- **D** Founder 授权 Production — 未授权  
