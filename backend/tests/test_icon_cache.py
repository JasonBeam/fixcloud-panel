import asyncio
import socket
from pathlib import Path

import httpx
import pytest

from app.services.icon_cache import IconCache, IconCacheError


PUBLIC_DNS = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 443))]
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20


@pytest.mark.asyncio
async def test_icon_cache_hit_does_not_fetch_twice(tmp_path: Path, monkeypatch) -> None:
    calls = 0

    async def fake_dns(*args, **kwargs):
        return PUBLIC_DNS

    async def handler(request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=PNG, request=request)

    monkeypatch.setattr(IconCache, "_validate_public_url", fake_dns)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    cache = IconCache(tmp_path)
    assert (await cache.get("https://example.com/a.png")).status == "stored"
    assert (await cache.get("https://example.com/a.png")).status == "hit"
    assert calls == 1


@pytest.mark.asyncio
async def test_icon_cache_concurrent_instances_share_digest_lock(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = 0

    async def fake_dns(*args, **kwargs):
        return PUBLIC_DNS

    async def handler(request: httpx.Request):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.03)
        return httpx.Response(200, content=PNG, request=request)

    monkeypatch.setattr(IconCache, "_validate_public_url", fake_dns)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    first, second = await asyncio.gather(
        IconCache(tmp_path).get("https://example.com/concurrent.png"),
        IconCache(tmp_path).get("https://example.com/concurrent.png"),
    )
    assert {first.status, second.status} == {"stored", "hit"}
    assert calls == 1
    assert not list((tmp_path / "icon-cache").glob("*.tmp"))


@pytest.mark.asyncio
async def test_public_url_allows_only_rfc2544_fake_ip_compatibility(monkeypatch) -> None:
    """Mihomo/Clash Fake-IP DNS uses RFC 2544's 198.18.0.0/15 benchmark range."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.42.9", 443))
        ],
    )
    await IconCache._validate_public_url("https://raw.githubusercontent.com/icon.png")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.1.1", "192.0.2.1"],
)
async def test_public_url_still_rejects_other_non_public_ranges(
    address: str,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
        ],
    )
    with pytest.raises(IconCacheError, match="内网"):
        await IconCache._validate_public_url("https://example.com/icon.png")


@pytest.mark.asyncio
async def test_icon_cache_rejects_private_dns_and_bad_format(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(IconCacheError, match="内网"):
        await IconCache(tmp_path).get("http://example.com/icon.png")

    async def fake_dns(*args, **kwargs):
        return None

    async def handler(request: httpx.Request):
        return httpx.Response(200, content=b"<html>no</html>", request=request)

    monkeypatch.setattr(IconCache, "_validate_public_url", fake_dns)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    with pytest.raises(IconCacheError, match="格式"):
        await IconCache(tmp_path / "bad").get("https://example.com/icon")
