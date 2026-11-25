> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

# Token 鉴权与用户管理（生成 / 轮换 / 吊销 / 配额 / 多用户隔离 / 最小权限）

> 来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。
> 【已验证】= 本次审计实际读到；【推测】= 提炼者推断。token/凭据/IP/域名/朋友姓名一律不出现，用 <token>/<EXAMPLE_PASSWORD>/fr-<id>/example.com 等示例；主机用角色名（主力/备份/东京/住宅落地/后端机）。

## ① 通用可复用经验（可直接迁移）

### 1. 按人签发 vs 共用 token（核心决策）
- 【已验证】旧方案所有人共用一个 token + 一组节点凭据：踢一个人 = 换 token + 轮换全部凭据 = 全员重加。新方案**每人一条链接 + 一组独立凭据**，撤销/到期只影响他自己。
- 生成：朋友 token = secrets.token_hex(16)（32 位 hex）；内部 id = token_hex(4)；user_tag = fr-<id>；每站点凭据 gen_creds() 用 uuid4 生成 reality_uuid / hy2_pw / trojan_pw（各站点独立）。
- 凭据由管理守护进程**每人随机生成**；生成器仓库里只留假的 SAMPLE_CREDS 供泄露检查样例，不对应任何服务端用户（verify 断言朋友产物必须是 SAMPLE_CREDS，防真凭据进仓库）。

### 2. 鉴权分层与监听口隔离（最小权限）
- 【已验证】两个监听口故意分开：
  - 管理 API + 订阅分发听 **127.0.0.1**，由 nginx 反代做门禁（管理挂在自用 token 路径下，nginx 那层就是门禁）；朋友订阅 /f/<token>/ 是公开路径，**token 本身即密钥**。
  - 节点凭据同步口绑 **tailscale IP**（不是 0.0.0.0）——公网网卡上根本没这个口，就算 ufw 配错也暴露不出去； additionally 要 Bearer 校验。
- Bearer 与 token 比较都用 **hmac.compare_digest**（常量时间，防时序侧信道）。
- 不复用现成的 0.0.0.0 状态口（它开着目录列表）→ 另起绑 tailnet 的口。
- 状态文件 friends.json 权限 **600**（里面是全部朋友的节点凭据）；线路目录 friends-lines.json 600，**凭据只在这个文件**，管理进程只读 label/expires，下发给节点的 users.json 只发线路 id（节点用本地目录解析，没有这条线的节点跳过）。

### 3. 撤销 = 真断连（不只是拉不到更新）
- 【已验证】users.json **只列未撤销且未到期的人**；节点侧 friends-apply 每 60s 拉一次，照着重写 sing-box 各 friends-* inbound 的 users 数组并重启 → 被撤销者的凭据在服务端就没了。
- 时效：订阅链接**立刻 410**；节点侧凭据失效 **≤60s**（节点每分钟拉）。
- 本质区别：只换订阅 token，对方手里已存的配置照常能用；删服务端 users 才是真断连。实测：建测试朋友→三地连通→点撤销→链接立刻 410、users 只剩旧用户→同一份客户端配置三地全连不上。
- 失效响应分对象：浏览器打开页面 → 同款设计语说明页（410，noindex）；客户端拉配置 → 纯文本 410（客户端只看状态码）；页面样式文件对失效链接照常提供。

### 4. 到期与自动续期（"好产品要安静"）
- 【已验证】expires=None 表示永久。auto_renew 条件全满足才续：未撤销 + 有到期日 + **距到期 ≤14 天** + **最近 30 天拉过订阅**（last_seen）+ 本人 auto_renew 未关 → 到期日 **+90 天**，记 renew_log。
- 不续的：永久/已撤销/已过期/30 天没拉过（不用的人自然失效 = 自动清理）/手动关了的。
- 触发点：节点每 2min 拉 users.json 时顺带跑 auto_renew（无需独立 cron）。客户端默认每 24h 自动拉，所以"在用"的人 last_seen 总是新的。
- 手动 renew：清 revoked + base=max(now, 原 expires) + days；delete：从库移除 + rmtree 其订阅目录。

### 5. 状态持久化与并发
- 【已验证】原子写：tmp → chmod 600 → os.replace；version 单调递增（save bump_version=True）；last_seen/hits 更新 bump_version=False（不触发节点无谓重启）；threading.Lock 串行读写，_build_lock 串行生成，_ulock 串行用量。
- POST body 上限 65536 字节，超则 413；输入校验：name 必填截断 40、note 截断 80、days 必须整数非负、airports 按目录规范化（未知前缀报错）。
- setairports 先 ensure_sub(force) 重生成成功**才落库**（失败不污染状态）。

