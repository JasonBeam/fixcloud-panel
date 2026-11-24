from __future__ import annotations

import hashlib
import posixpath
import secrets
import time
from dataclasses import dataclass
from typing import Any

from app.services.audit import AuditStore
from app.services.storage.base import StorageBackend
from app.services.yaml_service import YamlService
from app.services.browser_session import current_scope


@dataclass(slots=True)
class PreviewRecord:
    token: str
    created_at: float
    path: str
    before_hash: str
    after_hash: str
    candidate: bytes
    operations_count: int
    validation: dict[str, list[str]]
    diff: dict[str, Any]
    action: str = "save"
    source_id: str = "default-smb"
    session_scope: str = ""


class PreviewStore:
    def __init__(self) -> None:
        self._records: dict[str, PreviewRecord] = {}

    def put(self, record: PreviewRecord) -> None:
        self.cleanup()
        self._records[record.token] = record

    def take(self, token: str) -> PreviewRecord | None:
        self.cleanup()
        record = self._records.get(token)
        if not record or record.session_scope != current_scope():
            return None
        return self._records.pop(token, None)

    def cleanup(self) -> None:
        cutoff = time.time() - 900
        stale = [token for token, record in self._records.items() if record.created_at < cutoff]
        for token in stale:
            self._records.pop(token, None)


preview_store = PreviewStore()


class SaveCommitError(RuntimeError):
    def __init__(
        self,
        *,
        status: str,
        message: str,
        next_step: str,
        backup_path: str | None,
        formal_hash: str | None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.next_step = next_step
        self.backup_path = backup_path
        self.formal_hash = formal_hash

    def payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "nextStep": self.next_step,
            "backupPath": self.backup_path,
            "formalHash": self.formal_hash,
        }


