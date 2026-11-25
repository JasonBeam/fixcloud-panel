> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。

> 作者统一称「原作者」。示例一律用 example.com / 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24 / <EXAMPLE_TOKEN> 等文档示例值；机器以角色代称，不出现真实主机名/IP/域名/凭据/设备标识。【已验证】=实际读到/测到；【推测】=推断待核。

# 11 · 故障案例库

> 每案：现象 → 排查路径 → 根因 → 解决 → 预防。机器以角色代称；端口/域名/IP 用文档示例值或功能描述。【已验证】=实际读到/测到。

## ① 通用可复用经验（案例提炼）

### 案例 A · 频封 IP（主力出口 IPv4 TCP 全阻断）
- **现象**：主力出口机 IP 仅存活 30.5h 即遭 IPv4 TCP 全阻断，订阅/朋友 Emby 中转一起断。【已验证】
- **排查**：Globalping 中国 6 地（深圳/广州/北京/武汉/成都/西安，阿里/腾讯/联通）探测 → 6/6 无 TCP 回包 = **全国封锁非广东个案**；对照同机另一端口 6/6 通 = 端口级封锁；对照另一台 6/6 通排除本地。【已验证】
- **根因**：GFW 对明文/可探测协议入站做 IP 级或端口级 TCP 封锁；公网 SS-2022 无 fallback 是多余可探测面。【已验证】
- **解决**：付费换 IP（搬瓦工免死金牌）+ cf-ddns 立即更新；**全舰队抗封加固**：下线 7 个公网 SS-2022 + 2 个 IPRoyal SS 口；10/10 Trojan 入站加 HTTP decoy fallback（decoy 增 127.0.0.1/32 白名单豁免解决与 ip_is_private:reject 冲突）；Hy2 加 masquerade 伪装；6 节点 REALITY 换非 CDN SNI（冷门独立 SNI，ShortID 禁空）；订阅控制面迁出主力机经 tailnet 反代。换 IP 后 KiwiVM 重写 /etc/network/interfaces 塞回不存在 eth1→networking 红→再删（备份）；全舰队 fail2ban ignoreip 旧→新 IP；住宅落地 ufw 只放主力机旧 IP→改新（否则 AI 一级落地断）。【已验证】
- **预防**：高危节点换 IP 必做清单（新独立子域 + 轮换全套入站端口 + 重签 LE 证书 + 静置观察再切回流量，不复用旧域旧端口）；REALITY 是最强防御层（主动探测伪装真站）；代理高位随机口降扫描；监控只探 tailnet 不探公网代理端口。【已验证】

### 案例 B · 丢包 + 探针单采样放大成翻转风暴（自愈造成最严重自我伤害）
- **现象**：住宅落地「今天一直出问题」，主力机一天被重启 66 次，掐断全体用户连接（不只是 AI）。【已验证】
- **排查**：①落地本机 load 0.17/7 连接/0Mbps/网卡 errors+dropped 全 0/sing-box active 无重启→不是负载进程网卡；②落地出网 curl gstatic204 30/30 成功/openai401 t=0.25s/ip.sb=本机 IP→落地自己能用不是 DNS 黑洞；③落地→1.1.1.1 ping 16.7% 丢，mtr -c30 逐跳：hop1 网关 3.3% hop2 0% hop3 40% hop4 50% hop5 60% 终点 33%→丢包起于上游第 3 跳（ECMP 双下一跳疑似一条腿坏）；④网关 ping 50/50 0% 丢→落地↔网关干净问题在网关之外；⑤三方视角 主力出口机/备份出口机/算力中枢→落地 22-30% 双向与源无关=落地侧上游；⑥同供应商对照另一台 0% 丢→不是全网只是这台/这条上游；⑦**关键一步把探针失败和落地真挂分开**：直接复刻探针命令跑 45 次失败 5 次（11%）全 rc=28 超时，每次失败后立刻重试 4/5 拿到 401→落地没挂，是单次采样在丢包链路上必然出现的假阴性。【已验证】
- **根因**：两层叠加。外因落地上游丢包（机房侧无可修）；内因自己的探针把它放大——_flip_ai 每翻一次就 systemctl restart sing-box，p(单次失败)≈11-40%→p(连续 2 次)≈1-16%，每 2min 一轮→一天几十次翻转，66 次翻转=66 次 restart（journalctl 当日 132 条 Started/Stopping 佐证）。0903 刚把探针从只探 TCP 升级 e2e（修假阳性「端口活着但解析死」），这次是同一探针另一面假阴性：e2e 链路长，任何一环丢包都会超时，**探针越长越不能只采一次**。【已验证】
- **解决**：①多采样多数决 AI_PROBE_TRIES=3/NEED=2（带早退，健康态仍只跑 2 次 curl 近零开销）②非对称迟滞 DOWN_STREAK=2/UP_STREAK=3（快降级慢恢复）③抖动锁 1h 翻转 ≥6 次锁 direct 不再自动切回（降级方向永远放行）④日志/TG 带采样比 ok=2/3。**零重启**（0917）：selector 出站 + clash_api PUT 进程内换指针，不重启不掐连接。【已验证】
- **预防**：噪音被压住反而掩盖真实损害（此前只有播报限流 AI_FLIP_NOTIFY_MAX=4，TG 看着几条但重启一直在发生）——要限的是**动作本身**不是播报；开票机房附上游第 3 跳丢包 mtr + 网关 0% + 同商对照排除本机；丢包期公开直连口同样劣化，客户端该组手动避开。【已验证】

