# 11 · 私有订阅中心实施方案（FixCloud Panel）

> 来源归属与核实时间
> - 核实时间：2026-11-25（Asia/Shanghai）。本文所有【我方已验证】结论均来自本会话对源码仓库与生产面板的只读核实，不沿用旧报告推测。
> - 源码仓库：JasonBeam/fixcloud-panel（GitHub Private，remote 主机 github.com），核实 HEAD 9983f52（2026-11-25 01:53:50 +0800），工作树干净。【我方已验证】
> - 知识库仓库：homelab-panel，核实 HEAD b0e5d53（2026-11-25）。【我方已验证】
> - 生产面板：http://<NAS_LAN_IP>:8787（内网），本会话只读 GET /api/health 返回 {"status":"ok","storage":"ready","yaml":"valid"}。【我方已验证】
> - 参考项目：homelab-sanitize/fork-clone（上游 JimmyChan233/homelab 私有 Fork，licenseInfo=null 无许可证）。本文只提炼设计思想，不复制任何源码/配置/UI；参考结论已对照 scripts/friends/friendsd.py 抽查核实。【参考提炼】
> - 徽章含义：【我方已验证】=本会话读源码/只读探测证实；【生产配置】=compose/.env/交接报告记录的部署事实；【参考提炼】=参考项目设计思想（不可逐字复制）；【待验证】=本方案提出的设计契约，尚未实现/尚未实测；【已过时】=被本次核实推翻的旧结论。
> - 脱敏：全文不含真实凭据/IP/域名/邮箱/手机号/订阅 token/UUID。占位符 <NAS_LAN_IP> <NAS_PUBLIC_IPV6> <NAS_EGRESS_IPV4> <HOME_DOMAIN> <PUBLIC_FILE_DOMAIN> <VPS_JP_IP> <VPS_HK_IP> <SUB_PROVIDER_*_DOMAIN> <EXAMPLE_SUB_TOKEN>；示例值用 example.com / 192.0.2.10 / 198.51.100.20 / 203.0.113.30 / 00000000-0000-4000-8000-000000000000。容器名/路径/环境变量键名/端口/协议名/字段名属结构性事实予以保留。

---

## 1. 目标与范围

最终目标：FixCloud.yaml 不再通过 file 域名（<PUBLIC_FILE_DOMAIN>）无鉴权公开访问，改为由面板生成**可管理、可撤销、可自动更新**的私有订阅链接。【待验证】（目标形态，源自 roadmap/01）

目标数据流：内部主配置（全部凭据，仅 NAS 本地 0600）→ 订阅视图（自用视图=全量+回家节点；朋友视图=仅线路 id 白名单）→ 渲染器（MVP 仅 Clash YAML）→ GET/HEAD /api/sub/<token>（token 鉴权 + 配额/有效期 + Subscription-Userinfo）→ 客户端。【待验证】

范围内：
- 新增订阅输出子系统（token 存储、签发/撤销/轮换/列表管理 API、Clash YAML 渲染器、泄露断言、Subscription-Userinfo/HEAD/ETag/304）。【待验证】
- 前端新增「订阅发布」页（overview→list→detail）。【待验证】
- 从公开 file URL 到私有订阅的迁移流程与验收标准。【待验证】

范围外（本轮不做）：
- 不改任何生产服务、不重启、不部署、不修改防火墙、不执行订阅迁移。【我方已验证】（任务硬约束）
- 不做 base64 订阅输出；sing-box JSON remote profile 放 P2。【待验证】（roadmap/01 决策）
- 不改 FastAPI + Vue3 + Lucky 总体架构。【待验证】

核心安全原则：内部主配置与对外视图**物理分离**；对外视图永不含回家节点凭据、external-controller、secret、上游订阅 URL 与其 token、其他用户的线路。【待验证】（roadmap/01、playbook/03）

---

## 2. 现状与差距（精确到文件:行号与函数名）

### 2.1 面板是"订阅消费者 + 配置编辑器"，无订阅输出端点

- backend/app/api/routes.py 共 1193 行，router = APIRouter(prefix="/api")（routes.py:35），全表 34 条路由。【我方已验证】
- 订阅相关只有**读取**端点，全部 GET、无 require_internal_request：
  - GET /api/subscriptions/usage（routes.py:264-284，函数 subscription_usage）→ 读 YAML、YamlService().load、SubscriptionUsageService().get_usage(document.root, cache_key=..., force=...)。cache_key 形如 "{scope}:{source.id}:{yaml_path}:{sha256(raw)}"，scope 对 upload 来源取 current_scope() 否则 "formal"（routes.py:278-282）。【我方已验证】
  - GET /api/subscriptions/nodes（routes.py:293-311，函数 subscription_nodes）→ SubscriptionNodesService().get_nodes(document.root, cache_key="nodes:...", force)。【我方已验证】
  - GET /api/vps/usage（routes.py:287-290，函数 vps_usage）→ get_vps_usage()。【我方已验证】
- **不存在任何 /sub 输出路由**；面板只消费上游订阅（拉取流量/节点），不向客户端发布订阅。这是本方案要补的核心差距。【我方已验证】

### 2.2 内网门禁是"同源标记头"，不是 IP 白名单

- require_internal_request(request)（routes.py:107-109）：仅检查 request.headers.get("x-fixcloud-request") != "1" 则抛 403 "写请求缺少面板同源标记"。【我方已验证】
- 34 路由中 18 条非 GET 端点依赖它（probe/test/directories/create/update/delete source、upload/delete/select file、export/preview/validate/preview_raw/save config、restore_preview/delete_backup、update_log_settings/clear_logs）。【我方已验证】
- 差距：该头任何能到达端口的人都可伪造，无 IP 白名单。管理端点安全边界=内网可达性 + 同源标记；**订阅输出端点绝不能要求该头**（客户端无法设置），必须走 token 鉴权。【我方已验证】+【待验证】

### 2.3 安全头中间件会给每个请求创建浏览器会话（订阅输出的关键陷阱）

