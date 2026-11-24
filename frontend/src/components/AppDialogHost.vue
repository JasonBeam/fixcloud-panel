<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import { appDialogState, resolveDialog } from "@/composables/appDialog";

const input = ref<HTMLInputElement | null>(null);

watch(
  () => appDialogState.open,
  async (open) => {
    if (open && appDialogState.mode === "prompt") {
      await nextTick();
      input.value?.focus();
    }
  },
);

function confirm() {
  if (appDialogState.mode === "prompt") {
    const value = appDialogState.inputValue.trim();
    if (!value) return;
    resolveDialog(value);
  } else {
    resolveDialog(true);
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="appDialogState.open"
      class="modal-layer modal-layer-front"
      role="dialog"
      aria-modal="true"
      :aria-label="appDialogState.title"
      @keydown.esc="resolveDialog(null)"
    >
      <section class="app-dialog-card">
        <h2 class="text-xl font-bold">{{ appDialogState.title }}</h2>
        <p v-if="appDialogState.message" class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          {{ appDialogState.message }}
        </p>
        <label v-if="appDialogState.mode === 'prompt'" class="form-field mt-5">
          <span>{{ appDialogState.inputLabel }}</span>
          <input
            ref="input"
            v-model="appDialogState.inputValue"
            :placeholder="appDialogState.placeholder"
            @keydown.enter.prevent="confirm"
          />
        </label>
        <div class="mt-6 flex justify-end gap-2">
          <button class="soft-button min-h-11" @click="resolveDialog(null)">
            {{ appDialogState.cancelText }}
          </button>
          <button
            class="primary-button min-h-11"
            :class="{ 'danger-solid-button': appDialogState.danger }"
            @click="confirm"
          >
            {{ appDialogState.confirmText }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>
