> 分类：我方已验证 / 当前生产配置说明（FixCloud Panel 为 JasonBeam 自有项目）
> 核实时间：2026-11-25；核实方式：只读阅读当前源码 + 只读接口探测
> 脱敏：真实 IP/域名/凭据已占位符化，对照表仅存本机 local/（不入库）

# 09 · 集成关系（Lucky / QNAP NAS / VPS）

**结论**：FixCloud Panel 是家庭网络生态中的**配置编辑层**，与 QNAP NAS（宿主）、Lucky（NAS+两台 VPS 的 DNS/Web/证书/转发）、VPS（JP Vultr / HK Evoxt）集成。**面板只读写 YAML 与 /data，不改动 Lucky/隧道/证书/防火墙**；公开文件服务由 NAS Lucky 投递（extra_hosts 本地投递）；订阅来源从主配置 proxy-providers 只读用量；VPS 厂商 API 受 IP 白名单限制。sing-box/SSH 直连为规划，尚未实施。【已验证：源码 + inspect + 研究报告 §1.2/§7（11-24 只读核实）】

> 本节 IP/域名/主机别名全部占位符化。容器名、文件路径、端口、协议、字段名、服务账号名为结构性事实，保留。

## 1. QNAP NAS（宿主）

| 项 | 事实 | 状态 |
| --- | --- | --- |
| 系统 | QTS 5.2.11（20261023），RAM 31891MB，数据 CACHEDEV1/2_DATA | 【已验证】研究报告 §1.2 |
| Docker 访问 | docker CLI 不在 PATH、sudo 需密码；**经 /var/run/docker.sock 只读 GET 可用**（BeamJason 属 administrators）；14 容器 | 【已验证】 |
| 部署目录 | <NAS_DEPLOY_DIR>（=/share/Container/FixCloudPanel）＝完整源码副本 + .env（真实凭据，禁读）+ secrets（0700，禁读）+ backup-vps-20261122 + backup-usage-layout-20261122 + docker-compose.yml.bak-20261117 + 多个 deploy.log | 【已验证】NAS ls |
| 数据卷 | <NAS_APP_DATA_PATH>（=/share/Container/FixCloudPanel/data）→/data | 【已验证】inspect |
| 配置共享 | <NAS_CONFIG_SHARE_PATH>（=/share/BeamJason/files/config）→/mnt/fixcloud；FixCloud.yaml（BeamJason:everyone，面板可写）、oixCloud.yaml（admin:administrators，面板很可能不可写） | 【已验证】属主；【推测】可写性 |
| 面板容器 | fixcloud-panel，8787→8080，bridge fixcloudpanel_fixcloud，read_only+cap_drop ALL+非 root（1000:100） | 【已验证】inspect |

## 2. Lucky 集成

### 2.1 NAS Lucky（host 网络）

| 职责 | 说明 | 与面板关系 |
| --- | --- | --- |
| DNS / Web / 证书 / 回家转发 | 管家庭域名解析、Web 服务、证书、回家节点转发 | 面板不改其配置 |
| 公开文件服务 | 投递 https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml 与 /icon/<filename> | 面板核对线上 YAML、图标 url 重写经此投递 |
| 监听 | :::443（含 bridge IPv6 网关本地投递）、admin TCP 16601 | extra_hosts 把公开域名指向 <BRIDGE_GATEWAY_IPV6>→Lucky 本地投递（无 NAT66） |
| 目录缓存 | 公开目录索引有缓存，核对前先 GET 目录页 ?_fixcloud_refresh=<ms> 触发刷新 | publication.py:25-91、SettingsView.vue:256 |

### 2.2 VPS Lucky（JP/HK，host 网络）

| 项 | JP（Vultr） | HK（Evoxt） |
| --- | --- | --- |
| 镜像 | gdy666/lucky:v3_lucky_docker | 同 |
| TCP | 443 / 16601 / 22 / 127.0.0.1:39841 / 53 | 443 / 16601 / 22 / 127.0.0.1:34531 |
| UDP | 52889 / 68 / 53 | 55234 / 323 |
| ufw | active default deny incoming，仅放行 22/80/443 tcp | 同 |
| sing-box | 未装 | 未装 |

