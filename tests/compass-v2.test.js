const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const C = require("../compass-v2.js");
const raw = JSON.parse(read(C.COPY_URL));
const copy = C.prepareCopy(raw);
const step = (key) => copy.steps.find((s) => s.key === key);
const label = (key, id) => step(key).choices.find((c) => c.id === id).label;

function answers(spec) {
  const a = C.emptyAnswers(copy);
  for (const [key, v] of Object.entries(spec)) {
    a[key].choiceIds = v.ids || [];
    a[key].freeText = v.text || "";
    a[key].skipped = !!v.skipped;
  }
  return a;
}
const lines = (note) => note.sections.flatMap((s) => s.lines);
const FORBIDDEN = ["创伤", "人格", "潜意识", "依恋", "诊断", "抛弃", "遗弃", "你已经找到", "你已经看清", "治疗", "课程", "预约", "付款"];

test("copy registry matches the handoff rules", () => {
  assert.equal(copy.steps.length, 7);
  assert.deepEqual(copy.steps.map((s) => s.key), ["reality", "feeling", "body", "thought", "impulse", "protection", "awareness"]);
  for (const s of copy.steps) {
    assert.equal(s.selectMax, s.key === "feeling" ? 2 : 1);
    assert.equal(new Set(s.choices.map((c) => c.id)).size, s.choices.length);
    assert.ok(s.freeTextLabel.includes("选填"));
  }
  assert.equal(copy.interaction.freeTextMaxLength, 280);
  assert.equal(copy.interaction.allowSkipEveryStep, true);
  assert.equal(copy.status, "SEMANTIC_COPY_FINAL_CANDIDATE__FOUNDER_APPROVAL_REQUIRED__LOCAL_ONLY");
  assert.equal(copy.version, "2.1.0-founder-review");
  assert.equal(copy.privacy.resultAI, "NONE");
  assert.deepEqual(Object.keys(copy.bridges), ["feeling", "body", "thought", "impulse", "protection", "awareness"]);
  assert.deepEqual(Object.keys(copy.reflectionLibrary).sort(), [...step("protection").choices.map((c) => c.id), "default"].sort());
  for (const v of Object.values(copy.reflectionLibrary)) {
    assert.equal(v.questions.length, 2);
    assert.equal(v.actions.length, 2);
  }
});

test("repo supplement only fills labels the candidate lacks", () => {
  for (const k of Object.keys(raw.repoSupplement.labels)) assert.ok(!(k in raw.labels), k);
  for (const k of Object.keys(raw.labels)) assert.equal(copy.labels[k], raw.labels[k]);
  assert.equal(copy.labels.skip, "暂时跳过");
  assert.equal(copy.labels.final, "整理我刚刚看见的 →");
  assert.equal(copy.labels.restart, "重新开始");
});

test("v2.1 wording is used exactly", () => {
  assert.equal(step("thought").title, "想到这件事时，脑海里最容易冒出哪句话？");
  assert.equal(step("impulse").title, "面对这样的情况，你通常会怎样回应？");
  assert.deepEqual(step("impulse").choices.map((c) => c.id), ["fix", "ruminate", "avoid", "pause", "support", "unsure"]);
  assert.equal(step("awareness").title, "回头看看，刚才有什么是你比之前更留意到的？");
  assert.equal(copy.labels.noAnswers, "你选择先停在这里。现在还说不清，也没有关系。");
});

test("Q6 maps every choice to its first question and small action; missing Q6 uses default", () => {
  for (const c of step("protection").choices) {
    const note = C.buildNote(copy, answers({ protection: { ids: [c.id] } }));
    assert.equal(note.libraryKey, c.id);
    assert.equal(note.question, copy.reflectionLibrary[c.id].questions[0]);
    assert.equal(note.microAction, copy.reflectionLibrary[c.id].actions[0]);
  }
  const none = C.buildNote(copy, answers({ reality: { ids: ["unclear"] } }));
  assert.equal(none.libraryKey, "default");
  const skipped = C.buildNote(copy, answers({ protection: { ids: ["safety"], skipped: true } }));
  assert.equal(skipped.libraryKey, "default");
  const unknown = C.buildNote(copy, answers({ protection: { ids: ["not_a_choice"] } }));
  assert.equal(unknown.libraryKey, "default");
  const alternates = Object.values(copy.reflectionLibrary).flatMap((v) => [v.questions[1], v.actions[1]]);
  for (const c of step("protection").choices) {
    const n = C.buildNote(copy, answers({ protection: { ids: [c.id] } }));
    assert.ok(!alternates.includes(n.question) && !alternates.includes(n.microAction), "alternate copy must not be used");
  }
});

