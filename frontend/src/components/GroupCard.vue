<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <section class="mb-6">
    <div class="mb-2 px-1">
      <h2 class="text-sm font-semibold text-[var(--text-muted)]">{{ title }}</h2>
      <p v-if="description" class="mt-1 text-xs leading-5 text-[var(--text-faint)]">
        {{ description }}
      </p>
    </div>
    <div class="ios-card">
      <slot />
    </div>
  </section>
</template>

