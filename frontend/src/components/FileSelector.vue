<script setup lang="ts">
import { Check, ChevronDown, FileCode2, HardDrive, Search, Trash2, X } from "lucide-vue-next";
import { computed, ref } from "vue";

import { requestDraftTransition } from "@/composables/draftGuard";
import { confirmDialog } from "@/composables/appDialog";
import { type YamlFileItem, useAppStore } from "@/stores/app";
import { groupedFiles } from "@/utils/sourcePresentation";

const appStore = useAppStore();
const open = ref(false);
const search = ref("");
const switching = ref(false);
const deleting = ref("");

const currentName = computed(() => appStore.file.path.split("/").pop() || "选择 YAML");
const files = computed(() => {
  const needle = search.value.trim().toLowerCase();
  return appStore.files.filter((file) =>
    !needle ||
    `${file.name} ${file.sourceName} ${file.sourceType} ${file.path}`
      .toLowerCase()
      .includes(needle),
  );
});
const fileGroups = computed(() => groupedFiles(files.value));

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatTime(value: string) {
  if (!value) return "时间未知";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function sourceLabel(type: string) {
  if (type === "upload") return "已上传";
  if (type === "webdav") return "WebDAV";
  return "SMB";
}

async function remove(file: YamlFileItem) {
  const isCurrent = file.sourceId === appStore.file.sourceId && file.path === appStore.file.path;
  const fallback = appStore.files.find((item) =>
    !(item.sourceId === file.sourceId && item.path === file.path),
  );
  if (isCurrent && !fallback) {
    appStore.notify("没有可用的后备 YAML，无法删除当前文件");
    return;
  }
  const source = appStore.sources.find((item) => item.id === file.sourceId);
  const sourceType = file.sourceType === "upload" ? "本会话临时文件" : file.sourceType === "webdav" ? "WebDAV" : "SMB";
  const directory = file.sourceType === "upload" ? "本会话临时目录" : String(source?.config.configDirectory || "/");
  if (!(await confirmDialog({
    title: "确认删除 YAML",
    message: `文件：${file.name}\n来源：${file.sourceName}（${sourceType}）\n可编辑目录/路径：${directory}${file.path}`,
    confirmText: "继续",
    danger: true,
  }))) return;
  if (!(await confirmDialog({
    title: `最终确认删除 ${file.name}`,
    message: isCurrent && appStore.dirtyCount
      ? `当前有 ${appStore.dirtyCount} 项未保存操作，草稿将被丢弃。`
      : "此操作会直接删除文件，无法撤销。",
    confirmText: "永久删除",
    danger: true,
  }))) return;
  deleting.value = `${file.sourceId}:${file.path}`;
  try {
    await appStore.deleteYaml(file);
    if (isCurrent && fallback) await appStore.selectFile(fallback, true);
    await appStore.refreshSources();
    appStore.notify(`已删除 ${file.name}`);
  } catch (reason) {
    appStore.notify(reason instanceof Error ? reason.message : "删除失败");
  } finally {
    deleting.value = "";
  }
}

async function choose(file: YamlFileItem) {
  if (file.sourceId === appStore.file.sourceId && file.path === appStore.file.path) {
    open.value = false;
    return;
  }
  open.value = false;
  await requestDraftTransition(
    async () => {
      switching.value = true;
      try {
        await appStore.selectFile(file, true);
      } finally {
        switching.value = false;
      }
    },
    file.name,
    "switch",
  );
}
</script>

<template>
  <button class="file-selector-trigger" aria-label="选择 YAML 文件" @click="open = true">
    <span class="truncate">{{ currentName }}</span>
    <ChevronDown :size="14" />
  </button>

  <Teleport to="body">
    <div v-if="open" class="modal-layer" role="dialog" aria-modal="true" aria-label="选择 YAML 文件">
      <section class="file-picker-panel">
      <header class="picker-header">
        <div>
          <p class="eyebrow">配置目录直属文件</p>
          <h2 class="text-xl font-bold">选择 YAML 文件</h2>
        </div>
        <button class="icon-button" aria-label="关闭文件选择器" @click="open = false">
          <X :size="19" />
        </button>
      </header>
      <label class="search-field mx-4 mb-3" aria-label="搜索 YAML 文件">
        <Search :size="17" />
        <input v-model="search" type="search" placeholder="搜索文件名、来源或路径" autofocus />
      </label>
      <div class="file-picker-list">
        <template v-for="group in fileGroups" :key="group.title">
        <div class="file-group-title">{{ group.title }}</div>
        <div v-for="file in group.items" :key="`${file.sourceId}:${file.path}`" class="yaml-option">
          <button class="yaml-option-main" :disabled="switching || Boolean(deleting)" @click="choose(file)">
          <div class="row-icon" :class="file.sourceType === 'upload' ? 'bg-emerald-500' : file.sourceType === 'webdav' ? 'bg-violet-500' : 'bg-blue-500'">
            <FileCode2 :size="18" />
          </div>
          <div class="min-w-0 flex-1 text-left">
            <div class="flex items-center gap-2">
              <span class="truncate text-[15px] font-semibold">{{ file.name }}</span>
              <span class="source-mini-badge" :class="`source-mini-badge-${file.sourceType}`">{{ sourceLabel(file.sourceType) }}</span>
            </div>
            <div class="mt-1 truncate text-xs text-[var(--text-muted)]">{{ file.path }}</div>
            <div class="mt-0.5 text-[11px] text-[var(--text-faint)]">
              {{ file.sourceName }} · {{ formatBytes(file.size) }} · {{ formatTime(file.modifiedAt) }}
            </div>
          </div>
          <Check
            v-if="file.sourceId === appStore.file.sourceId && file.path === appStore.file.path"
            :size="19"
            class="text-emerald-500"
          />
          </button>
          <button class="yaml-delete-button" :disabled="Boolean(deleting)" :aria-label="`删除 ${file.name}`" @click="remove(file)">
            <Trash2 :size="16" />
          </button>
        </div>
        </template>
        <div v-if="files.length === 0" class="empty-picker">
          <HardDrive :size="24" />
          <p>配置目录中没有匹配的主配置 YAML</p>
        </div>
      </div>
      </section>
    </div>

  </Teleport>
</template>
