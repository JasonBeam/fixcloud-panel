> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。

> 作者统一称「原作者」。示例一律用 example.com / 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24 / <EXAMPLE_TOKEN> 等文档示例值；机器以角色代称，不出现真实主机名/IP/域名/凭据/设备标识。【已验证】=实际读到/测到；【推测】=推断待核。

# 12 · 可迁移到 FixCloud / Lucky / QNAP NAS 的经验清单

> 逐条：经验 → 为什么适用 → 在 FixCloud 的落点模块/页面 → 风险与前置条件。
> ⚠️ FixCloud 落点为【推测：需对照 FixCloud 实际模块/页面命名】，本清单未读 FixCloud 源码；Lucky/QNAP 落点基于原作者已验证用法。经验本身【已验证】来自 homelab 实践。

## ① 通用可复用经验（迁移清单）

### A. 建站基线 / 系统调优
1. **合规矩阵 + 一键幂等基线脚本**（apply-baseline 8 件：journald 封顶按盘大小 / APT keep-lean / logrotate 包必装 / sing-box logrotate copytruncate / conntrack 先 modules-load.d 再 sysctl / APT 自动清旧内核 / 小内存 512M swap / Tailscale UDP GRO 持久化）
   - 为什么适用：FixCloud 面向多机/多 NAS，每台新设备同一套标准、做完打勾，避免「配置漂移」和「只放配置没装包」空转。
   - 落点【推测】：建站向导 / 基线检查页 / 系统调优模块（一键体检 + 修复）。
   - 风险与前置：conntrack 必须先 modules-load.d 否则重启回落；logrotate 包必装；GRO 需 ethtool 支持 + 网卡名稳定；小盘阈值 80% 不是 90%。
2. **TCP LFN 缓冲调优按 BDP，不是越大越好**（1G 机 8MB，tcp_mem 全局硬顶；slow_start_after_idle=0 / mtu_probing=1 / tcp_fastopen=0）
   - 为什么适用：FixCloud 若做代理/中转/大文件传输，单流吞吐受默认缓冲钳死；但顶格会被全局硬顶放大成 memory pressure。
   - 落点【推测】：系统调优页 / 网络加速模块（按内存/线路自动推荐值）。
   - 风险与前置：tcp_fastopen=0（GFW 指纹）；别换内核/BBRplus；UDP 生效需重启服务；回滚删文件单跑 sysctl --system 不复原运行时值需 sysctl -w。
3. **每周凌晨错峰重启 + 计划重启标记静默**
   - 为什么适用：清内存 + 吃内核补丁，低峰 + 自愈兜底影响极小；NAS 长在线设计例外（重启中断下载/SMB）。
   - 落点【推测】：定时任务模块 / 维护窗口设置。
   - 风险与前置：NAS 不加自动重启；错峰防齐射；重启前打标记让告警静默；所有服务开机自启。

### B. 安全加固 / 最小权限
4. **ufw default-deny + 封出站 TCP25 + fail2ban 累进 + ignoreip 含 tailnet 段**
   - 为什么适用：FixCloud 暴露公网的设备头号现实风险是 SSH 爆破 + 被滥用发垃圾邮件封鸡；监控/自愈从 tailnet 探 22 会被自己封。
   - 落点【推测】：安全加固页 / 防火墙模块 / fail2ban 管理。
   - 风险与前置：ignoreip 必含 127.0.0.0/8 + 100.64.0.0/10；非标 SSH 端口改 jail action port；改端口同步 ufw allow；SS 要 UDP 就 allow 口/udp。
5. **SSH key-only + 厂商 drop-in 中和 + sshd -T 校验**
   - 为什么适用：厂商镜像出厂 drop-in 默认开密码/root，直接改主 config 被字典序压过；FixCloud 装机向导要确保真关。
   - 落点【推测】：SSH 加固页 / 装机向导安全步骤。
   - 风险与前置：00-00 排序最前 + 中和厂商 drop-in + cloud.cfg.d 防 cloud-init 重启再开；sshd -t 校验后 reload 不断现有连接再开新连接实测；救援后路面板 VNC + root 密码。
