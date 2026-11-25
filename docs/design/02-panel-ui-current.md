> 分类：我方已验证（来源：FixCloud 当前源码 /Users/beamjason/Documents/BeamNat/fixcloud-panel/frontend）
> 核实时间：2026-11-25

# 02 · FixCloud 当前 UI 实现事实

## 结论先行
- **当前生效视觉层 = visual-refresh.css**（Nothing 风单色红），style.css 为基础结构+语义色层。判定证据见下。【已验证】
- 布局：桌面持久左侧栏 244px + 有界居中工作列 1120px；移动全屏 + 底部 4 tab。【已验证】
- 导航：桌面 6 项（来源/编辑/流量/节点/历史/设置），移动 4 tab（编辑/来源/流量/更多）。【已验证】
- 技术栈：Vue 3 + TypeScript + Vite 7 + Tailwind 4 + Pinia 3 + vue-router 4 + lucide-vue-next 图标 + vitest。【已验证】

## 1. 生效视觉层判定与证据（重点）
| 证据 | 内容 | 来源 |
|---|---|---|
| import 顺序 | 先 import "./style.css" 再 import "./visual-refresh.css"，后者更晚加载 | frontend/src/main.ts:13-14 |
| token 覆盖 | vr 以同特异性（:root/.dark）更晚源序重定义全部 CSS 自定义属性 → vr 值胜出 | visual-refresh.css:2-35 vs style.css:3-27 |
| 组件覆盖 | vr 直接覆盖 .ios-card/.eyebrow/.page-title/.row-icon/.primary-button 等，部分 !important | visual-refresh.css:43-123 |
| 字体覆盖 | body font-family 改为 var(--nd-font-ui) | visual-refresh.css:37 |
| 字节数 | style.css 65531 字节/3338 行；visual-refresh.css 13914 字节/301 行 | 只读 wc -c |
| 残留岛 | vr 未覆盖 loading-orb/empty-icon/advanced-yaml/subscription/reference-impact（grep 无命中）→ 保留旧蓝/ scoped 样式 | grep visual-refresh.css |

**判定结论**：全局 chrome（卡/按钮/字体/token/导航/表单）= vr 单色红语言；style.css 仍提供布局结构 + 语义状态色（status-chip/dot 绿琥珀红，未被覆盖）+ 残留旧蓝岛。不存在「style.css 是生效层」的情况。【已验证】

## 2. 技术栈（package.json）【已验证】
| 类别 | 依赖 | 版本 |
|---|---|---|
| 框架 | vue | ^3.5.0 |
| 路由 | vue-router | ^4.5.0 |
| 状态 | pinia | ^3.0.0 |
| 图标 | lucide-vue-next | ^0.468.0 |
| 样式 | tailwindcss / @tailwindcss/vite | ^4.0.0 |
| 构建 | vite | ^7.0.0 |
| 语言 | typescript | ~5.8.0 |
| 类型检查 | vue-tsc | ^3.0.0 |
| 测试 | vitest | ^3.2.4 |
| 插件 | @vitejs/plugin-vue | ^6.0.0 |

scripts：dev=vite，build=vue-tsc -b && vite build，typecheck=vue-tsc -b，test=vitest run。
来源：frontend/package.json。与技能 delivery-workflow.md 偏好基线（Vue3+TS+Vite+Tailwind）一致。后端 FastAPI 不在前端包内（独立）。

## 3. 布局结构（AppShell.vue，253 行）【已验证】
| 区域 | 内容 | 来源 |
|---|---|---|
| 离线横幅 | !online 时 fixed top z50 bg-amber-500 黑字 WifiOff「网络已断开，草稿保留在本机，保存已禁用」 | AppShell.vue:119-125 |
| desktop-sidebar | 品牌「NAS 配置中心」uppercase tracking.22em + 「FixCloud」xl bold；6 导航项；底部状态卡 status-dot + 后端已连接/仅读取界面预览 + 内网访问 | AppShell.vue:127-155 |
| app-header | mobile-header-brand（NAS CONFIG CENTER / FixCloud / 连接点）；header-context（FileSelector + h1 title）；header-actions（上传/导出/主题切换） | AppShell.vue:158-189 |
| app-content | !backendReachable && !file.hash → empty-card 重新连接（bootstrap）；否则 RouterView | AppShell.vue:191-201 |
| mobile-tabbar | 4 tab，aria-label 主导航 | AppShell.vue:204-215 |
| app-toast | Transition role=status | AppShell.vue:216-218 |
| 上传模态 | Teleport modal-layer，选择上传方式：config（写入配置目录，冲突自动安全后缀）/ temporary（会话隔离） | AppShell.vue:219-230+ |

