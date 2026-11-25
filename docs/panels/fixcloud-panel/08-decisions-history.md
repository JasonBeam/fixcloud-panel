> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 08 · 历史技术决策与理由

**结论**：面板的核心决策围绕「可信家庭内网 + NAS 不可靠文件系统 + 最小攻击面」展开：无登录但同源标记、凭据后端-only、round-trip 保留、事务化三态保存、只读容器。**2026-11-17 公开文件核对故障的根因是 bridge 无 NAT66 导致容器直连 NAS 公网 IPv6 超时，修复为 extra_hosts 把公开域名指向 bridge IPv6 网关由宿主 Lucky 本地投递**。【已验证：README.md:78 + compose 注释 + inspect + .bak 文件】

## 1. 2026-11-17 公开文件核对故障（重点）

| 项 | 内容 |
| --- | --- |
| 现象 | 「设置 → 核对线上版本」失败/超时 |
| 根因 | 公开文件域名只有 AAAA 记录（=NAS 自身公网 IPv6）；面板容器在专用 bridge 只有**内部** IPv6，宿主**无 NAT66**→容器直连该公网 IPv6 不通→httpx 超时 |
| 修复 | compose extra_hosts 把 `<PUBLIC_FILE_DOMAIN>` 指向 `<BRIDGE_GATEWAY_IPV6>`（bridge IPv6 网关）；宿主 Lucky 监听 :::443，网关地址属本地投递→核对返回 matching |
| 证据 | README.md:78 原文；docker-compose.yml:18-21 注释；inspect ExtraHostsCount=1；NAS docker-compose.yml.bak-20261117（改动前备份，mtime Sep 16 cp 保留） |
| 可逆 | 若域名可从容器直连（如未来 NAT66/公网 IPv4），删除 extra_hosts 即可 |
| 状态 | 【已验证】生产 ExtraHostsCount=1，核对功能在运行（audit publication-check:32） |

> 教训：容器网络可达性 ≠ 宿主可达性；bridge 内部 IPv6 与宿主公网 IPv6 是不同地址空间，无 NAT66 时须显式 hosts 映射到网关本地投递。【已验证】

## 2. 架构与安全决策

| 决策 | 理由 | 证据 | 状态 |
| --- | --- | --- | --- |
| 无登录页 + 同源标记 | 可信家庭内网/自有隧道，避免凭据管理负担；x-fixcloud-request:1 仅防普通跨站表单，无 IP 白名单 | README.md:27、routes.py:107-109 | 【已验证】 |
| 凭据后端-only | SMB/WebDAV username/password 仅后端读取，safe_data 剔除，API 不回传、不进浏览器存储、不进审计 details | source_store.py:16,39-51、stores/app.ts:337-354、audit.py | 【已验证】 |
| Diff 完整显示敏感值 | 可信内网决策：用户须核对真实改动（password/secret/token/URL 原文）；非脱敏 | README.md:117、test_yaml_service | 【已验证】 |
| 会话 cookie 隔离 | 每标签页独立临时文件/审计 scope；httponly/samesite=strict/会话级；A 不可见 B | main.py:54-94、browser_session.py、test_session_* | 【已验证】 |
| 只读根文件系统 + cap_drop ALL + 非 root + tmpfs | 最小攻击面；不能装软件/写系统目录/绑<1024；新能力全在 /data + 纯 Python 依赖 | docker-compose.yml:36-42、inspect | 【已验证】 |
| 以 NAS UID/GID 运行 + 保留目标权限 | 避免安全替换后文件变容器 UID；move overwrite 保留原权限位；混合属主下只能写自己属主文件 | compose:9、mounted.py:136-147、README.md:36-38 | 【已验证】 |
| 勿映射公网 | LAN HTTP 非安全上下文；公开会暴露 YAML 凭据 | README.md:121-127 | 【已验证】 |

## 3. 编辑与保存决策

| 决策 | 理由 | 证据 | 状态 |
| --- | --- | --- | --- |
| ruamel round-trip | 保留注释/顺序/引号/未知字段，不破坏手写配置 | yaml_service.py:40-45、test_save_service | 【已验证】 |
| 不自动格式化 | 高级 YAML 模式保留用户精确字节；dump 后再 load 校验 | save_service.py:128-159、README.md:119 | 【已验证】 |
| 事务化三态保存 | NAS SMB/网络文件系统不可靠；rollback/temp/recovery 三隐藏文件 + 多重回读哈希；unchanged/restored/recovery_failed | save_service.py:206-322、test_save_service 故障注入 | 【已验证】 |
| **普通保存不再生成永久备份** | 避免备份累积；旧备份仍可管理；恢复用原始字节；失败恢复副本留盘供人工 | README.md:115、save_service.py:308/318、HistoryView.vue:105 | 【已验证】演进 |
| probe-first 来源保存 | 不保存不可达来源；连通才发 probeToken，表单改动失效 | source_store.py:281-316、SourceModal.vue:99-108 | 【已验证】 |
| 引用完整性守卫 | 删除前扫描直接引用/嵌套链/警告，防悬空引用；cancel/keep/remove/replace | referenceIntegrity.ts、ReferenceIntegrityModal.vue | 【已验证】 |
| 草稿守卫 | 路由切换/关闭/续编辑三模式，防误丢草稿；rawYamlDraft 绝不入浏览器存储 | draftGuard.ts、stores/app.ts:337-354 | 【已验证】 |
| 哈希冲突核对 | preview/save/export/delete 均核对 baseHash/expectedHash，防并发覆盖 | routes.py、save_service.py:207-209 | 【已验证】 |
| 文件选择前端管理 | app_state.py AppStateStore 成死代码；选择存 sessionStorage，/files/select 只校验 | grep 无引用、stores/app.ts | 【已验证】 |

