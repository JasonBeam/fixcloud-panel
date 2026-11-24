<script setup lang="ts">
import { ChevronLeft, ChevronRight, CloudDownload, Layers3, RefreshCw, Search, Server, WifiOff } from "lucide-vue-next";
import { computed, onMounted, ref, watch } from "vue";
import { useAppStore } from "@/stores/app";

type Node = { name: string; type: string };
type DisplayNode = Node & { provider: string; providerTitle: string };
type Provider = { provider: string; title: string; nodeCount: number; nodes: Node[]; status: "ok" | "error"; message?: string };
type NodesResponse = { providers: Provider[]; totalProviders: number; totalNodes: number; cached: boolean; refreshedAt: number };

const appStore = useAppStore();
const response = ref<NodesResponse | null>(null);
const selectedProvider = ref("__all__");
const query = ref("");
const loading = ref(false);
const error = ref("");
const page = ref(1);
const pageSize = 24;

const selected = computed(() => response.value?.providers.find((item) => item.provider === selectedProvider.value) || response.value?.providers[0]);
const visibleNodes = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  const providers = selectedProvider.value === "__all__"
    ? (response.value?.providers || []).filter((provider) => provider.status === "ok")
    : (selected.value?.status === "ok" ? [selected.value] : []);
  const nodes: DisplayNode[] = providers.flatMap((provider) => provider.nodes.map((node) => ({
    ...node,
    provider: provider.provider,
    providerTitle: provider.title,
  })));
  return keyword
    ? nodes.filter((node) => node.name.toLowerCase().includes(keyword) || node.type.toLowerCase().includes(keyword))
    : nodes;
});
const totalPages = computed(() => Math.max(1, Math.ceil(visibleNodes.value.length / pageSize)));
const pageItems = computed(() => Array.from({ length: totalPages.value }, (_, index) => index + 1));
const pagedNodes = computed(() => visibleNodes.value.slice((page.value - 1) * pageSize, page.value * pageSize));
const sourceLabel = computed(() => appStore.file.sourceType === "upload"
  ? "已上传文件"
  : appStore.file.sourceType === "webdav" ? "WebDAV" : "SMB");

async function refresh(force = false) {
  if (loading.value) return;
  loading.value = true;
  error.value = "";
  try {
    const queryString = new URLSearchParams({ sourceId: appStore.file.sourceId, path: appStore.file.path });
    if (force) queryString.set("force", "true");
    const payload = await appStore.request("/api/subscriptions/nodes?" + queryString) as NodesResponse;
    response.value = payload;
    if (selectedProvider.value !== "__all__" && !payload.providers.some((item) => item.provider === selectedProvider.value)) selectedProvider.value = "__all__";
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "无法读取订阅节点";
  } finally {
    loading.value = false;
  }
}

function providerNodeCount(provider: Provider) {
  return provider.status === "ok" ? provider.nodeCount + " 个节点" : provider.message || "读取失败";
}

onMounted(() => void refresh());
watch(() => appStore.file.sourceId + ":" + appStore.file.path, () => void refresh(true));
watch([selectedProvider, query], () => { page.value = 1; });
watch(totalPages, (count) => { if (page.value > count) page.value = count; });
</script>

