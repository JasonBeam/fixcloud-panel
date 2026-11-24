<script setup lang="ts">
import { ChevronRight, Images, Sparkles } from "lucide-vue-next";
import { computed, ref } from "vue";

import IconCatalogPicker from "@/components/IconCatalogPicker.vue";
import ProxyGroupMemberPicker from "@/components/ProxyGroupMemberPicker.vue";
import ProxyGroupIcon from "@/components/ProxyGroupIcon.vue";
import RegexFilterBuilder from "@/components/RegexFilterBuilder.vue";
import StashParameterGroup from "@/components/StashParameterGroup.vue";
import StructuredField from "@/components/StructuredField.vue";
import { useAppStore } from "@/stores/app";
import {
  groupSupportsHealthCheck,
  normalizeMemberList,
  proxyGroupMemberOptions,
  type ProxyGroupMemberKind,
} from "@/utils/proxyGroup";

const props = defineProps<{
  value: Record<string, unknown>;
  path: Array<string | number>;
}>();

const appStore = useAppStore();
const pickerKind = ref<ProxyGroupMemberKind | null>(null);
const showRegexBuilder = ref(false);
const showIconCatalog = ref(false);

const commonKeys = new Set(["name", "type", "icon", "hidden", "note"]);
const memberKeys = new Set([
  "proxies",
  "use",
  "include-all",
  "include-all-proxies",
  "include-all-providers",
  "include-from-url",
  "filter",
  "exclude-filter",
  "exclude-type",
]);
const behaviorKeys = new Set([
  "url",
  "interval",
  "tolerance",
  "strategy",
  "lazy",
  "empty-fallback",
  "timeout",
  "max-failed-times",
  "disable-udp",
  "expected-status",
]);

const advancedFields = computed(() =>
  Object.entries(props.value).filter(
    ([key]) => !commonKeys.has(key) && !memberKeys.has(key) && !behaviorKeys.has(key),
  ),
);
const groupType = computed(() => String(props.value.type ?? "select"));
const hasHealthCheck = computed(() => groupSupportsHealthCheck(groupType.value));
const pickerTitle = computed(() => {
  if (pickerKind.value === "use") return "包括远程代理集";
  if (pickerKind.value === "include-from-url") return "包括来自 URL 的代理";
  return "包括代理和策略组";
});
const pickerValues = computed(() =>
  normalizeMemberList(pickerKind.value ? props.value[pickerKind.value] : []),
);
const pickerOptions = computed(() =>
  pickerKind.value
    ? proxyGroupMemberOptions(
        appStore.document,
        pickerKind.value,
        String(props.value.name ?? ""),
      )
    : [],
);

function setText(key: string, event: Event) {
  appStore.setValue([...props.path, key], (event.target as HTMLInputElement).value);
}

function setNumber(key: string, event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  appStore.setValue([...props.path, key], raw === "" ? "" : Number(raw));
}

function setBoolean(key: string, event: Event) {
  appStore.setValue([...props.path, key], (event.target as HTMLInputElement).checked);
}

function setMemberValues(values: string[]) {
  if (!pickerKind.value) return;
  appStore.setValue([...props.path, pickerKind.value], values);
  pickerKind.value = null;
}

function memberCount(key: ProxyGroupMemberKind) {
  return normalizeMemberList(props.value[key]).length;
}

function applyGeneratedFilter(value: string) {
  appStore.setValue([...props.path, "filter"], value);
  showRegexBuilder.value = false;
}

function selectIcon(url: string) {
  appStore.setValue([...props.path, "icon"], url);
  showIconCatalog.value = false;
}
</script>

