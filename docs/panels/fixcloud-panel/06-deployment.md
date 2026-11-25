> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 06 · Docker 部署模板与运维

**结论**：面板以 QNAP NAS Docker 单容器部署，容器名 fixcloud-panel，端口 8787→8080，专用双栈 bridge 网络 fixcloudpanel_fixcloud，**只读根文件系统 + tmpfs /tmp + cap_drop ALL + no-new-privileges + 非 root（PUID:PGID）**。生产实际 WRITE_ENABLED=true、SMB bind 可写（覆盖 compose 默认）。**以下模板全部占位符化，真实值仅存本机 local/，禁止入库。**【已验证：Dockerfile + compose + .env.example + docker inspect】

> ⚠️ 本节所有 IP/域名/路径/凭据均为占位符或文档示例值（example.com / 192.0.2.10 / 198.51.100.20 / 203.0.113.30 / 2001:db8::10）。容器名、env 键名、端口、协议、字段名为结构性事实，保留。

## 1. 构建链（Dockerfile，21 行）

| 阶段 | 基础镜像 | 动作 |
| --- | --- | --- |
| 前端构建 | node:22-alpine | npm ci → npm run build（vue-tsc -b && vite build）→ dist |
| 运行时 | python:3.13-slim | pip install ./backend → COPY dist → 目录 755/文件 644 → mkdir /data |
| 入口 | — | EXPOSE 8080；CMD uvicorn app.main:app --host 0.0.0.0 --port 8080 |

> Dockerfile **无 USER 指令**，运行身份由 compose user 指定（避免镜像内固定 UID）。前端 dist 由后端 StaticFiles 挂载（main.py:97-99）。【已验证】

## 2. docker-compose.yml 模板（占位符化，对应源 66 行）

```yaml
services:
  fixcloud-panel:
    build: .
    container_name: ${CONTAINER_NAME:-fixcloud-panel}
    restart: unless-stopped
    user: "${PUID:-1000}:${PGID:-100}"
    environment:
      APP_ENV: ${APP_ENV:-production}
      APP_DATA_DIR: /data
      STORAGE_BACKEND: ${STORAGE_BACKEND:-smb-mounted}
      STORAGE_ROOT: /mnt/fixcloud
      YAML_PATH: ${YAML_PATH:-/FixCloud.yaml}
      WRITE_ENABLED: ${WRITE_ENABLED:-false}
      PUBLIC_FILE_BASE_URL: ${PUBLIC_FILE_BASE_URL:-https://files.example.com}
      # VPS 用量（11-22 新增，源 .env.example 未列，生产经 NAS .env 注入）：
      # EVOXT_USERNAME / EVOXT_API_PUBLIC / EVOXT_API_PRIVATE / EVOXT_SERVICE_ID / VULTR_API_KEY
    extra_hosts:
      # bridge 只有内部 IPv6、宿主无 NAT66→把公开域名指向 bridge IPv6 网关，由宿主 Lucky(:::443) 本地投递
      - "${PUBLIC_FILE_DOMAIN:-files.example.com}:${PUBLIC_FILE_LAN_IPV6:-2001:db8::10}"
    ports:
      - "${PANEL_BIND_IP:-192.0.2.10}:${PANEL_PORT:-8787}:8080"
    volumes:
      - type: bind
        source: ${SMB_MOUNT_PATH:?}        # <NAS_CONFIG_SHARE_PATH>
        target: /mnt/fixcloud
        read_only: ${YAML_MOUNT_READ_ONLY:-true}
        bind: { create_host_path: false }
      - type: bind
        source: ${APP_DATA_HOST_PATH:?}    # <NAS_APP_DATA_PATH>
        target: /data
        bind: { create_host_path: false }
    read_only: true
    tmpfs:
      - /tmp:size=32m,mode=1777
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
    networks: [fixcloud]

networks:
  fixcloud:
    driver: bridge
    enable_ipv6: true
    ipam:
      config:
        - subnet: ${FIXCLOUD_IPV4_SUBNET:-192.0.2.0/24}
        - subnet: ${FIXCLOUD_IPV6_SUBNET:-2001:db8:1::/64}
```