## 4. 网络与外部服务决策

| 决策 | 理由 | 证据 | 状态 |
| --- | --- | --- | --- |
| extra_hosts 公开域名→bridge 网关 | bridge 无 NAT66，宿主 Lucky 本地投递（见 §1） | compose:18-21、README.md:78 | 【已验证】 |
| 图标缓存公网 IP 校验 + Fake-IP 例外 | 防 SSRF；唯一例外 RFC2544 198.18.0.0/15 兼容 Mihomo Fake-IP；重定向≤4跳每跳重校验 | icon_cache.py:20,74-77,159-183 | 【已验证】 |
| 图标目录上游 GitHub + url 重写 | 社区目录 WHATSINStash；url 重写为公开域名/icon/ 经 Lucky 投递；个人图标分离 | icon_catalog.py:14-15,113-115 | 【已验证】外部依赖 |
| 订阅流量 HEAD 优先、不返回 URL、不更新订阅 | 只读用量，最小化外部请求；subscription-userinfo 头解析 | subscription_usage.py:162-166、test | 【已验证】 |
| VPS 用量并发 Evoxt/Vultr、不显示假 0 | 账单流量可见；未配置/失败→available:false+message；never return credentials | vps_usage.py（11-22）、test_vps_usage | 【已验证】生产受 IP 白名单限制 |
| PWA HTTP 无 Service Worker | LAN HTTP 非安全上下文；断网保内存草稿禁保存；不暴露公网 | README.md:121-127、manifest | 【已验证】 |

## 5. 视觉决策

| 决策 | 理由 | 证据 | 状态 |
| --- | --- | --- | --- |
| Nothing 风覆盖层 | visual-refresh.css 在 style.css 后导入（main.ts:14）→当前生效；扁平单色 + 红强调 #d71921、Space Grotesk/Space Mono、无阴影 | visual-refresh.css:2-19、main.ts:13-14 | 【已验证】 |
| 保留 iOS 基础层 | style.css 为底层（Tailwind v4 + iOS 变量），visual-refresh 覆盖；新模块复用 visual-refresh 类名 | style.css:1-14、研究报告 §1.1 | 【已验证】 |
| 移动输入 16px 防缩放 | iOS Safari 聚焦<16px 输入会缩放；!important 强制 | visual-refresh.css:268-270 | 【已验证】 |
| 外部 Google Fonts | Space Grotesk/Space Mono 经 Google Fonts；内网离线/被墙时回退（风险点） | index.html:14-16 | 【已验证】依赖 |

## 6. sing-box 集成研究决策（docs，尚未实施）

| 决策 | 理由 | 状态 |
| --- | --- | --- |
| 不引入第三方面板（3x-ui/s-ui/Marzban/hiddify） | Xray vs sing-box 冲突、GPL/AGPL 传染、成本 | 【推测】规划 |
| SSH=asyncssh 纯 Python 直连 VPS IPv4 | 容器 read_only+cap_drop ALL+非 root 装不了 openssh-client | 【推测】规划 |
| 不复用 lucky-*-admin-tunnel | 隧道只绑宿主 127.0.0.1:26611/26612，bridge 够不到 | 【推测】规划 |
| sing-box 官方镜像钉 tag + 独立 bridge + 显式端口 | 不动 Lucky host 网络 TCP443/16601；hy2 UDP443 与 Lucky TCP443 同号共存（协议不同） | 【推测】规划 |
| MVP=SS2022，阶段2 VLESS+Reality，阶段3 Hysteria2 | 渐进；SS2022 定长 PSK base64（禁口令派生）；hy2 需抬 sysctl 缓冲 | 【推测】规划 |
| **自建凭据绝不进公开 FixCloud.yaml（选项A）** | 公开文件无鉴权可读含凭据（硬红线）；节点只存后端 + 私有订阅端点 | 【推测】规划，当前公开文件仍含凭据 |
| 校验用 sing-box check，不复用 Clash yaml_service | 配置格式不同 | 【推测】规划 |
| 部署事务复刻 save_service 三态 | restored 须回读证明 | 【推测】规划 |

## 7. 演进时间线（文件 mtime + inspect + 备份证据）

| 日期 | 事件 | 证据 |
| --- | --- | --- |
| 07-26 | storage 后端/source_store/.gitignore 初建 | mtime |
| 07-28 | main/settings/routes/icon_catalog/publication/SettingsView/HistoryView + 多测试 | mtime |
| 09-02/04 | subscription_nodes + SubscriptionNodesView | mtime |
| 09-16 | save_service/yaml_service/stores/ItemEditor/SectionView/ReferenceIntegrityModal + test_save_service（事务保存成熟） | mtime |
| 09-25 | Dockerfile/main.ts/visual-refresh.css/router/AppShell/EditorHomeView/MoreView（Nothing 视觉 + PWA） | mtime |
| **11-17** | **extra_hosts 修复公开核对**；README/.env.example 更新 | compose .bak-20261117、README.md:78 |
| 11-19 | FixCloud.yaml 最后修改；audit.sqlite3 | mtime |
| **11-22** | **VPS 用量新增**（routes/vps_usage/UsageView/style.css/test_vps_usage/.dockerignore）；容器重建；backup-vps/backup-usage-layout；secrets 目录 | mtime、inspect StartedAt、NAS 备份目录 |
| 11-24 | docs/vps-singbox-integration-research.md（Beam 著，交 Codex 实施） | mtime 23:14 |
| 11-25 | 本次只读审计 | — |
