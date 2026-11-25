# playbooks — 标准操作流程

> 分类：【待验证】流程草案 + 【我方已验证】判据。
> **所有涉及生产的步骤都必须先获授权**（见根 AGENTS.md §4）。本目录不是"可直接执行"的脚本集。

## 索引

| 文件 | 流程 | 触发时机 |
|---|---|---|
| [01-new-vps-onboarding.md](01-new-vps-onboarding.md) | 新 VPS 接入 | 新增机器 |
| [02-config-change-and-rollback.md](02-config-change-and-rollback.md) | 配置变更与回滚 | 任何生产配置改动 |
| [03-subscription-token-lifecycle.md](03-subscription-token-lifecycle.md) | 订阅 token 生命周期 | 签发/轮换/撤销 |
| [04-incident-response.md](04-incident-response.md) | 故障响应 | 告警或用户报障 |
| [05-readonly-inspection.md](05-readonly-inspection.md) | 只读巡检 | 动手前的第一步 |

## 通用前置（每个 playbook 都适用）

1. **先只读巡检**（05），确认当前实际状态，不依赖旧报告/旧记忆。
2. **确认授权范围**：哪台机器、改什么、影响什么、如何回滚。
3. **备份先行**：配置、数据、挂载卷。
4. **最小改动**：不顺手重构、不扩大范围。
5. **验收区分层级**：已构建 / 已部署 / 已启动 / 已实测，分别报告。
6. **记录**：故障修复后写根因、解决方法、验证结果到 `troubleshooting/`。

## 禁止

- 禁止执行参考项目的任何部署脚本、plist、systemd 单元、安装器。
- 禁止连接或修改参考项目作者的服务器。
- 禁止用重启掩盖问题。
- 禁止清空防火墙整链 / flush ruleset。
- 禁止在未查清消费者前关闭公开服务。
