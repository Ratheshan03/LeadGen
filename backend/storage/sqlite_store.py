"""Default storage: a single local SQLite file (storage/leadgen.db)."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from backend.storage.base import (
    INSERTED, LEAD_FIELDS, REFRESHABLE_FIELDS, UNCHANGED, UPDATED, LeadFilter, LeadStore, now_iso,
)

_LIST_FIELDS = ("types", "opening_hours")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    place_id        TEXT PRIMARY KEY,
    name            TEXT,
    address         TEXT,
    phone           TEXT,
    phone_local     TEXT,
    website         TEXT,
    google_maps_url TEXT,
    rating          REAL,
    review_count    INTEGER,
    business_status TEXT,
    primary_type    TEXT,
    types           TEXT,   -- JSON list
    opening_hours   TEXT,   -- JSON list
    latitude        REAL,
    longitude       REAL,
    country         TEXT,
    state           TEXT,
    council         TEXT,
    sa2             TEXT,
    source          TEXT,
    first_seen      TEXT,
    last_seen       TEXT
);
CREATE TABLE IF NOT EXISTS lead_business_types (
    place_id      TEXT NOT NULL REFERENCES leads(place_id) ON DELETE CASCADE,
    business_type TEXT NOT NULL,
    PRIMARY KEY (place_id, business_type)
);
CREATE INDEX IF NOT EXISTS idx_leads_location ON leads(country, state, council);
CREATE INDEX IF NOT EXISTS idx_leads_name ON leads(name);
CREATE INDEX IF NOT EXISTS idx_lbt_type ON lead_business_types(business_type);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id         TEXT,
    mode           TEXT,
    country        TEXT,
    level          TEXT,
    state          TEXT,
    area           TEXT,
    business_types TEXT,
    dense          INTEGER,
    status         TEXT,
    started_at     TEXT,
    finished_at    TEXT,
    tiles          INTEGER,
    requests       INTEGER,
    leads_found    INTEGER,
    leads_new      INTEGER,
    excel_file     TEXT,
    error          TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_area ON crawl_runs(country, level, state, area);
"""

_RUN_FIELDS = ("job_id", "mode", "country", "level", "state", "area", "business_types", "dense", "status",
               "started_at", "finished_at", "tiles", "requests", "leads_found", "leads_new", "excel_file", "error")


