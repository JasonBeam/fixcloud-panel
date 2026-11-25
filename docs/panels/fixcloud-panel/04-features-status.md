> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 04 · 功能清单与状态

**结论**：面板核心功能（来源管理、结构化编辑、事务保存、历史、审计、订阅流量/节点、图标、发布核对、PWA）均已实现并在生产运行；**VPS 用量为 11-22 新增但生产不可用（厂商 IP 白名单）**；**sing-box 集成仅停留在研究/设计，尚未实施**。存在若干权限/脱敏/清理类已知问题。【已验证：源码 + 只读探测 + docs 研究报告】

## 1. 现有功能清单

| 功能 | 说明 | 关键实现 | 状态 |
| --- | --- | --- | --- |
| 多来源管理 | NAS 主机挂载 SMB（默认）、SMB 直连、WebDAV、会话上传；probe-first 连通才保存 | source_store.py、registry.py、SourceModal.vue | 【已验证】生产仅 2 内置来源 |
| 连接测试 | 延迟 latencyMs、测试时间 testedAt、明确错误分类 | routes.py:185-218、smb.py | 【已验证】 |
| 文件浏览/选择 | 仅列配置目录直属 .yaml/.yml，不递归；每标签页独立选择 | routes.py:221-248、FilesView.vue、stores/app.ts | 【已验证】 |
| 结构化编辑 | 10 分类：general/dns/proxies/proxy-providers/proxy-groups/rules/rule-providers/rewrite/script/other | EditorHomeView/SectionView/ItemEditorView | 【已验证】 |
| round-trip 保留 | 注释/顺序/引号/未知字段/列表顺序不丢失 | yaml_service.py:40-45 | 【已验证】test_save_service 断言 |
| 代理协议表单 | ss/vmess/vless/trojan/socks5/hysteria/hysteria2/tuic；schema 驱动分组 | editorSchemas.ts:21、ObjectParameterEditor.vue | 【已验证】 |
| 策略组编辑 | 5 类型含 relay；成员三入口 proxies/use/include-from-url；include-all；filter/exclude-filter；懒人地区筛选；图标 | ProxyGroupEditor.vue、RegexFilterBuilder.vue | 【已验证】 |
| 规则编辑 | 规则字符串⇄结构化双向；14 类型；no-resolve/hidden/remark；逻辑规则整条 raw | RuleFieldEditor.vue | 【已验证】 |
| 高级 YAML 模式 | 原始字节编辑，不自动格式化，校验通过才进 Diff | AdvancedYamlView.vue、save_service.py:128-159 | 【已验证】 |
| 完整 Diff + 校验 | unified_diff、引用检查（重名/悬空引用/RULE-SET）、errors 阻断保存 | yaml_service.py:170-260、DiffModal.vue | 【已验证】 |
| 事务化安全保存 | rollback/temp/recovery 三隐藏文件 + 多重回读哈希 + 三态恢复 + 保留原权限 | save_service.py:206-322、mounted.py:136-147 | 【已验证】test 故障注入 |
| 引用完整性守卫 | 删除前扫描直接引用/嵌套链/警告；cancel/keep/remove/replace | referenceIntegrity.ts、ReferenceIntegrityModal.vue | 【已验证】 |
| 草稿守卫 | 路由切换/关闭/续编辑三模式；放弃二次确认 | draftGuard.ts、UnsavedChangesModal.vue | 【已验证】 |
| 历史/备份恢复 | 列旧版 *.backup-*；恢复用备份原始字节；删备份双重确认 | save_service.py:324-343、HistoryView.vue | 【已验证】FixCloud.yaml backups:[] |
| 操作日志 | 按来源+文件过滤；limit 1..50000；清空（故意不审计）；不记录凭据/YAML 值 | audit.py、SettingsView.vue | 【已验证】currentCount:183 |
| 订阅流量 | proxy-providers subscription-userinfo 头；HEAD 优先；不返回 URL；不更新订阅 | subscription_usage.py | 【已验证】3 家可用 |
| 订阅节点 | YAML/base64 URI 解析；只返回 name/type；分页/筛选/搜索 | subscription_nodes.py、SubscriptionNodesView.vue | 【已验证】 |
| **VPS 用量（11-22 新增）** | Evoxt（HK 服务器套餐 GiB）+ Vultr（JP 账号本月 GB）；未配置不显示假 0 | vps_usage.py、UsageView.vue:171-197 | 【已验证】功能存在；**生产 available:false** |
| 图标缓存/目录 | 后端持久缓存（公网 IP 校验，Fake-IP 例外）；WHATSINStash 社区目录 + 个人图标 | icon_cache.py、icon_catalog.py、IconCatalogPicker.vue | 【已验证】 |
| 公开文件核对 | Lucky 目录刷新 + 流式 GET + sha256 比对线上 YAML | publication.py、SettingsView.vue | 【已验证】audit publication-check:32 |
| 导出/上传/删除 | 导出原字节或带 operations；上传双模式（config/temporary）；删除 expectedHash 守卫 | routes.py:528-831、AppShell.vue | 【已验证】 |
| PWA / 响应式 | standalone 可安装；iPhone 安全区域/底部 4tab；Mac 侧栏 6 导航/宽屏双栏；输入 16px 防缩放 | manifest、visual-refresh.css、AppShell.vue | 【已验证】 |
| Nothing 风视觉 | 扁平单色+红强调（#d71921）、Space Grotesk/Space Mono、无阴影 | visual-refresh.css（main.ts:14 后导入） | 【已验证】当前生效 |
| 深色模式 | matchMedia prefers-color-scheme + localStorage 主题 | stores/app.ts、visual-refresh.css .dark | 【已验证】 |
| 离线处理 | 断网保内存草稿、禁保存、离线横幅；恢复网络续编辑 | stores/app.ts:600-612、AppShell.vue:120-125 | 【已验证】 |
| 密码字段遮罩 | isSecret 正则自动 password 输入 + 眼睛切换 | StructuredField.vue:19-21、StashParameterRow.vue | 【已验证】 |

