<script setup lang="ts">
import { Check, X } from "lucide-vue-next";

import StructuredField from "@/components/StructuredField.vue";

defineProps<{
  open: boolean;
  title: string;
  value: unknown;
  path: Array<string | number>;
}>();

defineEmits<{
  close: [];
}>();
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-layer modal-layer-front" role="dialog" aria-modal="true" :aria-label="title">
      <section class="structured-value-panel">
        <header class="editor-topbar">
          <button class="editor-close-button" aria-label="关闭" @click="$emit('close')">
            <X :size="20" />
            <span>关闭</span>
          </button>
          <div class="editor-topbar-title"><h2>{{ title }}</h2></div>
          <div class="editor-topbar-actions">
            <button class="editor-save-button editor-save-button-active" @click="$emit('close')">
              <Check :size="16" />
              完成
            </button>
          </div>
        </header>
        <div class="structured-value-body">
          <StructuredField :label="title" :value="value" :path="path" />
        </div>
      </section>
    </div>
  </Teleport>
</template>