6. **age 公钥加密配置备份 + 恢复禁盲解 + 幂等重建**
   - 为什么适用：FixCloud 备份模块若明文打包机密进 git/云=泄密；盲解覆盖运行环境会重开已修好的洞。
   - 落点【推测】：备份恢复模块（加密备份 + 恢复向导）。
   - 风险与前置：私钥只存本机 0600 + 云盘绝不进 Git；.gitignore 阻止明文；**「安装脚本能否幂等重建全部配置」是先决条件需先验证**；git 历史不可逆。
7. **红队攻击面收敛 + 不变量常驻测试**（loopback/tailnet/域名三种绕过；ip_is_private 不含 CGNAT；域名绕过要 action:resolve）
   - 为什么适用：FixCloud 若做代理/反代，代理→内网洞被找到三次每次推翻上次「已修」，一次性验证不够。
   - 落点【推测】：安全审计页 / 代理路由模块（常驻红队探针）。
   - 风险与前置：复验字面 IP 和域名都要 502；规则序 [resolve, ip_is_private reject, cgnat reject]；同规则多字段 AND 要 OR 拆两条；回退表别混旧备份。
8. **账号层 2FA + 域名转移锁 + token 最小权限**（最省力收益最大，不改架构）
   - 为什么适用：FixCloud 用户域名/DNS 账号是命根子，被盗=全部服务被接管。
   - 落点【推测】：账号安全页 / 域名管理 / API token 管理。
   - 风险与前置：CF/注册商/邮箱都开 2FA；Transfer Lock；token scope 单 zone 别用 Global Key；截图露过 token 开头要撤销重建。
9. **凭据卫生**（env 600 不入库 / access_log off 防 token 路径泄漏 / authsvc fail-closed 移除 changeme / scrypt 加盐 / 改密码踢旧会话 / 递增延迟不按 IP 锁定）
   - 为什么适用：FixCloud 登录墙/订阅分发若用默认口令或无盐哈希或按 IP 锁定（L4 透传共用源 IP）=送 DoS 开关。
   - 落点【推测】：认证模块 / 订阅管理 / 日志配置。
   - 风险与前置：必填项 :? fail-closed；token location access_log off；递增延迟持锁串行；真要按 IP 限速须 PROXY protocol。

### C. DNS / DDNS / TLS / 反代
10. **DDNS 强制 proxied:false + 非 JSON 静默跳过 + TTL 纠正 + token 单 zone**
    - 为什么适用：Lucky 已有 DDNS，FixCloud 可复用「CF API 偶发非 JSON 不报错防误判」「IP 固定后降频」「灰云不暴露橙云误开」。
    - 落点：Lucky DDNS 模块（已验证）；FixCloud【推测】域名/DDNS 页。
    - 风险与前置：取本机公网 IP 别看 ipify（OpenClash 劫持假 IP），看 pppoe-wan；换 IP 高危节点要新子域 + 轮换端口 + 重签证书。
11. **证书信任链哨兵 + 档位降噪 + ACME 账户坏新建绕开 + 忽略 DNS-01 传播检查**
    - 为什么适用：Lucky 证书续期失败静默（错误写自己日志中心 stdout 看不到），FixCloud 证书管理要同时验信任链不只看到期日。
    - 落点：Lucky 证书模块（已验证）；FixCloud【推测】证书管理 / 监控告警页。
    - 风险与前置：trusted=no 与 expired 同等严重；CT 日志 Google Trust/Sectigo 是 CF 边缘证书别误判；删证书回落自签更糟（先 stop 容器再覆盖还原）；OpenClash 劫持 53→忽略传播检查。
12. **Caddy encode + 缓存三层 + 安全头 snippet + SSE 排除压缩**
    - 为什么适用：FixCloud 门户/看板若用 Caddy，默认不压缩 + no-store 误打 vendored 资源 = 首屏慢；缺安全头是架构决定（L4 透传碰不到 HTTP）。
    - 落点【推测】：反代配置页 / 门户性能设置。
    - 风险与前置：encode zstd gzip 一行省 74%；immutable 只给永不变 + 带 ?v= 资源；no-store 只留 HTML + telemetry；HSTS preload 不可回退慎加；SSE flush_interval -1。
