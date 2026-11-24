<script setup lang="ts">
import {
  ArrowDown,
  ArrowUp,
  CalendarDays,
  CloudDownload,
  Gauge,
  RefreshCw,
  TimerReset,
  WifiOff,
} from "lucide-vue-next";
import { computed, onMounted, ref, watch } from "vue";

import { useAppStore } from "@/stores/app";

type SubscriptionUsage = {
  provider: string;
  title: string;
  available: boolean;
  message?: string;
  upload?: number;
  download?: number;
  used?: number;
  total?: number;
  remaining?: number;
  remainingPercent?: number;
  expireAt?: string | null;
  remainingDays?: number | null;
  expired?: boolean;
};

const appStore = useAppStore();
const subscriptions = ref<SubscriptionUsage[]>([]);
const fetchedAt = ref("");
const cached = ref(false);
const loading = ref(false);
const error = ref("");
type VpsUsage = { name: string; provider: string; available: boolean; message?: string; used?: number; total?: number; unit?: string; scope?: string; note?: string; expiry?: string | null; upload?: number | null; download?: number | null };
const servers = ref<VpsUsage[]>([]);
const serverError = ref("");

function vpsDate(value?: string | null) {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.replace(/-/g, "/") : "未提供";
}

function vpsDays(value?: string | null) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "未提供";
  const end = Date.parse(`${value}T23:59:59+08:00`);
  return Number.isFinite(end) ? `${Math.max(0, Math.ceil((end - Date.now()) / 86400000))} 天` : "未提供";
}

function vpsTransfer(value: number | null | undefined, unit?: string) {
  return value == null ? "未提供" : `${value.toFixed(2)} ${unit ?? ""}`;
}

async function refreshServers() {
  try {
    const payload = await appStore.request("/api/vps/usage");
    servers.value = payload.servers;
    serverError.value = "";
  } catch {
    serverError.value = "暂时无法读取 VPS 流量";
  }
}

const availableCount = computed(
  () => subscriptions.value.filter((item) => item.available).length,
);

function formatBytes(value?: number) {
  const bytes = Math.max(0, Number(value ?? 0));
  const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
  let amount = bytes;
  let index = 0;
  while (amount >= 1024 && index < units.length - 1) {
    amount /= 1024;
    index += 1;
  }
  return `${amount >= 100 ? amount.toFixed(0) : amount.toFixed(1)} ${units[index]}`;
}

