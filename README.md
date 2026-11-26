# FixCloud Panel

Clash / Mihomo YAML 配置的图形化管理面板。运行在 Docker 中，通过浏览器管理代理、规则、DNS 和策略组，保存前可预览完整变更。

![License](https://img.shields.io/github/license/JasonBeam/fixcloud-panel)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Vue 3](https://img.shields.io/badge/Vue-3-42b883)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)

## 功能概览

- **可视化编辑** — 基础设置、DNS、代理、策略组、规则、rule-providers、rewrite 和 script，支持未知字段保留
- **多来源管理** — 默认 NAS 挂载目录，可额外添加 SMB 直连和 WebDAV 来源，每个来源独立设置配置目录
- **安全保存** — 保存前完整 Diff、SHA-256 冲突检查、YAML 重新解析和 Clash/Mihomo 引用校验，失败自动恢复
- **round-trip 保真** — 基于 ruamel.yaml，保留原始注释、顺序、引号和未知字段
- **iPhone 适配** — 安全区域、底部导航、全屏参数编辑，支持 PWA 添加到主屏幕
- **Mac 宽屏** — 左侧导航 + 双栏布局
- **历史版本** — 按来源和文件隔离，使用备份原始字节恢复
- **规则可视化** — 规则列表直接显示"匹配内容 → 策略组"
- **策略组图标** — 从 WHATSINStash 公共图标目录搜索选择

## 快速开始

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
- 来源凭据仅保存在后端，API 不返回账号密码
- 支持连接测试、延迟显示和明确错误提示

## 保存流程

每次保存执行以下检查：

1. 重新读取正式文件并核对哈希（冲突检测）
2. 在原始文档树上应用结构化修改
3. 生成完整 Diff 供确认
4. YAML 重新解析 + Clash/Mihomo 引用检查
5. 创建临时恢复副本 → 上传 → 回读校验 → 安全替换
6. 失败时自动恢复，明确区分"未替换 / 已恢复 / 恢复失败"

## iPhone 主屏幕

Safari 打开面板后，点击「共享 → 添加到主屏幕」即可创建独立入口。PWA 图标、启动模式和安全区域已适配。

> 局域网 HTTP 不是浏览器安全上下文，Service Worker 离线缓存不可用。断网时页面会保留内存草稿并禁止保存。

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

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite、Tailwind CSS、Pinia |
| 后端 | FastAPI、ruamel.yaml（round-trip YAML） |
| 部署 | Docker Compose、双栈 bridge 网络 |
| 安全 | read-only 容器、no-new-privileges、cap_drop ALL |

## 注意事项

- **不提供登录页** — 适用于可信内网环境，不要将端口映射到公网
- **配置中可能包含敏感内容** — 订阅链接、密码、Token 等，不要公开分享截图或 Diff
- **修改前保留备份** — 不同设备和网络环境下的行为需自行验证
- **凭据安全** — 来源账号密码仅保存在后端 `sources.json`，不通过 API 返回

## License

MIT
