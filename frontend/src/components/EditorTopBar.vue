<script setup lang="ts">
import { ArrowLeft, Plus } from "lucide-vue-next";

import { useAppStore } from "@/stores/app";

withDefaults(
  defineProps<{
    title: string;
    showAdd?: boolean;
    showSave?: boolean;
    closeLabel?: string;
  }>(),
  {
    showAdd: false,
    showSave: false,
    closeLabel: "关闭",
  },
);

const emit = defineEmits<{
  close: [];
  add: [];
}>();

const appStore = useAppStore();

async function save() {
  try {
    await appStore.createPreview();
  } catch {
    // 具体错误由页面和全局 Diff 状态显示。
  }
}
</script>

<template>
  <header class="editor-topbar">
    <button class="editor-close-button" :aria-label="closeLabel" @click="emit('close')">
      <ArrowLeft :size="21" />
      <span>{{ closeLabel }}</span>
    </button>

    <div class="editor-topbar-title">
      <h2>{{ title }}</h2>
      <span v-if="appStore.dirtyCount" class="editor-dirty-label">
        <i />
        有未保存修改
      </span>
    </div>

    <div class="editor-topbar-actions">
      <button
        v-if="showAdd"
        class="editor-add-button"
        aria-label="新增项目"
        @click="emit('add')"
      >
        <Plus :size="19" />
      </button>
      <button
        v-if="showSave"
        class="editor-save-button"
        :class="{ 'editor-save-button-active': appStore.canSave }"
        :disabled="!appStore.canSave"
        @click="save"
      >
        {{ appStore.saving ? "准备中…" : "保存" }}
      </button>
    </div>
  </header>
</template>
