from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.settings import Settings


SENSITIVE_FIELDS = {"username", "password"}
SUPPORTED_SOURCE_TYPES = {"smb-mounted", "smb", "webdav", "upload"}
DEFAULT_CONFIG_DIRECTORY = "config"


def normalize_directory(value: Any, *, default: str = "") -> str:
    raw = str(value or default).strip().replace("\\", "/")
    if raw in {"/", "."}:
        return "/"
    parts = [part for part in raw.split("/") if part and part != "."]
    if any(part == ".." or "\x00" in part for part in parts):
        raise ValueError("目录不能包含 .. 或无效字符")
    return "/".join(parts)


@dataclass(slots=True)
class SourceRecord:
    id: str
    type: str
    name: str
    config: dict[str, Any]
    built_in: bool = False

    def safe_data(self) -> dict[str, Any]:
        config = {
            key: value
            for key, value in self.config.items()
            if key not in SENSITIVE_FIELDS
        }
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "builtIn": self.built_in,
            "config": config,
        }


class SourceStore:
    def __init__(self, data_dir: Path, settings: Settings):
        self.path = data_dir / "sources.json"
        self.settings = settings

    def _defaults(self) -> list[SourceRecord]:
        return [
            SourceRecord(
                id="default-smb",
                type="smb-mounted",
                name="NAS SMB",
                config={
                    "root": str(self.settings.storage_root),
                    "configDirectory": DEFAULT_CONFIG_DIRECTORY,
                    "mountedConfigRoot": True,
                },
                built_in=True,
            ),
            SourceRecord(
                id="uploaded-files",
                type="upload",
                name="已上传文件",
                config={
                    "root": "browser-session",
                    "configDirectory": "/",
                    "mountedConfigRoot": True,
                },
                built_in=True,
            ),
        ]

    @staticmethod
    def _decode(payload: dict[str, Any]) -> SourceRecord:
        source_type = str(payload.get("type", ""))
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise ValueError("不支持的文件来源类型")
        return SourceRecord(
            id=str(payload["id"]),
            type=source_type,
            name=str(payload.get("name") or source_type),
            config=dict(payload.get("config") or {}),
            built_in=bool(payload.get("builtIn", False)),
        )

    def _read(self) -> list[SourceRecord]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            decoded = [self._decode(item) for item in payload.get("sources", [])]
            records: list[SourceRecord] = []
            changed = False
            for record in decoded:
                if record.id == "default-webdav" and record.built_in:
                    changed = True
                    continue
                config = dict(record.config)
                if not config.get("configDirectory"):
                    config["configDirectory"] = (
                        DEFAULT_CONFIG_DIRECTORY if record.id == "default-smb" else "/"
                    )
                    changed = True
                if record.type == "smb" and "rootDirectory" not in config:
                    config["rootDirectory"] = str(config.get("subdirectory", ""))
                    changed = True
                if record.id == "default-smb":
                    if not config.get("mountedConfigRoot"):
                        config["mountedConfigRoot"] = True
                        changed = True
                    record = SourceRecord(
                        id=record.id,
                        type="smb-mounted",
                        name=record.name,
                        config=config,
                        built_in=True,
                    )
                else:
                    record = SourceRecord(
                        id=record.id,
                        type=record.type,
                        name=record.name,
                        config=config,
                        built_in=record.built_in,
                    )
                records.append(record)
            if not any(record.id == "default-smb" for record in records):
                records.insert(0, self._defaults()[0])
                changed = True
            if not any(record.id == "uploaded-files" for record in records):
                records.append(self._defaults()[1])
                changed = True
            if records:
                if changed:
                    self._write(records)
                return records
        except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError, ValueError):
            pass
        defaults = self._defaults()
        self._write(defaults)
        return defaults

    def _write(self, records: list[SourceRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f".tmp-{secrets.token_hex(4)}")
        data = {
            "sources": [
                {
                    "id": item.id,
                    "type": item.type,
                    "name": item.name,
                    "config": item.config,
                    "builtIn": item.built_in,
                }
                for item in records
            ]
        }
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    async def list(self) -> list[SourceRecord]:
        return await asyncio.to_thread(self._read)

    async def get(self, source_id: str) -> SourceRecord | None:
        return next((item for item in await self.list() if item.id == source_id), None)

    async def create(self, source_type: str, name: str, config: dict[str, Any]) -> SourceRecord:
        records = await self.list()
        record = SourceRecord(
            id=f"source-{secrets.token_urlsafe(9)}",
            type=source_type,
            name=name.strip(),
            config={
                **dict(config),
                "configDirectory": normalize_directory(
                    config.get("configDirectory"),
                    default=DEFAULT_CONFIG_DIRECTORY,
                ),
            },
        )
        records.append(record)
        await asyncio.to_thread(self._write, records)
        return record

    async def update(
        self,
        source_id: str,
        source_type: str,
        name: str,
        config: dict[str, Any],
    ) -> SourceRecord:
        records = await self.list()
        for index, existing in enumerate(records):
            if existing.id != source_id:
                continue
            merged = dict(existing.config)
            for key, value in config.items():
                if key in SENSITIVE_FIELDS and value in {"", None}:
                    continue
                merged[key] = value
            merged["configDirectory"] = normalize_directory(
                merged.get("configDirectory"),
                default=DEFAULT_CONFIG_DIRECTORY,
            )
            updated = SourceRecord(
                id=existing.id,
                type=source_type,
                name=name.strip(),
                config=merged,
                built_in=existing.built_in,
            )
            records[index] = updated
            await asyncio.to_thread(self._write, records)
            return updated
        raise KeyError(source_id)

    async def delete(self, source_id: str) -> None:
        records = await self.list()
        remaining = [item for item in records if item.id != source_id]
        if len(remaining) == len(records):
            raise KeyError(source_id)
        if not remaining:
            raise ValueError("至少保留一个文件来源")
        await asyncio.to_thread(self._write, remaining)

    async def merged_candidate(
        self,
        source_id: str | None,
        source_type: str,
        name: str,
        config: dict[str, Any],
    ) -> SourceRecord:
        if source_id:
            existing = await self.get(source_id)
            if not existing:
                raise KeyError(source_id)
            merged = dict(existing.config)
            for key, value in config.items():
                if key in SENSITIVE_FIELDS and value in {"", None}:
                    continue
                merged[key] = value
            merged["configDirectory"] = normalize_directory(
                merged.get("configDirectory"),
                default=DEFAULT_CONFIG_DIRECTORY,
            )
            return SourceRecord(existing.id, source_type, name.strip(), merged, existing.built_in)
        candidate_config = dict(config)
        candidate_config["configDirectory"] = normalize_directory(
            candidate_config.get("configDirectory"),
            default=DEFAULT_CONFIG_DIRECTORY,
        )
        return SourceRecord("probe", source_type, name.strip(), candidate_config)


@dataclass(slots=True)
class ProbeRecord:
    token: str
    expires_at: float
    fingerprint: str


class ProbeStore:
    def __init__(self) -> None:
        self._records: dict[str, ProbeRecord] = {}

    @staticmethod
    def fingerprint(record: SourceRecord) -> str:
        raw = json.dumps(
            {"type": record.type, "name": record.name, "config": record.config},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def issue(self, record: SourceRecord) -> str:
        self.cleanup()
        token = secrets.token_urlsafe(28)
        self._records[token] = ProbeRecord(
            token=token,
            expires_at=time.time() + 600,
            fingerprint=self.fingerprint(record),
        )
        return token

    def consume(self, token: str, record: SourceRecord) -> bool:
        self.cleanup()
        probe = self._records.pop(token, None)
        return bool(probe and secrets.compare_digest(probe.fingerprint, self.fingerprint(record)))

    def cleanup(self) -> None:
        now = time.time()
        for token in [key for key, value in self._records.items() if value.expires_at < now]:
            self._records.pop(token, None)


probe_store = ProbeStore()
