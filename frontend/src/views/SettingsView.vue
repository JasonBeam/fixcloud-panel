<script setup lang="ts">
import {
  Cloud,
  ExternalLink,
  FileCheck2,
  Globe2,
  HardDrive,
  LockKeyhole,
  Network,
  RefreshCw,
  Shield,
} from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";

import GroupCard from "@/components/GroupCard.vue";
import { useAppStore } from "@/stores/app";
import { confirmDialog } from "@/composables/appDialog";

type OperationLog = {
  id: number; createdAt: string; fileName: string; sourceName: string;
  action: string; status: string; message: string;
};
type PublicationStatus = {
  matching: boolean;
  currentHash: string;
  publishedHash: string;
  publishedUrl: string;
  publishedSize: number;
  etag?: string | null;
  lastModified?: string | null;
  latencyMs: number;
  directoryRefreshed: boolean;
  baseUrl: string;
  fileName: string;
};
const appStore = useAppStore();
const logs = ref<OperationLog[]>([]);
const loading = ref(false);
const logError = ref("");
const currentOnly = ref(false);
const maxEntries = ref(500);
const currentCount = ref(0);
const customLimit = ref("");
const settingsError = ref("");
const settingsBusy = ref(false);
const publicationBaseUrl = ref("https://file.example.com");
const publication = ref<PublicationStatus | null>(null);
const publicationBusy = ref(false);
const publicationError = ref("");
const currentPublishedUrl = computed(() => {
  const name = appStore.file.path.split("/").filter(Boolean).at(-1) || "FixCloud.yaml";
  return `${publicationBaseUrl.value.replace(/\/+$/, "")}/${encodeURIComponent(name)}`;
});

async function loadLogs() {
  loading.value = true;
  logError.value = "";
  try {
    const query = currentOnly.value
      ? `?sourceId=${encodeURIComponent(appStore.file.sourceId)}&path=${encodeURIComponent(appStore.file.path)}`
      : "";
    const payload = await appStore.request(`/api/logs${query}`);
    logs.value = payload.logs;
    maxEntries.value = payload.maxEntries;
    currentCount.value = payload.currentCount;
  } catch (reason) {
    logError.value = reason instanceof Error ? reason.message : "日志加载失败";
  } finally {
    loading.value = false;
  }
}
async function saveLogLimit(value: number | string) {
  if (settingsBusy.value) return;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 50000) {
    settingsError.value = "最大日志条数必须是 1 到 50000 的正整数";
    return;
  }
  settingsError.value = "";
  settingsBusy.value = true;
  try {
    const payload = await appStore.request("/api/logs/settings", {
      method: "PUT", body: JSON.stringify({ maxEntries: parsed }),
    });
    maxEntries.value = payload.maxEntries;
    currentCount.value = payload.currentCount;
    await loadLogs();
  } catch (reason) {
    settingsError.value = reason instanceof Error
      ? `更新日志保留设置失败：${reason.message}`
      : "更新日志保留设置失败，请稍后重试";
  } finally {
    settingsBusy.value = false;
  }
}
async function clearLogs() {
  if (settingsBusy.value) return;
  if (!(await confirmDialog({
    title: "清空操作日志",
    message: "这只会删除操作日志，不会删除 YAML、备份、来源、临时文件、图标缓存或设置。",
    confirmText: "继续", danger: true,
  }))) return;
  if (!(await confirmDialog({
    title: "最终确认清空",
    message: `当前共有 ${currentCount.value} 条日志。清空后无法恢复。`,
    confirmText: "立即清空", danger: true,
  }))) return;
  settingsBusy.value = true;
  logError.value = "";
  try {
    const payload = await appStore.request("/api/logs", { method: "DELETE" });
    currentCount.value = payload.currentCount;
    logs.value = [];
  } catch (reason) {
    logError.value = reason instanceof Error
      ? `清空操作日志失败：${reason.message}`
      : "清空操作日志失败，请稍后重试";
  } finally {
    settingsBusy.value = false;
  }
}
async function checkPublication() {
  if (publicationBusy.value) return;
  publicationBusy.value = true;
  publication.value = null;
  publicationError.value = "";
  try {
    const query = new URLSearchParams({
      sourceId: appStore.file.sourceId,
      path: appStore.file.path,
    });
    const payload = await appStore.request(`/api/publication/status?${query}`);
    publication.value = payload;
    publicationBaseUrl.value = payload.baseUrl;
    await loadLogs();
  } catch (reason) {
    publicationError.value = reason instanceof Error ? reason.message : "线上版本核对失败";
    await loadLogs();
  } finally {
    publicationBusy.value = false;
  }
}
function actionLabel(action: string) {
  return ({
    upload: "上传", export: "导出", save: "保存", restore: "恢复",
    "delete-history": "删除历史", "connection-test": "连接测试", "icon-cache": "图标缓存",
    "publication-check": "线上版本核对",
  } as Record<string, string>)[action] ?? action;
}
onMounted(loadLogs);
</script>

