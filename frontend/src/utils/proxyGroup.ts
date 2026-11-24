export type ProxyGroupMemberKind = "proxies" | "use" | "include-from-url";

export type ProxyGroupMemberOption = {
  value: string;
  title: string;
  subtitle: string;
  category: "节点" | "策略组" | "远程代理集" | "URL";
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function uniqueOptions(options: ProxyGroupMemberOption[]) {
  const seen = new Set<string>();
  return options.filter((option) => {
    if (!option.value || seen.has(option.value)) return false;
    seen.add(option.value);
    return true;
  });
}

export function proxyGroupMemberOptions(
  document: Record<string, unknown>,
  kind: ProxyGroupMemberKind,
  currentGroupName = "",
): ProxyGroupMemberOption[] {
  if (kind === "include-from-url") return [];

  if (kind === "use") {
    const providers = asRecord(document["proxy-providers"]);
    return providers
      ? Object.entries(providers).map(([name, raw]) => {
          const provider = asRecord(raw);
          return {
            value: name,
            title: name,
            subtitle: String(provider?.url ?? provider?.path ?? "远程代理集"),
            category: "远程代理集" as const,
          };
        })
      : [];
  }

  const nodes = Array.isArray(document.proxies)
    ? document.proxies.flatMap((raw) => {
        const node = asRecord(raw);
        const name = String(node?.name ?? "");
        if (!name) return [];
        const server = String(node?.server ?? "");
        const type = String(node?.type ?? "proxy").toUpperCase();
        return [{
          value: name,
          title: name,
          subtitle: server ? `${type} · ${server}` : type,
          category: "节点" as const,
        }];
      })
    : [];

  const groups = Array.isArray(document["proxy-groups"])
    ? document["proxy-groups"].flatMap((raw) => {
        const group = asRecord(raw);
        const name = String(group?.name ?? "");
        if (!name || name === currentGroupName) return [];
        return [{
          value: name,
          title: name,
          subtitle: String(group?.type ?? "select").replace("-", " "),
          category: "策略组" as const,
        }];
      })
    : [];

  const builtIns = ["DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"].map((name) => ({
    value: name,
    title: name,
    subtitle: "Mihomo 内置策略",
    category: "节点" as const,
  }));

  return uniqueOptions([...nodes, ...groups, ...builtIns]);
}

export function normalizeMemberList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}

export function groupSupportsHealthCheck(type: unknown) {
  return ["url-test", "fallback", "load-balance"].includes(String(type ?? "").toLowerCase());
}
