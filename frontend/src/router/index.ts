import { createRouter, createWebHashHistory } from "vue-router";

import EditorHomeView from "@/views/EditorHomeView.vue";
import FilesView from "@/views/FilesView.vue";
import HistoryView from "@/views/HistoryView.vue";
import ItemEditorView from "@/views/ItemEditorView.vue";
import MoreView from "@/views/MoreView.vue";
import SectionView from "@/views/SectionView.vue";
import SettingsView from "@/views/SettingsView.vue";
import SourcesView from "@/views/SourcesView.vue";
import SubscriptionNodesView from "@/views/SubscriptionNodesView.vue";
import UsageView from "@/views/UsageView.vue";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", redirect: "/sources" },
    { path: "/sources", name: "sources", component: SourcesView, meta: { title: "文件来源" } },
    { path: "/files", name: "files", component: FilesView, meta: { title: "文件浏览器" } },
    { path: "/editor", name: "editor", component: EditorHomeView, meta: { title: "可视化编辑器" } },
    { path: "/editor/advanced-yaml", name: "advanced-yaml", component: () => import("@/views/AdvancedYamlView.vue"), meta: { title: "高级 YAML 修改" } },
    {
      path: "/editor/:section",
      name: "section",
      component: SectionView,
      meta: { title: "配置项目" },
    },
    {
      path: "/editor/:section/item/:itemId",
      name: "item",
      component: ItemEditorView,
      meta: { title: "参数编辑" },
    },
    { path: "/usage", name: "usage", component: UsageView, meta: { title: "机场流量" } },
    { path: "/more", name: "more", component: MoreView, meta: { title: "更多" } },
    { path: "/subscription-nodes", name: "subscription-nodes", component: SubscriptionNodesView, meta: { title: "订阅节点" } },
    { path: "/history", name: "history", component: HistoryView, meta: { title: "配置历史" } },
    { path: "/settings", name: "settings", component: SettingsView, meta: { title: "系统设置" } },
  ],
});

export default router;
