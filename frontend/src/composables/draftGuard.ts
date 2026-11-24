import { reactive } from "vue";

import { useAppStore } from "@/stores/app";

type GuardAction = null | (() => Promise<void>);

export const draftGuardState = reactive({
  open: false,
  confirmingDiscard: false,
  busy: false,
  destination: "",
  mode: "continue" as "continue" | "close" | "switch",
});

let pendingAction: GuardAction = null;
let bypassNextRoute = false;

export function consumeRouteBypass() {
  if (!bypassNextRoute) return false;
  bypassNextRoute = false;
  return true;
}

export function allowNextRoute() {
  bypassNextRoute = true;
}

export async function requestDraftTransition(
  action: () => Promise<void>,
  destination: string,
  mode: "continue" | "close" | "switch" = "continue",
) {
  const store = useAppStore();
  if (!store.dirtyCount) {
    await action();
    return true;
  }
  pendingAction = action;
  draftGuardState.destination = destination;
  draftGuardState.mode = mode;
  draftGuardState.confirmingDiscard = false;
  draftGuardState.open = true;
  return false;
}

export function cancelDraftTransition() {
  pendingAction = null;
  draftGuardState.open = false;
  draftGuardState.confirmingDiscard = false;
}

export async function saveAndContinue() {
  const store = useAppStore();
  if (!pendingAction) return;
  store.afterSaveAction = pendingAction;
  pendingAction = null;
  draftGuardState.open = false;
  draftGuardState.confirmingDiscard = false;
  await store.createPreview();
}

export function askDiscardConfirmation() {
  draftGuardState.confirmingDiscard = true;
}

export async function discardAndContinue() {
  const store = useAppStore();
  if (!pendingAction) return;
  draftGuardState.busy = true;
  try {
    const action = pendingAction;
    await action();
    await store.discardChanges();
    pendingAction = null;
    draftGuardState.open = false;
    draftGuardState.confirmingDiscard = false;
  } finally {
    draftGuardState.busy = false;
  }
}
