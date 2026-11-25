# templates — 脱敏配置与部署模板

> 分类：【待验证】模板（**我方自行重写**，不是参考项目文件的副本）。
> 所有值均为文档示例值；**替换占位符后必须跑官方校验再上线**。

## 目录

| 子目录 | 内容 |
|---|---|
| [singbox/](singbox/README.md) | sing-box 服务端配置模板（SS2022 / VLESS+REALITY / Hysteria2）+ Docker compose |
| [subscription/](subscription/README.md) | Clash 订阅输出模板 + `subscription-userinfo` 头示例 |
| [docker/](docker/README.md) | 通用容器栈模板 + `.env.example` |

## 使用规则

1. **先校验再上线**：sing-box 用 `sing-box check -C <目录>`；compose 用 `docker compose config`；nginx 用 `nginx -t`。
2. **占位符必须全部替换**：`<EXAMPLE_*>`、`192.0.2.x`、`example.com` 都是无效示例值，直接用会失败或产生无认证代理。
3. **凭据不入库**：替换后的真实配置只留在生产宿主机 0600 文件，**不得提交回本仓库**。
4. **最小权限**：模板默认绑 127.0.0.1 或显式端口，不默认 0.0.0.0；管理 API 必须设 secret。
5. **回滚优先**：任何应用模板的动作都要先备份现有配置。

## 占位符约定

见 [knowledge/ATTRIBUTION.md](../knowledge/ATTRIBUTION.md) §4 与 [infrastructure/README.md](../infrastructure/README.md)。
