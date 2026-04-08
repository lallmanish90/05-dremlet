from __future__ import annotations

from dataclasses import dataclass
import json
from importlib import resources
from typing import Any


@dataclass(frozen=True)
class WidgetSpec:
    kind: str
    name: str
    label: str | None
    key: str | None
    value_type: str
    default: Any
    generated_flag: str | None


@dataclass(frozen=True)
class PageEntry:
    page_id: str
    module_name: str
    source_file: str
    title: str
    status: str
    purpose: str
    source_compiles: bool
    widgets: tuple[WidgetSpec, ...]


def _catalog_path():
    return resources.files("dreamlet_cli").joinpath("page_catalog.json")


def load_catalog() -> dict[str, PageEntry]:
    raw = json.loads(_catalog_path().read_text(encoding="utf-8"))
    catalog: dict[str, PageEntry] = {}
    for item in raw:
        widgets = tuple(WidgetSpec(**widget) for widget in item["widgets"])
        catalog[item["page_id"]] = PageEntry(
            page_id=item["page_id"],
            module_name=item["module_name"],
            source_file=item["source_file"],
            title=item["title"],
            status=item["status"],
            purpose=item["purpose"],
            source_compiles=item["source_compiles"],
            widgets=widgets,
        )
    return catalog


def sorted_pages() -> list[PageEntry]:
    return sorted(load_catalog().values(), key=lambda item: item.page_id)
