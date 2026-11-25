> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 03 · API 路由与数据流

**结论**：当前 `backend/app/api/routes.py`（1193 行）共 **34 条路由**，统一前缀 `/api`（routes.py:35）。**全部 18 条非 GET 路由**经 `Depends(require_internal_request)` 要求请求头 `x-fixcloud-request:1`（routes.py:107-109），否则 403；**无 IP 白名单**。GET 路由不要求该标记，但 `GET /publication/status` 与 `GET /icons/cache` 有写审计/缓存副作用。保存另受 `write_enabled` 门禁。【已验证：grep 路由装饰器 + Depends + record_event】

## 1. 鉴权与门禁模型

| 机制 | 规则 | 行号 |
| --- | --- | --- |
| 同源标记 | 非 GET 须 `x-fixcloud-request:1`，否则 403「写请求缺少面板同源标记」；前端 request() 自动附加 | routes.py:107-109、stores/app.ts:262-275 |
| 无登录/无 IP 白名单 | 适用可信家庭内网/自有隧道；同源标记仅防普通跨站表单 | README.md:27 |
| 会话 cookie | `fixcloud_session`（httponly/samesite=strict/secure=False/path=/，无 Max-Age）；scope=sha256(token) 绑定请求级 ContextVar | main.py:54-94、browser_session.py |
| 写开关 | `POST /config/save` 时 write_enabled=False→403「服务器当前处于只读模式」 | routes.py:923-977 |
| 可编辑路径 | is_editable_yaml_path：仅配置目录直属 .yaml/.yml，非点文件、不含 .backup- | routes.py:137-151 |
| 请求级上下文 | requested_context：默认 default-smb + settings.yaml_path；来源不存在404、路径越界422 | routes.py:120-134 |
| probe-first | 新增/编辑来源必须先 POST /sources/probe 连通取得 probeToken，保存须带 token 且指纹匹配，否则409 | routes.py:447-488、source_store.py:281-316 |
| 哈希冲突 | preview/save/export/delete 均核对 baseHash/expectedHash，不符409 | routes.py:781-977、601-637 |
| 预览时效 | PreviewStore 内存 TTL900s，take 校验 session_scope；过期410 | save_service.py:32-54、routes.py:923-977 |

## 2. 请求模型（routes.py:38-104）

| 模型 | 字段与约束 |
| --- | --- |
| PatchOperation | op: set\|delete\|insert\|move；path: list[str\|int]；value；fromIndex/toIndex |
| PreviewRequest | sourceId≤128、path≤2048、baseHash=64字符、operations 1..1000 |
| RawYamlRequest | 同上 + content 1..2000000 |
| SaveRequest | previewToken 20..200 |
| ExportRequest | sourceId/path/baseHash + operations 0..1000 + filename≤255 |
| RestorePreviewRequest / DeleteBackupRequest | sourceId、path、backupPath |
| SelectFileRequest | sourceId、path |
| DeleteFileRequest | sourceId、path、expectedHash（64） |
| LogSettingsRequest | maxEntries 1..50000 |
| SourceInput | sourceId?、type: smb\|webdav、name、config:dict、probeToken? |

## 3. 路由全表（34 条，当前真实行号）

> 鉴权列：「同源」= 须 x-fixcloud-request:1；「—」= GET 无标记要求。审计列给出 action 名（SettingsView.vue:143-149 映射）。

### 3.1 健康 / 用量 / 发布（5 条）

| # | 方法 路径 | 行 | 入参 | 出参 | 鉴权 | 审计 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | GET /health | 251-261 | 无 | {status:ok,storage:ready,yaml:valid}；默认配置未就绪→503 | — | 无 |
| 2 | GET /subscriptions/usage | 264-284 | query sourceId,path,force | {subscriptions[],fetchedAt,cached}；缓存键含 scope+sha256 | — | 无 |
| 3 | GET /vps/usage | 287-290 | 无 | {servers:[Evoxt,Vultr]}（**11-22 新增**） | — | 无 |
| 4 | GET /subscriptions/nodes | 293-311 | query sourceId?,path?,force | {providers[],totalProviders,totalNodes,cached,refreshedAt} | — | 无 |
| 5 | GET /publication/status | 314-351 | query sourceId,path | {result,baseUrl,fileName}；result 含 matching/currentHash/publishedHash/publishedUrl/publishedSize/etag/lastModified/latencyMs/directoryRefreshed；PublicationCheckError→422 | — | publication-check（success/failure，330/340） |