> 模板与源 docker-compose.yml 结构一致（行号见 02/笔记）；默认值已替换为文档示例。源 compose 的 WRITE_ENABLED 默认 false、YAML_MOUNT_READ_ONLY 默认 true，但 **.env.example 与生产实际为 true/false**（见 §4）。【已验证】

## 3. .env.example 键清单（只列键名与用途，值占位）

| 键 | 用途 | 示例值（占位） |
| --- | --- | --- |
| PANEL_PORT | 宿主映射端口 | 8787 |
| PANEL_BIND_IP | 宿主绑定 IP（限内网） | <NAS_LAN_IP> / 192.0.2.10 |
| CONTAINER_NAME | 容器名 | fixcloud-panel |
| FIXCLOUD_IPV4_SUBNET | bridge IPv4 子网 | <FIXCLOUD_IPV4_SUBNET> / 192.0.2.0/24 |
| FIXCLOUD_IPV6_SUBNET | bridge IPv6 子网 | <FIXCLOUD_IPV6_SUBNET> / 2001:db8:1::/64 |
| APP_ENV | 运行环境（development 才开 /api/docs） | production |
| APP_DATA_DIR | 容器内数据目录 | /data |
| APP_DATA_HOST_PATH | 宿主数据目录（bind） | <NAS_APP_DATA_PATH> |
| PUID / PGID | 运行 UID/GID（NAS 属主） | 1000 / 100 |
| SMB_MOUNT_PATH | 宿主 SMB 配置共享（bind） | <NAS_CONFIG_SHARE_PATH> |
| STORAGE_BACKEND | 主存储后端 | smb-mounted |
| STORAGE_ROOT | 容器内挂载点 | /mnt/fixcloud |
| YAML_PATH | 默认主配置路径 | /FixCloud.yaml |
| YAML_MOUNT_READ_ONLY | SMB bind 只读标志 | false（生产）/ true（compose 默认） |
| WRITE_ENABLED | 保存写开关 | true（生产）/ false（compose 默认） |
| PUBLIC_FILE_BASE_URL | 公开文件服务基址 | https://<PUBLIC_FILE_DOMAIN> |
| PUBLIC_FILE_DOMAIN | 公开文件域名（extra_hosts 键） | <PUBLIC_FILE_DOMAIN> |
| PUBLIC_FILE_LAN_IPV6 | bridge IPv6 网关（extra_hosts 值） | <BRIDGE_GATEWAY_IPV6> |

> **缺口**：EVOXT_USERNAME/EVOXT_API_PUBLIC/EVOXT_API_PRIVATE/EVOXT_SERVICE_ID/VULTR_API_KEY 不在 .env.example/compose，仅生产 NAS .env 注入（docker inspect EnvKeys 证实 5 键全在）。新部署者需自行补充，否则 VPS 用量 available:false。【已验证】

## 4. 生产实际配置（docker inspect 只读核实，2026-11-25）

| 项 | 生产实际值 | 与 compose 默认差异 |
| --- | --- | --- |
| State / StartedAt | running / **2026-11-22**（当前源码已部署） | — |
| User | 1000:100 | 同默认 |
| ReadonlyRootfs | true | 同 |
| Tmpfs | /tmp size=32m mode=1777 | 同 |
| CapDrop / CapAdd | [ALL] / null | 同 |
| SecurityOpt | no-new-privileges:true | 同 |
| Privileged | false | 同 |
| NetworkMode | fixcloudpanel_fixcloud（双栈 bridge，hasGateway+hasIPv6Gateway） | 同 |
| PortBindings | 8080/tcp→HostPort 8787（HostIp 默认 0.0.0.0） | 同 |
| ExtraHostsCount | 1（公开域名→bridge IPv6 网关） | 同 |
| RestartPolicy | unless-stopped | 同 |
| Mount /data | bind <NAS_APP_DATA_PATH>→/data **RW:true** | 同 |
| Mount /mnt/fixcloud | bind <NAS_CONFIG_SHARE_PATH>→/mnt/fixcloud **RW:true** | **覆盖 read_only 默认 true** |
| WRITE_ENABLED | true（API /sources 证实） | **覆盖默认 false** |
| EnvKeys（20） | 含 5 个厂商键 + python slim 基础镜像键（GPG_KEY/LANG/PATH/PIP_*/PYTHON*） | 厂商键非 compose 注入 |

