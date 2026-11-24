# tools/ — 脱敏与泄露扫描

本目录是**源码纳管的验收工具**，与知识库 `JasonBeam/homelab-panel` 使用同一套规则，保证两个仓库判定一致。

| 文件 | 作用 |
|---|---|
| `verify-sanitized.py` | 脱敏验收门：扫 IPv4/IPv6、非白名单域名、非 example 邮箱、UUID、SS2022 密钥、PEM、AGE 私钥、Telegram token、+86 手机号、订阅 URL token、REALITY 私钥、密码赋值。**只输出 type + path:line，绝不打印命中值**；有残留 exit 1。跳过 gitignore 文件与二进制文件。 |
| `gitleaks-custom-rules.toml` | 自定义规则：中文密码赋值、订阅 URL token、UUID v4、SS2022 密钥上下文、REALITY 私钥上下文、Telegram token、AGE 私钥、PEM、通用 secret 赋值、Bearer、邮箱、+86 手机号。 |
| `gitleaks-repo.toml` | 本仓库配置：继承上面两套规则，再**精确收录已复核的代码表达式与合成测试占位符**（不放宽检测规则本身）。 |

## 用法（必须在仓库根运行）

```bash
python3 tools/verify-sanitized.py . --json /tmp/gate.json   # 必须 residual_findings=0
gitleaks dir . --config tools/gitleaks-repo.toml --redact --no-banner
gitleaks git . --config tools/gitleaks-repo.toml --redact --no-banner   # 提交后复扫历史
```

## 边界

- 正则是启发式，**不能替代人工复核**；变形/编码后的凭据可能漏检。
- 二进制文件（PNG 等）跳过文本扫描，其元数据须用专门工具另行检查。本仓库 5 个 PNG 已核验：eXIf 仅 ColorSpace 与像素尺寸，无 GPS/作者/设备/时间；icon-1024 的 caBX 为 Apple 图标工具私有块，无敏感标记。
- `gitleaks-repo.toml` 的 `[extend] path` 相对**进程 CWD**，不在仓库根运行会报 `failed to load extended config`。
