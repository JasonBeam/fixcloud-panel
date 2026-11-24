import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  cancelDraftTransition,
  discardAndContinue,
  draftGuardState,
  requestDraftTransition,
} from "./draftGuard";
import { useAppStore } from "@/stores/app";

describe("draft transition failure safety", () => {
  beforeEach(() => {
    vi.stubGlobal("navigator", { onLine: true });
    vi.stubGlobal("window", {
      matchMedia: () => ({ matches: false }),
    });
    setActivePinia(createPinia());
  });

  afterEach(() => {
    cancelDraftTransition();
    vi.unstubAllGlobals();
  });

  it("does not clear the draft when the deferred action fails", async () => {
    const store = useAppStore();
    store.operations = [{ op: "set", path: ["port"], value: 7891 }];

    const immediate = await requestDraftTransition(
      async () => {
        throw new Error("删除失败");
      },
      "删除当前临时文件",
    );

    expect(immediate).toBe(false);
    await expect(discardAndContinue()).rejects.toThrow("删除失败");
    expect(store.dirtyCount).toBe(1);
    expect(draftGuardState.open).toBe(true);
  });
});
