from __future__ import annotations

import asyncio
import hashlib
import re
import secrets
import shutil
import time
from contextvars import ContextVar
from pathlib import Path

COOKIE_NAME = "fixcloud_session"
SESSION_TTL_SECONDS = 24 * 60 * 60
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
_scope: ContextVar[str] = ContextVar("fixcloud_session_scope", default="")
_directory: ContextVar[Path | None] = ContextVar("fixcloud_session_directory", default=None)


def valid_token(value: str | None) -> bool:
    return bool(value and _TOKEN_PATTERN.fullmatch(value))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def scope_for_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def temporary_root(data_dir: Path) -> Path:
    return data_dir / "temporary-sessions"


def session_directory(data_dir: Path, token: str) -> Path:
    return temporary_root(data_dir) / scope_for_token(token)


def bind(scope: str, directory: Path):
    return _scope.set(scope), _directory.set(directory)


def unbind(tokens) -> None:
    scope_token, directory_token = tokens
    _scope.reset(scope_token)
    _directory.reset(directory_token)


def current_scope() -> str:
    return _scope.get()


def current_directory() -> Path:
    directory = _directory.get()
    if directory is None:
        raise RuntimeError("浏览器临时会话尚未建立")
    return directory


def touch(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    directory.touch(exist_ok=True)


def cleanup_expired(data_dir: Path, *, now: float | None = None) -> list[Path]:
    root = temporary_root(data_dir)
    if not root.is_dir():
        return []
    cutoff = (time.time() if now is None else now) - SESSION_TTL_SECONDS
    removed: list[Path] = []
    resolved_root = root.resolve()
    for candidate in root.iterdir():
        try:
            resolved = candidate.resolve()
            if (
                not candidate.is_dir()
                or candidate.is_symlink()
                or resolved.parent != resolved_root
                or not re.fullmatch(r"[0-9a-f]{64}", candidate.name)
                or candidate.stat().st_mtime >= cutoff
            ):
                continue
            shutil.rmtree(resolved)
            removed.append(resolved)
        except FileNotFoundError:
            continue
    return removed


async def cleanup_loop(data_dir: Path, stop: asyncio.Event) -> None:
    while not stop.is_set():
        await asyncio.to_thread(cleanup_expired, data_dir)
        try:
            await asyncio.wait_for(stop.wait(), timeout=60 * 60)
        except TimeoutError:
            pass
