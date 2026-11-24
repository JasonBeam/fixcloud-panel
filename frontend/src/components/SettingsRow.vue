<script setup lang="ts">
import { ChevronRight } from "lucide-vue-next";

withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    value?: string | number;
    iconClass?: string;
    to?: string;
  }>(),
  {
    subtitle: "",
    value: "",
    iconClass: "bg-slate-500",
    to: "",
  },
);
</script>

<template>
  <component
    :is="to ? 'RouterLink' : 'div'"
    :to="to || undefined"
    class="settings-row"
  >
    <div class="flex min-w-0 items-center gap-3">
      <div class="row-icon" :class="iconClass">
        <slot name="icon" />
      </div>
      <div class="min-w-0">
        <div class="truncate text-[15px] font-semibold">{{ title }}</div>
        <div v-if="subtitle" class="mt-0.5 truncate text-xs text-[var(--text-muted)]">{{ subtitle }}</div>
      </div>
    </div>
    <div class="ml-3 flex shrink-0 items-center gap-1.5 text-sm text-[var(--text-muted)]">
      <span v-if="value !== ''">{{ value }}</span>
      <ChevronRight v-if="to" :size="17" />
    </div>
  </component>
</template>

