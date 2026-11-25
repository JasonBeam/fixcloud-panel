# 02 · sing-box 自建节点管理（P1）

> 分类：【待验证】方案；现状依据为【我方已验证】。
> 完整研究报告（含证据与参考链接）：`/Users/beamjason/Documents/BeamNat/fixcloud-panel/docs/vps-singbox-integration-research.md`（本机，未入库）。
> **本轮不部署、不改 VPS。**

## 1. 现状【我方已验证】

| 事实 | 影响 |
|---|---|
| 两台 VPS **都没有 sing-box**，也没有 `/etc/sing-box` | 属全新部署，不是升级 |
| 两台都只有 Lucky 容器（host 网络） | TCP 443 已被占用 |
| **UDP 443 两台均空闲** | hy2 可复用 443/udp，与 Lucky TCP 443 共存 |
| ufw active，default deny incoming，仅放行 22/80/443 **tcp** | 新端口必须显式放行 |
| 东京 1 vCPU / 955 MB；UDP 缓冲 **208 KB** | 不适合重型面板；跑 QUIC 前必须抬 sysctl |
| 香港 1 vCPU / 1961 MB；UDP 缓冲 4 MB | 较宽裕，可作 hy2/测速优先落点 |
| 面板容器可直连两台 VPS 的 22/443 | **asyncssh 直连可行**，不需 host 网络、不动现有隧道 |

## 2. 技术选型决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 是否装第三方面板 | **不装**（3x-ui / Marzban / hiddify / s-ui 均不引入） | 东京资源紧张；许可证多为 GPL/AGPL；与现有面板职责重叠；维护成本高 |
| SSH 库 | **asyncssh**（EPL-2.0，py≥3.10） | 异步、与 FastAPI 契合；paramiko 是同步 LGPL；docker-py 会带入 paramiko |
| 部署形态 | **官方镜像钉版本 + 独立 bridge + 显式端口 + `/etc/sing-box` bind mount** | 回滚 = 改 tag；不污染宿主机；与 Lucky host 网络隔离 |
| 镜像 | `ghcr.io/sagernet/sing-box`（alpine，二进制 `/usr/local/bin/sing-box`，ENTRYPOINT `sing-box`） | 官方 |
| 版本 | **v1.14.4**（stable，2026-10-24 核实） | 官方 stable；不要用 latest |
| 启动命令 | `sing-box -D /var/lib/sing-box -C /etc/sing-box/ run` | 官方 compose 形态 |
| 配置校验 | **必须用官方 `sing-box check`** | 不可自研校验替代 |

## 3. 协议与端口规划

| 阶段 | 协议 | 端口（示例） | 理由 |
|---|---|---|---|
| **MVP** | **SS2022** | TCP + UDP **18388** | 实现最简、客户端覆盖最广、资源占用最低；先打通"部署→校验→发布→订阅→回滚"闭环 |
| P2 | **VLESS + REALITY** | TCP **18443**（非 443） | 抗封锁更强；无需自有证书；避开 Lucky 的 TCP 443 |
| P3 | **Hysteria2** | **UDP 443** | 需先抬 sysctl + 放行 UDP + 实测晚高峰 QoS |

**留决策杠杆**：若优先抗封锁，可对调 P1/P2（先 REALITY 后 SS2022）。

### 3.1 SS2022 关键字段

- `method`：`2022-blake3-aes-128-gcm`（16B 密钥）/ `2022-blake3-aes-256-gcm`（32B）/ `2022-blake3-chacha20-poly1305`（32B）。
- 密钥生成：`sing-box generate rand --base64 16`（或 32）。**禁止用口令派生**。
- 多用户：`users[]`；可配 `managed` + `ssm-api` 做 Shadowsocks Management。
- ⚠️ 参考项目经验：**公网裸 SS2022 口会触发主动重放**，需配合伪装/白名单（knowledge/10）。

### 3.2 VLESS + REALITY 关键字段

- `users[]`：`uuid` + `flow: xtls-rprx-vision`。
- `tls.reality`：`enabled`、`handshake{server,server_port}`、`private_key`、`short_id[]`。
- 密钥对：`sing-box generate reality-keypair`。
- **借壳目标要求**：GFW 外 + TLS1.3 + HTTP/2 + 非重定向 + 非 CDN。
- ⚠️ **张力点**：官方 README 推荐 `dl.google.com` 等热门目标；参考项目实测认为热门目标"被用烂"会被画像，改用**自有 AS 的高校/机构域名**（对照组 7 天 0 探测）。→ **必须实测选壳**，不照搬任何一方。验证：`openssl s_client -tls1_3 -alpn h2` + `curl -sI` 看有无 301。
- 空 `short_id` 必须摘除；零停机轮换用服务端双 id `["", 新id]` 过渡。

### 3.3 Hysteria2 关键字段

- `users[]`、`obfs{type: salamander, password}`（1.14 另有 gecko）、`masquerade`、`up_mbps`/`down_mbps`、`tls` **必填**。
- 前置：`net.core.rmem_max` / `wmem_max` = **16777216**（东京当前仅 212992）。
- 端口跳跃：`server_ports` + `hop_interval`（Clash 侧 `ports` / `hop-interval`）。
- ⚠️ 公开阻断报告较多（hysteria #1267/#1220/#1408/#1380），QUIC 用户态拥塞控制比内核 TCP 更耗 CPU。