13. **单域名多服务 DNS 故障切换 + 端到端健康 + 兜底撤离**
    - 为什么适用：FixCloud 若做多入口/多中转，朋友只记一个地址；relay 活但回家腿死照样挂，健康判定必须端到端。
    - 落点【推测】：反代 / 入口管理 / 故障切换模块。
    - 风险与前置：统一端口（DNS 只能换 IP 不能换端口）+ 证书 SAN；同 ServerId 同 token 才透明；切换器防抖 2 轮坏切 5 轮好抢回；DNS 切换不迁移正在播的流（电视盒子无视 TTL）；切换器自己挂要兜底撤离。
14. **nginx stream L4 SNI 透传 vs http 真终结的取舍 + PROXY protocol 保真实 IP**
    - 为什么适用：FixCloud 入口机若 L4 透传，边缘无法限流/缓存/WAF/加安全头；要边缘化须真终结 TLS。
    - 落点【推测】：反代架构选择 / 入口机配置。
    - 风险与前置：L4 透传 TLS 在后端终结→贵的是入口↔后端两跳非客户端↔边缘；socat 加不了 XFF→后端按 IP 限速有害；备份 vhost 别放 sites-enabled（include * 加载 .bak→limit_req_zone 重复 emerg）。

### D. 监控 / 告警 / 自愈
15. **selfheal 引擎 + 按机 checks + 护栏重启 + 防抖 + 静默首修**
    - 为什么适用：FixCloud 设备「systemd active 但实际卡死」is-active 探不到也不修；多次修复失败要升级处置但有护栏防 boot-loop。
    - 落点【推测】：故障自愈模块 / 健康检查配置。
    - 风险与前置：探针真实健康（TCP/HTTP200/docker .State.Health/服务 check）超越 is-active；重启间隔 ≥4h 开机 <10min 不重启 REBOOT_MAX_PER_DAY=2；FLAP_WINDOW 停手；磁盘护栏不重启；repair 为空=只告警型别发误导 🔧。
16. **多采样多数决 + 非对称迟滞 + 抖动锁 + 零重启 selector**
    - 为什么适用：FixCloud 若做 AI/代理出站切换，单采样在丢包链路必然假阴性→翻转风暴→每翻一次 restart 掐断全体用户。
    - 落点【推测】：代理出站 / AI 落地切换模块。
    - 风险与前置：探针越长越不能只采一次（TRIES=3 NEED=2）；快降级慢恢复；抖动锁降级方向永远放行；零重启用 selector + clash_api PUT（探针必须探本体不跟 selector）；AI_RULE_MODE 校验防静默失效。
17. **告警降噪状态机 + 播报责任制 + 依赖抑制 + 单一播报者 + 计划重启静默**
    - 为什么适用：FixCloud 多设备互监若每台齐报 down+up=刷屏（一周 47 条实际需动手 2 条）；底座故障下游连带要抑制。
    - 落点【推测】：告警设置页 / 通知渠道管理。
    - 风险与前置：REPORT_PEERS 写裸 host 别写全格式（匹配不上=无人播报）；每目标恰好一台播报者；底座先探下游抑制；DNS 死缓存 IP/--resolve/spool 补发；外部哨兵出网自检门 + 判罚钝 + 目标防抖。
18. **流量按账单周期 + 速率外推预测 + 按用户归属（token→UID→IP）+ 媒体路径专用日志**
    - 为什么适用：FixCloud 流量统计若按自然月会误判配额；多用户共享中转要按人记账；零新代码用 nginx log_format + 现有 DB 映射。
    - 落点【推测】：流量统计页 / 配额预警 / 用户用量卡。
    - 风险与前置：vnstat 首期偏少以面板为准；官方计数注意 multiplier；CST 日界聚合；token→用户名映射对账；含令牌的 json 切勿端口转发；自用直连不计入。
