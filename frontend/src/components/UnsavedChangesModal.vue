<script setup lang="ts">
import { AlertTriangle, Save, Trash2, X } from "lucide-vue-next";

import {
  askDiscardConfirmation,
  cancelDraftTransition,
  discardAndContinue,
  draftGuardState,
  saveAndContinue,
} from "@/composables/draftGuard";
import { useAppStore } from "@/stores/app";

const appStore = useAppStore();

const actionText = {
  close: {
    save: "保存并关闭",
    discard: "放弃修改",
    busy: "正在关闭…",
  },
  switch: {
    save: "保存并切换",
    discard: "放弃修改并切换",
    busy: "正在切换…",
  },
  continue: {
    save: "保存并继续",
    discard: "放弃修改并继续",
    busy: "正在继续…",
  },
};
</script>

<template>
  <Teleport to="body">
    <div
      v-if="draftGuardState.open"
      class="modal-layer modal-layer-front"
      role="dialog"
      aria-modal="true"
      aria-label="未保存修改"
    >
      <section class="switch-confirm-card">
        <div class="flex items-start gap-3">
          <div class="dialog-warning-icon"><AlertTriangle :size="20" /></div>
          <div class="min-w-0 flex-1">
            <h2 class="text-xl font-bold">
              {{ draftGuardState.confirmingDiscard ? "确认放弃修改？" : "有未保存修改" }}
            </h2>
            <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
              <template v-if="draftGuardState.confirmingDiscard">
                放弃后将无法恢复本窗口中的 {{ appStore.dirtyCount }} 项草稿。
              </template>
              <template v-else>
                前往“{{ draftGuardState.destination }}”前，请选择如何处理
                {{ appStore.dirtyCount }} 项草稿。
              </template>
            </p>
          </div>
          <button class="icon-button" aria-label="取消切换" @click="cancelDraftTransition">
            <X :size="18" />
          </button>
        </div>

        <div v-if="!draftGuardState.confirmingDiscard" class="mt-5 grid gap-2">
          <button class="primary-button min-h-12" @click="saveAndContinue">
            <Save :size="17" />{{ actionText[draftGuardState.mode].save }}
          </button>
          <button class="soft-button min-h-12 justify-center text-red-500" @click="askDiscardConfirmation">
            <Trash2 :size="17" />{{ actionText[draftGuardState.mode].discard }}
          </button>
          <button class="soft-button min-h-12 justify-center" @click="cancelDraftTransition">取消</button>
        </div>
        <div v-else class="mt-5 flex gap-2">
          <button class="soft-button min-h-12 flex-1 justify-center" @click="draftGuardState.confirmingDiscard = false">
            返回
          </button>
          <button
            class="danger-solid-button min-h-12 flex-1"
            :disabled="draftGuardState.busy"
            @click="discardAndContinue"
          >
            {{ draftGuardState.busy ? actionText[draftGuardState.mode].busy : "确认放弃" }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>