- 主题切换唯一开关：AppShell.vue:184-185（appStore.toggleTheme）。【已验证】
- 上传流程：openUploadChooser → uploadMode temporary/config → uploadYaml → requestDraftTransition(selectFile) → notify「已添加并打开 X」/「已添加 X，但未打开；当前草稿保持不变」。busy 锁。【已验证】AppShell.vue:55-93。
- 导出流程：promptDialog 导出文件名 → exportYaml。busy 锁。【已验证】AppShell.vue:95-114。

## 4. 导航结构
### 路由（router/index.ts，42 行，createWebHashHistory）【已验证】
| 路径 | 名称 | 视图 |
|---|---|---|
| / | redirect /sources | — |
| /sources | 文件来源 | SourcesView |
| /files | 文件浏览器 | FilesView |
| /editor | 可视化编辑器 | EditorHomeView |
| /editor/advanced-yaml | 高级 YAML 修改（lazy） | AdvancedYamlView |
| /editor/:section | 配置项目 | SectionView |
| /editor/:section/item/:itemId | 参数编辑 | ItemEditorView |
| /usage | 机场流量 | UsageView |
| /more | 更多 | MoreView |
| /subscription-nodes | 订阅节点 | SubscriptionNodesView |
| /history | 配置历史 | HistoryView |
| /settings | 系统设置 | SettingsView |

### 桌面侧栏 navItems（6）【已验证】AppShell.vue:35-42
来源 FolderKanban / 编辑 FileSliders / 流量 Gauge / 节点 Network / 历史 Clock3 / 设置 Settings。
### 移动 tabbar mobileNavItems（4）【已验证】AppShell.vue:43-48
编辑 / 来源 / 流量 / 更多 MoreHorizontal。/more 聚合 /more、/subscription-nodes、/history、/settings（isMobileNavActive）。
### MoreView（36 行）【已验证】
eyebrow「CONTROL / 04」+ page-title「工具与状态。」；链接行=订阅节点/配置历史/系统设置；状态卡=后端连接/YAML 文件/访问方式「内网访问」。

## 5. 组件清单与职责（26 个，frontend/src/components/）【已验证】
| 组件 | 职责 |
|---|---|
| AppShell | 应用外壳：侧栏/头部/移动 tab/离线横幅/上传导出/主题/toast |
| FileSelector | 当前文件下拉选择器：搜索/分组/切换/删除（双重确认+fallback 检查） |
| SourceModal | 文件来源新增/编辑（SMB/WebDAV，凭据只留后端） |
| GroupCard | 分组卡容器（标题 + ios-card slot） |
| SettingsRow | 标准设置行（icon/标题/描述/尾值/chevron） |
| EditorTopBar | 详情页顶栏（左返回/中标题/右添加或保存，dirty 指示） |
| SaveBar | 底部草稿条（N 项未保存 + 预览保存→Diff + 放弃），dirtyCount>0 显示 |
| DiffModal | 完整 Diff 评审（校验 ok/error/warn + diff-code + 确认并保存→commitPreview + 恢复副本说明） |
| UnsavedChangesModal | dirty 过渡三选（保存并继续/放弃/取消）+ 放弃二次确认 |
| AppDialogHost | 应用对话框宿主（confirm/prompt，Teleport，非 native） |
| ReferenceIntegrityModal | 删除引用完整性（扫描影响 + 移除/替换选择，琥珀 warning） |
| StructuredField | 结构化字段递归编辑器（保留未知字段） |
| StructuredValueModal | 复杂值全屏/面板编辑（StructuredField 递归 + 完成） |
| ObjectParameterEditor | 对象参数编辑（按 EditorGroup 分组 + 常用/高级 + complex→导航行） |
| PrimitiveParameterEditor | 原始值编辑（单行 StashParameterRow，multiline→textarea） |
| StashParameterGroup | 参数分组卡（标题 + group-card slot + help） |
| StashParameterRow | 参数行（label 左 value 右，text/number/password/select/toggle/textarea，showSecret，openUrl） |
| StashNavigationRow | 导航行（label+description+value+chevron，进下级） |
| GeneralSettingsEditor | 通用设置（监听端口/局域网/运行设置分组） |
| DnsSettingsEditor | DNS 设置（基础键 + 列表键→导航行 + 未知键→StructuredField） |
| ProxyGroupEditor | 策略组编辑（类型/成员/图标/筛选） |
| ProxyGroupMemberPicker | 策略组成员双栏选择器（已选/可选拖拽 + 搜索 + 自定义 URL） |
| ProxyGroupIcon | 策略组图标（后端缓存代理 /api/icons/cache，Waypoints 兜底） |
| RuleFieldEditor | 规则字段编辑（内容→目标关系） |
| RegexFilterBuilder | 正则筛选构建器（地区预设/关键词→生成预览+中文描述） |
| IconCatalogPicker | 图标目录选择器 |

