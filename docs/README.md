# Homelab 经验库（已并入 FixCloud Panel）

> JasonBeam 的个人 Homelab **基础设施知识库 · 面板开发中心 · 技术经验库 · 未来功能研究中心**。
> 本目录原为独立私有仓库 `JasonBeam/homelab-panel`，**2026-11-25 整体并入 FixCloud Panel 源码仓库**（https://github.com/JasonBeam/fixcloud-panel ，Private）的 `docs/` 下，原仓库随后删除。经验与源码现在**同仓共存**：更新/升级面板时直接在 `docs/` 查经验，不再跨仓库跳转。
> 不继承任何第三方 Git 历史，不与任何上游建立 Fork 关系。真实环境对照表只放 `docs/local/`（已 gitignore，永不入库）。
> 原参考 Fork `JasonBeam/homelab`（`JimmyChan233/homelab` 的授权学习副本）**仍保留**作私有审计存档，未并入、未复制其源码。

## 这个经验库是什么

不是某个开源 Homelab 项目的副本，而是把**两类来源**融合成一套可长期维护、可持续迭代、供 **DSH 与 Codex 共同使用**的工程资料：

1. **参考提炼**：从已授权学习的私有参考项目（`JimmyChan233/homelab`，经 Fork 授权）中提炼的通用技术经验——经过分类、归纳、重写与通用化，**不含任何原作者个人信息、真实网络环境与服务凭据，不复制其未经授权的源码与 UI 资产**。
2. **我方实践**：我自己的实际项目与已验证经验——FixCloud Panel、Lucky 统一管理架构、QNAP NAS Docker、东京/香港 VPS、F50/R5C OpenWrt、OpenClash/Mihomo、SOCKS5+TLS 回家节点、双栈入口、SSH 管理隧道、证书同步、私有订阅改造、sing-box 自建节点研究、Nothing 风格面板 UI。

**最终工程目标**：让 `FixCloud.yaml` 不再通过 file 域名无鉴权公开访问，改由 FixCloud 生成**可管理、可撤销、可自动更新**的私有订阅链接。详见 [roadmap/01-private-subscription.md](roadmap/01-private-subscription.md)。

## 内容分类徽章（每篇文档开头必须标注）

| 徽章 | 含义 | 使用约束 |
|---|---|---|
| **【我方已验证】** | 在我自己的环境里实际验证过的结论 | 可直接复用；仍需注明验证时间与边界 |
| **【生产配置】** | 当前生产环境的配置说明 | 只描述结构（端口/路径/容器名/环境变量键名），**真实 IP/域名/凭据一律占位符化** |
| **【参考提炼】** | 从参考项目提炼的通用经验 | **不等于我方已验证**；照搬前必须重新验证 |
| **【待验证】** | 尚未验证的技术方案/推测 | 必须附验证方法；不得当作事实引用 |
| **【已过时】** | 不再采用的方案 | 保留以说明"为什么放弃"，不得作为当前依据 |

> **严禁把参考项目的环境信息误认为我的实际环境。** 参考项目有 9 台 VPS + 群晖 + 自己的域名体系；我的环境是 QNAP NAS + 东京 Vultr + 香港 VPS + F50/R5C，两者拓扑、供应商、协议选型都不同。

## 目录导航（均相对本 `docs/` 目录）

| 目录 | 内容 | 索引 |
|---|---|---|
| `knowledge/` | 通用搭建经验与技术知识（12 篇，主要来自参考提炼 + 我方验证） | [knowledge/README.md](knowledge/README.md) |
| `panels/` | 我自己的面板项目资料（FixCloud Panel 十项） | [panels/README.md](panels/README.md) |
| `infrastructure/` | 我自己的基础设施架构（NAS/Lucky/VPS/OpenWrt/回家节点/隧道/证书/DNS） | [infrastructure/README.md](infrastructure/README.md) |
| `design/` | UI、组件与交互规范（含当前生效视觉层判定） | [design/README.md](design/README.md) |
| `templates/` | 脱敏配置与部署模板 | [templates/README.md](templates/README.md) |
| `playbooks/` | 标准操作流程（SOP） | [playbooks/README.md](playbooks/README.md) |
| `troubleshooting/` | 故障排查知识库（根因 → 解决 → 验证） | [troubleshooting/README.md](troubleshooting/README.md) |
| `roadmap/` | 未来功能与技术研究计划 | [roadmap/README.md](roadmap/README.md) |
| `reports/` | 脱敏审计与安全验收报告（含源码纳管判定） | [reports/README.md](reports/README.md) |
| `local/` | **仅本机**的真实环境对照表（已 gitignore，永不入库） | [local/README.md](local/README.md) |