test("safety terms match the server engine", () => {
  const engine = read("compass/compass_engine.py");
  const list = (name) => JSON.parse(engine.match(new RegExp(name + "\\s*=\\s*(\\[[^\\]]*\\])"))[1]);
  assert.deepEqual(C.CRITICAL_TERMS, list("CRITICAL_TERMS"));
  assert.deepEqual(C.CONCERN_TERMS, list("CONCERN_TERMS"));
});

test("safety: critical, concern, none, critical wins, spaces ignored", () => {
  assert.equal(C.assessText("我今天真的不想活了"), "CRITICAL");
  assert.equal(C.assessText("我 不 想 活"), "CRITICAL");
  assert.equal(C.assessText("想……死"), "CRITICAL");
  assert.equal(C.assessText("自-杀"), "CRITICAL");
  assert.equal(C.assessText("活不下去！"), "CRITICAL");
  assert.equal(C.assessText("不想\n活"), "CRITICAL");
  assert.equal(C.assessText("真的撑不住了"), "CRITICAL");
  assert.equal(C.assessText("最近总是想哭"), "CLARIFY");
  assert.equal(C.assessText("有点撑不住"), "CLARIFY");
  assert.equal(C.assessText("朋友很少回复我的消息"), "NONE");
  assert.equal(C.assessText(""), "NONE");
});

test("documented lexicon limits: known false positives and misses stay visible until professional review", () => {
  const falsePositives = {
    "想死你了，好久不见": "CRITICAL",
    "并不是没有希望": "CRITICAL",
    "我绝对不会伤害自己": "CRITICAL",
    "新闻里说有人自杀": "CRITICAL",
    "哭笑不得": "CLARIFY",
    "电影很感人，看哭了": "CLARIFY"
  };
  for (const [t, want] of Object.entries(falsePositives)) assert.equal(C.assessText(t), want, t);
  const misses = ["不活了", "想轻生", "想跳楼", "想割腕", "结束自己", "I want to kill myself", "suicide", "zisha", "活着没意思"];
  for (const t of misses) assert.equal(C.assessText(t), "NONE", t);
  assert.equal(C.assessText("我快撑不住了"), "CLARIFY");
  assert.equal(C.assessText("真的撑不住了"), "CRITICAL");
});

test("F-03 feeling allows two, refuses a third and keeps the first two", () => {
  const a = C.emptyAnswer();
  assert.equal(C.toggleChoice(step("feeling"), a, "anxiety").ok, true);
  assert.equal(C.toggleChoice(step("feeling"), a, "sadness").ok, true);
  const r = C.toggleChoice(step("feeling"), a, "anger");
  assert.deepEqual(r, { ok: false, reason: "max" });
  assert.deepEqual(a.choiceIds, ["anxiety", "sadness"]);
  C.toggleChoice(step("feeling"), a, "anxiety");
  assert.deepEqual(a.choiceIds, ["sadness"]);
});

test("single choice replaces, unknown ids are refused", () => {
  const a = C.emptyAnswer();
  C.toggleChoice(step("body"), a, "none");
  C.toggleChoice(step("body"), a, "unknown");
  assert.deepEqual(a.choiceIds, ["unknown"]);
  assert.equal(C.toggleChoice(step("body"), a, "<script>").ok, false);
});

test("F-09 text is capped at 280", () => {
  const a = C.emptyAnswer();
  C.setText(a, "字".repeat(300), 280);
  assert.equal(a.freeText.length, 280);
});

test("previous text with a safety word is never quoted; the label is shown instead", () => {
  const a = answers({ reality: { ids: ["unclear"], text: "最近总是想哭" } });
  assert.deepEqual(C.contextFor(copy, a, 1), { bridge: copy.bridges.feeling, prefix: "你刚才选择了：", text: "我说不清楚，但觉得有些不对劲" });
  const b = answers({ reality: { text: "最近总是想哭" } });
  assert.deepEqual(C.contextFor(copy, b, 1), { bridge: copy.bridges.feeling, prefix: "", text: "" });
});

