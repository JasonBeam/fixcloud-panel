# 07 纳管清单与源码纳管判定

> 分类：【我方已验证】。核实时间 2026-11-25（Asia/Shanghai），**全部基于实时检查，不依赖旧报告**。

## 1. 本仓库纳管了什么

| 目录 | 内容 | 来源 | 分类 |
|---|---|---|---|
| `knowledge/` | 12 篇通用技术经验 + README + ATTRIBUTION | 参考项目提炼（我方重写） | 【参考提炼】 |
| `infrastructure/` | 7 篇我方基础设施架构 + README | 我方环境实测 | 【生产配置】【我方已验证】 |
| `panels/fixcloud-panel/` | 面板架构/技术栈/API/功能/数据/部署/测试/决策/集成/源码纳管执行记录/私有订阅中心方案/安全边界方案 | 我方源码实时核实 | 【我方已验证】 |
| `design/` | 设计系统/当前面板 UI/交互/紧凑组件/响应式/参考思想/演进策略 | 我方源码 + 参考项目抽象思想 | 【我方已验证】+【参考提炼】 |
| `templates/` | sing-box 三协议配置 + compose + 订阅输出 + docker/env 示例 | **我方自行重写** | 【待验证】 |
| `playbooks/` | 5 个标准操作流程 | 我方实践 + 参考教训 | 【我方已验证】判据 +【待验证】流程 |
| `troubleshooting/` | 3 个我方实际案例 | 我方环境 | 【我方已验证】 |
| `roadmap/` | 6 篇研究计划 + README | 我方规划 | 【待验证】 |
| `reports/` | 7 份审计与验收报告 | 本轮审计 | 【我方已验证】 |
| `tools/` | 验收门 + gitleaks 规则 + 本仓库配置 | 本轮建立 | 【我方已验证】 |
| `local/` | **gitignore**，仅 README 与 example 模板入库 | 本机私有对照 | 不入库 |

## 2. FixCloud 源码纳管判定（用户第三节要求）

### 2.1 现有 Git 关系【已验证】

| 检查 | 结果 |
|---|---|
| `/Users/beamjason/Documents/BeamNat/fixcloud-panel/.git` | **不存在** —— 该项目**不是 Git 仓库** |
| 子目录内任何 `.git`（maxdepth 4） | **0 个** |
| 远程 / 分支 / 历史 | **无** |
| 结论 | **不存在嵌套 Git 仓库风险**；纳管不会破坏任何既有 Git 关系 |

### 2.2 敏感信息风险【已验证】

| 检查 | 结果 |
|---|---|
| 文件数（排除 node_modules/.venv/__pycache__/.pytest_cache/dist） | **127** |
| gitleaks 默认规则 | **0 leaks**（扫描 1.85 MB） |
| gitleaks 自定义规则 | 29 命中，**逐条判定全部为代码标识符或测试占位符**（见下） |
| `.env` 真实文件 | **0 个**（只有 `.env.example`） |
| 私钥/证书/数据库/日志 | **0 个** |
| 隐藏文件 | `.DS_Store`（需排除）、`.dockerignore`、`.gitignore`、`.env.example` |
| 测试 fixture `backend/tests/fixtures/FixCloud.sample.yaml` | 1319 B / 66 行；server 全为 `127.0.0.1`；proxy-provider URL 域名为 **`example.invalid` 与 `www.gstatic.com`，均无 query token**；secret/password 为占位符 → **干净** |
| 图标 PNG（5 个） | 4 个含 `eXIf` 块，解码后**仅 ColorSpace + PixelXDimension + PixelYDimension**；**无 Artist/Software/DateTime/GPS/设备/序列号** → 无个人元数据。`icon-1024.png` 含 `caBX` 私有块（Apple 图标工具产物），无个人信息 |
| **演示页 `frontend/public/demo/nothing-full.html`（91627 B）与 `nothing-iphone.html`（32512 B）** | **含真实值**：mock 数据里嵌入了真实订阅服务商域名、真实家庭域名、真实 NAS 公网 IPv4、真实节点端口。**未被 `.gitignore` 排除**（只排除了 `frontend/dist/`）→ 若纳管源码会一并入库 |
| **`docs/vps-singbox-integration-research.md`（61083 B）** | 我方上一轮研究报告，**正文含真实 IP/域名**（约 40 处）→ 纳管前必须脱敏或排除 |
| 演示页是否对外暴露 | 生产面板 `GET /demo/nothing-full.html` 与 `/demo/nothing-iphone.html` 均 **404**（22 B）→ **当前未通过 HTTP 暴露**【已验证】；但文件仍在源码树与本地 `dist/` 中 |

**真实域名/IP 扫描的误报澄清**（避免把公共标准值当成隐私）：