> 面板**不动** VPS Lucky 的 host 网络/端口；未来 sing-box 用独立 bridge + 高位端口，hy2 UDP443 与 Lucky TCP443 同号共存（协议不同）。【已验证现状；推测规划】

## 3. SSH 管理隧道（既有设施，面板不复用）

| 容器 | 网络 | 机制 | 挂载 |
| --- | --- | --- | --- |
| lucky-vps-admin-tunnel | host | local/lucky-vps-transport:1；ssh -4 -N BatchMode ExitOnForwardFailure StrictHostKeyChecking=yes UserKnownHostsFile=/ssh/known_hosts IdentitiesOnly -i /run/key/id -L 127.0.0.1:26611:127.0.0.1:16601 lucky-tunnel@<VPS_JP_IP> | <NAS_HOME>/.lucky-vps/tunnel→/ssh |
| lucky-hk-admin-tunnel | host | 同，-L 127.0.0.1:26612:127.0.0.1:16601 lucky-tunnel@<VPS_HK_IP> | .lucky-vps/hk-tunnel→/ssh |

| 项 | 事实 |
| --- | --- |
| 专用 SSH 用户 | lucky-tunnel（两台 VPS），密钥目录 <NAS_HOME>/.lucky-vps/{tunnel,hk-tunnel,cert,hk-cert} |
| 面板为何不复用 | 隧道只绑宿主 127.0.0.1:26611/26612，面板 bridge 够不到；未来 sing-box SSH=asyncssh 纯 Python 直连 VPS IPv4 |
| 安全边界 | 面板不读/不复制现有 lucky-tunnel 私钥；未来 SSH known_hosts 严格、首连展示指纹、私钥 0600 放 /data |

> 【已验证】隧道存在与绑定（研究报告 §1.2 只读 inspect）；【推测】未来 sing-box SSH 方案。

## 4. 证书同步（既有设施，面板不动）

| 容器 | 网络 | 机制 |
| --- | --- | --- |
| lucky-vps-cert-sync / lucky-hk-cert-sync | bridge | /bin/sh /ssh/sync.sh，把 <NAS_DEPLOY_DIR>/../goodlucky/.vps-cert-export 证书同步到 VPS |

> Reality 不需证书；未来 TLS 可复用同步证书（sing-box 1.14 certificate_provider 或 certificate_path/key_path，内联 acme 已 Deprecated）。面板不改证书同步。【已验证现状；推测规划】

## 5. Lucky 管理 Web（既有设施，面板可外链只读跳转）

| 项 | 事实 |
| --- | --- |
| 容器 | lucky-vps-admin-web（nginx:alpine，host 网络） |
| 监听 | <NAS_LAN_IP>:24443 ssl，server_name <LUCKY_LAN_DOMAIN> |
| 路由 | /jp/→127.0.0.1:26611、/hk/→127.0.0.1:26612、/→NAS Lucky 16601 |
| 与面板 | 面板 UI 可外链只读跳转，不改 nginx 配置 |

## 6. 公开文件服务（硬红线）

| 项 | 事实 | 状态 |
| --- | --- | --- |
| 端点 | https://<PUBLIC_FILE_DOMAIN>/FixCloud.yaml，**无鉴权 200**（20893B，11-24 核实） | 【已验证】 |
| 含凭据 | proxies[0]=localhost/socks5/<HOME_DOMAIN>:7891 含 username+password；proxy-providers 共 3 个，其中 **2 个** URL 带 query token（11-25 复核）；顶层 external-controller+secret | 【已验证】研究报告 §0.1 |
| 图标投递 | /icon/<filename>（icon_catalog url 重写经此） | 【已验证】 |
| **硬红线** | 自建节点密码/UUID/Reality 私钥/订阅 token **绝不进入公开下载文件**；选项A（推荐）节点只存后端 + 私有订阅端点 | 【推测】规划，当前公开文件仍含凭据 |
| 核对 | 面板 GET /publication/status 经 extra_hosts 本地投递核对 sha256 | 【已验证】 |

## 7. 订阅来源（只读用量，不返回 URL）

| 来源（配置键/公开品牌名） | 域名（占位） | 凭据 | 用量实测（11-25） |
| --- | --- | --- | --- |
| oixCloud | <SUB_PROVIDER_A_DOMAIN> | URL token（不回传） | available:true，剩 89.3%，expire 2027-07-05 |
| Kycloud | <SUB_PROVIDER_B_DOMAIN> | URL query token | available:true，剩 82.9%，expire 2027-01-14 |
| 悠兔（Youtu） | <SUB_PROVIDER_C_DOMAIN> | URL token | available:true，剩 99.8%，expire 2027-04-02 |

