<script setup lang="ts">
import { Plus } from "lucide-vue-next";
import { computed, ref } from "vue";

import StashNavigationRow from "@/components/StashNavigationRow.vue";
import StashParameterGroup from "@/components/StashParameterGroup.vue";
import StashParameterRow from "@/components/StashParameterRow.vue";
import StructuredField from "@/components/StructuredField.vue";
import StructuredValueModal from "@/components/StructuredValueModal.vue";
import { promptDialog } from "@/composables/appDialog";
import { useAppStore } from "@/stores/app";
import type { EditorField, EditorGroup } from "@/utils/editorSchemas";

const props = defineProps<{
  value: Record<string, unknown>;
  path: Array<string | number>;
  groups: EditorGroup[];
}>();

const appStore = useAppStore();
const nestedField = ref<EditorField | null>(null);
const currentType = computed(() => String(props.value.type ?? ""));
const proxyReferences = computed(() => {
  const groups = Array.isArray(appStore.document["proxy-groups"])
    ? appStore.document["proxy-groups"]
        .map((item) =>
          item && typeof item === "object"
            ? String((item as Record<string, unknown>).name ?? "")
            : "",
        )
        .filter(Boolean)
    : [];
  return [...new Set([...groups, "DIRECT", "REJECT", "PASS"])];
});
const knownKeys = computed(() =>
  new Set(props.groups.flatMap((group) => group.fields.map((field) => field.key))),
);
const advancedFields = computed(() =>
  Object.entries(props.value).filter(([key]) => !knownKeys.value.has(key)),
);

function visibleFields(group: EditorGroup) {
  return group.fields.filter((field) => {
    if (field.always || Object.prototype.hasOwnProperty.call(props.value, field.key)) return true;
    return field.types?.includes(currentType.value) ?? false;
  });
}

function update(field: EditorField, value: unknown) {
  appStore.setValue([...props.path, field.key], value);
}

function complexCount(value: unknown) {
  if (Array.isArray(value)) return value.length;
  if (value && typeof value === "object") return Object.keys(value).length;
  return 0;
}

function suggestions(field: EditorField) {
  if (field.key === "proxy") return proxyReferences.value;
  return field.suggestions ?? [];
}

function openComplex(field: EditorField) {
  if (!Object.prototype.hasOwnProperty.call(props.value, field.key)) {
    const listFields = new Set(["alpn", "arguments"]);
    appStore.setValue([...props.path, field.key], listFields.has(field.key) ? [] : {});
  }
  nestedField.value = field;
}

async function addField() {
  const key = await promptDialog({
    title: "添加高级字段",
    inputLabel: "字段名称",
    placeholder: "请输入 YAML 字段名",
  });
  if (!key || Object.prototype.hasOwnProperty.call(props.value, key)) return;
  appStore.setValue([...props.path, key], "");
}
</script>

<template>
  <div class="stash-form">
    <StashParameterGroup
      v-for="group in groups"
      :key="group.title"
      :title="group.title"
      :help="group.help"
    >
      <template v-for="field in visibleFields(group)" :key="field.key">
        <StashNavigationRow
          v-if="field.kind === 'complex'"
          :label="field.label"
          :description="field.description"
          :value="complexCount(value[field.key])"
          @open="openComplex(field)"
        />
        <StashParameterRow
          v-else
          :label="field.label"
          :description="field.description"
          :model-value="value[field.key]"
          :kind="field.kind"
          :options="field.options"
          :suggestions="suggestions(field)"
          :placeholder="field.placeholder"
          :unit="field.unit"
          :open-url="field.openUrl"
          @update:model-value="update(field, $event)"
        />
      </template>
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

    <button class="soft-button justify-center" @click="addField">
      <Plus :size="16" />
      添加高级字段
    </button>

    <StructuredValueModal
      :open="nestedField !== null"
      :title="nestedField?.label ?? '结构化参数'"
      :value="nestedField ? value[nestedField.key] : undefined"
      :path="nestedField ? [...path, nestedField.key] : path"
      @close="nestedField = null"
    />
  </div>
</template>
