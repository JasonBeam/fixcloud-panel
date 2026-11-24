from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_data_dir: Path = Path("/data")
    storage_backend: str = "smb-mounted"
    storage_root: Path = Path("/mnt/fixcloud")
    yaml_path: str = "/FixCloud.yaml"

    write_enabled: bool = False

    webdav_url: str = ""
    webdav_username: str = ""
    webdav_password: str = Field(default="", repr=False)
    webdav_yaml_path: str = "/FixCloud.yaml"

    public_file_base_url: str = "https://file.example.com"

    frontend_dist: Path = Path("/app/frontend/dist")


@lru_cache
def get_settings() -> Settings:
    return Settings()
