export type RegionPreset = {
  id: string;
  label: string;
  pattern: string;
};

export const REGION_PRESETS: RegionPreset[] = [
  { id: "hk", label: "香港", pattern: "🇭🇰|香港|\\b(?:HK|Hong(?: ?Kong)?)\\b" },
  { id: "tw", label: "台湾", pattern: "🇹🇼|台湾|台灣|\\b(?:TW|Taiwan)\\b" },
  { id: "jp", label: "日本", pattern: "🇯🇵|日本|\\b(?:JP|Japan)\\b" },
  { id: "sg", label: "新加坡", pattern: "🇸🇬|新加坡|狮城|獅城|\\b(?:SG|Singapore)\\b" },
  { id: "us", label: "美国", pattern: "🇺🇸|美国|美國|\\b(?:US|USA|United States)\\b" },
  { id: "kr", label: "韩国", pattern: "🇰🇷|韩国|韓國|\\b(?:KR|Korea)\\b" },
];

export type RegexPresetInput = {
  regionIds: string[];
  requiredKeywords: string;
  excludedKeywords?: string;
  requireEveryKeyword?: boolean;
};

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function keywords(value: string) {
  return value
    .split(/[,，/、\n]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map(escapeRegex);
}

export function buildProxyNameFilter(input: RegexPresetInput) {
  const regions = REGION_PRESETS
    .filter((region) => input.regionIds.includes(region.id))
    .map((region) => region.pattern);
  const required = keywords(input.requiredKeywords);
  const excluded = keywords(input.excludedKeywords ?? "");
  const assertions: string[] = [];

  if (regions.length) assertions.push(`(?=.*(?:${regions.join("|")}))`);
  if (required.length) {
    if (input.requireEveryKeyword) {
      assertions.push(...required.map((keyword) => `(?=.*(?:${keyword}))`));
    } else {
      assertions.push(`(?=.*(?:${required.join("|")}))`);
    }
  }
  if (excluded.length) assertions.push(`(?!.*(?:${excluded.join("|")}))`);

  if (!assertions.length) return "";
  return `(?i)${assertions.join("")}.*`;
}

export function describeProxyNameFilter(input: RegexPresetInput) {
  const regionLabels = REGION_PRESETS
    .filter((region) => input.regionIds.includes(region.id))
    .map((region) => region.label);
  const required = keywords(input.requiredKeywords).map((item) => item.replace(/\\/g, ""));
  const excluded = keywords(input.excludedKeywords ?? "").map((item) => item.replace(/\\/g, ""));
  const parts: string[] = [];

  if (regionLabels.length) parts.push(`${regionLabels.join(" / ")}节点`);
  if (required.length) {
    parts.push(`名称必须包含${input.requireEveryKeyword ? "全部" : "任一"}：${required.join("、")}`);
  }
  if (excluded.length) parts.push(`排除：${excluded.join("、")}`);
  return parts.join("，") || "尚未选择筛选条件";
}
