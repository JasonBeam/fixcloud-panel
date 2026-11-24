from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class StorageStat:
    path: str
    size: int
    modified_at: datetime | None
    etag: str
    is_directory: bool = False


@dataclass(slots=True)
class StorageEntry(StorageStat):
    name: str = ""


class StorageBackend(Protocol):
    source_type: str
    display_name: str

    async def status(self) -> dict: ...

    async def list_dir(self, path: str = "/") -> list[StorageEntry]: ...

    async def stat(self, path: str) -> StorageStat: ...

    async def read_bytes(self, path: str) -> bytes: ...

    async def write_bytes(
        self,
        path: str,
        content: bytes,
        *,
        overwrite: bool = False,
    ) -> None: ...

    async def copy(self, source: str, destination: str, *, overwrite: bool = False) -> None: ...

    async def move(self, source: str, destination: str, *, overwrite: bool = False) -> None: ...

    async def delete(self, path: str) -> None: ...
