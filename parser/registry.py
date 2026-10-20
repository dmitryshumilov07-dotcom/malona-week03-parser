from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from parser.settings import get_settings


@dataclass(frozen=True)
class SupplierConfig:
    id: str
    name: str
    base_url: str
    enabled: bool
    parser_module: str
    disabled_reason: str | None = None


@lru_cache
def load_suppliers() -> dict[str, SupplierConfig]:
    path: Path = get_settings().suppliers_yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, SupplierConfig] = {}
    for row in data.get("suppliers", []):
        cfg = SupplierConfig(
            id=row["id"],
            name=row["name"],
            base_url=row["base_url"],
            enabled=bool(row.get("enabled", True)),
            parser_module=row["parser_module"],
            disabled_reason=row.get("disabled_reason"),
        )
        out[cfg.id] = cfg
    return out
