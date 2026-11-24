from __future__ import annotations

import asyncio
import base64
import re
import time
from typing import Any
from urllib.parse import unquote, urlparse

import httpx
from ruamel.yaml import YAML

from app.services.subscription_usage import content_disposition_title

CACHE_TTL_SECONDS = 300
MAX_SUBSCRIPTION_BYTES = 8 * 1024 * 1024
MAX_NODES_PER_PROVIDER = 500
MAX_PROVIDERS = 20
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _text(value: Any, fallback: str) -> str:
    result = " ".join(str(value or "").strip().split())
    return result[:160] if result else fallback


def _node_from_mapping(value: Any, index: int) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    return {"name": _text(value.get("name"), f"未命名节点 {index + 1}"), "type": _text(value.get("type"), "未知协议").lower()}


def _decode_subscription(raw: bytes) -> str | None:
    compact = re.sub(rb"\s+", b"", raw)
    if not compact or len(compact) % 4 == 1:
        return None
    try:
        decoded = base64.b64decode(compact + b"=" * (-len(compact) % 4), validate=False)
        text = decoded.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return text if "://" in text else None


def _node_from_uri(line: str, index: int) -> dict[str, str] | None:
    uri = line.strip()
    if "://" not in uri:
        return None
    parsed = urlparse(uri)
    protocol = parsed.scheme.lower()
    if not protocol:
        return None
    return {"name": _text(unquote(parsed.fragment).strip(), f"未命名节点 {index + 1}"), "type": protocol}


def parse_subscription_nodes(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        document = YAML(typ="safe").load(text)
    except Exception:
        document = None
    candidates = document.get("proxies") if isinstance(document, dict) else document
    if isinstance(candidates, list):
        nodes = [_node_from_mapping(item, index) for index, item in enumerate(candidates)]
    else:
        uri_text = _decode_subscription(raw) or text
        nodes = [_node_from_uri(line, index) for index, line in enumerate(uri_text.splitlines())]
    return [item for item in nodes if item][:MAX_NODES_PER_PROVIDER]


class SubscriptionNodesService:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def get_nodes(self, document_root: Any, *, cache_key: str, force: bool = False) -> dict[str, Any]:
        cached = _cache.get(cache_key)
        if cached and not force and time.time() - cached[0] < CACHE_TTL_SECONDS:
            return {**cached[1], "cached": True}
        providers = self._providers(document_root)
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(18.0, connect=6.0), transport=self.transport, headers={"User-Agent": "clash.meta"}) as client:
            results = await asyncio.gather(*(self._fetch_provider(client, provider) for provider in providers), return_exceptions=False)
        payload = {"providers": results, "totalProviders": len(results), "totalNodes": sum(item["nodeCount"] for item in results), "cached": False, "refreshedAt": int(time.time() * 1000)}
        _cache[cache_key] = (time.time(), payload)
        return payload

    @staticmethod
    def _providers(document_root: Any) -> list[tuple[str, dict[str, Any]]]:
        configured = document_root.get("proxy-providers", {}) if isinstance(document_root, dict) else {}
        if not isinstance(configured, dict):
            return []
        providers: list[tuple[str, dict[str, Any]]] = []
        for name, config in configured.items():
            if not isinstance(config, dict) or str(config.get("type", "")).lower() != "http":
                continue
            url = str(config.get("url", "")).strip()
            if urlparse(url).scheme in {"http", "https"}:
                providers.append((str(name), config))
        return providers[:MAX_PROVIDERS]

    async def _fetch_provider(self, client: httpx.AsyncClient, provider: tuple[str, dict[str, Any]]) -> dict[str, Any]:
        name, config = provider
        url = str(config.get("url", "")).strip()
        try:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                title = content_disposition_title(response.headers.get("content-disposition")) or name
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_SUBSCRIPTION_BYTES:
                        raise ValueError("订阅内容过大")
                    chunks.append(chunk)
            nodes = parse_subscription_nodes(b"".join(chunks))
            return {"provider": name, "title": _text(title, name), "nodeCount": len(nodes), "nodes": nodes, "status": "ok"}
        except httpx.TimeoutException:
            message = "拉取超时"
        except httpx.HTTPStatusError as exc:
            message = f"HTTP {exc.response.status_code}"
        except ValueError as exc:
            message = str(exc)
        except httpx.HTTPError:
            message = "订阅连接失败"
        except Exception:
            message = "订阅内容无法解析"
        return {"provider": name, "title": name, "nodeCount": 0, "nodes": [], "status": "error", "message": message}
