from __future__ import annotations

import hashlib
import time
from urllib.parse import quote, urlparse

import httpx


MAX_PUBLIC_YAML_BYTES = 5 * 1024 * 1024


class PublicationCheckError(RuntimeError):
    pass


class PublicationVerifier:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def compare(self, *, filename: str, current: bytes) -> dict[str, object]:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise PublicationCheckError("公开文件服务地址格式不正确")

        clean_url = f"{self.base_url}/{quote(filename)}"
        request_url = f"{clean_url}?_fixcloud_verify={int(time.time() * 1000)}"
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
                directory_url = (
                    f"{self.base_url}/?_fixcloud_refresh={int(time.time() * 1000)}"
                )
                directory_response = await client.get(
                    directory_url,
                    headers={
                        "Accept": "application/json",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "User-Agent": "FixCloud-Panel/1.0",
                    },
                )
                directory_response.raise_for_status()
                async with client.stream(
                    "GET",
                    request_url,
                    headers={
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "User-Agent": "FixCloud-Panel/1.0",
                    },
                ) as response:
                    response.raise_for_status()
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_PUBLIC_YAML_BYTES:
                            raise PublicationCheckError("线上 YAML 超过 5 MiB，已停止核对")
                        chunks.append(chunk)
                    published = b"".join(chunks)
                    etag = response.headers.get("etag")
                    last_modified = response.headers.get("last-modified")
        except PublicationCheckError:
            raise
        except httpx.TimeoutException as exc:
            raise PublicationCheckError("公开文件服务连接超时") from exc
        except httpx.HTTPStatusError as exc:
            raise PublicationCheckError(
                f"公开文件服务返回 HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise PublicationCheckError("无法连接公开文件服务") from exc

        current_hash = self._hash(current)
        published_hash = self._hash(published)
        return {
            "matching": current_hash == published_hash,
            "currentHash": current_hash,
            "publishedHash": published_hash,
            "publishedUrl": clean_url,
            "publishedSize": len(published),
            "etag": etag,
            "lastModified": last_modified,
            "latencyMs": max(1, round((time.perf_counter() - started) * 1000)),
            "directoryRefreshed": True,
        }
