"use strict";

const FEE = 150;
const LATE_FEE = 75;
const NOTICE_MS = 24 * 60 * 60 * 1000;
const TZ = "Australia/Sydney";

function toInstant(value) {
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) throw new Error("invalid timestamp: " + value);
  if (typeof value === "string" && !/(Z|[+-]\d\d:\d\d)$/.test(value)) {
    throw new Error("timestamp needs an explicit offset: " + value);
  }
  return d;
}

function freeDeadline(start) {
  return new Date(toInstant(start).getTime() - NOTICE_MS);
}

function sydneyZone(instant) {
  const offset = new Intl.DateTimeFormat("en-AU", { timeZone: TZ, timeZoneName: "longOffset" })
    .formatToParts(toInstant(instant)).find((p) => p.type === "timeZoneName").value;
  if (offset === "GMT+11:00") return "AEDT";
  if (offset === "GMT+10:00") return "AEST";
  throw new Error("unexpected Sydney offset: " + offset);
}

function sydneyLabel(instant) {
  const d = toInstant(instant);
  const p = {};
  new Intl.DateTimeFormat("zh-CN", {
    timeZone: TZ, year: "numeric", month: "numeric", day: "numeric", weekday: "long",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(d).forEach((x) => { p[x.type] = x.value; });
  return p.year + " 年 " + p.month + " 月 " + p.day + " 日 " + p.weekday + " " + p.hour + ":" + p.minute + " " + sydneyZone(d) + "（悉尼时间）";
}

function sydneyParts(instant) {
  const p = {};
  new Intl.DateTimeFormat("zh-CN", {
    timeZone: TZ, year: "numeric", month: "numeric", day: "numeric", weekday: "long",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(toInstant(instant)).forEach((x) => { p[x.type] = x.value; });
  return {
    date: p.year + " 年 " + p.month + " 月 " + p.day + " 日 " + p.weekday,
    time: p.hour + ":" + p.minute,
    zone: sydneyZone(instant),
  };
}

// Fills only the time placeholders of policy/confirmation-email-draft.md; every status field stays manual.
function emailTimeFields(start) {
  const booking = sydneyParts(start);
  const cutoff = sydneyParts(freeDeadline(start));
  return {
    booking_date: booking.date,
    booking_time: booking.time,
    timezone_abbr: booking.zone,
    cutoff_date: cutoff.date,
    cutoff_time: cutoff.time,
    cutoff_timezone_abbr: cutoff.zone,
  };
}

/*
 * request: {
 *   service: "counselling" | "life-theme",
 *   start, end,               // the booked slot; ISO strings with offset, or Date
 *   received,                 // when SeeSoul received a cancel / reschedule notice
 *   arrived,                  // when the client arrived or joined the video call, if at all
 *   assessedAt,               // when attendance is being judged
 *   by: "client" | "seesoul",
 *   kind: "cancel" | "reschedule" | "attendance",
 *   paid: number,             // AUD already paid
 *   emergency: boolean,       // illness, emergency or technical failure; always goes to review
 * }
 *
 * A no-show exists only once the whole slot has ended with no attendance and no
 * cancellation received before the start. Lateness alone never makes a no-show.
 */
function attendance(request, start, paid) {
  const end = toInstant(request.end);
  if (request.arrived && toInstant(request.arrived) < end) {
    return { outcome: "ATTENDED", late: toInstant(request.arrived) > start, fee: 0, refund: 0, credit: 0, amountDue: 0, endsAt: end };
  }
  if (!request.assessedAt || toInstant(request.assessedAt) < end) {
    return { outcome: "SLOT_NOT_ENDED", fee: null, refund: null, credit: null, amountDue: null };
  }
  if (request.emergency) {
    return { outcome: "NO_SHOW_REVIEW", fee: null, refund: null, credit: null, amountDue: null, discretionary: true };
  }
  return { outcome: "NO_SHOW", fee: LATE_FEE, refund: Math.max(paid - LATE_FEE, 0), credit: 0, amountDue: Math.max(LATE_FEE - paid, 0) };
}

function assess(request) {
  const paid = request.paid || 0;
  if (request.service !== "counselling") {
    return { outcome: "NOT_COVERED", fee: 0, refund: 0, credit: 0, amountDue: 0 };
  }
  if (request.by === "seesoul") {
    return { outcome: "PROVIDER_CANCEL", fee: 0, refund: paid, credit: paid, amountDue: 0, clientChooses: ["reschedule", "full-refund"] };
  }

  const start = toInstant(request.start);
  const deadline = freeDeadline(start);

  if (request.kind === "attendance" || !request.received || toInstant(request.received) >= start) {
    return attendance(request, start, paid);
  }

  if (toInstant(request.received) <= deadline) {
    if (request.kind === "reschedule") return { outcome: "FREE_RESCHEDULE", fee: 0, refund: 0, credit: paid, amountDue: 0, deadline };
    return { outcome: "FREE_CANCEL", fee: 0, refund: paid, credit: 0, amountDue: 0, deadline };
  }

  if (request.emergency) {
    return { outcome: "LATE_CANCEL_REVIEW", fee: null, refund: null, credit: null, amountDue: null, deadline, discretionary: true };
  }
  return {
    outcome: "LATE_CANCEL",
    fee: LATE_FEE,
    refund: Math.max(paid - LATE_FEE, 0),
    credit: 0,
    amountDue: Math.max(LATE_FEE - paid, 0),
    deadline,
  };
}

module.exports = { FEE, LATE_FEE, TZ, freeDeadline, sydneyZone, sydneyLabel, emailTimeFields, assess };
