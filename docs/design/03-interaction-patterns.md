> 分类：我方已验证（来源：beam-web-product-guidelines 技能 interaction-patterns.md / data-safety.md + FixCloud 当前源码）
> 核实时间：2026-11-25

# 03 · 交互规范

## 结论先行
- 信息架构按用户任务组织，集合走 **overview → item list → item detail**。【已验证】
- 详情页头部：左返回 / 中标题 / 右上 Save；dirty 时标题下「有未保存修改」；**保存必须进 Diff 评审，禁静默写**。【已验证】
- dirty 过渡三选（保存并继续 / 放弃 / 取消）+ 放弃二次确认；新目标加载成功后才清旧草稿。【已验证】
- 每个异步动作即时 busy + 防重复；成功绿 / 失败红 + 时间/延迟；错误转清晰中文，禁 [object Object]。【已验证】
- 凭据只留后端，不返前端 / 不进 LocalStorage / 不进常规日志。【已验证】

## 1. 信息架构（技能 interaction-patterns.md + FixCloud router）
| 规则 | 内容 | 来源 |
|---|---|---|
| 按任务组织 | 不按后端 schema / 技术模块；overview 带类别/计数/状态/下一步 | 技能 interaction-patterns.md【已验证】 |
| 集合三级 | overview → item list → item detail | 技能；FixCloud /editor → /editor/:section → /editor/:section/item/:itemId【已验证】 |
| 列表页 | 左返回 / 中类别标题 / 右添加 / 搜索筛选 / 紧凑行 / 拖拽排序 | 技能；SectionView 实现【已验证】 |
| 列表页禁全局保存 | 不在集合列表页放全局保存按钮 | 技能 interaction-patterns.md【已验证】 |
| 首页分组 | EditorHomeView 分组卡（通用/代理/规则/扩展/选项）带计数+chevron | views/EditorHomeView.vue【已验证】 |

## 2. 详情页头部（技能 + EditorTopBar）
| 规则 | 内容 | 来源 |
|---|---|---|
| 头部布局 | 左上 close/back，中类型/标题，右上 Save | 技能；EditorTopBar【已验证】 |
| dirty 指示 | 仅 dirty 时标题下「有未保存修改」小指示 | 技能；editor-dirty-label（vr 红色）【已验证】 |
| Save 态 | 未改禁用/弱，改后高亮 | 技能；editor-save-button-active【已验证】 |
| 保存进 Diff | 完整性重要时 Save 进 review/Diff，禁静默写 | 技能；SaveBar/DiffModal【已验证】 |
| 禁底部主保存 | 不用底部固定保存条作桌面主保存入口 | 技能 interaction-patterns.md【已验证】 |

- FixCloud 现状：桌面详情主保存 = EditorTopBar 右上 Save；另有全局 SaveBar（底部草稿条）触发「预览保存」→ Diff。SaveBar 非静默写，而是 Diff 入口。【已验证】SaveBar.vue:34-36。是否构成「底部主保存」取决于解释。【推测】见 02 第 8 节。

## 3. 表单布局（技能 field-type 映射 + FixCloud 实现）
| 类型 | 控件 | FixCloud 实现 |
|---|---|---|
| string | 右侧文本输入 | StashParameterRow kind=text【已验证】 |
| number | 数字输入 | kind=number（Number 或 ""）【已验证】 |
| boolean | 右侧开关 | kind=toggle（checked）【已验证】 |
| enum | 值 + chevron/select | kind=select【已验证】 |
| URL | 输入 + open/test | openUrl→ExternalLink【已验证】 |
| password | 掩码 + 显示切换 | kind=password + showSecret（Eye/EyeOff）【已验证】 |
| 单引用 | 可搜索选择器 | ProxyGroupMemberPicker / suggestions【已验证】 |
| 多引用/list | 计数 + chevron 进管理器 | StashNavigationRow→StructuredValueModal / ProxyGroupMemberPicker【已验证】 |
| key/value 对象 | 结构化编辑器 | StructuredField【已验证】 |
| nested 对象 | 下级结构化页 | StructuredValueModal 递归【已验证】 |
| code | 同卡同头代码区 | AdvancedYamlView textarea / PrimitiveParameterEditor multiline【已验证】 |

