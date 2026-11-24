<script setup lang="ts">
import { RotateCcw, ShieldCheck } from "lucide-vue-next";

import { confirmDialog } from "@/composables/appDialog";
import { useAppStore } from "@/stores/app";

const appStore = useAppStore();

async function discard() {
  const confirmed = await confirmDialog({
    title: "放弃全部修改？",
    message: `当前 ${appStore.dirtyCount} 项草稿将被清除，此操作无法撤销。`,
    confirmText: "确认放弃",
    danger: true,
  });
  if (confirmed) await appStore.discardChanges();
}
</script>

<template>
  <div v-if="appStore.dirtyCount > 0" class="save-bar">
    <div>
      <div class="flex items-center gap-2 text-sm font-semibold">
        <ShieldCheck :size="17" class="text-emerald-500" />
        {{ appStore.dirtyCount }} 项未保存
      </div>
      <div class="mt-0.5 text-xs text-[var(--text-muted)]">保存前将显示完整 Diff</div>
    </div>
    <div class="flex gap-2">
      <button class="soft-button" :disabled="appStore.saving" @click="discard">
        <RotateCcw :size="15" />
        放弃
      </button>
      <button class="primary-button" :disabled="!appStore.canSave" @click="appStore.createPreview">
        {{ appStore.saving ? "检查中…" : "预览保存" }}
      </button>
    </div>
  </div>
</template>
