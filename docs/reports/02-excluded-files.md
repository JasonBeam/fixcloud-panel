# 交付 2｜脱敏与"整体不入库"文件清单

- 原则：**个人身份 / 学业 / 生活流程 / 加密备份 / 集中凭据 → 整体不进入知识库**；技术文档 → 保留设计思想，值全部占位符化。
- 占位符约定（见 `kb/ATTRIBUTION.md`）：`example.com` / `node-a.example.com`、`192.0.2.10`、`198.51.100.20`、`203.0.113.30`、`2001:db8::10`、UUID `00000000-0000-4000-8000-000000000000`、`<EXAMPLE_SS2022_KEY_BASE64_16B>`、`<EXAMPLE_REALITY_PRIVATE_KEY>`、`<EXAMPLE_SUB_TOKEN>`、`user@example.com`。
- 作者统一写"原作者"；保留归属，不冒充。

## A. 整体不进入知识库（删除 / 不复制）

| 类别 | 路径 | 理由 |
|---|---|---|
| 集中凭据 | `00-密码总表.md` | UUID×33、邮箱×6；集中凭据索引 |
| 加密备份 | `backups/akko-config-backup.tgz.age`、`bwg-`、`contabo-`、`hklisa-`、`hkrelay-`、`istoreos-`、`jprelay-`、`lisa-`、`malaysia-`（9 个） | X25519 加密无法扫描，按命名含原始配置与凭据 |
| 加密身份 | `.age-recipients` | age 公钥 = 身份标识 |
| 短信设备 | `sms-forwarder/SmsForwarder-ZFlip7.json`、`sms-forwarder/SmsForwarder-FindN6.json` | 设备型号 / 手机号 / 转发目标 / webhook / 账号 |
| 学业 | `HKU_2026-27_Sem1_课程清单.xlsx` | 课表/学分，含 78 个邮箱单元格 |
| 学业 | `HKU_UBC_TransferCredit_Approved.xlsx` | 转学分记录 |
| 学业 | `HKU_Sem1_Schedule.png`、`HKU_Sem1_Schedule_v2.png` | 个人课表图片 |
| 学业 | `hku-tcp/DASE3159_SIS_CourseInfo_and_Syllabus_2026-27.pdf`、`DASE3159_Syllabus_HKU2026-27.pdf`、`ELEC3544_Syllabus_HKU2026-27_and_CourseInfo.pdf`、`ELEC3644_CourseInformation.pdf`、`ELEC3644_SIS_CourseInfo_and_CourseInformation_2026-27.pdf`、`hku-tcp/TCP_additional_info.md` | 课程大纲/学业信息，1 PDF 含 Author 字段 |
| 学业 | `42-HKU选课-Hongxi.md` | 文件名含人名，email×17 |
| 学业 | `backups/dashboard/ui/elec3347/ELEC3347-A4-CheatSheet.pdf` 及该目录学业资料 | 课程资料 |
| 个人学习 | `39-韩语学习-plan.md`、`korean/README.md`、`korean/hanja-top300.tsv` | 个人学习计划 |
| 个人兴趣 | `40-DancePick-跳舞选片.md` | 个人选片 |
| 个人身份 | `36-Jimmy设计语.md` | 作者个人设计语/身份（如需保留，仅提炼抽象设计原则） |
| 个人计划 | `18-养站考核.md` | 个人养站计划/考核 |
| 个人课表 | `scripts/fnd/betty_timetable.html`、`docs/superpowers/specs/2026-09-11-fnd-schedule-design.md` | 含人名的个人课表 |
| 生活流程 | `21-iCloud照片归档.md`、`22-安卓照片备份-Immich.md`、`23-短信转发-SmsForwarder.md` | 个人照片/短信流程与设备（手机号×2、email×3） |
| 截图 | `reports/status-20261116/*.jpg`（7 张） | 真实会话路径/账单/界面隐私（EXIF 无 GPS，但画面内容含隐私） |
| 真实 env | `scripts/selfheal/selfheal.env`、`scripts/selfheal/openwrt/selfheal.env` | 被跟踪的 `.env`；前者注释含真实公网 IPv4×2 + 域名×1（**无凭据**，见交付 1 §7） |
| **自动触发器** | **21 个 `*.plist`**（`scripts/agent-panel/` 3 现役 + 5 归档、`scripts/selfheal/`、`scripts/emby-relay/` 等；Label 全含作者名，ProgramArguments 指向原作者家目录） | 装机/启用即无人值守外联；**一律不入库** |
| **自动触发器** | **23 个 `.service` + 14 个 `.timer` + 6 个 `.conf`**（`scripts/dashboard/`、`scripts/emby-relay/`、`scripts/entry/`、`scripts/friends/`、`scripts/hy2-hop/`、`scripts/ops/`、`scripts/selfheal/`） | 含周日 04:00 自动重启整机、群晖 root 自动部署、OpenWrt `*/2` 自愈；**一律不入库**，只在文档中描述设计思想 |
| **自动触发器** | **9 条 cron/任务计划**（OpenWrt crontab、Mac cron、群晖 DSM 任务计划，散见于脚本注释与文档） | 同上；文档中保留"调度周期与判据"的抽象描述，去掉真实主机与命令 |
| **安装器/hook** | `scripts/agent-panel/install-mcp.py`、`cutover-to-m5.sh`、`sync_leaderboard.py` 等（写 `~/.claude.json`、`~/.codex/config.toml`、`~/.gemini`、LaunchAgents） | 运行=把自动外联写入用户环境；**不入库** |
| **已退役归档** | `scripts/agent-panel/archive/20261123-ai-hub/`（含 5 个 KeepAlive/定时 plist、`receiver.py`、`test_mission_control.py`） | 已退役但仍在库且含凭据特征；**整目录不入库** |
| **远程管道安装** | 引用 astral uv 远程安装脚本的命令 | 不入库；如需保留经验，改写为"先下载校验再安装"的通用建议 |

