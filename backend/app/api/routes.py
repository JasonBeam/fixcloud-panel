from __future__ import annotations

import asyncio
import posixpath
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.settings import Settings, get_settings
from app.services.audit import AuditStore
from app.services.icon_catalog import IconCatalog, IconCatalogError
from app.services.icon_cache import IconCache, IconCacheError
from app.services.publication import PublicationCheckError, PublicationVerifier
from app.services.save_service import SaveCommitError, SaveService, preview_store
from app.services.source_store import (
    DEFAULT_CONFIG_DIRECTORY,
    SourceRecord,
    SourceStore,
    normalize_directory,
    probe_store,
)
from app.services.storage.base import StorageBackend
from app.services.storage.registry import build_storage_from_source
from app.services.subscription_usage import SubscriptionUsageService
from app.services.subscription_nodes import SubscriptionNodesService
from app.services.yaml_service import YamlService

router = APIRouter(prefix="/api")


class PatchOperation(BaseModel):
    op: Literal["set", "delete", "insert", "move"]
    path: list[str | int]
    value: Any = None
    fromIndex: int | None = None
    toIndex: int | None = None


class PreviewRequest(BaseModel):
    sourceId: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    baseHash: str = Field(min_length=64, max_length=64)
    operations: list[PatchOperation] = Field(min_length=1, max_length=1000)


class RawYamlRequest(BaseModel):
    sourceId: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    baseHash: str = Field(min_length=64, max_length=64)
    content: str = Field(min_length=1, max_length=2_000_000)


class SaveRequest(BaseModel):
    previewToken: str = Field(min_length=20, max_length=200)


class ExportRequest(BaseModel):
    sourceId: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    baseHash: str = Field(min_length=64, max_length=64)
    operations: list[PatchOperation] = Field(default_factory=list, max_length=1000)
    filename: str | None = Field(default=None, max_length=255)


class RestorePreviewRequest(BaseModel):
    sourceId: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    backupPath: str = Field(min_length=1, max_length=2048)


class DeleteBackupRequest(BaseModel):
    sourceId: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    backupPath: str = Field(min_length=1, max_length=2048)


class SelectFileRequest(BaseModel):
    sourceId: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)


class DeleteFileRequest(BaseModel):
    sourceId: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=2048)
    expectedHash: str = Field(min_length=64, max_length=64)


class LogSettingsRequest(BaseModel):
    maxEntries: int = Field(ge=1, le=50_000)


class SourceInput(BaseModel):
    sourceId: str | None = Field(default=None, max_length=128)
    type: Literal["smb", "webdav"]
    name: str = Field(min_length=1, max_length=128)
    config: dict[str, Any]
    probeToken: str | None = Field(default=None, max_length=200)


async def require_internal_request(request: Request) -> None:
    if request.headers.get("x-fixcloud-request") != "1":
        raise HTTPException(status_code=403, detail="写请求缺少面板同源标记")


def source_store(settings: Settings) -> SourceStore:
    return SourceStore(settings.app_data_dir, settings)


def default_source_id(settings: Settings) -> str:
    return "default-smb"


async def requested_context(
    settings: Settings,
    source_id: str | None = None,
    path: str | None = None,
) -> tuple[SourceRecord, StorageBackend, str]:
    store = source_store(settings)
    records = await store.list()
    selected_id = source_id or default_source_id(settings)
    selected_path = path or settings.yaml_path
    source = next((item for item in records if item.id == selected_id), None)
    if not source:
        raise HTTPException(status_code=404, detail="文件来源不存在")
    if not is_editable_yaml_path(selected_path):
        raise HTTPException(status_code=422, detail="只能选择配置目录直属的主配置 YAML")
    return source, build_storage_from_source(source), selected_path


def is_editable_yaml_path(path: str) -> bool:
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or "\x00" in path
        or posixpath.dirname(path) != "/"
    ):
        return False
    name = posixpath.basename(path)
    return bool(
        name
        and not name.startswith(".")
        and ".backup-" not in name.lower()
        and name.lower().endswith((".yaml", ".yml"))
    )


