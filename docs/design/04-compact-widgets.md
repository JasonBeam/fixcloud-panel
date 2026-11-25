> 分类：我方已验证（主干：beam-web-product-guidelines 技能 compact-widget-design.md + FixCloud UsageView 当前源码）；含「参考提炼」小节单独标注
> 核实时间：2026-11-25

# 04 · 紧凑监控卡与数据可视化规范

## 结论先行
- 紧凑面视觉语言 = Apple 克制 + Nothing 单色/点阵 + pixel 结构清晰（软 pixel 数据系统，非复古装饰）。【已验证】技能 compact-widget-design.md。
- **单一 hero 指标**（剩余配额/余额/功率/流量/时间/健康），一眼可读；支撑值小字克制色；「还剩多少」用进度/分段配额条。【已验证】
- 新鲜度放可预测低优先位；诚实标记缓存/离线，禁把缓存当新刷新。【已验证】
- 状态色传达状态非装饰，**颜色必须配文字/图标/填充/形状**（无色也可懂）。【已验证】
- FixCloud UsageView 是当前监控卡范式实现（连续配额条 + 3 支撑指标 + 新鲜度行 + 缓存标记）。【已验证】

## 1. Beam 紧凑视觉语言（技能 compact-widget-design.md）【已验证】
| 原则 | 内容 |
|---|---|
| 融合 | Apple 克制 + Nothing 单色/点阵 + pixel 结构清晰；软 pixel 数据系统非复古 |
| 底色 | 灰/中性底 + 一个有意义状态 accent |
| 身份标记 | 小语义 glyph 或用户可识别身份标记（保留用户选定符号如鲸鱼），非泛字母 logo |
| 禁装饰 | 小 widget 内禁卡套卡 |

## 2. 信息层级（技能）【已验证】
| 规则 | 内容 |
|---|---|
| 一个 hero | 选剩余配额/余额/功率/流量/时间/健康之一，一眼可读 |
| 支撑值 | 小字、克制色、一致对齐，强化 hero 而非等权竞争 |
| 配额条 | 核心问题是「还剩多少」时用进度/分段配额条 |
| 百分比 | 仅助解读时显示，禁重复同数多种形态 |
| 新鲜度 | 日期/新鲜度放可预测低优先位 |
| 语义标签 | 保留用户确认的精确标签（POWER/CARD/LEFT/最新日期），不泛化 |

## 3. FixCloud UsageView 监控卡范式（views/UsageView.vue，281 行）【已验证】
### 3.1 卡结构
| 部位 | 内容 | 来源 |
|---|---|---|
| 页头 | eyebrow 订阅状态 + page-title 机场流量 + subtitle「从当前主配置的 proxy-providers 读取标准流量响应头，不下载或更新订阅」+ 刷新 icon-button（disabled loading） | UsageView.vue:137-153 |
| 当前来源横幅 | current-source-banner 文件名·来源 + SMB/WebDAV/本地持久化 | UsageView.vue:154-159 |
| 新鲜度行 | usage-refresh-line：status-dot（error→warn 否则 ok）+「N 个订阅提供流量信息」/「读取失败」+ small（cached→「缓存数据 · 」+ formatRefreshTime） | UsageView.vue:161-167 |
| 卡头 | usage-provider-icon（Gauge）+ 标题 + Provider + status-chip（expired→warn 已到期 / ok 正常） | UsageView.vue:207-221 |
| hero 配额行 | usage-quota-line：strong「used / total」+ span「剩余 X%」 | UsageView.vue:223-226 |
| 配额条 | usage-progress aria-label「剩余流量比例」，i width=remainingPercent%（vr：height10 radius0 bg field-bg，i bg nd-inverse 单色） | UsageView.vue:227-229 + visual-refresh.css:117-118 |
| 3 支撑指标 | usage-metrics：CloudDownload 剩余流量 / CalendarDays 到期时间 / TimerReset 剩余天数 | UsageView.vue:231-249 |
| 传输 footer | usage-transfer：ArrowUp 上传 / ArrowDown 下载 | UsageView.vue:251-254 |
| 不可用态 | usage-unavailable：WifiOff + 标题 + message | UsageView.vue:257-265 |
| 空态 | loading→empty-card+loading-orb「正在读取订阅流量…」；否则 empty-card+empty-icon「没有可读取的订阅」+原因 | UsageView.vue:269-279 |

