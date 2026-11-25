> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

# 抗封锁经验：频封溯源 / 协议纯净化 / 借壳选择 / UDP QoS / 端口伪装 / 被封处置

> 来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。
> 【已验证】= 本次审计实际读到；【推测】= 提炼者推断。真实 IP/域名/ASN 编号/朋友姓名/设备别名一律不出现：自有域用 example.com / node-a.example.com，IP 用 192.0.2.10 / 198.51.100.20 / 203.0.113.30，高风险 ASN 只描述特征不写编号，借壳目标用"某自有 AS 的高校/机构域名"。供应商名（搬瓦工/DMIT/Evoxt/VMISS/LisaHost/Contabo/IPRoyal/Cloudflare）属事实信息保留。

## ① 通用可复用经验（可直接迁移）

### 1. 频封溯源方法（从服务端日志重建击杀链）
- 【已验证】取证数据源 = 服务端 sing-box access.log（含主动探测/无效握手记录）+ 中国侧多视角探测（Globalping CN + 家宽实测）。
- **精确击杀链特征**（按时间重建）：
  1. 换 IP 后**分钟级复用旧域名 + 全部旧端口** → 新 IP 与旧 IP 历史行为关联，域名-IP 关联在数分钟内完成。
  2. 朋友侧/未更新订阅终端**高频无效 REALITY 握手**（如 30h 累计 894 次 `REALITY: processed invalid connection`）= 显眼的行为异常特征。
  3. **SS2022 遭 GFW FET + 主动重放探测**（日志特征 `salt not unique` / `bad timestamp`），多波、多端口均被定位。
  4. 临死前出现**高频探测突发**（某几个内地省份段的 160 连接突发主动探测），与历史被封 IP 临死前特征一致。
  5. 最终**中国侧 IPv4 全端口 TCP SYN-ACK 丢包**（服务端可见 SYN-RECV，回包到不了客户端）= 整机阻断完成。
- 【已验证】存活时间递减趋势：约 4.5 个月 → 18 天 → **30.5 小时**。暴露面未肃清时，换 IP 只是重置计时器，且越来越短。

### 2. 六大暴露根因（换 IP 也救不了的结构性问题）
- 【已验证】① **身份与基础设施强复用**：换 IP 沿用旧域名 + 旧端口；nginx 对非匹配路径 `return 444`（TLS 握手后静默断连）本身是主动探测指纹；proxy-server-nameserver 明文 UDP 查询加速域名-IP 关联。
- ② **公网裸 SS2022 + 高频非 lazy 健康检查**：interval:60 且 lazy:false，无流量时每日向各机发 1440+ 次固定间隔探测；SS2022 触发 FET + 主动重放。
- ③ **Trojan/AnyTLS 无 HTTP 伪装回落**：fallback 未配置，TLS 握手后无密码流量直接 EOF → 主动探测指纹 100% 确定。
- ④ **REALITY 借壳违反规范（用 CDN/301 域名）**：对照唯一用自有 AS 大学域名的节点连续 7 天 0 次探测，其余借壳大厂/CDN 域名的节点均被探测。
- ⑤ **LAN 设备 STUN 经 REALITY mux 外发**：某网关设备每 ~10.7s 向公共 STUN 发 UDP 走 REALITY TCP mux，造成约 9500 次/天固定间隔建连/EOF 日志噪声。
- ⑥ **高风险 ASN + 单节点极高流量密度 + 朋友高频无效握手**：主力机所在 ASN 在主流 IP 库全标红（proxy:true），承担全舰队 95%+ 流量（峰值 112–178 GiB/day），叠加朋友高消费与无效握手 → 比普通 VPS 更严苛的行为阈值审视。