def is_selected_backup(path: str, selected_path: str) -> bool:
    if posixpath.dirname(path) != "/" or posixpath.dirname(selected_path) != "/":
        return False
    name = posixpath.basename(path)
    selected_name = posixpath.basename(selected_path)
    return name.startswith(f"{selected_name}.backup-") and name.endswith(".yaml")


def validate_source(record: SourceRecord) -> None:
    if not record.name.strip():
        raise ValueError("来源名称不能为空")
    config_directory = normalize_directory(
        record.config.get("configDirectory"),
        default=DEFAULT_CONFIG_DIRECTORY,
    )
    if not config_directory:
        raise ValueError("配置目录不能为空")
    normalize_directory(record.config.get("rootDirectory", ""))
    if record.type == "webdav":
        url = str(record.config.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("WebDAV URL 必须以 http:// 或 https:// 开头")
    elif record.type == "smb":
        if not str(record.config.get("server", "")).strip():
            raise ValueError("SMB 服务器地址不能为空")
        if not str(record.config.get("share", "")).strip():
            raise ValueError("SMB 共享目录不能为空")
    else:
        raise ValueError("只能添加 SMB 或 WebDAV 来源")


async def test_source_record(record: SourceRecord) -> dict[str, Any]:
    if record.type == "upload":
        from app.services.browser_session import current_directory
        root = current_directory()
        await asyncio.to_thread(root.mkdir, parents=True, exist_ok=True)
        return {
            **record.safe_data(),
            "connected": True,
            "readOnly": False,
            "message": "本地持久化目录可用",
            "reasonCode": "ok",
            "testedAt": datetime.now(timezone.utc).isoformat(),
            "latencyMs": 1,
        }
    started = time.perf_counter()
    try:
        status = await build_storage_from_source(record).status()
    except Exception:
        status = {
            "connected": False,
            "readOnly": True,
            "message": "连接测试失败",
            "reasonCode": "connection",
        }
    latency = max(1, round((time.perf_counter() - started) * 1000))
    return {
        **record.safe_data(),
        **status,
        "id": record.id,
        "name": record.name,
        "type": record.type,
        "testedAt": datetime.now(timezone.utc).isoformat(),
        "latencyMs": latency,
    }


async def list_editable_yaml_files(
    storage: StorageBackend,
    source: SourceRecord,
) -> list[dict[str, Any]]:
    entries = await storage.list_dir("/")
    results: list[dict[str, Any]] = []
    for entry in entries:
        if (
            not entry.is_directory
            and is_editable_yaml_path(entry.path)
            and entry.name.lower().endswith((".yaml", ".yml"))
            and ".backup-" not in entry.name.lower()
            and not entry.name.startswith(".")
        ):
            results.append(
                {
                    "sourceId": source.id,
                    "sourceType": source.type,
                    "sourceName": source.name,
                    "name": entry.name,
                    "path": entry.path,
                    "size": entry.size,
                    "modifiedAt": entry.modified_at,
                    "etag": entry.etag,
                    "hash": YamlService().sha256(await storage.read_bytes(entry.path)),
                }
            )
    return results


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    try:
        _, storage, yaml_path = await requested_context(settings)
        status = await storage.status()
        if not status.get("connected"):
            raise RuntimeError(str(status.get("message") or "默认配置目录不可用"))
        YamlService().load(await storage.read_bytes(yaml_path))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"面板后端可用，但默认配置未就绪：{exc}") from exc
    return {"status": "ok", "storage": "ready", "yaml": "valid"}


