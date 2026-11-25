# CHANGELOG — Homelab 经验库

本经验库更新记录（原 `homelab-panel` 仓库 CHANGELOG，并入 `fixcloud-panel/docs/` 后继续在此维护）。格式参考 Keep a Changelog；日期为 Asia/Shanghai。
面板源码自身的发布 CHANGELOG 另见仓库根（发布时建立）；本文件只记录经验库/文档侧变更。

## [Unreleased]

### 变更
- **2026-11-25 经验库整体并入源码仓库**：原独立私有仓库 `JasonBeam/homelab-panel` 的全部经验目录（knowledge/panels/infrastructure/design/templates/playbooks/troubleshooting/roadmap/reports/local）迁入 `fixcloud-panel/docs/`，交叉链接改为仓库内相对路径；源码与经验同仓共存，原 `homelab-panel` 远程仓库删除。原 Fork `JasonBeam/homelab` 保留作审计存档。真实值对照表（gitignore 的 `local/` 映射）未带入。

### 计划中
- 私有订阅中心实施（方案见 panels/fixcloud-panel/11-subscription-center-spec.md）：让 FixCloud.yaml 不再无鉴权公开，改为可管理/可撤销/可自动更新的私有订阅链接。
- 管理权限与安全边界加固（方案见 panels/fixcloud-panel/12-security-boundaries.md）。
- sing-box 自建节点管理集成（见 roadmap/02）——**用户已确认排在私有订阅完成之后**。

## [0.3.0] - 2026-11-25

### 新增
- `panels/fixcloud-panel/11-subscription-center-spec.md`（15 章）与 `12-security-boundaries.md`（10 章）正式纳入并**交叉对齐**：管理端点统一依赖 `require_admin`，Phase 0 先于订阅中心 P0-b，公开 URL 退役晚于消费方迁移。
- 验收门新增 **`shipped-asset-private-ip`** 规则：`frontend/src/`、`frontend/public/` 内禁止真实内网地址（RFC1918/ULA），因这些资产会随 `dist` 分发到浏览器；文档中的内网拓扑描述仍按原白名单容忍。附正/负/文档三组对照验证。规则已同步到两仓库 `tools/verify-sanitized.py`。

### 修复
- **漏脱敏**：源码仓库 `frontend/src/components/SourceModal.vue:248` 服务器地址 placeholder 为真实 NAS LAN IP、`:249` 共享目录 placeholder 为真实个人共享名 → 改为 `192.0.2.10` / `files`。漏检根因：门全局豁免 RFC1918、裸词不匹配域名正则。
- 修正 12 号文档 P1-4 的过时表述（demo 与 SettingsView 真实值已在纳管时清理），风险降级为「vite 无 publicDir 排除 → 下次构建仍会分发 demo」。
- 修正 11 号文档 §14 与 `reports/08` 的 temporary-sessions 表述：实测 2968 目录、`-mtime +1` 为 0 → **有界 churn**（healthcheck 每 30s 建会话），非无限增长；真隐患是 `cleanup_loop` 无异常守卫（browser_session.py:90-96）。
- 修正 11 号文档 §13.1 验收门命令：该工具按目录 `os.walk`，必须传目录而非单文件。

### 安全
- **3 条 P0 已独立复证**：① 16 条 GET 全无鉴权，`/api/config/raw` 实测 200/21399B 含回家凭据与上游 token；② 公开文件域根索引 200/683741B + 双 YAML 可公网下载；③ 18 条非 GET 仅靠可伪造头，生产 `WRITE_ENABLED=true`，`DELETE /logs` 自身不审计 → 与 ① 组合为读写接管 + 抹痕。
- 路由器 `uci firewall` 无 8787 DNAT（面板未经路由器转发 WAN）；生产 demo 页当前 404。
- 两仓库验收门 0 残留（知识库 99 文件 / 源码 154 文件）；源码 gitleaks 工作区与历史 0 leaks；`vue-tsc -b` 通过、vitest 19 passed。
- **本轮未做任何生产变更**：管理鉴权部署、QNAP /data ACL 收紧、Lucky 公开 file 处置均需用户单独授权（12 §9 A1/A2/A3）。

## [0.2.0] - 2026-11-25

