<script setup lang="ts">
import { Check, ExternalLink, Images, RefreshCw, Search, X } from "lucide-vue-next";
import { computed, ref, watch } from "vue";

import { useAppStore } from "@/stores/app";

type CatalogIcon = {
  name: string;
  filename: string;
  url: string;
};

const props = defineProps<{
  open: boolean;
  modelValue: string;
}>();

const emit = defineEmits<{
  close: [];
  select: [url: string];
}>();

const appStore = useAppStore();
const items = ref<CatalogIcon[]>([]);
const personalItems = ref<CatalogIcon[]>([]);
const collection = ref<"personal" | "community">("personal");
const query = ref("");
const loading = ref(false);
const error = ref("");
const warning = ref("");
const failedImages = ref(new Set<string>());
const repositoryUrl = ref("https://github.com/shindgew/WHATSINStash");

const activeItems = computed(() =>
  collection.value === "personal" ? personalItems.value : items.value,
);
const filtered = computed(() => {
  const needle = query.value.trim().toLowerCase();
  if (!needle) return activeItems.value;
  return activeItems.value.filter((item) =>
    `${item.name} ${item.filename}`.toLowerCase().includes(needle),
  );
});

async function load(force = false) {
  if (loading.value) return;
  const firstLoad = !items.value.length && !personalItems.value.length;
  loading.value = true;
  error.value = "";
  warning.value = "";
  try {
    const payload = await appStore.request(`/api/icons/catalog${force ? "?force=true" : ""}`);
    items.value = payload.items;
    personalItems.value = payload.personalItems ?? [];
    if (firstLoad) {
      collection.value = personalItems.value.length ? "personal" : "community";
    } else if (!personalItems.value.length) {
      collection.value = "community";
    }
    failedImages.value = new Set();
    repositoryUrl.value = payload.repositoryUrl;
    warning.value = payload.warning ?? "";
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "图标目录加载失败";
  } finally {
    loading.value = false;
  }
}

function choose(item: CatalogIcon) {
  emit("select", item.url);
}

function markFailed(url: string) {
  failedImages.value = new Set([...failedImages.value, url]);
}

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    query.value = "";
    collection.value = personalItems.value.length ? "personal" : "community";
    if (!items.value.length) void load();
  },
);
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="icon-catalog-layer" @click.self="emit('close')">
      <section class="icon-catalog-panel" role="dialog" aria-modal="true" aria-label="选择策略组图标">
        <header class="icon-catalog-header">
          <button type="button" class="member-picker-round-button" aria-label="关闭" @click="emit('close')">
            <X :size="21" />
          </button>
          <div>
            <h2>选择图标</h2>
            <small>我的图标 {{ personalItems.length }} · WHATSINStash {{ items.length }}</small>
          </div>
          <button type="button" class="icon-catalog-refresh" :disabled="loading" @click="load(true)">
            <RefreshCw :size="16" :class="{ 'animate-spin': loading }" />
            更新
          </button>
        </header>

        <div class="icon-catalog-body">
          <div class="icon-catalog-sources" role="tablist" aria-label="图标来源">
            <button
              type="button"
              role="tab"
              :aria-selected="collection === 'personal'"
              :class="{ active: collection === 'personal' }"
              @click="collection = 'personal'; query = ''"
            >
              我的图标
              <small>{{ personalItems.length }}</small>
            </button>
            <button
              type="button"
              role="tab"
              :aria-selected="collection === 'community'"
              :class="{ active: collection === 'community' }"
              @click="collection = 'community'; query = ''"
            >
              WHATSINStash
              <small>{{ items.length }}</small>
            </button>
          </div>

          <div class="member-picker-search">
            <Search :size="17" />
            <input v-model="query" placeholder="搜索 ChatGPT、Netflix、Apple…" autocomplete="off" />
          </div>

          <p v-if="warning" class="icon-catalog-notice">{{ warning }}</p>
          <p v-if="error" class="form-error">{{ error }}</p>

          <div v-if="filtered.length" class="icon-catalog-grid">
            <button
              v-for="item in filtered"
              :key="item.url"
              type="button"
              class="icon-catalog-item"
              :class="{ 'icon-catalog-item-selected': item.url === modelValue }"
              :title="item.filename"
              @click="choose(item)"
            >
              <span>
                <Images v-if="failedImages.has(item.url)" :size="24" />
                <img
                  v-else
                  :src="item.url"
                  :alt="item.name"
                  loading="lazy"
                  @error="markFailed(item.url)"
                />
              </span>
              <strong>{{ item.name }}</strong>
              <Check v-if="item.url === modelValue" :size="15" />
            </button>
          </div>

          <div v-else class="member-picker-empty">
            {{ loading ? "正在读取图标目录…" : query ? "没有符合搜索条件的图标" : "暂无可用图标" }}
          </div>
        </div>

        <footer class="icon-catalog-footer">
          <span>
            {{ collection === "personal"
              ? "来自 NAS icon 目录，不会覆盖或修改原图片。"
              : "选择后使用 公开文件域/icon 中的个人图标副本。" }}
          </span>
          <a v-if="collection === 'community'" :href="repositoryUrl" target="_blank" rel="noopener noreferrer">
            查看仓库
            <ExternalLink :size="14" />
          </a>
        </footer>
      </section>
    </div>
  </Teleport>
</template>
