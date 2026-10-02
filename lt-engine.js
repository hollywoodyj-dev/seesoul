/* ===================================================================
   SeeSoul Life Theme · S1 Matching Engine v0.1  ——  FOUNDER APPROVED Phase A
   输入：S1 Profile + 独立随机抽到的 3 张卡 + Current Experience(topic)
   分层：
     A3-O/T/I、A2  = S1 静态 affinity（Founder 批准，权威 Registry）
     A1 Contextual = 运行时动态层，由 S1 × Current Experience 产生
     A0             = 默认不预设
   最高治理规则：
     USER_RESONANCE > S1_AFFINITY（本引擎只产出「值得看看」的可能方向，
     最终是否贴近由用户在 Resonance Gate 决定；用户说「不太像我」→ 放下）
   面向用户：
     绝不暴露 affinity 数值/layer 名，只用 SeeSoul 语言呈现「可能的方向」。
   来源追溯：
     每个方向带 source：S1_STATIC_AFFINITY / A1_CONTEXTUAL_ACTIVATION / CARD_DRAW，
     内部记录在 lt_engine，永不合并成不透明的「AI 结论」。
   =================================================================== */

/* —— Current Experience 语境信号层（v0.1 占位，可 Founder 校准）——
   说明：这是“话题 → 该领域可能被唤起的一组候选卡”的上下文信号表，
   属于引擎的 Current Experience 检测层，不是卡牌含义，也不代表“命中即结论”。
   A1 仅当“抽到的某张卡命中此领域候选、且该卡不是 S1 静态 affinity(A3/A2)”
   时才激活为 contextual；否则保持关闭，绝不硬造弱关联去填满矩阵。
   —— Founder 后续可替换/校准此表 ——
*/
window.LT_CONTEXT_TOPIC = {
  "情绪":       [7, 8, 9, 28, 30],
  "关系":       [8, 11, 12, 16, 20, 31],
  "家庭":       [13, 14, 15, 16, 17, 18],
  "自己":       [1, 2, 3, 4, 5, 6, 37],
  "工作 · 方向": [35, 41, 33, 34, 32],
  "价值感":     [25, 26, 27, 28, 29, 30],
  "意义":       [37, 38, 40, 41, 42, 43],
  "说不清楚":   [4, 37, 39, 40]
};

/* —— 该角色在面向用户时的人性化措辞（解释 A3/A2/A1 的角色，不解释卡牌含义）—— */
window.LT_ROLE_LANG = {
  origin:      "这是你一贯比较自然的力量方向。",
  tension:     "当这股力量失衡或紧绷时，可能会以这样的张力出现。",
  integration: "更成熟、更缓和一些的表达，可能往这个方向走。",
  secondary:   "另一个相关、但未必是这个结构核心的方向。",
  contextual:  "在今天带来的经验里，这个方向似乎被轻轻提了一下。"
};

/* —— S1 静态反射结构（A3 + A2），Founder 批准，原样读取 —— */
window.LT_structure = function (sid) {
  var s1 = window.LT_S1_byId(sid);
  if (!s1) return null;
  var out = [];
  out.push({ role: "origin",      card: window.LT_cardById(s1.A3_O_ORIGIN.card_id) });
  out.push({ role: "tension",     card: window.LT_cardById(s1.A3_T_TENSION.card_id) });
  out.push({ role: "integration", card: window.LT_cardById(s1.A3_I_INTEGRATION.card_id) });
  (s1.A2_SECONDARY || []).forEach(function (x) {
    out.push({ role: "secondary", card: window.LT_cardById(x.card_id) });
  });
  return { s1: s1, structure: out };
};

/* —— 判断卡 id 是否属于某个 S1 的静态 affinity（A3∪A2）—— */
window.LT_isStatic = function (sid, cardId) {
  var s1 = window.LT_S1_byId(sid);
  if (!s1) return false;
  var ids = [s1.A3_O_ORIGIN.card_id, s1.A3_T_TENSION.card_id, s1.A3_I_INTEGRATION.card_id]
    .concat((s1.A2_SECONDARY || []).map(function (x) { return x.card_id; }));
  return ids.indexOf(Number(cardId)) !== -1;
};

/* —— A1 动态 Contextual 激活：
   抽到的卡若命中 topic 领域候选、且不属于 S1 静态 affinity → 激活为 contextual —— */
window.LT_contextual = function (sid, drawnCards, topic) {
  var cands = (window.LT_CONTEXT_TOPIC[topic] || []);
  var out = [];
  (drawnCards || []).forEach(function (c) {
    var id = Number(c.id);
    if (cands.indexOf(id) !== -1 && !window.LT_isStatic(sid, id)) {
      out.push(c);
    }
  });
  return out;
};

/* —— 当轮“抽到的卡 ∩ S1 静态 affinity”的强呼应信号 —— */
window.LT_drawHits = function (sid, drawnCards) {
  var s1 = window.LT_S1_byId(sid);
  if (!s1) return [];
  var map = {};
  map[s1.A3_O_ORIGIN.card_id] = "origin";
  map[s1.A3_T_TENSION.card_id] = "tension";
  map[s1.A3_I_INTEGRATION.card_id] = "integration";
  (s1.A2_SECONDARY || []).forEach(function (x) { map[x.card_id] = "secondary"; });
  var out = [];
  (drawnCards || []).forEach(function (c) {
    if (map[c.id]) out.push({ card: c, layer: map[c.id], source: "S1_STATIC_AFFINITY" });
  });
  return out;
};

/* —— 汇总匹配结果（供 1320 区域与共鸣页使用）—— */
window.LT_match = function (sid, drawnCards, topic) {
  var base = window.LT_structure(sid);
  if (!base) return null;
  var drawHits = window.LT_drawHits(sid, drawnCards);
  var contextual = window.LT_contextual(sid, drawnCards, topic);
  // 结果仅作界面上屏用，永不暴露 affinity 数值
  return {
    s1: base.s1,
    structure: base.structure,          // A3-O/T/I + A2（1320 反射结构）
    drawHits: drawHits,                 // 抽到的牌 ∩ S1 静态（当轮强呼应）
    contextual: contextual              // A1 动态激活（当前体验唤起）
  };
};

/* —— 1320 区域面向用户的 SeeSoul 语言开场（可复用在 map 与共鸣）—— */
window.LT_LENS_OPEN = "从你的 1320 结构和今天带来的经验来看，有几个方向似乎值得放在一起看看。";