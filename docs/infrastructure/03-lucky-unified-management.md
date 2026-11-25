# 03 · Lucky 统一管理架构

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）
> **这不是参考项目的环境。** 参考项目是 9 台 VPS + 群晖；我方是 QNAP NAS + 东京 Vultr + 香港 VPS + F50/R5C。

## 1. 职责边界【我方已验证】

Lucky 在我的架构里是**统一的边缘与管理层**，不是代理节点管理器：

| 能力 | NAS Lucky | VPS Lucky ×2 |
|---|---|---|
| DNS / DDNS | ✅ 主 | — |
| Web 服务 / 反向代理 | ✅ | ✅ 各自机器 |
| TLS 证书签发与续期 | ✅ Let's Encrypt，CN=`<HOME_DOMAIN>` | ✅ |
| 回家节点端口转发 | ✅ TCP 监听 + STUN 穿透 | — |
| 管理入口 | 16601 | 16601（经隧道访问） |
| VPS 自建代理 | ❌ 交给 sing-box | ❌ 交给 sing-box |

## 2. 监听与网络【我方已验证】

- NAS Lucky：**host 网络**，监听 `:::443` 与 `:::8443`（双栈），管理端口 16601。
- VPS Lucky：镜像 `gdy666/lucky:v3_lucky_docker`，**host 网络**，TCP 443 / 16601，UDP 各有一个高位端口（东京与香港不同）。
- 因为 Lucky 用 host 网络，**宿主机该 bridge IPv6 网关地址上也有 Lucky 的 :::443**——这是 `extra_hosts` 修复能成立的物理前提（本地投递，不需要 NAT66）。

## 3. 统一管理入口【我方已验证】

`lucky-vps-admin-web`（nginx:alpine，host 网络）：

| 配置项 | 值 |
|---|---|
| listen | `<NAS_LAN_IP>`:24443 ssl default_server |
| server_name | `lucky-lan.<HOME_DOMAIN>` |
| ssl_certificate | `/cert/xyz.pem`（来自证书导出目录） |
| `location = /jp` | 308 → `/jp/` |
| `location ^~ /jp/` | proxy_pass `http://127.0.0.1:26611/` |
| `location ^~ /hk/` | proxy_pass `http://127.0.0.1:26612/` |
| `location /` | proxy_pass `http://127.0.0.1:16601/`（NAS Lucky） |
| 热重载 | `nginx -t && nginx -s reload` |

> **一个入口管三台 Lucky**，靠 SSH 隧道把 VPS 的 16601 映射到 NAS loopback。详见 [07-ssh-tunnels-cert-sync.md](07-ssh-tunnels-cert-sync.md)。

## 4. 与 OpenClash 的共存陷阱【我方已验证】

Lucky 在 NAS host 网络做 TCP 监听端口转发时，**R5C 侧 OpenClash 的 TCP 接管链会先于 clash 规则命中**，导致 Lucky 的 STUN 穿透流量被错误接管。修复与回退见 [05-openwrt-openclash.md](05-openwrt-openclash.md)。

## 5. Lucky 开放接口【待验证】

- Lucky 文档明示 **OpenToken 可调接口**，但**无官方 OpenAPI 规范**。
- 社区抓包得到的 `PUT /api/portforward` 等路径**未验证**。
- **结论**：不要把"用 Lucky API 自动改端口转发"当作已具备的能力。若要做，先只读探测接口与鉴权方式，再申请授权。
- 参考项目有 4 个 Cloudflare DNS 写脚本——那是**它自己的**做法，我方 DNS 由 Lucky 管，不可照搬。

## 6. 不可破坏项（硬约束）

1. 现有网站与反代规则。
2. Lucky 管理入口（16601 与 24443 统一入口）。
3. SSH 隧道（26611/26612）。
4. 证书同步链路。
5. 回家节点的端口转发与 STUN 穿透。
