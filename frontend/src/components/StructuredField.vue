<script setup lang="ts">
import { ArrowDown, ArrowUp, Eye, EyeOff, Plus, Trash2 } from "lucide-vue-next";
import { computed, ref } from "vue";

import { useAppStore } from "@/stores/app";
import { promptDialog } from "@/composables/appDialog";

defineOptions({ name: "StructuredField" });

const props = defineProps<{
  label: string;
  value: unknown;
  path: Array<string | number>;
}>();

const appStore = useAppStore();
const showSecret = ref(false);

const isSecret = computed(() =>
  /(password|passwd|secret|token|authorization|api[-_]?key)/i.test(props.label),
);
const isBoolean = computed(() => typeof props.value === "boolean");
const isNumber = computed(() => typeof props.value === "number");
const isArray = computed(() => Array.isArray(props.value));
const isObject = computed(
  () => props.value !== null && typeof props.value === "object" && !Array.isArray(props.value),
);
const selectOptions = computed(() => {
  if (props.label === "mode") return ["rule", "global", "direct"];
  if (props.label === "log-level") return ["silent", "error", "warning", "info", "debug"];
  if (props.label === "type") {
    return [
      "select",
      "url-test",
      "fallback",
      "load-balance",
      "ss",
      "vmess",
      "vless",
      "trojan",
      "socks5",
      "hysteria",
      "hysteria2",
      "tuic",
      "http",
      "file",
    ];
  }
  if (props.label === "behavior") return ["domain", "ipcidr", "classical"];
  if (props.label === "enhanced-mode") return ["fake-ip", "redir-host"];
  return [];
});
const normalizedLabel = computed(() => {
  const tail = props.path[props.path.length - 1];
  return typeof tail === "number"
    ? String(props.path[props.path.length - 2] ?? props.label)
    : props.label;
});
const referenceOptions = computed(() => {
  if (normalizedLabel.value === "use") {
    const providers = appStore.document["proxy-providers"];
    return providers && typeof providers === "object" && !Array.isArray(providers)
      ? Object.keys(providers)
      : [];
  }
  if (normalizedLabel.value === "proxies" && props.path.includes("proxy-groups")) {
    const nodes = Array.isArray(appStore.document.proxies)
      ? appStore.document.proxies
          .map((item) => item && typeof item === "object" ? String((item as Record<string, unknown>).name ?? "") : "")
          .filter(Boolean)
      : [];
    const groups = Array.isArray(appStore.document["proxy-groups"])
      ? appStore.document["proxy-groups"]
          .map((item) => item && typeof item === "object" ? String((item as Record<string, unknown>).name ?? "") : "")
          .filter(Boolean)
      : [];
    return [...new Set([...nodes, ...groups, "DIRECT", "REJECT", "PASS"])];
  }
  return [];
});
const fieldDescription = computed(() => {
  const hints: Record<string, string> = {
    name: "列表中显示的唯一名称",
    type: "协议、策略组或 Provider 类型",
    server: "服务器域名或 IP 地址",
    port: "1–65535 的服务端口",
    password: "连接认证密码",
    cipher: "加密算法",
    tls: "启用 TLS 加密传输",
    udp: "允许 UDP 转发",
    url: "订阅或规则集下载地址",
    interval: "自动更新间隔，单位为秒",
    path: "Mihomo 本地缓存路径",
    proxies: "策略组引用的节点或其他策略组",
    use: "策略组引用的远程代理集",
    filter: "筛选节点名称的正则表达式",
    "include-all": "自动包含所有可用节点",
    behavior: "规则集内容格式",
    secret: "外部控制器认证密钥",
    "external-controller": "外部控制器监听地址",
  };
  return hints[normalizedLabel.value] ?? "";
});
const dataListId = computed(() => `ref-${props.path.map(String).join("-").replace(/[^a-zA-Z0-9_-]/g, "")}`);

function setScalar(event: Event) {
  const target = event.target as HTMLInputElement | HTMLSelectElement;
  let value: unknown = target.value;
  if (isNumber.value) value = Number(target.value);
  appStore.setValue(props.path, value);
}

function addArrayItem() {
  const items = props.value as unknown[];
  const template = items.length > 0 && typeof items[0] === "object" ? {} : "";
  appStore.insertValue([...props.path, items.length], template);
}

