# Agent 交接单

> 2026-11-25 · 任务：参考项目脱敏审计 → 新建 `homelab-panel` 知识库与面板开发中心 → **FixCloud 源码纳管（方案 A 已执行）** → 私有订阅中心与安全边界方案。
> **接手只读本文件**。完整证据在 `reports/01~07`，按需再查。
> **2026-11-25 合并更新**：原 `homelab-panel` 知识库已整体并入 `fixcloud-panel/docs/`，远程仓库删除。本文件中凡 `panels/`、`knowledge/`、`infrastructure/`、`design/`、`reports/`、`roadmap/`、`templates/`、`playbooks/`、`troubleshooting/`、`local/` 等路径，现均位于本仓库 **`docs/`** 下（如 `docs/panels/fixcloud-panel/11`）；源码路径 `backend/`、`frontend/` 仍在仓库根。

## 0. 状态

| | |
|---|---|
| **已完成** | 参考项目只读审计（442 文件 / 443 commit）；12 篇知识提炼；FixCloud 实时核实文档；UI 规范 8 篇；基础设施 7 篇；模板/SOP/故障案例/Roadmap；脱敏验收；`homelab-panel` Private 创建并推送 |
| **已完成（新）** | **FixCloud 源码纳管方案 A**：就地 `git init` → 脱敏 10 文件 → 门 0 残留 + gitleaks 工作区与历史 0 leaks → 后端 49 passed / vitest 19 passed / 构建通过 → 推送 **Private `JasonBeam/fixcloud-panel`**（125 文件，提交 `15c9fe3`） |
| **本轮未做** | 未改任何生产订阅、Lucky、NAS、VPS；未重启未部署；未执行参考项目任何脚本；未连接原作者服务器；未删除原 Fork |
| **进行中** | 私有订阅中心实施方案（`panels/fixcloud-panel/11`）、管理权限与安全边界方案（`panels/fixcloud-panel/12`） |

## 1. 坐标

- **唯一仓库 https://github.com/JasonBeam/fixcloud-panel** · `PRIVATE` · `fork=false` · `parent=null` · 分支 `main`（源码 + `docs/` 经验库同仓共存）
- 本地 `/Users/beamjason/Documents/BeamNat/fixcloud-panel`；**原路径与部署上下文未动**；真实值在 gitignore 的 `.env`；作者唯一 `JasonBeam <124451452+JasonBeam@users.noreply.github.com>`
- 经验库原 `JasonBeam/homelab-panel`（本地 `/Users/beamjason/Documents/GitHub/homelab-panel`，init `2eed993`）已于 2026-11-25 整体并入本仓库 `docs/`，**远程仓库删除**；交叉链接改为仓库内相对路径
- 原 Fork `JasonBeam/homelab` **保留**为私有审计存档；上游 `JimmyChan233/homelab` **未触碰**
- 审计工作区 `/Users/beamjason/Documents/GitHub/homelab-sanitize`（push 已禁用）

## 2. 硬约束（违反即停）

1. 生产变更（订阅/Lucky/NAS/VPS/防火墙/重启）**必须当次明确授权**。
2. **禁止执行参考项目脚本**、禁止连接或修改原作者服务器。危险审计 148 项，其中 **82 项执行即自动外联/部署**。
3. 上游 `licenseInfo=null` → **只提炼设计思想，不复制源码/CSS/UI 资产/脚本/plist/unit**。保留来源归属，不冒充。
4. 真实凭据、IP、域名、邮箱、手机号、订阅 token、UUID **零上传**。占位符对照表只放 `local/`（已 gitignore）。
5. 远程操作：先确认 `Private` 再推送；**不 force push、不删远程分支、不公开仓库、不改上游**。
6. 每条结论标徽章：**【我方已验证】/【生产配置】/【参考提炼】/【待验证】/【已过时】**。参考项目的"已验证"≠我方已验证。
7. 不重复研究 `roadmap/06` §E 已定论项；旧报告行号只作线索，动手前重新核实。

## 3. 已验证事实（可直接引用，勿重复探测）

