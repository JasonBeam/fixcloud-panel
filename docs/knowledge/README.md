# knowledge — 通用搭建经验与技术知识

> **分类：【参考提炼】**（全部 12 篇）
> 来源：参考项目 `JimmyChan233/homelab`（私有仓库，经 Fork 授权学习）。
> **这些经验来自原作者的环境，不是我的环境。** 迁移前必须按每篇「③ 需要重新验证的结论」重验。
> 归属与脱敏约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

## 阅读顺序建议

| 目的 | 先读 |
|---|---|
| 新建一台 VPS | 01 → 09 → 02 |
| 设计节点池与出口 | 04 → 03 → 10 |
| 做私有订阅服务 | 05 → 06 → 03 |
| 做监控与自愈 | 08 → 11 |
| 排查线上故障 | 11（案例库）→ 对应专题 |
| 迁移到 FixCloud | **12（24 条迁移清单）** → 各专题 |

## 目录

| # | 文件 | 主题 | 篇幅 |
|---|---|---|---|
| 01 | [01-vps-baseline.md](01-vps-baseline.md) | VPS 建站与安全基线：初始化/内核调优/防火墙/fail2ban/SSH key-only/端口规划/供应商取舍 | 80 行 |
| 02 | [02-docker-systemd.md](02-docker-systemd.md) | Docker 与 systemd：compose 规范/单元陷阱/launchd 差异/日志轮转/备份回滚 | 76 行 |
| 03 | [03-singbox-mihomo-clash.md](03-singbox-mihomo-clash.md) | 协议选型与字段语义：sing-box / mihomo / Clash / Stash / Surge 支持矩阵与映射 | 89 行 |
| 04 | [04-multi-node-architecture.md](04-multi-node-architecture.md) | 多节点多协议架构：节点池分层/中转链式/出口选择/故障切换 | 97 行 |
| 05 | [05-subscription-server.md](05-subscription-server.md) | 订阅服务器与生成器设计 | 96 行 |
| 06 | [06-token-auth-user-management.md](06-token-auth-user-management.md) | Token 鉴权与用户管理：生成/轮换/吊销/配额/多用户隔离/最小权限 | 102 行 |
| 07 | [07-dns-ddns-tls-reverse-proxy.md](07-dns-ddns-tls-reverse-proxy.md) | DNS/DDNS/TLS/反代：记录分层/双栈陷阱/证书签发同步/单域名多服务 | 97 行 |
| 08 | [08-traffic-monitoring-selfheal.md](08-traffic-monitoring-selfheal.md) | 流量统计/监控/故障自愈：指标口径/巡检节奏/触发回退/告警降噪/看板 | 85 行 |
| 09 | [09-ssh-hardening-least-privilege.md](09-ssh-hardening-least-privilege.md) | SSH/安全加固/最小权限：密钥/known_hosts/跳板隧道/age 加密/红队收敛/客户端泄漏 | 84 行 |
| 10 | [10-anti-censorship.md](10-anti-censorship.md) | 抗封锁：频封溯源/协议纯净化/借壳选择/UDP QoS/端口伪装/被封处置 | 113 行 |
| 11 | [11-fault-cases.md](11-fault-cases.md) | 故障案例库：14 组案例，每案 现象→排查→根因→解决→预防 | 132 行 |
| 12 | [12-fixcloud-migration.md](12-fixcloud-migration.md) | **可迁移到 FixCloud / Lucky / QNAP 的 24 条经验清单** | 141 行 |

## 每篇的固定结构

1. **① 通用可复用经验** — 与原作者环境无关、可直接借鉴的设计与判据。
2. **② 原作者特定环境经验** — 明确标注依赖（机型/供应商/客户端/拓扑），不可照搬。
3. **③ 需要重新验证的结论** — 给出验证方法，迁移前必须做。
4. **④ 来源文档路径清单** — 参考仓库内的相对路径，便于回溯（不含真实值）。
5. 部分篇目另有 **可迁移到 FixCloud / Lucky / QNAP** 段。

## 证据分级（本目录内）

| 标记 | 含义 |
|---|---|
| 【已验证】 | **原作者记录中**实际读到/测到 |
| 【推测】 | 提炼者推断，待核 |

> 我方环境的验证结论一律写在 `infrastructure/`、`panels/`、`troubleshooting/`，用【我方已验证】标记，**不与本目录混用**。

## 最有价值的 10 条（跨篇提炼）

1. **换 IP ≠ 安全**：复用旧域名 + 旧端口会让新 IP 被关联，存活时间从 4.5 月 → 18 天 → 30.5 小时递减。必须全新无关子域 + 独立证书 + 全新端口 + 白名单 + 静置。（10）
2. **协议纯净化**：无 fallback 的 Trojan/AnyTLS 握手后 EOF 是确定指纹；裸 SS2022 公网口会触发主动重放。必须补 decoy/masquerade。（03/10）
3. **探针要 e2e + 多采样多数决**：端口活 ≠ 能用；单采样在丢包链路必然假阴性，曾把主力机一天重启 66 次掐断全体用户。（08/11-B）
4. **自愈自身会引发事故**：docker 慢 ≠ 死；周期定时器一律 `OnCalendar`，只用 `OnUnitActiveSec` 会卡 elapsed；护栏 = 重启间隔 + 每日上限 + 防抖。（02/08/11-E）
5. **证书哨兵必须验信任链**，不只看到期日：误删回落自签 `notAfter 2028` 看着绿、浏览器照样红。（07/11-D）
6. **代理 → 内网洞三次假已修**：`ip_is_private` 不含 CGNAT 100.64/10；域名绕过要 `action:resolve`；复验字面 IP 和域名都要 502，一次性验证要变常驻红队探针。（09/11-I）
7. **测速口径决定结论**：明文 HTTP 被 DPI 降速给出差百倍的假数据；吞吐走加密多连接直连源，延迟只信光纤边缘。延迟 ≠ 吞吐，地理近 ≠ 晚高峰快。（01/08）
8. **封锁判定要防抖**：连续 2 轮 + >70% 不通才判封，非对称迟滞 + 抖动锁；限的是动作本身，不是播报。（04/08）
9. **订阅多用户最小权限**：token 路径鉴权、朋友凭据 600 隔离、只发线路 id、撤销即删凭据、原子写 + version 单调 + mtime 判重 + 泄露断言 + check 不过整体回滚。（05/06）
10. **行为去噪**：探测降频 + lazy + 统一 DoH、LAN 噪声 DIRECT、CT 日志会串联同主域 → 管理域与代理域物理隔离、跨机探活走 tailnet。（07/09/10）

## 使用边界

- 本目录**只含设计思想与判据**，不含可直接执行的原作者脚本、plist、systemd 单元、compose 文件。
- 参考仓库**无许可证**（`licenseInfo=null`）→ 不复制源码与 UI 资产，只重述设计。详见 ATTRIBUTION.md。
- 需要落地模板时去 `templates/`（我方重写、脱敏、可安全执行）。