### 案例 C · DNS / 双栈黑洞（端口全活探针全绿但流量黑洞）
- **现象**：两起事故——①住宅落地端口活着但解析全死，AI 断了 ~2h 没人回退（TCP 探针持续绿零告警）；②备份出口机硬重启后所有非 ts.net 域名 SERVFAIL，经它直连流量全黑洞，但所有端口全活 TCP 探针全绿舰队互监零告警。【已验证】
- **排查**：①resolvectl query 一律 Lookup failed due to system error: Invalid argument，而 dig @1.1.1.1 UDP/TCP 全正常 ping/TCP443 全通→systemd-resolved 把上游特性等级一路降到 TCP 之后卡死（开机瞬间上游 DNS 丢包让 resolved 学到降级后不再回升）；②tailscaled 接管的 /etc/resolv.conf（foreign 模式）只剩它自己 100.100.100.100，tailscaled 日志刷 dns: resolver: forward: no upstream resolvers set, returning SERVFAIL；③sing-box access.log 上千条 lookup SERVFAIL。【已验证】
- **根因**：①触发层机房网络事故 + 硬重置，开机瞬间上游 DNS 丢包让 resolved 卡死（systemd 255.4 Ubuntu，Debian 12 systemd 252 未见此症）；②设计层探针只探 TCP 证明能握手不是能当出口，DNS/出网任何一环死探针都不红，回退永远不触发，违反 fail-open 初衷；③tailscale 接管 DNS + sing-box 用系统解析（dns.servers:local）= 任一硬重启即复现黑洞。【已验证】
- **解决**：①resolvectl reset-server-features 一条命令解卡（无需重启 resolved）；②探针改 e2e（经 ai-probe 入站真拉源站）；③舰队根除 tailscale 接管 DNS（tailscale set --accept-dns=false，VPS 没有任何东西用 ts.net 名字已 grep 确认）；④六台 sing-box 全改自带 DNS（dns.servers=[udp 1.1.1.1] + default_domain_resolver prefer_ipv4），客户端流量解析不再经主机 resolver；⑤selfheal 新原语 repair_dns + 八台全加 dns-egress 检查（探 gstatic204 走系统 resolver + 出网，修复顺序：tailscale 若仍管 DNS→accept-dns=false；resolv.conf 含 100.100.100.100→还原 stub；resolved 在跑→repair_resolved；仍不通→静态兜底）。实证：把 resolv.conf 改成只剩 100.100.100.100 复现→跑一轮 selfheal UNHEALTHY→repairing→stub→3s 后 recovered silently 零 TG。【已验证】
- **预防**：探针 e2e 而非只探端口；sing-box 自带 DNS 去主机依赖；repair_dns 入口先 getent 护栏（两域名能解析=抖动不动 resolver）；残余盲区：主机 DNS 全坏时 tg-notify 也解析不了→先修再报 + 缓存 IP/--resolve/spool 补发。【已验证】
- **双栈子案**：家宽发布 AAAA 但入站 v6 不通→nginx 在 v4/v6 间轮询，北美分区入口 约一半请求挂死。修：中转只走家宽 IPv4（/etc/hosts 别名 家宽 IPv4 别名，DDNS 变化脚本跟进）。【已验证】

