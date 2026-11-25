> 分类：我方已验证（来源：beam-web-product-guidelines 技能 design-system.md + FixCloud 当前源码 visual-refresh.css / style.css）
> 核实时间：2026-11-25

# 01 · 设计系统主干（当前生效 token）

## 结论先行
- **当前生效设计语言 = Nothing 风单色 + 红色 accent**，由 frontend/src/visual-refresh.css 定义并覆盖 style.css。【已验证】
- 技能 design-system.md 文本仍描述「浅灰底 + 白/微透圆角卡 + 克制阴影 + 蓝色主 accent」的旧语言；FixCloud 当前实现已演进为「不透明卡 + 零阴影 + 红色 accent」。这是 evolution-policy 里的 **current preference 演进**（accent/阴影/透明度可演进），不是违规，但技能文本措辞滞后。【已验证】
- 所有新模块 token 以 visual-refresh.css 为准；语义状态色（绿/琥珀/红）仍来自 style.css 且未被覆盖，继续生效。【已验证】

## 1. 生效色彩 token（visual-refresh.css:2-35）【已验证】
| token | LIGHT | DARK | 用途 |
|---|---|---|---|
| --app-bg | #f5f5f5 | #000 | 应用背景 |
| --card | #fff | #111 | 卡片背景（不透明） |
| --card-strong | #fff | #111 | 强卡片背景 |
| --text-primary | #171717 | #f4f4f4 | 主文字 |
| --text-muted | #626262 | #a4a4a4 | 次要文字 |
| --text-faint | #858585 | #858585 | 弱化文字 |
| --field-bg | #f0f0f0 | #1a1a1a | 字段/hover 底 |
| --separator | #e6e6e6 | #292929 | 分隔线/卡边框 |
| --nd-border | #ccc | #3c3c3c | 控件边框 |
| --nd-accent | #d71921 | #d71921 | 红色强调（dirty/激活导航条/移动 tab 点/focus） |
| --nd-inverse | #111 | #f4f4f4 | 主按钮底（反色） |
| --nd-inverse-text | #fff | #111 | 主按钮文字 |
| --shadow / --shadow-soft | none | none | 零阴影 |

来源：frontend/src/visual-refresh.css:2-19（:root）、:21-35（.dark）。

## 2. 基础层 token（style.css:3-27，已被 vr 覆盖，仅留档）【已验证】
| token | LIGHT（基础） | DARK（基础） |
|---|---|---|
| --app-bg | #f2f2f7 | #111318 |
| --card | rgba(255,255,255,0.9) | rgba(31,34,41,0.92) |
| --card-strong | #ffffff | #20232a |
| --text-primary | #16171a | #f6f7f9 |
| --text-muted | #73777f | #a8adb7 |
| --text-faint | #9ba0a8 | #747a86 |
| --field-bg | rgba(118,118,128,0.08) | rgba(118,118,128,0.2) |
| --separator | rgba(60,60,67,0.13) | rgba(235,235,245,0.12) |
| --shadow | 0 8px 28px rgba(36,40,52,0.07) | 0 8px 32px rgba(0,0,0,0.2) |

来源：frontend/src/style.css:3-14（:root）、:16-27（.dark）。这些值在运行时被 vr 同特异性更晚源序覆盖，**不生效**。

## 3. 字体【已验证】
| 角色 | 生效字体栈 | 来源 |
|---|---|---|
| UI 字体 --nd-font-ui | "Space Grotesk", "PingFang SC", -apple-system, sans-serif | visual-refresh.css:15、:37（body） |
| 数据字体 --nd-font-data | "Space Mono", "SF Mono", monospace | visual-refresh.css:16 |
| 基础 body（被覆盖） | Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Helvetica Neue", Arial, sans-serif | style.css:39-41 |

