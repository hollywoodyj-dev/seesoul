"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const { freeDeadline, emailTimeFields, assess } = require("./cancellation");

const ROOT = path.resolve(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(ROOT, f), "utf8");
const summary = JSON.parse(read("policy/cancellation-summary.zh.json"));
const email = read("policy/confirmation-email-draft.md");

const results = [];
function test(name, fn) {
  try { fn(); results.push(["PASS", name]); }
  catch (e) { results.push(["FAIL", name + " | " + e.message]); }
}

const ENTITIES = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": "\"", "&#39;": "'", "&nbsp;": " " };
function plain(html) {
  return html.replace(/<[^>]+>/g, " ").replace(/&[a-z#0-9]+;/g, (m) => ENTITIES[m] || m).replace(/\s+/g, " ").trim();
}
function summaryBlocks(html) {
  return html.match(/<div class="policy-summary" data-policy-summary="cancellation-v1\.1"[^>]*>[\s\S]*?<\/div>/g) || [];
}
const canonical = summary.paragraphs.concat([summary.note]);
const UNQUALIFIED = [
  [/(?<!拟|现阶段)收取\s*(50%|AUD)/, "unqualified fee"],
  [/必收/, "必收"],
  [/自动扣除/, "自动扣除"],
  [/不予退款|概不退款|不退款/, "no-refund wording"],
];

test("canonical summary has four paragraphs, a note and the four pages", () => {
  assert.strictEqual(summary.paragraphs.length, 4);
  assert.deepStrictEqual(summary.pages, ["booking.html", "counselling.html", "consent.html", "consent-counselling.html"]);
});
test("canonical strings need no HTML escaping", () => {
  for (const s of canonical.concat([summary.title])) assert.ok(!/[<>&"]/.test(s), s);
});
test("canonical summary keeps the key limits", () => {
  const all = canonical.join("");
  for (const n of ["24 小时", "不收取取消或改期费用", "整个已确认的咨询时段内均未出席且未提前取消", "原则上拟收取 AUD $75（标准咨询费用的 50%）",
    "有效条款", "适用法律", "迟到不自动构成未出席", "同一次预约不会同时收取迟取消费用和未出席费用", "v1.1 尚待法律及专业审核，尚未正式生效",
    "不构成现阶段收取 AUD $75 的依据"]) assert.ok(all.includes(n), n);
});

for (const page of summary.pages) {
  const html = read(page);
  test(page + ": exactly one canonical summary block", () => assert.strictEqual(summaryBlocks(html).length, 1));
  test(page + ": block matches the canonical text in order", () => {
    const text = plain(summaryBlocks(html)[0] || "");
    let at = 0;
    for (const s of canonical) {
      const i = text.indexOf(s, at);
      assert.ok(i >= 0, "missing or out of order: " + s.slice(0, 24));
      at = i + s.length;
    }
  });
  test(page + ": canonical text is written verbatim in the source", () => {
    for (const s of canonical) assert.ok(html.includes(s), s.slice(0, 24));
  });
  test(page + ": block title is the canonical title", () => {
    assert.ok(html.includes("<h2>" + summary.title + "</h2>") || plain(summaryBlocks(html)[0] || "").startsWith(summary.title));
  });
  test(page + ": links to the full policy", () => assert.ok(html.includes('href="cancellation-policy.html"')));
  test(page + ": no unqualified fee or refund wording anywhere on the page", () => {
    const text = plain(html);
    for (const [re, label] of UNQUALIFIED) assert.ok(!re.test(text), label + ": " + (text.match(re) || [""])[0]);
  });
}

const EXPECTED_PLACEHOLDERS = ["booking_date", "booking_time", "timezone_abbr", "session_mode", "cutoff_date", "cutoff_time",
  "cutoff_timezone_abbr", "official_cancellation_email_or_channel", "payment_status_verified_or_pending_or_unpaid",
  "consent_status_signed_or_pending", "policy_title_version", "policy_effective_date", "policy_url"].sort();
const templatePart = email.split("## 邮件模板的发送门槛")[0];

test("email: placeholders are exactly the agreed set", () => {
  const found = [...new Set((templatePart.match(/\{\{([a-z_]+)\}\}/g) || []).map((m) => m.slice(2, -2)))].sort();
  assert.deepStrictEqual(found, EXPECTED_PLACEHOLDERS);
});
test("email: booking, payment and consent statuses are separate lines", () => {
  assert.ok(/- 付款状态： \{\{payment_status_verified_or_pending_or_unpaid\}\}/.test(templatePart));
  assert.ok(/- 知情同意书签署状态： \{\{consent_status_signed_or_pending\}\}/.test(templatePart));
  assert.ok(templatePart.includes("付款状态、预约状态和知情同意书签署状态是三个独立事项"));
});
test("email: booking time and cutoff both carry their own AEST/AEDT", () => {
  assert.ok(templatePart.includes("{{booking_date}} {{booking_time}}（{{timezone_abbr}}，悉尼当地时间）"));
  assert.ok(templatePart.includes("{{cutoff_date}} {{cutoff_time}}（{{cutoff_timezone_abbr}}，悉尼当地时间）"));
});
test("email: future-use restriction and sending gates are present", () => {
  for (const n of ["FUTURE USE ONLY", "不得把本模板视作现行强制收费通知", "仅在 SeeSoul 人工确认了预约时间", "不能根据打开付款成功页就标为已付",
    "v1.1 尚未生效时，不得填作现行适用版本", "本模板不增加自动扣费、自动确认预约、自动签署或新 API"]) assert.ok(email.includes(n), n);
});
test("email: no retroactive application and statutory rights kept", () => {
  assert.ok(templatePart.includes("后续网站更新不自动追溯既有预约"));
  assert.ok(templatePart.includes("相关消费者法定权利不受取消政策限制"));
});
test("email: same fee limits as the web summary, no unqualified wording", () => {
  for (const n of ["原则上拟收取 AUD $75", "有效条款", "迟到不自动算作未出席", "同一次预约不会同时收取迟取消与未出席费用", "恰好在截止时刻收到的通知视为按时"])
    assert.ok(templatePart.includes(n), n);
  for (const [re, label] of UNQUALIFIED) assert.ok(!re.test(templatePart), label);
});

const TIME_KEYS = ["booking_date", "booking_time", "timezone_abbr", "cutoff_date", "cutoff_time", "cutoff_timezone_abbr"];
const cases = [
  ["ordinary AEDT week", "2026-10-16T15:00:00+11:00",
    ["2026 年 10 月 16 日 星期五", "15:00", "AEDT", "2026 年 10 月 15 日 星期四", "15:00", "AEDT"]],
  ["DST start: AEDT booking, AEST cutoff one clock hour earlier", "2026-10-04T15:00:00+11:00",
    ["2026 年 10 月 4 日 星期日", "15:00", "AEDT", "2026 年 10 月 3 日 星期六", "14:00", "AEST"]],
  ["DST end: AEST booking, AEDT cutoff one clock hour later", "2027-04-04T15:00:00+10:00",
    ["2027 年 4 月 4 日 星期日", "15:00", "AEST", "2027 年 4 月 3 日 星期六", "16:00", "AEDT"]],
  ["booking just after the 2 am jump, cutoff before it", "2026-10-05T02:30:00+11:00",
    ["2026 年 10 月 5 日 星期一", "02:30", "AEDT", "2026 年 10 月 4 日 星期日", "01:30", "AEST"]],
];
for (const [name, start, expected] of cases) {
  test("email time fields, " + name, () => {
    const f = emailTimeFields(start);
    assert.deepStrictEqual(Object.keys(f), TIME_KEYS);
    assert.deepStrictEqual(TIME_KEYS.map((k) => f[k]), expected);
  });
  test("email cutoff agrees with the fee rule, " + name, () => {
    const base = { service: "counselling", by: "client", kind: "cancel", paid: 150, start };
    const cut = freeDeadline(start);
    assert.strictEqual(assess({ ...base, received: cut }).outcome, "FREE_CANCEL");
    assert.strictEqual(assess({ ...base, received: new Date(cut.getTime() + 1000) }).outcome, "LATE_CANCEL");
  });
}
test("email time fields refuse a time without an offset", () => {
  assert.throws(() => emailTimeFields("2026-10-16T15:00:00"));
});
test("filling time fields leaves every status field for a person to fill", () => {
  const f = emailTimeFields("2026-10-16T15:00:00+11:00");
  const filled = templatePart.replace(/\{\{([a-z_]+)\}\}/g, (m, k) => (k in f ? f[k] : m));
  assert.ok(!/\{\{(booking_|cutoff_|timezone_)/.test(filled));
  for (const k of ["payment_status_verified_or_pending_or_unpaid", "consent_status_signed_or_pending", "policy_title_version", "policy_effective_date"])
    assert.ok(filled.includes("{{" + k + "}}"), k);
});

for (const [s, n] of results) console.log(s, n);
const failed = results.filter((r) => r[0] === "FAIL").length;
console.log("FAILURES", failed);
process.exit(failed ? 1 : 0);
