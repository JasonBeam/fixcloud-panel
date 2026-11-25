> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 02 · 技术栈与构建链

**结论**：后端 Python ≥3.11（运行时镜像 python:3.13-slim）+ FastAPI + ruamel.yaml round-trip；前端 Vue 3.5 + TypeScript 5.8 + Vite 7 + Tailwind CSS 4 + Pinia 3；单 Dockerfile 多阶段构建（node:22-alpine 编前端 → python:3.13-slim 运行时）。依赖精简、无数据库服务（SQLite 文件）、无消息队列。【已验证：backend/pyproject.toml、frontend/package.json、Dockerfile】

## 1. 后端技术栈与依赖（backend/pyproject.toml，35 行）

包名 `fixcloud-panel-backend` 0.1.0；`requires-python>=3.11`；构建 setuptools>=75。

| 依赖 | 版本约束 | 用途 |
| --- | --- | --- |
| fastapi | >=0.115,<1 | Web 框架、路由、请求模型校验 |
| uvicorn[standard] | >=0.34,<1 | ASGI 服务器（CMD --host 0.0.0.0 --port 8080） |
| pydantic-settings | >=2.7,<3 | 环境变量 → Settings（env_file=.env，extra ignore） |
| ruamel.yaml | >=0.18,<0.19 | **round-trip YAML 文档树**，保留注释/顺序/引号/未知字段 |
| httpx | >=0.27,<1 | 订阅流量/节点拉取、公开文件核对、WebDAV、VPS 厂商 API |
| smbprotocol | >=1.15,<2 | SMB 直连来源（register_session/replace/rename） |
| python-multipart | >=0.0.20,<1 | 文件上传 multipart 解析 |
| defusedxml | >=0.7,<1 | WebDAV PROPFIND XML 安全解析 |
| tzdata | >=2025.1 | Asia/Shanghai 时区（订阅到期/审计时间） |
| pytest（test） | >=8.3,<9 | 后端测试 |
| pytest-asyncio（test） | >=0.25,<1 | 异步测试（asyncio_mode=auto） |

pytest 配置：`pythonpath=["."]`、`testpaths=["tests"]`、`asyncio_mode="auto"`。【已验证：pyproject.toml】

> 运行时镜像 python:3.13-slim；本地开发 venv 实测为 python3.14（backend/.venv，7-26 建）。【已验证：Dockerfile + ls】

## 2. 前端技术栈与依赖（frontend/package.json）

包名 `fixcloud-panel-frontend` v0.1.0，private，type:module。

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| vue | ^3.5.0 | 视图框架（Composition + Options 混用） |
| pinia | ^3.0.0 | 状态管理（options store "app"） |
| vue-router | ^4.5.0 | **hash 路由**（createWebHashHistory，适配静态托管/无服务端 rewrite） |
| lucide-vue-next | ^0.468.0 | 图标库（接口图标，非 emoji） |
| vite（dev） | ^7.0.0 | 构建/dev server |
| @vitejs/plugin-vue（dev） | ^6.0.0 | Vue SFC 支持 |
| tailwindcss（dev） | ^4.0.0 | **Tailwind v4 CSS-first**（style.css:1 @import "tailwindcss"） |
| @tailwindcss/vite（dev） | ^4.0.0 | Tailwind Vite 插件 |
| typescript（dev） | ~5.8.0 | 类型检查（strict + noUnusedLocals/Parameters） |
| vue-tsc（dev） | ^3.0.0 | Vue SFC 类型检查（build/typecheck） |
| vitest（dev） | ^3.2.4 | 前端单测 |
| @vue/tsconfig（dev） | ^0.7.0 | tsconfig 基座（dom） |
| @types/node（dev） | ^22.0.0 | Node 类型（vite 配置） |

scripts：`dev=vite`、`build=vue-tsc -b && vite build`、`typecheck=vue-tsc -b`、`test=vitest run`。【已验证：package.json】

## 3. 构建链

### Dockerfile（21 行，多阶段）

