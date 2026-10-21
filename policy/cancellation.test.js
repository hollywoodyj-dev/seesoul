"use strict";

const assert = require("assert");
const { freeDeadline, sydneyLabel, assess } = require("./cancellation");

const results = [];
function test(name, fn) {
  try { fn(); results.push(["PASS", name]); }
  catch (e) { results.push(["FAIL", name + " | " + e.message]); }
}

function sydneyOffset(iso) {
  const part = new Intl.DateTimeFormat("en-AU", { timeZone: "Australia/Sydney", timeZoneName: "longOffset" })
    .formatToParts(new Date(iso)).find((p) => p.type === "timeZoneName").value;
  return part.replace("GMT", "");
}

const base = { service: "counselling", by: "client", kind: "cancel", paid: 150 };

// Friday 16 Oct 2026, 3:00 pm AEDT
const FRI = "2026-10-16T15:00:00+11:00";

test("deadline is Thursday 3:00 pm Sydney", () => {
  assert.strictEqual(freeDeadline(FRI).toISOString(), "2026-10-15T04:00:00.000Z");
  assert.strictEqual(sydneyLabel(freeDeadline(FRI)), "2026 年 10 月 15 日 星期四 15:00 AEDT（悉尼时间）");
});
test("notice exactly at deadline is free", () => {
  const r = assess({ ...base, start: FRI, received: "2026-10-15T15:00:00+11:00" });
  assert.strictEqual(r.outcome, "FREE_CANCEL"); assert.strictEqual(r.refund, 150); assert.strictEqual(r.fee, 0);
});
test("one second after deadline is late", () => {
  const r = assess({ ...base, start: FRI, received: "2026-10-15T15:00:01+11:00" });
  assert.strictEqual(r.outcome, "LATE_CANCEL"); assert.strictEqual(r.fee, 75); assert.strictEqual(r.refund, 75);
});
test("one second before deadline is free", () => {
  assert.strictEqual(assess({ ...base, start: FRI, received: "2026-10-15T14:59:59+11:00" }).outcome, "FREE_CANCEL");
});
test("same notice written in UTC gives the same result", () => {
  assert.strictEqual(assess({ ...base, start: FRI, received: "2026-10-15T04:00:00Z" }).outcome, "FREE_CANCEL");
});
test("free reschedule moves the payment to the new time", () => {
  const r = assess({ ...base, kind: "reschedule", start: FRI, received: "2026-10-14T10:00:00+11:00" });
  assert.strictEqual(r.outcome, "FREE_RESCHEDULE"); assert.strictEqual(r.credit, 150); assert.strictEqual(r.refund, 0);
});
test("late cancel without payment owes AUD 75", () => {
  const r = assess({ ...base, paid: 0, start: FRI, received: "2026-10-16T09:00:00+11:00" });
  assert.strictEqual(r.amountDue, 75); assert.strictEqual(r.refund, 0);
});
test("late reschedule is treated as late", () => {
  assert.strictEqual(assess({ ...base, kind: "reschedule", start: FRI, received: "2026-10-16T09:00:00+11:00" }).outcome, "LATE_CANCEL");
});
const END = "2026-10-16T16:00:00+11:00";
const slot = { ...base, kind: "attendance", start: FRI, end: END };