- 分组：按功能在白圆角卡内分组（StashParameterGroup）。label 左、value 右；enum 右对齐 + chevron 贴值；label 下仅短决策帮助。【已验证】技能 + StashParameterRow.vue。
- **保留未识别字段**进高级结构化编辑器（ObjectParameterEditor advancedFields / StructuredField）；非用户显式要求不以 raw YAML/JSON 为主界面。【已验证】技能 interaction-patterns.md + ObjectParameterEditor.vue。
- editorSchemas.ts 定义 EditorField/EditorGroup（proxyEditorGroups/proxyProviderGroups/ruleProviderGroups/rewriteEditorGroups/scriptEditorGroups）。【已验证】utils/editorSchemas.ts。

## 4. dirty 态与保存进 Diff 评审（核心）
### 4.1 保存事务（技能 data-safety.md 11 步）【已验证】
1 重读目标验 sourceID/path/ETag-hash/session → 2 内存中仅施加意图结构化变更 → 3 按隐私决策生成完整 Diff → 4 校验语法+交叉引用 → 5 仅项目策略要求时建备份 → 6 写临时目标 → 7 回读校验 → 8 原子/安全替换正式 → 9 回读正式验 hash/内容 → 10 失败报告正式文件未动/已恢复/需人工 → 11 记录有用结果不泄凭据。
- 禁未读正式+证明就称「已恢复」；history/logs 按 source+file 作用域；从原始备份字节恢复非 parse-dump。【已验证】技能 data-safety.md。

### 4.2 FixCloud 实现【已验证】
| 步骤 | 实现 | 来源 |
|---|---|---|
| 草稿条 | SaveBar dirtyCount>0 显示「N 项未保存 / 保存前将显示完整 Diff」+ 预览保存（createPreview）+ 放弃（confirmDialog danger） | SaveBar.vue:21-37 |
| Diff 评审 | DiffModal：校验 ok「YAML 与引用检查通过」/ error「引用检查未通过」/ warn「提示」+ diff-code + 恢复副本说明 | DiffModal.vue:45-76 |
| 安全保存 | 确认并保存（disabled saving||errors>0）→ commitPreview；saving「正在安全保存…」 | DiffModal.vue:81-87 |
| 失败状态卡 | saveFailure → save-outcome-card（message + nextStep + backupPath「可用恢复副本」） | DiffModal.vue:31-44 |
| 备份策略 | 「保存时会使用临时恢复副本并回读确认，成功后自动清理」；普通保存不自动建持久历史备份 | DiffModal.vue:60 + HistoryView.vue【已验证】 |

- 项目备份策略与技能 data-safety 第 5 步一致（「仅项目策略要求时建备份」）：FixCloud 用临时恢复副本+回读+成功自动清理，历史备份显式管理。【已验证】

### 4.3 dirty 过渡守卫（draftGuard）【已验证】
| 机制 | 内容 | 来源 |
|---|---|---|
| 路由守卫 | operations.length>0 && from /editor && to≠from → requestDraftTransition（switch/continue） | main.ts:19-38 |
| 三选 | 保存并继续 / 放弃修改 / 取消（actionText 按 close/switch/continue 模式） | UnsavedChangesModal.vue:15-31、:65-73 |
| 放弃二次确认 | askDiscardConfirmation → confirmingDiscard →「确认放弃修改？放弃后无法恢复 N 项草稿」→ discardAndContinue | UnsavedChangesModal.vue:48-85 |
| 保存并继续 | saveAndContinue：afterSaveAction=pendingAction → createPreview（进 Diff） | draftGuard.ts:52-60 |
| 先导航后清草稿 | discardAndContinue：await action()（导航/加载）→ await discardChanges() | draftGuard.ts:66-80 |
| 路由 bypass | allowNextRoute / consumeRouteBypass | draftGuard.ts:18-26 |

- 技能：「Clear the old draft only after the new target loads successfully」→ discardAndContinue 先 action 后 discard，符合。【已验证】
- 同守卫用于 item/file/source/nav 退出（SectionView closeSection、FilesView open、SourcesView removeTemporaryFile、AppShell upload）。【已验证】
- 浏览器 refresh/close：用 beforeunload 警告 + 保留草稿（技能；页面卸载后无法自定义对话框）。【待验证】FixCloud beforeunload 具体实现未逐行核对。

