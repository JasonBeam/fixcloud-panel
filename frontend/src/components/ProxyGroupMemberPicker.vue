<script setup lang="ts">
import {
  Check,
  ChevronLeft,
  GripVertical,
  Link2,
  Minus,
  Plus,
  Search,
} from "lucide-vue-next";
import { computed, ref, watch } from "vue";

import type {
  ProxyGroupMemberKind,
  ProxyGroupMemberOption,
} from "@/utils/proxyGroup";

const props = defineProps<{
  open: boolean;
  kind: ProxyGroupMemberKind;
  title: string;
  modelValue: string[];
  options: ProxyGroupMemberOption[];
}>();

const emit = defineEmits<{
  close: [];
  save: [value: string[]];
}>();

const draft = ref<string[]>([]);
const query = ref("");
const customUrl = ref("");
const dragging = ref<{ value: string; from: "included" | "available"; index?: number } | null>(null);
const dropIndex = ref<number | null>(null);

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    draft.value = [...props.modelValue];
    query.value = "";
    customUrl.value = "";
    dragging.value = null;
    dropIndex.value = null;
  },
  { immediate: true },
);

const optionMap = computed(() =>
  new Map(props.options.map((option) => [option.value, option])),
);
const available = computed(() => {
  const selected = new Set(draft.value);
  const needle = query.value.trim().toLowerCase();
  return props.options.filter((option) => {
    if (selected.has(option.value)) return false;
    if (!needle) return true;
    return `${option.title} ${option.subtitle} ${option.category}`.toLowerCase().includes(needle);
  });
});

function optionFor(value: string): ProxyGroupMemberOption {
  return optionMap.value.get(value) ?? {
    value,
    title: value,
    subtitle: props.kind === "include-from-url" ? value : "原配置中的引用",
    category: props.kind === "include-from-url" ? "URL" : "节点",
  };
}

function add(value: string, index = draft.value.length) {
  if (!value || draft.value.includes(value)) return;
  draft.value.splice(index, 0, value);
}

function remove(index: number) {
  draft.value.splice(index, 1);
}

function addCustomUrl() {
  const value = customUrl.value.trim();
  if (!/^https?:\/\//i.test(value)) return;
  add(value);
  customUrl.value = "";
}

function startDrag(value: string, from: "included" | "available", index?: number) {
  dragging.value = { value, from, index };
}

function dropAt(index: number) {
  const item = dragging.value;
  if (!item) return;
  if (item.from === "included" && item.index !== undefined) {
    const [value] = draft.value.splice(item.index, 1);
    const adjusted = item.index < index ? index - 1 : index;
    draft.value.splice(Math.max(0, adjusted), 0, value);
  } else {
    add(item.value, index);
  }
  dragging.value = null;
  dropIndex.value = null;
}

function save() {
  emit("save", [...draft.value]);
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="member-picker-layer" @click.self="emit('close')">
      <section class="member-picker-panel" role="dialog" aria-modal="true" :aria-label="title">
        <header class="member-picker-header">
          <button type="button" class="member-picker-round-button" aria-label="返回" @click="emit('close')">
            <ChevronLeft :size="23" />
          </button>
          <div>
            <h2>{{ title }}</h2>
            <small>{{ draft.length }} 项已包含</small>
          </div>
          <button type="button" class="member-picker-save" @click="save">
            <Check :size="16" />
            完成
          </button>
        </header>

        <div class="member-picker-scroll">
          <div v-if="kind !== 'include-from-url'" class="member-picker-search">
            <Search :size="17" />
            <input v-model="query" placeholder="搜索名称、类型或地址" autocomplete="off" />
          </div>

          <section class="member-picker-section">
            <h3>已包含</h3>
            <div
              class="member-picker-list member-picker-dropzone"
              :class="{ 'member-picker-dropzone-active': dragging }"
              @dragover.prevent="dropIndex = draft.length"
              @drop.prevent="dropAt(draft.length)"
            >
              <div
                v-for="(value, index) in draft"
                :key="value"
                class="member-picker-row member-picker-row-included"
                :class="{ 'member-picker-drop-target': dropIndex === index }"
                draggable="true"
                @dragstart="startDrag(value, 'included', index)"
                @dragend="dragging = null; dropIndex = null"
                @dragover.prevent="dropIndex = index"
                @drop.prevent.stop="dropAt(index)"
              >
                <button type="button" class="member-remove-button" :aria-label="`移除 ${value}`" @click="remove(index)">
                  <Minus :size="17" />
                </button>
                <div class="member-picker-copy">
                  <strong>{{ optionFor(value).title }}</strong>
                  <small>{{ optionFor(value).subtitle }}</small>
                </div>
                <span class="member-category">{{ optionFor(value).category }}</span>
                <GripVertical class="member-drag-handle" :size="20" />
              </div>
              <div v-if="!draft.length" class="member-picker-empty">
                尚未包含项目，可从下方添加或拖入这里。
              </div>
            </div>
          </section>

          <section v-if="kind === 'include-from-url'" class="member-picker-section">
            <h3>添加 URL</h3>
            <div class="member-url-entry">
              <Link2 :size="17" />
              <input
                v-model="customUrl"
                placeholder="https://example.com/proxies.yaml"
                @keyup.enter="addCustomUrl"
              />
              <button type="button" :disabled="!/^https?:\/\//i.test(customUrl.trim())" @click="addCustomUrl">
                添加
              </button>
            </div>
            <p class="member-picker-note">
              此项用于兼容支持 URL 成员来源的客户端；Mihomo 官方策略组字段不保证执行它。
            </p>
          </section>

          <section v-else class="member-picker-section">
            <h3>可用项目</h3>
            <div class="member-picker-list">
              <div
                v-for="option in available"
                :key="option.value"
                class="member-picker-row"
                draggable="true"
                @dragstart="startDrag(option.value, 'available')"
                @dragend="dragging = null; dropIndex = null"
              >
                <button type="button" class="member-add-button" :aria-label="`添加 ${option.title}`" @click="add(option.value)">
                  <Plus :size="17" />
                </button>
                <div class="member-picker-copy">
                  <strong>{{ option.title }}</strong>
                  <small>{{ option.subtitle }}</small>
                </div>
                <span class="member-category">{{ option.category }}</span>
                <GripVertical class="member-drag-handle" :size="20" />
              </div>
              <div v-if="!available.length" class="member-picker-empty">
                {{ query ? "没有符合搜索条件的项目。" : "没有其他可添加项目。" }}
              </div>
            </div>
          </section>
        </div>
      </section>
    </div>
  </Teleport>
</template>