test("no-show after the whole slot ends charges AUD 75 and refunds AUD 75", () => {
  const r = assess({ ...slot, assessedAt: END });
  assert.strictEqual(r.outcome, "NO_SHOW"); assert.strictEqual(r.fee, 75); assert.strictEqual(r.refund, 75);
});
test("no-show unpaid owes AUD 75", () => {
  assert.strictEqual(assess({ ...slot, paid: 0, assessedAt: END }).amountDue, 75);
});
test("no judgement while the slot has not ended, even after 59 minutes", () => {
  const r = assess({ ...slot, assessedAt: "2026-10-16T15:59:00+11:00" });
  assert.strictEqual(r.outcome, "SLOT_NOT_ENDED"); assert.strictEqual(r.fee, null);
});
test("on-time attendance has no fee and ends at the original time", () => {
  const r = assess({ ...slot, arrived: FRI, assessedAt: END });
  assert.strictEqual(r.outcome, "ATTENDED"); assert.strictEqual(r.late, false); assert.strictEqual(r.endsAt.toISOString(), "2026-10-16T05:00:00.000Z");
});
test("late arrival is not a no-show, online or face-to-face", () => {
  for (const mode of ["online", "face-to-face"]) {
    const r = assess({ ...slot, mode, arrived: "2026-10-16T15:20:00+11:00", assessedAt: END });
    assert.strictEqual(r.outcome, "ATTENDED"); assert.strictEqual(r.late, true); assert.strictEqual(r.fee, 0);
    assert.strictEqual(r.endsAt.toISOString(), "2026-10-16T05:00:00.000Z");
  }
});
test("arriving one minute before the end still counts as attended", () => {
  assert.strictEqual(assess({ ...slot, arrived: "2026-10-16T15:59:00+11:00", assessedAt: END }).outcome, "ATTENDED");
});
test("arriving exactly at the end is not attendance", () => {
  assert.strictEqual(assess({ ...slot, arrived: END, assessedAt: END }).outcome, "NO_SHOW");
});
test("no-show with emergency or technical failure goes to review", () => {
  const r = assess({ ...slot, emergency: true, assessedAt: END });
  assert.strictEqual(r.outcome, "NO_SHOW_REVIEW"); assert.strictEqual(r.fee, null);
});
test("cancel notice received after start falls under attendance, not late cancel", () => {
  const r = assess({ ...base, start: FRI, end: END, received: "2026-10-16T15:10:00+11:00", assessedAt: END });
  assert.strictEqual(r.outcome, "NO_SHOW");
});
test("emergency goes to review, no automatic fee", () => {
  const r = assess({ ...base, emergency: true, start: FRI, received: "2026-10-16T09:00:00+11:00" });
  assert.strictEqual(r.outcome, "LATE_CANCEL_REVIEW"); assert.strictEqual(r.fee, null);
});
test("SeeSoul cancellation gives full refund or free reschedule", () => {
  const r = assess({ ...base, by: "seesoul", start: FRI, received: "2026-10-16T14:00:00+11:00" });
  assert.strictEqual(r.outcome, "PROVIDER_CANCEL"); assert.strictEqual(r.refund, 150); assert.deepStrictEqual(r.clientChooses, ["reschedule", "full-refund"]);
});
test("life theme is not covered by the AUD 75 rule", () => {
  const r = assess({ ...base, service: "life-theme", paid: 100, start: FRI, received: "2026-10-16T09:00:00+11:00" });
  assert.strictEqual(r.outcome, "NOT_COVERED"); assert.strictEqual(r.fee, 0);
});
test("timestamp without offset is rejected", () => {
  assert.throws(() => assess({ ...base, start: "2026-10-16T15:00:00", received: "2026-10-15T15:00:00" }));
});

// Daylight saving starts Sunday 4 Oct 2026, 2:00 am AEST -> 3:00 am AEDT
test("DST start dates are what the tests assume", () => {
  assert.strictEqual(sydneyOffset("2026-10-03T04:00:00Z"), "+10:00");
  assert.strictEqual(sydneyOffset("2026-10-04T04:00:00Z"), "+11:00");
});
const DST_START_APPT = "2026-10-04T15:00:00+11:00";
test("DST start: deadline is exactly 24 h earlier, Saturday 2:00 pm AEST", () => {
  assert.strictEqual(freeDeadline(DST_START_APPT).toISOString(), "2026-10-03T04:00:00.000Z");
  assert.strictEqual(sydneyLabel(freeDeadline(DST_START_APPT)), "2026 年 10 月 3 日 星期六 14:00 AEST（悉尼时间）");
  assert.strictEqual(sydneyLabel(DST_START_APPT), "2026 年 10 月 4 日 星期日 15:00 AEDT（悉尼时间）");
});
test("DST start: Saturday 2:30 pm AEST is late under the 24 h rule", () => {
  assert.strictEqual(assess({ ...base, start: DST_START_APPT, received: "2026-10-03T14:30:00+10:00" }).outcome, "LATE_CANCEL");
});

// Daylight saving ends Sunday 4 Apr 2027, 3:00 am AEDT -> 2:00 am AEST
test("DST end dates are what the tests assume", () => {
  assert.strictEqual(sydneyOffset("2027-04-03T05:00:00Z"), "+11:00");
  assert.strictEqual(sydneyOffset("2027-04-04T05:00:00Z"), "+10:00");
});
const DST_END_APPT = "2027-04-04T15:00:00+10:00";
test("DST end: deadline is exactly 24 h earlier, Saturday 4:00 pm AEDT", () => {
  assert.strictEqual(freeDeadline(DST_END_APPT).toISOString(), "2027-04-03T05:00:00.000Z");
  assert.strictEqual(sydneyLabel(freeDeadline(DST_END_APPT)), "2027 年 4 月 3 日 星期六 16:00 AEDT（悉尼时间）");
  assert.strictEqual(sydneyLabel(DST_END_APPT), "2027 年 4 月 4 日 星期日 15:00 AEST（悉尼时间）");
});
test("DST start: notice exactly at the deadline is free", () => {
  assert.strictEqual(assess({ ...base, start: DST_START_APPT, received: "2026-10-03T14:00:00+10:00" }).outcome, "FREE_CANCEL");
});
test("DST end: notice exactly at the deadline is free", () => {
  assert.strictEqual(assess({ ...base, start: DST_END_APPT, received: "2027-04-03T16:00:00+11:00" }).outcome, "FREE_CANCEL");
});
test("DST end: Saturday 3:30 pm AEDT is still free under the 24 h rule", () => {
  assert.strictEqual(assess({ ...base, start: DST_END_APPT, received: "2027-04-03T15:30:00+11:00" }).outcome, "FREE_CANCEL");
});

for (const [s, n] of results) console.log(s, n);
const failed = results.filter((r) => r[0] === "FAIL").length;
console.log("FAILURES", failed);
process.exit(failed ? 1 : 0);