<template>
  <div class="page-width nodes-reference-page">
    <header class="nodes-page-heading">
      <div>
        <p class="eyebrow">代理订阅</p>
        <h2 class="page-title">订阅节点</h2>
        <p class="page-subtitle">集中查看当前 YAML 中的远程代理节点。</p>
      </div>
      <button class="nodes-refresh-button" aria-label="刷新订阅节点" :disabled="loading" @click="refresh(true)">
        <RefreshCw :size="17" :class="{ 'animate-spin': loading }" />
        <span>{{ loading ? "读取中" : "刷新节点" }}</span>
      </button>
    </header>

    <div class="nodes-source-strip">
      <span class="nodes-source-dot" />
      <strong>{{ appStore.file.path.split("/").pop() }}</strong>
      <span>{{ sourceLabel }}</span>
      <small v-if="response">{{ response.totalProviders }} 个订阅 · {{ response.totalNodes }} 个节点</small>
    </div>

    <p v-if="error" class="form-error nodes-error">{{ error }}</p>
    <div v-if="loading && !response" class="empty-card">
      <div class="loading-orb" />
      <p class="mt-4 text-sm text-[var(--text-muted)]">正在读取机场节点…</p>
    </div>
    <div v-else-if="!response?.providers.length" class="empty-card">
      <div class="empty-icon"><CloudDownload :size="24" /></div>
      <h3 class="mt-4 font-semibold">没有可读取的订阅</h3>
      <p class="mt-1 text-sm text-[var(--text-muted)]">当前 YAML 的 proxy-providers 中没有带 URL 的 HTTP 来源。</p>
    </div>

    <section v-else class="nodes-workspace">
      <aside class="nodes-provider-panel" aria-label="机场订阅筛选">
        <header class="nodes-provider-heading">
          <div>
            <p>来源筛选</p>
            <h3>机场订阅</h3>
          </div>
          <Layers3 :size="18" />
        </header>

        <nav class="nodes-provider-list">
          <button type="button" class="nodes-provider-row" :class="{ selected: selectedProvider === '__all__' }" @click="selectedProvider = '__all__'">
            <span class="nodes-provider-icon all"><Layers3 :size="18" /></span>
            <span class="nodes-provider-copy"><strong>全部节点</strong><small>全部订阅来源</small></span>
            <em>{{ response.totalNodes }}</em>
          </button>
          <button v-for="provider in response.providers" :key="provider.provider" type="button" class="nodes-provider-row" :class="{ selected: selectedProvider === provider.provider, failed: provider.status === 'error' }" @click="selectedProvider = provider.provider">
            <span class="nodes-provider-icon"><CloudDownload :size="18" /></span>
            <span class="nodes-provider-copy"><strong>{{ provider.title }}</strong><small>{{ providerNodeCount(provider) }}</small></span>
            <em>{{ provider.status === "ok" ? provider.nodeCount : "!" }}</em>
          </button>
        </nav>
      </aside>

      <main class="nodes-content-panel">
        <header class="nodes-content-heading">
          <div>
            <p class="eyebrow">节点列表</p>
            <h3>{{ selectedProvider === "__all__" ? "订阅节点" : selected?.title }}</h3>
            <p>{{ selectedProvider === "__all__" ? "全部节点" : selected?.provider }} · {{ visibleNodes.length }} 个节点</p>
          </div>
          <label class="nodes-search">
            <Search :size="17" />
            <input v-model="query" type="search" placeholder="搜索节点或协议" aria-label="搜索节点或协议" />
          </label>
        </header>

        <div v-if="selectedProvider !== '__all__' && selected?.status === 'error'" class="nodes-empty">
          <WifiOff :size="26" />
          <p>{{ selected.message || "此机场订阅暂时无法读取" }}</p>
        </div>
        <div v-else-if="!visibleNodes.length" class="nodes-empty">
          <Search :size="26" />
          <p>没有匹配的节点</p>
        </div>
        <div v-else class="nodes-card-grid">
          <article v-for="node in pagedNodes" :key="node.provider + ':' + node.name" class="subscription-node-card">
            <div class="subscription-node-card-top">
              <span class="subscription-node-icon"><Server :size="20" /></span>
              <ChevronRight class="subscription-node-chevron" :size="17" />
            </div>
            <h4 :title="node.name">{{ node.name }}</h4>
            <div class="subscription-node-meta">
              <span class="subscription-protocol">{{ node.type }}</span>
              <span :title="node.providerTitle">{{ node.providerTitle }}</span>
            </div>
          </article>
        </div>

        <footer v-if="visibleNodes.length" class="nodes-pagination">
          <span>第 {{ page }} / {{ totalPages }} 页 · 共 {{ visibleNodes.length }} 个节点</span>
          <div>
            <button type="button" aria-label="上一页" :disabled="page === 1" @click="page -= 1"><ChevronLeft :size="16" /></button>
            <button v-for="item in pageItems" :key="item" type="button" :class="{ active: page === item }" @click="page = item">{{ item }}</button>
            <button type="button" aria-label="下一页" :disabled="page === totalPages" @click="page += 1"><ChevronRight :size="16" /></button>
          </div>
          <small>24 条/页</small>
        </footer>
      </main>
    </section>
  </div>
</template>

