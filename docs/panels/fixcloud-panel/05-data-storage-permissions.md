> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 05 · 数据存储、权限与凭据边界

**结论**：面板数据分两处——`/data`（应用状态/审计/缓存/会话）与 `/mnt/fixcloud`（SMB 配置共享，只读挂载默认、生产可写）。代码意图 `sources.json` 0600、原子写、凭据后端-only；**但 NAS 实测 /data 文件为 0770（QNAP ACL/umask 覆盖），sources.json 明文凭据在 NAS 上组可读**；config 共享混合属主，面板只能写自己属主的 FixCloud.yaml。普通保存不再生成永久备份。【已验证：源码 + NAS ls -la + docker inspect】

## 1. 存储布局

### 1.1 /data（APP_DATA_DIR，宿主 APP_DATA_HOST_PATH=<NAS_APP_DATA_PATH>）

| 路径 | 用途 | 实现 | 权限意图 | NAS 实测 |
| --- | --- | --- | --- | --- |
| sources.json | 来源记录（含明文 username/password） | source_store.py:153-178 | 0600 | **0770 BeamJason:everyone（516B）** |
| audit.sqlite3 | 审计日志 + app_settings | audit.py:18-49 | SQLite 默认 | 0770（61440B） |
| state.json | AppStateStore（**死代码遗留**） | app_state.py（无引用） | — | 0770（73B，可清理） |
| icon-cache/<sha256(url)>.bin/.json/.failed.json | 图标字节+元数据+失败标记 | icon_cache.py | 原子写 | 目录 0770 |
| icon-catalog/whatsinstash.json | 社区图标目录缓存 TTL24h | icon_catalog.py | — | 目录 0770 |
| temporary-sessions/<64hex>/ | 每浏览器会话临时目录（上传/审计 scope） | browser_session.py | 会话隔离 | **约 2911 子目录累积** |
| uploads/ | 遗留上传目录（现上传走会话目录） | — | — | 存在（Jul 26） |

> /data 全部条目 NAS 实测 0770（rwxrwx--- BeamJason:everyone），**非代码意图的 0600**。QNAP 共享 ACL/umask 在宿主侧覆盖了容器内 os.open 的 0o600。【已验证】

### 1.2 /mnt/fixcloud（STORAGE_ROOT，SMB bind，宿主 SMB_MOUNT_PATH=<NAS_CONFIG_SHARE_PATH>）

| 路径 | 属主:组 | 权限 | 面板可写？ |
| --- | --- | --- | --- |
| FixCloud.yaml（20893B，11-19） | BeamJason:everyone | 0770 | **是**（uid1000=BeamJason，gid100=everyone） |
| oixCloud.yaml（24012B，07-28） | admin:administrators | 0770 | **很可能否**（面板属 other→---）【推测/待验证】 |
| icon/ | admin | — | 只读（个人图标目录） |
| rules/ | admin | — | 只读（规则集，非配置目录直属→不可编辑） |
| 配置目录 config/ | admin:everyone | 0770 | 目录组 everyone rwx→可 stat/列出 |

> 面板以 PUID:PGID=1000:100（BeamJason:everyone）运行。**只能写自己属主的文件**；admin 属主文件正文读写 likely 失败（catalog 经目录组权限可列出，但打开正文需文件级权限）。oixCloud.yaml 未实际打开（避免凭据），结论为推测。【已验证属主/权限；推测可写性】

## 2. 文件权限与属主原则

| 原则 | 实现 | 行号 |
| --- | --- | --- |
| 以 NAS UID/GID 运行 | compose user "${PUID:-1000}:${PGID:-100}"，避免安全替换后文件变容器 UID | docker-compose.yml:9、README.md:36-38 |
| 保存保留目标原权限 | mounted.move overwrite 时先 stat 目标、写后 chmod 回原权限位 | storage/mounted.py:136-147 |
| 新建文件 0600 意图 | mounted.write_bytes O_EXCL/O_TRUNC 0o600+fsync；source_store os.open 0o600+chmod | mounted.py:97-111、source_store.py:153-178 |
| 越界拒绝 | _resolve：resolve 后必须在 root 内；smb/webdav 拒绝 ./.. | mounted.py:18-24、smb.py、webdav.py |
| 过滤系统垃圾 | list_dir 排除 ._*/.DS_Store/@eaDir | mounted.py:47 |
| 只编辑配置目录直属 YAML | is_editable_yaml_path：dirname=="/"、非点文件、不含 .backup-、.yaml/.yml | routes.py:137-151 |

