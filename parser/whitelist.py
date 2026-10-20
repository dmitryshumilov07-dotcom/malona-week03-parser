from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from parser.settings import ROOT, get_settings


@dataclass(frozen=True)
class WhitelistEntry:
    supplier_id: str
    article: str | None
    brand: str | None
    url: str | None
    snapshot: str | None
    expect_status: str | None


@lru_cache
def load_whitelist() -> list[WhitelistEntry]:
    path: Path = get_settings().whitelist_yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: list[WhitelistEntry] = []
    for row in data.get("queries", []):
        snap = row.get("snapshot")
        if snap:
            snap = str((ROOT / snap).resolve()) if not Path(snap).is_absolute() else snap
        out.append(
            WhitelistEntry(
                supplier_id=row["supplier_id"],
                article=row.get("article"),
                brand=row.get("brand"),
                url=row.get("url"),
                snapshot=snap,
                expect_status=row.get("expect_status"),
            )
        )
    return out


def is_allowed(supplier_id: str, article: str | None, url: str | None) -> bool:
    article_n = (article or "").strip().upper()
    url_n = (url or "").strip()
    for e in load_whitelist():
        if e.supplier_id != supplier_id:
            continue
        if url_n and e.url and url_n == e.url:
            return True
        if article_n and e.article and article_n == e.article.strip().upper():
            return True
    return False


def find_snapshot(supplier_id: str, article: str | None, url: str | None) -> str | None:
    article_n = (article or "").strip().upper()
    url_n = (url or "").strip()
    for e in load_whitelist():
        if e.supplier_id != supplier_id or not e.snapshot:
            continue
        if url_n and e.url and url_n == e.url:
            return e.snapshot
        if article_n and e.article and article_n == e.article.strip().upper() and e.expect_status == "ok":
            return e.snapshot
    return None
