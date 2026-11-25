# 交付 1｜仓库隐私风险清单（仅路径 + 凭据类型，不回显真实值）

- 对象：`JasonBeam/homelab`（Private，Fork 自 `JimmyChan233/homelab`，默认分支 main）
- 审计副本：`/Users/beamjason/Documents/GitHub/homelab-sanitize/fork-clone`（**push 已禁用**：remote push url = `no_push_disabled`）
- 口径：命中次数 = 正则命中；去重值 = sha256 前 8 位指纹去重；**任何真实值均不出现在本报告与所有 JSON 中**（gitleaks 使用 `--redact`）。
- 逐文件明细见 `reports/privacy-inventory.md` §8（241 个文件）；本文件是执行摘要。
- 标注：【已验证】= 本次实测；【推测】= 工程判断；【未验证】= 待确认。

## 0. 基线【已验证】

| 项 | 值 |
|---|---|
| 跟踪文件 | 442（411 文本 + 31 二进制） |
| 历史 commit | 443（gitleaks 扫 442） |
| 分支 / Tag | 单分支 main / **0 tag** |
| 远程 refs | 仅 HEAD 与 refs/heads/main = `f7f2cadcfd01f4f147a12308b8afa1c1489d7d0b` |
| GitHub Actions | **无 .github/workflows**（当前工作区） |
| hooks / submodule / LFS / gitlink | 无 active hooks、无 .gitmodules、无 LFS、无 gitlink |
| 可执行跟踪文件 | 42 个（100755） |
| 许可证 | **licenseInfo = null（无许可证）** → 只提炼设计思想，不复制源码发布 |
| commit 作者元数据 | 439 条 `原作者 <<ORIGINAL_AUTHOR_EMAIL>>`、4 条 `原作者 <<ORIGINAL_AUTHOR_EMAIL>>`（**PII，存在于全部历史 commit**） |
| 曾跟踪文件总数 | 513 → 现 442，**71 个已删/改名**（旧内容仍在历史中） |

## 1. 风险大类计数【已验证】

| 大类 | 类型 | 命中 | 去重值 | 涉及文件 | 严重级 |
|---|---|---:|---:|---:|---|
| 凭据 | UUID v4 | 78 | 39 | 11 | 高 |
| 凭据 | 密码字段 | 11 | 11 | 8 | 高 |
| 凭据 | token 字段 | 15 | 12 | 12 | 高 |
| 凭据 | secret / APIkey **字段名** | 8 | 6 | 7 | 高 |
| 凭据 | SS2022 候选密钥（16/32B base64） | 9 | 6 | 7 | 高 |
| 凭据 | 订阅 / 节点链接 | 11 | 10 | 3 | 高 |
| 凭据 | 订阅 URL 特征 / token 参数 | 2 + 2 | 2 + 2 | 2 + 2 | 高 |
| 凭据 | URL 内嵌账号密码 | 6 | 5 | 4 | 高 |
| 凭据 | Cookie | 13 | 5 | 3 | 高 |
| 凭据 | Webhook / 推送 URL | 30 | 16 | 21 | 高 |
| 凭据 | Telegram chat id | 3 | 2 | 3 | 高 |
| 凭据 | 长 base64 串（疑似密钥/订阅体） | 133 | 94 | 61 | 中 |
| 凭据 | Reality **配置行**（非私钥值） | 342 | 7 | 51 | 中 |
| 凭据 | SS 配置行 | 32 | 4 | 19 | 中 |
| 网络标识 | 疑似公网 IPv4 | 521 | 94 | 74 | 中 |
| 网络标识 | 内网 IPv4 | 159 | 21 | 45 | 中 |
| 网络标识 | Tailscale / CGNAT IPv4 | 247 | 23 | 79 | 中 |
| 网络标识 | 疑似个人 / 基础设施域名 | 1112 | 212 | 136 | 中 |
| 网络标识 | 机构 / 学业域名 | 24 | 14 | 2 | 中 |
| 个人身份 | 邮箱 | 47 | 26 | 18 | 中 |
| 个人身份 | 疑似 +86 手机号 | 22 | 7 | 8 | 中 |
| 个人身份 | age 公钥（身份标识） | 1 | 1 | 1 | 中 |
| 定位线索 | 中文敏感关键词行（订阅414/密码209/手机153/账号98/密钥93/令牌53/邮箱16/身份证2） | 971 | — | 135 | 低 |