## 3. 原子写与备份策略

### 3.1 原子写模式（统一：临时文件→校验→os.replace/move）

| 场景 | 机制 | 行号 |
| --- | --- | --- |
| sources.json | .tmp-<hex4> → O_WRONLY\|O_CREAT\|O_EXCL 0o600 → fsync → os.replace → chmod 0o600 | source_store.py:153-178 |
| 存储写入 | write_bytes O_EXCL（不覆盖）/O_TRUNC（覆盖）0o600+fsync；失败删半文件 | mounted.py:97-111 |
| 图标缓存 | .tmp-<hex8> → replace；成功清失败标记 | icon_cache.py |
| 保存事务 | 同目录隐藏 .{filename}.rollback-<hex8>.yaml / .tmp-<hex8>.yaml / .recovery-<hex8>.yaml | save_service.py:215-226 |

### 3.2 保存事务三态（save_service.commit，206-322）

```text
1 重读正式哈希核对（不符→取消，「正式文件已变化」）
2 validation.errors 阻断
3 写 rollback（当前字节，overwrite=False）→回读→load→哈希核对→rollback_ready
4 写 temp（候选）→回读→load→哈希核对
5 storage.move(temp→正式,overwrite=True,保留原权限)→回读正式→load→哈希核对
6 成功：删 rollback；audit.record(backupPath=None)
7 失败：删 temp；读正式哈希
    ==before → unchanged（尽量删 rollback）
    rollback_ready → 写 recovery→校验→move(recovery→正式)→回读==before → restored
    否则 → recovery_failed（保留 .rollback- 供人工）
```

### 3.3 备份策略演进（重点）

| 行为 | 当前实现 | 行号 |
| --- | --- | --- |
| **普通保存不再生成永久备份** | 成功 backupPath=None；不创建 *.backup-*.yaml | save_service.py:308/318、README.md:115 |
| 旧版备份仍可管理 | list_backups 扫 {filename}.backup-*.yaml 按名倒序 | save_service.py:324-343 |
| 恢复用备份原始字节 | create_restore_preview 候选=备份字节，不重 dump | save_service.py:165-172 |
| 失败恢复副本保留 | recovery_failed 时 .rollback- 留盘供人工 | save_service.py:296 |
| 删除备份双重确认 | DELETE /history/backup + delete_backup_records + delete-history 审计 | routes.py:1034-1073 |

> FixCloud.yaml 实测 backups:[]（无遗留备份）。HistoryView.vue:105 文案「普通保存不再自动创建新备份」与后端一致。【已验证】

## 4. 凭据处理与脱敏边界

| 边界 | 规则 | 行号 |
| --- | --- | --- |
| 来源凭据后端-only | SENSITIVE_FIELDS={username,password}；safe_data 剔除；API /sources 不返回 | source_store.py:16,39-51 |
| 持久化明文 | sources.json 存明文 username/password（0600 意图，NAS 实测 0770） | source_store.py:153-178、test_source_store 断言 |
| 编辑空凭据保留原值 | update 空敏感值不覆盖 | source_store.py:204-234 |
| 浏览器存储不含凭据 | rawYamlDraft 绝不写 sessionStorage（注释凭据安全）；仅存 operations 草稿+选择 | stores/app.ts:337-354 |
| 审计不记凭据/YAML 值 | details 仅 operations/changedLines/warnings/status/message；哈希空 | audit.py:71-102 |
| 订阅不返回 URL | subscription_usage/nodes 只返回用量/name/type，测试断言无 URL/server/password | subscription_usage.py、subscription_nodes.py |
| VPS 不返回凭据/原始响应 | vps_usage docstring「never return credentials or raw provider responses」 | vps_usage.py:11 |
| **Diff 完整显示敏感值** | password/secret/token/URL 在 Diff 原文显示（可信内网决策，非脱敏） | README.md:117、yaml_service.full_diff、test_yaml_service |
| 前端密码遮罩 | isSecret 正则 /(password\|passwd\|secret\|token\|authorization\|api[-_]?key)/i → password 输入+眼睛切换 | StructuredField.vue:19-21、StashParameterRow.vue:102-119 |
| 图标 URL 公网校验 | DNS 解析后仅公网 IP，唯一例外 RFC2544 198.18.0.0/15（Fake-IP）；重定向≤4跳每跳重校验 | icon_cache.py:20,74-77,159-183 |

