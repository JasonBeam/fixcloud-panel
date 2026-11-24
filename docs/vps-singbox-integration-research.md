# FixCloud 面板 × VPS / sing-box 自建节点管理 —— 研究报告与实施契约

- 版本：2026-11-24（Asia/Shanghai）
- 交付对象：Codex（实施方）／ Beam（决策方）
- 仓库根：`/Users/beamjason/Documents/BeamNat/fixcloud-panel`（下文相对路径均以此为根；**当前无 .git、无 docs/**）
- 本轮性质：**只研究与设计**。未修改任何运行中的 VPS 服务、未修改 NAS 面板容器、未写入任何生产配置。所有环境结论均来自只读探测（SSH 只读命令、Docker API 只读 GET、HTTP GET）。
- 标注约定：【已验证】= 本次实测或官方文档/源码核实；【推测】= 工程判断；【未验证】= 需后续确认。

---

## 0. 摘要与关键决策

**结论：可行，且不需要改动现有 Lucky / SSH 隧道 / 证书同步，也不需要把面板改成 host 网络。**

| 决策项 | 选择 | 依据 |
|---|---|---|
| 是否引入第三方面板（3x-ui / s-ui / Marzban / hiddify） | **不引入** | 架构冲突（Xray vs sing-box）、GPL/AGPL 传染、资源与维护成本、与现有面板重复 |
| SSH 传输 | **asyncssh 2.24.1（纯 Python）直连 VPS IPv4** | 容器 read_only + cap_drop ALL + 非 root，无法安装 openssh-client；实测容器可直连两台 VPS 22 端口 |
| 是否复用现有 lucky-*-admin-tunnel | **不复用、不修改** | 隧道只绑宿主机 127.0.0.1:26611/26612，bridge 内的面板够不到；改绑定会动到运行中的服务 |
| sing-box 部署形态 | **官方 Docker 镜像 ghcr.io/sagernet/sing-box:v1.14.4 + 独立 bridge + 显式端口发布 + /etc/sing-box bind mount** | 版本钉住可回滚、与 Lucky（host 网络）隔离、端口占用可见 |
| MVP 协议 | **Shadowsocks 2022（2022-blake3-aes-128-gcm，TCP+UDP，专用高位端口）** | 东京 1 vCPU / 955MB、JP UDP 缓冲仅 208KB、ufw 默认 deny、Lucky 占 TCP 443、Stash 版本未验证 |
| 第二阶段协议 | VLESS + Reality（TCP，非 443 端口） | 抗封锁最强、不需自有证书；TCP 443 已被 Lucky 占用 |
| 第三阶段协议 | Hysteria2（UDP 443，两台均空闲） | 需先抬 sysctl 缓冲 + 放行 UDP + 实测移动网络 QoS；QUIC 用户态在 1 vCPU 上易成瓶颈 |
| 节点地址 | **直连 VPS IPv4，或新建仅 A 记录的专用子域** | jpedge/hkedge 的 AAAA 指向家庭 NAS，**禁止**用于定位 VPS 代理 |
| 订阅输出 | **面板自建 Clash YAML 端点 + subscription-userinfo 头**；sing-box JSON profile 可选；**不做 base64 订阅** | sing-box 官方无订阅输出；Verge 源码拒收 base64 |
| 配置校验 | **sing-box check 官方命令前置**，不复用 Clash 语义校验链 | yaml_service 的 KNOWN_TOP_LEVEL 与引用检查全是 Clash/Mihomo 语义 |

### 0.1 必须先处理的两个既有问题（不属于本次升级，但会直接影响它）

1. **【已验证】服务商 API 被 IP 白名单挡住**：面板现有「VPS 流量」卡片两台都不可用。
   - Vultr：`GET /v2/account/bandwidth` → `401 {"error":"Unauthorized IP address: <NAS_EGRESS_IPV4>"}`
   - Evoxt：`GET /listserver` → HTTP 200，但 body 仅 `{"IP Address": …, "error":"IP Address Unauthorized"}`
   - 网络本身正常（容器到两家 API 的 TCP 443 分别 0.02s / 0.01s）。**修复动作在服务商控制台（把 NAS 当前出口 IPv4 <NAS_EGRESS_IPV4> 加入 API 白名单），属账号侧操作，须由 Beam 本人执行。**
2. **【已验证】当前 FixCloud.yaml 已被公开可读，且其中含凭据**：
   - `https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml` 无鉴权返回 200、20893 字节，与 NAS 本地文件一致。
   - 结构探测（不回显任何值）：`proxies` 1 条 = `localhost / socks5 / <HOME_DOMAIN>:7891`，**含 username 与 password 字段**；`proxy-providers` 3 条（Kycloud → <SUB_PROVIDER_1_DOMAIN> 带 query token、Youtu → <SUB_PROVIDER_2_DOMAIN>、DlerCloud → <SUB_PROVIDER_3_DOMAIN> 带 query token）；顶层含 `external-controller` 与 `secret`；rules 66、proxy-groups 33。
   - **设计硬约束：自建节点的密码 / UUID / Reality 私钥 / 订阅 token 绝不能进入这个会被公开下载的文件。** 见 §3.6 的三个处置选项（需 Beam 决策）。

---

## 1. 当前项目与 sing-box 集成的可行性

### 1.1 现有架构锚点（只读源码核实）

后端 `backend/app`（约 3000 行，FastAPI + 文件型状态，无 ORM）：

| 模块 | 关键事实 | 对集成的意义 |
|---|---|---|
| `main.py:27-99` | lifespan 启动 cleanup_loop；docs 仅 development；CORS 仅 localhost:5173；`security_headers` 中间件读 cookie `fixcloud_session` 绑定 contextvar（scope + 临时目录），注入 CSP/nosniff、`/api/*` no-store；挂载前端 dist | 新路由自动继承安全头与会话隔离 |
| `core/settings.py:15-35` | pydantic-settings，`env_file=".env"`、`extra="ignore"`；字段 app_env / app_data_dir=/data / storage_backend=smb-mounted / storage_root=/mnt/fixcloud / yaml_path=/FixCloud.yaml / write_enabled=False / webdav_*（password repr=False）/ public_file_base_url / frontend_dist；`@lru_cache get_settings()` | **无任何 SSH/VPS 字段**，需新增 |
| `api/routes.py`（1193 行，prefix `/api`:35） | 所有写路由 `Depends(require_internal_request)`（:107-109，要求头 `X-FixCloud-Request: 1`，否则 403） | 新增写/部署路由必须继承同一门禁 |
| `services/storage/base.py:1-44` | `StorageBackend` Protocol：source_type/display_name + async status()/list_dir()/stat()/read_bytes()/write_bytes(overwrite=False)/copy()/move()/delete()；`StorageStat(path,size,modified_at,etag,is_directory)` | **纯文件语义，无 exec/channel**。SFTP 实现可复用保存/历史/审计全链路；远程命令执行必须另建 service |
| `services/storage/registry.py:14-103` | build_primary_storage 按 backend 分派；build_storage_from_source 按 source.type 分派 smb-mounted/upload/smb/webdav；未知类型 `raise ValueError(f"不支持的存储后端：{source.type}")` | 新增 `ssh` 类型是自然扩展点（可选） |
| `services/source_store.py` | `SourceRecord(id,type,name,config,built_in)`；`SENSITIVE_FIELDS={"username","password"}`（:16）经 safe_data() 剔除；`SUPPORTED_SOURCE_TYPES`（:17）；持久化 /data/sources.json，`_write`（:153-178）O_EXCL 0o600 + fsync + os.replace；**凭据明文 JSON，无加密**；`ProbeStore`（:274-316）fingerprint=sha256(config)、TTL 600s 一次性 consume，保存前必须探测成功否则 409 | VPS 主机凭据沿用同一范式（0600 + 不回传 + probe 门禁） |
| `services/save_service.py` | create_preview（:94-126）重读 sha256 防冲突 → load → apply_operations → dump → validate_references → full_diff → PreviewStore（TTL 900s、绑 session_scope）；commit（:206-322）哈希复核 → 写隐藏 `.rollback-<hex8>` → 回读解析 → 写 `.tmp-` → 回读哈希 → move(overwrite=True) → 回读正式；失败区分 unchanged / restored / recovery_failed；成功删 rollback，**不再生成永久备份**（backupPath:None） | 这是本项目已验证的 11 步安全保存范式，**远程 sing-box 配置写入必须复刻同一状态机** |
| `services/audit.py` | SQLite `audit_log(id,created_at,username,action,path,before_hash,after_hash,backup_path,details,source_id,session_scope)`；record_event(...)（:94-102，username="内网访问"）；list_recent 按 session_scope 过滤 | 部署/回滚/节点变更全部走同一审计表，新增 action 值即可 |
| `services/yaml_service.py` | ruamel typ="rt"、preserve_quotes、width 4096；apply_operations 支持 set/delete/insert/move；validate_references（:170-237）重名/缺 provider/RULE-SET=error；**KNOWN_TOP_LEVEL（:11-30）与校验全是 Clash/Mihomo 语义** | **sing-box JSON 不能走这条校验链**，需独立 schema + 官方 check |
| `services/vps_usage.py:10-54` | 已存在！async get_vps_usage(transport=None)，httpx timeout=12，asyncio.gather(_evoxt,_vultr)；env 读 EVOXT_USERNAME/API_PUBLIC/API_PRIVATE/SERVICE_ID 与 VULTR_API_KEY；未配置/出错 → available:False，不显示假零，不回传凭据 | 唯一的现有 VPS 痕迹（只读账单流量）；测试范式 httpx.MockTransport 可直接沿用 |
| `services/subscription_usage.py` / `subscription_nodes.py` | 取 proxy-providers type=http 前 20；UA="clash.meta"、Timeout(12,connect 6)；先 HEAD 取 subscription-userinfo 再 stream GET；模块缓存 TTL 300s；节点解析支持 YAML proxies 或 base64/URI 逐行，≤500 节点/provider、≤8MiB | **只读拉取，无输出端点**。缓存/超时/中文错误/脱敏范式可复用到自建订阅输出 |
| `services/publication.py` | 公开文件核对（目录 + 流式 GET + sha256） | 与自建节点无直接关系，但见 §0.1 的公开暴露问题 |

前端 `frontend/src`（约 5000 行，Vue 3 + TS + Pinia + vue-router hash + Tailwind 4）：

- `stores/app.ts`：request()（:262-275）非 GET 自动加 `X-FixCloud-Request: 1`、credentials same-origin、!ok → ApiRequestError(detail,status)、normalizeApiDetail 转中文；notify 2600ms；persistDraft（:337-354）**rawYamlDraft 含凭据绝不写浏览器**，operations 草稿存 sessionStorage `fixcloud-session-draft`，选择存 `fixcloud-session-selection`，每标签页独立。
- `router/index.ts`：/sources /files /editor /editor/advanced-yaml /editor/:section(/item/:itemId) /usage /subscription-nodes /history /settings /more；`main.ts:19-38` beforeEach 草稿守卫。
- `components/AppShell.vue:35-53`：桌面 6 项（来源/编辑/流量/节点/历史/设置），移动 4 tab（编辑/来源/流量/更多）；节点/历史/设置经 `MoreView.vue` 进入 → **新页面挂 desktop navItems + MoreView 即可**。
- 守卫：`composables/draftGuard.ts` requestDraftTransition(action,destination,mode)（:28-44）；`referenceGuard.ts` requestReferenceDelete(impact)（:14-21）→ cancel/keep/remove/replace。
- **设计 token 现状（重要）**：`style.css` 是 iOS 风基础层（--app-bg #f2f2f7、ios-card radius 20、primary-button #0a84ff、settings-row min 58、form-field input min 48/radius 14、page-width max 1120）；**`visual-refresh.css` 是当前生效的覆盖层（Nothing 风）**：--nd-accent #d71921、--nd-inverse #111、Space Grotesk / Space Mono、shadow:none、卡片统一 radius 15 + 1px 边框、primary-button 黑底白字、soft-button 胶囊 radius 999、settings-row min 70、桌面侧栏 244px、移动 safe-area + 输入 16px、prefers-reduced-motion。
  → **新模块必须复用当前生效的 visual-refresh 视觉语言与既有类名/组件，不得回退到 iOS 基础层，也不得另写一套 CSS。**
- `utils/editorSchemas.ts`：proxyTypes = [ss, vmess, vless, trojan, socks5, hysteria, hysteria2, tuic]（:21）——**已有协议枚举但无 sing-box schema**。
- 测试：backend pytest（pythonpath=["."]、testpaths=["tests"]、asyncio_mode="auto"，13 个文件）；约定 tmp_path + `Settings(storage_backend="local")` + `app.dependency_overrides[get_settings]`（test_api.py:36-45）、httpx.MockTransport 注入（test_vps_usage.py:19）、存储子类故障注入验证 unchanged/restored/recovery_failed（test_save_service.py:96-114）。前端 vitest ^3.2.4，6 个 .test.ts。

### 1.2 运行环境实测（决定可行性的硬事实）

**面板容器（NAS，fixcloud-panel）**【已验证】
- compose：user 1000:100、**read_only: true**、tmpfs /tmp 32m、no-new-privileges:true、**cap_drop: ALL**、ports 8787:8080、/data 卷、SMB bind 默认 read_only、bridge 双栈 10.0.8.0/24 + <BRIDGE_GATEWAY_IPV6>::/64、extra_hosts 把公开域名解析到 LAN IPv6。
- 推论：**容器内不能安装软件、不能写系统目录、不能绑 <1024 端口**；SSH 客户端必须是纯 Python 库；known_hosts / 密钥只能放 /data（持久）或 /tmp（32m tmpfs）。
- 出网：IPv4 正常；IPv6 到公网正常（ipv6.baidu.com 200 / 0.16s），但**到 NAS 自身公网 IPv6 不通**（无 NAT66，已用 extra_hosts 修复核对功能）。
- **直连 VPS SSH 实测**：`<VPS_JP_IP>:22 OK 0.41s（SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.2）`、`<VPS_HK_IP>:22 OK 0.18s（SSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3）`；两台 :443 亦可达。
  → **面板后端可以直接 SSH 到 VPS，无需 host 网络、无需改动现有隧道。**

**两台 VPS**【已验证，SSH 只读】
| 项 | 东京（别名 vps，<VPS_JP_DOMAIN>） | 香港（别名 hk） |
|---|---|---|
| IP | <VPS_JP_IP> | <VPS_HK_IP> |
| OS / kernel | Ubuntu 24.04.5 / 6.8.0-149 | Ubuntu 26.04 / 7.0.0-14 |
| CPU / 内存 | 1 vCPU / 955MB（可用 538） | 1 vCPU / 1961MB（可用 1369） |
| 磁盘 / | 23G 用 6.4G（30%） | 20G 用 1.8G（10%） |
| SSH 用户 | **root，sudo 免密** | **root，sudo 免密** |
| 已装容器 | 仅 lucky（gdy666/lucky:v3_lucky_docker，host 网络） | 仅 lucky（同镜像，host 网络） |
| 监听 TCP | 443（lucky）、16601（lucky）、22（sshd）、127.0.0.1:39841（containerd）、53（resolved） | 443、16601、22、127.0.0.1:34531（containerd） |
| 监听 UDP | 52889（lucky）、68、53 | 55234（lucky）、323（chrony） |
| 防火墙 | **ufw active，default deny incoming / allow outgoing / deny routed**；放行仅 22/tcp、80/tcp、443/tcp（v4+v6） | 同左 |
| net.core.rmem_max / wmem_max | **212992 / 212992（208KB）** | 4194304 / 4194304（4MB） |
| sing-box | **未安装**（command -v 无、/etc/sing-box 不存在） | **未安装** |

**NAS**【已验证】
- QNAP QTS 5.2.11（20261023），内存 31891MB；root 为 ramdisk，数据在 CACHEDEV1/2_DATA；docker CLI 不在 PATH、sudo 需密码；**经 /var/run/docker.sock 只读 GET 可用**（BeamJason 属 administrators）；14 个容器。
- config 目录：FixCloud.yaml 20893B（BeamJason，11-19）、oixCloud.yaml 24012B（admin，07-28）。
- **既有 NAS↔VPS 设施（只读 inspect，未读密钥内容）**：
  - `lucky-vps-admin-tunnel`：local/lucky-vps-transport:1，**host 网络**，`ssh -4 -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/ssh/known_hosts -o IdentitiesOnly=yes -i /run/key/id -L 127.0.0.1:26611:127.0.0.1:16601 lucky-tunnel@<VPS_JP_IP>`；挂载 /share/homes/BeamJason/.lucky-vps/tunnel → /ssh。
  - `lucky-hk-admin-tunnel`：同上，`-L 127.0.0.1:26612:127.0.0.1:16601 lucky-tunnel@<VPS_HK_IP>`。
  - `lucky-vps-cert-sync` / `lucky-hk-cert-sync`：bridge，`/bin/sh /ssh/sync.sh`，把 /share/Container/goodlucky/.vps-cert-export 的证书同步到 VPS。
  - `lucky-vps-admin-web`：nginx:alpine，host 网络，`listen <NAS_LAN_IP>:24443 ssl`、`server_name <LUCKY_LAN_DOMAIN>`；`/jp/` → 127.0.0.1:26611、`/hk/` → 26612、`/` → NAS Lucky 16601。
  - 专用 SSH 用户 `lucky-tunnel`（两台 VPS），密钥目录 /share/homes/BeamJason/.lucky-vps/{tunnel,hk-tunnel,cert,hk-cert}。
- **推论**：隧道只绑宿主机 loopback，bridge 内的面板容器够不到 → 不复用；面板自建 SSH 直连是零侵入路径。既有隧道/证书同步/admin nginx **一律不动**。

### 1.3 可行性判定

| 能力 | 判定 | 说明 |
|---|---|---|
| SSH 多 VPS 管理 | **可行** | asyncssh 纯 Python，容器可直连 22；凭据沿用 sources.json 0600 范式 |
| sing-box 自动部署 / 版本管理 | **可行** | 官方镜像钉 tag；部署=写配置 + check + docker compose up -d；回滚=改 tag 重建 |
| SS2022 / Hysteria2 / VLESS | **可行（分阶段）** | 官方 inbound 字段已核实；环境约束决定顺序，见 §3.3 |
| 自动生成 Clash / sing-box 订阅 | **可行，需自建** | 官方无订阅输出；渲染器 + subscription-userinfo 头 |
| 健康检查 / 延迟 / 流量 | **部分可行** | 延迟走 mihomo REST（路由器/客户端侧）；sing-box clash_api 提供连接级流量；**按用户精确计费在官方镜像下不可用**（v2ray_api 未编入），见 §3.5 |
| VPS IP 变化后更新 | **可行** | 主机记录存 IP + 可选专用 A 记录；变更走同一 preview/Diff/审计流 |
| 配置备份 / 校验 / 更新 / 回滚 | **可行** | 复刻 save_service 状态机 + 官方 check + 钉 tag |
| 与回家节点统一管理 | **可行（只读纳管）** | 现有 socks5 节点纳入同一节点目录视图，**不修改其配置** |
| 未来更多 VPS | **可行** | 主机记录为数据驱动，无硬编码台数 |

---

## 2. 可复用的 GitHub 项目与组件

### 2.1 推荐复用（引入或调用）

| 项目 / 组件 | 版本 / 许可 | 用途 | 集成代价 | 判定 |
|---|---|---|---|---|
| **asyncssh** | 2.24.1，EPL-2.0，py≥3.10 | SSH 命令执行 + SFTP + 多会话复用 + TCP/SOCKS 转发 + known_hosts 校验 | 新增一个纯 Python 依赖（含 cryptography wheel） | **首选**【已验证 PyPI】 |
| **sing-box 官方镜像** | ghcr.io/sagernet/sing-box:**v1.14.4**（stable，2026-10-24）；tag 另有 latest/latest-beta/latest-testing | VPS 侧运行时 | 0（docker pull） | **采用**，钉 v1.14.4【已验证 registry API + releases.atom】 |
| **sing-box 官方 CLI** | check / format / run / version / generate uuid\|rand\|reality-keypair / merge / api | 配置校验、密钥生成、格式化 | 0 | **必须用 check 做下发前置校验**【已验证 v1.14.4 源码 cmd/sing-box】 |
| **sing-box 官方 systemd unit** | release/config/sing-box.service：User=sing-box、ExecStart=`/usr/bin/sing-box -D /var/lib/sing-box -C /etc/sing-box run`、**ExecReload=/bin/kill -HUP $MAINPID**、Restart=on-failure、RestartSec=10s、LimitNOFILE=infinity | 备选部署形态（非 Docker） | 低 | 备选【已验证】 |
| **sing-box clash_api** | experimental.clash_api：external_controller / secret / external_ui | 连接级流量、延迟、日志、selector 切换 | 配置字段 | **采用**（绑 127.0.0.1）【已验证文档 + 源码路由】 |
| **sing-box 1.14 service/api + ssm-api** | gRPC 观测/控制；SS managed 用户动态增删 + cache_path 停机保存流量/用户状态 | 进阶统计与用户管理 | 中 | P3 评估【已验证】 |
| **sing-box-dashboard** | 139★，GPL-3.0 | 官方监控远控 UI（非订阅） | 可选嵌入/外链 | 可选，注意 GPL【已验证】 |
| **mihomo REST API** | v1.19.34（2026-11-11），MIT | 健康检查 / 延迟 / 流量：`GET /proxies/{name}/delay?url=&timeout=5000` → {"delay":ms}；/connections、/traffic(WS)、/providers/proxies/{p}/healthcheck；Bearer secret | 只读调用路由器/客户端控制器 | **采用**【已验证 wiki + 源码】 |
| **Lucky OpenToken** | gdy666/lucky 8.4★ MIT，v3.5.0（2026-02-15） | 第三方调接口自动加端口转发 | 中；**无官方 OpenAPI**，社区抓包 `PUT /api/portforward` + openToken【未验证】 | P4 可选；DNS/证书/回家仍归 Lucky【文档已验证，接口未验证】 |
| **docker-py** | 7.2.0，Apache-2.0，支持 ssh:// 传输（paramiko + use_ssh_client） | 免开 2375 管远程 Docker | 会引入 paramiko | **不采用**：直接用 asyncssh 执行 docker CLI 更轻、依赖更少【已验证能力】 |
| **官方 install.sh** | `curl -fsSL https://sing-box.app/install.sh \| sh`（--version/--beta） | 非 Docker 形态安装 | 低 | 备选；**233boy 脚本非官方**【已验证】 |

### 2.2 仅参考（不引入代码）

- **233boy/sing-box**（5.7k★ GPL-3.0，v1.20）：add/change/del/info 参数化思路可参考；交互菜单、无回滚，非官方。
- **Toperlock/sing-box-subscribe**（2.6k★ Python，2026-09 维护）：订阅→JSON 的模板思路可参考；**无 LICENSE**，不可直接复制代码。
- **tindy2013/subconverter**（17k★ GPL-3.0，v0.9.0 / 2023-10，2026-07 仅构建）：`:25500/sub?target=clash&url=&config=`；目标无 sing-box；GPL + 额外常驻服务 + 维护停滞 → **不引入**，自写渲染器更可控。
- **XTLS/REALITY**、**Shadowsocks-NET/shadowsocks-specs**、**apernet/hysteria**：协议规范与性能建议来源。

### 2.3 明确不引入（含理由）

| 项目 | 数据 | 不引入理由 |
|---|---|---|
| 3x-ui | 51k★ GPL-3.0 v3.10.2 | **仅 Xray-core**，与 sing-box 目标不符；GPL |
| Marzban | 7.5k★ AGPL-3.0 | Xray；**2025-01-09 后停滞**；AGPL |
| hiddify-manager | 9.7k★ GPL-3.0 v14.5.0b2 | 多用户重面板，资源与维护成本远超需求 |
| s-ui / 2s-ui | 10k★ / 303★，GPL-3.0，v1.6.8 / v2.1.0 | sing-box 系但独立部署即重复造面板；GPL 传染 |
| Sub-Store | 11k★ AGPL-3.0 2.44.29 | Node 运行时过重；AGPL |
| singbox_ui 等桌面端 | — | 与 Web 面板形态冲突 |

> 版本口径说明：reuse 调研曾报 sing-box stable 1.14.3、mihomo v1.19.33；本报告以 releases.atom + registry API 直接核实的 **sing-box v1.14.4（2026-10-24）**、**mihomo v1.19.34（2026-11-11）** 为准。

---

## 3. 推荐技术架构

### 3.1 分层

```
前端（Vue3 + Pinia，复用现有视觉语言与组件）
  VpsOverviewView → VpsHostListView → VpsHostDetailView(概览/节点/配置/部署历史) → NodeDetailView
        │  stores/vps.ts（request/notify/draftGuard 复用）
        ▼
FastAPI 新路由（继承 require_internal_request + session_scope + 安全头）
  /api/vps/hosts            CRUD + probe（探测门禁）
  /api/vps/hosts/{id}/preflight   端口/防火墙/资源/版本只读预检
  /api/vps/hosts/{id}/deploy      preview → commit（复刻 save_service 状态机）
  /api/vps/hosts/{id}/rollback
  /api/vps/nodes            自建节点目录（含回家节点只读纳管）
  /api/vps/subscription     Clash YAML 输出（token 鉴权）+ subscription-userinfo
  /api/vps/health           延迟/可用性（经 mihomo REST 或 TCP 探测）
        ▼
新增 services/vps/*
  hosts.py      主机记录 + 凭据（0600，safe_data 脱敏，probe 门禁）
  ssh.py        asyncssh 连接池 / 命令执行 / SFTP / known_hosts
  singbox.py    JSON schema 渲染 + 官方 check + format + generate
  deploy.py     部署事务（备份→写临时→check→替换→回读→失败三态）
  nodes.py      节点目录（自建 + 回家只读）
  subscription.py  Clash YAML / sing-box JSON 渲染 + userinfo 头
  health.py     探测与缓存（TTL、force、中文错误）
        ▼
VPS（Docker：ghcr.io/sagernet/sing-box:v1.14.4）
  /etc/sing-box/config.json（bind mount）  /var/lib/sing-box（数据）
  clash_api 绑 127.0.0.1（经 SSH 隧道读取，不对公网开放）
```

### 3.2 部署形态决策

**推荐：官方 Docker 镜像 + 独立 bridge + 显式端口发布 + 配置目录 bind mount。**

理由：
- 版本钉 tag（v1.14.4）→ 回滚 = 改 tag 重建，语义清晰；
- 与 Lucky（host 网络，占 TCP 443/16601）**网络隔离**，端口占用在 compose 里显式可见，满足"自动检测端口占用"；
- 配置/数据目录 bind mount → 备份与回滚是文件级操作，可复刻 save_service 状态机；
- 官方 compose 约定：`command: -D /var/lib/sing-box -C /etc/sing-box/ run`，`restart: always`【已验证官方 Docker 安装页】。

备选：systemd + 官方 install.sh（开销更低、ExecReload=HUP 原生），但版本钉住与回滚需自行实现，且会在宿主机装包（改动面更大）。**MVP 不选。**

**热重载注意**【已验证 v1.14.4 cmd_run.go】：SIGHUP 会先 check，失败则保持旧配置运行；成功则**关闭旧实例重建 → 存量连接会断**。无 reload 子命令；Clash API 的 `PUT /configs` 是空操作，不能经 API 重载。
→ 面板必须把"重载会断连"写进确认文案；Docker 形态下用 `docker compose up -d`（重建）或 `docker kill -s HUP`，并在部署历史里记录连接中断风险。

### 3.3 协议决策矩阵（环境驱动，不照单全收）

| 维度 | SS2022 | VLESS+Reality | Hysteria2 |
|---|---|---|---|
| 传输 | TCP + UDP | TCP（Vision） | **QUIC / UDP** |
| CPU / 内存（1 vCPU 东京） | 最低（内核 TCP + AEAD） | 低（多一次借握手 TLS） | **高**（用户态 QUIC） |
| 是否需自有证书 | 否 | **否**（借目标站证书） | **是**（tls 必填） |
| 与 Lucky TCP 443 冲突 | 不冲突（用高位端口） | **冲突**（需换 TCP 端口） | 不冲突（**UDP 443 两台均空闲**） |
| 系统前置改动 | 无 | 无 | **需抬 net.core.rmem_max/wmem_max 到 16MB**（JP 现仅 208KB） |
| 防火墙改动 | ufw 放行 1 TCP + 1 UDP | ufw 放行 1 TCP | ufw 放行 1 UDP |
| 客户端覆盖 | 全（Stash 无 2022-chacha20） | 全，但 **Stash 需 iOS 3.4.0+**（用户版本未验证） | 全，但 **Stash 字段不同**（auth / up-speed / down-speed） |
| 抗封锁 | 流量与随机字节不可区分、完整重放保护；**无伪装** | **最强**（借真实 TLS1.3+H2 握手，消除服务端 TLS 指纹） | 伪装 HTTP/3，但**有公开针对性阻断报告**（hysteria #1267/#1220/#1408/#1380），大陆移动 UDP QoS 风险高 |
| 运维复杂度 | 最低（一个 base64 PSK） | 中（keypair + short_id + 握手目标） | 高（证书 + sysctl + QoS 调优） |

**决策：MVP = SS2022；P2 = VLESS+Reality；P3 = Hysteria2（有条件）。**

MVP 选 SS2022 的理由（与"Reality 优先"的通用建议不同，依据是本环境实测）：
1. 东京 1 vCPU / 955MB，SS2022 资源占用最低，最不容易把 Lucky 挤垮；
2. JP `net.core.rmem_max=212992`（208KB）远低于 Hysteria 官方建议的 16MB，hy2 在 JP 先天受限；
3. ufw 默认 deny 且只放行 22/80/443 tcp，任何新端口都要加规则——SS2022 只需一条 TCP+UDP，改动面最小；
4. Stash 版本未验证，SS2022 对所有版本通用，Reality 需 iOS 3.4.0+；
5. MVP 的目标是**打通 SSH→部署→check→节点→订阅→客户端 的完整闭环**，协议升级之后只是同一管线里的配置变更。

> **决策杠杆（留给 Beam）**：若优先级是"抗封锁"而非"最低运维成本"，可把 P1/P2 对调（Reality 先行）。两者都不需要证书、都不触碰 Lucky 证书体系；差别只在客户端版本门槛与握手目标选择。

**端口方案（示例，实施前必须预检确认空闲）**
| 用途 | 端口 | 现状 |
|---|---|---|
| SS2022 | TCP+UDP 18388 | 两台均空闲【已验证 ss -tulpn】 |
| VLESS+Reality | TCP 18443 | 两台均空闲；**不要用 TCP 443（Lucky 占用）** |
| Hysteria2 | **UDP 443** | 两台均空闲，可与 Lucky TCP 443 同号共存 |
| clash_api | 127.0.0.1:19090（仅 loopback） | 经 SSH 隧道读取，不对公网开放 |
| 避开 | Lucky TCP 443/16601、UDP 52889(JP)/55234(HK)、sshd 22、resolved 53、chrony 323 | 一律不动 |

**Reality 握手目标**：须在 GFW 之外、支持 TLS1.3+H2、非重定向域名，官方推荐 `dl.google.com`【已验证 XTLS/REALITY README】。

### 3.4 节点地址与 DNS

- **禁止**用 jpedge / hkedge 定位 VPS 代理节点（其 AAAA 指向家庭 NAS）【用户硬约束 + 环境考古确认】。
- 推荐：节点 server 直接填 VPS IPv4（<VPS_JP_IP> / <VPS_HK_IP>），或新建**仅 A 记录**的专用子域（如 jpnode / <VPS_NODE_DOMAIN>），由 Lucky DNS 管理。
- SSH 目标同样用 IPv4 或 `-4`，避免走到家庭 NAS。
- **IP 变化处理**：主机记录保存 `address` + `addressMode: ip|domain`；变更 IP 走 preview/Diff/审计，并联动更新已生成节点与订阅（订阅是渲染产物，自动跟随）。

### 3.5 订阅输出与统计

**订阅（面板自建，官方无此能力）**【已验证】
- Clash YAML：含 `proxies` / `proxy-groups`（Verge 源码只校验 HTTP 200 + YAML 正文含 proxies/proxy-providers 键，不检查 Content-Type、不解码 base64）；建议返回 `application/yaml`。
- 响应头 `subscription-userinfo: upload=<bytes>; download=<bytes>; total=<bytes>; expire=<unix秒>`（0=长期）。OpenClash lua、Verge（兼容 x-amz-meta- 前缀）、Stash 官方均解析此头。
- 更新节奏：Stash 默认 12h 且优先 HEAD；Verge 按 profile update_interval（分钟）+ allow_auto_update → **端点必须支持 HEAD**。
- sing-box 客户端：另供 JSON remote profile（官方客户端只吃 sing-box JSON，默认 60min 自动更新，导入 scheme `sing-box://import-remote-profile?url=…#name`）。
- **不做 base64 订阅**（Verge 拒收，三类目标客户端无必要）。
- 鉴权：URL 携带高熵 token（后端保存、可轮换），**token 与节点凭据不得进入公开文件**（见 §3.6）。

**字段映射（Clash YAML → sing-box JSON）**【已验证官方文档】
`cipher→method`；`up/down→up_mbps/down_mbps`（纯数值，留空=用 BBR 而非 Brutal）；`obfs-password→obfs:{type:"salamander",password}`；`servername→tls.server_name`；`skip-cert-verify→tls.insecure`；`client-fingerprint→tls.utls:{enabled:true,fingerprint:"chrome"}`；`reality-opts→tls.reality:{enabled:true,public_key,short_id}`；`ports→server_ports`（≥1.11）、`hop-interval→hop_interval`。
**Stash 差异**：hy2 用 `auth`（非 password）、`up-speed/down-speed`（Mbps 数值）；mihomo 专有 `bbr-profile / realm-opts / name-cert-verify / fingerprint / udp-over-tcp-version` Stash 不认；Stash 默认 `block-quic` 拦截经代理的 QUIC（可按代理关闭）→ **若输出 Stash 订阅必须做字段转换**。
**SS2022 密钥**：定长 PSK 的 base64，`sing-box generate rand --base64 16`（aes-128）/ `32`（aes-256），**禁止从口令派生**【已验证规范 §2.1】。

**统计能力边界（重要）**【已验证】
- 官方镜像下可用：clash_api `GET /connections`（downloadTotal/uploadTotal + 每连接流量）、`GET /traffic`、`GET /proxies/{name}/delay`、`GET /logs`(WS)。
- **`experimental.v2ray_api` 的按用户计数（`user>>>name>>>traffic>>>uplink/downlink`）在官方 Docker/deb 默认构建中不可用**（DEFAULT_BUILD_TAGS 无 with_v2ray_api），需自编译。
- 替代：SS `managed:true` + `ssm-api`（cache_path 停机保存流量/用户状态），或 1.14 `service/api`。
- **MVP 不做按用户精确计费**；先做"节点可用性 + 延迟 + 连接级总量"，并诚实标注口径。
- 服务商账单流量（现有 vps_usage.py）与节点流量是**两个不同口径**，UI 必须分开标注，不可混算。

### 3.6 公开暴露问题：三个处置选项（需 Beam 决策）

现状【已验证】：`https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml` 无鉴权可读，含回家 socks5 的 username/password、3 个订阅 URL（2 个带 token）、external-controller secret。

| 选项 | 做法 | 影响 | 建议 |
|---|---|---|---|
| A（推荐） | **自建节点与凭据完全不进入 FixCloud.yaml**；节点只存在于面板后端 + 私有订阅端点；FixCloud.yaml 里如需引用，用 proxy-provider 指向**仅内网/回家隧道可达**的订阅 URL | 不动现有发布流；公开文件仍含既有凭据（既有问题另行处理） | MVP 采用 |
| B | 发布产物改为**脱敏版**（凭据替换为占位），完整版仅内网 | 需改发布流程，可能影响现有核对/订阅消费方 | 需先确认谁在消费公开文件 |
| C | 给公开文件加鉴权（Lucky 侧）或停止公开发布 | 触碰 Lucky 配置，违反"不影响现有网站"约束除非明确授权 | 需 Beam 明确授权 |

**无论选哪个，自建节点的密码/UUID/Reality 私钥/订阅 token 都不得写入会被公开下载的文件。** 这是本次设计的硬红线。

### 3.7 安全设计

- 所有 inbound 认证字段必填（SS password、hy2 users+tls、VLESS uuid）→ **不存在无认证开放代理**【已验证官方文档】。
- clash_api 只绑 127.0.0.1；若将来公网监听必须设 secret【已验证】。
- 凭据只留后端：沿用 sources.json 0600 + safe_data 剔除 + API 永不回传 + 不进浏览器存储 + 不进审计 details。
- SSH：known_hosts 严格校验（`StrictHostKeyChecking=yes` 语义），首次连接显式展示指纹让用户确认；私钥文件 0600 放 /data；**不读取、不复制现有 lucky-tunnel 私钥**。
- 写操作继承 `require_internal_request`（X-FixCloud-Request: 1）+ write_enabled 门禁 + probe 门禁。
- 远程命令白名单化：只允许预定义命令模板（docker / sing-box check / ss / ufw status / cat 指定路径），**禁止把用户输入拼进 shell**；参数用 shlex.quote 或 asyncssh 参数数组。
- 部署事务复刻 save_service 三态：unchanged / restored / recovery_failed，且"已恢复"必须回读证明文件未变。

---

## 4. 需要新增或修改的源码模块

### 4.1 后端新增

| 路径 | 职责 | 关键接口（建议签名） |
|---|---|---|
| `backend/app/services/vps/__init__.py` | 包 | — |
| `backend/app/services/vps/hosts.py` | VPS 主机记录 + 凭据 + probe 门禁 | `@dataclass VpsHostRecord(id,name,address,address_mode,ssh_user,ssh_port,credential_ref,built_in=False)`；`safe_data()` 剔除 ssh 私钥/密码；`create/update/delete/list`；`HostProbeStore`（fingerprint=sha256(config)、TTL 600s、一次性 consume） |
| `backend/app/services/vps/ssh.py` | asyncssh 连接与命令执行 | `async open_host(host) -> SSHClientConnection`；`async run(host, argv: list[str], *, timeout=20) -> CommandResult(stdout,stderr,exit_status)`；`async read_file(host,path)->bytes`；`async write_file_atomic(host,path,data,*,mode=0o600)`；known_hosts 存 /data/vps/known_hosts |
| `backend/app/services/vps/singbox.py` | 配置渲染 + 官方校验 | `render_config(host, nodes, *, version) -> dict`；`async check_remote(host, config_bytes) -> CheckResult`（执行 `sing-box check -C /etc/sing-box`）；`generate_ss_key(bits=128)->str`、`generate_reality_keypair()->tuple`、`generate_uuid()->str` |
| `backend/app/services/vps/deploy.py` | 部署事务（复刻 save_service） | `async create_deploy_preview(host,*,base_hash,changes)->DeployPreview`；`async commit_deploy(host, preview,*,username)->DeployResult(status: unchanged\|restored\|recovery_failed\|success, message, nextStep, formalHash)`；`async rollback(host,*,target_version\|backup_path)` |
| `backend/app/services/vps/nodes.py` | 节点目录（自建 + 回家只读） | `list_nodes(host_id=None)->list[Node]`；`Node(id,name,protocol,server,port,host_id,origin: self-built\|home-relay,secret_ref,enabled)`；回家节点从 FixCloud.yaml 只读解析，**不提供写接口** |
| `backend/app/services/vps/subscription.py` | 订阅渲染 | `render_clash_yaml(nodes,*,group_name="Self-Built")->bytes`；`render_stash_yaml(...)`（字段转换）；`render_singbox_json(...)`；`userinfo_header(nodes)->str`；token 校验与轮换 |
| `backend/app/services/vps/health.py` | 探测与缓存 | `async probe_tcp(server,port,timeout=5)->ProbeResult`；`async mihomo_delay(controller,secret,name,*,url,timeout=5000)->int\|None`；模块缓存 TTL 300s + force |
| `backend/app/api/vps_routes.py` | 新路由（挂到现有 router 或独立 APIRouter） | 见 §4.3 |
| `backend/tests/test_vps_hosts.py` 等 | 单测 | 沿用 tmp_path + Settings(storage_backend="local") + dependency_overrides + MockTransport；SSH 层用 fake transport 注入 |

### 4.2 后端修改（最小改动）

| 路径 | 改动 | 约束 |
|---|---|---|
| `backend/pyproject.toml` | dependencies 增 `asyncssh>=2.24,<3` | 不引入 paramiko/docker-py |
| `backend/app/core/settings.py` | 增 `vps_enabled: bool = False`、`vps_data_dir: str = "/data/vps"`、`vps_subscription_token: str = Field(default="", repr=False)`、`mihomo_controller_url: str = ""`、`mihomo_controller_secret: str = Field(default="", repr=False)` | 沿用 env_file + extra="ignore" + lru_cache |
| `backend/app/main.py` | 挂载 vps_routes；cleanup_loop 纳入 VPS 探测缓存/preview 过期 | 不改安全头与 CORS |
| `backend/app/api/routes.py` | 仅在需要处引用新 service；**保留 /vps/usage 原样** | 不重写既有路由 |
| `backend/app/services/source_store.py` | 可选：`SUPPORTED_SOURCE_TYPES` 增 `"ssh"` 以复用来源 UI；**若新增必须同步 safe_data 的 SENSITIVE_FIELDS（增 ssh_private_key / ssh_password / token）** | 不破坏既有来源迁移逻辑 |
| `backend/app/services/storage/registry.py` + 新 `storage/sftp.py` | 可选（P4）：实现 StorageBackend Protocol 的 SFTP 版，复用文件浏览/保存/历史 | MVP 不做 |
| `docker-compose.yml` / `.env.example` | 增 /data/vps 持久化（已在 /data 卷内，无需新卷）+ 新 env 说明 | **不改 read_only/cap_drop/user/ports/extra_hosts** |

### 4.3 新增 API（建议契约）

所有写操作：`Depends(require_internal_request)` + write_enabled 门禁 + probe/preview 门禁；错误返回中文 detail；审计 action 新增 `vps-host-create/update/delete`、`vps-preflight`、`vps-deploy`、`vps-rollback`、`vps-node-create/update/delete`、`vps-subscription-rotate`。

| 方法 路径 | 入参 | 出参 |
|---|---|---|
| GET `/api/vps/hosts` | — | `{hosts:[safe_data]}` |
| POST `/api/vps/hosts/probe` | `{name,address,sshUser,sshPort,credential}` | `{connected,latencyMs,hostKeyFingerprint,os,cpu,memoryMb,disk,singboxVersion\|null,dockerVersion,listening:[{proto,port,process}],firewall:{ufwActive,rules},sysctl:{rmemMax,wmemMax}}` |
| POST `/api/vps/hosts` | probeToken + 主机字段 | `{host}`（409 若未探测） |
| PUT/DELETE `/api/vps/hosts/{id}` | 同上 | `{host}` / 204 |
| GET `/api/vps/hosts/{id}/preflight` | — | 端口占用 / 防火墙 / 资源 / 版本 / 冲突项清单（只读） |
| POST `/api/vps/hosts/{id}/deploy/preview` | `{baseHash,changes}` | `{previewToken,diff,validation,willRestart,warns}` |
| POST `/api/vps/hosts/{id}/deploy/commit` | `{previewToken}` | `{status,message,nextStep,formalHash}` |
| POST `/api/vps/hosts/{id}/rollback` | `{targetVersion\|backupPath}` | 同上 |
| GET `/api/vps/nodes` | `hostId?` | `{nodes:[脱敏]}`（含回家节点只读项） |
| POST/PUT/DELETE `/api/vps/nodes/{id}` | 节点字段（凭据只写不回传） | `{node}` |
| GET `/api/vps/subscription` | `?token=&format=clash\|stash\|singbox` | YAML/JSON + `subscription-userinfo`；**支持 HEAD**；此路由**不要求** X-FixCloud-Request（客户端订阅拉取），但必须 token 鉴权 |
| POST `/api/vps/subscription/rotate` | — | `{token}`（仅此次返回，之后掩码） |
| GET `/api/vps/health` | `hostId?,force?` | `{nodes:[{name,reachable,delayMs,checkedAt}],cached}` |

### 4.4 前端新增 / 修改

| 路径 | 改动 |
|---|---|
| `frontend/src/stores/vps.ts`（新） | 主机/节点/部署/健康状态；复用 app store 的 request/notify；草稿存 sessionStorage（**凭据绝不写浏览器**） |
| `frontend/src/views/VpsOverviewView.vue`（新） | 概览：主机数、节点可用率 hero 指标、最近部署、快捷入口 |
| `frontend/src/views/VpsHostListView.vue`（新） | 列表行：图标 + 名称 + 地址/OS 摘要 + 状态 chip + chevron |
| `frontend/src/views/VpsHostDetailView.vue`（新） | 页签：概览 / 节点 / 配置 / 部署历史；头部 左返回 / 中标题 / 右保存（dirty 才亮） |
| `frontend/src/views/NodeDetailView.vue`（新） | 节点参数表单（左标签右值），凭据掩码 + "重新生成"动作 |
| `frontend/src/components/VpsDeployDiffModal.vue`（新） | 复用 DiffModal 骨架，展示配置 Diff + "会重启/断连"警示 |
| `frontend/src/components/VpsPreflightCard.vue`（新） | 端口/防火墙/资源预检结果卡（复用 ios-card / status-chip） |
| `frontend/src/router/index.ts`（改） | 增 /vps、/vps/hosts、/vps/hosts/:id、/vps/nodes/:id |
| `frontend/src/components/AppShell.vue`（改） | desktop navItems 增「自建节点」 |
| `frontend/src/views/MoreView.vue`（改） | 移动入口增「自建节点」 |
| `frontend/src/utils/vpsSchemas.ts`（新） | 协议字段 schema（ss2022 / vless-reality / hysteria2），与 editorSchemas 分离 |
| 测试 | `vpsSchemas.test.ts`、订阅渲染快照测试、draftGuard 交互测试 |

**复用清单（禁止另写 CSS）**：GroupCard、SettingsRow、ios-card / settings-row / status-chip-ok|warn|off / primary-button / soft-button / danger-button / form-field、AppDialogHost、UnsavedChangesModal、DiffModal、SaveBar、FileSelector、ReferenceIntegrityModal、SourceModal 的 probe 门禁骨架、SubscriptionNodesView 的网格布局、usage-card 的配额条范式、draftGuard / referenceGuard。**视觉以 visual-refresh.css 当前生效层为准。**

---

## 5. UI 与操作流程设计

遵循 Beam 既有产品规范（iOS 设置页 / Stash 式流程 + 当前 Nothing 覆盖层），信息架构 **overview → list → detail**。

### 5.1 导航与页面层级

- 桌面左侧持久导航新增「自建节点」（与 来源/编辑/流量/节点/历史/设置 并列）；工作列有界居中（page-width max 1120）。
- 移动：经「更多」进入；全屏详情页 + 底部 tab + safe-area + ≥44px 触达。
- 层级：
  ```
  自建节点概览
    ├─ VPS 列表（行：图标/名称/地址·OS/状态 chip/chevron）
    │    └─ VPS 详情（概览 | 节点 | 配置 | 部署历史）
    │         ├─ 概览：资源 hero 指标 + sing-box 版本 + 端口占用 + 防火墙状态
    │         ├─ 节点：该主机下的自建节点列表 → 节点详情（参数表单）
    │         ├─ 配置：结构化 JSON 视图（未知字段保留）+ 官方 check 结果
    │         └─ 部署历史：时间/版本/哈希/结果/回滚入口
    ├─ 节点目录（全部自建 + 回家节点只读纳管）
    └─ 订阅接入（Clash / Stash / sing-box 三种格式 + token 管理 + 客户端接入指引）
  ```

### 5.2 关键流程

**A. 添加 VPS**
1. 表单：名称 / 地址（IPv4 或专用 A 记录）/ SSH 用户 / 端口 / 凭据（私钥或密码，掩码）。
2. 「测试连接」→ busy + 防重复 → 成功绿（含延迟、OS、CPU/内存、sing-box 版本、监听端口、ufw 状态、host key 指纹）/ 失败红（中文分类：认证失败 / 超时 / 主机密钥不匹配 / 地址不可达）。
3. 首次连接显式展示 host key 指纹并要求确认（不静默 trust）。
4. 保存需 probeToken（沿用 ProbeStore 600s 一次性），否则 409。

**B. 部署 sing-box（核心事务）**
1. 「预检」只读展示：目标端口是否空闲、ufw 是否需放行、资源余量、现有容器、版本。
2. 选择协议与参数 → 生成配置 → **官方 check** → 展示完整 Diff + 警示（"将重建容器，存量连接会中断"、"需放行 ufw 规则 X"）。
3. 确认 → commit：备份现有配置 → 写临时 → check → 安全替换 → 回读校验 → 启动/重建 → 健康探测。
4. 结果三态明确：成功（绿 + 哈希 + 延迟）/ 未替换（unchanged）/ 已恢复（restored，附回读证据）/ 需人工（recovery_failed，保留 rollback 文件与路径）。
5. 全程审计，details 不含凭据。

**C. 生成节点与订阅接入**
1. 节点详情：左标签右值；密码/UUID 掩码 + 「重新生成」（二次确认，命名具体目标）； Reality 展示 public-key/short-id（私钥永不回传）。
2. 订阅页：三种格式各自的 URL（token 掩码，可复制）+ 「轮换 token」（二次确认）+ 各客户端接入步骤（Clash Verge / OpenClash / Stash / sing-box）。
3. 明确标注：订阅 URL 仅内网/回家隧道可达；**不得写入公开文件**。

**D. 健康检查**
- 节点行展示 可达性 + 延迟 + 检查时间（新鲜度低位）；「重新检查」busy + force。
- 延迟来源标注清楚：经路由器 OpenClash mihomo REST（真实链路）vs 面板 TCP 探测（仅端口可达）。**UDP 不用 nc -vzu 判定**（无握手不可靠）。

**E. IP 变更**
- 主机详情改地址 → Diff（列出受影响节点与订阅）→ 确认 → 更新 → 订阅自动跟随 → 提示客户端刷新。

### 5.3 状态与文案

- 每个异步动作：立即 busy + 防重复点击；成功绿 / 失败红 + 延迟或时间。
- 错误分类中文：认证失败 / 主机密钥不匹配 / 地址不可达 / 超时 / 端口被占用 / 防火墙未放行 / 配置校验失败 / 目标未变化 / 已恢复 / 需人工介入。
- 空态：无主机 → 引导添加；无节点 → 引导部署；离线 → 保留草稿禁止远程写。
- 列表页不放全局保存；保存只在详情页头部，dirty 才显示「有未保存修改」。
- 破坏性操作（删除主机/节点、轮换 token、回滚）二次确认且文案命名具体目标。
- 暗色模式覆盖卡片/弹窗/字段/分隔线/代码区/hover/禁用态；prefers-reduced-motion 生效。

### 5.4 紧凑监控卡（概览页）

- 单一 hero 指标：**节点可用率**（或剩余流量，二选一，不并列竞争）。
- 配额条 + 新鲜度低位 + 一个状态强调色；颜色必须配文字/图标（非纯色传达）。
- 服务商账单流量与节点流量分卡分口径标注，不混算。

---

## 6. 分阶段开发计划

| 阶段 | 范围 | 交付物 | 验收门槛 | 风险 / 回滚 |
|---|---|---|---|---|
| **P0 前置（需 Beam 动作）** | ① 服务商 API 白名单加 <NAS_EGRESS_IPV4>；② 决策 §3.6 公开暴露处置（推荐 A）；③ 确认是否 git init 建立回滚点；④ 确认 Stash 版本与 OpenClash 内核版本 | 决策记录 + 白名单生效 | /api/vps/usage 两台 available:true | 不动代码；账号侧操作由 Beam 执行 |
| **P1 MVP（SS2022 闭环）** | asyncssh + 主机 CRUD/probe + preflight + SS2022 配置渲染 + 官方 check + 部署事务 + 回滚 + 节点目录 + Clash 订阅端点（token + userinfo + HEAD）+ 前端概览/列表/详情/部署 Diff | 可跑通：添加 VPS → 预检 → 部署 SS2022 → 生成节点 → 订阅 → 客户端可用 | 后端 pytest 全绿；前端 typecheck/build/test 全绿；隔离环境部署成功 + 健康探测通过；**至少 1 个客户端真实拉取订阅并连通**；部署前后权威数据 hash/计数核对 | 部署失败三态 + 配置备份 + 钉 tag 回滚；ufw 规则按编号删除 |
| **P2 抗封锁升级** | VLESS+Reality（keypair 生成、握手目标选择、非 443 TCP 端口）+ Stash 字段转换输出 + sing-box JSON profile + 健康检查（mihomo REST 延迟） | Reality 节点 + 三格式订阅 + 延迟视图 | 同 P1 门槛 + Reality 在 ≥2 类客户端连通 | 协议切换只改配置，走同一部署事务 |
| **P3 吞吐与统计（有条件）** | Hysteria2（UDP 443）+ sysctl 缓冲抬升（**需单独授权**）+ ufw UDP 放行 + 连接级流量统计 + ssm-api/service-api 评估 | hy2 节点 + 流量卡 | 移动网络实测 QoS 可接受；JP 1vCPU 下 CPU 占用可接受；否则只在 HK 启用 | sysctl 改动可逆（记录原值 212992/4194304）；hy2 被阻断时回退 SS2022/Reality |
| **P4 自动化与扩展** | Lucky OpenToken 自动端口转发（接口需先验证）+ SFTP StorageBackend（复用文件浏览/历史）+ IP 变更联动 + 更多 VPS | 自动化转发 + 远程文件浏览 | OpenToken 接口实测通过才启用；否则保持手工 ufw | 不触碰 DNS/证书/回家转发 |

**每阶段通用门槛**：先在隔离目录实现 → 复用组件不复制 CSS → tsc/前端单测/生产构建/后端测试/API 校验 → 授权后 compose 部署 → 容器健康 → Mac Safari 目视 + 暗色 + 响应式 + 控制台无错 → 加载/空/离线/失败/dirty 态覆盖 → 部署前后权威数据 hash 与计数核对。**构建通过 ≠ 交互验收；HTTP 200 ≠ 数据路径正确。**

---

## 7. 与现有 Lucky 环境的兼容性

| 现有资产 | 现状【已验证】 | 本次设计的处理 |
|---|---|---|
| VPS Lucky（两台） | host 网络，TCP 443 + 16601，UDP 52889(JP)/55234(HK) | **不动**。sing-box 用独立 bridge + 高位端口；hy2 用 UDP 443（与 Lucky TCP 443 同号共存，协议不同不冲突） |
| NAS Lucky | 统一管 DNS / Web / 证书 / 回家端口转发 | **职责不变**。新增专用 A 记录（仅 A）由 Lucky DNS 管理；不改现有解析 |
| jpedge / hkedge | 双栈域名，AAAA 指向家庭 NAS | **禁止**用于定位 VPS 代理节点；SSH 与节点 server 用 IPv4 或专用 A 记录 |
| 回家节点 | FixCloud.yaml proxies[0]：localhost / socks5 / <HOME_DOMAIN>:7891（含凭据） | **只读纳管**进节点目录，不修改其配置、不触碰其转发 |
| 证书同步 | lucky-vps-cert-sync / lucky-hk-cert-sync 把 .vps-cert-export 同步到 VPS | **不动**。Reality 不需证书；若将来用 TLS 方案，可复用同步过来的证书文件（1.14 `certificate_provider` 或 certificate_path/key_path；内联 acme 已 Deprecated） |
| SSH 隧道 | lucky-vps-admin-tunnel（127.0.0.1:26611→JP 16601）、lucky-hk-admin-tunnel（26612→HK） | **不动、不复用**。面板自建 asyncssh 直连 VPS IPv4 |
| Lucky 管理入口 | nginx <NAS_LAN_IP>:24443 ssl，<LUCKY_LAN_DOMAIN>，/jp/ /hk/ / | **不动**。面板可在 UI 外链到该入口（只读跳转） |
| ufw（两台） | active，default deny incoming；仅放行 22/80/443 tcp | 新端口必须显式放行；**预检阶段只读检测并列出需新增的规则，执行需用户确认**；回滚按规则编号删除，不清空整链 |
| 云防火墙（Vultr/Evoxt） | 未验证 | 列为预检未确认项；若存在需同步放行 |
| R5C / OpenClash | iStoreOS fw4/nftables + Fake-IP 非 TUN；OpenClash TCP 接管在 inet fw4 openclash 链先于 clash 规则 | 若将来经 Lucky STUN 穿透，需按 lucky-openclash-stun 范式加 `nft insert rule inet fw4 openclash ip saddr <NAS> tcp sport <端口范围> counter return comment 'lucky_stun_bypass'`；回退按 handle 删除。**本次 MVP 不涉及** |
| 面板容器 | bridge，read_only，cap_drop ALL，非 root | 不改网络模式、不改端口、不改 extra_hosts；新增能力全部在 /data 与纯 Python 依赖内完成 |

---

## 8. 实际部署与测试方案

### 8.1 开发与验收命令（按顺序）

```bash
# 前端
cd frontend && npm ci
npm run typecheck        # vue-tsc -b
npm run test             # vitest run
npm run build            # vue-tsc -b && vite build

# 后端
cd ../backend
python3 -m venv .venv && .venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q

# 部署（仅在获得授权后）
docker compose up -d --build
docker ps --filter name=fixcloud-panel   # 期望 Up (healthy)
curl -s http://<NAS_LAN_IP>:8787/api/health
```

### 8.2 部署前只读预检（面板 preflight 端点应覆盖）

```bash
ss -tulpn                      # 端口占用（TCP/UDP）
ufw status numbered            # 防火墙规则（按编号，便于回滚）
sudo -n nft list ruleset | head # 只读
sysctl net.core.rmem_max net.core.wmem_max
free -m; nproc; df -h /
docker ps --format '{{.Names}} | {{.Image}} | {{.Ports}}'
command -v sing-box; ls /etc/sing-box
```

### 8.3 部署步骤（授权后，每台 VPS）

1. 记录权威数据基线：现有容器清单、监听端口、ufw 规则编号、FixCloud.yaml sha256 与 proxies/providers/rules/groups 计数。
2. 备份：`/etc/sing-box` 若存在则整目录备份；记录当前镜像 tag。
3. 写配置到临时路径 → `sing-box check -C <临时目录>` → 通过后安全替换 → 回读校验哈希。
4. `docker compose up -d`（钉 v1.14.4）→ 容器健康 → `sing-box version`。
5. ufw 放行新端口（**逐条、可编号回滚**）；云防火墙若存在同步放行。
6. 健康探测：TCP 可达 + 经客户端/路由器 mihomo REST 取真实延迟。
7. 订阅验证：客户端拉取 → 解析 proxies → 实际连通（至少 Clash Verge + OpenClash + Stash 中两类）。
8. 复核基线：Lucky 容器仍在、TCP 443/16601 仍监听、回家节点仍可用、证书同步容器未受影响、FixCloud.yaml 哈希未变（若选 §3.6 选项 A）。
9. 审计记录：action / 主机 / 版本 / 前后哈希 / 结果三态；不含凭据。

### 8.4 回滚

- 配置：恢复备份字节（不重新解析 dump）→ check → 重建 → 回读证明。
- 版本：compose 改回旧 tag → up -d。
- 防火墙：按规则编号删除新增项，**不清空整链**。
- sysctl（若 P3 改过）：恢复原值（JP 212992、HK 4194304）。
- 明确报告：正式文件未变 / 已恢复 / 需人工，且"已恢复"必须有回读证据。

### 8.5 测试矩阵

| 维度 | 覆盖 |
|---|---|
| 协议 × 客户端 | SS2022 / Reality / hy2 × Clash Verge Rev 2.5.10 / OpenClash 0.48.002（mihomo 1.19.34）/ Stash（版本待确认）/ sing-box 客户端 |
| 网络 | 家庭宽带（电信，IPv6 入站在线）/ 移动网络（UDP QoS 风险）/ 经回家 SOCKS5+TLS 隧道 |
| 订阅格式 | Clash YAML / Stash 转换版 / sing-box JSON；HEAD 请求；subscription-userinfo 解析；token 轮换后旧 token 失效 |
| 故障注入 | SSH 认证失败 / 主机密钥不匹配 / 超时 / 端口占用 / check 失败 / 部署中途失败（验证 unchanged/restored/recovery_failed）/ 离线草稿保留 |
| UI 态 | 加载 / 空 / 离线 / 失败 / dirty / 暗色 / 响应式 / 控制台无错 / Mac Safari 目视 |
| 数据安全 | 部署前后 FixCloud.yaml 哈希与计数核对；凭据不出现在 API 响应/审计/浏览器存储/日志 |

### 8.6 明确未验证项（实施前需确认）

- Stash 实际版本（Reality 需 iOS 3.4.0+）、OpenClash 实际内核版本。
- Vultr / Evoxt 云防火墙是否存在及其规则。
- Lucky OpenToken 的具体接口（社区抓包 PUT /api/portforward 未验证）。
- 各协议在用户实际线路的延迟/吞吐（需实测）。
- sing-box 官方内存/CPU 量级（官方未给数字；第三方空闲 RSS 17–35MB 未复核）。
- HK VPS 供应商归属（IP <VPS_HK_IP>，用户称 Evoxt，未验证）。
- oixCloud.yaml 的用途与是否纳入管理。
- 谁在消费公开的 <PUBLIC_FILE_DOMAIN>/FixCloud.yaml（决定 §3.6 选项）。

---

## 9. 给 Codex 的实施契约

### 9.1 可直接粘贴的启动指令

```
项目：/Users/beamjason/Documents/BeamNat/fixcloud-panel（Vue3+TS+Vite+Tailwind4 / FastAPI / ruamel.yaml round-trip / Docker bridge on QNAP）。
任务：按 docs/vps-singbox-integration-research.md 实施 P1 MVP（SS2022 闭环），不要推倒重写。
硬约束：
1. 本轮不得修改任何运行中的 VPS 服务、NAS 面板容器、Lucky 配置、SSH 隧道、证书同步、正式 FixCloud.yaml。
2. SSH 用 asyncssh（纯 Python）直连 VPS IPv4；不引入 paramiko/docker-py；不改 host 网络；不复用 127.0.0.1:26611/26612 隧道。
3. sing-box 用官方镜像 ghcr.io/sagernet/sing-box:v1.14.4，配置目录 /etc/sing-box、数据目录 /var/lib/sing-box；下发前必须 sing-box check。
4. sing-box JSON 不走 yaml_service 的 Clash 校验链；新建独立 schema + 官方 check。
5. 部署事务复刻 save_service 状态机（备份→写临时→校验→安全替换→回读→失败三态 unchanged/restored/recovery_failed），审计沿用 audit_log，details 不含凭据。
6. 凭据只留后端（0600 + safe_data 脱敏 + API 不回传 + 不进浏览器存储/日志）；写路由继承 require_internal_request（X-FixCloud-Request: 1）+ write_enabled + probe 门禁。
7. 节点地址用 VPS IPv4 或仅 A 记录的专用子域；禁止用 jpedge/hkedge（AAAA 指向家庭 NAS）。
8. 自建节点凭据与订阅 token 绝不写入会被公开下载的 FixCloud.yaml（<PUBLIC_FILE_DOMAIN> 当前无鉴权可读）。
9. 前端复用现有组件与当前生效的 visual-refresh.css 视觉层，不另写 CSS；信息架构 overview→list→detail；详情页头部 左返回/中标题/右保存，保存进 Diff 评审流；列表页不放全局保存。
10. 端口：SS2022 TCP+UDP 18388（示例，实施前预检）；避开 Lucky TCP 443/16601、UDP 52889/55234、22、53、323。ufw 新规则逐条可编号回滚。
验收：npm run typecheck/test/build 全绿；backend pytest 全绿；隔离环境部署 + 健康探测；至少 1 个客户端真实拉取订阅并连通；部署前后权威数据 hash/计数核对；Mac Safari + 暗色 + 响应式 + 控制台无错 + 加载/空/离线/失败/dirty 态覆盖。
先输出实施计划与文件清单，确认后再写代码。
```

### 9.2 Do / Don't

**Do**：复用 StorageBackend/save_service/audit/ProbeStore/request/notify/draftGuard/GroupCard/SettingsRow/DiffModal；新增 services/vps/* 与 vps_routes.py；asyncssh；官方 check；钉 tag；三态失败语义；中文错误；token 订阅 + HEAD + subscription-userinfo；预检只读先行。

**Don't**：引入 3x-ui/Marzban/hiddify/s-ui/Sub-Store/subconverter；用 paramiko/docker-py；改 host 网络或容器 read_only/cap_drop；动 Lucky/隧道/证书同步/回家节点；用 jpedge/hkedge 定位 VPS；把凭据写进公开文件或浏览器存储；用 Clash 校验链校验 sing-box JSON；把用户输入拼进远程 shell；用 nc -vzu 判定 UDP 可达；把服务商账单流量当节点流量；声称"已恢复"而不回读证明；在 design-only 阶段安装/迁移/重写/删除/保存生产数据。

---

## 10. 附录：本次实测证据清单

| 证据 | 命令/方式 | 结果 |
|---|---|---|
| 面板容器直连 VPS SSH | docker exec fixcloud-panel python socket.create_connection | <VPS_JP_IP>:22 OK 0.41s（OpenSSH_9.6p1 Ubuntu-3ubuntu13.2）；<VPS_HK_IP>:22 OK 0.18s（OpenSSH_10.2p1 Ubuntu-2ubuntu3）；两台 :443 OK |
| 服务商 API 可达性 | 同上 + httpx | api.vultr.com / api.evoxt.com DNS 仅 IPv4，TCP 0.02s / 0.01s；无 token GET /v2/account → 401 Invalid API token |
| 服务商 API 授权 | 带已配置凭据（未回显值） | Vultr /v2/account/bandwidth → 401 Unauthorized IP address: <NAS_EGRESS_IPV4>；Evoxt /listserver → 200 {"error":"IP Address Unauthorized"} |
| 现有 VPS 用量端点 | GET http://<NAS_LAN_IP>:8787/api/vps/usage | 200，两台 available:false，1.34s |
| VPS 端口/防火墙/缓冲 | ssh vps/hk 只读 ss/ufw/sysctl/docker ps | 见 §1.2 表；ufw 仅放行 22/80/443 tcp；JP rmem/wmem 212992、HK 4194304；两台均无 sing-box |
| NAS 隧道与 admin 入口 | docker.sock 只读 inspect + 读 nginx.conf | 见 §1.2；隧道只绑 127.0.0.1:26611/26612；admin nginx <NAS_LAN_IP>:24443 /jp/ /hk/ / |
| 公开文件暴露 | GET https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml（无鉴权）+ ruamel 结构解析 | 200，20893 字节；proxies 1（socks5 含 username/password）；providers 3（2 个带 query token）；rules 66、groups 33；顶层含 external-controller/secret |
| 容器 IPv6 能力 | docker exec httpx | ipv6.baidu.com 200 / 0.16s（出网正常）；到 NAS 自身公网 IPv6 超时（无 NAT66） |
| sing-box 版本/镜像 | releases.atom + ghcr registry API + 官方文档/源码 | stable v1.14.4（2026-10-24）；tag v1.14.4/latest/latest-beta/latest-testing；alpine；/usr/local/bin/sing-box；compose command -D /var/lib/sing-box -C /etc/sing-box/ run |
| 客户端版本 | releases.atom / 官方更新日志 | mihomo v1.19.34（2026-11-11）、Verge Rev v2.5.10、OpenClash v0.48.002、Stash iOS 3.4.0 / macOS 4.2.0 |

### 参考链接

- sing-box：https://github.com/SagerNet/sing-box ｜ https://sing-box.sagernet.org/ ｜ https://sing-box.sagernet.org/installation/docker/ ｜ https://sing-box.sagernet.org/configuration/inbound/shadowsocks/ ｜ /hysteria2/ ｜ /vless/ ｜ https://sing-box.sagernet.org/configuration/shared/tls/ ｜ https://sing-box.sagernet.org/configuration/experimental/clash-api/ ｜ /v2ray-api/ ｜ https://sing-box.sagernet.org/configuration/service/api/ ｜ /ssm-api/ ｜ https://github.com/SagerNet/sing-box/blob/v1.14.4/release/config/sing-box.service ｜ https://github.com/SagerNet/sing-box/blob/v1.14.4/cmd/sing-box/cmd_run.go
- mihomo：https://github.com/MetaCubeX/mihomo ｜ https://wiki.metacubex.one/api/ ｜ https://wiki.metacubex.one/config/proxies/ss/ ｜ /hysteria2/ ｜ /vless/
- 客户端：https://github.com/clash-verge-rev/clash-verge-rev ｜ https://github.com/vernesong/OpenClash ｜ https://stash.wiki/proxy-protocols/proxy-types ｜ https://stash.wiki/features/service-provider-subscription ｜ https://stash.wiki/release-notes/ios ｜ https://sing-box.sagernet.org/clients/general/
- 协议规范：https://github.com/XTLS/REALITY ｜ https://github.com/Shadowsocks-NET/shadowsocks-specs ｜ https://hysteria.network/docs/advanced/Performance/ ｜ https://v2.hysteria.network/
- Lucky：https://github.com/gdy666/lucky ｜ https://lucky666.cn/docs/intro
- SSH/工具：https://asyncssh.readthedocs.io/en/latest/ ｜ https://github.com/tindy2013/subconverter ｜ https://github.com/Toperlock/sing-box-subscribe ｜ https://github.com/SagerNet/sing-box-dashboard
- 本项目历史：Codex 线程 <CODEX_THREAD_ID>（FixCloud 面板开发，07-20→09-29；**该线程无 sing-box/VPS 选型实质决策**）

---

*本报告全部环境结论来自只读探测；未修改任何运行中的服务、未写入任何生产配置、未回显任何凭据值。*
