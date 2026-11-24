from pathlib import Path

import httpx
import pytest

from app.services.icon_catalog import IconCatalog


@pytest.mark.asyncio
async def test_icon_catalog_fetches_and_reuses_persistent_cache(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = 0

    async def handler(request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json=[
                {
                    "type": "file",
                    "name": "chatgpt.png",
                    "download_url": (
                        "https://raw.githubusercontent.com/shindgew/"
                        "WHATSINStash/main/icon/chatgpt.png"
                    ),
                },
                {"type": "dir", "name": "nested", "download_url": None},
            ],
            request=request,
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )

    first = await IconCatalog(tmp_path, "https://file.example").list()
    second = await IconCatalog(tmp_path, "https://file.example").list()

    assert first["status"] == "updated"
    assert second["status"] == "cached"
    assert first["items"][0]["name"] == "chatgpt"
    assert first["items"][0]["url"] == "https://file.example/icon/chatgpt.png"
    assert "raw.githubusercontent.com" in first["items"][0]["upstreamUrl"]
    assert calls == 1
    assert (tmp_path / "icon-catalog" / "whatsinstash.json").is_file()


@pytest.mark.asyncio
async def test_icon_catalog_separates_personal_icons(
    tmp_path: Path,
    monkeypatch,
) -> None:
    personal_dir = tmp_path / "personal-icons"
    personal_dir.mkdir()
    (personal_dir / "panel.png").write_bytes(b"panel")
    (personal_dir / "chatgpt.png").write_bytes(b"community")
    (personal_dir / "iconset.json").write_text("{}", encoding="utf-8")

    async def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=[
                {
                    "type": "file",
                    "name": "chatgpt.png",
                    "download_url": (
                        "https://raw.githubusercontent.com/shindgew/"
                        "WHATSINStash/main/icon/chatgpt.png"
                    ),
                },
            ],
            request=request,
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = await IconCatalog(
        tmp_path,
        "https://file.example",
        personal_dir,
    ).list()

    assert [item["filename"] for item in result["personalItems"]] == ["panel.png"]
    assert result["personalItems"][0]["url"] == "https://file.example/icon/panel.png"
