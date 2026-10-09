# -*- coding: utf-8 -*-
"""Local P0/P1 regression. Does not call a model and does not deploy."""
import reflect
from compass_engine import LABELS, R0_MIRROR, _audit_question, build_evidence, sufficiency

failures = []

def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ((" | " + detail) if detail else ""))
    if not ok:
        failures.append(name)

def no_model(cfg, prompt):
    raise AssertionError("model was called")

reflect.call_llm = no_model

critical = reflect.reflect({"1": "work"}, "我今天真的不想活了，这件事已经说了很久。")
check("critical-is-r0", critical.get("reflection_mode") == "R0", str(critical.get("reflection_mode")))
check("critical-copy", critical.get("mirror") == R0_MIRROR)
check("critical-no-reflection", critical.get("bounded_reflection") is None and critical.get("discovery_question") is None and critical.get("small_movement") is None)
check("critical-no-commerce", critical.get("router") == "NO_COMMERCIAL_CTA")
check("r0-shows-000", "000" in (critical.get("mirror") or ""))
check("r0-shows-131114", "13 11 14" in (critical.get("mirror") or ""))
check("r0-no-booking-cta", critical.get("router") == "NO_COMMERCIAL_CTA" and "counselling.html" not in str(critical) and "booking.html" not in str(critical))

clarify = reflect.reflect({"6": "break-down"}, "我有点累。")
check("ambiguous-is-clarify", clarify.get("safety") == "CLARIFY" and clarify.get("reflection_mode") is None, str(clarify))
check("concern-is-clarify", reflect.reflect({}, "我最近很痛苦，不知道怎么办。").get("safety") == "CLARIFY")

needs = reflect.reflect({"6": "break-down"}, "我有点累。", "needs_help")
check("needs-help-is-r0", needs.get("reflection_mode") == "R0" and needs.get("mirror") == R0_MIRROR)
check("needs-help-not-in-mirror", "需要立即的帮助" not in (needs.get("mirror") or "") and "我现在是安全的" not in (needs.get("mirror") or ""))

captured = {}
def capture(cfg, prompt):
    captured["prompt"] = prompt
    class R:
        ok = False
        payload = None
        status = "SKIPPED"
    return R()

reflect.call_llm = capture
reflect.load_explicit_config = lambda: type("C", (), {"configured": True})()
safe = reflect.reflect({"6": "break-down"}, "我有点累。", "safe_now")
prompt = captured.get("prompt", "")
check("safe-now-not-r0", safe.get("reflection_mode") in ("R1", "R2"), str(safe.get("reflection_mode")))
check("safe-now-absent-from-prompt", "我现在是安全的" not in prompt and "需要立即的帮助" not in prompt)
check("safe-now-absent-from-output", "我现在是安全的" not in str(safe))

long_text = "这件事已经重复了很多次，我还是不知道它为什么会这样出现，想看清楚一点。"
r2 = reflect.reflect({"1": "work", "2": "tight"}, long_text, "safe_now") if False else reflect.reflect({"1": "work", "2": "tight"}, long_text)
check("long-text-not-r3", r2.get("reflection_mode") != "R3", str(r2.get("reflection_mode")))
check("prompt-anticipated-concern", "anticipated_concern" in prompt and "protection" not in prompt, prompt)

reflect.call_llm = no_model
reflect.load_explicit_config = lambda: type("C", (), {"configured": False})()

allowed = [
    "这件事里，你现在最想再看清楚哪一部分？",
    "当这种感觉出现时，你最先注意到的是什么？",
]
forbidden = [
    "你是不是其实害怕被抛下？",
    "你是在害怕失去，还是害怕自己不够好？",
    "是不是因为你怕被留下？",
    "其实是因为你一直在忍。",
    "你怕的是被抛下。",
]
check("allowed-questions", all(_audit_question(q) == "PASS" for q in allowed))
check("forbidden-phrases", all(_audit_question(q) == "FAIL" for q in forbidden))
# Known limit: no semantic classifier. This sentence is not caught by the phrase list.
check("semantic-limit-documented", _audit_question("会不会真正困住你的是对失去的恐惧？") == "PASS")

check("q7-label", LABELS["body-rest"] == "身体这一侧，包括累和需要休息")
check("critical-before-concern", sufficiency(build_evidence("t", {}, "真的撑不住了")).safety_signals == "CRITICAL")

stay = reflect.reflect({}, "我不想活了", "safe_now")
check("safe-now-cannot-downgrade-critical", stay.get("reflection_mode") == "R0" and stay.get("mirror") == R0_MIRROR)

dirty = {
    "mirror": "你停在这里看了一眼。",
    "bounded_reflection": None,
    "discovery_question": "你是不是其实害怕被抛下？",
    "small_movement": "喝一口水。",
    "sentence_provenance": [],
    "system_offered_claims": [],
    "safety_override": False,
}
reflect._bounded = lambda eo, suff: dirty
replaced = reflect.reflect({"1": "work"}, "")
check("question-only-replaced", replaced.get("discovery_question") == "如果此刻要给这股感觉一个名字，你会怎么叫它？", str(replaced.get("discovery_question")))
check("question-only-keeps-mirror", replaced.get("mirror") == "你停在这里看了一眼。")

root = __import__("pathlib").Path(__file__).resolve().parents[1]
pages = {
    "counselling.html": ["提交预约请求", "这还不是一次已经确认的预约", "阅读知情同意与保密说明"],
    "life-theme.html": ["提交预约请求", "这还不是一次已经确认的预约"],
    "consent.html": ["这一页只是说明，不是已经完成的签署", "Compass 的七个选择和你写下的话保存在这台浏览器里"],
    "lt-safety.html": ["如果你在澳大利亚", "如果你在中国大陆", "如果你在其他地区", "13 11 14", "12356"],
    "lt-draw.html": ["这一版结构对照还不是最终计算规则，不能当作定论。"],
    "compass-result.html": ["我想先确认一下你的安全", "是，我现在需要立即的帮助", "没有，我现在是安全的", "查看其他地区支持 →", 'href="lt-safety.html"'],
    "compass-question.html": ["身体这一侧，包括累和需要休息"],
}
for name, needles in pages.items():
    text = (root / name).read_text(encoding="utf-8")
    missing = [n for n in needles if n not in text]
    check("page-" + name, not missing, ",".join(missing))
banned = ["预约已确认", "已确认并签署", "我已阅读并同意签署", "400-161-9995"]
for name in ("counselling.html", "life-theme.html", "consent.html", "lt-safety.html", "booking.js"):
    text = (root / name).read_text(encoding="utf-8")
    hit = [n for n in banned if n in text]
    check("banned-" + name, not hit, ",".join(hit))

print("FAILURES", len(failures))
raise SystemExit(1 if failures else 0)
