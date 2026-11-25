> 分类：【我方已验证】执行记录 +【生产配置】结构说明
> 核实时间：2026-11-25（Asia/Shanghai）；方式：只读审计 → 脱敏 → 隔离测试 → Private 推送
> 脱敏：真实 IP/域名/凭据一律占位符；对照表仅存本机 local/（不入库）

# 10 · 源码纳管：方案 A 已执行

**结论**：用户已批准**方案 A（独立 Private 源码仓库 + 本知识库链接引用）**，并已完成执行。
源码仓库 **https://github.com/JasonBeam/fixcloud-panel**（Private、`isFork=false`、`parent=null`、分支 `main`）。
本仓库**不复制源码、不建 submodule、不嵌套 Git**，只以链接 + 文档引用。原工程路径与部署上下文**完全未动**。

## 1. 两仓库职责与关联

| 仓库 | 定位 | 本地路径 | 关系 |
| --- | --- | --- | --- |
| `JasonBeam/fixcloud-panel` | **源码唯一事实源**（可运行工程 + 部署模板 + 项目内 docs） | `/Users/beamjason/Documents/BeamNat/fixcloud-panel` | 就地 `git init`，原路径不变 |
| `JasonBeam/homelab-panel` | **知识库 + 开发中心 + 经验库 + 研究中心** | `/Users/beamjason/Documents/GitHub/homelab-panel` | 链接引用源码仓库，不持有源码副本 |

关联方式：本目录文档描述架构/API/UI/验收；源码改动在源码仓库提交；**每次开发或故障修复后把已验证经验同步回本仓库**（AGENTS.md 长期机制）。
不使用 submodule / subtree / 符号链接 —— 用户明确禁止嵌套 Git 仓库，且符号链接对 Docker 构建上下文不友好。

## 2. 执行前 Git 关系事实【我方已验证】

| 检查 | 结果 |
| --- | --- |
| 源项目 `.git` | **不存在**（非 Git 仓库，无远程、无历史） |
| 子目录内任何 `.git`（maxdepth 4） | **0 个** → 无嵌套风险 |
| NAS 部署目录 | 完整源码副本（无 `.git`），另含 `.env`/`secrets/`/`backup-vps-*`/日志（重敏感，**未读取未复制**） |
| 源项目凭据文件 | **0 个**（只有 `.env.example`） |

## 3. 脱敏执行清单（10 个文件）

计数：domain 26、ipv4 30、ipv6_ula 4、ui_text 2、uuid 1。

| 文件:行 | 原内容类型 | 处置 |
| --- | --- | --- |
| `backend/app/core/settings.py:28` | `public_file_base_url` 默认值含真实公开域名 | 改 `https://file.example.com`，真实值由 env 注入 |
| `.env.example:25,30` | 示例值含真实域名/IPv6 | 改示例值 + 注释说明由本机 `.env` 覆盖 |
| `docker-compose.yml:17,21` | 默认 env 与 `extra_hosts` 含真实域名/ULA IPv6 | 改示例值；真实值走 gitignore 的 `.env` |
| `README.md:73,74` | 部署说明含真实域名/IP | 占位符化 |
| `frontend/src/views/SettingsView.vue:46,200` | `publicationBaseUrl` ref 初值 + 展示文案 | 初值改示例；文案改「公开文件域 · Lucky」 |
| `frontend/src/components/IconCatalogPicker.vue:173` | 图标 URL 示例文案 | 改「公开文件域/icon」 |
| `frontend/public/demo/nothing-full.html` | mock 数据 9 处真实域名/LAN/端口 | 全部改示例值（**保留演示页**，它是 UI 设计参考） |
| `frontend/public/demo/nothing-iphone.html` | mock 数据 6 处同上 | 同上 |
| `backend/tests/test_icon_cache.py:11` | `PUBLIC_DNS` 常量含真实域名 | 改示例域名 |
| `docs/vps-singbox-integration-research.md` | 约 40 处真实 VPS IP/域名/出口 IP/线程 UUID | 占位符化（`<VPS_JP_IP>` 等）；`<PRIVATE_DOMAIN>` 统一为 `<VPS_NODE_DOMAIN>` |

**保留可部署性的关键做法**：仓库内默认值全部改示例值，同时在源项目根新建 **gitignore 的 `.env`** 写入真实 `PUBLIC_FILE_BASE_URL` / `PUBLIC_FILE_DOMAIN` / `PUBLIC_FILE_LAN_IPV6`。`docker compose` 自动读取该文件 → **本地部署行为不变，仓库不含真实值**。

**原件备份**（脱敏前快照，本机不入库）：`/Users/beamjason/Documents/GitHub/homelab-sanitize/fixcloud-pre-sanitize/`（两个 demo HTML、docs 报告、`gitignore.orig`）。

## 4. .gitignore 加固（在原 11 行基础上追加）