### 案例 D · 证书过期 + ACME 账户坏 + CT 日志误判 + 删证书回落自签
- **现象**：家宽泛域名证书 08-06 过期，10 个服务浏览器集体报错，靠用户自己点网页才发现已过期 3 天，全舰队没有任何东西在盯。【已验证】
- **排查**：①最初只看 CT 日志日期以为 06-09/07-02 有新证书误判「续到了没装上」；②加 issuer_name 真相：07-02/06-09/05-04 都是 Google Trust Services WE1/Sectigo DV E36 = **Cloudflare Universal SSL 边缘证书**（CF 给托管 zone 自动签，与 Lucky 无关，Lucky 里根本不存在也用不上，非标端口橙云救不了）；只 05-08 那张 Let's Encrypt R13 才是 Lucky 的也是它唯一一张；③用户手点续期才暴露真失败：acme error 400 malformed / No Key ID in JWS header = ACME 账户注册状态坏/丢，不是 DNS-01 问题不是 CF 凭据问题（DDNS 同套凭据一直好）；④路由器上 curl ipify 得到的 IP 是假的（OpenClash 出站被劫走）→判断家里公网 IP 要看 ip addr show pppoe-wan。【已验证】
- **根因**：Lucky 的 ACME 账户坏了自 05-08 后一次没续成；Lucky 把错误写进自己日志中心 stdout 看不到；无任何证书监控。【已验证】
- **解决**：①新建一张证书即注册全新 ACME 账户绕开坏的（域名主 + 泛都勾，DNS 服务商 CF，证书来源选 LE 不选 ZeroSSL，联系邮箱务必填，Token 必须区域 scoped 单 zone）；②DNS-01 传播检查查不动（Lucky 把 DoH 发到 53 端口本身错 + OpenClash 劫持所有出站 53）→打开「忽略传播检查错误」+「禁用权威 NS 传播检查」（直接交 LE 自己验证）；③用户后台删证书条目回落自签更糟（证书连同 ACME 任务和 CF 凭据一起没，回落内置自签 CN=Lucky 有效期 2028，服务照常 302 但浏览器从过期变不受信任一样红且没法再自动续）→从备份还原（**必须先 docker stop 再覆盖文件**，Lucky 配置缓存内存活着时写文件会被刷回去）。结果 notAfter 推进 issuer LE，10 域名全换上信任链 OK。【已验证】
- **预防**：证书哨兵**必须同时验信任链**（Verify return code != 0 即 trusted=no 与已过期同等严重，自签 notAfter 2028 看着剩 900 天绿浏览器照样红）；档位降噪只在变差播报；一张泛域名证书覆盖 10 服务只探 1 个就够，但两个 watcher 目标集要互补且别让唯一 watcher 跑在被保护那台；续期新条目带两开关约 60 天后自动续走同一路，真失败哨兵剩 14 天报警不再拖到过期。【已验证】

