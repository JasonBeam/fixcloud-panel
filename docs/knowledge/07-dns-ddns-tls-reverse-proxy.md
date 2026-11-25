> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。

> 作者统一称「原作者」。示例一律用 example.com / 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24 / <EXAMPLE_TOKEN> 等文档示例值；机器以角色代称，不出现真实主机名/IP/域名/凭据/设备标识。【已验证】=实际读到/测到；【推测】=推断待核。

# 07 · DNS / DDNS / TLS / 反向代理

## ① 通用可复用经验

### 1. DNS 记录分层
- **A 记录灰云 DNS-only（proxied:false）TTL 120/60**：CF 只解析不挡流量，源站 IP 直接暴露。脚本强制 proxied:false，不会误开橙云。【已验证】
- **橙云 CF 代理隐藏源 IP**，但免费版只代理白名单端口（80/443/2053/2083/2087/2096/8443/8880）。非标端口（如家宽自定义 HTTPS 入口）就地橙云行不通，必须换端口 + 改所有 URL/书签/门户卡片/回调。**灰云下 CF 规则不生效**——要么换端口橙云，要么接受裸奔。【已验证】
- **泛域名解析风险**：*.example.com 任意子域都返回家宽 IP → 攻击者可造无限子域名全砸向你家（枚举/反射/被挂进列表后爬）。家宽无 DDoS 防护，IP 被盯上一波流量打瘫全家网，所有服务同 IP 一损俱损。【已验证】
- **CAA 记录**锁签发方（把签发权限定到实际用的 CA，issuewild 泛域名要单独授权）；无 CAA = 任何 CA 被骗/被黑都能给你签合法证书用于中间人。注意：CF Universal SSL 会自动加一组 CAA 放行 5 家 CA（橙云边缘证书依赖），别误删。【已验证】
- **DNSSEC**（CF 一键开，DS 记录要在注册商贴一次）防 DNS 投毒，优先级低；**DMARC** p=none 仅声明不拦信，**不设 rua** 以免公网 DNS 暴露邮箱；SPF v=spf1 include:~all。【已验证】
- 删记录前全量备份；指向已不属于自己的旧 IP 的记录有子域接管风险，要删。【已验证】

### 2. DDNS 更新
- 节点链接用**域名而非 IP**：VPS 脚本每 3-15min 检测自己公网 IP，变了调 CF API 更新 A 记录，换 IP 客户端无需改动，TTL 120s 几分钟全网生效。【已验证】
- cf-ddns.sh 设计：set -euo pipefail；env（600，CF_API_TOKEN + CF_RECORD）；${VAR:?} 缺即退出；取本机公网 IP（cloudflare trace ip=，失败 fallback 另一 api）；**CF API 非 JSON/不可达 → skip exit 0**（不报错防误判，偶发非 JSON 静默跳过）；cur==ip && curttl==120 → unchanged exit；body 强制 proxied:false TTL 120；rid null → POST 创建否则 PUT 更新。【已验证】
- **CF API Token 最小权限**：DNS·Edit 仅单 zone，只存服务器 env（0600）与 age 加密备份，不以明文入库。轮换：CF 删旧建新 → 服务器 read -rsp 写入 env chmod 600 unset。【已验证】
- IP 固定后 timer 降频（3min→15min）；统一版顺手纠正 TTL≠120 的记录。【已验证】
- **换 IP 流程演进**：旧流程（面板换 IP→等 DDNS 自动更新→客户端无需改）适合静态/非高危节点；高危节点换 IP 须同步启用新独立子域 + 轮换全套入站端口 + 重签 LE 证书 + 静置观察再切回流量（不复用旧域旧端口）。【已验证】

### 3. 双栈陷阱
- **家宽发布 AAAA 但入站 v6 不通** → nginx 在 v4/v6 间轮询，约一半请求挂死。解法：中转只走家宽 IPv4（/etc/hosts 别名 家宽 IPv4 别名，DDNS 变化由脚本跟进）。【已验证】
- 代理强制 IPv4 优先出站（prefer_ipv4）；**不在系统层关 IPv6**（sing-box 监听 ::，关栈重启绑不上→节点挂）。gai.conf IPv4 优先只影响节点自身 apt/curl，不影响代理流量（sing-box 自己做 DNS + Happy Eyeballs）。【已验证】
- **客户端 IPv6 三层绕过**（详见 09/52）：路由 OpenClash ipv6_enable=0 但 LAN 仍发 RA/DHCPv6、fw4 TUN 转发全 meta nfproto ipv4 无 v6 劫持 → LAN 设备公网 v6 直接出 pppoe 不进代理；客户端 ipv6=false 不等于拦 v6（只是不查 AAAA，仍可按地址直连）。【已验证】

