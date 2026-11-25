# env-map.example.md — 占位符对照表模板

> 复制本文件为 `env-map.md`（已 gitignore）后填入真实值。**不要把填好的版本入库。**

| 占位符 | 含义 | 真实值（本机填写） |
|---|---|---|
| `<NAS_LAN_IP>` | NAS 局域网 IPv4 | |
| `<NAS_PUBLIC_IPV6>` | NAS 公网 IPv6（AAAA 值） | |
| `<NAS_EGRESS_IPV4>` | NAS 当前出口 IPv4（服务商 API 白名单用） | |
| `<HOME_DOMAIN>` | 主域名 | |
| `<PUBLIC_FILE_DOMAIN>` | 公开文件服务子域 | |
| `<VPS_JP_IP>` | 东京 Vultr VPS 公网 IPv4 | |
| `<VPS_HK_IP>` | 香港 VPS 公网 IPv4 | |
| `<BRIDGE_GATEWAY_IPV6>` | 面板 bridge 网络 IPv6 网关 | |
| `<BRIDGE_IPV6>` | 面板 bridge IPv6 前缀 | |
| `<SUB_PROVIDER_1_DOMAIN>` | 订阅服务商 1 域名 | |
| `<SUB_PROVIDER_2_DOMAIN>` | 订阅服务商 2 域名 | |
| `<SUB_PROVIDER_3_DOMAIN>` | 订阅服务商 3 域名 | |
| `<LUCKY_PORT_RANGE>` | Lucky STUN 转发端口范围 | |
| `<PANEL_PORT>` | 面板对外端口（当前 8787） | |
| `<ADMIN_WEB_PORT>` | Lucky 统一入口端口（当前 24443） | |

## 不在此表登记的内容

密码、Token、API Key、SSH 私钥、订阅 URL、UUID、REALITY 私钥、Cookie、Webhook —— **一律不写入本仓库任何文件**，包括 local/。
