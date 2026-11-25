# 06 本仓库脱敏扫描与验收报告

> 对象：`JasonBeam/homelab-panel`（本仓库）。
> 分类：【我方已验证】。扫描时间：2026-11-25（Asia/Shanghai）。
> **本报告只含类型、路径、行号、计数，不含任何真实值。**

## 1. 结论

| 检查 | 结果 |
|---|---|
| 脱敏验收门 `tools/verify-sanitized.py` | **residual_findings = 0**（最终：scanned_files=92，skipped_gitignored=2，skipped_tooling=3） |
| gitleaks 8.30.1 默认规则（dir） | **0 leaks**（最终扫描 ~741 KB） |
| gitleaks 自定义中文/节点规则（dir，无白名单） | 14 命中（首轮 64 文件）→ **逐条判定全部为文档占位符或代码 API 名**（见 §3） |
| gitleaks 本仓库配置（含占位符白名单） | **0 leaks**（最终扫描 ~637 KB） |
| 压缩包递归检查 | **无压缩包**（0 个 .tgz/.tar/.gz/.zip/.age/.7z/.rar） |
| 图片与文件元数据检查 | **无图片/PDF/Office 文件**（0 个）→ 无 EXIF 风险 |
| 隐藏文件检查 | 仅 `.gitignore`（1 个）；无 .env/.DS_Store/其他 dotfile |
| `.env` 与数据库检查 | **0 个** .env / .db / .sqlite / .wal / .shm |
| 私钥/证书检查 | **0 个** .pem / .key / .p12 / .pfx / .crt / .cer / id_* |
| GitHub Actions 安全检查 | **无 .github 目录**，0 个工作流 |
| Git hooks | 仅 sample，**0 个 active hook** |
| 子模块 / LFS / gitlink | **无** .gitmodules、无 LFS、无 gitlink |
| 可执行文件 | **0 个**（本仓库不含任何可执行脚本） |
| Git 历史 | 全新 `git init`，**不继承参考项目历史**；提交后需复扫（见 §6） |

## 2. 扫描范围与方法

- 验收门：正则启发式，覆盖 IPv4/IPv6（排除 RFC5737 文档网段 + RFC1918 + loopback/CGNAT + 2001:db8）、非白名单域名、非 example 邮箱、UUID、SS2022 密钥、PEM 私钥、age 密钥、Telegram token、+86 手机号、订阅 URL token、REALITY private_key、密码赋值。
- **默认跳过 gitignore 文件**（`local/` 下的真实对照表不入库，故不参与验收）。
- gitleaks：默认规则 + 自定义规则（`tools/gitleaks-custom-rules.toml`），`--redact` 确保报告不含值。
- 人工复核：对每条命中打印**掩码后**的上下文判定性质，绝不回显原值。

## 3. 自定义规则 14 条命中的逐条判定

| 规则 | 条数 | 位置 | 判定 |
|---|---|---|---|
| uuid-v4 | 5 | templates/singbox/vless-reality.json、templates/subscription/clash-subscription.example.yaml、knowledge/ATTRIBUTION.md、knowledge/03、reports/02 | **全零文档示例 UUID** `00000000-0000-4000-8000-000000000000`，非真实凭据 |
| cn-password-assignment | 3 | templates/subscription/clash-subscription.example.yaml | `<EXAMPLE_*>` 占位符 |
| cn-password-assignment | 1 | templates/docker/env.example | `WEBDAV_PASSWORD=<EXAMPLE_PASSWORD>` |
| cn-password-assignment | 2 | reports/04-danger-audit.md | 已脱敏为 `<EXAMPLE_PASSWORD>`（原为参考项目 compose 中的凭据字段，**值已移除**） |
| generic-secret-assignment | 1 | knowledge/06-token-auth-user-management.md | `secrets.token_hex(16)` —— **Python API 名**，非凭据 |
| cn-password-assignment | 1 | local/audit-notes.md | **gitignore，不入库**；复核为 UI 控件类型描述（`password=...showPassword`），非凭据 |
| generic-secret-assignment | 1 | local/audit-notes.md | **gitignore，不入库** |

**新增 3 条（panels/ 与 reports/07 纳入后）**：

| 规则 | 条数 | 位置 | 判定 |
|---|---|---|---|
| cn-password-assignment | 2 | reports/07-inclusion-manifest.md:64 | **变量赋值代码表达式**（非真实口令）：`password=settings.webdav_password or ""`、`self.password = password` |
| cn-password-assignment | 1 | reports/06-scan-acceptance.md:42 | 本报告自身描述 UI 控件类型 `password=...showPassword`，非凭据 |

**结论：0 条真实凭据。** 白名单只收录上述明确的文档占位符、API 名与**逐字引用的代码表达式**（精确字符串匹配，非通配放宽），未放宽任何检测规则。

## 4. 本轮主动脱敏动作

