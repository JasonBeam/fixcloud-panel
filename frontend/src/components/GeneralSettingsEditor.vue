<script setup lang="ts">
import StashParameterGroup from "@/components/StashParameterGroup.vue";
import StashParameterRow from "@/components/StashParameterRow.vue";
import { useAppStore } from "@/stores/app";

const appStore = useAppStore();

function value(key: string) {
  return appStore.document[key];
}

function set(key: string, next: unknown) {
  appStore.setValue([key], next);
}
</script>

<template>
  <div class="stash-form">
    <StashParameterGroup title="监听端口">
      <StashParameterRow label="HTTP 端口" :model-value="value('port')" kind="number" @update:model-value="set('port', $event)" />
      <StashParameterRow label="混合端口" :model-value="value('mixed-port')" kind="number" @update:model-value="set('mixed-port', $event)" />
      <StashParameterRow label="SOCKS 端口" :model-value="value('socks-port')" kind="number" @update:model-value="set('socks-port', $event)" />
    </StashParameterGroup>

    <StashParameterGroup title="局域网">
      <StashParameterRow
        label="允许局域网"
        description="允许其他内网设备连接代理端口"
        :model-value="value('allow-lan')"
        kind="toggle"
        @update:model-value="set('allow-lan', $event)"
      />
      <StashParameterRow
        label="绑定地址"
        :model-value="value('bind-address')"
        placeholder="*"
        @update:model-value="set('bind-address', $event)"
      />
      <StashParameterRow
        label="启用 IPv6"
        :model-value="value('ipv6')"
        kind="toggle"
        @update:model-value="set('ipv6', $event)"
      />
    </StashParameterGroup>

    <StashParameterGroup title="运行设置">
      <StashParameterRow
        label="运行模式"
        :model-value="value('mode')"
        kind="select"
        :options="[
          { value: 'rule', label: 'Rule' },
          { value: 'global', label: 'Global' },
          { value: 'direct', label: 'Direct' },
        ]"
        @update:model-value="set('mode', $event)"
      />
      <StashParameterRow
        label="日志级别"
        :model-value="value('log-level')"
        kind="select"
        :options="['silent', 'error', 'warning', 'info', 'debug']"
        @update:model-value="set('log-level', $event)"
      />
    </StashParameterGroup>

    <StashParameterGroup title="外部控制">
      <StashParameterRow
        label="控制器地址"
        :model-value="value('external-controller')"
        placeholder="0.0.0.0:9090"
        @update:model-value="set('external-controller', $event)"
      />
      <StashParameterRow
        label="控制器密钥"
        :model-value="value('secret')"
        kind="password"
        @update:model-value="set('secret', $event)"
      />
    </StashParameterGroup>
  </div>
</template>
