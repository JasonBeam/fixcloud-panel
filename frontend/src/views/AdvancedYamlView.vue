<script setup lang="ts">
import { AlertTriangle, Code2, RefreshCw } from "lucide-vue-next";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import EditorTopBar from "@/components/EditorTopBar.vue";
import { requestDraftTransition } from "@/composables/draftGuard";
import { useAppStore } from "@/stores/app";

const router = useRouter();
const appStore = useAppStore();
const content = ref("");
const loading = ref(true);
const applying = ref(false);
const error = ref("");
const validated = ref(false);

function markRawEdited() {
  validated.value = false;
  if (appStore.rawYamlDraft !== null && appStore.rawYamlDraft !== content.value) {
    appStore.rawYamlDraft = null;
    appStore.preview = null;
    appStore.persistDraft();
  }
}

async function loadRaw() {
  loading.value = true;
  error.value = "";
  try {
    const raw = await appStore.fetchRawYaml();
    content.value = raw.content;
    validated.value = false;
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "无法读取完整 YAML";
  } finally {
    loading.value = false;
  }
}

async function applyDraft() {
  if (applying.value || loading.value) return;
  applying.value = true;
  error.value = "";
  try {
    await appStore.applyAdvancedYaml(content.value);
    await appStore.createPreview();
    validated.value = true;
    appStore.notify("YAML 格式检查通过，已生成保存 Diff");
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "YAML 校验失败";
  } finally {
    applying.value = false;
  }
}

async function close() {
  await requestDraftTransition(async () => { await router.push("/editor"); }, "可视化编辑器", "close");
}

onMounted(() => { void loadRaw(); });
</script>

<template>
  <div class="page-width editor-detail-page advanced-yaml-page">
    <EditorTopBar title="YAML 修改" close-label="关闭" show-save @close="close" />

    <section class="advanced-yaml-intro">
      <Code2 :size="19" />
      <div><strong>复杂嵌套或未知字段可在这里修改</strong><p>点击下方按钮会先检查 YAML 格式和引用关系，再生成完整 Diff；不会直接写入正式文件。</p></div>
    </section>
    <p v-if="error" class="form-error">{{ error }}</p>

    <section class="advanced-yaml-card">
      <header>
        <div><strong>当前完整 YAML</strong><span v-if="validated" class="advanced-yaml-valid">已校验并同步草稿</span></div>
        <button class="icon-soft-button" aria-label="重新读取正式 YAML" :disabled="loading || appStore.dirtyCount > 0" @click="loadRaw"><RefreshCw :size="17" /></button>
      </header>
      <textarea v-model="content" :disabled="loading" spellcheck="false" aria-label="完整 YAML 高级编辑器" @input="markRawEdited" />
      <footer>
        <span v-if="loading">正在读取…</span>
        <span v-else>不会自动格式化；通过检查后才可以进入 Diff 确认。</span>
        <button class="primary-button" :disabled="loading || applying || !content.trim()" @click="applyDraft">
          {{ applying ? "正在检查…" : "检查格式并查看 Diff" }}
        </button>
      </footer>
    </section>

    <div class="advanced-yaml-note"><AlertTriangle :size="16" />若语法有误，会显示 YAML 提供的行、列和中文原因；未通过 Diff 确认前不会写入正式文件。</div>
  </div>
</template>

<style scoped>
.advanced-yaml-page { max-width: 1080px; }.advanced-yaml-intro { display: flex; gap: 11px; margin: 18px 0 12px; border: 1px solid rgba(10, 132, 255, .2); border-radius: 15px; padding: 13px 15px; color: #0a84ff; background: rgba(10, 132, 255, .07); }.advanced-yaml-intro strong { color: var(--text-primary); }.advanced-yaml-intro p { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.5; }
.advanced-yaml-card { overflow: hidden; border: 1px solid var(--separator); border-radius: 18px; background: var(--card-strong); box-shadow: var(--shadow); }.advanced-yaml-card header, .advanced-yaml-card footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 14px; border-bottom: 1px solid var(--separator); font-size: 13px; }.advanced-yaml-card header > div { display: flex; align-items: center; gap: 9px; }.advanced-yaml-card footer { border-top: 1px solid var(--separator); border-bottom: 0; color: var(--text-muted); font-size: 12px; }.advanced-yaml-card textarea { display: block; width: 100%; min-height: 510px; resize: vertical; border: 0; padding: 16px; outline: 0; color: var(--text-primary); background: color-mix(in srgb, var(--field-bg) 55%, var(--card-strong)); font: 13px/1.65 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; tab-size: 2; }.advanced-yaml-valid { border-radius: 999px; padding: 3px 7px; color: #15803d; background: rgba(34, 197, 94, .12); font-size: 11px; }.advanced-yaml-note { display: flex; gap: 8px; margin-top: 12px; color: var(--text-muted); font-size: 12px; line-height: 1.5; }
@media (max-width: 640px) { .advanced-yaml-card footer { align-items: stretch; flex-direction: column; }.advanced-yaml-card footer button { width: 100%; }.advanced-yaml-card textarea { min-height: 440px; } }
</style>
