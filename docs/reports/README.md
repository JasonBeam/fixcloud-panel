# reports — 审计与验收报告

> 本目录记录**参考项目审计结果**与**本仓库自身的脱敏验收结果**。
> 所有报告只含路径、类型、计数、hash 前缀，**不含任何真实凭据值**。

## 索引

| 文件 | 内容 | 对象 |
|---|---|---|
| [01-privacy-risk-inventory.md](01-privacy-risk-inventory.md) | 隐私风险清单：凭据/网络标识/身份/学业隐私分布 | 参考项目 Fork |
| [02-excluded-files.md](02-excluded-files.md) | 未纳管文件清单及原因 | 参考项目 Fork |
| [03-history-risk.md](03-history-risk.md) | Git 历史风险：明文备份、已删敏感文件、作者元数据 | 参考项目 Fork |
| [04-danger-audit.md](04-danger-audit.md) | 自动外联与部署审计（148 项危险项、21 plist、23 service、14 timer、CI=0） | 参考项目 Fork |
| [05-history-action-plan.md](05-history-action-plan.md) | 历史处置方案 A/B/C 与原作者轮换清单 | 参考项目 Fork |
| [06-scan-acceptance.md](06-scan-acceptance.md) | **本仓库**脱敏扫描与验收报告 | homelab-panel |
| [07-inclusion-manifest.md](07-inclusion-manifest.md) | 纳管清单：哪些资料进了哪个目录 | homelab-panel |

## 阅读顺序

1. 先读 **06**（本仓库是否干净、能否推送）。
2. 再读 **07**（纳管了什么）。
3. 需要追溯参考项目风险时读 01–05。

## 重要提醒

- **01–05 描述的是参考项目（上游）的风险，不是本仓库的风险。** 不要混淆。
- 上游历史中的凭据**无法由本仓库的任何操作清除**；即使重写自己的 Fork 也不能宣称上游已清理。
- 发现的有效凭据必须由**原持有人自行轮换**（清单见 03、05）。
