<script setup lang="ts">
import {
  Clock3,
  Download,
  FileSliders,
  FolderKanban,
  Gauge,
  Moon,
  MoreHorizontal,
  Network,
  Settings,
  Sun,
  Upload,
  WifiOff,
  X,
} from "lucide-vue-next";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";

import { useAppStore } from "@/stores/app";
import FileSelector from "@/components/FileSelector.vue";
import { promptDialog } from "@/composables/appDialog";
import { requestDraftTransition } from "@/composables/draftGuard";

const route = useRoute();
const appStore = useAppStore();
const title = computed(() => String(route.meta.title ?? "FixCloud"));
const uploadInput = ref<HTMLInputElement | null>(null);
const busy = ref(false);
const uploadModalOpen = ref(false);
const uploadMode = ref<"temporary" | "config">("temporary");
const uploadSourceId = ref("default-smb");
const formalSources = computed(() => appStore.sources.filter((source) => source.type !== "upload"));

const navItems = [
  { to: "/sources", label: "来源", icon: FolderKanban },
  { to: "/editor", label: "编辑", icon: FileSliders },
  { to: "/usage", label: "流量", icon: Gauge },
  { to: "/subscription-nodes", label: "节点", icon: Network },
  { to: "/history", label: "历史", icon: Clock3 },
  { to: "/settings", label: "设置", icon: Settings },
];
const mobileNavItems = [
  { to: "/editor", label: "编辑", icon: FileSliders },
  { to: "/sources", label: "来源", icon: FolderKanban },
  { to: "/usage", label: "流量", icon: Gauge },
  { to: "/more", label: "更多", icon: MoreHorizontal },
];

function isMobileNavActive(to: string) {
  if (to === "/more") return ["/more", "/subscription-nodes", "/history", "/settings"].some((path) => route.path.startsWith(path));
  return route.path.startsWith(to);
}

async function uploadSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || busy.value) return;
  busy.value = true;
  try {
    const uploaded = await appStore.uploadYaml(
      file,
      uploadMode.value,
      uploadMode.value === "config" ? uploadSourceId.value : undefined,
    );
    const opened = await requestDraftTransition(
      () => appStore.selectFile(uploaded, true),
      uploaded.name,
      "switch",
    );
    appStore.notify(opened
      ? `已添加并打开 ${uploaded.name}`
      : `已添加 ${uploaded.name}，但未打开；当前草稿保持不变`);
  } catch (reason) {
    appStore.error = reason instanceof Error ? reason.message : "上传失败";
    appStore.notify(appStore.error);
  } finally {
    busy.value = false;
  }
}

function openUploadChooser() {
  uploadMode.value = "temporary";
  const current = appStore.sources.find((source) => source.id === appStore.file.sourceId);
  uploadSourceId.value = current && current.type !== "upload" ? current.id : "default-smb";
  uploadModalOpen.value = true;
}

function continueUpload() {
  uploadModalOpen.value = false;
  uploadInput.value?.click();
}

