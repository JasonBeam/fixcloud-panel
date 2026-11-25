# homelab fork-clone「危险自动化与外联」只读审计报告

- 审计对象:`/Users/beamjason/Documents/GitHub/homelab-sanitize/fork-clone`(JasonBeam/homelab,Private,fork 自 JimmyChan233/homelab)
- 仓库状态【已验证】:单分支 main,443 commits,442 跟踪文件,0 tag,工作区干净;origin fetch=https://github.com/JasonBeam/homelab.git,push=no_push_disabled(已禁推);当前无任何 CI 文件。
- 审计方式:只读(read/cat/ls/git log/git show/git ls-files/grep/stat/plistlib 解析/python 只读结构解析);未执行仓库内任何脚本/plist/安装器,未发起任何网络请求,未修改仓库任何文件。
- 脱敏约定:本报告不含任何真实凭据值与真实地址。占位符:`＜AUTHOR_HOME＞`=原作者家目录、`＜AUTHOR_DOMAIN＞`=作者真实域名、`＜AUTHOR_BOT＞`=作者 Bot handle、`＜PUB_IP＞/＜CGNAT_IP＞/＜LAN_IP＞`=真实公网/tailnet/内网 IP、`＜SUB_TOKEN＞/＜MP_TOKEN＞`=订阅路径 token/MoviePilot token、`＜EMAIL＞`=真实邮箱。示例值一律用 example.com / 192.0.2.1 / 203.0.113.7 / `＜REDACTED_PASSWORD＞`。sha8=本人对敏感值生成的 sha256 前 8 位(仅用于去重定位,不可逆)。
- 证据分级:【已验证】=实际读到/解析到;【推测】=由注释/README/命名推断,未实机核实。

## 一、摘要

- 危险项总数:**148 项**(主表行数;一行可代表同组多文件)。按风险级:**P0=82 / P1=33 / P2=33**。
- launchd:**21 个 plist 文件**(Label 全部含作者名 jimmy/jimmycloud,需替换;ProgramArguments 全部指向原作者家目录绝对路径,克隆内对应脚本在仓库相对路径)+ 6 个内联生成/被引用但仓库缺失的 Label + 1 个历史已删除 Label。
- systemd:**23 个 .service + 14 个 .timer + 6 个 .conf**(含 nginx/stream 配置与 timer drop-in);另有 **9 条 cron/任务计划**触发(OpenWrt crontab、Mac cron、群晖 DSM 任务计划)。
- CI:**0**(全历史从未添加任何 GitHub Actions/GitLab CI/Jenkins/CircleCI/Drone/Woodpecker/Azure/Travis/Buildkite 文件,git log --all --diff-filter=A 取证)。
- 历史已删除自动化:scripts/mc/ 9 文件(commit 5bed1c3,2026-10-14,MC 服下线)+ scripts/emby-relay/com.<ORIGINAL_AUTHOR>.emby-hub-watch.plist(commit 1d599d4,2026-11-16)。
- 加密配置备份:**9 个 backups/*-config-backup.tgz.age**(akko/bwg/contabo/hklisa/hkrelay/istoreos/jprelay/lisa/malaysia),内含舰队 /etc 密钥;age 私钥在 git 外(.age-recipients 仅公钥)。
- 凭据暴露面:00-密码总表.md(271 行/137 表行,全类型凭据)为最高优先脱敏对象;全仓扫描 unique 指纹:email 26、http_url 459、ipv4 179(公网 138/内网 18/CGNAT 23)、long_b64 90、long_hex 46、uuid 38、sub_url 6、token_kv 8、phone_cn 2。
- 外联目标类型(不含真实地址):Telegram Bot API(全舰队告警出口)、Cloudflare DNS API(4 个写脚本)、作者 9 台 VPS+家里路由+群晖(SSH 别名 contabo/m5/syno/bwg/akko/lisa/jprelay/hklisa/hkrelay/istoreos)、家里 Emby/Immich/MoviePilot、AI API(MiniMax/Qwen/Kimi/Gemini/Claude/Codex)、GitHub releases、OpenSubtitles、TMDB、BWG KiwiVM、IPRoyal 住宅代理、astral uv 安装脚本(远程管道安装)。
- 矛盾点【已验证】:scripts/agent-panel/README 宣称 2026-11-23 AI Hub 下线后「Zero launchd daemons」,但 scripts/agent-panel/ 仍存 push/usage/plan-usage 三个现役 plist(RunAtLoad+定时),归档目录还保留 5 个 KeepAlive/定时 plist。

## 二、风险级定义

- **P0(会自动外联/部署)**:具备自动触发器(launchd RunAtLoad/KeepAlive/StartInterval/StartCalendarInterval、systemd timer/Restart=always/开机 oneshot、cron、compose restart、agent hook),或安装器会把上述自动触发写入用户环境;一旦部署/装机即无人值守外联、自动重启服务/整机、写 DNS/防火墙、自动部署更新。
- **P1(需凭据才可运行)**:手动触发,但执行即连接作者基础设施/外部 API(SSH 别名、TG token、CF token、AI key、Emby/Immich 账号等),或写入用户环境配置;无自动触发器。
- **P2(仅本地只读/离线)**:本地采集、离线测试、纯模板/文档、本地 serve;不自动外联。注意:P2 文档仍可能含真实凭据(数据暴露另行标注)。

## 三、主表(路径相对 fork-clone 根)


### scripts/ 告警出口

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/tg-notify.sh | 脚本(部署到全舰队 /usr/local/bin) | 被 selfheal/pollers 自动调用 | TG sendMessage(bot token+chat id 取自 /etc/tg-notify.env);DNS 死时 --resolve 公网 IP 兜底;curl cloudflare trace 探出口 IP | TG bot token+chat id | P0 | 占位符化(保留状态机去重设计) |

### scripts/agent-panel(现役)

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/agent-panel/push-to-contabo.py + com.<ORIGINAL_AUTHOR>.agent-panel.push.plist | launchd+脚本 | RunAtLoad+StartInterval=120 | ssh contabo(BatchMode)执行内联 python 写 /opt/svcstatus/{usage,plan-usage,m5}.json;采集 hostname/CPU/内存/磁盘/uptime/launchctl list(:145-220,:236-248) | SSH 别名 contabo 密钥 | P0 | 删 plist;脚本 ssh 目标占位符化 |
| scripts/agent-panel/usage-collector.py + com.<ORIGINAL_AUTHOR>.agent-panel.usage.plist | launchd+脚本 | RunAtLoad+StartInterval=600 | 并行采集 6 家 CLI 配额/日志→~/.agent-panel/usage.json;launchctl print/kickstart plan-usage(:157,163) | 各 CLI OAuth | P0 | 删 plist;保留采集设计 |
| scripts/agent-panel/plan-usage.py + com.<ORIGINAL_AUTHOR>.agent-panel.plan-usage.plist | launchd+脚本 | RunAtLoad+StartInterval=1800 | qianwen CLI subscription status→plan-usage.json | qwen OAuth | P0 | 删 plist |
| scripts/agent-panel/router.py | 脚本 | 手动/import | 本地配额瀑布选择;非 m5 主机 ssh m5 cat ~/.agent-panel/usage.json 写缓存(:908-929) | SSH 别名 m5 | P1 | ssh 回落占位符化 |
| scripts/agent-panel/control.py | 脚本 | 手动/import | 本地 CLI 编排(ACP stdio;mmx --max-tokens 12288);无直接 ssh/curl | CLI OAuth | P1 | 仅保留设计思想 |
| scripts/agent-panel/agent-relay.py | 脚本 | MCP stdio 手动 | 拉起 6 家官方 CLI 子进程;宣称不向云端上报 | CLI OAuth | P1 | 仅保留设计思想 |
| scripts/agent-panel/install-mcp.py | 安装器 | 手动 | 写 ~/.claude.json、~/.codex/config.toml [mcp_servers.agent-relay]、~/.gemini mcp_config(+antigravity 变体) | 无 | P1 | 删除或改 dry-run |
| scripts/agent-panel/cutover-to-m5.sh | 安装器 | 手动 | 装 LaunchAgents+launchctl bootstrap/bootout com.<ORIGINAL_AUTHOR>.agent-panel.*;curl -x 代理 cloudflare trace | SSH/代理 | P0 | 删除 |
| scripts/agent-panel/sync_leaderboard.py | 脚本 | 手动 | curl 外部榜单 HTML(UA 伪装,:75);写 ~/.codex/models_cache.json+~/.qwen/settings.json(:497,512,513) | 无 | P1 | 删除外联与用户配置写入 |
| scripts/agent-panel/kimi-quota.py | 脚本 | 手动 | curl Kimi API Bearer(key 自 ~/.agent-panel/kimi-quota.key) | Kimi API key | P1 | 占位符化 |
| scripts/agent-panel/gemini-usage.py、claude-plan-usage.py、claude-usage-report.py、codex-usage.py、usage-collector.sh | 脚本 | 手动/cron 10min | 本地 CLI 配额/日志采集(gemini 临时 --settings 注入) | CLI OAuth | P1 | 保留设计;去除 cron 部署注释 |
| scripts/agent-panel/quickcmd.py | 脚本 | 手动 | curl 本机 :9102/healthz | 无 | P2 | 保留 |
| scripts/agent-panel/models.json、test_*.py | 配置/测试 | 无 | 模型目录/离线 mock | 无 | P2 | 保留 |

### scripts/agent-panel/archive/20261123-ai-hub(已退役但仍在库)

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/agent-panel/archive/20261123-ai-hub/receiver.py + com.<ORIGINAL_AUTHOR>.agent-panel.receiver.plist | launchd+脚本 | RunAtLoad+KeepAlive | HTTP :9102 守护;control.token/HMAC cookie 鉴权;创建 worktree | control.token | P0 | 整目录删除(已退役) |
| scripts/agent-panel/archive/20261123-ai-hub/tg-hub.py + com.<ORIGINAL_AUTHOR>.agent-panel.tghub.plist | launchd+脚本 | RunAtLoad+KeepAlive | 专用 TG Bot;PUBLIC_HUB_URL 默认作者域名 /hub/;tailscale pair 链接;/login 远程重登 | TG bot token+chat 白名单 | P0 | 删除 |
| scripts/agent-panel/archive/20261123-ai-hub/tg-push.py + com.<ORIGINAL_AUTHOR>.agent-panel.tgpush.plist | launchd+脚本 | RunAtLoad+StartInterval=30 | 正则从 config 提取 bot token→TG sendMessage;receiver attention | TG token(config 内) | P0 | 删除 |
| scripts/agent-panel/archive/20261123-ai-hub/autoloop.py + com.<ORIGINAL_AUTHOR>.agent-panel.autoloop.plist | launchd+脚本 | RunAtLoad+StartInterval=180 | TG sendMessage+receiver POST+router failover | TG token+control.token | P0 | 删除 |
| scripts/agent-panel/archive/20261123-ai-hub/summaries.py + com.<ORIGINAL_AUTHOR>.agent-panel.summaries.plist | launchd+脚本 | StartInterval=300 | receiver new/input/events/stop;mmx 摘要(烧配额) | control.token+mmx | P0 | 删除 |
| scripts/agent-panel/archive/20261123-ai-hub/install-hooks.py | 安装器 | 手动 | 合并 hooks 进 ~/.claude/settings.json、~/.codex/hooks.json、kimi config.toml、~/.gemini/settings.json(先 backup) | 无 | P0 | 删除(安装自动外发 hook) |
| scripts/agent-panel/archive/20261123-ai-hub/bridge-hook.sh、codex-notify-wrapper.sh | hook | 自动(agent 事件) | stdin→curl POST receiver(max-time 2 后台) | control.token | P0 | 删除 |
| scripts/agent-panel/archive/20261123-ai-hub/orchestrator.py | 脚本 | 手动 | Gemini brain Goal Spec+codex review;worktree | CLI OAuth | P1 | 仅保留设计思想 |
| scripts/agent-panel/archive/20261123-ai-hub/reauth.py | 脚本 | 手动 | 6 家 CLI OAuth 重登(localhost 回调) | OAuth | P1 | 仅保留设计思想 |
| scripts/agent-panel/archive/20261123-ai-hub/delegate-run.sh、ai-dispatch.py、scavenger.py | 脚本 | 手动/门控 | curl POST receiver(delegate/events/stop);SCAVENGER_ENABLED=1 门控 | control.token | P1 | 删除 |
| scripts/agent-panel/archive/20261123-ai-hub/transcript.py | 脚本 | 手动 | 读 ~/.claude/projects/*.jsonl+~/.codex/sessions(本地隐私) | 无 | P2 | 删除(隐私) |
| scripts/agent-panel/archive/20261123-ai-hub/web/index.html、web/app.js | 配置 | 手动 | AP_TOKEN 模板注入;含作者 Bot handle 标识 | control.token | P2 | 标识占位符化 |

### scripts/dashboard

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/dashboard/poll-emby-relays.sh + .service/.timer | systemd+脚本 | timer 30s | GET 4 中转+家 Emby /System/Info/Public(免鉴权) | 无 | P0 | URL 占位符化 |
| scripts/dashboard/poll-emby-usage.sh + .service/.timer | systemd+脚本 | timer 60s | 拉 mac :9101/emby-tokens.json+4 中转 emby-traffic.json;7 日归档 | 无(tailnet 公开文件) | P0 | 占位符化 |
| scripts/dashboard/poll-fleet.sh + .service/.timer | systemd+脚本 | timer 30s | 8 节点 services.json+MoviePilot statistic?token= | MP token | P0 | 占位符化 |
| scripts/dashboard/poll-web.sh + .service/.timer | systemd+脚本 | timer 60s | 内网/tailnet web 探测(-k)+MP token | MP token | P0 | 占位符化 |
| scripts/dashboard/poll-extras.sh | 脚本 | 手动(注释 15s,无 unit) | Emby api_key Items/Sessions/ActivityLog+mac+owrt CGI | EMBY key | P1 | 占位符化 |
| scripts/dashboard/clash-stats.sh | 脚本 | 手动 | OpenClash API /connections /memory Bearer | CLASH_SECRET | P1 | 占位符化 |
| scripts/dashboard/cloud-quota.py + cloud-quota-minute.conf/cloud-quota-balanced.conf | systemd drop-in+脚本 | 每分钟/每 5 分钟 | MiniMax /v1/token_plan/remains | MINIMAX_API_KEY | P0 | 占位符化 |
| scripts/dashboard/sync-minimax-key.sh→sync-minimax-key.py | 脚本 | 手动 | MiniMax remains→写 /opt/dashboard/cloud-quota.env;ssh contabo(:70) | MINIMAX key+SSH | P1 | 占位符化 |
| scripts/dashboard/snmp-nas.py | 脚本 | 手动(注释 timer 2min) | SNMP walk syno/qnap | SNMP community | P1 | 占位符化 |
| scripts/dashboard/svcstatus-serve.py | 脚本 | 手动 | HTTP :9101 serve bootstrap.json | 无 | P2 | 保留 |
| scripts/dashboard/cert-check.py、nas_snapshot.py、quota_model.py | 脚本 | 手动 | 本地证书到期/快照/配额模型 | 无 | P2 | 保留 |
| scripts/dashboard/homelab-pollers.env.example | 模板 | 无 | MP_TOKEN/CLASH_SECRET=CHANGE_ME | 无 | P2 | 保留 |
| scripts/dashboard/README.md、test-*(6 个) | 文档/测试 | 无 | 含 scp+systemctl 部署命令;test-poll-fleet-web.sh fixture 含作者域名(mock curl 离线) | 无 | P2 | 文档/fixture 域名占位符化 |

### scripts/emby-relay

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/emby-relay/emby-failover.sh + emby-failover.timer | systemd+脚本 | 每分钟 | CF DNS A 记录按优先级故障切换写;tg-notify | CF API token(自 /etc/letsencrypt/cloudflare.ini) | P0 | 占位符化 |
| scripts/emby-relay/emby-evac.sh | 脚本 | OpenWrt cron */2 | CF DNS 写+cloudflare trace+hub 心跳 /emby-failover.json+tg-notify | CF token(/etc/entry-failover.env) | P0 | 占位符化 |
| scripts/emby-relay/emby-upstream-reload.sh + timer | systemd+脚本 | 5min Persistent | 解析家 DDNS→/etc/hosts 别名;nginx reload/start | 无 | P0 | 占位符化 |
| scripts/emby-relay/emby-traffic-agg.sh + timer | systemd+脚本 | 1min | nginx 日志→emby-traffic.json 本地聚合 | EMBY_HASH_SALT 可选 | P2 | 保留 |
| scripts/emby-relay/emby-hub-watch.sh | 脚本 | 手动(launchd 已移除) | ssh contabo curl 60MB 家 Emby | SSH 别名 | P1 | 占位符化 |
| scripts/emby-relay/emby-egress-peaktest.sh | 脚本 | 一次性 launchd | ssh bwg/hklisa/jprelay curl 家 Emby 60MB(?api_key=);TG;自删 plist com.<ORIGINAL_AUTHOR>.emby-egress-peaktest(:31-32) | EMBY key+TG+SSH | P1 | 删除 |
| scripts/emby-relay/emby-{as,eu,hub,jp,na}.nginx(5 个) | nginx 配置 | 部署 | 反代回家 Emby :233;TLS listen 443/8443/8920;作者域名+LE 证书路径;hub 注释 certbot --dns-cloudflare | 证书/CF token | P0 | 域名/upstream 占位符化 |
| scripts/emby-relay/nginx-restart.conf | systemd drop-in | 部署 | nginx Restart=on-failure | 无 | P0 | 保留设计 |
| scripts/emby-relay/README.md | 文档 | 无 | cf-ddns token 复用/:9101 令牌暴露警告 | 无 | P2 | 占位符化 |

