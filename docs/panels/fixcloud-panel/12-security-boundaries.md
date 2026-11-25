# FixCloud Panel 安全边界与加固方案

核实时间：2026-11-25（源码只读核实 + 生产只读探测，未做任何生产写入）。
源码仓库：/Users/beamjason/Documents/BeamNat/fixcloud-panel（git 单提交 15c9fe3，remote Private，工作树干净）。
生产容器：fixcloud-panel（8787->8080，bridge 网络 fixcloudpanel_fixcloud）。
徽章约定：【我方已验证】=本次实时读源码/只读探测证实；【生产配置】=生产 inspect/文件实测；【参考提炼】=来自 knowledge/参考项目，非我方环境；【待验证】=尚未证实；【已过时】=旧报告结论被本次推翻。
占位符：<NAS_LAN_IP> <NAS_LAN_SUBNET> <PUBLIC_FILE_DOMAIN> <HOME_DOMAIN> <NAS_EGRESS_IPV4>；示例值仅用 example.com / 192.0.2.10 / 198.51.100.20 / 203.0.113.30。

---

## 1. 威胁模型

面板历史决策为"无账号密码登录，仅家庭内网 + 自有 SOCKS5 通道访问"（README.md:32）【我方已验证】。该决策把"内网可达"当作信任边界，但内网并非单一可信主体。攻击者能力假设：

| 攻击者 | 能力 | 对面板的现实威胁 |
|---|---|---|
| 同局域网设备（家人手机/电脑/访客设备） | 可直连 <NAS_LAN_IP>:8787（端口绑 0.0.0.0）【生产配置】 | 一条 GET 即可读全量凭据 YAML；带 x-fixcloud-request:1 头即可写配置/删文件/清审计 |
| 被入侵的 IoT（摄像头/音箱/ESP 设备） | 同上，且常驻、无人察觉 | 与 LAN 设备同等能力；可静默外传订阅凭据、篡改代理配置实现流量劫持 |
| 公网扫描者 | 可访问 https://<PUBLIC_FILE_DOMAIN>/（Lucky 投递）【我方已验证】 | 目录索引 200（683741B、167 条目）可枚举；FixCloud.yaml 与第二个 YAML 均无鉴权 200，直接拿到回家节点凭据、provider query token、external-controller secret |
| 拿到订阅链接的第三方 | 持有含 token 的 provider URL | 可消耗订阅流量、读取节点列表；若 URL 来自公开 YAML 则与公网扫描者重合 |
| 拿到面板访问权的家庭成员 | 浏览器正常使用 | 误操作/恶意保存可改生产代理配置；writeEnabled=true 放大影响；审计 username 固定"内网访问"无法区分具体人 |

关键判断【我方已验证】：
- 路由器 op 的 uci firewall 无 8787/fixcloud DNAT 规则 → 面板端口未经路由器转发 WAN；公网暴露面主要是 Lucky 投递的公开文件域，而非 8787 本身。（Lucky 自身是否有 8787 转发规则【待验证】）
- "内网可信"假设不成立：LAN 内任何设备（含被入侵 IoT）都能零鉴权读凭据、带头写配置。header 与 cookie 都不是身份边界（见 §2）。

---

## 2. 当前安全边界清单

