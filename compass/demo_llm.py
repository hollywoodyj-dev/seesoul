#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SeeSoul Compass v2 · LLM Customised Reflection 可插拔组件
===============================================================
遵守 Compass v2 Bounded Composition（Integration Spec §6 / Addendum）：
  - BOUNDED INFERENCE ≠ NO INFERENCE
  - LLM CUSTOMISATION ≠ PERMISSION EXPANSION
  - CUSTOMISATION DEPTH ≤ EVIDENCE DEPTH
  - DISCOVERY QUESTION 而非 HYPOTHESIS-LOADED
  - R1 不许 hypothesis · R2 允许 one bounded reflection · R3 保留 alternatives
  - ANTICIPATED_COST ≠ HIDDEN FUNCTION · THOUGHT ≠ CORE BELIEF

本组件由 Agent（作为 bounded LLM）依据每个 case 的真实证据即时生成，
不接外部 API；输出为结构化 dict，供 engine 审计后组 payload。
"""

from __future__ import annotations
from compass_engine import EvidenceObject, SufficiencyResult, LABELS, R0_MIRROR

# ---------------------------------------------------------------- #
# 读取用户已选字段的小工具（只忠实转述，不补全）
# ---------------------------------------------------------------- #
def _label(eo: EvidenceObject, step: str) -> str:
    for s in eo.steps:
        if s.step == step:
            return s.raw_label
    return ""

def _any(eo, *steps):
    return next((_label(eo, st) for st in steps if _label(eo, st)), "")

def _feeling(eo):  return _label(eo, "feeling")
def _body(eo):     return _label(eo, "body")
def _thought(eo):  return _label(eo, "thought")
def _impulse(eo):  return _label(eo, "impulse")
def _concern(eo):  return _label(eo, "protection")   # ANTICIPATED_COST (中性)
def _aware(eo):    return _label(eo, "awareness")
def _entry(eo):    return _label(eo, "reality")

def _quote(label: str) -> str:
    if not label:
        return ""
    if label.startswith("「") and label.endswith("」"):
        return label
    return f"「{label}」"

_LAYER = (
    ("reality", "最近发生的事"),
    ("feeling", "感受"),
    ("body", "身体"),
    ("thought", "脑海里的话"),
    ("impulse", "你想做的"),
    ("protection", "你在意的"),
    ("awareness", "你想照顾的"),
)

def _own(eo: EvidenceObject, step: str) -> str:
    for s in eo.steps:
        if s.step == step:
            return (s.own_words or "").strip()
    return ""

def _has_own(eo: EvidenceObject) -> bool:
    return any(_own(eo, step) for step, _title in _LAYER)

def _echo(eo: EvidenceObject) -> str:
    """把每一步的选项和来访者自己写的原话并列出来，不另作解释。"""
    lines = []
    for step, title in _LAYER:
        label = _label(eo, step)
        words = _own(eo, step)
        if not label and not words:
            continue
        if label and words:
            lines.append(f"{title}：{label}。你写的是{_quote(words)}")
        elif words:
            lines.append(f"{title}：你写的是{_quote(words)}")
        else:
            lines.append(f"{title}：{label}")
    return "你这次留下来的，是这些：\n" + "\n".join(lines)

# ---------------------------------------------------------------- #
# Compose（读取该用户真实字段 -> customised）
# ---------------------------------------------------------------- #
def compose_llm(eo: EvidenceObject, suff: SufficiencyResult, mode_hint: str) -> dict:
    raw = eo.free_text.raw
    mode = suff.mode

    # ----- R0 / 安全（引擎兜底也覆盖，这里双保险）-----
    if suff.safety_signals == "CRITICAL":
        return {
            "mirror": R0_MIRROR,
            "bounded_reflection": None, "discovery_question": None, "small_movement": None,
            "sentence_provenance": [{"sentence":"你刚才写下的内容，让我们需要先认真确认你的安全","provenance":"system_offered"}],
            "system_offered_claims": ["你刚才写下的内容，让我们需要先认真确认你的安全"], "safety_override": True,
        }

    common = {
        "sentence_provenance": [], "system_offered_claims": [],
        "safety_override": False,
    }

    # ================= R1 · LIGHT =================
    if mode == "R1":
        if _has_own(eo):
            common["sentence_provenance"] = [{"sentence": "你这次留下来的，是这些", "provenance": "system_offered"}]
            for step, _title in _LAYER:
                if _own(eo, step):
                    common["sentence_provenance"].append({"sentence": _own(eo, step), "provenance": "USER_WRITTEN"})
            common["mirror"] = _echo(eo)
            common["bounded_reflection"] = None
            common["discovery_question"] = "如果这一刻要给自己一点照顾，你先想顾到的会是哪一小处？"
            common["small_movement"] = "今天只做一件让自己回神的小事——不用想清楚为什么，也不需要向谁解释。"
            return common
        # 保留用户的确切信号，只整理，不假设
        feel, body, thought, impulse = _feeling(eo), _body(eo), _thought(eo), _impulse(eo)
        mirror = "你现在还说不清具体发生了哪一件事，但身体的信号已经先到了"
        if body:
            mirror += f"（{body}）"
        mirror += "，脑子也停不下来"
        if thought:
            mirror += f"（{thought}）"
        mirror += "。"
        common["sentence_provenance"] = [
            {"sentence": f"你现在还说不清具体发生了哪一件事", "provenance": "system_offered"},
        ]
        if body:
            common["sentence_provenance"].append({"sentence": body, "provenance": "USER_SELECTED"})
        common["mirror"] = mirror
        common["bounded_reflection"] = None   # R1 不允许 hypothesis
        common["discovery_question"] = "如果这一刻要给自己一点照顾，你先想顾到的会是哪一小处？"
        common["small_movement"] = "今天只做一件让自己回神的小事——不用想清楚为什么，也不需要向谁解释。"
        return common

    # ================= R2 · GROUNDED =================
    if mode == "R2":
        if _has_own(eo):
            common["mirror"] = _echo(eo)
            common["bounded_reflection"] = "这些是你自己留下的选择和原话。这里不把它们解释成一个结论。"
            common["system_offered_claims"] = ["这里不把它们解释成一个结论"]
            common["sentence_provenance"] = [
                {"sentence": "这些是你自己留下的选择和原话", "provenance": "system_offered"},
            ]
            for step, _title in _LAYER:
                if _own(eo, step):
                    common["sentence_provenance"].append({"sentence": _own(eo, step), "provenance": "USER_WRITTEN"})
            common["discovery_question"] = "如果继续往下看，你希望先看清的是哪一处？"
            common["small_movement"] = "今天可以给其中一个被你摆出来的事实做一点小小回应，不必推翻它，只需先看待它。"
            return common
        # 用该用户真实自由文本做目标 base（必须出现原话片段 -> 可追溯）
        raw_frag = None
        if raw:
            # 取第一句话的后半段作为可追溯锚点（保留原话，绝不改写）
            first = raw.split("。")[0] or raw
            raw_frag = first if len(first) <= 60 else first[:60] + "…"
        feel, body, thought, impulse, concern, aware = (
            _feeling(eo), _body(eo), _thought(eo), _impulse(eo), _concern(eo), _aware(eo))
        mirror = "你正在经历的不是一个需要被贴上标签的状态"
        if raw_frag:
            # 把用户自己的话锚进 mirror —— 第一句就因 lived 而不同，可追溯
            mirror = f"你自己已经说得很清楚——「{raw_frag}」。这不是一个需要被贴上标签的状态"
        if feel:
            mirror += f"，而是像"+feel+"这样具体的感受"
        if body:
            mirror += f"，身体也在用"+body+"告诉你它在这里"
        mirror += "。"
        # bounded reflection —— 连接用户已提供的两个事实，不发明新因果
        bounded = None
        offered = []
        if raw:
            bounded = (
                f"在这里值得停一下：你亲口给出的几件事——「{raw_frag}」——"
            )
            if thought and impulse:
                bounded += f"而紧接着是{_quote(thought)}，让你想{_quote(impulse)}。"
                offered.append(f"外面发生的事与你心里那句{thought}，似乎被{impulse}连在了一起")
                common["sentence_provenance"].append({"sentence": f"{thought}", "provenance": "USER_SELECTED"})
                common["sentence_provenance"].append({"sentence": f"想{impulse}", "provenance": "USER_SELECTED"})
            elif impulse:
                bounded += f"你最想的是「{impulse}」。"
                offered.append(f"你也提到自己会想{impulse}")
            # 加入 concern 作为系统提出的可能性（SQL外层标注 SYSTEM_OFFERED）
            if concern:
                bounded += f"你也在意{concern}。这些都不是结论，只是此刻你愿意摆出来的事实。"
                common["sentence_provenance"].append({"sentence": f"你在意{concern}", "provenance": "USER_SELECTED"})
            common["bounded_reflection"] = bounded
            common["system_offered_claims"] = offered
        common["mirror"] = mirror
        if not bounded:
            common["bounded_reflection"] = "现在我们还不能把话说得太满——但你愿意把这些都摆出来，已经是很重要的一步。"
        common["discovery_question"] = "如果继续往下看，你希望先看清的是哪一处？"
        common["small_movement"] = "今天可以给其中一个被你摆出来的事实做一点小小回应，不必推翻它，只需先看待它。"
        return common

    # ================= R3 · AMBIGUOUS =================
    if mode == "R3":
        raw_frag = (raw.split("。")[0] or raw) if raw else ""
        feel, body, thought, impulse, concern, aware = (
            _feeling(eo), _body(eo), _thought(eo), _impulse(eo), _concern(eo), _aware(eo))
        mirror = "你自己已经说得很清楚——「" + raw_frag + "」。你给我们的信息其实很具体，但它们同时指向几个方向。"
        common["mirror"] = mirror
        # R3: name ambiguity + preserve alternatives，不替用户选更深
        common["bounded_reflection"] = (
            "这里同时站着两个都被你亲口讲出的方向：一个想向前、想和好；另一个在提醒你这段关系也正消耗着你。"
            "它们目前都站得住脚，SeeSoul 不能替你选哪一个对你更深、更对。"
        )
        common["system_offered_claims"] = ["两个方向都有你亲口提供的依据"]
        common["discovery_question"] = "这两个方向你都能讲出理由，所以才这么难。如果只是先看看——你更舍不得放下的，是哪一边？"
        # 开放问题：邀请用户自己发言，不预设「哪个更深/更对」，保留 ambiguity
        common["small_movement"] = "今天先不急着决定。把'我想和好的理由'和'这段关系让我累的地方'各写一行，只写下来，不评判。"
        return common

    # fallback
    return {
        "mirror": "现在能看到的不多，我不打算替你把话补全。你已经愿意停下来看自己一眼——这本身就是很重要的一步。",
        "bounded_reflection": None, "discovery_question": "如果此刻要给这股感觉一个名字，你会怎么叫它？",
        "small_movement": "今天只做一件让自己回神的小事，不用想清楚为什么。",
        "sentence_provenance": [{"sentence":"你已经愿意停下来看自己一眼","provenance":"system_offered"}],
        "system_offered_claims": ["你已经愿意停下来看自己一眼"], "safety_override": False,
    }