### 案例 E · 自愈误动作（四类）
- **E1 翻转风暴**：见案例 B（单采样 e2e + 2 次即翻→一天 66 次 restart 打主出口）。【已验证】
- **E2 docker 慢被当死重启 daemon 放大全站 outage**：现象 status 断两次（~4min 有播 / ~3.5min 无播用户手动发现），入口 nginx 对后端 443 全 refused。排查：①后端渐慢 selfheal 单轮 8s→138s load→7.6；②Docker 本身慢空闲机 dockerd 78%+containerd 71% CPU，kworker D 态卡 css_release_work_fn/synchronize_rcu_expedite，PSI cpu some≈57%—cgroup 高频创建销毁内核回收拥堵，churn 源 6 定时器每分钟 :00 齐射 + selfheal 每 2min 对 8 容器 inspect/exec + homepage healthcheck 每 10s wget exec；③旧 docker 检查 timeout 20 docker ps 单次超时 critical=1→首轮即 restart docker 8 容器全灭 daemon 高负载 3 分多才起；④告警空洞恢复快于第 2 次失败→recovered silently 外部哨兵要 5 次（~10min）两层都漏 3.5min 事故；⑤余震容器 10s 没退被强杀→containerd task 泄漏（task already exists）重启循环 Exited(128) 不自愈。解决：docker 慢≠死（unit 真死立即修；active 但探测超时=慢连续 2 轮 ~4min 才判失败单轮只记日志）；daemon 重启必播报 TG；定时器错峰 AccuracySec=1s；homepage healthcheck 10s→30s；classnet 重建 rm -f 清泄漏 task。验证 load 13.8→2.95 selfheal 7-16s/轮 e2e 延迟 2-3s→<1s。预防：内核 -149 回归未证若复发 grub 回退 -147 对照。【已验证】
- **E3 ntfy-subs 瞬时采样 flap**：现象检查反复异常→修复→恢复→又异常（1h 修 5 次被暂停）。根因：数 ntfy 容器 :80 的 ESTABLISHED 连接要求瞬时 ≥1，但手机 NAT/省电重连连接 0↔1 秒级抖动，瞬时采样必然 flap。解决：改 15min（后 21600s）宽限窗，「最近 N 分钟见过」才算活。预防：瞬时采样探活对移动网络客户端天然不稳。【已验证】
- **E4 定时器 OnUnitActiveSec 卡 elapsed**：现象 8 台 21 个定时器全卡 3 天（门户/DDNS/朋友下发全停），最该响那次只一条含糊 telemetry 异常。根因：20-freq.conf 只写 OnUnitActiveSec，daemon-reload 后卡 elapsed 不再触发。解决：改墙钟 OnCalendar。预防：周期定时器一律 OnCalendar；补 watchers 检查 + 定时器自愈（卡 elapsed→restart）。【已验证】
- **E5 launchd AbandonProcessGroup 杀后台长任务**：现象 Mac Immich 挂 10.5h selfheal 重试十几轮没生效。根因：launchd 默认主进程退出 SIGKILL 整个进程组，immich_repair & 后台 colima start ~50s 主脚本几秒退出→每轮 colima start ~3s 被杀（铁证日志每轮只 colima stop 完整输出紧接 run end，colima start 零输出）。解决：plist 加 AbandonProcessGroup true。预防：凡定时任务 + & 后台长任务都查这条；验证必须由 launchd 自己拉起（kickstart 观察 run end 后子进程活着）。【已验证】

### 案例 F · 客户端泄漏（Auto 墙外全直连 / DNS 同发 / IPv6 绕过）
- **现象**：只读审计发现 Auto 墙外=全直连真实 IP 暴露（trace 出口 AS 校园网）；DNS 缓存 153 条 109 条由中国解析器答复含敏感域名；conntrack 7 台 LAN 主机 60 条 v6 直连。【已验证】
- **排查**：①未列名域名→网络位置 DIRECT，所有节点判死闸门回退第一成员=直连 fail-open；②All queried concurrently 4 家都收到每条 + ECS 带真实网段 /24；触发未列名域名 Rule evaluating requires DNS lookup for RULE-SET LAN（LAN/Domestic IPs/GEOIP CN 都没 no-resolve）；③路由 ipv6_enable=0 但 LAN 仍发 RA/DHCPv6、fw4 TUN 全 nfproto ipv4 无 v6 劫持；客户端 ipv6=false 不等于拦 v6。【已验证】
- **根因**：fail-open 闸门 + DNS 并发无 no-resolve + IPv6 三层绕过 + allow-lan 开放。【已验证】
- **解决**：AI Suite 强制走代理删 DIRECT；nameserver 走代理 DoH + nameserver-policy geosite:cn,private 才问中国 DNS + 尾部 IP 规则全 no-resolve；路由 LAN 侧 RA/DHCPv6 disabled；allow-lan:false/bind 127.0.0.1。【已验证（过语法行为未实测）】
- **预防**：客户端配置生成器要审计泄漏面；墙内冷启动闸门探测 DNS 循环依赖必须实测；Mac 本地 [General] 不随订阅更新；真机/WebRTC/v6 网络未覆盖。【已验证】

