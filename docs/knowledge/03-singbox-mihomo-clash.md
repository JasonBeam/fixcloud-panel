> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

# 协议选型与字段语义：sing-box / mihomo / Clash 生态

> 来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。
> 【已验证】= 本次审计实际读到的原作者记录；【推测】= 提炼者推断。真实域名/IP/凭据/ASN/设备别名一律不出现：作者自有域用 example.com / node-a.example.com，借壳目标用"某自有 AS 的高校/机构域名"描述，IP 用 192.0.2.10 / 198.51.100.20 / 203.0.113.30，凭据用 <EXAMPLE_SS2022_KEY_BASE64_INVALID> / 00000000-0000-4000-8000-000000000000 / <EXAMPLE_PASSWORD>。协议名/字段名/命令名属事实性技术信息予以保留。

## ① 通用可复用经验（可直接迁移）

### 1. 内核选型与角色分工
- 【已验证】服务端用 **sing-box 裸核**（约 20MB，对比 Xray 约 60MB），单实例多 inbound 共享一套路由；用 233boy 脚本部署，**不上 3X-UI 面板**（减暴露面与依赖）。
- 客户端/路由侧用 **mihomo（Clash.Meta）内核**读 Clash yaml；**Stash 是闭源独立实现，只是读 Clash 配置格式，≠ mihomo 内核**（健康检查语义不同，见 §6）。Surge 是另一套私有配置语法。
- 【已验证】协议演进：旧 Surge 不支持 REALITY → 曾双协议并存；一度 5 协议 → 2026-10-31"抗封三件套"（Hy2 端口跳跃 + CF CDN Trojan-WS 兜底 + 每 3h 逐协议被封检测）→ 2026-11-19 收敛为 **REALITY（非 CDN SNI）+ Hy2（masquerade + 端口跳跃）+ Trojan-TLS（LE 真证书 + HTTP decoy fallback）+ CF CDN Trojan-WS**；退役 8 个公网 SS2022 + 10 个 AnyTLS。fallback 统一 REALITY → Hy2 → Trojan。

### 2. 协议横向评估（抗主动探测 / 抗流量分析 / 客户端兼容）
> 以下为原作者 2025–2026 调研结论的重述，非原文复制。

| 协议组合 | 伪装原理 | 抗主动探测 | 抗流量分析/ML | 客户端兼容 | 定位 |
|---|---|---|---|---|---|
| **VLESS+REALITY+xtls-rprx-vision** | uTLS 伪装外部无 CDN 合规站 TLS 指纹；Vision 对内部 TLS 帧填充消去 TLS-in-TLS 特征 | 极强（未认证探测透明转发回真实目标站，无自签/自有域泄露） | 极低（直连 TCP 金标准） | mihomo/Stash/Shadowrocket ✅；Surge Mac 6.12+/iOS 6.0+ ✅ | **第一主力** |
| VLESS+XHTTP(SplitHTTP)+REALITY | 数据切片封装进标准 HTTP 请求/响应（packet-up/stream-up/stream-one），外层 REALITY 或 CDN/Nginx TLS | 极强（真实站点回落，对 CDN 友好） | 更低（打破单条长连接字节流，模拟碎片化浏览） | mihomo/SR ✅；Stash ⚠️；Surge ❌；**sing-box 原生 ❌（需 Xray-core）** | 极端审查期加餐 |
| NaiveProxy（Caddy forwardproxy） | 复用 Chromium 真实网络栈跑 HTTPS H2/H3 | 极强（本身生产级 Caddy 站） | 极低（帧行为与真 Chrome 一致） | mihomo ❌（需外部）；Surge ❌（iOS 不可用） | 高隐蔽桌面/路由旁挂备份 |
| **Hysteria2**（端口跳跃+masquerade） | QUIC 改拥塞控制 + UDP 端口跳跃 + HTTP/3 伪装 | 强（配真实 masquerade 探测回 HTTP 页） | 中（晚高峰部分省网 QUIC QoS；salamander 破特征但失伪装变高熵 UDP） | 全客户端 ✅ | **高速抗丢包副力** |
| Trojan（带 HTTP decoy fallback） | 真域 TLS + 首包口令，失败回落本地 200 HTML | 强（补 fallback 后） | 中偏高（无 Vision 消 TLS-in-TLS 长度特征；依赖自有域证书暴露同源关联） | 全客户端原生 ✅ | 旧客户端/兜底过渡 |
| AnyTLS v2 | 可调 early-write padding 隐藏 TLS-in-TLS 长度 | ⚠️ 弱（sing-box 1.13.13 无 fallback，握手后对非认证探针直接 EOF） | 中 | mihomo ✅；Surge 5.17+ ✅ | **最大短板，已退役** |
| TUIC v5 | 标准 QUIC 0-RTT | 中偏弱（缺端口跳跃配合更易受 UDP QoS） | 中 | mihomo/Surge ✅ | 已有 Hy2 覆盖，无必要重复增暴露面 |
| Snell v5/v6 | Surge 私有，v6 PSK 衍生降指纹 | 中（无标准 HTTP 回落） | 中 | 仅 Surge/少量派生（朋友端 Clash/Stash/SR 不兼容） | 不适用多客户端舰队 |
| ShadowTLS v3 / Mieru | 二次 TLS 握手移交 / 自定义多路复用帧 | 偏弱/中（学术 *Chasing Shadows* 揭示转发状态机/TCP 时序易被多包探测分辨；Mieru 高熵 heuristic） | 中偏高 | 维护负担重 | 已被 REALITY 替代，不建议回退 |
| MASQUE / TrustTunnel | IETF H3 CONNECT-UDP / 企业隧道 | 未针对 GFW 主动防御与垫片填充优化 | 高 | 生态极小 | 不适合翻墙 |
| **SS2022** | 2022-blake3-aes-128/256-gcm | ⚠️ GFW FET + 主动重放（salt not unique / bad timestamp）可识别 | — | mihomo 不支持 chacha20 变体 → 用 aes-256-gcm | **公网裸口高危，已退役**；多用户须 EIH |

