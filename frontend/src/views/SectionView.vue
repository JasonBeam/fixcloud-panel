<script setup lang="ts">
import {
  Braces,
  ChevronRight,
  CloudDownload,
  Code2,
  FileJson,
  Filter,
  GripVertical,
  Plus,
  Search,
  SlidersHorizontal,
} from "lucide-vue-next";
import { computed, ref, type Component } from "vue";
import { useRoute, useRouter } from "vue-router";

import EditorTopBar from "@/components/EditorTopBar.vue";
import DnsSettingsEditor from "@/components/DnsSettingsEditor.vue";
import GeneralSettingsEditor from "@/components/GeneralSettingsEditor.vue";
import ProxyGroupIcon from "@/components/ProxyGroupIcon.vue";
import { promptDialog } from "@/composables/appDialog";
import { allowNextRoute, requestDraftTransition } from "@/composables/draftGuard";
import { useAppStore } from "@/stores/app";

type Row = {
  id: string;
  title: string;
  subtitle: string;
  value?: string;
  badge?: string;
  icon?: string;
  typeLabel?: string;
  ruleContent?: string;
  ruleTarget?: string;
  index?: number;
  movable: boolean;
};

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const search = ref("");
const selectedFilter = ref("全部");
const dragFrom = ref<number | null>(null);
const dragOver = ref<number | null>(null);
const suppressOpen = ref(false);

const sectionKey = computed(() => String(route.params.section));
const isSettingsSection = computed(() => ["general", "dns"].includes(sectionKey.value));
const sectionIcons: Record<string, Component> = {
  "proxy-providers": CloudDownload,
  "rule-providers": FileJson,
  rewrite: SlidersHorizontal,
  script: Code2,
  other: Braces,
};

const catalog: Record<string, { title: string; description: string }> = {
  general: {
    title: "通用设置",
    description: "缺失字段不会自动写入默认值；每项修改均在原始文档树上完成。",
  },
  dns: {
    title: "DNS 服务器",
    description: "管理监听、Fake IP、服务器列表、策略和过滤器。",
  },
  proxies: {
    title: "本地代理",
    description: "兼容 SS、VMess、VLESS、Trojan、SOCKS5、Hysteria、TUIC 等字段。",
  },
  "proxy-groups": {
    title: "策略组",
    description: "支持 proxies、use、filter、include-all 等字段。",
  },
  "proxy-providers": {
    title: "远程代理集",
    description: "管理 type、URL、path、interval、health-check 和扩展字段。",
  },
  rules: {
    title: "规则",
    description: "",
  },
  "rule-providers": {
    title: "远程规则集",
    description: "管理 type、behavior、URL、path、interval 及未知字段。",
  },
  rewrite: { title: "HTTP 改写", description: "以结构化列表或键值对管理改写配置。" },
  script: { title: "脚本", description: "保留脚本结构及所有未识别参数。" },
  other: {
    title: "其他设置",
    description: "未知顶层字段完整保留，并通过结构化高级字段编辑。",
  },
};

const generalKeys = [
  "port",
  "mixed-port",
  "socks-port",
  "allow-lan",
  "bind-address",
  "mode",
  "log-level",
  "ipv6",
  "external-controller",
  "secret",
];
const knownTopLevel = new Set([
  ...generalKeys,
  "dns",
  "proxies",
  "proxy-providers",
  "proxy-groups",
  "rules",
  "rule-providers",
  "rewrite",
  "script",
]);

function badgeFor(item: unknown): string {
  if (typeof item === "string") return item.split(",", 1)[0] || "RULE";
  if (item && typeof item === "object") {
    return String((item as Record<string, unknown>).type ?? "OBJECT").toUpperCase();
  }
  return typeof item;
}

function subtitleFor(section: string, item: unknown): string {
  if (typeof item === "string") {
    const parts = item.split(",");
    return parts.slice(1).join(" · ") || "字符串";
  }
  if (!item || typeof item !== "object") return String(item ?? "未配置");
  const object = item as Record<string, unknown>;
  if (section === "proxies") return `${object.server ?? "未设置服务器"} · ${object.port ?? "未设置端口"}`;
  if (section === "proxy-groups") {
    const count = Array.isArray(object.proxies) ? object.proxies.length : 0;
    const useCount = Array.isArray(object.use) ? object.use.length : 0;
    return `${count} 个目标 · ${useCount} 个代理集`;
  }
  if (section.includes("providers")) {
    const urlStatus = object.url ? "URL 已配置" : "URL 未配置";
    return `${object.behavior ?? object.type ?? "provider"} · ${urlStatus} · ${object.interval ?? "未设置周期"}`;
  }
  return `${Object.keys(object).length} 个字段`;
}