## 4. 证书复用

- sing-box 1.14 提供 `certificate_provider`（内联 `acme` 已 Deprecated）。
- **可复用 Lucky 已签发的证书**（经现有证书同步链路落到 VPS），避免 sing-box 自己跑 ACME 抢 80/443。
- REALITY 不需要自有证书。

## 5. 配置生命周期（校验 / 原子更新 / 回滚）

| 步骤 | 做法 |
|---|---|
| 1 生成 | 面板侧生成候选 JSON，**不落盘到生产** |
| 2 校验 | `sing-box check -C <候选目录>`（官方，必须） |
| 3 备份 | 备份当前 `/etc/sing-box` 到带时间戳目录（保留 N 份） |
| 4 写入 | 写临时文件 → 回读校验 hash → `os.replace` 原子替换 |
| 5 重载 | **SIGHUP**（`kill -HUP`）；sing-box 会**先 check**，失败保持旧配置，成功则重建 → **存量连接会断** |
| 6 验证 | 重载后探活 + 端口监听 + 客户端实测 |
| 7 回滚 | 失败则恢复备份 + 再次 SIGHUP；容器形态可直接改回旧 tag |

**重要事实**：
- **没有 `reload` 子命令**；Clash API 的 `PUT /configs` 对 sing-box 是**空操作**，不要指望它热更配置。
- systemd 形态：`ExecReload=/bin/kill -HUP $MAINPID`，`Restart=on-failure`，`RestartSec=10s`。
- 子命令全集：`check` / `format` / `run` / `version` / `generate` / `merge` / `api`。

## 6. 统计与 API

| 能力 | 可用性 |
|---|---|
| `clash_api` | ✅ 官方构建可用。路由：`/connections`（含 `downloadTotal`/`uploadTotal`）、`/traffic`、`/logs`(ws)、`/proxies`、`/proxies/{name}/delay`、`PUT /proxies/{name}`、`GET/PATCH /configs`（**仅 mode/log-level**）、`/version`、`/rules`、`/cache` |
| `clash_api` 安全 | 绑 `0.0.0.0` **必须设 secret**；建议只绑 127.0.0.1，经 SSH 隧道访问 |
| `v2ray_api` 按用户统计 | ❌ **官方 Docker/deb 默认构建不可用**（`DEFAULT_BUILD_TAGS` 无 `with_v2ray_api`）→ 不要把它写进 MVP 依赖 |
| 官方 Clash 订阅输出 | ❌ 无 → 由 FixCloud 自己渲染（见 01） |

**流量统计口径**：MVP 用 `clash_api` 的 connections 累计 + 服务商账单 API（`/api/vps/usage`）双口径，**明确区分"节点流量"与"账号账单流量"**。参考项目教训：指标口径先定义再采集（knowledge/08）。

## 7. 与 Lucky 的兼容性

| 项 | 结论 |
|---|---|
| DNS/Web/证书/回家端口转发 | **继续由 Lucky 管**，sing-box 不碰 |
| TCP 443 | Lucky 占用 → sing-box 用 18443 等非 443 TCP |
| UDP 443 | 空闲 → 可给 hy2（需 ufw + 云防火墙放行） |
| 网络模式 | sing-box 用**独立 bridge**，不用 host，避免与 Lucky 抢端口 |
| 管理入口 | 不影响 24443 统一入口与 26611/26612 隧道 |
| 回家节点 | 不破坏 `<HOME_DOMAIN>:7891` 的 SOCKS5+TLS |

## 8. 安全底线

- 不创建无认证的公开代理。
- 节点密码 / UUID / REALITY 私钥 / 订阅密钥 **只存服务端 0600**，不入浏览器、不入日志、不入本仓库。
- SSH 私钥不进入面板容器镜像；用挂载 + 专用低权限用户。
- 不用 `jpedge`/`hkedge` 双栈域名定位 VPS（AAAA 指向家庭 NAS）。
- 自动检测 TCP/UDP 端口占用与防火墙状态后再部署。

## 9. 分阶段

| 阶段 | 内容 | 验收 |
|---|---|---|
| P1-a | SSH 通道 + 只读巡检（系统/资源/端口/防火墙/已装服务） | 巡检报告，无写入 |
| P1-b | 单台单协议（SS2022）部署 + check + 探活 | 客户端实测可用 |
| P1-c | 配置备份/校验/原子更新/回滚闭环 | 故意写坏配置 → 保持旧配置；故意失败 → 回滚成功 |
| P1-d | 节点纳入私有订阅（01） | 订阅含新节点且不含凭据泄露 |
| P2 | VLESS+REALITY（含实测选壳） | 抗封锁观察期 |
| P3 | Hysteria2（sysctl + UDP 放行 + QoS 实测） | 晚高峰吞吐/延迟数据 |

## 10. 未验证项

- 香港 VPS 供应商归属。
- 云厂商安全组是否另有 UDP 限制。
- 实际延迟/吞吐/晚高峰 QUIC QoS。
- 客户端版本（Stash iOS 3.4.0+ 才支持 REALITY；Stash 不支持 2022-chacha20）。
- 借壳目标最终选择（需实测）。
