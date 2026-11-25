# 01 · 私有订阅服务（P0）

> 分类：【待验证】方案 + 【我方已验证】现状
> 目标：取代 `https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml` 的无鉴权公开访问。
> **本轮只设计，不改动生产订阅、Lucky、NAS、VPS。**

## 1. 现状与问题【我方已验证】

| 事实 | 证据 |
|---|---|
| 公开 URL 无鉴权返回 200 | 直接 GET，20893 字节，与 NAS 本地文件一致 |
| 文件内含回家节点凭据 | `proxies[0]` 的 `username`/`password`（值不入库） |
| 文件内含订阅 token | 3 个 `proxy-providers`，其中 2 个 URL 带 token query |
| 文件内含管理面信息 | `external-controller` + `secret` |
| 面板已有订阅**读取**能力 | `subscription_usage.py` / `subscription_nodes.py`：只读拉取、缓存 TTL 300s、UA `clash.meta` |
| 面板**没有订阅输出端点** | 全后端无 serve/subscription 输出路由 |

**结论**：面板目前是"订阅消费者 + 配置编辑器"，要变成"订阅发布者"，需新增一个**输出子系统**。

## 2. 目标形态

```
FixCloud 内部主配置（含全部凭据，仅 NAS 本地 0600）
        │
        ├─ 自用版视图（全量节点 + 回家节点）
        ├─ 朋友版视图（仅指定线路 id，无回家节点、无管理面字段）
        │
        ▼
  订阅渲染器（Clash YAML / sing-box JSON）
        │
        ▼
  GET/HEAD /sub/<token>  ── Token 鉴权 ── 配额/有效期 ── subscription-userinfo
        │
        ▼
  Clash Verge / OpenClash / Stash / sing-box 客户端
```

**关键原则**：**内部主配置与对外订阅视图物理分离**。对外视图永远不包含：回家节点凭据、`external-controller`/`secret`、上游订阅 URL 与 token、其他用户的线路。

## 3. Token 签发与存储

| 设计点 | 做法 | 来源 |
|---|---|---|
| Token 形态 | 高熵随机（≥128 bit），URL 路径段 `/sub/<token>`，**不用 query**（避免进日志/Referer） | knowledge/06 |
| 存储 | 服务端只存 **hash**（如 SHA-256）+ 元数据；明文只在签发那一刻返回一次 | knowledge/06 |
| 元数据 | id、label、scope（self/friend）、允许线路 id 列表、created_at、expires_at、revoked_at、last_used_at、use_count | knowledge/06 |
| 权限 | 凭据文件 0600，属主为面板运行 UID；**不入浏览器 localStorage** | 我方现有 `persistDraft` 已遵循 |
| 隔离 | 每个 token 独立视图；朋友 token **只发线路 id**，不发管理信息 | knowledge/05/06 |
| 泄露断言 | 渲染后断言输出中不含主配置的敏感字段集合；命中则拒绝发布并告警 | knowledge/05 |

## 4. 撤销与有效期

| 能力 | 实现 |
|---|---|
| 撤销 | 标记 `revoked_at` → 立即 404/410；**同时删除该 token 对应的渲染缓存与凭据副本** |
| 有效期 | `expires_at`；到期返回 410 并在 `subscription-userinfo` 写 expire |
| 轮换 | 新 token 签发 → 旧 token 保留宽限期（可配）→ 到期自动撤销 |
| 配额 | 按 token 累计上行/下行；超额返回 403 或降级视图（需先有流量统计，见 04） |
| 审计 | 每次签发/撤销/轮换写审计（复用现有 `audit.py` 的 11 列结构），**不记录 token 明文** |

## 5. 多客户端兼容【参考提炼 + 待验证】

### 5.1 格式选择

| 客户端 | 吃什么 | 注意 |
|---|---|---|
| Clash Verge Rev | **Clash YAML**；只校验 HTTP 200 + 含 `proxies`/`proxy-providers` 键 | 不查 Content-Type、**不解 base64**；base64 订阅会被拒收 |
| OpenClash | Clash YAML；解析 `subscription-userinfo`（lua） | 更新间隔由 `update_interval`（分钟）控制 |
| Stash | Clash YAML；官方解析 `subscription-userinfo` | **默认 12h 更新，优先发 HEAD** → 必须正确响应 HEAD |
| sing-box 官方客户端 | **JSON remote profile**（`sing-box://import-remote-profile`），默认 60min | 与 Clash YAML 是两套输出，需分别渲染 |