function ruleDisplay(rule: string): { title: string; badge: string; content: string; target: string } {
  const parts = rule.split(",").map((part) => part.trim());
  const badge = (parts[0] || "RULE").toUpperCase();
  const target = badge === "MATCH" ? parts[1] : parts[2];
  const content = badge === "MATCH" ? "MATCH" : (parts[1] || badge);
  return {
    title: `${content} → ${target || "未设置策略"}`,
    badge,
    content,
    target: target || "未设置策略",
  };
}

function groupTypeLabel(type: unknown) {
  const labels: Record<string, string> = {
    select: "Select",
    "url-test": "URL Test",
    fallback: "Fallback",
    "load-balance": "Load Balance",
  };
  return labels[String(type ?? "")] ?? String(type ?? "未设置类型");
}

const allRows = computed<Row[]>(() => {
  const section = sectionKey.value;
  if (section === "general") {
    return generalKeys
      .filter((key) => Object.prototype.hasOwnProperty.call(appStore.document, key))
      .map((key) => ({
        id: key,
        title: key,
        subtitle: typeof appStore.document[key] === "boolean" ? "开关" : "基础参数",
        value: String(appStore.document[key]),
        movable: false,
      }));
  }
  if (section === "dns") {
    const dns = (appStore.document.dns ?? {}) as Record<string, unknown>;
    return Object.entries(dns).map(([key, value]) => ({
      id: key,
      title: key,
      subtitle: Array.isArray(value) ? `${value.length} 项列表` : typeof value,
      value: Array.isArray(value) || typeof value === "object" ? undefined : String(value),
      badge: Array.isArray(value) ? "LIST" : undefined,
      movable: false,
    }));
  }
  if (section === "other") {
    return Object.entries(appStore.document)
      .filter(([key]) => !knownTopLevel.has(key))
      .map(([key, value]) => ({
        id: key,
        title: key,
        subtitle: Array.isArray(value) ? `${value.length} 项列表` : typeof value,
        value: value !== null && typeof value === "object" ? undefined : String(value),
        badge: "ADVANCED",
        movable: false,
      }));
  }
  const value = appStore.document[section];
  if (Array.isArray(value)) {
    return value.map((item, index) => {
      const object = item && typeof item === "object" ? (item as Record<string, unknown>) : null;
      const rule = section === "rules" && typeof item === "string" ? ruleDisplay(item) : null;
      return {
        id: String(index),
        index,
        title:
          rule?.title ||
          String(object?.name ?? "") ||
          (section === "rules" ? "未识别规则" : `${catalog[section]?.title ?? section} ${index + 1}`),
        subtitle: rule ? "" : subtitleFor(section, item),
        value: undefined,
        badge: rule?.badge ?? badgeFor(item),
        icon: ["proxy-groups", "proxies"].includes(section)
          ? String(object?.icon ?? "")
          : undefined,
        typeLabel: section === "proxy-groups" ? groupTypeLabel(object?.type) : undefined,
        ruleContent: rule?.content,
        ruleTarget: rule?.target,
        movable: true,
      };
    });
  }
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).map(([key, item], index) => ({
      id: key,
      index,
      title: key,
      subtitle: subtitleFor(section, item),
      badge: badgeFor(item),
      movable: true,
    }));
  }
  return [];
});

const filterOptions = computed(() => [
  "全部",
  ...Array.from(new Set(allRows.value.map((row) => row.badge).filter(Boolean) as string[])),
]);

const rows = computed(() => {
  const needle = search.value.trim().toLowerCase();
  return allRows.value.filter((row) => {
    const matchesSearch =
      !needle ||
      `${row.title} ${row.subtitle} ${row.value ?? ""} ${row.badge ?? ""}`
        .toLowerCase()
        .includes(needle);
    const matchesFilter = selectedFilter.value === "全部" || row.badge === selectedFilter.value;
    return matchesSearch && matchesFilter;
  });
});
const canDrag = computed(() => !search.value.trim() && selectedFilter.value === "全部");

function openItem(row: Row) {
  if (suppressOpen.value) return;
  void router.push({
    name: "item",
    params: { section: sectionKey.value, itemId: row.id },
  });
}

