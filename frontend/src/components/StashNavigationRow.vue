<script setup lang="ts">
import { ChevronRight } from "lucide-vue-next";

defineProps<{
  label: string;
  description?: string;
  value?: string | number;
}>();

defineEmits<{
  open: [];
}>();
</script>

<template>
  <button type="button" class="stash-navigation-row" @click="$emit('open')">
    <span>
      <strong>{{ label }}</strong>
      <small v-if="description">{{ description }}</small>
    </span>
    <b v-if="value !== undefined">{{ value }}</b>
    <ChevronRight :size="18" />
  </button>
</template>
