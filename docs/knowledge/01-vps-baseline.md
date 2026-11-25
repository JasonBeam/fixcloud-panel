> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。

> 作者统一称「原作者」。示例一律用 example.com / 192.0.2.0/24 / 198.51.100.0/24 / 203.0.113.0/24 / <EXAMPLE_TOKEN> 等文档示例值；机器以角色代称，不出现真实主机名/IP/域名/凭据/设备标识。【已验证】=实际读到/测到；【推测】=推断待核。

# 01 · VPS 建站与安全基线

## ① 通用可复用经验

### 1. 系统初始化（每台新 VPS 同一套标准，做完在合规矩阵打勾）
- **干净重装** Debian 12 / Ubuntu 24.04，不在厂商脏镜像上叠加。【已验证】
- **时区 + NTP**：时区统一 Asia/Shanghai，NTP 必开。时钟漂移会直接破坏 REALITY/TLS 握手（握手对时间敏感）。【已验证】
- **swap 策略**：1 核小鸡加 1G swap（swappiness=10），大机 2G；小盘机用 512M swapfile 即可，别用 1G 顶满小盘。【已验证】
- **BBR + fq**：原版 BBR 即可，别碰 BBRplus/锐速/换内核——好线路上无收益，换内核有崩机风险。【已验证】

### 2. 网络内核调优（核心认知：服务端调优只能在线路天花板下把单流跑满，不能突破国际出口/晚高峰拥塞/客户端最后一公里）
- **TCP 缓冲区 LFN 调优是头号杠杆（数量级收益）**：rmem/wmem max 按 BDP=带宽×RTT 估算（如 2.5G×150ms≈47MB），解除单流默认 ~330Mbps 封顶。但**不是越大越好**：1G 小机取 8MB，顶格 16MB/socket 会被 tcp_mem 全局硬顶（如 38MB）放大成 memory pressure。【已验证】
- tcp_moderate_rcvbuf=1、slow_start_after_idle=0、notsent_lowat=131072、mtu_probing=1、somaxconn/backlog 提高。【已验证】
- **tcp_fastopen=0**：TFO 有 GFW 指纹 + 中间盒风险，主动关掉。【已验证】
- **conntrack ≥65536 三件套**：modules-load.d/nf_conntrack.conf + sysctl nf_conntrack_max + modprobe.d hashsize。**必须先写 modules-load.d 再设 sysctl**，否则开机 systemd-sysctl 跑在模块加载前、该键不存在被跳过，重启静默回落内核默认（8192/4096），事后极难定位。established 超时用 86400（tcp_loose=0 时 7200 太激进，过期表项无法 mid-stream 重建）。【已验证】
- 代理强制 **IPv4 优先出站**（IPv6 回程烂时联通 440ms vs IPv4 CN2GIA 150ms）：sing-box 用 dns.servers=[local] + route.default_domain_resolver={server:local,strategy:prefer_ipv4}（1.13 新写法，旧出站 domain_strategy 已废弃会 FATAL）。**不要在系统层关 IPv6**（sing-box 监听 ::，关栈重启绑不上→节点挂，尤其有每周自动重启）。【已验证】

### 3. 防火墙与最小权限
- **ufw default-deny**，只放 SSH + 服务口 + allow in on tailscale0。出站默认全放（代理/DDNS 需要），返回流量靠 conntrack established 自动放行，无需开临时口。【已验证】
- **封出站 TCP 25**：自建节点头号现实风险是被滥用发垃圾邮件→机房 abuse 封鸡。【已验证】
- 改/加代理端口要**同步 ufw allow**，否则连不上；SS 默认 tcp+udp，只放 tcp 会「TCP 通 UDP 全黑」静默失败，要 UDP 就 allow 口/udp。【已验证】
- **docker 绕 ufw**：docker 发布端口绕过 ufw，要在 DOCKER-USER 链封 + 持久化 service。坑：docker daemon 中途 restart 会重建 DOCKER-USER 链，开机只跑一次的 service 需手动 restart。【已验证】
- 仅内网服务绑 127.0.0.1 / tailnet，监控口绝不暴露公网。【已验证】

### 4. fail2ban + 自动更新
- fail2ban 用 **systemd 后端 sshd jail**；bantime.increment=true 累进封禁（maxtime=1w）；**ignoreip 必含 127.0.0.0/8 + 100.64.0.0/10（tailnet 段）**，否则监控/自愈从 tailnet 探 22 会被自己封（防自锁）。非标 SSH 端口要改 jail.d/port.local 的 action port。【已验证】
- unattended-upgrades 自动安全补丁**不自动重启**；**内核元包要装**（如 linux-image-cloud-amd64），否则内核冻结、U-U 天天「无可升级」；Allowed-Origins 要含 -updates 池，否则内核卡住。【已验证】

