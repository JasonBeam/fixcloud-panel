import { describe, expect, it } from "vitest";

import {
  proxyEditorGroups,
  proxyProviderGroups,
  ruleProviderGroups,
} from "./editorSchemas";

describe("visual editor schemas", () => {
  it("covers every supported local proxy type", () => {
    const typeField = proxyEditorGroups
      .flatMap((group) => group.fields)
      .find((field) => field.key === "type");
    expect(typeField?.options).toEqual(
      expect.arrayContaining([
        "ss",
        "vmess",
        "vless",
        "trojan",
        "socks5",
        "hysteria",
        "hysteria2",
        "tuic",
      ]),
    );
  });

  it("keeps provider complex fields behind structured sub-pages", () => {
    const fields = proxyProviderGroups.flatMap((group) => group.fields);
    expect(fields.find((field) => field.key === "health-check")?.kind).toBe("complex");
    expect(fields.find((field) => field.key === "override")?.kind).toBe("complex");
  });

  it("exposes rule-provider behavior and format", () => {
    const keys = ruleProviderGroups.flatMap((group) => group.fields.map((field) => field.key));
    expect(keys).toEqual(
      expect.arrayContaining(["type", "behavior", "format", "url", "path", "interval"]),
    );
  });
});