### 案例 G · Emby 单域名（一域名切 4 入口）
- **现象**：朋友要记 4 个分区域名，某入口被墙/劣化要手动换。【已验证】
- **排查/根因**：4 入口后面同一台 Emby（同 ServerId 同 token）换入口对客户端透明；但端口不一（443/8443）DNS 只能换 IP 不能换端口；relay 活但回家腿死照样挂（NA/AS 就是）。【已验证】
- **解决**：统一端口（全部加 listen 统一端口 ssl + ufw 放行 + 证书 SAN）；DNS 故障切换单 A 记录灰云 TTL60，优先级 hub>eu>na>as；切换器端到端健康判定（经 relay 回家拿 /System/Info/Public Version，3 次 1 成功）+ 防抖（当前 2 轮坏切 / 高优先级 5 轮好抢回 / 全挂不动只告警一次）；家里路由兜底撤离（切换器整机挂时只撤离不抢回）。为什么不用 8443（被 DERP 占）不用 443（后端被 docker-user-fw 封）。【已验证】
- **预防**：DNS 切换不迁移正在播的流（客户端断一下重连，电视盒子无视 TTL 缓存几分钟，现实 1-5min）；分区域名保留当手动备选；零基建路用支持多线路择优的第三方客户端。【已验证】

### 案例 H · Tailscale 转发优先（直连反而慢 + ACL 全断）
- **现象**：远端 WiFi 到家打洞直连 ~200ms，经近港转发 ~45ms；第一次只加 relay grants 全 tailnet TCP 断最长 ~28min。【已验证】
- **排查**：traceroute 家→远端直连第 6 跳起从 3-4ms 跳到 200ms（电信 163→PCCW）；家→近港转发精品线 ~11ms；tailscale ping 直连 190-213ms 转发 44-48ms。ACL 断：tailscale ping 还通（disco 不过滤）但 TCP 全断。【已验证】
- **根因**：①打洞只负责让两边能对发 UDP，路线由运营商决定，直连走普通线反而慢；②tailnet policy 原本没写访问规则靠默认全放行，加任何一条 grants 就从默认放行变默认拒绝。【已验证】
- **解决**：①转发机设 relay-server-port + ufw allow udp；家里 nft 挡发往远端公网 IP 的 UDP 逼走转发；看守脚本每分钟检查转发坏了撤规则恢复直连（连续 5 轮只有 DERP/超时→撤规则冷却 30min）；②补全放行 grants（src[*] dst[*] ip[*]）+ relay 授权。【已验证】
- **预防**：**动 policy 前先读现有内容**；两台转发同时开反而变差（Tailscale 没有固定选延迟低的那台，路径频繁切换）只留一台；看守脚本是退路不是 Tailscale 自带；只测一晚多日稳定性没数据；远端公网 IP 写死变了规则失效退回直连不会断。【已验证】

### 案例 I · 代理→内网洞三次假已修（loopback / tailnet / 域名绕过）
- **现象**：任意订阅用户（含朋友版）经公开代理入站可达服务器 loopback / NAS / IP-KVM / 门户 / 全部 SSH。【已验证】
- **排查/根因**：①45 说 ai-probe 不可达错漏「经自己入站到 loopback」（route.final 空→direct 自己连自己）；②0917 加 ip_is_private reject 错不含 CGNAT 100.64/10（tailscale 正用这段）；③1008 域名绕过（reject 只在 IP 字面量生效，CONNECT 解析到私网的域名时路由阶段还没解析→不命中→direct 自己解析拨号）。【已验证】
- **解决**：规则序 [action:resolve(prefer_ipv4), ip_is_private reject, ip_cidr[100.64.0.0/10, fd7a:115c:a1e0::/48] reject]；同规则多字段是 AND 要 OR 拆两条；七台全应用。【已验证】
- **预防**：**复验字面 IP 和域名都要 502**；一次性验证要编码成常驻外部红队探针（连续三次假已修后应有站得住的探针）；assert_invariants 每轮断言三规则形状对；回退表别混迁移前旧备份（恢复成没 reject 的旧配置=洞重开）。【已验证】

### 案例 J · 配额用尽关机 41h（集中度事故）
- **现象**：主力出口机 2TB 月配额用尽，搬瓦工直接关机 ~41h（干净 ACPI 关机→开机），窗口内自己和所有朋友订阅分发/凭据管理/NA Emby 一起没。【已验证】
- **排查/根因**：日均 ~70GB 峰值 175GB，朋友占 342.8GB；主力机集中承载主出口 + 订阅服务器 + friendsd + 按人记账 + Emby 中转 + 安装包镜像 + 住宅入站 + 4 级 AI selector。【已验证】
- **解决**：每小时配额预测器 + 速率外推提前 6 天告警（做得对）；订阅控制面迁出主力机。【已验证】
- **预防**：「提前 6 天要做什么」写成 runbook 预先决定；需求侧杠杆（朋友版主选默认分流一部分到备份机/入口机，让主力机配额主要留给自己）；集中度按「一台挂了同时带走什么」排序治理。【已验证】

