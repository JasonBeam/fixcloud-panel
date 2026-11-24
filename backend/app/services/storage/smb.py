from __future__ import annotations

import asyncio
import hashlib
import ntpath
from datetime import datetime, timezone

import smbclient

from .base import StorageEntry, StorageStat


class SmbStorage:
    source_type = "smb"

    def __init__(
        self,
        server: str,
        share: str,
        username: str,
        password: str,
        subdirectory: str = "",
        display_name: str = "SMB",
    ):
        self.server = server.strip()
        self.share = share.strip().strip("\\/")
        self.username = username
        self.password = password
        self.subdirectory = subdirectory.strip().strip("\\/")
        self.display_name = display_name

    def _register(self) -> None:
        smbclient.register_session(
            self.server,
            username=self.username or None,
            password=self.password or None,
            connection_timeout=8,
        )

    def _resolve(self, path: str) -> str:
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        if any(part in {".", ".."} for part in parts):
            raise ValueError("路径超出已配置的 SMB 根目录")
        root = rf"\\{self.server}\{self.share}"
        if self.subdirectory:
            root = ntpath.join(root, self.subdirectory.replace("/", "\\"))
        return ntpath.join(root, *parts)

    @property
    def root_label(self) -> str:
        suffix = f"/{self.subdirectory}" if self.subdirectory else ""
        return f"//{self.server}/{self.share}{suffix}"

    async def status(self) -> dict:
        try:
            def probe() -> None:
                self._register()
                with smbclient.scandir(self._resolve("/")) as entries:
                    next(iter(entries), None)

            await asyncio.wait_for(asyncio.to_thread(probe), timeout=10)
            return {
                "type": self.source_type,
                "name": self.display_name,
                "connected": True,
                "readOnly": False,
                "root": self.root_label,
                "message": "已连接",
                "reasonCode": "ok",
            }
        except asyncio.TimeoutError:
            return {
                "type": self.source_type,
                "name": self.display_name,
                "connected": False,
                "readOnly": True,
                "root": self.root_label,
                "message": "连接超时",
                "reasonCode": "timeout",
            }
        except Exception as exc:
            message = str(exc).lower()
            if "logon failure" in message or "access denied" in message:
                reason, text = "authentication", "认证失败"
            elif "object_name_not_found" in message or "bad network name" in message:
                reason, text = "not_found", "共享目录不存在"
            else:
                reason, text = "connection", "无法连接 SMB"
            return {
                "type": self.source_type,
                "name": self.display_name,
                "connected": False,
                "readOnly": True,
                "root": self.root_label,
                "message": text,
                "reasonCode": reason,
            }

    async def list_dir(self, path: str = "/") -> list[StorageEntry]:
        directory = self._resolve(path)

        def scan() -> list[StorageEntry]:
            self._register()
            entries: list[StorageEntry] = []
            with smbclient.scandir(directory) as items:
                for item in items:
                    if item.name.startswith("._") or item.name in {".DS_Store", "@eaDir"}:
                        continue
                    stat = item.stat()
                    relative = "/" + "/".join(
                        part for part in [path.strip("/"), item.name] if part
                    )
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
            entries.sort(key=lambda item: (not item.is_directory, item.name.lower()))
            return entries

        return await asyncio.to_thread(scan)

    async def stat(self, path: str) -> StorageStat:
        def inspect() -> StorageStat:
            self._register()
            stat = smbclient.stat(self._resolve(path))
            return StorageStat(
                path=path,
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                etag=f'W/"{stat.st_mtime_ns:x}-{stat.st_size:x}"',
                is_directory=False,
            )

        return await asyncio.to_thread(inspect)

    async def read_bytes(self, path: str) -> bytes:
        def read() -> bytes:
            self._register()
            with smbclient.open_file(self._resolve(path), mode="rb") as handle:
                return handle.read()

        return await asyncio.to_thread(read)

    async def content_hash(self, path: str) -> str:
        return hashlib.sha256(await self.read_bytes(path)).hexdigest()

    async def write_bytes(
        self,
        path: str,
        content: bytes,
        *,
        overwrite: bool = False,
    ) -> None:
        def write() -> None:
            self._register()
            mode = "wb" if overwrite else "xb"
            with smbclient.open_file(self._resolve(path), mode=mode) as handle:
                handle.write(content)
                handle.flush()

        await asyncio.to_thread(write)

    async def copy(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        content = await self.read_bytes(source)
        await self.write_bytes(destination, content, overwrite=overwrite)

    async def move(self, source: str, destination: str, *, overwrite: bool = False) -> None:
        def move_file() -> None:
            self._register()
            source_path = self._resolve(source)
            destination_path = self._resolve(destination)
            if overwrite:
                smbclient.replace(source_path, destination_path)
            else:
                smbclient.rename(source_path, destination_path)

        await asyncio.to_thread(move_file)

    async def delete(self, path: str) -> None:
        def remove() -> None:
            self._register()
            try:
                smbclient.remove(self._resolve(path))
            except FileNotFoundError:
                pass

        await asyncio.to_thread(remove)