**FixCloud 生产**【我方已验证 2026-11-25】
- 容器 `fixcloud-panel` `8787->8080`，bridge `fixcloudpanel_fixcloud` 双栈，`User 1000:100`，`read_only:true`，`tmpfs /tmp 32m`，`cap_drop ALL`，`no-new-privileges`，`restart unless-stopped`。
- **生产覆盖 `writeEnabled:true`**（compose 默认 false）；`default-smb readOnly:false`；SMB bind RW。
- 34 路由；**18 条非 GET** 靠 `require_internal_request`（header `x-fixcloud-request:1`，`routes.py:107-109`）——**无 IP 白名单**。
- 普通保存**不再永久生成备份**（`save_service.py:308/318` 成功 `backupPath=None`）。
- `/data` 实际 **0770**（代码意图 0600）→ `sources.json` 明文凭据组可读。
- `temporary-sessions` **规模有界，非无限增长**【我方已验证 2026-11-25 复核】：实测 **2968** 个、`-mtime +1` 为 **0** → TTL 24h 清理存活；根因是 healthcheck 每 30s 无 cookie 建会话（约 2880/天）。旧表述「累积约 2911／无限增长」**【已过时】**。真隐患 = `cleanup_loop` 无异常守卫（`browser_session.py:90-96`）。`app_state.py AppStateStore` 为死代码。
- 内置来源仅 2：`default-smb`、`uploaded-files`；订阅 3 家可用，**不返回 URL**。
- `/api/vps/usage` 两台 `available:false`；根因 = **NAS 出口 IPv4 不在服务商 API 白名单**（非网络故障）。

**暴露面**【我方已验证 2026-11-25，含本轮独立复证】
- **P0-1 零鉴权凭据读取**：`GET /api/config/raw`（`routes.py:698`）与 `GET /api/config`（`routes.py:732`）**无任何鉴权**，`yaml_service.py:73-80` 零掩码。本机 LAN 实证：raw → **200 / 21399 B**（含 password/username/secret/token 各 1 处）、config → **200 / 21050 B**。**16 条 GET 路由全部无鉴权**。
- **P0-2 公开文件域无鉴权 + 目录索引**：`https://<PUBLIC_FILE_DOMAIN>/` → **200 / 683741 B**（目录索引，含 2 个 YAML 条目）；`FixCloud.yaml` → **200 / 20893 B**；`oixCloud.yaml` → **200 / 24012 B** → 公网可枚举下载双 YAML。
- **P0-3 管理写端点仅靠可伪造头**：18 条非 GET 全靠 `x-fixcloud-request:1`（`routes.py:107-109`），无 IP/网段/令牌；生产 `WRITE_ENABLED=true` → 带头即可改配置、删文件/备份、清审计（`DELETE /logs` 自身不审计）。与 P0-1 组合 = 完整读写接管 + 抹痕。
- `FixCloud.yaml` 内容含回家节点凭据、**3 个 provider 中 2 个带 query token**、`external-controller`+`secret`、66 rules、33 groups。
- 路由器 `op` uci firewall **无 8787 DNAT** → 面板未经路由器转发 WAN；公网暴露面主要是 Lucky 投递的公开文件域。
- `frontend/public/demo/*.html` 原含真实域名/IP/端口 → **已在源码仓库脱敏**（保留演示页）。生产 `GET /demo/*.html` 实测 **404**（镜像早于 demo 加入）→ 当前未暴露；但 vite 无 `publicDir` 排除，**下次构建将暴露**（P1，需构建前确认）。
- `docs/vps-singbox-integration-research.md` 约 40 处真实值。

**VPS / 网络**【我方已验证】
- 东京、香港两台**均无 sing-box**，只有 Lucky（host 网络）占 **TCP 443**；**UDP 443 两台均空闲**；`ufw` default deny，仅放行 22/80/443 tcp。
- 东京 1 vCPU / 955 MB / UDP 缓冲 208 KB；香港 1 vCPU / 1961 MB / 4 MB。
- 面板容器**可直连两台 VPS 22 与 443** → 走 `asyncssh` 独立连接，**不复用/不改动现有 SSH 隧道与密钥**。
- 面板在 bridge，**够不到宿主机 127.0.0.1 隧道端口**。
- `jpedge`/`hkedge` 双栈域名 AAAA 指向家庭 NAS，**不可用于定位 VPS 代理**。
- UI 生效层 = `visual-refresh.css`（`main.ts:13-14` 后 import 覆盖 `style.css`），Nothing 风单色红 `--nd-accent #d71921`。

## 4. 用户已决策（2026-11-25，按此执行）

