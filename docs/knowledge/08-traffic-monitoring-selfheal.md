> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。

> 作者统一称「原作者」。示例一律用 example.com / 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24 / <EXAMPLE_TOKEN> 等文档示例值；机器以角色代称，不出现真实主机名/IP/域名/凭据/设备标识。【已验证】=实际读到/测到；【推测】=推断待核。

# 08 · 流量统计 / 监控 / 故障自愈

## ① 通用可复用经验

### 1. 指标口径（先定义「算什么」，再谈采集）
- **流量按真实账单周期，非自然月**：vnstat + tg-quota.sh 按 QUOTA_GB/RESET_DAY 计算，80%/95% 提醒。vnstat 从安装起计首期偏少，精确以面板为准；搬瓦工配额优先读官方计数（/run/kiwivm-traffic 第二列，env 兜底），注意 monthly_data_multiplier（当前 mult=1 无影响，换 mult>1 会低报）。【已验证】
- **配额预测 + 速率外推**：每小时预测器回放可提前 6 天告警（做得对），但「提前 6 天要做什么」的 runbook 要预先写，需求侧杠杆（限朋友版/分流）要预先决定。【已验证】
- **Emby 流量按用户归属（零新代码）**：relay nginx log_format emby_traffic（时间/api_key/X-Emby-Token/body_bytes_sent，**仅媒体路径 videos|audio**）→ agg timer 每 1min 按 CST 日界聚合 → Mac 读 authentication.db Tokens_2 ⋈ users.db LocalUsersv2 得 token→用户名 → poll-emby-usage 60s 合并三区 + 映射留 7 日 → 门户卡（今日总量/每用户 GB/分区/7 日柱）。Token→UID→IP 三级归因，per-IP .ts 分片回填，.NET 混合端序 GUID 解码。未匹配 token 归「未识别」；自用直连不经 relay 不计入。【已验证】
- **延迟只信光纤边缘**（OpenWrt/有线 Mac mini），别信 WiFi 笔记本（抖动 + clash tun 假象）；**吞吐走加密多连接直连源**（明文 HTTP 被 DPI 降速伪象，见 01）。先验源侧（网关/锚点）别拿被污染样本给远端下结论。【已验证】
- 采集失败改「待确认」独立业务检查才判离线；SNMP 磁盘/卷字段保留原采样时间、标记缓存 10min 过期停止显示旧快照、**不伪造新采样**；阈值按实际采集器频率（证书 12h / 分区 NAS 2min）。【已验证】

### 2. 巡检节奏
- selfheal 每 2min（OnBootSec=3min）；tg-monitor 每 3min；tg-quota 每小时；证书每天一次（慢变量 DAILY_GATE）；外部哨兵每 2min。【已验证】
- **降频用 OnCalendar**（别只用 OnUnitActiveSec，daemon-reload 后卡 elapsed）：svcstatus-gen 15s→60s、poll-fleet 60s、poll-emby-relays 2min、cf-ddns 15min（IP 固定）、clash-stats 5s→15s。不动 selfheal 2min/tg-monitor 3min。【已验证】
- **定时器错峰 AccuracySec=1s** 防齐射（多个 *:*:00 齐射 + 高频容器 inspect 是 docker 慢的 churn 源）。【已验证】
- 心跳：原 6 台每天各 1 条（42 条/周）→ 中枢每天 10:00 一条 hub（PEERS 列全舰队一条见全局），其余轮值周报 → 最终全舰队只剩一条周报。【已验证】