### 5. SSH key-only（厂商 drop-in 是最大的坑）
- 装 fleet 公钥 + 关密码与 root 密码登录；**sshd -t 校验后 reload**（不断现有连接），再开新连接实测。救援后路 = 面板 VNC + root 密码。【已验证】
- **厂商 drop-in 坑**：部分厂商 Debian 镜像出厂带 sshd_config.d/*.conf 默认开 password+root，直接改主 config 被字典序压过。解法：加 00-00-fleet-hardening.conf（排序最前）+ 中和厂商 drop-in + cloud.cfg.d/99-disable-ssh-pwauth.cfg 防 cloud-init 重启再开。验证用 sshd -T | grep -i passwordauthentication 看实际生效值，别只看主 config。【已验证】
- 回滚备份 *.pre-harden.bak；authorized_keys 复核仅合法 fleet key 无后门。【已验证】

### 6. 端口规划与接入
- 代理用**高位随机口降扫描**；监控/互监一律探 Tailscale:9101，**绝不探公网代理端口**（防公网握手噪音 + 防 fail2ban 封家宽）。【已验证】
- SSH 别名 + Tailscale 入网记 tailnet IP；DDNS + 域名（CF 灰云 A + cf-ddns.timer）；TLS 首选真证书 certbot dns-cloudflare（复用 CF token，不用开 80 口）+ deploy-hook 续期重启。自签是例外，须①客户端 skip-cert-verify ②文档写原因 ③记合规矩阵。【已验证】

### 7. 韧性与日志/磁盘护栏
- **每周日凌晨错峰重启**（8 台 04:30→06:00 各错 15min）：清内存 + 吃内核补丁；低峰 + selfheal 兜底影响极小；所有服务开机自启。【已验证】
- sing-box access.log 默认无上限（曾 454M 撑爆小盘）→ logrotate daily×7 compress copytruncate；journald SystemMaxUse 封顶（<8G 小盘 64M，常规 200M）。**logrotate 包必装**，只放 /etc/logrotate.d 配置没装包→轮转从未跑。【已验证】
- 磁盘护栏随 selfheal：根分区 ≥90% 自动 journalctl --vacuum + 截断 >100M 日志 + 告警，回落 <85% 发恢复。小盘机阈值改 80%（90% 才清≈剩 490MB 太晚）。【已验证】
- APT 自动清旧内核（Remove-Unused-Kernel-Packages/Dependencies=true），防 5G 小盘被 5 代残留内核 + modules（单内核 ~400M）顶满。【已验证】
- 配置纳入 age 加密备份；文档四件套（README 表行/密码登记/节点文档/续费提醒）。【已验证】

### 8. 供应商选择取舍（延迟 ≠ 吞吐，地理近 ≠ 晚高峰快）
- **回程线路是判据**：三网精品（电信/联通 CN2 GIA + 移动 CMIN2）适合主力代理；普通 163/4837/CMI 即使地理近（HK）晚高峰也崩。marketing 名「精品」要 backtrace 实锤，名不副实常见。【已验证】
- **明文 HTTP 测速伪象（核心教训）**：晚高峰明文 HTTP 下载可被透明代理/DPI 降速到 ~10KB/s（对 off-peak 6.6MB/s ≈600× 塌陷），同 IP 同峰值走 SSH 加密通道 6-7MB/s。**峰值吞吐必须走加密通道（SSH/代理）量**，别信明文 HTTP。TCP 22 握手 2.3ms < ping 12ms 印证 TCP 前置终结中间盒。【已验证】
- **中国吞吐权威口径**：源 = 有线 Mac mini（openssh 硬件 AES，dropbear/dbclient 卡 2-4Mbps 假象）；8 并发加密流（单流欠采×3-5）；box→China 下行；每箱 connect 核验直连剔除 tailnet/代理污染。三铁律：加密通道、直连源、多连接。【已验证】
- **测量源教训**：量延迟只信光纤边缘（OpenWrt/有线 Mac mini），别信笔记本（WiFi 抖动 + clash tun 到阿里 DNS 都 56ms±14 假象；OpenWrt 到阿里 DNS 5.5ms 才是真广东电信）。先验源侧（网关/锚点），别拿被污染样本给远端下结论。【已验证】
- **换 IP 免死金牌**：搬瓦工每两周免费换 IP 是大流量 DDoS/频封的逃生口（1Gbps 小机扛不住 DDoS）。换 IP 后 DDNS 跟上，客户端无需改。【已验证】
- **IP 风险评分口径差异**：同一 IP 不同库判法不同（Scam75 高但 IP2Loc0/Abuse0，落地影响有限；IP2Loc99 高但 Scam2 干净）。住宅 IP 纯度 > 静态 ISP > 机房，AI/流媒体解锁挑出口。【已验证】
- 低延迟 HK 地理线适合网站入口/回国中转（流量小），不适合大吞吐代理；CN2 GIA 物理远（~160ms）但晚高峰稳，适合主力。【已验证】

## ② 原作者特定环境经验（标注依赖）
- **8 台舰队角色分工**（依赖：原作者多机舰队 + Tailscale 组网）：主力 US 精品出口（搬瓦工，换 IP 免死金牌 + 2TB 配额）、住宅 AI 落地（LisaHost 西雅图，单租户真住宅纯度最高）、算力/监控中枢（Contabo 东京，6C/12G 性价比无对手但亚洲 peering 烂）、HK 入口（精品 CMI 三网 ~10ms）、东京网站后端（唯一 Caddy 终结 TLS）、UK 备份 + 哨兵（Akko 伦敦，三网精品这价格无第二台）、JP 中转（VMISS 东京，性价比之王）。【已验证】
- **搬瓦工 2TB 配额用尽直接关机 ~41h 事故**（依赖：主力出口机 集中承载主出口 + 订阅服务器 + 朋友 Emby 中转 + 凭据管理）：日均 ~70GB 峰值 175GB，朋友占 342.8GB。每小时配额预测器 + 速率外推提前 6 天告警（做得对），但「提前 6 天要做什么」的 runbook 未写、需求侧杠杆（限朋友版/分流到 UK/HK）仍开着。【已验证】
- **具体 vendor 取舍**（依赖：原作者实测）：Evoxt 联通 305ms 短板（电信 84 移动 79，回程联通绕 4837 崩）→降备用；LisaHost 西雅图两月三次宿主故障（RCU stall 93s / virtio_net TX timeout 硬重启 / 上游第 3 跳丢包 17h）工单未开；Contabo 亚洲 peering 烂（近港入口机→Contabo 154ms 跨太平洋，但→VMISS 东京 57ms 正常）只适合算力不适合中转；DMIT 已退租且贵、RackNerd 普通线晚高峰炸。【已验证】
- **IPRoyal 静态 ISP 作 AI 二/三级落地**（依赖：0916 住宅落地机 单点丢包暴露）：一 IP 绑一源机（第二台 403 先到先得）；明文 HTTP 代理国内不能直连（CONNECT+TLS SNI 明文过墙被重置）；AS3257/AS3561 骨干运营商非真住宅，纯度不如 住宅落地机 排其后；300GB/月计量，客户端别当普通节点直连，用服务端专用入站钉死出站（凭据永不离开服务器）。【已验证】

## ③ 需要重新验证的结论（给验证方法）
- **TCP 缓冲最优值依线路 BDP**：别照抄 8MB/128MB。验证：每周 nstat 看 PruneCalled/TCPMemoryPressures 修剪计数增速，求收敛不求归零（部分修剪是快收慢发固有自保）；ss -tin 看单流 cwnd/rtt 估 BDP。【推测：最优值随线路/内存变化】
- **conntrack 重启存活**：验证：重启后 cat /proc/sys/net/netfilter/nf_conntrack_max 应 ≥65536；ls /etc/modules-load.d/nf_conntrack.conf 存在。【已验证方法，新机器需重跑】
- **厂商 drop-in 是否真关**：验证：sshd -T | grep -iE 'passwordauthentication|permitrootlogin' 看实际生效值，别只看主 config；新厂商镜像装机后必查。【已验证方法】
- **晚高峰吞吐**：验证：21-23 点用有线源 + openssh + 8 并发加密流 + 直连（--noproxy 排除系统代理），多日复测；别用单次/明文/WiFi 笔记本。【已验证方法】
- **IP 风险评分**：验证：多库交叉（Scam/IP2Loc/Abuse/ipapi/IPQS），别信单库；住宅落地用 ip.sb 看出口 IP 是否本机。【已验证方法】
- **每周重启是否真吃内核补丁**：验证：重启后 uname -r 对比 apt list --installed linux-image；U-U 是否含 -updates 池。【推测：需逐机核】

## ④ 来源文档路径清单
- 20-建站规范-standard.md（A1-A7 基线 / B 新服务 / C 约定 / D 合规矩阵）
- 09-安全加固.md（威胁现实 / 防火墙 / SSH key-only / 定时重启 / 日志磁盘 / 网络提速）
- 24-舰队网络与系统审计.md（conntrack 三件套 / TCP 缓冲 / socat TasksMax / SS-UDP / docker 绕 ufw / fail2ban 累进）
- 25-VPS-IP与网络质量测试.md（IPQuality/NetQuality 读表 / 明文 HTTP 伪象 / 中国吞吐口径 / 测量源教训）
- 26-2027续费精简规划.md（供应商取舍 / 成本年化 / IPRoyal / Contabo 不升不迁）
- 05-部署进度清单.md（sing-box 裸核不上面板 / SSH 专用密钥 / 住宅验货）
- 44-全舰队体检-20260826.md、48-全面体检-20261015.md（journald 封顶 / 内核 autoremove / conntrack 漂移）
- scripts/ops/apply-baseline.sh（幂等一键 8 件）、scripts/ops/fleet-baseline/、scripts/ops/scheduled-reboot.timer、scripts/ops/journald-cap.conf、scripts/ops/sing-box.logrotate
