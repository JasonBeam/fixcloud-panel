import { defineStore } from "pinia";

export type SectionCounts = {
  general: number;
  dns: number;
  proxies: number;
  proxyGroups: number;
  proxyProviders: number;
  rules: number;
  ruleProviders: number;
  rewrite: number;
  script: number;
  other: number;
};

export type SourceStatus = {
  id: string;
  type: string;
  name: string;
  builtIn: boolean;
  config: Record<string, unknown>;
  connected: boolean;
  readOnly: boolean;
  root?: string;
  message: string;
  reasonCode?: string;
  testedAt?: string;
  latencyMs?: number;
};

export type YamlFileItem = {
  sourceId: string;
  sourceType: string;
  sourceName: string;
  name: string;
  path: string;
  size: number;
  modifiedAt: string;
  etag: string;
  hash: string;
};

export type PatchOperation = {
  op: "set" | "delete" | "insert" | "move";
  path: Array<string | number>;
  value?: unknown;
  fromIndex?: number;
  toIndex?: number;
};

export type SavePreview = {
  previewToken: string;
  beforeHash: string;
  afterHash: string;
  diff: {
    text: string;
    changedLines: number;
    formatOnly: boolean;
  };
  validation: {
    errors: string[];
    warnings: string[];
  };
};

export type SaveFailure = {
  status: "unchanged" | "restored" | "recovery_failed" | "unknown";
  message: string;
  nextStep: string;
  backupPath?: string | null;
  formalHash?: string | null;
};

type ConfigPayload = {
  file: {
    sourceId: string;
    sourceType: string;
    sourceName: string;
    path: string;
    size: number;
    modifiedAt: string;
    etag: string;
    hash: string;
  };
  document: Record<string, unknown>;
  summary: { sections: SectionCounts };
  validation: { errors: string[]; warnings: string[] };
  writeEnabled: boolean;
};

type DraftPayload = {
  sourceId: string;
  path: string;
  baseHash: string;
  operations: PatchOperation[];
};

const emptyCounts: SectionCounts = {
  general: 0,
  dns: 0,
  proxies: 0,
  proxyGroups: 0,
  proxyProviders: 0,
  rules: 0,
  ruleProviders: 0,
  rewrite: 0,
  script: 0,
  other: 0,
};

const SELECTION_KEY = "fixcloud-session-selection";
const DRAFT_KEY = "fixcloud-session-draft";

function clone<T>(value: T): T {
  if (value === undefined) return value;
  return JSON.parse(JSON.stringify(value)) as T;
}

function normalizeApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") return String(item);
        const record = item as Record<string, unknown>;
        const location = Array.isArray(record.loc)
          ? record.loc.filter((part) => part !== "body").join(" → ")
          : "";
        const message = String(record.msg ?? "参数不正确")
          .replace("Field required", "不能为空")
          .replace("String should have at least 1 character", "不能为空");
        return location ? `${location}：${message}` : message;
      })
      .join("；");
  }
  if (detail && typeof detail === "object") {
    return String((detail as Record<string, unknown>).message ?? "请求处理失败");
  }
  return "请求处理失败";
}

export class ApiRequestError extends Error {
  detail: unknown;

  constructor(detail: unknown, status: number) {
    super(normalizeApiDetail(detail) || `请求失败（${status}）`);
    this.detail = detail;
  }
}

function resolveParent(
  root: Record<string, unknown>,
  path: Array<string | number>,
): { parent: Record<string, unknown> | unknown[]; key: string | number } {
  let current: unknown = root;
  for (const segment of path.slice(0, -1)) {
    current = Array.isArray(current)
      ? current[Number(segment)]
      : (current as Record<string, unknown>)[String(segment)];
  }
  return {
    parent: current as Record<string, unknown> | unknown[],
    key: path[path.length - 1],
  };
}

function applyOperation(root: Record<string, unknown>, operation: PatchOperation) {
  if (operation.op === "move") {
    let target: unknown = root;
    for (const segment of operation.path) {
      target = Array.isArray(target)
        ? target[Number(segment)]
        : (target as Record<string, unknown>)[String(segment)];
    }
    const fromIndex = Number(operation.fromIndex);
    const toIndex = Number(operation.toIndex);
    if (Array.isArray(target)) {
      const [item] = target.splice(fromIndex, 1);
      target.splice(toIndex, 0, item);
    } else if (target && typeof target === "object") {
      const record = target as Record<string, unknown>;
      const entries = Object.entries(record);
      const [item] = entries.splice(fromIndex, 1);
      entries.splice(toIndex, 0, item);
      for (const key of Object.keys(record)) delete record[key];
      for (const [key, value] of entries) record[key] = value;
    }
    return;
  }
  const { parent, key } = resolveParent(root, operation.path);
  const normalizedKey = Array.isArray(parent) ? Number(key) : String(key);
  if (operation.op === "delete") {
    if (Array.isArray(parent)) parent.splice(Number(normalizedKey), 1);
    else delete parent[String(normalizedKey)];
  } else if (operation.op === "insert") {
    if (!Array.isArray(parent)) throw new Error("目标不是列表");
    parent.splice(Number(normalizedKey), 0, clone(operation.value));
  } else if (Array.isArray(parent)) {
    parent[Number(normalizedKey)] = clone(operation.value);
  } else {
    parent[String(normalizedKey)] = clone(operation.value);
  }
}

