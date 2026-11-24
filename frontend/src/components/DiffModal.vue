<script setup lang="ts">
import { AlertTriangle, CheckCircle2, X } from "lucide-vue-next";

import { useAppStore } from "@/stores/app";

const appStore = useAppStore();

async function confirm() {
  try {
    await appStore.commitPreview();
  } catch {
    // 真实保存状态由下方状态卡展示，保留 Diff 供用户核对。
  }
}
</script>

<template>
  <div v-if="appStore.preview" class="modal-layer" role="dialog" aria-modal="true" aria-label="保存确认">
    <section class="diff-panel">
      <header class="diff-header">
        <div>
          <p class="eyebrow">保存前确认</p>
          <h2 class="text-2xl font-bold">完整 Diff</h2>
        </div>
        <button class="icon-button" aria-label="关闭" @click="appStore.preview = null">
          <X :size="20" />
        </button>
      </header>

      <div class="diff-content">
        <div
          v-if="appStore.saveFailure"
          class="save-outcome-card"
          :class="`save-outcome-${appStore.saveFailure.status}`"
        >
          <AlertTriangle :size="20" />
          <div>
            <strong>{{ appStore.saveFailure.message }}</strong>
            <p>{{ appStore.saveFailure.nextStep }}</p>
            <p v-if="appStore.saveFailure.backupPath">
              可用恢复副本：{{ appStore.saveFailure.backupPath }}
            </p>
          </div>
        </div>
        <div
          v-if="appStore.preview.validation.errors.length"
          class="validation-box validation-error"
        >
          <AlertTriangle :size="19" />
          <div>
            <strong>引用检查未通过</strong>
            <p v-for="item in appStore.preview.validation.errors" :key="item">{{ item }}</p>
          </div>
        </div>
        <div v-else class="validation-box validation-ok">
          <CheckCircle2 :size="19" />
          <div>
            <strong>YAML 与引用检查通过</strong>
            <p>
              {{ appStore.preview.diff.changedLines }} 行变化；保存时会使用临时恢复副本并回读确认，成功后自动清理。
            </p>
          </div>
        </div>
        <div
          v-if="appStore.preview.validation.warnings.length"
          class="validation-box validation-warn"
        >
          <AlertTriangle :size="19" />
          <div>
            <strong>提示</strong>
            <p v-for="item in appStore.preview.validation.warnings.slice(0, 8)" :key="item">
              {{ item }}
            </p>
          </div>
        </div>
        <pre class="diff-code">{{ appStore.preview.diff.text || "没有内容变化" }}</pre>
      </div>

      <footer class="diff-actions">
        <button class="soft-button min-h-12 flex-1" @click="appStore.preview = null">返回修改</button>
        <button
          class="primary-button min-h-12 flex-1"
          :disabled="appStore.saving || appStore.preview.validation.errors.length > 0"
          @click="confirm"
        >
          {{ appStore.saving ? "正在安全保存…" : "确认并保存" }}
        </button>
      </footer>
    </section>
  </div>
</template>
