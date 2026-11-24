<script setup lang="ts">
import StashParameterGroup from "@/components/StashParameterGroup.vue";
import StashParameterRow from "@/components/StashParameterRow.vue";
import { useAppStore } from "@/stores/app";

const props = defineProps<{
  label: string;
  value: string | number | boolean;
  path: Array<string | number>;
  multiline?: boolean;
}>();

const appStore = useAppStore();
</script>

<template>
  <div class="stash-form">
    <StashParameterGroup title="参数内容">
      <StashParameterRow
        :label="label"
        :model-value="value"
        :kind="multiline ? 'textarea' : typeof value === 'boolean' ? 'toggle' : typeof value === 'number' ? 'number' : 'text'"
        @update:model-value="appStore.setValue(path, $event)"
      />
    </StashParameterGroup>
  </div>
</template>