class SaveService:
    def __init__(self, storage: StorageBackend, audit: AuditStore):
        self.storage = storage
        self.audit = audit
        self.yaml = YamlService()

    @staticmethod
    def _hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def create_preview(
        self,
        *,
        path: str,
        source_id: str,
        base_hash: str,
        operations: list[dict[str, Any]],
    ) -> PreviewRecord:
        current = await self.storage.read_bytes(path)
        current_hash = self._hash(current)
        if current_hash != base_hash:
            raise RuntimeError("配置文件已在其他位置发生变化，请重新加载后再修改")
        document = self.yaml.load(current)
        self.yaml.apply_operations(document, operations)
        candidate = self.yaml.dump_candidate(document)
        validation = self.yaml.validate_references(self.yaml.load(candidate))
        diff = self.yaml.full_diff(current, candidate)
        token = secrets.token_urlsafe(32)
        record = PreviewRecord(
            token=token,
            created_at=time.time(),
            path=path,
            before_hash=current_hash,
            after_hash=self._hash(candidate),
            candidate=candidate,
            operations_count=len(operations),
            validation=validation,
            diff=diff,
            source_id=source_id,
            session_scope=current_scope(),
        )
        preview_store.put(record)
        return record

    async def create_raw_preview(
        self,
        *,
        path: str,
        source_id: str,
        base_hash: str,
        content: bytes,
    ) -> PreviewRecord:
        current = await self.storage.read_bytes(path)
        current_hash = self._hash(current)
        if current_hash != base_hash:
            raise RuntimeError("配置文件已在其他位置发生变化，请重新加载后再修改")
        # Advanced mode keeps the exact bytes entered by the user. ruamel in
        # round-trip mode validates the candidate but never auto-formats it.
        document = self.yaml.load(content)
        validation = self.yaml.validate_references(document)
        record = PreviewRecord(
            token=secrets.token_urlsafe(32),
            created_at=time.time(),
            path=path,
            before_hash=current_hash,
            after_hash=self._hash(content),
            candidate=content,
            operations_count=1,
            validation=validation,
            diff=self.yaml.full_diff(current, content),
            action="advanced-save",
            source_id=source_id,
            session_scope=current_scope(),
        )
        preview_store.put(record)
        return record

    async def create_restore_preview(
        self,
        *,
        path: str,
        backup_path: str,
        source_id: str,
    ) -> PreviewRecord:
        current = await self.storage.read_bytes(path)
        backup = await self.storage.read_bytes(backup_path)
        restored_document = self.yaml.load(backup)
        validation = self.yaml.validate_references(restored_document)
        candidate = backup
        token = secrets.token_urlsafe(32)
        record = PreviewRecord(
            token=token,
            created_at=time.time(),
            path=path,
            before_hash=self._hash(current),
            after_hash=self._hash(candidate),
            candidate=candidate,
            operations_count=1,
            validation=validation,
            diff=self.yaml.full_diff(current, candidate),
            action="restore",
            source_id=source_id,
            session_scope=current_scope(),
        )
        preview_store.put(record)
        return record

    async def _read_hash(self, path: str) -> str | None:
        try:
            return self._hash(await self.storage.read_bytes(path))
        except Exception:
            return None

    async def _delete_quietly(self, path: str) -> bool:
        try:
            await self.storage.delete(path)
            return True
        except FileNotFoundError:
            return True
        except Exception:
            return False

    async def commit(self, record: PreviewRecord, *, username: str) -> dict[str, Any]:
        current = await self.storage.read_bytes(record.path)
        if self._hash(current) != record.before_hash:
            raise RuntimeError("正式文件已变化，本次保存已取消")
        if record.validation["errors"]:
            raise ValueError("配置引用检查未通过")

        directory = posixpath.dirname(record.path) or "/"
        filename = posixpath.basename(record.path)
        rollback_path = posixpath.join(
            directory,
            f".{filename}.rollback-{secrets.token_hex(8)}.yaml",
        )
        temporary_path = posixpath.join(
            directory,
            f".{filename}.tmp-{secrets.token_hex(8)}.yaml",
        )
        recovery_path = posixpath.join(
            directory,
            f".{filename}.recovery-{secrets.token_hex(8)}.yaml",
        )
        rollback_ready = False

        try:
            await self.storage.write_bytes(rollback_path, current, overwrite=False)
            rollback = await self.storage.read_bytes(rollback_path)
            self.yaml.load(rollback)
            if self._hash(rollback) != record.before_hash:
                raise RuntimeError("临时恢复副本哈希与保存前不一致")
            rollback_ready = True

            await self.storage.write_bytes(temporary_path, record.candidate, overwrite=False)

            uploaded = await self.storage.read_bytes(temporary_path)
            self.yaml.load(uploaded)
            if self._hash(uploaded) != record.after_hash:
                raise RuntimeError("临时文件回读校验失败")

            await self.storage.move(temporary_path, record.path, overwrite=True)
            persisted = await self.storage.read_bytes(record.path)
            self.yaml.load(persisted)
            if self._hash(persisted) != record.after_hash:
                raise RuntimeError("正式文件回读校验失败")
        except Exception as original_error:
            await self._delete_quietly(temporary_path)

            formal_hash = await self._read_hash(record.path)
            if formal_hash == record.before_hash:
                rollback_cleaned = await self._delete_quietly(rollback_path)
                raise SaveCommitError(
                    status="unchanged",
                    message="保存失败，正式文件未被替换",
                    next_step="请检查来源连接后重新生成 Diff 再试。",
                    backup_path=rollback_path if rollback_ready and not rollback_cleaned else None,
                    formal_hash=formal_hash,
                ) from original_error

            if rollback_ready:
                try:
                    rollback = await self.storage.read_bytes(rollback_path)
                    self.yaml.load(rollback)
                    if self._hash(rollback) != record.before_hash:
                        raise RuntimeError("临时恢复副本哈希与保存前不一致")
                    await self.storage.write_bytes(recovery_path, rollback, overwrite=False)
                    recovery = await self.storage.read_bytes(recovery_path)
                    if self._hash(recovery) != record.before_hash:
                        raise RuntimeError("恢复文件哈希不一致")
                    await self.storage.move(recovery_path, record.path, overwrite=True)
                    restored_hash = await self._read_hash(record.path)
                    if restored_hash == record.before_hash:
                        rollback_cleaned = await self._delete_quietly(rollback_path)
                        raise SaveCommitError(
                            status="restored",
                            message="保存失败，正式文件已从临时恢复副本还原",
                            next_step="正式文件已恢复到保存前版本。请检查来源连接后重新生成 Diff。",
                            backup_path=rollback_path if not rollback_cleaned else None,
                            formal_hash=restored_hash,
                        ) from original_error
                    formal_hash = restored_hash
                except SaveCommitError:
                    raise
                except Exception:
                    formal_hash = await self._read_hash(record.path)
                finally:
                    await self._delete_quietly(recovery_path)

            raise SaveCommitError(
                status="recovery_failed",
                message="保存失败，自动恢复未能确认",
                next_step="请立即停止继续保存，并使用保留的临时恢复副本人工核对或恢复正式配置。",
                backup_path=rollback_path if rollback_ready else None,
                formal_hash=formal_hash,
            ) from original_error

        rollback_cleaned = await self._delete_quietly(rollback_path)
        await self.audit.record(
            source_id=record.source_id,
            username=username,
            action=record.action,
            path=record.path,
            before_hash=record.before_hash,
            after_hash=record.after_hash,
            backup_path=None,
            details={
                "operations": record.operations_count,
                "changedLines": record.diff["changedLines"],
                "warnings": len(record.validation["warnings"]),
                "temporaryRecoveryCleaned": rollback_cleaned,
            },
        )
        return {
            "path": record.path,
            "backupPath": None,
            "beforeHash": record.before_hash,
            "afterHash": record.after_hash,
            "temporaryRecoveryCleaned": rollback_cleaned,
        }

    async def list_backups(self, path: str) -> list[dict[str, Any]]:
        directory = posixpath.dirname(path) or "/"
        filename = posixpath.basename(path)
        prefix = f"{filename}.backup-"
        entries = await self.storage.list_dir(directory)
        backups = [
            {
                "name": entry.name,
                "path": entry.path,
                "size": entry.size,
                "modifiedAt": entry.modified_at,
                "etag": entry.etag,
            }
            for entry in entries
            if not entry.is_directory
            and entry.name.startswith(prefix)
            and entry.name.endswith(".yaml")
        ]
        backups.sort(key=lambda item: item["name"], reverse=True)
        return backups
