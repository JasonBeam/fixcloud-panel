from __future__ import annotations

import asyncio
import math
import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

import httpx


SHANGHAI = ZoneInfo("Asia/Shanghai")
CACHE_TTL_SECONDS = 300
_usage_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def parse_subscription_userinfo(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    values: dict[str, int] = {}
    for part in value.split(";"):
        key, separator, raw_value = part.strip().partition("=")
        if not separator:
            continue
        normalized = key.strip().lower()
        if normalized not in {"upload", "download", "total", "expire"}:
            continue
        try:
            values[normalized] = max(0, int(raw_value.strip()))
        except ValueError:
            continue
    if values.get("total", 0) <= 0:
        return None
    values.setdefault("upload", 0)
    values.setdefault("download", 0)
    values.setdefault("expire", 0)
    return values


def content_disposition_title(value: str | None) -> str | None:
    if not value:
        return None
    encoded = re.search(r"filename\*=UTF-8''([^;]+)", value, flags=re.IGNORECASE)
    plain = re.search(r'filename="?([^";]+)"?', value, flags=re.IGNORECASE)
    title = unquote(encoded.group(1)) if encoded else (plain.group(1) if plain else "")
    title = " ".join(title.strip().split())[:80]
    return title or None


def usage_payload(
    provider_name: str,
    headers: httpx.Headers,
    *,
    fetched_at: datetime,
) -> dict[str, Any]:
    info = parse_subscription_userinfo(headers.get("subscription-userinfo"))
    title = content_disposition_title(headers.get("content-disposition")) or provider_name
    if not info:
        return {
            "provider": provider_name,
            "title": title,
            "available": False,
            "message": "订阅服务器未提供流量信息",
        }

    upload = info["upload"]
    download = info["download"]
    total = info["total"]
    used = upload + download
    remaining = max(0, total - used)
    expire = info["expire"]
    expire_at = datetime.fromtimestamp(expire, SHANGHAI) if expire > 0 else None
    seconds_remaining = (expire_at - fetched_at).total_seconds() if expire_at else None
    remaining_days = (
        max(0, math.ceil(seconds_remaining / 86400))
        if seconds_remaining is not None
        else None
    )
    return {
        "provider": provider_name,
        "title": title,
        "available": True,
        "upload": upload,
        "download": download,
        "used": used,
        "total": total,
        "remaining": remaining,
        "remainingPercent": round((remaining / total) * 100, 1),
        "expireAt": expire_at.isoformat() if expire_at else None,
        "remainingDays": remaining_days,
        "expired": seconds_remaining is not None and seconds_remaining <= 0,
    }


class SubscriptionUsageService:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def get_usage(
        self,
        root: dict[str, Any],
        *,
        cache_key: str,
        force: bool = False,
    ) -> dict[str, Any]:
        cached = _usage_cache.get(cache_key)
        now_monotonic = time.monotonic()
        if not force and cached and now_monotonic - cached[0] < CACHE_TTL_SECONDS:
            return {**cached[1], "cached": True}

        providers = root.get("proxy-providers", {})
        candidates: list[tuple[str, str]] = []
        if isinstance(providers, dict):
            for name, value in list(providers.items())[:20]:
                if not isinstance(value, dict) or str(value.get("type", "")).lower() != "http":
                    continue
                url = str(value.get("url", "")).strip()
                if urlparse(url).scheme in {"http", "https"}:
                    candidates.append((str(name), url))

        fetched_at = datetime.now(SHANGHAI)
        timeout = httpx.Timeout(12.0, connect=6.0)
        limits = httpx.Limits(max_connections=8, max_keepalive_connections=4)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            limits=limits,
            transport=self.transport,
            headers={"User-Agent": "clash.meta"},
        ) as client:
            results = await asyncio.gather(
                *(self._fetch_one(client, name, url, fetched_at) for name, url in candidates),
            )

        results.sort(
            key=lambda item: (
                not bool(item.get("available")),
                -int(item.get("total", 0)),
                str(item.get("title", "")).lower(),
            ),
        )
        payload = {
            "fetchedAt": fetched_at.isoformat(),
            "cached": False,
            "refreshAfterSeconds": CACHE_TTL_SECONDS,
            "subscriptions": results,
        }
        _usage_cache[cache_key] = (now_monotonic, payload)
        return payload

    async def _fetch_one(
        self,
        client: httpx.AsyncClient,
        name: str,
        url: str,
        fetched_at: datetime,
    ) -> dict[str, Any]:
        try:
            response = await client.head(url)
            headers = response.headers
            if not headers.get("subscription-userinfo"):
                async with client.stream("GET", url) as streamed:
                    headers = streamed.headers
            return usage_payload(name, headers, fetched_at=fetched_at)
        except httpx.TimeoutException:
            message = "连接订阅服务器超时"
        except httpx.HTTPError:
            message = "无法连接订阅服务器"
        except Exception:
            message = "读取流量信息失败"
        return {
            "provider": name,
            "title": name,
            "available": False,
            "message": message,
        }
