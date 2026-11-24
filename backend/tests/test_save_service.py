from pathlib import Path
import pytest

from app.services.audit import AuditStore
from app.services.save_service import SaveCommitError, SaveService
from app.services.storage.mounted import MountedFilesystemStorage


SOURCE = b"""# keep this comment
port: 7890
secret: very-private
proxies:
  - name: Local
    type: socks5
    server: 127.0.0.1
    port: 7891
proxy-groups:
  - name: Proxy
    type: select
    proxies:
      - Local
rules:
  - MATCH,Proxy
experimental:
  keep-me: true
"""


@pytest.mark.asyncio
async def test_safe_save_removes_temporary_recovery_and_preserves_unknown_fields(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE)
    config.chmod(0o666)
    storage = MountedFilesystemStorage(tmp_path)
    service = SaveService(storage, AuditStore(tmp_path / "data"))

    preview = await service.create_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(SOURCE),
        operations=[{"op": "set", "path": ["port"], "value": 7892}],
    )
    assert "7892" in preview.diff["text"]
    assert preview.diff["changedLines"] == 2

    result = await service.commit(preview, username="内网访问")
    persisted = config.read_text()
    assert "# keep this comment" in persisted
    assert "port: 7892" in persisted
    assert "keep-me: true" in persisted
    assert config.stat().st_mode & 0o777 == 0o666
    assert result["backupPath"] is None
    assert result["temporaryRecoveryCleaned"] is True
    assert not list(tmp_path.glob("FixCloud.yaml.backup-*.yaml"))
    assert not list(tmp_path.glob(".*.rollback-*.yaml"))


@pytest.mark.asyncio
async def test_advanced_raw_preview_preserves_exact_candidate_bytes(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE)
    service = SaveService(MountedFilesystemStorage(tmp_path), AuditStore(tmp_path / "data"))
    candidate = SOURCE.replace(b"port: 7890", b"port: 7901  # directly edited")

    preview = await service.create_raw_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(SOURCE),
        content=candidate,
    )

    assert preview.candidate == candidate
    assert "directly edited" in preview.diff["text"]
    assert preview.validation["errors"] == []


@pytest.mark.asyncio
async def test_conflict_stops_before_backup(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE)
    storage = MountedFilesystemStorage(tmp_path)
    service = SaveService(storage, AuditStore(tmp_path / "data"))
    preview = await service.create_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(SOURCE),
        operations=[{"op": "set", "path": ["port"], "value": 7893}],
    )
    config.write_bytes(SOURCE.replace(b"7890", b"7888"))

    with pytest.raises(RuntimeError, match="正式文件已变化"):
        await service.commit(preview, username="内网访问")
    assert not list(tmp_path.glob("*.backup-*.yaml"))


class CorruptAfterReplaceStorage(MountedFilesystemStorage):
    async def move(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        await super().move(source, destination, overwrite=overwrite)
        if ".tmp-" in source and destination == "/FixCloud.yaml":
            self._resolve(destination).write_bytes(b"not: [valid")


class FailTemporaryWriteStorage(MountedFilesystemStorage):
    async def write_bytes(self, path: str, content: bytes, *, overwrite: bool = False) -> None:
        if ".tmp-" in path:
            raise OSError("simulated temporary upload failure")
        await super().write_bytes(path, content, overwrite=overwrite)


class FailRecoveryStorage(CorruptAfterReplaceStorage):
    async def move(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        if ".recovery-" in source:
            raise OSError("simulated recovery replacement failure")
        await super().move(source, destination, overwrite=overwrite)


@pytest.mark.asyncio
async def test_failed_upload_reports_formal_file_unchanged(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE)
    storage = FailTemporaryWriteStorage(tmp_path)
    service = SaveService(storage, AuditStore(tmp_path / "data"))
    preview = await service.create_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(SOURCE),
        operations=[{"op": "set", "path": ["port"], "value": 7894}],
    )

    with pytest.raises(SaveCommitError) as error:
        await service.commit(preview, username="内网访问")
    assert error.value.status == "unchanged"
    assert error.value.formal_hash == service._hash(SOURCE)
    assert config.read_bytes() == SOURCE
    assert error.value.backup_path is None
    assert not list(tmp_path.glob(".*.rollback-*.yaml"))


@pytest.mark.asyncio
async def test_failed_readback_restores_original(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE)
    storage = CorruptAfterReplaceStorage(tmp_path)
    service = SaveService(storage, AuditStore(tmp_path / "data"))
    preview = await service.create_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(SOURCE),
        operations=[{"op": "set", "path": ["port"], "value": 7894}],
    )

    with pytest.raises(SaveCommitError) as error:
        await service.commit(preview, username="内网访问")
    assert error.value.status == "restored"
    assert config.read_bytes() == SOURCE
    assert not list(tmp_path.glob(".*.tmp-*.yaml"))
    assert not list(tmp_path.glob(".*.recovery-*.yaml"))
    assert not list(tmp_path.glob(".*.rollback-*.yaml"))


@pytest.mark.asyncio
async def test_failed_recovery_reports_manual_intervention(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE)
    storage = FailRecoveryStorage(tmp_path)
    service = SaveService(storage, AuditStore(tmp_path / "data"))
    preview = await service.create_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(SOURCE),
        operations=[{"op": "set", "path": ["port"], "value": 7894}],
    )

    with pytest.raises(SaveCommitError) as error:
        await service.commit(preview, username="内网访问")
    assert error.value.status == "recovery_failed"
    assert error.value.backup_path is not None
    assert ".rollback-" in error.value.backup_path
    assert error.value.formal_hash != service._hash(SOURCE)
    assert config.read_bytes() != SOURCE
    assert (tmp_path / error.value.backup_path.lstrip("/")).read_bytes() == SOURCE
    assert not list(tmp_path.glob(".*.recovery-*.yaml"))


@pytest.mark.asyncio
async def test_restore_preview_uses_original_backup_bytes(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE.replace(b"7890", b"7800"))
    backup = tmp_path / "FixCloud.yaml.backup-20260726-120000.yaml"
    original_backup = SOURCE.replace(b"port: 7890", b"port: 7890  # exact backup spacing")
    backup.write_bytes(original_backup)
    storage = MountedFilesystemStorage(tmp_path)
    service = SaveService(storage, AuditStore(tmp_path / "data"))

    preview = await service.create_restore_preview(
        path="/FixCloud.yaml",
        backup_path=f"/{backup.name}",
        source_id="test",
    )

    assert preview.candidate == original_backup


@pytest.mark.asyncio
async def test_repeated_saves_do_not_leave_backup_files(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(SOURCE)
    storage = MountedFilesystemStorage(tmp_path)
    service = SaveService(storage, AuditStore(tmp_path / "data"))

    first = await service.create_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(SOURCE),
        operations=[{"op": "set", "path": ["port"], "value": 7895}],
    )
    first_result = await service.commit(first, username="内网访问")
    current = config.read_bytes()
    second = await service.create_preview(
        path="/FixCloud.yaml",
        source_id="test",
        base_hash=service._hash(current),
        operations=[{"op": "set", "path": ["port"], "value": 7896}],
    )
    second_result = await service.commit(second, username="内网访问")

    assert first_result["backupPath"] is None
    assert second_result["backupPath"] is None
    assert b"port: 7896" in config.read_bytes()
    assert not list(tmp_path.glob("FixCloud.yaml.backup-*.yaml"))
    assert not list(tmp_path.glob(".*.rollback-*.yaml"))