**全仓 0 命中的类型【已验证】**：Reality 私钥字段值、已知厂商 API key 前缀（ghp_ / github_pat_ / sk- / AKIA / xoxb- / AIza）、JWT、Bearer token、PEM 私钥头、SSH 公钥、Telegram Bot Token、18 位身份证候选、+852 手机号、可解码订阅 base64 体。
→ **含义**：这些秘密**不在仓库明文**，而是按 `00-密码总表.md` 的外置索引指向宿主机 0600 `.env` / 加密备份 / 密码管理器。**不等于它们不存在**，且历史明文 tar 备份中可能含有（见交付 5）。

## 2. 最高优先：`00-密码总表.md`【已验证】

- 集中式凭据索引，**UUID v4 命中 33 处（全仓 39 个不同值中的大部分）**、邮箱 6 处；gitleaks 自定义规则在该文件命中 39 条。
- 处置：**整体不进入知识库**。若需保留"密码总表应如何组织"的方法论，只提取**表头结构与分类思想**，所有值替换为 `<EXAMPLE_*>`。

## 3. 节点与订阅文档（高危路径）【已验证】

| 路径 | 命中类型（gitleaks 自定义规则） |
|---|---|
| `12-订阅服务器与新增节点.md` | uuid×14、ss2022-key×3、subscription-url-token×1 |
| `06-节点信息与链接.md` | uuid×6、email×3 |
| `08-备份节点Akko-链接.md` | uuid×6、email×3 |
| `27-*.md` / `28-*.md` / `29-*.md` / `30-*.md`（节点文档） | 各 uuid×4 + ss2022-key×1 |
| `40-朋友版订阅-friends.md` | **gitleaks 0 命中 → 需中文规则 + 人工复核**（朋友凭据/线路 id 可能以中文描述承载） |
| `scripts/selfheal/singbox-resi-inbounds.sh` | cn-password-assignment×5 |
| `scripts/friends/friendsd.py` | generic-secret-assignment |
| `scripts/dashboard/poll-web.sh` / `poll-fleet.sh` | subscription-url-token |
| `backups/dashboard/glance.yml` | subscription-url-token |

## 4. 凭据载体【已验证】

| 路径 | 事实 | 处置 |
|---|---|---|
| `backups/*.tgz.age`（9 个：akko / bwg / contabo / hklisa / hkrelay / istoreos / jprelay / lisa / malaysia） | X25519 recipient 加密，**无法解密扫描**；按命名含原始配置与凭据 | **整体删除，不进知识库** |
| `.age-recipients` | 2 行，含 1 个 age 公钥（身份标识） | 删除 |
| `backups/immich/.env.template`、`backups/dashboard/.env.example` | 模板/示例（占位符为主） | 可保留结构，值占位符化 |
| `sms-forwarder/SmsForwarder-ZFlip7.json`、`SmsForwarder-FindN6.json` | 设备型号 / 手机号 / 转发目标 / webhook / 账号 | **整体删除** |
| `scripts/selfheal/mac/selfheal.env.template` | Telegram chat id×1（L4） | 占位符替换 |
| `scripts/selfheal/selfheal.env` | **见 §7 复核纠正** | 移除跟踪 + 注释脱敏 |
| `scripts/selfheal/openwrt/selfheal.env` | **见 §7 复核纠正** | 移除跟踪（卫生问题） |

## 5. 个人身份与学业隐私【已验证】

