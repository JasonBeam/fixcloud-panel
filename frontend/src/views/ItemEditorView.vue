<script setup lang="ts">
import { Plus, Trash2 } from "lucide-vue-next";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import EditorTopBar from "@/components/EditorTopBar.vue";
import ObjectParameterEditor from "@/components/ObjectParameterEditor.vue";
import PrimitiveParameterEditor from "@/components/PrimitiveParameterEditor.vue";
import ProxyGroupEditor from "@/components/ProxyGroupEditor.vue";
import RuleFieldEditor from "@/components/RuleFieldEditor.vue";
import StructuredField from "@/components/StructuredField.vue";
import { promptDialog } from "@/composables/appDialog";
import { requestReferenceDelete } from "@/composables/referenceGuard";
import { allowNextRoute, requestDraftTransition } from "@/composables/draftGuard";
import { useAppStore } from "@/stores/app";
import { scanDeleteImpact, type DeleteImpact } from "@/utils/referenceIntegrity";
import {
  proxyEditorGroups,
  proxyProviderGroups,
  rewriteEditorGroups,
  ruleProviderGroups,
  scriptEditorGroups,
} from "@/utils/editorSchemas";

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();

const section = computed(() => String(route.params.section));
const itemId = computed(() => String(route.params.itemId));
const mapItemName = ref(itemId.value);
watch(itemId, (value) => { mapItemName.value = value; });

const sectionTitles: Record<string, string> = {
  general: "通用设置",
  dns: "DNS 服务器",
  proxies: "本地代理",
  "proxy-groups": "策略组",
  "proxy-providers": "远程代理集",
  rules: "规则",
  "rule-providers": "远程规则集",
  rewrite: "HTTP 改写",
  script: "脚本",
  other: "其他设置",
};

const target = computed(() => {
  if (section.value === "general") return appStore.document[itemId.value];
  if (section.value === "dns") {
    return (appStore.document.dns as Record<string, unknown> | undefined)?.[itemId.value];
  }
  if (section.value === "other") return appStore.document[itemId.value];
  const root = appStore.document[section.value];
  if (Array.isArray(root)) return root[Number(itemId.value)];
  if (root && typeof root === "object") {
    return (root as Record<string, unknown>)[itemId.value];
  }
  return undefined;
});

const targetPath = computed<Array<string | number>>(() => {
  if (section.value === "general" || section.value === "other") return [itemId.value];
  if (section.value === "dns") return ["dns", itemId.value];
  const root = appStore.document[section.value];
  if (Array.isArray(root)) return [section.value, Number(itemId.value)];
  return [section.value, itemId.value];
});

const objectEntries = computed(() => {
  const value = target.value;
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { primary: [] as Array<[string, unknown]>, advanced: [] as Array<[string, unknown]> };
  }
  const record = value as Record<string, unknown>;
  const type = String(record.type ?? "");
  const common: Record<string, string[]> = {
    proxies: ["name", "type", "server", "port", "password", "cipher", "uuid", "alterId", "network", "tls", "udp", "sni", "servername", "client-fingerprint"],
    "proxy-groups": [
      "name", "type", "icon", "hidden", "note", "proxies", "use", "include-from-url",
      "include-all", "include-all-proxies", "include-all-providers", "filter",
      "exclude-filter", "exclude-type", "url", "interval", "lazy", "timeout",
      "max-failed-times", "expected-status", "tolerance", "strategy", "empty-fallback",
      "disable-udp",
    ],
    "proxy-providers": ["type", "url", "path", "interval", "proxy", "health-check", "override"],
    "rule-providers": ["type", "behavior", "url", "path", "interval", "proxy"],
  };
  const typeSpecific: Record<string, string[]> = {
    vmess: ["uuid", "alterId", "cipher", "network", "ws-opts", "grpc-opts"],
    vless: ["uuid", "flow", "network", "reality-opts", "ws-opts", "grpc-opts"],
    trojan: ["password", "network", "ws-opts", "grpc-opts"],
    hysteria: ["auth-str", "up", "down", "alpn", "obfs"],
    hysteria2: ["password", "up", "down", "obfs", "obfs-password"],
    tuic: ["uuid", "password", "congestion-controller", "udp-relay-mode"],
  };
  const ordered = [...(common[section.value] ?? Object.keys(record)), ...(typeSpecific[type] ?? [])];
  const primaryKeys = new Set(ordered.filter((key) => key in record));
  const primary = ordered
    .filter((key, index) => primaryKeys.has(key) && ordered.indexOf(key) === index)
    .map((key) => [key, record[key]] as [string, unknown]);
  const advanced = Object.entries(record).filter(([key]) => !primaryKeys.has(key));
  return { primary, advanced };
});