### 3. 自愈触发与回退（selfheal 引擎）
- **架构**：一套引擎全机同一份 + 按机注册检查项 checks.<host>.sh（唯一按机不同）+ 阈值 env + timer + 日志（logrotate）+ 状态 /run（tmpfs 重启清）+ /var/lib（持久：重启限速戳/防抖窗口）+ 告警复用 tg-notify 状态机式。【已验证】
- **探针是真实健康，超越 is-active**：本地 TCP 连通（/dev/tcp）、HTTP 200、docker .State.Health、sing-box check。systemd 显示 active 但实际卡死/端口不应答，is-active 探不到也不修。【已验证】
- **单次逻辑**：探针健康→若之前异常且发过消息发 ✅ 恢复清计数，静默修好的（只失败 1 次）只记日志不发；探针异常→计数 +1，≤MAX_REPAIR（默认 3）执行修复（重启单元/docker restart/自定义），第 1 次静默修（NOTIFY_MIN_FAILS=2）连续第 2 次起才发 🔧；>MAX_REPAIR 升级：关键服务且允许重启且未限速→有护栏整机重启，否则发 🆘 需人工。【已验证】
- **防抖**：FLAP_WINDOW（1h）内修复超 FLAP_MAX（5）次→停手只告警（防重启循环掩盖真问题）。【已验证】
- **有护栏整机重启**：仅关键服务多次修复失败或系统级卡死（可用内存 <3% 且 15min loadavg > 核数×4 连续 2 轮）。护栏：两次自愈重启间隔 ≥4h；开机 <10min 不重启（防 boot-loop）；不与每周 scheduled-reboot/U-U 打架；每次重启前发 TG；**REBOOT_MAX_PER_DAY=2**（reboots.log）。【已验证】
- **磁盘护栏（不重启）**：根分区 ≥90%→journalctl --vacuum + 截断 >100M 日志 + TG，回落 <85% 发恢复。【已验证】
- **repair 为空 = 只告警型**：连续 NOTIFY_MIN_FAILS 次发 ⚠️（仅告警无自动修复），不再发误导 🔧/🆘；WARN_MIN_FAILS=5（~10min），没 ⚠️ 就不 ✅。【已验证】
- **回退表分级 + 不变量断言**：config.json.lastgood（每轮校验通过刷新）→ .selfheal.bak → ls -t bak*；无可用备份不盲目重启不升级整机；每轮断言私网 reject/tailnet-reject/selector 三项在位，缺了 🆘 指明重跑哪脚本（防恢复成旧配置重开安全洞）。【已验证】

### 4. AI 落地回退（fail-open：可用性 > 住宅 IP 纯度）
- **探针改 e2e**：经本机 sing-box ai-probe 入站（127.0.0.1 固定路由→住宅落地）真拉 https://api.openai.com/v1/models，一次验落地 TCP + 隧道 + 落地端 DNS + 出网。2xx/3xx/4xx 都算通（401/403=到达源站），000/5xx=黑洞。**只探 TCP 曾漏掉「端口活着但解析死」的黑洞**。【已验证】
- **多采样多数决**（0916 翻转风暴教训）：AI_PROBE_TRIES=3 / AI_PROBE_NEED=2（3 次里需 2 次拿到源站应答才算可用，带早退）。探针越长越不能只采一次——e2e 链路长（TCP+隧道+DNS+出网），任何一环丢包都会超时，单采样把长链路瞬时抖动当落地故障。p(单次失败)≈11-40% → p(连续 2 次)≈1-16%，每 2min 一轮 → 一天几十次翻转。【已验证】
- **非对称迟滞**：AI_DOWN_STREAK=2 / AI_UP_STREAK=3，快降级慢恢复（降级关系 AI 能不能用要快，切回只关系住宅 IP 纯度，降级期 AI 照常能用不急，反复切回正是翻转风暴燃料）。【已验证】
- **抖动锁**：FLAP_WINDOW（1h）内翻转 ≥6 次→锁定 direct 不再自动切回（降级方向永远放行），发一条 🔒，稳定 1h 后窗口自然清零自动解锁。【已验证】
- **零重启翻转（0917 核心）**：伤害不是翻转本身，是每翻一次 systemctl restart 掐断全体用户连接。改成 sing-box **selector 出站 + clash_api**（仅 127.0.0.1 + secret），一个 HTTP PUT /proxies/<selector> 进程内换指针，不改配置不重启，已有连接不断（interrupt_exist_connections:false，规则指向 selector 时翻转对已有连接 no-op 只改新连接）。cache_file.enabled 选择项重启后恢复上次选的（不回 default）。期望 204 且复核 .now==target，否则退回老路改 config + 重启。【已验证】
- **探针必须探本体**：ai-probe 路由仍直指落地成员（不跟 selector 走，否则永远探不到恢复）；_flip 的 jq 只改含 domain_suffix 的规则不碰探针规则。【已验证】
- **三级/四级 + 粘滞**：住宅→静态 ISP→机房；降级快，升级须上级连续健康 required_dwell 秒；指数流放近 24h 每多降一次 dwell 翻倍（1800→3600→7200 封顶 12h），越不稳回去越慢，稳了自然回无需人工。每级探自己那条 IP（别统一探同一 URL，否则 ca 挂也判健康）。【已验证】
- **校验不过绝不带坏配置重启**，自动回滚；config 被安装脚本重写导致规则丢失→记日志 + 告警不崩。【已验证】