| 动作 | 数量 | 说明 |
|---|---|---|
| 真实作者邮箱 → `<ORIGINAL_AUTHOR_EMAIL>` | 6 处 / 3 文件 | commit 作者元数据描述中的学校邮箱与个人邮箱 |
| 真实姓名 → 「原作者」 | 6 处 | 保留 GitHub 账号 handle 用于来源归属 |
| launchd label 个人标识 → `com.<ORIGINAL_AUTHOR>.` | 83 处 | reports/04 |
| 参考项目凭据字段值 → `<EXAMPLE_PASSWORD>` | 2 处 | reports/04 |
| kb 草稿非白名单域名 → 占位符 | 4 处 | 见 knowledge/ATTRIBUTION.md |

**保留项（ deliberate ）**：上游仓库 handle `JimmyChan233/homelab` 作为**技术来源归属**保留（用户要求"保留必要的版权、许可和技术来源说明"）；参考项目的**文件路径**与**服务商派生的主机别名**作为来源引用保留（不含凭据与个人身份）。

## 5. 修正过的误判（复核记录）

| 原判定 | 复核结论 |
|---|---|
| `scripts/selfheal/selfheal.env` 含"真实凭据被跟踪" | **不准确**。键名全为调参阈值（MAX_REPAIR/NOTIFY_MIN_FAILS/FLAP_WINDOW/…），无 password/token/secret/uuid。但**注释含公网 IP 与域名**，属网络标识 PII，需脱敏。降级为"*.env 被跟踪的卫生问题 + 注释脱敏"。 |
| 验收门报 14 处"非白名单域名" | 全部为**公共标准/配置文件名**：公共 DNS 锚点 IP、`ts.net`（Tailscale 公共域）、`jail.local`/`port.local`/`fail2ban-ignoreip.local`（fail2ban 配置文件名）、`.env.example`、`nip.io`/`sslip.io`/`ip.sb`（公共技术服务）。已加入白名单并记录理由。 |
| 验收门报 `xxx.example.md` 为域名 | **文件名误报**（RE_DOMAIN 的 TLD 列表含 `example`）。已加文件扩展名排除逻辑。 |
| `.gitignore` 的 `local/` + 否定规则 | **无效**：git 不进入被忽略的目录，否定规则不生效。已改为 `local/*` + `!local/README.md` + `!local/*.example.md`，实测 README 与 example 文件可跟踪、真实对照表被忽略。 |
| 子代理称「demo 页随 dist 由 `/demo/` **公开服务**，属高危公开暴露」 | **不准确**。生产面板 `GET /demo/nothing-full.html` 与 `/demo/nothing-iphone.html` 实测均 **404（22 B）** → **当前未通过 HTTP 暴露**。真实风险是文件仍在源码树与本地 `dist/`，**纳管即固化泄漏**。已修正 panels/04、panels/10 的表述与风险等级。 |
| 子代理称公开 YAML「**3 订阅 URL 含 token**」 | **不准确**。11-25 复核：proxy-providers 共 **3** 个，其中 **2** 个 URL 带 query token（Kycloud、DlerCloud），Youtu **不带**。已修正 panels/04、panels/09、panels/10。 |
| 子代理称图标上游 `shindgew/WHATSINStash`「**疑似友人仓库**」 | **不准确**。gh API 核实：**第三方公开仓库**，owner=`shindgew`，非 Fork，license=null，**与参考项目作者无关**。仍因无许可证而不复制其资产。已修正 panels/02、panels/04、panels/10。 |
| 验收门自命中（`tools/verify-sanitized.py` 的 `RE_PWD = ...` 与注释里的 `xxx.example`） | 检测工具源码按设计含模式与白名单。已加 `TOOLING_FILES` 跳过自身与两个 gitleaks 规则文件（skipped_tooling=3），**不放宽对文档的检测**。 |
| 验收门把 `navigator.onLine` / `store.online` / `server.host` 当域名 | **JS/配置属性误报**（`online`/`host` 是真实 TLD）。已加 `PROPERTY_FALSE_POSITIVES` 精确字符串豁免。 |
| 验收门把 `private.example` / `xxx.example` 当真实域名 | **RFC 2606/6761 保留文档顶级域**（example/invalid/test/localhost），定义上非真实域名。已加 `RESERVED_TLDS` 豁免。 |
| 验收门把源码变量赋值当口令 | 已加**代码表达式豁免**：值含点且为纯标识符（如 `settings.webdav_password`），或值就是字段名本身（password/passwd/pwd/secret/token）。**不含点的纯字母数字串仍然告警**，避免放过真实口令。 |

## 6. 推送前必做（已全部执行，附证据）

- [x] `git add` 后确认**不含 local/ 下真实对照表**：暂存的 local/ 条目仅 `local/README.md`、`local/env-map.example.md`；`local/audit-notes.md` 与 `local/placeholder-map.md` 被忽略。
- [x] 首次 commit 用本人署名 + noreply 邮箱：`author = committer = JasonBeam <124451452+JasonBeam@users.noreply.github.com>`；`git log --all --format="%an <%ae>" | sort -u` **只有这一条**。
- [x] **提交后复扫历史**：`gitleaks git . --config tools/gitleaks-repo.toml --redact` → **1 commits scanned，scanned ~658209 bytes，no leaks found**（报告 `reports/gitleaks-git-final.json`）。
- [x] 确认远程仓库 **Private** 后才推送：创建后先查 `gh repo view` → `visibility=PRIVATE, isPrivate=true, isFork=false, parent=null`，**然后**才 `git push -u origin main`。
- [x] 推送后核对远程文件数与本地一致：远程 tree blob 数 **92** = 本地 `git ls-tree -r HEAD` **92**；`HEAD == origin/main == 2eed9933b7ffa133df106cf71430fb65a9e565ce`；远程 `local/` 只有 README.md 与 env-map.example.md；远程敏感文件名检查（`.env/.pem/.key/.db/.sqlite/.age/DS_Store/audit-notes/placeholder-map/secrets//backups/`）→ **NONE**。

