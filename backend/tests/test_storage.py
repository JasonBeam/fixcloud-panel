from pathlib import Path

import pytest

from app.services.storage.mounted import MountedFilesystemStorage


@pytest.mark.asyncio
async def test_mounted_storage_lists_yaml_and_blocks_traversal(tmp_path: Path) -> None:
    (tmp_path / "FixCloud.yaml").write_text("mode: rule\n", encoding="utf-8")
    storage = MountedFilesystemStorage(tmp_path)

    entries = await storage.list_dir("/")
    assert [entry.name for entry in entries] == ["FixCloud.yaml"]

    with pytest.raises(ValueError):
        await storage.read_bytes("/../outside.yaml")

