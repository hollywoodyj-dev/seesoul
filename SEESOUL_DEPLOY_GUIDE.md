# SEE SOUL 原型站上线 seesoul.com 部署手册

目标：把 seesoul-prototype（生命映照原型站，纯静态）上线到正式域名 **seesoul.com**，
并将旧 Wix 官网 **seesoulpsychotherapy.com** 一并处置。
当前原型站在扣子预览域：https://yfpsmg8db2.page.coze.site/ （仅供内部，不能绑正式域名）。

---

## 一、DNS 现状（2026-09-24 探测）

| 域名 | 当前解析 | 归属 | 说明 |
|---|---|---|---|
| seesoul.com | A → 160.153.61.201 | GoDaddy 托管 | 正式目标域名，在 GoDaddy 注册+托管 |
| www.seesoul.com | CNAME → seesoul.com | GoDaddy | 同上 |
| seesoulpsychotherapy.com | A → 185.230.63.107 | Wix | 现有心理咨询官网 |
| www.seesoulpsychotherapy.com | CNAME → wixdns.net | Wix | 同上 |

结论：
- **seesoul.com 使用 GoDaddy 托管** → 上线时需在 GoDaddy 面板改 DNS 到新托管平台。
- **seesoulpsychotherapy.com 使用 Wix** → 处置方式见下文。

---

## 二、推荐路径：静态托管 + DNS 指向

扣子 Pages 不支持绑定自定义域名，因此正式上线必须走第三方静态托管平台。
我们推荐 **Cloudflare Pages**（免费、全球 CDN、可同时托管两个域名的 DNS），
也可用 Netlify / Vercel（同样免费、支持自定义域名）。

### 第 1 步：准备静态站文件
已打包：`seesoul-site-static.tar.gz`（9.4MB，含 index.html 入口，
不含 cli 配置 `.coze`）。解压后把 `site/` 目录内容作为站点根目录上传。

### 第 2 步：在 Cloudflare Pages 部署
1. 注册/登录 Cloudflare → 左侧「Workers & Pages」→「Create」
2. 选 Pages → Connect to Git（推荐，后续更新方便）
   或 Upload assets（直接拖 `seesoul-site-static.tar.gz` 解压后的文件）
3. 项目名如 `seesoul-site`，首次部署完成会获得子域 `seesoul-site.pages.dev`

### 第 3 步：把 seesoul.com 指向 Cloudflare
在 Cloudflare 添加 seesoul.com（Add a domain，会引导你改 GoDaddy 的 NS）
或使用 Cloudflare 的 CNAME setup（不改 NS，只加 DNS 记录）：

- 方式一（推荐）**代理托管**：把 seesoul.com 的域名服务器 NS 改成 Cloudflare 分配的
  两个 NS（在 GoDaddy 域名管理 → 名称服务器里改），然后在 Cloudflare 添加 DNS 记录：
  - `A  seesoul.com  → 1.2.3.4`（Cloudflare Pages 分配的 IP，按 Pages 提示填）
  - `CNAME  www  → seesoul-site.pages.dev`
  - 或直接用 Pages 的「Custom domains」绑定，Cloudflare 会自动配 CNAME + HTTPS
- 方式二 **不改 NS**：在 GoDaddy 直接加一条 CNAME：
  - `CNAME  www  → seesoul-site.pages.dev`
  - 根域名 seesoul.com 若 GoDaddy 不支持 CNAME flatten，需用 A 记录指向平台 IP

### 第 4 步：HTTPS
Cloudflare 自动签发 SSL 证书。绑定自定义域名后约几分钟内生效，
线上即显示为 `https://seesoul.com`。

### 第 5 步：验收
- https://seesoul.com 及 https://www.seesoul.com 均返回 200 且指向新站
- 检查首页、导航、页脚 LOGO、自我探索四篇文章、compass/life-theme 流程可访问
- 资源（assets/*.png、theme.css、lt-*.js）均 200

---

## 三、旧 Wix 官网 seesoulpsychotherapy.com 的处置（二选一）

> 注意：旧站是真实运营的心理咨询预约官网（有付费预约）。**下线前建议先导出/备份
> 服务信息、价格、联系方式**，避免业务中断或客户流失。

**方案 A（推荐）· 整站指向新站**
在 Wix（或 Wix 使用的注册商）把 seesoulpsychotherapy.com 的 DNS 也指向 Cloudflare
Pages 的同一站点，使旧域名访问到新原型站。适合「品牌统一，全站换成 SEE SOUL 新体系」。

**方案 B · 保留咨询业务，仅换主品牌域名**
seesoulpsychotherapy.com 保留在 Wix 继续做心理咨询预约业务；
生命周期映照新站单独挂 seesoul.com。两者并存，域名各司其职。

> 你此前选择「一并处理」，默认按**方案 A（都指向新站）**执行；
> 若你倾向方案 B，告诉我，我调整手册。

---

## 四、更新流程（后续改版上线）

每次改版推送方法：
1. 更新 seesoul-prototype 源码（本地/我这边改好）
2. 重新生成静态包，push 到 Cloudflare 接的 Git 仓库 → 自动重新构建部署
   或重新 Upload assets 覆盖
3. 几分钟内线上 seesoul.com 自动更新（Cloudflare 全球 CDN）

---

## 五、回滚
Cloudflare Pages 保留历史部署，出问题时在控制台点「Rollback to this deployment」
即可回退上一版本，无需改 DNS。

---

### 需要你提供 / 操作的部分
1. **GoDaddy 面板**：改 seesoul.com 的 NS 或加 CNAME（需你登录 GoDaddy 账号操作）
2. **Cloudflare 账号**：注册并添加域名（或告诉我你已有 Netlify/Vercel 账号也行）
3. 若走方案 A，还需处理 **Wix** 侧 seesoulpsychotherapy.com 的 DNS

这三步涉及你在注册商/平台的独立账号，我无法代登录操作；其余部署与打包我已备好。