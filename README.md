# FixCloud Panel

Clash / Mihomo YAML 配置的图形化管理面板。运行在 NAS Docker 中，通过浏览器管理代理、规则、DNS 和策略组，保存前可预览完整变更。

📦 [快速部署](#快速部署) · 📖 [功能介绍](#功能介绍) · 🖥️ [界面预览](#界面预览) · 🔗 [文件来源](#文件来源) · ✨ [让 AI 帮你上手](#让-ai-帮你上手)

> 当前为**个人使用的 NAS 内网面板**，不提供登录页，不要将端口映射到公网。

## 选一种使用方式

| 你想做什么 | 从这里开始 |
| --- | --- |
| 在浏览器里管理 Clash/Mihomo YAML | [快速部署](#快速部署)，Docker Compose 启动 |
| 在 iPhone 主屏幕快速打开 | 部署后 Safari「共享 → 添加到主屏幕」，PWA 已适配 |
| 不熟悉命令，想让 AI 带着操作 | [AI 上手教程](#让-ai-帮你上手) |
| 了解保存前会做哪些检查 | [保存流程](#保存流程) |

## 功能介绍

- **可视化编辑**：基础设置、DNS、代理、策略组、规则、rule-providers、rewrite 和 script，支持未知字段保留。
- **多来源管理**：默认 NAS 挂载目录，可额外添加 SMB 直连和 WebDAV 来源，每个来源独立设置配置目录。
- **安全保存**：保存前完整 Diff、SHA-256 冲突检查、YAML 重新解析和 Clash/Mihomo 引用校验，失败自动恢复。
- **round-trip 保真**：基于 ruamel.yaml，保留原始注释、顺序、引号和未知字段。
- **iPhone 适配**：安全区域、底部导航、全屏参数编辑，支持 PWA 添加到主屏幕。
- **Mac 宽屏**：左侧导航 + 双栏布局。
- **历史版本**：按来源和文件隔离，使用备份原始字节恢复。
- **规则可视化**：规则列表直接显示「匹配内容 → 策略组」。
- **策略组图标**：从 WHATSINStash 公共图标目录搜索选择。
- **凭据保护**：来源账号密码仅保存在后端，API 不返回。

## 快速部署

### 1. 准备目录

```bash
mkdir -p /path/to/config   # 存放 YAML 配置的目录
mkdir -p /path/to/data     # 面板持久化数据
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少修改以下项：

```dotenv
PANEL_PORT=8787
SMB_MOUNT_PATH=/path/to/config          # 你的配置目录
APP_DATA_HOST_PATH=/path/to/data        # 面板数据目录
PUID=1000                               # 容器运行用户
PGID=100
```

### 3. 启动

```bash
docker compose up -d --build
```

访问 `http://你的NAS_IP:8787`。

## 文件来源

默认使用 NAS 主机挂载的目录。可在「来源」页面添加额外的 SMB 或 WebDAV 来源：

- 每个来源独立设置根目录和配置目录
- 面板只扫描配置目录直属的 `.yaml/.yml` 文件，不递归子目录
- 来源凭据仅保存在后端 `sources.json`，API 不返回账号密码
- 支持连接测试、延迟显示和明确错误提示

编辑已有来源时，账号和密码输入框为空；留空表示继续使用后端保存的原值。

## 保存流程

每次保存执行以下检查：

1. 重新读取正式文件并核对哈希（冲突检测）
2. 在原始文档树上应用结构化修改
3. 生成完整 Diff 供确认
4. YAML 重新解析 + Clash/Mihomo 引用检查
5. 创建临时恢复副本 → 上传 → 回读校验 → 安全替换
6. 失败时自动恢复，明确区分「未替换 / 已恢复 / 恢复失败」

普通保存不会自动格式化 YAML。保存前 Diff 完整显示修改前后的真实内容，包括 `password`、`secret`、`token` 和 URL；来源连接凭据仍只由后端保存和使用。

## 界面预览

> 截图待补充。当前面板已在维护者 NAS 上日常使用，iPhone PWA 和 Mac Safari 均已验证。

## 让 AI 帮你上手

可以先复制这一段：

```text
我想使用 FixCloud Panel：
https://github.com/JasonBeam/fixcloud-panel
请先阅读当前 README 和 .env.example。
我的设备是【填写 NAS 型号和系统】，Docker 环境是【Docker Compose / 其他】。
请先带我完成部署，再说明如何添加 SMB/WebDAV 来源。
不要索取或读取我的 YAML 配置、订阅链接、密码或 Token。
每一步说明操作位置、预期结果；没有真实验证的步骤请明确标注。
```

AI 是可选的操作助手。它不能代替你验证网络环境、容器权限或 YAML 语法。

## 注意事项

- **不提供登录页**：适用于可信内网环境，不要将端口映射到公网。
- **配置中可能包含敏感内容**：订阅链接、密码、Token 等，不要公开分享截图或 Diff。
- **修改前保留备份**：不同设备和网络环境下的行为需自行验证。
- **凭据安全**：来源账号密码仅保存在后端 `sources.json`，不通过 API 返回。
- **iPhone PWA 限制**：局域网 HTTP 不是浏览器安全上下文，Service Worker 离线缓存不可用。断网时页面会保留内存草稿并禁止保存。

## 验证到哪一步

- Docker Compose 部署、NAS 挂载目录读写、iPhone PWA 主屏幕和 Mac Safari 双栏布局已在维护者环境验证。
- SMB 直连和 WebDAV 来源的连接测试、延迟显示和错误提示已有记录。
- 安全保存流程（冲突检查、临时恢复副本、失败恢复）已在日常使用中验证。
- 不同 NAS 型号、Docker 版本和网络拓扑的兼容性仍需使用者自行确认。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite、Tailwind CSS、Pinia |
| 后端 | FastAPI、ruamel.yaml（round-trip YAML） |
| 部署 | Docker Compose、双栈 bridge 网络 |
| 安全 | read-only 容器、no-new-privileges、cap_drop ALL |

## 本地开发

```bash
# 前端
cd frontend
npm ci
npm run build      # 生产构建
npm run test       # 单元测试

# 后端
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

## 许可与致谢

源码采用 [MIT License](LICENSE)。

本项目为个人维护的 NAS 内网工具，不代表 Clash、Mihomo 或任何代理服务的官方立场。
