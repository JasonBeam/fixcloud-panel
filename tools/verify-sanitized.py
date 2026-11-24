#!/usr/bin/env python3
"""Sanitization acceptance gate. Reports TYPE + path:line only; never prints matched values.

Usage: python3 verify-sanitized.py <dir> [--json out.json]
Exit code 1 if any residual sensitive-looking value is found.
"""
import ipaddress, json, os, re, sys, collections

DOC_NETS = [ipaddress.ip_network(n) for n in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "127.0.0.0/8", "169.254.0.0/16", "100.64.0.0/10",
    "0.0.0.0/8", "224.0.0.0/4", "240.0.0.0/4", "255.255.255.255/32",
    "192.88.99.0/24", "198.18.0.0/15",
)]
DOC_V6 = [ipaddress.ip_network(n) for n in ("2001:db8::/32", "::1/128", "fe80::/10", "fc00::/7", "fd00::/8")]
ALLOW_DOMAINS = {
    "example.com","example.org","example.net","example.invalid","localhost",
    "github.com","gist.github.com","raw.githubusercontent.com","objects.githubusercontent.com",
    "sing-box.sagernet.org","wiki.metacubex.one","hysteria.network","v2.hysteria.network",
    "stash.wiki","lucky666.cn","developers.cloudflare.com","docs.docker.com","hub.docker.com",
    "ghcr.io","docker.io","registry-1.docker.io","pypi.org","files.pythonhosted.org",
    "nodejs.org","npmjs.com","www.npmjs.com","golang.org","go.dev","proxy.golang.org",
    "man7.org","ss64.com","www.cloudflare.com","letsencrypt.org","acme-v02.api.letsencrypt.org",
    "tailscale.com","login.tailscale.com","immich.app","moviepilot.github.io",
    "api.telegram.org","telegram.org","core.telegram.org",
    "vultr.com","api.vultr.com","evoxt.com","api.evoxt.com","bandwagonhost.com","bwh81.net",
    "akkocloud.com","lisahost.com","vmiss.com","dmit.io","contabo.com",
    "openai.com","anthropic.com","google.com","dl.google.com","www.google.com",
    "apple.com","icloud.com","microsoft.com","live.com","outlook.com","gmail.com",
    "ubc.ca","student.ubc.ca","qq.com","163.com","126.com","foxmail.com",
    "sagernet.org","metacubex.one","xtls.github.io","shadowsocks.org",
    "readthedocs.io","asyncssh.readthedocs.io","fastapi.tiangolo.com","vuejs.org","vitejs.dev",
    "tailwindcss.com","pinia.vuejs.org","router.vuejs.org","vitest.dev","pytest.org",
    "docs.astral.sh","astral.sh","openwrt.org","istoreos.com","openclash.org",
    "emby.media","jellyfin.org","qbittorrent.org","transmissionbt.com",
    "cloudflare.com","one.one.one.one","dns.google","alidns.com","dnspod.cn",
    # 公共技术服务与配置文件名（非作者私有资产）
    "nip.io","sslip.io","ip.sb","api.ip.sb","jail.local","fail2ban-ignoreip.local",
    # 公共协议/服务域名与配置文件名（复核确认为公共标准，非作者私有资产）
    "ts.net","host.docker.internal","sshd.local","port.local","env.example","resolv.conf",
    "gstatic.com","www.gstatic.com","connectivitycheck.gstatic.com","ifconfig.me","icanhazip.com",
    "googleapis.com","fonts.googleapis.com","npmjs.org","registry.npmjs.org",
    # 源码仓库纳管复核：公共包镜像/赞助/官方站点/脚本文件名（非作者私有资产）
    "registry.npmmirror.com","opencollective.com","tidelift.com","api.github.com",
    "ipv6.baidu.com","sing-box.app","nas.local","install.sh","sync.sh",
}
# RFC 2606 / RFC 6761 保留的文档专用顶级域：定义上不是真实域名
RESERVED_TLDS = {"example", "invalid", "test", "localhost"}
# 已复核的 JS / 配置属性误报：点号形式被 RE_DOMAIN 当成域名（非网络标识）
PROPERTY_FALSE_POSITIVES = {
    "server.host","navigator.online","store.online","state.online","app.online",
    "is.online","window.online","router.host","server.port",
    "this.online","request.app","tsconfig.app","icons.plus","appstore.online","request.url.host",
}
# 检测工具自身源码与规则文件：按设计包含正则模式与白名单，会自命中，扫描时跳过
TOOLING_FILES = {
    "tools/verify-sanitized.py","tools/gitleaks-custom-rules.toml","tools/gitleaks-repo.toml",
}
# 密码赋值豁免：值是代码表达式（属性访问）或字段名本身，而非真实口令
CODE_VALUE_PREFIXES = ("self.","settings.","os.","process.","config.","kwargs.","app.","ctx.","params.","data.")
CODE_VALUE_NAMES = {"password","passwd","pwd","secret","token","none","null"}
RE_CODE_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
# 属性链误报：xxx.id（.id 为印尼 ccTLD）
RE_PROPERTY_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\.id")
RE_CJK = re.compile(r"[\u4e00-\u9fff]")
# 已复核的合成测试占位口令（backend/tests/ 内 fixture，非真实凭据）
SYNTHETIC_TEST_VALUES = {"proxy-private", "dav-password"}
# 公共 DNS / 公共锚点 IP（非作者资产）
ALLOW_PUBLIC_IPS = {
    "1.1.1.1","1.0.0.1","8.8.8.8","8.8.4.4","9.9.9.9","149.112.112.112",
    "223.5.5.5","223.6.6.6","119.29.29.29","180.76.76.76","100.100.100.100",
}
ALLOW_EMAIL_DOMAINS = {"example.com","example.org","example.net","example.invalid","localhost","users.noreply.github.com"}

RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
RE_IPV6 = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){3,7}[0-9A-Fa-f]{1,4}\b")
RE_DOMAIN = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|cn|xyz|top|io|me|co|cc|tv|app|dev|info|biz|site|online|club|vip|link|cloud|host|space|fun|icu|pw|tk|ml|ga|cf|gq|ru|jp|hk|tw|sg|us|uk|de|fr|kr|my|th|vn|ph|id|in|au|ca|edu|gov|mil|int|arpa|local|internal|lan|home|test|invalid|example)\b")
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
RE_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
RE_SS2022 = re.compile(r"2022-blake3-[^\n]{0,120}?(?:[A-Za-z0-9+/]{22}==|[A-Za-z0-9+/]{43}=)")
RE_PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
RE_AGE = re.compile(r"AGE-SECRET-KEY-1[0-9A-Z]{58}")
RE_TG = re.compile(r"\b[0-9]{8,10}:AA[A-Za-z0-9_-]{33}\b")
RE_TGURL = re.compile(r"api\.telegram\.org/bot[0-9]+:[A-Za-z0-9_-]+")
RE_MOBILE = re.compile(r"(?<![0-9A-Za-z])1[3-9][0-9]{9}(?![0-9A-Za-z])")
RE_SUBURL = re.compile(r"https?://[^\s)\"'\]]*(?:token=|/sub\?|/link/|subscribe\?|/api/v1/client/subscribe)[^\s)\"'\]]{6,}")
RE_REALITY = re.compile(r"(?i)(?:private_key|privatekey)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_-]{38,}")
RE_PWD = re.compile(r"(?i)(密码|口令|password|passwd|pwd)\s*[:：=]\s*([^\s|]{6,})")
PLACEHOLDER_HINTS = ("<", "EXAMPLE", "example", "xxxx", "XXXX", "***", "REDACTED", "redacted", "占位", "示例", "your-", "YOUR_", "changeme", "CHANGE_ME", "…", "...")
# 文档示例 UUID（全零占位，非真实凭据）
EXAMPLE_UUIDS = {"00000000-0000-4000-8000-000000000000"}
# 文件扩展名：用于排除 "foo.example.md" 这类文件名被 RE_DOMAIN 误判为域名
FILE_EXTS = (
    ".md",".yaml",".yml",".json",".toml",".txt",".py",".sh",".ts",".tsx",".js",".mjs",".cjs",
    ".vue",".css",".scss",".html",".xml",".ini",".cfg",".conf",".plist",".service",".timer",
    ".png",".jpg",".jpeg",".webp",".gif",".svg",".ico",".pdf",".xlsx",".docx",".pptx",".csv",
    ".tgz",".tar",".gz",".zip",".age",".pem",".key",".crt",".cer",".p12",".pfx",".db",".sqlite3",
    ".log",".lock",".env",".example",".template",".sample",".dist",".bak",".orig",".patch",".diff",
    ".go",".rs",".java",".kt",".swift",".c",".h",".cpp",".rb",".php",".lua",".sql",".map",".woff",".woff2",
)

def is_doc_ip(s):
    try:
        a = ipaddress.ip_address(s)
    except ValueError:
        return True
    nets = DOC_NETS if a.version == 4 else DOC_V6
    return any(a in n for n in nets)

def looks_placeholder(v):
    return any(h in v for h in PLACEHOLDER_HINTS)