### 案例 K · 备份层双向死锁
- **现象**：配置备份包冻结 43 天（9 个 .tgz mtime 全停在 09-04 仍被 git 跟踪），横跨 tailnet reject / 域名绕过加固；实测包内 sing-box conf 只有 ai-probe 零 harden/resi 规则→按备份重建节点会静默重开两个已修好的洞。【已验证】
- **排查/根因**：重新打包把 /etc/sing-box 明文机密（clash_api.secret/SS 密码）写进 git 历史，而 tgz 不透明事后难清；NAS 备份 ~90% 未落地（~720G 活跃数据无第二拷贝无快照无异地）；其余单份（数据卷在同机、另一份在本地非异地、当前笔记本完全无备份）。【已验证】
- **解决**：age 公钥加密（私钥本机 + iCloud 不入库，明文 .tgz 删 + .gitignore）；打包排除机密通配符（config.json.*/zz-resi.json.*）；配置由安装脚本幂等重建。【已验证】
- **预防**：**「三个安装脚本能否幂等重建全部配置」尚未验证=先决条件**；git 历史不可逆现在处理比以后便宜；群晖快照是唯一防勒索层且唯一不需新硬件应先做（镜像几分钟内忠实传播删除与勒索，快照是镜像方案生命线）。【已验证】

### 案例 L · conntrack 重启回落默认
- **现象**：apply-baseline 写 90-homelab-conntrack.conf=65536，定时重启后回落 8192/4096。【已验证】
- **排查/根因**：部分机没有 /etc/modules-load.d/nf_conntrack.conf，开机 systemd-sysctl 跑在 nf_conntrack 模块加载前、该键不存在被跳过，之后 ufw/sing-box 拉起模块用内核按内存默认值。【已验证】
- **解决**：apply-baseline 先写 modules-load.d 再设 sysctl；四台全补，在线 65536。【已验证】
- **预防**：重启后 cat /proc/sys/net/netfilter/nf_conntrack_max 复验；svcstatus 新增 conntrack_pct + conntrack_max（<32768=漂移）告警。【已验证】

### 案例 M · Emby 媒体服务器系列（依赖：Emby + Mac mini + launchd）
- **M1 库重置 0705**：盘满→SQLite 损坏→整库丢失。预防：Mac 磁盘分级护栏 EMERG<15GB 优雅停 Emby（SIGTERM 让 SQLite flush）+ 紧急期不重启。【已验证】
- **M2 DELETE /Library/VirtualFolders 在 4.9.5 崩 NRE**：API 缺陷，别用该端点删库。【已验证】
- **M3 最近添加看不到新剧 DateCreated 全库 0001-01-01**：10-23 复发 launchd TCC 拦目录列举。预防：launchd 任务给完全磁盘访问权限。【已验证】
- **M4 DB 备份静默死 28 天 0809**：备份任务失败无告警。预防：备份新鲜度推送门户 >30 天亮灯。【已验证】
- **M5 CPU 常年 99% 0908**：转码/扫库负载。【已验证】
- **M6 亚洲分区入口 静默宕 3 天 近港入口机 nginx 开机解析失败 1014**：nginx 开机 DNS 未就绪→host not found in upstream 启动失败 unit 无 Restart。解决：Restart drop-in + 脚本兜底拉起。预防：nginx 上游用域名要加 Restart + 开机 DNS 就绪依赖。【已验证】
- **M7 权限事故「没有兼容的流」0720**：用户权限/转码配置。【已验证】
- **M8 新剧没封面 MP 首刮豆瓣图 418**：图片代理 SSRF 误杀 fake-ip（见案例 N）。【已验证】

