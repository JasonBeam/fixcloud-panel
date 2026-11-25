# roadmap — 未来功能与研究计划

> 分类：【待验证】为主，含【我方已验证】的现状依据。
> **本目录全部是计划，不是已实现功能。** 任何落地都需要单独授权，且不得在本轮改动生产订阅/Lucky/NAS/VPS。

## 优先级总览

| # | 主题 | 优先级 | 依赖 | 文件 |
|---|---|---|---|---|
| 1 | **私有订阅服务**（取代无鉴权公开文件） | **P0** | 无（纯面板侧） | [01-private-subscription.md](01-private-subscription.md) |
| 2 | sing-box 自建节点管理 | P1 | SSH 通道、VPS 防火墙 | [02-singbox-selfhosted-nodes.md](02-singbox-selfhosted-nodes.md) |
| 3 | 多 VPS 节点同步与配置生命周期 | P1 | 1、2 | [03-multi-vps-sync.md](03-multi-vps-sync.md) |
| 4 | 健康检查 / 延迟 / 测速 / 流量统计 | P2 | 2 | [04-monitoring-health.md](04-monitoring-health.md) |
| 5 | Dashboard 监控与 UI 交互升级 | P2 | 4 | [05-dashboard-ui.md](05-dashboard-ui.md) |
| 6 | 研究待办与开放问题 | — | — | [06-research-backlog.md](06-research-backlog.md) |

## 为什么是这个顺序

1. **P0 私有订阅**：当前 `https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml` 无鉴权可读且含凭据，是**已验证的实际暴露面**；而它完全在面板侧可解，不需要碰 VPS/Lucky，风险最低、收益最高。
2. **P1 sing-box**：需要新建部署、改防火墙、抬 sysctl，属生产变更，必须在订阅出口安全之后再做，否则新节点凭据又会落进公开文件。
3. **P1 同步**：多 VPS 一致性依赖前两者。
4. **P2 监控/UI**：有了节点才有监控对象；参考项目的教训是**监控与自愈本身会引发事故**，必须先有护栏再上自动化。

## 九项重点技术研究（用户指定）

| 研究项 | 落点 |
|---|---|
| 私有订阅服务器 | 01 |
| 独立订阅 Token 签发 | 01 §3 |
| 订阅撤销与有效期管理 | 01 §4 |
| Clash / Stash / OpenClash 多客户端兼容 | 01 §5 |
| 自用版与朋友版订阅隔离 | 01 §6 |
| Subscription-Userinfo 流量响应头 | 01 §5.2 |
| 多 VPS sing-box 节点同步 | 03 |
| 配置校验、原子更新与失败回滚 | 02 §5、03 §3 |
| Dashboard 监控与 UI 交互逻辑 | 05 |

## 最终目标（用户要求要点）

> 让 FixCloud.yaml 不再通过 file 域名无鉴权公开访问，而是由 FixCloud 生成**可管理、可撤销、可自动更新**的私有订阅链接。

## 通用前置条件

- 服务商 API 白名单：把 NAS 当前出口 IPv4 `<NAS_EGRESS_IPV4>` 加入 Vultr / Evoxt 控制台白名单（**需我本人操作**，已验证根因）。
- 客户端版本确认：Stash iOS/macOS、OpenClash 内核版本（影响 REALITY / hy2 / SS2022 cipher 支持）。
- 云厂商侧防火墙（安全组）UDP 规则确认。
