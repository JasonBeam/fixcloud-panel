> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。

> 作者统一称「原作者」。示例一律用 example.com / 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24 / <EXAMPLE_TOKEN> 等文档示例值；机器以角色代称，不出现真实主机名/IP/域名/凭据/设备标识。【已验证】=实际读到/测到；【推测】=推断待核。

# 02 · Docker 与 systemd 运维

## ① 通用可复用经验

### 1. compose 规范（一份可复用的容器栈模板）
- **restart: unless-stopped** 全容器统一；常驻 systemd 服务用 Restart=on-failure，socat 类转发用 Restart=always。【已验证】
- **logging 全 json-file max-size=10m max-file=3**：防容器日志撑爆小盘。【已验证】
- **healthcheck**（wget 或 python urlopen）interval=30s timeout=5s retries=3 start_period=10-30s；依赖方用 depends_on: condition: service_healthy（如 caddy 等 authsvc 健康才起）。【已验证】
- **端口只绑 127.0.0.1**：仅入口容器（caddy 80/443）公网，其余（ntfy/smsbus/业务容器）全绑 127.0.0.1，经反代访问。【已验证】
- **资源限制**：mem_limit（如 ntfy 256m / smsbus 128m）+ cpus（0.5）防单容器吃满。【已验证】
- **机密不内联**：env_file 读 ./.env；必填项用 ${VAR:?set in .env} fail-closed（缺即报错不起，绝不用 changeme 默认值）。【已验证】
- **named volumes** 持久化（caddy_data/config、prometheus、grafana、authsvc 等）；extra_hosts: host.docker.internal:host-gateway 让容器访问宿主机服务。【已验证】
- prometheus retention.time=30d retention.size=2GB 双限；ntfy NTFY_AUTH_DEFAULT_ACCESS=deny-all + BEHIND_PROXY=true；grafana 匿名 Viewer + serve_from_sub_path + cookie samesite lax。【已验证】

### 2. systemd 单元设计陷阱
- **TimeoutStartSec 必设**：默认 infinity 时 dockerd 卡死会让整套自愈静默停摆零告警；设 300s。docker 原语（inspect/ps/exec）套 timeout 20，restart 套 90。【已验证】
- **Type=oneshot 子进程 cgroup**：KillMode=control-group 默认会收掉后台子进程（& 起的长任务），与 launchd AbandonProcessGroup 同源问题。同步执行的 service 不受影响。【已验证】
- **周期定时器一律 OnCalendar，别只用 OnUnitActiveSec**：后者在 daemon-reload 后会卡 elapsed 不再触发（曾 8 台 21 个定时器全卡 3 天，门户/DDNS/朋友下发全停）。【已验证】
- **定时器错峰 AccuracySec=1s**：防默认 1min 精度把多个 *:*:00 定时器合并回去齐射（齐射 + 高频容器 inspect 是 docker 慢的 churn 源）。【已验证】
- **docker 慢 ≠ 死**：unit 真死立即修；active 但探测超时 = 慢，连续 2 轮（~4min）才判失败，单轮只记日志。**daemon 重启必播报 TG**（全站容器中断 1-3 分钟）。旧检查 timeout 20 docker ps 单次超时 critical=1 → 首轮即 restart docker，8 容器全灭、daemon 高负载 3 分多才起，把慢放大成全站 outage。【已验证】
- **容器 task 泄漏**：容器 10s 没退被强杀 → containerd task already exists → 重启循环 Exited(128) 不自愈；重建前 rm -f 清泄漏 task。【已验证】

