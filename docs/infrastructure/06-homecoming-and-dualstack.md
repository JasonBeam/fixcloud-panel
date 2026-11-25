# 06 · 回家节点、双栈入口与 DNS 架构

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）

## 1. SOCKS5 + TLS 回家节点【生产配置】

| 项 | 值 |
|---|---|
| 在 Clash 配置中的位置 | `proxies` 数组，**唯一的手工节点** |
| name | `localhost`（历史命名，语义是"回家"） |
| type | `socks5` |
| server | `<HOME_DOMAIN>` |
| port | 7891 |
| 其他字段 | `tls: true`、`udp: true`、`username`、`password`（**值不入库**） |

**用途**：在外通过它回到家庭内网，访问 NAS 面板与其他内网服务。面板本身**无登录页**，安全性依赖"仅家庭内网 + 这条 SOCKS5 通道"。

**硬约束**：任何改造（私有订阅、sing-box 自建节点）**不得破坏这条节点**，也不得把它的凭据扩散到新的公开面。

## 2. DNS 架构与陷阱【我方已验证】

| 记录 | 类型 | 指向 | 用途 / 陷阱 |
|---|---|---|---|
| `<HOME_DOMAIN>` | **仅 AAAA** | `<NAS_PUBLIC_IPV6>` | 家庭 IPv6 入口；**无 A 记录** |
| `jpedge.<HOME_DOMAIN>` | 双栈 | A→东京 VPS，**AAAA→家庭 NAS** | ⚠️ **不可用于定位 VPS 代理节点** |
| `hkedge.<HOME_DOMAIN>` | 双栈 | A→香港 VPS，**AAAA→家庭 NAS** | ⚠️ 同上 |
| `origin.<HOME_DOMAIN>` | — | 源站 | 证书/回源用 |
| `<PUBLIC_FILE_DOMAIN>` | — | NAS Lucky | 公开文件服务（**当前无鉴权**） |
| `lucky-lan.<HOME_DOMAIN>` | — | NAS 局域网 | 统一管理入口（24443） |

> **最大的坑**：`jpedge`/`hkedge` 的 AAAA 指向家庭 NAS。双栈客户端会优先 IPv6 → 把本该去 VPS 的流量引回家。
> **对策**：VPS 定位一律用 **IPv4 直连 IP** 或强制 `-4` / `ipv4_only`；不要用这两个域名做代理 server。

## 3. 公开文件服务的暴露面【我方已验证 · 高风险】

- `https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml` **无鉴权返回 200**，20893 字节，与 NAS 本地文件一致。
- 解析后确认内含：回家节点的 `username`/`password`、3 个 `proxy-providers` 的订阅 URL（其中 2 个带 token query）、`external-controller` 与 `secret`、66 条 rules、33 个 proxy-groups。
- **结论**：自建节点凭据与订阅 token **绝不能进入这个文件**。
- **改造目标**：由 FixCloud 生成**可管理、可撤销、可自动更新的私有订阅链接**取代公开文件。见 `roadmap/01-private-subscription.md`。
- 本轮**只记录与规划，不改动生产订阅**。

## 4. IPv6 连通性矩阵【我方已验证】

| 路径 | 结果 |
|---|---|
| 面板容器 → 公网 IPv6 站点 | ✅ 通（200 / 0.16s） |
| 面板容器 → **NAS 自身公网 IPv6** | ❌ **不通**（无 NAT66 / 回环投递） |
| NAS 宿主机 → 公网 IPv6 出网 | ❌ 超时 |
| 外部网络 → NAS 公网 IPv6 入站 | ✅ 在线（跨网访问 `<PUBLIC_FILE_DOMAIN>` 0.13s / 200） |

**曾导致的故障**：面板"发布核对"要回读公开 URL，容器解析到 NAS 自身公网 IPv6 → 12s 超时。

**修复（已验证）**：给面板容器加 `extra_hosts`，把 `<PUBLIC_FILE_DOMAIN>` 指到 **bridge 网络的 IPv6 网关** `<BRIDGE_GATEWAY_IPV6>`。因为 Lucky 用 host 网络监听 `:::443`，宿主机该地址上就有 Lucky → **本地投递成功**，核对 `matching:true`，87ms。

**为什么不用 NAT66**：QNAP 宿主机 sudo 需密码、根文件系统是 ramdisk，无法持久写 ip6tables 规则。Docker 层的 `extra_hosts` 是唯一可行且可回滚的最小改动。

## 5. 待验证

- 家庭 IPv4 出口是否仍有公网可达性（当前出口 IPv4 为 `<NAS_EGRESS_IPV4>`，疑似 CGNAT）。
- DDNS 更新链路与 TTL（本轮未核实）。
- 是否需要为私有订阅单独准备一个与代理域物理隔离的管理域（参考项目经验：CT 日志会串联同主域，见 knowledge/07、10）。
