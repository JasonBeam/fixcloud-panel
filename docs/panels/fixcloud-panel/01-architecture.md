> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 01 · 项目架构与功能说明

**结论**：FixCloud Panel 是「FastAPI 后端 + Vue3 前端」的单容器 NAS 应用，后端按 `api → services → storage` 三层组织，前端按 `views → components → composables/utils → stores` 组织；核心设计原则是**编辑范围硬隔离**（只编辑所选来源配置目录直属 YAML）与**事务化安全保存**（多重回读哈希 + 三态失败恢复）。【已验证：源码结构 + routes.py + save_service.py】

## 1. 总体分层

```text
浏览器（Vue3 SPA，hash 路由，PWA）
   │  同源 fetch（非 GET 自动带 X-FixCloud-Request:1）
   ▼
FastAPI 后端（uvicorn，单容器，非 root UID:GID）
   ├─ api/routes.py        34 条路由，请求模型与鉴权门禁
   ├─ services/            业务逻辑（YAML/保存/来源/审计/发布/订阅/VPS/图标/会话）
   │    └─ storage/        存储后端抽象（mounted/smb/webdav + registry）
   └─ core/settings.py     pydantic-settings 环境配置
   ▼
持久化：/data（audit.sqlite3 / sources.json / icon-cache / temporary-sessions）
        /mnt/fixcloud（NAS config 共享 bind mount，YAML 正式文件）
```

