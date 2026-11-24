<script setup lang="ts">
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Cloud,
  Folder,
  FolderOpen,
  HardDrive,
  LoaderCircle,
  X,
  XCircle,
} from "lucide-vue-next";
import { computed, reactive, ref, watch } from "vue";

import { confirmDialog } from "@/composables/appDialog";
import { type SourceStatus, useAppStore } from "@/stores/app";

const props = defineProps<{ source?: SourceStatus | null }>();
const emit = defineEmits<{ close: []; saved: [] }>();
const appStore = useAppStore();

const initialType = props.source?.type === "webdav" ? "webdav" : "smb";
const form = reactive({
  type: initialType,
  name: props.source?.name ?? "",
  server: String(props.source?.config.server ?? ""),
  share: String(props.source?.config.share ?? ""),
  username: "",
  password: "",
  rootDirectory: String(
    props.source?.config.rootDirectory ?? props.source?.config.subdirectory ?? "",
  ),
  configDirectory: String(props.source?.config.configDirectory ?? "config"),
  url: String(props.source?.config.url ?? ""),
});
const testing = ref(false);
const saving = ref(false);
const probeToken = ref("");
const result = ref<{ connected: boolean; message: string; latencyMs?: number; testedAt?: string } | null>(null);
const error = ref("");
const directoryOpen = ref(false);
const directoryLoading = ref(false);
const directoryPath = ref("/");
const directories = ref<Array<{ name: string; path: string }>>([]);
const directoryError = ref("");
let initializing = true;

const title = computed(() => props.source ? "编辑文件来源" : "添加文件来源");
const canSave = computed(() => Boolean(probeToken.value && result.value?.connected && !saving.value));
const originalConfigDirectory = String(props.source?.config.configDirectory ?? "config");
const directoryChanged = computed(
  () => Boolean(props.source && form.configDirectory.trim() !== originalConfigDirectory.trim()),
);
const directoryParent = computed(() => {
  const parts = directoryPath.value.split("/").filter(Boolean);
  parts.pop();
  return `/${parts.join("/")}` || "/";
});

function payload() {
  const config = form.type === "smb"
    ? {
        server: form.server.trim(),
        share: form.share.trim(),
        username: form.username,
        password: form.password,
        rootDirectory: form.rootDirectory.trim(),
        configDirectory: form.configDirectory.trim() || "config",
      }
    : {
        url: form.url.trim(),
        username: form.username,
        password: form.password,
        rootDirectory: form.rootDirectory.trim() || "/",
        configDirectory: form.configDirectory.trim() || "config",
      };
  return {
    sourceId: props.source?.id,
    type: form.type,
    name: form.name.trim(),
    config,
  };
}

function validateForm() {
  if (!form.name.trim()) return "来源名称不能为空";
  if (form.type === "smb") {
    if (!form.server.trim()) return "SMB 服务器地址不能为空";
    if (!form.share.trim()) return "SMB 共享目录不能为空";
  } else if (!/^https?:\/\//i.test(form.url.trim())) {
    return "WebDAV URL 必须以 http:// 或 https:// 开头";
  }
  if (!form.configDirectory.trim()) return "配置目录不能为空";
  return "";
}

watch(
  form,
  () => {
    if (initializing) return;
    probeToken.value = "";
    result.value = null;
    error.value = "";
  },
  { deep: true },
);
queueMicrotask(() => { initializing = false; });

async function testConnection() {
  const validationError = validateForm();
  if (validationError) {
    error.value = validationError;
    return;
  }
  testing.value = true;
  error.value = "";
  result.value = null;
  try {
    const response = await appStore.request("/api/sources/probe", {
      method: "POST",
      body: JSON.stringify(payload()),
    });
    result.value = response.source;
    probeToken.value = response.probeToken ?? "";
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "连接测试失败";
  } finally {
    testing.value = false;
  }
}

