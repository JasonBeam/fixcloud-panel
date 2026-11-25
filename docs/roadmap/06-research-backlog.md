# 06 · 研究待办与开放问题

> 分类：【待验证】。每条给出**为什么重要**与**验证方法**。

## A. 阻塞项（需我本人操作）

| # | 问题 | 为什么重要 | 验证/解决 |
|---|---|---|---|
| A1 | 服务商 API IP 白名单 | 现有 `/api/vps/usage` 两台都不可用 | 在 Vultr / Evoxt 控制台把 `<NAS_EGRESS_IPV4>` 加入白名单；已验证根因（Vultr 401 Unauthorized IP；Evoxt 200 但 IP Address Unauthorized） |
| A2 | 公开文件处置决策 | `<PUBLIC_FILE_DOMAIN>/FixCloud.yaml` 无鉴权含凭据 | 先查清消费者（A3），再选 roadmap/01 §8 的 A/B/C |
| A3 | **谁在消费公开 URL** | 直接关闭会断网 | 查 Lucky 访问日志 / 客户端订阅配置 / 其他服务引用 |
| A4 | 客户端版本 | 决定 REALITY / hy2 / SS2022 cipher 可用性 | Stash iOS≥3.4.0 才支持 REALITY；Stash 不支持 2022-chacha20；核实 OpenClash 内核版本 |

## B. 环境待核实

| # | 问题 | 验证方法 |
|---|---|---|
| B1 | 香港 VPS 供应商归属 | 控制台/IP whois（用户称 Evoxt，未验证） |
| B2 | 云厂商安全组 UDP 规则 | 控制台只读查看；ufw 之外还有一层 |
| B3 | F50 / R5C 当前角色与固件 | 只读 SSH 查版本与 OpenClash 模式 |
| B4 | `oixCloud.yaml` 用途 | 只读查看结构与消费者（24012B，admin 属主，07-28） |
| B5 | 证书同步 `sync.sh` 机制与触发周期 | 只读查看脚本（本轮未读） |
| B6 | Lucky OpenToken 接口能力 | 只读探测；文档明示可调但无官方 OpenAPI，社区抓包路径未验证 |
| B7 | 家庭 IPv4 出口是否公网可达 | 外部实测；当前出口疑似 CGNAT |
| B8 | DDNS 更新链路与 TTL | 只读查 Lucky 配置 |

## C. 技术待实测

| # | 问题 | 验证方法 |
|---|---|---|
| C1 | REALITY 借壳目标选择 | 官方推荐热门目标 vs 参考项目主张自有 AS 机构域名 → `openssl s_client -tls1_3 -alpn h2` + `curl -sI` 验 TLS1.3/h2/无 301，再做观察期对照 |
| C2 | 东京 1 vCPU 上 hy2 与 REALITY 并存的 CPU 占用 | 压测 + `top`/`pidstat` 采样 |
| C3 | 晚高峰 QUIC QoS | 多时段加密多连接测速，记录延迟与吞吐 |
| C4 | sing-box 重启后流量累计基线 | 持久化累计值，重启后校验不断档 |
| C5 | 订阅 HEAD/ETag/304 在三客户端的实际行为 | 抓包 + 客户端日志 |
| C6 | `v2ray_api` 是否值得自编译 | 官方默认构建无 `with_v2ray_api`；自编译维护成本高，MVP 不依赖 |

## D. 历史悬置问题

| # | 问题 | 状态 |
|---|---|---|
| D1 | 面板容器网络模式选择（bridge vs host） | 悬置未答；当前 bridge + extra_hosts 已解决公开 URL 核对问题，**倾向保持 bridge** |
| D2 | 自建节点是否开放延迟测试 | 旧约束"订阅节点页取消延迟测试"针对订阅节点；自建节点属自有资产，需重新确认边界 |
| D3 | 原 Fork `JasonBeam/homelab` 是否删除 | **用户已决定：暂时保留，不执行删除**（2026-11-25） |
| D4 | 上游历史凭据轮换 | 需原持有人自行处理；清单见 `reports/history-risk.md` |

## F. UI 待办（用户已决定：记录但暂不优先修改）

来源 `design/07` 六项不一致。**不阻塞私有订阅中心与安全边界工作**；待订阅出口安全后再排期。

| # | 不一致 | 影响 | 处置方向（待排期） |
|---|---|---|---|
| F1 | 残留旧蓝岛 4 处 | 与当前生效 Nothing 单色红层冲突 | 统一到 `visual-refresh.css` token |
| F2 | 暗色模式纯黑 | 与浅灰底卡片语言不一致 | 暗色覆盖卡片/弹窗/字段/代码区 |
| F3 | 部分触达 <44px | iPhone 可用性 | 触达区补到 44px |
| F4 | 两个红并存 | 强调色语义混乱 | 收敛为单一 `--nd-accent` |
| F5 | 技能文本滞后 | 文案与实现不符 | 同步文案 |
| F6 | 底部 SaveBar | 与"保存进 Diff 评审流"交互约定冲突 | 评估改为详情页头部保存 + Diff |

> 新增 UI 一律复用**当前生效层**（`visual-refresh.css`），不得复制旧蓝岛样式；详见 `design/02`。

## E. 不重复研究清单（已有结论，直接用）

| 主题 | 结论位置 |
|---|---|
| sing-box 官方能力/版本/字段/重载行为 | roadmap/02、knowledge/03 |
| 客户端协议支持矩阵与字段映射 | knowledge/03 |
| 可复用开源项目取舍 | roadmap/02 §2（不装第三方面板） |
| 订阅格式与 userinfo 头 | roadmap/01 §5 |
| 探针/自愈/告警判据 | roadmap/04、knowledge/08、knowledge/11 |
| Lucky × OpenClash STUN 共存 | infrastructure/05、troubleshooting/ |
| 容器 IPv6 回环投递问题 | infrastructure/06 §4（已修复并验证） |