function formatDate(value?: string | null) {
  if (!value) return "未提供";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function formatRefreshTime(value: string) {
  if (!value) return "尚未刷新";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

async function refresh(force = false) {
  if (loading.value) return;
  loading.value = true;
  void refreshServers();
  error.value = "";
  try {
    const query = new URLSearchParams({
      sourceId: appStore.file.sourceId,
      path: appStore.file.path,
    });
    if (force) query.set("force", "true");
    const payload = await appStore.request(`/api/subscriptions/usage?${query}`);
    subscriptions.value = payload.subscriptions;
    fetchedAt.value = payload.fetchedAt;
    cached.value = Boolean(payload.cached);
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "无法读取订阅流量";
  } finally {
    loading.value = false;
  }
}

onMounted(() => void refresh());
watch(
  () => [appStore.file.sourceId, appStore.file.path],
  () => void refresh(true),
);
</script>

<template>
  <div class="page-width usage-page">
    <div class="usage-page-heading">
      <div>
        <p class="eyebrow">订阅状态</p>
        <h2 class="page-title">机场流量</h2>
        <p class="page-subtitle">
          从当前主配置的 proxy-providers 读取标准流量响应头，不下载或更新订阅。
        </p>
      </div>
      <button
        class="icon-button"
        aria-label="刷新机场流量"
        :disabled="loading"
        @click="refresh(true)"
      >
        <RefreshCw :size="18" :class="{ 'animate-spin': loading }" />
      </button>
    </div>
    <div class="current-source-banner">
      <strong>{{ appStore.file.path.split("/").pop() }}</strong>
      <span>·</span>
      <span>{{ appStore.file.sourceType === "upload" ? "已上传文件" : appStore.file.sourceName }}</span>
      <small>{{ appStore.file.sourceType === "upload" ? "本地持久化" : appStore.file.sourceType === "webdav" ? "WebDAV" : "SMB" }}</small>
    </div>

    <div class="usage-refresh-line">
      <span class="status-dot" :class="error ? 'status-dot-warn' : 'status-dot-ok'" />
      <span>
        {{ error ? "读取失败" : `${availableCount} 个订阅提供流量信息` }}
      </span>
      <small>{{ cached ? "缓存数据 · " : "" }}{{ formatRefreshTime(fetchedAt) }}</small>
    </div>

    <p v-if="error" class="form-error mb-4">{{ error }}</p>

    <section v-if="servers.length || serverError" class="mb-6">
      <h3 class="mb-3 font-semibold">VPS 流量</h3>
      <p v-if="serverError" class="form-error">{{ serverError }}</p>
      <div class="usage-grid">
        <article v-for="server in servers" :key="server.provider" class="usage-card">
          <header class="usage-card-header">
            <div class="usage-provider-icon"><Gauge :size="22" /></div>
            <div><h3>{{ server.name }}</h3><p>{{ server.provider }} · {{ server.scope || '官方流量' }}</p></div>
          </header>
          <template v-if="server.available && server.total && server.used !== undefined">
            <div class="usage-quota-line"><strong>{{ server.used.toFixed(2) }} / {{ server.total.toFixed(2) }} {{ server.unit }}</strong><span>剩余 {{ Math.max(0, 100 - server.used / server.total * 100).toFixed(1) }}%</span></div>
            <div class="usage-progress" aria-label="剩余流量比例"><i :style="{ width: `${Math.max(0, Math.min(100, 100 - server.used / server.total * 100))}%` }" /></div>
            <div class="usage-metrics">
              <div><CloudDownload :size="17" /><span>剩余流量</span><strong>{{ Math.max(0, server.total - server.used).toFixed(2) }} {{ server.unit }}</strong></div>
              <div><CalendarDays :size="17" /><span>到期时间</span><strong class="usage-expiry">{{ vpsDate(server.expiry) }}</strong></div>
              <div><TimerReset :size="17" /><span>剩余天数</span><strong>{{ vpsDays(server.expiry) }}</strong></div>
            </div>
            <footer class="usage-transfer">
              <span><ArrowUp :size="14" />上传 {{ vpsTransfer(server.upload, server.unit) }}</span>
              <span><ArrowDown :size="14" />下载 {{ vpsTransfer(server.download, server.unit) }}</span>
            </footer>
            <p class="mt-3 text-sm text-[var(--text-muted)]">{{ server.note }}</p>
          </template>
          <p v-else class="mt-3 text-sm text-[var(--text-muted)]">{{ server.message }}</p>
        </article>
      </div>
    </section>

    <div v-if="subscriptions.length" class="usage-grid">
      <article
        v-for="subscription in subscriptions"
        :key="subscription.provider"
        class="usage-card"
        :class="{ 'usage-card-unavailable': !subscription.available }"
      >
        <template v-if="subscription.available">
          <header class="usage-card-header">
            <div class="usage-provider-icon"><Gauge :size="22" /></div>
            <div class="min-w-0">
              <h3 class="truncate">{{ subscription.title }}</h3>
              <p v-if="subscription.title !== subscription.provider">
                Provider：{{ subscription.provider }}
              </p>
            </div>
            <span
              class="status-chip"
              :class="subscription.expired ? 'status-chip-warn' : 'status-chip-ok'"
            >
              {{ subscription.expired ? "已到期" : "正常" }}
            </span>
          </header>

          <div class="usage-quota-line">
            <strong>{{ formatBytes(subscription.used) }} / {{ formatBytes(subscription.total) }}</strong>
            <span>剩余 {{ subscription.remainingPercent?.toFixed(1) }}%</span>
          </div>
          <div class="usage-progress" aria-label="剩余流量比例">
            <i :style="{ width: `${Math.min(100, subscription.remainingPercent ?? 0)}%` }" />
          </div>

          <div class="usage-metrics">
            <div>
              <CloudDownload :size="17" />
              <span>剩余流量</span>
              <strong>{{ formatBytes(subscription.remaining) }}</strong>
            </div>
            <div>
              <CalendarDays :size="17" />
              <span>到期时间</span>
              <strong class="usage-expiry">{{ formatDate(subscription.expireAt) }}</strong>
            </div>
            <div>
              <TimerReset :size="17" />
              <span>剩余天数</span>
              <strong>
                {{ subscription.remainingDays === null ? "未提供" : `${subscription.remainingDays} 天` }}
              </strong>
            </div>
          </div>

          <footer class="usage-transfer">
            <span><ArrowUp :size="14" />上传 {{ formatBytes(subscription.upload) }}</span>
            <span><ArrowDown :size="14" />下载 {{ formatBytes(subscription.download) }}</span>
          </footer>
        </template>

        <template v-else>
          <div class="usage-unavailable">
            <div class="usage-provider-icon"><WifiOff :size="22" /></div>
            <div>
              <h3>{{ subscription.title }}</h3>
              <p>{{ subscription.message || "暂时无法读取流量信息" }}</p>
            </div>
          </div>
        </template>
      </article>
    </div>

    <div v-else-if="loading" class="empty-card">
      <div class="loading-orb" />
      <p class="mt-4 text-sm text-[var(--text-muted)]">正在读取订阅流量…</p>
    </div>
    <div v-else class="empty-card">
      <div class="empty-icon"><Gauge :size="24" /></div>
      <h3 class="mt-4 font-semibold">没有可读取的订阅</h3>
      <p class="mt-1 text-sm text-[var(--text-muted)]">
        当前 YAML 的 proxy-providers 中没有带 URL 的 HTTP 来源。
      </p>
    </div>
  </div>
</template>