| 命中位置 | 实质 | 判定 |
|---|---|---|
| `frontend/src/stores/app.ts:213,247,602,606`、`AppShell.vue:120` | `navigator.onLine` / `store.online` 被正则误当成 `.online` 域名 | **误报** |
| `frontend/index.html:14,16`、`demo/nothing-iphone.html:8,10` | Google Fonts `fonts.googleapis.com` / `fonts.gstatic.com` | 公共资源 |
| `backend/app/services/icon_catalog.py:114`、`tests/test_icon_catalog.py` | `github.com/shindgew/WHATSINStash` 图标上游 | 公共仓库 |
| `backend/app/services/icon_cache.py:20`、`DnsSettingsEditor.vue:60`、fixture | `198.18.0.0/15` RFC 2544 基准网段（Mihomo Fake-IP 默认） | 公共标准 |
| `backend/tests/test_icon_cache.py`、fixture `dns-query` | 公共 DNS 锚点与 `example.com` | 公共/示例 |
| `frontend/package-lock.json`（209 处） | npm registry URL | 依赖锁文件，非隐私 |

**29 条自定义命中的性质**（全部非凭据）：

| 类型 | 位置 | 实质 |
|---|---|---|
| `token = secrets.token_urlsafe(...)` / `token_hex(...)` | save_service.py、source_store.py、main.py、icon_cache.py | **Python API 调用**，生成随机值的代码 |
| `password=settings.webdav_password or ""` / `self.password = password` | storage/registry.py、storage/smb.py | **变量赋值代码** |
| `password: ...` | StructuredField.vue、SourceModal.vue | **表单字段 kind 定义** |
| 测试用 `password`/`webdav_password` | test_api.py、test_source_store.py、test_subscription_nodes.py | **测试占位值**，server 用 `private.example` |
| `frontend/dist/`、`.venv/`、`__pycache__/` 内命中 | 构建产物 | **不纳管**（已在 .gitignore） |

### 2.3 判定结论（历史判定，已被 §2.5 执行结果取代）

**源码无凭据泄露、无 Git 嵌套、fixture 与图标干净，但含两处真实网络标识**（`frontend/public/demo/*.html` 演示页 mock 数据、`docs/vps-singbox-integration-research.md` 研究报告正文）。

因此判定修正为：**源码"可纳管但不可原样纳管"** —— 必须先处理这两处（脱敏为示例值，或加入 `.gitignore` 排除），才能进入任何 Git 仓库（即使 Private）。

**本轮不迁移源码**，理由：

1. 该项目是**正在使用的生产工程**，`docker-compose.yml` 的 `build.context: .` 依赖当前目录结构；迁移会改变构建上下文与部署路径，属**破坏性操作，需明确授权**。
2. 复制一份源码进本仓库会产生**双份事实源**，必然漂移；本仓库定位是知识库与开发中心，不应制造无人维护的副本。
3. 用户明确要求"禁止直接嵌套其他 Git 仓库或破坏原有工程"。

**本轮做法**：只纳管**脱敏后的项目文档、架构、UI 与开发规范**（`panels/fixcloud-panel/` + `design/`），源码留在原路径。

### 2.4 源码纳管方案（另行提出，待批准）

| 方案 | 做法 | 优点 | 缺点 | 建议 |
|---|---|---|---|---|
| **A 独立源码仓库（推荐）** | 在 `/Users/beamjason/Documents/BeamNat/fixcloud-panel` 就地 `git init`，推到**独立 Private 仓库** `JasonBeam/fixcloud-panel`；本仓库以**链接 + 文档**引用，不用 submodule | 原路径与部署完全不动；源码有版本历史；两仓库职责清晰；无嵌套 | 跨仓库跳转；需维护两处文档同步 | ✅ 风险最低，可立即执行（需授权创建远程） |
| **B  monorepo 迁移** | 把源码移入 `homelab-panel/panels/fixcloud-panel/source/`，原路径改为符号链接或更新 compose 路径 | 单一事实源；符合"统一仓库"字面要求 | **改变部署路径与构建上下文**；符号链接对 Docker 构建不友好；回滚复杂 | ⚠️ 需先验证 compose 与 NAS 部署，且必须授权 |
| **C 快照副本** | 复制源码进本仓库作为只读快照 | 简单 | **必然漂移**，无人维护；违反单一事实源 | ❌ 不推荐 |
| **D submodule / subtree** | 以子模块引用 | 标准做法 | 用户**明确禁止嵌套其他 Git 仓库**；且需先给原项目建 Git | ❌ 不符合约束 |

**推荐 A**。**用户已于 2026-11-25 批准方案 A 并授权执行**（远程名 `JasonBeam/fixcloud-panel`）；执行结果见 §2.5。

**A 的强制前置（本轮新发现，必须先做）**：