- 邮箱 47 处（26 个不同值）；学业 xlsx 另有 **78 个邮箱单元格**；+86 手机号 22 处（7 个值）。
- 学业/个人二进制与文档：`HKU_2026-27_Sem1_课程清单.xlsx`、`HKU_UBC_TransferCredit_Approved.xlsx`、`HKU_Sem1_Schedule.png`、`HKU_Sem1_Schedule_v2.png`、`hku-tcp/`（5 PDF + TCP_additional_info.md）、`42-HKU选课-Hongxi.md`（文件名含人名，email×17）、`39-韩语学习-plan.md`、`korean/`、`40-DancePick-跳舞选片.md`、`36-Jimmy设计语.md`、`18-养站考核.md`、`scripts/fnd/betty_timetable.html`、`docs/superpowers/specs/2026-09-11-fnd-schedule-design.md`、`backups/dashboard/ui/elec3347/`。
- 个人生活流程：`21-iCloud照片归档.md`、`22-安卓照片备份-Immich.md`、`23-短信转发-SmsForwarder.md`（手机号×2）。
- **图片元数据**：9 张已检查（7 JPG + 2 PNG），EXIF **均不含 GPS / 设备 / 时间 / 作者**；2 张课表 PNG 含 Software 文本块；1 个 PDF 含 Author 字段。
- 处置：以上**整体不进入知识库**（清单见交付 2）。

## 6. 自动外联与自动部署风险【已验证】

> 完整逐文件主表、launchd/systemd 专表、凭据 sha8 指纹与「未经授权不得运行」清单见 `reports/danger-audit.md`（804 行）。全程只读：未执行任何脚本、未联网、未改仓库。

### 6.1 规模与分级

| 项 | 数量 | 说明 |
|---|---:|---|
| 危险项合计 | **148** | 主表行数（一行可代表同组多文件） |
| P0 会自动外联/部署 | **82** | 有自动触发器（launchd RunAtLoad/KeepAlive/StartInterval/StartCalendarInterval、systemd timer/Restart=always/开机 oneshot、cron、compose restart、agent hook），或安装器会把自动触发写入用户环境 |
| P1 需凭据才可运行 | **33** | 手动触发，但执行即连接原作者基础设施/外部 API 或写用户环境配置 |
| P2 仅本地只读/离线 | **33** | 本地采集/离线测试/模板文档；**仍可能含真实凭据**（数据暴露另行标注） |
| launchd plist | **21** | Label 全部含作者名（jimmy/jimmycloud）需替换；ProgramArguments 全部指向原作者家目录绝对路径 |
| systemd | **23 service + 14 timer + 6 conf** | 另有 **9 条 cron/任务计划**（OpenWrt crontab、Mac cron、群晖 DSM 任务计划） |
| CI | **0** | 全历史从未添加任何 GitHub Actions/GitLab CI/Jenkins/CircleCI/Drone/Woodpecker/Azure/Travis/Buildkite（`git log --all --diff-filter=A` 取证，我已独立复核为空） |

### 6.2 典型自动触发（无人值守副作用）

- `push-to-contabo` 120s、`tg-push` 30s、`selfheal-mac` 120s 等 RunAtLoad + 定时。
- **周日 04:00 自动重启整机**（`scripts/ops/scheduled-reboot.{service,timer}`）。
- **群晖 root 自动部署更新**；**4 个 Cloudflare DNS 写脚本**；OpenWrt `*/2` 自愈/故障切换。
- 历史已删除自动化：`scripts/mc/` 9 文件（commit `5bed1c3`，2026-10-14）、`scripts/emby-relay/com.<ORIGINAL_AUTHOR>.emby-hub-watch.plist`（commit `1d599d4`，2026-11-16）——**仍在历史中**。

### 6.3 外联目标类型（不含真实地址）

Telegram Bot API（全舰队告警出口）、Cloudflare DNS API（4 个写脚本）、原作者 **9 台 VPS + 家里路由 + 群晖**（SSH 别名 contabo/m5/syno/bwg/akko/lisa/jprelay/hklisa/hkrelay/istoreos）、家里 Emby/Immich/MoviePilot、6 家 AI API（MiniMax/Qwen/Kimi/Gemini/Claude/Codex）、GitHub releases、OpenSubtitles、TMDB、BWG KiwiVM、IPRoyal 住宅代理、**astral uv 远程管道安装脚本**。

### 6.4 最高危脱敏对象

1. `00-密码总表.md`（271 行 / 137 表行，全类型凭据）
2. 9 个 `backups/*-config-backup.tgz.age`（内含舰队 /etc 密钥；age 私钥在 git 外，`.age-recipients` 仅公钥）
3. `sms-forwarder/` 双机 JSON —— **导入即自动把短信转发到原作者 Bark/webhook**，含 frpc 凭据
4. `scripts/agent-panel/archive/20261123-ai-hub/` —— 已退役但 KeepAlive plist 仍在库