### scripts/entry

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/entry/entry-failover.sh | 脚本 | OpenWrt cron */2 | CF DNS 写 status/auth/ntfy/smsbus/sna 等域名;tg-notify;socat/SNI 探 | CF token | P0 | 占位符化 |
| scripts/entry/web-relay-443.service、web-relay-80.service | systemd | 开机 Restart=always | socat TCP4-LISTEN:443/80→tailnet Caddy | 无 | P0 | 删除或目标占位符化 |
| scripts/entry/hk-cmi-stream.conf | nginx stream | 部署 | 443 SNI 分流→127.0.0.1:9443 剥 PROXY 头→tailnet Caddy 透传 | 无 | P0 | 占位符化 |
| scripts/entry/README.md | 文档 | 无 | 4 入口机公网 IP+ufw allow 80,443 | 无 | P2 | 删真实 IP |

### scripts/friends

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/friends/friendsd.py + friendsd.service | systemd+脚本 | Restart=always | 订阅守护绑 tailnet IP+Bearer;每朋友 token /f/＜token＞ 公开路径;生成 hy2/trojan 口令;PUBLIC_BASE 默认作者域名 | FRIENDSD_SECRET/NODE_SECRET | P0 | 占位符化 |
| scripts/friends/friends-apply.py + friends-apply.timer | systemd+脚本 | 60s | 经各出口探 AI(PROBE_URL);Clash external_controller Bearer;iptables/ip6tables 规则;systemctl restart sing-box(:394) | FRIENDSD_SECRET/SITE_KEY | P0 | 占位符化 |
| scripts/friends/friendacct-collect.py + timer | systemd+脚本 | 60s | POST friendsd Bearer;iptables 计数归零判定 | FRIENDSD_SECRET | P0 | 占位符化 |
| scripts/friends/friendacct-rules.sh + service | systemd | 开机 oneshot | iptables/ip6tables mangle FRIENDACCT 计数 | 无 | P0 | 保留设计 |
| scripts/friends/install-friendacct.sh | 安装器 | 手动 | scp+ssh bwg/akko/jprelay;systemctl enable --now rules+collect.timer | SSH | P0 | 删除 |
| scripts/friends/mirror-apps.py + mirror-apps.timer | systemd+脚本 | 周一 05:30 Persistent | GitHub release 下载(max-time 900) | GITHUB_TOKEN 可选 | P0 | 占位符化(目标为公开 GitHub) |

### scripts/hy2-hop

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/hy2-hop/hy2-hop.sh + hy2-hop.service | systemd | 开机 oneshot | iptables/ip6tables nat UDP 端口跳跃段 | 无 | P0 | 保留设计 |

### scripts/icloud-archive

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/icloud-archive/icloud-archive.sh + plist | launchd+脚本 | 每日 04:00 | osxphotos 导出→NAS;TG sendMessage | iCloud 照片访问+TG token | P0 | 删 plist;脚本占位符化 |
| scripts/icloud-archive/icloudpd-weekly.sh + plist | launchd+脚本 | 周日 07:00 | icloudpd --username ＜EMAIL＞ --cookie-directory ~/.icloudpd-cookies;TG | iCloud 账号+cookie | P0 | 删除 |
| scripts/icloud-archive/com.<ORIGINAL_AUTHOR>.immich-ml-socat.plist | launchd | RunAtLoad+KeepAlive | socat TCP-LISTEN:3003→tailnet ML 主机:3003 | 无 | P0 | 删除/目标占位符化 |
| scripts/icloud-archive/install-mac.sh | 安装器 | 手动 | curl -LsSf https://＜astral＞/uv/install.sh | sh(远程管道安装);launchctl bootstrap icloud-archive | 无 | P0 | 删除 |
| scripts/icloud-archive/setup-photos-nfs-for-immich.sh | 安装器 | 手动 | sudo NFS 挂;内联生成 root LaunchDaemon com.<ORIGINAL_AUTHOR>.photos-nfs RunAtLoad+bootstrap system | 无 | P0 | 删除 |
| scripts/icloud-archive/immich-ml-toggle.sh | 脚本 | 手动 | Immich /api/auth/login email+password→PUT /api/jobs pause/resume | Immich 账号 | P1 | 占位符化 |
| scripts/icloud-archive/icloud-hidden-vault.sh | 脚本 | 手动 | AES-256 HFS+ sparseimage(NAS);密码自 PWFILE 并回显「抄进 00-密码总表」 | vault 密码 | P1 | 删除回显逻辑 |
| scripts/icloud-archive/nas-dedup-dryrun.py、xmp-anchored-fill.py | 脚本 | 手动 | DRY-RUN 去重/XMP 边车写 | 无 | P2 | 保留 |
| scripts/icloud-archive/README.md | 文档 | 无 | rsync+ssh install-mac 部署 | 无 | P2 | 占位符化 |

