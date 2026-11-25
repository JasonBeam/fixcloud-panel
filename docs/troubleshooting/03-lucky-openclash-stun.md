# 03 Lucky STUN 穿透 × OpenClash 接管

> 分类：【我方已验证】。公开案例：github.com/JasonBeam/openclash-lucky-stun。
> 环境：R5C iStoreOS（fw4/nftables）+ OpenClash Fake-IP（非 TUN）+ NAS 上 host 网络 Lucky。

## 现象

Lucky 做 TCP 监听端口转发 + STUN 打洞，拿到的映射在外网不可用。

## 根因

**OpenClash 的 TCP 接管发生在 `inet fw4 openclash` 链，位置先于 clash 规则链。**
因此：
- 配置里写 `DIRECT` **不代表流量未被接管**。
- Lucky 发出的 STUN 相关 TCP 流量被 OpenClash 截走，导致打洞结果不可用。

## 解决方法（最小范围）

在 OpenClash 链**前部插入精确放行规则**，只放行 NAS 源地址 + Lucky 端口范围：

```sh
nft insert rule inet fw4 openclash ip saddr <NAS_LAN_IP> tcp sport <LUCKY_PORT_RANGE> counter return comment 'lucky_stun_bypass'
```

## 回退

按 **handle 删除**该条规则：

```sh
nft -a list chain inet fw4 openclash      # 找到 comment 对应的 handle
nft delete rule inet fw4 openclash handle <N>
```

## 禁止

- **禁止清空整链**、禁止 `flush ruleset`、禁止重启 OpenClash 来"试试"。
- 这些动作会破坏现有全部代理流量，且掩盖真实根因。

## 验证判据

- **拿到 STUN 映射 ≠ 外网可达**。必须从外部实际连接验证。
- 规则插入后看 `counter` 是否增长，确认命中。

## 预防措施

- 任何"DIRECT 却不生效"的问题，先查**链顺序**，再查规则内容。
- 防火墙改动一律带 comment，便于精确回退。

## 未覆盖

- 未验证 UDP 路径是否有同类接管问题。
- 未验证 OpenClash 升级后链结构是否变化（升级后需重新确认 handle 与链名）。
