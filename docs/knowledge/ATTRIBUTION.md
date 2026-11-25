# 来源归属与脱敏约定

## 1. 来源

| 项 | 值 |
|---|---|
| 参考仓库 | `JimmyChan233/homelab`（GitHub，**Private**） |
| 我的 Fork | `JasonBeam/homelab`（Private，isFork=true，parent=JimmyChan233/homelab） |
| 获取方式 | 用户已授权 Fork 与学习；本仓库只读取该 Fork 的本地克隆 |
| 许可证 | **无**（GitHub API `licenseInfo=null`，仓库内无 LICENSE 文件） |
| 参考仓库规模 | 442 个跟踪文件、443 个 commit、单分支 main、0 tag、无 GitHub Actions |
| 作者归属 | 全部技术经验归属**原作者**；本仓库作者不冒充原创 |

## 2. 许可证缺失下的处理原则

因为上游**没有明确许可证**：

- ✅ 允许：阅读、学习、**用自己的语言重述设计思想/判据/流程/字段语义**，并标注来源。
- ❌ 禁止：逐字复制源码、脚本、配置文件、UI 资产（HTML/CSS/JS/图片/配色值）后发布。
- ❌ 禁止：把上游代码改个名当作自己的作品。
- ✅ 本仓库 `templates/` 下的模板是**我方自行重写**的脱敏示例，不是上游文件的副本。
- ✅ 若将来上游补充许可证，按其条款重新评估可复制范围。

## 3. 已彻底移除的类别

| 类别 | 处理 |
|---|---|
| 姓名/昵称/联系方式/邮箱/私人账号 | 删除；作者统称「原作者」 |
| 公网/内网 IP、真实域名、设备标识、私人拓扑 | 占位符或角色代称（主力出口机/住宅落地机/算力中枢/近港入口机） |
| SSH 私钥、密码、Token、API Key、Webhook、Cookie | 删除，换明显无效示例值 |
| 机场订阅链接、SS 密钥、UUID、Trojan/Hysteria 密码、REALITY 私钥 | 删除，换示例值 |
| 订阅 Token、管理后台入口、个人账单、服务器订单、用户数据 | 删除 |
| 个人学业文件（课表/成绩单/选课/作业 PDF）、生活流程、短信转发配置 | **整体不入库** |
| 加密备份 `.tgz.age`、`.age-recipients` | **整体不入库**（无法解密，也不应持有） |
| launchd plist / systemd service+timer / cron / 安装器 / AI hook | **整体不入库**，只保留设计思想 |
| 截图与图片内文字、PDF 正文 | 不入库；EXIF 已核查无 GPS/设备/时间/作者 |

## 4. 示例值约定（全仓库统一）

| 类型 | 示例值 |
|---|---|
| 域名 | `example.com`、`node-a.example.com`、`sub.example.com` |
| 公网 IPv4 | `192.0.2.10`、`198.51.100.20`、`203.0.113.30`（RFC 5737 文档段） |
| 公网 IPv6 | `2001:db8::10`（RFC 3849 文档段） |
| 内网 IPv4 | `192.168.0.0/16`、`10.0.0.0/8`、`172.16.0.0/12`（RFC 1918） |
| UUID | `00000000-0000-4000-8000-000000000000` |
| SS2022 密钥 | `<EXAMPLE_SS2022_KEY_BASE64_16B>`（明显无效） |
| REALITY 私钥 | `<EXAMPLE_REALITY_PRIVATE_KEY>` |
| 订阅 Token | `<EXAMPLE_SUB_TOKEN>` |
| 邮箱 | `user@example.com` |
| 密码 | `<EXAMPLE_PASSWORD>` |
| 我方环境占位符 | `<NAS_LAN_IP>` `<HOME_DOMAIN>` `<VPS_JP_IP>` 等，见 `infrastructure/README.md` |

## 5. 保留的事实性技术信息

协议名、配置字段名、命令名、端口号、公共 DNS（1.1.1.1 / 8.8.8.8）、公共技术服务域名（ts.net / ip.sb / host.docker.internal）、供应商名（作为公开商业实体用于取舍论证）、配置文件名（sshd.local / resolv.conf）——这些不是隐私，保留以维持技术准确性。

## 6. 验收

- 扫描工具：Gitleaks 8.30.1（默认规则 + 自定义中文规则）+ 自研验收门 `verify-sanitized.py`。
- 本目录 12 篇：**residual_findings = 0**（见 `reports/scan-acceptance.md`）。
- 复核纠正记录：子代理曾报「selfheal.env 含真实凭据被跟踪」，经逐键复核**不成立**（只有调参阈值），但其中一台的 env **注释里含公网 IP 与域名**，属网络标识 PII，已列入不入库清单。

## 7. 上游凭据轮换提醒

参考仓库历史中存在明文凭据（含未加密 tar 备份、已删除的 `.env`、脚本内硬编码 API key）。**这些凭据的有效性只能由原持有人判断与轮换**，本仓库不持有、不使用、不回显其值。清单见 `reports/history-risk.md`。