| 阶段 | 基础镜像 | 动作 |
| --- | --- | --- |
| 前端构建 | node:22-alpine | npm ci → npm run build（vue-tsc + vite）→ dist |
| 运行时 | python:3.13-slim | pip install ./backend；COPY 前端 dist；目录 755/文件 644；mkdir /data；EXPOSE 8080；CMD uvicorn app.main:app --host 0.0.0.0 --port 8080 |

> Dockerfile **无 USER 指令**，运行用户由 compose `user: PUID:PGID` 指定（生产 1000:100）。【已验证：Dockerfile + docker-compose.yml:9 + inspect】

### vite.config.ts（21 行）

plugins vue + tailwindcss；alias `@`→./src；server.host 0.0.0.0；dev proxy `/api`→`process.env.VITE_DEV_API_PROXY || http://127.0.0.1:8000`（vite.config.ts:17）。【已验证】

### 前端入口与样式加载顺序

- index.html（23 行）：lang zh-CN；viewport-fit=cover；theme-color light/dark；apple-mobile-web-app-capable；manifest + apple-touch-icon；**外部 Google Fonts：Space Grotesk 400/500/600 + Space Mono 400/700**（index.html:14-16）。
- main.ts:13-14：先 import style.css（iOS 基础层，3338 行），后 import visual-refresh.css（Nothing 风覆盖层，301 行）→**当前生效视觉为 Nothing 风**。
- manifest.webmanifest：standalone，background #f2f2f7，theme #0a84ff，icons 192+512(maskable)→PWA 可安装。

| 风险 | 说明 | 标注 |
| --- | --- | --- |
| 外部字体依赖 | index.html 依赖 Google Fonts（Space Grotesk/Space Mono）；内网离线/被墙时回退到 PingFang SC/SF Mono/系统字体，视觉降级 | 【已验证】index.html:14-16；【推测】离线影响 |
| HTTP 非安全上下文 | LAN IP 的 HTTP 页面不是 secure context→Service Worker 离线缓存不可用；断网仅保内存草稿禁保存 | 【已验证】README.md:125 |

## 4. 数据存储与外部服务依赖

| 类别 | 依赖 | 说明 |
| --- | --- | --- |
| 本地持久化 | SQLite 文件 audit.sqlite3 | 无独立数据库服务；audit_log + app_settings 两表 |
| 本地持久化 | sources.json / icon-cache / icon-catalog / temporary-sessions | 均在 /data 卷 |
| 文件系统 | NAS config 共享 bind mount | /mnt/fixcloud（YAML 正式文件） |
| 外部 HTTP | 订阅提供商（proxy-providers url） | 流量/节点拉取，UA clash.meta |
| 外部 HTTP | GitHub api.github.com / raw.githubusercontent.com（shindgew/WHATSINStash） | 图标目录上游（**第三方公开仓库，license=null，非参考项目作者仓库**；11-25 gh API 核实） |
| 外部 HTTP | 公开文件域名（Lucky 投递） | 发布核对 + 图标 url 重写 |
| 外部 HTTP | api.evoxt.com / api.vultr.com | VPS 用量（11-22 新增，需厂商 API 凭据 + IP 白名单） |
| 外部字体 | Google Fonts | 前端字体（可离线降级） |

> 纳管注意：图标目录上游 `shindgew/WHATSINStash` 为外部 GitHub 仓库，非本项目代码；文档仅注明依赖关系，不复制其资产。【已验证：icon_catalog.py:14-15,113-115】

## 5. 版本与运行时事实（生产）

| 项 | 值 | 来源 |
| --- | --- | --- |
| 容器镜像 | fixcloudpanel-fixcloud-panel（compose 构建） | docker inspect |
| 运行用户 | 1000:100 | inspect User |
| Python 运行时 | 3.13-slim（镜像）；基础镜像 env 含 PYTHON_VERSION/PYTHON_SHA256/GPG_KEY | inspect EnvKeys |
| 容器启动 | 2026-11-22（当前源码版本） | inspect StartedAt |
| 只读根文件系统 | true | inspect ReadonlyRootfs |
| tmpfs | /tmp size=32m mode=1777 | inspect Tmpfs |
| 能力 | cap_drop ALL，no-new-privileges:true，非 privileged | inspect |
