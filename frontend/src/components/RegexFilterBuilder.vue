<script setup lang="ts">
import { Check, Sparkles, X } from "lucide-vue-next";
import { computed, ref, watch } from "vue";

import {
  buildProxyNameFilter,
  describeProxyNameFilter,
  REGION_PRESETS,
} from "@/utils/regexPreset";

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  apply: [value: string];
}>();

const regionIds = ref<string[]>([]);
const requiredKeywords = ref("");
const excludedKeywords = ref("");
const requireEveryKeyword = ref(false);

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    regionIds.value = [];
    requiredKeywords.value = "";
    excludedKeywords.value = "";
    requireEveryKeyword.value = false;
  },
);

const input = computed(() => ({
  regionIds: regionIds.value,
  requiredKeywords: requiredKeywords.value,
  excludedKeywords: excludedKeywords.value,
  requireEveryKeyword: requireEveryKeyword.value,
}));
const generated = computed(() => buildProxyNameFilter(input.value));
const description = computed(() => describeProxyNameFilter(input.value));

function toggleRegion(id: string) {
  const index = regionIds.value.indexOf(id);
  if (index >= 0) regionIds.value.splice(index, 1);
  else regionIds.value.push(id);
}

function useQuickPreset(region: string[], keyword: string) {
  regionIds.value = region;
  requiredKeywords.value = keyword;
  excludedKeywords.value = "";
  requireEveryKeyword.value = false;
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="regex-builder-layer" @click.self="emit('close')">
      <section class="regex-builder-panel" role="dialog" aria-modal="true" aria-label="懒人筛选">
        <header class="regex-builder-header">
          <button type="button" aria-label="关闭" @click="emit('close')"><X :size="21" /></button>
          <div>
            <h2>懒人筛选</h2>
            <small>组合地区和节点名称条件</small>
          </div>
          <button
            type="button"
            class="regex-builder-apply"
            :disabled="!generated"
            @click="emit('apply', generated)"
          >
            <Check :size="15" />
            使用
          </button>
        </header>

        <div class="regex-builder-content">
          <section>
            <h3>快速选择</h3>
            <div class="regex-quick-grid">
              <button type="button" @click="useQuickPreset([], 'GPT')">所有 GPT 节点</button>
              <button type="button" @click="useQuickPreset(['hk', 'tw'], 'GPT')">香港 / 台湾 + GPT</button>
              <button type="button" @click="useQuickPreset(['jp', 'sg'], 'GPT')">日本 / 新加坡 + GPT</button>
              <button type="button" @click="useQuickPreset(['us'], 'GPT')">美国 + GPT</button>
            </div>
          </section>

          <section>
            <h3>节点地区（可多选）</h3>
            <div class="regex-region-chips">
              <button
                v-for="region in REGION_PRESETS"
                :key="region.id"
                type="button"
                :class="{ active: regionIds.includes(region.id) }"
                @click="toggleRegion(region.id)"
              >
                {{ region.label }}
              </button>
            </div>
          </section>

          <section>
            <h3>名称条件</h3>
            <div class="regex-builder-card">
              <label>
                <span>必须包含</span>
                <input v-model="requiredKeywords" placeholder="例如 GPT，多个词用逗号分隔" />
              </label>
              <label class="regex-mode-row">
                <span>多个关键词</span>
                <select v-model="requireEveryKeyword">
                  <option :value="false">包含任意一个</option>
                  <option :value="true">必须全部包含</option>
                </select>
              </label>
              <label>
                <span>需要排除</span>
                <input v-model="excludedKeywords" placeholder="可选，例如 家宽、倍率" />
              </label>
            </div>
          </section>

          <section>
            <h3>生成结果</h3>
            <div class="regex-preview-card">
              <div>
                <Sparkles :size="17" />
                <strong>{{ description }}</strong>
              </div>
              <code>{{ generated || "选择条件后将在这里生成正则表达式" }}</code>
            </div>
          </section>
        </div>
      </section>
    </div>
  </Teleport>
</template>