class SQLiteLeadStore(LeadStore):
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        with self._conn() as c:
            c.executescript(_SCHEMA)

    # One connection per thread (the crawler writes from a worker thread while
    # the API reads from others). WAL lets reads continue during writes.
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def describe(self) -> str:
        return f"SQLite ({self.path})"

    # --- leads ---------------------------------------------------------------
    def upsert_lead(self, lead: dict, business_type: str) -> str:
        now = now_iso()
        row = {f: lead.get(f) for f in LEAD_FIELDS if f != "business_types"}
        for f in _LIST_FIELDS:
            row[f] = json.dumps(row.get(f) or [], ensure_ascii=False)
        with self._write_lock:
            conn = self._conn()
            with conn:
                exists = conn.execute("SELECT 1 FROM leads WHERE place_id=?", (row["place_id"],)).fetchone()
                if not exists:
                    row["first_seen"] = row["last_seen"] = now
                    cols = ", ".join(row)
                    conn.execute(f"INSERT INTO leads ({cols}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))
                    outcome = INSERTED
                else:
                    updates = {f: row[f] for f in REFRESHABLE_FIELDS
                               if row.get(f) not in (None, "", "[]")}
                    updates["last_seen"] = now
                    conn.execute(
                        f"UPDATE leads SET {', '.join(f'{k}=?' for k in updates)} WHERE place_id=?",
                        (*updates.values(), row["place_id"]),
                    )
                    outcome = None
                cur = conn.execute(
                    "INSERT OR IGNORE INTO lead_business_types (place_id, business_type) VALUES (?, ?)",
                    (row["place_id"], business_type),
                )
                if outcome is None:
                    outcome = UPDATED if cur.rowcount else UNCHANGED
        return outcome

    def _where(self, flt: LeadFilter) -> tuple[str, list]:
        clauses, params = [], []
        for field in ("country", "state", "council"):
            value = getattr(flt, field)
            if value:
                clauses.append(f"l.{field} = ? COLLATE NOCASE")
                params.append(value)
        if flt.business_type:
            clauses.append("EXISTS (SELECT 1 FROM lead_business_types b WHERE b.place_id = l.place_id AND b.business_type = ?)")
            params.append(flt.business_type)
        if flt.search:
            clauses.append("l.name LIKE ? ESCAPE '\\'")
            escaped = flt.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params.append(f"%{escaped}%")
        if flt.has_phone is not None:
            clauses.append("COALESCE(l.phone, l.phone_local, '') " + ("!= ''" if flt.has_phone else "= ''"))
        if flt.has_website is not None:
            clauses.append("COALESCE(l.website, '') " + ("!= ''" if flt.has_website else "= ''"))
        if flt.place_ids is not None:
            if not flt.place_ids:
                clauses.append("0")
            else:
                clauses.append(f"l.place_id IN ({', '.join('?' * len(flt.place_ids))})")
                params.extend(flt.place_ids)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def _row_to_lead(self, row: sqlite3.Row, types_by_place: dict[str, list[str]]) -> dict:
        lead = dict(row)
        for f in _LIST_FIELDS:
            lead[f] = json.loads(lead[f]) if lead.get(f) else []
        lead["business_types"] = types_by_place.get(lead["place_id"], [])
        return lead

    def query_leads(self, flt: LeadFilter, offset: int = 0, limit: int | None = 100) -> tuple[int, list[dict]]:
        conn = self._conn()
        where, params = self._where(flt)
        total = conn.execute(f"SELECT COUNT(*) FROM leads l{where}", params).fetchone()[0]
        sql = f"SELECT l.* FROM leads l{where} ORDER BY l.name COLLATE NOCASE, l.place_id"
        page_params = list(params)
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            page_params += [int(limit), int(offset)]
        rows = conn.execute(sql, page_params).fetchall()
        types_by_place: dict[str, list[str]] = {}
        ids = [r["place_id"] for r in rows]
        for i in range(0, len(ids), 900):  # SQLite parameter limit
            chunk = ids[i:i + 900]
            for r in conn.execute(
                f"SELECT place_id, business_type FROM lead_business_types WHERE place_id IN ({', '.join('?' * len(chunk))}) "
                "ORDER BY business_type", chunk,
            ):
                types_by_place.setdefault(r["place_id"], []).append(r["business_type"])
        return total, [self._row_to_lead(r, types_by_place) for r in rows]

    def summary(self, flt: LeadFilter) -> dict:
        conn = self._conn()
        where, params = self._where(flt)
        total, with_phone, with_website = conn.execute(
            "SELECT COUNT(*), SUM(COALESCE(l.phone, l.phone_local, '') != ''), SUM(COALESCE(l.website, '') != '') "
            f"FROM leads l{where}", params,
        ).fetchone()

        def grouped(column: str) -> dict:
            rows = conn.execute(
                f"SELECT COALESCE(l.{column}, 'Unknown') k, COUNT(*) n FROM leads l{where} GROUP BY k ORDER BY n DESC",
                params,
            ).fetchall()
            return {r["k"]: r["n"] for r in rows}

        by_type = conn.execute(
            "SELECT b.business_type k, COUNT(*) n FROM lead_business_types b JOIN leads l ON l.place_id = b.place_id"
            f"{where} GROUP BY k ORDER BY n DESC", params,
        ).fetchall()
        return {
            "total": total or 0, "with_phone": with_phone or 0, "with_website": with_website or 0,
            "by_country": grouped("country"), "by_state": grouped("state"), "by_council": grouped("council"),
            "by_business_type": {r["k"]: r["n"] for r in by_type},
        }

    def count(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    # --- crawl history -------------------------------------------------------
    def start_run(self, run: dict) -> str:
        row = {f: run.get(f) for f in _RUN_FIELDS}
        row["started_at"] = row["started_at"] or now_iso()
        row["status"] = row["status"] or "running"
        row["dense"] = int(bool(row["dense"]))
        with self._write_lock:
            conn = self._conn()
            with conn:
                cur = conn.execute(
                    f"INSERT INTO crawl_runs ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()),
                )
        return str(cur.lastrowid)

    def finish_run(self, run_id: str, updates: dict) -> None:
        updates = {k: v for k, v in updates.items() if k in _RUN_FIELDS}
        updates.setdefault("finished_at", now_iso())
        with self._write_lock:
            conn = self._conn()
            with conn:
                conn.execute(
                    f"UPDATE crawl_runs SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
                    (*updates.values(), int(run_id)),
                )

    def list_runs(self, country: str | None = None, state: str | None = None, limit: int = 200) -> list[dict]:
        clauses, params = [], []
        if country:
            clauses.append("country = ?")
            params.append(country)
        if state:
            clauses.append("state = ? COLLATE NOCASE")
            params.append(state)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._conn().execute(f"SELECT * FROM crawl_runs{where} ORDER BY id DESC LIMIT ?", (*params, limit))
        out = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d["id"])
            d["dense"] = bool(d["dense"])
            out.append(d)
        return out

    def completed_areas(self, country: str, level: str, types_key: str, dense: bool) -> set[tuple[str, str]]:
        rows = self._conn().execute(
            "SELECT state, area FROM crawl_runs WHERE country=? AND level=? AND business_types=? AND dense=? "
            "AND status='completed' AND mode != 'nearby'",
            (country, level, types_key, int(bool(dense))),
        )
        return {(r["state"], r["area"]) for r in rows}

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
