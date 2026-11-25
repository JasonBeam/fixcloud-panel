# Git 历史处置操作计划（**待批准，未执行任何远程操作**）

对象：`JasonBeam/homelab`（Private，Fork 自 `JimmyChan233/homelab`，默认分支 main，442 跟踪文件 / 443 commit / 0 tag / 无 GitHub Actions）。
审计克隆：`/Users/beamjason/Documents/GitHub/homelab-sanitize/fork-clone`，**push 已禁用**（remote push url = `no_push_disabled`）。

---

## 0. 为什么"删文件"不够

普通 `git rm` + commit 只改变最新快照，旧 commit 的 blob 仍在仓库对象库里，任何有读权限的人都能用 `git log --all -- <path>` + `git cat-file` 取回。本仓库已确认三类历史残留：

| 类别 | 证据（只给路径与类型，不回显值） | 影响 |
|---|---|---|
| **明文配置备份曾入库** | `backups/{akko,bwg,contabo,hklisa,hkrelay,istoreos,jprelay,lisa,malaysia}-config-backup.tgz` 在历史中是 **gzip 明文 tarball**（magic `1f8b`，非 age），后才替换为 `.tgz.age`。解包成员分类统计：akko 46 项（代理配置 6 / .env 2 / 脚本或 unit 12）、bwg 51（6/2/12）、contabo 11（.env 1 / 脚本 5）、hklisa 36（8/3/18）、hkrelay 37（8/2/1）、istoreos 80（代理配置 20）、jprelay 38（9/2/1）、lisa 29（9/3/1）、malaysia 42（8/3/1） | 历史 commit 内含各节点代理配置、.env、路由器配置。**gitleaks 默认与自定义规则均未扫出**（二进制 tar 需解包才可见）→ 这是本仓库最大的历史风险 |
| **真实 .env 与设备导入文件曾入库** | `backups/immich/.env`（commit a76f040d，密码 + API key 类型）、`sms-forwarder/SmsForwarder-import.json`（订阅 URL token x2 + UUID） | 已从工作区删除，但历史可取回 |
| **脚本历史版本含 API key** | `scripts/emby-relay/{emby-egress-peaktest.sh,emby-hub-watch.sh}`、`scripts/ops/{emby-posterfill,emby-autosub,emby-fix-dateadded,emby-rebuild-9libs,emby-covers,emby-rebuild-libraries}.py`（当前版本已清理，历史版本含 key）；已删除的 `scripts/agent-panel/{test_mission_control.py,tg-push.py}`、`scripts/ops/emby-optimize.py` | 当前文件干净 ≠ 历史干净 |
| **commit 作者元数据 PII** | 439 条 `原作者 <<ORIGINAL_AUTHOR_EMAIL>>`、4 条 `原作者 <<ORIGINAL_AUTHOR_EMAIL>>` | 即使文件全脱敏，作者邮箱仍暴露原作者身份与学校 |

另：ever-tracked 513 vs 当前 442 → **71 个文件已删/改名**（含 35/37/38 号 plan、agent-panel 旧版 30+ 文件与 5 个 `com.<ORIGINAL_AUTHOR>.*.plist`、`scripts/mc/*` systemd unit/timer）。

---

## 1. 三个可选方案

### 方案 A（**推荐**）：新建独立干净 Private 知识库，不继承任何原历史

- 新仓库：`JasonBeam/homelab-kb`（Private，**非 Fork**，与上游无 parent 关系）。
- 内容：只放脱敏后的知识库 markdown（设计思想提炼，不逐字复制无授权源码）+ 脱敏审计/扫描报告。
- 历史：全新 `git init`，作者为 JasonBeam 自己的 git 身份；**不添加上游 remote**。
- 原 Fork 处置：保持 Private 原样作为审计存档，或（经批准后）删除 Fork。**删除 Fork 不影响上游**。
- 优点：彻底切断历史残留与作者 PII；不需要 force push；不触碰上游；符合"优先建议全新独立干净库"。
- 代价：失去原 commit 时间线（可用脱敏后的 CHANGELOG 摘要保留"经验演进"而不保留原始元数据）。

参考命令（**批准后才执行**）：
```bash
cd /Users/beamjason/Documents/GitHub/homelab-sanitize/kb
git init -b main
git add .
git -c user.name="<JasonBeam 自己的署名>" -c user.email="<JasonBeam 自己的邮箱>" commit -m "init: sanitized homelab knowledge base (design ideas only)"
gh repo create JasonBeam/homelab-kb --private --source . --remote origin --push
```