### 新增
- **FixCloud 源码纳管（方案 A，用户已批准并执行完成）**：源项目就地 `git init`，推送独立 Private 仓库 **https://github.com/JasonBeam/fixcloud-panel**（`fork=false`、`parent=null`、`main`、125 文件、提交 `15c9fe380880a189a45a9a4191324b713b9dc5af`）。经验库以链接 + 文档关联，**不复制源码、不建 submodule、不嵌套 Git**；原工程路径与 Docker 构建上下文完全未动。
- 源码仓库新增 `tools/`：验收门、严格版与仓库版 gitleaks 规则、用法说明。
- `panels/fixcloud-panel/10-source-inclusion-plan.md` 改写为**执行记录**（脱敏清单、.gitignore 加固、验收结果、后续守护）。
- `panels/fixcloud-panel/11-subscription-center-spec.md`：私有订阅中心详细实施方案、迁移步骤、验收标准。
- `panels/fixcloud-panel/12-security-boundaries.md`：管理权限、安全边界与加固方案。
- `roadmap/06` §F：`design/07` 六项 UI 不一致待办（用户决定暂不优先修改）。

### 变更
- 脱敏 10 个源码文件（settings.py:28、.env.example、docker-compose.yml:17/21、README.md:73/74、SettingsView.vue:46/200、IconCatalogPicker.vue:173、两个 demo HTML、test_icon_cache.py:11、docs 研究报告）：真实域名/IP/IPv6/线程 UUID → 示例值或占位符。
- **保留可部署性**：仓库默认值改示例值，真实值写入 gitignore 的 `.env`（`PUBLIC_FILE_BASE_URL`/`PUBLIC_FILE_DOMAIN`/`PUBLIC_FILE_LAN_IPV6`），compose 自动读取 → 本地部署行为不变。
- 验收门修正误报：补公共技术服务域名白名单、`xxx.id` 属性链识别（`.id` 为印尼 ccTLD）、二进制文件跳过、中文提示文案与代码表达式豁免。
- `reports/07`、`reports/08`、`README.md` 同步执行结果与用户 10 项决策。

### 安全
- 源码仓库验收门 `scanned_files=154` **residual_findings=0**；Gitleaks 默认 0 leaks、仓库配置工作区 0 leaks、**Git 历史 0 leaks**；远程敏感文件名复检仅 `.env.example`；5 个 PNG 元数据无个人信息。
- 隔离测试：后端 **49 passed**、`vue-tsc -b` 通过、vitest **19 passed / 6 files**、`vite build` 2.21 s。
- 未读取/复制 NAS `.env`/`secrets`/`data`；未重启、未部署、未迁移订阅；原 Fork `JasonBeam/homelab` **保留未删除**。

### 说明
- 用户授权边界：允许本地开发、隔离测试、Git 初始化、脱敏后 Private 上传；**生产配置修改、服务重启、防火墙修改、正式订阅迁移仍需单独授权**。

## [0.1.0] - 2026-11-25

### 新增
- 仓库创建：**https://github.com/JasonBeam/homelab-panel**（Private，`isFork=false`、`parent=null`），全新独立 Git 历史，无上游；署名 JasonBeam + GitHub noreply 邮箱；首次提交 `2eed993`，92 文件。（该仓库已于 2026-11-25 并入 `fixcloud-panel/docs/` 并删除，此处保留历史记录。）
- 根文件：README.md（总览与导航）、AGENTS.md（Agent 操作规范）、.gitignore（排除真实配置/凭据/密钥/日志/数据库/备份/缓存）。
- 目录骨架：knowledge/ panels/ infrastructure/ design/ templates/ playbooks/ troubleshooting/ roadmap/ reports/ local/，每个重要目录含 README 索引。
- 内容分类徽章体系：【我方已验证】/【生产配置】/【参考提炼】/【待验证】/【已过时】。
- 脱敏验收门 tools/verify-sanitized.py（只输出类型与位置，绝不回显真实值）。
- 从参考项目提炼的通用技术知识（12 篇，分类归纳重写，不含原作者个人信息与凭据，不复制其源码/UI 资产）。
- 我自己的 FixCloud Panel 十项资料、基础设施架构、UI 设计规范、部署模板、SOP、故障案例、Roadmap。
- 本次脱敏审计与安全验收报告（reports/）。

### 安全
- 全量 Gitleaks + 自定义中文规则扫描；压缩包递归检查；图片与文件元数据检查；隐藏文件检查；Git 历史检查；.env 与数据库文件检查；GitHub Actions 安全检查。
- 原 Fork JasonBeam/homelab 暂时保留为私有审计存档；删除需另行确认。
- 明确记录：上游历史凭据未因本次脱敏而清除，需原持有人自行轮换。

### 说明
- 本阶段**只整理知识库与项目资料**，未修改任何生产订阅、Lucky、NAS 或 VPS 服务。