### scripts/ops

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/ops/cf-ddns.sh + cf-ddns.timer | systemd+脚本 | 15min | CF DNS POST/PUT dns_records TTL120 灰云;curl 探 IP(cloudflare trace+兜底) | CF_API_TOKEN+CF_RECORD(/etc/cf-ddns.env) | P0 | 占位符化 |
| scripts/ops/block-watch.sh | 脚本 | OpenWrt cron 25 */3 | OpenClash API 127.0.0.1:9090(secret=uci openclash.config.dashboard_password);逐节点 delay;确认被封/恢复才 TG | OpenClash secret+TG | P0 | 占位符化 |
| scripts/ops/tg-quota.sh + timer | systemd+脚本 | 每小时 Persistent | KiwiVM /run/kiwivm-traffic2+cycle-info;TG 配额告警+速率外推 | TG token | P0 | 占位符化 |
| scripts/ops/sub-userinfo.sh + .service/.timer | systemd+脚本 | 每小时 | 写 nginx Subscription-Userinfo snippet;cmp 去抖 reload | 无 | P0 | 保留设计 |
| scripts/ops/kiwivm-poll.sh + timer | systemd+脚本 | 5min | BWG KiwiVM /v1/getServiceInfo | KIWIVM_VEID+api_key(/etc/kiwivm.env) | P0 | 占位符化 |
| scripts/ops/mp-autoupdate.sh(+mp-autoupdate.env.example) | 脚本 | 群晖 DSM 任务计划 root | 检新镜像→备 user.db→docker compose pull/up moviepilot→健康检查→TG;失败自动回滚;API_TOKEN versions 端点 | API_TOKEN+TG | P0 | 删除(自动部署更新) |
| scripts/ops/emby-autosub.py + plist | launchd+脚本 | 每小时 | Emby API+MoviePilot POST login+OpenSubtitles 下载(PER_DAY=10)+SSH 写 srt 到群晖(id_syno_backup) | EMBY key+MP 账号+SSH key | P0 | 删 plist;占位符化 |
| scripts/ops/emby-posterfill.py + plist | launchd+脚本 | RunAtLoad+1800 | TMDB API+Emby+SSH 写 poster.jpg | TMDB key+EMBY key+SSH | P0 | 删 plist |
| scripts/ops/emby-fix-dateadded.py + plist | launchd+脚本 | 1800 | Emby API 写;EMBY_ADMIN_ID 默认真实 GUID | EMBY key | P0 | 删 plist;去默认 GUID |
| scripts/ops/emby-token-dump.sh + plist | launchd+脚本 | RunAtLoad+900 | Emby authentication.db Tokens_2⋈users.db→token/UserId/设备公网 IP→用户名 json;经 mac-status :9101 暴露 | 本地 DB | P0 | 删除(隐私聚合) |
| scripts/ops/emby-backup.sh + plist | launchd+脚本 | 每日 03:30 | rsync -a -e ssh→群晖;TG | SSH key(id_syno_backup)+TG | P0 | 删 plist |
| scripts/ops/macmini-config-backup.sh + plist | launchd+脚本 | 周日 06:30 | rsync -a --delete→syno:/volume1/BACKUP/macmini-config/(LaunchAgents/.env/Emby config) | SSH key | P0 | 删 plist |
| scripts/ops/fleet-speedtest.sh | 脚本 | 周日 21:30 launchd(plist 不在库) | BOXES 硬编码 5 机真实公网 IP+SSH 端口;8 并发加密流×25MB;ping;TG | SSH+TG | P0 | 删真实 IP 表 |
| scripts/ops/fleet-config-backup.sh | 脚本 | 手动 | ssh 9 节点 tar /root/config-backup.tgz(含 sing-box/cf-ddns/tg-notify/selfheal env);age -R .age-recipients→backups/;ssh contabo 写 backups.json | SSH 别名+age | P1 | 节点列表占位符化 |
| scripts/ops/istoreos-config-backup.sh | 脚本 | 手动 | Tailscale SSH root@istoreos(或 -J contabo);tar 配置;age 加密 | SSH | P1 | 占位符化 |
| scripts/ops/decrypt-backup.sh | 脚本 | 手动 | age -d -i HOMELAB_AGE_KEY→tar tzf/xzf backups/*.tgz.age | age 私钥(git 外) | P1 | 保留(需显式授权) |
| scripts/ops/apply-baseline.sh | 安装器 | 手动 root | journald 封顶+restart/APT 清缓存/logrotate/conntrack/swap/tailscale-gro enable --now | SSH | P0 | 删除 |
| scripts/ops/timer-tuning/apply.sh | 安装器 | 手动 root | timer drop-in 20-freq.conf 重写;systemctl disable/restart | SSH | P0 | 删除 |
| scripts/ops/derper.service + derper-reload.sh | systemd+hook | Restart=always;LE 续期 hook | derper -hostname ＜AUTHOR_DOMAIN＞ -a :8443 -stun-port 3478 -certmode manual -verify-clients;hook restart derper | TLS 证书 | P0 | 域名占位符化 |
| scripts/ops/scheduled-reboot.service + .timer | systemd | 周日 04:00(按机错峰) | ExecStart=/sbin/reboot;ExecStartPre touch selfheal 标记 | 无 | P0 | 删除(自动重启) |
| scripts/ops/mac-status.py | 脚本 | launchd com.<ORIGINAL_AUTHOR>.macstatus KeepAlive(plist 不在库) | HTTP :9101 绑 tailnet IP;serve 状态+emby-tokens.json | 无 | P0 | 删除/绑定占位符化 |
| scripts/ops/svcstatus.sh + svcstatus-gen.service | systemd+脚本 | 15s | systemctl 状态+curl 健康→/opt/svcstatus/services.json | 无 | P2 | 保留 |
| scripts/ops/cycle-info.sh | 脚本 | 被 tg-quota 调用 | 本地 vnstat 账期流量(:10) | 无 | P2 | 保留 |
| scripts/ops/owrt-status | 脚本 | CGI 手动 | 路由状态 | 无 | P2 | 保留 |
| scripts/ops/peak-retest-20260704.sh | 脚本 | 一次性 crontab | nc -z×20+curl http://＜IP＞:48211/t.bin 200MB;自删 cron 行 | 无 | P1 | 删除 |
| scripts/ops/peak-retest-hklisa.sh | 脚本 | launchd+cron 6 时段 | ssh id_ed25519 200MB 流;TG;自清 cron+launchctl unload+rm cc.jimmycloud.hklisa-peak.plist | SSH+TG | P1 | 删除 |
| scripts/ops/portable-ssd.sh | 脚本 | 手动 | ssh m5 bash -s;rsync push/pull ExFAT;git bundle scp | SSH | P1 | 占位符化 |
| scripts/ops/lucky-admin-tunnel.sh | 脚本 | 手动 | ssh -N -L 转发→路由 Lucky 后台;curl 127.0.0.1 | SSH | P1 | 占位符化 |
| scripts/ops/setup-videos-nfs-for-emby.sh | 安装器 | 手动 | sudo NFS 只读挂;内联 root LaunchDaemon com.<ORIGINAL_AUTHOR>.emby-videos-nfs RunAtLoad+bootstrap system | 无 | P0 | 删除 |
| scripts/ops/sync-sub.sh | 脚本 | 手动/cron | cd /opt/clash-config && git pull(:4);cp 订阅文件→/var/www/sub/＜SUB_TOKEN＞/(路径 token 硬编码 10+处) | git remote(作者 clash-config 仓库) | P1 | 删 token 路径 |
| scripts/ops/emby-covers.py | 脚本 | 手动 | Emby 封面上传 | EMBY key | P1 | 占位符化 |
| scripts/ops/emby-rebuild-9libs.py、emby-rebuild-libraries.py | 脚本 | 手动 | pkill EmbyServer;DELETE /Library/VirtualFolders | EMBY key | P1 | 删除(破坏性) |
| scripts/ops/openwrt-home-proxy.init | procd init | 开机 START=95 respawn 3600 5 5 | xray VLESS-REALITY :28443+tailnet SS-2022 :8888(nobody);config /etc/home-proxy/config.json(Reality 私钥在库外) | 节点凭据(库外) | P0 | 删除/占位符化 |
| scripts/ops/decoy-http/decoy-http.py + .service | systemd | Restart=always User=nobody | 假 CDN 诱饵站本地 serve | DECOY_* env | P2 | 保留 |
| scripts/ops/tokyo-server/docker-user-fw.service | systemd | 开机 | iptables/ip6tables DOCKER-USER DROP 80,443,3000,3001,8080 | 无 | P0 | 保留设计 |
| scripts/ops/fleet-baseline/51homelab-origins(.tokyo-server) | APT 配置 | 部署 | unattended-upgrades 加 Tailscale/Docker 源→自动第三方升级 | 无 | P0 | 删除 |
| scripts/ops/fleet-baseline/fail2ban-ignoreip.local、journald-50-homelab.conf、tailscale-gro.service、README;journald-cap.conf;sing-box.logrotate | 配置 | 部署/scp | 白名单 tailnet/journald 封顶/ethtool GRO | 无 | P2 | 保留设计 |
| scripts/ops/emby-ops.env.example | 模板 | 无 | 占位符 | 无 | P2 | 保留 |
| scripts/ops/README.md、dec1-bwg-cutover/RUNBOOK.md + nginx-443-sni-mux.conf.template | 文档/模板 | 手动 | 割接手册(ssh/ufw/sing-box/nginx);SNI mux 模板(singbox_reality_backend 127.0.0.1:＜NEW_REALITY_PORT＞) | 无 | P2 | 文档真实地址占位符化 |

### scripts/peer-relay

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/peer-relay/relay-pref.sh | 脚本 | cron #relay-pref | nft table inet ts_relay_pref drop UDP 到 HKU 公网 IP;tailscale status/ping;relay 离线自动撤+冷却 | 无 | P0 | 目标 IP 占位符化 |

### scripts/selfheal

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/selfheal/selfheal.sh + selfheal.service + selfheal.timer | systemd+脚本 | OnBootSec=3min+OnCalendar=*:0/2 | 探测→repair_unit/repair_docker/repair_singbox/repair_resolved(改 resolv.conf、tailscale set --accept-dns=false)→critical 护栏整机重启;clash_api PUT selector(:578);AI_PROBE_URL(:39);TG | TG token+/etc/selfheal.env(AI_CLASH_SECRET/AI_IPROYAL_URL 凭据) | P0 | 占位符化;保留设计思想 |
| scripts/selfheal/install.sh | 安装器 | 手动 | install -m 0600 selfheal.env;--enable→enable --now selfheal.timer | 无 | P0 | 删除 |
| scripts/selfheal/checks.{akko,bwg,contabo,hklisa,hkrelay,lisa,malaysia,vmiss}.sh(8) | 配置 | 部署 | 按角色 run_check 自动修复表(contabo repair_docker dashboard-caddy-1;smsbus /stats;cert-watch;external-watch;lisa 39720 critical;vmiss socat) | 无 | P0 | 占位符化 |
| scripts/selfheal/lib.external-watch.sh | 组件 | 部署 | 外部 HTTP 哨兵;锚点 ＜PUB＞:443 门;SUB_CHECK_URL 自 env;3 次失败判罚 | env | P0 | 占位符化 |
| scripts/selfheal/lib.cert-watch.sh | 组件 | 部署 | openssl s_client+x509 enddate 验链 | 无 | P2 | 保留 |
| scripts/selfheal/singbox-ai-probe.sh | 安装器 | 手动 | 写 zz-ai-probe.json mixed 入站 127.0.0.1:19720;route.rules 插队;sing-box check+restart | 无 | P0 | 删除 |
| scripts/selfheal/singbox-ai-selector.sh | 安装器 | 手动 | selector+clash_api(127.0.0.1+secret);openssl rand 生成 AI_CLASH_SECRET→env;IPRoyal 出站凭据自 env;jq 改 config;restart+回滚 | env 凭据 | P0 | 删除 |
| scripts/selfheal/singbox-harden-routes.sh | 安装器 | 手动 | route.rules 封 private+CGNAT 目的地(防代理用户借道打内网);restart+回滚 | 无 | P0 | 保留设计思想 |
| scripts/selfheal/singbox-ig-split.sh | 安装器 | 手动 | IG 拆 ig-out;IGPROBE curl https://＜REMOTE＞/data/shared_data/;改 config+restart | 无 | P0 | 删除 |
| scripts/selfheal/singbox-resi-inbounds.sh | 安装器 | 手动 | bwg 开 SS 住宅入站 resi-us/resi-ca;openssl rand -base64 16 口令;ufw allow 端口;restart;回显 ss://含口令 | env(IPRoyal) | P0 | 删除(开公网口) |
| scripts/selfheal/stagger-contabo-timers.sh、fix-freq-timers.sh | 安装器 | 手动 ssh bash -s | timer 错峰/单调→墙钟;daemon-reload+restart | SSH | P0 | 删除 |
| scripts/selfheal/mac/selfheal-mac.sh + plist | launchd+脚本 | RunAtLoad+120s | Emby/Immich/Tailscale 探测修复;docker-compose up -d;launchctl kickstart -k immich-ml-socat;TG(--resolve 公网 IP 兜底);绝不重启整机 | TG token(~/bin/selfheal.env) | P0 | 删 plist;占位符化 |
| scripts/selfheal/mac/install-mac.sh | 安装器 | 手动 | env 模板 0600→~/bin/selfheal.env(FILL_ME);launchctl bootout/bootstrap/enable gui | 无 | P0 | 删除 |
| scripts/selfheal/mac/tailscale-health.sh | 组件 | 装机 | open -ga Tailscale;重连保存配置;状态机 TG | 无 | P0 | 保留设计 |
| scripts/selfheal/mac/colima/immich-colima-up.sh + plist | launchd+脚本 | RunAtLoad | 等 NFS→colima start→docker-compose up -d;pgrep 守卫 | 无 | P0 | 删 plist |
| scripts/selfheal/mac/selfheal.env.template | 模板 | 无 | TG_TOKEN=FILL_ME;注释含作者 Bot handle | 无 | P2 | handle 占位符化 |
| scripts/selfheal/openwrt/selfheal.sh + install.sh + checks.router.sh + tg-notify.sh | 脚本+安装器 | cron */2(--enable) | busybox 引擎;init.d/docker restart;guarded_reboot 兜底;TG(--resolve 兜底);install 写 crontab | TG token(/etc/tg-notify.env) | P0 | 删安装器;引擎占位符化 |
| scripts/selfheal/openwrt/tg-notify.env.template、selfheal.env;selfheal.env;selfheal.logrotate;mac/test-tailscale-health.sh;README | 模板/配置/测试/文档 | 无 | 阈值/占位符/离线测试 | 无 | P2 | 保留(README handle 占位符化) |

