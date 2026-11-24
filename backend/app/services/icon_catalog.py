from __future__ import annotations

import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


CATALOG_URL = "https://api.github.com/repos/shindgew/WHATSINStash/contents/icon?ref=main"
REPOSITORY_URL = "https://github.com/shindgew/WHATSINStash"
CACHE_TTL_SECONDS = 24 * 60 * 60
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


class IconCatalogError(RuntimeError):
    pass


class IconCatalog:
    def __init__(
        self,
        data_dir: Path,
        public_base_url: str,
        personal_icon_dir: Path | None = None,
    ):
        self.root = data_dir / "icon-catalog"
        self.cache_path = self.root / "whatsinstash.json"
        self.public_base_url = public_base_url.rstrip("/")
        self.personal_icon_dir = personal_icon_dir

    def _response(self, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
        upstream_filenames = {item["filename"] for item in payload["items"]}
        items = [
            {
                **item,
                "upstreamUrl": item["url"],
                "url": f"{self.public_base_url}/icon/{quote(item['filename'])}",
            }
            for item in payload["items"]
        ]
        return {
            **payload,
            **extra,
            "items": items,
            "personalItems": self._personal_items(upstream_filenames),
            "repositoryUrl": REPOSITORY_URL,
            "publicIconBaseUrl": f"{self.public_base_url}/icon/",
        }

    def _personal_items(self, upstream_filenames: set[str]) -> list[dict[str, str]]:
        if not self.personal_icon_dir:
            return []
        try:
            paths = [
                path
                for path in self.personal_icon_dir.iterdir()
                if path.is_file()
                and path.suffix.lower() in ALLOWED_SUFFIXES
                and path.name not in upstream_filenames
            ]
        except OSError:
            return []
        return [
            {
                "name": path.stem,
                "filename": path.name,
                "url": f"{self.public_base_url}/icon/{quote(path.name)}",
            }
            for path in sorted(paths, key=lambda path: path.name.lower())
        ]

    def _read_cache(self) -> tuple[dict[str, Any], float] | None:
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            created_at = float(payload["createdAt"])
            if not isinstance(payload.get("items"), list):
                return None
            return payload, created_at
        except (FileNotFoundError, OSError, ValueError, KeyError, json.JSONDecodeError):
            return None

    def _write_cache(self, payload: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_name(
            f"{self.cache_path.name}.{secrets.token_hex(8)}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            temporary.replace(self.cache_path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _normalize(entries: Any) -> list[dict[str, str]]:
        if not isinstance(entries, list):
            raise IconCatalogError("图标仓库返回格式不正确")
        items: list[dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "file":
                continue
            name = str(entry.get("name") or "")
            url = str(entry.get("download_url") or "")
            if (
                Path(name).suffix.lower() not in ALLOWED_SUFFIXES
                or not url.startswith(
                    "https://raw.githubusercontent.com/shindgew/WHATSINStash/"
                )
            ):
                continue
            items.append(
                {
                    "name": Path(name).stem,
                    "filename": name,
                    "url": url,
                }
            )
        if not items:
            raise IconCatalogError("图标仓库中没有可用图片")
        items.sort(key=lambda item: item["name"].lower())
        return items

    async def list(self, *, force: bool = False) -> dict[str, Any]:
        cached = self._read_cache()
        now = time.time()
        if cached and not force and now - cached[1] < CACHE_TTL_SECONDS:
            return self._response(cached[0], status="cached")

        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
                response = await client.get(
                    CATALOG_URL,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "FixCloud-Panel/1.0",
                    },
                )
                response.raise_for_status()
                items = self._normalize(response.json())
            payload = {
                "createdAt": now,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "items": items,
            }
            self._write_cache(payload)
            return self._response(payload, status="updated")
        except (httpx.HTTPError, OSError, ValueError, IconCatalogError) as exc:
            if cached:
                return self._response(
                    cached[0],
                    status="stale",
                    warning="无法更新图标目录，正在显示上次缓存",
                )
            if isinstance(exc, IconCatalogError):
                raise
            raise IconCatalogError("暂时无法读取 WHATSINStash 图标目录") from exc
