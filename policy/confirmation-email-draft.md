# SeeSoul 预约确认邮件 · 待生效后的正式候选模板（FUTURE USE ONLY）

政策基线：`cancellation-policy.html` v1.1 文案定稿。状态：LEGAL & PROFESSIONAL REVIEW REQUIRED，尚未正式生效。
适用：一对一心理咨询。生命课题解读不用这封模板。

**使用限制：** 在政策经法律/专业审核、Founder 批准生效及客户在预约承诺前获得并接受适用条款之前，不得把本模板视作现行强制收费通知，或据此要求客户支付 AUD $75。

---

邮件主题： 【SeeSoul】咨询预约确认｜{{booking_date}} {{booking_time}}（{{timezone_abbr}}）

您好，

您的 SeeSoul 心理咨询预约已由我们确认，详情如下：

- 服务： 一对一心理咨询（60 分钟）
- 咨询费用： AUD $150
- 日期与时间： {{booking_date}} {{booking_time}}（{{timezone_abbr}}，悉尼当地时间）
- 咨询形式： {{session_mode}}
- 免费取消／改期截止： {{cutoff_date}} {{cutoff_time}}（{{cutoff_timezone_abbr}}，悉尼当地时间）
- 取消或改期联系渠道： {{official_cancellation_email_or_channel}}
- 付款状态： {{payment_status_verified_or_pending_or_unpaid}}
- 知情同意书签署状态： {{consent_status_signed_or_pending}}
- 适用政策： {{policy_title_version}}（{{policy_effective_date}}）｜{{policy_url}}

取消及改期说明

如需取消或改期，请至少在已确认的咨询开始前 24 小时通过上述渠道通知 SeeSoul。提前至少 24 小时取消或改期，不收取取消或改期费用；已支付该次咨询费而取消预约的，原则上全额退款。

不足 24 小时取消，或在整个已确认的预约时段内均未出席且未提前取消，原则上拟收取 AUD $75（标准咨询费的 50%）。实际适用须以预约承诺前已明确提供并经您接受的有效条款、具体情况及适用法律为准。迟到不自动算作未出席；同一次预约不会同时收取迟取消与未出席费用。突发情况或技术故障可与 SeeSoul 联系，讨论适当安排。

截止时间按预约开始时刻倒推实际经过的整整 24 小时计算；跨越夏令时切换亦按该方式处理，恰好在截止时刻收到的通知视为按时。通知时间原则上以可核实的接收记录为准，发生邮件技术问题时会公平审核相应记录。

本邮件列出的付款状态、预约状态和知情同意书签署状态是三个独立事项。相关消费者法定权利不受取消政策限制。适用条款以客户作出预约承诺前已获提供并接受的版本为准；后续网站更新不自动追溯既有预约。

如需协助，请回复本邮件或联系 {{official_cancellation_email_or_channel}}。

SeeSoul 熙愈心空间
Seeing Before Being™

---

## 邮件模板的发送门槛

- 仅在 SeeSoul 人工确认了预约时间后才可发送标题含“预约确认”的邮件。付款成功、付款链接跳转与询问邮件都不等于预约确认。
- {{booking_date}}, {{booking_time}}, {{cutoff_date}}, {{cutoff_time}} 需用真实预约记录填充，且时区标记必须是对应时间的 AEST/AEDT；不允许手写猜测。
- {{payment_status...}} 只能来自已核实的支付记录；不能根据打开付款成功页就标为已付。
- {{consent_status...}} 只反映实际签署记录。
- {{policy_title_version}} 必须是客户在预约承诺前获得并接受、且当时已生效的版本；v1.1 尚未生效时，不得填作现行适用版本。
- 本模板不增加自动扣费、自动确认预约、自动签署或新 API。

## 填写说明

- 四个时间字段和两个时区标记，用 `policy/cancellation.js` 的 `emailTimeFields(预约开始时刻)` 生成，不要手算。预约开始时刻必须带时区偏移，例如 `2026-10-04T15:00:00+11:00`。
- 付款状态、预约状态、签署状态分开填写，不能从一个推出另一个。