<template>
  <div class="stash-form">
    <StashParameterGroup title="通用设置">
        <label class="stash-form-row">
          <span>名称</span>
          <input
            :value="String(value.name ?? '')"
            autocomplete="off"
            @input="setText('name', $event)"
          />
        </label>
        <label class="stash-form-row">
          <span>类型</span>
          <select :value="String(value.type ?? 'select')" @change="setText('type', $event)">
            <option value="select">Select</option>
            <option value="url-test">URL Test</option>
            <option value="fallback">Fallback</option>
            <option value="load-balance">Load Balance</option>
            <option value="relay">Relay</option>
          </select>
        </label>
        <div class="stash-form-row stash-icon-url-row">
          <span>图标 URL</span>
          <input
            :value="String(value.icon ?? '')"
            placeholder="https://…"
            @input="setText('icon', $event)"
          />
          <button
            type="button"
            class="icon-catalog-open-button"
            aria-label="从图标集选择"
            @click="showIconCatalog = true"
          >
            <Images :size="16" />
            选择
          </button>
          <ProxyGroupIcon
            :src="String(value.icon ?? '')"
            :name="String(value.name ?? '策略组')"
          />
        </div>
        <label class="stash-toggle-row">
          <span>
            <strong>从列表中隐藏</strong>
            <small>对应 YAML 的 hidden 字段</small>
          </span>
          <input
            type="checkbox"
            :checked="Boolean(value.hidden)"
            @change="setBoolean('hidden', $event)"
          />
          <i class="toggle-track" />
        </label>
        <label class="stash-form-row">
          <span>备注</span>
          <input
            :value="String(value.note ?? '')"
            placeholder="可选"
            @input="setText('note', $event)"
          />
        </label>
    </StashParameterGroup>

    <StashParameterGroup
      title="成员来源"
      help="成员顺序会按列表保存；筛选器只作用于远程代理集和自动包含的节点。"
    >
        <button type="button" class="stash-navigation-row" @click="pickerKind = 'proxies'">
          <span>
            <strong>包括代理和策略组</strong>
            <small>节点、内置策略及其他策略组</small>
          </span>
          <b>{{ memberCount("proxies") }}</b>
          <ChevronRight :size="18" />
        </button>
        <button type="button" class="stash-navigation-row" @click="pickerKind = 'use'">
          <span>
            <strong>包括远程代理集</strong>
            <small>引用 proxy-providers</small>
          </span>
          <b>{{ memberCount("use") }}</b>
          <ChevronRight :size="18" />
        </button>
        <button type="button" class="stash-navigation-row" @click="pickerKind = 'include-from-url'">
          <span>
            <strong>包括来自 URL 的代理</strong>
            <small>Stash 兼容字段</small>
          </span>
          <b>{{ memberCount("include-from-url") }}</b>
          <ChevronRight :size="18" />
        </button>
        <label class="stash-toggle-row">
          <span><strong>包括所有代理和代理集</strong><small>对应 include-all</small></span>
          <input type="checkbox" :checked="Boolean(value['include-all'])" @change="setBoolean('include-all', $event)" />
          <i class="toggle-track" />
        </label>
        <label class="stash-toggle-row">
          <span><strong>包括所有本地代理</strong><small>不包括其他策略组</small></span>
          <input type="checkbox" :checked="Boolean(value['include-all-proxies'])" @change="setBoolean('include-all-proxies', $event)" />
          <i class="toggle-track" />
        </label>
        <label class="stash-toggle-row">
          <span><strong>包括所有远程代理集</strong><small>启用后 Mihomo 会忽略 use 列表</small></span>
          <input type="checkbox" :checked="Boolean(value['include-all-providers'])" @change="setBoolean('include-all-providers', $event)" />
          <i class="toggle-track" />
        </label>
        <div class="stash-form-row stash-filter-row">
          <span>正则表达式过滤器</span>
          <input :value="String(value.filter ?? '')" placeholder="例如 (?i)gpt" @input="setText('filter', $event)" />
          <button
            type="button"
            class="regex-builder-button"
            aria-label="打开懒人筛选"
            @click="showRegexBuilder = true"
          >
            <Sparkles :size="15" />
            懒人筛选
          </button>
        </div>
        <label class="stash-form-row">
          <span>排除正则表达式</span>
          <input :value="String(value['exclude-filter'] ?? '')" placeholder="可选" @input="setText('exclude-filter', $event)" />
        </label>
        <label class="stash-form-row">
          <span>排除节点类型</span>
          <input :value="String(value['exclude-type'] ?? '')" placeholder="例如 ss|http" @input="setText('exclude-type', $event)" />
        </label>
    </StashParameterGroup>

    <StashParameterGroup title="选项">
        <label v-if="groupType === 'url-test'" class="stash-form-row">
          <span>延迟容差</span>
          <span class="stash-value-with-unit">
            <input type="number" min="0" :value="String(value.tolerance ?? '')" placeholder="0" @input="setNumber('tolerance', $event)" />
            <small>ms</small>
          </span>
        </label>
        <label v-if="groupType === 'load-balance'" class="stash-form-row">
          <span>负载均衡策略</span>
          <select :value="String(value.strategy ?? 'consistent-hashing')" @change="setText('strategy', $event)">
            <option value="consistent-hashing">Consistent Hashing</option>
            <option value="round-robin">Round Robin</option>
            <option value="sticky-sessions">Sticky Sessions</option>
          </select>
        </label>
        <label class="stash-form-row">
          <span>空组回退节点</span>
          <input :value="String(value['empty-fallback'] ?? '')" placeholder="COMPATIBLE" @input="setText('empty-fallback', $event)" />
        </label>
        <label class="stash-toggle-row">
          <span><strong>禁用 UDP</strong></span>
          <input type="checkbox" :checked="Boolean(value['disable-udp'])" @change="setBoolean('disable-udp', $event)" />
          <i class="toggle-track" />
        </label>
    </StashParameterGroup>

    <StashParameterGroup v-if="hasHealthCheck" title="定期延迟测试">
        <label class="stash-form-row">
          <span>测试地址</span>
          <input :value="String(value.url ?? '')" placeholder="https://www.gstatic.com/generate_204" @input="setText('url', $event)" />
        </label>
        <label class="stash-form-row">
          <span>延迟测试间隔</span>
          <span class="stash-value-with-unit">
            <input type="number" min="0" :value="String(value.interval ?? '')" placeholder="600" @input="setNumber('interval', $event)" />
            <small>秒</small>
          </span>
        </label>
        <label class="stash-form-row">
          <span>测试超时</span>
          <span class="stash-value-with-unit">
            <input type="number" min="0" :value="String(value.timeout ?? '')" placeholder="5000" @input="setNumber('timeout', $event)" />
            <small>ms</small>
          </span>
        </label>
        <label class="stash-form-row">
          <span>最大失败次数</span>
          <input type="number" min="1" :value="String(value['max-failed-times'] ?? '')" placeholder="5" @input="setNumber('max-failed-times', $event)" />
        </label>
        <label class="stash-form-row">
          <span>期望 HTTP 状态</span>
          <input :value="String(value['expected-status'] ?? '')" placeholder="*" @input="setText('expected-status', $event)" />
        </label>
        <label class="stash-toggle-row">
          <span><strong>惰性模式</strong><small>未使用此策略组时不主动测试</small></span>
          <input type="checkbox" :checked="Boolean(value.lazy)" @change="setBoolean('lazy', $event)" />
          <i class="toggle-track" />
        </label>
    </StashParameterGroup>

    <details v-if="advancedFields.length" class="advanced-fields-card">
      <summary>
        <span>高级字段</span>
        <small>{{ advancedFields.length }} 项 · 保存时原样保留</small>
      </summary>
      <div class="structured-children">
        <StructuredField
          v-for="[key, fieldValue] in advancedFields"
          :key="key"
          :label="key"
          :value="fieldValue"
          :path="[...path, key]"
        />
      </div>
    </details>

    <ProxyGroupMemberPicker
      :open="pickerKind !== null"
      :kind="pickerKind ?? 'proxies'"
      :title="pickerTitle"
      :model-value="pickerValues"
      :options="pickerOptions"
      @close="pickerKind = null"
      @save="setMemberValues"
    />
    <RegexFilterBuilder
      :open="showRegexBuilder"
      @close="showRegexBuilder = false"
      @apply="applyGeneratedFilter"
    />
    <IconCatalogPicker
      :open="showIconCatalog"
      :model-value="String(value.icon ?? '')"
      @close="showIconCatalog = false"
      @select="selectIcon"
    />
  </div>
</template>