async function addMapField() {
  const key = await promptDialog({
    title: `为 ${props.label} 添加字段`,
    inputLabel: "字段名称",
    placeholder: "请输入 YAML 字段名",
  });
  if (!key || Object.prototype.hasOwnProperty.call(props.value, key)) return;
  appStore.setValue([...props.path, key], "");
}
</script>

<template>
  <section v-if="isObject" class="structured-group">
    <div class="structured-heading">
      <div>
        <div class="text-[15px] font-semibold">{{ label }}</div>
        <div class="mt-0.5 text-xs text-[var(--text-muted)]">{{ fieldDescription || "键值对" }}</div>
      </div>
      <button class="mini-action-button" aria-label="添加字段" @click="addMapField">
        <Plus :size="16" />
      </button>
    </div>
    <div class="structured-children">
      <StructuredField
        v-for="(child, childKey) in value as Record<string, unknown>"
        :key="String(childKey)"
        :label="String(childKey)"
        :value="child"
        :path="[...path, String(childKey)]"
      />
    </div>
  </section>

  <section v-else-if="isArray" class="structured-group">
    <div class="structured-heading">
      <div>
        <div class="text-[15px] font-semibold">{{ label }}</div>
        <div class="mt-0.5 text-xs text-[var(--text-muted)]">
          {{ (value as unknown[]).length }} 项 · 顺序将保留
        </div>
      </div>
      <button class="mini-action-button" aria-label="添加项目" @click="addArrayItem">
        <Plus :size="16" />
      </button>
    </div>
    <div class="structured-children">
      <div v-for="(child, index) in value as unknown[]" :key="index" class="array-editor-row">
        <div class="min-w-0 flex-1">
          <StructuredField
            :label="`${label} ${index + 1}`"
            :value="child"
            :path="[...path, index]"
          />
        </div>
        <div class="array-actions">
          <button
            aria-label="上移"
            :disabled="index === 0"
            @click="appStore.moveValue(path, index, index - 1)"
          >
            <ArrowUp :size="15" />
          </button>
          <button
            aria-label="下移"
            :disabled="index === (value as unknown[]).length - 1"
            @click="appStore.moveValue(path, index, index + 1)"
          >
            <ArrowDown :size="15" />
          </button>
          <button aria-label="删除" class="text-red-500" @click="appStore.deleteValue([...path, index])">
            <Trash2 :size="15" />
          </button>
        </div>
      </div>
    </div>
  </section>

  <label v-else-if="isBoolean" class="toggle-field">
    <div>
      <div class="text-[15px] font-semibold">{{ label }}</div>
      <div class="mt-0.5 text-xs text-[var(--text-muted)]">{{ fieldDescription || "开关" }}</div>
    </div>
    <input
      type="checkbox"
      :checked="Boolean(value)"
      @change="appStore.setValue(path, ($event.target as HTMLInputElement).checked)"
    />
    <span class="toggle-track" />
  </label>

  <label v-else class="form-field structured-scalar">
    <span>{{ label }}</span>
    <small v-if="fieldDescription" class="field-description">{{ fieldDescription }}</small>
    <select v-if="selectOptions.length" :value="String(value ?? '')" @change="setScalar">
      <option v-for="option in selectOptions" :key="option" :value="option">{{ option }}</option>
    </select>
    <div v-else-if="isSecret" class="password-field">
      <input
        :type="showSecret ? 'text' : 'password'"
        :value="String(value ?? '')"
        autocomplete="new-password"
        @input="setScalar"
      />
      <button type="button" :aria-label="showSecret ? '隐藏敏感值' : '显示敏感值'" @click="showSecret = !showSecret">
        <EyeOff v-if="showSecret" :size="17" />
        <Eye v-else :size="17" />
      </button>
    </div>
    <template v-else-if="referenceOptions.length">
      <input
        :list="dataListId"
        :value="String(value ?? '')"
        autocomplete="off"
        @input="setScalar"
      />
      <datalist :id="dataListId">
        <option v-for="option in referenceOptions" :key="option" :value="option" />
      </datalist>
    </template>
    <input
      v-else
      :type="isNumber ? 'number' : 'text'"
      :value="String(value ?? '')"
      @input="setScalar"
    />
  </label>
</template>