### 3. 封锁类型诊断（区分 ICMP / TCP / UDP / 单端口 / 整 IP）
- 【已验证】**单向丢包封 IP**：国内 SYN 到本机、本机回 SYN-ACK，但回包到不了客户端 + 本机 ping 国内 DNS 100% 丢 + 海外视角全通 → 单向丢包封 IP（非整机宕机）。
- 【已验证】**ICMP 通 ≠ TCP 通**（ICMP 限速伪象，TCP 20/20 全通）；**ICMP 丢包 ≠ TCP 丢包**。诊断必须分协议分端口测。
- 【已验证】**整 IP 回程 UDP 被丢**（非单端口）：服务端 tcpdump 看到客户端打跳跃口的 QUIC、服务端也回包了，家里仍收不到；换口/端口跳跃都救不了；同机 TCP 四协议正常 → 只能换 IP。
- 【已验证】**单端口被封**：某机仅一个 Trojan 端口 CN TCP 0/4，其余端口可用 → 换端口即可恢复（不必换 IP）。
- 【已验证】封 IP 后连带故障：走公网 IPv4 回源家宽的服务（如媒体反代）双向 TCP 阻断；订阅域 CNAME 指向被封机在直连模式下无法拉取 → 订阅域必须脱钩到独立入口体系。

### 4. 协议纯净化（方案 A，消除最脆弱暴露面）
- 【已验证】**退役无 fallback 的 AnyTLS**（sing-box 1.13.13 不支持 anytls fallback，握手发真域证书后对非认证探针直接 EOF）+ **退役公网裸 SS2022**（FET + 主动重放）。朋友版精简为 3 地 × 3 协议 = 9 节点（REALITY/Hy2/Trojan）。
- 【已验证】**Trojan 补 HTTP decoy fallback**：回落到本地 127.0.0.1:18080 返回 200 HTML 伪装页；无 nginx 的机部署轻量 decoy-http.py（User=nobody、MemoryMax=64M、Server: nginx 头）。验收：从外部对全部 Trojan 端口发 HTTPS 请求，10/10 返回 200 + 伪装页标题。
- 【已验证】**Hy2 补 masquerade**（http://127.0.0.1:18080），探测回 HTTP 页面。
- 【已验证】**REALITY 借壳换自有 AS 机构域名**（非 CDN、TLS1.3+h2+X25519、HTTP 200、无 301）。
- 【已验证】**REALITY 升 :443**：唯一公网 443 未被占用的节点直接上 443（sing-box 以 root 运行可绑特权端口）；其余机 443 被 nginx/socat 占用 → 需前置 SNI 分流（见 §6）。
- 【已验证】**回家隧道升级**：关公网老 AEAD SS，改原生 xray VLESS-REALITY 公网入口 + tailnet 专用 SS2022（详见草稿 03 §7）。
- 【已验证】纯净化后公网零 AnyTLS、零传统 SS 暴露，延迟不增反降。

### 5. Reality 握手目标选择（与草稿 03 §3 呼应）
- 【已验证】标准：TLS1.3+h2、国外未被墙 VPS 直连、非 CDN 不解析回中国、美西低延迟、无 301/302；别用被用烂的大厂域名。验证 openssl s_client -tls1_3 -alpn h2 + curl -sI（location 空）。
- 【已验证】选壳过程：同 /24 扫 TLS1.3+h2 邻居全是别人的 REALITY 或小站不可用 → 改测高校/政府/运营商站，Incapsula/Cloudflare/CloudFront/Akamai 托管全排除，剩自有 AS 的大学域名。
- 【已验证】每台独立 SNI/ShortID/密钥 → 独立指纹，避免一损俱损。

