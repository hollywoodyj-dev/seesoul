# -*- coding: utf-8 -*-
"""Local P0/P1 regression. Does not call a model and does not deploy."""
import re
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
    "counselling.html": ["写好预约邮件", "要等回复，才是一次确认的咨询", "时间仍然没有被占住", "阅读知情同意与保密说明", "cancellation-policy.html"],
    "payment-success.html": ["并不代表 SeeSoul 已经确认收到付款", "根据实际支付记录核对付款状态", "不代表预约时间已经确认", "知情同意书签署", "避免重复付款", "counselling.html#booking", "noindex"],
    "life-theme.html": ["提交预约请求", "这还不是一次已经确认的预约"],
    "consent.html": ["这一页只是说明，不是已经完成的签署", "CONSENT-DRAFT-2026-10-13", "000", "13 11 14", "consent-counselling.html", "consent-sign.html"],
    "consent-counselling.html": ["Draft v1.0", "Online Counselling", "Face-to-Face Counselling", "AUD $150", "待确认", "000", "13 11 14", "迟到本身不构成未出席", "不因迟到而自动延长", "整个预约时段内始终没有参加咨询"],
    "consent-sign.html": ["尚未启用", "consent-counselling.html", "付款状态分开", "cancellation-policy.html"],
    "cancellation-policy.html": ["24 小时", "AUD $75", "全额退款", "澳大利亚消费者法", "生命课题解读（AUD $100 / 50 分钟）不适用本政策", "还没有生效"],
    "booking.html": ["cancellation-policy.html", "AUD $75", "生命课题解读不适用", "仍可使用原定时段内的剩余时间", "整个预约时段结束后仍未参加"],    "lt-intake.html": ["不是命运预测，也不是心理测评", "LT-12", "lt-safety.html", "life-theme.html#booking", "网站不会替你发送"],
    "compass-privacy.html": ["不会发送给本网站，也不会发送给 OpenAI", "不会保存在这台浏览器里", "不使用 AI 生成结果", "所填内容不会发送给 OpenAI 用于生成觉察笔记", "本页只说明 Compass", "不能识别所有风险", "compass-safety.html", "旧记录会被清除", "不是心理测试或诊断", "000", "13 11 14", "COMPASS-PRIVACY-2026-10-20-DRAFT"],
    "compass-start.html": ["不是心理测试或诊断", "compass-privacy.html", "开始整理自己", "不会发送给本网站或任何 AI", "000", "13 11 14", "compass-v2.js"],
    "lt-safety.html": ["如果你在澳大利亚", "如果你在中国大陆", "如果你在其他地区", "13 11 14", "12356"],
    "lt-draw.html": ["这一版结构对照还不是最终计算规则，不能当作定论。"],
    "compass-result.html": ["觉察笔记不会被保存", "compass-start.html", "compass-v2.js"],
    "compass-question.html": ["我想先确认一下你的安全", "是，我现在需要立即的帮助", "没有，我现在是安全的", "compass-v2.js", "这份笔记没有被保存", "不等于预约或付款"],
    "compass-safety.html": ["先把安全放在前面", "这里的自我整理先暂时停下", "无法判断你的具体情况", "000", "Lifeline 13 11 14", "12356"],
    "compass-v2.js": ['SAFETY_PAGE = "compass-safety.html"', "seesoul_compass_answers", "removeItem"],
}
for name, needles in pages.items():
    text = (root / name).read_text(encoding="utf-8")
    missing = [n for n in needles if n not in text]
    check("page-" + name, not missing, ",".join(missing))
consent_absent = ["严格保密", "不会向任何第三方", "在有外部法律与专业复核之前", "咨询记录仅用于"]
consent_text = (root / "consent.html").read_text(encoding="utf-8")
check("consent-no-internal-or-absolute", not any(n in consent_text for n in consent_absent), ",".join(n for n in consent_absent if n in consent_text))
banned = ["预约已确认", "已确认并签署", "我已阅读并同意签署", "400-161-9995", "任何情况下不退款", "概不退款"]
for name in ("counselling.html", "life-theme.html", "consent.html", "consent-counselling.html", "consent-sign.html", "cancellation-policy.html", "booking.html", "lt-safety.html", "booking.js", "compass-safety.html", "compass-question.html", "compass-start.html"):
    text = (root / name).read_text(encoding="utf-8")
    hit = [n for n in banned if n in text]
    check("banned-" + name, not hit, ",".join(hit))

