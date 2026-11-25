# 05 只读巡检

> 分类：【我方已验证】。**动手前的第一步**，全部命令只读。

## 本机 / NAS

```sh
# 容器与网络（QNAP 无 docker CLI 时用 socket API）
curl -s --unix-socket /var/run/docker.sock http://localhost/containers/json
curl -s --unix-socket /var/run/docker.sock http://localhost/containers/<id>/json

# 面板接口（只读 GET）
curl -s http://<NAS_LAN_IP>:<PANEL_PORT>/api/vps/usage

# 配置目录清单（不读凭据值）
ls -la <CONFIG_DIR>
```

## VPS（SSH 只读）

```sh
ssh -4 -o BatchMode=yes <host> 'uname -a; cat /etc/os-release; nproc; free -m; df -h'
ssh -4 -o BatchMode=yes <host> 'ss -tulpn; ufw status verbose'
ssh -4 -o BatchMode=yes <host> 'docker ps --format "{{.Names}} {{.Image}} {{.Status}}"'
ssh -4 -o BatchMode=yes <host> 'command -v sing-box; ls -la /etc/sing-box 2>/dev/null'
ssh -4 -o BatchMode=yes <host> 'sysctl net.core.rmem_max net.core.wmem_max'
```

## 网络与证书

```sh
# DNS 分别看 A / AAAA（双栈域名可能指向不同目标）
dig +short A <domain>; dig +short AAAA <domain>

# 证书信任链（不只看到期日）
echo | openssl s_client -connect <domain>:443 -servername <domain> 2>/dev/null | openssl x509 -noout -issuer -subject -dates

# REALITY 借壳候选验证
echo | openssl s_client -connect <candidate>:443 -servername <candidate> -tls1_3 -alpn h2 2>/dev/null | head -20
curl -sI https://<candidate>/ | head -5      # 看是否 301/302
```

## 判据提醒

- **旧报告/旧记忆里的地址、版本、路径只作线索**，动手前重新核实。
- 容器内可达 ≠ 宿主机可达 ≠ 外部可达，三者分别测。
- 宿主机 loopback 端口（如隧道 127.0.0.1:26611）**bridge 容器够不到**。
- 明文 HTTP 测速会被 DPI 降速，给出差百倍的假数据。

## 禁止

- 巡检阶段**不做任何写操作**、不重启、不部署。
- 不读取/回显凭据值；只看键名、类型、长度、hash 前缀。
- 不执行参考项目的任何脚本。