async function addItem() {
  const section = sectionKey.value;
  const root = appStore.document[section];
  if (section === "general") {
    const missing = generalKeys.filter(
      (key) => !Object.prototype.hasOwnProperty.call(appStore.document, key),
    );
    if (!missing.length) return;
    const key = await promptDialog({
      title: "新增通用参数",
      message: `可添加：${missing.join("、")}`,
      inputLabel: "字段名称",
      initialValue: missing[0],
    });
    if (!key || !missing.includes(key)) return;
    const defaults: Record<string, unknown> = {
      port: 7890,
      "mixed-port": 7890,
      "socks-port": 7891,
      "allow-lan": false,
      "bind-address": "*",
      mode: "rule",
      "log-level": "info",
      ipv6: false,
      "external-controller": "0.0.0.0:9090",
      secret: "",
    };
    appStore.setValue([key], defaults[key]);
    allowNextRoute();
    void router.push({ name: "item", params: { section, itemId: key } });
    return;
  }
  if (Array.isArray(root)) {
    const templates: Record<string, unknown> = {
      proxies: { name: "新节点", type: "ss", server: "", port: 443, cipher: "aes-128-gcm", password: "", udp: true },
      "proxy-groups": { name: "新策略组", type: "select", proxies: [] },
      rules: "DOMAIN-SUFFIX,example.com,DIRECT",
      rewrite: { name: "新改写", enabled: true },
      script: { name: "新脚本", enabled: true },
    };
    appStore.insertValue([section, root.length], templates[section] ?? {});
    allowNextRoute();
    void router.push({ name: "item", params: { section, itemId: String(root.length - 1) } });
    return;
  }
  if (["rewrite", "script"].includes(section) && root === undefined) {
    const template = section === "rewrite"
      ? { name: "新改写", enabled: true, match: "", replacement: "" }
      : { name: "新脚本", enabled: true, type: "generic", script: "" };
    appStore.setValue([section], []);
    appStore.insertValue([section, 0], template);
    allowNextRoute();
    void router.push({ name: "item", params: { section, itemId: "0" } });
    return;
  }
  if (section === "proxy-providers" || section === "rule-providers") {
    const name = await promptDialog({
      title: section === "rule-providers" ? "新增远程规则集" : "新增远程代理集",
      inputLabel: "名称",
      placeholder: "请输入唯一名称",
    });
    if (!name || (root && Object.prototype.hasOwnProperty.call(root, name))) return;
    const template =
      section === "rule-providers"
        ? { type: "http", behavior: "classical", url: "", path: `./ruleset/${name}.yaml`, interval: 86400 }
        : { type: "http", url: "", path: `./proxy_provider/${name}.yaml`, interval: 86400 };
    appStore.setValue([section, name], template);
    allowNextRoute();
    void router.push({ name: "item", params: { section, itemId: name } });
    return;
  }
  const parentPath = section === "dns" ? ["dns"] : [];
  const parent =
    section === "dns"
      ? ((appStore.document.dns ?? {}) as Record<string, unknown>)
      : appStore.document;
  const key = await promptDialog({
    title: section === "dns" ? "新增 DNS 字段" : "新增高级字段",
    inputLabel: "字段名称",
    placeholder: "例如：bind-address",
  });
  if (!key || Object.prototype.hasOwnProperty.call(parent, key)) return;
  appStore.setValue([...parentPath, key], "");
  allowNextRoute();
  void router.push({ name: "item", params: { section, itemId: key } });
}

function startDrag(row: Row) {
  if (!row.movable || !canDrag.value || row.index === undefined) return;
  dragFrom.value = row.index;
  suppressOpen.value = true;
}

function dropOn(row: Row) {
  if (dragFrom.value === null || row.index === undefined || dragFrom.value === row.index) {
    dragFrom.value = null;
    dragOver.value = null;
    return;
  }
  appStore.moveValue([sectionKey.value], dragFrom.value, row.index);
  appStore.notify(`已移动到第 ${row.index + 1} 位`);
  dragFrom.value = null;
  dragOver.value = null;
  window.setTimeout(() => { suppressOpen.value = false; }, 120);
}

function endDrag() {
  dragFrom.value = null;
  dragOver.value = null;
  window.setTimeout(() => { suppressOpen.value = false; }, 120);
}

async function closeSection() {
  await requestDraftTransition(
    async () => {
      await router.push("/editor");
    },
    "可视化编辑器",
    "close",
  );
}
</script>

