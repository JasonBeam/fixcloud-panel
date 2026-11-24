import httpx
import pytest

from app.services.publication import PublicationVerifier


@pytest.mark.asyncio
async def test_publication_verifier_compares_real_bytes(monkeypatch) -> None:
    async def handler(request: httpx.Request):
        assert request.headers["cache-control"] == "no-cache"
        if "_fixcloud_refresh=" in str(request.url):
            assert request.headers["accept"] == "application/json"
            return httpx.Response(200, json=[], request=request)
        assert "_fixcloud_verify=" in str(request.url)
        return httpx.Response(
            200,
            content=b"port: 7890\n",
            headers={"etag": '"current"', "last-modified": "Tue, 28 Jul 2026 08:30:46 GMT"},
            request=request,
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = await PublicationVerifier("https://file.example").compare(
        filename="FixCloud.yaml",
        current=b"port: 7890\n",
    )

    assert result["matching"] is True
    assert result["currentHash"] == result["publishedHash"]
    assert result["publishedUrl"] == "https://file.example/FixCloud.yaml"
    assert result["directoryRefreshed"] is True
