from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.browser_session import current_scope

DEFAULT_LIMIT = 500
MAX_LIMIT = 50_000


class AuditStore:
    def __init__(self, data_dir: Path):
        self.database = data_dir / "audit.sqlite3"

    def _connect(self) -> sqlite3.Connection:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                username TEXT NOT NULL, action TEXT NOT NULL, path TEXT NOT NULL,
                before_hash TEXT NOT NULL, after_hash TEXT NOT NULL,
                backup_path TEXT, details TEXT NOT NULL
            )
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(audit_log)")}
        if "source_id" not in columns:
            connection.execute(
                "ALTER TABLE audit_log ADD COLUMN source_id TEXT NOT NULL DEFAULT 'legacy'"
            )
        if "session_scope" not in columns:
            connection.execute(
                "ALTER TABLE audit_log ADD COLUMN session_scope TEXT NOT NULL DEFAULT ''"
            )
        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            )
        """)
        connection.execute(
            "INSERT OR IGNORE INTO app_settings(key, value) VALUES ('audit_limit', ?)",
            (str(DEFAULT_LIMIT),),
        )
        connection.commit()
        return connection

    @staticmethod
    def _limit(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT value FROM app_settings WHERE key='audit_limit'"
        ).fetchone()
        try:
            return max(1, min(int(row["value"]), MAX_LIMIT))
        except (TypeError, ValueError):
            return DEFAULT_LIMIT

    @staticmethod
    def _prune(connection: sqlite3.Connection, limit: int) -> None:
        connection.execute(
            "DELETE FROM audit_log WHERE id NOT IN "
            "(SELECT id FROM audit_log ORDER BY id DESC LIMIT ?)",
            (limit,),
        )

    async def record(
        self, *, source_id: str, username: str, action: str, path: str,
        before_hash: str, after_hash: str, backup_path: str | None,
        details: dict[str, Any],
    ) -> None:
        scope = current_scope() if source_id == "uploaded-files" else ""

        def write() -> None:
            with self._connect() as connection:
                connection.execute("""
                    INSERT INTO audit_log (
                        created_at, source_id, session_scope, username, action, path,
                        before_hash, after_hash, backup_path, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(), source_id, scope, username,
                    action, path, before_hash, after_hash, backup_path,
                    json.dumps(details, ensure_ascii=False),
                ))
                self._prune(connection, self._limit(connection))
                connection.commit()
        await asyncio.to_thread(write)

    async def record_event(
        self, *, source_id: str, action: str, path: str, status: str,
        message: str, details: dict[str, Any] | None = None,
    ) -> None:
        await self.record(
            source_id=source_id, username="内网访问", action=action, path=path,
            before_hash="", after_hash="", backup_path=None,
            details={"status": status, "message": message, **(details or {})},
        )

    async def list_recent(
        self, *, source_id: str | None = None, path: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        scope = current_scope()

        def read() -> list[dict[str, Any]]:
            with self._connect() as connection:
                where = ["(session_scope = '' OR session_scope = ?)"]
                parameters: list[Any] = [scope]
                if source_id:
                    where.append("source_id = ?")
                    parameters.append(source_id)
                if path:
                    where.append("path = ?")
                    parameters.append(path)
                parameters.append(max(1, min(limit, 5000)))
                rows = connection.execute(
                    "SELECT * FROM audit_log WHERE " + " AND ".join(where)
                    + " ORDER BY id DESC LIMIT ?", parameters,
                ).fetchall()
            return [{
                "id": row["id"], "createdAt": row["created_at"],
                "sourceId": row["source_id"], "username": row["username"],
                "action": row["action"], "path": row["path"],
                "beforeHash": row["before_hash"], "afterHash": row["after_hash"],
                "backupPath": row["backup_path"], "details": json.loads(row["details"]),
            } for row in rows]
        return await asyncio.to_thread(read)

    async def delete_backup_records(
        self, *, source_id: str, path: str, backup_path: str,
    ) -> int:
        scope = current_scope() if source_id == "uploaded-files" else ""

        def remove() -> int:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM audit_log WHERE source_id=? AND path=? "
                    "AND backup_path=? AND session_scope=?",
                    (source_id, path, backup_path, scope),
                )
                connection.commit()
                return max(0, cursor.rowcount)
        return await asyncio.to_thread(remove)

    async def settings(self) -> dict[str, int]:
        scope = current_scope()

        def read() -> dict[str, int]:
            with self._connect() as connection:
                count = connection.execute(
                    "SELECT COUNT(*) count FROM audit_log "
                    "WHERE session_scope='' OR session_scope=?",
                    (scope,),
                ).fetchone()["count"]
                return {"maxEntries": self._limit(connection), "currentCount": count}
        return await asyncio.to_thread(read)

    async def set_limit(self, limit: int) -> dict[str, int]:
        if limit < 1 or limit > MAX_LIMIT:
            raise ValueError(f"最大日志条数必须是 1 到 {MAX_LIMIT} 的整数")

        def update() -> None:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO app_settings(key,value) VALUES('audit_limit',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(limit),),
                )
                self._prune(connection, limit)
                connection.commit()
        await asyncio.to_thread(update)
        return await self.settings()

    async def clear(self) -> dict[str, int]:
        def remove() -> None:
            with self._connect() as connection:
                connection.execute("DELETE FROM audit_log")
                connection.commit()
        await asyncio.to_thread(remove)
        return await self.settings()
