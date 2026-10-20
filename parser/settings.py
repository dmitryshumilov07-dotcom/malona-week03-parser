from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    parser_api_key: str = "dev-parser-key-change-me"
    parser_version: str = "1.0.0"
    parser_use_page_snapshots: bool = True
    parser_supplier_pause_sec: float = 2.0
    parser_rate_limit_per_min: int = 60
    parser_max_parallel_per_supplier: int = 5
    suppliers_yaml: Path = ROOT / "config" / "suppliers.yaml"
    whitelist_yaml: Path = ROOT / "fixtures" / "suppliers_test_queries.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
