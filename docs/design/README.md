> 分类：我方已验证主干 + 参考提炼（索引页；各子文档分类以其开头徽章为准）
> 核实时间：2026-11-25
> 核实方式：只读源码核查（read/glob/grep + 只读 wc 元数据），未执行任何脚本、未联网访问生产服务、未修改任何源项目文件

# homelab-panel UI / 交互设计规范 · 索引

## 结论先行
- 本目录是 JasonBeam 个人 Homelab 面板（homelab-panel）的可复用 UI/交互设计规范，供 DSH 与 Codex 后续开发复用。
- **主干 = 我方已验证**：beam-web-product-guidelines 技能（个人 Web 产品标准）+ FixCloud 面板当前源码。当前生效视觉层是 **visual-refresh.css（Nothing 风单色 + 红色 accent）**，而非技能文本里描述的旧 iOS 蓝。
- **参考项目思想单独标注「参考提炼」**：仅从经授权 Fork 副本提炼抽象设计思想，**非我方验证、需重新验证后才可采纳**，且未复制任何源码/UI 资产。

## 文档索引
| 文件 | 分类 | 用途 |
|---|---|---|
| README.md | 索引 | 本文件：索引 + 适用边界 + 来源分类 |
| [01-design-system.md](01-design-system.md) | 我方已验证 | 设计系统主干：当前生效色彩/字体/圆角/间距/阴影/层级/暗色 token |
| [02-panel-ui-current.md](02-panel-ui-current.md) | 我方已验证 | FixCloud 当前 UI 实现事实：生效层判定、布局、导航、组件清单、关键交互 |
| [03-interaction-patterns.md](03-interaction-patterns.md) | 我方已验证 | 交互规范：overview→list→detail、详情头部、dirty→保存→Diff、异步 busy、反馈、错误中文化、凭据只留后端 |
| [04-compact-widgets.md](04-compact-widgets.md) | 我方已验证（主干）+ 参考提炼（标注） | 紧凑监控卡与数据可视化：单一 hero 指标、配额条、新鲜度、状态强调色、颜色配文字/图标 |
| [05-responsive-mac-iphone.md](05-responsive-mac-iphone.md) | 我方已验证 | Mac 与 iPhone 适配：持久侧栏+有界居中工作列 vs 全屏详情+底部 tab、44px 触达、safe-area |
| [06-reference-ideas.md](06-reference-ideas.md) | 参考提炼 | 参考项目抽象设计思想（需重新验证、不复制资产、已掩码） |
| [07-evolution-policy.md](07-evolution-policy.md) | 我方已验证 | 演进策略：在既有生效视觉语言上迭代不推倒重写；新增模块复用当前生效层 |

> 相关：面板功能与接口在 [panels/fixcloud-panel/](../panels/README.md)；新增页面的规划在 [roadmap/05-dashboard-ui.md](../roadmap/05-dashboard-ui.md)；我方基础设施在 [infrastructure/](../infrastructure/README.md)。

## 规范适用边界
- 适用：Beam 个人 homelab-panel 及同类 NAS 工具 / 配置编辑器 / 监控面板 / 门户 / PWA / 响应式 Web 产品。
- 不把 FixCloud / YAML / Clash / Stash / NAS 概念强加到无关产品（技能 SKILL.md「Start with context」第 4 条）。
- 参考思想（06）不是我方标准；采纳任何一条前须在本项目重新验证，确认后才转为「我方已验证」。
- 优先级（技能 SKILL.md「Resolve priorities」）：1 用户当前显式指令 > 2 安全与权威数据 preservation > 3 显式选定的参考页/截图 > 4 技能持久偏好 > 5 项目现有约定。两条持久偏好冲突时保持当前实现不变并询问。

## 来源分类说明
| 分类 | 含义 | 来源 |
|---|---|---|
| 我方已验证 | 经当前源码/技能读取确认 | beam-web-product-guidelines 技能（/Users/beamjason/.codex/skills/beam-web-product-guidelines）+ FixCloud 当前源码（/Users/beamjason/Documents/BeamNat/fixcloud-panel/frontend） |
| 参考提炼 | 仅提炼抽象思想，非我方验证，需重新验证 | JimmyChan233/homelab 私有仓库经授权 Fork 副本（/Users/beamjason/Documents/GitHub/homelab-sanitize/fork-clone，无许可证） |
| 【推测】 | 由源码推断但未直接证实 | 文中逐条标注 |
| 【待验证】 | 需运行时/真机/视觉验收 | 文中逐条标注 |

## 当前生效视觉层判定（重点结论）
- **生效层 = visual-refresh.css**。证据：frontend/src/main.ts:13-14 先 import style.css 再 import visual-refresh.css；后者以同特异性、更晚源序重定义 :root/.dark 自定义属性并覆盖组件类（部分 !important），故胜出。
- style.css（65531 字节 / 3338 行）= 基础结构 + 布局 + 语义状态色层；visual-refresh.css（13914 字节 / 301 行）= 当前生效视觉语言层。
- 残留旧 iOS 蓝岛（vr 未覆盖）：loading-orb、empty-icon、AdvancedYamlView / SubscriptionNodesView / ReferenceIntegrityModal 的 scoped 样式。详见 01 / 02 / 07。

## 掩码与合规声明
- 产出中不含任何真实凭据、真实 IP、真实域名、朋友个人信息。FixCloud 公开文件服务域名以 <PLACEHOLDER> 掩码；参考项目域名/IP/主机名一律以 example.com / 192.0.2.10 / 203.0.113.30 / <PLACEHOLDER> 代替。
- 参考项目无许可证 → 只提炼设计思想，不复制表达（源码/CSS/组件代码/图片/图标/字体/配色具体值）。06 含来源归属句与「不复制资产」声明。
- 本任务为只读研究：未修改源项目文件、未执行脚本、未联网访问生产服务。