### 6. 多用户隔离：独立 inbound + AI 出口护栏
- 【已验证】朋友走三台机上**独立 friends-* inbound**（独立端口、独立 uuid/密码），与自用 inbound 不共享任何凭据。好处：朋友配置外泄 ≠ 自用节点外泄（不用全量轮换）；断朋友 = 停 friends-* inbound + 关端口，自用不受影响；流量按端口精确计数。
- REALITY **复用各机原密钥对**（只换端口 + uuid）：公钥按设计就是发给每个客户端的公开值，不做身份认证（认证靠 uuid），复用不是泄露。
- **AI 出口护栏**：主力/备份机的 route.rules 会把 AI 域名分流到住宅落地 outbound。若不管，朋友 AI 流量会悄悄从主人住宅 IP 出去（烧住宅带宽 + 多人共用把住宅 IP 送进 AI 厂商风控）。修法：在 route.rules **最前面**插 {inbound:[friends-*], outbound:direct}，朋友流量一律本机直出。**以后加任何分流规则须确认护栏仍在第一条**。
- selfheal 联动坑：兜底脚本按"domain_suffix 含 openai.com"找自家 AI 规则，朋友专属规则也含 openai.com 且排前面 → 会被误改指住宅或误读。四处 jq 都加 (.auth_user|not) 排除带 auth_user 的规则。**以后写按 openai.com 找规则的 jq 记得排除 auth_user**。

### 7. 按人配额 / 流量计数（fwmark + mangle）
- 【已验证】同端口多用户、sing-box 又没编译 v2ray_api（233boy 只编译 clash_api，/connections 是实时快照、漏短连接、实测不带用户名）→ 绕开 sing-box 统计，用 **fwmark**：
  - 管理进程每人分配一个 mark（0x1001 起，存 friends.json；**一经分配不变，撤销也保留**）。
  - friends-apply 给每人建 outbound fr-acct-<tag> = direct + routing_mark，规则 {inbound:friends-*, auth_user:[tag]} → fr-acct-<tag>，插在护栏之前、朋友 IG 分流之后。
  - mangle FRIENDUSR 链挂 OUTPUT + PREROUTING，**增量增删不 flush**（免得每分钟清零计数器）；fru-save 把 mark 低 16 位 CONNMARK save；fru-tx:<tag> 匹配本机发包的 socket mark；fru-rx:<tag> 匹配回包 connmark 且包自身无 mark。
  - mark 只用低 16 位（掩码 0xffff），tailscale 用 0xff0000，互不干扰也不命中任何 ip rule。**只记字节数，不记访问目的地**。
- 为什么用 mangle 表不用 filter：ufw 只管 filter，ufw reload 不冲 mangle；塞 filter 的 ufw-after-input 会漏计（被 ufw-user-input 提前 ACCEPT 的包走不到）。无 -j 目标的规则只累加 pkts/bytes 继续走原链路，纯计数不改转发。
- 计数累加：iptables 计数器重启/规则重载归零 → "当前值 < 上次值 ⇒ 已归零，整体计入"（最多丢上次轮询到重启间 ≤60s）；上报**累计值**，报丢一次下次自动补；跨账期归档 history（RESET_DAY 与本机 VPS 配额同步）；管理进程做月度切分（base），hist 最多留 24 月。
- **计费口径**：friends_gb 计的是"朋友↔本机"字节；VPS 实际计费 ≈ **×2**（代理从公网收一份、再发给朋友一份）。门户显示按 ×2 折算，超配额 60% 变黄；不另发告警（整机流量告警已涵盖，再加只是噪音）。

### 8. 朋友专属 AI 线路 + 备用链（零重启切换）
- 【已验证】管理台每人一个"AI 线路"下拉，默认机房直出；选一条 ≤60s 生效。线路目录凭据只在 600 文件，下发只发 id。
- 备用链 selector fr-ai-<tag> 成员按优先级：专属线路 → 自家 IPRoyal-US → IPRoyal-CA → 机房直出。**故意不含住宅落地 lisa**：lisa 是唯一单租户真住宅、无可替代，朋友账号落上去会和自家账号同 IP 关联（违背"不共用"初衷）；IPRoyal ISP 便宜可随时换，适合当共享备用。
- 每个成员都是带该人 routing_mark 的副本 → **落到哪一级流量都照样按人计**。
- 探活：每轮经该出口拉 api.openai.com/v1/models，**任何 HTTP 状态（含 401）= 活**，407/5xx/连不上 = 死；用 urllib 而非 curl -x（**口令不进进程命令行**）。连续 3 次失败判死、连续 3 次成功判活（迟滞防抖）。
- 切换经 **clash_api PUT /proxies/<selector> {name:成员}**，不改配置不重启；selector default 固定第一级，重启后回第一级、同一轮 reconcile 马上切回该在的级。状态写 lines.json 的 _now，管理台显示 🟢在用/🟡备用/🔴机房直出/⚠️切换未生效。
- 分配/取消分配那一下配置才变 → sing-box 重启一次，所有走该节点的连接（含主人自己）断 1-2s 自动重连。
- 让朋友自验：浏览器开 <CF_PROXIED_DOMAIN>/cdn-cgi/trace 看 ip（别用 ip.sb：客户端那侧它不一定走 AI 组，可能误判）。

