<script setup lang="ts">
import {
  Check,
  Cloud,
  FolderCog,
  FolderOpen,
  HardDrive,
  LoaderCircle,
  Upload,
  Pencil,
  Plus,
  RefreshCw,
  Server,
  Trash2,
  XCircle,
} from "lucide-vue-next";
import { computed, ref } from "vue";

import GroupCard from "@/components/GroupCard.vue";
import SourceModal from "@/components/SourceModal.vue";
import { confirmDialog } from "@/composables/appDialog";
import { requestDraftTransition } from "@/composables/draftGuard";
import { type SourceStatus, type YamlFileItem, useAppStore } from "@/stores/app";
import {
  formalSources,
  requiresDraftGuardForTemporaryDelete,
  sessionUploadFiles,
} from "@/utils/sourcePresentation";

const appStore = useAppStore();
const testing = ref<string | null>(null);
const feedback = ref<Record<string, SourceStatus>>({});
const editor = ref<SourceStatus | "new" | null>(null);
const error = ref("");
const visibleSources = computed(() => formalSources(appStore.sources));
const temporaryFiles = computed(() => sessionUploadFiles(appStore.files));

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatModifiedAt(value: string) {
  return value ? new Date(value).toLocaleString("zh-CN") : "时间未知";
}

async function removeTemporaryFile(file: YamlFileItem) {
  if (!(await confirmDialog({
    title: `删除临时文件“${file.name}”？`,
    message: "只会删除当前浏览器会话中的临时 YAML，不会影响正式配置目录或远程文件。",
    confirmText: "删除临时文件",
    danger: true,
  }))) return;
  const isCurrent = appStore.file.sourceId === file.sourceId && appStore.file.path === file.path;
  const fallback = appStore.files.find((item) =>
    item.sourceType !== "upload" &&
    !(item.sourceId === file.sourceId && item.path === file.path),
  );
  if (isCurrent && !fallback) {
    error.value = "没有可切换的正式 YAML，无法删除当前临时文件；文件未删除，当前编辑状态保持不变。";
    return;
  }

  const action = async () => {
    try {
      await appStore.deleteYaml(file);
      await appStore.refreshSources();
      if (isCurrent && fallback) await appStore.selectFile(fallback);
      appStore.notify(`已删除 ${file.name}`);
    } catch (reason) {
      const detail = reason instanceof Error ? reason.message : "未知错误";
      error.value = `删除临时文件“${file.name}”失败：${detail}。未执行静默草稿清除。`;
      appStore.notify(error.value);
      throw new Error(error.value);
    }
  };

  if (requiresDraftGuardForTemporaryDelete(appStore.file, file, appStore.dirtyCount)) {
    await requestDraftTransition(action, `删除临时文件“${file.name}”`);
    return;
  }

  try {
    await action();
  } catch {
    // action 已显示明确错误；直接路径在此终止，避免未处理的 Promise 拒绝。
  }
}

function formatTestTime(value?: string) {
  return value ? new Date(value).toLocaleTimeString("zh-CN") : "";
}

function configDirectory(source: SourceStatus) {
  return String(source.config.configDirectory || "config").replace(/^\/+/, "") || "/";
}

async function testConnection(source: SourceStatus) {
  if (testing.value) return;
  testing.value = source.id;
  error.value = "";
  try {
    const payload = await appStore.request(`/api/sources/${source.id}/test`, { method: "POST" });
    feedback.value[source.id] = payload.source;
    const index = appStore.sources.findIndex((item) => item.id === source.id);
    if (index >= 0) appStore.sources[index] = payload.source;
    await appStore.refreshSources();
  } catch (reason) {
    const message = reason instanceof Error ? reason.message : "连接测试失败";
    error.value = message;
    feedback.value[source.id] = {
      ...source,
      connected: false,
      readOnly: true,
      message,
      testedAt: new Date().toISOString(),
    };
    try {
      await appStore.refreshSources();
    } catch {
      // 保留本次明确的卡片错误，不以刷新失败覆盖。
    }
  } finally {
    testing.value = null;
  }
}