> 注：`scripts/fnd/`（四校课表→.ics）与 `scripts/subtrans/`（字幕 AI 翻译）**与节点/订阅无关**，不纳入技术知识库；其中通用工程思想如需保留，另行抽象提炼。

## B. 进入知识库但必须值级脱敏（保留结构 / 字段 / 原理）

| 路径 | 需替换的类型 |
|---|---|
| `06-节点信息与链接.md`、`08-备份节点Akko-链接.md`、`12-订阅服务器与新增节点.md`、`27/28/29/30-*.md` | UUID、SS2022 密钥、订阅链接 token、邮箱、服务器地址/端口、节点名中的身份线索 |
| `40-朋友版订阅-friends.md` | **gitleaks 0 命中 → 中文规则 + 人工复核**（朋友凭据、线路 id、账号） |
| `scripts/selfheal/singbox-resi-inbounds.sh` | 密码赋值×5 |
| `scripts/friends/friendsd.py` | secret 赋值 |
| `scripts/dashboard/poll-web.sh`、`poll-fleet.sh`、`backups/dashboard/glance.yml` | 订阅 URL token |
| `scripts/ops/fleet-speedtest.sh`、`scripts/icloud-archive/icloudpd-weekly.sh` | 邮箱 / 主机标识 |
| `backups/dashboard/docker-compose.yml`、`authsvc/app.py`、`ui/next/applications.json`、`backups/immich/docker-compose.yml` | 域名 / 邮箱 / 密钥字段 |
| `01/02/21/41/FINDINGS.md`、`32/48/14-*.md`、`docs/superpowers/plans/2026-07-23-smsbus-短信总线.md` | curl 内嵌账号密码、API key、webhook |
| 全部技术文档 | 公网/内网/Tailscale IP → RFC5737/RFC1918 示例；个人域名 → example.com；设备别名 → `node-a`/`nas-a`；ASN/机房名 → "某机房" |

## C. 可保留原样（低风险 / 公共资产）

- 第三方 vendor 代码（如 `backups/dashboard/ui/next/vendor/maplibre/maplibre-gl.js`）：**不复制进知识库**（体积大、非原创经验），只在文档中说明"用了哪个开源组件"。
- 公共 DNS IP、公共服务域名、回环/保留段、文档示例段、版本号：无需替换。
- `*.env.example` / `*.env.template`：保留结构，确认值为占位符（`scripts/selfheal/mac/selfheal.env.template` 的 Telegram chat id 需替换）。

## D. 知识库侧产出状态

- 已完成并通过验收门（0 残留）：`kb/drafts/03-singbox-mihomo-clash.md`、`04-multi-node-architecture.md`、`05-subscription-server.md`、`06-token-auth-user-management.md`、`10-anti-censorship.md`。
- 待补（`kb-ops` 子代理进行中）：01 VPS 基线、02 Docker/systemd、07 DNS/DDNS/TLS/反代、08 流量监控自愈、09 SSH 加固最小权限、11 故障案例、12 FixCloud 迁移。
- 汇编为正式 `kb/` 12 篇后，本清单 B 节将补充"逐文件脱敏映射表"。