### 方案 B：重写 Fork 历史（仅在明确批准后）

- 工具：`git filter-repo`（需安装）。
- 移除路径：`backups/*-config-backup.tgz`、`backups/immich/.env`、`sms-forwarder/SmsForwarder-import.json`、已删除的含 key 脚本历史版本。
- 重写作者元数据：把原作者姓名/邮箱替换为 `Original Author <original-author@example.com>`（保留归属但不泄露真实邮箱）。
- 之后 `git push --force` **仅指向 JasonBeam 自己的 Fork**。
- 风险与限制（必须知情）：
  1. **上游 `JimmyChan233/homelab` 的历史不会被改变**，也不能宣称其凭据已删除。
  2. GitHub 可能仍通过 commit SHA 缓存/PR 引用访问旧对象；需联系 GitHub Support 请求清除缓存视图。
  3. Fork 关系仍在，上游若新增 commit 可能重新引入敏感内容。
  4. 任何已 clone 过该 Fork 的第三方副本不受影响。
  5. force push 会改写 443 个 commit 的 SHA，破坏既有引用。
- 结论：**成本高于方案 A，且不能达成"彻底干净"**，除非用户特别需要保留 Fork 关系。

### 方案 C：不做任何远程操作

- 仅在本地独立目录产出脱敏知识库；Fork 保持 Private 原样。
- 风险最低，但 Fork 内的历史残留与作者 PII 仍然存在（仅靠 Private 权限保护）。

---

## 2. 必须提醒原持有人自行轮换的凭据（只列类型与路径，不回显值）

| 类型 | 位置 |
|---|---|
| 节点 UUID / SS2022 密钥 / 订阅 token | `00-密码总表.md`、`06-节点信息与链接.md`、`08-备份节点Akko-链接.md`、`12-订阅服务器与新增节点.md`、`27/28/29/30-*.md`、`40-朋友版订阅-friends.md` |
| 明文配置备份内全部凭据 | 历史中的 `backups/*-config-backup.tgz`（9 台主机/路由器） |
| Immich 部署凭据 | 历史 `backups/immich/.env`；当前 `backups/immich/.env.template`、`docker-compose.yml` |
| Emby API key | `scripts/ops/emby-*.py`、`scripts/emby-relay/*.sh` 的历史版本；`32-Emby媒体服务器.md` |
| Telegram bot token / webhook | `scripts/agent-panel/archive/20261123-ai-hub/tg-push.py`、历史 `scripts/agent-panel/tg-push.py`、`scripts/tg-notify.sh` |
| 面板 / 服务 secret | `backups/dashboard/authsvc/app.py`、`backups/dashboard/.env.example`、`scripts/friends/friendsd.py`、`scripts/selfheal/singbox-resi-inbounds.sh` |
| 个人邮箱 / 手机号 / Apple ID | `42-HKU选课-Hongxi.md`、`23-短信转发-SmsForwarder.md`、`21-iCloud照片归档.md`、`scripts/icloud-archive/*`、commit 作者元数据 |
| age 备份接收者公钥 | `.age-recipients`（公钥本身非机密，但可关联身份；对应私钥不在库内） |

> 这些凭据一旦进入过 Git 历史，就应视为已泄露。**轮换必须由原持有人执行**，本任务不代为操作。

---

## 3. 禁止事项（本任务全程遵守）

- 不修改上游 `JimmyChan233/homelab`，不提交上游 PR，不触发原作者部署流程。
- 未经批准不 force push、不删除远程分支、不把仓库改为 Public、不新建远程仓库。
- 不执行仓库内任何脚本（尤其 `scripts/**`、`*.plist`、compose、自愈/部署脚本）。
- 不宣称"上游历史中的凭据已被删除"。
- 不回显任何真实凭据值；报告只给路径、类型、行号、哈希前缀。

---

## 4. 等待批准的具体决策点

1. 选方案 A / B / C？（推荐 A）
2. 若选 A：新仓库名 `JasonBeam/homelab-kb` 是否可用？是否保留原 Fork 作为私有审计存档？
3. 若选 A：新库的 git 作者署名与邮箱用哪个？
4. 是否由你本人联系原作者告知轮换清单？