### 4. 证书签发与同步
- **真证书 > 自签**：certbot dns-cloudflare（复用 CF token，不用开 80 口）+ deploy-hook 续期重启服务。自签是例外须写明理由 + 客户端 skip-cert-verify + 记合规矩阵。【已验证】
- **证书哨兵必须同时验信任链，只看到期日会瞎**：用户误删证书条目回落自签（CN=Lucky 有效期到 2028），只看 notAfter 是剩 900 天一片绿，浏览器照样红。取 openssl s_client 的 Verify return code != 0 即 trusted=no，与已过期同等严重。【已验证】
- 档位 ok(>14)/warn(≤14)/urgent(≤3)/untrusted/expired，数字越大越差；**只在档位变差时播报**，变好播一次恢复，卡坏档最多每 3 天复读；探不通不报警（可达性由别的探针管，免一条线路抖引发两路告警）；**不自动修**（续期必须人工，签发方在后台要确认换绑）。证书是慢变量，每天只探一次（DAILY_GATE 24h）。【已验证】
- cert-check.py：先用 verified ctx（ssl.create_default_context）拿 notAfter；捕获 SSLCertVerificationError → 改 unverified ctx 拿 DER binary 解析 days 但 trusted=False；原子写 tmp + os.replace；失败显式记录不静默跳过；支持 name:port。【已验证】
- **ACME 账户坏坑**：Lucky 续期报 acme error 400 malformed / No Key ID in JWS header = 账户注册状态坏/丢，不是 DNS-01 问题不是 CF 凭据问题（DDNS 同套凭据一直好）。解法：新建一张证书即注册全新 ACME 账户绕开坏的。【已验证】
- **CT 日志误判坑**：只看 CT 日志日期以为续到了，其实 06-09/07-02 都是 Google Trust Services / Sectigo = **Cloudflare Universal SSL 边缘证书**（CF 给托管 zone 自动签 *.domain + domain，定期续期都进 CT 日志），与 Lucky 无关、Lucky 里根本不存在也用不上（非标端口橙云救不了）。**必须看 issuer_name**：只有 Let's Encrypt 那张才是 Lucky 的。【已验证】
- **DNS-01 传播检查被 OpenClash 劫持**：Lucky 把 DoH 请求发到 53 端口（DoH 应走 443，URL 本身就错）+ 路由器 OpenClash 把所有出站 53 劫走 → 传播检查查不动。解法：证书条目打开「忽略传播检查错误」+「禁用权威 NS 传播检查」（直接交 LE 自己验证，LE 从它自己解析器查不受你家 OpenClash 影响）。【已验证】
- **删证书回落自签更糟**：证书条目删除会连同 ACME 任务和 CF 凭据一起没，回落内置自签，服务照常 HTTP 302 但浏览器从「过期」变「不受信任」一样红且没法再自动续。从备份还原必须**先 docker stop 再覆盖文件**（Lucky 把配置缓存内存，活着时写文件会被刷回去）。【已验证】
- 一张泛域名证书覆盖 10 个服务，只探 1 个就够（探 10 个纯属自己给自己刷屏）；但**两个 watcher 目标集要互补**，别让唯一 watcher 跑在被保护那台机上。【已验证】