- 【已验证】Surge 官方明确**不支持 XHTTP / HTTPUpgrade / mKCP / VLESS Encryption**；Mac 6.12.0+ / iOS 6.0.0+ 才原生支持 VLESS+REALITY+xtls-rprx-vision（作者本机曾 6.11.0，差一个小版本，升级后一键翻 SURGE_VLESS=True）。

### 3. REALITY 借壳（dest/SNI）选择标准
- 【已验证】标准：目标站须 **TLS1.3 + h2（ALPN）**、国外未被墙的 VPS 可直连、**非 CDN 且不解析回中国**、美西低延迟、**无 301/302 跳转**；别用被用烂的 apple/microsoft，别偷 dl.google.com 这类。
- 验证命令：`openssl s_client -tls1_3 -alpn h2`（TLS1.3 与 h2 两行都要出现）+ `curl -sI`（location 头为空）。
- 参数：`flow=xtls-rprx-vision`、传输 TCP RAW、`uTLS=chrome`、**SNI == dest**。
- 【已验证】违规借壳（CDN/301 域名，如某些大厂官网/CDN 控制台）会被主动探测画像；改用**自有 AS 的高校/机构域名**（非 CDN、TLS1.3+h2+X25519、HTTP 200）。对照组（唯一用自有 AS 大学域名的节点）连续 7 天 **0 次** GFW 探测突发，其余借壳 CDN 的节点均被探测。
- 选壳方法：同 /24 扫 TLS1.3+h2 邻居往往全是别人的 REALITY（伪装 cloudflare/yahoo/apple）或小站，不可用 → 改测东南亚高校/政府/运营商站，**Incapsula/Cloudflare/CloudFront/Akamai 托管的全排除**。
- 【已验证】每台独立 SNI/ShortID/密钥 → 独立指纹；单 IP 流量节制。

### 4. 分享链接字段语义
- 【已验证】VLESS：`encryption=none&security=reality&flow=xtls-rprx-vision&type=tcp&sni=…&pbk=…&sid=…&fp=chrome`。
- **空 shortId 必须摘除**：short_id 为空时任何拿到 pbk+SNI 的人都能完成握手层，认证只剩 uuid。零停机迁移用**服务端双 id** `short_id:["", "<新id>"]`（旧订阅空 id 与新订阅新 id 同时可连）；≥1 周等所有客户端重拉后再摘空 id，摘前用日志确认无空 id 连接。⚠️ 233boy `sb` 重写 conf 可能把 short_id 打回空 → 动过 sb 后核对。
- Hy2：`alpn=h3&sni=自身域名`（LE 真证书免 insecure=1）+ masquerade；Trojan：`sni=自身域名` + decoy fallback。
- 【已验证】sb 工具输出的 IP 版链接换 IP 即失效 → 用 DDNS 域名版。