test("F-10 / G2 continuity: neutral bridge always, quote only the previous real answer", () => {
  const a = answers({ reality: { ids: ["relationship_change"], text: "最近一个朋友很少回复我的消息。" } });
  assert.equal(C.contextFor(copy, a, 0), null);
  assert.deepEqual(C.contextFor(copy, a, 1), { bridge: copy.bridges.feeling, prefix: "你刚才提到：", text: "最近一个朋友很少回复我的消息。" });
  assert.deepEqual(C.contextFor(copy, a, 2), { bridge: copy.bridges.body, prefix: "", text: "" }, "unanswered previous step: bridge only");
  a.feeling.choiceIds = ["sadness", "anxiety"];
  assert.deepEqual(C.contextFor(copy, a, 2), { bridge: copy.bridges.body, prefix: "你刚才选择了：", text: "难过、失落、担心、紧张" });
  assert.equal(C.contextFor(copy, a, 4).text, "", "only the immediately previous step is quoted");
  a.feeling.skipped = true;
  assert.equal(C.contextFor(copy, a, 2).text, "", "skipped step is never quoted");
});

test("R-01 relationship persona: grounded, no abandonment inference", () => {
  const a = answers({
    reality: { ids: ["relationship_change"], text: "最近一个朋友很少回复我的消息。" },
    feeling: { ids: ["sadness"] },
    impulse: { ids: ["ruminate"] },
    protection: { ids: ["relationship"] }
  });
  const note = C.buildNote(copy, a);
  const all = lines(note).join("\n");
  assert.ok(all.includes("「" + label("reality", "relationship_change") + "」"));
  assert.ok(all.includes("「最近一个朋友很少回复我的消息。」"));
  assert.ok(all.includes("「难过、失落」"));
  assert.ok(all.includes("「一个人在心里反复想、反复分析」"));
  assert.ok(all.includes("你选择了「一段重要的关系」作为你很在意的部分。"));
  for (const w of FORBIDDEN) assert.ok(!all.includes(w), w);
  assert.deepEqual(note.sections.map((s) => s.k), ["01 · 我正在面对", "02 · 我的感受与反应", "03 · 我很在意的"]);
  assert.equal(note.question, "在这段关系里，我最希望被看见或理解的是什么？");
  assert.equal(note.microAction, "如果愿意，把已经发生的互动和自己的猜测分开写一写。");
});

test("R-02 direction persona keeps uncertainty and pushes nothing", () => {
  const a = answers({
    reality: { ids: ["recurring_issue"], text: "我迟迟没办法决定要不要换工作。" },
    feeling: { ids: ["anxiety"] },
    impulse: { ids: ["unsure"] },
    protection: { ids: ["unsure"] },
    awareness: { ids: ["confused"] }
  });
  const note = C.buildNote(copy, a);
  const all = lines(note).join("\n") + note.question + note.microAction;
  assert.ok(all.includes("关于回应，你选择了「暂时不知道该怎么回应」。"));
  assert.ok(all.includes("还不确定自己最在意什么，也没有关系。"));
  assert.ok(all.includes("你选择了「我现在仍然有些混乱」。还在整理中，也没有关系。"));
  for (const w of FORBIDDEN) assert.ok(!all.includes(w), w);
  assert.equal(note.question, "此刻有没有一个小地方，是我愿意慢慢弄清楚的？");
});

test("R-03 / F-02 all skipped: no personal statement, gentle general prompt", () => {
  const a = C.emptyAnswers(copy);
  for (const k of Object.keys(a)) a[k].skipped = true;
  const note = C.buildNote(copy, a);
  assert.equal(note.empty, true);
  assert.equal(note.sections.length, 0);
  assert.equal(note.intro, "你选择先停在这里。现在还说不清，也没有关系。");
  assert.equal(note.question, copy.reflectionLibrary.default.questions[0]);
  assert.equal(note.microAction, copy.reflectionLibrary.default.actions[0]);
});

test("skipped step drops its earlier content from the note", () => {
  const a = answers({ reality: { ids: ["unclear"], text: "不想被看到", skipped: true } });
  assert.equal(C.buildNote(copy, a).sections.length, 0);
});

test("F-04 thought text only: quoted and marked as a thought", () => {
  const note = C.buildNote(copy, answers({ thought: { text: "他是不是讨厌我" } }));
  assert.deepEqual(lines(note), ["你写下脑海里的一句话：「他是不是讨厌我」", "这是一个想法，不一定是已经确认的事实。"]);
});

test("F-05 body none: plain statement only", () => {
  const note = C.buildNote(copy, answers({ body: { ids: ["none"] } }));
  assert.deepEqual(lines(note), ["你没有注意到特别明显的身体反应。"]);
});

test("F-06 awareness confused is never turned into an insight", () => {
  const note = C.buildNote(copy, answers({ awareness: { ids: ["confused"] } }));
  const all = lines(note).join("");
  assert.ok(all.includes("我现在仍然有些混乱"));
  assert.ok(!/找到|看清|明白了/.test(all));
});