| # | 边界 | 实现位置（文件:行号） | 是否足够 | 证据/徽章 |
|---|---|---|---|---|
| B1 | 非 GET 路由同源标记 | backend/app/api/routes.py:107-109 require_internal_request 仅查 header x-fixcloud-request=="1"，否则 403 | 不足：客户端可任意伪造该头；只防浏览器跨站 CSRF，不防 LAN 直连 | 【我方已验证】POST /api/config/save 无头→403（loopback 与 LAN 双测）；带头即通过 |
| B2 | CORS | backend/app/main.py:44-50 allow_origins 仅 http://localhost:5173 / http://127.0.0.1:5173，allow_credentials:true，allow_headers:["*"] | 部分：限制浏览器跨源，但对非浏览器客户端无效 | 【我方已验证】 |
| B3 | cookie 会话 | main.py:54-94 每请求读 fixcloud_session；browser_session.py:19-20 valid_token 仅验格式 ^[A-Za-z0-9_-]{43}$，不验服务端注册 | 不足：cookie 是会话隔离键，不是认证；任何人可自选合法格式 token 进入自己的 scope | 【我方已验证】set_cookie httponly:true samesite:strict secure:false（main.py:70-78） |
| B4 | 安全响应头/CSP | main.py:79-87 nosniff、X-Frame-Options SAMEORIGIN、Referrer-Policy no-referrer、CSP default-src 'self'; script-src 'self'; img-src 'self' data: https: http:; style-src 'self' 'unsafe-inline' | 基本足够：script-src 'self' 防注入；img-src 宽放但图标走后端代取 | 【我方已验证】 |
| B5 | 静态资源挂载 | main.py:97-99 frontend_dist 存在则 app.mount("/", StaticFiles(html=True))，dist 内一切文件无鉴权 GET | 不足：dist 内容即暴露面；当前生产 dist 无 demo（404），但仓库 public/demo 含真实值，下次构建将进 dist | 【我方已验证】容器 find 无 nothing-full.html；vite.config.ts 无 publicDir 排除 |
| B6 | 来源凭据后端隔离 | source_store.py:16 SENSITIVE_FIELDS={username,password}；safe_data:39-51 仅剔这两键 | 不足：config 内其他敏感值（URL 内嵌 token 等）仍返前端；且 GET /config 的 YAML 正文完全未掩码 | 【我方已验证】yaml_service.py:73-80 to_safe_data 仅 CommentedMap→dict，零掩码 |
| B7 | YAML 读取鉴权 | routes.py:698 GET /config、:732 GET /config/raw 无任何鉴权依赖 | 严重不足：零鉴权返回全量凭据 | 【我方已验证】LAN 设备 GET /api/config/raw→200 21399B 原文 |
| B8 | 写闸 writeEnabled | routes.py:929-930 save 前查 settings.write_enabled；settings.py:21 默认 False；compose:16 默认 false | 部分：生产 .env WRITE_ENABLED=true 覆盖；写闸只挡"功能开关"，不挡"身份" | 【生产配置】inspect env WRITE_ENABLED=true |
| B9 | probeToken/previewToken | source_store.py:281-316 ProbeStore TTL600s 一次性消费；save_service.py:40-45 take 校验 session_scope | 部分：防"未探测直接保存"/跨会话消费，但 scope 依赖 cookie 保密，cookie 可伪造格式 → 非身份鉴权 | 【我方已验证】 |
| B10 | 路径穿越防护 | mounted.py:18-24 _resolve resolve+parents 校验；routes.py:137-151 is_editable_yaml_path 仅配置目录直属 YAML | 足够（就路径穿越而言） | 【我方已验证】 |
| B11 | 图标代取 SSRF 防护 | icon_cache.py:59-77 _validate_public_url 仅 http/https，解析 IP 须 is_global 或 198.18.0.0/15；每跳重定向重验（159-183，≤4 跳） | 基本足够，残留 DNS rebinding TOCTOU（校验与 httpx 连接分别解析） | 【我方已验证】 |
| B12 | 容器最小权限 | compose:36 read_only:true、:38 tmpfs /tmp 32m mode1777、:40 no-new-privileges、:42 cap_drop ALL、:9 user 1000:100 | 足够（容器层）；但 /data 与 SMB bind 均 RW，宿主 ACL 0770 削弱文件层 | 【生产配置】inspect ReadOnly=true CapDrop=[ALL] SecurityOpt=[no-new-privileges:true] User=1000:100 |
| B13 | /data 文件权限 | source_store.py:168 O_EXCL 0o600 + :175 os.chmod 0o600（代码意图） | 不足：QNAP 共享 ACL 覆盖 → 实际 0770，everyone 组可读 sources.json 明文凭据 | 【生产配置】容器内 stat data/sources.json/sessions 均 0770；宿主 sources.json 0770 516B |
| B14 | 审计 | audit.py:71-92 record 仅 uploaded-files 写 session_scope；:99 username 固定"内网访问"；:179-185 clear 全表 DELETE 无 scope 过滤；routes.py:1187-1192 DELETE /logs 故意不审计 | 不足：无法区分操作者；清审计本身不留痕且无鉴权（仅 B1 头） | 【我方已验证】 |
| B15 | 公开文件投递 | publication.py:25-91 compare 外连公开 URL；routes.py:314/349 GET /publication/status 返回真实 publishedUrl | 不足：公开域无鉴权 + 目录索引可枚举 | 【我方已验证】https://<PUBLIC_FILE_DOMAIN>/ 索引 200；FixCloud.yaml 200 20893B；oixCloud.yaml 200 24012B |
| B16 | 会话清理 | browser_session.py:65-87 cleanup_expired 仅删 64hex 名/非 symlink/mtime<cutoff；:90-96 cleanup_loop 无 try/except | 部分：TTL24h 有效、规模有界；但一次 PermissionError 即永久杀死清理任务 | 【生产配置】temporary-sessions 2936 个，oldest 24.8h，>24h 仅 100 → 清理存活 |
| B17 | 错误响应 | routes.py:259-260 GET /health 503 detail 含 {exc} 原文；smb.py:81-97 已映射通用中文消息 | 部分：health 异常文本可能带来源主机名/路径 | 【我方已验证】 |
| B18 | 前端凭据存储 | app.ts:339-341 rawYamlDraft 明确不入存储；:353 operations 写 sessionStorage（可含用户输入 secret 值）；:260/395 localStorage 仅 theme | 部分：raw YAML 不持久化（好）；但 operations 草稿可能含 secret 值入 sessionStorage | 【我方已验证】StructuredField.vue:19-21 isSecret 仅 UI 掩码，uuid/username 不掩 |

---

## 3. 完整路由鉴权矩阵

前缀 /api。"当前鉴权"列：头=require_internal_request（routes.py:107-109，仅 x-fixcloud-request:1）；无=完全无鉴权（cookie 仅会话隔离，非认证）。风险级针对"LAN 可达攻击者"。

### 3.1 非 GET 路由（18 条，全部仅靠头）【我方已验证】