### scripts/smsbus

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/smsbus/smsbus.py + Dockerfile(compose build) | 容器 | restart unless-stopped | webhook 入站 HMAC-SHA256 验签→去重→落盘→分级→扇出 Bark(AES256/CBC)+ntfy | SMSBUS_SECRET+BARK_SERVER/KEY/IV+NTFY_BASE/TOKEN | P0 | 占位符化(短信内容自动外发) |
| scripts/smsbus/senders.py | 组件 | 容器 | Bark AES 推送+ntfy Bearer | 同上 | P0 | 占位符化 |
| scripts/smsbus/classify.py、tests/*(4) | 代码/测试 | 无 | 纯函数分级/离线测试 | 无 | P2 | 保留 |
| scripts/smsbus/README.md | 文档 | 无 | 部署链路(VMISS socat SNI) | 无 | P2 | 占位符化 |

### scripts/subtrans

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/subtrans/translate_subs.py | 脚本 | 手动 | Qwen/MiniMax chat/completions(key 文件 ~/.agent-panel/*.key;curl -K -);EMBY_KEY;ssh syno 写 .chi.AI翻译版.srt;配额耗尽即停 | AI key+EMBY key+SSH | P1 | 占位符化 |
| scripts/subtrans/finish5.py | 脚本 | 手动 | ssh syno ffmpeg 抽字幕+rm tmp | SSH | P1 | 占位符化 |

### scripts/fnd 与 whisperlivekit

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| scripts/fnd/gen_ics.py、test_fnd.py、betty_timetable.html | 脚本/测试 | 手动 | 课表→ICS 本地 | 无 | P2 | 保留 |
| whisperlivekit/start.sh | 脚本 | 手动 | 本地 wlk serve --host 0.0.0.0 --port 8888(LAN 暴露;注释 --api-token) | 无 | P2 | bind 改 127.0.0.1 |

### sms-forwarder(手机 App 配置)

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| sms-forwarder/SmsForwarder-FindN6.json | 手机配置 | 导入即自动 | sender type2=Bark(server+key+iv)、type3=Webhook×2(webServer+secret,目标域名 sha8=e30f3680);frpc config 27 行含 server_addr+auth token(autorun=0);2 条 rule;settings 含设备信息 | Bark key+webhook secret+frp token | P1 | 删除或全占位符化(导入=短信/来电自动外发) |
| sms-forwarder/SmsForwarder-ZFlip7.json | 手机配置 | 导入即自动 | 同结构(webhook 目标同 e30f3680;Bark server 同 87fdcd4e) | 同上 | P1 | 同上 |

### backups/

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| backups/dashboard/docker-compose.yml | compose | restart unless-stopped×7 | caddy 80/443 公网;authsvc;prometheus;grafana(anonymous Viewer;GF_SERVER_ROOT_URL 硬编码作者域名:65);ntfy(NTFY_BASE_URL 作者域名:86);smsbus 127.0.0.1:8090;classnet 127.0.0.1:8095 | GF_ADMIN_PASSWORD:<EXAMPLE_PASSWORD> env | P0 | 域名占位符化;保留结构 |
| backups/dashboard/Caddyfile | Caddy 配置 | 部署 | 6 作者域名虚拟主机(auth/status/ntfy/smsbus/sna/sub);forward_auth authsvc;/sub-center→{$SUB_CENTER_URL};sub→host.docker.internal:8712;telemetry file server;CSP connect-src 允许 open-meteo/github/openfreemap | 无(env) | P0 | 域名占位符化 |
| backups/dashboard/glance.yml | 配置(已退役) | 无 | :45 订阅中心 URL 含 ＜SUB_TOKEN＞;:402 MoviePilot http://＜CGNAT_IP＞:3000 statistic?token=＜MP_TOKEN＞;:397/:409 作者域名 | sub token+MP token | P2 | 删除(退役+真实凭据) |
| backups/dashboard/.env.example | 模板 | 无 | replace-with-strong-password 占位 | 无 | P2 | 保留 |
| backups/dashboard/authsvc/app.py | 服务代码 | compose 自启 | AUTH_SECRET 必需(:6-8);AUTH_USER 默认作者名(:10);AUTH_URL/DEFAULT_RD/COOKIE_DOMAIN 默认作者域名(:12-14);scrypt cookie;/change-password | AUTH_SECRET/AUTH_PWHASH env | P0 | 默认域名/用户名占位符化 |
| backups/immich/docker-compose.yml | compose | restart always×4 | 端口 2283:2283 全接口;volume /Users/＜AUTHOR_HOME＞/photos-nas(:24);image sha256 钉版(:57/:64,非凭据) | DB_PASSWORD env | P0 | 家目录占位符化 |
| backups/immich/.env.template | 模板 | 无 | DB_PASSWORD=<EXAMPLE_PASSWORD> | 无 | P2 | 保留 |
| backups/immich/immich-colima-up.sh、immich-nfs-mount.sh | 脚本 | launchd RunAtLoad | docker-compose up -d;root NFS 挂群晖 | 无 | P0 | 删除/占位符化 |
| backups/*-config-backup.tgz.age(9:akko/bwg/contabo/hklisa/hkrelay/istoreos/jprelay/lisa/malaysia) | 加密归档 | 手动解密 | 含舰队 /etc 密钥(sing-box/cf-ddns/tg-notify/selfheal/ufw/sshd/fail2ban;contabo 另 /opt/dashboard+pollers env) | age 私钥(git 外) | P1 | 删除或移出仓库(密文仍敏感) |
| .age-recipients | 配置 | 无 | 1 个 age1 公钥收件人;注释私钥仅存 git 外 | 无 | P2 | 保留/换自己收件人 |

### 根目录文档

| 路径 | 类型 | 触发方式 | 行为摘要(不含真实地址) | 需要的凭据类型 | 风险级 | 处置建议 |
|---|---|---|---|---|---|---|
| 00-密码总表.md | 文档 | 无 | 271 行/137 表行:SSH/服务器、VPS 面板、API key/TG Bot、订阅地址(路径 token 即密钥)、按朋友签发 token、SS/Hy2/Trojan 节点口令、IPRoyal 住宅代理凭据、clash_api secret;标题含真实域名 | 全部凭据类型 | P2 | 删除或移出仓库(数据暴露最高优先脱敏) |
| 其余 57 个根目录 md(含 06/08 节点链接文档、CHANGELOG/FINDINGS/README) | 文档 | 无 | 订阅 URL+email+ssh/systemctl/iptables 示例+真实 IP/域名 | sub URL/email | P2 | 批量占位符化 |

## 四、launchd plist 专表

【已验证】plistlib 解析全部 21 个 plist。**所有 Label 含作者名(jimmy/jimmycloud),脱敏时需替换**;ProgramArguments 中 `/Users/＜AUTHOR_HOME＞` 为原作者家目录绝对路径(克隆内对应脚本见主表);日志多写 ~/.agent-panel/*.log 或 /tmp。

| plist 路径 | Label(含作者名,需替换) | ProgramArguments(家目录已脱敏) | 自启/定时参数 | 备注 |
|---|---|---|---|---|
| backups/immich/com.<ORIGINAL_AUTHOR>.colima.plist | com.<ORIGINAL_AUTHOR>.colima | /bin/bash /Users/＜AUTHOR_HOME＞/.local/bin/immich-colima-up.sh | RunAtLoad | 与 selfheal/mac/colima 同名重复;对应仓库脚本 scripts/selfheal/mac/colima/immich-colima-up.sh |
| backups/immich/com.<ORIGINAL_AUTHOR>.immich-nfs.plist | com.<ORIGINAL_AUTHOR>.immich-nfs | /bin/bash /usr/local/bin/immich-nfs-mount.sh | RunAtLoad | 注释称 root LaunchDaemon;对应 backups/immich/immich-nfs-mount.sh |
| scripts/agent-panel/archive/20261123-ai-hub/com.<ORIGINAL_AUTHOR>.agent-panel.autoloop.plist | com.<ORIGINAL_AUTHOR>.agent-panel.autoloop | python3.12 /Users/＜AUTHOR_HOME＞/Downloads/homelab/scripts/agent-panel/autoloop.py --tick | RunAtLoad;StartInterval=180 | 已退役归档 |
| scripts/agent-panel/archive/20261123-ai-hub/com.<ORIGINAL_AUTHOR>.agent-panel.receiver.plist | com.<ORIGINAL_AUTHOR>.agent-panel.receiver | python3.12 …/archive/20261123-ai-hub/receiver.py | RunAtLoad;KeepAlive | 已退役归档 |
| scripts/agent-panel/archive/20261123-ai-hub/com.<ORIGINAL_AUTHOR>.agent-panel.summaries.plist | com.<ORIGINAL_AUTHOR>.agent-panel.summaries | python3.12 …/summaries.py | StartInterval=300(无 RunAtLoad) | 已退役归档 |
| scripts/agent-panel/archive/20261123-ai-hub/com.<ORIGINAL_AUTHOR>.agent-panel.tghub.plist | com.<ORIGINAL_AUTHOR>.agent-panel.tghub | python3.12 …/tg-hub.py | RunAtLoad;KeepAlive | 已退役归档 |
| scripts/agent-panel/archive/20261123-ai-hub/com.<ORIGINAL_AUTHOR>.agent-panel.tgpush.plist | com.<ORIGINAL_AUTHOR>.agent-panel.tgpush | python3.12 …/tg-push.py | RunAtLoad;StartInterval=30 | 已退役归档 |
| scripts/agent-panel/com.<ORIGINAL_AUTHOR>.agent-panel.plan-usage.plist | com.<ORIGINAL_AUTHOR>.agent-panel.plan-usage | python3.12 /Users/＜AUTHOR_HOME＞/Downloads/homelab/scripts/agent-panel/plan-usage.py | RunAtLoad;StartInterval=1800 | 现役(与 README「零 launchd」矛盾) |
| scripts/agent-panel/com.<ORIGINAL_AUTHOR>.agent-panel.push.plist | com.<ORIGINAL_AUTHOR>.agent-panel.push | python3.12 …/push-to-contabo.py | RunAtLoad;StartInterval=120 | 现役;ssh contabo 外发 |
| scripts/agent-panel/com.<ORIGINAL_AUTHOR>.agent-panel.usage.plist | com.<ORIGINAL_AUTHOR>.agent-panel.usage | python3.12 …/usage-collector.py | RunAtLoad;StartInterval=600 | 现役 |
| scripts/icloud-archive/com.<ORIGINAL_AUTHOR>.icloud-archive.plist | com.<ORIGINAL_AUTHOR>.icloud-archive | /bin/bash /Users/＜AUTHOR_HOME＞/bin/icloud-archive.sh | StartCalendarInterval 每日 04:00(无 RunAtLoad) | LowPriorityIO |
| scripts/icloud-archive/com.<ORIGINAL_AUTHOR>.icloudpd-weekly.plist | com.<ORIGINAL_AUTHOR>.icloudpd-weekly | /bin/bash /Users/＜AUTHOR_HOME＞/bin/icloudpd-weekly.sh | StartCalendarInterval 周日 07:00 | iCloud 凭据 |
| scripts/icloud-archive/com.<ORIGINAL_AUTHOR>.immich-ml-socat.plist | com.<ORIGINAL_AUTHOR>.immich-ml-socat | /opt/homebrew/bin/socat TCP-LISTEN:3003,fork,reuseaddr TCP:＜CGNAT_IP＞:3003 | RunAtLoad;KeepAlive | 端口转发到 tailnet ML 主机 |
| scripts/ops/com.<ORIGINAL_AUTHOR>.config-backup.plist | com.<ORIGINAL_AUTHOR>.config-backup | /bin/bash /Users/＜AUTHOR_HOME＞/bin/macmini-config-backup.sh | StartCalendarInterval 周日 06:30 | rsync --delete 到群晖 |
| scripts/ops/com.<ORIGINAL_AUTHOR>.emby-autosub.plist | com.<ORIGINAL_AUTHOR>.emby-autosub | /usr/bin/python3 /Users/＜AUTHOR_HOME＞/bin/emby-autosub.py | StartInterval=3600 |  |
| scripts/ops/com.<ORIGINAL_AUTHOR>.emby-backup.plist | com.<ORIGINAL_AUTHOR>.emby-backup | /bin/bash /Users/＜AUTHOR_HOME＞/bin/emby-backup.sh | StartCalendarInterval 每日 03:30 |  |
| scripts/ops/com.<ORIGINAL_AUTHOR>.emby-dateadded.plist | com.<ORIGINAL_AUTHOR>.emby-dateadded | /usr/bin/python3 /Users/＜AUTHOR_HOME＞/bin/emby-fix-dateadded.py | StartInterval=1800 |  |
| scripts/ops/com.<ORIGINAL_AUTHOR>.emby-posterfill.plist | com.<ORIGINAL_AUTHOR>.emby-posterfill | /usr/bin/python3 /Users/＜AUTHOR_HOME＞/bin/emby-posterfill.py | RunAtLoad;StartInterval=1800 | TMDB 外联 |
| scripts/ops/com.<ORIGINAL_AUTHOR>.emby-tokens.plist | com.<ORIGINAL_AUTHOR>.emby-tokens | /bin/bash /Users/＜AUTHOR_HOME＞/emby-token-dump.sh | RunAtLoad;StartInterval=900 | 隐私聚合 |
| scripts/selfheal/mac/colima/com.<ORIGINAL_AUTHOR>.colima.plist | com.<ORIGINAL_AUTHOR>.colima | /bin/bash /Users/＜AUTHOR_HOME＞/.local/bin/immich-colima-up.sh | RunAtLoad | AbandonProcessGroup;与 backups 同名重复 |
| scripts/selfheal/mac/com.<ORIGINAL_AUTHOR>.selfheal.plist | com.<ORIGINAL_AUTHOR>.selfheal | /bin/bash /Users/＜AUTHOR_HOME＞/bin/selfheal-mac.sh | RunAtLoad;StartInterval=120 | AbandonProcessGroup |

### 补充:内联生成/被引用但仓库缺失/历史已删除的 Label

| Label | 来源 | 触发 | 备注 |
|---|---|---|---|
| com.<ORIGINAL_AUTHOR>.photos-nfs | scripts/icloud-archive/setup-photos-nfs-for-immich.sh 内联生成 | root LaunchDaemon;RunAtLoad;launchctl bootstrap system | 仓库无 plist 文件 |
| com.<ORIGINAL_AUTHOR>.emby-videos-nfs | scripts/ops/setup-videos-nfs-for-emby.sh 内联生成 | root LaunchDaemon;RunAtLoad;bootstrap system | 仓库无 plist 文件 |
| com.<ORIGINAL_AUTHOR>.macstatus | scripts/ops/README.md 与 mac-status.py 引用 | KeepAlive;HTTP :9101 | 仓库无 plist 文件 |
| cc.jimmycloud.hklisa-peak | scripts/ops/peak-retest-hklisa.sh 自删 | launchd+cron 6 时段 | 跑完 launchctl unload+rm plist |
| com.<ORIGINAL_AUTHOR>.emby-egress-peaktest | scripts/emby-relay/emby-egress-peaktest.sh:31-32 自删 | 一次性 | 跑完 bootout+rm plist |
| (fleet-speedtest,label 未知) | scripts/ops/fleet-speedtest.sh 注释 | 周日 21:30 | 仓库无 plist 文件 |
| com.<ORIGINAL_AUTHOR>.emby-hub-watch | 历史已删除(commit 1d599d4,2026-11-16) | /bin/bash /Users/＜AUTHOR_HOME＞/emby-hub-watch.sh;未见 RunAtLoad/StartInterval/KeepAlive 键 | git show 取证 |

## 五、systemd/timer 与 cron 自启动

### 5.1 cron/任务计划(非 systemd)

| 调度器 | 文件 | 频率 | 行为 |
|---|---|---|---|
| OpenWrt crontab | scripts/emby-relay/emby-evac.sh | */2 flock | CF DNS 写+TG |
| OpenWrt crontab | scripts/entry/entry-failover.sh | */2 | CF DNS 写+TG |
| OpenWrt crontab | scripts/ops/block-watch.sh | 25 */3 | OpenClash API+TG |
| OpenWrt crontab | scripts/peer-relay/relay-pref.sh | #relay-pref 标记 | nft drop+tailscale ping |
| OpenWrt crontab | scripts/selfheal/openwrt/install.sh --enable 写入 | */2 flock | 自愈引擎 |
| Mac cron | scripts/agent-panel/usage-collector.sh | 10min(注释) | 本地配额采集 |
| Mac crontab | scripts/ops/peak-retest-20260704.sh | 一次性(自删 cron 行) | nc+curl 200MB |
| Mac launchd+cron | scripts/ops/peak-retest-hklisa.sh | 6 时段(自清) | ssh 200MB+TG |
| 群晖 DSM 任务计划 | scripts/ops/mp-autoupdate.sh | root 定时 | docker compose pull/up+回滚+TG |

