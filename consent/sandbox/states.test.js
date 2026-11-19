"use strict";
const assert = require("assert");
const { emptyRecord, apply, deriveReady, BOOKING_REF } = require("./states");

const results = [];
function test(name, fn) {
  try { fn(); results.push(["PASS", name]); }
  catch (e) { results.push(["FAIL", name + " | " + e.message]); }
}

test("booking_reference format rejects personal data", () => {
  assert.ok(BOOKING_REF.test("SSC-2026-A1B2C3"));
  assert.throws(() => emptyRecord("hugo@example.com"));
  assert.throws(() => emptyRecord("cs_live_ABC"));
});

test("payment verified does not confirm booking or consent", () => {
  let r = emptyRecord("SSC-2026-SYN001");
  r = apply(r, "payment_status", "VERIFIED", "stripe dashboard synthetic session");
  assert.strictEqual(r.booking_status, "REQUESTED");
  assert.strictEqual(r.consent_status, "NOT_SENT");
  assert.strictEqual(r.ready_for_session, false);
});

test("confirmed booking without payment is not session-ready", () => {
  let r = emptyRecord("SSC-2026-SYN002");
  r = apply(r, "booking_status", "CONFIRMED", "manual email confirmation");
  assert.strictEqual(r.payment_status, "NOT_VERIFIED");
  assert.strictEqual(r.ready_for_session, false);
});

test("draft or review consent cannot be marked signed", () => {
  let r = emptyRecord("SSC-2026-SYN003");
  r.document_version = "SSC-CONSENT-2.1-NSW-REVIEW";
  assert.throws(() => apply(r, "consent_status", "SIGNED", "sandbox"));
  r.document_version = "SSC-CONSENT-2.1-DRAFT";
  assert.throws(() => apply(r, "consent_status", "SIGNED", "sandbox"));
});

test("session ready only when all three independent gates pass", () => {
  let r = emptyRecord("SSC-2026-SYN004");
  r.session_mode = "online";
  r.document_version = "SSC-CONSENT-2.1-NSW";
  r = apply(r, "booking_status", "CONFIRMED", "manual email");
  r = apply(r, "payment_status", "VERIFIED", "stripe live receipt");
  assert.strictEqual(r.ready_for_session, false);
  r = apply(r, "consent_status", "SIGNED", "vendor audit trail + PDF");
  assert.strictEqual(r.ready_for_session, true);
  assert.strictEqual(deriveReady(r), true);
});

test("declined consent does not auto-refund or auto-cancel", () => {
  let r = emptyRecord("SSC-2026-SYN005");
  r = apply(r, "booking_status", "CONFIRMED", "manual email");
  r = apply(r, "payment_status", "VERIFIED", "stripe");
  r.document_version = "SSC-CONSENT-2.1-NSW";
  r = apply(r, "consent_status", "DECLINED", "client declined invite");
  assert.strictEqual(r.booking_status, "CONFIRMED");
  assert.strictEqual(r.payment_status, "VERIFIED");
  assert.strictEqual(r.ready_for_session, false);
});

test("expired invite is not signed", () => {
  let r = emptyRecord("SSC-2026-SYN006");
  r = apply(r, "consent_status", "SENT", "vendor invite id INV-SYN");
  r = apply(r, "consent_status", "EXPIRED", "invite TTL elapsed");
  assert.strictEqual(r.consent_status, "EXPIRED");
  assert.notStrictEqual(r.consent_status, "SIGNED");
});

test("state change without evidence is rejected", () => {
  const r = emptyRecord("SSC-2026-SYN007");
  assert.throws(() => apply(r, "booking_status", "CONFIRMED", "  "));
});

test("query flags cannot mark consent signed", () => {
  const url = "https://seesoul.com.au/consent-sign.html?signed=true";
  assert.ok(!url.includes("localStorage"));
  const r = emptyRecord("SSC-2026-SYN008");
  assert.strictEqual(r.consent_status, "NOT_SENT");
  assert.strictEqual(r.production_eligible, false);
});

test("face-to-face confirmed unpaid is not session-ready", () => {
  let r = emptyRecord("SSC-2026-SYN009");
  r.session_mode = "face-to-face";
  r = apply(r, "booking_status", "CONFIRMED", "manual email");
  assert.strictEqual(r.ready_for_session, false);
});

test("public html has no signature controls or signed localStorage", () => {
  const fs = require("fs");
  const path = require("path");
  const root = path.resolve(__dirname, "../..");
  for (const f of ["consent-counselling.html", "consent-sign.html", "nsw-code-of-conduct.html"]) {
    const html = fs.readFileSync(path.join(root, f), "utf8");
    assert.ok(!/<(input|textarea|canvas)\b/i.test(html), f);
    assert.ok(!/localStorage\.setItem/i.test(html), f);
    assert.ok(!/现在签署|立即签署/.test(html) || /没有/.test(html), f);
  }
});

for (const [s, n] of results) console.log(s, n);
const failed = results.filter((r) => r[0] === "FAIL").length;
console.log("FAILURES", failed);
process.exit(failed ? 1 : 0);