### 3. launchd 与 systemd 差异（macOS 侧）
- **launchd AbandonProcessGroup 默认 false**：主进程退出会 SIGKILL 整个进程组。selfheal 脚本 & 后台起 colima start（~50s），主脚本几秒退出 → 每轮 colima start ~3s 被杀，挂 10.5h 重试十几轮没生效。修：plist 加 AbandonProcessGroup true。**验证必须由 launchd 自己拉起**：launchctl kickstart gui/$(id -u)/... 观察 run end 后子进程是否活着。【已验证】
- 凡「定时任务 + & 后台长任务」都查这条（systemd Type=oneshot 同理）。【已验证】
- **Mac 定时重启用 pmset repeat restart**（原生可靠，能休眠唤醒），别用 launchd + osascript——headless 下 TCC 会拦，易静默失败。【已验证】
- LaunchAgent gui/501 每 120s；凭据 ~/bin/*.env（600）；用户态日志轮转用 LaunchAgent 代替 newsyslog（sudo 要密码），白名单 >10MB copytruncate 保尾 2MB（同 inode，launchd O_APPEND fd 安全）。【已验证】
- **NAS（群晖/QNAP）不加自动重启**：NAS 长在线设计，重启中断 qB 下载 + SMB。【已验证】

### 4. 日志轮转与磁盘
- **logrotate 包必装**（command -v 检测）：只放 /etc/logrotate.d 配置没装包 → 轮转从未跑（备份出口机 教训）。【已验证】
- sing-box logrotate daily rotate7 compress delaycompress missingok notifempty **copytruncate**（保 inode，进程不用重开 fd）。【已验证】
- journald SystemMaxUse 自动按盘大小（<8G→64M，否则 200M）+ SystemMaxFileSize=20M；删旧双层配置防打架；restart journald + vacuum。【已验证】
- 5G 小盘元凶：Debian 单内核 modules ~400M 叠加 5 代残留 + 1G swapfile → APT autoremove 旧内核 + swapfile 缩 512M。【已验证】

### 5. 备份与回滚
- **回退表分级**：config.json.lastgood（每轮校验通过才刷新）→ .selfheal.bak → ls -t /root/config.json.bak*。**无可用备份不盲目重启、不升级整机重启**，发一次 🆘。旧做法「覆盖→check→失败还原」中间一刻是坏的；改为「候选文件先 check 过了才覆盖」。【已验证】
- **ls -t bak* 混迁移前旧备份的风险**：损坏时可能悄悄恢复成没 reject/没 selector 的旧配置，安全洞重开。修：每轮断言不变量（私网 reject / tailnet-reject / selector 三项在位），缺了 🆘 指明重跑哪个脚本。【已验证】
- **age 公钥加密备份**：私钥只存本机 0600 + iCloud，绝不进 Git；.gitignore 阻止明文 .tgz/.env/*.age.key 再提交；收件公钥 .age-recipients。**git 历史不可逆，现在处理比以后便宜**。【已验证】
- **恢复禁盲解覆盖运行环境**：重建节点别直接 tar xzf /etc/sing-box 覆盖（会静默重开已修好的洞）；按规范用安装脚本幂等重装跑通 assert_invariants，再从解密包提取不可再生凭据/规则/单元。【已验证】
- 备份新鲜度推送门户（>30 天自动亮灯）；单次 SSH 打包流式回传 + 指数退避重试 + gzip -t 校验 + age 加密。【已验证】
- **备份排除机密通配符**：config.json.* / zz-resi.json.*（防 .lastgood 泄密）；derper 证书私钥要备，25MB 二进制可再生不备。【已验证】

### 6. docker 网络与防火墙
- docker 发布端口绕 ufw → DOCKER-USER 链 DROP + 持久化 service；daemon restart 重建链，开机 service 只跑一次需手动 restart（整机重启不受影响）。【已验证】
- 公网只经入口机架构：后端机 80/443 被 DOCKER-USER 封死，只收 tailnet；入口机经 tailnet 反代后端。【已验证】

## ② 原作者特定环境经验（标注依赖）
- **Contabo 7 容器 dashboard 栈**（依赖：docker compose + Caddy 入口 + authsvc 登录墙）：caddy/authsvc/smsbus/classnet/prometheus/grafana/ntfy，全 healthcheck healthy，端口只 caddy 公网。【已验证】
- **Mac mini M4 launchd 自愈**（依赖：macOS + colima/lima VM + Emby 原生 App）：selfheal-mac.sh 每 120s；Emby 挂了 pkill + open -a（~4s 复活）；colima start 需 AbandonProcessGroup；icloud-archive/immich 各 plist。【已验证】
- **OpenWrt procd/init.d + busybox ash**（依赖：路由器 minimal 环境）：与 systemd 版分开，不能共用引擎；busybox ash 无 bash-ism；调度 busybox cron + flock 防重叠；日志/状态全走 /tmp（tmpfs）零 flash 磨损；重启戳落 /etc/selfheal。【已验证】
- **233boy sb 包装脚本坑**（依赖：用 233boy 安装脚本）：/usr/local/bin/sing-box 是 bash 包装（symlink→sh/），kill $! 只杀包装、真二进制成孤儿继续监听；临时起 sing-box 直接调 /etc/sing-box/bin/sing-box，收尾 pkill -f "<cfg>"（pattern 加 [.] 否则把自己 ssh 会话一起杀）。【已验证】
- **OpenWrt 无真硬件看门狗**（依赖：iKOOLCORE 路由）：实测无 /dev/watchdog、lsmod 无 wdt、procd watchdog offline、opkg 无 watchcat → 真内核 panic 自愈不了（cron 一起冻），只能靠双周 cron 重启兜底（最坏 ~14 天瞎）。【已验证】

## ③ 需要重新验证的结论（给验证方法）
- **healthcheck 真实反映业务**：验证：healthcheck 探业务端点（如 /System/Info/Public 拿 Version）而非只看端口活；手动停业务但留端口，看 healthcheck 是否转 unhealthy。【推测：端口活 ≠ 业务可用】
- **定时器 OnCalendar 改后真触发**：验证：daemon-reload 后 systemctl list-timers 看 NEXT/LEFT 不是 elapsed；等一个周期看 journal 有无触发。【已验证方法，改后必跑】
- **launchd 后台长任务存活**：验证：launchctl kickstart 后观察 run end 之后 colima start/limactl 是否活着（ps）；别只在终端手动跑脚本验证。【已验证方法】
- **docker 慢判定阈值**：验证：压测 load 下 docker ps 耗时，确认「连续 2 轮 ~4min」不误判慢为死；观察 cgroup churn（kworker D 态 css_release_work_fn / PSI cpu some）。【推测：内核 6.8.0-149 回归未证，复发 grub 回退 -147 对照】
- **备份幂等重建**：验证：三个安装脚本能否幂等重建全部配置（含 harden/resi/selector 规则）尚未验证 = 加密备份方案的先决条件；在干净机跑安装脚本 + assert_invariants，再对比解密包差异。【已验证：此先决条件未核】
- **conntrack/UDP GRO 重启存活**：验证：重启后 cat nf_conntrack_max、ethtool -k dev | grep rx-udp-gro-forwarding。【已验证方法】

## ④ 来源文档路径清单
- 20-建站规范-standard.md（B 新服务 systemd/docker 规范 / A7 韧性）
- 19-故障自愈-selfheal.md（launchd AbandonProcessGroup 陷阱 / docker 慢被当死 / 回退表 / 定时器自愈）
- 24-舰队网络与系统审计.md（socat TasksMax / docker 绕 ufw / 手动重启验证）
- 44-全舰队体检-20260826.md（MC 备份超时静默杀死 / pigz / 用户态日志轮转 LaunchAgent）
- 48-全面体检-20261015.md（OnCalendar 回溯 / networkd-wait-online 自愈 / 内核 autoremove）
- 49-红队四审-20261017.md（备份层双向死锁 / 配置包冻结 43 天）
- backups/dashboard/docker-compose.yml（7 容器栈规范）
- scripts/ops/apply-baseline.sh、scripts/ops/scheduled-reboot.timer、scripts/ops/journald-cap.conf、scripts/ops/sing-box.logrotate
- scripts/selfheal/install.sh、scripts/icloud-archive/（plist + sh）、CHANGELOG.md（1124 age 加密 / 1116 原子写 / 1022 磁盘整治）