19. **看板遥测新鲜度 + 原子写 + 缓存过期不伪造 + 定时器自愈 + watchers**
    - 为什么适用：FixCloud 仪表盘若显示旧快照伪造新采样=误导；采集器挂/定时器卡死要能自检。
    - 落点【推测】：仪表盘模块 / 遥测采集器管理。
    - 风险与前置：STALE 阈值按实际采集频率；原子写 tmp + os.replace；缓存过期停止显示标记原采样时间；周期定时器一律 OnCalendar + 错峰 AccuracySec；telemetry（json >10min 没更新）+ watchers（定时器非 active）+ 监控的监控第三层。
20. **指标口径：延迟只信光纤边缘 / 吞吐加密多连接直连源 / 明文 HTTP 伪象**
    - 为什么适用：FixCloud 若做线路质量测速，WiFi 笔记本 + 明文 HTTP 会给差百倍假数据。
    - 落点【推测】：网络质量测试模块 / 线路评测页。
    - 风险与前置：源用有线（openssh 硬件 AES，dropbear 卡 2-4Mbps 假象）；8 并发加密流；--noproxy 排除系统代理；21-23 点晚高峰多日；先验源侧网关/锚点。

### E. NAS / 备份 / 穿透
21. **双 NAS 互备单向 + 快照前置硬条件 + 离站加密**
    - 为什么适用：QNAP/群晖互备若双向=删除传染；镜像≠备份（错误几分钟内忠实复制），版本保护全靠快照；同屋檐火灾/盗窃一锅端→不可再生数据加加密云离站。
    - 落点：QNAP/群晖备份模块（已验证 Cloud Sync 单向 WebDAV + Hyper Backup AES-256 + B2）；FixCloud【推测】备份策略页。
    - 风险与前置：每个数据集只有一个写入侧，镜像方向跟写入侧走；快照计划是前置硬条件（群晖各共享原本只有 TM 有快照其余全 0）；黑名单过滤 @eaDir/#recycle 等；初次种子逐个建让每个先种完；撤销窗口=快照保留天数；加密密码记入密码管理器（丢=数据废）；恢复演练半年一次。
22. **Tailscale Peer Relay 转发优先 + 看守脚本 + ACL 先读现有内容**
    - 为什么适用：FixCloud 若做异地组网/穿透，直连走普通线反而慢，经近港精品转发快；但 ACL 加一条 grants 会从默认放行变默认拒绝全断。
    - 落点【推测】：网络 / 穿透 / Tailscale 管理模块。
    - 风险与前置：动 policy 前先读现有内容补全放行；两台转发同时开反而变差只留一台；看守脚本撤规则恢复直连是退路不是 Tailscale 自带；转发计入 VPS 配额；远端 IP 写死变了退回直连不会断；Peer Relay 需 Tailscale ≥1.86。
23. **launchd/systemd 定时器 OnCalendar + 错峰 + AbandonProcessGroup + pmset 原生重启**
    - 为什么适用：FixCloud 若管 Mac/NAS 定时任务，OnUnitActiveSec daemon-reload 后卡 elapsed；launchd 默认杀后台长任务；headless osascript 被 TCC 拦。
    - 落点【推测】：定时任务模块 / Mac 代理管理。
    - 风险与前置：周期定时器一律 OnCalendar；AccuracySec=1s 防齐射； plist AbandonProcessGroup true（验证由 launchd 自己拉起）；Mac 重启用 pmset repeat restart；用户态日志轮转用 LaunchAgent 代替 newsyslog（sudo 要密码）。
24. **客户端配置生成器泄漏审计**（Auto 墙外全直连 / DNS 同发中国解析器 / IPv6 三层绕过 / allow-lan 开放 / DoH 跟随循环依赖）
    - 为什么适用：FixCloud 若生成 Clash/Surge 订阅，默认配置可能泄漏真实 IP/DNS/IPv6，同网段任何人可用代理。
    - 落点【推测】：客户端配置生成器 / 订阅管理页（生成前泄漏 lint）。
    - 风险与前置：AI Suite 强制走代理删 DIRECT；nameserver 走代理 DoH + 尾部 IP 规则 no-resolve；allow-lan:false/bind 127.0.0.1；路由 LAN 侧 RA/DHCPv6 disabled；墙内冷启动闸门 DNS 循环依赖必须实测；Mac 本地 [General] 不随订阅更新；真机/WebRTC/v6 未覆盖。

