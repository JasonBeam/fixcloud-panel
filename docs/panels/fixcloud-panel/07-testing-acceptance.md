> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 07 · 测试规范与验收流程

**结论**：后端 13 个 pytest 文件（含 11-22 新增 test_vps_usage）+ 前端 6 个 vitest 文件，范式统一（TestClient + dependency_overrides 沙箱 + MockTransport + 故障注入）。**构建成功/接口 200 ≠ 验收完成**；须按本清单完成本地验证、部署前后哈希核对与 Mac Safari/iPhone 实机目视。本次只读审计**未执行任何测试或写接口**，测试清单为源码核实，实机验收待 Beam 本人执行。【已验证：tests 源码 + pyproject + package.json】

## 1. 后端测试清单（backend/tests，13 文件 + 2 fixture）

| 文件 | 行数 | 覆盖要点 |
| --- | --- | --- |
| test_api.py | 186 | 无同源标记 POST→403；CSP img-src；document 含 secret/password 原文（内网决策）；来源=[default-smb,uploaded-files]；rules 子目录选择/恢复→422；preview set port→diff；save→backupPath None、无 *.backup-*/.rollback-*；audit username 内网访问；请求级文件选择无全局状态 |
| test_save_service.py | 231 | 成功保留注释/未知字段/原权限 0o666、temporaryRecoveryCleaned；raw preview 精确字节；冲突备份前中止；**三故障注入**：FailTemporaryWrite→unchanged、CorruptAfterReplace→restored、FailRecovery→recovery_failed 保留 .rollback-；restore 用备份原始字节；重复保存无备份累积 |
| test_session_upload_delete_log_settings.py | 173 | cookie httponly/samesite=strict/path=/ 无 max-age；temporary/config 双模式上传、同名 -1、无 /data/uploads；**A/B 会话隔离**（catalog/config/summary/usage/export/preview/logs/delete 全断言）；delete expectedHash 不符 409/子目录 422/备份名 422；cleanup 只删过期 64hex；审计 limit 默认 500/改 3 裁剪/50001→422/清空只删行 |
| test_source_store.py | 132 | 凭据后端-only（safe_data 无 username/password；sources.json 0600 含明文——持久化事实）；迁移剔除 default-webdav 保留用户 webdav；configDirectory 补默认；更新空凭据保留原值 |
| test_icon_cache.py | 122 | 缓存命中不二次下载；并发共享 digest 锁只下载 1 次无 .tmp 残留；Fake-IP 198.18.42.9 放行；127/10/172.16/192.168/169.254/192.0.2 拒绝；HTML→格式错误 |
| test_icon_catalog.py | 95 | updated→cached 只请求 1 次；url 重写 public_base/icon/；personalItems 分离 |
| test_publication.py | 37 | no-cache 头；目录刷新 Accept json；matching True；publishedUrl |
| test_subscription_usage.py | 88 | userinfo 解析（total 缺失→None）；content-disposition 两格式；used/remaining/percent/days；不返回订阅 URL |
| test_subscription_nodes.py | 42 | YAML/base64 URI 只返回 name/type；不泄漏 server/password/URL |
| test_upload_export_logs.py | 138 | 上传唯一化/非法 YAML 422 不落盘/会话隔离；export 原字节（CRLF 保留）与 operations；logs 按文件过滤；icon-cache 审计带 sourceId/path、missing-source→404 |
| **test_vps_usage.py（11-22 新增）** | 33 | mock Evoxt/Vultr；scope 区分（服务器套餐 GiB vs 账号本月 GB）；expiry/upload/download 语义；password/secret 不回传；未配置不显示假 0 |
| test_yaml_service.py | 62 | sample summary 计数 + round-trip 不变；mapping move 保 provider 内容；full_diff 保留敏感值（内网决策） |
| test_storage.py | 18 | mounted 列目录 + 越界 read 拒绝 |
| fixtures/FixCloud.sample.yaml | 66 | 脱敏样例（secret masked-example、example.invalid URL、公共 DNS、gstatic generate_204） |
| fixtures/rules/AdBlock.yaml | 2 | 规则集夹具 |

## 2. 前端测试清单（vitest，6 文件，全部 example.com 占位）

| 文件 | 行数 | 覆盖 |
| --- | --- | --- |
| composables/draftGuard.test.ts | 42 | 延迟动作失败不清草稿；守卫仍 open |
| utils/sourcePresentation.test.ts | 75 | formalSources 排除 upload；临时分组条件；删除守卫条件 |
| utils/proxyGroup.test.ts | 52 | 成员排除自引用；provider subtitle；normalizeMemberList；健康检查类型 |
| utils/regexPreset.test.ts | 41 | (?i)+lookahead；关键词转义（GPT+→GPT\+）；全部/排除；中文描述 |
| utils/editorSchemas.test.ts | 40 | proxy type 8 种；provider health-check/override=complex；rule-provider behavior/format |
| utils/referenceIntegrity.test.ts | 27 | 删 provider 找直接引用 + 嵌套链；删唯一 MATCH 警告兜底 |

