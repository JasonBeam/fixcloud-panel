<script setup lang="ts">
import { ExternalLink, Eye, EyeOff } from "lucide-vue-next";
import { computed, ref } from "vue";

type Option = string | { value: string; label: string };

const props = withDefaults(
  defineProps<{
    label: string;
    description?: string;
    modelValue: unknown;
    kind?: "text" | "number" | "password" | "select" | "toggle" | "textarea";
    options?: Option[];
    suggestions?: string[];
    placeholder?: string;
    unit?: string;
    readonly?: boolean;
    openUrl?: boolean;
  }>(),
  {
    description: "",
    kind: "text",
    options: () => [],
    suggestions: () => [],
    placeholder: "",
    unit: "",
    readonly: false,
    openUrl: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: unknown];
}>();

const showSecret = ref(false);
const datalistId = `stash-options-${Math.random().toString(36).slice(2)}`;
const normalizedOptions = computed(() =>
  props.options.map((option) =>
    typeof option === "string" ? { value: option, label: option } : option,
  ),
);

function update(event: Event) {
  const target = event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
  if (props.kind === "toggle") {
    emit("update:modelValue", (target as HTMLInputElement).checked);
  } else if (props.kind === "number") {
    emit("update:modelValue", target.value === "" ? "" : Number(target.value));
  } else {
    emit("update:modelValue", target.value);
  }
}
</script>

<template>
  <label v-if="kind === 'toggle'" class="stash-toggle-row">
    <span>
      <strong>{{ label }}</strong>
      <small v-if="description">{{ description }}</small>
    </span>
    <input
      type="checkbox"
      :checked="Boolean(modelValue)"
      :disabled="readonly"
      @change="update"
    />
    <i class="toggle-track" />
  </label>

  <label
    v-else
    class="stash-form-row"
    :class="{ 'stash-form-row-stacked': kind === 'textarea' }"
  >
    <span>
      {{ label }}
      <small v-if="description">{{ description }}</small>
    </span>

    <select
      v-if="kind === 'select'"
      :value="String(modelValue ?? '')"
      :disabled="readonly"
      @change="update"
    >
      <option v-for="option in normalizedOptions" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>

    <textarea
      v-else-if="kind === 'textarea'"
      :value="String(modelValue ?? '')"
      :placeholder="placeholder"
      :readonly="readonly"
      rows="9"
      spellcheck="false"
      @input="update"
    />

    <div v-else-if="kind === 'password'" class="password-field">
      <input
        :type="showSecret ? 'text' : 'password'"
        :value="String(modelValue ?? '')"
        :placeholder="placeholder"
        :readonly="readonly"
        autocomplete="new-password"
        @input="update"
      />
      <button
        type="button"
        :aria-label="showSecret ? '隐藏敏感值' : '显示敏感值'"
        @click.prevent="showSecret = !showSecret"
      >
        <EyeOff v-if="showSecret" :size="17" />
        <Eye v-else :size="17" />
      </button>
    </div>

    <span v-else class="stash-value-with-unit">
      <input
        :type="kind === 'number' ? 'number' : 'text'"
        :value="String(modelValue ?? '')"
        :placeholder="placeholder"
        :list="suggestions.length ? datalistId : undefined"
        :readonly="readonly"
        autocomplete="off"
        @input="update"
      />
      <small v-if="unit">{{ unit }}</small>
      <a
        v-if="openUrl && String(modelValue ?? '').startsWith('http')"
        :href="String(modelValue)"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="打开链接"
      >
        <ExternalLink :size="15" />
      </a>
    </span>
    <datalist v-if="suggestions.length" :id="datalistId">
      <option v-for="suggestion in suggestions" :key="suggestion" :value="suggestion" />
    </datalist>
  </label>
</template>