> YAML_MOUNT_READ_ONLY 不是容器 env（compose 期 bind 标志），inspect 以 Mounts RW:true 体现。【已验证】

## 5. 容器约束（只读根文件系统的影响）

| 约束 | 后果 | 应对 |
| --- | --- | --- |
| read_only:true | 不能写系统目录/装软件 | 新能力全在 /data + 纯 Python 依赖（pip 构建期装好） |
| cap_drop ALL + 非 root | 不能绑 <1024 端口、不能改网络 | 容器内 8080，宿主 8787；不改网络模式 |
| tmpfs /tmp 32m | 临时空间有限、重启即失 | 大文件走 /data 或 SMB bind |
| bridge 仅内部 IPv6、无 NAT66 | 容器直连 NAS 自身公网 IPv6 不通 | extra_hosts 公开域名→bridge IPv6 网关，宿主 Lucky 本地投递（见 08） |
| 出网 IPv4 正常 | 可直连 VPS:22、厂商 API | VPS 用量/未来 SSH 集成可行 |

## 6. 重建与回滚步骤（只读审计未执行，以下为模板）

### 6.1 部署前（NAS 部署目录 <NAS_DEPLOY_DIR>）

```bash
# 1 备份当前 compose 与关键目录（生产已有先例：docker-compose.yml.bak-20261117、backup-vps-20261122、backup-usage-layout-20261122）
cp docker-compose.yml docker-compose.yml.bak-<DATE>
# 2 核对 .env（真实凭据，禁入库）与 SMB/data 属主（PUID:PGID 须匹配 FixCloud.yaml 属主）
# 3 本地验证（见 07）：frontend npm ci && npm run build；backend pytest -q
```

### 6.2 重建

```bash
docker compose up -d --build      # README.md:83
# QNAP docker CLI 不在 PATH：经 Container Station 或 /var/run/docker.sock 只读 GET 核实状态
curl -s http://<NAS_LAN_IP>:8787/api/health   # 期望 {status:ok,storage:ready,yaml:valid}
```

### 6.3 部署后核对

- GET /api/health、/api/sources（writeEnabled）、/api/files/catalog（文件哈希/size）。
- 容器健康（healthcheck）、StartedAt、Mounts RW、ExtraHostsCount。
- 权威数据哈希核对：保存前后 GET /config/raw 的 hash 一致（见 07）。

### 6.4 回滚

```bash
cp docker-compose.yml.bak-<DATE> docker-compose.yml
docker compose up -d --build      # 重建上一版镜像
# /data 与 SMB 配置为 bind 持久卷，回滚不丢数据；审计/来源/缓存保留
```

> **禁止**：回滚清空整链防火墙规则、删除 bind 数据、覆盖 .env。回滚按备份文件还原 compose，数据卷不动。【推测：步骤为模板，未实际执行】

## 7. 网络与端口拓扑（占位）

```text
浏览器（Mac Safari / iPhone PWA）
  → http://<NAS_LAN_IP>:8787（宿主绑定，限内网，勿映射公网）
  → 容器 fixcloud-panel :8080（bridge fixcloudpanel_fixcloud 双栈）
  → /mnt/fixcloud（SMB bind <NAS_CONFIG_SHARE_PATH>）读写 YAML
  → /data（bind <NAS_APP_DATA_PATH>）审计/来源/缓存/会话
  → 公开核对：extra_hosts <PUBLIC_FILE_DOMAIN>→<BRIDGE_GATEWAY_IPV6>
      → 宿主 Lucky(:::443) 本地投递公开文件（无 NAT66）
  → 厂商 API（api.evoxt.com / api.vultr.com，出网 IPv4，受 IP 白名单限制）
```
