(function (root) {
  "use strict";

  var CRITICAL_TERMS = ["自杀", "不想活", "活不下去", "结束生命", "伤害自己", "想死", "死掉算了", "自残", "真的撑不住了", "没有希望"];
  var CONCERN_TERMS = ["哭", "撑不住", "绝望", "很痛苦", "熬不下去"];
  var OLD_STORAGE_KEY = "seesoul_compass_answers";
  var SAFETY_PAGE = "compass-safety.html";
  var COPY_URL = "compass-copy-zh-v2.1.json";

  function assessText(text) {
    var t = String(text || "").replace(/[\s\p{P}\p{S}]+/gu, "");
    if (!t) return "NONE";
    for (var i = 0; i < CRITICAL_TERMS.length; i++) if (t.indexOf(CRITICAL_TERMS[i]) >= 0) return "CRITICAL";
    for (var j = 0; j < CONCERN_TERMS.length; j++) if (t.indexOf(CONCERN_TERMS[j]) >= 0) return "CLARIFY";
    return "NONE";
  }

  function prepareCopy(raw) {
    var extra = (raw.repoSupplement && raw.repoSupplement.labels) || {};
    var labelsOut = {};
    Object.keys(extra).forEach(function (k) { labelsOut[k] = extra[k]; });
    Object.keys(raw.labels || {}).forEach(function (k) { labelsOut[k] = raw.labels[k]; });
    var out = {};
    Object.keys(raw).forEach(function (k) { out[k] = raw[k]; });
    out.labels = labelsOut;
    return out;
  }

  function emptyAnswer() { return { choiceIds: [], freeText: "", skipped: false }; }

  function emptyAnswers(copy) {
    var out = {};
    copy.steps.forEach(function (s) { out[s.key] = emptyAnswer(); });
    return out;
  }

  function hasAnswer(a) {
    return !!a && !a.skipped && (a.choiceIds.length > 0 || a.freeText.trim() !== "");
  }

  function findChoice(step, id) {
    for (var i = 0; i < step.choices.length; i++) if (step.choices[i].id === id) return step.choices[i];
    return null;
  }

  function labels(step, answer) {
    return answer.choiceIds.map(function (id) { var c = findChoice(step, id); return c ? c.label : null; }).filter(Boolean);
  }

  function toggleChoice(step, answer, id) {
    if (!findChoice(step, id)) return { ok: false, reason: "unknown" };
    var at = answer.choiceIds.indexOf(id);
    if (at >= 0) { answer.choiceIds.splice(at, 1); return { ok: true }; }
    if (step.selectMax === 1) { answer.choiceIds = [id]; answer.skipped = false; return { ok: true }; }
    if (answer.choiceIds.length >= step.selectMax) return { ok: false, reason: "max" };
    answer.choiceIds.push(id);
    answer.skipped = false;
    return { ok: true };
  }

  function setText(answer, text, max) {
    answer.freeText = String(text || "").slice(0, max);
    if (answer.freeText.trim()) answer.skipped = false;
  }

  function contextFor(copy, answers, index) {
    if (index <= 0) return null;
    var out = { bridge: (copy.bridges && copy.bridges[copy.steps[index].key]) || "", prefix: "", text: "" };
    var prev = copy.steps[index - 1];
    var a = answers[prev.key];
    if (hasAnswer(a)) {
      var own = a.freeText.trim();
      if (own && assessText(own) === "NONE") { out.prefix = copy.labels.contextPrefix; out.text = own; }
      else if (a.choiceIds.length) { out.prefix = "你刚才选择了："; out.text = labels(prev, a).join("、"); }
    }
    return out.bridge || out.text ? out : null;
  }

  function q(text) { return "「" + text + "」"; }

  function stepByKey(copy, key) {
    for (var i = 0; i < copy.steps.length; i++) if (copy.steps[i].key === key) return copy.steps[i];
    return null;
  }

  function linesFor(copy, answers, key) {
    var step = stepByKey(copy, key);
    var a = answers[key];
    if (!step || !hasAnswer(a)) return [];
    var ids = a.choiceIds;
    var ls = labels(step, a);
    var text = a.freeText.trim();
    var out = [];
    var textLine = text ? "你写下：" + q(text) : null;

    if (key === "reality") {
      if (ls.length) out.push("你选择了" + q(ls[0]) + "。");
    } else if (key === "feeling") {
      if (ids.length === 1 && ids[0] === "unclear") out.push("关于感受，你选择了" + q(ls[0]) + "。");
      else if (ls.length) out.push("想到这件事时，你心里最明显的感受是" + ls.map(q).join("和") + "。");
    } else if (key === "body") {
      if (ids[0] === "none") out.push("你没有注意到特别明显的身体反应。");
      else if (ids[0] === "unknown") out.push("身体这一步，你选择了" + q(ls[0]) + "。");
      else if (ls.length) out.push("身体上，你注意到" + q(ls[0]) + "。");
    } else if (key === "thought") {
      if (ids[0] === "other" && !text) out.push("你提到脑海里还有别的想法。");
      else if (ids[0] && ids[0] !== "other") out.push("你脑海里最先出现的想法是" + q(ls[0]) + "。");
      if (text) { out.push("你写下脑海里的一句话：" + q(text)); textLine = null; }
      if (ids.length || text) out.push("这是一个想法，不一定是已经确认的事实。");
    } else if (key === "impulse") {
      if (ids[0] === "unsure") out.push("关于回应，你选择了" + q(ls[0]) + "。");
      else if (ls.length) out.push("你通常的回应是" + q(ls[0]) + "。");
    } else if (key === "protection") {
      if (ids[0] === "unsure") out.push("你选择了" + q(ls[0]) + "。还不确定自己最在意什么，也没有关系。");
      else if (ls.length) out.push("你选择了" + q(ls[0]) + "作为你很在意的部分。");
    } else if (key === "awareness") {
      if (ids[0] === "confused") out.push("你选择了" + q(ls[0]) + "。还在整理中，也没有关系。");
      else if (ids[0] === "write_own") {
        if (text) { out.push("你用自己的话记录下：" + q(text)); textLine = null; }
        else out.push("你想用自己的话记录下来，这一次还没有写下。");
      } else if (ls.length) out.push("关于这次的发现，你选择了" + q(ls[0]) + "。");
    }
    if (textLine) out.push(textLine);
    return out;
  }

  var SECTIONS = [
    { k: "01 · 我正在面对", keys: ["reality"] },
    { k: "02 · 我的感受与反应", keys: ["feeling", "body", "thought", "impulse"] },
    { k: "03 · 我很在意的", keys: ["protection"] },
    { k: "04 · 我此刻的发现", keys: ["awareness"] }
  ];

  function buildNote(copy, answers) {
    var sections = [];
    SECTIONS.forEach(function (sec) {
      var lines = [];
      sec.keys.forEach(function (key) { lines = lines.concat(linesFor(copy, answers, key)); });
      if (lines.length) sections.push({ k: sec.k, lines: lines });
    });
    var lib = copy.reflectionLibrary;
    var p = answers.protection;
    var key = p && !p.skipped && p.choiceIds[0] && lib[p.choiceIds[0]] ? p.choiceIds[0] : "default";
    return {
      empty: sections.length === 0,
      intro: sections.length === 0 ? copy.labels.noAnswers : null,
      sections: sections,
      libraryKey: key,
      question: lib[key].questions[0],
      microAction: lib[key].actions[0]
    };
  }

  function noteText(copy, note) {
    var out = [copy.labels.resultTitle + " · SeeSoul Compass™", copy.labels.resultSubtitle, ""];
    if (note.intro) out.push(note.intro, "");
    note.sections.forEach(function (s) { out.push(s.k); s.lines.forEach(function (l) { out.push(l); }); out.push(""); });
    out.push("留给自己的一个问题", note.question, "", "今天可以试试的一件小事", note.microAction);
    return out.join("\n");
  }

  var api = {
    CRITICAL_TERMS: CRITICAL_TERMS,
    CONCERN_TERMS: CONCERN_TERMS,
    COPY_URL: COPY_URL,
    prepareCopy: prepareCopy,
    assessText: assessText,
    emptyAnswer: emptyAnswer,
    emptyAnswers: emptyAnswers,
    hasAnswer: hasAnswer,
    toggleChoice: toggleChoice,
    setText: setText,
    contextFor: contextFor,
    buildNote: buildNote,
    noteText: noteText
  };

  if (typeof module !== "undefined" && module.exports) { module.exports = api; return; }
  root.SeeSoulCompass = api;

  try { root.localStorage.removeItem(OLD_STORAGE_KEY); } catch (e) {}

  var app = document.getElementById("sscApp");
  if (!app) return;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function show(node, on) { node.hidden = !on; }

  function fail() {
    show($("sscLoading"), false);
    show($("sscQuestion"), false);
    show($("sscNav"), false);
    show($("sscError"), true);
  }

  fetch(COPY_URL, { cache: "no-cache", credentials: "omit" })
    .then(function (res) { if (!res.ok) throw new Error("copy " + res.status); return res.json(); })
    .then(start)
    .catch(fail);

  function start(raw) {
    if (!raw || !raw.steps || raw.steps.length !== 7) throw new Error("copy");
    var copy = prepareCopy(raw);
    var max = (copy.interaction && copy.interaction.freeTextMaxLength) || 280;
    var answers = emptyAnswers(copy);
    var confirmedSafe = {};
    var index = 0;
    var pendingAction = null;

    var qBox = $("sscQuestion"), nav = $("sscNav"), result = $("sscResult"), safety = $("sscSafety");
    var eyebrow = $("sscEyebrow"), title = $("sscTitle"), help = $("sscHelp");
    var ctx = $("sscContext"), ctxBridge = $("sscContextBridge"), ctxQuote = $("sscContextQuote");
    var ctxPrefix = $("sscContextPrefix"), ctxText = $("sscContextText");
    var list = $("sscOptions"), limit = $("sscLimit"), multi = $("sscMulti");
    var textToggle = $("sscTextToggle"), textPanel = $("sscTextPanel"), textLabel = $("sscTextLabel");
    var textBox = $("sscText"), count = $("sscCount");
    var progress = $("sscProgress"), dots = $("sscDots");
    var back = $("sscBack"), skip = $("sscSkip"), next = $("sscNext");

    textBox.maxLength = max;
    textToggle.textContent = copy.labels.freeText;
    skip.textContent = copy.labels.skip;
    back.textContent = copy.labels.back;
    multi.textContent = copy.labels.multipleHelp;

    for (var d = 0; d < copy.steps.length; d++) dots.appendChild(el("li"));

    function setTextOpen(open) {
      textToggle.setAttribute("aria-expanded", open ? "true" : "false");
      show(textPanel, open);
    }

    function updateCount() {
      count.textContent = "已写 " + textBox.value.length + " / " + max + " 字";
    }

    function render(focus) {
      var step = copy.steps[index];
      var a = answers[step.key];
      show($("sscLoading"), false);
      show(qBox, true);
      show(nav, true);
      show(safety, false);
      show(result, false);
      show($("sscTop"), true);

      progress.textContent = copy.labels.progress.replace("{current}", index + 1);
      Array.prototype.forEach.call(dots.children, function (li, i) {
        li.className = i < index ? "is-done" : (i === index ? "is-current" : "");
      });

      eyebrow.textContent = step.eyebrow;
      title.textContent = step.title;
      help.textContent = step.help;

      var c = contextFor(copy, answers, index);
      ctxBridge.textContent = c ? c.bridge : "";
      show(ctxBridge, !!(c && c.bridge));
      ctxPrefix.textContent = c ? c.prefix : "";
      ctxText.textContent = c ? c.text : "";
      ctxText.title = c ? c.text : "";
      show(ctxQuote, !!(c && c.text));
      show(ctx, !!c);

      show(multi, step.selectMax > 1);
      limit.textContent = "";
      while (list.firstChild) list.removeChild(list.firstChild);
      step.choices.forEach(function (choice) {
        var b = el("button", "option", null);
        b.type = "button";
        b.setAttribute("data-choice", choice.id);
        b.setAttribute("aria-pressed", a.choiceIds.indexOf(choice.id) >= 0 ? "true" : "false");
        b.appendChild(el("span", null, choice.label));
        b.addEventListener("click", function () { onChoice(step, choice.id); });
        list.appendChild(b);
      });

      textLabel.textContent = step.freeTextLabel;
      textBox.value = a.freeText;
      updateCount();
      setTextOpen(a.freeText !== "" || (step.key === "awareness" && a.choiceIds[0] === "write_own"));

      back.style.visibility = index === 0 ? "hidden" : "visible";
      next.textContent = index === copy.steps.length - 1 ? copy.labels.final : copy.labels.next;

      if (focus) { window.scrollTo(0, 0); title.focus(); }
    }

    function onChoice(step, id) {
      var a = answers[step.key];
      var r = toggleChoice(step, a, id);
      if (!r.ok && r.reason === "max") {
        limit.textContent = copy.labels.multipleHelp + "。如果想换一项，请先取消一个已选的。";
        return;
      }
      limit.textContent = "";
      Array.prototype.forEach.call(list.children, function (b) {
        b.setAttribute("aria-pressed", a.choiceIds.indexOf(b.getAttribute("data-choice")) >= 0 ? "true" : "false");
      });
      if (step.key === "awareness" && id === "write_own" && a.choiceIds[0] === "write_own") {
        setTextOpen(true);
        textBox.focus();
      }
    }

    textToggle.addEventListener("click", function () {
      var open = textToggle.getAttribute("aria-expanded") !== "true";
      setTextOpen(open);
      if (open) textBox.focus();
    });
    function toSafety() {
      answers = emptyAnswers(copy);
      textBox.value = "";
      ctxText.textContent = "";
      while ($("sscResultBody").firstChild) $("sscResultBody").removeChild($("sscResultBody").firstChild);
      app.style.display = "none";
      window.location.replace(SAFETY_PAGE);
    }

    function onText(e) {
      setText(answers[copy.steps[index].key], textBox.value, max);
      updateCount();
      if (e && e.isComposing) return;
      if (assessText(textBox.value) === "CRITICAL") toSafety();
    }
    textBox.addEventListener("input", onText);
    textBox.addEventListener("compositionend", onText);

    function safetyGate(texts, then) {
      var level = "NONE";
      texts.forEach(function (t) {
        var s = assessText(t.text);
        if (s === "CRITICAL") level = "CRITICAL";
        else if (s === "CLARIFY" && level === "NONE" && confirmedSafe[t.key] !== t.text) level = "CLARIFY";
      });
      if (level === "CRITICAL") { toSafety(); return; }
      if (level === "CLARIFY") {
        pendingAction = function () { texts.forEach(function (t) { confirmedSafe[t.key] = t.text; }); then(); };
        show(qBox, false);
        show(nav, false);
        show(safety, true);
        window.scrollTo(0, 0);
        $("sscSafetyTitle").focus();
        return;
      }
      then();
    }

    $("sscSafetyHelp").addEventListener("click", toSafety);
    $("sscSafetyOk").addEventListener("click", function () {
      var go = pendingAction;
      pendingAction = null;
      if (go) go();
    });

    function advance() {
      if (index < copy.steps.length - 1) { index++; render(true); return; }
      var all = copy.steps.map(function (s) { return { key: s.key, text: answers[s.key].freeText }; });
      safetyGate(all, showResult);
    }

    function current() { var k = copy.steps[index].key; return [{ key: k, text: answers[k].freeText }]; }

    next.addEventListener("click", function () {
      var a = answers[copy.steps[index].key];
      a.skipped = false;
      safetyGate(current(), advance);
    });
    skip.addEventListener("click", function () {
      safetyGate(current(), function () {
        var k = copy.steps[index].key;
        answers[k] = emptyAnswer();
        answers[k].skipped = true;
        advance();
      });
    });
    back.addEventListener("click", function () {
      if (index > 0) { index--; render(true); }
    });

    function showResult() {
      var note = buildNote(copy, answers);
      show(qBox, false);
      show(nav, false);
      show(safety, false);
      show($("sscTop"), false);
      $("sscResultTitle").textContent = copy.labels.resultTitle;
      $("sscResultSubtitle").textContent = copy.labels.resultSubtitle;

      var body = $("sscResultBody");
      while (body.firstChild) body.removeChild(body.firstChild);
      if (note.intro) {
        var intro = el("section", "result-section");
        intro.appendChild(el("p", "ssc-result-intro", note.intro));
        body.appendChild(intro);
      }
      note.sections.forEach(function (s) {
        var sec = el("section", "result-section");
        sec.appendChild(el("h2", "k", s.k));
        s.lines.forEach(function (l) { sec.appendChild(el("p", "ssc-line", l)); });
        body.appendChild(sec);
      });
      var qs = el("section", "result-section");
      qs.appendChild(el("h2", "k", "留给自己的一个问题"));
      qs.appendChild(el("div", "result-question", note.question));
      body.appendChild(qs);
      var act = el("section", "result-section action-card");
      act.appendChild(el("h2", "k", "今天可以试试的一件小事"));
      act.appendChild(el("p", null, note.microAction));
      body.appendChild(act);

      $("sscCopy").textContent = copy.labels.copyResult;
      $("sscRestart").textContent = copy.labels.restart;
      $("sscCopyStatus").textContent = "";
      show(result, true);
      window.scrollTo(0, 0);
      $("sscResultTitle").focus();
      result._text = noteText(copy, note);
    }

    function fallbackCopy(text) {
      var t = document.createElement("textarea");
      t.value = text;
      t.setAttribute("readonly", "");
      t.style.position = "fixed";
      t.style.opacity = "0";
      document.body.appendChild(t);
      t.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(t);
      return ok;
    }

    $("sscCopy").addEventListener("click", function () {
      var text = result._text || "";
      var status = $("sscCopyStatus");
      function done(ok) {
        status.textContent = ok ? "已复制。它现在在你的剪贴板里，粘贴到哪里由你决定。" : "这个浏览器没能复制。你可以直接选中上面的文字，手动复制。";
      }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(fallbackCopy(text)); });
      } else {
        done(fallbackCopy(text));
      }
    });
    $("sscRestart").addEventListener("click", function () {
      answers = emptyAnswers(copy);
      confirmedSafe = {};
      index = 0;
      render(true);
    });
    $("sscEdit").addEventListener("click", function () {
      index = copy.steps.length - 1;
      render(true);
    });

    render(false);
  }
})(typeof window !== "undefined" ? window : this);