### 5.2 systemd 单元摘录(已脱敏,完整 40 单元)

```
### scripts/dashboard/cloud-quota-balanced.conf
  3: OnUnitActiveSec=
  4: OnCalendar=
  5: OnCalendar=*:0/5:35
  6: AccuracySec=1s
### scripts/dashboard/cloud-quota-minute.conf
  2: OnUnitActiveSec=
  3: OnCalendar=
  4: OnCalendar=*:*:00
  5: AccuracySec=1s
### scripts/dashboard/poll-emby-relays.service
  4: Description=Poll Emby regional relay entrypoints for the homelab portal
  7: Type=oneshot
  8: ExecStart=/usr/local/bin/poll-emby-relays.sh
### scripts/dashboard/poll-emby-relays.timer
  5: OnBootSec=35s
  6: OnUnitActiveSec=30s
### scripts/dashboard/poll-emby-usage.service
  4: Description=Merge Emby relay per-user traffic for the homelab portal
  7: Type=oneshot
  8: ExecStart=/usr/local/bin/poll-emby-usage.sh
### scripts/dashboard/poll-emby-usage.timer
  4: Description=Poll Emby per-user traffic usage
  7: OnBootSec=50s
  8: OnUnitActiveSec=60s
### scripts/dashboard/poll-fleet.service
  4: Description=Aggregate fleet-wide node status into fleet.json for the portal header
  7: Type=oneshot
  8: ExecStart=/usr/local/bin/poll-fleet.sh
### scripts/dashboard/poll-fleet.timer
  4: OnBootSec=20s
  5: OnUnitActiveSec=30s
### scripts/dashboard/poll-web.service
  2: Description=Portal web-services poller (web.json for /ui/next SWITCHBOARD)
  3: After=network-online.target
  6: Type=oneshot
  7: ExecStart=/usr/local/bin/poll-web.sh
### scripts/dashboard/poll-web.timer
  2: Description=Run poll-web.sh every 60s
  5: OnBootSec=45s
  6: OnUnitActiveSec=60s
  7: AccuracySec=5s
### scripts/emby-relay/emby-failover.service
  2: Description=Emby unified entry ＜DOMAIN＞ DNS failover (doc50)
  3: After=network-online.target
  4: Wants=network-online.target
  7: Type=oneshot
  8: ExecStart=/usr/local/bin/emby-failover.sh
### scripts/emby-relay/emby-failover.timer
  2: Description=Run emby-failover every minute
  6: OnCalendar=*:*:00
  7: AccuracySec=5s
  8: Persistent=false
### scripts/emby-relay/emby-traffic-agg.service
  2: Description=Aggregate Emby relay traffic log → /opt/svcstatus/emby-traffic.json
  5: Type=oneshot
  7: ExecStart=/usr/local/bin/emby-traffic-agg.sh REGION_PLACEHOLDER
### scripts/emby-relay/emby-traffic-agg.timer
  2: Description=Emby relay traffic aggregator (every minute)
  5: OnCalendar=*-*-* *:*:00
  6: AccuracySec=5s
### scripts/emby-relay/emby-upstream-reload.service
  2: Description=Reload nginx when home Emby DDNS IP changes
  5: Type=oneshot
  6: ExecStart=/usr/local/bin/emby-upstream-reload.sh
### scripts/emby-relay/emby-upstream-reload.timer
  2: Description=Check home Emby DDNS IP every 5min (emby-na upstream)
  5: OnBootSec=2min
  6: OnUnitActiveSec=5min
  7: Persistent=true
### scripts/emby-relay/nginx-restart.conf
  7: Restart=on-failure
### scripts/entry/web-relay-443.service
  2: Description=web-relay 443 -＞ tokyo-server Caddy via tailnet(网站入口候选,见 scripts/entry/README.md)
  3: After=network-online.target tailscaled.service
  4: Wants=network-online.target tailscaled.service
  6: ExecStart=/usr/bin/socat TCP4-LISTEN:443,fork,reuseaddr,nodelay,backlog=256,max-children=200 TCP4:＜IP:CGNAT＞:443,nodelay,connect-timeout=10
  7: Restart=always
### scripts/entry/web-relay-80.service
  2: Description=web-relay 80 -＞ tokyo-server Caddy via tailnet(网站入口候选,见 scripts/entry/README.md)
  3: After=network-online.target tailscaled.service
  4: Wants=network-online.target tailscaled.service
  6: ExecStart=/usr/bin/socat TCP4-LISTEN:80,fork,reuseaddr,nodelay,backlog=256,max-children=200 TCP4:＜IP:CGNAT＞:80,nodelay,connect-timeout=10
  7: Restart=always
### scripts/friends/friendacct-collect.service
  2: Description=朋友版流量累加(读 mangle 计数器 → /var/lib/friendacct/state.json)
  3: After=friendacct-rules.service
  4: Wants=friendacct-rules.service
  7: Type=oneshot
  8: ExecStart=/usr/local/bin/friendacct-collect.py
### scripts/friends/friendacct-collect.timer
  2: Description=每 60s 累加朋友版流量
  5: OnBootSec=90
  6: OnCalendar=*:*:00
  7: AccuracySec=1s
### scripts/friends/friendacct-rules.service
  2: Description=朋友版流量计数规则(mangle FRIENDACCT)
  4: After=network-pre.target ufw.service
  5: Wants=network-pre.target
  8: Type=oneshot
  9: ExecStart=/usr/local/bin/friendacct-rules.sh
### scripts/friends/friends-apply.service
  2: Description=同步 friendsd 的朋友凭据到本机 sing-box
  3: After=network-online.target sing-box.service
  4: Wants=network-online.target
  7: Type=oneshot
  8: EnvironmentFile=-/etc/friends-apply.env
  9: ExecStart=/usr/local/bin/friends-apply.py
### scripts/friends/friends-apply.timer
  2: Description=每 60s 同步一次朋友凭据
  5: OnBootSec=45
  6: OnCalendar=*:*:00
  7: AccuracySec=1s
### scripts/friends/friendsd.service
  2: Description=朋友订阅按人签发服务(friendsd)
  3: After=network-online.target tailscaled.service
  4: Wants=network-online.target tailscaled.service
  7: Type=simple
  8: EnvironmentFile=/etc/friendsd.env
  9: ExecStart=/usr/local/bin/friendsd.py
  10: Restart=always
### scripts/friends/mirror-apps.service
  2: Description=镜像代理客户端安装包到 ＜DOMAIN＞
  3: After=network-online.target
  4: Wants=network-online.target
  7: Type=oneshot
  8: ExecStart=/usr/local/bin/mirror-apps.py
### scripts/friends/mirror-apps.timer
  2: Description=每周镜像一次客户端安装包
  5: OnCalendar=Mon 05:30
  6: Persistent=true
  7: RandomizedDelaySec=1800
### scripts/hy2-hop/hy2-hop.service
  2: Description=Hysteria2 端口跳跃(nat HY2HOP:UDP 段 → 自用 Hy2 口)
  3: After=network-pre.target ufw.service sing-box.service
  4: Wants=network-pre.target
  7: Type=oneshot
  8: ExecStart=/usr/local/bin/hy2-hop.sh
### scripts/ops/decoy-http/decoy-http.service
  2: Description=Local HTTP Decoy for sing-box Trojan fallback and Hysteria2 masquerade
  3: After=network.target
  6: Type=simple
  7: User=nobody
  8: ExecStart=/usr/bin/python3 /usr/local/bin/decoy-http.py
  9: Restart=always
### scripts/ops/derper.service
  6: Description=Tailscale DERP relay (self-hosted, ＜DOMAIN＞:8443)
  7: After=network-online.target tailscaled.service
  8: Wants=network-online.target
  11: ExecStart=/usr/local/bin/derper -hostname ＜DOMAIN＞ -a :8443 -http-port -1 -stun-port 3478 -certmode manual -certdir /var/lib/derper/certs -c /var/lib/derper/derper.key -verify-clients
  12: Restart=always
### scripts/ops/fleet-baseline/tailscale-gro.service
  2: Description=Enable Linux UDP GRO forwarding for Tailscale
  3: After=network-online.target tailscaled.service
  4: Wants=network-online.target
  7: Type=oneshot
  8: Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
  9: ExecStart=/bin/sh -c 'set -- $(ip -o route get ＜IP:PUB＞); while [ $# -gt 1 ]; do if [ "$1" = dev ]; then ethtool -K "$2" rx-udp-gro-forwarding on rx-gro-list off; exit $?; fi; shift; done; exit 1'
### scripts/ops/scheduled-reboot.service
  2: Description=Scheduled weekly reboot
  5: Type=oneshot
  9: ExecStart=/sbin/reboot
### scripts/ops/scheduled-reboot.timer
  3: Description=Weekly reboot (staggered)
  6: OnCalendar=Sun *-*-* 04:00:00
  7: Persistent=false
### scripts/ops/sub-userinfo.service
  2: Description=Refresh Subscription-Userinfo header for ＜DOMAIN＞ (self-hosted sub traffic/expiry display)
  3: After=network-online.target nginx.service
  6: Type=oneshot
  7: ExecStart=/usr/local/bin/sub-userinfo.sh
### scripts/ops/sub-userinfo.timer
  2: Description=Hourly refresh of Subscription-Userinfo header for self-hosted sub
  5: OnBootSec=3min
  6: OnUnitActiveSec=1h
  7: Persistent=true
### scripts/ops/svcstatus-gen.service
  6: Description=Generate svcstatus services.json for the portal
  9: Type=oneshot
  10: ExecStart=/bin/sh -c '/usr/local/bin/svcstatus.sh ＞ /opt/svcstatus/.services.tmp && mv -f /opt/svcstatus/.services.tmp /opt/svcstatus/services.json'
### scripts/ops/tg-quota.timer
  2: Description=Hourly traffic quota check + burn-rate forecast (tg-quota.sh)
  5: OnCalendar=hourly
  6: RandomizedDelaySec=300
  7: Persistent=true
### scripts/ops/tokyo-server/docker-user-fw.service
  7: Description=Block public direct access to docker-published ports (doc24; 80/443 since 2026-10-15)
  8: After=docker.service network-online.target
  9: Wants=network-online.target
  13: Type=oneshot
  14: ExecStart=/bin/sh -c 'R="-i eth0 -p tcp -m multiport --dports 80,443,3000,3001,8080 -m conntrack --ctstate NEW -j DROP"; for T in iptables ip6tables; do $T -S DOCKER-USER ＞/dev/null 2＞&1 || continue; $T -D DOCKER-USER -i
### scripts/selfheal/selfheal.service
  2: Description=Fleet self-heal check (probe -＞ repair -＞ escalate)
  3: After=network-online.target
  4: Wants=network-online.target
  7: Type=oneshot
  9: ExecStart=/usr/local/bin/selfheal.sh
### scripts/selfheal/selfheal.timer
  2: Description=Run fleet self-heal every 2 minutes
  5: OnBootSec=3min
  6: OnCalendar=*:0/2
  7: AccuracySec=15s
  8: Unit=selfheal.service
```