## 3. 测试范式

| 要素 | 做法 |
| --- | --- |
| 后端框架 | pytest + pytest-asyncio（asyncio_mode="auto"，pyproject） |
| 沙箱注入 | TestClient(app) + app.dependency_overrides[get_settings] → tmp_path Settings(storage_backend="local", write_enabled=True)；finally 清 overrides |
| 外部模拟 | httpx.MockTransport 模拟厂商/订阅/图标/Lucky；monkeypatch env/DNS |
| 故障注入 | Storage 子类模拟写失败/替换后损坏/恢复失败，验证三态 |
| 断言重点 | 凭据不回传、会话隔离、round-trip 保留、原子写无残留、权限保留、审计裁剪 |
| 前端框架 | vitest run；纯函数/composable 单测，example.com 占位无真实凭据 |
| 配置 | pyproject：pythonpath=["."]、testpaths=["tests"]；package.json：test=vitest run |

## 4. 本地验证命令（README.md:129-140）

```bash
# 前端
cd frontend
npm ci
npm run typecheck      # vue-tsc -b
npm test               # vitest run
npm run build          # vue-tsc -b && vite build（生产构建）

# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest -q
```

> 本次只读审计**未执行**上述命令（避免改动源项目 .venv/缓存）。命令为源码核实的标准流程。【已验证命令存在；未执行】

## 5. 部署前后核对项

| 阶段 | 核对项 | 期望 |
| --- | --- | --- |
| 部署前 | 本地 typecheck/单测/生产构建/后端 pytest 全绿 | 无失败 |
| 部署前 | 备份 compose + 关键目录（先例 .bak-20261117/backup-*-20261122） | 备份存在 |
| 部署前 | .env 键齐全（含 5 厂商键）、SMB/data 属主匹配 PUID:PGID | FixCloud.yaml 属主=面板 UID |
| 部署前 | 记录权威数据哈希：GET /api/config/raw 的 hash | 留存基线 |
| 部署后 | GET /api/health | {status:ok,storage:ready,yaml:valid} |
| 部署后 | GET /api/sources | writeEnabled 符合预期、来源 connected |
| 部署后 | GET /api/files/catalog | 文件 size/hash 与基线一致（未意外改动） |
| 部署后 | docker inspect（只读） | StartedAt 更新、Mounts RW、ExtraHostsCount=1、healthcheck healthy |
| 部署后 | 保存事务验证（受控）：preview→save→回读 hash | afterHash 匹配、无 .rollback-/.tmp- 残留、backupPath None |
| 部署后 | 公开核对 GET /api/publication/status | matching（extra_hosts 生效） |

## 6. UI 验收清单（Mac Safari + iPhone 实机，待 Beam 执行）

| 类别 | 检查项 |
| --- | --- |
| 视觉 | Nothing 风扁平单色 + 红强调（#d71921）；Space Grotesk/Space Mono 加载（离线回退是否可接受）；卡片 radius 15 + 1px 边框无阴影 |
| 响应式 | 桌面≥960 侧栏 244px/双栏；移动<960 底部 4tab + safe-area；输入 font-size 16px 防 iOS 缩放；diff-panel 移动全屏 100dvh |
| 深色模式 | matchMedia + localStorage 切换；.dark 变量（--app-bg #000/--card #111） |
| 状态覆盖 | loading（booting orb）/empty（无文件）/offline（横幅 + 禁保存）/failure（SaveFailure 四态卡 + backupPath 提示）/dirty（SaveBar + 顶栏标记） |
| 编辑流 | 10 分类入口；结构化表单；高级 YAML 不自动格式化；拖拽排序；引用完整性删除守卫（cancel/keep/remove/replace）；草稿守卫三模式 |
| 保存流 | Diff 完整显示（含敏感值，内网决策）；errors 阻断确认；warnings≤8；保存成功 clearDraft + 回读；失败三态文案 |
| 来源 | probe-first（改动失效 token）；连接测试延迟；编辑空凭据保留；内置不可删 |
| 用量 | 订阅流量 3 家；VPS 区块（生产 available:false 文案，不显示假 0）；订阅节点分页/筛选 |
| 历史/设置 | 备份恢复/删除双重确认；审计过滤/limit/清空；公开核对 matching |
| PWA | iPhone 添加到主屏幕 standalone；safe-area；theme-color |
| console | 无报错；网络请求带 X-FixCloud-Request（非 GET）；无凭据泄漏到浏览器存储 |

> **验收原则**（beam-web-product-guidelines）：编译成功、接口 200、文件存在都不等于实机验收完成；须区分「已构建/已部署/已实机验证」。本次审计仅完成源码核实 + 只读接口探测，**UI 实机验收未执行**。【已验证原则；实机待验证】
