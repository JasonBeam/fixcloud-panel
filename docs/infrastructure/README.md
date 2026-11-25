# infrastructure — 我的基础设施架构

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）
> **这不是参考项目的环境。** 参考项目是 9 台 VPS + 群晖；我方是 QNAP NAS + 东京 Vultr + 香港 VPS + F50/R5C。

## 索引

| 文件 | 内容 |
|---|---|
| [01-topology.md](01-topology.md) | 总体拓扑、角色分工、数据流与信任边界 |
| [02-nas-qnap-docker.md](02-nas-qnap-docker.md) | QNAP NAS 与 Docker 环境（容器清单、网络、权限、只读约束） |
| [03-lucky-unified-management.md](03-lucky-unified-management.md) | Lucky 统一管理架构（DNS/Web/证书/端口转发/管理入口） |
| [04-vps-fleet.md](04-vps-fleet.md) | 东京 Vultr 与香港 VPS 现状（规格、系统、防火墙、端口占用） |
| [05-openwrt-openclash.md](05-openwrt-openclash.md) | F50/R5C OpenWrt + OpenClash/Mihomo 与 Lucky STUN 共存 |
| [06-homecoming-and-dualstack.md](06-homecoming-and-dualstack.md) | SOCKS5+TLS 回家节点、IPv4/IPv6 双栈入口、DNS 架构与陷阱 |
| [07-ssh-tunnels-cert-sync.md](07-ssh-tunnels-cert-sync.md) | VPS SSH 管理隧道、TLS 证书同步、统一管理 Web 入口 |

## 占位符约定

| 占位符 | 含义 |
|---|---|
| `<NAS_LAN_IP>` | NAS 局域网 IPv4 |
| `<NAS_PUBLIC_IPV6>` | NAS 公网 IPv6（AAAA 记录值） |
| `<NAS_EGRESS_IPV4>` | NAS 当前出口 IPv4（服务商 API 白名单用） |
| `<HOME_DOMAIN>` | 我的主域名 |
| `<PUBLIC_FILE_DOMAIN>` | 公开文件服务子域 |
| `<VPS_JP_IP>` / `<VPS_HK_IP>` | 东京 / 香港 VPS 公网 IPv4 |
| `<BRIDGE_GATEWAY_IPV6>` | 面板 bridge 网络的 IPv6 网关（宿主机侧） |
| `<SUB_PROVIDER_*_DOMAIN>` | 订阅服务商域名 |

## 使用约束

- 本目录描述**结构**（角色、端口、路径、容器名、环境变量键名、网络模式），不含真实地址与凭据。
- 需要真实值时查本机 `local/env-map.md`；**不得把该文件内容复制进入库文档**。
- 任何改动生产环境的操作必须先获授权（见根 AGENTS.md §4）。
