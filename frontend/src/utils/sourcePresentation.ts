import type { SourceStatus, YamlFileItem } from "@/stores/app";

export function formalSources(sources: SourceStatus[]): SourceStatus[] {
  return sources.filter((source) =>
    source.type === "smb" || source.type === "smb-mounted" || source.type === "webdav",
  );
}

export function sessionUploadFiles(files: YamlFileItem[]): YamlFileItem[] {
  return files.filter((file) => file.sourceType === "upload");
}

export function requiresDraftGuardForTemporaryDelete(
  selected: Pick<YamlFileItem, "sourceId" | "path">,
  target: Pick<YamlFileItem, "sourceId" | "path">,
  dirtyCount: number,
): boolean {
  return dirtyCount > 0 &&
    selected.sourceId === target.sourceId &&
    selected.path === target.path;
}

export function groupedFiles(files: YamlFileItem[]) {
  return [
    {
      title: "正式配置 / 配置目录",
      items: files.filter((file) => file.sourceType !== "upload"),
    },
    {
      title: "本会话临时文件",
      items: sessionUploadFiles(files),
    },
  ].filter((group) => group.items.length > 0);
}
