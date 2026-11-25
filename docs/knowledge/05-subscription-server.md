> **分类：【参考提炼】** — 来源为参考项目 JimmyChan233/homelab（私有仓库，经 Fork 授权学习）的脱敏设计思想提炼，**不是我方环境**。
> 文中【已验证】指**原作者记录中实际读到/测到**，不代表我方已验证；迁移到我方环境前必须按「③ 需要重新验证的结论」逐条重验。
> 真实域名/IP/凭据/设备标识/个人信息一律不出现；示例值约定见 [ATTRIBUTION.md](ATTRIBUTION.md)。

# 订阅服务器与订阅生成器设计

> 来源：JimmyChan233/homelab（私有仓库，经 Fork 授权学习）；本文件为脱敏后的设计思想提炼，非原文复制。
> 【已验证】= 本次审计实际读到的原作者记录；【推测】= 提炼者推断。域名/IP/凭据/品牌一律用文档示例值（example.com / sub.example.com / <token>），真实值不出现；作者统称"原作者"，主机用角色名（主力/备份/东京/住宅落地/后端机）。

## ① 通用可复用经验（可直接迁移）

### 1. 为什么要自建订阅服务器
- 【已验证】根因：订阅放 GitHub raw，国内被墙，而**客户端默认不走代理拉订阅** → 永远不更新。解法：在一台干净线路节点跑 nginx，定时从私有仓库 git pull 最新订阅，客户端直接从这台干净节点拉。
- 拉私有仓库用**只读 Deploy Key**（最小权限，不用个人 PAT）；ssh 别名固定。
- 订阅域名用 CNAME 指向节点域名 → 节点换 IP 自动跟随；真 Let's Encrypt 证书。

### 2. 端点形态：每客户端一份文件 + 多变体
- 【已验证】同一 token 路径下并列：Clash/Stash/OpenClash 的 yaml、Surge 的 conf、Shadowrocket/v2rayN/v2rayNG/NekoBox/Hiddify 的 base64 节点列表 txt、merged 备份、overseas 海外变体、auto 墙内外自动变体。
- **token 入 URL 路径**做防扫描鉴权：随机 hex token，无 token 的裸路径 nginx 直接 444（断开连接，不回任何内容）。token 即唯一密钥，不外泄。
- 换 token = 改 nginx location + 同步脚本路径 → restart nginx + 重跑同步。

### 3. 同步节奏与脚本健壮性
- 【已验证】sync-sub.timer 每 6h：git pull + 拷贝到 web 根。push 改动 → CI 重建订阅 → ≤6h 自动同步；想立即同步手动 systemctl start sync-sub.service。
- 坑：脚本末行用 if…fi，**别写 `[ -f ] && cp`** —— 文件不存在时末行返回非 0，会让整个 systemd service 判失败。
- 控制面（订阅生成/朋友管理/客户端镜像/用量头）后来集中迁到后端机，宿主 nginx 只听本机/Docker/Tailnet，由反代暴露 → 收敛攻击面。

### 4. Subscription-Userinfo 与自动更新头
- 【已验证】静态订阅原本不发 Subscription-Userinfo，客户端"订阅"栏显示"-"。补法：每小时脚本生成 nginx snippet 注入两个响应头：
  - `Subscription-Userinfo: upload=…; download=…; total=…; expire=…`：用量取主出口本计费周期（vnstat 本月比例劈上下行）+ 配额 + 舰队最早续费日当"到期"。
  - `profile-update-interval: 24`：客户端每 24h 自动更新订阅，改配置无需手动重拉。
- snippet **变化才 reload**（cmp 去抖）；客户端需重拉一次才读到头。
- **朋友版刻意不发此头**：自用版头里是主人真实用量/配额，给朋友看等于泄露。

### 5. 多客户端格式对齐（同源同序）
- 【已验证】Surge 的 [Rule] 从 Clash rules **逐条翻译**（同源同序），RULE-SET 指上游；删静态规则文件防漂移。曾出现同一域名 Clash 走 AI 组、Surge 走 DIRECT 的顺序漂移 bug。
- Surge 托管配置 **MANAGED-CONFIG 头必须带 URL**，否则托管自动更新从未生效。
- skip-proxy 要**挖掉回家网段**（否则 Mac 系统代理下回家规则被 bypass）；encrypted-dns-server DoH 对齐 Clash；删臆造键（如 tcp-connection-keep-alive）。
- **simple-obfs 必须保留**：Surge 加 obfs=/obfs-host=，Shadowrocket 走 SIP002 plugin 串；丢了则机场 SS 节点全连不上（存量 bug）。