> **关键区分**：来源连接凭据（SMB/WebDAV username/password）严格后端-only；但**被编辑的 YAML 正文内的 secret/password/token/订阅 URL 在 Diff 与 GET /config 中原文可见**——这是可信内网的明确决策（README.md:117），不是漏洞，但意味着公开下载的 FixCloud.yaml 含凭据（见 09/10 硬红线）。【已验证】

## 5. 审计表结构（audit.sqlite3）

### 5.1 audit_log 表（audit.py:24-40）

| 列 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK AUTOINCREMENT | 自增 |
| created_at | TEXT | UTC ISO |
| username | TEXT | 固定「内网访问」（无登录） |
| action | TEXT | save/restore/export/upload/delete-file/delete-history/connection-test/icon-cache/publication-check |
| path | TEXT | 文件路径 |
| before_hash | TEXT | 保存前 sha256（record_event 空） |
| after_hash | TEXT | 保存后 sha256 |
| backup_path | TEXT | 失败恢复副本路径（成功 None） |
| details | TEXT | JSON：operations/changedLines/warnings/status/message |
| source_id | TEXT DEFAULT 'legacy' | 迁移新增（来源隔离） |
| session_scope | TEXT DEFAULT '' | 迁移新增（仅 uploaded-files 记 sha256(token)） |

### 5.2 app_settings 表（audit.py:41-49）

| key | value | 说明 |
| --- | --- | --- |
| audit_limit | 500（默认） | 保留条数上限，1..50000 |

### 5.3 审计行为

| 行为 | 规则 | 行号 |
| --- | --- | --- |
| 会话隔离 | 仅 uploaded-files 记 session_scope；list_recent WHERE session_scope='' OR 当前 scope | audit.py:71-92,104-132 |
| 裁剪 | 插入后按 limit 删旧行；DEFAULT_LIMIT=500、MAX_LIMIT=50000 | audit.py:12-13 |
| 查询上限 | list_recent limit≤5000 | audit.py:104-132 |
| 删备份联动 | delete_backup_records 删引用该备份的审计行 | audit.py:134-148 |
| 清空 | clear 只删行不删文件；**DELETE /logs 故意不审计**（后置条件必须 0 行） | audit.py:179-185、routes.py:1192 |
| API 序列化 | DB snake_case → API camelCase（createdAt/sourceId/beforeHash/afterHash/backupPath） | routes.py:980-998（实测） |

> 实测：maxEntries:500、currentCount:183；FixCloud.yaml 审计 100 行（publication-check:32/save:41/icon-cache:27）。【已验证】

## 6. 会话临时目录清理

| 项 | 规则 | 行号 |
| --- | --- | --- |
| 目录命名 | /data/temporary-sessions/<sha256(token) 64hex> | browser_session.py |
| TTL | 24h（mtime 过期） | browser_session.py:13 |
| 清理条件 | 名字=64hex、非符号链接、父目录==root、mtime 过期 | browser_session.py:65-87 |
| 周期 | cleanup_loop 每小时（lifespan 启动） | browser_session.py:90-96、main.py:27-35 |
| **实测问题** | 约 2911 子目录累积，24h 清理有效性存疑 | NAS ls（链接数 2913）【待验证】 |
