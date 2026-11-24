<script setup lang="ts">
import { ArchiveRestore, Clock3, Eye, RefreshCw, ShieldCheck, Trash2 } from "lucide-vue-next";
import { onMounted, ref, watch } from "vue";

import GroupCard from "@/components/GroupCard.vue";
import { confirmDialog } from "@/composables/appDialog";
import { useAppStore } from "@/stores/app";

type Backup = { name: string; path: string; size: number; modifiedAt: string };
type Audit = {
  id: number;
  createdAt: string;
  username: string;
  action: string;
  details: { operations: number; changedLines: number; warnings: number };
};

const appStore = useAppStore();
const backups = ref<Backup[]>([]);
const audit = ref<Audit[]>([]);
const loading = ref(false);
const deletingPath = ref("");
const error = ref("");

async function refresh() {
  loading.value = true;
  error.value = "";
  try {
    const payload = await appStore.request(
      `/api/history?sourceId=${encodeURIComponent(appStore.file.sourceId)}&path=${encodeURIComponent(appStore.file.path)}`,
    );
    backups.value = payload.backups;
    audit.value = payload.audit;
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "无法读取历史记录";
  } finally {
    loading.value = false;
  }
}

async function restore(backup: Backup) {
  if (!appStore.writeEnabled) return;
  try {
    appStore.preview = await appStore.request("/api/history/restore-preview", {
      method: "POST",
      body: JSON.stringify({
        sourceId: appStore.file.sourceId,
        path: appStore.file.path,
        backupPath: backup.path,
      }),
    });
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "无法生成恢复预览";
  }
}

async function deleteBackup(backup: Backup) {
  if (!appStore.writeEnabled || deletingPath.value) return;
  const confirmed = await confirmDialog({
    title: "删除这个历史备份？",
    message: `将永久删除备份文件“${backup.name}”（${formatTime(backup.modifiedAt)}）及对应历史记录。当前正式 YAML 不会被删除。`,
    confirmText: "删除备份",
    danger: true,
  });
  if (!confirmed) return;

  deletingPath.value = backup.path;
  error.value = "";
  try {
    await appStore.request("/api/history/backup", {
      method: "DELETE",
      body: JSON.stringify({
        sourceId: appStore.file.sourceId,
        path: appStore.file.path,
        backupPath: backup.path,
      }),
    });
    await refresh();
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "删除备份失败";
  } finally {
    deletingPath.value = "";
  }
}

function formatTime(value: string) {
  return value
    ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
    : "未知时间";
}

onMounted(refresh);
watch(
  () => [appStore.file.sourceId, appStore.file.path],
  () => void refresh(),
);
</script>

<template>
  <div class="page-width">
    <div class="mb-6 flex items-end justify-between">
      <div>
        <p class="eyebrow">安全恢复</p>
        <h2 class="page-title">配置历史</h2>
        <p class="page-subtitle">保留并管理已有历史备份；普通保存不再自动创建新备份。</p>
      </div>
      <button class="icon-button" aria-label="刷新历史" :disabled="loading" @click="refresh">
        <RefreshCw :size="18" :class="{ 'animate-spin': loading }" />
      </button>
    </div>

    <p v-if="error" class="form-error mb-4">{{ error }}</p>
    <div class="summary-grid">
      <div class="metric-card">
        <Clock3 :size="22" class="text-blue-500" />
        <div class="mt-4 text-2xl font-bold">{{ backups.length }}</div>
        <div class="mt-1 text-sm text-[var(--text-muted)]">历史版本</div>
      </div>
      <div class="metric-card">
        <ShieldCheck :size="22" class="text-emerald-500" />
        <div class="mt-4 text-2xl font-bold">{{ appStore.writeEnabled ? "受控写入" : "只读" }}</div>
        <div class="mt-1 text-sm text-[var(--text-muted)]">当前模式</div>
      </div>
    </div>

    <GroupCard title="备份文件">
      <article v-for="backup in backups" :key="backup.path" class="settings-row">
        <div class="flex min-w-0 items-center gap-3">
          <div class="row-icon bg-blue-500"><ArchiveRestore :size="18" /></div>
          <div class="min-w-0">
            <div class="truncate text-[14px] font-semibold">{{ backup.name }}</div>
            <div class="mt-0.5 text-xs text-[var(--text-muted)]">
              {{ formatTime(backup.modifiedAt) }} · {{ backup.size.toLocaleString() }} bytes
            </div>
          </div>
        </div>
        <div class="history-actions">
          <button
            class="soft-button"
            :disabled="!appStore.writeEnabled"
            title="查看恢复 Diff"
            @click="restore(backup)"
          >
            <Eye :size="15" />
            查看 Diff
          </button>
          <button
            class="soft-button"
            :disabled="!appStore.writeEnabled"
            @click="restore(backup)"
          >
            <ArchiveRestore :size="15" />
            恢复
          </button>
          <button
            class="icon-soft-button history-delete-button"
            :disabled="!appStore.writeEnabled || Boolean(deletingPath)"
            :aria-label="`删除 ${backup.name}`"
            @click="deleteBackup(backup)"
          >
            <RefreshCw v-if="deletingPath === backup.path" :size="15" class="animate-spin" />
            <Trash2 v-else :size="15" />
          </button>
        </div>
      </article>
      <div v-if="!backups.length" class="empty-card border-0 bg-transparent shadow-none">
        <div class="empty-icon"><ArchiveRestore :size="24" /></div>
        <h3 class="mt-4 font-semibold">尚无历史版本</h3>
        <p class="mt-1 text-sm text-[var(--text-muted)]">普通保存不会自动生成历史备份。</p>
      </div>
    </GroupCard>

    <GroupCard title="操作日志">
      <article v-for="entry in audit" :key="entry.id" class="settings-row">
        <div class="min-w-0">
          <div class="text-[14px] font-semibold">
            {{ entry.action === "restore" ? "恢复配置" : "保存配置" }}
          </div>
          <div class="mt-1 text-xs text-[var(--text-muted)]">
            {{ formatTime(entry.createdAt) }} · 内网访问 ·
            {{ entry.details.changedLines }} 行变化
          </div>
        </div>
        <ShieldCheck :size="18" class="text-emerald-500" />
      </article>
      <p v-if="!audit.length" class="p-5 text-center text-sm text-[var(--text-muted)]">暂无操作记录</p>
    </GroupCard>
  </div>
</template>
