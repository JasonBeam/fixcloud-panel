export type ReferenceLocation = {
  path: Array<string | number>;
  label: string;
  relation: string;
};

export type DeleteImpact = {
  path: Array<string | number>;
  type: string;
  name: string;
  references: ReferenceLocation[];
  chains: string[];
  warnings: string[];
  replacementOptions: string[];
};

type RecordValue = Record<string, unknown>;

function objectName(item: unknown) {
  return item && typeof item === "object" && !Array.isArray(item)
    ? String((item as RecordValue).name ?? "")
    : "";
}

function ruleParts(rule: unknown) {
  return typeof rule === "string" ? rule.split(",").map((part) => part.trim()) : [];
}

function ruleTarget(parts: string[]) {
  return parts.at(-1)?.toLowerCase() === "no-resolve" ? parts.at(-2) : parts.at(-1);
}

function pathText(path: Array<string | number>) {
  return path.map((part) => typeof part === "number" ? String(part + 1) : String(part)).join(" → ");
}

function targetAt(document: RecordValue, path: Array<string | number>) {
  let value: unknown = document;
  for (const segment of path) value = Array.isArray(value) ? value[Number(segment)] : (value as RecordValue)?.[String(segment)];
  return value;
}

function identify(document: RecordValue, path: Array<string | number>) {
  const section = String(path[0] ?? "");
  const value = targetAt(document, path);
  if (section === "proxies") return { type: "本地代理", name: objectName(value) || "未命名节点" };
  if (section === "proxy-groups") return { type: "策略组", name: objectName(value) || "未命名策略组" };
  if (section === "proxy-providers") return { type: "远程代理集", name: String(path[1] ?? "") };
  if (section === "rule-providers") return { type: "Rule Provider", name: String(path[1] ?? "") };
  if (section === "rules") return { type: "规则", name: typeof value === "string" ? value : "第 " + (Number(path[1]) + 1) + " 条规则" };
  return { type: "高级字段", name: pathText(path) };
}

function uniqueLocations(items: ReferenceLocation[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = JSON.stringify(item.path);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function scanDeleteImpact(document: RecordValue, path: Array<string | number>): DeleteImpact {
  const target = identify(document, path);
  const references: ReferenceLocation[] = [];
  const chains: string[] = [];
  const warnings: string[] = [];
  const groups = Array.isArray(document["proxy-groups"]) ? document["proxy-groups"] : [];
  const rules = Array.isArray(document.rules) ? document.rules : [];

  if (target.type === "本地代理" || target.type === "策略组") {
    groups.forEach((group, groupIndex) => {
      const record = group as RecordValue;
      const groupName = objectName(group) || "策略组 " + (groupIndex + 1);
      if (Array.isArray(record?.proxies)) {
        record.proxies.forEach((item, index) => {
          if (String(item) === target.name) references.push({
            path: ["proxy-groups", groupIndex, "proxies", index],
            label: groupName + " → proxies",
            relation: "策略组成员",
          });
        });
      }
    });
    if (target.type === "策略组") {
      rules.forEach((rule, index) => {
        const parts = ruleParts(rule);
        if (ruleTarget(parts) === target.name) references.push({
          path: ["rules", index],
          label: "规则 " + (index + 1),
          relation: "规则分流目标",
        });
      });
    }
  }

  if (target.type === "远程代理集") {
    groups.forEach((group, groupIndex) => {
      const record = group as RecordValue;
      const groupName = objectName(group) || "策略组 " + (groupIndex + 1);
      if (Array.isArray(record?.use)) {
        record.use.forEach((item, index) => {
          if (String(item) === target.name) {
            references.push({
              path: ["proxy-groups", groupIndex, "use", index],
              label: groupName + " → use",
              relation: "策略组远程代理集",
            });
            rules.forEach((rule, ruleIndex) => {
              if (ruleTarget(ruleParts(rule)) === groupName) chains.push("规则 " + (ruleIndex + 1) + " → 策略组 " + groupName + " → 远程代理集 " + target.name);
            });
          }
        });
      }
    });
  }

  if (target.type === "Rule Provider") {
    rules.forEach((rule, index) => {
      const parts = ruleParts(rule);
      if (parts[0]?.toUpperCase() === "RULE-SET" && parts[1] === target.name) {
        references.push({ path: ["rules", index], label: "规则 " + (index + 1), relation: "RULE-SET 引用" });
        const policy = ruleTarget(parts);
        if (policy) chains.push("RULE-SET " + target.name + " → 策略组 " + policy);
      }
    });
  }

  if (target.type === "规则") {
    const remaining = rules.filter((_, index) => index !== Number(path[1]));
    const matchCount = remaining.filter((rule) => ruleParts(rule)[0]?.toUpperCase() === "MATCH").length;
    if (ruleParts(targetAt(document, path))[0]?.toUpperCase() === "MATCH") {
      warnings.push(matchCount ? "删除后仍保留 MATCH 兜底规则，但顺序不会自动调整。" : "删除后没有 MATCH 兜底规则，规则末尾可能不再有默认分流。");
    }
  }

  const referenceKeys = target.type === "远程代理集"
    ? new Set(["use", "proxy-provider", "proxy-providers"])
    : target.type === "Rule Provider"
      ? new Set(["rule-provider", "rule-providers"])
      : new Set(["proxy", "proxies", "proxy-group", "policy"]);
  const walk = (value: unknown, currentPath: Array<string | number>, parentKey = "") => {
    if (Array.isArray(value)) {
      value.forEach((item, index) => walk(item, [...currentPath, index], parentKey));
      return;
    }
    if (value && typeof value === "object") {
      Object.entries(value as RecordValue).forEach(([key, item]) => walk(item, [...currentPath, key], key));
      return;
    }
    if (referenceKeys.has(parentKey) && String(value) === target.name) {
      references.push({ path: currentPath, label: pathText(currentPath), relation: "高级字段中的已识别引用" });
    }
  };
  walk(document, []);

  if (target.type === "策略组" && (targetAt(document, path) as RecordValue)?.["include-all"]) warnings.push("该策略组启用了 include-all；删除不会自动调整其他策略组的筛选规则。");
  if (target.type === "远程代理集") warnings.push("include-all、filter、exclude-filter、exclude-type 为动态筛选关系；它们不会被自动重写。");

  const replacementOptions = target.type === "本地代理" || target.type === "策略组"
    ? [...(Array.isArray(document.proxies) ? document.proxies.map(objectName) : []), ...groups.map(objectName), "DIRECT", "REJECT"].filter((item) => item && item !== target.name)
    : target.type === "远程代理集"
      ? Object.keys((document["proxy-providers"] as RecordValue) || {}).filter((item) => item !== target.name)
      : target.type === "Rule Provider"
        ? Object.keys((document["rule-providers"] as RecordValue) || {}).filter((item) => item !== target.name)
        : [];

  return {
    path,
    ...target,
    references: uniqueLocations(references).filter((item) => JSON.stringify(item.path) !== JSON.stringify(path)),
    chains: [...new Set(chains)],
    warnings: [...new Set(warnings)],
    replacementOptions: [...new Set(replacementOptions)],
  };
}