pay_patterns = [r"buy\.stripe\.com", r"checkout\.stripe\.com", r"paypal\.me", r"paypal\.com/", r"(?i)westpac", r"\bBSB\b", r"(?i)hotmail\.com", r"\b04\d{2}\s?\d{3}\s?\d{3}\b", r"\b\d{3}-\d{3}\b.*\b\d{6}\b", r"[sp]k_(live|test)_"]
pay_hits = []
for f in list(root.glob("*.html")) + list(root.glob("*.js")):
    text = f.read_text(encoding="utf-8", errors="ignore")
    pay_hits += [f.name + ":" + p for p in pay_patterns if re.search(p, text)]
check("no-unverified-payment-details-public", not pay_hits, ",".join(pay_hits))

nav_bad = []
for f in root.glob("*.html"):
    text = f.read_text(encoding="utf-8")
    if 'id="siteNav"' not in text or f.name == "payment-success.html":
        continue
    if '<script src="nav.js" defer></script>' not in text: nav_bad.append(f.name + ":no-nav.js")
    if 'getElementById("navToggle")' in text: nav_bad.append(f.name + ":inline-toggle")
    if 'aria-label="打开导航菜单"' not in text or 'aria-controls="siteNav"' not in text: nav_bad.append(f.name + ":toggle-aria")
    if not re.search(r'href="booking\.html"[^>]*>预约咨询</a>\s*</nav>', text): nav_bad.append(f.name + ":cta")
check("shared-mobile-nav", not nav_bad, ",".join(nav_bad))

pay_text = (root / "payment-success.html").read_text(encoding="utf-8")
pay_default = re.sub(r"<script[\s\S]*?</script>", "", pay_text)
pay_default = re.sub(r'<div[^>]*data-pay-state="(paid|pending|checking)"[^>]*\bhidden\b[^>]*>[\s\S]*?</div>', "", pay_default)
pay_absent = ["已收到", "付款已经收到", "Payment received"]
check("payment-success-no-unverified-claim", not any(n in pay_default for n in pay_absent), ",".join(n for n in pay_absent if n in pay_default))
check("payment-success-no-1320", "1320" not in pay_text)
check("payment-success-verifies-server-side", "/api/seesoul-payment-status?session_id=" in pay_text and 'data-pay-state="paid" hidden' in pay_text and "[data-pay-state][hidden] { display: none !important; }" in pay_text)

import json
compass_copy = json.loads((root / "compass-copy-zh-v2.1.json").read_text(encoding="utf-8"))
csteps = compass_copy["steps"]
check("compass-v2-copy-registry",
      [s["key"] for s in csteps] == ["reality", "feeling", "body", "thought", "impulse", "protection", "awareness"]
      and all(s["selectMax"] == (2 if s["key"] == "feeling" else 1) for s in csteps)
      and all(len({c["id"] for c in s["choices"]}) == len(s["choices"]) for s in csteps)
      and compass_copy["interaction"]["freeTextMaxLength"] == 280 and compass_copy["interaction"]["allowSkipEveryStep"] is True
      and compass_copy["privacy"]["resultAI"] == "NONE"
      and set(compass_copy["reflectionLibrary"]) == {c["id"] for c in csteps[5]["choices"]} | {"default"})
check("compass-v2-no-stale-copy-file", not (root / "compass-copy-zh-v2.json").exists() and 'COPY_URL = "compass-copy-zh-v2.1.json"' in (root / "compass-v2.js").read_text(encoding="utf-8"))
from compass_engine import CRITICAL_TERMS, CONCERN_TERMS
v2_js = (root / "compass-v2.js").read_text(encoding="utf-8")
def js_list(name):
    m = re.search(name + r"\s*=\s*(\[[^\]]*\])", v2_js)
    return json.loads(m.group(1)) if m else None
check("compass-v2-safety-terms-match-engine", js_list("CRITICAL_TERMS") == CRITICAL_TERMS and js_list("CONCERN_TERMS") == CONCERN_TERMS)
compass_leaks = []
for name in ("compass-start.html", "compass-question.html", "compass-result.html", "compass-safety.html", "compass-v2.js"):
    text = (root / name).read_text(encoding="utf-8")
    compass_leaks += [name + ":" + n for n in ("/api/compass", "localStorage.setItem", "sessionStorage", "innerHTML", "XMLHttpRequest", "sendBeacon", "gtag(", "1320") if n in text]
check("compass-v2-local-only", not compass_leaks, ",".join(compass_leaks))

intake_text = (root / "lt-intake.html").read_text(encoding="utf-8")
intake_absent = ["1320", "lt-data.js", "lt-profile.html", "fetch(", "XMLHttpRequest", "/api/", "localStorage"]
check("lt-intake-independent", not any(n in intake_text for n in intake_absent), ",".join(n for n in intake_absent if n in intake_text))

print("FAILURES", len(failures))
raise SystemExit(1 if failures else 0)
