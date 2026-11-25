> 分类：我方已验证（来源：beam-web-product-guidelines 技能 design-system.md + FixCloud visual-refresh.css / AppShell.vue 当前源码）
> 核实时间：2026-11-25

# 05 · Mac 与 iPhone 适配

## 结论先行
- **Mac**：持久左侧栏 244px + 有界居中工作列 1120px；宽主区，参数编辑用聚焦单工作列。【已验证】
- **iPhone**：真实产品表面非缩小桌面；全屏详情页 + 底部 4 tab；safe-area；大触达；单手可达。【已验证】
- 断点：min-width 960px 桌面 / max-width 959px 移动；hover:hover+pointer:fine 精细指针；prefers-reduced-motion。【已验证】
- 触达目标 ≥~44×44 CSS px；移动输入 font-size 16px 防 iOS 缩放。【已验证】

## 1. 断点总表（visual-refresh.css）【已验证】
| 媒体查询 | 作用 | 来源 |
|---|---|---|
| min-width 960px | 桌面侧栏/头部/内容/顶栏 | visual-refresh.css:169-193 |
| max-width 959px | 移动头部/品牌/文件选择器/tabbar/全屏详情/Diff | visual-refresh.css:195-281 |
| hover:hover and pointer:fine | 精细指针 hover（bg field-bg/border nd-border/transform none） | visual-refresh.css:283-298 |
| prefers-reduced-motion: reduce | 全部 animation/transition .01ms | visual-refresh.css:299-301 |

## 2. Mac 布局（min-width 960px）【已验证】
| 项 | 值 | 来源 |
|---|---|---|
| desktop-sidebar | width 244px，bg card，backdrop-filter none | visual-refresh.css:170-174 |
| 侧栏品牌 | nd-font-data 11px/.12em + 名 23px/600 | visual-refresh.css:175-181 |
| desktop-nav-item | radius 8px/500；active bg field-bg + ::before 3×18px nd-accent 条 | visual-refresh.css:182-184 |
| app-main | margin-left 244px | visual-refresh.css:185 |
| app-header | min-height 92px，padding 18px 32px，h1 20px/600 | visual-refresh.css:186-187 |
| app-content | padding 36px 32px 60px | visual-refresh.css:188 |
| editor-home | page-title 38px，desktop-two-column gap 24，ios-card radius 15 | visual-refresh.css:189-191 |
| editor-topbar | top 104px（sticky） | visual-refresh.css:192 |
| page-width | max-width 1120px 居中（基础） | style.css:91-95 |

- 技能：持久左导航 + 宽主区；工作列舒适居中有界，避免表单行横跨整屏；双列仅用于比较/导航，参数编辑通常单工作列。【已验证】技能 design-system.md「Desktop and Mac」。
- 技能：Mac Safari 一等评审目标；hover 轻反馈（抬升/阴影/淡蓝/chevron 动）但不改布局尺寸。当前 vr 已演进为 hover bg field-bg + transform none（零抬升）。【已验证】

## 3. iPhone 布局（max-width 959px）【已验证】
| 项 | 值 | 来源 |
|---|---|---|
| app-header | relative grid minmax(0,1fr) auto，gap 18/12，border 0，bg app-bg，blur none，padding 22+safe-top | visual-refresh.css:196-205 |
| mobile-header-brand | span 11px nd-font-data/.13em；strong 21px/600 -.03em；small 10px；i 6px 点（connected #34844a / disconnected nd-accent） | visual-refresh.css:206-212 |
| header-action-button | 44×44，隐文字 span | visual-refresh.css:214-215 |
| file-selector-trigger | 全宽 pill min-height 50，border nd-border radius 999，15px/400 | visual-refresh.css:218-231 |
| app-content | padding 20px max(20px,safe) 36px | visual-refresh.css:232 |
| editor-home-mobile-hero | h2 clamp(36,10vw,46)/1.07/500 -.055em；desktop-two-column block | visual-refresh.css:234-237 |
| mobile-tabbar | 4 列，bg card，blur none，padding 7+safe-bottom | visual-refresh.css:244-250 |
| mobile-tab | min-height 50，radius 0，nd-font-data 10px faint；active text-primary + ::after 4px nd-accent 点 | visual-refresh.css:251-253 |
| app-main | padding-bottom calc(80px+safe-area) | visual-refresh.css:254 |
| editor-topbar | top 0，min-height 70，margin 0 0 28，border 0 radius 0 bg app-bg | visual-refresh.css:255 |
| editor-close/add | 44×44；save min-height 44 | visual-refresh.css:256-261 |
| editor-workspace/detail | max-width none（全宽） | visual-refresh.css:262 |
| entity-row | min-height 72 | visual-refresh.css:264 |
| 输入字号 | stash-form/search/filter/form-field input/select/textarea font-size 16px!important（防 iOS 缩放） | visual-refresh.css:268-270 |
| stash-form-row | min-height 64 | visual-refresh.css:275 |
| DiffModal | 全屏 100dvh，border 0 radius 0；diff-header padding-top safe；diff-actions padding-bottom safe | visual-refresh.css:277-280 |