### 5. 告警外发与降噪（好产品要安静：一周 47 条 TG 实际需动手约 2 条）
- **TG 状态机式**：只翻转发不刷屏；掉线连续 3 次/恢复连续 2 次才播报（超时 6→8s）；1h 内翻转 ≥5 次判网络抖动→只发一条静默提示稳定 30min 恢复。【已验证】
- **播报责任制 REPORT_PEERS**：单机宕机原 5 台齐报 down+up≈10 条→每目标指定播报者其余照常探测/记状态/心跳显示只是不发翻转消息→最终**单一播报者**（每目标恰好一台）。⚠️格式坑：必须写裸 host（与 PEERS 条目中段一致）不能写全格式（名字:host:port），匹配逻辑 case 全格式永远匹配不上→实际无人播报。【已验证】
- **计划重启不播**：scheduled-reboot 重启前打标记，tg-boot 见新鲜标记（<30min）静默，非计划启动才播（文案带「非计划启动」更有信号量）。【已验证】
- **外部哨兵 v2 三层降噪**：①出网自检门（锚点 1.1.1.1/8.8.8.8:443 全不可达=本机线路问题→跳过外探只发一条哨兵出网异常）②判罚更钝（异常连续 3 次旧 2，恢复连续 2 次旧 1）③目标级防抖（1h 翻转 ≥3 次静默该目标稳定自动恢复）。每目标只归一台哨兵避免双哨兵各发一遍，不探自己托管服务。【已验证】
- **依赖抑制**：底座（中枢/家宽）先探，下游（门户/订阅依赖中枢，Emby 分区依赖家宽）底座已 down 时下游 down 和配对恢复都不播（只同哨兵内有效，跨哨兵靠 EXT_DOWN_N 宽限兜短抖）。EXT_DOWN_N=5（~10min@2min，旧 3~6min 一周 11 条 down 多是几分钟自愈抖动）。【已验证】
- **DNS 死时告警发不出**：先系统 DNS 失败用缓存 IP（/var/lib/tg-notify.ip）/内置 IP --resolve 兜底→仍失败进 spool 下次成功补发 ≤5 条；repair_dns 先修再报。【已验证】
- **监控中枢自身盲区**：监控全在中枢，中枢自己挂了没人报→至少一台舰队外机器 HTTP 探它（独立外部哨兵）。【已验证】
- 三个永久误报源要清：PEERS 残留已退役机器（心跳永远 🔴）；探有源 IP 白名单的口（永远 down，改探公开口）；互为路由黑洞的对端（双向 100% 丢包，从 PEERS 移除仍由其他机盯）。【已验证】

### 6. 看板设计
- svcstatus→:9101/services.json；门户舰队卡片 poll-fleet.sh 的 NODES/IPS/NAMES 三数组同序各加一项（别只加 Prometheus 以为接入）。【已验证】
- **遥测新鲜度**：门户 STALE 300s（fleet）/30s（clash）；telemetry 检查（4 门户 json >10min 没更新→采集器挂）；watchers 检查（在线节点 selfheal/tg-monitor 定时器非 active）。【已验证】
- **定时器自愈**：已启用应周期触发却卡 elapsed→restart（一次性/过期/disabled 不算），首次静默修 3 次不好才 🆘。最该响那次（定时器卡死 3 天）只一条含糊 telemetry 异常→补 watchers。【已验证】
- **原子写 JSON**（tmp + os.replace）防读到半截；缓存过期停止显示旧快照不伪造新采样；document.hidden 时暂停轮询是有意省电非 bug。【已验证】
- Prometheus 零告警规则是有意设计（告警全靠 selfheal + tg-notify + 哨兵 + entry-failover），Grafana 只是仪表盘。**但这意味着没有独立告警基底，一条代码路径一个 TG 频道决定一切**——会持不同意见的第二信源有价值。【已验证】