**决策**：MVP 只做 **Clash YAML**（覆盖 Verge/OpenClash/Stash），sing-box JSON 输出放 P2。**不做 base64 订阅**。

### 5.2 `subscription-userinfo` 响应头

```
subscription-userinfo: upload=<bytes>; download=<bytes>; total=<bytes>; expire=<unix_seconds>
```

- 单位 **bytes**，时间 **unix 秒**；`expire=0` 表示长期有效。
- 无统计时先给 `upload=0; download=0; total=0; expire=0`，**不要省略该头**（部分客户端会显示异常）。
- 兼容别名：Verge 也接受 `x-amz-meta-subscription-userinfo`。
- **必须同时支持 HEAD**，且 HEAD 与 GET 的头一致、body 为空。

### 5.3 缓存与更新

- 响应带 `ETag` / `Last-Modified`；支持 `If-None-Match` → 304，减少客户端流量与服务器负载。
- `Cache-Control: no-store`（含凭据的响应不应被中间缓存）。
- 内部渲染缓存 TTL 建议 60s，配置变更时主动失效。

## 6. 自用版与朋友版隔离

| 维度 | 自用版 | 朋友版 |
|---|---|---|
| 节点范围 | 全量 + 回家节点 | 仅白名单线路 id |
| 管理面字段 | 可保留（仅本机访问） | **一律剔除** |
| 上游订阅 URL | 可保留 | **剔除**，只输出解析后的节点 |
| 流量配额 | 不限 | 按 token 配额 |
| 有效期 | 长期 | 明确到期 |
| 撤销影响 | 仅自己 | 立即失效，不影响其他 token |

## 7. 与现有架构的接法（最小改动）

| 复用 | 说明 |
|---|---|
| `save_service.py` 的原子写 + 三态回滚 | 订阅视图渲染产物同样走"写临时 → 回读校验 → 安全替换" |
| `audit.py` | 签发/撤销/轮换审计 |
| `source_store.py` 的 O_EXCL 0600 + fsync + os.replace | token 元数据存储 |
| `require_internal_request` | **管理类端点**（签发/撤销/列表）仍限内网；**订阅输出端点**走 token 鉴权，不要求该头 |
| 现有 Diff 评审流 | 视图模板变更也走 Diff |

**新增模块（建议）**：`backend/app/services/subscription_publisher.py`、`backend/app/services/subscription_tokens.py`、`backend/app/api/routes_subscription.py`；前端新增「订阅发布」页（列表 → 详情 → 签发/撤销）。

> ⚠️ 上述文件名为**建议**，落地前必须对照当前源码核实（2026-11-22 已有演进，旧行号不可信）。

## 8. 公开暴露的三种处置选项

| 选项 | 做法 | 评价 |
|---|---|---|
| **A（推荐）** | 自建节点与订阅凭据**完全不进 FixCloud.yaml**；公开文件只保留无凭据的公共部分，或直接关闭公开访问 | 最彻底，不需要改 Lucky |
| B | 公开文件加鉴权（Lucky 反代 + token/Basic Auth） | 需改 Lucky 配置，属生产变更 |
| C | 保留公开文件但移除全部凭据，节点改为只从私有订阅获取 | 折中，需确认谁在消费该文件 |

**未决问题**：当前**谁在消费**这个公开 URL？（客户端订阅？其他服务？）必须先查清，否则关闭会断网。→ 列入 06 研究待办。

## 9. 分阶段

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0-a | 只读盘点：谁在消费公开 URL、客户端版本、现有订阅字段 | 清单 + 证据 |
| P0-b | token 存储 + 签发/撤销/列表 API（内网） | 单测 + 审计不泄密 |
| P0-c | Clash YAML 渲染器 + 泄露断言 + HEAD/ETag | 三客户端实测拉取成功 |
| P0-d | 自用/朋友双视图 + 配额占位 | 朋友视图断言无回家节点与管理面字段 |
| P0-e | 切换客户端订阅 URL → 观察一个更新周期 → 关闭公开文件 | 公开 URL 返回 404/403，客户端仍正常 |

## 10. 禁止事项

- 不得在本轮改动生产订阅、Lucky、NAS、VPS。
- 不得把 token 明文写进日志、审计、前端存储、入库文档。
- 不得让朋友版视图包含回家节点或管理面字段。
- 不得用"关闭公开文件"代替"先查清消费者"。
