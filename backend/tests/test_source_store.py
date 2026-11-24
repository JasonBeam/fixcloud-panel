import json
import os
from pathlib import Path

import pytest

from app.core.settings import Settings
from app.services.source_store import SourceStore


@pytest.mark.asyncio
async def test_source_store_keeps_credentials_backend_only(tmp_path: Path) -> None:
    settings = Settings(
        app_env="test",
        app_data_dir=tmp_path / "data",
        storage_root=tmp_path,
        webdav_url="http://nas.invalid/dav/",
        webdav_username="dav-user",
        webdav_password="dav-password",
    )
    store = SourceStore(settings.app_data_dir, settings)
    defaults = await store.list()

    assert [item.id for item in defaults] == ["default-smb", "uploaded-files"]
    assert defaults[0].config["configDirectory"] == "config"

    webdav = await store.create(
        "webdav",
        "Private DAV",
        {
            "url": "http://nas.invalid/dav/",
            "username": "dav-user",
            "password": "dav-password",
            "rootDirectory": "/",
            "configDirectory": "config",
        },
    )
    assert webdav.config["username"] == "dav-user"
    assert webdav.config["password"] == "dav-password"
    assert "username" not in webdav.safe_data()["config"]
    assert "password" not in webdav.safe_data()["config"]
    if os.name != "nt":
        assert store.path.stat().st_mode & 0o777 == 0o600

    raw = json.loads(store.path.read_text(encoding="utf-8"))
    persisted_webdav = next(item for item in raw["sources"] if item["id"] == webdav.id)
    assert persisted_webdav["config"]["password"] == "dav-password"


@pytest.mark.asyncio
async def test_source_store_migrates_out_built_in_webdav(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "sources.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "default-smb",
                        "type": "smb-mounted",
                        "name": "NAS SMB",
                        "builtIn": True,
                        "config": {"root": str(tmp_path)},
                    },
                    {
                        "id": "default-webdav",
                        "type": "webdav",
                        "name": "WebDAV",
                        "builtIn": True,
                        "config": {
                            "url": "http://nas.invalid/dav/",
                            "username": "old",
                            "password": "old",
                        },
                    },
                    {
                        "id": "source-user-webdav",
                        "type": "webdav",
                        "name": "User DAV",
                        "builtIn": False,
                        "config": {
                            "url": "http://nas.invalid/user/",
                            "username": "keep",
                            "password": "keep",
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(app_env="test", app_data_dir=data_dir, storage_root=tmp_path)
    records = await SourceStore(data_dir, settings).list()

    assert {record.id for record in records} == {
        "default-smb",
        "uploaded-files",
        "source-user-webdav",
    }
    assert next(record for record in records if record.id == "default-smb").config[
        "configDirectory"
    ] == "config"
    assert next(record for record in records if record.id == "source-user-webdav").config[
        "configDirectory"
    ] == "/"


@pytest.mark.asyncio
async def test_source_update_blank_credentials_preserves_existing(tmp_path: Path) -> None:
    settings = Settings(app_env="test", app_data_dir=tmp_path / "data", storage_root=tmp_path)
    store = SourceStore(settings.app_data_dir, settings)
    created = await store.create(
        "smb",
        "Remote",
        {
            "server": "nas",
            "share": "config",
            "username": "beam",
            "password": "secret",
            "rootDirectory": "",
            "configDirectory": "config",
        },
    )
    updated = await store.update(
        created.id,
        "smb",
        "Remote 2",
        {"server": "nas2", "username": "", "password": ""},
    )
    assert updated.config["username"] == "beam"
    assert updated.config["password"] == "secret"
    assert updated.config["server"] == "nas2"