## 6. 视图清单与职责（11 个，frontend/src/views/）【已验证】
| 视图 | 职责 |
|---|---|
| SourcesView | 主配置来源卡（测试连接/浏览/编辑/删除）+ 会话临时文件 + 当前文件 |
| FilesView | 文件浏览器（/api/files，打开→draftGuard→selectFile→/editor） |
| EditorHomeView | 可视化编辑器首页（分组卡：通用/代理/规则/扩展/选项，计数+chevron） |
| SectionView | 配置项目列表（搜索/筛选/拖拽排序/添加，general/dns→专用编辑器） |
| ItemEditorView | 参数编辑（按类型分派编辑器，删除走引用完整性，重命名保键序） |
| AdvancedYamlView | 高级 YAML 修改（textarea + 语法检查 + Diff，保留旧蓝 intro） |
| UsageView | 机场流量监控卡（订阅+VPS 配额，hero 剩余%，新鲜度，缓存标记） |
| SubscriptionNodesView | 订阅节点（provider 列表 + node-card 网格 + 分页，整页保留旧蓝） |
| HistoryView | 配置历史（备份查看 Diff/恢复/删除 + 操作日志，普通保存不自动建备份） |
| SettingsView | 系统设置（连接/文件发布/日志保留/安全/操作日志） |
| MoreView | 更多（工具链接 + 状态卡） |

## 7. 关键交互（详见 03）【已验证】
- dirty 守卫：main.ts:19-38 router.beforeEach + composables/draftGuard.ts（requestDraftTransition / saveAndContinue→createPreview / discardAndContinue 先导航后清草稿）。
- 保存进 Diff：SaveBar 预览保存 / EditorTopBar Save → createPreview → DiffModal（校验+diff+临时恢复副本回读）→ commitPreview。
- 拖拽排序：SectionView startDrag/dropOn → moveValue + notify「已移动到第 N 位」+ suppressOpen 120ms。
- 引用完整性：ItemEditorView deleteItem → scanDeleteImpact → requestReferenceDelete → 移除/替换。
- 重命名保键序：renameMapItem（JSON 快照→setValue 新键→moveValue 恢复序→deleteValue 旧键→router.replace）。
- 异步 busy：loading/busy/saving/testing/deletingPath 锁 + disabled 防重复。

## 8. 与规范不一致之处（发现）
| 项 | 现状 | 规范期望 | 标注 |
|---|---|---|---|
| 残留旧蓝岛 | loading-orb/empty-icon/AdvancedYaml/SubscriptionNodes 用 #0a84ff | 全局单色红（vr） | 【已验证】不一致，建议收敛（07） |
| 暗色纯黑 | vr --app-bg #000 | 技能「非处处纯黑」 | 【已验证】措辞滞后，建议询问 |
| 小触达控件 | SubscriptionNodes 分页 29×29/refresh 40px；mini-order-button 28×25；drag-handle 28×36 | 技能 ≥~44×44 | 【已验证】部分低于 44 |
| 两个红 | danger-solid-button #ff3b30 与 accent #d71921 并存 | 单一 accent | 【已验证】语义红 vs 强调红，可接受但需记录 |
| 底部 SaveBar | save-bar fixed bottom（移动位；桌面 left calc(250+32)） | 技能「禁底部固定保存条作桌面主保存」 | 【推测】SaveBar 触发 Diff 评审而非静默写，桌面详情主保存仍是 EditorTopBar 右上 Save；是否违规取决于解释，待验证 |
| 技能 accent 措辞 | 技能写蓝，实现红 | current preference 可演进 | 【已验证】演进合理，文本滞后 |