## 六、「未经授权不得运行」清单

以下文件一旦执行/导入/启用,即会联系原作者基础设施(SSH 别名 contabo/m5/syno/bwg/akko/…、TG Bot、Cloudflare DNS、家里 Emby/Immich/MoviePilot、AI API)或产生副作用(重启服务/整机、写 DNS/防火墙、写用户配置、自动部署更新、外发隐私数据)。P2 项未列入。

### A. 安装器/hook(运行=把自动外联写入用户环境)

- scripts/agent-panel/cutover-to-m5.sh — 装 LaunchAgents+launchctl bootstrap/bootout com.<ORIGINAL_AUTHOR>.agent-panel.*;curl -x 代理 cloudflare trace
- scripts/agent-panel/archive/20261123-ai-hub/install-hooks.py — 合并 hooks 进 ~/.claude/settings.json、~/.codex/hooks.json、kimi config.toml、~/.gemini/settings.json(先 backup)
- scripts/agent-panel/archive/20261123-ai-hub/bridge-hook.sh、codex-notify-wrapper.sh — stdin→curl POST receiver(max-time 2 后台)
- scripts/friends/install-friendacct.sh — scp+ssh bwg/akko/jprelay;systemctl enable --now rules+collect.timer
- scripts/icloud-archive/install-mac.sh — curl -LsSf https://＜astral＞/uv/install.sh | sh(远程管道安装);launchctl bootstrap icloud-archive
- scripts/icloud-archive/setup-photos-nfs-for-immich.sh — sudo NFS 挂;内联生成 root LaunchDaemon com.<ORIGINAL_AUTHOR>.photos-nfs RunAtLoad+bootstrap system
- scripts/ops/apply-baseline.sh — journald 封顶+restart/APT 清缓存/logrotate/conntrack/swap/tailscale-gro enable --now
- scripts/ops/timer-tuning/apply.sh — timer drop-in 20-freq.conf 重写;systemctl disable/restart
- scripts/ops/derper.service + derper-reload.sh — derper -hostname ＜AUTHOR_DOMAIN＞ -a :8443 -stun-port 3478 -certmode manual -verify-clients;hook restart derper
- scripts/ops/setup-videos-nfs-for-emby.sh — sudo NFS 只读挂;内联 root LaunchDaemon com.<ORIGINAL_AUTHOR>.emby-videos-nfs RunAtLoad+bootstrap system
- scripts/selfheal/install.sh — install -m 0600 selfheal.env;--enable→enable --now selfheal.timer
- scripts/selfheal/singbox-ai-probe.sh — 写 zz-ai-probe.json mixed 入站 127.0.0.1:19720;route.rules 插队;sing-box check+restart
- scripts/selfheal/singbox-ai-selector.sh — selector+clash_api(127.0.0.1+secret);openssl rand 生成 AI_CLASH_SECRET→env;IPRoyal 出站凭据自 env;jq 改 config;restart+回滚
- scripts/selfheal/singbox-harden-routes.sh — route.rules 封 private+CGNAT 目的地(防代理用户借道打内网);restart+回滚
- scripts/selfheal/singbox-ig-split.sh — IG 拆 ig-out;IGPROBE curl https://＜REMOTE＞/data/shared_data/;改 config+restart
- scripts/selfheal/singbox-resi-inbounds.sh — bwg 开 SS 住宅入站 resi-us/resi-ca;openssl rand -base64 16 口令;ufw allow 端口;restart;回显 ss://含口令
- scripts/selfheal/stagger-contabo-timers.sh、fix-freq-timers.sh — timer 错峰/单调→墙钟;daemon-reload+restart
- scripts/selfheal/mac/install-mac.sh — env 模板 0600→~/bin/selfheal.env(FILL_ME);launchctl bootout/bootstrap/enable gui
- scripts/selfheal/openwrt/selfheal.sh + install.sh + checks.router.sh + tg-notify.sh — busybox 引擎;init.d/docker restart;guarded_reboot 兜底;TG(--resolve 兜底);install 写 crontab

### B. 自动触发组件(装机/部署/启用=无人值守外联或副作用)