### 3.2 来源管理（7 条）

| # | 方法 路径 | 行 | 入参 | 出参 | 鉴权 | 审计 |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | GET /sources | 354-362 | 无 | {sources:[safe_data+连接状态],default:"default-smb",writeEnabled} | — | 无 |
| 7 | POST /sources/probe | 365-386 | SourceInput（无 probeToken） | {source,probeToken}（连通才发） | 同源 | 无 |
| 8 | POST /sources/{id}/test | 389-406 | path id | {connected,latencyMs,testedAt,...} | 同源 | connection-test（399） |
| 9 | POST /sources/directories | 409-444 | query path（默认/）+ SourceInput | 非点目录列表+status（浏览候选来源，include_config_directory=False） | 同源 | 无 |
| 10 | POST /sources | 447-462 | SourceInput + probeToken | 新来源 safe_data；无 token/指纹不符→409 | 同源 | 无 |
| 11 | PUT /sources/{id} | 465-488 | SourceInput + probeToken | 更新后 safe_data；空凭据保留原值 | 同源 | 无 |
| 12 | DELETE /sources/{id} | 491-506 | path id | {deleted}；built_in→409；至少留一个来源 | 同源 | 无 |

### 3.3 文件浏览 / 上传 / 删除 / 选择（5 条）

| # | 方法 路径 | 行 | 入参 | 出参 | 鉴权 | 审计 |
| --- | --- | --- | --- | --- | --- | --- |
| 13 | GET /files/catalog | 509-525 | 无 | 全部来源可编辑 YAML 汇总排序（含 hash/size/modified） | — | 无 |
| 14 | POST /files/upload | 528-598 | multipart file + mode(temporary\|config，默认temporary) + sourceId | file 元数据+mode；仅.yaml/.yml、≤5MiB、YAML 校验、文件名清洗、同名 -1..-999 | 同源 | upload（567/589） |
| 15 | DELETE /files | 601-637 | DeleteFileRequest（expectedHash） | {deleted}；哈希不符409；仅配置目录直属 | 同源 | delete-file（622/633） |
| 16 | GET /files | 640-673 | query path（必须"/"否则403）,sourceId | source.safe_data + 可编辑条目（含hash） | — | 无 |
| 17 | POST /files/select | 676-695 | SelectFileRequest | {sourceId,path}（校验 YAML 可解析；选择存浏览器侧） | 同源 | 无 |

### 3.4 配置读取 / 导出 / 预览 / 保存（8 条）

| # | 方法 路径 | 行 | 入参 | 出参 | 鉴权 | 审计 |
| --- | --- | --- | --- | --- | --- | --- |
| 18 | GET /config | 698-729 | query sourceId,path | {file{sourceId,sourceType,sourceName,path,size,modifiedAt,etag,hash},document,summary,validation,writeEnabled} | — | 无 |
| 19 | GET /config/raw | 732-747 | query sourceId,path | {content,hash} | — | 无 |
| 20 | GET /config/summary | 750-778 | query sourceId,path | {file,**summary} | — | 无 |
| 21 | POST /config/export | 781-831 | ExportRequest（baseHash，可选operations） | application/yaml 附件下载（UTF-8 filename*）；哈希不符409 | 同源 | export（808/823） |
| 22 | POST /config/preview | 834-865 | PreviewRequest | {previewToken,beforeHash,afterHash,diff,validation}；冲突409、非法422 | 同源 | 无（预览不落盘） |
| 23 | POST /config/advanced/validate | 868-890 | RawYamlRequest（baseHash） | {document,validation}（不落盘） | 同源 | 无 |
| 24 | POST /config/preview/raw | 893-920 | RawYamlRequest | previewToken+diff（action=advanced-save，保留原始字节） | 同源 | 无 |
| 25 | POST /config/save | 923-977 | SaveRequest（previewToken） | {path,backupPath:None,beforeHash,afterHash,temporaryRecoveryCleaned}；只读403、预览过期410、来源消失/越界409；SaveCommitError→500{status,message,nextStep,backupPath,formalHash} | 同源 + write_enabled | save/restore（成功在 SaveService.commit；失败分支946-964） |