<style scoped>
.nodes-reference-page { max-width: 1480px; }
.nodes-page-heading { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 16px; }
.nodes-page-heading .page-subtitle { margin-bottom: 0; }
.nodes-refresh-button { display: inline-flex; min-height: 40px; flex: 0 0 auto; align-items: center; justify-content: center; gap: 8px; border: 1px solid color-mix(in srgb, var(--separator) 90%, transparent); border-radius: 12px; padding: 0 14px; color: var(--text-primary); background: var(--card-strong); box-shadow: 0 3px 12px rgba(30, 41, 59, .06); font-size: 13px; font-weight: 700; transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease; }
.nodes-refresh-button:hover:not(:disabled) { border-color: color-mix(in srgb, #0a84ff 40%, var(--separator)); box-shadow: 0 7px 16px rgba(10, 132, 255, .12); transform: translateY(-1px); }
.nodes-refresh-button:disabled { opacity: .65; }
.nodes-source-strip { display: flex; min-height: 39px; align-items: center; gap: 8px; margin-bottom: 18px; padding: 0 13px; border: 1px solid var(--separator); border-radius: 12px; color: var(--text-muted); background: color-mix(in srgb, var(--card-strong) 83%, transparent); font-size: 12px; }
.nodes-source-strip strong { color: var(--text-primary); font-size: 13px; }.nodes-source-strip small { margin-left: auto; color: var(--text-faint); }.nodes-source-dot { width: 7px; height: 7px; flex: 0 0 auto; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 3px rgba(34, 197, 94, .13); }.nodes-error { margin-bottom: 16px; }
.nodes-workspace { display: grid; min-height: 690px; grid-template-columns: 236px minmax(0, 1fr); gap: 16px; padding: 16px; border: 1px solid color-mix(in srgb, var(--separator) 90%, transparent); border-radius: 24px; background: var(--card-strong); box-shadow: 0 14px 35px rgba(23, 35, 54, .07); }
.nodes-provider-panel, .nodes-content-panel { min-width: 0; border: 1px solid var(--separator); border-radius: 17px; background: var(--card-strong); box-shadow: 0 3px 12px rgba(20, 30, 45, .035); }
.nodes-provider-panel { padding: 16px 10px; }.nodes-provider-heading { display: flex; align-items: center; justify-content: space-between; margin: 2px 8px 15px; color: #0a84ff; }.nodes-provider-heading p { margin: 0 0 3px; color: var(--text-faint); font-size: 11px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }.nodes-provider-heading h3 { margin: 0; color: var(--text-primary); font-size: 17px; letter-spacing: -.02em; }
.nodes-provider-list { display: grid; gap: 5px; }.nodes-provider-row { display: grid; width: 100%; grid-template-columns: 34px minmax(0, 1fr) auto; gap: 9px; align-items: center; border: 1px solid transparent; border-radius: 12px; padding: 10px 8px; color: var(--text-primary); text-align: left; background: transparent; transition: transform 150ms ease, border-color 150ms ease, background 150ms ease, box-shadow 150ms ease; }.nodes-provider-row:hover { border-color: color-mix(in srgb, #0a84ff 22%, var(--separator)); background: color-mix(in srgb, #0a84ff 5%, var(--card-strong)); transform: translateY(-1px); }.nodes-provider-row.selected { border-color: color-mix(in srgb, #0a84ff 22%, transparent); background: #eef6ff; box-shadow: inset 3px 0 0 #0a84ff; }.dark .nodes-provider-row.selected { background: color-mix(in srgb, #0a84ff 17%, var(--card-strong)); }.nodes-provider-row.failed { opacity: .64; }.nodes-provider-icon { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 10px; color: #398df7; background: #eef6ff; }.dark .nodes-provider-icon { background: color-mix(in srgb, #0a84ff 17%, var(--card-strong)); }.nodes-provider-icon.all { color: #0a84ff; }.nodes-provider-copy { display: grid; min-width: 0; gap: 2px; }.nodes-provider-copy strong, .nodes-provider-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.nodes-provider-copy strong { font-size: 13px; }.nodes-provider-copy small { color: var(--text-muted); font-size: 11px; }.nodes-provider-row em { display: grid; min-width: 21px; height: 21px; place-items: center; border-radius: 999px; color: var(--text-muted); background: var(--field-bg); font-size: 10px; font-style: normal; font-weight: 750; }.nodes-provider-row.selected em { color: #0a84ff; background: rgba(10, 132, 255, .12); }
.nodes-content-panel { display: flex; min-height: 0; flex-direction: column; padding: 20px; }.nodes-content-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 18px; padding: 0 1px 17px; border-bottom: 1px solid var(--separator); }.nodes-content-heading .eyebrow { margin: 0 0 4px; font-size: 10px; }.nodes-content-heading h3 { margin: 0 0 4px; color: var(--text-primary); font-size: 22px; letter-spacing: -.035em; }.nodes-content-heading p:not(.eyebrow) { margin: 0; color: var(--text-muted); font-size: 12px; }.nodes-search { display: flex; width: min(310px, 42%); height: 39px; align-items: center; gap: 8px; border: 1px solid var(--separator); border-radius: 11px; padding: 0 11px; color: var(--text-muted); background: var(--field-bg); transition: border-color 150ms ease, box-shadow 150ms ease; }.nodes-search:focus-within { border-color: rgba(10, 132, 255, .55); box-shadow: 0 0 0 3px rgba(10, 132, 255, .12); }.nodes-search input { width: 100%; min-width: 0; border: 0; outline: 0; color: var(--text-primary); background: transparent; font-size: 13px; }
.nodes-card-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; align-content: start; }.subscription-node-card { display: flex; min-width: 0; min-height: 126px; flex-direction: column; justify-content: space-between; border: 1px solid var(--separator); border-radius: 14px; padding: 13px; background: var(--card-strong); box-shadow: 0 3px 10px rgba(23, 36, 58, .035); transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease; }.subscription-node-card:hover { border-color: color-mix(in srgb, #0a84ff 30%, var(--separator)); box-shadow: 0 10px 19px rgba(10, 132, 255, .12); transform: translateY(-3px); }.subscription-node-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }.subscription-node-icon { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 10px; color: #2584f3; background: #eef6ff; }.dark .subscription-node-icon { background: color-mix(in srgb, #0a84ff 16%, var(--card-strong)); }.subscription-node-chevron { color: var(--text-faint); transition: transform 160ms ease; }.subscription-node-card:hover .subscription-node-chevron { color: #0a84ff; transform: translateX(2px); }.subscription-node-card h4 { overflow: hidden; margin: 0 0 9px; color: var(--text-primary); font-size: 13px; font-weight: 750; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }.subscription-node-meta { display: flex; min-width: 0; align-items: center; gap: 6px; color: var(--text-muted); font-size: 10px; }.subscription-node-meta > span:last-child { overflow: hidden; min-width: 0; text-overflow: ellipsis; white-space: nowrap; }.subscription-protocol { flex: 0 0 auto; border-radius: 6px; padding: 3px 5px; color: #0a84ff; background: #eef6ff; font-size: 9px; font-weight: 800; line-height: 1; text-transform: uppercase; }.dark .subscription-protocol { background: color-mix(in srgb, #0a84ff 17%, var(--card-strong)); }
.nodes-empty { display: grid; min-height: 390px; flex: 1; place-content: center; justify-items: center; gap: 10px; color: var(--text-muted); text-align: center; }.nodes-empty p { margin: 0; }
.nodes-pagination { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; margin-top: auto; padding: 20px 1px 0; color: var(--text-muted); font-size: 12px; }.nodes-pagination > div { display: flex; gap: 4px; }.nodes-pagination button { display: grid; width: 29px; height: 29px; place-items: center; border: 1px solid transparent; border-radius: 8px; color: var(--text-primary); background: transparent; transition: background 150ms ease, transform 150ms ease; }.nodes-pagination button:hover:not(:disabled) { background: #eef6ff; color: #0a84ff; transform: translateY(-1px); }.dark .nodes-pagination button:hover:not(:disabled) { background: color-mix(in srgb, #0a84ff 16%, var(--card-strong)); }.nodes-pagination button.active { color: white; background: #0a84ff; }.nodes-pagination button:disabled { opacity: .35; }.nodes-pagination > small { text-align: right; }
@media (max-width: 1280px) { .nodes-card-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 960px) { .nodes-workspace { grid-template-columns: 1fr; }.nodes-provider-panel { padding: 13px; }.nodes-provider-heading { margin-bottom: 10px; }.nodes-provider-list { grid-auto-columns: minmax(175px, 1fr); grid-auto-flow: column; grid-template-rows: 1fr; overflow-x: auto; }.nodes-provider-row { min-width: 175px; }.nodes-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .nodes-page-heading { align-items: flex-start; flex-direction: column; }.nodes-refresh-button { width: 100%; }.nodes-source-strip { align-items: flex-start; flex-wrap: wrap; padding: 10px 13px; }.nodes-source-strip small { width: 100%; margin-left: 15px; }.nodes-workspace { gap: 12px; padding: 10px; border-radius: 18px; }.nodes-content-panel { padding: 15px; }.nodes-content-heading { align-items: stretch; flex-direction: column; }.nodes-search { width: 100%; }.nodes-card-grid { grid-template-columns: 1fr; }.nodes-pagination { grid-template-columns: 1fr auto; }.nodes-pagination > small { display: none; } }
@media (prefers-reduced-motion: reduce) { .nodes-refresh-button, .nodes-provider-row, .nodes-search, .subscription-node-card, .subscription-node-chevron, .nodes-pagination button { transition: none; }.nodes-refresh-button:hover:not(:disabled), .nodes-provider-row:hover, .subscription-node-card:hover, .nodes-pagination button:hover:not(:disabled) { transform: none; } }
</style>