function selectedQuery(sourceId: string, path: string) {
  return `sourceId=${encodeURIComponent(sourceId)}&path=${encodeURIComponent(path)}`;
}

export const useAppStore = defineStore("app", {
  state: () => ({
    booting: true,
    writeEnabled: false,
    online: navigator.onLine,
    backendReachable: false,
    dark: window.matchMedia("(prefers-color-scheme: dark)").matches,
    loading: false,
    saving: false,
    error: "",
    notice: "",
    saveFailure: null as SaveFailure | null,
    sources: [] as SourceStatus[],
    files: [] as YamlFileItem[],
    counts: { ...emptyCounts },
    document: {} as Record<string, unknown>,
    operations: [] as PatchOperation[],
    rawYamlDraft: null as string | null,
    preview: null as SavePreview | null,
    file: {
      sourceId: "default-smb",
      sourceType: "smb-mounted",
      sourceName: "NAS SMB",
      path: "/FixCloud.yaml",
      size: 0,
      modifiedAt: "",
      etag: "",
      hash: "",
    },
    validation: {
      errors: [] as string[],
      warnings: [] as string[],
    },
    afterSaveAction: null as null | (() => Promise<void>),
  }),
  getters: {
    dirtyCount: (state) => state.rawYamlDraft !== null ? 1 : state.operations.length,
    canSave: (state) =>
      state.online &&
      state.backendReachable &&
      state.writeEnabled &&
      (state.rawYamlDraft !== null || state.operations.length > 0) &&
      !state.saving,
  },
  actions: {
    applyTheme() {
      document.documentElement.classList.toggle("dark", this.dark);
    },
    toggleTheme() {
      this.dark = !this.dark;
      this.applyTheme();
      localStorage.setItem("fixcloud-theme", this.dark ? "dark" : "light");
    },
    async request(path: string, init: RequestInit = {}) {
      const headers = new Headers(init.headers);
      if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
      if (init.method && init.method !== "GET") headers.set("X-FixCloud-Request", "1");
      const response = await fetch(path, {
        ...init,
        headers,
        credentials: "same-origin",
        cache: "no-store",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new ApiRequestError(payload.detail ?? payload, response.status);
      return payload;
    },
    notify(message: string) {
      this.notice = message;
      window.setTimeout(() => {
        if (this.notice === message) this.notice = "";
      }, 2600);
    },
    async uploadYaml(file: File, mode: "temporary" | "config" = "temporary", sourceId?: string): Promise<YamlFileItem> {
      const form = new FormData();
      form.append("file", file);
      form.append("mode", mode);
      if (sourceId) form.append("sourceId", sourceId);
      const payload = await this.request("/api/files/upload", { method: "POST", body: form });
      await this.refreshSources();
      this.notify(`已上传 ${payload.file.name}`);
      return payload.file as YamlFileItem;
    },
    async deleteYaml(file: YamlFileItem) {
      await this.request("/api/files", {
        method: "DELETE",
        body: JSON.stringify({
          sourceId: file.sourceId,
          path: file.path,
          expectedHash: file.hash,
        }),
      });
    },
    async exportYaml(filename: string) {
      const response = await fetch("/api/config/export", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-FixCloud-Request": "1" },
        body: JSON.stringify({
          sourceId: this.file.sourceId,
          path: this.file.path,
          baseHash: this.file.hash,
          operations: this.operations,
          filename,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new ApiRequestError(payload.detail ?? payload, response.status);
      }
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      const downloadName = encoded ? decodeURIComponent(encoded) : filename;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = downloadName;
      anchor.click();
      URL.revokeObjectURL(url);
      this.notify(`已导出 ${downloadName}`);
    },
    saveSelection() {
      sessionStorage.setItem(
        SELECTION_KEY,
        JSON.stringify({ sourceId: this.file.sourceId, path: this.file.path }),
      );
    },
    persistDraft() {
      // Full YAML may contain credentials; never write it to browser storage.
      if (this.rawYamlDraft !== null) {
        sessionStorage.removeItem(DRAFT_KEY);
        return;
      }
      if (!this.operations.length) {
        sessionStorage.removeItem(DRAFT_KEY);
        return;
      }
      const draft: DraftPayload = {
        sourceId: this.file.sourceId,
        path: this.file.path,
        baseHash: this.file.hash,
        operations: clone(this.operations),
      };
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    },
    clearDraft() {
      this.operations = [];
      this.rawYamlDraft = null;
      this.preview = null;
      sessionStorage.removeItem(DRAFT_KEY);
    },
    applyConfig(payload: ConfigPayload, restoreDraft = false) {
      this.writeEnabled = payload.writeEnabled;
      this.counts = payload.summary.sections;
      this.file = payload.file;
      this.document = payload.document;
      this.validation = payload.validation;
      this.operations = [];
      this.rawYamlDraft = null;
      this.preview = null;
      this.saveFailure = null;
      this.saveSelection();
      if (restoreDraft) {
        try {
          const draft = JSON.parse(sessionStorage.getItem(DRAFT_KEY) || "null") as DraftPayload | null;
          if (
            draft &&
            draft.sourceId === payload.file.sourceId &&
            draft.path === payload.file.path &&
            draft.baseHash === payload.file.hash
          ) {
            for (const operation of draft.operations) applyOperation(this.document, operation);
            this.operations = draft.operations;
          } else {
            sessionStorage.removeItem(DRAFT_KEY);
          }
        } catch {
          sessionStorage.removeItem(DRAFT_KEY);
        }
      }
    },
    async fetchConfig(sourceId: string, path: string) {
      return await this.request(`/api/config?${selectedQuery(sourceId, path)}`) as ConfigPayload;
    },
    async bootstrap() {
      const savedTheme = localStorage.getItem("fixcloud-theme");
      if (savedTheme) this.dark = savedTheme === "dark";
      this.applyTheme();
      try {
        const [sourcesPayload, filesPayload] = await Promise.all([
          this.request("/api/sources"),
          this.request("/api/files/catalog"),
        ]);
        this.sources = sourcesPayload.sources;
        this.files = filesPayload.files;
        const saved = JSON.parse(sessionStorage.getItem(SELECTION_KEY) || "null") as {
          sourceId?: string;
          path?: string;
        } | null;
        const selected =
          this.files.find((item) => item.sourceId === saved?.sourceId && item.path === saved?.path) ??
          this.files.find((item) => item.sourceId === sourcesPayload.default) ??
          this.files[0];
        if (!selected) throw new Error("配置目录中没有可编辑的 YAML 文件");
        this.applyConfig(await this.fetchConfig(selected.sourceId, selected.path), true);
        this.backendReachable = true;
      } catch (error) {
        this.backendReachable = false;
        this.error = error instanceof Error ? error.message : "无法读取配置";
      } finally {
        this.booting = false;
      }
    },
    async refresh() {
      this.loading = true;
      this.error = "";
      try {
        const [sourcesPayload, filesPayload, configPayload] = await Promise.all([
          this.request("/api/sources"),
          this.request("/api/files/catalog"),
          this.fetchConfig(this.file.sourceId, this.file.path),
        ]);
        this.sources = sourcesPayload.sources;
        this.files = filesPayload.files;
        this.applyConfig(configPayload);
        this.backendReachable = true;
      } catch (error) {
        this.backendReachable = false;
        this.error = error instanceof Error ? error.message : "无法读取配置";
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async refreshSources() {
      const [sourcesPayload, filesPayload] = await Promise.all([
        this.request("/api/sources"),
        this.request("/api/files/catalog"),
      ]);
      this.sources = sourcesPayload.sources;
      this.files = filesPayload.files;
    },
    async selectFile(file: YamlFileItem, clearOldDraft = false) {
      const payload = await this.fetchConfig(file.sourceId, file.path);
      if (clearOldDraft) this.clearDraft();
      this.applyConfig(payload);
      this.backendReachable = true;
    },
    setValue(path: Array<string | number>, value: unknown) {
      if (this.rawYamlDraft !== null) {
        this.notify("当前为高级 YAML 草稿；请先在 Diff 中保存或放弃后再使用图形化修改");
        return;
      }
      applyOperation(this.document, { op: "set", path, value });
      const existingIndex = this.operations.findIndex(
        (item) => item.op === "set" && JSON.stringify(item.path) === JSON.stringify(path),
      );
      const operation: PatchOperation = { op: "set", path: clone(path), value: clone(value) };
      if (existingIndex >= 0) this.operations.splice(existingIndex, 1, operation);
      else this.operations.push(operation);
      this.preview = null;
      this.persistDraft();
    },
    insertValue(path: Array<string | number>, value: unknown) {
      if (this.rawYamlDraft !== null) {
        this.notify("当前为高级 YAML 草稿；请先在 Diff 中保存或放弃后再使用图形化修改");
        return;
      }
      const operation: PatchOperation = { op: "insert", path: clone(path), value: clone(value) };
      applyOperation(this.document, operation);
      this.operations.push(operation);
      this.preview = null;
      this.persistDraft();
    },
    deleteValue(path: Array<string | number>) {
      if (this.rawYamlDraft !== null) {
        this.notify("当前为高级 YAML 草稿；请先在 Diff 中保存或放弃后再使用图形化修改");
        return;
      }
      const operation: PatchOperation = { op: "delete", path: clone(path) };
      applyOperation(this.document, operation);
      this.operations.push(operation);
      this.preview = null;
      this.persistDraft();
    },
    moveValue(path: Array<string | number>, fromIndex: number, toIndex: number) {
      if (this.rawYamlDraft !== null) {
        this.notify("当前为高级 YAML 草稿；请先在 Diff 中保存或放弃后再使用图形化修改");
        return;
      }
      const operation: PatchOperation = {
        op: "move",
        path: clone(path),
        fromIndex,
        toIndex,
      };
      applyOperation(this.document, operation);
      this.operations.push(operation);
      this.preview = null;
      this.persistDraft();
    },
    async discardChanges() {
      const payload = await this.fetchConfig(this.file.sourceId, this.file.path);
      this.clearDraft();
      this.applyConfig(payload);
    },
    async createPreview() {
      if (!this.canSave) return;
      this.saving = true;
      this.error = "";
      this.saveFailure = null;
      try {
        this.preview = await this.request(this.rawYamlDraft !== null ? "/api/config/preview/raw" : "/api/config/preview", {
          method: "POST",
          body: JSON.stringify({
            sourceId: this.file.sourceId,
            path: this.file.path,
            baseHash: this.file.hash,
            ...(this.rawYamlDraft !== null ? { content: this.rawYamlDraft } : { operations: this.operations }),
          }),
        });
      } catch (error) {
        this.error = error instanceof Error ? error.message : "无法生成保存预览";
        this.afterSaveAction = null;
        throw error;
      } finally {
        this.saving = false;
      }
    },
    async fetchRawYaml() {
      return await this.request("/api/config/raw?" + selectedQuery(this.file.sourceId, this.file.path)) as {
        content: string;
        hash: string;
      };
    },
    async applyAdvancedYaml(content: string) {
      const payload = await this.request("/api/config/advanced/validate", {
        method: "POST",
        body: JSON.stringify({
          sourceId: this.file.sourceId,
          path: this.file.path,
          baseHash: this.file.hash,
          content,
        }),
      }) as { document: Record<string, unknown>; validation: { errors: string[]; warnings: string[] } };
      if (payload.validation.errors.length) {
        this.validation = payload.validation;
        throw new Error(`YAML 检查未通过：${payload.validation.errors.join("；")}`);
      }
      this.document = payload.document;
      this.validation = payload.validation;
      this.operations = [];
      this.rawYamlDraft = content;
      this.preview = null;
      this.persistDraft();
      return payload;
    },
    async commitPreview() {
      if (!this.preview) return;
      this.saving = true;
      this.error = "";
      this.saveFailure = null;
      try {
        await this.request("/api/config/save", {
          method: "POST",
          body: JSON.stringify({ previewToken: this.preview.previewToken }),
        });
        const continuation = this.afterSaveAction;
        this.afterSaveAction = null;
        this.clearDraft();
        this.applyConfig(await this.fetchConfig(this.file.sourceId, this.file.path));
        if (continuation) await continuation();
      } catch (error) {
        if (error instanceof ApiRequestError && error.detail && typeof error.detail === "object") {
          const detail = error.detail as Partial<SaveFailure>;
          this.saveFailure = {
            status: detail.status ?? "unknown",
            message: detail.message ?? error.message,
            nextStep: detail.nextStep ?? "请保留当前页面并检查来源状态后再操作。",
            backupPath: detail.backupPath,
            formalHash: detail.formalHash,
          };
        }
        this.error = error instanceof Error ? error.message : "保存失败";
        this.afterSaveAction = null;
        throw error;
      } finally {
        this.saving = false;
      }
    },
    bindNetworkEvents() {
      window.addEventListener("online", () => {
        this.online = true;
        if (this.operations.length === 0) void this.refresh();
      });
      window.addEventListener("offline", () => {
        this.online = false;
        this.backendReachable = false;
      });
      window.addEventListener("beforeunload", (event) => {
        if (this.operations.length > 0) event.preventDefault();
      });
    },
  },
});