> 订阅来源从**当前主配置 proxy-providers**（type:http，url http(s)，≤20）读取；HEAD 优先解析 subscription-userinfo 头；不下载/更新订阅正文、不返回 URL。品牌名为配置键/公开名（非凭据）可保留，域名/URL/token 一律占位。研究报告 §0.1 另列 DlerCloud（带 token）。【已验证】

## 8. VPS 与厂商 API

| 项 | JP（别名 vps，Vultr） | HK（别名 hk，Evoxt） |
| --- | --- | --- |
| 边缘域名 | <VPS_JP_EDGE_DOMAIN> | <VPS_HK_EDGE_DOMAIN> |
| IP | <VPS_JP_IP> | <VPS_HK_IP> |
| 系统 | Ubuntu 24.04.5 / kernel 6.8.0-149 | Ubuntu 26.04 / kernel 7.0.0-14 |
| 资源 | 1vCPU / 955MB（可用 538）/ 盘 23G 用 6.4G | 1vCPU / 1961MB（可用 1369）/ 盘 20G 用 1.8G |
| rmem/wmem | 212992（208KB） | 4194304（4MB） |
| SSH | root sudo 免密；容器直连 :22 OK（OpenSSH_9.6p1） | 同（OpenSSH_10.2p1） |
| 厂商 API | GET api.vultr.com/v2/account/bandwidth（Bearer VULTR_API_KEY）→账号本月 GB | GET api.evoxt.com/listserver（BasicAuth public/private，params username/serviceid）→服务器套餐 GiB |
| 用量状态 | **available:false（IP 白名单）** | **available:false（IP 白名单）** |

| 项 | 事实 |
| --- | --- |
| 边缘域名解析 | <VPS_*_EDGE_DOMAIN> 双栈：A=VPS IPv4、AAAA=家庭 NAS IPv6；**禁止用 AAAA 定位 VPS 节点**（指向家庭） |
| IP 白名单问题 | Vultr 401「Unauthorized IP address: <NAS_EGRESS_IPV4>」；Evoxt 200 {"error":"IP Address Unauthorized"}；网络正常（TCP443 0.02s）；修复=把 NAS 出口 IPv4 加入厂商控制台白名单（账号侧，须 Beam 本人） |
| env 注入 | 5 厂商键（EVOXT_USERNAME/API_PUBLIC/API_PRIVATE/SERVICE_ID、VULTR_API_KEY）生产已注入（inspect EnvKeys）→available:false 非缺 env |
| 回家节点 | proxies[0] socks5 <HOME_DOMAIN>:7891，只读纳管不改配置 |

> 【已验证】VPS 现状/白名单/env（研究报告 §0.1/§1.2 + inspect + GET /api/vps/usage）；【待验证】白名单放行后用量恢复。

## 9. 集成边界总表（面板触碰/不触碰）

| 对象 | 面板行为 | 边界 |
| --- | --- | --- |
| YAML 配置（FixCloud.yaml） | 读写（事务保存） | 只写自己属主文件；admin 属主很可能不可写 |
| /data（审计/来源/缓存/会话） | 读写 | 容器内唯一可写系统区 |
| NAS Lucky DNS/Web/证书/转发 | **不改** | 仅经公开文件服务核对/图标投递 |
| SSH 管理隧道 | **不复用/不改** | bridge 够不到 127.0.0.1 绑定 |
| 证书同步 | **不动** | 未来 TLS 可复用证书 |
| Lucky admin nginx | **不动** | 可外链只读跳转 |
| VPS Lucky / ufw / 云防火墙 | **不动** | 未来 sing-box 新端口显式放行需用户确认 |
| 订阅来源 | 只读用量/节点 | 不返回 URL、不更新订阅 |
| 厂商 API | 只读用量 | 受 IP 白名单；不返回凭据 |
| 回家节点 | 只读纳管 | 不改配置 |
| sing-box / SSH 直连 | **尚未实施** | 规划（asyncssh + 官方镜像 + 独立 bridge） |
