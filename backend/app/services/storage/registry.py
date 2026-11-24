from pathlib import Path
from urllib.parse import quote, urljoin

from app.core.settings import Settings
from app.services.source_store import SourceRecord, normalize_directory

from .base import StorageBackend
from .mounted import MountedFilesystemStorage
from .smb import SmbStorage
from .webdav import WebDavStorage
from app.services.browser_session import current_directory


def build_primary_storage(settings: Settings) -> StorageBackend:
    if settings.storage_backend == "smb-mounted":
        return MountedFilesystemStorage(settings.storage_root)
    if settings.storage_backend == "webdav":
        return WebDavStorage(
            settings.webdav_url,
            settings.webdav_username,
            settings.webdav_password,
        )
    if settings.storage_backend == "local":
        return MountedFilesystemStorage(settings.storage_root, display_name="本地测试目录")
    raise ValueError(f"不支持的存储后端：{settings.storage_backend}")


def build_available_storages(settings: Settings) -> list[StorageBackend]:
    sources: list[StorageBackend] = [build_primary_storage(settings)]
    if settings.webdav_url and settings.storage_backend != "webdav":
        sources.append(
            WebDavStorage(
                settings.webdav_url,
                settings.webdav_username,
                settings.webdav_password,
            )
        )
    return sources


def _join_directory(*values: object) -> str:
    return "/".join(
        part
        for value in values
        for part in normalize_directory(value).split("/")
        if part
    )


def build_storage_from_source(
    source: SourceRecord,
    *,
    include_config_directory: bool = True,
) -> StorageBackend:
    if source.type == "smb-mounted":
        return MountedFilesystemStorage(
            Path(str(source.config["root"])),
            display_name=source.name,
        )
    if source.type == "upload":
        storage = MountedFilesystemStorage(
            current_directory(),
            display_name=source.name,
        )
        storage.source_type = "upload"
        return storage
    if source.type == "smb":
        root_directory = source.config.get(
            "rootDirectory",
            source.config.get("subdirectory", ""),
        )
        scoped_directory = _join_directory(
            root_directory,
            source.config.get("configDirectory", "config")
            if include_config_directory
            else "",
        )
        return SmbStorage(
            server=str(source.config.get("server", "")),
            share=str(source.config.get("share", "")),
            username=str(source.config.get("username", "")),
            password=str(source.config.get("password", "")),
            subdirectory=scoped_directory,
            display_name=source.name,
        )
    if source.type == "webdav":
        root_directory = _join_directory(
            source.config.get("rootDirectory", ""),
            source.config.get("configDirectory", "config")
            if include_config_directory
            else "",
        )
        base_url = str(source.config.get("url", "")).rstrip("/") + "/"
        if root_directory:
            encoded_root = "/".join(quote(part) for part in root_directory.split("/") if part)
            base_url = urljoin(base_url, encoded_root + "/")
        return WebDavStorage(
            base_url,
            str(source.config.get("username", "")),
            str(source.config.get("password", "")),
            display_name=source.name,
        )
    raise ValueError(f"不支持的存储后端：{source.type}")
