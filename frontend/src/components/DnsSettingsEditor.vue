<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

import StashNavigationRow from "@/components/StashNavigationRow.vue";
import StashParameterGroup from "@/components/StashParameterGroup.vue";
import StashParameterRow from "@/components/StashParameterRow.vue";
import StructuredField from "@/components/StructuredField.vue";
import { allowNextRoute } from "@/composables/draftGuard";
import { useAppStore } from "@/stores/app";

const appStore = useAppStore();
const router = useRouter();
const dns = computed(() => (appStore.document.dns ?? {}) as Record<string, unknown>);

const baseKeys = new Set(["enable", "listen", "ipv6", "enhanced-mode", "fake-ip-range"]);
const listKeys = ["default-nameserver", "nameserver", "fallback", "fake-ip-filter"];
const knownKeys = new Set([...baseKeys, ...listKeys]);
const advancedFields = computed(() =>
  Object.entries(dns.value).filter(([key]) => !knownKeys.has(key)),
);

function set(key: string, value: unknown) {
  appStore.setValue(["dns", key], value);
}

function count(key: string) {
  const value = dns.value[key];
  if (Array.isArray(value)) return value.length;
  if (value && typeof value === "object") return Object.keys(value).length;
  return value === undefined ? 0 : 1;
}

async function openList(key: string) {
  if (!Object.prototype.hasOwnProperty.call(dns.value, key)) {
    set(key, []);
    allowNextRoute();
  }
  await router.push({ name: "item", params: { section: "dns", itemId: key } });
}
</script>

<template>
  <div class="stash-form">
    <StashParameterGroup title="基础设置">
      <StashParameterRow label="启用 DNS" :model-value="dns.enable" kind="toggle" @update:model-value="set('enable', $event)" />
      <StashParameterRow label="监听地址" :model-value="dns.listen" placeholder="0.0.0.0:1053" @update:model-value="set('listen', $event)" />
      <StashParameterRow label="启用 IPv6" :model-value="dns.ipv6" kind="toggle" @update:model-value="set('ipv6', $event)" />
      <StashParameterRow
        label="增强模式"
        :model-value="dns['enhanced-mode']"
        kind="select"
        :options="[
          { value: 'fake-ip', label: 'Fake IP' },
          { value: 'redir-host', label: 'Redir Host' },
          { value: 'normal', label: 'Normal' },
        ]"
        @update:model-value="set('enhanced-mode', $event)"
      />
      <StashParameterRow label="Fake IP 范围" :model-value="dns['fake-ip-range']" placeholder="198.18.0.1/16" @update:model-value="set('fake-ip-range', $event)" />
    </StashParameterGroup>

    <StashParameterGroup title="服务器与过滤器">
      <StashNavigationRow label="默认 DNS" description="解析上游服务器域名" :value="count('default-nameserver')" @open="openList('default-nameserver')" />
      <StashNavigationRow label="Nameserver" description="主要 DNS 服务器" :value="count('nameserver')" @open="openList('nameserver')" />
      <StashNavigationRow label="Fallback" description="备用 DNS 服务器" :value="count('fallback')" @open="openList('fallback')" />
      <StashNavigationRow label="Fake IP Filter" description="不使用 Fake IP 的域名" :value="count('fake-ip-filter')" @open="openList('fake-ip-filter')" />
    </StashParameterGroup>

    <details v-if="advancedFields.length" class="advanced-fields-card">
      <summary>
        <span>高级字段</span>
        <small>{{ advancedFields.length }} 项 · 原样保留</small>
      </summary>
      <div class="structured-children">
        <StructuredField
          v-for="[key, fieldValue] in advancedFields"
          :key="key"
          :label="key"
          :value="fieldValue"
          :path="['dns', key]"
        />
      </div>
    </details>
  </div>
</template>
