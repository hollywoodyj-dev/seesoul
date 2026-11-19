"use strict";
/**
 * SeeSoul Consent & E-Signature — local sandbox state machine.
 * REVIEW / LOCAL PLANNING ONLY. No vendor API, no real client data, no production store.
 */
const BOOKING = ["REQUESTED", "CONFIRMED", "RESCHEDULED", "CANCELLED"];
const PAYMENT = ["NOT_VERIFIED", "VERIFIED", "REFUND_PENDING", "REFUNDED"];
const CONSENT = ["NOT_SENT", "SENT", "VIEWED", "SIGNED", "DECLINED", "EXPIRED", "SUPERSEDED"];

const BOOKING_REF = /^SSC-\d{4}-[A-Z0-9]{6}$/;

function emptyRecord(booking_reference) {
  if (!BOOKING_REF.test(booking_reference)) throw new Error("invalid booking_reference");
  return {
    booking_reference,
    booking_status: "REQUESTED",
    payment_status: "NOT_VERIFIED",
    consent_status: "NOT_SENT",
    document_version: null,
    session_mode: null,
    ready_for_session: false,
    production_eligible: false,
  };
}

function deriveReady(record) {
  return record.booking_status === "CONFIRMED"
    && record.payment_status === "VERIFIED"
    && record.consent_status === "SIGNED";
}

function apply(record, field, next, evidence) {
  const allowed = field === "booking_status" ? BOOKING
    : field === "payment_status" ? PAYMENT
      : field === "consent_status" ? CONSENT : null;
  if (!allowed) throw new Error("unknown field");
  if (!allowed.includes(next)) throw new Error("invalid state: " + next);
  if (!evidence || typeof evidence !== "string" || !evidence.trim()) {
    throw new Error("state changes require an evidence note");
  }
  const out = { ...record, [field]: next };
  if (field === "consent_status" && next === "SIGNED") {
    if (!out.document_version) throw new Error("SIGNED requires a locked document_version");
    const ver = String(out.document_version);
    if (ver.includes("DRAFT") || ver.includes("REVIEW")) {
      throw new Error("DRAFT or REVIEW documents cannot be marked SIGNED");
    }
  }
  out.ready_for_session = deriveReady(out);
  out.production_eligible = false;
  return out;
}

function assertIndependent(record) {
  if (record.payment_status === "VERIFIED" && record.booking_status === "REQUESTED") return true;
  if (record.booking_status === "CONFIRMED" && record.payment_status === "NOT_VERIFIED") return true;
  if (record.consent_status !== "SIGNED" && record.payment_status === "VERIFIED") return true;
  return true;
}

module.exports = {
  BOOKING, PAYMENT, CONSENT, BOOKING_REF,
  emptyRecord, apply, deriveReady, assertIndependent,
};