async function exportCurrent() {
  const currentName = appStore.file.path.split("/").pop() || "config.yaml";
  const filename = await promptDialog({
    title: "导出当前 YAML",
    inputLabel: "导出文件名",
    initialValue: currentName,
    placeholder: "config.yaml",
    confirmText: "导出",
  });
  if (!filename) return;
  busy.value = true;
  try {
    await appStore.exportYaml(filename);
  } catch (reason) {
    appStore.error = reason instanceof Error ? reason.message : "导出失败";
    appStore.notify(appStore.error);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="min-h-dvh bg-[var(--app-bg)] text-[var(--text-primary)]">
    <div
      v-if="!appStore.online"
      class="fixed inset-x-0 top-0 z-50 flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-sm font-semibold text-black"
    >
      <WifiOff :size="16" />
      网络已断开，草稿保留在本机，保存已禁用
    </div>

    <aside class="desktop-sidebar">
      <div class="px-5 pb-6 pt-7">
        <div class="mb-1 text-xs font-semibold uppercase tracking-[0.22em] text-[var(--text-muted)]">
          NAS 配置中心
        </div>
        <div class="text-xl font-bold">FixCloud</div>
      </div>
      <nav class="space-y-1 px-3">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="desktop-nav-item"
          active-class="desktop-nav-item-active"
        >
          <component :is="item.icon" :size="19" />
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="mt-auto p-4">
        <div class="rounded-2xl bg-[var(--card)] p-4 shadow-sm">
          <div class="flex items-center gap-2 text-sm font-semibold">
            <span class="status-dot" :class="appStore.backendReachable ? 'status-dot-ok' : 'status-dot-warn'" />
            {{ appStore.backendReachable ? "后端已连接" : "仅读取界面预览" }}
          </div>
          <p class="mt-2 text-xs leading-5 text-[var(--text-muted)]">内网访问</p>
        </div>
      </div>
    </aside>

    <main class="app-main">
      <header class="app-header">
        <div class="mobile-header-brand">
          <span>NAS CONFIG CENTER</span>
          <strong>FixCloud</strong>
          <small><i :class="appStore.backendReachable ? 'connected' : 'disconnected'" />{{ appStore.backendReachable ? "后端已连接" : "后端未连接" }} · 内网访问</small>
        </div>
        <div class="header-context min-w-0">
          <FileSelector />
          <h1 class="mt-0.5 text-xl font-bold">{{ title }}</h1>
        </div>
        <div class="header-actions flex gap-2">
          <input
            ref="uploadInput"
            class="sr-only"
            type="file"
            accept=".yaml,.yml,application/yaml,text/yaml"
            @change="uploadSelected"
          />
          <button class="header-action-button" aria-label="上传 YAML" :disabled="busy" @click="openUploadChooser">
            <Upload :size="18" />
            <span>上传</span>
          </button>
          <button class="header-action-button" aria-label="导出 YAML" :disabled="busy || !appStore.file.hash" @click="exportCurrent">
            <Download :size="18" />
            <span>导出</span>
          </button>
          <button class="icon-button" aria-label="切换深色模式" @click="appStore.toggleTheme">
            <Sun v-if="appStore.dark" :size="19" />
            <Moon v-else :size="19" />
          </button>
        </div>
      </header>

      <div class="app-content">
        <div v-if="!appStore.backendReachable && !appStore.file.hash" class="empty-card page-width">
          <WifiOff :size="26" class="text-amber-500" />
          <h2 class="mt-4 text-xl font-bold">暂时无法连接后端</h2>
          <p class="mt-2 text-sm text-[var(--text-muted)]">{{ appStore.error || "请检查容器和网络状态" }}</p>
          <button class="primary-button mt-5 min-h-11" :disabled="appStore.loading" @click="appStore.bootstrap">
            {{ appStore.loading ? "正在重试…" : "重新连接" }}
          </button>
        </div>
        <RouterView v-else />
      </div>
    </main>

    <nav class="mobile-tabbar" aria-label="主导航">
      <RouterLink
        v-for="item in mobileNavItems"
        :key="item.to"
        :to="item.to"
        class="mobile-tab"
        :class="{ 'mobile-tab-active': isMobileNavActive(item.to) }"
      >
        <component :is="item.icon" :size="21" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
    <Transition name="toast">
      <div v-if="appStore.notice" class="app-toast" role="status">{{ appStore.notice }}</div>
    </Transition>
    <Teleport to="body">
      <div v-if="uploadModalOpen" class="modal-layer" role="dialog" aria-modal="true" aria-label="选择上传方式">
        <section class="app-dialog-card upload-mode-card">
          <header class="picker-header">
            <div><p class="eyebrow">上传 YAML</p><h2 class="text-xl font-bold">选择上传方式</h2></div>
            <button class="icon-button" aria-label="关闭" @click="uploadModalOpen = false"><X :size="19" /></button>
          </header>
          <div class="upload-mode-options">
            <label :class="{ active: uploadMode === 'config' }">
              <input v-model="uploadMode" type="radio" value="config" />
              <span><strong>上传到当前配置目录</strong><small>文件会写入所选来源已配置的可编辑目录，名称冲突时自动添加安全后缀。</small></span>
            </label>
            <label :class="{ active: uploadMode === 'temporary' }">
              <input v-model="uploadMode" type="radio" value="temporary" />
              <span><strong>临时编辑并导出</strong><small>仅当前浏览器会话可见，保存在应用临时目录，24 小时后自动过期。</small></span>
            </label>
          </div>
          <label v-if="uploadMode === 'config'" class="form-field">
            <span>配置来源与可编辑目录</span>
            <select v-model="uploadSourceId">
              <option v-for="source in formalSources" :key="source.id" :value="source.id">
                {{ source.name }} · {{ source.type === "webdav" ? "WebDAV" : "SMB" }} · {{ source.config.configDirectory || "/" }}
              </option>
            </select>
            <small>继续后将直接修改该来源的配置目录。</small>
          </label>
          <div class="dialog-actions">
            <button class="soft-button" @click="uploadModalOpen = false">取消</button>
            <button class="primary-button" :disabled="busy || (uploadMode === 'config' && !uploadSourceId)" @click="continueUpload">选择文件</button>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>