### 6.5 文档与实物矛盾【已验证，我独立复核】

`scripts/agent-panel/README.md:32` 宣称「Zero launchd daemons（已卸载所有 `com.<ORIGINAL_AUTHOR>.agent-panel.*` 服务与 Claude/Codex Hooks）」，但仓库仍跟踪 **3 个现役 plist**（`push` / `usage` / `plan-usage`，RunAtLoad + 定时）与 **5 个归档 KeepAlive/定时 plist**（`autoloop` / `receiver` / `summaries` / `tghub` / `tgpush`）。
→ **不能以 README 的「已卸载」声明作为安全依据**；判断依据必须是仓库内实际存在的触发器文件。

### 6.6 处置原则

- **未经授权不得运行任何仓库脚本/plist/安装器/配置导入**（清单分 A 安装器与 hook、B 自动触发组件、C 手动但执行即外联、D 配置导入/解密，见 `danger-audit.md` §六）。
- 知识库只保留**设计思想**（状态机去重、配额瀑布、自愈防抖、故障切换判据），**不复制可执行脚本与任何自动触发器**；plist/systemd/cron 一律不入库。
- 所有 SSH 别名、Bot handle、家目录路径、域名/IP 占位符化；作者名从 Label 与路径中移除。

## 7. 复核纠正记录（我对子代理结论的独立验证）【已验证】

| 原结论 | 复核结果 | 依据 |
|---|---|---|
| privacy-inventory §5.1/§9/§11：`scripts/selfheal/selfheal.env` 与 `scripts/selfheal/openwrt/selfheal.env` 是"真实凭据被跟踪" | ** overstated，需降级**：两文件**无任何凭据**。键名仅调参阈值：MAX_REPAIR / NOTIFY_MIN_FAILS / FLAP_WINDOW / FLAP_MAX / ALLOW_REBOOT / REBOOT_MIN_INTERVAL / MIN_UPTIME / LOAD_MULT / MEM_MIN_PCT（openwrt 另 DISK_MAX_PCT / NET_CRITICAL）；无 password/token/secret/uuid 键，无 cred 关键词命中 | 逐行分类：selfheal.env 9 个赋值全为数值或数值+行内注释；**L17、L19 注释含公网 IPv4，L22 注释含域名** → 属**网络标识 PII（中危）**，非凭据。openwrt/selfheal.env **无任何 IP/域名/邮箱/凭据命中**，纯阈值 |
| 处置修正 | 从"凭据泄露"改为：①`*.env` 被跟踪的**卫生问题**（.gitignore 规则晚于入库，对已跟踪文件无效）；②selfheal.env **注释中的真实 IP/域名需脱敏**；③openwrt/selfheal.env 可整体保留为阈值示例（仍建议改名 `.env.example`） | 历史 commit 数：selfheal.env 4、openwrt/selfheal.env 1 |
| privacy-inventory "APIkey 特征全仓 0 命中" | **口径需区分**：已知厂商前缀（ghp_/sk-/AKIA…）确实 0 命中；但**通用 secret/APIkey 字段名**有 8 处命中（6 个值、7 文件），且历史中多个 Emby 脚本含 generic-api-key | gitleaks 默认 + 自定义规则 git 扫描 |

## 8. 处置优先级

1. **立即**：`00-密码总表.md`、9 个 `.tgz.age`、`.age-recipients`、sms-forwarder JSON、学业/个人二进制 → 整体不入库。
2. **高**：节点/订阅文档（§3）全部凭据值 → `<EXAMPLE_*>`；`40-朋友版订阅-friends.md` 人工复核。
3. **中**：公网/内网/Tailscale IP 与个人域名 → RFC5737 / example.com；selfheal.env 注释脱敏。
4. **历史**：见交付 5（**明文 tar 备份是最大风险，gitleaks 扫不出**）。
5. **轮换提醒**：发现的有效凭据须由**原持有人自行轮换**；本审计不代为轮换、不宣称上游已清理。
