/* ===================================================================
   SeeSoul Life Theme Cards™ · v0.1 数据 + 独立随机抽牌引擎
   —— 本文件只包含 Founder 已授权的 Card ID / Domain / 中英名 ——
   —— 深层语义（archetype/life_question/possible_expression…）均为
      FOUNDER CONTENT REQUIRED，本文件【不】生成、不填充任何解释 ——
   Domain:
   I SELF · II RELATIONSHIP · III FAMILY · IV SAFETY ·
   V VALUE · VI CHOICE · VII MEANING · SEEING · CHOOSING
   =================================================================== */
window.LT_CARDS = [
  // I · SELF｜自我（6）
  { id: 1, domain: "SELF", zh: "被看见", en: "Seen" },
  { id: 2, domain: "SELF", zh: "真实", en: "Authenticity" },
  { id: 3, domain: "SELF", zh: "身份", en: "Identity" },
  { id: 4, domain: "SELF", zh: "自我怀疑", en: "Self-Doubt" },
  { id: 5, domain: "SELF", zh: "接纳", en: "Acceptance" },
  { id: 6, domain: "SELF", zh: "成为", en: "Becoming" },
  // II · RELATIONSHIP｜关系（6）
  { id: 7, domain: "RELATIONSHIP", zh: "靠近", en: "Closeness" },
  { id: 8, domain: "RELATIONSHIP", zh: "距离", en: "Distance" },
  { id: 9, domain: "RELATIONSHIP", zh: "依附", en: "Attachment" },
  { id: 10, domain: "RELATIONSHIP", zh: "失去", en: "Loss" },
  { id: 11, domain: "RELATIONSHIP", zh: "投射", en: "Projection" },
  { id: 12, domain: "RELATIONSHIP", zh: "互惠", en: "Reciprocity" },
  // III · FAMILY｜家庭（6）
  { id: 13, domain: "FAMILY", zh: "归属", en: "Belonging" },
  { id: 14, domain: "FAMILY", zh: "承担", en: "Carrying" },
  { id: 15, domain: "FAMILY", zh: "忠诚", en: "Loyalty" },
  { id: 16, domain: "FAMILY", zh: "边界", en: "Boundary" },
  { id: 17, domain: "FAMILY", zh: "角色", en: "Role" },
  { id: 18, domain: "FAMILY", zh: "分化", en: "Differentiation" },
  // IV · SAFETY｜安全（6）
  { id: 19, domain: "SAFETY", zh: "控制", en: "Control" },
  { id: 20, domain: "SAFETY", zh: "警觉", en: "Vigilance" },
  { id: 21, domain: "SAFETY", zh: "逃避", en: "Avoidance" },
  { id: 22, domain: "SAFETY", zh: "抓住", en: "Holding" },
  { id: 23, domain: "SAFETY", zh: "保护", en: "Protection" },
  { id: 24, domain: "SAFETY", zh: "信任", en: "Trust" },
  // V · VALUE｜价值（6）
  { id: 25, domain: "VALUE", zh: "证明", en: "Proving" },
  { id: 26, domain: "VALUE", zh: "认可", en: "Approval" },
  { id: 27, domain: "VALUE", zh: "比较", en: "Comparison" },
  { id: 28, domain: "VALUE", zh: "羞耻", en: "Shame" },
  { id: 29, domain: "VALUE", zh: "匮乏", en: "Scarcity" },
  { id: 30, domain: "VALUE", zh: "值得", en: "Worthiness" },
  // VI · CHOICE｜选择（6）
  { id: 31, domain: "CHOICE", zh: "讨好", en: "Pleasing" },
  { id: 32, domain: "CHOICE", zh: "责任", en: "Responsibility" },
  { id: 33, domain: "CHOICE", zh: "自由", en: "Freedom" },
  { id: 34, domain: "CHOICE", zh: "代价", en: "Cost" },
  { id: 35, domain: "CHOICE", zh: "行动", en: "Action" },
  { id: 36, domain: "CHOICE", zh: "主权", en: "Sovereignty" },
  // VII · MEANING｜意义（6）
  { id: 37, domain: "MEANING", zh: "重复", en: "Repetition" },
  { id: 38, domain: "MEANING", zh: "转折", en: "Transition" },
  { id: 39, domain: "MEANING", zh: "未知", en: "Not Knowing" },
  { id: 40, domain: "MEANING", zh: "失义", en: "Meaninglessness" },
  { id: 41, domain: "MEANING", zh: "方向", en: "Direction" },
  { id: 42, domain: "MEANING", zh: "意义", en: "Meaning" },
  // INTEGRATION CARDS（整合卡 2）
  { id: 43, domain: "INTEGRATION", zh: "看见", en: "Seeing" },
  { id: 44, domain: "INTEGRATION", zh: "选择", en: "Choosing" }
];

