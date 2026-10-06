# -*- coding: utf-8 -*-
"""Compass result for the website.

The mode (R0–R3) is decided here by compass_engine. A model, when fully
configured, may only phrase the mirror. With no credential the bounded
composer in demo_llm.py is used. No key is read from a file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compass_engine import (  # noqa: E402
    assess_safety,
    audit_output,
    build_evidence,
    compose_llm as engine_r0,
    route,
    safe_fallback,
    sufficiency,
)
from demo_llm import compose_llm as bounded_compose  # noqa: E402
from sandbox_real_llm import call_llm, load_explicit_config  # noqa: E402

UI_STEP = {
    "1": "reality",
    "2": "feeling",
    "3": "body",
    "4": "thought",
    "5": "impulse",
    "6": "protection",
    "7": "awareness",
    "reality": "reality",
    "feeling": "feeling",
    "body": "body",
    "thought": "thought",
    "impulse": "impulse",
    "protection": "protection",
    "awareness": "awareness",
}

_MAX_FREE = 2000


def _clip(text: str) -> str:
    text = (text or "").strip()
    return text[:_MAX_FREE]


def _field_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, dict):
        inner = value.get("text")
        if isinstance(inner, str) and inner.strip():
            return inner.strip()
    return None


def _public(composed: dict, mode: str, router: str, safety: str, source: str, audit: str) -> dict:
    return {
        "ok": True,
        "source": source,
        "reflection_mode": mode,
        "mirror": composed.get("mirror") or "",
        "bounded_reflection": composed.get("bounded_reflection"),
        "discovery_question": composed.get("discovery_question"),
        "small_movement": composed.get("small_movement"),
        "router": router,
        "safety": safety,
        "audit": audit,
    }


def _prompt_step(step_name: str) -> str:
    # Q6 stays an anticipated concern. Do not send the internal name "protection".
    if step_name == "protection":
        return "anticipated_concern"
    return step_name


def _prompt(eo, suff) -> str:
    steps = [
        {"step": _prompt_step(s.step), "words": s.raw_label}
        for s in eo.steps
    ]
    return (
        "The reflection mode is already decided. Do not change it. "
        "Do not diagnose, name a disorder, assign a personality label, "
        "state a life-theme conclusion, recommend a service, or mention price. "
        "Use only the evidence below. Respond with one JSON object and nothing else.\n"
        "Schema: {"
        '"reflection_mode":"R0|R1|R2|R3",'
        '"mirror":{"text":"..."},'
        '"bounded_reflection":{"text":"..."} or null,'
        '"discovery_question":{"text":"..."} or null,'
        '"small_movement":{"text":"..."} or null'
        "}\n"
        "R0 and R1 must set bounded_reflection to null. "
        "R2 may offer one bounded reflection that stays inside the evidence. "
        "R3 must keep more than one reading open and must not choose for the person.\n"
        f"reflection_mode={suff.mode}\n"
        f"selected={steps}\n"
        f"free_text={eo.free_text.raw}\n"
    )


def _from_model(payload: dict, suff) -> dict | None:
    if payload.get("reflection_mode") != suff.mode:
        return None
    mirror = _field_text(payload.get("mirror"))
    if not mirror:
        return None
    bounded = payload.get("bounded_reflection")
    if suff.mode in ("R0", "R1"):
        bounded_text = None
    else:
        bounded_text = _field_text(bounded) if bounded is not None else None
    return {
        "mirror": mirror,
        "bounded_reflection": bounded_text,
        "discovery_question": _field_text(payload.get("discovery_question")),
        "small_movement": _field_text(payload.get("small_movement")),
        "sentence_provenance": [{"sentence": mirror[:24], "provenance": "model_phrase"}],
        "system_offered_claims": [bounded_text] if bounded_text else ["mirror phrasing"],
        "safety_override": suff.safety_signals == "CRITICAL",
    }


def _bounded(eo, suff) -> dict:
    if suff.safety_signals == "CRITICAL":
        return engine_r0(eo, suff, suff.mode)
    return bounded_compose(eo, suff, suff.mode)


def _clarify_hold() -> dict:
    return {
        "ok": True,
        "source": "safety_gate",
        "reflection_mode": None,
        "mirror": "",
        "bounded_reflection": None,
        "discovery_question": None,
        "small_movement": None,
        "router": "NO_COMMERCIAL_CTA",
        "safety": "CLARIFY",
        "audit": "HELD",
    }


def reflect(answers: dict | None, free_text: str = "", safety_confirmation: str | None = None) -> dict:
    # CLARIFY RESPONSE IS SAFETY EVIDENCE ONLY. IT MUST NOT BECOME REFLECTION EVIDENCE.
    if safety_confirmation not in ("needs_help", "safe_now"):
        safety_confirmation = None
    step_codes = {}
    for key, value in (answers or {}).items():
        step = UI_STEP.get(str(key))
        if step and isinstance(value, str) and value.strip():
            step_codes[step] = value.strip()
    free_text = _clip(free_text if isinstance(free_text, str) else "")
    if not step_codes and not free_text and safety_confirmation is None:
        return {"ok": False, "status": "EMPTY_INPUT"}

    eo = build_evidence("web", step_codes, free_text)
    signal = assess_safety(eo)
    if signal != "CRITICAL" and safety_confirmation == "needs_help":
        signal = "CRITICAL"
    elif signal == "CLARIFY" and safety_confirmation == "safe_now":
        signal = "NONE"
    elif signal == "CLARIFY":
        return _clarify_hold()

    # R3 = SPECIFIED / NOT PRODUCTION-REACHABLE. Do not enable it here.
    suff = sufficiency(eo, multi_interpretation=False)
    if signal == "CRITICAL":
        suff.safety_signals = "CRITICAL"
        suff.mode = "R0"
    elif signal == "NONE":
        suff.safety_signals = "NONE"
    source = "bounded"
    composed = _bounded(eo, suff)

    if suff.safety_signals != "CRITICAL":
        cfg = load_explicit_config()
        if cfg.configured:
            result = call_llm(cfg, _prompt(eo, suff))
            mapped = _from_model(result.payload, suff) if result.ok and result.payload else None
            if mapped is None:
                logger_status = result.status if not result.ok else "MAP_REJECTED"
            else:
                model_audit = audit_output(mapped, eo, suff)
                failed = [k for k, v in model_audit["checks"].items() if v == "FAIL"]
                logger_status = "OK" if model_audit["overall"] == "PASS" else ("AUDIT_FAIL:" + ",".join(failed))
                if model_audit["overall"] == "PASS":
                    composed = mapped
                    source = "llm"
            print("LLM_STATUS " + logger_status, flush=True)

    audit = audit_output(composed, eo, suff)
    failed = [k for k, v in audit["checks"].items() if v == "FAIL"]
    if failed == ["question_hygiene"]:
        composed["discovery_question"] = "如果此刻要给这股感觉一个名字，你会怎么叫它？"
        audit = audit_output(composed, eo, suff)
    if audit["overall"] != "PASS":
        if suff.safety_signals == "CRITICAL":
            composed = engine_r0(eo, suff, suff.mode)
            source = "safety_gate"
            audit = {"overall": "R0_HELD"}
        else:
            composed = safe_fallback(suff.mode)
            source = "fallback"
            audit = {"overall": "FALLBACK"}

    router_decision = "NO_COMMERCIAL_CTA" if suff.safety_signals == "CRITICAL" else route(suff, eo)
    return _public(composed, suff.mode, router_decision, suff.safety_signals, source, audit["overall"])