| 方法 | 路径 | 行号 | 当前鉴权 | 应有鉴权 | 风险级 |
|---|---|---|---|---|---|
| POST | /sources/probe | 365 | 头 | 管理员 | 高（可探测任意来源） |
| POST | /sources/{id}/test | 389 | 头 | 管理员 | 中（写审计 connection-test） |
| POST | /sources/directories | 409 | 头 | 管理员 | 高（可列任意候选来源目录） |
| POST | /sources | 447 | 头+probeToken | 管理员 | 高（新增来源含凭据） |
| PUT | /sources/{id} | 465 | 头+probeToken | 管理员 | 高（改来源凭据） |
| DELETE | /sources/{id} | 491 | 头（built_in 禁删 499） | 管理员 | 高 |
| POST | /files/upload | 528 | 头 | 管理员 | 高（≤5MiB yaml，temporary/config） |
| DELETE | /files | 601 | 头+expectedHash | 管理员 | 高（删配置文件） |
| POST | /files/select | 676 | 头 | 管理员 | 低（仅校验不持久化） |
| POST | /config/export | 781 | 头+baseHash | 管理员 | 严重（返回完整 YAML 含凭据） |
| POST | /config/preview | 834 | 头+baseHash | 管理员 | 高（diff 原文含凭据） |
| POST | /config/advanced/validate | 868 | 头+baseHash | 管理员 | 中 |
| POST | /config/preview/raw | 893 | 头+baseHash | 管理员 | 高 |
| POST | /config/save | 923 | 头+write_enabled+previewToken | 管理员 | 严重（改生产代理配置） |
| POST | /history/restore-preview | 1001 | 头+is_selected_backup | 管理员 | 高 |
| DELETE | /history/backup | 1034 | 头+is_selected_backup | 管理员 | 高（删备份+审计） |
| PUT | /logs/settings | 1178 | 头 | 管理员 | 中 |
| DELETE | /logs | 1187 | 头（故意不审计 1192） | 管理员+不可清或强审计 | 高（抹除痕迹） |

### 3.2 GET 路由（16 条，全部无鉴权）【我方已验证】

| 路径 | 行号 | 当前鉴权 | 应有鉴权 | 风险级 |
|---|---|---|---|---|
| /health | 251 | 无 | 内部/最小化（去来源探测） | 中（503 含 exc；每 30s 建会话） |
| /subscriptions/usage | 264 | 无 | 管理员 | 中（流量元数据） |
| /vps/usage | 287 | 无 | 管理员 | 中 |
| /subscriptions/nodes | 293 | 无 | 管理员 | 中（节点 name+type） |
| /publication/status | 314 | 无（有副作用：外连+写审计） | 管理员 | 中（泄露 publishedUrl） |
| /sources | 354 | 无 | 管理员 | 高（safe_data+writeEnabled；触发全部来源连接测试） |
| /files/catalog | 509 | 无 | 管理员 | 中 |
| /files | 640 | 无（仅 path="/"） | 管理员 | 中 |
| /config | 698 | 无 | 管理员 | 严重（全量凭据 YAML，零掩码） |
| /config/raw | 732 | 无 | 管理员 | 严重（完整原文+hash） |
| /config/summary | 750 | 无 | 管理员 | 中 |
| /history | 980 | 无 | 管理员 | 中（备份列表+审计） |
| /icons/cache | 1076 | 无 | 公开可接受（SSRF 由 B11 缓解） | 低（残留 rebinding） |
| /icons/catalog | 1117 | 无 | 公开可接受 | 低 |
| /logs | 1132 | 无 | 管理员 | 高（≤5000 条审计可读） |
| /logs/settings | 1171 | 无 | 管理员 | 低 |

结论【我方已验证】：34 条路由中，18 条非 GET 仅靠可伪造头，16 条 GET 完全无鉴权；其中 /config、/config/raw、/config/export、/config/save 构成"零鉴权读全量凭据 + 带头改生产配置"的完整接管链。

---

## 4. 差距与风险分级

### P0（3 条，需优先处置）

- P0-1 零鉴权凭据读取【我方已验证】：GET /api/config（routes.py:698）与 /api/config/raw（:732）无任何鉴权，yaml_service.py:73-80 to_safe_data 零掩码。影响：任何 LAN 设备一条 GET 拿到回家节点凭据、3 个 provider 中 2 个的 query token、external-controller secret、全量订阅 URL。可利用前提：LAN 可达（端口绑 0.0.0.0，无 IP 白名单）。已从本机 LAN 实证 200 21399B。
- P0-2 公开文件域无鉴权 + 目录索引【我方已验证】：https://<PUBLIC_FILE_DOMAIN>/ 索引 200（683741B、167 hrefs，含 2 个 .yaml、icon/、rules/）；FixCloud.yaml 200 20893B；oixCloud.yaml 200 24012B。影响：公网任何人可枚举并下载双 YAML，凭据外泄面从 LAN 扩大到互联网。可利用前提：知道/猜出域名（目录索引助枚举；域名可能经订阅链接/DNS 泄露）。
- P0-3 管理写端点仅靠可伪造头【我方已验证】：18 条非 GET 全靠 x-fixcloud-request:1（routes.py:107-109），无 IP/网段/令牌校验。影响：LAN 攻击者带头即可新增来源、上传/删除文件、保存生产配置（writeEnabled=true）、删备份、清审计（DELETE /logs 自身不审计）。可利用前提：LAN 可达 + 设一个头。与 P0-1 组合 = 完整读写接管 + 抹痕。

### P1

