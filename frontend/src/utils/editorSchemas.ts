export type EditorField = {
  key: string;
  label: string;
  description?: string;
  kind?: "text" | "number" | "password" | "select" | "toggle" | "textarea" | "complex";
  options?: Array<string | { value: string; label: string }>;
  suggestions?: string[];
  placeholder?: string;
  unit?: string;
  openUrl?: boolean;
  always?: boolean;
  types?: string[];
};

export type EditorGroup = {
  title: string;
  help?: string;
  fields: EditorField[];
};

const proxyTypes = ["ss", "vmess", "vless", "trojan", "socks5", "hysteria", "hysteria2", "tuic"];

export const proxyEditorGroups: EditorGroup[] = [
  {
    title: "基础信息",
    fields: [
      { key: "name", label: "名称", always: true },
      { key: "type", label: "类型", kind: "select", options: proxyTypes, always: true },
      { key: "server", label: "服务器", always: true },
      { key: "port", label: "端口", kind: "number", always: true },
      { key: "username", label: "用户名", types: ["socks5"] },
      { key: "password", label: "密码", kind: "password", types: ["ss", "trojan", "socks5", "hysteria2", "tuic"] },
      { key: "uuid", label: "UUID", types: ["vmess", "vless", "tuic"] },
    ],
  },
  {
    title: "协议参数",
    fields: [
      { key: "cipher", label: "加密方式", types: ["ss", "vmess"] },
      { key: "alterId", label: "Alter ID", kind: "number", types: ["vmess"] },
      { key: "flow", label: "Flow", types: ["vless"] },
      { key: "auth-str", label: "认证字符串", kind: "password", types: ["hysteria"] },
      { key: "up", label: "上行速率", types: ["hysteria", "hysteria2"] },
      { key: "down", label: "下行速率", types: ["hysteria", "hysteria2"] },
      { key: "obfs", label: "混淆方式", types: ["hysteria", "hysteria2"] },
      { key: "obfs-password", label: "混淆密码", kind: "password", types: ["hysteria2"] },
      { key: "congestion-controller", label: "拥塞控制", types: ["tuic"] },
      { key: "udp-relay-mode", label: "UDP 中继模式", types: ["tuic"] },
    ],
  },
  {
    title: "传输与安全",
    fields: [
      { key: "network", label: "传输网络", kind: "select", options: ["tcp", "ws", "grpc", "http"] },
      { key: "tls", label: "TLS", kind: "toggle", always: true },
      { key: "udp", label: "UDP", kind: "toggle", always: true },
      { key: "sni", label: "SNI" },
      { key: "servername", label: "服务器名称" },
      { key: "skip-cert-verify", label: "跳过证书验证", kind: "toggle" },
      { key: "client-fingerprint", label: "客户端指纹" },
      { key: "ws-opts", label: "WebSocket 选项", kind: "complex" },
      { key: "grpc-opts", label: "gRPC 选项", kind: "complex" },
      { key: "reality-opts", label: "Reality 选项", kind: "complex" },
      { key: "alpn", label: "ALPN", kind: "complex" },
    ],
  },
];

export const proxyProviderGroups: EditorGroup[] = [
  {
    title: "基础信息",
    fields: [
      { key: "type", label: "类型", kind: "select", options: ["http", "file", "inline"], always: true },
      { key: "url", label: "订阅 URL", openUrl: true, always: true },
      { key: "path", label: "缓存路径", always: true },
      { key: "interval", label: "更新间隔", kind: "number", unit: "秒", always: true },
      { key: "proxy", label: "下载代理", suggestions: ["DIRECT"] },
    ],
  },
  {
    title: "节点筛选",
    fields: [
      { key: "filter", label: "包含过滤器", always: true },
      { key: "exclude-filter", label: "排除过滤器", always: true },
      { key: "exclude-type", label: "排除节点类型", always: true },
    ],
  },
  {
    title: "检查与覆盖",
    fields: [
      { key: "health-check", label: "健康检查", kind: "complex", always: true },
      { key: "override", label: "节点覆盖", kind: "complex", always: true },
      { key: "header", label: "请求头", kind: "complex" },
    ],
  },
];

export const ruleProviderGroups: EditorGroup[] = [
  {
    title: "基础信息",
    fields: [
      { key: "type", label: "类型", kind: "select", options: ["http", "file", "inline"], always: true },
      { key: "behavior", label: "Behavior", kind: "select", options: ["domain", "ipcidr", "classical"], always: true },
      { key: "format", label: "格式", kind: "select", options: ["yaml", "text", "mrs"], always: true },
      { key: "url", label: "规则集 URL", openUrl: true, always: true },
      { key: "path", label: "缓存路径", always: true },
      { key: "interval", label: "更新间隔", kind: "number", unit: "秒", always: true },
      { key: "proxy", label: "下载代理", suggestions: ["DIRECT"] },
    ],
  },
];

export const rewriteEditorGroups: EditorGroup[] = [
  {
    title: "匹配条件",
    fields: [
      { key: "name", label: "名称", always: true },
      { key: "type", label: "类型", kind: "select", options: ["request", "response", "reject", "redirect"] },
      { key: "match", label: "匹配表达式" },
      { key: "url", label: "匹配 URL" },
      { key: "method", label: "请求方法", kind: "select", options: ["GET", "POST", "PUT", "PATCH", "DELETE"] },
    ],
  },
  {
    title: "操作内容",
    fields: [
      { key: "replacement", label: "替换内容" },
      { key: "target", label: "目标地址", openUrl: true },
      { key: "body", label: "响应内容", kind: "textarea" },
      { key: "headers", label: "请求头", kind: "complex" },
    ],
  },
  {
    title: "选项",
    fields: [
      { key: "enabled", label: "启用", kind: "toggle", always: true },
      { key: "requires-body", label: "需要请求体", kind: "toggle" },
      { key: "timeout", label: "超时", kind: "number", unit: "ms" },
      { key: "note", label: "备注" },
    ],
  },
];

export const scriptEditorGroups: EditorGroup[] = [
  {
    title: "基础信息",
    fields: [
      { key: "name", label: "名称", always: true },
      { key: "type", label: "类型", kind: "select", options: ["request", "response", "cron", "generic"] },
      { key: "enabled", label: "启用", kind: "toggle", always: true },
      { key: "match", label: "匹配条件" },
      { key: "timeout", label: "超时", kind: "number", unit: "ms" },
      { key: "note", label: "备注" },
    ],
  },
  {
    title: "脚本内容",
    fields: [
      { key: "script", label: "代码", kind: "textarea", always: true },
      { key: "code", label: "代码", kind: "textarea" },
      { key: "arguments", label: "参数", kind: "complex" },
    ],
  },
];
