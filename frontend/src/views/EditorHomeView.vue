<script setup lang="ts">
import {
  Braces,
  Boxes,
  Code2,
  FileCode2,
  Globe2,
  Network,
  PanelsTopLeft,
  Route,
  ScrollText,
  ServerCog,
} from "lucide-vue-next";
import { computed } from "vue";

import GroupCard from "@/components/GroupCard.vue";
import SettingsRow from "@/components/SettingsRow.vue";
import { useAppStore } from "@/stores/app";

const appStore = useAppStore();
const currentFileName = computed(
  () => appStore.file.path.split("/").pop() || "未选择 YAML",
);
const currentSource = computed(() =>
  appStore.file.sourceType === "upload" ? "已上传文件" : appStore.file.sourceName,
);
</script>

<template>
  <div class="page-width editor-home">
    <div class="editor-home-intro mb-6">
      <p class="eyebrow">{{ currentFileName }} · {{ currentSource }}</p>
      <h2 class="page-title">可视化编辑器</h2>
      <p class="page-subtitle">所有项目都通过结构化表单管理，未知字段不会被删除。</p>
    </div>
    <div class="editor-home-mobile-hero">
      <p class="eyebrow">VISUAL EDITOR / 01</p>
      <h2>配置，<br />一目了然。</h2>
      <p>选择分类，进入结构化参数编辑。</p>
    </div>

    <div class="desktop-two-column">
      <div>
        <GroupCard title="通用" description="日志级别、端口、运行模式与 DNS 设置。">
          <SettingsRow title="通用设置" :value="appStore.counts.general" to="/editor/general" icon-class="bg-slate-500">
            <template #icon><PanelsTopLeft :size="18" /></template>
          </SettingsRow>
          <SettingsRow title="DNS 服务器" :value="appStore.counts.dns" to="/editor/dns" icon-class="bg-slate-500">
            <template #icon><Globe2 :size="18" /></template>
          </SettingsRow>
        </GroupCard>

        <GroupCard title="代理" description="本地代理、策略组和远程代理集。">
          <SettingsRow title="本地代理" :value="appStore.counts.proxies" to="/editor/proxies" icon-class="bg-blue-500">
            <template #icon><ServerCog :size="18" /></template>
          </SettingsRow>
          <SettingsRow title="策略组" :value="appStore.counts.proxyGroups" to="/editor/proxy-groups" icon-class="bg-cyan-500">
            <template #icon><Network :size="18" /></template>
          </SettingsRow>
          <SettingsRow title="远程代理集" :value="appStore.counts.proxyProviders" to="/editor/proxy-providers" icon-class="bg-teal-500">
            <template #icon><Boxes :size="18" /></template>
          </SettingsRow>
        </GroupCard>
      </div>

      <div>
        <GroupCard title="规则" description="按顺序匹配连接，并支持 RULE-SET 与 GEOIP。">
          <SettingsRow title="规则" :value="appStore.counts.rules" to="/editor/rules" icon-class="bg-violet-500">
            <template #icon><Route :size="18" /></template>
          </SettingsRow>
          <SettingsRow title="远程规则集" :value="appStore.counts.ruleProviders" to="/editor/rule-providers" icon-class="bg-purple-500">
            <template #icon><ScrollText :size="18" /></template>
          </SettingsRow>
        </GroupCard>

        <GroupCard title="扩展">
          <SettingsRow title="HTTP 改写" :value="appStore.counts.rewrite" to="/editor/rewrite" icon-class="bg-amber-500">
            <template #icon><FileCode2 :size="18" /></template>
          </SettingsRow>
          <SettingsRow title="脚本" :value="appStore.counts.script" to="/editor/script" icon-class="bg-indigo-500">
            <template #icon><Code2 :size="18" /></template>
          </SettingsRow>
          <SettingsRow title="其他设置" :value="appStore.counts.other" to="/editor/other" icon-class="bg-zinc-500">
            <template #icon><Braces :size="18" /></template>
          </SettingsRow>
        </GroupCard>

        <GroupCard title="选项" description="复杂嵌套和未知字段的高级修改入口。">
          <SettingsRow title="YAML 修改" subtitle="格式检查 · 完整 Diff" to="/editor/advanced-yaml" icon-class="bg-slate-700">
            <template #icon><Code2 :size="18" /></template>
          </SettingsRow>
        </GroupCard>
      </div>
    </div>
  </div>
</template>
