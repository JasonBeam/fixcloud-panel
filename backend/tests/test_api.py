from pathlib import Path

from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.main import app


CONFIG = b"""port: 7890
secret: should-not-leak
proxies:
  - name: Local
    type: socks5
    server: 127.0.0.1
    port: 7891
    password: proxy-private
proxy-groups:
  - name: Proxy
    type: select
    proxies: [Local]
rules:
  - MATCH,Proxy
unknown-block:
  enabled: true
"""


def test_internal_preview_and_save(tmp_path: Path) -> None:
    config = tmp_path / "FixCloud.yaml"
    config.write_bytes(CONFIG)
    rules = tmp_path / "rules"
    rules.mkdir()
    rule_file = rules / "AdBlock.yaml"
    rule_file.write_text("payload:\n  - DOMAIN-SUFFIX,ads.example\n", encoding="utf-8")
    rule_hash = rule_file.read_bytes()
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
    try:
        with TestClient(app) as client:
            assert client.post("/api/sources/default-smb/test").status_code == 403
            headers = {"X-FixCloud-Request": "1"}
            config_response = client.get("/api/config")
            assert "img-src 'self' data: https: http:" in config_response.headers["content-security-policy"]
            document = config_response.json()
            assert document["document"]["secret"] == "should-not-leak"
            assert document["document"]["proxies"][0]["password"] == "proxy-private"
            assert document["document"]["unknown-block"]["enabled"] is True
            sources = client.get("/api/sources").json()
            assert [source["id"] for source in sources["sources"]] == ["default-smb", "uploaded-files"]
            catalog = client.get("/api/files/catalog").json()["files"]
            assert [item["name"] for item in catalog] == ["FixCloud.yaml"]
            browser = client.get("/api/files", params={"sourceId": "default-smb"}).json()
            assert [item["name"] for item in browser["entries"]] == ["FixCloud.yaml"]
            blocked = client.post(
                "/api/files/select",
                headers=headers,
                json={"sourceId": "default-smb", "path": "/rules/AdBlock.yaml"},
            )
            assert blocked.status_code == 422
            blocked_restore = client.post(
                "/api/history/restore-preview",
                headers=headers,
                json={
                    "sourceId": "default-smb",
                    "path": "/FixCloud.yaml",
                    "backupPath": "/rules/AdBlock.yaml",
                },
            )
            assert blocked_restore.status_code == 422

            preview = client.post(
                "/api/config/preview",
                headers=headers,
                json={
                    "sourceId": "default-smb",
                    "path": "/FixCloud.yaml",
                    "baseHash": document["file"]["hash"],
                    "operations": [{"op": "set", "path": ["port"], "value": 7895}],
                },
            )
            assert preview.status_code == 200
            assert "port: 7895" in preview.json()["diff"]["text"]

            saved = client.post(
                "/api/config/save",
                headers=headers,
                json={"previewToken": preview.json()["previewToken"]},
            )
            assert saved.status_code == 200
            assert b"port: 7895" in config.read_bytes()
            assert saved.json()["backupPath"] is None
            assert not list(tmp_path.glob("FixCloud.yaml.backup-*.yaml"))
            assert not list(tmp_path.glob(".*.rollback-*.yaml"))
            history = client.get(
                "/api/history",
                params={"sourceId": "default-smb", "path": "/FixCloud.yaml"},
            ).json()
            assert history["backups"] == []
            assert history["audit"][0]["username"] == "内网访问"
            assert history["audit"][0]["sourceId"] == "default-smb"

            blocked_delete = client.request(
                "DELETE",
                "/api/history/backup",
                headers=headers,
                json={
                    "sourceId": "default-smb",
                    "path": "/FixCloud.yaml",
                    "backupPath": "/FixCloud.yaml",
                },
            )
            assert blocked_delete.status_code == 422
            assert b"port: 7895" in config.read_bytes()

            legacy_backup = tmp_path / "FixCloud.yaml.backup-20260726-120000.yaml"
            legacy_backup.write_bytes(CONFIG)
            history = client.get(
                "/api/history",
                params={"sourceId": "default-smb", "path": "/FixCloud.yaml"},
            ).json()
            assert len(history["backups"]) == 1
            backup_path = history["backups"][0]["path"]

            deleted = client.request(
                "DELETE",
                "/api/history/backup",
                headers=headers,
                json={
                    "sourceId": "default-smb",
                    "path": "/FixCloud.yaml",
                    "backupPath": backup_path,
                },
            )
            assert deleted.status_code == 200
            assert not list(tmp_path.glob("FixCloud.yaml.backup-*.yaml"))
            after_delete = client.get(
                "/api/history",
                params={"sourceId": "default-smb", "path": "/FixCloud.yaml"},
            ).json()
            assert after_delete["backups"] == []
            assert after_delete["audit"][0]["action"] == "delete-history"
            assert rule_file.read_bytes() == rule_hash
    finally:
        app.dependency_overrides.clear()


def test_config_selection_is_request_scoped(tmp_path: Path) -> None:
    first = tmp_path / "First.yaml"
    second = tmp_path / "Second.yaml"
    first.write_text("port: 7001\nrules: []\n", encoding="utf-8")
    second.write_text("port: 7002\nrules: []\n", encoding="utf-8")
    settings = Settings(
        app_env="test",
        app_data_dir=tmp_path / "data",
        storage_backend="local",
        storage_root=tmp_path,
        yaml_path="/First.yaml",
        write_enabled=True,
        frontend_dist=tmp_path / "missing",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            first_payload = client.get(
                "/api/config",
                params={"sourceId": "default-smb", "path": "/First.yaml"},
            ).json()
            second_payload = client.get(
                "/api/config",
                params={"sourceId": "default-smb", "path": "/Second.yaml"},
            ).json()

            assert first_payload["document"]["port"] == 7001
            assert second_payload["document"]["port"] == 7002
            assert first_payload["file"]["path"] == "/First.yaml"
            assert second_payload["file"]["path"] == "/Second.yaml"
    finally:
        app.dependency_overrides.clear()