### 3.5 历史 / 备份（3 条）

| # | 方法 路径 | 行 | 入参 | 出参 | 鉴权 | 审计 |
| --- | --- | --- | --- | --- | --- | --- |
| 26 | GET /history | 980-998 | query sourceId,path | {backups[],audit[]}（camelCase：id/createdAt/sourceId/username/action/path/beforeHash/afterHash/backupPath/details） | — | 无 |
| 27 | POST /history/restore-preview | 1001-1031 | RestorePreviewRequest | previewToken+diff（action=restore，候选=备份原始字节）；backupPath 须属当前主文件否则422 | 同源 | 无（恢复审计在 save commit） |
| 28 | DELETE /history/backup | 1034-1073 | DeleteBackupRequest | {deleted,removedHistoryRecords}；仅当前主文件备份 | 同源 | delete-history（1066）+ delete_backup_records（1054） |

### 3.6 图标（2 条）

| # | 方法 路径 | 行 | 入参 | 出参 | 鉴权 | 审计 |
| --- | --- | --- | --- | --- | --- | --- |
| 29 | GET /icons/cache | 1076-1114 | query url(8..2048),sourceId,path | 图片字节（Cache-Control public,max-age=31536000,immutable） | — | icon-cache（1094/1103） |
| 30 | GET /icons/catalog | 1117-1129 | query force? | {items,personalItems,repositoryUrl,warning} | — | 无（写缓存文件） |

### 3.7 操作日志（4 条）

| # | 方法 路径 | 行 | 入参 | 出参 | 鉴权 | 审计 |
| --- | --- | --- | --- | --- | --- | --- |
| 31 | GET /logs | 1132-1168 | query sourceId?,path?,limit(1..5000默认100) | {logs,maxEntries,currentCount} | — | 无 |
| 32 | GET /logs/settings | 1171-1175 | 无 | {maxEntries,currentCount} | — | 无 |
| 33 | PUT /logs/settings | 1178-1184 | LogSettingsRequest（maxEntries 1..50000） | {maxEntries,currentCount} | 同源 | 无 |
| 34 | DELETE /logs | 1187-1193 | 无 | {cleared}；**故意不审计**（L1192 注释：后置条件必须0行） | 同源 | 无（故意） |

## 4. 关键数据流时序

### 4.1 结构化编辑 → 保存事务（核心）

```text
前端 setValue/insert/delete/move → 本地 document 立即应用 + operations 记录（stores/app.ts:458-510）
  → POST /api/config/preview {sourceId,path,baseHash,operations}
      后端 create_preview（save_service.py:94-126）：
        重读正式文件 + 哈希核对（不符→「配置文件已在其他位置发生变化」）
        → apply_operations（round-trip 树上）→ dump_candidate（dump 后再 load 校验）
        → validate_references → full_diff → previewToken（TTL900s，绑定 session_scope）
  → DiffModal 显示完整 Diff（含 password/secret/token/URL 原文，可信内网决策）
  → POST /api/config/save {previewToken}
      preview_store.take（校验 scope，过期410）
      write_enabled 门禁（False→403）
      commit（save_service.py:206-322）：
        1 重读正式哈希核对（不符→取消）
        2 validation.errors 阻断
        3 写同目录隐藏 .{filename}.rollback-<hex8>.yaml（当前字节）→回读→load→哈希核对→rollback_ready
        4 写 .tmp-<hex8>.yaml（候选）→回读→load→哈希核对
        5 storage.move(temp→正式,overwrite=True,保留目标原权限位)→回读正式→load→哈希核对
        6 成功：删 rollback；audit.record(action,before/after,backupPath=None,details)
        7 失败：删 temp；读正式哈希
            ==before → status unchanged（尽量删 rollback）
            rollback_ready → 写 .recovery-<hex8>.yaml→校验→move(recovery→正式)→回读==before → restored
            否则 → recovery_failed（保留 rollback 供人工）
  → 前端 clearDraft → 重新 fetchConfig → afterSaveAction 续动作
```