async function addField() {
  if (!target.value || typeof target.value !== "object" || Array.isArray(target.value)) return;
  const key = await promptDialog({
    title: "添加高级字段",
    inputLabel: "字段名称",
    placeholder: "例如：client-fingerprint",
  });
  if (!key || Object.prototype.hasOwnProperty.call(target.value, key)) return;
  appStore.setValue([...targetPath.value, key], "");
}

async function deleteItem() {
  const impact = scanDeleteImpact(appStore.document, targetPath.value);
  const choice = await requestReferenceDelete(impact);
  if (choice.resolution === "cancel") return;
  if (choice.resolution === "remove" || choice.resolution === "replace") {
    applyReferenceResolution(impact, choice.resolution, choice.replacement);
  }
  appStore.deleteValue(targetPath.value);
  void router.push("/editor/" + section.value);
}

function applyReferenceResolution(impact: DeleteImpact, resolution: "remove" | "replace", replacement: string) {
  const references = [...impact.references].sort((left, right) => JSON.stringify(right.path).localeCompare(JSON.stringify(left.path)));
  for (const reference of references) {
    if (resolution === "remove") {
      appStore.deleteValue(reference.path);
      continue;
    }
    if (reference.path[0] === "rules") {
      const current = String((appStore.document.rules as unknown[])[Number(reference.path[1])]);
      const parts = current.split(",").map((part) => part.trim());
      if (impact.type === "Rule Provider") parts[1] = replacement;
      else {
        const targetIndex = parts.at(-1)?.toLowerCase() === "no-resolve" ? parts.length - 2 : parts.length - 1;
        parts[targetIndex] = replacement;
      }
      appStore.setValue(reference.path, parts.join(","));
    } else {
      appStore.setValue(reference.path, replacement);
    }
  }
}

async function renameMapItem() {
  if (!["proxy-providers", "rule-providers"].includes(section.value)) return;
  const nextName = mapItemName.value.trim();
  const oldName = itemId.value;
  if (!nextName || nextName === oldName) {
    mapItemName.value = oldName;
    return;
  }
  const root = appStore.document[section.value];
  if (!root || typeof root !== "object" || Array.isArray(root)) return;
  const record = root as Record<string, unknown>;
  if (Object.prototype.hasOwnProperty.call(record, nextName)) {
    appStore.notify(`“${nextName}”已经存在`);
    mapItemName.value = oldName;
    return;
  }
  const oldIndex = Object.keys(record).indexOf(oldName);
  const snapshot = JSON.parse(JSON.stringify(record[oldName]));
  appStore.setValue([section.value, nextName], snapshot);
  const addedIndex = Object.keys(record).indexOf(nextName);
  if (oldIndex >= 0 && addedIndex >= 0 && oldIndex !== addedIndex) {
    appStore.moveValue([section.value], addedIndex, oldIndex);
  }
  appStore.deleteValue([section.value, oldName]);
  allowNextRoute();
  await router.replace({
    name: "item",
    params: { section: section.value, itemId: nextName },
  });
}

async function closeEditor() {
  await requestDraftTransition(
    async () => {
      await router.push(`/editor/${section.value}`);
    },
    sectionTitles[section.value] ?? "配置列表",
    "close",
  );
}

</script>

