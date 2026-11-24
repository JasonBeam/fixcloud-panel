import { describe, expect, it } from "vitest";

import { buildProxyNameFilter, describeProxyNameFilter } from "./regexPreset";

describe("lazy proxy name filter builder", () => {
  it("requires a selected region and GPT in the same node name", () => {
    const value = buildProxyNameFilter({
      regionIds: ["hk", "tw"],
      requiredKeywords: "GPT",
    });
    expect(value).toContain("香港");
    expect(value).toContain("台湾");
    expect(value).toContain("(?=.*(?:GPT))");
    expect(value.startsWith("(?i)")).toBe(true);
  });

  it("escapes user keywords so presets stay literal", () => {
    expect(buildProxyNameFilter({
      regionIds: [],
      requiredKeywords: "GPT+, Claude (AI)",
    })).toContain("GPT\\+|Claude \\(AI\\)");
  });

  it("supports requiring every keyword and exclusions", () => {
    const value = buildProxyNameFilter({
      regionIds: ["jp"],
      requiredKeywords: "GPT, 专线",
      excludedKeywords: "家宽",
      requireEveryKeyword: true,
    });
    expect(value).toContain("(?=.*(?:GPT))(?=.*(?:专线))");
    expect(value).toContain("(?!.*(?:家宽))");
  });

  it("describes the selected conditions in plain Chinese", () => {
    expect(describeProxyNameFilter({
      regionIds: ["hk", "tw"],
      requiredKeywords: "GPT",
    })).toBe("香港 / 台湾节点，名称必须包含任一：GPT");
  });
});