## 2. 待开发功能（仅研究/设计，尚未实施）

| 功能 | 设计要点 | 来源 | 状态 |
| --- | --- | --- | --- |
| sing-box 集成 | asyncssh 2.24.1 纯 Python SSH 直连 VPS IPv4（容器 read_only+cap_drop ALL 装不了 openssh-client）；官方镜像 ghcr.io/sagernet/sing-box:v1.14.4 钉 tag + 独立 bridge + 显式端口 + /etc/sing-box bind | docs 研究报告 §0 | 【已验证】未实施（routes 无 sing-box 路由、settings 无 SSH 字段） |
| 自建节点 MVP | SS2022（2022-blake3-aes-128-gcm TCP+UDP 高位端口）；阶段2 VLESS+Reality（TCP 非443）；阶段3 Hysteria2（UDP443 需抬 sysctl 缓冲） | docs §0 | 【推测】规划，未实施 |
| 私有订阅端点 | 自建 Clash YAML 端点 + subscription-userinfo 头 + 支持 HEAD；不做 base64（Verge 拒收）；URL 高熵 token 可轮换 | docs §3.5 | 【推测】规划 |
| 自建凭据隔离 | 节点密码/UUID/Reality 私钥/订阅 token 绝不进公开 FixCloud.yaml；选项A（推荐）节点只存后端+私有订阅端点 | docs §0.1/§3.6 | 【推测】规划，**当前公开文件仍含凭据** |
| sing-box 校验 | 用官方 sing-box check，不复用 Clash yaml_service 链 | docs §0 | 【推测】规划 |
| 节点流量统计 | 官方 clash_api /connections /traffic /proxies/{name}/delay；experimental.v2ray_api 按用户计数官方构建不可用（需自编译）；MVP 只做连接级总量+诚实标注 | docs §3.5 | 【推测】规划 |
| VPS IP 白名单放行 | 把 NAS 出口 IPv4 加入 Vultr/Evoxt 控制台白名单（账号侧，须 Beam 本人） | docs §0.1 | 【待验证】修复后 VPS 用量才可用 |