### 4.2 来源 probe-first

```text
SourceModal 表单 → POST /api/sources/probe（merged_candidate+validate+test_source_record）
  → 连通才发 probeToken（指纹=sha256(sorted JSON{type,name,config})，TTL600s）
  → 表单任何改动 deep watch 失效 probeToken（SourceModal.vue:99-108）
  → POST /api/sources 或 PUT /api/sources/{id} 带 probeToken
  → 后端 consume（一次性 compare_digest 指纹）→不符409「请先测试连接成功后再保存」
  → 空凭据保留后端原值；safe_data 剔除 username/password 返回
```

### 4.3 公开文件核对

```text
GET /api/publication/status?sourceId&path
  → PublicationVerifier.compare（publication.py:25-91）：
      GET 目录页 ?_fixcloud_refresh=<ms>（Accept:application/json，触发 Lucky 目录刷新）
      → stream GET {base}/{quote(filename)}?_fixcloud_verify=<ms>（no-cache，UA FixCloud-Panel/1.0，≤5MiB）
      → sha256(线上字节) vs sha256(当前文件)
  → matching/currentHash/publishedHash/publishedUrl/...
  → audit publication-check（success/failure）
  → 容器经 extra_hosts 把公开域名解析到 bridge IPv6 网关，由宿主 Lucky 本地投递（见 08/09）
```

### 4.4 订阅流量 / 节点 / VPS 用量

```text
订阅流量：从当前主配置 proxy-providers（type:http,url http(s)，≤20）→ HEAD 优先，无 subscription-userinfo 头再 stream GET
  → 解析 upload/download/total/expire（total<=0 视为无）→ used/remaining/remainingPercent/expireAt/remainingDays
  → TTL300s 缓存；不返回订阅 URL；不下载/更新订阅正文
订阅节点：拉取订阅 → YAML proxies 或 base64 URI 解析 → 只返回 {name,type}（≤500/provider，≤20 provider，8MiB）
VPS 用量（11-22）：并发 Evoxt（GET api.evoxt.com/listserver，BasicAuth public/private，params username/serviceid）
  + Vultr（GET api.vultr.com/v2/account/bandwidth，Bearer）→ 服务器套餐 GiB / 账号本月 GB
  → 未配置或失败→available:false+message，不显示假 0；never return credentials/raw provider responses
```

### 4.5 浏览器会话隔离

```text
首次请求无 cookie → new_token（token_urlsafe32）→ set_cookie（httponly/samesite=strict/会话级）
  → scope=sha256(token) → /data/temporary-sessions/<64hex> 目录 → ContextVar 绑定（请求级，finally unbind）
上传 temporary → 写本会话目录；审计/临时文件/预览/日志按 scope 过滤 → A 标签页不可见 B
cleanup_loop 每小时删过期（mtime>24h、名字=64hex、非符号链接、父目录==root）目录
```

## 5. 只读探测实证（2026-11-25）

| 接口 | 实测返回（脱敏） | 标注 |
| --- | --- | --- |
| GET /api/health | {status:ok,storage:ready,yaml:valid} | 【已验证】 |
| GET /api/sources | writeEnabled:true，default:default-smb，2 内置来源，default-smb readOnly:false | 【已验证】 |
| GET /api/files/catalog | FixCloud.yaml 20893B（11-19）、oixCloud.yaml 24012B（07-28） | 【已验证】 |
| GET /api/history?sourceId=default-smb&path=/FixCloud.yaml | backups:[]，audit 100 行（publication-check:32/save:41/icon-cache:27），camelCase 字段 | 【已验证】 |
| GET /api/logs/settings | maxEntries:500，currentCount:183 | 【已验证】 |
| GET /api/subscriptions/usage | 3 家全 available:true，不返回 URL | 【已验证】 |
| GET /api/vps/usage | 两台 available:false（IP 白名单），通用文案无 IP 泄漏 | 【已验证】 |

> 未探测（避免副作用/凭据）：GET /api/config（返回含 secret/password 的 document）、GET /api/publication/status（写审计）、GET /api/icons/cache（写审计+缓存）、GET /api/icons/catalog（写缓存文件）。全部写接口未调用。