### 5. sing-box 与 mihomo 配置差异（关键陷阱）
- 【已验证】**sing-box 无原生 fallback 出站**（只有 selector/urltest，写 fallback 报 `unknown outbound type:fallback`）→ 优先级 fallback 用 selfheal 探活 + 防抖 + 翻 outbound（selector + clash_api 零重启）。mihomo 有 fallback 组（组级 url 测所有成员，含内置 DIRECT）。
- 【已验证】**sing-box 1.13 出站 domain_strategy 废弃**（写则 FATAL）→ 走 DNS 规则（如 example.com → ipv4_only 堵 v6 泄漏）。
- 【已验证】**Trojan fallback 与 ip_is_private:reject 冲突**：sing-box 把 fallback 连接经内部 router 投递到 127.0.0.1:18080，被首条 `ip_is_private:true→reject` 静默拒绝 → 主动探测收 Empty reply。修：在 resolve 与 ip_is_private 之间精确插 `{network:tcp, ip_cidr:["127.0.0.1/32"], port:[18080], outbound:direct}`，既让回落返回 200 伪装页，又保持对其它管理口/tailnet 的隔离。
- 【已验证】**ip_is_private reject 被"域名→私网 IP"整体绕过**：reject 是 IP 规则，目的地是域名时路由阶段尚未解析 → 不命中 → route.final 落 direct → sing-box 自己解析再拨号。用通配 DNS（nip.io/sslip.io）复现：`127-0-0-1.nip.io` → 200、私网 tailnet IP 的 nip 形式 → 200（字面 IP 则 000 被拒）。修：规则序前置 `{action:resolve, strategy:prefer_ipv4}` 再 ip_is_private reject + cgnat reject（sing-box ≥1.11）。**教训：凡 IP 判据的 reject 前面必须先 resolve；验证要同时试字面 IP 和通配 DNS。**
- 【已验证】sing-box 自带 DNS（dns.servers + route.default_domain_resolver），不依赖系统 resolved；tailscale 设 accept-dns=false 防硬重置后 DNS 无上游全 SERVFAIL（端口活但直连黑洞）。
- 【已验证】mihomo DoH 缓存旧 IP，换 IP 后需隔几分钟二次 flush；proxy-server-nameserver 明文 UDP 查询会暴露 → 统一 DoH（保留数值 default-nameserver 作 bootstrap）。

### 6. 健康检查语义差异（客户端兼容陷阱）
- 【已验证】mihomo `/group/<组>/delay` **不认 expected-status**（单节点 `/delay?expected=401` 才认）；AI 组探 api.openai.com/v1/models 用 expected-status:401（403 判死）；Surge 无此参数靠顺序；store-selected 只更新本地不回写仓库。
- 【已验证】**Stash 按代理级 benchmark-url/benchmark-timeout 测**（组上没有测试 URL），默认探 apple.com（墙内可达）→ 内置 DIRECT 墙内也判活 → 卡直连。修：门组第一成员改 type:direct 的探测代理，自带 benchmark-url=https://www.google.com/generate_204（用 HTTPS：墙内 DNS 污染可能指向会回 HTTP 的随机主机造成假阳性；HTTPS 证书对不上必失败，测不了 HTTPS 的后果是永远判墙内=一直走代理，安全方向）。同一份 yaml 两边通用（mihomo 忽略 benchmark-*）。
- 【已验证】Surge 离线 surge-cli --check/lsp 比 app 宽松（放过"direct 策略+每策略 test-url"行），app 真加载才报错 → 离线校验不能当最终依据；Surge 测试 URL 一律 http + 全局 internet-test-url。