## 3. 已知问题

| 问题 | 影响 | 证据 | 状态 |
| --- | --- | --- | --- |
| VPS 用量生产不可用 | 两台 available:false；厂商 API 拒绝 NAS 出口 IPv4（Vultr 401 Unauthorized IP、Evoxt IP Address Unauthorized） | GET /api/vps/usage + inspect 5 env 键已注入 + docs §0.1 | 【已验证】非缺 env，是 IP 白名单 |
| 公开 FixCloud.yaml 含凭据 | 公开域名无鉴权可读，含回家 socks5 username/password、**3 个 proxy-provider 中 2 个 URL 带 query token**（11-25 复核：Kycloud/DlerCloud 带，Youtu 不带）、external-controller secret | docs §0.1（11-24 已验证 200/20893B） | 【已验证】硬红线，自建凭据绝不进公开文件 |
| /data 文件实际 0770 | sources.json 明文凭据在 NAS 上组（everyone）可读，代码意图 0600 未落盘（QNAP ACL/umask） | NAS ls -la /data | 【已验证】权限偏差 |
| oixCloud.yaml 面板很可能不可写 | admin:administrators 0770，面板 uid1000/gid100(everyone) 属 other→---；catalog 可列出但正文读写 likely 失败 | NAS ls config 共享 | 【推测/待验证】未实际打开（避免凭据） |
| temporary-sessions 大量累积 | 约 2911 子目录（链接数 2913），24h 清理有效性存疑 | NAS ls /data | 【已验证】数量；【待验证】清理是否生效 |
| demo 页含真实 LAN（**当前未对外暴露**） | public/demo/nothing-*.html 的 mock 数据硬编码真实家庭 LAN 子网/网关与真实域名；**生产 GET /demo/nothing-full.html 与 /demo/nothing-iphone.html 均 404**（11-25 实测），故当前不经 HTTP 暴露；风险在于文件仍在源码树与本地 dist/，纳管即固化 | nothing-iphone.html:154,161、nothing-full.html:409,426；HTTP 404 实测 | 【已验证】纳管必改/排除 |
| 代码硬编码真实域名/IP | settings.py:28、SettingsView.vue:46,200、IconCatalogPicker.vue:173、SourceModal.vue:248-249 | grep | 【已验证】纳管必脱敏 |
| 源 .env.example 缺 VPS env 键 | EVOXT_*/VULTR_API_KEY 不在 .env.example/compose，仅生产 NAS .env 注入；新部署者无从得知 | grep + inspect EnvKeys | 【已验证】文档/配置缺口 |
| 外部 Google Fonts 依赖 | 内网离线/被墙时字体回退，视觉降级 | index.html:14-16 | 【已验证】依赖；【推测】离线影响 |
| HTTP 非安全上下文 | LAN HTTP 无 Service Worker 离线缓存；断网仅内存草稿 | README.md:125 | 【已验证】设计取舍 |
| app_state.py 死代码 | AppStateStore/state.json 无引用，遗留文件占位 | grep 全 backend/app 无引用 + NAS state.json 73B | 【已验证】可清理 |
| 图标目录外部上游 | 依赖 GitHub `shindgew/WHATSINStash`：**第三方公开仓库**（owner=shindgew，非 Fork，license=null，11-25 gh API 核实），**不是参考项目作者的仓库**；无许可证 → 只运行时引用 URL，不复制其资产 | icon_catalog.py:14-15；gh api repos/shindgew/WHATSINStash | 【已验证】外部依赖 |

## 4. 功能验证状态汇总

- **已验证（生产运行 + 源码 + 只读探测一致）**：核心编辑/保存/来源/历史/审计/订阅/图标/发布核对/PWA。
- **已验证存在但生产不可用**：VPS 用量（IP 白名单）。
- **推测/待验证**：oixCloud.yaml 写权限、temporary-sessions 清理有效性、sing-box 全部规划功能。
- **未覆盖**：任何写接口的实际执行（只读审计禁止）；UI 实机目视验收（见 07 清单，需 Beam 本人在 Mac Safari/iPhone 执行）。
