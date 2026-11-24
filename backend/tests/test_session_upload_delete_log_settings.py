import hashlib
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.main import app
from app.services.audit import AuditStore
from app.services.browser_session import cleanup_expired, temporary_root


HEADERS = {"X-FixCloud-Request": "1"}


def configured(tmp_path: Path) -> Settings:
    (tmp_path / "FixCloud.yaml").write_text("port: 7890\nrules: []\n", encoding="utf-8")
    settings = Settings(
        app_env="test", app_data_dir=tmp_path / "data", storage_backend="local",
        storage_root=tmp_path, yaml_path="/FixCloud.yaml", write_enabled=True,
        frontend_dist=tmp_path / "missing",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return settings


def test_browser_session_cookie_has_session_only_security_attributes(tmp_path: Path) -> None:
    configured(tmp_path)
    try:
        with TestClient(app) as client:
            response = client.get("/api/files/catalog")
            cookie = response.headers["set-cookie"].lower()
            assert cookie.startswith("fixcloud_session=")
            assert "httponly" in cookie
            assert "samesite=strict" in cookie
            assert "path=/" in cookie
            assert "max-age" not in cookie
            assert "expires=" not in cookie
    finally:
        app.dependency_overrides.clear()


def test_two_upload_modes_unique_and_formal_catalog(tmp_path: Path) -> None:
    settings = configured(tmp_path)
    try:
        with TestClient(app) as client:
            temp = client.post("/api/files/upload", headers=HEADERS, data={"mode": "temporary"},
                files={"file": ("new.yaml", b"port: 1\n", "application/yaml")})
            formal = client.post("/api/files/upload", headers=HEADERS,
                data={"mode": "config", "sourceId": "default-smb"},
                files={"file": ("new.yaml", b"port: 2\n", "application/yaml")})
            duplicate = client.post("/api/files/upload", headers=HEADERS,
                data={"mode": "config", "sourceId": "default-smb"},
                files={"file": ("new.yaml", b"port: 3\n", "application/yaml")})
            assert [temp.status_code, formal.status_code, duplicate.status_code] == [200, 200, 200]
            assert temp.json()["file"]["hash"] == hashlib.sha256(b"port: 1\n").hexdigest()
            assert formal.json()["file"]["hash"] == hashlib.sha256(b"port: 2\n").hexdigest()
            assert duplicate.json()["file"]["hash"] == hashlib.sha256(b"port: 3\n").hexdigest()
            assert temp.json()["file"]["sourceType"] == "upload"
            assert formal.json()["file"]["sourceType"] == "smb-mounted"
            assert duplicate.json()["file"]["sourceType"] == "smb-mounted"
            assert (tmp_path / "new.yaml").read_bytes() == b"port: 2\n"
            assert (tmp_path / "new-1.yaml").read_bytes() == b"port: 3\n"
            catalog = client.get("/api/files/catalog").json()["files"]
            assert {(item["sourceId"], item["name"]) for item in catalog} >= {
                ("uploaded-files", "new.yaml"), ("default-smb", "new.yaml"),
                ("default-smb", "new-1.yaml"),
            }
            assert next(item for item in catalog if item["name"] == "new-1.yaml")["sourceType"] == "smb-mounted"
            assert not (settings.app_data_dir / "uploads").exists()
    finally:
        app.dependency_overrides.clear()


def test_session_a_b_isolation_read_export_delete_and_logs(tmp_path: Path) -> None:
    configured(tmp_path)
    try:
        with TestClient(app) as a, TestClient(app) as b:
            uploaded = a.post("/api/files/upload", headers=HEADERS,
                files={"file": ("private.yaml", b"port: 8\n", "application/yaml")}).json()["file"]
            assert "private.yaml" in [x["name"] for x in a.get("/api/files/catalog").json()["files"]]
            assert "private.yaml" not in [x["name"] for x in b.get("/api/files/catalog").json()["files"]]
            params = {"sourceId": "uploaded-files", "path": "/private.yaml"}
            assert a.get("/api/config", params=params).status_code == 200
            assert b.get("/api/config", params=params).status_code == 404
            assert b.get("/api/config/summary", params=params).status_code == 404
            assert b.get("/api/subscriptions/usage", params=params).status_code == 404
            digest = hashlib.sha256(b"port: 8\n").hexdigest()
            export_body = {**params, "baseHash": digest, "operations": []}
            assert a.post("/api/config/export", headers=HEADERS, json=export_body).status_code == 200
            assert b.post("/api/config/export", headers=HEADERS, json=export_body).status_code == 404
            assert b.post("/api/config/preview", headers=HEADERS, json={
                **export_body, "operations": [{"op": "set", "path": ["port"], "value": 9}],
            }).status_code == 404
            assert any(x["fileName"] == "private.yaml" for x in a.get("/api/logs").json()["logs"])
            assert not any(x["fileName"] == "private.yaml" for x in b.get("/api/logs").json()["logs"])
            assert uploaded["hash"] == digest
            delete_body = {**params, "expectedHash": uploaded["hash"]}
            assert b.request("DELETE", "/api/files", headers=HEADERS, json=delete_body).status_code == 404
            assert a.request("DELETE", "/api/files", headers=HEADERS, json=delete_body).status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_delete_expected_hash_and_scoped_safety(tmp_path: Path) -> None:
    configured(tmp_path)
    rules = tmp_path / "rules"
    rules.mkdir()
    protected = rules / "keep.yaml"
    protected.write_text("payload: []\n", encoding="utf-8")
    try:
        with TestClient(app) as client:
            digest = hashlib.sha256((tmp_path / "FixCloud.yaml").read_bytes()).hexdigest()
            base = {"sourceId": "default-smb", "path": "/FixCloud.yaml"}
            stale = client.request("DELETE", "/api/files", headers=HEADERS,
                json={**base, "expectedHash": "0" * 64})
            assert stale.status_code == 409
            traversal = client.request("DELETE", "/api/files", headers=HEADERS,
                json={"sourceId": "default-smb", "path": "/rules/keep.yaml", "expectedHash": digest})
            assert traversal.status_code == 422
            backup = client.request("DELETE", "/api/files", headers=HEADERS,
                json={"sourceId": "default-smb", "path": "/FixCloud.yaml.backup-x.yaml", "expectedHash": digest})
            assert backup.status_code == 422
            assert protected.exists()
    finally:
        app.dependency_overrides.clear()


def test_cleanup_removes_only_expired_owned_session_directories(tmp_path: Path) -> None:
    root = temporary_root(tmp_path)
    expired = root / ("a" * 64)
    active = root / ("b" * 64)
    legacy = root / "legacy-files"
    formal = tmp_path / "formal"
    for directory in (expired, active, legacy, formal):
        directory.mkdir(parents=True)
        (directory / "keep.yaml").write_text("port: 1\n", encoding="utf-8")
    old = time.time() - 25 * 60 * 60
    os.utime(expired, (old, old))
    os.utime(legacy, (old, old))
    removed = cleanup_expired(tmp_path)
    assert removed == [expired.resolve()]
    assert not expired.exists()
    assert active.exists() and legacy.exists() and formal.exists()


def test_audit_limit_prune_settings_and_clear_only_rows(tmp_path: Path) -> None:
    configured(tmp_path)
    sentinel = tmp_path / "data" / "sentinel.yaml"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("keep: true\n", encoding="utf-8")
    try:
        with TestClient(app) as client:
            assert client.get("/api/logs/settings").json()["maxEntries"] == 500
            store = AuditStore(tmp_path / "data")
            for index in range(8):
                client.post("/api/config/export", headers=HEADERS, json={
                    "sourceId": "default-smb", "path": "/FixCloud.yaml",
                    "baseHash": hashlib.sha256((tmp_path / "FixCloud.yaml").read_bytes()).hexdigest(),
                    "operations": [], "filename": f"{index}.yaml",
                })
            reduced = client.put("/api/logs/settings", headers=HEADERS, json={"maxEntries": 3})
            assert reduced.status_code == 200
            assert reduced.json()["currentCount"] == 3
            invalid = client.put("/api/logs/settings", headers=HEADERS, json={"maxEntries": 50001})
            assert invalid.status_code == 422
            cleared = client.request("DELETE", "/api/logs", headers=HEADERS).json()
            assert cleared["currentCount"] == 0
            assert sentinel.exists()
            assert (tmp_path / "FixCloud.yaml").exists()
    finally:
        app.dependency_overrides.clear()
