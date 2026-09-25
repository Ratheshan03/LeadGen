"""
Loads the business types to crawl from config/business_types.yaml.

The file is re-read automatically when it changes, so edits take effect
without restarting anything.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import yaml

from backend.config.settings import CONFIG_DIR

BUSINESS_TYPES_FILE = CONFIG_DIR / "business_types.yaml"


class BusinessTypesError(ValueError):
    """config/business_types.yaml is missing or malformed."""


@dataclass(frozen=True)
class BusinessTypes:
    categories: dict[str, list[str]]     # category -> types, in file order

    @property
    def all_types(self) -> list[str]:
        """Every distinct type, sorted - the order an "ALL" crawl runs in."""
        return sorted({t for types in self.categories.values() for t in types})

    @property
    def type_to_category(self) -> dict[str, str]:
        return {t: cat for cat, types in self.categories.items() for t in types}

    def resolve(self, requested) -> list[str]:
        """
        Turn a request into a list of types. Accepts "ALL", a category name,
        a single type, or a list of any of these.
        """
        items = requested if isinstance(requested, (list, tuple)) else [requested]
        out: list[str] = []
        by_category = {c.lower(): t for c, t in self.categories.items()}
        for item in items:
            key = normalise_type(str(item))
            if key in ("all", ""):
                return self.all_types
            if str(item).strip().lower() in by_category:
                out.extend(by_category[str(item).strip().lower()])
            else:
                out.append(key)
        seen: set[str] = set()
        return [t for t in out if not (t in seen or seen.add(t))]


def normalise_type(value: str) -> str:
    """'Car Repair ' -> 'car_repair'"""
    return "_".join(value.strip().lower().replace("-", " ").split())


def _parse(path: Path) -> BusinessTypes:
    if not path.exists():
        raise BusinessTypesError(f"Business types file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise BusinessTypesError(f"{path.name} is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise BusinessTypesError(f"{path.name} must map category names to lists of types.")
    categories: dict[str, list[str]] = {}
    for category, types in raw.items():
        if types is None:
            continue
        if not isinstance(types, list):
            raise BusinessTypesError(f"Category '{category}' in {path.name} must be a list of types (lines starting with '- ').")
        cleaned = [normalise_type(str(t)) for t in types if t is not None and str(t).strip()]
        if cleaned:
            categories[str(category).strip()] = cleaned
    if not categories:
        raise BusinessTypesError(f"{path.name} does not list any business types.")
    return BusinessTypes(categories)


_lock = threading.Lock()
_cached: tuple[float, BusinessTypes] | None = None


def get_business_types(path: Path = BUSINESS_TYPES_FILE) -> BusinessTypes:
    """Current business types (re-read if the file changed)."""
    global _cached
    if path != BUSINESS_TYPES_FILE:
        return _parse(path)
    with _lock:
        mtime = path.stat().st_mtime if path.exists() else -1
        if _cached is None or _cached[0] != mtime:
            _cached = (mtime, _parse(path))
        return _cached[1]