## ② 原作者特定环境经验（标注依赖）
- **Lucky 落点已验证**：DDNS（cf-ddns 同套 CF 凭据）、证书（ACME 账户坏新建绕开 + 忽略 DNS-01 传播检查两开关）、反代（10 服务共用泛域名证书，非标端口橙云救不了）、后台 SSH 隧道（tailnet 源 IP 判外网 403→SSH 本地转发源 IP=内网放行）。依赖：iStoreOS 容器 lucky:3.0.0beta，配置 .lkcf 私有加密格式。【已验证】
- **QNAP/群晖落点已验证**：群晖 Cloud Sync 单向 WebDAV（5005HTTP 换 5006HTTPS）+ Hyper Backup AES-256 离站 B2 + DSM 快照管理器每日保留 14-30 份；QNAP vol1 每夜快照保留 23 份。依赖：双 NAS + WebDAV + B2 账号。【已验证】
- **FixCloud 落点全部【推测】**：本清单未读 FixCloud 源码，模块/页面命名为建议，需对照 FixCloud 实际架构核实。原作者舰队角色分工（主力出口/住宅落地/算力中枢/入口/网站后端/备份哨兵/中转）可作为 FixCloud 多设备角色建模参考。【推测】

## ③ 需要重新验证的结论（给验证方法）
- **FixCloud 模块映射**：验证：读 FixCloud 源码/路由表，把本清单 24 条落点逐条对照实际模块/页面命名，标注已有/缺失/需新建。【推测：全部待对照】
- **幂等重建先决条件**：验证：干净机跑安装脚本 + assert_invariants，对比解密包差异，确认能否重建全部配置（含 harden/resi/selector 规则）。【已验证：此先决条件未核】
- **Lucky 证书自动续期**：验证：新 ACME 账户 + 两开关约 60 天后 notAfter 推进 issuer 仍 LE。【已验证：首次手动成功】
- **双 NAS 备份落地**：验证：~90% 未落地（群晖无快照无异地，Cloud Sync 9 个只建 1 个），先群晖快照（唯一防勒索层不需新硬件）→厘清 QNAP 老数据身份逐个建任务→B2 离站。【已验证：大部分未落地】
- **客户端泄漏修复真机**：验证：iPhone/安卓真机 + WebRTC/DNS 泄漏 + v6 网络（过语法行为未实测）。【已验证：真机未覆盖】
- **Peer Relay 多日稳定性**：验证：只测一晚，多日 ping/下载对比 + 看守脚本阈值改 5 轮后重新演练退路。【已验证：单晚数据】

## ④ 来源文档路径清单
- 20-建站规范-standard.md（基线 / 合规矩阵 / 新服务规范）
- 09-安全加固.md、41-红队审计-攻击面.md、45-红队复审-20260904.md、49-红队四审-20261017.md（安全加固 / 攻击面 / 凭据卫生）
- 07-DDNS与域名.md、10-配置备份.md、14-Homelab门户-Tailscale.md（DDNS / 证书 / age 备份 / Lucky 后台隧道）
- 19-故障自愈-selfheal.md（selfheal 引擎 / 多采样 / 零重启 / 降噪 / launchd 陷阱）
- 33-双NAS互备与离站备份.md（单向镜像 / 快照前置 / 离站加密 / 维护 runbook）
- 53-Tailscale转发优先-PeerRelay-20261106.md（转发优先 / ACL / 看守脚本）
- 52-客户端泄漏审计-20261105.md（客户端配置泄漏审计）
- 32-Emby媒体服务器.md、50-舰队巡检与Emby单域名-20261030.md（单域名多服务 / 流量归属 / 时区感知中转）
- 25-VPS-IP与网络质量测试.md（指标口径 / 测速伪象）
- scripts/ops/apply-baseline.sh、scripts/ops/cf-ddns.sh、scripts/entry/、scripts/emby-relay/、scripts/selfheal/、scripts/dashboard/、backups/dashboard/{Caddyfile,docker-compose.yml,authsvc/app.py}