仓库根文件：[../AGENTS.md](../AGENTS.md)（Agent 操作规范）· [CHANGELOG.md](CHANGELOG.md)（经验库更新记录）· [../tools/README.md](../tools/README.md)（脱敏验收门与 gitleaks 规则）· [../README.md](../README.md)（面板源码说明）

> `docs/vps-singbox-integration-research.md` 为面板源码仓库原有的 sing-box 集成研究，保留在 `docs/` 根。

## 安全边界（不可协商）

- **即使是 Private 仓库，也禁止上传任何真实生产凭据**：密码、Token、API Key、UUID、订阅链接、SSH 私钥、Webhook、Cookie、chat id、私人账单。
- 真实 IP / 域名 / 主机别名 / 设备标识 → 占位符（`<NAS_LAN_IP>`、`<PUBLIC_FILE_DOMAIN>`、`<VPS_JP_IP>` 等）；文档示例地址统一用 `example.com`、`192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`、`2001:db8::/32`。
- 真实值对照表只放 `docs/local/`（已 gitignore）。
- **不复制参考项目未经授权的源码与 UI 资产**；只提炼设计思想，并保留来源归属。
- **禁止执行参考项目的任何部署脚本，禁止连接或修改原作者服务器。**
- 生产环境（订阅 / Lucky / NAS / VPS）的任何修改必须获得明确授权；经验库**只整理资料，不改生产**。
- 推送前必须确认远程为 **Private**；不得公开仓库，不得修改上游。

## 脱敏验收门（在仓库根目录运行）

```bash
python3 tools/verify-sanitized.py . --json docs/reports/verify-final.json
gitleaks dir . --config tools/gitleaks-repo.toml --redact     # 需在仓库根目录运行
```

该门扫描 IPv4/IPv6、非白名单域名、邮箱、UUID、SS2022 密钥、PEM、age 私钥、Telegram token、+86 手机号、订阅 URL token、REALITY 私钥、密码赋值；**只输出类型与文件:行号，绝不打印真实值**；有残留则 exit 1。源码与经验库共用同一套规则，判定一致。

## 当前状态

- 2026-11-25：经验库整体并入 `fixcloud-panel/docs/`，原 `homelab-panel` 仓库删除；源码与经验同仓，交叉链接改为仓库内相对路径。
- 原 Fork `JasonBeam/homelab` **保留**作为私有审计存档。
- **上游 `JimmyChan233/homelab` 的历史凭据并未因脱敏而清除**；发现的有效凭据应由原持有人自行轮换（清单见 [reports/03-history-risk.md](reports/03-history-risk.md)）。
- **源码纳管已执行（方案 A）**：FixCloud 就地 `git init` → 脱敏 10 文件 → 验收门 0 残留 + Gitleaks 工作区与历史 0 leaks → 后端 49 passed / vitest 19 passed / 构建通过 → 推送 Private。**原路径与部署上下文未动**，真实值在 gitignore 的 `.env`。执行记录见 [panels/fixcloud-panel/10-source-inclusion-plan.md](panels/fixcloud-panel/10-source-inclusion-plan.md)。
- **当前优先**：管理权限与安全边界 + 私有订阅中心（[panels/fixcloud-panel/11](panels/fixcloud-panel/11-subscription-center-spec.md)、[12](panels/fixcloud-panel/12-security-boundaries.md)）；私有订阅完成后才做 sing-box 自建节点集成。
- `design/07` 六项 UI 不一致已记入 [roadmap/06](roadmap/06-research-backlog.md) §F 待办，**暂不优先修改**。
- 验收结果：见 [reports/06-scan-acceptance.md](reports/06-scan-acceptance.md)。
