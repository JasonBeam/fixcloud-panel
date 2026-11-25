# 通用容器栈模板

> 分类：【待验证】。我方自行重写的脱敏示例，非参考项目文件副本。

## 文件

| 文件 | 用途 |
|---|---|
| [docker-compose.example.yml](docker-compose.example.yml) | 面板类服务的最小安全 compose 骨架 |
| [env.example](env.example) | 环境变量键名示例（**只有键名与无效示例值**） |

## 设计原则（来自参考项目教训 + 我方实践）

| 原则 | 做法 |
|---|---|
| 钉版本 | 镜像用明确 tag 或 digest，**不用 latest**（回滚 = 改 tag） |
| 最小暴露 | 管理端口绑 `127.0.0.1` 或局域网 IP，**不绑 0.0.0.0 公网** |
| 只读根 | `read_only: true` + 显式 tmpfs；写入只落在挂载卷 |
| 身份对齐 | `user: "<UID>:<GID>"` 与宿主机数据属主一致，避免 0600 权限污染 |
| 日志护栏 | `json-file` + `max-size`/`max-file`，防磁盘打满 |
| 健康检查 | 用**真实校验命令**（如 `sing-box check`），不只探进程 |
| 凭据外置 | 真实值放宿主机 0600 `.env`，**不入库**；仓库只留 `.env.example` |
| 网络隔离 | 自建 bridge；需要访问宿主机服务时用 `extra_hosts: host-gateway` 或显式网关地址 |
| 备份先行 | 应用任何配置变更前先备份挂载卷 |

## 校验命令

```sh
docker compose config          # 语法与变量插值校验
docker compose up -d
docker compose ps
docker inspect <container> --format '{{.State.Health.Status}}'
```
