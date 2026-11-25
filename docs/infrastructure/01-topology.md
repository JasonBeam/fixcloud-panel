# 01 · 总体拓扑与信任边界

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）
> **这不是参考项目的环境。** 参考项目是 9 台 VPS + 群晖；我方是 QNAP NAS + 东京 Vultr + 香港 VPS + F50/R5C。

## 1. 角色分工【我方已验证】

| 角色 | 载体 | 职责 | 不负责 |
|---|---|---|---|
| **Lucky（NAS）** | QNAP Docker，host 网络 | DNS/DDNS、Web 服务与反向代理、TLS 证书签发与续期、回家节点端口转发、统一管理入口 | 不做 VPS 自建代理 |
| **Lucky（VPS ×2）** | 东京/香港 Docker，host 网络 | 各自机器的 Web/证书/端口转发 | 不做节点管理面板 |
| **FixCloud Panel** | QNAP Docker，自定义 bridge | Clash/Mihomo 配置的图形化编辑、来源管理、Diff 评审保存、备份、发布核对、订阅用量读取 | 不登录页、不公网暴露 |
| **sing-box（规划）** | VPS Docker，独立 bridge | VPS 自建代理节点（SS2022 / VLESS+REALITY / Hysteria2） | 不碰 Lucky 的 DNS/Web/证书 |
| **OpenClash/Mihomo** | F50/R5C OpenWrt | 家庭侧分流与出口选择 | — |
| **客户端** | Clash Verge / OpenClash / Stash | 消费订阅 | — |

## 2. 数据流【我方已验证】

```
订阅服务商 ──(proxy-providers, http, interval 86400)──┐
手工节点（SOCKS5+TLS 回家）────────────────────────────┤
                                                      ▼
                                          FixCloud.yaml（NAS SMB 挂载目录）
                                                      │
                              FixCloud Panel 结构化编辑 → Diff → 原子保存 → 备份
                                                      │
                                                      ▼
                                   公开文件服务（当前：无鉴权，待改造）
                                                      │
                                      Clash Verge / OpenClash / Stash 拉取
```

**改造目标**：把最后一段换成 FixCloud 自建的**私有订阅端点**（Token 鉴权、可撤销、可自动更新），见 `roadmap/01-private-subscription.md`。

## 3. 信任边界【我方已验证】

| 边界 | 事实 | 影响 |
|---|---|---|
| 面板访问 | 仅家庭内网 + 自己的 SOCKS5 通道；**无登录页**；端口 8787 **不得映射公网** | 面板本身不是公网攻击面 |
| 内网请求头 | 后端 `require_internal_request` 校验 `X-FixCloud-Request: 1` | 非浏览器直连需带该头 |
| 公开文件服务 | `https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml` **无鉴权可读**，且文件内含回家节点凭据与订阅 token | **当前最大暴露面**，必须改造 |
| 容器 → 宿主机 loopback | 面板在 bridge，**够不到宿主机 127.0.0.1 上的 SSH 隧道端口** | 复用隧道需改绑定或直连 VPS |
| 容器 → NAS 自身公网 IPv6 | **不通**（无 NAT66/回环投递） | 曾导致发布核对 12s 超时，已用 extra_hosts 修复 |
| 容器 → 公网 IPv6 | **通**（实测某公网 IPv6 站点 200 / 0.16s） | 不能笼统说"容器 IPv6 不通" |
| 容器 → VPS SSH | **通**（东京 0.41s、香港 0.18s，TCP 22 与 443 均可达） | asyncssh 直连可行，无需 host 网络 |

## 4. 关键约束（不可违反）

1. **不用 jpedge/hkedge 双栈域名定位 VPS 代理节点**——其 AAAA 指向家庭 NAS，会把流量引回家。VPS 定位用 IPv4 直连或 `-4`。
2. Lucky 继续管 DNS/Web/证书/回家端口转发；sing-box 只管 VPS 自建代理。
3. 不影响现有网站、Lucky 管理入口、SSH 隧道、证书同步。
4. 不创建无认证的公开代理；不泄露节点密码、订阅密钥、SSH 私钥。
5. 编辑范围硬隔离：只改 config 主 YAML，不读/改/覆盖 rules 与订阅内容。