<template>
  <div class="page-width editor-detail-page">
    <EditorTopBar
      :title="sectionTitles[section] ?? '配置编辑'"
      close-label="关闭"
      show-save
      @close="closeEditor"
    />

    <div v-if="target !== undefined" class="editor-form">
      <RuleFieldEditor
        v-if="section === 'rules' && typeof target === 'string'"
        :value="target"
        :path="targetPath"
      />
      <ProxyGroupEditor
        v-else-if="section === 'proxy-groups' && target && typeof target === 'object' && !Array.isArray(target)"
        :value="target as Record<string, unknown>"
        :path="targetPath"
      />
      <ObjectParameterEditor
        v-else-if="section === 'proxies' && target && typeof target === 'object' && !Array.isArray(target)"
        :value="target as Record<string, unknown>"
        :path="targetPath"
        :groups="proxyEditorGroups"
      />
      <template
        v-else-if="['proxy-providers', 'rule-providers'].includes(section) && target && typeof target === 'object' && !Array.isArray(target)"
      >
        <div class="stash-form provider-identity-form">
          <section>
            <h3 class="stash-section-title">名称</h3>
            <div class="stash-group-card">
              <label class="stash-form-row">
                <span>Provider 名称</span>
                <input v-model="mapItemName" autocomplete="off" @change="renameMapItem" />
              </label>
            </div>
          </section>
        </div>
        <ObjectParameterEditor
          :value="target as Record<string, unknown>"
          :path="targetPath"
          :groups="section === 'proxy-providers' ? proxyProviderGroups : ruleProviderGroups"
        />
      </template>
      <ObjectParameterEditor
        v-else-if="section === 'rewrite' && target && typeof target === 'object' && !Array.isArray(target)"
        :value="target as Record<string, unknown>"
        :path="targetPath"
        :groups="rewriteEditorGroups"
      />
      <ObjectParameterEditor
        v-else-if="section === 'script' && target && typeof target === 'object' && !Array.isArray(target)"
        :value="target as Record<string, unknown>"
        :path="targetPath"
        :groups="scriptEditorGroups"
      />
      <PrimitiveParameterEditor
        v-else-if="section === 'script' && ['string', 'number', 'boolean'].includes(typeof target)"
        label="脚本内容"
        :value="target as string | number | boolean"
        :path="targetPath"
        multiline
      />
      <PrimitiveParameterEditor
        v-else-if="section === 'rewrite' && ['string', 'number', 'boolean'].includes(typeof target)"
        label="改写表达式"
        :value="target as string | number | boolean"
        :path="targetPath"
      />
      <template v-else-if="target && typeof target === 'object' && !Array.isArray(target)">
        <div v-if="objectEntries.primary.length" class="form-section-heading">
          <strong>常用参数</strong>
          <span>根据当前类型显示</span>
        </div>
        <StructuredField
          v-for="[key, value] in objectEntries.primary"
          :key="key"
          :label="key"
          :value="value"
          :path="[...targetPath, key]"
        />
        <details v-if="objectEntries.advanced.length" class="advanced-fields-card">
          <summary>
            <span>高级字段</span>
            <small>{{ objectEntries.advanced.length }} 项 · 原样保留</small>
          </summary>
          <div class="structured-children">
            <StructuredField
              v-for="[key, value] in objectEntries.advanced"
              :key="key"
              :label="key"
              :value="value"
              :path="[...targetPath, key]"
            />
          </div>
        </details>
        <button class="soft-button justify-center" @click="addField">
          <Plus :size="16" />
          添加高级字段
        </button>
      </template>
      <StructuredField v-else :label="itemId" :value="target" :path="targetPath" />

      <button
        v-if="section === 'proxy-groups' && target && typeof target === 'object' && !Array.isArray(target)"
        class="soft-button justify-center"
        @click="addField"
      >
        <Plus :size="16" />
        添加高级字段
      </button>

      <button
        v-if="!['general', 'dns'].includes(section)"
        class="danger-button"
        @click="deleteItem"
      >
        <Trash2 :size="17" />
        删除此项目
      </button>
    </div>
    <div v-else class="empty-card">
      <p>此项目已不存在，可能已被删除。</p>
      <button class="soft-button mt-4" @click="router.back()">返回列表</button>
    </div>
  </div>
</template>