### 6. 端口与伪装取舍
- 【已验证】**高位端口 + 知名机构 SNI 组合**会被 GFW 建立高置信度代理画像（标准 HTTPS 站都在 443，自建 REALITY 全挂 5 位高位端口）。
- 解法：**:443 统一 SNI 复用**——前置 nginx stream ssl_preread（或 Xray/sing-box fallback）按 TLS ClientHello SNI 分流：自建网站/媒体/CDN 域名送本地 nginx/Caddy/relay，REALITY 伪装域名直接送进 REALITY → 外部探测器只见标准 443 TLS 行为。⚠️ 注意 L4 ssl_preread 与 PROXY protocol / fail2ban 真实源 IP 透传的兼容设计。
- 【已验证】**CDN 兜底腿（Trojan-WS 经 Cloudflare）**：客户端 TLS(sni=cdn.example.com) → CF 边缘 → 节点 nginx:443（cdn vhost，秘密 ws 路径）→ sing-box trojan-ws 127.0.0.1 → 出口。DNS 橙云 CNAME → 节点 DDNS 域（换 IP 自动跟上）。
  - 坑：CF 区 SSL 模式 Flexible（回源走 :80）而节点只开 443 → 起初 522；须对 cdn 主机名单独设 Configuration Rule SSL=Full strict（只影响这一个主机名）。
  - 去指纹：nginx 非匹配路径从 return 444 改返回 200 HTML + server_tokens off。
  - 定位：CF 免费版晚高峰慢（午间 ~345ms、晚高峰 ~804ms）+ 大流量视频有违反 CF 条款风险 → **只作主选末位应急**（自建 → 机场 → CDN），不抢日常流量。
  - 为什么 Trojan 不用 VLESS：Surge 不支持 vless，Trojan-WS 三家客户端都能用。
- 【已验证】**Hy2 端口跳跃**：nat PREROUTING 把 UDP 整段 REDIRECT 到本机实际 Hy2 口（从 conf 自动读，跳过 friends-*）；原口照常监听（旧订阅不受影响）；ufw 看转换后的目的口 → 不用给整段开口；只对 NEW 入站生效，本机出站临时端口回包走 conntrack 不误转。朋友段独立（23000:24999），FRIENDACCT mangle PREROUTING 在 REDIRECT 前执行同步计入不漏账。
- 【已验证】**UDP QoS 取舍**：Hy2 晚高峰部分省网 QUIC 限速/丢包；salamander 混淆破特征但**彻底失去 HTTP/3 伪装**变高熵 UDP（反而更像加密隧道）→ 不建议全局盲开；个别线路晚高峰 UDP 被严重 QoS 时优先切回 REALITY-Vision 或换运营商路由。

### 7. 被封后的处置流程（自动发现 + 故障切换 + 换 IP）
- 【已验证】**block-watch（被封自动发现，家里路由 cron 每 3h）**：经 OpenClash API 对每个自建节点测 delay（失败重测一次）；**连续 2 轮不通=确认被封、连续 2 轮通=确认恢复**；只在确认集合变化时发一条告警（🔴新不通/🟢已恢复/⚪仍不通）。防误报：单轮 >70% 不通 → 判家宽/OpenClash 自己挂，整轮作废；跳过计量住宅 ISP；首次运行只记基线。
- 【已验证】**entry-failover（网站入口故障切换，家里路由 cron 每 2min）**：从**中国侧**对每台候选做 1 次 HTTPS 全链路探测（--resolve 到该机 IP），失败才补探 2 次（控制频率 ~2 请求/分钟）；探测以 gid 65534 跑绕过 OpenClash 对路由器自身流量的劫持。当前入口连续 2 轮（4min）不健康 → 切最高优先级健康候选；更高优先级候选连续 5 轮（10min）健康 → 抢占切回；全挂不动 + 告警一次。切换改多条 A 记录（TTL 60）。备选连续 30min 不可达也告警一次（否则要等真需要切过去时才发现）。局限：只有单一运营商视角，家里断网时不切换。
- 【已验证】**为什么在中国侧跑探测**：要从"中国这一侧"判断入口能不能用（被墙/线路烂），海外机看不到。
- 【已验证】**换 IP 后必做清单**（切勿沿用旧域名+旧端口+立刻切大流量，否则复现 30h 重封）：
  1. 清理厂商重写的系统接口多余网卡行 → restart networking。
  2. **废弃旧域，换全新无关子域**（随机前缀）+ 独立 LE 证书；更新 DDNS env、nginx decoy、sing-box 各协议证书与 server_name。
  3. **一次性全量轮换全部公网端口**（REALITY 放 443 或全新随机高位；若放 443 需先迁走占用 443 的服务或用 SNI 分流/fallback+proxy_protocol 接管）；重跑 hy2-hop 与 friendacct-rules。
  4. 更新外部依赖白名单：落地机 ufw 放行新 IP 删旧、全舰队 fail2ban <FAIL2BAN_LOCAL_CONF> 换新 + reload、本机 ssh config + ssh-keygen -R 旧 IP。
  5. 更新订阅生成器（新域+新端口）→ 推送 → 同步 → **先用中国侧多地测通 4/4 并静置 15–30min 确认无立即探测突发**，再清家用 dnsmasq + OpenClash DNS cache + 切回主力流量。
  6. **订阅域永久留在 entry-failover + 后端 Caddy，切勿指回主力机**。