- P1-1 /data 0770 组可读【生产配置】：sources.json（516B 明文凭据）、audit.sqlite3（61440B）实际 0770，everyone 组可读；代码意图 0600（source_store.py:168/175）被 QNAP ACL 覆盖。前提：NAS 本地另一用户/进程属 everyone 组。
- P1-2 写能力未绑真实身份【生产配置】：WRITE_ENABLED=true + SMB bind RW（inspect /mnt/fixcloud RW=true）。写闸（routes.py:929-930）只是功能开关，背后无身份；P0-3 成立时写闸形同虚设。
- P1-3 审计可被无痕清除【我方已验证】：DELETE /logs（routes.py:1187-1192）仅头鉴权、clear 全表无 scope 过滤（audit.py:179-185）、自身故意不审计；username 固定"内网访问"（audit.py:99）无法归因。
- P1-4 demo 未来暴露（**真实值已清理，风险已降级**）【我方已验证·2026-11-25 复核】：两个 demo HTML 与 SettingsView.vue:46、IconCatalogPicker.vue:173 已在源码纳管时脱敏为 example.com / 192.0.2.x；**本轮另发现并修复漏项** SourceModal.vue:248（服务器地址 placeholder 为真实 NAS LAN IP）与 :249（共享目录 placeholder 为真实个人共享名），改为 192.0.2.10 / files。漏检根因：验收门全局豁免 RFC1918、且裸词不匹配域名正则 → 已新增 `shipped-asset-private-ip` 规则（仅对 frontend/src、frontend/public 收紧，附正/负对照验证）。**剩余风险**：vite.config.ts 无 publicDir 排除 → 下次构建 demo 仍会进 dist 并经 main.py:97-99 无鉴权暴露（当前生产 404，镜像早于 demo 加入）；内容虽已脱敏，仍建议构建时排除 demo 或加访问控制。
- P1-5 仓库内自有环境路径的取舍约定【我方已验证】：.env.example、README.md、docs/ 与知识库中保留用户**自有**环境的 NAS 共享路径/用户名（非凭据、仅仓库内可见、且部署需要），但**任何随前端构建分发到浏览器的资产一律只用示例值**。此约定已写入验收门，避免后续代理反复 churn。

### P2

- P2-1 health 异常文本泄露【我方已验证】：routes.py:259-260 503 detail 含 {exc}，可能带来源主机名/路径。
- P2-2 health 每 30s 建会话【生产配置】：compose healthcheck（48-57）无 cookie GET /api/health → main.py:58-64 每次新建会话目录，≈2880/天（实测 <1h 117 个吻合）。temporary-sessions 有界 churn≈2900（oldest 24.8h），非无限增长；handoff"累积约 2911 子目录/无限增长"表述【已过时】，修正为"有界但高频 churn + 清理任务无异常守卫"。
- P2-3 cleanup_loop 无异常守卫【我方已验证】：browser_session.py:90-96 无 try/except，一次 PermissionError 即永久杀死清理 → 潜在无限增长。
- P2-4 cookie 非认证 + secure:false【我方已验证】：browser_session.py:19-20 仅格式校验；main.py:70-78 secure:false（LAN HTTP 可接受，若经 HTTPS 代理应置 true）。
- P2-5 icon_cache DNS rebinding TOCTOU【我方已验证】：icon_cache.py:59-77 校验与 httpx 连接分别解析 DNS，存在重绑定窗口；198.18.0.0/15 例外（:20/76-77）为 Fake-IP 兼容。
- P2-6 前端 operations 草稿含 secret【我方已验证】：app.ts:353 operations 写 sessionStorage，可含用户输入 secret 值；isSecret（StructuredField.vue:19-21）仅 UI 掩码且漏 uuid/username。
- P2-7 docker inspect 明文 env【生产配置】：EVOXT_*/VULTR_API_KEY 在 inspect 可见（docker.sock 读权限=已特权，参考 knowledge/09 的 AUTH_PWHASH 教训【参考提炼】）。
- P2-8 GET /publication/status 副作用 + 泄露 publishedUrl【我方已验证】：routes.py:314/349，publication.py:85。
- P2-9 死代码 app_state.py【我方已验证】：54 行 AppStateStore，全仓库仅自身类定义（app_state.py:9），无调用方；state.json 遗留。
- P2-10 无管理端点限速【我方已验证】：routes.py 全局限速缺失；参考 knowledge/09：socat L4 无 XFF 时按 IP 硬锁定有害（DoS 自锁），应递增延迟而非永久拒绝【参考提炼】。

---

## 5. 加固方案

每项含：精确改动点（文件:行号）、改法、是否需生产授权、验收方法、回滚点。所有源码改动在仓库进行，生产部署需当次授权；本文档不改任何源码/生产。

### 5.1 管理端点真实鉴权（不引入账号密码登录）

改动点：
- backend/app/api/routes.py:107-109（require_internal_request 定义）；18 条非 GET 的 Depends 注入处（365/389/409/447/465/491/528/601/676/781/834/868/893/923/1001/1034/1178/1187）；敏感 GET（698/732/750/354/509/640/980/1132/1171/314/264/287/293）。
- backend/app/core/settings.py:21 附近新增 admin_token（Field(repr=False)，env ADMIN_TOKEN）、trusted_lan_subnet（env TRUSTED_LAN_SUBNET）、trusted_proxies（env TRUSTED_PROXIES）。
- backend/app/main.py:54-94 中间件：新增管理员会话 cookie 交换逻辑。
- frontend/src/stores/app.ts:262-275 request：管理请求改带管理员会话 cookie（同源自动），不再仅靠 X-FixCloud-Request。

