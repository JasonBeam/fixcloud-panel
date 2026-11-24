import { describe, expect, it } from "vitest";

import type { SourceStatus, YamlFileItem } from "@/stores/app";
import {
  formalSources,
  groupedFiles,
  requiresDraftGuardForTemporaryDelete,
  sessionUploadFiles,
} from "./sourcePresentation";

const source = (id: string, type: string): SourceStatus => ({
  id,
  type,
  name: id,
  builtIn: false,
  config: {},
  connected: true,
  readOnly: false,
  message: "可用",
});

const file = (name: string, sourceType: string, sourceId = sourceType): YamlFileItem => ({
  sourceId,
  sourceType,
  sourceName: sourceId,
  name,
  path: `/${name}`,
  size: 12,
  modifiedAt: "2026-07-26T12:00:00Z",
  etag: "etag",
  hash: "hash",
});

describe("source presentation", () => {
  it("shows only formal SMB and WebDAV sources", () => {
    expect(formalSources([
      source("mounted", "smb-mounted"),
      source("smb", "smb"),
      source("dav", "webdav"),
      source("uploaded-files", "upload"),
    ]).map((item) => item.id)).toEqual(["mounted", "smb", "dav"]);
  });

  it("does not create an upload area or empty temporary group without session files", () => {
    const files = [file("formal.yaml", "webdav", "dav")];
    expect(sessionUploadFiles(files)).toEqual([]);
    expect(groupedFiles(files).map((group) => group.title)).toEqual(["正式配置 / 配置目录"]);
  });

  it("shows the temporary group only while session upload files remain", () => {
    const temporary = file("temporary.yaml", "upload", "uploaded-files");
    const files = [file("formal.yaml", "smb-mounted", "mounted"), temporary];
    expect(sessionUploadFiles(files)).toEqual([temporary]);
    expect(groupedFiles(files).map((group) => group.title)).toEqual([
      "正式配置 / 配置目录",
      "本会话临时文件",
    ]);
    expect(groupedFiles(files.filter((item) => item !== temporary)).map((group) => group.title))
      .toEqual(["正式配置 / 配置目录"]);
  });

  it("keeps config-directory uploads in their formal source group", () => {
    const uploadedToWebDav = file("config-upload.yaml", "webdav", "dav");
    expect(sessionUploadFiles([uploadedToWebDav])).toEqual([]);
    expect(groupedFiles([uploadedToWebDav])[0].items).toEqual([uploadedToWebDav]);
  });

  it("guards deletion only for the selected temporary file with a dirty draft", () => {
    const selected = file("current.yaml", "upload", "uploaded-files");
    const other = file("other.yaml", "upload", "uploaded-files");
    expect(requiresDraftGuardForTemporaryDelete(selected, selected, 2)).toBe(true);
    expect(requiresDraftGuardForTemporaryDelete(selected, selected, 0)).toBe(false);
    expect(requiresDraftGuardForTemporaryDelete(selected, other, 2)).toBe(false);
  });
});
