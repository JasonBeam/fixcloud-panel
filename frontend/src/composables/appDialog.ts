import { reactive } from "vue";

type DialogMode = "confirm" | "prompt";

type DialogState = {
  open: boolean;
  mode: DialogMode;
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
  danger: boolean;
  inputLabel: string;
  inputValue: string;
  placeholder: string;
};

export const appDialogState = reactive<DialogState>({
  open: false,
  mode: "confirm",
  title: "",
  message: "",
  confirmText: "确认",
  cancelText: "取消",
  danger: false,
  inputLabel: "",
  inputValue: "",
  placeholder: "",
});

let resolver: ((value: boolean | string | null) => void) | null = null;

function openDialog() {
  if (resolver) resolver(null);
  appDialogState.open = true;
  return new Promise<boolean | string | null>((resolve) => {
    resolver = resolve;
  });
}

export async function confirmDialog(options: {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}) {
  Object.assign(appDialogState, {
    mode: "confirm",
    title: options.title,
    message: options.message,
    confirmText: options.confirmText ?? "确认",
    cancelText: options.cancelText ?? "取消",
    danger: options.danger ?? false,
    inputLabel: "",
    inputValue: "",
    placeholder: "",
  });
  return (await openDialog()) === true;
}

export async function promptDialog(options: {
  title: string;
  message?: string;
  inputLabel: string;
  placeholder?: string;
  initialValue?: string;
  confirmText?: string;
}) {
  Object.assign(appDialogState, {
    mode: "prompt",
    title: options.title,
    message: options.message ?? "",
    confirmText: options.confirmText ?? "添加",
    cancelText: "取消",
    danger: false,
    inputLabel: options.inputLabel,
    inputValue: options.initialValue ?? "",
    placeholder: options.placeholder ?? "",
  });
  const result = await openDialog();
  return typeof result === "string" ? result : null;
}

export function resolveDialog(value: boolean | string | null) {
  appDialogState.open = false;
  resolver?.(value);
  resolver = null;
}