- backend/app/main.py 共 99 行。security_headers 中间件（main.py:54-94）对**每个请求**：读 cookie fixcloud_session，无效则 new_token()，session_directory(...) + touch(directory)（main.py:58-64），bind(scope_for_token(token), directory)（main.py:65），finally unbind（main.py:69），新建则 set_cookie httponly/samesite=strict/secure=False/path=/（main.py:70-78）。【我方已验证】
- 差距/风险：未来订阅客户端每次拉取（无 cookie）都会触发新建会话目录 + touch，加剧本已累积的 temporary-sessions（生产实测约 2911 个子目录，见 panels/05）。**订阅输出端点必须绕过浏览器会话绑定**（中间件对 /api/sub 路径跳过 session 创建，或订阅路由不经过该 bind 逻辑）。【我方已验证】（机制）+【待验证】（修法）
- Cache-Control：中间件在 call_next 之后设置，/api/* → no-store（main.py:88-89），其余 GET/HEAD → no-cache（main.py:90-93）。⇒ 订阅输出放在 /api/sub/<token> 可自动继承 no-store；若放裸 /sub 会被设成 no-cache（不符合订阅要求）。**建议订阅输出路径置于 /api 前缀下**。【我方已验证】+【待验证】
- 安全头：X-Content-Type-Options nosniff、X-Frame-Options SAMEORIGIN、Referrer-Policy no-referrer、Permissions-Policy、CSP default-src 'self'（main.py:79-87）。CORS 仅允许 http://localhost:5173 / http://127.0.0.1:5173（开发源），allow_methods GET/POST/PUT/DELETE（main.py:44-50）。订阅客户端为非浏览器，不受 CORS 限制。【我方已验证】
- 静态挂载：app.mount("/", StaticFiles(directory=frontend_dist, html=True))（main.py:97-99）在 include_router(router)（main.py:51）之后；API 路由优先匹配，/api/sub 不会被 SPA fallback 吞掉。【我方已验证】
- lifespan 启动 cleanup_loop(settings.app_data_dir, stop)（main.py:27-35）。【我方已验证】

### 2.4 配置服务现状

- backend/app/core/settings.py 共 35 行。Settings 字段：app_env、app_data_dir(/data)、storage_backend(smb-mounted)、storage_root(/mnt/fixcloud)、yaml_path(/FixCloud.yaml)、write_enabled(False)、webdav_*、public_file_base_url(https://file.example.com)、frontend_dist(/app/frontend/dist)（settings.py:15-30）；get_settings() 带 lru_cache（settings.py:33-35）。**无任何订阅相关配置项**，需新增。【我方已验证】
- backend/app/services/subscription_usage.py：CACHE_TTL_SECONDS=300（:16）、SHANGHAI=ZoneInfo("Asia/Shanghai")（:15）；parse_subscription_userinfo（:20）、content_disposition_title（:43）、usage_payload（:53-95）、SubscriptionUsageService（:98，__init__ 接受 transport: httpx.AsyncBaseTransport|None）、get_usage（:102）、_fetch_one（:154）。HEAD 优先、无 userinfo 头再 stream GET、不返回 URL、不下载正文（panels/03）。【我方已验证】
- backend/app/services/subscription_nodes.py：MAX_SUBSCRIPTION_BYTES=8MiB（:16）、MAX_NODES_PER_PROVIDER=500（:17）、MAX_PROVIDERS=20（:18）；_decode_subscription（:33，输入侧 base64 解码）、parse_subscription_nodes（:56）、get_nodes（:75）。注意：面板**输入侧**已能解 base64 订阅，但**输出侧** MVP 不做 base64。【我方已验证】
- backend/app/services/publication.py：MAX_PUBLIC_YAML_BYTES=5MiB（:10）、PublicationCheckError（:13）、PublicationVerifier(base_url)（:18）、compare(*, filename, current)（:25）。GET /api/publication/status（routes.py:314-351）会写审计（publication-check success/failure），是**有副作用的 GET**。【我方已验证】

### 2.5 公开暴露面（要消除的目标）

- https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml 无鉴权 200，20893 字节，含回家节点凭据、3 个 provider 中 2 个带 query token、external-controller + secret、66 条 rules、33 个 groups（交接报告 reports/08，2026-11-25 核实）。【生产配置】+【我方已验证】（本会话 GET /api/health 证实面板在线；公开文件内容引用交接报告同日核实）
- frontend/public/demo/nothing-full.html（9 处）/nothing-iphone.html（6 处）含真实值且未 gitignore；生产 GET /demo/*.html 实测 404，当前未暴露。【我方已验证】（交接报告同日探测）
- 容器经 extra_hosts 把 <PUBLIC_FILE_DOMAIN> 解析到 bridge IPv6 网关（fd00::1），由宿主 Lucky 本地投递（docker-compose.yml:18-21）。【生产配置】

### 2.6 存储与权限现状（影响 token 落盘）

- /data 实测 0770（代码意图 0600），QNAP 共享 ACL/umask 在宿主侧覆盖容器内 os.open 0o600 ⇒ sources.json 明文凭据组可读（panels/05）。【我方已验证】
- mounted.move overwrite 保留目标原权限位（storage/mounted.py:136-147）⇒ 0770 目标经 move 覆盖后仍 0770，tmp 的 0600 不会带到正式文件。token 存储的权限断言必须按此设计（不能假设落盘即 0600）。【我方已验证】
- 普通保存不再产生永久备份（save_service.py commit 返回 backupPath=None，:316-322；交接报告 :308/318）。【我方已验证】
- 已过时：交接报告称源码"无 .git"——本次核实源码已是 git 仓库（HEAD 9983f52，remote github.com/JasonBeam/fixcloud-panel）。【已过时】

---

## 3. 数据模型

以下均为【待验证】设计契约（尚未实现），存储路径/权限复用现有范式处标注【我方已验证】。

### 3.1 Token 记录（subscription_tokens.json）

建议存储路径：/data/subscription-tokens.json（属主面板 UID 1000:GID 100）。落盘复用 source_store._write 的 O_EXCL 0o600 + fsync + os.replace + chmod 范式（source_store.py:153-178）。【我方已验证】（范式）+【待验证】（新文件）

每条记录字段（JSON，snake_case 存储，API 序列化 camelCase）：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | str | 内部 id，secrets.token_hex(4)（8 hex），用于审计/日志，非密钥 |
| token_hash | str | SHA-256(明文 token) 的 64 hex；**只存 hash，不存明文** |
| label | str | 人类可读备注，≤40 字符 |
| scope | "self" \| "friend" | 自用视图 / 朋友视图 |
| allowed_line_ids | list[str] | 朋友视图允许输出的线路 id 白名单；自用视图为空（=全量） |
| created_at | str(ISO8601 UTC) | 签发时间 |
| expires_at | int | unix 秒；0=长期有效 |
| revoked_at | int \| null | 撤销时间戳；非 null 即失效 |
| last_used_at | int \| null | 最近拉取时间（unix 秒） |
| use_count | int | 累计拉取次数 |
| quota_total_bytes | int | 配额总字节；0=不限 |
| quota_used_bytes | int | 累计上下行字节（需流量统计支撑，MVP 占位 0） |
| rotate_grace_until | int \| null | 轮换宽限期截止（unix 秒），宽限期内旧 token 仍可用 |
| note | str | 备注 ≤80 字符 |

权限：文件意图 0600；但须按 2.6 的 NAS ACL 现实，在验收中实测宿主侧权限并必要时由用户在宿主侧收紧（属生产变更，需单独授权）。【我方已验证】（ACL 现实）+【待验证】（收紧动作）

### 3.2 订阅视图（渲染产物缓存）

- 渲染产物为 bytes（Clash YAML），按 token_hash + 主配置 sha256 + scope 派生缓存键。内部渲染缓存 TTL 建议 60s，主配置变更主动失效（roadmap/01）。【待验证】
- 缓存落点只能在 /data 或 /tmp（容器 read_only:true 根文件系统，tmpfs /tmp 32m，docker-compose.yml:36-38）。建议 /data/subscription-cache/<token_hash>.yaml，0600 意图。【生产配置】+【待验证】
- 撤销时删除该 token 的渲染缓存与任何凭据副本（playbook/03）。【待验证】

### 3.3 配额计数

- MVP：quota_used_bytes 占位 0，userinfo 全 0（无流量统计）。真正按 token 计上下行需要节点侧流量统计（参考 fwmark 按人计数思想，见第 8 章），放 P1/P2。【待验证】+【参考提炼】
- 超配额行为：403 且 userinfo 反映用量（playbook/03）；MVP 无统计时不触发。【待验证】

### 3.4 审计事件

- 复用现有 AuditStore（audit.py:16）与 audit_log 表（自增 id + 10 数据列，共 11 列：created_at, source_id, session_scope, username, action, path, before_hash, after_hash, backup_path, details）。【我方已验证】（audit.py:80-89 INSERT）
- 订阅事件用 record_event(source_id, action, path, status, message, details)（audit.py:94-102），username 固定 "内网访问"，details={status, message, ...}。【我方已验证】
- 新增 action 建议：subscription-issue / subscription-revoke / subscription-rotate / subscription-fetch（fetch 只记内部 id 或 hash 前缀，**绝不记明文 token**）。details 不记凭据（沿用 audit.py:71-102 边界）。【待验证】
- source_id 对订阅事件建议用固定标识（如 "subscription"），session_scope 留空（订阅输出不绑浏览器会话，见 2.3）。【待验证】

---

## 4. API 契约

管理端点与订阅输出端点**分开鉴权**，且**绝不共用鉴权依赖**。

> **与 12 号安全边界文档的强制对齐**：现状 `require_internal_request`（routes.py:107-109）只查可伪造的 `x-fixcloud-request:1` 头，已被 12 号文档判定为 **P0-3**。因此本方案所有管理端点一律依赖 **`require_admin`（12 §5.1：可信网段 + ADMIN_TOKEN 换取 httponly 管理员会话 cookie）**，不得沿用旧头作为安全边界；旧头仅保留为 CSRF 辅助。实施顺序上 **12 §8 的 Phase 0（管理鉴权）必须先于本章 P0-b**，否则新端点会继承零鉴权面。【我方已验证】（现状门禁）+【待验证】（新契约）

订阅输出端点走路径段 capability token，**不要求**管理员 cookie，也**不做网段限制**（移动设备需在外网取订阅）。

### 4.1 管理端点（内网 + 同源标记，prefix /api）

| 方法/路径 | 鉴权 | 请求体 | 响应体 | 错误码 |
|---|---|---|---|---|
| POST /api/subscriptions/tokens | require_admin（12 §5.1） | {label, scope, allowedLineIds?, expiresAt?, quotaTotalBytes?, note?} | {id, token(明文，仅此一次), label, scope, expiresAt, createdAt} | 403 缺标记；422 参数非法 |
| GET /api/subscriptions/tokens | require_admin（12 §5.1；token 列表敏感，必须加） | — | {tokens:[{id,label,scope,expiresAt,revokedAt,lastUsedAt,useCount,quotaUsedBytes,...}]}（**不含明文/hash 全量**） | 403 |
| POST /api/subscriptions/tokens/{id}/revoke | require_admin（12 §5.1） | — | {id, revokedAt} | 403；404 id 不存在 |
| POST /api/subscriptions/tokens/{id}/rotate | require_admin（12 §5.1） | {graceSeconds?} | {id, token(新明文，仅此一次), oldGraceUntil} | 403；404 |
| GET /api/subscriptions/tokens/{id} | require_admin（12 §5.1） | — | {id,label,scope,allowedLineIds,expiresAt,revokedAt,...}（不回显明文） | 403；404 |

请求约束建议（沿用现有 Field 风格，routes.py:46-104）：label≤40、note≤80、scope∈{self,friend}、expiresAt 整数≥0、allowedLineIds 数组。POST body 上限建议 65536（参考 friendsd 413 思想）。【待验证】+【参考提炼】

### 4.2 订阅输出端点（token 鉴权，不要求同源标记）

| 方法/路径 | 鉴权 | 响应 | 错误码 |
|---|---|---|---|
| GET /api/sub/<token> | 路径段 token → SHA-256 → 常量时间比对 token_hash | 200 Clash YAML body + 头（见第 7 章） | 404/410 不存在或已撤销；410 已过期；403 超配额；500 渲染失败/泄露断言命中 |
| HEAD /api/sub/<token> | 同上 | 200 头与 GET 一致，body 空 | 同上 |

- token 不存在/已撤销：404 或 410，**不泄露该 token 是否曾存在**（playbook/03、templates/http-response.example.md）。【待验证】
- 已过期：410，userinfo 写 expire（templates）。【待验证】
- 超配额：403，userinfo 反映用量。【待验证】
- 渲染失败/泄露断言命中：500 通用错误，不回显敏感内容，服务端告警（templates）。【待验证】
- 比对用 hmac.compare_digest 常量时间（参考 friendsd.py:440）。【参考提炼】
- 错误响应绝不回显 token/节点凭据/内部路径；访问日志只记 hash 前缀或内部 id（playbook/03）。【待验证】
- 订阅输出路径置于 /api 前缀下以继承 no-store 并避开 SPA fallback（见 2.3）。【我方已验证】+【待验证】

---

## 5. Token 生命周期

均为【待验证】契约（playbook/03、roadmap/01），参考思想标【参考提炼】。

- 签发：secrets.token_urlsafe(32)（32 字节=256bit，≥128bit 要求）。明文 token 只在签发响应返回一次，此后任何接口/日志/页面不回显。【待验证】
- 存储：只存 SHA-256 hash + 元数据（第 3.1）；0600 意图；不入 localStorage/sessionStorage。【待验证】
- 路径段：token 放 URL 路径段（/api/sub/<token>），**不用 query**（防日志/Referer 泄露）。【待验证】+【参考提炼】（knowledge/05 token 入路径防扫描）
- 使用：每次 GET/HEAD 渲染后做泄露断言（回家凭据/external-controller/secret/上游 provider token/其他用户线路），命中拒绝发布并告警。【待验证】
- 轮换：签新 token → 旧 token 进宽限期（graceSeconds 可配）→ 经既有可信通道通知（不公开发）→ 宽限结束自动撤销旧 → 记审计。【待验证】
- 撤销：标记 revoked_at（保留元数据）→ 立即 404/410 → 删渲染缓存与凭据副本 → 记审计。撤销只影响该 token，不影响其他。【待验证】
- 有效期：expires_at=0 长期；否则 unix 秒，到期 410 且 userinfo 写 expire。【待验证】
- 配额：按 token 累计上下行，超额 403/降级（需先有流量统计，MVP 占位）。【待验证】
- 参考思想（不可复制实现）：按人签发每人一链接+独立凭据，撤销只影响他自己；撤销=真断连（节点侧重写 inbound users，链接立刻 410 + 凭据短时失效），而非仅换 token（对方已存配置仍可用）。本方案 MVP 在面板输出侧做撤销即 404/410；节点侧凭据联动失效放 P1（需 sing-box/节点改造）。【参考提炼】（knowledge/06、friendsd.py:93-187）

---

## 6. 渲染器与多客户端兼容

### 6.1 MVP 决策

- MVP 只做 Clash YAML 输出，覆盖 Clash Verge Rev / OpenClash / Stash；**不做 base64 输出**；sing-box JSON remote profile 放 P2。【待验证】（roadmap/01 决策）
- 渲染器复用 YamlService.load / validate_references / sha256（yaml_service.py:47-58/170-237/67-71）做主配置解析与引用校验；但**对外视图应新建纯 dict → YAML(typ="safe") dump**，不继承主配置的注释/格式（主配置用 ruamel RoundTrip，yaml_service.py:40-45）。泄露断言在 dump 后对 bytes 做。【我方已验证】（现有能力）+【待验证】（新渲染路径）

### 6.2 客户端差异矩阵

| 客户端 | 订阅格式 | 更新行为 | 关键兼容点 | 徽章 |
|---|---|---|---|---|
| Clash Verge Rev | Clash YAML | 手动/定时 | 只校验 200 + 含 proxies/proxy-providers 键；不查 Content-Type；不解 base64（base64 被拒收）；接受 x-amz-meta-subscription-userinfo 别名 | 【待验证】（roadmap/01） |
| OpenClash | Clash YAML | update_interval（分钟） | 解析 subscription-userinfo（lua）；update_interval 单位分钟 | 【待验证】 |
| Stash | Clash YAML | 默认 12h，优先发 HEAD | 必须正确响应 HEAD；不支持 2022-blake3-chacha20-poly1305；REALITY 需 iOS 3.4.0+；Stash≠mihomo 内核，按每代理 benchmark-url 探测 | 【待验证】+【参考提炼】（templates/README、knowledge/05） |
| sing-box 官方 | JSON remote profile | 默认 60min | sing-box://import-remote-profile；P2 才做 | 【待验证】 |

### 6.3 字段映射表（主配置 → 对外 Clash YAML 视图）

| 主配置字段 | 自用视图 | 朋友视图 | 说明 |
|---|---|---|---|
| proxies（自建节点，含回家 socks5+TLS） | 输出（回家节点凭据仅自用） | **剔除回家节点**；仅白名单线路 id 对应的解析后节点 | 朋友视图不含回家凭据 |
| proxy-providers（上游订阅 URL+token） | 可保留 URL（自用可信） | **剔除 URL/token**，只输出解析后的节点 | 防上游凭据外泄 |
| external-controller / secret | **剔除** | **剔除** | 任何对外视图都不输出管理面 |
| proxy-groups | 输出 | 输出（仅引用白名单节点） | 组内成员须与可见节点一致 |
| rules / rule-providers | 输出 | 输出（裁剪指向不可见节点的规则） | 防引用悬空 |
| dns / general（port/socks-port/mode/log-level） | 输出 | 输出 | 骨架见 templates/clash-subscription.example.yaml |

骨架示例（脱敏，源自 templates/subscription/clash-subscription.example.yaml）：port 7890 / socks-port 7891 / allow-lan false / mode rule / log-level info；示例节点 ss2022(192.0.2.10:18388)、vless-reality(198.51.100.20:18443, uuid 00000000-0000-4000-8000-000000000000)、hysteria2(203.0.113.30:443, sni node-a.example.com)；PROXY select 组；MATCH,PROXY。**对外视图不输出 external-controller/secret**。【待验证】（模板为我方脱敏示例）

### 6.4 参考思想（不可复制）

- 多客户端同源同序翻译防漂移；auto 变体独立文件名 + Content-Disposition inline; filename 定配置名；Stash 门组第一成员 type:direct + benchmark-url=https://www.google.com/generate_204（HTTPS 防污染假阳性，apple.com 墙内可达会误判 DIRECT 活）。【参考提炼】（knowledge/05）
- 渲染产物原子写 + version 单调 + mtime/hash 判重（内容未变不重写不重载）。【参考提炼】（knowledge/05、templates/README）

---

## 7. Subscription-Userinfo 响应头

契约（templates/http-response.example.md、roadmap/01）【待验证】，解析复用【我方已验证】。

- 头格式：subscription-userinfo: upload=<bytes>; download=<bytes>; total=<bytes>; expire=<unix秒>。【待验证】
- 单位：upload/download/total 为 bytes；expire 为 unix 秒；expire=0 表示长期。【待验证】
- 无统计时给全 0，**不省略该头**（部分客户端省略会显示异常）。MVP 无流量统计 ⇒ upload=0; download=0; total=0; expire=<expires_at 或 0>。【待验证】
- 别名：同时提供 x-amz-meta-subscription-userinfo（Clash Verge Rev 接受）。【待验证】
- HEAD 支持：HEAD 与 GET 头一致，body 空（Stash 优先 HEAD）。【待验证】
- 缓存协商：ETag（渲染 body 的 sha256）、Last-Modified（http-date）、If-None-Match 命中 → 304 无 body。【待验证】
- Cache-Control: no-store（/api 前缀自动继承，main.py:88-89）。【我方已验证】+【待验证】
- Content-Type: application/yaml; charset=utf-8；Content-Disposition: attachment; filename="subscription.yaml"（templates）。【待验证】
- 解析复用：parse_subscription_userinfo(value)（subscription_usage.py:20）用于**消费上游** userinfo；输出侧自行构造该头。usage_payload（subscription_usage.py:53-95）的 used=upload+download、remaining=max(0,total-used)、expire>0 才转 datetime 的逻辑可作输出侧计算参考。【我方已验证】
- 参考思想：朋友版刻意不发主人用量头（防泄露主人配额）；profile-update-interval 头建议更新周期。【参考提炼】（knowledge/05）

---

## 8. 自用版与朋友版隔离

契约【待验证】（roadmap/01、playbook/03），参考思想【参考提炼】（knowledge/06、friendsd.py）。

- 朋友视图只发**线路 id 白名单**对应的解析后节点；凭据隔离 0600；管理面字段（external-controller/secret）一律剔除；上游订阅 URL/token 剔除。【待验证】
- 渲染后泄露断言（每次输出）：命中回家节点凭据 / external-controller / secret / 上游 provider token / 其他用户线路 ⇒ 拒绝发布 + 服务端告警。【待验证】
- 朋友 token 与自用 token 独立签发、独立撤销；朋友外泄 ≠ 自用外泄。【待验证】+【参考提炼】（knowledge/06 独立 friends-* inbound）
- AI 出口护栏（参考思想，P1 节点侧）：朋友 AI 流量不得走主人住宅 IP（烧带宽 + 风控关联）；route.rules 最前插 {inbound:[friends-*], outbound:direct}，后续加分流规则须确认护栏仍第一条。本方案 MVP 仅在视图侧隔离，节点侧护栏放 P1。【参考提炼】（knowledge/06、friendsd.py）
- 按人配额计数（参考思想，P1/P2）：fwmark 每人一个（0x1001 起，一经分配不变），mangle 表增量增删不 flush，CONNMARK save，低 16 位掩码避开 tailscale mark；只记字节不记目的地；报累计值；计费×2 口径（朋友↔本机字节×2≈VPS 实际计费）。MVP 面板侧 quota_used_bytes 占位 0。【参考提炼】（knowledge/06、friendsd.py:53/321）
- 撤销=真断连（参考）：节点侧每 60s 拉取重写 inbound users，链接立刻 410 + 凭据≤60s 失效；仅换 token 对方已存配置照常能用。MVP 面板输出侧撤销即 404/410；节点侧联动 P1。【参考提炼】（knowledge/06）
- 失效响应分对象（参考）：浏览器 410 设计页 noindex；客户端纯文本 410（客户端只看状态码）。【参考提炼】（friendsd.py:457-461）

---

## 9. 复用点（精确签名，接入而不重写）

以下签名均【我方已验证】（本会话读源码）。FastAPI + Vue3 + Lucky 架构不变。【待验证】（接入方式）

### 9.1 后端

- source_store.SourceStore._write(self, records: list[SourceRecord]) -> None（source_store.py:153）：O_EXCL 0o600 + fsync + os.replace + chmod 原子写范式 ⇒ token 存储直接照此实现（新 SubscriptionTokenStore._write）。【我方已验证】
- source_store.SENSITIVE_FIELDS = {"username","password"}（source_store.py:16）、SourceRecord.safe_data()（:39）⇒ 凭据剔除范式参考。【我方已验证】
- source_store.ProbeStore（:281）：fingerprint(record)（:286）、issue(record)（:295）、consume(token, record)（:305，compare_digest 一次性）、cleanup()（:310）⇒ 一次性 token 消费/常量时间比对范式参考。【我方已验证】
- audit.AuditStore(data_dir: Path)（audit.py:17）；record(*, source_id, username, action, path, before_hash, after_hash, backup_path, details)（:71）；record_event(*, source_id, action, path, status, message, details=None)（:94）；list_recent（:104）；set_limit（:163）；clear（:179）⇒ 订阅审计直接调 record_event。【我方已验证】
- save_service.SaveService(storage, audit)（save_service.py:84）；create_preview（:94）；commit(record, *, username)（:206，三态事务 unchanged/restored/recovery_failed）；preview_store（:54，TTL900 绑 scope）⇒ 订阅视图发布若需"预览→确认"可参考三态回滚与原子写；但订阅输出是只读渲染，不需要写主配置。【我方已验证】
- yaml_service.YamlService：load(raw: bytes)（:47）、dump_candidate(document)（:60）、sha256(raw)（:67）、validate_references(document)（:170）、full_diff（:239）、summary（:262）⇒ 渲染器复用 load/validate_references/sha256；对外 dump 新建 safe 路径。【我方已验证】
- subscription_usage.parse_subscription_userinfo(value: str|None) -> dict[str,int]|None（:20）、content_disposition_title（:43）、usage_payload(provider_name, headers, *, fetched_at)（:53）、SubscriptionUsageService(transport=None)（:98）.get_usage(root, *, cache_key, force=False)（:102）⇒ userinfo 解析/计算复用。【我方已验证】
- subscription_nodes.SubscriptionNodesService(transport=None)（:71）.get_nodes(document_root, *, cache_key, force=False)（:75）、parse_subscription_nodes(raw: bytes)（:56）⇒ 朋友视图"只输出解析后节点"可复用节点解析（但输出侧需重新渲染为 YAML，而非返回 {name,type}）。【我方已验证】
- publication.PublicationVerifier(base_url)（:18）.compare(*, filename, current)（:25）⇒ 迁移期"私有订阅产物 vs 主配置"哈希核对可参考；公开文件核对仍用现有。【我方已验证】
- storage.registry.build_storage_from_source(source, *, include_config_directory=True)（registry.py:50）、build_primary_storage(settings)（:14）⇒ 读主配置复用。【我方已验证】
- storage.mounted.MountedFilesystemStorage(root, display_name)（mounted.py:11）：write_bytes（:88，O_EXCL/O_TRUNC 0o600+fsync）、move（:131，overwrite 保留目标 mode）⇒ 渲染缓存落盘复用，注意权限现实（2.6）。【我方已验证】
- routes.require_internal_request(request)（routes.py:107）⇒ **改造为 require_admin 后**供管理端点 Depends 复用（12 §5.1；旧头降级为 CSRF 辅助，不再是安全边界）。【我方已验证】（现状）+【待验证】（改造）
- routes.requested_context(settings, source_id=None, path=None)（routes.py:120）⇒ 管理端点解析来源/存储复用。【我方已验证】
- browser_session：COOKIE_NAME="fixcloud_session"（:12）、scope_for_token（:27）、bind（:39）、current_scope（:49）、cleanup_loop（:90）⇒ 订阅输出须**绕过** bind（2.3），不新建会话目录。【我方已验证】
- settings.Settings（settings.py:8）+ get_settings()（:33）⇒ 新增订阅配置项（如 subscription_enabled、subscription_rotate_grace_seconds、subscription_cache_ttl_seconds）。【我方已验证】+【待验证】

建议新增模块（文件名仅建议，实现时核实）：backend/app/services/subscription_tokens.py、backend/app/services/subscription_publisher.py、backend/app/api/routes_subscription.py（或并入 routes.py）。【待验证】（roadmap/01）

### 9.2 前端

- stores/app.ts useAppStore.request(path, init)（:262-275）：非 GET 自动加 X-FixCloud-Request:1、credentials same-origin、cache no-store、!ok→ApiRequestError ⇒ 订阅管理 API 走此方法自动带内网标记。【我方已验证】
- notify（:276）、busy 锁范式（saving/loading/testing）⇒ 异步动作 busy + 防重复复用。【我方已验证】
- persistDraft（:337-354）注释"Full YAML may contain credentials; never write it to browser storage" ⇒ token 明文绝不入 sessionStorage/localStorage/persistDraft。【我方已验证】
- router/index.ts（42 行 createWebHashHistory）⇒ 新增 /subscription-publish 路由 + meta.title。【我方已验证】
- AppShell.vue navItems（:35-42）/mobileNavItems（:43-48）/isMobileNavActive（:50-53）⇒ 桌面加导航项（lucide KeyRound/Send），移动归 /more（数组加新路径）。【我方已验证】
- 组件 GroupCard/ios-card、confirmDialog（AppDialogHost）、SettingsRow ⇒ 订阅发布页循 SettingsView/SourcesView 范式。【我方已验证】

---

## 10. 前端页面与交互

遵循 design/02 当前生效视觉层 visual-refresh.css（Nothing 风单色红 --nd-accent #d71921；main.ts:13-14 后 import 覆盖 style.css）。【我方已验证】

- 页面结构：overview（订阅发布总览：已签发数/活跃数/最近拉取）→ list（token 列表：label/scope/状态/到期/最近使用）→ detail（单 token：元数据/撤销/轮换/泄露断言状态）。【待验证】
- 路由：/subscription-publish（list），/subscription-publish/:id（detail）；桌面 navItems 加「订阅发布」，移动归 /more。【待验证】+【我方已验证】（导航范式）
- dirty 才显示未保存：沿用 dirtyCount>0 才显示 SaveBar/未保存指示（stores/app.ts:245）。订阅管理多为即时动作（签发/撤销），表单（label/note/到期）编辑才产生 dirty。【我方已验证】+【待验证】
- 保存进 Diff：若订阅视图发布涉及主配置变更，走 createPreview→DiffModal→commitPreview（不静默写）。纯 token 管理动作（签发/撤销）经 confirmDialog 二次确认即可，不涉及主配置 Diff。【我方已验证】（现有流）+【待验证】
- 异步动作 busy + 防重复：签发/撤销/轮换按钮 busy 锁 + disabled（沿用 saving/testing 范式）。【我方已验证】+【待验证】
- 凭据不入 localStorage：token 明文绝不写 sessionStorage/localStorage/persistDraft（stores/app.ts:337-354 边界）。【我方已验证】
- 订阅链接只在签发时完整显示一次：签发响应含明文 token，前端在签发成功模态中完整展示一次（含复制按钮，三级兜底 Clipboard API→execCommand→prompt，参考 knowledge/05），关闭后任何页面/接口不再回显明文；列表/详情只显示内部 id 与掩码。【待验证】+【参考提炼】
- 撤销二次确认：confirmDialog（非 native），明确"撤销后该链接立即失效且不可恢复"。【待验证】+【我方已验证】（组件）
- 视觉一致：用 visual-refresh.css 变量，避免残留旧蓝岛（design/07 待决策项）；触达≥44px；danger 用统一 accent。【我方已验证】（design/02、design/07）

---

## 11. 分阶段实施步骤

每步含改动文件、验收断言、可回滚点。均为【待验证】（尚未实施）。本轮只产出方案，不改生产。

### P0-a 只读盘点（无代码改动）
- 动作：查清谁在消费公开 URL（客户端/设备/人）、各客户端版本、主配置订阅字段清单。
- 改动文件：无（只读）。
- 验收断言：产出消费者清单（设备+客户端+版本+更新周期）；确认回家节点/上游 token/external-controller 在公开文件中的具体位置。
- 可回滚点：纯只读，无副作用。
- 需用户授权：访问客户端设备/查日志属用户侧动作。

### P0-b Token 存储 + 管理 API（内网）
- **前置依赖**：12 §8 Phase 0 的管理鉴权（require_admin）必须已就位；本步所有管理端点直接依赖 require_admin，不得先用旧头上线再补。
- 改动文件：backend/app/services/subscription_tokens.py（新）、backend/app/api/routes_subscription.py（新）或 routes.py、backend/app/core/settings.py（新配置项）、backend/tests/test_subscription_tokens.py（新）。
- 验收断言：签发返回明文一次；存储只含 hash；GET 列表不回显明文；撤销后标记 revoked_at；审计 record_event 不含明文；单测覆盖 O_EXCL 原子写/常量时间比对/撤销/轮换宽限。
- 可回滚点：新模块独立，删除路由注册即回滚；token 文件可保留（不影响现有）。

### P0-c Clash YAML 渲染器 + 泄露断言 + HEAD/ETag
- 改动文件：backend/app/services/subscription_publisher.py（新）、backend/app/api/routes_subscription.py（输出端点）、backend/app/main.py（中间件对 /api/sub 跳过会话绑定）、backend/tests/test_subscription_publisher.py（新）。
- 验收断言：GET/HEAD /api/sub/<token> 200 + YAML 含 proxies/proxy-providers；HEAD body 空；ETag/If-None-Match→304；Cache-Control no-store；userinfo 全 0 不省略；泄露断言命中→500+告警；三客户端实测（第 13 章）。
- 可回滚点：输出端点独立路由，移除即回滚；中间件改动可还原。

### P0-d 自用/朋友双视图 + 配额占位
- 改动文件：subscription_publisher.py（scope 分支）、subscription_tokens.py（allowed_line_ids）、测试。
- 验收断言：朋友视图断言无回家节点/无 external-controller/secret/无上游 URL token/无其他用户线路；自用视图全量；quota_used_bytes 占位 0。
- 可回滚点：scope 分支可关闭朋友签发。

### P0-e 客户端切换 + 关闭公开出口（需用户单独授权）
- 动作：客户端逐个切到私有订阅 URL → 观察一个更新周期 → 关闭公开 file 出口。
- 改动文件：生产 Lucky/文件服务配置（**属生产变更，需用户当次明确授权**）。
- 验收断言：公开 URL 404/403；各客户端仍正常更新；私有订阅拉取成功。
- 可回滚点：恢复公开出口（迁移期双出口并行，见第 12 章）。

---

## 12. 迁移步骤（公开 file URL → 私有订阅）

原则：**先查清消费者，再关闭公开出口**；不得用"关闭公开文件"代替"先查清消费者"（roadmap/01 禁止）。【待验证】

1. 排查谁在消费公开 URL（P0-a）：列出所有客户端/设备/人 + 版本 + 更新周期。未查清前不关闭。【待验证】
2. 并行期双出口：私有订阅端点上线（P0-b/c/d），公开 file URL 暂保留。两出口同时可用，互不影响。【待验证】
3. 客户端逐个切换：按消费者清单逐台把订阅 URL 改为 http(s)://<NAS_LAN_IP>:8787/api/sub/<EXAMPLE_SUB_TOKEN>（或经 Lucky 反代的私有域名）；每切一台观察一个更新周期确认正常。【待验证】
4. 关闭公开出口：全部消费者切换并稳定后，关闭 <PUBLIC_FILE_DOMAIN>/FixCloud.yaml 公开访问（404/403）。**此步属生产变更，需用户单独授权。**【待验证】
5. 回滚预案：迁移期任一客户端异常，恢复公开出口（双出口并行期天然可回滚）；关闭后若需回滚，重新开放公开 URL（需用户授权）并排查私有订阅问题。【待验证】

需用户单独授权的步骤：
- 步骤 4 关闭公开出口（改 Lucky/文件服务/防火墙）。
- 步骤 5 回滚中重新开放公开出口。
- 任何 NAS/VPS/Lucky 配置修改、重启、部署。
- 宿主侧收紧 /data 或 token 文件权限（2.6/3.1）。
- 服务商 API 白名单添加 NAS 出口 IPv4（需本人控制台，交接报告 P0 前置）。

公开文件处置三选项（roadmap/01）：
- A（推荐）：自建节点与订阅凭据完全不进 FixCloud.yaml，公开文件只留无凭据公共部分或关闭公开访问（不需改 Lucky）。【待验证】
- B：公开文件加鉴权（Lucky 反代 + token/BasicAuth，属生产变更）。【待验证】
- C：保留公开文件但移除全部凭据。【待验证】
- 本方案目标=私有订阅取代公开访问，倾向 A + 关闭公开出口；具体由用户决策（第 14 章）。

---

## 13. 验收标准

区分"构建通过"与"交互验收"（AGENTS.md、skill beam-web-product-guidelines：构建通过≠交互验收）。【我方已验证】（原则）

### 13.1 构建/单测门（可执行命令）

- 后端测试：cd backend && python -m pytest tests/ -q（范式 tmp_path + Settings(storage_backend="local") + dependency_overrides + httpx.MockTransport，见 test_subscription_usage.py / test_api.py）。断言：新增 subscription_tokens/publisher 测试全绿；现有 14 个测试文件不回归。【我方已验证】（范式）+【待验证】（新测试）
- 前端类型检查：cd frontend && npm run typecheck（vue-tsc -b）。【我方已验证】（package scripts）
- 前端单测：npm run test（vitest run）。【待验证】
- 生产构建：npm run build（vue-tsc -b && vite build）。断言：构建成功≠交互验收。【我方已验证】
- 脱敏门：`python3 tools/verify-sanitized.py panels/fixcloud-panel --json reports/verify-subscription.json`（**该工具按目录 os.walk，传单个文件路径会 scanned_files=0，必须传目录**）。断言：residual_findings=0、exit 0。源码仓库侧另跑 `python3 tools/verify-sanitized.py .`，其中 `shipped-asset-private-ip` 规则专门禁止 frontend/src 与 frontend/public 出现真实内网地址（会随 dist 分发到浏览器）。【我方已验证】
- gitleaks：gitleaks dir/git --config tools/gitleaks-repo.toml --redact。断言：无泄露。【我方已验证】（交接报告门）

### 13.2 交互验收（三客户端实测矩阵）

| 客户端 | 实测动作 | 通过断言 |
|---|---|---|
| Clash Verge Rev | 导入私有订阅 URL，更新 | 200 + 含 proxies/proxy-providers；节点可用；userinfo 显示（含 x-amz-meta 别名）；base64 不被误用 |
| OpenClash | 配置订阅 URL + update_interval | 解析 userinfo（lua）；定时更新成功；流量显示 |
| Stash | 添加订阅（优先 HEAD） | HEAD 200 头正确；GET YAML 可用；REALITY 节点 iOS 3.4.0+ 可用；不支持的 cipher 不出现 |

每客户端须实机/真实客户端验证，记录版本；一次成功≠全部场景通过（AGENTS.md）。【待验证】

### 13.3 泄露断言（自动化 + 人工）

- 对朋友视图渲染 bytes 断言不含：回家节点凭据、external-controller、secret、上游 provider URL/token、其他用户线路。命中→拒绝发布+告警。【待验证】
- 对自用视图断言不含：external-controller、secret、上游 provider token（自用可含回家节点凭据，但管理面仍剔除）。【待验证】
- 错误响应/日志/审计断言不含明文 token/凭据。【待验证】

### 13.4 权限断言

- token 文件落盘后实测宿主侧权限（stat），确认是否被 QNAP ACL 覆盖为 0770（2.6）；若组可读则需用户授权收紧。断言：意图 0600，实测记录在案。【我方已验证】（ACL 现实）+【待验证】（实测）
- 渲染缓存文件权限同上。【待验证】
- 容器 read_only:true / tmpfs /tmp 32m / cap_drop ALL / no-new-privileges 不回归（docker-compose.yml）。【生产配置】

### 13.5 API 校验（只读探测，授权后）

- GET /api/health 200 ok。【我方已验证】（本会话已探测）
- 管理端点缺管理员会话 cookie → 403；**仅带 x-fixcloud-request:1 而无管理员 cookie 也必须 403**（12 §5.1，P0-3 回归断言）。【待验证】
- 订阅输出端点不带该头仍可 200（token 正确）；错误 token→404/410。【待验证】
- HEAD 与 GET 头一致；If-None-Match→304。【待验证】

### 13.6 验收顺序（AGENTS.md）

类型检查→前端单测→生产构建→后端测试→API 校验→授权部署→容器健康→Mac Safari 目视→暗色→响应式→控制台→各态→数据 hash 核对。【我方已验证】

---

## 14. 风险与未决问题

- 【我方已验证】安全头中间件对每个请求创建会话目录（main.py:58-64），订阅客户端每次拉取都会新建一个目录，必须让 /api/sub 绕过会话绑定。**规模修正**：经 NAS docker.sock 实测 temporary-sessions 为 2968 个目录且 `find -mtime +1` 为 0 → TTL 24h 清理存活、规模**有界**（约 2880/天来自 healthcheck 每 30s 无 cookie 探测），旧表述「累积约 2911／无限增长」【已过时】。真隐患是 `cleanup_loop` 无 try/except（browser_session.py:90-96），一次 PermissionError 会永久杀死清理任务 → 才可能无限增长。修法待实现验证。
- 【我方已验证】/data 实测 0770（QNAP ACL 覆盖 0o600），token 文件即使容器内 chmod 0600 也可能宿主侧组可读。需用户在宿主侧收紧（生产变更，单独授权）。
- 【我方已验证】require_internal_request 仅同源标记头无 IP 白名单，管理端点边界=内网可达性。若面板端口暴露公网则管理面可被伪造头访问。需确认 PANEL_BIND_IP 仅内网（.env.example 示例 192.0.2.10，生产实际值未展开）。
- 【待验证】谁在消费公开 URL 未查清——关闭公开出口前必须完成 P0-a，否则断网。
- 【待验证】流量统计缺失——MVP 配额占位 0，真正按 token 计费需节点侧 fwmark 统计（P1/P2）。
- 【待验证】撤销=真断连需节点侧联动（重写 inbound users），MVP 仅面板输出侧 404/410；对方已存配置在节点侧凭据失效前仍可用。
- 【待验证】Stash cipher/REALITY 版本兼容需实机确认（不支持 2022-blake3-chacha20-poly1305，REALITY iOS 3.4.0+）。
- 【待验证】公开文件处置 A/B/C 由用户决策；本方案倾向 A+关闭。
- 【待验证】服务商 API 白名单（NAS 出口 IPv4）需本人控制台添加，否则 /api/vps/usage 持续 available:false（交接报告根因）。
- 【已过时】交接报告"源码无 .git"已被推翻（现 git 仓库 HEAD 9983f52）。
- 【待验证】design/07 六项 UI 不一致（残留旧蓝/暗色纯黑/小触达/双红/SaveBar）未决策，新页面须避免引入同类问题。

---

## 15. 禁止事项

- 禁止本轮修改任何生产订阅/Lucky/NAS/VPS 配置、重启、部署、防火墙修改、执行订阅迁移（任务硬约束）。【我方已验证】
- 禁止修改源码仓库任何文件；本方案唯一允许写入的文件是本 spec。【我方已验证】
- 禁止 token 明文进入日志/审计/前端存储（localStorage/sessionStorage）/入库文档；明文只签发时返回一次。【待验证】（契约）
- 禁止朋友视图含回家节点凭据/管理面字段（external-controller/secret）/上游 URL token/其他用户线路。【待验证】
- 禁止用"关闭公开文件"代替"先查清消费者"。【待验证】（roadmap/01）
- 禁止订阅输出做 base64（MVP 仅 Clash YAML）。【待验证】
- 禁止 query 传 token；禁止错误响应回显 token/凭据/内部路径。【待验证】（playbook/03）
- 禁止复制参考项目源码/配置/UI/真实值（licenseInfo=null）；禁止执行参考项目任何脚本；禁止连接参考项目任何服务器。【我方已验证】（AGENTS.md、任务约束）
- 禁止文档出现真实凭据/IP/域名/邮箱/手机号/订阅 token/UUID；统一占位符与示例值。【我方已验证】（任务约束）
- 禁止把"构建通过/接口返回成功/文件存在"当作实机或界面验收完成。【我方已验证】（AGENTS.md、skill）