| 层 | 职责 | 关键文件 |
| --- | --- | --- |
| 入口/中间件 | lifespan 启动会话清理循环；CORS（仅开发）；安全响应头 + 会话 cookie 绑定；静态托管前端 dist | backend/app/main.py:27-99 |
| 配置 | 环境变量 → Settings（lru_cache 单例） | backend/app/core/settings.py:15-35 |
| API | 路由、请求模型、同源标记门禁、可编辑路径判定、请求级来源/路径上下文 | backend/app/api/routes.py:35-248 |
| 业务服务 | YAML round-trip、保存事务、来源存储、审计、发布核对、订阅流量/节点、VPS 用量、图标缓存/目录、浏览器会话 | backend/app/services/* |
| 存储抽象 | Protocol 统一 status/list/stat/read/write/copy/move/delete；按来源类型构建后端 | backend/app/services/storage/* |
| 前端状态 | Pinia options store：文件选择、草稿 operations、预览、保存失败四态、网络/主题 | frontend/src/stores/app.ts |
| 前端视图 | 11 views + 26 components + 4 composables + 10 utils | frontend/src/* |

## 2. 后端模块职责（当前真实）

| 模块 | 行数 | 职责 | 关键行 |
| --- | --- | --- | --- |
| main.py | 99 | lifespan cleanup_loop；docs 仅 development；CORS 仅 localhost:5173；security_headers 中间件（cookie 会话绑定 + CSP + 缓存策略）；StaticFiles 挂 dist | main.py:27-99 |
| core/settings.py | 35 | BaseSettings：app_env/app_data_dir/storage_backend/storage_root/yaml_path/write_enabled/public_file_base_url/frontend_dist；遗留 webdav_* 字段（compose 不再注入） | settings.py:15-35 |
| api/routes.py | 1193 | 34 路由；require_internal_request（写请求须 x-fixcloud-request:1）；is_editable_yaml_path（仅配置目录直属）；requested_context（请求级来源/路径） | routes.py:107-151 |
| services/yaml_service.py | 318 | ruamel round-trip（preserve_quotes、width4096、indent 2/4/2）；apply_operations（set/delete/insert/move，拒绝 __proto__/constructor）；validate_references；full_diff；summary | yaml_service.py:40-318 |
| services/save_service.py | 343 | PreviewStore（内存，TTL900s，会话 scope 校验）；create_preview/raw/restore；commit 事务（rollback/temp/recovery 三隐藏文件 + 多重回读哈希 + 三态恢复）；list_backups | save_service.py:32-343 |
| services/source_store.py | 316 | sources.json 原子写 0600；safe_data 剔除 username/password；内置 default-smb/uploaded-files；迁移逻辑；ProbeStore（probe-first，TTL600s 一次性 token） | source_store.py:16-316 |
| services/audit.py | 185 | SQLite audit_log + app_settings；record（UTC、会话 scope 仅 upload）；list_recent（按 source/path 过滤）；limit 裁剪；clear | audit.py:18-185 |
| services/publication.py | 91 | PublicationVerifier：先 GET 目录页触发 Lucky 刷新，再 stream GET 公开 YAML，sha256 比对；5MiB 上限；no-cache 头 | publication.py:25-91 |
| services/subscription_usage.py | 179 | 解析 subscription-userinfo 头（upload/download/total/expire）；HEAD 优先；TTL300s；不返回订阅 URL | subscription_usage.py:35-166 |
| services/subscription_nodes.py | 126 | 解析订阅 YAML proxies 或 base64 URI；只返回 name/type；8MiB/500 节点/20 provider 上限；不返回 URL/server/password | subscription_nodes.py:15-53 |
| services/vps_usage.py | 54 | **11-22 新增**：Evoxt（HK，服务器套餐 GiB）+ Vultr（JP，账号本月 GB）并发；未配置→available:false 不显示假 0；never return credentials | vps_usage.py:11-54 |
| services/browser_session.py | 96 | cookie fixcloud_session（token_urlsafe32）；scope=sha256(token)；/data/temporary-sessions/<64hex>；ContextVar 请求级绑定；TTL24h；每小时 cleanup_loop | browser_session.py:13-96 |
| services/icon_cache.py | 196 | /data/icon-cache/<sha256(url)>；1MiB 上限；per-digest 锁；DNS 解析后仅公网 IP（例外 RFC2544 198.18.0.0/15 Fake-IP）；魔数嗅探；原子写 | icon_cache.py:20-183 |
| services/icon_catalog.py | 163 | 上游 GitHub shindgew/WHATSINStash；TTL24h；url 重写为公开域名/icon/；personalItems=storage_root/icon | icon_catalog.py:14-115 |
| services/app_state.py | 54 | **死代码/遗留**：AppStateStore state.json，grep 全 backend/app 无引用；文件选择实际由前端 store 管理 | app_state.py（无引用） |
| storage/base.py | 44 | StorageBackend Protocol + StorageStat/StorageEntry（etag） | base.py |
| storage/registry.py | 103 | build_primary_storage / build_storage_from_source（按类型 mounted/smb/webdav/upload） | registry.py |
| storage/mounted.py | 153 | 本地/主机挂载文件系统；_resolve 防越界；过滤 ._*/.DS_Store/@eaDir；write O_EXCL/O_TRUNC 0600+fsync；**move 保留目标原权限位** | mounted.py:18-147 |
| storage/smb.py | 193 | smbprotocol 直连；register_session；错误分类 authentication/not_found/connection/timeout | smb.py |
| storage/webdav.py | 194 | httpx BasicAuth；PROPFIND + defusedxml；PUT If-None-Match:*；COPY/MOVE Overwrite | webdav.py |

## 3. 前端模块职责