async function removeSource(source: SourceStatus) {
  const isCurrent = source.id === appStore.file.sourceId;
  if (
    !(await confirmDialog({
      title: isCurrent ? "删除当前文件来源？" : `删除“${source.name}”？`,
      message: isCurrent
        ? "只会删除面板中的连接记录，不会删除远程 YAML。删除后将切换到其他可用来源。"
        : "只会删除面板中的连接记录，其他来源和远程文件不会受到影响。",
      confirmText: "删除来源",
      danger: true,
    }))
  ) return;
  error.value = "";
  try {
    await appStore.request(`/api/sources/${source.id}`, { method: "DELETE" });
    await appStore.refreshSources();
    if (isCurrent) {
      const next = appStore.files[0];
      if (!next) throw new Error("来源已删除，但当前没有其他可编辑 YAML");
      await appStore.selectFile(next, true);
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "无法删除来源";
  }
}
</script>

<template>
  <div class="page-width">
    <div class="mb-6 flex items-end justify-between">
      <div>
        <p class="eyebrow">文件来源</p>
        <h2 class="page-title">主配置来源</h2>
        <p class="page-subtitle">只显示所选配置目录直属的 YAML；不递归扫描其他目录。</p>
      </div>
      <button class="round-add-button" aria-label="添加文件来源" @click="editor = 'new'">
        <Plus :size="22" />
      </button>
    </div>
    <p v-if="error" class="form-error mb-4">{{ error }}</p>

    <div class="source-grid">
      <article
        v-for="source in visibleSources"
        :key="source.id"
        class="source-card"
        :class="{ 'source-card-primary': source.id === appStore.file.sourceId }"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="source-icon" :class="source.type === 'upload' ? 'bg-emerald-500' : source.type === 'webdav' ? 'bg-violet-500' : 'bg-blue-500'">
            <Cloud v-if="source.type === 'webdav'" :size="24" />
            <Upload v-else-if="source.type === 'upload'" :size="24" />
            <HardDrive v-else :size="24" />
          </div>
          <span class="status-chip" :class="source.connected ? 'status-chip-ok' : 'status-chip-off'">
            <Check v-if="source.connected" :size="13" />
            <XCircle v-else :size="13" />
            {{ source.message }}
          </span>
        </div>
        <h3 class="mt-5 text-lg font-bold">{{ source.name }}</h3>
        <p class="mt-1 truncate text-sm text-[var(--text-muted)]">{{ source.type === "upload" ? "应用数据目录 · 持久化保存" : source.root || "后端文件来源" }}</p>
        <div class="source-scope">
          <FolderCog :size="15" />
          <span>配置目录 <strong>{{ configDirectory(source) }}</strong></span>
          <small>仅直属 YAML</small>
        </div>

        <div
          v-if="feedback[source.id]"
          class="source-test-feedback"
          :class="feedback[source.id].connected ? 'source-test-ok' : 'source-test-error'"
        >
          <strong>{{ feedback[source.id].connected ? "连接成功" : feedback[source.id].message }}</strong>
          <span>
            {{ formatTestTime(feedback[source.id].testedAt) }}
            <template v-if="feedback[source.id].connected"> · {{ feedback[source.id].latencyMs }} ms</template>
          </span>
        </div>

        <div v-if="source.type !== 'upload'" class="source-actions">
          <button class="soft-button" :disabled="Boolean(testing)" @click="testConnection(source)">
            <LoaderCircle v-if="testing === source.id" :size="15" class="animate-spin" />
            <RefreshCw v-else :size="15" />
            {{ testing === source.id ? "测试中…" : "测试连接" }}
          </button>
          <RouterLink
            class="soft-button"
            :to="{ path: '/files', query: { sourceId: source.id } }"
          >
            <FolderOpen :size="15" />浏览配置目录
          </RouterLink>
          <button
            v-if="!source.builtIn"
            class="icon-soft-button"
            aria-label="编辑来源"
            @click="editor = source"
          >
            <Pencil :size="15" />
          </button>
          <button
            v-if="!source.builtIn"
            class="icon-soft-button text-red-500"
            aria-label="删除来源"
            @click="removeSource(source)"
          >
            <Trash2 :size="15" />
          </button>
        </div>
      </article>
    </div>

    <section v-if="temporaryFiles.length" class="session-upload-section" aria-labelledby="session-upload-title">
      <div class="session-upload-heading">
        <div>
          <p class="eyebrow">当前浏览器会话</p>
          <h2 id="session-upload-title" class="text-lg font-bold">已上传文件</h2>
        </div>
        <span class="status-chip status-chip-ok">{{ temporaryFiles.length }} 个临时文件</span>
      </div>
      <div class="ios-card overflow-hidden">
        <div
          v-for="file in temporaryFiles"
          :key="`${file.sourceId}:${file.path}`"
          class="yaml-option session-upload-row"
        >
          <div class="row-icon bg-emerald-500"><Upload :size="18" /></div>
          <div class="min-w-0 flex-1">
            <div class="truncate text-[15px] font-semibold">{{ file.name }}</div>
            <div class="mt-1 truncate text-xs text-[var(--text-muted)]">{{ file.path }}</div>
            <div class="mt-0.5 text-[11px] text-[var(--text-faint)]">
              {{ formatBytes(file.size) }} · {{ formatModifiedAt(file.modifiedAt) }}
            </div>
          </div>
          <span
            class="status-chip"
            :class="file.sourceId === appStore.file.sourceId && file.path === appStore.file.path ? 'status-chip-ok' : 'status-chip-off'"
          >
            {{ file.sourceId === appStore.file.sourceId && file.path === appStore.file.path ? "当前使用" : "可用" }}
          </span>
          <button class="yaml-delete-button" :aria-label="`删除 ${file.name}`" @click="removeTemporaryFile(file)">
            <Trash2 :size="16" />
          </button>
        </div>
      </div>
    </section>

    <GroupCard title="当前文件">
      <div class="settings-row">
        <div class="flex min-w-0 items-center gap-3">
          <div class="row-icon bg-emerald-500"><Server :size="18" /></div>
          <div class="min-w-0">
            <div class="truncate text-[15px] font-semibold">{{ appStore.file.path.split("/").pop() }}</div>
            <div class="mt-0.5 truncate text-xs text-[var(--text-muted)]">
              {{ appStore.file.sourceName }} · {{ appStore.file.path }}
            </div>
          </div>
        </div>
        <span class="status-chip status-chip-ok">已选择</span>
      </div>
    </GroupCard>
  </div>

  <SourceModal
    v-if="editor"
    :source="editor === 'new' ? null : editor"
    @close="editor = null"
    @saved="editor = null"
  />
</template>
