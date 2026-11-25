# 02 · QNAP NAS 与 Docker 环境

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）
> **这不是参考项目的环境。** 参考项目是 9 台 VPS + 群晖；我方是 QNAP NAS + 东京 Vultr + 香港 VPS + F50/R5C。

## 1. 宿主机事实【我方已验证】

| 项 | 值 |
|---|---|
| 系统 | QTS 5.2.11（20261023） |
| 内存 | 31891 MB |
| 根文件系统 | ramdisk（**不可持久写入**） |
| 数据卷 | `CACHEDEV1_DATA` / `CACHEDEV2_DATA` |
| 容器运行时 | Container Station；docker CLI **不在 PATH**，位于 `/share/CACHEDEV2_DATA/.qpkg/container-station/bin/` |
| docker compose | v2.29.1-qnap2（可用，`config` / `up -d` 实测通过） |
| sudo | **需要密码**（不可用） |
| 替代通道 | `/var/run/docker.sock` HTTP API **只读 GET 可用**（当前用户属 administrators） |
| 容器数 | 14 |

> **运维含义**：任何需要 root 的宿主机操作（ip6tables NAT66、sysctl、systemd）都不可行；能做的只有 Docker 层与用户可写路径。这是选择 `extra_hosts` 而非 NAT66 的决定性原因。

## 2. 容器清单【我方已验证】

| 容器 | 镜像 | 网络 | 端口 | 用途 |
|---|---|---|---|---|
| `lucky` | `gdy666/lucky`（**未钉 tag**） | host | :::443、:::8443、16601(管理) | DNS/Web/证书/端口转发 |
| `fixcloud-panel` | `fixcloudpanel-fixcloud-panel:latest`（188MB） | bridge `fixcloudpanel_fixcloud` | 0.0.0.0:8787→8080 | 配置面板 |
| `lucky-vps-admin-tunnel` | `local/lucky-vps-transport:1` | host | 127.0.0.1:26611（本地转发） | 东京 Lucky 管理隧道 |
| `lucky-hk-admin-tunnel` | 同上 | host | 127.0.0.1:26612 | 香港 Lucky 管理隧道 |
| `lucky-vps-cert-sync` / `lucky-hk-cert-sync` | 同上 | bridge | — | 证书同步 |
| `lucky-vps-admin-web` | `nginx:alpine` | host | `<NAS_LAN_IP>`:24443 ssl | 统一管理入口（/jp /hk /） |
| `lucky-sharks` | `nginx:alpine` | bridge | 127.0.0.1:18080→80 | 内部 Web |
| `embyserver` | — | bridge | 0.0.0.0:8096→8096 等 | 媒体 |
| `moviepilot-v3`、`homeassistant`、`pt-accelerator`、`myservers`、`qbittorrent` | — | — | — | 其他服务 |

## 3. 面板容器网络与约束【我方已验证】

| 项 | 值 |
|---|---|
| IPv4 | 10.0.8.2/24，网关 10.0.8.1（示例段，实际见 local/） |
| IPv6 | `<BRIDGE_IPV6>`::2/64，网关 `<BRIDGE_GATEWAY_IPV6>` |
| 根文件系统 | **read_only** + `/tmp` tmpfs |
| 运行身份 | 必须以 NAS 的 UID/GID 运行，避免 0600 权限污染 |
| 后果 | `docker cp` 进根文件系统**失败**；探测脚本要用 `docker exec -i <容器> python -` 或临时容器 |

## 4. 关键路径【生产配置】

| 路径 | 用途 |
|---|---|
| `/share/Container/FixCloudPanel/` | 面板部署目录（`.env`、`docker-compose.yml`、部署日志） |
| `/share/Container/FixCloudPanel/data/` | `audit.sqlite3`、`sources.json`、`state.json`、`icon-cache/`、`icon-catalog/`、`temporary-sessions/`、`uploads/` |
| `/share/BeamJason/files/config/` | SMB 挂载的配置目录（`FixCloud.yaml`、`oixCloud.yaml`） |
| `/share/homes/BeamJason/.lucky-vps/` | 隧道与证书同步的密钥/脚本目录（**不读取内容**） |
| `/share/Container/goodlucky/.vps-cert-export/` | 证书导出目录 |

## 5. 待改进【待验证】

- `lucky` 镜像未钉 tag → 重建可能拉到不同版本；建议钉版本（需授权）。
- 面板镜像用 `latest` → 回滚困难；建议改钉 digest 或版本 tag。
- 宿主机公网 IPv6 出网本身不通（实测某公网 IPv6 站点超时），但**入站在线**（跨网访问 `<PUBLIC_FILE_DOMAIN>` 0.13s / 200）。
