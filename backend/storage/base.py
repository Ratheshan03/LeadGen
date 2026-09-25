"""
Storage interface shared by the SQLite (default) and MongoDB backends.

A lead is a plain dict with these keys:
    place_id, name, address, phone, phone_local, website, google_maps_url,
    rating, review_count, business_status, primary_type, types (list),
    business_types (list), opening_hours (list), latitude, longitude,
    country, state, council, sa2, source, first_seen, last_seen
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

LEAD_FIELDS = (
    "place_id", "name", "address", "phone", "phone_local", "website", "google_maps_url",
    "rating", "review_count", "business_status", "primary_type", "types", "business_types",
    "opening_hours", "latitude", "longitude", "country", "state", "council", "sa2",
    "source", "first_seen", "last_seen",
)
# Refreshed from Google every time a lead is seen again (when Google returns a value).
REFRESHABLE_FIELDS = (
    "name", "address", "phone", "phone_local", "website", "google_maps_url", "rating",
    "review_count", "business_status", "primary_type", "types", "opening_hours",
    "latitude", "longitude", "country", "state", "council", "sa2",
)

INSERTED, UPDATED, UNCHANGED = "inserted", "updated", "unchanged"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class LeadFilter:
    country: str | None = None
    state: str | None = None
    council: str | None = None
    business_type: str | None = None
    search: str | None = None          # name contains (case-insensitive)
    has_phone: bool | None = None
    has_website: bool | None = None
    place_ids: list[str] | None = None


class LeadStore(ABC):
    """Everything the app needs from a database."""

    # --- leads ---------------------------------------------------------------
    @abstractmethod
    def upsert_lead(self, lead: dict, business_type: str) -> str:
        """
        Insert a new lead, or refresh an existing one and add `business_type`
        to its business_types. Returns INSERTED, UPDATED (new business type
        added) or UNCHANGED (already had that type; details refreshed).
        """

    @abstractmethod
    def query_leads(self, flt: LeadFilter, offset: int = 0, limit: int | None = 100) -> tuple[int, list[dict]]:
        """(total matching, page of leads sorted by name)."""

    @abstractmethod
    def summary(self, flt: LeadFilter) -> dict:
        """{"total", "with_phone", "with_website", "by_state", "by_council", "by_business_type"}"""

    @abstractmethod
    def count(self) -> int: ...

    # --- crawl history -------------------------------------------------------
    @abstractmethod
    def start_run(self, run: dict) -> str: ...

    @abstractmethod
    def finish_run(self, run_id: str, updates: dict) -> None: ...

    @abstractmethod
    def list_runs(self, country: str | None = None, state: str | None = None, limit: int = 200) -> list[dict]: ...

    @abstractmethod
    def completed_areas(self, country: str, level: str, types_key: str, dense: bool) -> set[tuple[str, str]]:
        """{(state, area)} that finished a crawl with the same settings."""

    # --- misc ----------------------------------------------------------------
    @abstractmethod
    def describe(self) -> str: ...

    def close(self) -> None:  # pragma: no cover - optional
        pass