/* — 独立随机抽牌：与 1320 完全无关 —— */
window.LT_drawThree = function () {
  var pool = window.LT_CARDS.slice();
  // Fisher–Yates
  for (var i = pool.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var t = pool[i]; pool[i] = pool[j]; pool[j] = t;
  }
  return [pool[0], pool[1], pool[2]]; // = Three Mirrors 三张（此刻在场/可能在重复/什么变得可能）
};

/* — 简易状态存取（原型用 sessionStorage，不落长期数据）—— */
window.LT_store = function (k, v) { try { sessionStorage.setItem("lt_" + k, JSON.stringify(v)); } catch (e) {} };
window.LT_load = function (k, d) { try { var v = sessionStorage.getItem("lt_" + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } };
window.LT_clear = function () { try { sessionStorage.removeItem("lt_topic"); sessionStorage.removeItem("lt_topicText"); sessionStorage.removeItem("lt_draw"); sessionStorage.removeItem("lt_reso"); } catch (e) {} };

/* ===================================================================
   W05 · 1320_CONTEXT 统一访问器（消除 legacy S1 手选依赖）
   —— 唯一结构来源：1320_CONTEXT
   · CALCULATED : DOB provided，经 1320 calculator 得到 s1/s3/s2/s0
   · NOT_USED   : DOB absent 或 1320 calculator 尚未接入（PENDING）
   —— 绝不 hardcode 默认 S1；未接入时走「这次不参与」占位路径
   =================================================================== */
window.LT_1320_NONE = { status: "NOT_USED", note: "PENDING_IMPLEMENTATION" };
window.LT_1320Context = function () {
  try {
    var raw = sessionStorage.getItem("lt_1320");
    if (!raw) return window.LT_1320_NONE;
    var c = JSON.parse(raw || "{}");
    if (c && c.status === "CALCULATED" && c.s1 != null) return c;
    return window.LT_1320_NONE;
  } catch (e) { return window.LT_1320_NONE; }
};
window.LT_1320S1 = function () { var c = window.LT_1320Context(); return (c && c.status === "CALCULATED") ? c.s1 : null; };
window.LT_1320Name = function () { var c = window.LT_1320Context(); return (c && c.status === "CALCULATED" && c.display_name) ? c.display_name : ""; };

/* — 1320 区域无 S1 时面向用户的占位文案（温和、不引导、不假装已接入）—— */
window.LT_1320_PLACEHOLDER = "这一层观察角度（1320）这次不参与。它不会影响你抽到哪三张牌，也不会影响你本轮的共鸣与反思——它只是 SeeSoul 在完成 Life Theme 时可能会请你看的一面镜子，等你需要时再加入。";

window.LT_cardById = function (id) {
  for (var i = 0; i < window.LT_CARDS.length; i++) if (window.LT_CARDS[i].id === Number(id)) return window.LT_CARDS[i];
  return { id: id, zh: "待定", en: "" };
};

/* — Three Mirrors 官方三结构（锁）—— */
window.LT_MIRRORS = [
  { key: "present",    zh: "此刻正在发生什么？", en: "What Is Present",       order: 1 },
  { key: "repeating",  zh: "什么似乎正在重复？", en: "What May Be Repeating", order: 2 },
  { key: "possible",   zh: "当我看见以后，有什么新的可能？", en: "What Becomes Possible", order: 3 }
];