改法（网络位置 + 轻量令牌双因子，无密码）：
1. 来源判定：取 request.client 的 host 字段（请求对端 IP）；仅当该地址属 trusted_proxies（Lucky/nginx 宿主地址）时才信 X-Forwarded-For 最左一跳，否则忽略 XFF（防伪造）。判定真实来源 IP ∈ trusted_lan_subnet（如 192.0.2.0/24 示例；生产填 <NAS_LAN_SUBNET>）。不在网段 → 403。
2. 轻量令牌：env ADMIN_TOKEN（随机 ≥32 字节）。新增 POST /api/admin/session：校验来源网段 + 令牌（constant-time compare）→ 签发独立 httponly cookie fixcloud_admin（SameSite=Strict，Secure 视部署，path=/api，TTL 如 12h），与 fixcloud_session 分离。管理路由依赖改为 require_admin：校验网段 + fixcloud_admin 服务端注册（非仅格式）。令牌不入浏览器存储（仅内存中一次性提交换 cookie），符合 design/03 凭据约束。
3. 保留 x-fixcloud-request 头作为 CSRF 辅助（非安全边界），require_admin 取代 require_internal_request 成为真边界。
4. 不引入账号密码登录的论证：单用户家庭场景，网段+令牌已满足"位置+持有"双因子；密码登录会引入 LAN 爆破面（参考 knowledge/09：登录页无防爆破教训【参考提炼】）与会话管理复杂度，收益不抵成本。令牌轮换=改 env+重启，可接受。
5. 限速：管理端点失败递增延迟（参考 knowledge/09，永不永久拒绝，避免 socat L4 无 XFF 自锁【参考提炼】）。

是否需生产授权：是（部署新镜像 + 注入 ADMIN_TOKEN/TRUSTED_LAN_SUBNET/TRUSTED_PROXIES env + 重启容器）。
验收：本地 compose（§7）pytest 覆盖网段内/外、伪造 XFF、无令牌、令牌换 cookie、跨 cookie 消费拒绝；生产只读探测：无 cookie GET /api/config/raw 应 403（部署后），LAN 内带 admin cookie 应 200。
回滚点：保留旧镜像 tag 与 NAS compose 备份（/share/Container/FixCloudPanel/docker-compose.yml.bak-20261117 已存在）；env 移除 ADMIN_TOKEN 即回退旧行为（需同时回退镜像）。

### 5.2 订阅输出与管理端点鉴权分离

改动点：未来私有订阅中心新增路由（独立前缀如 /api/subscription/{token}）；routes.py:698/732/781 管理读取加 require_admin；publication.py:25-91 与 routes.py:314 公开校验逻辑迁移。
改法：订阅输出走"每订阅能力令牌"（capability URL，token 即鉴权，无网段限制以便移动设备在外网取订阅）；管理 API 走 §5.1 网段+admin cookie。两者绝不共用鉴权依赖；管理 API 永不向未认证调用方返回订阅 URL/凭据。私有订阅中心服务端读取 FixCloud.yaml，客户端只拿到带 token 的订阅输出，不再依赖公开 file URL。
是否需生产授权：是（新服务部署）。依赖：必须在 §5.1 管理鉴权之后或同期，避免新端点继承零鉴权。
验收：pytest 订阅 token 有效/无效/过期；管理端点无 admin cookie 403；订阅端点无网段限制但无 token 403。
回滚点：订阅中心独立容器/路由，可单独下线；公开 file URL 在迁移完成前保持（见 5.6）。

### 5.3 /data 与 sources.json 权限修复（0770→0700/0600）

改动点（生产宿主，非源码）：/share/Container/FixCloudPanel/data 及其下 sources.json、audit.sqlite3、temporary-sessions、icon-cache、icon-catalog。源码侧 source_store.py:168/175 已有 0o600 意图，无需改；mounted.py:101 write 0o600、move:138/146-147 保留目标 mode 亦无需改。
改法与可行性：
- 根因【生产配置】：QNAP 共享文件夹 ACL/umask 覆盖容器 os.chmod，故容器内 chmod 无效，必须在宿主 QNAP 侧处置。
- 方案 A（推荐）：QNAP「高级文件夹权限」对 data 目录停用 ACL 继承，再 chmod 0700（目录）/0600（文件），属主保持 1000:100（PUID:PGID 不变）。需先 getfacl 快照。
- 方案 B：将 APP_DATA_HOST_PATH 迁出共享 ACL 管辖路径（如非共享的容器专用卷），改 .env APP_DATA_HOST_PATH + compose bind，重启生效。迁移需停容器复制数据，影响更大。
- QNAP UID/GID 约束：容器 user 1000:100（compose:9），宿主 data 属主 1000:100，chmod 0700 后容器仍可读写（属主不变）；everyone 组其他成员失去访问。不得改属主为 admin（会破坏容器写入）。
- 对现有容器影响：方案 A 不停容器即可生效（ACL 变更后即时）；方案 B 需重启。sources.json 必须保持容器用户 1000 可读，否则来源加载失败。
是否需生产授权：是（宿主权限/ACL 变更，属生产写入）。本文档只读核实，未执行任何 chmod。
验收：变更后容器内 stat data/sources.json 应 0700/0600；GET /api/sources 仍 200（来源正常加载）；宿主以非属主 everyone 成员尝试读应拒绝。
回滚点：getfacl 快照恢复；方案 B 保留原 data 目录与旧 .env 值。