- 【已验证】换 IP 后 mihomo DoH 缓存旧 IP（TTL 过了仍返回旧值）→ POST /cache/dns/flush 才解析到新 IP；改 DNS 记录后家里要立即生效先 flush。
- 【已验证】跨机存活探测**全迁 tailnet 内网口**：原 PEERS 直连对端公网 REALITY 口 → 每秒级 invalid connection 污染服务端日志 + 触发高频异常握手计数；改指各机 tailnet 内网状态口后，来自舰队服务器 IP 的无效握手降至 0。

### 8. 降频 / 去噪 / 去关联（消除行为特征）
- 【已验证】探测降频 interval 60→300 + lazy:True（机场 300→600）；proxy-server-nameserver 剔除明文 UDP 统一 DoH；STUN 域名加 DIRECT 规则根除经 REALITY mux 的高频噪声。
- 【已验证】**证书 CT 去关联**：7 台代理 + 订阅/门户全集中同一主域 → CT（Certificate Transparency）日志公开可查，任一子域证书变更可串联全部主机。建议主力节点（尤其换新 IP 时）及朋友分发展示拆用完全无关新域；长期内部管理域与代理节点域物理隔离。
- 【已验证】**高风险 ASN 治本（方案 D，不加中转延迟）**：不做 dialer-proxy，把朋友重流量/日常高消耗下载拆向非高风控 ASN 的高信誉直连节点，或给朋友独立机器/限速、错峰分散首选顺位 → 剥离单 IP 流量密度与错误握手来源。
- 【已验证】**机场中转 → 自建落地**（mihomo dialer-proxy / Surge underlying-proxy）：墙内只连机场入口（被封由机场自己换），自建落地 IP 永远不被墙内直连 → 不会被墙；出口仍是自己的 IP（AI 分流照旧），内层 REALITY/Trojan 端到端加密，机场只看到连到我们服务器的 TLS。代价：多一跳延迟 + 吃机场流量 + 依赖机场稳定；Stash/Shadowrocket 支持度未验证。= 不花钱实现"入口可换 IP"。

### 9. 监控自身的盲区（谁监控监控者）
- 【已验证】家里（路由 + 家庭服务器）零外部探针 → 家宽挂=全静默。修：外部哨兵加"→ 家宽媒体端口"探测（沿用目标级防抖，1h 内 ≥3 次翻转自动静默）。
- 【已验证】自建 DERP 墙内 TCP 连不上 → 连家里设备的中继路径断（STUN 走 UDP 能通所以测距选它，但 DERP 是 TCP）→ 打洞失败的 peer 全超时。修：DERP 迁到墙内可达的近端机（域名不变改 A 记录），或先从 derpMap 摘掉回落官方。
- 【已验证】互监 PEERS 探活端口须与目标实际监听口一致（曾探 ufw 白名单只放特定机的端口 → 永远 down 等于没盯）；布防脚本 0 字节静默空跑 → wc -c + bash -n 验。

## ② 原作者特定环境经验（不可照搬）
- 【已验证】具体被封 IP/域名/端口/高风险 ASN 编号/朋友无效握手来源 IP/供应商换 IP 条款均为其私有或时效信息：
  - 搬瓦工 KiwiVM 免费换 IP 有 14 天窗口；DMIT Pro/EB 系列满足"开通≥7天、距上次换≥15天、ICMP+全部TCP被封、剩余≥7天"免费换，否则 $5/次（间隔≥7天），首连不通发工单免费换；搬瓦工免费双周换据论坛只限特定 SLA 款，其余 ~$7.39 且须已被封；Evoxt/VMISS 无公开换 IP 条款，LisaHost 不能换。
  - 主力机所在高风险 ASN 全段标红 + 95%+ 流量集中是其特定选址问题，换 IP 后仍面临更严苛阈值。
