from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path


class AppStateStore:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "state.json"

    def _read(self, default_source_id: str, default_yaml_path: str) -> tuple[str, str]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            selected = payload.get("selectedYamlPath")
            source_id = payload.get("selectedSourceId", default_source_id)
            if isinstance(selected, str) and selected.startswith("/"):
                return str(source_id), selected
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return default_source_id, default_yaml_path

    async def selected(
        self,
        default_source_id: str,
        default_yaml_path: str,
    ) -> tuple[str, str]:
        return await asyncio.to_thread(self._read, default_source_id, default_yaml_path)

    def _write(self, source_id: str, selected_path: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "selectedSourceId": source_id,
                    "selectedYamlPath": selected_path,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    async def select(self, source_id: str, selected_path: str) -> None:
        if (
            not source_id
            or not selected_path.startswith("/")
            or not selected_path.lower().endswith((".yaml", ".yml"))
            or "\x00" in selected_path
        ):
            raise ValueError("只能选择 YAML 文件")
        await asyncio.to_thread(self._write, source_id, selected_path)
