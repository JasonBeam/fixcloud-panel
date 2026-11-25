# 订阅输出模板

> 分类：【待验证】。我方自行重写的脱敏示例。
> 设计依据：roadmap/01、knowledge/03、knowledge/05、knowledge/06。

## 文件

| 文件 | 用途 |
|---|---|
| [clash-subscription.example.yaml](clash-subscription.example.yaml) | Clash YAML 订阅输出骨架（自用版/朋友版共用结构） |
| [http-response.example.md](http-response.example.md) | 订阅端点的 HTTP 响应规范（GET/HEAD/304/头） |

## 渲染原则

1. **对外视图 ≠ 内部主配置**。渲染时必须剔除：
   - 回家节点（`socks5` + TLS 那条）及其凭据
   - `external-controller` / `secret`
   - 上游 `proxy-providers` 的 URL 与 token（朋友版只输出解析后的节点）
   - 其他用户/token 的线路
2. **泄露断言**：渲染后扫描输出，命中敏感字段集合则拒绝发布并告警。
3. **原子写 + version 单调 + mtime/hash 判重**：内容未变不重写、不重载。
4. **朋友版只发线路 id 白名单**，不发管理信息。

## 客户端兼容要点

| 客户端 | 要点 |
|---|---|
| Clash Verge Rev | 只校验 200 + 含 `proxies`/`proxy-providers` 键；**不解 base64** |
| OpenClash | 解析 `subscription-userinfo`；`update_interval` 单位分钟 |
| Stash | **默认 12h，优先 HEAD**；不支持 `2022-blake3-chacha20-poly1305`；REALITY 需 iOS 3.4.0+ |
| sing-box 客户端 | 需 **JSON remote profile**，另一套渲染（P2） |