### 7. 参数取舍（为什么这样设）
- 【已验证】Hy2 **Brutal 拥塞控制是最大性能杠杆**，需低峰测线速后设约 80%；端口跳跃 `ports:21000-22999`（自用）/`23000-24999`（朋友）+ `hop-interval:30`；服务端 HY2_HOP_RANGE 与客户端 HY2_HOP_PORTS **必须一致**。
- 【已验证】探测降频：fallback 组 interval 60→300 + lazy:True（机场 300→600 + lazy）。非 lazy 60s 每日 1440+ 次固定间隔探测本身就是暴露特征。
- 【已验证】回家隧道升级：公网入口 VLESS-REALITY:28443（借壳某 Apple 中国站，实测 TLS1.3+h2）+ tailnet 专用 SS2022:8888（2022-blake3-aes-256-gcm 独立 32B PSK），**关闭公网老 AEAD ss-libev:8888**（7 年前镜像、固定密码、无时间窗防重放）。home-proxy 以 user=nobody/gid=65534 运行，命中 OpenClash fw4 openclash_output 首条 `meta skgid 65534 return` 豁免 → 出访/回访内网零经 REDIRECT，无回环。
- 【已验证】SS2022 多用户须改 EIH（服务端 password→iPSK，客户端密码→serverPSK:userPSK），会破坏主人现有 SS 配置 → 朋友版无 SS，用 REALITY/Hy2/Trojan。

## ② 原作者特定环境经验（不可照搬）
- 【已验证】具体借壳域名/各机端口/REALITY 密钥对/shortId/客户端版本基线（Surge 6.11→6.12、Stash 4.3.5、mihomo alpha 某 commit）/高风险 ASN 编号均为其私有或时效性信息；借壳目标随封锁态势变化，不可照搬具体域名，应照搬**选择标准与验证方法**。
- 【推测】"REALITY 主力 + Hy2 副力 + Trojan-WS CDN 兜底"三协议收敛适合其苹果全家桶 + OpenWrt 路由 + 多客户端朋友 fleet；纯 Xray 生态或单一客户端可另选 XHTTP/NaiveProxy。

## ③ 需要重新验证的结论（含验证方法）
- Stash 对 hysteria2 `ports` 字段支持未实测（未知字段会被忽略，最差=单口照常）→ 真机抓包确认是否打跳跃段。
- XHTTP 需 Xray-core，与 sing-box+Surge 全兼容体系割裂 → 旁挂第二套进程前评估运维复杂度。
- nip.io/sslip.io 绕过修复在新版 sing-box 的行为：同时试字面 IP 与通配 DNS，复验私网目标全 502、example.com 200。
- 各协议晚高峰 QUIC/TCP QoS：低峰/晚高峰分别测线速与丢包。
- 借壳目标当前是否仍 TLS1.3+h2+无 301+非 CDN：openssl s_client + curl -sI 重验（目标站可能改版）。

## ④ 可迁移到 FixCloud / Lucky / QNAP NAS 的具体做法
- **FixCloud**：协议栈收敛 REALITY（主力）+ Hy2（抗丢包副力）+ Trojan-WS（CDN 兜底）；借壳按"自有 AS 机构域名 + TLS1.3+h2 + 无 301 + 非 CDN"标准选并用 openssl/curl 验证；shortId 双 id 零停机迁移；探测降频 + lazy + DoH；sing-box 路由 resolve 前置挡板 + Trojan fallback 豁免 127.0.0.1。
- **Lucky / OpenWrt**：回家用原生 xray VLESS-REALITY 公网入口 + tailnet 专用 SS2022，关公网老 AEAD SS；home-proxy gid=65534 命中 OpenClash 豁免防回环；mihomo 健康检查 expected-status 语义与 Stash benchmark-url 差异要在订阅生成器里分别处理。
- **QNAP NAS**：经 tailnet SS2022 访问，不对公网暴露老 SS；注意 QTS 权限墙（守护进程跑 admin/root）；sing-box/mihomo 配置改动先 check 再重启、保留 lastgood 回滚。

## ⑤ 来源文档路径清单（只给路径，不给敏感内容）
- fork-clone/04-网络架构与协议方案.md
- fork-clone/55-代理协议抗封调研与现网风险盘点-20261119.md
- fork-clone/56-方案A协议纯净化与回家代理升级-20261119.md
- fork-clone/51-抗封三件套-20261031.md
- fork-clone/06-节点信息与链接.md、fork-clone/08-备份节点Akko-链接.md
- fork-clone/47-节点池扩容与红队三审-20261008.md
- fork-clone/29-东京中转节点-VMISS.md
- fork-clone/scripts/hy2-hop/hy2-hop.sh