### 案例 N · MoviePilot 媒体自动化（依赖：MoviePilot + Clash fake-ip + Emby）
- **N1 封面不出 = v2.14 图片代理 SSRF 误杀 fake-ip**：fake-ip 段 + Tailscale CGNAT 段被 SSRF 防护当内网拦。解决：加白名单。【已验证】
- **N2 新内容不进 Emby 断链 0827**：MoviePilot→Emby 通知断。【已验证】
- **N3 反复下载库里只有 sample 0930**：下载/识别循环。【已验证】
- **预防**：自动更新安全版备份 + 健康检查 + 回滚；升级前 SQL 备份。【已验证】

## ② 原作者特定环境经验（标注依赖）
- 案例 A 依赖搬瓦工换 IP 免死金牌 + Globalping 中国多地探测；案例 B/C 依赖 LisaHost 西雅图住宅落地 + sing-box e2e 探针；案例 D 依赖 Lucky iStoreOS 容器 + OpenClash 劫持 53；案例 E2 依赖 Contabo docker 栈 + 内核 6.8.0-149；案例 E5 依赖 Mac mini colima/lima；案例 H 依赖 Tailscale Peer Relay（≥1.86）+ 近港精品转发机；案例 J 依赖搬瓦工 2TB 配额 + 主力机集中承载；案例 M/N 依赖 Emby 4.9 + MoviePilot v2.14 + Mac launchd。【已验证】
- 供应商集中度已反转：2 台 Evoxt + 2 台 LisaHost，LisaHost 同时承载不稳定西雅图机和最吃重 HK 机（网站入口#1/亚洲分区入口/DERP/仅两台外部哨兵之一）→一次 LisaHost 控制面或网络事件同时打到 AI 出口 + 主网站入口 + 一半外部监控。【已验证】

## ③ 需要重新验证的结论（给验证方法）
- **频封抗封加固有效性**：验证：换 IP + 新子域 + 轮换端口后 Globalping 中国 6 地 6/6 通 + 家里 OpenClash 清旧 IP 缓存后 5 协议全通；长期观察是否再封。【已验证方法，长期待观察】
- **丢包根因机房侧**：验证：mtr -r -c30 逐跳 + 网关 0% 丢 + 同商另一台 0% 丢佐证排除本机；开票后机房是否修上游第 3 跳。【已验证：工单未开】
- **零重启 selector 不掐连接**：验证：翻转多次 MainPID/ActiveEnterTimestamp 不变；AI_RULE_MODE 必须 cfgout==selector 才走 API（否则静默失效）。【已验证方法】
- **证书自动续期**：验证：新 ACME 账户 + 忽略传播检查约 60 天后 notAfter 推进 issuer 仍 LE。【已验证：首次手动成功，自动续待时间】
- **客户端泄漏修复真机**：验证：iPhone/安卓真机 + WebRTC/DNS 泄漏测试 + v6 网络（只读审计过语法行为未实测）。【已验证：真机未覆盖】
- **备份幂等重建**：验证：干净机跑安装脚本 + assert_invariants 对比解密包差异（先决条件未核）。【已验证：未核】
- **内核 -149 回归**：验证：docker 慢复发 grub 回退 -147 对照。【推测：相关性待证】

## ④ 来源文档路径清单
- 19-故障自愈-selfheal.md（案例 B/C/E1/E3/E4/E5/I）
- 50-舰队巡检与Emby单域名-20261030.md（案例 A/G/L + Globalping + 换 IP + 端口迁移）
- 14-Homelab门户-Tailscale.md（案例 D 证书根因）
- 53-Tailscale转发优先-PeerRelay-20261106.md（案例 H）
- 52-客户端泄漏审计-20261105.md（案例 F）
- 49-红队四审-20261017.md（案例 I/J/K + 拱心石集中度）
- 45-红队复审-20260904.md（案例 C DNS 黑洞 + 审计员误删）
- 44-全舰队体检-20260826.md、48-全面体检-20261015.md（案例 E4/L + Emby/MoviePilot）
- 32-Emby媒体服务器.md（案例 M 系列）、15-MoviePilot-媒体自动化.md（案例 N 系列）
- 25-VPS-IP与网络质量测试.md（案例 B 丢包测量）、26-2027续费精简规划.md（案例 J 配额）
- 10-配置备份.md（案例 K）、CHANGELOG.md（1119 频封溯源 / 1106 PeerRelay / 1023 溢出入口）
- reports/lisahost-packetloss-20260917.txt（案例 B 丢包证据）