- 数据字体用于：eyebrow / section-title / stash-section-title（11px/400/.08em）、settings-row 末列（12px）、usage 数字、rule-row-type/target、mobile-tab、mobile-header-brand。【已验证】visual-refresh.css:52-58、:71、:121、:207-209、:251、:265-267。
- 中文排版：技能要求强中文可读、lineHeight ≥1.3、零字距（技能 design-system.md / compact-widget-design.md）。page-subtitle 14px/1.65。【已验证】style.css:112-118。
- page-title：clamp(26px,4vw,34px)，vr 改 font-weight 600、letter-spacing -.035em。【已验证】style.css:106-110 + visual-refresh.css:59。

## 4. 圆角【已验证】
| 元素 | 生效圆角 | 来源 |
|---|---|---|
| 卡类（ios-card/stash-group-card/usage-card/source-card/app-dialog-card/file-picker-panel/source-modal-panel/diff-panel/structured-group/structured-scalar/toggle-field） | 15px | visual-refresh.css:43-51 |
| 药丸按钮（soft/header-action/icon/editor-add/close/save） | 999px | visual-refresh.css:86-93 |
| 图标 tile（row-icon/entity-kind-icon） | 9px | visual-refresh.css:61-67 |
| source-icon | 10px | visual-refresh.css:79 |
| search-field/filter-button | 9px | visual-refresh.css:97-101 |
| usage-progress（配额条） | 0（方角） | visual-refresh.css:117-118 |
| desktop-nav-item | 8px | visual-refresh.css:182 |
| 基础 ios-card（被覆盖） | 20px | style.css:120-127 |

## 5. 间距与布局尺寸【已验证】
| 项 | 值 | 来源 |
|---|---|---|
| page-width（工作列） | max-width 1120px 居中 | style.css:91-95 |
| app-content（桌面） | padding 36px 32px 60px | visual-refresh.css:188 |
| app-content（移动） | padding 20px max(20px,safe) 36px | visual-refresh.css:232 |
| settings-row | min-height 70px | visual-refresh.css:70 |
| stash-form-row/toggle-row | min-height 62px（移动 64px） | visual-refresh.css:128、:275 |
| stash-form gap | 24px | visual-refresh.css:124 |
| more-link | min-height 72px | visual-refresh.css:150-152 |
| entity-row（移动） | min-height 72px | visual-refresh.css:264 |
| 桌面侧栏宽 | 244px | visual-refresh.css:171 |

## 6. 阴影与层级【已验证】
- **零阴影**：--shadow / --shadow-soft = none（visual-refresh.css:17-18、:33-34）；卡类 box-shadow:none、backdrop-filter:none（:49-50）。
- 层级靠 **边框 + 背景色** 而非阴影：卡 border 1px separator；hover 用 field-bg 底 + nd-border 边（visual-refresh.css:283-297，hover:hover+pointer:fine 下 transform:none 压平抬升）。
- 技能 design-system.md 仍写「restrained shadows / 轻微抬升」，当前实现已演进为零阴影平面化。属 current preference 演进。【已验证】
- 拖拽抬升例外：entity-row-dragging 仍用 scale 1.015 + 阴影（style.css，vr 的 hover transform:none 不影响 dragging 类）。【已验证】

## 7. 层级与强调【已验证】
- 行层级 = 前导 icon → 主名称 → 类型/摘要 → 尾部状态/计数 → chevron（技能 design-system.md「Cards and rows」；FixCloud SettingsRow/SectionView 实现）。
- eyebrow：vr 改为 text-muted + nd-font-data 11px/400/.08em（覆盖基础蓝 #0a84ff 12px/700）。visual-refresh.css:52-58 vs style.css:97-104。
- 彩色图标 tile 被压单色：row-icon/entity-kind-icon background transparent!important、color text-primary!important（visual-refresh.css:61-67）。EditorHomeView 的 bg-blue-500 等彩色 class 因此失效。【已验证】
- 主按钮：primary-button/editor-save-button-active = nd-inverse 底 + nd-inverse-text 字（visual-refresh.css:81-85）。
- 红色 accent 用途：editor-dirty-label（覆盖基础琥珀）、激活导航 ::before 3×18px 条、移动 tab active ::after 4px 点、focus outline 2px。visual-refresh.css:95-96、:184、:253、:39-42。