`.env.*` + 否定 `!.env.example` `!.env.template`；`secrets/` `credentials/` `private/` `backup-vps-*/` `*.bak-*` `*.pem` `*.key` `*.p12` `*.pfx` `*.crt` `*.cer` `id_rsa*` `id_ed25519*` `*_ed25519` `*.age` `.age-recipients` `known_hosts` `authorized_keys` `*.sqlite3` `*.db` `*.wal` `*.shm` `*.log` `logs/` `backups/` `*.tgz` `*.tar` `*.zip` `*-config-backup*` `.local-originals/` `screenshots/raw/`。
原有排除保留：`.venv/` `node_modules/` `frontend/dist/` `__pycache__/` `.pytest_cache/` `*.egg-info/` `data/` `.DS_Store` `._*`。

## 5. 验收结果【我方已验证】

| 检查 | 结果 |
| --- | --- |
| 脱敏验收门（`tools/verify-sanitized.py`） | `scanned_files=154` **residual_findings=0**；skipped_gitignored=29、skipped_tooling=3 |
| Gitleaks 默认规则（工作区） | **0 leaks**（1.85 MB） |
| Gitleaks 自定义规则（无白名单） | 30 命中 → 逐条判定：12 在 gitignore 产物内，18 条全为代码表达式或合成 fixture（随机值生成 API 调用、存储层变量赋值、表单字段 kind 定义、测试值 `proxy-private`/`dav-password`、中文提示文案、全零示例 UUID） |
| Gitleaks 仓库配置（精确白名单） | 工作区 **0 leaks**（793 KB）；**Git 历史 0 leaks**（892 KB） |
| PNG 元数据（5 个图标） | 4 个 `eXIf` 68 B 仅 ColorSpace + 像素尺寸；`icon-1024.png` `caBX` 24922 B 为 Apple 图标工具私有块；敏感标记（域名/服务商/GPS/Artist/Software/DateTime/Make/Model/OwnerName/SerialNumber/用户名）**全 0** |
| 后端隔离测试 | `backend/.venv/bin/python -m pytest -q` → **49 passed** |
| 前端类型检查 | `npm run typecheck`（`vue-tsc -b`）通过 |
| 前端单测 | `npm run test`（vitest）→ **19 passed / 6 files** |
| 前端生产构建 | `npm run build` 2.21 s 成功；`dist/demo` 已含示例域名 |
| 远程可见性 | `visibility=private`、`private=true`、`fork=false`、`parent=null`、`default_branch=main` |
| 文件数一致性 | 本地 125 = 远程 125；`HEAD == origin/main` |
| 远程敏感文件名复检 | 146 条路径中仅 `.env.example` 命中 env 模式；私钥/证书/数据库/日志/备份/压缩包 **0** |
| 暂存区敏感文件 | NONE；`.env` 未入库 |

首次提交：`15c9fe380880a189a45a9a4191324b713b9dc5af`，125 文件，作者 `JasonBeam <124451452+JasonBeam@users.noreply.github.com>`。

## 6. 源码仓库新增 tools/（4 件）

`verify-sanitized.py`（与本仓库同源，已修正误报）、`gitleaks-custom-rules.toml`（严格版，用于人工复核）、`gitleaks-repo.toml`（精确白名单版，用于门禁）、`README.md`（用法与判定原则）。

**验收门修正记录**（初扫 332 残留 → 全部误报 → 修正后 0）：
- 白名单域名补公共技术服务：`registry.npmmirror.com`（150 命中）、`opencollective.com`、`tidelift.com`、`api.github.com`、`ipv6.baidu.com`、`sing-box.app`、`nas.local`、`install.sh`、`sync.sh`。
- 新增属性链识别：`xxx.id` 形式（`source.id`/`record.id`/`e.target.id`）跳过 —— **`.id` 是印尼 ccTLD**，占域名误报绝大多数。
- 属性误报补：`this.online`、`request.app`、`tsconfig.app`、`icons.plus`、`appstore.online`、`request.url.host`。
- **二进制跳过**：前 8192 字节含 NUL 即跳过（PNG 字节垃圾曾误报邮箱/UUID/域名）。
- 密码豁免：中文提示文案、`str(`/`.get(` 代码表达式、合成测试值集合、值按换行切分后再判定。

## 7. 未纳管 / 未改动

| 项 | 状态 |
| --- | --- |
| NAS 部署目录 `.env`/`secrets/`/`data/sources.json`/备份/日志 | **未读取、未复制、未修改** |
| 生产容器与订阅出口 | **未重启、未部署、未迁移** |
| `frontend/dist/`、`.venv/`、`node_modules/`、缓存 | gitignore 排除，不入库 |
| 真实值对照表 | 仅本机 `local/`（gitignore） |
| 原 Fork `JasonBeam/homelab` | **保留**，未删除（用户决定） |

## 8. 后续守护

1. 每次源码提交前跑：门 + `gitleaks dir`；提交后跑 `gitleaks git`。
2. 新增硬编码域名/IP 一律改 env 驱动，默认值用示例值。
3. 公开文件凭据硬红线：自建节点凭据与订阅 token **绝不进** `FixCloud.yaml` 公开出口（见 roadmap/01）。
4. 外部依赖注明归属：图标上游 `shindgew/WHATSINStash`（第三方公开仓库，`license=null` → 不复制其代码/UI 资产）、Google Fonts、厂商 API 端点（结构性可保留，密钥值绝不入源码）。