<template>
  <div class="page-width editor-workspace">
    <EditorTopBar
      :title="catalog[sectionKey]?.title ?? '其他设置'"
      :show-add="!isSettingsSection"
      :show-save="isSettingsSection"
      close-label="返回"
      @close="closeSection"
      @add="addItem"
    />

    <GeneralSettingsEditor v-if="sectionKey === 'general'" />
    <DnsSettingsEditor v-else-if="sectionKey === 'dns'" />

    <template v-else>
    <p v-if="catalog[sectionKey]?.description" class="editor-section-description">
      {{ catalog[sectionKey]?.description }}
    </p>
    <div class="mb-3 flex gap-2">
      <label class="search-field">
        <Search :size="17" />
        <input v-model="search" type="search" placeholder="搜索名称、类型或参数" />
      </label>
      <label class="filter-button" aria-label="筛选">
        <Filter :size="17" />
        <select v-model="selectedFilter">
          <option v-for="option in filterOptions" :key="option">{{ option }}</option>
        </select>
      </label>
    </div>
    <p class="mb-4 text-xs text-[var(--text-muted)]">
      {{
        sectionKey === "rules"
          ? `共 ${rows.length} 条规则`
          : search || selectedFilter !== "全部"
            ? `显示 ${rows.length} 项 · 共 ${allRows.length} 项`
            : `共 ${allRows.length} 项`
      }}
    </p>

    <div v-if="rows.length" class="ios-card overflow-hidden">
      <article
        v-for="row in rows"
        :key="row.id"
        class="entity-row entity-row-clickable"
        :class="{
          'rule-entity-row': sectionKey === 'rules',
          'entity-row-dragging': dragFrom === row.index,
          'entity-row-drag-target': dragOver === row.index && dragFrom !== row.index,
        }"
        @dragover.prevent="dragOver = row.index ?? null"
        @drop.prevent="dropOn(row)"
        @click="openItem(row)"
      >
        <template v-if="sectionKey === 'proxy-groups'">
          <button
            class="drag-handle"
            :class="{ 'drag-handle-disabled': !canDrag }"
            :draggable="canDrag"
            aria-label="拖动调整策略组位置"
            @click.stop
            @dragstart.stop="startDrag(row)"
            @dragend.stop="endDrag"
          >
            <GripVertical :size="18" />
          </button>
          <ProxyGroupIcon :src="row.icon" :name="row.title" />
          <div class="min-w-0 flex-1">
            <h3 class="truncate policy-row-name">{{ row.title }}</h3>
            <p class="policy-row-type">{{ row.typeLabel }}</p>
          </div>
          <ChevronRight :size="19" class="text-[var(--text-faint)]" />
        </template>

        <template v-else-if="sectionKey === 'rules'">
          <button
            class="drag-handle"
            :class="{ 'drag-handle-disabled': !canDrag }"
            :draggable="canDrag"
            aria-label="拖动调整规则位置"
            @click.stop
            @dragstart.stop="startDrag(row)"
            @dragend.stop="endDrag"
          >
            <GripVertical :size="18" />
          </button>
          <div class="min-w-0 flex-1">
            <div class="rule-row-type">{{ row.badge }}</div>
            <div class="rule-row-content">{{ row.ruleContent }}</div>
          </div>
          <div class="rule-row-target">{{ row.ruleTarget }}</div>
          <ChevronRight :size="19" class="text-[var(--text-faint)]" />
        </template>

        <template v-else>
          <button
            v-if="row.movable"
            class="drag-handle"
            :class="{ 'drag-handle-disabled': !canDrag }"
            :draggable="canDrag"
            :aria-label="`拖动调整${catalog[sectionKey]?.title ?? '项目'}位置`"
            @click.stop
            @dragstart.stop="startDrag(row)"
            @dragend.stop="endDrag"
          >
            <GripVertical :size="18" />
          </button>
          <ProxyGroupIcon
            v-if="sectionKey === 'proxies'"
            :src="row.icon"
            :name="row.title"
          />
          <span v-else-if="sectionIcons[sectionKey]" class="entity-kind-icon">
            <component :is="sectionIcons[sectionKey]" :size="18" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span v-if="row.badge" class="type-badge">{{ row.badge }}</span>
              <h3 class="truncate text-[15px] font-semibold">{{ row.title }}</h3>
            </div>
            <p v-if="row.subtitle" class="mt-1 truncate text-xs text-[var(--text-muted)]">{{ row.subtitle }}</p>
          </div>
          <span v-if="row.value" class="max-w-28 truncate text-sm text-[var(--text-muted)]">{{ row.value }}</span>
          <ChevronRight :size="17" class="text-[var(--text-faint)]" />
        </template>
      </article>
    </div>

    <div v-else class="empty-card">
      <div class="empty-icon"><Plus :size="24" /></div>
      <h3 class="mt-4 font-semibold">暂无匹配项目</h3>
      <p class="mt-1 text-sm text-[var(--text-muted)]">调整搜索条件或点击右上角添加。</p>
    </div>
    </template>
  </div>
</template>
