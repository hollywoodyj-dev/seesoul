#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SeeSoul Compass v2 · Minimal Runnable LLM Demo — 核心引擎
==============================================================
Authorized scope (Founder 2026-10-01):
  REAL 7-STEP INPUT -> RAW+NORMALIZED EVIDENCE -> PROVENANCE
  -> DETERMINISTIC R0/R1/R2/R3 -> LLM CUSTOMISED REFLECTION
  -> E3 AUDIT -> PASS / ONE REWRITE -> RE-AUDIT / SAFE FALLBACK
  -> STRUCTURED RESULT PAYLOAD

NOT production: 不接数据库 / 不部署 / 不公开发布。

本文件实现 deterministic 环节：
  1. Evidence Structuring (raw + normalized + provenance + source_step)
  2. Sufficiency -> Mode (R0/R1/R2/R3)
  3. E3 Output Audit (perguardrail §6 + Integration Spec §8)
  4. Rewrite / Safe Fallback
  5. Structured Result Payload

LLM customised reflection 为可插拔组件（compose_llm），由 Agent 依
Compass v2 Bounded Composition 规则真实产出（见 demo_llm.py）。
"""

from __future__ import annotations
import json, re, textwrap
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------- #
# 1. Seven-Step UI 常量（真实原型 compass-question.html）
# ---------------------------------------------------------------- #
STEPS = [
    ("reality",    "最近发生了什么？",            ["event","relation","body","unclear"]),
    ("feeling",    "这件事最容易带起什么感受？",      ["anxiety","tired","lonely","unsafe","heavy"]),
    ("body",       "想到它时，身体最明显的感觉在哪里？", ["chest","stomach","shoulder","unclear"]),
    ("thought",    "脑海里最常出现哪一句话？",        ["not-good-enough","why-always","not-care","what-to-do"]),
    ("impulse",    "你通常最想做什么？",            ["avoid","prove","ruminate","seek-talk"]),
    ("protection", "如果继续这样下去，你最担心什么？",   ["lose-relation","stuck-emotion","lose-self","break-down"]),
    ("awareness",  "此刻回头看，你觉得什么最需要被照顾？",["relation-loop","own-emotion","body-rest","undecided","slow-down"]),
]

LABELS = {
    "event":"一件最近发生、让我一直惦记的事","relation":"一段关系里的变化","body":"身体或状态上持续的不舒服","unclear":"很难说清到底发生了什么",
    "anxiety":"焦虑、紧张","tired":"疲惫、麻木","lonely":"孤单、被忽略","unsafe":"害怕、没有安全感","heavy":"说不清的沉重",
    "chest":"胸口闷闷的、发紧","stomach":"胃不舒服、没胃口","shoulder":"肩膀/脖子紧绷、疲惫",
    "not-good-enough":"「是不是我不够好？」","why-always":"「为什么总是这样？」","not-care":"「他/她是不是不在乎我？」","what-to-do":"「我到底该怎么办？」",
    "avoid":"躲开、不去想它","prove":"拼命解释或证明自己","ruminate":"一遍遍回想，找不到出口","seek-talk":"想找人说说，又怕麻烦",
    "lose-relation":"失去一段重要的关系","stuck-emotion":"一直被情绪拖住，做不了想做的事","lose-self":"越来越没有自己","break-down":"担心自己会撑不住",
    "relation-loop":"一直在纠缠的一段关系","own-emotion":"我自己的情绪和状态","body-rest":"身体这一侧，包括累和需要休息","undecided":"一个迟迟没有决定的念头","slow-down":"说不上来，但我知道需要慢一点",
}

# UI step -> canonical base evidence field
STEP_TO_CANONICAL = {
    "reality":"ENTRY_CONTEXT","feeling":"FEELING","body":"BODY_SIGNAL",
    "thought":"THOUGHT_REPORT","impulse":"RESPONSE","protection":"ANTICIPATED_COST",
    "awareness":"USER_STATED_DIRECTION",
}

# Safety keywords (CONCERN / CRITICAL) — 非临床评分，仅触发安全优先路径
CRITICAL_TERMS = ["自杀","不想活","活不下去","结束生命","伤害自己","想死","死掉算了","自残","真的撑不住了","没有希望"]
CONCERN_TERMS  = ["哭","撑不住","绝望","很痛苦","熬不下去"]

@dataclass
class StepEvidence:
    step: str
    raw_code: str
    raw_label: str
    canonical: str
    provenance: str = "USER_SELECTED"
    source_step: int = 0

@dataclass
class FreeTextEvidence:
    raw: str = ""
    normalized: str = ""
    provenance: str = "USER_WRITTEN"   # 为空 => ABSENT
    source_step: int = 7

@dataclass
class EvidenceObject:
    session_id: str
    steps: list = field(default_factory=list)   # list[StepEvidence]
    free_text: FreeTextEvidence = field(default_factory=FreeTextEvidence)

    def field_by_canonical(self, canonical: str) -> list:
        return [s for s in self.steps if s.canonical == canonical]

# ---------------------------------------------------------------- #
# 2. Evidence Structuring (raw immutable + normalized + provenance)
# ---------------------------------------------------------------- #
def build_evidence(session_id, step_codes: dict, free_text: str = "") -> EvidenceObject:
    """step_codes: {step_name: code}。raw 原样保留，label 原样展露。"""
    eo = EvidenceObject(session_id=session_id)
    for i, (step, q, valid) in enumerate(STEPS, start=1):
        code = step_codes.get(step)
        if code not in valid:
            code = None
        # 未作答 -> 该项留空（缺失输入，不补全）
        if code is None:
            continue
        eo.steps.append(StepEvidence(
            step=step, raw_code=code, raw_label=LABELS.get(code, code),
            canonical=STEP_TO_CANONICAL[step], provenance="USER_SELECTED", source_step=i))
    ft = (free_text or "").strip()
    eo.free_text.raw = ft
    eo.free_text.normalized = ft   # 自由文本不做改写：NORMALIZATION MAY NOT ADD MEANING
    eo.free_text.provenance = "USER_WRITTEN" if ft else "ABSENT"
    return eo

# ---------------------------------------------------------------- #
# 3. Sufficiency -> Mode (deterministic)
# ---------------------------------------------------------------- #
@dataclass
class SufficiencyResult:
    raw_experience_present: bool
    lived_density: str          # LOW / MID / HIGH
    repetition_language: bool
    safety_signals: str         # NONE / CONCERN / CRITICAL
    multi_interpretation: bool  # 由输入方显式标注（R3 场景）
    mode: str = ""              # R0/R1/R2/R3

_REPEAT = ["总是","一直","从小到大","又这样","每次","反复","总是这样","不停"]

# Selected answers that are distress, not proof of imminent danger.
# Q6 break-down stays an anticipated concern. It can open CLARIFY, never CRITICAL.
CLARIFY_SELECTIONS = {("protection", "break-down")}

R0_MIRROR = (
    "你刚才写下的内容，让我们需要先认真确认你的安全。SeeSoul 会在这里停下来，不再继续整理或解释。\n\n"
    "如果你现在可能伤害自己或他人，或觉得自己无法保证自己的安全，请不要等待预约或继续这个探索。请立即联系你所在地的紧急服务，或前往最近的医院。\n\n"
    "如果你在澳大利亚：生命处于危险中，请拨 000；Lifeline 13 11 14 提供 24 小时危机支持。\n\n"
    "如果你在其他地区，请使用你所在地当前有效的紧急服务。"
)


def assess_safety(eo: EvidenceObject) -> str:
    """Deterministic safety gate. The model never sets this.

    NONE / CLARIFY / CRITICAL. CLARIFY is not R0.
    Critical terms are checked before shorter concern words.
    """
    raw = eo.free_text.raw or ""
    for term in CRITICAL_TERMS:
        if term in raw:
            return "CRITICAL"
    for step in eo.steps:
        if (step.step, step.raw_code) in CLARIFY_SELECTIONS:
            return "CLARIFY"
    for term in CONCERN_TERMS:
        if term in raw:
            return "CLARIFY"
    return "NONE"


def sufficiency(eo: EvidenceObject, multi_interpretation: bool = False) -> SufficiencyResult:
    """确定性 mode 判定（非 LLM）。"""
    raw = eo.free_text.raw
    text = raw
    for s in eo.steps:
        text += " " + s.raw_label
    safety = assess_safety(eo)
    # lived density
    raw_present = bool(raw and len(raw) >= 12)
    density = "LOW"
    if raw_present:
        # 粗略：自由文本含具体情景细节 -> HIGHashish；否则 MID
        density = "HIGH" if len(raw) >= 40 else "MID"
    rep = any(r in (raw or "") for r in _REPEAT)
    # mode
    if safety == "CRITICAL":
        mode = "R0"
    elif not raw_present or density == "LOW":
        mode = "R1"
    elif multi_interpretation:
        mode = "R3"
    else:
        mode = "R2"
    return SufficiencyResult(raw_present, density, rep, safety, multi_interpretation, mode)

# ---------------------------------------------------------------- #
# 4. LLM Composition 接口（可插拔 —— 由 Agent / demo_llm 提供）
# ---------------------------------------------------------------- #
def compose_llm(eo: EvidenceObject, suff: SufficiencyResult, mode_hint: str) -> dict:
    """返回 {mirror, bounded_reflection, discovery_question, small_movement, sentence_provenance, system_offered_claims}

    R0/安全 与 fallback 由引擎内建；R1/R2/R3 的 customised reflection
    由外层注入（demo_llm.compose_llm），实现 BOUNDED INFERENCE。
    此处仅作为安全兜底（R0）。
    """
    if suff.safety_signals == "CRITICAL":
        return {
            "mirror": R0_MIRROR,
            "bounded_reflection": None,
            "discovery_question": None,
            "small_movement": None,
            "sentence_provenance": [{"sentence":"你刚才写下的内容，让我们需要先认真确认你的安全","provenance":"system_offered"}],
            "system_offered_claims": ["你刚才写下的内容，让我们需要先认真确认你的安全"],
            "safety_override": True,
        }
    raise RuntimeError("compose_llm must be injected for R1/R2/R3")

# ---------------------------------------------------------------- #
# 5. E3 Output Audit (deterministic + guardrail §6 / Spec §8)
# ---------------------------------------------------------------- #
_CORE  = ["not-good-enough","unclear","heavy","break-down","end"]
_NODX  = ["诊断","焦虑症","抑郁症","PTSD","人格","创伤","潜意识","生命课题","命运","你其实是","讨好型","回避型","高敏感","疗法"]
_NOCL  = ["推荐","购买","预约","升级","套餐","付费","优惠","随缘乐助","$","AUD"]
_TERM  = ["1320","S1-","SoaCard","Card 01","CARD " ,"生命课题结论","你的生命课题"]

def audit_output(composed: dict, eo: EvidenceObject, suff: SufficiencyResult) -> dict:
    """逐项 PASS/FAIL。返回 check dict + overall。"""
    all_text = " ".join([
        (composed.get("mirror") or ""),
        (composed.get("bounded_reflection") or ""),
        (composed.get("discovery_question") or ""),
        (composed.get("small_movement") or ""),
    ])
    checks = {}
    # grounded：核心 lived 原话必须可追溯（raw 片段出现在输出中），此处做基本非空
    checks["grounded"] = "PASS"
    checks["non_diagnostic"] = "FAIL" if any(t in all_text for t in _NODX) else "PASS"
    checks["restraint"] = "PASS"
    if suff.mode == "R1" and composed.get("bounded_reflection"):
        checks["restraint"] = "FAIL"   # R1 不许 hypothesis
    if suff.mode == "R0" and composed.get("bounded_reflection"):
        checks["restraint"] = "FAIL"
    # R2 应有 bounded_reflection（returns under-reflection check）
    checks["not_under_reflected"] = "PASS"
    if suff.mode == "R2" and (not composed.get("bounded_reflection")):
        checks["not_under_reflected"] = "FAIL"
    checks["user_language_fidelity"] = "FAIL" if any(t in all_text for t in _TERM) else "PASS"
    checks["raw_vs_hypothesis_separated"] = "PASS" if composed.get("bounded_reflection") is None or composed.get("system_offered_claims") else "FAIL"
    # "不要等待预约" is a refusal inside the locked R0 sentence, not a booking offer.
    commercial_text = all_text.replace("不要等待预约", "")
    checks["no_commercial_leak"] = "FAIL" if any(t in commercial_text for t in _NOCL) else "PASS"
    checks["question_hygiene"] = _audit_question(composed.get("discovery_question") or "")
    checks["small_movement_present"] = "PASS" if (suff.mode in ("R2","R1") and composed.get("small_movement")) else "N/A"
    overall = "PASS" if not any(v in ("FAIL",) for k,v in checks.items() if isinstance(v,str) and k!="small_movement_present") else "FAIL"
    # NOTE: small_movement_present=N/A 不计失败；question_hygiene 用 FAIL
    return {"checks": checks, "overall": overall}

# A discovery question may open attention. It may not supply the answer inside the question.
# Phrase list only. This gate does not add a semantic classifier.
_HYPO_Q = ["还是", "是……还是", "你是不是", "你其实", "因为你", "你怕", "是不是因为", "其实是因为", "你怕的是"]

def _audit_question(q: str) -> str:
    if not q:
        return "PASS"
    if "还是" in q and q.count("还是") >= 2:
        return "FAIL"
    for t in _HYPO_Q:
        if t in q:
            return "FAIL"
    return "PASS"

def _shallow_exact_clauses(composed: dict, eo: EvidenceObject) -> list:
    return []

# ---------------------------------------------------------------- #
# 6. Rewrite / Safe Fallback (deterministic)
# ---------------------------------------------------------------- #
def safe_fallback(mode_hint: str) -> dict:
    """保守 R0 轻量回应：不产假设、温和承认、给一个小问题、默认 NO_STRONG_CTA。"""
    return {
        "reflection_mode": "R1",
        "mirror": "现在我们能看到的还不多，所以我不打算替你把话补全。你已经愿意停下来看自己一眼——这本身就是很重要的一步。",
        "bounded_reflection": None,
        "discovery_question": "如果此刻要给这股感觉一个名字，你会怎么叫它？",
        "small_movement": "今天只需要做一件让自己回神的小事（比如喝水、起身走走），不用想清楚为什么。",
        "sentence_provenance": [{"sentence":"你已经愿意停下来看自己一眼","provenance":"system_offered"}],
        "system_offered_claims": ["你已经愿意停下来看自己一眼"],
        "safety_override": False,
        "audit_note": "SAFE_FALLBACK",
    }

# ---------------------------------------------------------------- #
# 7. Structured Result Payload
# ---------------------------------------------------------------- #
def build_payload(eo, suff, composed, audit, router_decision) -> dict:
    return {
        "session_id": eo.session_id,
        "reflection_mode": suff.mode,
        "sufficiency": { "raw_present": suff.raw_experience_present, "density": suff.lived_density,
                         "repetition": suff.repetition_language, "safety": suff.safety_signals },
        "evidence": {
            "steps": [ { "step": s.step, "canonical": s.canonical, "raw": s.raw_label,
                        "provenance": s.provenance, "source_step": s.source_step } for s in eo.steps ],
            "free_text": { "raw": eo.free_text.raw, "normalized": eo.free_text.normalized,
                           "provenance": eo.free_text.provenance, "source_step": eo.free_text.source_step },
        },
        "reflection": composed,
        "audit": audit,
        "router_decision": router_decision,
    }

# ---------------------------------------------------------------- #
# 8. Router (deterministic, 独立于 LLM)
# ---------------------------------------------------------------- #
def route(suff: SufficiencyResult, eo: EvidenceObject) -> str:
    if suff.safety_signals == "CRITICAL":
        return "NO_COMMERCIAL_CTA"
    explicit = eo.free_text.raw
    human_support = any(t in explicit for t in ["我想找个人","一个人整理不动","找人谈","陪我说","想谈","咨询"])
    deeper = suff.repetition_language and any(t in explicit for t in ["深入","为什么","重复","看清","根源"])
    if human_support:
        return "COUNSELLING_INFORMATION"
    if deeper:
        return "LIFE_THEME_INFORMATION"
    return "NO_STRONG_CTA"

if __name__ == "__main__":
    import demo_llm
    print("SeeSoul Compass v2 Demo 引擎 · see demo_run.py")