## ② 原作者特定环境经验（标注依赖）
- **Contabo 监控中枢**（依赖：Prometheus/Grafana/node_exporter:9100/svcstatus:9101）：8/8 台全量 poll-fleet + Tailscale:9101 互监 + age 备份。【已验证】
- **外部哨兵 HK 备用哨兵机/近港入口机**（依赖：舰队外视角）：HK 备用哨兵机 扛 5 目标外部哨兵 + ts-watchers（唯一盯东京后端自己 watchers 的东西），2027-07-01 退役后无继任者（挂 8.5 个月）；交接排除最明显继任者 近港入口机（它托管 亚洲分区入口/自建 DERP/入口#1 自探无意义），伦敦机是唯一既在舰队外又不承担入口角色的候选。【已验证】
- **Mac mini M4 launchd 自愈**（依赖：macOS + Emby 原生 + Tailscale App）：Emby 探 /System/Info/Public 挂了 pkill + open -a；tailscale-health.sh 每 120s 验 BackendState=Running 且 WantRunning=true，异常打开 App + 不带参数 tailscale up 保留配置重连，CLI 外层硬超时，前三次失败后每 10min 静默重试不再永久 giveup，NeedsLogin/NeedsMachineAuth 只告警不自动改凭据。**打开 App 不等于连接 VPN**（M4 掉线复盘：旧脚本三次失败后永久放弃，重启也不清失败计数）。【已验证】
- **Mac 磁盘分级护栏**（依赖：内置 SSD 单 APFS 容器，填盘源=iCloud 下载原始）：WARN<120GB 预警/CRIT<45GB 清 emby cache/temp/EMERG<15GB 优雅停 Emby（SIGTERM 让 SQLite flush）+ 置 disk-emergency.flag，emby 自愈紧急期不重启（否则拉回满盘写坏 DB）/恢复 ≥160GB（滞回）清 flag 自动拉起；绝不 rm 照片/用户文件。【已验证】
- **OpenWrt busybox ash 引擎**（依赖：路由器 minimal）：探端口用 curl 连接阶段退出码（busybox nc 无 -z/-w，7=拒绝=DOWN 其它=UP 偏安全）；internet 探 ping 锚点 ICMP 不走 clash→ifup wan 重拨；dns 仅出网时判 nslookup→restart dnsmasq；flash /overlay≥90% 只告警不自动删（路由器删文件太危险写满变只读）。【已验证】
- **ntfy-subs 移动客户端宽限窗**（依赖：手机 NAT/省电重连）：瞬时 ESTABLISHED≥1 采样必然 flap（0↔1 秒级抖动）→改 15min（后 3600→21600s 旅行手机长断）宽限窗，「最近 N 分钟见过」才是正确信号。【已验证】

## ③ 需要重新验证的结论（给验证方法）
- **探针假阴性**：验证：直接复刻探针命令跑 45 次看失败率（曾 11% 全 rc=28 超时，每次失败后立刻重试 4/5 拿到 401=落地没挂是单采样假阴性）；日志/TG 带采样比 tcp=ok http=401 ok=2/3 一眼看出真挂还是抖。【已验证方法】
- **定时器卡死**：验证：OnCalendar 改后 daemon-reload + list-timers 看 NEXT 不是 elapsed；watchers 检查覆盖「监控的监控」第三层（HK 备用哨兵机 的 ts-watchers 没人盯）。【已验证：第三层缺失】
- **告警通道单点**：验证：主机 DNS 死时 TG 发不出（已用缓存 IP/--resolve/spool 修）；模拟 DNS 黑洞看 spool 补发。【已验证方法】
- **docker 慢被当死放大 outage**：验证：压测 load 下 docker ps 耗时 + cgroup churn（kworker D 态/PSI）；确认「连续 2 轮 ~4min」阈值不误判；daemon 重启必播报。【已验证：内核 -149 回归未证】
- **零重启 selector 真不掐连接**：验证：翻转多次看 MainPID 与 ActiveEnterTimestamp 全程不变；PUT 期望 204 且 .now==target；AI_RULE_MODE 必须 cfgout==selector 才走 API（否则规则直指成员 selector 被旁路，API 切换仍 204 但流量不动=静默失效）。【已验证方法】
- **流量归属准确性**：验证：token→用户名映射对账（authentication.db Tokens_2 ⋈ users.db）；未匹配 token 归「未识别」前 6；自用直连不计入。【已验证：.NET 混合端序 GUID 解码已修】

## ④ 来源文档路径清单
- 19-故障自愈-selfheal.md（架构 / 单次逻辑 / 护栏重启 / AI 回退 / 多采样多数决 / 零重启 selector / 三级四级粘滞 / 降噪 / 定时器自愈 / launchd 陷阱 / docker 慢）
- 20-建站规范-standard.md（A5 监控 / A6 自愈 / D 合规矩阵外部哨兵）
- 24-舰队网络与系统审计.md（延迟丢包矩阵 / 审计方法与可信度）
- 25-VPS-IP与网络质量测试.md（指标口径 / 测量源教训 / 中国吞吐）
- 44-全舰队体检-20260826.md、48-全面体检-20261015.md（telemetry/watchers / 降频 / 流量预警统一）
- 49-红队四审-20261017.md（监控的监控只两层 / 告警单通道 / 拱心石）
- 50-舰队巡检与Emby单域名-20261030.md（端到端健康 / 切换器）
- scripts/selfheal/（selfheal.sh / checks.*.sh / lib.cert-watch.sh / lib.external-watch.sh / singbox-ai-probe.sh / singbox-ai-selector.sh / mac/ / openwrt/）
- scripts/dashboard/（poll-fleet.sh / svcstatus-serve.py / cert-check.py / clash-stats.sh / nas_snapshot.py / snmp-nas.py / cloud-quota.py / quota_model.py / README）
- scripts/ops/tg-quota.sh、scripts/ops/svcstatus.sh、scripts/emby-relay/emby-traffic-agg.sh、reports/status-cadence-20261118.md、reports/status-watch-20261118.md