async function loadDirectories(path = directoryPath.value) {
  directoryLoading.value = true;
  directoryError.value = "";
  try {
    const response = await appStore.request(
      `/api/sources/directories?path=${encodeURIComponent(path)}`,
      {
        method: "POST",
        body: JSON.stringify(payload()),
      },
    );
    if (!response.status?.connected) {
      throw new Error(response.status?.message || "无法读取来源根目录");
    }
    directoryPath.value = response.path;
    directories.value = response.directories;
  } catch (reason) {
    directoryError.value = reason instanceof Error ? reason.message : "无法读取目录";
  } finally {
    directoryLoading.value = false;
  }
}

async function openDirectoryBrowser() {
  const validationError = validateForm();
  if (validationError) {
    error.value = validationError;
    return;
  }
  directoryOpen.value = true;
  directoryPath.value = "/";
  directories.value = [];
  await loadDirectories("/");
}

function selectDirectory() {
  form.configDirectory = directoryPath.value === "/"
    ? "/"
    : directoryPath.value.replace(/^\/+/, "");
  directoryOpen.value = false;
}

async function save() {
  if (!canSave.value) return;
  if (
    props.source?.id === appStore.file.sourceId &&
    directoryChanged.value &&
    !(await confirmDialog({
      title: "修改当前来源的配置目录？",
      message: "保存后会重新加载该来源的 YAML 列表；不会移动或删除任何远程文件。",
      confirmText: "确认修改",
    }))
  ) {
    return;
  }
  saving.value = true;
  error.value = "";
  try {
    const endpoint = props.source ? `/api/sources/${props.source.id}` : "/api/sources";
    await appStore.request(endpoint, {
      method: props.source ? "PUT" : "POST",
      body: JSON.stringify({ ...payload(), probeToken: probeToken.value }),
    });
    await appStore.refreshSources();
    if (props.source?.id === appStore.file.sourceId) {
      const next =
        appStore.files.find(
          (item) => item.sourceId === props.source?.id && item.path === appStore.file.path,
        ) ?? appStore.files.find((item) => item.sourceId === props.source?.id);
      if (next) await appStore.selectFile(next, true);
      else {
        error.value = "来源已保存，但新的配置目录中没有可编辑 YAML。请添加文件或切换来源。";
        return;
      }
    }
    emit("saved");
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "保存来源失败";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-layer modal-layer-front" role="dialog" aria-modal="true" :aria-label="title">
      <section class="source-modal-panel">
      <header class="picker-header">
        <div>
          <p class="eyebrow">文件来源</p>
          <h2 class="text-xl font-bold">{{ title }}</h2>
        </div>
        <button class="icon-button" aria-label="关闭来源设置" @click="emit('close')"><X :size="19" /></button>
      </header>

      <div class="source-form-scroll">
        <div v-if="!source" class="source-type-picker">
          <button :class="{ active: form.type === 'smb' }" @click="form.type = 'smb'">
            <HardDrive :size="21" />
            <span><strong>SMB</strong><small>服务器共享目录</small></span>
          </button>
          <button :class="{ active: form.type === 'webdav' }" @click="form.type = 'webdav'">
            <Cloud :size="21" />
            <span><strong>WebDAV</strong><small>HTTP 文件服务</small></span>
          </button>
        </div>

        <label class="form-card source-name-field">
          <span>来源名称</span>
          <input v-model="form.name" placeholder="例如：家庭 NAS" />
        </label>

        <template v-if="form.type === 'smb'">
          <label class="form-card"><span>服务器地址</span><input v-model="form.server" placeholder="192.168.11.193" /></label>
          <label class="form-card"><span>共享目录</span><input v-model="form.share" placeholder="BeamJason" /></label>
          <label class="form-card"><span>用户名</span><input v-model="form.username" autocomplete="off" :placeholder="source ? '留空保持原用户名' : 'SMB 用户名'" /></label>
          <label class="form-card"><span>密码</span><input v-model="form.password" type="password" autocomplete="new-password" :placeholder="source ? '留空保持原密码' : 'SMB 密码'" /></label>
          <label class="form-card source-root-field"><span>根目录</span><input v-model="form.rootDirectory" placeholder="files（可选）" /></label>
        </template>
        <template v-else>
          <label class="form-card source-url-field"><span>WebDAV URL</span><input v-model="form.url" type="url" placeholder="http://NAS_IP:端口/路径/" /></label>
          <label class="form-card"><span>用户名</span><input v-model="form.username" autocomplete="off" :placeholder="source ? '留空保持原用户名' : 'WebDAV 用户名'" /></label>
          <label class="form-card"><span>密码</span><input v-model="form.password" type="password" autocomplete="new-password" :placeholder="source ? '留空保持原密码' : 'WebDAV 密码'" /></label>
          <label class="form-card source-root-field"><span>根目录</span><input v-model="form.rootDirectory" placeholder="/（可选）" /></label>
        </template>

        <div class="editable-directory-card">
          <div>
            <strong>配置目录 / 可编辑目录</strong>
            <p>只列出该目录直属的 YAML，不扫描子目录。</p>
          </div>
          <div class="directory-input-row">
            <input v-model="form.configDirectory" placeholder="config" />
            <button class="soft-button" type="button" @click="openDirectoryBrowser">
              <FolderOpen :size="16" />
              浏览选择
            </button>
          </div>
        </div>

        <div v-if="directoryChanged" class="directory-change-warning">
          <AlertTriangle :size="18" />
          <p>保存后会刷新当前 YAML 下拉列表，但不会移动、修改或删除任何远程文件。</p>
        </div>

        <div v-if="result" class="connection-result" :class="result.connected ? 'connection-result-ok' : 'connection-result-error'">
          <CheckCircle2 v-if="result.connected" :size="19" />
          <XCircle v-else :size="19" />
          <div>
            <strong>{{ result.connected ? "连接成功" : result.message }}</strong>
            <p>
              {{ result.connected ? `${result.latencyMs ?? "-"} ms` : "请检查地址和凭据" }}
              <template v-if="result.testedAt"> · {{ new Date(result.testedAt).toLocaleTimeString("zh-CN") }}</template>
            </p>
          </div>
        </div>
        <p v-if="error" class="form-error">{{ error }}</p>
      </div>

      <footer class="source-modal-actions">
        <button class="soft-button min-h-12 flex-1 justify-center" :disabled="testing || saving" @click="testConnection">
          <LoaderCircle v-if="testing" :size="17" class="animate-spin" />
          {{ testing ? "正在测试…" : "测试连接" }}
        </button>
        <button class="primary-button min-h-12 flex-1" :disabled="!canSave" @click="save">
          {{ saving ? "正在保存…" : "保存来源" }}
        </button>
      </footer>
      </section>

      <section v-if="directoryOpen" class="directory-browser-panel" aria-label="选择配置目录">
        <header class="picker-header">
          <div>
            <p class="eyebrow">来源根目录</p>
            <h2 class="text-xl font-bold">选择配置目录</h2>
          </div>
          <button class="icon-button" aria-label="关闭目录选择器" @click="directoryOpen = false">
            <X :size="19" />
          </button>
        </header>
        <div class="directory-browser-path">
          <FolderOpen :size="17" />
          <span>{{ directoryPath }}</span>
          <LoaderCircle v-if="directoryLoading" :size="16" class="animate-spin" />
        </div>
        <p v-if="directoryError" class="form-error mx-4">{{ directoryError }}</p>
        <div class="directory-browser-list">
          <button
            v-if="directoryPath !== '/'"
            class="directory-row"
            :disabled="directoryLoading"
            @click="loadDirectories(directoryParent)"
          >
            <ArrowLeft :size="17" />
            <span>上一级</span>
          </button>
          <button
            v-for="directory in directories"
            :key="directory.path"
            class="directory-row"
            :disabled="directoryLoading"
            @click="loadDirectories(directory.path)"
          >
            <Folder :size="18" class="text-blue-500" />
            <span>{{ directory.name }}</span>
            <ChevronRight :size="17" />
          </button>
          <p v-if="!directoryLoading && !directoryError && directories.length === 0" class="empty-directory">
            此目录没有子目录
          </p>
        </div>
        <footer class="source-modal-actions">
          <button class="soft-button min-h-12 flex-1 justify-center" @click="directoryOpen = false">
            取消
          </button>
          <button class="primary-button min-h-12 flex-1" :disabled="directoryLoading" @click="selectDirectory">
            选择当前目录
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>
