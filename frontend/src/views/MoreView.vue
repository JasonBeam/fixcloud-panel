<script setup lang="ts">
import { ChevronRight, Clock3, Network, Settings, Wifi } from "lucide-vue-next";
import { computed } from "vue";

import { useAppStore } from "@/stores/app";

const appStore = useAppStore();
const fileName = computed(() => appStore.file.path.split("/").pop() || "未选择 YAML");

const links = [
  { to: "/subscription-nodes", title: "订阅节点", subtitle: "查看机场节点", icon: Network },
  { to: "/history", title: "配置历史", subtitle: "查看与恢复", icon: Clock3 },
  { to: "/settings", title: "系统设置", subtitle: "连接与操作日志", icon: Settings },
];
</script>

<template>
  <div class="page-width more-page">
    <p class="eyebrow">CONTROL / 04</p>
    <h2 class="page-title">工具与状态。</h2>
    <p class="section-title">配置</p>
    <div class="ios-card more-links">
      <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="more-link">
        <component :is="link.icon" :size="19" :stroke-width="1.7" />
        <span><strong>{{ link.title }}</strong><small>{{ link.subtitle }}</small></span>
        <ChevronRight :size="18" />
      </RouterLink>
    </div>
    <p class="section-title">当前状态</p>
    <div class="ios-card more-status">
      <div><span>后端连接</span><strong><Wifi :size="15" />{{ appStore.backendReachable ? "已连接" : "未连接" }}</strong></div>
      <div><span>YAML 文件</span><strong>{{ fileName }}</strong></div>
      <div><span>访问方式</span><strong>内网访问</strong></div>
    </div>
  </div>
</template>
