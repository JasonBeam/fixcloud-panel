# panels — 我自己的面板项目

> 分类：【我方已验证】。本目录只放**我自己的**项目资料，不放参考项目的面板。

## 索引

| 项目 | 状态 | 索引 |
|---|---|---|
| **FixCloud Panel** | 生产中（QNAP NAS Docker，局域网访问） | [fixcloud-panel/README.md](fixcloud-panel/README.md) |

## FixCloud Panel 资料范围（用户第三节十项）

| # | 内容 | 文件 |
|---|---|---|
| 1 | 项目架构及功能说明 | [01-architecture.md](fixcloud-panel/01-architecture.md) |
| 2 | 前后端技术栈 | [02-tech-stack.md](fixcloud-panel/02-tech-stack.md) |
| 3 | API 接口及数据流 | [03-api-dataflow.md](fixcloud-panel/03-api-dataflow.md) |
| 4 | UI 设计规范及脱敏截图 | [design/](../design/README.md)（截图见该目录说明） |
| 5 | 现有功能、待开发功能及已知问题 | [04-features-status.md](fixcloud-panel/04-features-status.md) |
| 6 | Docker 部署模板及环境变量示例 | [06-deployment.md](fixcloud-panel/06-deployment.md) + [templates/docker/](../templates/docker/README.md) |
| 7 | 数据存储与权限设计 | [05-data-storage-permissions.md](fixcloud-panel/05-data-storage-permissions.md) |
| 8 | 测试规范和验收流程 | [07-testing-acceptance.md](fixcloud-panel/07-testing-acceptance.md) |
| 9 | 历史技术决策 | [08-decisions-history.md](fixcloud-panel/08-decisions-history.md) |
| 10 | 与 Lucky、NAS、VPS 的集成关系 | [09-integrations.md](fixcloud-panel/09-integrations.md) + [infrastructure/](../infrastructure/README.md) |
| — | 源码纳管范围与方案 | [10-source-inclusion-plan.md](fixcloud-panel/10-source-inclusion-plan.md) + [reports/07](../reports/07-inclusion-manifest.md) |

## 源码位置（本轮不迁移）

`/Users/beamjason/Documents/BeamNat/fixcloud-panel` —— **不是 Git 仓库**，无远程无历史。
纳管判定与推荐方案见 [reports/07-inclusion-manifest.md](../reports/07-inclusion-manifest.md) §2。

## 边界

- 本目录描述**结构与契约**（模块职责、接口签名、字段语义、端口、环境变量键名）。
- **不含**真实 IP/域名/凭据；真实对照只在 `local/`（gitignore）。
- 参考项目的面板（dashboard/agent-panel）**不在此目录**，其抽象设计思想在 [design/06-reference-ideas.md](../design/06-reference-ideas.md)。