def scan_file(path):
    out = []
    try:
        raw = open(path, "rb").read()
    except Exception:
        return out
    # 二进制文件（图片/压缩包/数据库）：文本正则会把字节垃圾误判为域名/邮箱/UUID。
    # 跳过文本扫描；其元数据（EXIF/XMP/私有块）必须用专门工具另行检查并记录。
    if b"\x00" in raw[:8192]:
        return out
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return out
    for i, line in enumerate(text.splitlines(), 1):
        for m in RE_IPV4.finditer(line):
            if m.group(0) in ALLOW_PUBLIC_IPS:
                continue
            if not is_doc_ip(m.group(0)):
                out.append((i, "public-or-unknown-ipv4"))
        for m in RE_IPV6.finditer(line):
            if m.group(0) in ALLOW_PUBLIC_IPS:
                continue
            if not is_doc_ip(m.group(0)):
                out.append((i, "public-or-unknown-ipv6"))
        for m in RE_EMAIL.finditer(line):
            if m.group(1).lower() not in ALLOW_EMAIL_DOMAINS:
                out.append((i, "email-pii"))
        for m in RE_DOMAIN.finditer(line):
            d = m.group(0).lower()
            if d in ALLOW_DOMAINS:
                continue
            if any(d.endswith("." + a) for a in ALLOW_DOMAINS):
                continue
            if d.rsplit(".", 1)[-1] in RESERVED_TLDS:
                continue
            if d in PROPERTY_FALSE_POSITIVES:
                continue
            # .id 是印尼国家顶级域，但 source.id / e.target.id 这类属性链是代码误报
            if RE_PROPERTY_ID.fullmatch(d):
                continue
            # 文件名误报：匹配到的其实是 "xxx.example" 这类文件名前缀，后面紧跟文档/代码扩展名
            tail = line[m.end():m.end() + 16].lower()
            if any(tail.startswith(ext) for ext in FILE_EXTS):
                continue
            out.append((i, "non-allowlisted-domain"))
        for m in RE_UUID.finditer(line):
            if m.group(0).lower() not in EXAMPLE_UUIDS:
                out.append((i, "uuid"))
        if RE_SS2022.search(line): out.append((i, "ss2022-key"))
        if RE_PEM.search(line): out.append((i, "pem-private-key"))
        if RE_AGE.search(line): out.append((i, "age-secret-key"))
        if RE_TG.search(line) or RE_TGURL.search(line): out.append((i, "telegram-token"))
        if RE_MOBILE.search(line): out.append((i, "cn-mobile"))
        if RE_SUBURL.search(line): out.append((i, "subscription-url-token"))
        if RE_REALITY.search(line): out.append((i, "reality-private-key"))
        for m in RE_PWD.finditer(line):
            raw = m.group(2)
            if looks_placeholder(raw):
                continue
            v = raw.strip(chr(96) + "\"'(),;|")
            v = re.split(r"\\n|\\r", v)[0]
            if looks_placeholder(v):
                continue
            # 中文提示文案（如 password: "连接认证密码"）是字段说明，不是口令
            if RE_CJK.search(v):
                continue
            # 代码调用表达式（str(...) / .get(...)）不是字面口令
            if v.startswith(("str(", "bytes(", "int(")) or ".get(" in v:
                continue
            if v.lower() in SYNTHETIC_TEST_VALUES:
                continue
            # 代码表达式（属性访问）或字段名本身 → 非真实口令
            if "." in v and RE_CODE_IDENT.fullmatch(v):
                continue
            if v.lower() in CODE_VALUE_NAMES:
                continue
            out.append((i, "password-assignment"))
    return out

def gitignored_set(root):
    """Return set of git-ignored relative paths (empty if not a git repo)."""
    import subprocess
    try:
        r = subprocess.run(["git", "-C", root, "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return set()
        listing = subprocess.run(["git", "-C", root, "ls-files", "--others", "--ignored",
                                  "--exclude-standard", "--directory"],
                                 capture_output=True, text=True, timeout=60)
        out = set()
        for ln in listing.stdout.splitlines():
            ln = ln.strip()
            if ln:
                out.add(ln.rstrip("/"))
        return out
    except Exception:
        return set()


def main():
    root = sys.argv[1]
    jsonout = None
    if "--json" in sys.argv:
        jsonout = sys.argv[sys.argv.index("--json") + 1]
    include_ignored = "--include-ignored" in sys.argv
    ignored = set() if include_ignored else gitignored_set(root)
    skipped_ignored = 0
    skipped_tooling = 0
    findings = []
    per_type = collections.Counter()
    per_file = collections.Counter()
    nfiles = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__", ".venv")]
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
            nfiles += 1
            rel = os.path.relpath(p, root)
            if rel.replace(os.sep, "/") in TOOLING_FILES:
                skipped_tooling += 1
                continue
            if ignored and (rel in ignored or any(rel.startswith(d + "/") for d in ignored)):
                skipped_ignored += 1
                continue
            for line, kind in scan_file(p):
                findings.append({"file": rel, "line": line, "type": kind})
                per_type[kind] += 1
                per_file[rel] += 1
    print(f"scanned_files={nfiles} residual_findings={len(findings)} skipped_gitignored={skipped_ignored} skipped_tooling={skipped_tooling}")
    for k, v in per_type.most_common():
        print(f"  {k}: {v}")
    for f, v in per_file.most_common(40):
        print(f"  {v:4d}  {f}")
    if jsonout:
        json.dump(findings, open(jsonout, "w"), ensure_ascii=False, indent=1)
    sys.exit(1 if findings else 0)

main()
