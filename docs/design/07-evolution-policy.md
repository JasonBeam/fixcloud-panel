> 分类：我方已验证（来源：beam-web-product-guidelines 技能 evolution-policy.md / SKILL.md + FixCloud visual-refresh.css 演进先例）
> 核实时间：2026-11-25

# 07 · 演进策略

## 结论先行
- **在既有生效视觉语言上迭代，不推倒重写**。FixCloud 的先例：visual-refresh.css 作为覆盖层叠在 style.css 基础之上，重定义 token + 压平组件，而非重写基础。【已验证】
- **新增模块必须复用当前生效层**（visual-refresh.css 的 --nd-* token / 卡 radius15 / 药丸按钮 / nd-font-data eyebrow / style.css 语义状态色），不得重新引入旧 iOS 蓝。【已验证】
- 偏好分三层（core / current / project exception）；仅在用户显式要求时更新技能；一次性实验不升为持久规则。【已验证】技能 evolution-policy.md。
- 残留旧蓝岛与措辞滞后是已知技术债，按最小范围收敛，不借机扩大重构。【已验证】

## 1. 偏好三层（技能 evolution-policy.md）【已验证】
| 层 | 含义 | 例 |
|---|---|---|
| core preference | 反复确认的稳定价值 | 清晰、克制卡设计、显式保存评审、iPhone 一等、保权威数据 |
| current preference | 可演进的视觉/交互方向 | 卡透明度、间距、accent 色、导航处理、阴影 |
| project exception | 仅适用于一个产品/实验的刻意选择 | FixCloud 的 YAML/Clash 特定流程 |

- accent/阴影/透明度属 current preference → FixCloud 从蓝/克制阴影/微透卡演进到红/零阴影/不透明卡是合法演进。【已验证】
- 安全规则（data-safety）属稳定 core，除非用户显式定范围改，否则保留。【已验证】

## 2. 技能更新规则（技能 evolution-policy.md）【已验证】
| 规则 | 内容 |
|---|---|
| 显式触发 | 仅在「以后都这样 / 加入我的 Web Skill / 替换之前的规范 / 更新我的审美」等显式请求后更新技能 |
| 不升一次性 | 不把一次性实验升为持久规则 |
| 冲突处理 | 新持久偏好与既有冲突 → 指出冲突 + 问替换/收窄/条件并存 |
| 保安全 | 保稳定安全规则除非显式定范围改 |
| 技术中立 | 措辞技术中立除非真依赖框架 |
| 记录流程 | 定类 → 改最小节 → 移除/收窄冲突过时 → 验证 → 告知用户改了什么+影响哪些未来项目 |
| 无 changelog | 技能内不维护 changelog；当前文件=当前真相 |

## 3. FixCloud visual-refresh 演进先例（可复用模式）【已验证】
| 维度 | 做法 | 来源 |
|---|---|---|
| 叠加而非重写 | 新增 visual-refresh.css 覆盖层，main.ts 在 style.css 之后 import | main.ts:13-14 |
| token 重定义 | vr :root/.dark 重定义全部自定义属性 + 新增 --nd-* | visual-refresh.css:2-35 |
| 组件压平 | 卡 radius15/零阴影/零 blur；按钮药丸；图标单色；eyebrow 数据字体 | visual-refresh.css:43-123 |
| 响应式覆盖 | min-960/max-959 媒体查询覆盖基础布局 | visual-refresh.css:169-281 |
| 保留语义色 | status-chip/dot 等语义状态色留在 style.css 未覆盖，继续生效 | style.css |
| 基础留档 | style.css 旧 token/组件保留作结构基础，不删除 | style.css |

- **优点**：迭代可逆（移除 vr 即回退基础），不破坏既有结构/语义色。【已验证】
- **代价/技术债**：覆盖层模式产生残留岛（vr 未覆盖的 scoped 样式/旧蓝组件），且与技能「响应式结构化非晚期 override 堆」偏好存在张力。【已验证】
- **homelab-panel 建议**：新工程可直接把生效语言作为唯一基础层（结构化设计 token + 响应式），避免再叠覆盖层；若需迭代，沿用「最小覆盖 + 明确收敛清单」模式。【推测】

