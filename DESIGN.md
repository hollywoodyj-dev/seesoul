# 设计契约 — SEESOUL 熙愈心空间 · 中文网站

## 目标

为 SeeSoul 中文网站交付 Gate 3 视觉方向的高保真可运行原型，供创始人像设计总监一样逐屏评审。

- 产品：SeeSoul 熙愈心空间 —— 一个帮助用户理解自己、整理生命、并重新找到选择的心空间。
- 受众：正在经历情绪、关系、家庭、自我价值、人生方向困扰的简体中文用户；部分用户说不太清自己怎么了（PATH B）。
- 核心任务：用户 10 秒内看懂"SeeSoul 能帮我处理什么"；通过现实问题入口或 SeeSoul Compass™ 找到下一步；不靠强销售转化。
- 交付平台：Web（桌面端 + 移动端响应式）。视觉以"真实可打开页面"交付，供逐屏审查"清楚·温暖·安静·专业·深"是否成立。

## 视觉方向

- 类别自洽：**人的心空间**，不是疗愈冥想站、占星塔罗站、奢侈品 SPA、医疗诊所、通用咨询师模板。
- 标志性元素：克制的**柔和金线 + 深 Navy 上的微弱暖光**。一条贯穿首页的细金分隔线与问题卡的温和金描边，制造"安静、被托住"的情绪，而非炫技。
- 页面节奏：深 Navy 与 Warm Ivory 交替段落，大幅留白，正文阅读宽度受限，非对称构图 + 大体量标题字号（桌面端）。
- 动效：仅允许轻微 Fade、Gentle reveal、柔和金辉、Compass 进度转场。基线遵守 `prefers-reduced-motion`。

## 设计令牌（Token）

- 色彩（唯一事实源在 theme.css）：
  - Deep Navy `#18263f` / 近黑 `#0f1526`（主色）
  - Muted Premium Gold `#b79a63` / 柔和金 `#d6c39f`（强调，克制使用）
  - Warm Ivory `#f4f0e6` / 深一档 `#ebe4d4`（背景）
  - Soft dusk pink `#c09aa8` / muted purple `#9d8aa8`（极低比例辅助，仅在个别体现"温暖"处点缀）
- 字体：
  - 正文 `--font-body`：现代高可读中文 Sans（Noto Sans SC / PingFang / Microsoft YaHei + system-ui）
  - 标题 `--font-display`：优雅中文 Serif（Noto Serif SC / Songti SC），英文 Editorial Serif + Clean Sans
  - 移动端不让过细过小字号。
- 间距：`--space-unit: 0.25rem`，按语义章节使用大段留白。
- 圆角：克制（卡片 `--radius-lg`），整体偏"纸面、安静"而非"圆润泡泡"。

## 共享壳层

- 顶部导航（桌面）：SEESOUL Logo（金色字标，不重新设计 Logo，仅用文字占位近似）+ 首页｜心理咨询｜生命课题｜SeeSoul Compass｜自我探索｜认识 SeeSoul ＋ 右侧"预约咨询"金按钮。
- 导航标签全部指向真实页面；"不知道从哪里开始"不进导航，仅出现在英雄区/问题卡/内容底部/移动端 CTA。
- 移动端：Logo + ☰ 菜单；顶部保留轻量"预约 / Compass"CTA。
- 底部：SEESOUL + 说明文字 + 主要"预约 / Compass"入口，Footer 带 "Seeing Before Being™"。
- 响应式：窄屏重排为单列、2 列问题卡、导航折叠为抽屉菜单。

## 页面

- `index.html` — `home`（入口）｜首页。Hero → 问题卡 → Compass → 服务 → 真实例子 → 方法层 → 内容 → 创始人/信任/FAQ → Final CTA。
- `compass-start.html` — `compass-start`｜Compass 起始 + Orientation（为什么来到这里）。
- `compass-question.html` — `compass-question`｜Seven Layers 问答流程（一次一屏、进度 3/7、返回上一题）。
- `compass-result.html` — `compass-result`｜结果页「此刻的你」（看见当下→值得再看看→Reflection Question→今天可以试试→下一步）。
- `counselling.html` — `counselling`｜心理咨询页（Hero + 服务流程 + 议题 + 费用/保密 + 预约）。
- `life-theme.html` — `life-theme`｜生命课题解读页（去神秘化：先讲"不是算命"→现实问题→模式整理→预约）。
- `explore.html` — `explore`｜自我探索内容 Hub（分类 chips + Popular Questions + Guides + Wisdom + Exercises + Deep Reads）。

## 状态与交互

- 可演示已约定流程（Compass 的隔屏推进、问题卡跳转、FAQ 手风琴、移动端菜单）。
- 锚点：问题卡 `home.problem-card.情绪` 等、Compass 进度等，供后续迭代定位。
- 导航用普通相对链接；浮层用 `aria-controls` + `id`；键盘焦点可见；支持减少动态效果。

## 资产与来源

- 全部视觉由 CSS Token 表达，无外部图片依赖（保持原型无依赖、可离线打开）。
- 不嵌入真实敏感数据；文案使用蓝图与 SeeSoul 既定话语体系。
- 本原型为 Gate 3 视觉评审用，**非生产实现**；Logo 以金色文字字标近似占位，正式 Logo 资产待完成后替换。