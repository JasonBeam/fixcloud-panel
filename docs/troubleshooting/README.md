# troubleshooting — 故障排查知识库

> 本目录只放**我方环境实际遇到并处理过**的案例，标【我方已验证】。
> 参考项目的 14 组案例在 [knowledge/11-fault-cases.md](../knowledge/11-fault-cases.md)，标【参考提炼】，**不要混为我方经验**。

## 案例索引

| 文件 | 现象 | 根因层级 | 状态 |
|---|---|---|---|
| [01-public-url-check-timeout.md](01-public-url-check-timeout.md) | 面板核对公开订阅 URL 超时 | 容器网络 / IPv6 回环投递 | 已定位并验证修复路径 |
| [02-provider-api-ip-whitelist.md](02-provider-api-ip-whitelist.md) | 两台 VPS 流量都读不到 | 服务商 API IP 白名单 | 已定位，**修复需本人操作** |
| [03-lucky-openclash-stun.md](03-lucky-openclash-stun.md) | Lucky STUN 穿透拿不到可用映射 | OpenClash nftables 接管顺序 | 已定位并有最小修复 |

## 记录格式（新增案例请沿用）

```
## 现象
## 影响面
## 排查过程（只读优先）
## 根因
## 解决方法（最小改动）
## 验证结果（分层：已定位/已修复/已实测/未覆盖）
## 预防措施
## 证据（命令、返回码、耗时；不回显凭据）
```

## 通用判据（踩过的坑）

- **端口活 ≠ 能用**；拿到 STUN 映射 ≠ 外网可达。
- **容器内可达 ≠ 宿主机可达 ≠ 外部可达**，三者分别测。
- **DIRECT 规则 ≠ 未被接管**（OpenClash 在更前的链上接管 TCP）。
- **证书到期日绿 ≠ 浏览器信任**（要验信任链与 issuer）。
- **单采样探测在丢包链路必然假阴性** → 多采样多数决。
- **明文 HTTP 测速被 DPI 降速**，会给出差百倍的假数据。
- **旧报告里的地址/版本/路径只作线索**，动手前重新核实。