## 4. 新增模块必须复用当前生效层（硬约束）
| 必须复用 | 值/来源 |
|---|---|
| 色彩 token | --app-bg/--card/--text-*/--field-bg/--separator/--nd-border/--nd-accent/--nd-inverse（visual-refresh.css:2-35） |
| 卡 | radius15 + border1 separator + 零阴影（visual-refresh.css:43-51） |
| 按钮 | 主按钮 nd-inverse 反色；次按钮药丸 radius999 border nd-border（visual-refresh.css:81-93） |
| 字体 | UI=nd-font-ui，数据/eyebrow=nd-font-data（visual-refresh.css:15-16、:52-58） |
| 图标 tile | 单色 border nd-border radius9（visual-refresh.css:61-67），不用彩色底 |
| 语义状态色 | status-chip/dot 绿琥珀红（style.css），颜色配文字/图标 |
| 触达 | 移动交互控件 ≥44×44（visual-refresh.css:214-261） |
| 响应式 | 直接在生效层内结构化设计 min-960/max-959，safe-area，输入 16px |

- **禁止**：重新引入旧 iOS 蓝 #0a84ff 作主 accent；彩色图标底；卡套卡；每模块独立 CSS 副本（技能 delivery-workflow.md「Avoid a separate CSS copy for each module」）。【已验证】

## 5. 已知不一致收敛清单（最小范围，不扩大重构）
| 项 | 现状 | 收敛建议 | 标注 |
|---|---|---|---|
| loading-orb 旧蓝 | #0a84ff spinner（style.css:630-637） | 改用 nd-accent 或中性色，纳入生效层 | 【已验证】待收敛 |
| empty-icon 旧蓝 | #0a84ff（style.css:551-559） | 改用中性/单色，纳入生效层 | 【已验证】待收敛 |
| AdvancedYamlView intro 旧蓝 | scoped #0a84ff（AdvancedYamlView.vue:93-97） | scoped 改用生效 token | 【已验证】待收敛 |
| SubscriptionNodesView 整页旧蓝 | scoped #0a84ff 系（SubscriptionNodesView.vue:174-195） | 整页迁移到生效层；分页/refresh 触达扩到 44 | 【已验证】待收敛 |
| 小触达控件 | 分页 29×29/mini-order 28×25/drag-handle 28×36 | 扩热区到 ≥44（或间距补偿） | 【已验证】待收敛 |
| 暗色纯黑措辞 | vr --app-bg #000 vs 技能「非处处纯黑」 | 询问用户：更新技能措辞或调整背景 | 【已验证】待询问 |
| 技能 accent 措辞 | 技能写蓝 vs 实现红 | 若用户确认红为持久标准 → 显式更新技能 design-system.md | 【已验证】待显式确认 |
| 两个红 | danger #ff3b30 vs accent #d71921 | 记录语义红/强调红分工，或统一 | 【已验证】待决策 |
| 底部 SaveBar | fixed bottom 草稿条 | 确认桌面主保存仍是 EditorTopBar 右上 Save；SaveBar 仅作 Diff 入口 | 【推测】待验证 |

- 收敛原则（技能 SKILL.md / 全局约定）：小步可回滚、沿用现有结构、不引入无关重构；破坏性/批量改动先说明对象和影响并等待确认。【已验证】

## 6. 参考思想采纳流程（衔接 06）
1. 06 中任何「参考提炼」思想默认**不采纳**。
2. 需要时在当前生效层下做小样验证（不复制参考资产）。
3. 验证通过 + 与技能主干不冲突 → 按第 2 节显式触发流程升级为「我方已验证」并更新对应文档。
4. 冲突时按 SKILL.md 优先级裁决（用户当前指令 > 安全 > 选定参考 > 技能持久偏好 > 项目约定），必要时询问。
【已验证】技能 evolution-policy.md + SKILL.md。

## 7. 演进决策记录（本次研究确认）
| 决策 | 理由 | 标注 |
|---|---|---|
| 以 visual-refresh.css 为当前生效设计语言主干 | main.ts import 顺序 + token/组件覆盖证据 | 【已验证】 |
| 红 accent/零阴影/不透明卡视为合法 current preference 演进 | evolution-policy 允许 accent/阴影/透明度演进；compact-widget-design 认可 Nothing 单色方向 | 【已验证】 |
| 参考项目思想单独隔离为「参考提炼·需重新验证」 | 无许可证只提炼思想；非我方验证 | 【已验证】 |
| 残留旧蓝岛列为技术债而非立即重写 | 最小范围收敛原则 | 【已验证】 |
| 技能措辞滞后不擅自改技能 | 仅显式请求后更新技能 | 【已验证】 |