### 5.4 temporary-sessions 治理（TTL/上限/清理，禁误删活跃）

改动点：backend/app/main.py:58-64（每请求建会话）；backend/app/services/browser_session.py:65-87（cleanup_expired）、:90-96（cleanup_loop）；docker-compose.yml:48-57（healthcheck）。
改法：
1. healthcheck 免建会话：main.py 中间件对 /api/health（或 loopback + 特定 UA）跳过 new_token/touch，消除 ≈2880/天 churn（P2-2）。
2. cleanup_loop 加 try/except（browser_session.py:90-96），捕获 PermissionError/OSError 并记日志，保证清理任务不因单次异常永久死亡（P2-3）。
3. 上限 + LRU 淘汰：cleanup_expired 增加 max_sessions（如 5000）；超限时按 mtime 升序淘汰最旧，但跳过最近 touch（如 5min 内）目录，确保活跃会话不被误删。现有 touch（:60-62）每请求刷新 mtime，活跃会话天然保活。
4. 保留现有安全删除约束（仅 64hex 名、非 symlink、resolved 父目录==root），不放宽。
是否需生产授权：源码改动随镜像部署需授权；无独立生产写入。
验收：pytest 模拟超限淘汰 + 活跃保活 + 异常后清理仍存活；本地 compose 跑 healthcheck 1h 后目录数应稳定不再线性增长。
回滚点：旧镜像；上限设很大即近似旧行为。

### 5.5 writeEnabled 策略与最小权限

改动点：docker-compose.yml:16（WRITE_ENABLED 默认 false，保持）；NAS .env WRITE_ENABLED=true（生产）；routes.py:929-930 写闸；compose:28 SMB read_only 默认 true（生产 .env YAML_MOUNT_READ_ONLY=false 覆盖）。
改法：writeEnabled=true 是保存功能所需，保留；但必须置于 §5.1 真实身份之后（写闸=功能开关，身份=安全边界，二者正交）。最小权限复核：容器 read_only:true / cap_drop ALL / no-new-privileges / tmpfs 32m 已达标（B12），无需放宽；/data bind RW 与 SMB RW 为功能必需，不改为 RO（否则保存失败）。非默认来源建议默认 readOnly，仅用户显式启用写。
是否需生产授权：策略本身无需（保持现状）；若调整 .env 需授权。
验收：pytest write_enabled=false 时 save 403/409；=true 且无 admin cookie 时 save 403（§5.1 后）。
回滚点：.env 原值。

### 5.6 公开 file URL 暴露面处置（衔接私有订阅中心）

改动点（生产 Lucky/宿主，非源码）：https://<PUBLIC_FILE_DOMAIN>/ 的投递规则与目录索引；publication.py:25-91 / routes.py:314 校验逻辑随订阅中心迁移。
改法与依赖顺序：
- 终态：私有订阅中心（§5.2）上线并迁移所有消费方后，退役公开 YAML 投递（删除公开目录中的 FixCloud.yaml/oixCloud.yaml，或整个 file 域改为鉴权投递）。
-  interim（订阅中心未就绪前）：Lucky 反代对 /FixCloud.yaml、/oixCloud.yaml 路径加令牌/Basic 鉴权；关闭 file 根目录 autoindex（消除 167 条目枚举）。需先确认谁在消费公开 URL（handoff 未决问题），避免断订。
- 依赖关系【我方已验证】：公开 URL 当前无鉴权 200，是 P0-2 根因；退役必须晚于订阅中心可用 + 消费方迁移，否则断订。interim 鉴权可先行（不依赖订阅中心）。
是否需生产授权：是（Lucky 配置变更/文件移除，属生产写入）。
验收：变更后公网 GET https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml 应 401/403（interim）或 404（退役）；目录索引应 403/404；订阅中心带 token 输出仍 200。
回滚点：Lucky 配置备份；公开文件移除前保留副本于非公开路径。

### 5.7 凭据在日志/审计/错误响应/前端的泄露面

改动点与改法：
- 错误响应：routes.py:259-260 health 503 detail 去 {exc}，改通用消息（P2-1）；复核 save_service.py:255-298 三态错误消息不含凭据（当前为状态描述，保持）。
- 审计：audit.py:71-92 details 仅存 message/status，不存 YAML 正文（已验证良好，保持）；smb.py:81-97 通用错误映射保持；DELETE /logs（routes.py:1187-1192）改为需 admin + 清审计本身写一条不可删审计（或禁止全清，仅按 scope 清），解决 P1-3。
- 前端：app.ts:353 operations 草稿持久化前剔除/掩码 isSecret 命中字段（StructuredField.vue:19-21 正则），或整个 operations 不入 sessionStorage（与 rawYamlDraft:339-341 一致）；isSecret 正则视需要补 uuid/username（仅 UI 层，真边界在后端鉴权）。
- GET /config 掩码：yaml_service.py:73-80 to_safe_data 可选对 secret 类键掩码后返结构化视图；但 README.md:122 决策"可信内网显式全 Diff 请求允许原文"——保留全 Diff，但仅对已认证 admin（§5.1）开放，不再零鉴权。
- docker inspect env（P2-7）：参考 knowledge/09 外置 .env 教训【参考提炼】，可改 docker secrets / env_file 受限权限；优先级低（docker.sock=已特权）。
是否需生产授权：源码随镜像部署需授权；无独立生产写入。
验收：pytest health 503 不含 exc 文本；DELETE /logs 无 admin 403、清后留痕；前端 sessionStorage 草稿不含 secret 值。
回滚点：旧镜像。

