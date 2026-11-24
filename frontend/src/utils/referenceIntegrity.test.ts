import { describe, expect, it } from "vitest";

import { scanDeleteImpact } from "./referenceIntegrity";

const document = {
  proxies: [{ name: "HK", type: "ss" }],
  "proxy-providers": { Kycloud: { type: "http" } },
  "proxy-groups": [{ name: "Proxy", type: "select", proxies: ["HK"], use: ["Kycloud"] }],
  "rule-providers": { AdBlock: { type: "http", behavior: "domain" } },
  rules: ["RULE-SET,AdBlock,Proxy", "MATCH,Proxy"],
  experimental: { policy: "Proxy" },
};

describe("reference integrity scanner", () => {
  it("finds direct and nested provider references", () => {
    const impact = scanDeleteImpact(document, ["proxy-providers", "Kycloud"]);
    expect(impact.references).toEqual(expect.arrayContaining([
      expect.objectContaining({ relation: "策略组远程代理集" }),
    ]));
    expect(impact.chains[0]).toContain("规则 1 → 策略组 Proxy → 远程代理集 Kycloud");
  });

  it("warns before removing the only MATCH rule", () => {
    const impact = scanDeleteImpact(document, ["rules", 1]);
    expect(impact.warnings.join(" ")).toContain("没有 MATCH 兜底规则");
  });
});
