# 订阅端点 HTTP 响应规范

> 分类：【待验证】。落地前需在三客户端实测。

## 端点

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/sub/<token>` | token（路径段） | 返回订阅 body |
| HEAD | `/sub/<token>` | token | **必须支持**；头与 GET 一致，body 为空 |
| GET | `/sub/<token>` + `If-None-Match` | token | 命中返回 **304**，无 body |

**管理类端点**（签发/撤销/列表）仍走内网限制（`X-FixCloud-Request: 1`），**不**用 token 鉴权。

## 成功响应头

```http
HTTP/1.1 200 OK
Content-Type: application/yaml; charset=utf-8
Content-Disposition: attachment; filename="subscription.yaml"
Cache-Control: no-store
ETag: "<hash-of-rendered-body>"
Last-Modified: <http-date>
subscription-userinfo: upload=0; download=0; total=0; expire=0
```

| 头 | 规则 |
|---|---|
| `subscription-userinfo` | 单位 **bytes**，时间 **unix 秒**；`expire=0` = 长期；**无统计也要给全 0，不要省略** |
| 兼容别名 | 可同时给 `x-amz-meta-subscription-userinfo`（Verge 接受） |
| `Cache-Control` | `no-store`（含凭据，不被中间缓存） |
| `ETag` | 渲染 body 的 hash；支持 `If-None-Match` → 304 |
| `Content-Type` | Verge 不校验，但给正确值有利于其他客户端 |

## 错误响应

| 情况 | 状态码 | body |
|---|---|---|
| token 不存在 / 已撤销 | **404** 或 **410** | 空或极简文本，**不泄露 token 是否存在过的细节** |
| 已过期 | **410** | 同上，`subscription-userinfo` 写 expire |
| 超配额 | **403** | 同上 |
| 渲染失败（泄露断言命中） | **500** | 通用错误，**不回显敏感内容**；服务端告警 |

## 禁止

- 不用 query 传 token（会进日志/Referer）。
- 不在错误响应里回显 token、节点凭据、内部路径。
- 不记录 token 明文到访问日志；日志只记 token 的 hash 前缀或内部 id。
- 不做 base64 订阅（Verge 拒收）。