- 技能：iPhone 用 safe-area insets、大触达、卡组、全屏详情页、底部 tab/紧凑抽屉；重要动作单手可达；全屏 list/param/Diff 非挤压桌面对话框。【已验证】技能 design-system.md「iPhone and responsive behavior」。
- FixCloud 移动导航 4 tab（编辑/来源/流量/更多），/more 聚合节点/历史/设置。【已验证】AppShell.vue:43-53。

## 4. 44px 触达【已验证】
| 控件 | 移动尺寸 | 来源 |
|---|---|---|
| header-action-button | 44×44 | visual-refresh.css:214 |
| editor-close/add-button | 44×44 | visual-refresh.css:256-260 |
| editor-save-button | min-height 44 | visual-refresh.css:261 |
| mobile-tab | min-height 50 | visual-refresh.css:251 |
| AppDialogHost 按钮 | min-h-11=44 | AppDialogHost.vue |
| UnsavedChangesModal 按钮 | min-h-12=48 | UnsavedChangesModal.vue |
| DiffModal 按钮 | min-h-12=48 | DiffModal.vue:80-82 |

- 技能：触达 ≥~44×44 CSS px。【已验证】
- **不一致点**：SubscriptionNodesView 分页按钮 29×29、refresh 40px；mini-order-button 28×25；drag-handle 28×36 —— 低于 44。【已验证】views/SubscriptionNodesView.vue:174-195 + style.css。建议收敛（07）。
- 参考项目 design-review 亦指出小控件触区紧（<44px 不自动 WCAG 失败，需查间距例外）——见 06（参考提炼）。

## 5. safe-area【已验证】
| 位置 | inset | 来源 |
|---|---|---|
| app-header（移动） | padding-top calc(22px+env(safe-area-inset-top))，左右 max(20px,safe) | visual-refresh.css:204 |
| app-content | 左右 max(16/20px,safe) | style.css:88 + visual-refresh.css:232 |
| mobile-tabbar | padding-bottom calc(8px+env(safe-area-inset-bottom))，左右 max(7px,safe) | visual-refresh.css:249 |
| app-main | padding-bottom calc(78/80px+safe-area) | style.css:66 + visual-refresh.css:254 |
| DiffModal | diff-header padding-top max(20px,safe-top)；diff-actions padding-bottom max(16px,safe-bottom) | visual-refresh.css:279-280 |
| index.html | viewport-fit=cover | frontend/index.html【已验证】 |

## 6. 全屏详情 vs 桌面对话框【已验证】
- 移动 DiffModal 全屏 100dvh（visual-refresh.css:277-280）；StructuredValueModal 移动全屏（max-699）；桌面为居中面板。
- 技能：全屏 list/param/Diff 确认页，非挤压桌面对话框。【已验证】

## 7. 显式移动控件（拖拽不可靠处）【已验证】
- 技能：「Retain explicit move controls where drag-only interaction would be unreliable on touch devices」。
- FixCloud：SectionView 拖拽（drag-handle GripVertical）+ mini-order-button（上/下移）作为显式移动控件。【已验证】SectionView.vue + style.css。
- 注意 mini-order-button 28×25 低于 44（见第 4 节不一致）。【已验证】

## 8. 响应式结构化（技能）【已验证】
- 技能 delivery-workflow.md：「Keep responsive behavior structural, not a collection of late overrides」。
- FixCloud 现状：vr 用 min-960/max-959 媒体查询覆盖基础 style.css。【已验证】
- 【推测】vr 作为覆盖层本身是「late overrides」模式，与技能「结构化响应式」偏好存在张力；但这是既有视觉语言迭代的现实产物（07）。新模块应直接在生效层内结构化设计响应式，避免再叠覆盖层。

## 9. 参考提炼小节（非我方验证，需重新验证）
> 分类：参考提炼（来源：JimmyChan233/homelab 经授权 Fork；详见 06）
| 参考思想 | 抽象描述 | 标注 |
|---|---|---|
| 移动首页顺序 | 状态 → 异常 → 服务入口 → 详细仪表；避免重复健康状态占据首屏 | 【参考提炼·需重新验证】 |
| 导航溢出提示 | 横滑导航补明显延续提示或合理换行，不隐藏滚动条 | 【参考提炼·需重新验证】 |
| 相对时间 | 一律相对时间（7s/3m/2h），悬浮才绝对值 | 【参考提炼·需重新验证】 |
- 来源：fork-clone/reports/status-20261116/design-review.md、fork-clone/scripts/dashboard/README.md。