- 【推测】"中国侧单运营商视角"的 entry-failover/block-watch 适合其家宽（广东电信）；多运营商/多地域用户需多视角探针避免误判。

## ③ 需要重新验证的结论（含验证方法）
- 换 IP + 新域 + 新端口 + :443 后的实际寿命：静置观察 + 中国侧多地 TCP/UDP 分协议探测，记录是否再现探测突发。
- :443 SNI 分流（ssl_preread）与 PROXY protocol / fail2ban 真实源 IP 透传兼容：外部 curl --resolve 验 302/200，fail2ban 日志确认拿到真实客户端 IP。
- CDN 兜底腿晚高峰吞吐与延迟：晚高峰实测（午间数据不代表晚高峰）。
- salamander 取舍按节点角色：个别线路晚高峰 UDP QoS 实测后再定，不全局盲开。
- 方案 B（XHTTP 旁挂）需 Xray-core，与 sing-box 协同的运维复杂度；Stash/SR 对 dialer-proxy 支持度。
- 通配 DNS（nip.io/sslip.io）绕过修复在新版 sing-box：字面 IP + 通配 DNS 双试。

## ④ 可迁移到 FixCloud / Lucky / QNAP NAS 的具体做法
- **FixCloud（抗封基线）**：协议纯净化（退役无 fallback 的 AnyTLS/公网裸 SS2022，Trojan 补 decoy fallback、Hy2 补 masquerade）；借壳按自有 AS 机构域名标准选 + openssl/curl 验证；探测降频 + lazy + DoH；证书 CT 去关联（管理域与代理域物理隔离）；换 IP 全轮换清单（新无关子域 + 全新端口 + 白名单 + 静置观察再切流量）；高风险 ASN 流量分散。
- **Lucky / OpenWrt**：block-watch（连续 2 轮判封/恢复 + >70% 不通整轮作废防误报）+ entry-failover（中国侧探测 + gid 65534 豁免 + 防抖切换 + 备选坏了也告警）；回家用原生 xray REALITY + tailnet SS2022，关公网老 SS；跨机探活走 tailnet 不打公网 REALITY 口。
- **QNAP NAS**：回家经 tailnet 不暴露公网老 SS；外部哨兵补"谁监控监控者"（家宽/NAS 挂=全静默盲区）；自建 DERP 若墙内 TCP 不通要迁可达机；配置/凭据文件 600，备份刷新前排除 secret 或明确接受含 secret（旧包恢复会重开 tailnet 洞）。

## ⑤ 来源文档路径清单（只给路径，不给敏感内容）
- fork-clone/54-LA频封溯源与全舰队P0抗封加固-20261119.md
- fork-clone/55-代理协议抗封调研与现网风险盘点-20261119.md
- fork-clone/56-方案A协议纯净化与回家代理升级-20261119.md
- fork-clone/51-抗封三件套-20261031.md
- fork-clone/47-节点池扩容与红队三审-20261008.md
- fork-clone/29-东京中转节点-VMISS.md、fork-clone/30-香港备用节点-Evoxt.md
- fork-clone/04-网络架构与协议方案.md
- fork-clone/scripts/hy2-hop/hy2-hop.sh、hy2-hop.service
- fork-clone/scripts/entry/entry-failover.sh、README.md、hk-cmi-stream.conf、web-relay-80/443.service

> 范围澄清【已验证】：scripts/fnd/{gen_ics.py,test_fnd.py,betty_timetable.html} 是"四校课表 → .ics 生成器"（朋友共享空闲日历），与节点/协议/订阅/抗封方向无关，未纳入本知识库。scripts/subtrans/ 是字幕 AI 翻译管线（非订阅转换），其工程健壮性模式已在草稿 05 末尾提炼。
