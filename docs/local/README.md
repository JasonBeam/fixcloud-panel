# local — 本机私有对照表（永不入库）

> **本目录已被 .gitignore 排除**（仅保留本 README 与 `*.example.md`）。
> 用途：存放占位符 ↔ 真实值的对照表，供本机 Agent 在需要时查阅。
> **禁止**把本目录内的真实值复制进入库文档、提交、日志或聊天输出。

## 约定

| 文件 | 内容 | 是否入库 |
|---|---|---|
| `README.md` | 本说明 | ✅ |
| `env-map.example.md` | 对照表**模板**（只有占位符） | ✅ |
| `env-map.md` | 真实对照表 | ❌ gitignore |
| `screenshots/raw/` | 未脱敏原始截图 | ❌ gitignore |

## 使用规则

1. Agent 需要真实地址时，读本目录的 `env-map.md`；**输出到入库文档前必须替换回占位符**。
2. 入库文档中出现的任何 `<...>` 占位符，其含义见 `infrastructure/README.md` 的占位符表。
3. 本目录不得存放凭据（密码/Token/私钥/订阅链接）。凭据只留在生产宿主机的 0600 文件与容器 env 中。
4. 若本目录意外被跟踪，立即 `git rm --cached` 并检查历史；**不要**用 force push 掩盖。
