import asyncio
import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .base import StorageEntry, StorageStat


class MountedFilesystemStorage:
    source_type = "smb-mounted"

    def __init__(self, root: Path, display_name: str = "NAS SMB"):
        self.root = root
        self.display_name = display_name

    def _resolve(self, path: str) -> Path:
        relative = path.lstrip("/")
        candidate = (self.root / relative).resolve()
        root = self.root.resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("路径超出已配置的 SMB 根目录")
        return candidate

    async def status(self) -> dict:
        exists = await asyncio.to_thread(self.root.is_dir)
        writable = exists and await asyncio.to_thread(os.access, self.root, os.W_OK)
        return {
            "type": self.source_type,
            "name": self.display_name,
            "connected": exists,
            "readOnly": not writable,
            "root": str(self.root),
            "message": "已连接" if exists else "挂载目录不可用",
            "reasonCode": "ok" if exists else "not_found",
        }

    async def list_dir(self, path: str = "/") -> list[StorageEntry]:
        directory = self._resolve(path)

        def scan() -> list[StorageEntry]:
            if not directory.is_dir():
                raise FileNotFoundError(path)
            entries: list[StorageEntry] = []
            for item in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if item.name.startswith("._") or item.name in {".DS_Store", "@eaDir"}:
                    continue
                stat = item.stat()
                relative = "/" + item.relative_to(self.root).as_posix()
                entries.append(
                    StorageEntry(
                        path=relative,
                        name=item.name,
                        size=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                        etag=f'W/"{stat.st_mtime_ns:x}-{stat.st_size:x}"',
                        is_directory=item.is_dir(),
                    )
                )
            return entries

        return await asyncio.to_thread(scan)

    async def stat(self, path: str) -> StorageStat:
        file_path = self._resolve(path)

        def inspect() -> StorageStat:
            stat = file_path.stat()
            return StorageStat(
                path=path,
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                etag=f'W/"{stat.st_mtime_ns:x}-{stat.st_size:x}"',
                is_directory=file_path.is_dir(),
            )

        return await asyncio.to_thread(inspect)

    async def read_bytes(self, path: str) -> bytes:
        file_path = self._resolve(path)
        return await asyncio.to_thread(file_path.read_bytes)

    async def content_hash(self, path: str) -> str:
        content = await self.read_bytes(path)
        return hashlib.sha256(content).hexdigest()

    async def write_bytes(
        self,
        path: str,
        content: bytes,
        *,
        overwrite: bool = False,
    ) -> None:
        file_path = self._resolve(path)

        def write() -> None:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT
            flags |= os.O_TRUNC if overwrite else os.O_EXCL
            descriptor = os.open(file_path, flags, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    file_path.unlink(missing_ok=True)
                finally:
                    raise

        await asyncio.to_thread(write)

    async def copy(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        source_path = self._resolve(source)
        destination_path = self._resolve(destination)

        def copy_file() -> None:
            if destination_path.exists() and not overwrite:
                raise FileExistsError(destination)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "wb" if overwrite else "xb"
            with source_path.open("rb") as reader, destination_path.open(mode) as writer:
                shutil.copyfileobj(reader, writer)
                writer.flush()
                os.fsync(writer.fileno())

        await asyncio.to_thread(copy_file)

    async def move(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        source_path = self._resolve(source)
        destination_path = self._resolve(destination)

        def move_file() -> None:
            destination_mode = None
            if overwrite and destination_path.exists():
                destination_mode = destination_path.stat().st_mode & 0o777
            if destination_path.exists() and not overwrite:
                raise FileExistsError(destination)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if overwrite:
                os.replace(source_path, destination_path)
            else:
                os.rename(source_path, destination_path)
            if destination_mode is not None:
                os.chmod(destination_path, destination_mode)

        await asyncio.to_thread(move_file)

    async def delete(self, path: str) -> None:
        file_path = self._resolve(path)
        await asyncio.to_thread(file_path.unlink, missing_ok=True)
