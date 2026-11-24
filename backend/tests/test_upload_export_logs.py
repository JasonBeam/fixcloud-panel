import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.main import app
from app.services.icon_cache import CachedIcon, IconCache


def make_client(tmp_path: Path):
    (tmp_path / "FixCloud.yaml").write_bytes(b"# keep\r\nport: 7890\r\nrules: []\r\n")
    settings = Settings(
        app_env="test",
        app_data_dir=tmp_path / "data",
        storage_backend="local",
        storage_root=tmp_path,
        yaml_path="/FixCloud.yaml",
        write_enabled=True,
        frontend_dist=tmp_path / "missing",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), settings


def test_upload_unique_invalid_and_isolated(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    headers = {"X-FixCloud-Request": "1"}
    try:
        with client:
            first = client.post(
                "/api/files/upload", headers=headers,
                files={"file": ("sample.yaml", b"# uploaded\nport: 7000\n", "application/yaml")},
            )
            second = client.post(
                "/api/files/upload", headers=headers,
                files={"file": ("sample.yaml", b"port: 7001\n", "application/yaml")},
            )
            assert first.status_code == second.status_code == 200
            assert first.json()["file"]["path"] == "/sample.yaml"
            assert second.json()["file"]["path"] == "/sample-1.yaml"
            sessions = settings.app_data_dir / "temporary-sessions"
            uploads = next(item for item in sessions.iterdir() if item.is_dir())
            assert (uploads / "sample.yaml").read_bytes().startswith(b"# uploaded")
            assert not (tmp_path / "sample.yaml").exists()
            before = set(uploads.iterdir())
            invalid = client.post(
                "/api/files/upload", headers=headers,
                files={"file": ("bad.yaml", b"- not\n- a mapping\n", "application/yaml")},
            )
            assert invalid.status_code == 422
            assert set(uploads.iterdir()) == before
    finally:
        app.dependency_overrides.clear()


def test_export_original_bytes_and_operations(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    headers = {"X-FixCloud-Request": "1"}
    original = (tmp_path / "FixCloud.yaml").read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    base = {
        "sourceId": "default-smb", "path": "/FixCloud.yaml", "baseHash": digest,
        "filename": "copy.yml",
    }
    try:
        with client:
            unchanged = client.post(
                "/api/config/export", headers=headers, json={**base, "operations": []},
            )
            assert unchanged.status_code == 200
            assert unchanged.content == original
            changed = client.post(
                "/api/config/export", headers=headers,
                json={**base, "operations": [{"op": "set", "path": ["port"], "value": 7899}]},
            )
            assert changed.status_code == 200
            assert b"port: 7899" in changed.content
            assert b"# keep" in changed.content
    finally:
        app.dependency_overrides.clear()


def test_logs_filter_by_current_file(tmp_path: Path) -> None:
    client, settings = make_client(tmp_path)
    headers = {"X-FixCloud-Request": "1"}
    try:
        with client:
            raw = (tmp_path / "FixCloud.yaml").read_bytes()
            client.post("/api/config/export", headers=headers, json={
                "sourceId": "default-smb", "path": "/FixCloud.yaml",
                "baseHash": hashlib.sha256(raw).hexdigest(), "operations": [],
            })
            client.post("/api/files/upload", headers=headers, files={
                "file": ("other.yaml", b"port: 1\n", "application/yaml"),
            })
            filtered = client.get("/api/logs", params={
                "sourceId": "default-smb", "path": "/FixCloud.yaml",
            }).json()["logs"]
            assert len(filtered) == 1
            assert filtered[0]["action"] == "export"
            assert filtered[0]["status"] == "success"
            assert settings.app_data_dir.joinpath("audit.sqlite3").exists()
    finally:
        app.dependency_overrides.clear()


def test_icon_cache_audit_uses_selected_yaml_context(tmp_path: Path, monkeypatch) -> None:
    client, _ = make_client(tmp_path)

    async def fake_get(self, url: str):
        return CachedIcon(b"\x89PNG\r\n\x1a\nmock", "image/png", "stored")

    monkeypatch.setattr(IconCache, "get", fake_get)
    try:
        with client:
            response = client.get("/api/icons/cache", params={
                "url": "https://example.com/icon.png",
                "sourceId": "default-smb",
                "path": "/FixCloud.yaml",
            })
            assert response.status_code == 200
            logs = client.get("/api/logs", params={
                "sourceId": "default-smb",
                "path": "/FixCloud.yaml",
            }).json()["logs"]
            assert logs[0]["action"] == "icon-cache"
            assert logs[0]["sourceId"] == "default-smb"
            assert logs[0]["path"] == "/FixCloud.yaml"

            invalid = client.get("/api/icons/cache", params={
                "url": "https://example.com/icon.png",
                "sourceId": "missing-source",
                "path": "/FixCloud.yaml",
            })
            assert invalid.status_code == 404
    finally:
        app.dependency_overrides.clear()