- scripts/tg-notify.sh — 触发:被 selfheal/pollers 自动调用
- scripts/agent-panel/push-to-contabo.py + com.<ORIGINAL_AUTHOR>.agent-panel.push.plist — 触发:RunAtLoad+StartInterval=120
- scripts/agent-panel/usage-collector.py + com.<ORIGINAL_AUTHOR>.agent-panel.usage.plist — 触发:RunAtLoad+StartInterval=600
- scripts/agent-panel/plan-usage.py + com.<ORIGINAL_AUTHOR>.agent-panel.plan-usage.plist — 触发:RunAtLoad+StartInterval=1800
- scripts/agent-panel/archive/20261123-ai-hub/receiver.py + com.<ORIGINAL_AUTHOR>.agent-panel.receiver.plist — 触发:RunAtLoad+KeepAlive
- scripts/agent-panel/archive/20261123-ai-hub/tg-hub.py + com.<ORIGINAL_AUTHOR>.agent-panel.tghub.plist — 触发:RunAtLoad+KeepAlive
- scripts/agent-panel/archive/20261123-ai-hub/tg-push.py + com.<ORIGINAL_AUTHOR>.agent-panel.tgpush.plist — 触发:RunAtLoad+StartInterval=30
- scripts/agent-panel/archive/20261123-ai-hub/autoloop.py + com.<ORIGINAL_AUTHOR>.agent-panel.autoloop.plist — 触发:RunAtLoad+StartInterval=180
- scripts/agent-panel/archive/20261123-ai-hub/summaries.py + com.<ORIGINAL_AUTHOR>.agent-panel.summaries.plist — 触发:StartInterval=300
- scripts/dashboard/poll-emby-relays.sh + .service/.timer — 触发:timer 30s
- scripts/dashboard/poll-emby-usage.sh + .service/.timer — 触发:timer 60s
- scripts/dashboard/poll-fleet.sh + .service/.timer — 触发:timer 30s
- scripts/dashboard/poll-web.sh + .service/.timer — 触发:timer 60s
- scripts/dashboard/cloud-quota.py + cloud-quota-minute.conf/cloud-quota-balanced.conf — 触发:每分钟/每 5 分钟
- scripts/emby-relay/emby-failover.sh + emby-failover.timer — 触发:每分钟
- scripts/emby-relay/emby-evac.sh — 触发:OpenWrt cron */2
- scripts/emby-relay/emby-upstream-reload.sh + timer — 触发:5min Persistent
- scripts/emby-relay/emby-{as,eu,hub,jp,na}.nginx(5 个) — 触发:部署
- scripts/emby-relay/nginx-restart.conf — 触发:部署
- scripts/entry/entry-failover.sh — 触发:OpenWrt cron */2
- scripts/entry/web-relay-443.service、web-relay-80.service — 触发:开机 Restart=always
- scripts/entry/hk-cmi-stream.conf — 触发:部署
- scripts/friends/friendsd.py + friendsd.service — 触发:Restart=always
- scripts/friends/friends-apply.py + friends-apply.timer — 触发:60s
- scripts/friends/friendacct-collect.py + timer — 触发:60s
- scripts/friends/friendacct-rules.sh + service — 触发:开机 oneshot
- scripts/friends/mirror-apps.py + mirror-apps.timer — 触发:周一 05:30 Persistent
- scripts/hy2-hop/hy2-hop.sh + hy2-hop.service — 触发:开机 oneshot
- scripts/icloud-archive/icloud-archive.sh + plist — 触发:每日 04:00
- scripts/icloud-archive/icloudpd-weekly.sh + plist — 触发:周日 07:00
- scripts/icloud-archive/com.<ORIGINAL_AUTHOR>.immich-ml-socat.plist — 触发:RunAtLoad+KeepAlive
- scripts/ops/cf-ddns.sh + cf-ddns.timer — 触发:15min
- scripts/ops/block-watch.sh — 触发:OpenWrt cron 25 */3
- scripts/ops/tg-quota.sh + timer — 触发:每小时 Persistent
- scripts/ops/sub-userinfo.sh + .service/.timer — 触发:每小时
- scripts/ops/kiwivm-poll.sh + timer — 触发:5min
- scripts/ops/mp-autoupdate.sh(+mp-autoupdate.env.example) — 触发:群晖 DSM 任务计划 root
- scripts/ops/emby-autosub.py + plist — 触发:每小时
- scripts/ops/emby-posterfill.py + plist — 触发:RunAtLoad+1800
- scripts/ops/emby-fix-dateadded.py + plist — 触发:1800
- scripts/ops/emby-token-dump.sh + plist — 触发:RunAtLoad+900
- scripts/ops/emby-backup.sh + plist — 触发:每日 03:30
- scripts/ops/macmini-config-backup.sh + plist — 触发:周日 06:30
- scripts/ops/fleet-speedtest.sh — 触发:周日 21:30 launchd(plist 不在库)
- scripts/ops/scheduled-reboot.service + .timer — 触发:周日 04:00(按机错峰)
- scripts/ops/mac-status.py — 触发:launchd com.<ORIGINAL_AUTHOR>.macstatus KeepAlive(plist 不在库)
- scripts/ops/openwrt-home-proxy.init — 触发:开机 START=95 respawn 3600 5 5
- scripts/ops/tokyo-server/docker-user-fw.service — 触发:开机
- scripts/ops/fleet-baseline/51homelab-origins(.tokyo-server) — 触发:部署
- scripts/peer-relay/relay-pref.sh — 触发:cron #relay-pref
- scripts/selfheal/selfheal.sh + selfheal.service + selfheal.timer — 触发:OnBootSec=3min+OnCalendar=*:0/2
- scripts/selfheal/checks.{akko,bwg,contabo,hklisa,hkrelay,lisa,malaysia,vmiss}.sh(8) — 触发:部署
- scripts/selfheal/lib.external-watch.sh — 触发:部署
- scripts/selfheal/mac/selfheal-mac.sh + plist — 触发:RunAtLoad+120s
- scripts/selfheal/mac/tailscale-health.sh — 触发:装机
- scripts/selfheal/mac/colima/immich-colima-up.sh + plist — 触发:RunAtLoad
- scripts/smsbus/smsbus.py + Dockerfile(compose build) — 触发:restart unless-stopped
- scripts/smsbus/senders.py — 触发:容器
- backups/dashboard/docker-compose.yml — 触发:restart unless-stopped×7
- backups/dashboard/Caddyfile — 触发:部署
- backups/dashboard/authsvc/app.py — 触发:compose 自启
- backups/immich/docker-compose.yml — 触发:restart always×4
- backups/immich/immich-colima-up.sh、immich-nfs-mount.sh — 触发:launchd RunAtLoad

### C. 手动但执行即外联/需凭据(未经授权不得转载运行)

