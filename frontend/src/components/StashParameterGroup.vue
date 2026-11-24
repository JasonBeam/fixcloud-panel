<script setup lang="ts">
defineProps<{
  title: string;
  help?: string;
}>();
</script>

<template>
  <section>
    <h3 class="stash-section-title">{{ title }}</h3>
    <div class="stash-group-card">
      <slot />
    </div>
    <p v-if="help" class="stash-field-help">{{ help }}</p>
  </section>
</template>