### 6. 客户端兼容陷阱（重点）
- 【已验证】Surge 当时不支持 VLESS/REALITY（协议硬限制，后续 Mac 6.12+/iOS 6.0+ 才原生支持）；anytls 需 iOS 5.17+/Mac 6.4.3+，且**手选 anytls 时 UDP 被 Surge REJECT**（打游戏别手选）；Shadowrocket 的 anytls 分享链接格式未确认 → 不输出；SR/Surge 故意 ipv6=false（移动稳定优先）。
- **Stash ≠ mihomo 内核**：闭源独立实现，只是读 Clash 配置格式。健康检查差异：mihomo fallback 用组级 url 测所有成员（含内置 DIRECT）；Stash 按**每个代理自己的 benchmark-url/benchmark-timeout** 测，组上没有测试 URL，默认探 apple.com（墙内可达）→ 内置 DIRECT 墙内也判活 → 卡直连。修法：门组第一成员改用 type:direct 的探测代理，自带 benchmark-url=https://www.google.com/generate_204。同一份 yaml 两边通用（mihomo 忽略 benchmark-*）。用 HTTPS 而非 HTTP：墙内 DNS 污染可能指向会回 HTTP 的随机主机造成假阳性；HTTPS 证书对不上必失败（测不了 HTTPS 的后果是永远判墙内=一直走代理，安全方向）。
- **Surge 离线校验比 app 宽松**：surge-cli --check / lsp 都放过"direct 策略 + 每策略 test-url"行，只有 app 真加载才报错 → 离线校验不能当最终依据。修法照抄用户每天能加载的主配置写法：fallback 组级 url + 全局 internet-test-url，测试 URL 一律 http。

### 7. 墙内外自动识别变体
- 【已验证】门组 = fallback[直连探测, 原组]，探 Google generate_204、expected-status 204；墙外（能直连 Google）→ 直连，墙内 → 走代理；回国视频默认直连。兜底 MATCH/FINAL 指向可见的"网络位置"门。
- **自动版必须独立文件名**（如 Auto.yaml/Auto.conf）才能与传统版同时导入：客户端按文件名/下载名/一键导入 name 命名配置，同名会覆盖或分不清。响应头 Content-Disposition inline; filename 给确定配置名；旧路径作别名保留（已导入的不断）。
- 坑：**手动点选门组成员会固定它**——mihomo 固定成员探测失败会被跳过（安全），但 Surge 手动选中会覆盖自动结果（墙外点了直连再进墙会一直直连）→ 页面加"别手点，点测速按钮"说明。
- 审计方法：墙内等价（门组按探测失败展开第二成员，目标必须=主配置同条、规则匹配段与顺序一致）+ 墙外等价（按探测成功展开直连=海外变体）逐条 0 差异；端到端用 mihomo 探针绑真实网卡(墙外)/绑 lo0 让直连必败(墙内)；DNS 污染对比 AliDNS DoH vs Cloudflare 答案。

### 8. 朋友页 / 订阅中心 / 一键导入
- 【已验证】朋友页按客户端分 5 张卡 + 一键导入 scheme：clash://install-config、stash://install-config、surge:///install-config、shadowrocket://add/sub://<base64>；通用 base64 给 v2rayN 等。
- 页面 base URL 从 location.pathname 推导 → 换 token 不用改页面。
- **personal.html 含自用 token，绝不能拷到朋友路径**；verify_friends.py 断言朋友产物不含自用凭据/回家内网/住宅/小配额节点/机场（自用凭据从 merged.yaml 反查，不手抄）。
- 手机复制三级兜底：Clipboard API → execCommand('copy')（隐藏 textarea）→ prompt() 长按复制。原生 select 的 change 事件 iOS 不算用户点击 → clipboard 被拒，改按钮弹菜单（每项真点击）。

### 9. 客户端安装包自建镜像
- 【已验证】GitHub Releases 国内拉不动（与自建订阅同因）→ 把开源客户端安装包镜像到同一台干净节点；mirror-apps.timer 每周跑。
- **原子下载**：先下到临时文件、校验字节数与上游一致，再 os.replace；已有且大小一致则跳过。
- **manifest.json 驱动页面**：只渲染实际镜像成功的包，上游改名/下载失败不会出现点了 404 的条目（失败保留旧版并告警）。
- .apk 不在 nginx mime.types → 落 default_type text/plain 被当文本显示；用 add_header Content-Disposition attachment 强制下载（比改系统 mime.types 稳，包升级不覆盖）。
- 安装包目录只存一份，nginx alias 挂到两个 token 路径，裸目录路径仍 444；大文件 nginx 直出**不经 Python**。
- **付费 iOS app（Shadowrocket/Stash/Loon）不镜像**（转发安装包属盗版）→ 只给商店链接 + 提示需非中国区 Apple ID。