## 8. 暗色模式【已验证】
- 实现：.dark 类切换；唯一开关在 AppShell.vue:184-185（appStore.toggleTheme，Sun/Moon icon-button），设置页无重复开关（符合技能「one clear theme toggle in main header」）。
- 记忆：localStorage（fixcloud-theme），即时应用。【已验证】stores/app.ts + AppShell.vue。
- 应用面：卡/对话框/字段/分隔/图标/代码/hover/禁用全量（vr .dark 重定义全部 token）。
- **不一致点**：技能 design-system.md 写「Preserve contrast without using pure black everywhere」，但 vr 暗色 --app-bg = #000（纯黑）+ --card #111。当前实现用了纯黑背景。【已验证】visual-refresh.css:22。属 current preference 演进，建议在 07 记录并询问是否更新技能措辞。

## 9. 语义状态色（style.css，vr 未覆盖 → 生效）【已验证】
| 元素 | 亮色 | 暗色 | 来源 |
|---|---|---|---|
| status-chip-ok | 底 rgba(52,199,89,.14) 字 #21833b | 字 #63dc7f | style.css（status-chip） |
| status-chip-warn | 底 rgba(255,159,10,.16) 字 #b86500 | — | style.css |
| status-chip-off | 灰 | — | style.css |
| status-dot-ok | #34c759 + 4px 光晕 | — | style.css |
| status-dot-warn | #ff9f0a + 光晕 | — | style.css |
| danger-solid-button | #ff3b30 白字 radius12 | — | style.css |
| usage-quota-line span | #34844a | #69bb7a | visual-refresh.css:122-123 |
| log-status-ok / fail | #10b981 / #ef4444 | — | style.css |

- 注意：danger-solid-button 用 iOS 红 #ff3b30，与 vr accent #d71921 并存（两个红）。【已验证】
- 状态色必须配文字/图标（status-chip 带文字 + Check/XCircle 图标），符合技能「non-color status cues」。

## 10. 残留旧 iOS 蓝岛（vr 未覆盖 → 与全局单色红不一致）【已验证】
| 元素 | 旧蓝值 | 来源 |
|---|---|---|
| loading-orb（spinner） | border rgba(10,132,255,.15) / border-top #0a84ff | style.css:630-637 |
| empty-icon | bg rgba(10,132,255,.12) / color #0a84ff | style.css:551-559 |
| AdvancedYamlView .advanced-yaml-intro | border rgba(10,132,255,.2)/bg .07 | views/AdvancedYamlView.vue:93-97（scoped） |
| SubscriptionNodesView 整页 | #0a84ff 系（refresh/provider/分页/node-card） | views/SubscriptionNodesView.vue:174-195（scoped） |

- grep 确认 visual-refresh.css 无 loading-orb/empty-icon/0a84ff/advanced-yaml/subscription/reference-impact 命中 → 这些保留旧蓝。【已验证】
- ReferenceIntegrityModal 的琥珀 warning 属语义色（非旧蓝），合理保留。【已验证】
- 收敛建议见 07-evolution-policy.md。

## 11. 技能文本 vs 当前实现对照（演进记录）
| 维度 | 技能 design-system.md 措辞 | 当前生效（vr） | 性质 |
|---|---|---|---|
| 主 accent | 蓝色 | 红 #d71921 | current preference 演进【已验证】 |
| 阴影 | restrained shadows | none | current preference 演进【已验证】 |
| 卡片 | 白/微透 | 不透明 #fff/#111 | current preference 演进【已验证】 |
| 卡圆角 | （未指定具体） | 15px | 项目具体化【已验证】 |
| 暗色背景 | 非处处纯黑 | #000 纯黑 | 措辞滞后，建议询问【已验证】 |
| 紧凑面语言 | Nothing 单色/点阵（compact-widget-design.md 明确认可） | 全局单色红 | 与技能紧凑面方向一致【已验证】 |

> 注：技能 compact-widget-design.md 明确认可「Nothing-like monochrome/dot language」，故 vr 的单色方向与技能紧凑面偏好一致，只是被应用到全局。accent/阴影/透明度按 evolution-policy 属可演进的 current preference。
