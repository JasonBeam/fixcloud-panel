import { reactive } from "vue";

import type { DeleteImpact } from "@/utils/referenceIntegrity";

export type DeleteResolution = "cancel" | "keep" | "remove" | "replace";

export const referenceGuardState = reactive({
  open: false,
  impact: null as DeleteImpact | null,
  replacement: "",
  resolver: null as ((value: { resolution: DeleteResolution; replacement: string }) => void) | null,
});

export function requestReferenceDelete(impact: DeleteImpact) {
  referenceGuardState.impact = impact;
  referenceGuardState.replacement = impact.replacementOptions[0] ?? "";
  referenceGuardState.open = true;
  return new Promise<{ resolution: DeleteResolution; replacement: string }>((resolve) => {
    referenceGuardState.resolver = resolve;
  });
}

export function resolveReferenceDelete(resolution: DeleteResolution) {
  const resolver = referenceGuardState.resolver;
  const replacement = referenceGuardState.replacement;
  referenceGuardState.open = false;
  referenceGuardState.impact = null;
  referenceGuardState.resolver = null;
  resolver?.({ resolution, replacement });
}
