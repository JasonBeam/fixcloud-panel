# sing-box 服务端配置模板

> 分类：【待验证】。**我方自行重写的脱敏示例**，非参考项目文件副本。
> 依据：sing-box 官方文档（stable v1.14.4，2026-10-24 核实）+ knowledge/03 字段语义。

## 文件

| 文件 | 协议 | 端口（示例） | 阶段 |
|---|---|---|---|
| [ss2022.json](ss2022.json) | Shadowsocks 2022 | TCP+UDP 18388 | MVP |
| [vless-reality.json](vless-reality.json) | VLESS + REALITY + vision | TCP 18443 | P2 |
| [hysteria2.json](hysteria2.json) | Hysteria2 | UDP 443 | P3 |
| [docker-compose.yml](docker-compose.yml) | 官方镜像部署 | — | 全阶段 |

## 上线前必做

```sh
# 1 替换全部占位符（密钥用官方生成器，不要手编）
sing-box generate rand --base64 16          # SS2022 aes-128-gcm
sing-box generate rand --base64 32          # SS2022 aes-256 / chacha20
sing-box generate reality-keypair           # REALITY 私钥/公钥
sing-box generate uuid                      # VLESS uuid

# 2 官方校验（必须，不可用自研校验替代）
sing-box check -C /etc/sing-box/

# 3 格式化（可选，便于 diff）
sing-box format -C /etc/sing-box/ -w

# 4 端口占用与防火墙检查
ss -tulpn | grep -E '18388|18443|:443'
ufw status verbose

# 5 备份现有配置后再原子替换，重载用 SIGHUP
```

## 关键注意

| 项 | 说明 |
|---|---|
| **重载** | 只有 SIGHUP；**没有 reload 子命令**；Clash API `PUT /configs` 是空操作 |
| **SIGHUP 行为** | 先 check，失败保持旧配置；成功则重建 → **存量连接断** |
| **clash_api** | 绑 0.0.0.0 **必须设 secret**；建议只绑 127.0.0.1 经 SSH 隧道访问 |
| **v2ray_api** | 官方 Docker/deb 默认构建**不含** `with_v2ray_api` → 按用户统计不可用 |
| **REALITY 借壳** | 目标须 GFW 外 + TLS1.3 + h2 + 非重定向 + 非 CDN；**最终目标需实测选择** |
| **hy2 前置** | `net.core.rmem_max`/`wmem_max` = 16777216；UDP 端口需 ufw + 云防火墙放行 |
| **证书** | 1.14 用 `certificate_provider`（内联 acme 已 Deprecated）；可复用 Lucky 证书 |
| **SS2022 公网裸口** | 参考项目经验：会触发主动重放，需配合伪装/白名单 |

## 安全底线

- 不创建无认证代理：所有 inbound 必须有 users/password。
- 凭据只存服务端 0600；不入浏览器、日志、本仓库。
- 不用双栈域名（AAAA 指向家庭 NAS）定位 VPS。
