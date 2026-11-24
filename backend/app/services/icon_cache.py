from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import socket
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx


MAX_ICON_BYTES = 1024 * 1024
FAILURE_TTL_SECONDS = 600
FAKE_IP_BENCHMARK_NETWORK = ipaddress.ip_network("198.18.0.0/15")
_PROCESS_LOCKS_GUARD = threading.Lock()
_PROCESS_LOCKS: dict[str, asyncio.Lock] = {}


def _shared_lock(key: str) -> asyncio.Lock:
    with _PROCESS_LOCKS_GUARD:
        return _PROCESS_LOCKS.setdefault(key, asyncio.Lock())


@dataclass(slots=True)
class CachedIcon:
    content: bytes
    content_type: str
    status: str


class IconCacheError(ValueError):
    def __init__(self, message: str, *, fresh: bool = True) -> None:
        super().__init__(message)
        self.fresh = fresh


class IconCache:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "icon-cache"

    @staticmethod
    def _digest(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _paths(self, digest: str) -> tuple[Path, Path, Path]:
        return (
            self.root / f"{digest}.bin",
            self.root / f"{digest}.json",
            self.root / f"{digest}.failed.json",
        )

    @staticmethod
    async def _validate_public_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise IconCacheError("图标 URL 格式无效")
        try:
            addresses = await asyncio.to_thread(
                socket.getaddrinfo,
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise IconCacheError("图标域名无法解析") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            # Mihomo/Clash Fake-IP mode intentionally answers public hostnames from
            # RFC 2544's benchmark range. Permit only that exact compatibility range.
            if not ip.is_global and ip not in FAKE_IP_BENCHMARK_NETWORK:
                raise IconCacheError("图标 URL 不允许访问内网地址")

    @staticmethod
    def _detect_content_type(content: bytes) -> str | None:
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if content.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "image/webp"
        if content.startswith(b"\x00\x00\x01\x00"):
            return "image/x-icon"
        return None

    def _read_cached(self, digest: str) -> CachedIcon | None:
        data_path, meta_path, _ = self._paths(digest)
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            content = data_path.read_bytes()
            content_type = self._detect_content_type(content)
            if not content_type or content_type != metadata.get("contentType"):
                return None
            return CachedIcon(content, content_type, "hit")
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
            return None

    def _read_recent_failure(self, digest: str) -> str | None:
        _, _, failure_path = self._paths(digest)
        try:
            payload = json.loads(failure_path.read_text(encoding="utf-8"))
            if time.time() - float(payload.get("createdAt", 0)) < FAILURE_TTL_SECONDS:
                return str(payload.get("message") or "图标暂时无法加载")
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
            return None
        failure_path.unlink(missing_ok=True)
        return None

    def _write_success(self, digest: str, content: bytes, content_type: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        data_path, meta_path, failure_path = self._paths(digest)
        token = secrets.token_hex(8)
        temporary_data = data_path.with_name(f"{data_path.name}.{token}.tmp")
        temporary_meta = meta_path.with_name(f"{meta_path.name}.{token}.tmp")
        try:
            temporary_data.write_bytes(content)
            temporary_meta.write_text(
                json.dumps({"contentType": content_type, "createdAt": time.time()}),
                encoding="utf-8",
            )
            temporary_data.replace(data_path)
            temporary_meta.replace(meta_path)
            failure_path.unlink(missing_ok=True)
        finally:
            temporary_data.unlink(missing_ok=True)
            temporary_meta.unlink(missing_ok=True)

    def _write_failure(self, digest: str, message: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        _, _, failure_path = self._paths(digest)
        failure_path.write_text(
            json.dumps({"message": message, "createdAt": time.time()}, ensure_ascii=False),
            encoding="utf-8",
        )

    async def get(self, url: str) -> CachedIcon:
        digest = self._digest(url)
        cached = await asyncio.to_thread(self._read_cached, digest)
        if cached:
            return cached
        previous_failure = await asyncio.to_thread(self._read_recent_failure, digest)
        if previous_failure:
            raise IconCacheError(previous_failure, fresh=False)

        lock = _shared_lock(f"{self.root.resolve()}:{digest}")
        async with lock:
            cached = await asyncio.to_thread(self._read_cached, digest)
            if cached:
                return cached
            try:
                current_url = url
                async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                    for redirect_count in range(4):
                        await self._validate_public_url(current_url)
                        async with client.stream(
                            "GET",
                            current_url,
                            headers={"User-Agent": "FixCloud-Panel/1.0"},
                        ) as response:
                            if response.is_redirect:
                                location = response.headers.get("location")
                                if not location or redirect_count == 3:
                                    raise IconCacheError("图标重定向无效")
                                current_url = str(response.url.join(location))
                                continue
                            response.raise_for_status()
                            chunks: list[bytes] = []
                            size = 0
                            async for chunk in response.aiter_bytes():
                                size += len(chunk)
                                if size > MAX_ICON_BYTES:
                                    raise IconCacheError("图标文件超过 1 MiB")
                                chunks.append(chunk)
                            break
                    else:
                        raise IconCacheError("图标重定向过多")
                content = b"".join(chunks)
                content_type = self._detect_content_type(content)
                if not content_type:
                    raise IconCacheError("图标格式不受支持")
                await asyncio.to_thread(self._write_success, digest, content, content_type)
                return CachedIcon(content, content_type, "stored")
            except IconCacheError as exc:
                await asyncio.to_thread(self._write_failure, digest, str(exc))
                raise
            except (httpx.HTTPError, OSError) as exc:
                message = "图标下载失败"
                await asyncio.to_thread(self._write_failure, digest, message)
                raise IconCacheError(message) from exc
