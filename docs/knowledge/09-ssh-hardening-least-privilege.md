> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。

> 作者统一称「原作者」。示例一律用 example.com / 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24 / <EXAMPLE_TOKEN> 等文档示例值；机器以角色代称，不出现真实主机名/IP/域名/凭据/设备标识。【已验证】=实际读到/测到；【推测】=推断待核。

# 09 · SSH / 安全加固 / 最小权限

## ① 通用可复用经验

### 1. 密钥管理
- **SSH 专用密钥 ed25519 + passphrase + 钥匙串**；~/.ssh/config 别名 + AddKeysToAgent。【已验证】
- **无口令私钥是重大风险**：私钥无口令且散在多台 root authorized_keys → 物理拿走一台机器即得全部 root。长远用 FIDO2 ed25519-sk（硬件绑定）。给私钥加口令（ssh-keygen -p）+ keychain；**但无人值守任务用的那把加口令会断任务，要先做整机加密/关自动登录再动那把**。【已验证】
- **authorized_keys 复核**：仅合法 fleet key 无后门；拆行去重（公钥粘在上一行末缺换行→该 key 失效），ssh-keygen -lf 校验指纹。【已验证】
- **退租清理**：清 ssh config + 私钥 + 从对端 authorized_keys 移除；**先 ssh-keygen -y 导出公钥逐字匹配才删**（别删错 key）。陈旧 authorized_keys.bak / sshd_config.d/*.bak 要删。【已验证】
- 各节点私钥/uuid/密码跨机全唯一（仅隧道 PSK 多处同=预期）；朋友凭据与自用全不同；SS2022 密钥长度全对。【已验证】

### 2. known_hosts 与主机密钥
- **host key 不匹配**：ssh-keygen -R 后**核对指纹再连**（别盲目接受）；换 IP 后 host key 变=可能已是别人的机器。物理 break-glass 通道（IP-KVM）host key 不匹配要本人核。【已验证】
- 变更主机密钥前先核对（全局工作约定）。【已验证】

### 3. 跳板与隧道
- ssh -J 跳板（拥塞机下载改 ssh -J 经主力机）；后台管理改 **SSH 本地转发不放开公网**。【已验证】
- **Lucky 后台 tailnet 源 IP 判外网 403**：Lucky 把 tailnet 源 IP（CGNAT 100.64/10）判成外网，后台只有「允许外网访问」粗粒度开关一开等于对整个互联网开放。解法：SSH 本地转发，请求经路由器自己发给 Lucky 源 IP=内网→直接放行，不改 Lucky 任何配置不放开任何公网面，SSH 本身走 tailnet 已加密鉴权。【已验证】
- **socat L4 透传加不了 X-Forwarded-For** → 后端看到来源全是转发机同一 IP → **按 IP 硬锁定有害**（任何人狂试密码把你自己一起锁门外=送对方 DoS 开关）。改「失败越多响应越慢但永不拒绝」（递增延迟 1/2/4/8s 封顶 10s，15min 窗口，持锁串行否则并发各睡各的延迟形同虚设），统一回 401 非 429 免攻击者摸清阈值。真要按 IP 限速须转发改 PROXY protocol + 后端开 proxy_protocol 监听。【已验证】
- 远程 pkill -f 注意模式匹配到 SSH 远端命令行自身（曾以 255 自杀退出）。【已验证】

### 4. 凭据存储与加密 age
- **age 公钥加密备份**：私钥只存本机 ~/.config/homelab/age.key（0600）+ iCloud，绝不进 Git；收件公钥 .age-recipients；.gitignore 阻止明文 .tgz/.env/*.age.key 再提交。**git 历史不可逆，现在处理比以后便宜**。【已验证】
- **恢复禁盲解覆盖运行环境**：按规范用安装脚本幂等重装跑通 assert_invariants，再从解密包提取不可再生凭据/规则/单元（盲解会静默重开已修好的洞）。【已验证】
- **token 路径明文写 nginx access.log**（自用订阅 token 在 URL 路径，985 行 0640 留 14 天）→ 7 个 token location 加 access_log off。【已验证】
- env 600 不入库（tg-notify.env/cf-ddns.env/selfheal.env/pollers.env）；脚本源入库无 token；**全脚本移除硬编码密钥改读各机 .env，仓库仅留 .env.example**。【已验证】
- **authsvc 加固**：①改密码踢掉所有旧会话（会话签名密钥从密码哈希派生→密码一改已签发 cookie 全失效；此前固定 secret 签 exp 改密码不影响旧 cookie 最长 30 天）②密码哈希无盐 SHA-256→scrypt 加盐（~79ms/次，旧格式自动兼容下次登录就地升级）③登录失败递增延迟。**移除 changeme 默认签名回退改 fail-closed**（未配置即拒绝，绝不默认口令）。【已验证】
- docker inspect 明文可见 AUTH_PWHASH/AUTH_SECRET → 外置 .env，删 compose 内联（早失效的 AUTH_PWHASH 也删）。【已验证】
- 轮换 CF token：删旧建新 → 服务器 read -rsp 写入 env chmod 600 unset。【已验证】
- sing-box config.json + conf/*.json（含 REALITY 私钥）+ /root/*.bak* 全 644→600（root 跑无影响）；selfheal.env 0644→0600。【已验证】

### 5. 红队攻击面收敛（方法：全程从外部 VPS 视角扫描，不是内网自检）
- **源站 IP 裸奔 + 泛域名**是「被 30 多万解析」的结构性前提（每条记录直接返回家宽 IP，*.泛解析任意子域都返回家 IP）。根治：换 CF 可代理端口 + 橙云隐藏家 IP + WAN 关直连。【已验证】
- **🔴 loopback 洞**：代理用户可 CONNECT 127.0.0.1:port，route.final 空→落 direct→服务器自己连自己 loopback。任何订阅用户（含朋友版）可借道 ai-probe 白嫖住宅出口/读内部状态。**对代理机判断 loopback 安全，外部扫描不够，要多问「用户能不能把它当目的地」**。修：route.rules 最前插 ip_is_private:reject。【已验证】
- **🔴 tailnet 洞**：ip_is_private = RFC1918 + loopback + link-local，**不含 CGNAT 100.64.0.0/10（RFC6598，tailscale 正用这段）**。任意订阅用户可达 NAS/IP-KVM/门户/全部 SSH。修：同规则多字段是 AND 要 OR 拆两条（ip_is_private reject + ip_cidr[100.64.0.0/10, fd7a:115c:a1e0::/48] reject）。【已验证】
- **🔴 域名绕过**：reject 只在目的地 IP 字面量生效；CONNECT 解析到私网的域名时路由阶段还没解析→不命中→final 空→direct 自己解析拨号→回环/tailnet 照样可达。修：规则序 [action:resolve(strategy prefer_ipv4), ip_is_private reject, cgnat reject]。**复验字面 IP 和域名都要 502**。【已验证】
- **不变量无常驻测试**：代理→内网洞被找到三次，每次推翻上次「已修」。一次性验证要编码成**常驻外部探针**（连续三次假已修后应有站得住的红队探针）。【已验证】
- **SS 对全网开放是多余攻击面**：DNAT 无来源限制全网可连，密码一旦泄露立刻变开放代理别人拿你家 IP 中转；回家/翻墙有 Tailscale + 舰队，不用→删转发停容器，还要用→限来源 IP 段或改走 Tailscale。【已验证】
- **登录页公网无防爆破**：所有服务登录页对公网开放（有认证墙没有未授权直进=好），但路由器/反代没有 fail2ban/速率限制/WAF→可慢速撞库无人拦。修：反代开 WAF + 速率限制；高价值后台加 IP 白名单或 Basic Auth 前置；长期这些后台不该走公网该走 Tailscale。qB 关 HostHeaderValidation=false 略增 DNS-rebinding 面。【已验证】
- **账号层最省力收益最大**（不改任何架构）：CF 账号 2FA（域名命根子必须开）；注册商 Transfer Lock（防域名被转走）；CF API Token 收敛（截图露过 token 开头建议撤销重建，最小权限 scope 到单 zone 别用 Global Key）；注册商邮箱也开 2FA（邮箱丢了域名全丢）。【已验证】
- 明确跳过的「安全剧场」：换 SSH 端口（只降噪不增安全）、SSH 2FA（徒增自锁风险）、关 ICMP ping（挡不住攻击还碍自己 ping/mtr 排查）。【已验证】
- 主机加固：内核元包要装（否则冻结）；U-U Allowed-Origins 含 -updates；X11Forwarding yes 无用途→关；dropbear 密码登录默认开→关；WAN IPsec ESP/ISAKMP 默认规则无服务→禁用；监控面绑 0.0.0.0 仅 ufw 单层（改绑 tailscale 有开机竞态，不算欠账但残余风险网卡改名）。【已验证】
- **审计员误删教训**：无监听就删 ufw 放行前要先看服务是否本该在跑（unit enabled 但 failed=该修不该删）；关 MagicDNS 前先 grep http://短名。【已验证】

### 6. 客户端泄漏审计（只读没改线上，方法：trace 出口 + DNS 缓存 + conntrack）
- **P0 Auto 墙外=全直连真实 IP 暴露**：未列名域名→网络位置 DIRECT；所有节点判死闸门回退第一成员=直连 fail-open。AI Suite 必须强制走代理（删 DIRECT，全挂也不直连）；部分 AI 域名不在列表→FINAL DIRECT→头部加 DOMAIN-SUFFIX；Clash 无 sniffer App 自带 DoH 用 IP 连接域名规则不命中→加 sniffer。【已验证】
- **P0 DNS 同发阿里 + 腾讯**：All queried concurrently 不管谁赢 4 家都收到每条；ECS 带真实网段 /24 转给权威。触发：未列名域名 Rule evaluating requires DNS lookup for RULE-SET LAN；LAN/Domestic IPs/GEOIP CN 都没 no-resolve。Clash nameserver 混明文中国解析器 + proxy-server-nameserver 明文优先→节点域名明文可见；没 respect-rules/follow-rule。修：nameserver 无中国解析器走代理 DoH，nameserver-policy geosite:cn,private 才问中国 DNS，proxy-server-nameserver 只解析节点域名，尾部 IP 规则全 no-resolve。【已验证】
- **P0 IPv6 三层绕过**：①路由 ipv6_enable=0 但 LAN 仍发 RA/DHCPv6、fw4 TUN 转发全 nfproto ipv4 无 v6 劫持→LAN 设备公网 v6 直接出 pppoe 不进代理（conntrack 7 台 LAN 主机 60 条 v6 直连）②Stash Tunnel only IPv4 by default 双栈 v4/v6 同时握手取先成者③Surge ipv6=false 但 ipv6-vif 默认 disabled，官方「不开也 can still access IPv6 by addresses directly」→ipv6=false 不等于拦 v6 只是不查 AAAA。修：路由 LAN 侧 RA/DHCPv6 disabled（WAN v6 不动）。【已验证】
- **P1 allow-lan 开放**：基础 yaml allow-lan:true + bind:* + DNS 0.0.0.0:1053 无 authentication，同网段（校园/酒店 WiFi）任何人可用代理包括回家内网进家里 LAN。修：allow-lan:false（路由单独变体才 true）/bind 127.0.0.1/listen 127.0.0.1。【已验证】
- **DoH 跟随规则循环依赖**：follow-outbound-mode=true 让 DoH 按规则匹配上游列表，没 1.1.1.1/8.8.8.8 落 FINAL→节点；节点主机名是域名回退 DIRECT 告警。墙内冷启动闸门探测需 DNS 而 DoH 又走闸门=循环依赖，必须实测。用户决定关该选项不钉 IP（钉 IP 让 DDNS 换 IP 不透明）。【已验证】
- **墙内节点解析**：15 境外 DoH IP 直连 0/4 全超时；dns.alidns.com/doh.pub 通（都不在中国，不违背「外网不问国内 DNS」，代价每条外网查询这两家也收到）。⚠️第一轮只绑 pppoe-wan 没换用户 12 境外 DoH 全超时不算数——OpenClash 把路由自身 TCP 重定向，只放行 gid65534，用 Apple/微软节点 IP 对照才发现。【已验证】
- **Mac 本地 [General] 不随订阅更新**：Auto.conf 本地文件只 include [Proxy][Proxy Group][Rule]，[General][Host] 不随订阅更新；编辑触发自动重载必须先让 include 缓存更新（曾改远程还改本地→节点域名靠 DoH DoH 又靠节点→代理超时全量重启网络扩展断开）。【已验证】
- conntrack 地址补零坑：一行两方向元组，用 src=240e:3b5 查 0 条假阴性，按首元组解析才得 60。【已验证】

## ② 原作者特定环境经验（标注依赖）
- **Mac mini FileVault 关 + 自动登录开 + 无口令 id_ed25519 在 6 台 VPS root authorized_keys + ARD 全开 + macOS 15.6 已 13 月未更新**（依赖：物理机）：物理拿走即得 6 台 root。需本人办（FileVault/关自动登录/系统更新/两把 SSH key 加口令）。【已验证】
- **MacBook 主力登录密钥（8 台 + 路由 + Mac 唯一登录 key）无口令常驻 agent**（依赖：主力笔记本）：ssh-keygen -p + keychain，长远 FIDO2 ed25519-sk。【已验证】
- **TG bot token 全舰队同一枚**（依赖：单告警通道）：任一沦陷即得→接受（root 沦陷等价），文件 600 日志无泄漏。【已验证】
- **REALITY short_id 空字符串仍被接受 4 台**（依赖：sing-box 版本）：1018 摘空 id，事前核实订阅全带 sid。【已验证】
- **朋友版凭据隔离**：朋友 Hy2 跳端口独立段；朋友版 hy2_selfsigned=False（改指 letsencrypt live）；IPRoyal 凭据进订阅朋友版须排除（用服务端专用入站钉死出站）。【已验证】

## ③ 需要重新验证的结论（给验证方法）
- **厂商 drop-in 真关**：验证：sshd -T | grep -iE 'passwordauthentication|permitrootlogin' 看实际生效值（主 config 可能被字典序压过）。【已验证方法】
- **loopback/tailnet/域名三种绕过**：验证：经公开代理入站 CONNECT 127.0.0.1:port / tailnet IP:port / 解析到私网的域名，**字面 IP 和域名都要 502**；常驻外部红队探针而非一次性验证。【已验证：三次假已修，需常驻探针】
- **客户端泄漏真机**：验证：iPhone/安卓真机 + WebRTC/DNS 泄漏测试 + v6 网络客户端行为（只读审计未覆盖真机）；rule explain 未列名不再 DNS lookup；dump dns 外网无中国解析器；conntrack LAN→internet v6=0。【已验证：真机未覆盖】
- **私钥加口令断无人值守**：验证：先做 FileVault/关自动登录，再给无人值守那把加口令，观察 launchd 任务是否断（keychain 能否解锁）。【推测：顺序依赖】
- **墙内 DoH 多运营商**：验证：只测电信一个点一时段，移动/联通/蜂窝没测；两家以后也可能被封，真不依赖 DoH 得给节点加 IP 直连兜底。【已验证：单点单时段】
- **递增延迟并发绕过**：验证：离线 test_authsvc.py 21 项（scrypt 往返/旧格式兼容/改密码失效旧 cookie/递增延迟/并发绕过/极端值溢出 2**n 钳位）；持锁串行否则并发各睡各的延迟形同虚设。【已验证方法】

## ④ 来源文档路径清单
- 09-安全加固.md（SSH key-only / 厂商 drop-in / 安全剧场跳过 / 凭据 env 600）
- 41-红队审计-攻击面.md（外部视角方法 / 源站裸奔 / SS 多余面 / 登录页防爆破 / CAA/DNSSEC / 账号 2FA）
- 45-红队复审-20260904.md（主机加固 / 代理密钥 / access_log off / 自签 MITM / DNS 明文 / 监控自愈恢复）
- 49-红队四审-20261017.md（三方法论陷阱 / P1 六条 / 拱心石 / ip_is_private 无常驻测试 / 家宽 Lucky 无保护）
- 52-客户端泄漏审计-20261105.md（P0 三项 / P1 / 修复 / 关 DoH 跟随 / 墙内节点解析）
- 19-故障自愈-selfheal.md（loopback 洞 / tailnet 洞 / 域名绕过 / assert_invariants）
- 14-Homelab门户-Tailscale.md（authsvc 加固 / 为什么不按 IP 锁定 / SSH 隧道后台）
- 10-配置备份.md（age 加密 / token 轮换 / 恢复禁盲解）
- 24-舰队网络与系统审计.md（fail2ban 累进 ignoreip / authorized_keys 复核）
- scripts/selfheal/singbox-harden-routes.sh、scripts/ops/lucky-admin-tunnel.sh、backups/dashboard/authsvc/app.py