### 5. Caddy / nginx 反向代理
- **Caddy v2 默认不压缩**，必须显式 encode zstd gzip（全站性价比最高一行，实测 12 文本资源 1203KB→308KB 省 74%）。【已验证】
- **缓存三层互斥按序**：immutable（vendor/* + fonts/* 永不变 + 带 ?v= 的 js/css）→ public,max-age=31536000,immutable；no-cache（无 ?v= 的 js/css，靠 ETag/Last-Modified 拿 304）；no-store（HTML + 实时 JSON telemetry）。**no-store 别打在永不改变的 vendored 资源上**（803KB MapLibre 每次重下从 HK 拉 9.16s）。vendor/fonts 的 handle 放通配之前避免被覆盖。【已验证】
- **安全头 snippet**：HSTS（max-age=31536000，暂不加 includeSubDomains/preload 因 preload 不可回退）、X-Content-Type-Options nosniff、X-Frame-Options SAMEORIGIN、Referrer-Policy、Permissions-Policy、**-Server**（去后端透传 Server:BaseHTTP Python 版本）+ 各 reverse_proxy header_down -Server 兜底。CSP 用 Report-Only 起步（内联 token 需 nonce）。【已验证】
- forward_auth 做登录墙（authsvc:5000 uri /verify）；*.bak* respond 404；telemetry deny 点文件/.py/.tmp/敏感 json；ntfy /metrics、smsbus /stats respond 404（无鉴权指标别暴露）。【已验证】
- **SSE /api/stream 用 flush_interval -1 且排除压缩**（压缩会缓冲事件拖慢推送）。【已验证】
- **nginx stream L4 SNI 透传**（ssl_preread on + proxy_protocol on + map $ssl_preread_server_name 分流）：只嗅 SNI 不终结 TLS，TLS 在后端终结 → 边缘碰不到 HTTP，无法边缘限流/缓存/WAF/加安全头（全站缺安全头是架构决定）。**PROXY protocol 保真实客户端 IP**。要边缘化须把入口机从 stream 改 http 真终结 TLS。【已验证】
- **nginx 媒体反代统一 recipe**：keepalive 上游 + WebSocket（map Upgrade/Connection）+ Range + 关 buffering + 长超时 + 登录 limit_req + certbot dns-01 + emby-upstream-reload.timer 每 5min 追家（域名 v4/v6 变即 reload）。【已验证】
- **备份 vhost 别放 sites-enabled**：include 是 * 会加载 .bak → limit_req_zone 重复直接 emerg。【已验证】
- socat L4 转发加不了 X-Forwarded-For → 后端看到来源全是转发机同一 IP（影响按 IP 限速，见 09 authsvc）。【已验证】

### 6. 单域名多服务（Emby 统一入口）
- **一域名切 4 入口可行**：前提 4 入口后面同一台 Emby（同 ServerId 同 token），换入口对客户端透明不用重登。【已验证】
- **须统一端口**：DNS 只能换 IP 不能换端口，4 入口端口不一（443/8443）→ 全部加 listen 统一端口 ssl + ufw 放行；每台 nginx 证书加 SAN 统一域名（certbot dns-01 --expand -d）。【已验证】
- **健康判定必须端到端**（经 relay 回家拿 /System/Info/Public 的 Version），不能只看 relay 活（relay 活但回家腿死照样挂）。【已验证】
- **方案 A（推荐免费）DNS 故障切换单 A 记录**：统一域名 A 灰云 TTL60 → 当前最优入口，优先级 hub>eu>na>as。切换器防抖（当前连续 2 轮坏才切 / 高优先级连续 5 轮好才抢回 / 全挂不动只告警一次）；候选 IP 每轮按域名解析，换 IP 自动跟上。跑在监控中枢，挂已有端到端探测（海外朋友视角）。【已验证】
- **兜底撤离**：切换器自己整机挂 → 家里路由 cron 兜底（心跳 >10min + 记录仍指 hub + 家里探 hub 连续 3 轮不通 → 改指 eu，只撤离不抢回，不和切换器抢主控）。【已验证】
- 方案 B CF Load Balancing 付费带地理分流（约 $5/月起含 2 源，4 源约 $15/月，DNS-only 灰云，Emby 走 CF 代理违反 ToS 且慢）；方案 C 自建 GeoDNS 不推荐（多两台关键 DNS，挂了 Emby 就找不到，维护最高）。【已验证】
- **DNS 切换不迁移正在播的流**：客户端断一下重连才解析新入口；电视盒子/部分 App 无视 TTL 多缓存几分钟，现实切换 1-5min。零基建路：部分第三方 Emby 客户端支持同服务器配多线路自动择优，把 4 分区域名都填。【已验证】
- **时区感知架构核心洞察**：瓶颈 = 中国晚高峰 20-01 CST 出境限速，非地理距离。NA/EU 观看 = 中国 off-peak（时差大）→ 长途直连出境反而快，不绕 HK；亚洲观看 = 中国晚高峰 → 长途直连塌 <8M，必须近港出境。【已验证】

### 7. 内网穿透与 Tailscale
- **Peer Relay 转发优先（直连反而慢）**：打洞只负责让两边能对发 UDP，路线由运营商决定。家→远端直连走普通线 ~200ms，经近港转发机走精品线 ~45ms。Tailscale 顺序写死「直连→Peer Relay→DERP」，故家里路由 nft 挡住发往远端公网 IP 的 UDP 逼它走转发；转发坏了看守脚本撤规则恢复直连。【已验证】
- 转发机设 tailscale relay-server-port + ufw allow udp；家里 nft 表 inet ts_relay_pref 的 output/forward 丢弃发往远端公网 IP 的 UDP（不在 fw4 里，fw4 reload 不影响，重启后表消失 cron 下一分钟重建）。【已验证】
- **看守脚本**：路由器 ping 远端 8 次出现任意一次 via peer-relay 算正常；连续 5 轮只有 DERP 或超时 → 撤规则冷却 30min 再试；远端离线或 ping 到直连（说明已不在那个网络）不算失败。【已验证】
- **两台转发同时开反而变差**：Tailscale 没有固定选延迟低的那台，路径频繁切换；只留一台后丢包/延迟明显改善。【已验证】
- **🔴 ACL 踩坑**：tailnet policy 原本没写访问规则靠默认全放行，第一次只加 relay grants 就变成只放行写明内容 → 全 tailnet TCP 断（tailscale ping 还通因为 disco 不过滤）。**动 policy 前先读现有内容，没有 acls/grants 的 policy 加任何一条都会从默认放行变默认拒绝**。补全放行 grants（src[*] dst[*] ip[*]）+ relay 授权。【已验证】
- DERP 是 TCP，强制走 DERP 不是解法（去程经接收方 home DERP 回程经发起方 home DERP，估算比直连还慢）。【已验证】
- **MagicDNS 短名坑**：--accept-dns=false 后短名（http://<路由短名>:9090）不解析 → 改 tailnet IP。关 MagicDNS 前先 grep http://短名。【已验证】
- **tailscale 接管 resolv.conf 黑洞**：tailscaled foreign 模式把 /etc/resolv.conf 只剩它自己 100.100.100.100，无上游 → 所有非 ts.net 域名 SERVFAIL。VPS 没有任何东西用 ts.net 名字 → tailscale set --accept-dns=false 根除。【已验证】
- 流量转发计入 VPS 配额；远端公网 IP 写死变了规则失效退回直连不会断（但该 IP 其他 UDP 也被丢弃，同网络其他设备也算在内）。【已验证】

## ② 原作者特定环境经验（标注依赖）
- **6 网站入口域名 entry-failover**（依赖：家里 OpenWrt 必须在中国侧判断入口能不能用，海外机看不到）：A 灰云 TTL60 → 一台入口机 → 80/443 原样转发东京后端 Caddy（tailnet）TLS 由 Caddy 终结。候选优先级近港精品 CMI（nginx stream SNI 分流，媒体域名→本机 PROXY protocol 保真实 IP，其余→剥头→Caddy）> 1G 晚高峰稳 > 三网 BGP（曾被墙）> 电信精品联通差。切换器家里 cron 每 2min 中国侧广东电信 HTTPS 全链路 --resolve 探测，gid65534 跑绕 OpenClash 对路由器自身流量劫持；当前连续 2 轮（4min）坏切最高优先级健康候选，更高优先级连续 5 轮（10min）好抢占切回，全挂不动 + 🆘 一次。**局限：只电信一视角，家里断网不切换维持现状**。【已验证】
- **Lucky 家宽反代 10 服务共用泛域名证书**（依赖：iStoreOS 容器 lucky:3.0.0beta，配置 .lkcf 私有加密格式读不了）：非标 HTTPS 入口端口不在 CF 白名单，橙云救不了；ACME 账户坏 + DNS-01 传播检查被 OpenClash 劫持双重坑。【已验证】
- **亚洲分区入口 走 tailnet 绕 TCP 封锁**（依赖：近港入口机 公网 IPv4 被墙 TCP 双向，但 近港入口机↔家路由 tailscale 直连 UDP 15ms 不受影响）：上游改家路由 tailnet IP，reload timer 停用因 tailnet IP 固定。⚠️curl 默认 HTTP/2 经 tailnet 挂起，HTTP/1.1 正常（nginx 上游本 1.1 不受影响）。【已验证】
- **自建 DERP**（依赖：derper.service + 证书私钥备份）；**家宽公网只 3 口**（WAN→LAN 加固后）。【已验证】
- **判断家里公网 IP 别看 ipify**（依赖：家里路由 跑 OpenClash 出站被代理劫走，curl ipify 得到假 IP）：看 ip addr show pppoe-wan / ubus call network.interface.wan status。【已验证】

## ③ 需要重新验证的结论（给验证方法）
- **DNS 切换实际生效时间**：验证：TTL60 + 客户端缓存，电视盒子/部分 App 无视 TTL；实测切换后多久客户端真正连新入口（1-5min 是估计）。【推测：依客户端】
- **证书自动续期无人值守**：验证：新 ACME 账户 + 忽略传播检查两开关，约 60 天后看是否真自动续（notAfter 推进 + issuer 仍 LE）；证书哨兵剩 14 天报警兜底。【已验证：首次手动成功，自动续待时间验证】
- **Peer Relay 多日稳定性**：验证：只测过一个晚上（无晚高峰长期数据），多日 ping/下载对比；看守脚本阈值改 5 轮后没重新演练退路。【已验证：单晚数据，多日未测】
- **双栈 v6 直连绕过**：验证：conntrack 看 LAN→internet v6 连接数应 =0（关 RA/DHCPv6 后）；手机 v6 跑 WebRTC/DNS 泄漏测试。【已验证方法，真机未全覆盖】
- **DDNS 换 IP 后全套**：验证：换 IP 后新子域 + 轮换端口 + 重签证书 + 中国多地 Globalping 6/6 通 + 家里 OpenClash 清旧 IP 缓存（killall -HUP dnsmasq + mihomo /cache/dns/flush）后 5 协议全通。【已验证方法】
- **入口切换算术**：验证：DOWN_N=2×2min≈4min 检测下限 + TTL60 + 客户端缓存；抢占回更优需 UP_N=5≈10min；入口机故障最坏 ~5-10min 网站不可用（可接受），家宽上联故障无界。【已验证：单视角局限】

## ④ 来源文档路径清单
- 07-DDNS与域名.md（记录分层 / cf-ddns 部件 / 换 IP 流程 / 重命名否决）
- 10-配置备份.md（CF token 轮换 / DNS 记录清理 / DMARC/SPF / TTL 纠正）
- 14-Homelab门户-Tailscale.md（证书 08-06 过期根因 / ACME 账户坏 / CT 日志误判 / DNS-01 传播检查 / SSH 隧道后台 / Tailscale 升级）
- 32-Emby媒体服务器.md（跨区中转 / 三分区只走家宽 IPv4 / 亚洲分区入口 宕 3 天）
- 50-舰队巡检与Emby单域名-20261030.md（conntrack 重启失效 / Emby 一域名切 4 入口 / 方案 ABC / Globalping 中国 6 地 / 换 IP / 端口迁移）
- 53-Tailscale转发优先-PeerRelay-20261106.md（直连反而慢 / 架构 / 看守脚本 / ACL 踩坑 / 两台转发变差 / 回滚 / 局限）
- 41-红队审计-攻击面.md（源站 IP 裸奔 + 泛域名 / CAA / DNSSEC / CF 端口白名单）
- 49-红队四审-20261017.md（L4 SNI 透传性能根因 / Caddyfile 无 encode / no-store 误用 / 证书两 watcher 不相交）
- scripts/ops/cf-ddns.sh、scripts/entry/（entry-failover.sh + README）、scripts/emby-relay/（emby-failover.sh + README + nginx recipe）
- scripts/dashboard/cert-check.py、scripts/selfheal/lib.cert-watch.sh、backups/dashboard/Caddyfile
