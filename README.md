# FixCloud YAML 图形化管理面板

运行在 NAS Docker 中的 Clash / Mihomo YAML 图形化管理后台。默认使用 NAS 主机挂载目录，支持额外添加 SMB 和 WebDAV 文件来源。

## 主要功能

- Vue 3、TypeScript、Vite、Tailwind CSS 与 FastAPI
- `ruamel.yaml` round-trip 文档树，保留注释、顺序、引号、未知字段和列表顺序
- iPhone 安全区域、底部导航、全屏参数编辑和完整 Diff
- Mac 左侧导航与宽屏双栏布局
- 顶部 YAML 文件选择器，仅列出各来源“配置目录”直属的 `.yaml/.yml`
- 每个浏览器标签页独立保存当前 `sourceId + path + hash`，不会互相改变保存目标
- SMB 主机挂载、SMB 直连、WebDAV 三种文件访问方式
- 每个外部来源独立设置根目录与配置目录；默认配置目录为 `config`
- 不递归扫描配置目录以外的路径；选择哪个配置目录，就只编辑该目录直属 YAML
- 来源连接测试、延迟、测试时间和明确错误原因
- 来源凭据仅保存在后端 `/data/sources.json`，API 不返回账号或密码
- 基础设置、DNS、proxies、proxy-providers、proxy-groups、rules、rule-providers、rewrite、script 和未知字段
- 规则列表直接显示“匹配内容 → 策略组”
- 策略组可从 WHATSINStash 公共图标目录搜索并选择图标 URL，选中后继续使用后端持久化缓存
- 设置页提供 Lucky 公开文件服务入口，并可按真实字节哈希核对线上 YAML
- 保存前完整 Diff、YAML 重新解析和 Clash / Mihomo 引用检查
- SHA-256 冲突检查、临时恢复副本、临时文件回读、安全替换、正式文件回读和失败恢复
- 历史版本按“来源 + YAML 文件”隔离，使用备份原始字节恢复
- 操作日志不记录来源账号、来源密码或 YAML 配置值

面板不提供登录页，适用于可信家庭内网或用户自己的内网隧道。写请求仍要求页面自动附带同源标记，避免普通跨站表单直接调用修改接口。

## NAS Docker 架构

容器使用 bridge 网络，并以 NAS 用户 UID/GID 运行。配置目录和应用数据都显式绑定到 NAS：

```text
/share/BeamJason/files/config       -> /mnt/fixcloud
/share/Container/FixCloudPanel/data -> /data
```

以 NAS 用户运行可避免安全替换 YAML 后文件变成容器内部 UID。保存事务还会保留正式文件原有权限模式。

## 部署

项目目录：

```text
/share/Container/FixCloudPanel
```

创建持久化目录：

```bash
mkdir -p /share/Container/FixCloudPanel/data
```

复制并修改环境变量：

```bash
cp .env.example .env
```

核心配置：

```dotenv
PANEL_PORT=8787
PUID=1000
PGID=100
FIXCLOUD_IPV4_SUBNET=10.0.8.0/24
FIXCLOUD_IPV6_SUBNET=fd00::1::/64
APP_DATA_HOST_PATH=/share/Container/FixCloudPanel/data
SMB_MOUNT_PATH=/share/BeamJason/files/config
YAML_PATH=/FixCloud.yaml
YAML_MOUNT_READ_ONLY=false
WRITE_ENABLED=true
PUBLIC_FILE_BASE_URL=https://file.example.com
PUBLIC_FILE_DOMAIN=file.example.com
PUBLIC_FILE_LAN_IPV6=fd00::1
```

> 公开文件域名只有 AAAA（NAS 自己的公网 IPv6），而面板容器在专用 bridge 上只有内部 IPv6 且宿主机没有 NAT66，容器内直连会超时。compose 里通过 `extra_hosts` 把域名指向 bridge 的 IPv6 网关（宿主机 Lucky 监听 `:::443`，属本地投递），"设置 → 核对线上版本"即可正常返回 `matching`。若域名可从容器直连，删除该 `extra_hosts` 即可。

启动：

```bash
docker compose up -d --build
```

访问：

```text
http://NAS_IP:8787
```

## 文件来源与编辑边界

默认只有 NAS 主机挂载的 SMB `config` 目录。WebDAV 不再通过环境变量预置，需要时在来源页用 `+` 添加。

外部 SMB/WebDAV 来源分别设置连接根目录和“配置目录 / 可编辑目录”。面板只扫描用户所选配置目录直属的 YAML；目录浏览、文件选择、保存、备份和历史恢复都使用该来源与文件的显式上下文。配置目录没有硬编码禁用项；若选择 `rules`，其中直属 YAML 也会按用户选择进入可编辑范围。默认仍为 `config`。

编辑已有来源时，账号和密码输入框为空；留空表示继续使用后端保存的原值。

## 安全保存顺序

1. 重新读取正式文件并核对哈希
2. 在原始 round-trip 文档树上应用结构化修改
3. 生成完整 Diff
4. YAML 重新解析
5. Clash / Mihomo 引用检查
6. 创建同目录隐藏临时恢复副本
7. 上传同目录临时文件
8. 回读临时文件并校验哈希
9. 同文件系统安全替换正式文件并保留原权限模式
10. 回读正式文件确认
11. 失败后重新读取正式文件并核对哈希，明确区分“未替换 / 已恢复 / 恢复失败”
12. 保存成功后删除临时恢复副本，并记录 Asia/Shanghai 时间、来源路径、哈希和修改行数

普通保存不再永久生成 `*.backup-*.yaml`。已有历史备份仍可查看、恢复和删除；恢复时使用备份文件原始字节，不做重新 dump。若保存失败且自动恢复也无法确认，临时恢复副本会保留，供人工核对。

保存前 Diff 完整显示修改前后的真实内容，包括 `password`、`secret`、`token` 和 URL；来源连接凭据仍只由后端保存和使用，不会通过来源 API 返回浏览器。

普通保存不会自动格式化 YAML。

## HTTP 与 iPhone 主屏幕

Safari 可通过“共享 → 添加到主屏幕”创建独立入口，PWA 图标、启动模式和安全区域已经适配。

局域网 IP 的 HTTP 页面不是浏览器安全上下文，因此 Service Worker 离线缓存不可用。断网时当前页面会保留内存草稿并禁止保存；恢复网络后可以继续。

不要把该端口映射到公网。

## 本地验证

```bash
cd frontend
npm ci
npm run build

cd ../backend
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q
```