### 6.1 发布证据

| 项 | 值 |
|---|---|
| 远程仓库 | https://github.com/JasonBeam/homelab-panel （历史快照；该仓库 2026-11-25 已并入 `fixcloud-panel/docs/` 并删除） |
| 可见性 | **PRIVATE**（`isPrivate=true`） |
| Fork 关系 | **无**（`isFork=false`，`parent=null`） |
| 默认分支 | `main` |
| 首次提交 | `2eed9933b7ffa133df106cf71430fb65a9e565ce`（2026-11-25 01:01 +0800） |
| 提交文件数 / 体积 | 92 文件 / 658209 B |
| 历史扫描 | 1 commit，0 leaks |
| GitHub Actions | 无 `.github/`，**0 workflow**，不会触发任何自动部署 |
| 本地工作区 | `/Users/beamjason/Documents/GitHub/homelab-panel` |

## 7. 已知局限（不能宣称"绝对干净"）

- 验收门是**正则启发式**，不能替代人工复核；变形/编码/拆分后的凭据可能漏检。
- 本仓库**不含二进制**，故无图片内文字、PDF 正文、加密压缩包风险；但也意味着**未对参考项目的这些内容做任何提取**（一律不入库）。
- 参考项目上游历史中的凭据**仍然存在**，本仓库的任何操作都无法清除。
- 未验证：GitHub 服务端缓存、Fork 网络中其他副本、上游作者本地副本。

---

## 8. 源码仓库（JasonBeam/fixcloud-panel）扫描与本轮补漏

### 8.1 纳管时验收结果【我方已验证】

| 项 | 结果 |
| --- | --- |
| 验收门 | `scanned_files=154`、`residual_findings=0`、`skipped_gitignored=29`、`skipped_tooling=3` |
| Gitleaks 默认规则 | 0 leaks |
| Gitleaks 仓库配置（工作区） | 0 leaks（794.66 KB） |
| Gitleaks 仓库配置（Git 历史） | 0 leaks（2 commits，893.15 KB） |
| 远程敏感文件名复检 | 146 条路径，仅命中 `.env.example`；私钥/证书/数据库/日志/备份/压缩包 0 |
| PNG 元数据 | 5 个图标：4 个仅 eXIf 68B（ColorSpace + 像素尺寸），icon-1024 为 Apple 工具私有块 caBX；敏感标记扫描全 0 |
| 隔离测试 | 后端 49 passed、`vue-tsc -b` 通过、vitest 19 passed / 6 files、`vite build` 2.21s |

### 8.2 本轮发现的漏项与修复【我方已验证】

- **漏项**：`frontend/src/components/SourceModal.vue:248` 服务器地址 placeholder 为真实 NAS LAN IP；`:249` 共享目录 placeholder 为真实个人共享名。
- **漏检根因**：① 验收门为容忍文档中的内网拓扑描述，全局把 RFC1918 列入白名单；② 个人共享名是裸词，不匹配域名正则。两者叠加使「会随前端构建分发到浏览器」的资产逃过检查。
- **修复**：placeholder 改为 `192.0.2.10` / `files`。
- **门加固（不弱化原有规则）**：新增 `shipped-asset-private-ip`，仅对 `frontend/src/`、`frontend/public/` 前缀收紧，禁止 RFC1918/ULA 真实地址（文档示例段 192.0.2/198.51.100/203.0.113/2001:db8 仍豁免）。三组对照验证：真实内网 IP 于 shipped 资产 → 命中 exit 1；示例值 → exit 0；同一 IP 于普通文档 → 仍 exit 0。规则已同步两仓库 `tools/verify-sanitized.py`。
- **复验**：源码门 154/0、知识库门 99/0、gitleaks 工作区与历史 0 leaks、`vue-tsc -b` 通过、vitest 19 passed。

### 8.3 取舍约定（避免后续代理反复 churn）【我方已验证】

- **随浏览器分发的资产**（`frontend/src`、`frontend/public` → `dist`）：一律只用示例值，连 placeholder 也不例外。
- **仅仓库内可见的自有环境文档**（`.env.example`、`README.md`、`docs/`、本知识库）：可保留用户**自有** NAS 共享路径与用户名（非凭据、部署需要）；真实值仍走 gitignore 的 `.env`。
- **任何位置**都禁止：真实凭据、订阅 token、UUID、私钥、公网 IP、真实域名、他人个人信息。
- 参考项目（JimmyChan233/homelab）的任何真实值一律不入库，只提炼设计思想。