| 模块 | 职责 | 关键行 |
| --- | --- | --- |
| stores/app.ts（614 行） | Pinia options store：booting/online/backendReachable/dark/writeEnabled；file 选择；operations 草稿；rawYamlDraft（**绝不入浏览器存储**）；canSave=online&&backendReachable&&writeEnabled&&dirty；request() 非 GET 自动加同源标记；SaveFailure 四态 | stores/app.ts:245-599 |
| router/index.ts（42 行） | **createWebHashHistory**；/→/sources；sources/files/editor/editor/advanced-yaml/editor/:section/editor/:section/item/:itemId/usage/more/subscription-nodes/history/settings | router/index.ts |
| main.ts（40 行） | createPinia；beforeEach 草稿守卫；导入 style.css + visual-refresh.css（后者覆盖） | main.ts:13-14 |
| views（11） | EditorHome（10 分类入口）/Section（列表+拖拽排序）/ItemEditor（按 section 分发编辑器）/AdvancedYaml（原始 YAML）/Files/Sources/Usage（订阅+VPS）/SubscriptionNodes/History/Settings/More | frontend/src/views/* |
| components（26） | AppShell（桌面侧栏6/移动tab4）/SourceModal（probe-first）/ProxyGroupEditor/StructuredField（isSecret 自动遮罩）/FileSelector/IconCatalogPicker/RuleFieldEditor/DiffModal/ReferenceIntegrityModal/UnsavedChangesModal/SaveBar 等 | frontend/src/components/* |
| composables（4） | draftGuard（三模式 continue/close/switch）/appDialog（Promise 化全局对话框）/referenceGuard（cancel/keep/remove/replace） | frontend/src/composables/* |
| utils（10） | editorSchemas（proxyTypes 8 种）/proxyGroup（成员候选）/referenceIntegrity（scanDeleteImpact）/regexPreset（地区懒人筛选）/sourcePresentation（正式/临时分组） | frontend/src/utils/* |

## 4. 数据流总览

```text
来源（NAS SMB bind / SMB 直连 / WebDAV / 会话上传）
  → storage 后端读取 YAML 字节
  → yaml_service.load（round-trip CommentedMap）
  → 前端结构化编辑（operations 草稿，本地立即应用）
  → POST /api/config/preview（重读+哈希核对→apply→dump→validate→diff→previewToken）
  → DiffModal 确认
  → POST /api/config/save（previewToken）
  → save_service.commit 事务：
       重读正式哈希核对 → 写 rollback 隐藏副本 → 写 temp → 回读 temp 哈希
       → move(temp→正式,保留原权限) → 回读正式哈希
       → 成功删 rollback / 失败三态 unchanged|restored|recovery_failed
  → audit.record（before/after hash，backupPath=None）
  → 前端重新 fetchConfig
  →（可选）GET /api/publication/status 核对线上公开 YAML 哈希
```

## 5. 编辑范围硬隔离原则（核心安全设计）

| 原则 | 实现 | 行号 |
| --- | --- | --- |
| 只编辑配置目录直属 YAML | is_editable_yaml_path：以/开头、dirname=="/"、非点文件、不含 ".backup-"、.yaml/.yml 结尾 | routes.py:137-151 |
| 不递归扫描 | list_editable_yaml_files 仅列配置目录直属；目录浏览 include_config_directory=False | routes.py:221-248、registry.py |
| 请求级上下文 | requested_context 默认 default-smb + settings.yaml_path；来源不存在404、路径越界422；**无全局可变选择状态** | routes.py:120-134 |
| 浏览器会话隔离 | 每标签页独立 cookie→scope→temporary-sessions 目录；上传/临时文件/审计按 scope 隔离；A 不可见 B | browser_session.py、main.py:54-94 |
| 文件选择前端管理 | sessionStorage fixcloud-session-selection（sourceId+path）；/files/select 仅校验返回，不落全局状态 | stores/app.ts、routes.py:676-695 |
| 备份名不可当主文件编辑 | is_selected_backup 判定 {主文件名}.backup-*.yaml；删主文件当备份→422 | routes.py:154-159 |
| 写请求同源门禁 | require_internal_request：非 GET 须 x-fixcloud-request:1，否则403（**无 IP 白名单**，适用可信内网） | routes.py:107-109 |
| 凭据后端-only | sources.json 存明文但 safe_data 剔除 username/password；API 不回传；不进浏览器存储/审计 details | source_store.py:39-51 |

> 设计取舍：面板**不提供登录页**，适用于可信家庭内网或用户自己的内网隧道；写请求同源标记仅防普通跨站表单，不防恶意内网客户端。【已验证：README.md:27、routes.py:107-109】
