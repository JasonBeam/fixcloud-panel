# 02 服务商流量 API 读不到（IP 白名单）

> 分类：【我方已验证】。**修复属账号侧，需本人操作，Agent 不代改。**

## 现象

`GET /api/vps/usage` 返回 200，但两台都 `available: false`：

```json
{"servers":[
  {"name":"香港 VPS","provider":"Evoxt","available":false,"message":"无法读取 Evoxt 用量，请检查连接或授权"},
  {"name":"日本 VPS","provider":"Vultr","available":false,"message":"无法读取 Vultr 用量，请检查连接或授权"}
]}
```

耗时 1.34s。

## 排查过程（容器内，只读）

| 探测 | 结果 |
|---|---|
| DNS（两家 API 域名） | 仅 IPv4 |
| TCP 443 连通 | Vultr 0.02s / Evoxt 0.01s，**均 OK** |
| 无 token 请求 Vultr | 401 `{"error":"Invalid API token.","status":401}` → **证明网络可达** |
| 带已配置凭据请求 Vultr `/v2/account/bandwidth` | **401 `{"error":"Unauthorized IP address: <NAS_EGRESS_IPV4>","status":401}`** |
| 带已配置凭据请求 Evoxt `/listserver` | **HTTP 200**，但 body 为 `{"IP Address":"<...>","error":"IP Address Unauthorized"}` |
| 容器 env 键名 | 五项凭据键齐全（**未回显值**），VULTR_API_KEY 长度 36 |

## 根因

**不是网络问题、不是凭据缺失、不是代码 bug**。
NAS 当前出口 IPv4 不在两家服务商的 API IP 白名单内。

**关键陷阱**：Evoxt 返回 **HTTP 200 + body 里的 error**。只看状态码会误判为成功。

## 解决方法

由本人在服务商控制台把当前出口 IPv4 加入 API 白名单：
- Vultr：Account → API → 允许访问的 IP。
- Evoxt：API 设置里的 IP 白名单。

**注意**：家庭 IPv4 出口疑似 CGNAT 且可能变化 → 白名单需要随出口变化维护，或改用固定出口（如经 VPS 转发 API 请求，**属待验证方案**）。

## 验证结果

- 已定位根因（有明确错误文本证据）。
- **未修复**：账号侧操作保留给用户。
- 修复后验收：`/api/vps/usage` 两台 `available: true` 且数值与服务商控制台一致。

## 预防措施

- 错误处理必须**解析 body**，不能只看 HTTP 状态码。
- 错误信息转中文时保留可诊断的关键字（如"IP 未授权"），不要笼统说"检查连接"。
- 现有实现把两种失败都归为"请检查连接或授权"，**掩盖了白名单这个具体根因** → 建议改进（见 roadmap/06）。

## 未覆盖

- 未验证加白名单后是否立即生效（可能有缓存/延迟）。
- 未验证出口 IP 变化频率。