### 10. 订阅生成器架构
- 【已验证】凭据与拓扑解耦：拓扑写死、creds 由调用方传（重构后输出逐字节不变已验证）。
- ensure_sub 按**源文件 mtime** 判是否重生成（缺文件如新增 auto/ 也触发）；生成器模块每次重生成前 importlib.reload（常驻进程不重载就一直用启动时的旧代码，git pull 了新代码也不生效）。
- **原子目录替换**：stage → 把旧 outdir 改名 old → stage 改名 outdir → 删 old；失败回滚 old，清理 stage；_build_lock 串行防并发。
- 验收工具链：mihomo -t、surge-cli --check、verify_friends.py（节点/组引用完整、无环、规则 1:1 同源同序、skip-proxy 挖洞、无凭据泄露）。

### 11. nginx 与机场订阅的坑
- 【已验证】nginx 正则含 {} 必须加引号，否则 {32} 被当块分隔符报 unknown directive；改 nginx 一律先 nginx -t 成功再 reload（曾 map 引号写错→reload 失败但 nginx 跑旧配置站点没断）。
- 机场订阅**地域互补**：某机场主站入口仅大陆可达、其 Global 站仅海外可达 → 两站合起来才覆盖"在家/在外"；CI runner 在海外拉主站必然 download-failed（不只是临时链接过期）；临时订阅链接过期需在后台开订阅后 15min 内 refresh；拉取 UA 伪装 ClashforWindows。

## ② 原作者特定环境经验（不可照搬）
- 【已验证】具体订阅域名/随机 token/各节点端口/证书域名/机场名与配额/朋友页品牌均为其私有配置；控制面集中到后端机（Contabo 东京）宿主 nginx 只听本机/Docker/Tailnet + Caddy 反代。这些依赖其拓扑与供应商。
- 【推测】"每 6h 同步 + 24h 客户端更新"的节奏适合其个人/小圈子规模；多用户大规模需更短同步或推送式失效（见 06 的 ≤60s 真断连）。

## ③ 需要重新验证的结论（含验证方法）
- Stash 加载**完整** auto 配置：真机只测过小测试配置（协议逐项对照已过），需内地真机验探针超时落 Others。
- 三家客户端（Clash/Stash/Surge）内地真机表现：过关时看"网络位置"=Others 且 Google 能开。
- Surge 自动版 app 真加载（离线 check 不算数）：重新导入能加载、墙外显示 DIRECT。
- 各机场入口地域可达性：四地探针实测（家/港/海外节点），不能按订阅商标称猜。

## ④ 可迁移到 FixCloud / Lucky / QNAP NAS 的具体做法
- **FixCloud**：订阅生成器采用 mtime 判重 + importlib.reload + stage/old 原子目录替换 + verify 泄露断言；多客户端产物同源同序翻译；Subscription-Userinfo/profile-update-interval 头按计费周期生成、cmp 去抖 reload；朋友/多用户版不发主人用量头。
- **Lucky**：用 Lucky 反代订阅端点（TLS 终结 + DDNS 跟随换 IP）；裸路径拒绝（444 语义）；管理口经反代门禁，后端只听本机/tailnet。
- **QNAP NAS**：不直接对公网暴露订阅/管理端口，经 tailnet 或入口机访问；客户端镜像的"原子下载 + manifest 驱动 + 单目录 alias"模式可迁移到任何静态资源分发；付费 app 只给商店链接。

## ⑤ 来源文档路径清单（只给路径，不给敏感内容）
- fork-clone/12-订阅服务器与新增节点.md
- fork-clone/40-朋友版订阅-friends.md
- fork-clone/13-后端机-Contabo东京.md
- fork-clone/04-网络架构与协议方案.md
- fork-clone/scripts/friends/friendsd.py
- fork-clone/scripts/friends/friends-apply.py
- fork-clone/scripts/friends/mirror-apps.py
- fork-clone/scripts/subtrans/translate_subs.py、finish5.py（注：实为字幕 AI 翻译管线，非订阅转换，见下）

> 命名澄清【已验证】：scripts/subtrans/ 的 "subtrans" 是 **subtitle translation（字幕翻译）**，不是 subscription transform。其内容是 Emby 媒体库缺中文字幕 → 大模型翻译 → 写回 NAS。与订阅服务器方向无直接关系，但其中几条工程模式可迁移到订阅生成器健壮性：① 配额耗尽立即停（QuotaError fail-fast，绝不写出未翻译/半成品内容）；② 批量失败递归拆半、单条仍失败保留原文（保底不丢数据）；③ 原子写（临时文件 + os.replace）+ 跳过已存在（幂等）；④ 密钥从 600 权限文件读、不硬编码；⑤ 用 curl -K 从 stdin 读配置传 Authorization，避免密钥进进程命令行/urllib 的 MITM CA 问题。这些与 friends-apply 的"口令不进命令行（urllib 探活）"一致。