### 3.2 数据行为【已验证】
| 机制 | 内容 | 来源 |
|---|---|---|
| 刷新锁 | if loading return；loading ref 防重叠 | UsageView.vue:106-108 |
| 双数据源 | /api/subscriptions/usage（订阅）+ /api/vps/usage（VPS，并行 refreshServers） | UsageView.vue:56-64、:117 |
| 缓存标记 | cached ref → 「缓存数据 · 」前缀；fetchedAt 真实采样时间 | UsageView.vue:120、:166 |
| 文件切换重刷 | watch sourceId/path → refresh(true) | UsageView.vue:129-132 |
| 强制刷新 | force=true query | UsageView.vue:116 |
| 错误中文化 | 「无法读取订阅流量」「暂时无法读取 VPS 流量」 | UsageView.vue:62、:122 |
| 字节格式 | B/KiB/MiB/GiB/TiB/PiB，≥100 toFixed(0) 否则 toFixed(1) | UsageView.vue:70-80 |
| 日期格式 | zh-CN hour12 false；VPS 到期 YYYY/MM/DD，剩余天数 ceil((end-now)/86400000)，缺失「未提供」 | UsageView.vue:42-50、:82-104 |

- 与技能一致：一个 hero（剩余配额%）、支撑值小字、配额条、新鲜度低优先位、缓存诚实标记、刷新锁、颜色配文字（status-chip 文字+图标、status-dot+文字）。【已验证】
- **项目具体化**：FixCloud 用**连续**配额条（usage-progress，vr 方角单色），非分段仪表。技能允许「progress or segmented quota bars」，故连续条合规。【已验证】

## 4. 配额条规范
| 维度 | 我方当前（FixCloud） | 标注 |
|---|---|---|
| 形态 | 连续条 height10 radius0 | 【已验证】visual-refresh.css:117 |
| 填充 | nd-inverse 单色（非语义色渐变） | 【已验证】visual-refresh.css:118 |
| 轨道 | field-bg | 【已验证】 |
| 语义 | aria-label「剩余流量比例」+ 文字「剩余 X%」 | 【已验证】UsageView.vue:227 |
| 阈值色 | 当前未对配额条做阈值变色（状态由 status-chip 表达） | 【已验证】 |

## 5. 状态强调色 + 颜色配文字/图标（技能）【已验证】
- 色传达状态非装饰；色配文字/icon/填充/形状，无色也可懂。
- 警告/严重阈值领域感知可配；相关指标进度基线/标签对齐。
- FixCloud：status-chip（文字+Check/XCircle）、status-dot（+文字）、usage-quota-line span 绿（#34844a/#69bb7a）配「剩余 X%」文字。【已验证】

## 6. Small-first / 家族一致 / 视觉探索（技能）【已验证】
| 原则 | 内容 |
|---|---|
| Small-first | 比较方向时先设计验证 Small；Medium/Large 仅历史/趋势/动作需要时；Small 无需滚动交互可读；强纵向或双区胜多等瓦片 |
| 家族一致 | 先借既有家族语言再发明；共享字体/间距节奏/条处理/新鲜度标签/glyph 风格/状态色；各产品保留自己身份 glyph + hero |
| 视觉探索 | 给几个可立即查看的 Small 变体非只长文档；变体间数据/刷新逻辑相同仅表现层变；清晰命名；选定后精炼该方向非平均 |
| 数据行为分离 | UI-only 重构与 fetch/parse/cache/auth/refresh 分离；保留配置/安全存储使视觉更新不强制重输 ID/凭据；刷新锁；短缓存复用/stale 兜底/显式 mock；诚实标记 stale/offline；调试基于捕获 API 证据 |

## 7. 参考提炼小节（非我方验证，需重新验证）
> 分类：参考提炼（来源：JimmyChan233/homelab 私有仓库经授权 Fork；仅提炼思想，未复制资产；详见 06）
> 以下思想来自参考项目，**采纳前须在本项目重新验证**，不直接作为我方标准。

| 参考思想 | 抽象描述 | 与我方当前差异 | 标注 |
|---|---|---|---|
| 分段仪表 | 配额/进度用固定格数（如 14 格）小方块分段，填色随阈值（低绿/中琥珀/高红），禁纯色长条 | FixCloud 用连续单色条 | 【参考提炼·需重新验证】 |
| 点阵大数字 | 关键大数字（金额/百分比）用点阵字模渲染，幽灵点铺底；小数字不用 | FixCloud 用等宽字体数字 | 【参考提炼·需重新验证】 |
| 方形状态点 | 状态用圆角小方块（绿=工作中呼吸/琥珀=等待或失败/灰=空闲/空=结束），圆点仅留给 LIVE 脉冲 | FixCloud 用圆形 status-dot | 【参考提炼·需重新验证】 |
| 阈值领域感知 | 分段阈值（如 <70/≥70/≥90）按领域配置 | 我方配额条当前无阈值变色 | 【参考提炼·需重新验证】 |

- 来源路径：fork-clone/36-Jimmy设计语.md、fork-clone/scripts/dashboard/README.md。具体配色值/字体/CSS 未复制（见 06 掩码声明）。
- 注意：分段仪表/点阵/方点与技能 compact-widget-design.md 的「Nothing 单色/点阵」方向相容，可作为未来演进候选，但须先验证再采纳（07）。