1. 处理 `frontend/public/demo/nothing-full.html` 与 `nothing-iphone.html`：把 mock 数据里的真实域名/IP/端口替换为 `example.com` / `192.0.2.10` / 示例端口，**或**在 `.gitignore` 中排除 `frontend/public/demo/`。二者择一，需用户决定（演示页是 UI 设计参考，建议脱敏保留而非删除）。
2. 处理 `docs/vps-singbox-integration-research.md`：正文真实 IP/域名占位符化（本仓库 `roadmap/02-singbox-selfhosted-nodes.md` 已是脱敏版，可作为替代）。
3. 补 `.gitignore`：`.DS_Store` 已有；建议追加 `secrets/`、`backup-vps-*/`、`*.bak-*`（NAS 部署目录存在这些，源 Mac 项目当前没有，但 `.dockerignore` 已列出 `secrets` 与 `backup-vps-20261122`，说明部署侧有）。
4. 首次 commit 前跑 `gitleaks dir` + 本仓库验收门，确认 0 残留。

### 2.5 方案 A 执行结果【我方已验证 2026-11-25】

| 项 | 结果 |
|---|---|
| 源码仓库 | **https://github.com/JasonBeam/fixcloud-panel** · `private=true` · `fork=false` · `parent=null` · `main` |
| 本地路径 | `/Users/beamjason/Documents/BeamNat/fixcloud-panel`（**原路径与部署上下文未动**，就地 `git init`） |
| 首次提交 | `15c9fe380880a189a45a9a4191324b713b9dc5af`，125 文件，作者 JasonBeam + GitHub noreply |
| 一致性 | 本地 125 = 远程 125；`HEAD == origin/main`；远程敏感文件名复检仅 `.env.example` |
| 脱敏 | 10 文件（settings.py:28、.env.example、compose:17/21、README:73/74、SettingsView:46/200、IconCatalogPicker:173、两个 demo HTML、test_icon_cache.py:11、docs 研究报告） |
| 可部署性 | 仓库默认值改示例值；真实值写入 **gitignore 的 `.env`**（`PUBLIC_FILE_BASE_URL`/`PUBLIC_FILE_DOMAIN`/`PUBLIC_FILE_LAN_IPV6`），compose 自动读取 → 本地部署行为不变 |
| 验收门 | `scanned_files=154` **residual_findings=0** |
| Gitleaks | 默认 0 leaks；仓库配置工作区 0 leaks、**Git 历史 0 leaks** |
| 隔离测试 | 后端 **49 passed**；`vue-tsc -b` 通过；vitest **19 passed / 6 files**；`vite build` 2.21 s |
| 本仓库关联 | **链接 + 文档引用**，不复制源码、不建 submodule、不嵌套 Git |
| 未做 | 未读取/复制 NAS `.env`/`secrets`/`data`；未重启未部署未迁移订阅 |

详见 [../panels/fixcloud-panel/10-source-inclusion-plan.md](../panels/fixcloud-panel/10-source-inclusion-plan.md)。

## 3. 未纳管的内容及原因

详见 [02-excluded-files.md](02-excluded-files.md)。摘要：

| 类别 | 原因 |
|---|---|
| 参考项目 `00-密码总表.md` | 全类型凭据集中载体，**整体不入库** |
| 9 个 `backups/*.tgz.age` | 加密无法扫描，且历史中曾以**明文 tar** 入库 → 整体不入库 |
| `.age-recipients` | 加密收件人公钥，属作者资产 |
| 短信转发 JSON、学业 xlsx/png/PDF、韩语/选课/设计语文档、生活流程文档、状态截图 | 个人隐私，与技术经验无关 |
| 21 个 launchd plist、23 service、14 timer、9 cron、安装器/hook | **会自动外联或部署到原作者设备**，禁止执行也禁止入库；只保留设计思想 |
| 参考项目源码与 UI 资产 | **上游无许可证**，只提炼设计思想，不复制代码/CSS/图片/配色值 |
| 两个 `selfheal.env` | 被跟踪的调参文件（无凭据），但注释含公网 IP/域名 → 不入库 |
| FixCloud `frontend/dist/`、`.venv/`、`__pycache__/`、`.pytest_cache/`、`node_modules/`、`.DS_Store` | 构建产物与缓存 |
| FixCloud `frontend/public/demo/*.html`（原样） | mock 数据含真实域名/IP/端口；**已脱敏后纳入源码仓库**（保留演示页作 UI 参考） |
| FixCloud `docs/vps-singbox-integration-research.md`（原样） | 正文含真实 IP/域名；**已占位符化后纳入源码仓库**；本仓库另有脱敏版 `roadmap/02-singbox-selfhosted-nodes.md` |
| 真实 IP/域名/主机别名对照表 | 只留 `local/`（gitignore），仓库内一律占位符 |
