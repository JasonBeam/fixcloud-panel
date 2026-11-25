# 交付 5｜仍然存在的历史记录风险

> **核心结论：普通删除文件不会删除旧 commit 中的数据。本仓库最大的历史风险不是当前工作区，而是 ①曾以明文入库的 9 个配置备份 tarball ②全部 443 个 commit 的作者邮箱 PII。即使 Fork 完成脱敏，也不能宣称上游历史中的凭据已被删除。**

## 1. 历史明文配置备份（最高风险，gitleaks 扫不出）【已验证】

`backups/{name}-config-backup.tgz` 在旧 commit 中是 **gzip 明文 tarball**（magic `1f8b`，非 age 加密），后来才改为 `.tgz.age`。**旧 commit 里仍是明文**。gitleaks 不拆解 tar，故默认/自定义规则均未报出；本结论来自**解包历史 blob 后按类别计数**（只统计类别，不回显任何值）。

| 备份名 | 成员数 | 代理配置 | .env | 脚本/unit | 最早 commit | 涉及 commit 数 |
|---|---:|---:|---:|---:|---|---:|
| akko | 46 | 6 | 2 | 12 | `d480c487` | 7 |
| bwg | 51 | 6 | 2 | 12 | `d480c487` | 7 |
| contabo | 11 | 0 | 1 | 5 | `c607f163` | 5 |
| hklisa | 36 | 8 | 3 | 18 | `54505936` | 7 |
| hkrelay | 37 | 8 | 2 | 1 | `e68a5baa` | 6 |
| istoreos | 80 | 20 | 0 | 0 | `c607f163` | 4 |
| jprelay | 38 | 9 | 2 | 1 | `e68a5baa` | 6 |
| lisa | 29 | 9 | 3 | 1 | `e68a5baa` | 6 |
| malaysia | 42 | 8 | 3 | 1 | `e68a5baa` | 6 |

- `ssh_key_or_hostkey` 类别命中 **0**（未在这些 tar 中发现私钥文件）【已验证】。
- 但"代理配置 + .env + 脚本"合计 **每备份 8–28 个敏感成员**，按 `.gitignore` 与文档索引推断含节点凭据、面板密钥、推送 webhook【推测，需原作者确认】。
- **处置**：这些 blob 必须从历史中移除（方案 B），或**放弃继承历史**（方案 A，推荐）。

## 2. 已删除但仍存在于历史的敏感文件【已验证】

| 路径 | 历史命中类型 | 备注 |
|---|---|---|
| `backups/immich/.env` | cn-password-assignment + generic-api-key | 真实 `.env` 曾入库，commit `a76f040d` 前后删除 |
| `sms-forwarder/SmsForwarder-import.json` | subscription-url-token×2 + uuid | 已删 |
| `scripts/agent-panel/test_mission_control.py` | generic-api-key | 已删，3 个 commit |
| `scripts/agent-panel/tg-push.py` | 推送凭据 | 已删 |
| `scripts/ops/emby-optimize.py` | generic-api-key | 已删 |
| `24-Emby媒体服务器.md` | — | 已删/改名为 `32-` |
| `35-` / `37-` / `38-` 号 plan 文档 | — | 已删 |
| `scripts/agent-panel/` 旧版 30+ 文件（含 5 个 `com.<ORIGINAL_AUTHOR>.*.plist`） | launchd 自启/定时 | 已删 |
| `scripts/emby-relay/com.<ORIGINAL_AUTHOR>.emby-hub-watch.plist` | launchd | 已删 |
| `scripts/mc/*`（Minecraft systemd service/timer） | 服务单元 | 已删 |

**仍在磁盘、但历史版本含 key 的文件**（generic-api-key，多为 Emby API key）：
`scripts/emby-relay/emby-egress-peaktest.sh`、`emby-hub-watch.sh`；`scripts/ops/emby-posterfill.py`、`emby-autosub.py`、`emby-fix-dateadded.py`、`emby-rebuild-9libs.py`、`emby-covers.py`、`emby-rebuild-libraries.py`。
→ **即使当前版本已脱敏，旧版本仍在历史中。**

## 3. commit 作者元数据 PII（无法靠删文件解决）【已验证】

- 439 条 `原作者 <<ORIGINAL_AUTHOR_EMAIL>>`、4 条 `原作者 <<ORIGINAL_AUTHOR_EMAIL>>`，覆盖 2026-07-01 → 2026-11-24 全部历史。
- 删文件**不会**改 author/committer 字段；必须 `git filter-repo --mailmap` 或**放弃继承历史**。

## 4. 结构面（限制了风险扩散，也限制了清理手段）【已验证】

- 远程仅 `refs/heads/main`（`f7f2cadcfd01f4f147a12308b8afa1c1489d7d0b`），**0 tag**、无其他分支 → 无需清理多分支/tag。
- 无 active hooks、无 submodule、无 LFS、无 gitlink → 无额外隐藏对象通道。
- 曾跟踪 513 文件 vs 现 442 → **71 个已删/改名**，旧内容全部仍在历史。
- 当前工作区**无 GitHub Actions**；历史中是否存在 CI 由 `danger-audit` 补全。

## 5. 处置方案（详见 `reports/history-action-plan.md`，**需批准，未执行**）

| 方案 | 做法 | 残留风险 |
|---|---|---|
| **A（推荐）** | 新建**独立、干净、Private** 知识库（如 `JasonBeam/homelab-kb`），**非 Fork、全新 git init、不继承任何历史、不加 upstream remote**；只复制脱敏后的内容。原 Fork 留作私有审计存档 | 新库无历史风险；**原 Fork 与上游历史依旧含全部敏感数据** |
| B | 对自己的 Fork 执行 `git filter-repo`：移除 `backups/*-config-backup.tgz`、`backups/immich/.env`、`sms-forwarder/SmsForwarder-import.json`、含 key 脚本旧版本；作者邮箱改 `Original Author <original-author@example.com>`；**仅 force push 自己的 Fork** | 上游历史不变；GitHub 缓存/旧 SHA 可能仍可访问；Fork 关系仍在；需重写 443 commit |
| C | 不做任何远程操作，仅本地脱敏 + 知识库 | 远程 Fork 与上游风险完全保留 |

**禁止事项（未经批准不得执行）**：force push、删除远程分支、公开仓库、修改上游、提交上游 PR、触发原作者部署流程。

## 6. 必须提醒原持有人轮换的凭据（按类型 + 路径，不回显值）

- Emby API key（`scripts/ops/emby-*.py`、`scripts/emby-relay/*.sh` 历史版本）
- Immich `.env` 凭据（`backups/immich/.env` 历史）
- 订阅 token / 节点 UUID / SS2022 密钥（`00-密码总表.md`、`06/08/12/27/28/29/30-*.md`、历史 tar 备份）
- Telegram bot token / chat id / webhook（`scripts/agent-panel/tg-push.py` 历史、`scripts/selfheal/mac/selfheal.env.template`、推送 URL×30）
- Cookie×13、URL 内嵌账号密码×6
- 9 个明文 tar 备份中的全部配置凭据（**按类别推断，需原作者逐项确认**）

> 本审计**不代为轮换**，也**不宣称上游历史中的凭据已被删除**。发现有效凭据应由原持有人自行轮换。