## 5. 异步 busy 与防重复【已验证】
| 动作 | busy 锁 | 来源 |
|---|---|---|
| 订阅流量刷新 | if loading return；loading ref；refresh 按钮 disabled | UsageView.vue:106-126、:148 |
| 来源测试连接 | testing ref；「测试中…」+ LoaderCircle spin | SourcesView.vue:210-213 |
| 上传/导出 | busy ref；disabled | AppShell.vue:59-80、:105-113 |
| 保存 | saving；DiffModal 确认 disabled | DiffModal.vue:83 |
| 删除备份 | deletingPath 行级 busy | HistoryView.vue:157-161 |
| 发布核对 | busy 锁「尝试核对/核对中…」 | SettingsView.vue【已验证】 |
| 日志清空 | 双重 confirmDialog danger | SettingsView.vue【已验证】 |

技能：「Every asynchronous action needs an immediate busy state and duplicate-click protection」。【已验证】

## 6. 成功/失败反馈【已验证】
- 成功绿 / 失败红 + 时间/延迟（技能）。FixCloud：status-chip-ok/warn、status-dot、source-test-feedback（连接成功+时间+latency ms）、publication-result（ok/mismatch + hash 前 12 位 + latency ms）。【已验证】
- toast：app-toast role=status（AppShell.vue:216-218）；notify 轻完成语「已移动到第 N 位」。【已验证】
- 空态 + 恢复动作：empty-card「暂无匹配项目/调整搜索条件或点击右上角添加」、UsageView「没有可读取的订阅」、AppShell「暂时无法连接后端 + 重新连接」。【已验证】
- 离线：AppShell 离线横幅「网络已断开，草稿保留在本机，保存已禁用」（技能「offline prevent remote save retain local」）。【已验证】AppShell.vue:119-125。

## 7. 错误中文化【已验证】
- 技能：后端对象/技术异常 → 清晰中文，禁 [object Object]；区分认证失败/路径缺失/超时/冲突/校验失败/未变更/已恢复/需人工。
- FixCloud 实例：「无法读取订阅流量」「暂时无法读取 VPS 流量」「没有可切换的正式 YAML，无法删除当前临时文件；文件未删除，当前编辑状态保持不变」「未执行静默草稿清除」「X已经存在」「此项目已不存在，可能已被删除」。【已验证】UsageView/SourcesView/ItemEditorView。
- AdvancedYamlView：「若语法有误，会显示 YAML 提供的行、列和中文原因；未通过 Diff 确认前不会写入正式文件」。【已验证】

## 8. 凭据只留后端【已验证】
- 技能 data-safety.md：SMB/WebDAV 密码仅后端；禁 secret 返前端/LocalStorage/常规日志；常规 UI 掩码，可信本地环境尊重显式全 Diff 请求。
- FixCloud：SettingsView 安全卡「连接凭据仅由后端读取，不返回浏览器」+ Shield；日志「持久化记录，不包含连接凭据」；SourceModal 凭据只留后端。【已验证】SettingsView.vue + SourceModal.vue。
- 公开文件服务域名在源码 SettingsView.vue:46/200 含真实值 → 本产出以 <PLACEHOLDER> 掩码。【已验证】

## 9. 列表与排序【已验证】
- 搜索 + 有意义筛选；安静拖拽柄；拖拽抬升阴影+缩放、邻行平滑；重排留草稿至 save/review；轻完成语「已移动到第 4 位」。【已验证】技能 + SectionView.vue:340-529。
- 内容风格：去掉「规则 1」泛名（有有意义内容时）；关系摘要「内容 → 目标」（rule-row-content → rule-row-target）；紧凑上下文帮助非冗长横幅；破坏性视觉分离 + 确认点名精确目标。【已验证】技能 + SectionView/ItemEditorView。

## 10. 对话框【已验证】
- 应用对话框（appDialog confirm/prompt）非 native prompt/confirm（技能）。AppDialogHost Teleport role=dialog aria-modal；prompt 自动聚焦 + Enter 确认 + Esc 取消；按钮 min-h-11=44px。【已验证】AppDialogHost.vue。
- 破坏性双重确认：FileSelector remove（第一重列文件/来源/路径，第二重「最终确认删除」含 dirty 警告）；SettingsView clearLogs（第一重明示只删日志，第二重报条数+无法恢复）。【已验证】
