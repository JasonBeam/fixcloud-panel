# 07 · VPS SSH 管理隧道、证书同步与统一入口

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）

## 1. 设计目的【我方已验证】

VPS 上的 Lucky 管理端口（16601）**不直接暴露公网**，而是通过 SSH 本地转发映射到 NAS 的 loopback，再由 NAS 上一个 nginx 统一入口按路径分发。这样：

- 管理面只有一个局域网入口（`<NAS_LAN_IP>:24443`）。
- VPS 侧只需放行 SSH，不需要为管理端口开防火墙。
- 三台 Lucky（NAS / 东京 / 香港）在一个界面里切换。

## 2. 隧道容器【生产配置】

| 容器 | 镜像 | 网络 | 转发 |
|---|---|---|---|
| `lucky-vps-admin-tunnel` | `local/lucky-vps-transport:1` | **host** | `127.0.0.1:26611` → `127.0.0.1:16601`（东京） |
| `lucky-hk-admin-tunnel` | 同上 | **host** | `127.0.0.1:26612` → `127.0.0.1:16601`（香港） |

**SSH 命令形态**（脱敏后，结构保留）：

```sh
umask 077
cat /ssh/id_ed25519 >/run/key/id      # 东京；香港复制到 /tmp/key/id
chmod 600 /run/key/id
exec /usr/bin/ssh -4 -N \
  -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/ssh/known_hosts \
  -o IdentitiesOnly=yes -i /run/key/id \
  -L 127.0.0.1:<LOCAL_PORT>:127.0.0.1:16601 lucky-tunnel@<VPS_IP>
```

**值得借鉴的设计点**：

| 做法 | 理由 |
|---|---|
| 专用低权限用户 `lucky-tunnel` | 不用 root 做隧道；最小权限 |
| `-4` | 强制 IPv4，避开 AAAA 指向家庭 NAS 的双栈陷阱 |
| `BatchMode=yes` | 禁止交互式口令提示，失败即退出 |
| `ExitOnForwardFailure=yes` | 转发建不起来就退出，避免"隧道活着但端口不通"的假健康 |
| `ServerAliveInterval=15` + `CountMax=3` | 45s 内检出死连接 |
| `StrictHostKeyChecking=yes` + 固定 `known_hosts` | 防中间人；主机密钥变更会失败而不是静默接受 |
| `IdentitiesOnly=yes` | 只用指定密钥，不乱试 agent 里的其他密钥 |
| `umask 077` + 复制到临时路径 + `chmod 600` | 挂载卷上的密钥权限可能不符合 SSH 要求，复制后收紧 |
| 绑定 **127.0.0.1** | 转发端口不对外暴露 |

**密钥目录**（只记录路径，**不读取内容**）：`/share/homes/BeamJason/.lucky-vps/{tunnel,hk-tunnel}` → 容器内 `/ssh`。

## 3. 证书同步【生产配置】

| 容器 | 网络 | 入口 | 挂载 |
|---|---|---|---|
| `lucky-vps-cert-sync` | bridge | `/ssh/sync.sh` | `.lucky-vps/cert` → `/ssh`；`/share/Container/goodlucky/.vps-cert-export` → `/export` |
| `lucky-hk-cert-sync` | bridge | 同上 | `.lucky-vps/hk-cert` → `/ssh`；同一 export 目录 |

**链路**：NAS Lucky 签发/续期证书 → 导出到 `.vps-cert-export` → sync 容器经 SSH 推到 VPS → VPS Lucky/nginx 使用。

> 本轮**未读取 sync.sh 内容**，具体推送机制与触发周期属【待验证】。

## 4. 统一管理入口【生产配置】

`lucky-vps-admin-web`（nginx:alpine，host 网络）：

| 路径 | 后端 |
|---|---|
| `/jp/` | `http://127.0.0.1:26611/`（东京 Lucky） |
| `/hk/` | `http://127.0.0.1:26612/`（香港 Lucky） |
| `/` | `http://127.0.0.1:16601/`（NAS Lucky） |

- listen `<NAS_LAN_IP>:24443 ssl default_server`，server_name `lucky-lan.<HOME_DOMAIN>`，证书 `/cert/xyz.pem`。
- `location = /jp` → 308 到 `/jp/`（补斜杠，避免相对路径错乱）。
- 热重载：`nginx -t && nginx -s reload`（先校验再重载，失败不影响现网）。

## 5. 对 FixCloud 集成的影响【我方已验证】

| 事实 | 影响 |
|---|---|
| 隧道只绑 **宿主机 loopback** | 面板容器在 bridge，**够不到 26611/26612** |
| 面板容器可直连 VPS 的 22/443 | **asyncssh 直连可行**，不需要 host 网络、不需要改隧道 |
| 隧道用的是专用低权限用户 | 若面板要复用同一用户，需确认其权限是否够做 sing-box 部署（大概率不够，应另建专用用户） |

**决策**：MVP 走 **面板容器 → VPS 的独立 SSH 连接（asyncssh）**，与现有 Lucky 隧道**互不干扰**。不复用隧道、不改其绑定、不动其密钥。

## 6. 不可破坏项

1. 两个隧道容器与其转发端口。
2. 证书同步链路与 export 目录。
3. 统一入口 nginx 的 listen/server_name/证书路径与三个 location。
4. `lucky-tunnel` 用户与其 authorized_keys。