| # | 决策 | 状态 |
|---|---|---|
| 1 | 源码纳管**方案 A**：独立 Private `JasonBeam/fixcloud-panel`，本仓库链接关联 | ✅ **已执行完成** |
| 2 | 上传前完成源码/demo/docs/配置/历史/凭据脱敏，禁上传真实密钥 | ✅ 已执行（门 0 + gitleaks 0） |
| 3 | **原 Fork 暂时保留，不删除** | ✅ 遵守中 |
| 4 | `design/07` 六项 UI 不一致 → **记入待办，暂不优先修改** | ✅ 已记 `roadmap/06` §F |
| 5 | **优先研究并完善管理权限、安全边界、私有订阅中心** | 🔄 进行中（`panels/fixcloud-panel/11`、`12`） |
| 6 | 参考朋友订阅管理设计但**独立实现**，复用现有 FastAPI + Vue + Lucky | 🔄 方案中 |
| 7 | **私有订阅完成后**再做 VPS 与 sing-box 自建节点集成 | ⏸ 排序已固定 |
| 8 | 每次开发/故障修复后把**已验证经验同步回本仓库** | 🔄 长期机制 |
| 9 | 不重复研究已有结论，先读 AGENTS.md 与对应知识库 | 🔄 长期机制 |
| 10 | 允许本地开发、隔离测试、Git 初始化、脱敏后 Private 上传；**生产配置修改/服务重启/防火墙修改/正式订阅迁移仍需单独授权** | 🔄 长期边界 |

**仍阻塞（需本人操作）**：服务商 API 白名单（控制台）、公开文件处置决策、**谁在消费公开 URL**、客户端版本确认。见 `roadmap/06` §A。

## 5. 下一步优先级

`P0 管理权限与安全边界 + 私有订阅中心` → `P1 sing-box 自建节点` → `P1 多 VPS 同步` → `P2 监控自愈` → `P2 Dashboard UI`（用户已确认此排序）
排序理由：公开文件是已验证暴露面且纯面板侧可解；sing-box 属生产变更，必须在订阅出口安全之后，否则新凭据又落进公开文件；自愈本身会引发事故，先护栏后自动化。

## 6. 入口索引

| 要做什么 | 读哪个 |
|---|---|
| 开工规范 | `AGENTS.md` |
| 找资料 | `README.md` |
| 改 FixCloud | `panels/fixcloud-panel/README.md` |
| 源码在哪 / 怎么提交 | `panels/fixcloud-panel/10-source-inclusion-plan.md` |
| 做私有订阅中心 | `panels/fixcloud-panel/11-subscription-center-spec.md` + `roadmap/01` |
| 做权限与安全加固 | `panels/fixcloud-panel/12-security-boundaries.md`（10 章／323 行／3 条 P0，门 0 残留） |
| 做新功能 | `roadmap/README.md` + 对应 01~05 |
| 查通用经验 | `knowledge/README.md`（12 篇，【参考提炼】） |
| 改 UI | `design/README.md`（生效层正本在 02） |
| 我方环境 | `infrastructure/README.md` |
| 排障 | `troubleshooting/README.md` + `playbooks/04` |
| 安全证据 | `reports/06-scan-acceptance.md` |

## 7. 验收命令（改完必跑，在仓库根）

```bash
python3 tools/verify-sanitized.py . --json reports/verify-final.json   # 必须 residual_findings=0
gitleaks dir . --config tools/gitleaks-repo.toml --redact --no-banner  # 必须 no leaks
gitleaks git . --config tools/gitleaks-repo.toml --redact --no-banner  # 提交后复扫历史
```
当前基线：本仓库门 0 残留、gitleaks 工作区与历史 0 leaks；源码仓库门 154 文件 0 残留、gitleaks 工作区与历史 0 leaks、125 文件本地=远程。

## 8. 未清除的风险（本仓库无法解决）

- 原 Fork 历史中 9 个 `backups/*-config-backup.tgz` 曾以**未加密明文 tarball** 入库（含代理配置与 `.env`）；`backups/immich/.env`、`sms-forwarder/SmsForwarder-import.json` 已删但仍在历史；443 条 commit 作者邮箱含 PII。
- **上游凭据需原持有人自行轮换**（Emby API key、Immich `.env`、订阅 token、Telegram bot token、密码总表全部凭据）。清单按类型+路径见 `reports/03-history-risk.md`，未回显真实值。
- 验收门是正则启发式，不能替代人工复核；变形/编码凭据可能漏检。
