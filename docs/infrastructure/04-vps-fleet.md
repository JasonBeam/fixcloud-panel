# 04 · VPS 舰队现状

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）
> **这不是参考项目的环境。** 参考项目是 9 台 VPS + 群晖；我方是 QNAP NAS + 东京 Vultr + 香港 VPS + F50/R5C。

## 1. 规格与系统【我方已验证，只读 SSH】

| 项 | 东京（Vultr） | 香港 |
|---|---|---|
| SSH 别名 | `vps` → `jpedge.<HOME_DOMAIN>` | `hk` → `<VPS_HK_IP>` |
| 公网 IPv4 | `<VPS_JP_IP>` | `<VPS_HK_IP>` |
| 系统 | Ubuntu 24.04.5 | Ubuntu 26.04 |
| 内核 | 6.8.0-149 | 7.0.0-14 |
| vCPU | **1** | **1** |
| 内存 | **955 MB**（可用 538） | **1961 MB**（可用 1369） |
| 根盘 | 23G，已用 6.4G（30%） | 20G，已用 1.8G（10%） |
| SSH 用户 | root，**sudo 免密** | root，**sudo 免密** |
| sshd | OpenSSH_9.6p1 Ubuntu-3ubuntu13.2 | OpenSSH_10.2p1 Ubuntu-2ubuntu3 |
| 供应商 | Vultr（IP 段推断） | **未验证**（用户称 Evoxt，需核实） |

## 2. 已部署服务【我方已验证】

- 两台**都只有 Lucky 容器**（`gdy666/lucky:v3_lucky_docker`，host 网络）。
- 两台**都没有 sing-box**，也没有 `/etc/sing-box`。→ sing-box 属**全新部署**，不是升级。
- 监听：TCP 443（Lucky）、TCP 16601（Lucky 管理）、TCP 22（sshd）；UDP 各一个高位端口（Lucky）。

## 3. 防火墙与端口占用【我方已验证】

| 项 | 东京 | 香港 |
|---|---|---|
| ufw | **active**，default **deny incoming** | 同 |
| 已放行 | 22/80/443 **tcp**（v4+v6） | 同 |
| **UDP 443** | **空闲** | **空闲** |
| TCP 443 | 被 Lucky 占用 | 被 Lucky 占用 |
| `net.core.rmem_max` / `wmem_max` | **212992（208 KB）** | **4194304（4 MB）** |

> **两个决定性结论**：
> 1. **UDP 443 可与 Lucky 的 TCP 443 共存** → Hysteria2 可以复用 443/udp，不必另开高位端口（但仍需 ufw 放行 + 云防火墙确认）。
> 2. **东京 UDP 缓冲只有 208 KB** → 跑 QUIC/Hysteria2 前必须抬 `rmem_max`/`wmem_max`（官方建议 16777216），否则高带宽下丢包。这是把 hy2 排到 P3 而非 MVP 的硬理由之一。

## 4. 资源约束对选型的影响【我方已验证 + 推测】

- 东京 **1 vCPU / 955 MB**：不适合再叠重型面板（3x-ui / Marzban / hiddify 等）。sing-box 裸核约 20 MB 量级，单实例多 inbound 共享路由，是合适的形态。【推测：具体占用需实测】
- QUIC 在用户态跑拥塞控制，比内核 TCP 更耗 CPU → 1 vCPU 上 hy2 与 Reality 并存需实测。【待验证】
- 香港内存较宽裕，可作为 hy2 / 测速 / 中转的优先落点。【推测】

## 5. 面板容器到 VPS 的可达性【我方已验证】

| 目标 | 结果 |
|---|---|
| `<VPS_JP_IP>`:22 | OK，0.41s |
| `<VPS_HK_IP>`:22 | OK，0.18s |
| 两台 :443 | OK |

→ **asyncssh 从面板容器直连 VPS 可行**，不需要 host 网络，不需要改动现有 SSH 隧道。

## 6. 服务商流量 API【我方已验证，当前不可用】

- 面板已有 `/api/vps/usage`（读**服务商账单流量**，不是节点流量）。
- 实测：Vultr 返回 401 `Unauthorized IP address: <NAS_EGRESS_IPV4>`；Evoxt 返回 HTTP 200 但 body 为 `IP Address Unauthorized`。
- 网络本身通（TCP 443 到两家 API 均 0.01–0.02s；无 token 请求 Vultr 返回 `Invalid API token`，证明可达）。
- **根因 = NAS 当前出口 IPv4 不在两家 API 白名单**，属账号侧配置，需我本人在控制台添加。【已验证】
- 凭据已配置在容器 env（键名齐全），**不回显值**。

## 7. 待验证项

- 香港 VPS 供应商归属。
- 云厂商侧防火墙（安全组）是否另有 UDP 限制——ufw 之外还有一层。
- 实际延迟/吞吐/晚高峰 QUIC QoS 表现（未实测）。