test("Q7 write_own quotes the user once, or says nothing was written", () => {
  assert.deepEqual(lines(C.buildNote(copy, answers({ awareness: { ids: ["write_own"], text: "我其实很在乎" } }))), ["你用自己的话记录下：「我其实很在乎」"]);
  assert.deepEqual(lines(C.buildNote(copy, answers({ awareness: { ids: ["write_own"] } }))), ["你想用自己的话记录下来，这一次还没有写下。"]);
});

test("traceability: every personal line carries a label or the user's own words", () => {
  const spec = {
    reality: { ids: ["repeated_event"], text: "A1" }, feeling: { ids: ["anger", "numbness"], text: "B2" },
    body: { ids: ["chest"], text: "C3" }, thought: { ids: ["other_mind"], text: "D4" },
    impulse: { ids: ["support"], text: "E5" }, protection: { ids: ["boundary"], text: "F6" },
    awareness: { ids: ["values"], text: "G7" }
  };
  const fixed = ["这是一个想法，不一定是已经确认的事实。"];
  const sources = [];
  for (const [k, v] of Object.entries(spec)) { sources.push(v.text); v.ids.forEach((id) => sources.push(label(k, id))); }
  for (const l of lines(C.buildNote(copy, answers(spec)))) {
    assert.ok(fixed.includes(l) || sources.some((s) => l.includes("「" + s + "」")), l);
  }
});

test("F-08 markup stays a plain string inside the note text", () => {
  const evil = "<script>alert(1)</script></textarea><img src=x onerror=alert(2)>";
  const note = C.buildNote(copy, answers({ reality: { text: evil } }));
  assert.ok(lines(note).includes("你写下：「" + evil + "」"));
  assert.ok(C.noteText(copy, note).includes(evil));
});

test("copy text has the title, subtitle, sections and the closing prompts", () => {
  const note = C.buildNote(copy, answers({ feeling: { ids: ["calm"] } }));
  const t = C.noteText(copy, note);
  for (const s of [copy.labels.resultTitle, copy.labels.resultSubtitle, "02 · 我的感受与反应", "留给自己的一个问题", "今天可以试试的一件小事"]) assert.ok(t.includes(s), s);
});

test("D-01 / D-02 pages and script never send, store or inject answers", () => {
  const js = read("compass-v2.js");
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write/.test(js));
  assert.ok(!/localStorage\.setItem|sessionStorage|document\.cookie|indexedDB/.test(js));
  assert.ok(!/XMLHttpRequest|sendBeacon|\/api\//.test(js));
  const fetches = js.match(/fetch\([^)]*\)/g) || [];
  assert.deepEqual(fetches, ['fetch(COPY_URL, { cache: "no-cache", credentials: "omit" })']);
  assert.equal(C.COPY_URL, "compass-copy-zh-v2.1.json");
  assert.ok(!/console\./.test(js));
  for (const f of ["compass-start.html", "compass-question.html", "compass-result.html", "compass-safety.html"]) {
    const h = read(f);
    assert.ok(!/<script(?![^>]*src="compass-v2\.js")[^>]*>/.test(h), f + " has an extra script");
    assert.ok(!/\/api\/|gtag|analytics|localStorage\.setItem/.test(h), f);
  }
});

test("V-04 official logo kept; totem not used as header logo", () => {
  for (const f of ["compass-start.html", "compass-question.html", "compass-result.html"]) {
    const h = read(f);
    assert.ok(h.includes('class="brand-logo" src="assets/seesoul-logo-gold.png"'), f);
    assert.ok(!/brand-logo"[^>]*compass-totem/.test(h), f);
  }
});

test("safety page: v2.1 wording, AU numbers, no echo, no commerce, no old number, no script", () => {
  const h = read("compass-safety.html");
  for (const s of ["先把安全放在前面", "这里的自我整理先暂时停下", "这个网页不能提供紧急心理支持，也无法判断你的具体情况", "000", "Lifeline 13 11 14", "12356"]) assert.ok(h.includes(s), s);
  for (const s of ["400-161-9995", "booking.html", "counselling.html", "life-theme.html", "AUD", "<script", "你刚才写下", "noindex"]) assert.ok(!h.includes(s), s);
});

test("redirect to the safety page carries nothing in the URL", () => {
  const js = read("compass-v2.js");
  assert.ok(js.includes('SAFETY_PAGE = "compass-safety.html"'));
  assert.ok(/location\.replace\(SAFETY_PAGE\)/.test(js));
  assert.ok(!/SAFETY_PAGE\s*\+/.test(js));
});
