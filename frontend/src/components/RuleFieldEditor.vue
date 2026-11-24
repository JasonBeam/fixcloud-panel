<script setup lang="ts">
import { computed, reactive, watch } from "vue";

import StashParameterGroup from "@/components/StashParameterGroup.vue";
import { useAppStore } from "@/stores/app";

const props = defineProps<{
  value: string;
  path: Array<string | number>;
}>();

const appStore = useAppStore();
const state = reactive({
  type: "DOMAIN-SUFFIX",
  content: "",
  target: "DIRECT",
  noResolve: false,
  hidden: false,
  note: "",
  raw: "",
});

let hydrating = false;
let preservedOptions: string[] = [];

const logical = computed(() =>
  ["AND", "OR", "NOT", "SUB-RULE"].includes(state.type.toUpperCase()),
);

function hydrate(raw: string) {
  hydrating = true;
  const parts = raw.split(",").map((part) => part.trim());
  const type = (parts[0] || "DOMAIN-SUFFIX").toUpperCase();
  const isMatch = type === "MATCH";
  const isLogical = ["AND", "OR", "NOT", "SUB-RULE"].includes(type);
  const options = isMatch ? parts.slice(2) : parts.slice(3);

  state.type = type;
  state.content = isMatch ? "" : (parts[1] ?? "");
  state.target = isMatch ? (parts[1] ?? "DIRECT") : (parts[2] ?? "DIRECT");
  state.noResolve = options.some((item) => item.toLowerCase() === "no-resolve");
  state.hidden = options.some((item) => item.toLowerCase() === "hidden");
  state.note = options.find((item) => item.toLowerCase().startsWith("remark="))?.slice(7) ?? "";
  state.raw = raw;
  preservedOptions = isLogical ? [] : options;
  queueMicrotask(() => {
    hydrating = false;
  });
}

hydrate(props.value);
watch(
  () => props.value,
  (value) => {
    if (value !== state.raw && value !== buildRule()) hydrate(value);
  },
);

const ruleProviders = computed(() => {
  const value = appStore.document["rule-providers"];
  return value && typeof value === "object" && !Array.isArray(value) ? Object.keys(value) : [];
});

const targets = computed(() => {
  const groups = Array.isArray(appStore.document["proxy-groups"])
    ? appStore.document["proxy-groups"]
        .map((item) =>
          item && typeof item === "object"
            ? String((item as Record<string, unknown>).name ?? "")
            : "",
        )
        .filter(Boolean)
    : [];
  return [...new Set([...groups, "DIRECT", "REJECT", "REJECT-DROP", "PASS"])];
});

const contentLabel = computed(() => {
  if (state.type === "RULE-SET") return "远程规则集";
  if (state.type === "IP-CIDR" || state.type === "IP-CIDR6") return "CIDR";
  if (state.type === "GEOIP") return "国家或地区代码";
  return "内容";
});

const typeOptions = computed(() => {
  const options = [
    "RULE-SET",
    "DOMAIN-SUFFIX",
    "DOMAIN",
    "DOMAIN-KEYWORD",
    "IP-CIDR",
    "IP-CIDR6",
    "GEOIP",
    "GEOSITE",
    "PROCESS-NAME",
    "PROCESS-PATH",
    "NETWORK",
    "DST-PORT",
    "SRC-IP-CIDR",
    "MATCH",
  ];
  if (!options.includes(state.type)) options.unshift(state.type);
  return options;
});

function applyOption(
  options: string[],
  token: string,
  enabled: boolean,
  predicate = (item: string) => item.toLowerCase() === token.toLowerCase(),
) {
  const index = options.findIndex(predicate);
  if (enabled && index < 0) options.push(token);
  if (!enabled && index >= 0) options.splice(index, 1);
}

function buildRule() {
  if (logical.value) return state.raw;
  const options = [...preservedOptions];
  applyOption(options, "no-resolve", state.noResolve);
  applyOption(options, "hidden", state.hidden);
  const remarkIndex = options.findIndex((item) => item.toLowerCase().startsWith("remark="));
  if (state.note) {
    const nextRemark = `remark=${state.note}`;
    if (remarkIndex >= 0) options.splice(remarkIndex, 1, nextRemark);
    else options.push(nextRemark);
  } else if (remarkIndex >= 0) {
    options.splice(remarkIndex, 1);
  }
  return (
    state.type === "MATCH"
      ? ["MATCH", state.target, ...options]
      : [state.type, state.content, state.target, ...options]
  ).join(",");
}

watch(
  state,
  () => {
    if (hydrating) return;
    appStore.setValue(props.path, buildRule());
  },
  { deep: true },
);
</script>

<template>
  <div v-if="logical" class="stash-form">
    <div class="advanced-callout">
      该逻辑规则包含嵌套表达式，当前使用单条规则值编辑；保存时不会拆解、格式化或丢失结构。
    </div>
    <StashParameterGroup title="高级逻辑规则">
        <label class="stash-form-row stash-form-row-stacked">
          <span>完整规则</span>
          <input v-model="state.raw" />
        </label>
    </StashParameterGroup>
  </div>

  <div v-else class="stash-form">
    <StashParameterGroup
      title="基础信息"
      :help="state.type === 'RULE-SET'
        ? '引用主配置中的 rule-providers，不会修改规则目录中的下载文件。'
        : '修改只进入当前浏览器草稿，顶部保存后仍需确认完整 Diff。'"
    >
        <label class="stash-form-row">
          <span>规则类型</span>
          <select v-model="state.type">
            <option v-for="type in typeOptions" :key="type" :value="type">{{ type }}</option>
          </select>
        </label>
        <label v-if="state.type !== 'MATCH'" class="stash-form-row">
          <span>{{ contentLabel }}</span>
          <input
            v-model="state.content"
            :list="state.type === 'RULE-SET' ? 'rule-provider-options' : undefined"
            autocomplete="off"
          />
          <datalist v-if="state.type === 'RULE-SET'" id="rule-provider-options">
            <option v-for="provider in ruleProviders" :key="provider" :value="provider" />
          </datalist>
        </label>
        <label class="stash-form-row">
          <span>分流策略</span>
          <input v-model="state.target" list="rule-target-options" autocomplete="off" />
          <datalist id="rule-target-options">
            <option v-for="target in targets" :key="target" :value="target" />
          </datalist>
        </label>
    </StashParameterGroup>

    <StashParameterGroup title="选项">
        <label class="stash-toggle-row">
          <span>
            <strong>不解析主机名</strong>
            <small>写入 no-resolve，适用于 IP 与 GEOIP 类规则</small>
          </span>
          <input v-model="state.noResolve" type="checkbox" />
          <i class="toggle-track" />
        </label>
        <label class="stash-toggle-row">
          <span>
            <strong>隐藏连接</strong>
            <small>写入 hidden 扩展选项</small>
          </span>
          <input v-model="state.hidden" type="checkbox" />
          <i class="toggle-track" />
        </label>
        <label class="stash-form-row">
          <span>备注</span>
          <input v-model="state.note" placeholder="可选，保存为 remark= 扩展选项" />
        </label>
    </StashParameterGroup>

    <div v-if="preservedOptions.some((item) => !['no-resolve', 'hidden'].includes(item.toLowerCase()) && !item.toLowerCase().startsWith('remark='))" class="advanced-callout">
      此规则还包含未识别的扩展选项；图形化修改后仍会按原值保留。
    </div>
  </div>
</template>
