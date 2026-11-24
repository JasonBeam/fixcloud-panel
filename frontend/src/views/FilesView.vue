<script setup lang="ts">
import { ArrowLeft, Check, FileCode2, RefreshCw } from "lucide-vue-next";
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { allowNextRoute, requestDraftTransition } from "@/composables/draftGuard";
import { useAppStore } from "@/stores/app";

type FileEntry = {
  name: string;
  path: string;
  size: number;
  modifiedAt: string;
  etag: string;
  hash: string;
  directory: boolean;
};

const router = useRouter();
const route = useRoute();
const appStore = useAppStore();
const currentPath = ref("/");
const entries = ref<FileEntry[]>([]);
const loading = ref(false);
const error = ref("");
const sourceId = ref(String(route.query.sourceId || appStore.file.sourceId));
const sourceName = ref("");

async function load(path = currentPath.value) {
  loading.value = true;
  error.value = "";
  try {
    const payload = await appStore.request(
      `/api/files?path=${encodeURIComponent(path)}&sourceId=${encodeURIComponent(sourceId.value)}`,
    );
    currentPath.value = payload.path;
    sourceName.value = payload.source.name;
    entries.value = payload.entries;
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "无法读取目录";
  } finally {
    loading.value = false;
  }
}

async function open(entry: FileEntry) {
  await requestDraftTransition(
    async () => {
      try {
        await appStore.selectFile(
          {
            sourceId: sourceId.value,
            sourceType: "",
            sourceName: sourceName.value,
            name: entry.name,
            path: entry.path,
            size: entry.size,
            modifiedAt: entry.modifiedAt,
            etag: entry.etag,
            hash: entry.hash,
          },
          true,
        );
        allowNextRoute();
        await router.push("/editor");
      } catch (reason) {
        error.value = reason instanceof Error ? reason.message : "无法打开文件";
        throw reason;
      }
    },
    entry.name,
    "switch",
  );
}

onMounted(() => load("/"));
</script>

<template>
  <div class="page-width">
    <div class="editor-page-header">
      <button class="icon-button" aria-label="返回文件来源" @click="router.push('/sources')">
        <ArrowLeft :size="20" />
      </button>
      <div class="min-w-0 flex-1">
        <p class="eyebrow">{{ sourceName || "NAS" }} 文件浏览器</p>
        <h2 class="truncate text-2xl font-bold">{{ currentPath }}</h2>
      </div>
      <button class="icon-button" aria-label="刷新目录" :disabled="loading" @click="load()">
        <RefreshCw :size="18" :class="{ 'animate-spin': loading }" />
      </button>
    </div>

    <p class="page-subtitle mb-5">
      这里只显示所选配置目录直属的 YAML；不会递归进入其他目录。
    </p>
    <p v-if="error" class="form-error mb-4">{{ error }}</p>

    <div class="ios-card overflow-hidden">
      <button v-for="entry in entries" :key="entry.path" class="file-row" @click="open(entry)">
        <div class="row-icon bg-emerald-500">
          <FileCode2 :size="18" />
        </div>
        <div class="min-w-0 flex-1 text-left">
          <div class="truncate text-[15px] font-semibold">{{ entry.name }}</div>
          <div class="mt-0.5 truncate text-xs text-[var(--text-muted)]">
            {{ entry.size.toLocaleString() }} bytes
          </div>
        </div>
        <Check v-if="entry.path === appStore.file.path" :size="18" class="text-emerald-500" />
      </button>

      <p v-if="!loading && entries.length === 0" class="p-8 text-center text-sm text-[var(--text-muted)]">
        此目录没有 YAML 文件
      </p>
    </div>
  </div>
</template>
