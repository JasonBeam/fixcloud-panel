> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# FixCloud Panel 面板资料索引

**一句话定位**：运行在 QNAP NAS Docker 中的 Clash / Mihomo YAML 图形化管理后台，以 `ruamel.yaml` round-trip 文档树保留注释/顺序/引号/未知字段，提供来源管理、结构化编辑、完整 Diff、事务化安全保存、历史恢复、订阅流量与 VPS 用量监控、公开文件哈希核对。【已验证：README.md:3、backend/app/services/yaml_service.py:40-45】

> 源项目根：`/Users/beamjason/Documents/BeamNat/fixcloud-panel` → **源码仓库 https://github.com/JasonBeam/fixcloud-panel**（Private、`main`、提交 `15c9fe3`、125 文件；2026-11-25 就地 `git init` 并脱敏后推送，**原路径与部署上下文未动**）。下文所有 `backend/...`、`frontend/...` 引用均为该根下相对路径，行号为 2026-11-25 当前文件真实行号。
> 本仓库与源码仓库的关系：**链接 + 文档引用**，不复制源码、不建 submodule、不嵌套 Git。源码改动在源码仓库提交，已验证经验同步回本仓库。
> 生产部署：QNAP NAS Docker，容器名 `fixcloud-panel`，端口 `8787->8080`，bridge 网络 `fixcloudpanel_fixcloud`。【已验证：docker inspect】

## 当前状态摘要（结论先行）

| 维度 | 当前事实 | 标注 |
| --- | --- | --- |
| 生产运行 | 容器 running，StartedAt **2026-11-22**（与源码 11-22 改动同日，当前源码已部署） | 【已验证】docker inspect |
| 健康 | `GET /api/health` → `{status:ok,storage:ready,yaml:valid}` | 【已验证】只读探测 |
| 写开关 | 生产 `writeEnabled:true`、默认来源 `readOnly:false`（覆盖 compose 默认 false/true） | 【已验证】GET /api/sources + inspect bind RW:true |
| 路由数 | **34 条**（routes.py 1193 行 / 47203B） | 【已验证】routes.py |
| 来源 | 仅 2 个内置来源：`default-smb`（NAS SMB）、`uploaded-files`（会话上传）；无用户新增 smb/webdav | 【已验证】GET /api/sources |
| 可编辑文件 | FixCloud.yaml（20893B，面板属主可写）、oixCloud.yaml（24012B，admin 属主，面板很可能不可写正文） | 【已验证】catalog；【推测】oixCloud 权限 |
| VPS 用量 | 新功能（11-22），两台 `available:false`——厂商 API IP 白名单未放行 NAS 出口 IPv4（非缺 env，5 键已注入） | 【已验证】GET /api/vps/usage + inspect env 键名 |
| 订阅流量 | 3 家全可用（oixCloud/Kycloud/悠兔），不返回订阅 URL | 【已验证】GET /api/subscriptions/usage |
| 备份策略 | 普通保存**不再永久生成** `*.backup-*.yaml`；成功保存 backupPath=None；历史备份为旧版遗留 | 【已验证】README.md:115、save_service.py:308-318 |
| 当前视觉 | **Nothing 风扁平单色+红强调**（visual-refresh.css 覆盖层），非 style.css 的 iOS 基础层 | 【已验证】main.ts:13-14、visual-refresh.css |
| sing-box 集成 | **仅研究/设计，尚未实施**（routes 无 sing-box 路由、settings 无 SSH 字段） | 【已验证】grep + docs 研究报告 |
| 源码纳管 | **方案 A 已执行完成**：脱敏 10 文件 → 门 0 残留 + gitleaks 工作区与历史 0 leaks → 后端 49 passed / vitest 19 passed / 构建通过 → Private `JasonBeam/fixcloud-panel`（125 文件） | 【已验证】（详见 10） |
| 当前优先 | **管理权限与安全边界 + 私有订阅中心**；私有订阅完成后才做 sing-box 自建节点集成（用户 2026-11-25 决定） | 【我方已验证】用户决策 |

## 文档索引