@router.get("/subscriptions/usage")
async def subscription_usage(
    sourceId: str = Query(min_length=1, max_length=128),
    path: str = Query(min_length=1, max_length=2048),
    force: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(settings, sourceId, path)
    try:
        raw = await storage.read_bytes(yaml_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    yaml_service = YamlService()
    document = yaml_service.load(raw)
    from app.services.browser_session import current_scope
    session_cache_scope = current_scope() if source.type == "upload" else "formal"
    return await SubscriptionUsageService().get_usage(
        document.root,
        cache_key=f"{session_cache_scope}:{source.id}:{yaml_path}:{yaml_service.sha256(raw)}",
        force=force,
    )


@router.get("/vps/usage")
async def vps_usage() -> dict[str, Any]:
    from app.services.vps_usage import get_vps_usage
    return {"servers": await get_vps_usage()}


@router.get("/subscriptions/nodes")
async def subscription_nodes(
    sourceId: str | None = Query(default=None),
    path: str | None = Query(default=None),
    force: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(settings, sourceId, path)
    raw = await storage.read_bytes(yaml_path)
    yaml_service = YamlService()
    document = yaml_service.load(raw)
    from app.services.browser_session import current_scope

    session_cache_scope = current_scope() if source.type == "upload" else "formal"
    return await SubscriptionNodesService().get_nodes(
        document.root,
        cache_key=f"nodes:{session_cache_scope}:{source.id}:{yaml_path}:{yaml_service.sha256(raw)}",
        force=force,
    )


@router.get("/publication/status")
async def publication_status(
    sourceId: str = Query(min_length=1, max_length=128),
    path: str = Query(min_length=1, max_length=2048),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(settings, sourceId, path)
    try:
        current = await storage.read_bytes(yaml_path)
        result = await PublicationVerifier(settings.public_file_base_url).compare(
            filename=posixpath.basename(yaml_path),
            current=current,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except PublicationCheckError as exc:
        await AuditStore(settings.app_data_dir).record_event(
            source_id=source.id,
            action="publication-check",
            path=yaml_path,
            status="failure",
            message=str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    matching = bool(result["matching"])
    await AuditStore(settings.app_data_dir).record_event(
        source_id=source.id,
        action="publication-check",
        path=yaml_path,
        status="success" if matching else "failure",
        message="线上 YAML 与当前文件一致" if matching else "线上 YAML 与当前文件不一致",
    )
    return {
        **result,
        "baseUrl": settings.public_file_base_url,
        "fileName": posixpath.basename(yaml_path),
    }


@router.get("/sources")
async def sources(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    records = await source_store(settings).list()
    statuses = await asyncio.gather(*(test_source_record(item) for item in records))
    return {
        "sources": statuses,
        "default": default_source_id(settings),
        "writeEnabled": settings.write_enabled,
    }


@router.post("/sources/probe")
async def probe_source(
    payload: SourceInput,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    try:
        candidate = await source_store(settings).merged_candidate(
            payload.sourceId,
            payload.type,
            payload.name,
            payload.config,
        )
        validate_source(candidate)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="文件来源不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = await test_source_record(candidate)
    if not result["connected"]:
        return {"source": result, "probeToken": None}
    return {"source": result, "probeToken": probe_store.issue(candidate)}


@router.post("/sources/{source_id}/test")
async def test_saved_source(
    source_id: str,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source = await source_store(settings).get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="文件来源不存在")
    result = await test_source_record(source)
    await AuditStore(settings.app_data_dir).record_event(
        source_id=source.id,
        action="connection-test",
        path="",
        status="success" if result["connected"] else "failure",
        message=str(result.get("message") or ("连接成功" if result["connected"] else "连接失败")),
    )
    return {"source": result}


@router.post("/sources/directories")
async def source_directories(
    payload: SourceInput,
    path: str = Query(default="/"),
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    try:
        candidate = await source_store(settings).merged_candidate(
            payload.sourceId,
            payload.type,
            payload.name,
            payload.config,
        )
        validate_source(candidate)
        normalized_path = "/" + normalize_directory(path)
        if normalized_path == "/":
            normalized_path = "/"
        storage = build_storage_from_source(candidate, include_config_directory=False)
        status = await storage.status()
        if not status.get("connected"):
            return {"path": normalized_path, "directories": [], "status": status}
        entries = await storage.list_dir(normalized_path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="文件来源不存在") from exc
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "path": normalized_path,
        "directories": [
            {"name": entry.name, "path": entry.path}
            for entry in entries
            if entry.is_directory and not entry.name.startswith(".")
        ],
        "status": status,
    }


@router.post("/sources")
async def create_source(
    payload: SourceInput,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = source_store(settings)
    candidate = await store.merged_candidate(None, payload.type, payload.name, payload.config)
    try:
        validate_source(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not payload.probeToken or not probe_store.consume(payload.probeToken, candidate):
        raise HTTPException(status_code=409, detail="请先测试连接成功后再保存")
    created = await store.create(payload.type, payload.name, payload.config)
    return {"source": await test_source_record(created)}


@router.put("/sources/{source_id}")
async def update_source(
    source_id: str,
    payload: SourceInput,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = source_store(settings)
    try:
        candidate = await store.merged_candidate(
            source_id,
            payload.type,
            payload.name,
            payload.config,
        )
        validate_source(candidate)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="文件来源不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not payload.probeToken or not probe_store.consume(payload.probeToken, candidate):
        raise HTTPException(status_code=409, detail="请先测试连接成功后再保存")
    updated = await store.update(source_id, payload.type, payload.name, payload.config)
    return {"source": await test_source_record(updated)}


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    record = await source_store(settings).get(source_id)
    if record and record.built_in:
        raise HTTPException(status_code=409, detail="默认 SMB 来源不能删除")
    try:
        await source_store(settings).delete(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="文件来源不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"deleted": True}


@router.get("/files/catalog")
async def file_catalog(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    records = await source_store(settings).list()

    async def collect(source: SourceRecord) -> list[dict[str, Any]]:
        result = await test_source_record(source)
        if not result["connected"]:
            return []
        try:
            return await list_editable_yaml_files(build_storage_from_source(source), source)
        except Exception:
            return []

    groups = await asyncio.gather(*(collect(source) for source in records))
    files = [item for group in groups for item in group]
    files.sort(key=lambda item: (item["name"].lower(), item["sourceName"].lower(), item["path"]))
    return {"files": files}


@router.post("/files/upload")
async def upload_yaml(
    file: UploadFile = File(...),
    mode: Literal["temporary", "config"] = Form(default="temporary"),
    sourceId: str | None = Form(default=None),
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    audit = AuditStore(settings.app_data_dir)
    original_name = Path(file.filename or "").name
    selected_source_id = "uploaded-files" if mode == "temporary" else (sourceId or "default-smb")
    source = await source_store(settings).get(selected_source_id)
    if source and mode == "config" and source.type == "upload":
        raise HTTPException(status_code=422, detail="配置目录模式必须选择 SMB 或 WebDAV 来源")
    if not source:
        raise HTTPException(status_code=500, detail="上传来源不可用")
    try:
        if not original_name.lower().endswith((".yaml", ".yml")):
            raise ValueError("只允许上传 .yaml 或 .yml 文件")
        raw = await file.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError("文件大小不能超过 5 MiB")
        YamlService().load(raw)
        stem = re.sub(r"[^\w .()-]+", "_", Path(original_name).stem, flags=re.UNICODE)
        stem = stem.strip(" .")[:180] or "uploaded"
        suffix = Path(original_name).suffix.lower()
        storage = build_storage_from_source(source)
        selected_path = ""
        for index in range(1000):
            candidate = f"/{stem}{'' if index == 0 else f'-{index}'}{suffix}"
            try:
                await storage.write_bytes(candidate, raw, overwrite=False)
                selected_path = candidate
                break
            except FileExistsError:
                continue
        if not selected_path:
            raise ValueError("同名文件过多，请修改文件名后重试")
        stat = await storage.stat(selected_path)
        await audit.record_event(
            source_id=source.id,
            action="upload",
            path=selected_path,
            status="success",
            message=f"已上传 {posixpath.basename(selected_path)}",
        )
        return {
            "file": {
                "sourceId": source.id,
                "sourceType": source.type,
                "sourceName": source.name,
                "name": posixpath.basename(selected_path),
                "path": selected_path,
                "size": stat.size,
                "modifiedAt": stat.modified_at,
                "etag": stat.etag,
                "hash": YamlService().sha256(raw),
            },
            "mode": mode,
        }
    except (UnicodeDecodeError, ValueError) as exc:
        await audit.record_event(
            source_id=source.id,
            action="upload",
            path=f"/{original_name}" if original_name else "/",
            status="failure",
            message=str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()


@router.delete("/files")
async def delete_yaml_file(
    payload: DeleteFileRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source = await source_store(settings).get(payload.sourceId)
    if not source:
        raise HTTPException(status_code=404, detail="文件来源不存在")
    if not is_editable_yaml_path(payload.path):
        raise HTTPException(status_code=422, detail="只能删除配置目录直属的 YAML 文件")
    storage = build_storage_from_source(source)
    audit = AuditStore(settings.app_data_dir)
    try:
        stat = await storage.stat(payload.path)
        if stat.is_directory:
            raise ValueError("不能删除目录")
        digest = YamlService().sha256(await storage.read_bytes(payload.path))
        if digest != payload.expectedHash:
            raise RuntimeError("文件已发生变化，请刷新后重试")
        await storage.delete(payload.path)
        await audit.record_event(
            source_id=source.id, action="delete-file", path=payload.path,
            status="success", message=f"已删除 {posixpath.basename(payload.path)}",
        )
        return {"deleted": payload.path}
    except FileNotFoundError as exc:
        message, status = "文件不存在", 404
    except RuntimeError as exc:
        message, status = str(exc), 409
    except (PermissionError, ValueError) as exc:
        message, status = str(exc), 422
    await audit.record_event(
        source_id=source.id, action="delete-file", path=payload.path,
        status="failure", message=message,
    )
    raise HTTPException(status_code=status, detail=message)


@router.get("/files")
async def files(
    path: str = Query(default="/"),
    sourceId: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source = await source_store(settings).get(sourceId or default_source_id(settings))
    if not source:
        raise HTTPException(status_code=404, detail="文件来源不存在")
    if path != "/":
        raise HTTPException(status_code=403, detail="只能浏览该来源的配置目录")
    storage = build_storage_from_source(source)
    try:
        entries = await storage.list_dir(path)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    editable_entries = []
    for entry in entries:
        if entry.is_directory or not is_editable_yaml_path(entry.path):
            continue
        editable_entries.append({
            "name": entry.name,
            "path": entry.path,
            "size": entry.size,
            "modifiedAt": entry.modified_at,
            "etag": entry.etag,
            "hash": YamlService().sha256(await storage.read_bytes(entry.path)),
            "directory": False,
        })
    return {
        "source": source.safe_data(),
        "path": path,
        "entries": editable_entries,
    }


@router.post("/files/select")
async def select_file(
    payload: SelectFileRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    source = await source_store(settings).get(payload.sourceId)
    if not source:
        raise HTTPException(status_code=404, detail="文件来源不存在")
    if not is_editable_yaml_path(payload.path):
        raise HTTPException(status_code=422, detail="只能选择配置目录直属的主配置 YAML")
    storage = build_storage_from_source(source)
    try:
        raw = await storage.read_bytes(payload.path)
        YamlService().load(raw)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="所选文件不存在") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"无法选择该 YAML：{exc}") from exc
    return {"sourceId": source.id, "path": payload.path}


@router.get("/config")
async def config_document(
    sourceId: str | None = Query(default=None),
    path: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(settings, sourceId, path)
    yaml_service = YamlService()
    try:
        stat = await storage.stat(yaml_path)
        raw = await storage.read_bytes(yaml_path)
        document = yaml_service.load(raw)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"YAML 解析失败：{exc}") from exc
    return {
        "file": {
            "sourceId": source.id,
            "sourceType": source.type,
            "sourceName": source.name,
            "path": stat.path,
            "size": stat.size,
            "modifiedAt": stat.modified_at,
            "etag": stat.etag,
            "hash": yaml_service.sha256(raw),
        },
        "document": yaml_service.to_safe_data(document.root),
        "summary": yaml_service.summary(document),
        "validation": yaml_service.validate_references(document),
        "writeEnabled": settings.write_enabled,
    }


@router.get("/config/raw")
async def config_raw_document(
    sourceId: str | None = Query(default=None),
    path: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    _, storage, yaml_path = await requested_context(settings, sourceId, path)
    try:
        raw = await storage.read_bytes(yaml_path)
        service = YamlService()
        service.load(raw)
        return {"content": raw.decode("utf-8"), "hash": service.sha256(raw)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"YAML 解析失败：{exc}") from exc


@router.get("/config/summary")
async def config_summary(
    sourceId: str | None = Query(default=None),
    path: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(settings, sourceId, path)
    try:
        stat = await storage.stat(yaml_path)
        raw = await storage.read_bytes(yaml_path)
        service = YamlService()
        document = service.load(raw)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"YAML 解析失败：{exc}") from exc
    return {
        "file": {
            "sourceId": source.id,
            "sourceType": source.type,
            "sourceName": source.name,
            "path": stat.path,
            "size": stat.size,
            "modifiedAt": stat.modified_at,
            "etag": stat.etag,
            "hash": service.sha256(raw),
        },
        **service.summary(document),
    }


@router.post("/config/export")
async def export_config(
    payload: ExportRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> Response:
    source, storage, yaml_path = await requested_context(settings, payload.sourceId, payload.path)
    audit = AuditStore(settings.app_data_dir)
    try:
        raw = await storage.read_bytes(yaml_path)
        service = YamlService()
        if service.sha256(raw) != payload.baseHash:
            raise RuntimeError("原文件已变化，请重新加载后再导出")
        content = raw
        if payload.operations:
            document = service.load(raw)
            service.apply_operations(
                document,
                [operation.model_dump() for operation in payload.operations],
            )
            content = service.dump_candidate(document)
        requested_name = Path(payload.filename or posixpath.basename(yaml_path)).name
        if not requested_name.lower().endswith((".yaml", ".yml")):
            requested_name += ".yaml"
        requested_name = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "_", requested_name).strip(" .")
        if not requested_name:
            requested_name = "config.yaml"
        await audit.record_event(
            source_id=source.id,
            action="export",
            path=yaml_path,
            status="success",
            message=f"已导出 {requested_name}",
        )
        return Response(
            content,
            media_type="application/yaml",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(requested_name)}"},
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except (KeyError, IndexError, TypeError, UnicodeDecodeError, ValueError, RuntimeError) as exc:
        await audit.record_event(
            source_id=source.id,
            action="export",
            path=yaml_path,
            status="failure",
            message=str(exc),
        )
        status = 409 if isinstance(exc, RuntimeError) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/config/preview")
async def preview_config(
    payload: PreviewRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(
        settings,
        payload.sourceId,
        payload.path,
    )
    service = SaveService(storage, AuditStore(settings.app_data_dir))
    try:
        record = await service.create_preview(
            path=yaml_path,
            source_id=source.id,
            base_hash=payload.baseHash,
            operations=[operation.model_dump() for operation in payload.operations],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "previewToken": record.token,
        "beforeHash": record.before_hash,
        "afterHash": record.after_hash,
        "diff": record.diff,
        "validation": record.validation,
    }


@router.post("/config/advanced/validate")
async def validate_advanced_yaml(
    payload: RawYamlRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    _, storage, yaml_path = await requested_context(settings, payload.sourceId, payload.path)
    service = YamlService()
    try:
        current = await storage.read_bytes(yaml_path)
        if service.sha256(current) != payload.baseHash:
            raise RuntimeError("配置文件已在其他位置发生变化，请重新加载后再修改")
        document = service.load(payload.content.encode("utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"YAML 语法检查失败：{exc}") from exc
    return {
        "document": service.to_safe_data(document.root),
        "validation": service.validate_references(document),
    }


@router.post("/config/preview/raw")
async def preview_raw_config(
    payload: RawYamlRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(settings, payload.sourceId, payload.path)
    service = SaveService(storage, AuditStore(settings.app_data_dir))
    try:
        record = await service.create_raw_preview(
            path=yaml_path,
            source_id=source.id,
            base_hash=payload.baseHash,
            content=payload.content.encode("utf-8"),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"YAML 语法检查失败：{exc}") from exc
    return {
        "previewToken": record.token,
        "beforeHash": record.before_hash,
        "afterHash": record.after_hash,
        "diff": record.diff,
        "validation": record.validation,
    }


@router.post("/config/save")
async def save_config(
    payload: SaveRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if not settings.write_enabled:
        raise HTTPException(status_code=403, detail="服务器当前处于只读模式")
    record = preview_store.take(payload.previewToken)
    if not record:
        raise HTTPException(status_code=410, detail="保存预览已过期，请重新生成 Diff")
    source = await source_store(settings).get(record.source_id)
    if not source:
        raise HTTPException(status_code=409, detail="原文件来源已不存在")
    if not is_editable_yaml_path(record.path):
        raise HTTPException(status_code=409, detail="保存目标已超出配置目录")
    service = SaveService(
        build_storage_from_source(source),
        AuditStore(settings.app_data_dir),
    )
    try:
        return await service.commit(record, username="内网访问")
    except SaveCommitError as exc:
        await AuditStore(settings.app_data_dir).record_event(
            source_id=record.source_id, action=record.action, path=record.path,
            status="failure", message=exc.message,
        )
        raise HTTPException(status_code=500, detail=exc.payload()) from exc
    except RuntimeError as exc:
        await AuditStore(settings.app_data_dir).record_event(
            source_id=record.source_id, action=record.action, path=record.path,
            status="failure", message=str(exc),
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        await AuditStore(settings.app_data_dir).record_event(
            source_id=record.source_id, action=record.action, path=record.path,
            status="failure", message=str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        await AuditStore(settings.app_data_dir).record_event(
            source_id=record.source_id, action=record.action, path=record.path,
            status="failure", message="保存失败，暂时无法确认正式文件状态",
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unknown",
                "message": "保存失败，暂时无法确认正式文件状态",
                "nextStep": "请停止继续保存，并核对正式文件哈希及目录内是否存在临时恢复副本。",
                "backupPath": None,
                "formalHash": None,
            },
        ) from exc


@router.get("/history")
async def history(
    sourceId: str = Query(min_length=1, max_length=128),
    path: str = Query(min_length=1, max_length=2048),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(settings, sourceId, path)
    service = SaveService(storage, AuditStore(settings.app_data_dir))
    try:
        backups = await service.list_backups(yaml_path)
    except (FileNotFoundError, ValueError):
        backups = []
    return {
        "backups": backups,
        "audit": await AuditStore(settings.app_data_dir).list_recent(
            source_id=source.id,
            path=yaml_path,
        ),
    }


@router.post("/history/restore-preview")
async def restore_preview(
    payload: RestorePreviewRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(
        settings,
        payload.sourceId,
        payload.path,
    )
    if not is_selected_backup(payload.backupPath, yaml_path):
        raise HTTPException(status_code=422, detail="只能恢复当前主配置 YAML 的历史备份")
    service = SaveService(storage, AuditStore(settings.app_data_dir))
    try:
        record = await service.create_restore_preview(
            path=yaml_path,
            backup_path=payload.backupPath,
            source_id=source.id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="备份文件不存在") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"备份校验失败：{exc}") from exc
    return {
        "previewToken": record.token,
        "beforeHash": record.before_hash,
        "afterHash": record.after_hash,
        "diff": record.diff,
        "validation": record.validation,
    }


@router.delete("/history/backup")
async def delete_history_backup(
    payload: DeleteBackupRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    source, storage, yaml_path = await requested_context(
        settings,
        payload.sourceId,
        payload.path,
    )
    if payload.backupPath == yaml_path or not is_selected_backup(payload.backupPath, yaml_path):
        raise HTTPException(status_code=422, detail="只能删除当前主配置 YAML 的指定历史备份")
    try:
        await storage.delete(payload.backupPath)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="备份文件不存在，可能已被删除") from exc
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"无法删除备份：{exc}") from exc
    except Exception as exc:
        await AuditStore(settings.app_data_dir).record_event(
            source_id=source.id, action="delete-history", path=yaml_path,
            status="failure", message="删除历史备份失败",
        )
        raise HTTPException(status_code=500, detail="删除备份失败，请检查来源连接和目录权限") from exc

    audit_store = AuditStore(settings.app_data_dir)
    removed_records = await audit_store.delete_backup_records(
        source_id=source.id,
        path=yaml_path,
        backup_path=payload.backupPath,
    )
    await audit_store.record_event(
        source_id=source.id, action="delete-history", path=yaml_path,
        status="success", message=f"已删除历史备份 {posixpath.basename(payload.backupPath)}",
    )
    return {
        "deleted": payload.backupPath,
        "removedHistoryRecords": removed_records,
    }


@router.get("/icons/cache")
async def cached_icon(
    url: str = Query(min_length=8, max_length=2048),
    sourceId: str = Query(min_length=1, max_length=128),
    path: str = Query(min_length=1, max_length=2048),
    settings: Settings = Depends(get_settings),
) -> Response:
    source, storage, yaml_path = await requested_context(settings, sourceId, path)
    try:
        await storage.stat(yaml_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="当前 YAML 文件不存在") from exc
    cache = IconCache(settings.app_data_dir)
    audit = AuditStore(settings.app_data_dir)
    try:
        icon = await cache.get(url)
    except IconCacheError as exc:
        if exc.fresh:
            await audit.record_event(
                source_id=source.id,
                action="icon-cache",
                path=yaml_path,
                status="failure",
                message=str(exc),
            )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if icon.status == "stored":
        await audit.record_event(
            source_id=source.id,
            action="icon-cache",
            path=yaml_path,
            status="success",
            message="策略组图标已缓存",
        )
    return Response(
        icon.content,
        media_type=icon.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/icons/catalog")
async def icon_catalog(
    force: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    try:
        return await IconCatalog(
            settings.app_data_dir,
            settings.public_file_base_url,
            settings.storage_root / "icon",
        ).list(force=force)
    except IconCatalogError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/logs")
async def operation_logs(
    sourceId: str | None = Query(default=None, max_length=128),
    path: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=100, ge=1, le=5000),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    records = await AuditStore(settings.app_data_dir).list_recent(
        source_id=sourceId,
        path=path,
        limit=limit,
    )
    sources_by_id = {item.id: item for item in await source_store(settings).list()}
    action_messages = {
        "save": "配置已安全保存",
        "restore": "历史版本已恢复",
    }
    logs = []
    for record in records:
        details = record.get("details") or {}
        source = sources_by_id.get(record["sourceId"])
        logs.append(
            {
                "id": record["id"],
                "createdAt": record["createdAt"],
                "sourceId": record["sourceId"],
                "sourceName": source.name if source else ("系统" if record["sourceId"] == "system" else "未知来源"),
                "sourceType": source.type if source else "system",
                "path": record["path"],
                "fileName": posixpath.basename(record["path"]) or "—",
                "action": record["action"],
                "status": details.get("status", "success"),
                "message": details.get("message") or action_messages.get(record["action"], "操作成功"),
            }
        )
    metadata = await AuditStore(settings.app_data_dir).settings()
    return {"logs": logs, **metadata}


@router.get("/logs/settings")
async def get_log_settings(
    settings: Settings = Depends(get_settings),
) -> dict[str, int]:
    return await AuditStore(settings.app_data_dir).settings()


@router.put("/logs/settings")
async def update_log_settings(
    payload: LogSettingsRequest,
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, int]:
    return await AuditStore(settings.app_data_dir).set_limit(payload.maxEntries)


@router.delete("/logs")
async def clear_operation_logs(
    _: None = Depends(require_internal_request),
    settings: Settings = Depends(get_settings),
) -> dict[str, int]:
    # Intentionally not audited: the postcondition must remain exactly zero rows.
    return await AuditStore(settings.app_data_dir).clear()