### 5.8 静态资源与 demo 页暴露面

改动点：frontend/public/demo/nothing-full.html、nothing-iphone.html（git-tracked 真实值）；frontend/src/components/SourceModal.vue:248-249、SettingsView.vue:46（硬编码真实值）；vite.config.ts（publicDir）；main.py:97-99 静态挂载。
改法：将 demo 移出 public/（如 docs/，不进构建）或删除其中真实值改占位符；SourceModal/SettingsView 真实值改占位符（<NAS_LAN_IP>/<PUBLIC_FILE_DOMAIN>）；构建期校验 dist 不含敏感文件。生产当前 demo 404（镜像早于 demo），但下次构建将暴露，必须先清理仓库再构建。
是否需生产授权：仓库改动无需；部署新镜像需授权。
验收：构建后 dist 无 demo/真实值；生产 GET /demo/*.html 保持 404；grep 仓库无真实 IP/域名（verify-sanitized 门）。
回滚点：git  revert；旧镜像。

### 5.9 死代码清理（app_state.py）

改动点：backend/app/services/app_state.py（54 行，AppStateStore:9，全仓库无调用方【我方已验证】）；/data/state.json 遗留。
改法：删除 app_state.py；state.json 生产遗留可在 §5.3 权限修复时一并归档移除（需授权）。
是否需生产授权：源码删除随镜像部署需授权；state.json 移除属生产写入需授权。
验收：grep 无 AppStateStore 引用；pytest 全绿；GET /api/sources 等不依赖 state.json。
回滚点：git revert。

---

## 6. 权限模型设计

角色/能力/端点映射（管理 vs 订阅 vs 静态三分）：

| 角色 | 鉴权方式 | 能力 | 端点 |
|---|---|---|---|
| 管理员（单用户家庭） | 网段 ∈ <NAS_LAN_SUBNET> + ADMIN_TOKEN 换 httponly fixcloud_admin cookie（§5.1） | read-config / write-config / manage-sources / upload / delete / export / audit-read / audit-clear（受限）/ publication-check | 全部 18 非 GET + 敏感 GET（/config /config/raw /config/summary /sources /files /files/catalog /history /logs /logs/settings /publication/status /subscriptions/* /vps/usage） |
| 订阅者（未来） | 每订阅 capability token（URL 即凭据，无网段限制） | subscription-read（仅自己的订阅输出） | /api/subscription/{token}（私有订阅中心，§5.2） |
| 静态/公开 | 无 | 仅无敏感静态资源 | / /assets /icons/cache /icons/catalog（SSRF 由 B11 缓解） |
| 内部健康 | loopback / docker healthcheck | minimal-health（去来源探测、免建会话） | /api/health（最小化响应） |

能力约束：
- write-config 额外受 writeEnabled 功能闸（routes.py:929-930）与 previewToken/baseHash 乐观锁约束，身份与功能正交。
- audit-clear 不再无痕：清审计本身留不可删记录，或仅允许按 session_scope 清（audit.py:179-185 改）。
- 订阅 token 与管理 cookie 绝不互认；管理 API 不向订阅者返回凭据/订阅 URL。
- 静态角色永不接触 YAML/凭据/审计；dist 内容经构建期校验（§5.8）。
- 归因：当前 username 固定"内网访问"（audit.py:99）；单用户下可接受，若未来多成员需引入操作者标识（不引入密码登录，可用令牌别名）。

---

## 7. 隔离测试方案（不动生产）

1. 本地 compose：用仓库 docker-compose.yml 默认值（WRITE_ENABLED=false、PANEL_BIND_IP=127.0.0.1、YAML_MOUNT_READ_ONLY=true），独立网络/端口，不连生产 NAS。注入测试 ADMIN_TOKEN/TRUSTED_LAN_SUBNET（示例 192.0.2.0/24）。
2. pytest：沿用 backend/tests/test_api.py 模式（TestClient + Settings(app_env="test", storage_backend="local", tmp_path)，无 conftest）。新增覆盖：
   - 鉴权：网段内/外、伪造 XFF（非可信代理忽略）、无令牌 403、令牌换 cookie、跨 cookie 消费 previewToken 拒绝、18 非 GET + 敏感 GET 无 admin 403。
   - 会话：超限 LRU 淘汰、活跃 touch 保活、cleanup_loop 异常后仍存活、healthcheck 免建会话。
   - 凭据：health 503 不含 exc；DELETE /logs 留痕；前端草稿不含 secret（可单测 store 逻辑）。
   - 回归：test_api.py:53-54 现断言 GET /config 原样返 secret——§5.1 后该测试需改为"无 admin 403 / 有 admin 200 原文"，保留可信内网全 Diff 决策（README:122）。
3. 只读探测生产（部署前后对比，仅 GET/inspect，禁写入）：无 cookie GET /api/config/raw 部署前 200→部署后应 403；LAN 带 admin cookie 应 200；公开 YAML 处置后应 401/403/404。所有探测仅读，不 chmod/不重启/不写。
4. 权限修复验证（§5.3）在本地模拟 QNAP ACL 不可行，需生产授权后以 getfacl 快照 + 容器 stat 只读复核，不在测试阶段触碰生产权限。

---

## 8. 分阶段实施顺序与依赖

| 阶段 | 内容 | 依赖 | 与私有订阅中心关系 |
|---|---|---|---|
| Phase 0（订阅中心之前） | §5.1 管理鉴权、§5.3 /data ACL、§5.4 会话治理、§5.8 仓库/demo 清理、§5.9 死代码 | 无前置；均需生产授权部署 | 必须先于订阅中心：新端点应继承真实鉴权，避免扩大零鉴权面 |
| Phase 1（订阅中心建设） | §5.2 订阅/管理鉴权分离 + 私有订阅中心实现（handoff P0 优先级） | Phase 0 管理鉴权就位 | 本体；消费方迁移清单需先确认（§9） |
| Phase 2（订阅中心之后） | §5.6 公开 file URL 退役/鉴权、关 autoindex | 订阅中心可用 + 所有消费方迁移完成 | 必须晚于订阅中心，否则断订；interim 鉴权可提前至 Phase 0/1 |
| Phase 3（持续） | §5.5 writeEnabled 策略细化、§5.7 泄露面收敛、P2 项（rebinding/限速/secure cookie） | 随镜像迭代 | 无强依赖 |

关键依赖链【我方已验证】：公开 URL 当前无鉴权 200（P0-2），退役会断订 → 必须等订阅中心 + 消费方迁移；管理鉴权（P0-1/P0-3）不依赖订阅中心，应最先做。

---

## 9. 未决问题与需用户授权事项

未决问题：
1. 谁在消费公开 https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml？（handoff 未决）退役前必须确认消费方清单与迁移路径。
2. 第二个公开 YAML（oixCloud.yaml，24012B）是否有意公开？需用户确认其用途与处置。
3. Lucky 自身是否有 8787 转发规则？（路由器 uci 无 DNAT 已证实，Lucky 侧【待验证】）
4. TRUSTED_LAN_SUBNET 与 TRUSTED_PROXIES 的真实值需用户提供（文档用占位符）。
5. ADMIN_TOKEN 轮换策略与有效期（admin cookie TTL）需用户定。
6. 是否多家庭成员需操作归因？当前 username 固定"内网访问"，单用户可接受。

需用户授权（生产写入，本文档未执行任何一项）：
- A1 管理鉴权部署：注入 ADMIN_TOKEN/TRUSTED_LAN_SUBNET/TRUSTED_PROXIES env + 新镜像 + 重启容器。
- A2 QNAP /data ACL/权限修复（0770→0700/0600），含 getfacl 快照与属主保持 1000:100。
- A3 Lucky 公开 file 处置：interim 路径鉴权 + 关 autoindex；终态 YAML 退役（依赖订阅中心）。
- A4 仓库真实值清理后新镜像构建部署（demo/SourceModal/SettingsView）。
- A5 state.json 遗留移除、DELETE /logs 策略变更随镜像部署。

最需要用户授权的 3 件事（按风险/依赖排序）：
1. A1 管理端点真实鉴权（网段+ADMIN_TOKEN）——直接消除 P0-1/P0-3 接管链，且是订阅中心前置。
2. A2 /data 权限修复（QNAP ACL 0770→0700）——消除 P1-1 本地组可读凭据，容器内 chmod 无效必须宿主处置。
3. A3 公开 file URL 处置（Lucky 鉴权/关索引 + 订阅中心迁移后退役）——消除 P0-2 公网凭据外泄，需先确认消费方。

---

## 10. 禁止事项

- 禁止在本文档/仓库写入任何真实凭据、IP、域名、邮箱、手机号、token、UUID；一律占位符（<NAS_LAN_IP> <PUBLIC_FILE_DOMAIN> <HOME_DOMAIN> <NAS_EGRESS_IPV4> 等），示例仅 example.com / 192.0.2.10 / 198.51.100.20 / 203.0.113.30。
- 禁止未经当次授权对生产写入、重启、部署、改防火墙、chmod 生产目录；本次仅只读 GET/inspect。
- 禁止引入账号密码登录，除非论证必要（当前论证：网段+令牌足够，密码引入爆破面，见 §5.1）。
- 禁止把 x-fixcloud-request 头或 fixcloud_session cookie 当作身份鉴权边界（仅 CSRF 辅助/会话隔离）。
- 禁止误删活跃会话：淘汰须按 mtime 且跳过最近 touch 目录，保留 64hex/非 symlink/父目录校验。
- 禁止在订阅中心可用 + 消费方迁移完成前退役公开 file URL（断订）。
- 禁止破坏 Lucky 现有反代（16601/24443）、隧道（26611/26612）、证书链、回家 STUN 端口转发（infrastructure/03、07 不可破坏清单【生产配置】）。
- 禁止执行参考项目（JimmyChan233/homelab）脚本；其结论仅【参考提炼】。
- 禁止提交 .env/secrets/密钥；禁止凭据入浏览器持久存储（rawYamlDraft 已排除，operations 草稿需收敛）。
- 禁止静默保存：保存必须进 Diff 评审（design/03 交互约束）；破坏性操作双重确认。
- 禁止改容器属主为 admin 或放宽 cap_drop/no-new-privileges/read_only 来"解决"权限问题。
