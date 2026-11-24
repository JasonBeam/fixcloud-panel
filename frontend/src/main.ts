import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import {
  allowNextRoute,
  consumeRouteBypass,
  draftGuardState,
  requestDraftTransition,
} from "./composables/draftGuard";
import { useAppStore } from "./stores/app";
import "./style.css";
import "./visual-refresh.css";

const pinia = createPinia();
const appStore = useAppStore(pinia);

router.beforeEach((to, from) => {
  if (consumeRouteBypass()) return true;
  if (draftGuardState.busy) return true;
  if (
    appStore.operations.length > 0 &&
    from.path.startsWith("/editor") &&
    to.fullPath !== from.fullPath
  ) {
    void requestDraftTransition(
      async () => {
        allowNextRoute();
        await router.push(to.fullPath);
      },
      String(to.meta.title ?? (to.path.startsWith("/editor") ? "其他配置项目" : "其他页面")),
      to.path.startsWith("/editor") ? "switch" : "continue",
    );
    return false;
  }
  return true;
});

createApp(App).use(pinia).use(router).mount("#app");
