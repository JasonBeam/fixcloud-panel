<script setup lang="ts">
import { onMounted } from "vue";

import AppShell from "@/components/AppShell.vue";
import AppDialogHost from "@/components/AppDialogHost.vue";
import DiffModal from "@/components/DiffModal.vue";
import ReferenceIntegrityModal from "@/components/ReferenceIntegrityModal.vue";
import UnsavedChangesModal from "@/components/UnsavedChangesModal.vue";
import { useAppStore } from "@/stores/app";

const appStore = useAppStore();

onMounted(() => {
  appStore.bindNetworkEvents();
  void appStore.bootstrap();
});
</script>

<template>
  <div v-if="appStore.booting" class="login-screen">
    <div class="loading-orb" aria-label="正在载入" />
  </div>
  <template v-else>
    <AppShell />
    <DiffModal />
    <ReferenceIntegrityModal />
    <UnsavedChangesModal />
    <AppDialogHost />
  </template>
</template>