### 9. 节点侧应用器（friends-apply）的安全设计
- 【已验证】**拉不到用户表保持现状，不清空 users**：宁可让已授权的人继续能用，也不因管理机抖一下把所有朋友踢下线；真撤销下次拉取成功生效。（可用性 > 严格性）
- **只接管 fr- 前缀用户**，服务端其它用户原样保留。
- **内容真变了才重启 sing-box**（否则每分钟重启会打断主人自己的连接）。
- **先 sing-box check 再重启**：check 不过则**整体回滚所有改过的文件**（含 config.json）再退出，宁可不重启也不能把 sing-box 搞挂（那会连主人节点一起断）。
- write 保留原文件 mode（config.json 是 600，别被 umask 放宽）；tmp + os.replace 原子写。
- selfheal 若把 config.json 回退旧备份 → 按人规则丢 → 下一轮 friends-apply（≤60s）自动补回并重启一次。
- 端口自适应：各机朋友口可能不同（某机被墙后改端口）→ 从本机 friends-*.json 的 listen_port 读，不写死。

### 10. 定时器停摆的教训（运维）
- 【已验证】给一批定时器加 drop-in 只用 OnUnitActiveSec=（单调时钟），舰队 daemon-reload 后这些定时器陆续进入 SubState=elapsed、NextElapse=infinity **再也不触发**，波及 8 台 21 个定时器（朋友同步/DDNS/状态生成/配额轮询全停），朋友变更 3 天没下发。
- 修：改成同间隔墙钟 OnCalendar（60s→*:*:00、2min→*:0/2、15min→*:0/15，AccuracySec=1s）+ daemon-reload + restart。
- 排查提示：数据"停更"先查 systemctl show <timer> -p SubState，elapsed + NextElapseUSecRealtime 为空 = 定时器死了。自愈引擎内置 timers 检查每 2min 扫，卡 elapsed 的周期定时器自动 restart。

## ② 原作者特定环境经验（不可照搬）
- 【已验证】具体 token/凭据/朋友端口（41011-41014 及被墙后改 port）/线路 IP/朋友姓名/三台站点键（la/uk/jp）/控制面部署机均为其私有；朋友版只给三台大带宽机房机 × 协议，刻意剔除回家内网/住宅/小配额 HK/MY/全部付费机场/私人域名规则。
- 【已验证】朋友版无 SS：SS2022 多用户要改 EIH 结构（服务端 password 变 iPSK、客户端密码变 serverPSK:userPSK），会连带破坏主人现有 SS 客户端配置 → 朋友用 REALITY/Hy2/Trojan 够用。
- 【推测】fwmark 低 16 位与 tailscale 0xff0000 不冲突的结论依赖其当前 mark 布局；换内核/换 overlay 需重验。

## ③ 需要重新验证的结论（含验证方法）
- fwmark 计数准确性：loopback 穿朋友 inbound 用某人凭据下固定字节（如 3,000,000）→ 核对该人 fru-rx 增量（实测 +3,022,734 含协议开销）。
- 自动续期边界：8 种情况单测（永久/撤销/过期/未到期/超窗/不活跃/手动关/二次运行不重复续）。
- 专属线路迟滞：探活序列单测（第 3 次连续失败才摘、第 3 次连续成功才挂回；错口令探活=不通）。
- mangle 计数在 nftables 后端 / 新内核的行为；mark 与 tailscale/ip rule 不冲突。
- 真断连时效：撤销后实测同一份客户端配置三地连不上（≤60s）。

## ④ 可迁移到 FixCloud / Lucky / QNAP NAS 的具体做法
- **FixCloud（用户/订阅管理）**：按人独立凭据 + 真断连（删服务端 users 而非只换 token）；管理口听 127.0.0.1 经反代门禁、节点同步口绑 tailnet + Bearer（hmac.compare_digest）；状态 600 + 原子写 + version 单调；拉不到权威表保持现状不清空；先校验再重启、失败整体回滚；AI/敏感出口护栏置顶且 jq 排除 auth_user；按人 fwmark + mangle 计数（只记字节不记目的地，计费 ×2 口径）。
- **Lucky**：反代管理 API 做门禁（自用 token 路径），朋友公开路径 token 即密钥；裸路径 444；DDNS 跟随。
- **QNAP NAS**：若做共享代理/多用户，借鉴独立 inbound + 按人凭据 + fwmark 配额；注意 QTS 权限墙（守护进程跑 admin/root，普通 SSH 用户改不了系统级配置）；状态/凭据文件 600，不硬编码密钥。

## ⑤ 来源文档路径清单（只给路径，不给敏感内容）
- fork-clone/40-朋友版订阅-friends.md
- fork-clone/12-订阅服务器与新增节点.md
- fork-clone/scripts/friends/friendsd.py
- fork-clone/scripts/friends/friends-apply.py
- fork-clone/scripts/friends/friendacct-rules.sh
- fork-clone/scripts/friends/friendacct-collect.py
- fork-clone/scripts/friends/install-friendacct.sh
- fork-clone/scripts/friends/friendsd.service、friends-apply.timer、friendacct-collect.timer