| 文件 | 内容 |
| --- | --- |
| [01-architecture.md](01-architecture.md) | 分层架构、模块职责、数据流总览、编辑范围硬隔离原则 |
| [02-tech-stack.md](02-tech-stack.md) | 前后端技术栈与版本、构建链、依赖清单及用途 |
| [03-api-dataflow.md](03-api-dataflow.md) | 34 条路由逐条（方法/路径/入参/出参/鉴权/审计）+ 关键数据流时序 |
| [04-features-status.md](04-features-status.md) | 现有功能、待开发、已知问题（逐条标注验证状态） |
| [05-data-storage-permissions.md](05-data-storage-permissions.md) | 存储布局、文件权限属主、原子写与备份、凭据脱敏边界、审计表 |
| [06-deployment.md](06-deployment.md) | Docker 部署模板（全占位符）、网络/端口/只读根/tmpfs/UID-GID、重建回滚 |
| [07-testing-acceptance.md](07-testing-acceptance.md) | 测试清单与范式、本地验证命令、部署前后核对、UI 验收清单 |
| [08-decisions-history.md](08-decisions-history.md) | 历史技术决策及理由，含 2026-11-17 公开文件核对故障根因与修复 |
| [09-integrations.md](09-integrations.md) | 与 Lucky / QNAP NAS / VPS 集成（SSH 隧道、证书同步、公开文件、订阅来源） |
| [10-source-inclusion-plan.md](10-source-inclusion-plan.md) | **源码纳管执行记录（方案 A）**：两仓库职责、脱敏清单、.gitignore 加固、验收结果、后续守护 |
| [11-subscription-center-spec.md](11-subscription-center-spec.md) | **私有订阅中心实施方案**（15 章）：数据模型、API 契约、Token 生命周期、多客户端渲染、Subscription-Userinfo、自用/朋友隔离、复用点、P0-a…e 分阶段、迁移步骤、验收标准 |
| [12-security-boundaries.md](12-security-boundaries.md) | **管理权限与安全边界**（10 章）：威胁模型、路由鉴权矩阵、**3 条 P0**、加固方案（精确到文件:行号）、分阶段依赖、需用户授权事项 |

> **两份方案的强制依赖**：12 §8 的 **Phase 0（管理鉴权 require_admin、/data ACL、会话治理、demo 清理）必须先于 11 的 P0-b**；11 的所有管理端点一律依赖 `require_admin`，不得沿用可伪造的 `x-fixcloud-request` 头。**公开 file URL 退役（11 P0-e / 12 Phase 2）必须晚于订阅中心可用 + 消费方迁移完成**，否则断订。

## 相比一周前的主要变化（重点，基于 mtime + 当前源码，不凭旧报告）

1. **新增 VPS 流量监控功能（2026-11-22）**：新文件 `backend/app/services/vps_usage.py`（54 行）+ `backend/tests/test_vps_usage.py`（33 行）；新增路由 `GET /api/vps/usage`（routes.py:287-290）；`UsageView.vue` 新增 VPS 区块（L171-197）。读取 Evoxt（HK VPS，服务器套餐 GiB）与 Vultr（JP VPS，账号本月 GB 出站）厂商 API。【已验证：mtime + 源码 + 路由】
2. **routes.py 增至 1193 行 / 47203B、style.css 增至 3338 行 / 65531B、UsageView.vue 增至 281 行 / 10781B**（均 11-22 改动）。【已验证：ls mtime + read】
3. **.dockerignore 新增 `secrets` 与 `backup-vps-20261122`**（11-22 11:26），对应 NAS 部署目录新增的 secrets 目录与两个 11-22 部署前备份。【已验证：.dockerignore:13-14 + NAS ls】
4. **2026-11-17 公开文件核对故障修复**：README.md / docker-compose.yml / .env.example（均 11-17 mtime）记录 extra_hosts 把公开域名指向 bridge IPv6 网关由宿主 Lucky 本地投递；NAS 留有 `docker-compose.yml.bak-20261117`。【已验证：README.md:78 + compose:18-21 + bak 文件】
5. **生产容器 11-22 重建**，当前源码即生产版本（/api/vps/usage 等新路由已响应）。【已验证：inspect StartedAt + API 探测】

> 注：备份策略「普通保存不再生成永久备份」（save_service.py mtime 9-16）与 Nothing 风视觉（visual-refresh.css mtime 9-25）早于 11-22，若旧报告仍描述「每次保存生成备份」或「iOS 视觉」，应以当前事实为准。【已验证：当前源码；推测：旧报告差异】

## 脱敏与边界声明

- 本套文档不含任何真实凭据、真实 IP/域名/主机别名；占位符对照表仅存本机 `local/placeholder-map.md`（已被仓库 .gitignore 忽略，不入库）。
- 容器名、文件路径、环境变量键名、端口号、协议名、字段名属结构性事实，予以保留。
- 全程只读：未修改源项目任何文件，未调用任何写接口，未重启/部署。