- scripts/agent-panel/router.py — SSH 别名 m5
- scripts/agent-panel/control.py — CLI OAuth
- scripts/agent-panel/agent-relay.py — CLI OAuth
- scripts/agent-panel/install-mcp.py — 无
- scripts/agent-panel/sync_leaderboard.py — 无
- scripts/agent-panel/kimi-quota.py — Kimi API key
- scripts/agent-panel/gemini-usage.py、claude-plan-usage.py、claude-usage-report.py、codex-usage.py、usage-collector.sh — CLI OAuth
- scripts/agent-panel/archive/20261123-ai-hub/orchestrator.py — CLI OAuth
- scripts/agent-panel/archive/20261123-ai-hub/reauth.py — OAuth
- scripts/agent-panel/archive/20261123-ai-hub/delegate-run.sh、ai-dispatch.py、scavenger.py — control.token
- scripts/dashboard/poll-extras.sh — EMBY key
- scripts/dashboard/clash-stats.sh — CLASH_SECRET
- scripts/dashboard/sync-minimax-key.sh→sync-minimax-key.py — MINIMAX key+SSH
- scripts/dashboard/snmp-nas.py — SNMP community
- scripts/emby-relay/emby-hub-watch.sh — SSH 别名
- scripts/emby-relay/emby-egress-peaktest.sh — EMBY key+TG+SSH
- scripts/icloud-archive/immich-ml-toggle.sh — Immich 账号
- scripts/icloud-archive/icloud-hidden-vault.sh — vault 密码
- scripts/ops/fleet-config-backup.sh — SSH 别名+age
- scripts/ops/istoreos-config-backup.sh — SSH
- scripts/ops/decrypt-backup.sh — age 私钥(git 外)
- scripts/ops/peak-retest-20260704.sh — 无
- scripts/ops/peak-retest-hklisa.sh — SSH+TG
- scripts/ops/portable-ssd.sh — SSH
- scripts/ops/lucky-admin-tunnel.sh — SSH
- scripts/ops/sync-sub.sh — git remote(作者 clash-config 仓库)
- scripts/ops/emby-covers.py — EMBY key
- scripts/ops/emby-rebuild-9libs.py、emby-rebuild-libraries.py — EMBY key
- scripts/subtrans/translate_subs.py — AI key+EMBY key+SSH
- scripts/subtrans/finish5.py — SSH
- sms-forwarder/SmsForwarder-FindN6.json — Bark key+webhook secret+frp token
- sms-forwarder/SmsForwarder-ZFlip7.json — 同上
- backups/*-config-backup.tgz.age(9:akko/bwg/contabo/hklisa/hkrelay/istoreos/jprelay/lisa/malaysia) — age 私钥(git 外)

### D. 配置导入/解密(导入或解密即激活外发/暴露密钥)

- sms-forwarder/SmsForwarder-FindN6.json、SmsForwarder-ZFlip7.json — 导入手机 App 即按 rule 自动把短信/来电转发到作者 Bark+webhook;frpc config 含 server_addr+auth token(autorun=0,手动开启即建隧道)。
- backups/*-config-backup.tgz.age(9 个)— 解密需 age 私钥(git 外);密文内含舰队 /etc 全量密钥,不得未经授权解密/传播。
- backups/dashboard/glance.yml — 含真实订阅 token 与 MoviePilot token(已退役,仍敏感)。
- 00-密码总表.md — 全类型凭据明文表;不得复制/传播/写入长期记忆。

## 七、CI 与历史自动化

- 【已验证】当前无 .github/workflows 或任何 CI 配置;`git log --all --diff-filter=A --name-only` 全历史从未添加 .github/workflow/gitlab-ci/Jenkinsfile/circleci/drone/woodpecker/azure-pipelines/.travis/buildkite 文件。
- 【已验证】历史曾存在、现已删除的自动化文件:
  - commit **5bed1c3**(2026-10-14,「MC 服彻底下线清除」)删除 scripts/mc/ 9 文件:README.md、chunky-guard.sh、mc-backup.service、mc-backup.sh、mc-backup.timer、mc-status.py、mc-status.service、mc-status.timer。git show 取证:mc-backup.timer OnCalendar=*-*-* 05:15:00 Persistent=true;mc-backup.service ExecStart=/usr/local/bin/mc-backup.sh(本地 rsync --delete 快照+tar+失败 TG+rm -f 旧备份);mc-status.timer OnBootSec=3min OnUnitActiveSec=2min;mc-status.service ExecStart=/usr/local/bin/mc-status.py→/opt/svcstatus/mc.json。
  - commit **1d599d4**(2026-11-16,「retire hub speedtest alerts」)删除 scripts/emby-relay/com.<ORIGINAL_AUTHOR>.emby-hub-watch.plist(Label com.<ORIGINAL_AUTHOR>.emby-hub-watch;/bin/bash /Users/＜AUTHOR_HOME＞/emby-hub-watch.sh;未见 RunAtLoad/StartInterval/KeepAlive 键)。对应脚本 emby-hub-watch.sh 仍在库(手动 ssh contabo curl 60MB)。
- 【已验证】push 已禁用(remote push url=no_push_disabled),本审计未做任何 git 写操作。

## 八、凭据/隐私暴露面(仅指纹,不含值)

### 8.1 关键定位指纹(sha8)

| 文件:行 | 类型 | sha8 | 核实备注 |
|---|---|---|---|
| backups/dashboard/authsvc/app.py:9 | token_kv | 56fe7abc | 【已验证】实为 SECRET=env 派生,非硬编码凭据;AUTH_SECRET 缺失即 RuntimeError |
| scripts/agent-panel/archive/20261123-ai-hub/tg-push.py:100 | token_kv | b2868aaa | TG bot token 正则提取源 |
| scripts/agent-panel/archive/20261123-ai-hub/tg-push.py:12 | chat_id | 851442e5 | TG chat id |
| scripts/agent-panel/control.py:1027 | token_kv | 1f574549 | control.token 相关 |
| scripts/agent-panel/archive/20261123-ai-hub/web/app.js:8 | token_kv | 99c7ebe7 | 前端 TOKEN 变量 |
| scripts/ops/fleet-config-backup.sh:12 | b64 | 768f5d7f | SSH 别名列表 blob |
| scripts/ops/mp-autoupdate.sh:53 | b64 | 04bb051e | docker-compose 路径变体 |
| scripts/ops/sync-sub.sh:15/19/52 | b64/hex | 79b2ae52/b6cc32df/1e900253 | 【已验证】订阅路径 token(16-hex)硬编码 10+ 处(:7 等) |
| backups/immich/docker-compose.yml:57/64 | hex | ba6ba317/fe1529c8 | 【已验证】image digest 钉版,非凭据 |
| sms-forwarder/SmsForwarder-FindN6.json:9 | uuid | d213d161 | 设备标识 |
| sms-forwarder/SmsForwarder-FindN6.json:108 | b64 | 19aa1d3b | 通道密钥类 |
| sms-forwarder/两机 | url | 723af2e0 | frpc config(本地字符串,含 server_addr+auth token) |
| sms-forwarder/两机 | url | 87fdcd4e | Bark server 域名 |
| sms-forwarder/两机 | url | e30f3680 | webhook 目标域名(smsbus) |
| 00-密码总表.md:110-227 | uuid×33 | — | 节点 UUID 群 |
| 00-密码总表.md:18-19 | email×6 | — | 真实邮箱 |
| .age-recipients:2 | age 公钥 | — | 公钥非私钥;注释私钥仅存 git 外 |

### 8.2 全仓扫描聚合(occurrences/unique sha8)

- email 47/26;http_url 826/459;ipv4 1255/179(public 138/private 18/cgnat 23);long_b64 129/90;long_hex 69/46;phone_cn 2/2;sub_url 6/6;token_kv 9/8;uuid 77/38。tg_bot_token/private_key_block/password_kv 正则零命中(密码以表格形式存于 00-密码总表.md,格式未匹配正则)。
- URL host 分类(unique):remote_host 255、ip_private 30、github 17、local 58、tailscale 3、cgnat 39、ip_public 15、openai 5、registry 14、cloudflare 4、apple_icloud 2、google 11、telegram 5。
- .gitignore【已验证】排除:clash-merged-repo/(作者独立子仓库)、*.key/*.pem/*id_ed25519*/*id_bwg_node*/*homelab_nas*/*id_dmit* 等私钥、*.env(保留 .example/.template)、backups/*-config-backup.tgz 明文、*.age.key、whisperlivekit/.venv。即:私钥与明文 env 不在库,但 00-密码总表.md、age 密文、plist、脚本内嵌 token 路径仍在库。

## 九、nginx 对外暴露面(已脱敏摘录)

```
### scripts/emby-relay/emby-as.nginx
  3: # 家→hklisa 是唯一能扛单流的中国出境腿(晚高峰 13–18M)。DDNS 换 IP 由 emby-upstream-reload.timer 兜。
  24: upstream emby_home_as { server ＜IP:CGNAT＞:233; keepalive 8; }   # 2026-10-30 hklisa 公网 IP 被墙(TCP)→ 走 tailnet 直连家路由(UDP/WireGuard,同走 CMI;tailnet IP 固定,无需 upstream-reload)
  27: listen ＜IP:LOOP＞:8444 ssl proxy_protocol;   # 2026-10-15 前置 stream SNI 分流(/etc/nginx/stream-entry.conf)
  30: listen 8920 ssl;           # 2026-10-30 统一入口 ＜DOMAIN＞:8920(四台同口)
  31: listen [::]:8920 ssl;
  32: server_name ＜DOMAIN＞ ＜DOMAIN＞;   # 2026-10-30 tv = 统一入口(DNS 故障切换,doc50)
  34: ssl_certificate     /etc/letsencrypt/live/＜DOMAIN＞/fullchain.pem;
  59: location ~* /(emby/)?Users/.*Authenticate {
  61: proxy_pass https://＜HOST:REMOTE＞
  65: location ~* ^/(emby/)?(videos|audio|items/[^/]+/download)(/|$) {
  66: proxy_pass https://＜HOST:REMOTE＞
  69: location / {
  70: proxy_pass https://＜HOST:REMOTE＞
### scripts/emby-relay/emby-eu.nginx
  25: upstream emby_home_eu { server emby-home-v4:233; keepalive 8; }   # 2026-10-15 只走 IPv4(见 emby-upstream-reload.sh)
  28: listen 443 ssl;
  29: listen [::]:443 ssl;
  30: listen 8920 ssl;           # 2026-10-30 统一入口 ＜DOMAIN＞:8920(四台同口)
  31: listen [::]:8920 ssl;
  32: server_name ＜DOMAIN＞ ＜DOMAIN＞;   # 2026-10-30 tv = 统一入口(DNS 故障切换,doc50)
  34: ssl_certificate     /etc/letsencrypt/live/＜DOMAIN＞/fullchain.pem;
  59: location ~* /(emby/)?Users/.*Authenticate {
  61: proxy_pass https://＜HOST:REMOTE＞
  65: location ~* ^/(emby/)?(videos|audio|items/[^/]+/download)(/|$) {
  66: proxy_pass https://＜HOST:REMOTE＞
  69: location / {
  70: proxy_pass https://＜HOST:REMOTE＞
### scripts/emby-relay/emby-hub.nginx
  6: # 证书:certbot --dns-cloudflare(复用 /etc/letsencrypt/cloudflare.ini,从 akko 拷入)。DDNS 追 IP:emby-upstream-reload.timer。
  27: upstream emby_home_hub { server emby-home-v4:233; keepalive 8; }   # 只走 IPv4(见 emby-upstream-reload.sh)
  30: listen 8443 ssl;
  31: listen [::]:8443 ssl;
  32: listen 8920 ssl;           # 2026-10-30 统一入口 ＜DOMAIN＞:8920(四台同口)
  33: listen [::]:8920 ssl;
  34: server_name ＜DOMAIN＞ ＜DOMAIN＞;   # 2026-10-30 tv = 统一入口(DNS 故障切换,doc50)
  36: ssl_certificate     /etc/letsencrypt/live/＜DOMAIN＞/fullchain.pem;
  63: location ~* /(emby/)?Users/.*Authenticate {
  65: proxy_pass https://＜HOST:REMOTE＞
  69: location ~* ^/(emby/)?(videos|audio|items/[^/]+/download)(/|$) {
  70: proxy_pass https://＜HOST:REMOTE＞
  73: location / {
  74: proxy_pass https://＜HOST:REMOTE＞
### scripts/emby-relay/emby-jp.nginx
  7: upstream emby_home_jp { server ＜DOMAIN＞:233; keepalive 8; }
  10: listen 8443 ssl;
  11: listen [::]:8443 ssl;
  12: server_name ＜DOMAIN＞;
  14: ssl_certificate     /etc/letsencrypt/live/＜DOMAIN＞/fullchain.pem;
  39: location ~* /(emby/)?Users/.*Authenticate {
  41: proxy_pass https://＜HOST:REMOTE＞
  44: location / {
  45: proxy_pass https://＜HOST:REMOTE＞
### scripts/emby-relay/emby-na.nginx
  3: # 家里/Emby 不改;bwg 像浏览器一样回源已在跑的公网口。DDNS 换 IP 由 emby-upstream-reload.timer 兜(定时 reload)。
  24: upstream emby_home_na { server ＜IP:CGNAT＞:233; keepalive 8; }   # 2026-10-15 只走 IPv4(见 emby-upstream-reload.sh)
  27: listen 443 ssl;
  28: listen [::]:443 ssl;
  29: listen 8920 ssl;           # 2026-10-30 统一入口 ＜DOMAIN＞:8920(四台同口)
  30: listen [::]:8920 ssl;
  31: server_name ＜DOMAIN＞ ＜DOMAIN＞;   # 2026-10-30 tv = 统一入口(DNS 故障切换,doc50)
  33: ssl_certificate     /etc/letsencrypt/live/＜DOMAIN＞/fullchain.pem;
  60: location ~* /(emby/)?Users/.*Authenticate {
  62: proxy_pass https://＜HOST:REMOTE＞
  66: location ~* ^/(emby/)?(videos|audio|items/[^/]+/download)(/|$) {
  67: proxy_pass https://＜HOST:REMOTE＞
  70: location / {
  71: proxy_pass https://＜HOST:REMOTE＞
### scripts/entry/hk-cmi-stream.conf
  4: #   其余(status/auth/ntfy/smsbus/sna)→ ＜IP:LOOP＞:9443 剥掉 PROXY 头 → tokyo-server Caddy(tailnet)TLS 透传
  12: listen 443;
  13: listen [::]:443;
  16: proxy_pass $entry_backend;
  20: listen ＜IP:LOOP＞:9443 proxy_protocol;
  21: proxy_pass ＜IP:CGNAT＞:443;
  25: listen 80;
  26: listen [::]:80;
  27: proxy_pass ＜IP:CGNAT＞:80;
### scripts/ops/dec1-bwg-cutover/nginx-443-sni-mux.conf.template
  9: #        listen ＜IP:LOOP＞:18443 ssl http2 proxy_protocol;
  29: upstream singbox_reality_backend {
  31: server ＜IP:LOOP＞:＜NEW_REALITY_PORT＞;
  34: upstream nginx_tls_internal {
  35: server ＜IP:LOOP＞:18443;
  39: listen ＜IP:LOOP＞:443 reuseport;
  40: listen [::]:443 reuseport;
  44: proxy_pass $sni_upstream;
  51: #   (a) keep `proxy_protocol off` (default above) and leave :18443 as standard `listen ＜IP:LOOP＞:18443 ssl http2;`
```

## 十、方法论与局限

- 【已验证】本报告所有路径/行号/参数来自只读 read/cat/git show/plistlib/python 结构解析;扫描器覆盖全部 442 文件(危险模式:ssh/scp/rsync/sshpass/curl 写/wget/nc/telegram/webhook/launchctl/systemctl/docker compose up/crontab/@reboot/RunAtLoad/StartInterval/gh api 写/git push/force push/rm -rf/iptables/nft/ufw/age -d/openssl enc/LLM API/tailscale/socat/用户环境写入)。
- 【推测】风险级为静态代码/配置判断;作者设备实际部署/运行状态未知,未实机核实。
- 【推测】部分调度来自脚本注释/README(poll-extras 15s、snmp-nas 2min、fleet-speedtest 周日 21:30、mac-status com.<ORIGINAL_AUTHOR>.macstatus KeepAlive),对应 plist/unit 不在仓库,无法核实是否现役。
- age 密文未解密(私钥在 git 外,且未经授权不得解密);sms-forwarder settings 字段为字符串未展开(设备隐私);根目录 58 个 md 为结构扫描+抽查,非逐行精读;backups/dashboard/web 静态门户未逐文件审计(Caddyfile 注释提及其含内联 AP_TOKEN 脚本)。
- 本审计未执行任何仓库脚本、未发起网络请求、未修改仓库;产出仅写入 reports/danger-audit.md(本人目录)。
