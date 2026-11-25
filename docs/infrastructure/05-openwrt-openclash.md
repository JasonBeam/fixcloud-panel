# 05 · F50 / R5C OpenWrt + OpenClash / Mihomo

> 分类：【生产配置】+【我方已验证】（JasonBeam 自有环境）
> 核实时间：2026-11-17 ~ 2026-11-25；核实方式：只读 SSH / docker.sock API / 容器内探测 / 面板接口 GET
> 脱敏：真实 IP、域名、主机别名、凭据一律占位符化；对照表仅存本机 `local/`（已 gitignore，永不入库）

## 1. 设备与固件【我方已验证】

| 项 | 值 |
|---|---|
| 设备 | F50 / R5C（ARM 软路由） |
| 系统 | iStoreOS（OpenWrt 衍生） |
| 防火墙 | **fw4 / nftables**（不是 iptables-legacy） |
| 代理组件 | OpenClash，内核 Mihomo |
| 运行模式 | **Fake-IP，非 TUN** |

> 参考项目用的是另一套路由与群晖，**其 OpenWrt crontab / 自愈脚本不可照搬**（见 knowledge/02、08）。

## 2. 与 Lucky STUN 穿透的共存陷阱【我方已验证】

**现象**：Lucky 在 NAS（host 网络）做 TCP 监听端口转发用于 STUN 穿透，拿到映射后外网仍不可达。

**根因**：OpenClash 的 TCP 接管规则位于 `inet fw4 openclash` 链，**先于 clash 规则命中**。因此：

- 即使分流规则判为 `DIRECT`，**流量仍已被接管**（DIRECT 只决定出口，不决定是否被劫持）。
- Lucky 的 STUN 探测/回应包被错误接管 → 映射建立但外部连不进来。

**修复（最小范围）**：

```sh
nft insert rule inet fw4 openclash ip saddr <NAS_LAN_IP> tcp sport <LUCKY_PORT_RANGE> counter return comment 'lucky_stun_bypass'
```

**回退**：按 **handle 删除该条规则**。`nft -a list chain inet fw4 openclash` 找 handle → `nft delete rule inet fw4 openclash handle <N>`。

**禁止**：清空整链、flush ruleset、重启 OpenClash 来"试试看"——会掩盖问题并影响全家网络。

## 3. 判据【我方已验证】

- **拿到 STUN 映射 ≠ 外网可达**。必须从外部网络实测 TCP 握手才算验收。
- 排查顺序：Lucky 监听 → NAS 防火墙 → 路由 fw4 接管链 → 运营商 NAT/端口封锁 → 外部实测。

## 4. 公开案例

- `github.com/JasonBeam/openclash-lucky-stun`（我方公开仓库，记录该问题与修复）。
- 技能 `lucky-openclash-stun` 封装了完整排查流程。

## 5. 待验证

- F50 与 R5C 当前各自承担的角色与固件版本（本轮未逐台核实）。
- OpenClash 内核版本与是否启用 TUN 的当前状态（历史为非 TUN，需重核）。
- 客户端实际使用的订阅来源与更新间隔。