<template>
  <div class="page-width">
    <div class="mb-6">
      <p class="eyebrow">面板设置</p>
      <h2 class="page-title">系统设置</h2>
      <p class="page-subtitle">局域网 HTTP 访问，SMB 默认，WebDAV 辅助。</p>
    </div>

    <GroupCard title="连接">
      <div class="settings-row">
        <div class="flex items-center gap-3">
          <div class="row-icon bg-blue-500"><HardDrive :size="18" /></div>
          <div>
            <div class="text-[15px] font-semibold">默认文件来源</div>
            <div class="mt-0.5 text-xs text-[var(--text-muted)]">NAS 主机挂载目录</div>
          </div>
        </div>
        <span class="status-chip status-chip-ok">SMB</span>
      </div>
      <div class="settings-row">
        <div class="flex items-center gap-3">
          <div class="row-icon bg-violet-500"><Cloud :size="18" /></div>
          <div>
            <div class="text-[15px] font-semibold">辅助来源</div>
            <div class="mt-0.5 text-xs text-[var(--text-muted)]">按需配置</div>
          </div>
        </div>
        <span class="text-sm text-[var(--text-muted)]">WebDAV</span>
      </div>
      <div class="settings-row">
        <div class="flex items-center gap-3">
          <div class="row-icon bg-emerald-500"><Network :size="18" /></div>
          <div>
            <div class="text-[15px] font-semibold">访问协议</div>
            <div class="mt-0.5 text-xs text-[var(--text-muted)]">仅限局域网</div>
          </div>
        </div>
        <span class="status-chip status-chip-warn">HTTP</span>
      </div>
    </GroupCard>

    <GroupCard title="文件发布">
      <div class="settings-row publication-source-row">
        <div class="flex min-w-0 items-center gap-3">
          <div class="row-icon bg-cyan-500"><Globe2 :size="18" /></div>
          <div class="min-w-0">
            <div class="text-[15px] font-semibold">公开文件服务</div>
            <div class="mt-0.5 truncate text-xs text-[var(--text-muted)]">公开文件域 · Lucky</div>
          </div>
        </div>
        <a
          class="soft-button"
          :href="publicationBaseUrl"
          target="_blank"
          rel="noopener noreferrer"
        >
          打开
          <ExternalLink :size="15" />
        </a>
      </div>
      <div class="settings-row publication-source-row">
        <div class="min-w-0">
          <div class="text-[15px] font-semibold">当前线上 YAML</div>
          <div class="mt-0.5 truncate text-xs text-[var(--text-muted)]">{{ currentPublishedUrl }}</div>
        </div>
        <a
          class="icon-soft-button"
          :href="currentPublishedUrl"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="打开当前线上 YAML"
        >
          <ExternalLink :size="16" />
        </a>
      </div>
      <div class="settings-row">
        <div>
          <div class="text-[15px] font-semibold">自动核对线上版本</div>
          <div class="mt-0.5 text-xs text-[var(--text-muted)]">网络可达时刷新 Lucky 根目录索引并比较真实字节哈希</div>
        </div>
        <button class="soft-button" :disabled="publicationBusy" @click="checkPublication">
          <RefreshCw :size="15" :class="{ 'animate-spin': publicationBusy }" />
          {{ publicationBusy ? "核对中…" : "尝试核对" }}
        </button>
      </div>
      <div
        v-if="publication"
        class="publication-result"
        :class="publication.matching ? 'publication-result-ok' : 'publication-result-mismatch'"
      >
        <FileCheck2 :size="20" />
        <div>
          <strong>{{ publication.matching ? "线上版本与当前 YAML 一致" : "线上版本与当前 YAML 不一致" }}</strong>
          <p>
            当前 {{ publication.currentHash.slice(0, 12) }} ·
            线上 {{ publication.publishedHash.slice(0, 12) }} ·
            {{ publication.latencyMs }} ms
          </p>
          <p v-if="publication.lastModified">线上时间：{{ publication.lastModified }}</p>
        </div>
      </div>
      <p v-if="publicationError" class="form-error mx-4 mb-4">{{ publicationError }}</p>
      <p class="publication-help">
        Lucky 会缓存目录索引。请先点“打开”，让 Mac 浏览器刷新根目录；Docker bridge 无法访问仅有 IPv6 的公开地址时，自动核对会明确提示失败。完成后仍需在 Stash、OpenClash 或其他客户端执行订阅更新。
      </p>
    </GroupCard>

    <GroupCard title="日志保留">
      <div class="settings-row">
        <div>
          <div class="text-[15px] font-semibold">最大日志条数</div>
          <div class="mt-0.5 text-xs text-[var(--text-muted)]">
            当前 {{ currentCount }} 条，自动保留最新最多 {{ maxEntries }} 条
          </div>
        </div>
        <select :value="maxEntries" class="compact-select" :disabled="settingsBusy" @change="saveLogLimit(($event.target as HTMLSelectElement).value)">
          <option v-for="value in [100, 500, 1000, 5000]" :key="value" :value="value">{{ value }}</option>
          <option v-if="![100, 500, 1000, 5000].includes(maxEntries)" :value="maxEntries">自定义 {{ maxEntries }}</option>
        </select>
      </div>
      <div class="settings-row">
        <label class="form-field flex-1">
          <span>自定义条数</span>
          <input v-model="customLimit" inputmode="numeric" placeholder="1–50000" :disabled="settingsBusy" />
        </label>
        <button class="soft-button" :disabled="settingsBusy" @click="saveLogLimit(customLimit)">
          {{ settingsBusy ? "处理中…" : "应用" }}
        </button>
      </div>
      <p v-if="settingsError" class="form-error px-4">{{ settingsError }}</p>
      <div class="settings-row">
        <div><strong>立即清空操作日志</strong><div class="mt-0.5 text-xs text-[var(--text-muted)]">仅删除审计行</div></div>
        <button class="danger-button" :disabled="settingsBusy" @click="clearLogs">
          {{ settingsBusy ? "处理中…" : "立即清空" }}
        </button>
      </div>
    </GroupCard>

    <GroupCard title="安全">
      <div class="settings-row">
        <div class="flex items-center gap-3">
          <div class="row-icon bg-red-500"><LockKeyhole :size="18" /></div>
          <div>
            <div class="text-[15px] font-semibold">连接凭据</div>
            <div class="mt-0.5 text-xs text-[var(--text-muted)]">仅由后端读取，不返回浏览器</div>
          </div>
        </div>
        <Shield :size="18" class="text-emerald-500" />
      </div>
    </GroupCard>

    <section class="logs-section">
      <div class="logs-heading">
        <div>
          <h3>操作与状态日志</h3>
          <p>持久化记录，不包含连接凭据。</p>
        </div>
        <button class="icon-button" aria-label="刷新日志" :disabled="loading" @click="loadLogs">
          <RefreshCw :size="17" :class="{ 'animate-spin': loading }" />
        </button>
      </div>
      <div class="log-filters">
        <button :class="{ active: !currentOnly }" @click="currentOnly = false; loadLogs()">全部</button>
        <button :class="{ active: currentOnly }" @click="currentOnly = true; loadLogs()">当前文件</button>
      </div>
      <p v-if="logError" class="form-error">{{ logError }}</p>
      <div v-if="logs.length" class="ios-card overflow-hidden">
        <article v-for="entry in logs" :key="entry.id" class="log-row">
          <i :class="entry.status === 'success' ? 'log-status-ok' : 'log-status-fail'" />
          <div class="min-w-0 flex-1">
            <div class="log-row-title">
              <strong>{{ actionLabel(entry.action) }}</strong>
              <span>{{ entry.fileName }} · {{ entry.sourceName }}</span>
            </div>
            <p>{{ entry.message }}</p>
          </div>
          <time>{{ new Date(entry.createdAt).toLocaleString("zh-CN", { hour12: false }) }}</time>
        </article>
      </div>
      <div v-else class="empty-card">
        <p>{{ loading ? "正在加载日志…" : "暂无操作日志" }}</p>
      </div>
    </section>
  </div>
</template>
