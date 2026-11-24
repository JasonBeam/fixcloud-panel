import { describe, expect, it } from "vitest";

import {
  groupSupportsHealthCheck,
  normalizeMemberList,
  proxyGroupMemberOptions,
} from "./proxyGroup";

describe("proxy group editor helpers", () => {
  const document = {
    proxies: [
      { name: "HK 01", type: "ss", server: "hk.example.com" },
      { name: "TW GPT", type: "vless", server: "tw.example.com" },
    ],
    "proxy-groups": [
      { name: "AI", type: "fallback" },
      { name: "Proxy", type: "select" },
    ],
    "proxy-providers": {
      Kycloud: { type: "http", url: "https://example.com/ky" },
      Youtu: { type: "http", path: "./providers/youtu.yaml" },
    },
  };

  it("builds node and group options without a self reference", () => {
    const options = proxyGroupMemberOptions(document, "proxies", "AI");
    expect(options.map((item) => item.value)).toContain("HK 01");
    expect(options.map((item) => item.value)).toContain("Proxy");
    expect(options.map((item) => item.value)).toContain("DIRECT");
    expect(options.map((item) => item.value)).not.toContain("AI");
  });

  it("builds provider options with useful subtitles", () => {
    const options = proxyGroupMemberOptions(document, "use");
    expect(options).toEqual([
      expect.objectContaining({ value: "Kycloud", subtitle: "https://example.com/ky" }),
      expect.objectContaining({ value: "Youtu", subtitle: "./providers/youtu.yaml" }),
    ]);
  });

  it("normalizes absent and scalar member fields", () => {
    expect(normalizeMemberList(undefined)).toEqual([]);
    expect(normalizeMemberList("Youtu")).toEqual(["Youtu"]);
    expect(normalizeMemberList(["Kycloud", "Youtu"])).toEqual(["Kycloud", "Youtu"]);
  });

  it("shows health checks only for automatic group types", () => {
    expect(groupSupportsHealthCheck("fallback")).toBe(true);
    expect(groupSupportsHealthCheck("url-test")).toBe(true);
    expect(groupSupportsHealthCheck("select")).toBe(false);
  });
});
