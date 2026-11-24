<script setup lang="ts">
import { Waypoints } from "lucide-vue-next";
import { computed, ref, watch } from "vue";
import { useAppStore } from "@/stores/app";

const props = defineProps<{
  src?: string;
  name: string;
}>();

const failed = ref(false);
const loaded = ref(false);
const appStore = useAppStore();
const cachedSrc = computed(() => {
  if (!props.src) return "";
  const query = new URLSearchParams({
    url: props.src,
    sourceId: appStore.file.sourceId,
    path: appStore.file.path,
  });
  return `/api/icons/cache?${query}`;
});

watch(
  () => props.src,
  () => {
    failed.value = false;
    loaded.value = false;
  },
);
</script>

<template>
  <span class="proxy-group-icon" :title="name">
    <Waypoints v-if="!loaded || failed || !src" :size="23" aria-hidden="true" />
    <img
      v-if="src && !failed"
      :src="cachedSrc"
      :alt="`${name} 图标`"
      loading="lazy"
      :class="{ 'opacity-0': !loaded }"
      @load="loaded = true"
      @error="failed = true"
    />
  </span>
</template>
