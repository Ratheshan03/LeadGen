"""
Optional storage: MongoDB (local or Atlas). Enable with STORAGE=mongodb and
MONGO_DB_URI / MONGO_DB_NAME in .env. Reads leads written by earlier LeadGen
versions too (nested `location`, `region` instead of `council`).
"""
from __future__ import annotations

import re

from backend.storage.base import (
    INSERTED, LEAD_FIELDS, REFRESHABLE_FIELDS, UNCHANGED, UPDATED, LeadFilter, LeadStore, now_iso,
)


class MongoLeadStore(LeadStore):
    def __init__(self, uri: str, db_name: str, client=None):
        try:
            from pymongo import ASCENDING, DESCENDING, MongoClient
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pymongo is not installed: pip install -r requirements.txt") from exc
        if client is None:
            if not uri:
                raise RuntimeError("STORAGE=mongodb but MONGO_DB_URI is empty in .env")
            options = {"serverSelectionTimeoutMS": 15000}
            if uri.startswith("mongodb+srv://") or "tls=true" in uri.lower():
                import certifi  # installed with requests
                options["tlsCAFile"] = certifi.where()
            client = MongoClient(uri, **options)
            client.admin.command("ping")  # fail fast with a clear error
        self._client = client
        self._db = self._client[db_name]
        self._uri_host = re.sub(r"//[^@]*@", "//", uri).split("?")[0]
        self.leads = self._db["leads"]
        self.runs = self._db["crawl_runs"]
        self.leads.create_index([("place_id", ASCENDING)], unique=True, name="unique_place_id_index")
        self.leads.create_index([("country", ASCENDING), ("state", ASCENDING), ("council", ASCENDING)])
        self.leads.create_index([("business_types", ASCENDING)])
        self.runs.create_index([("country", ASCENDING), ("level", ASCENDING), ("state", ASCENDING), ("area", ASCENDING)])
        self._desc = DESCENDING

    def describe(self) -> str:
        return f"MongoDB ({self._uri_host}, database '{self._db.name}')"

    # --- leads ---------------------------------------------------------------
    def upsert_lead(self, lead: dict, business_type: str) -> str:
        now = now_iso()
        doc = {f: lead.get(f) for f in LEAD_FIELDS if f not in ("business_types", "first_seen", "last_seen")}
        existing = self.leads.find_one({"place_id": doc["place_id"]}, {"business_types": 1, "business_type": 1})
        if existing is None:
            doc.update(business_types=[business_type], first_seen=now, last_seen=now)
            self.leads.insert_one(doc)
            return INSERTED
        known = set(existing.get("business_types") or [])
        if existing.get("business_type"):
            known.add(existing["business_type"])
        updates = {f: doc[f] for f in REFRESHABLE_FIELDS if doc.get(f) not in (None, "", [])}
        updates["last_seen"] = now
        self.leads.update_one({"place_id": doc["place_id"]},
                              {"$set": updates, "$addToSet": {"business_types": business_type}})
        return UNCHANGED if business_type in known else UPDATED

    @staticmethod
    def _query(flt: LeadFilter) -> dict:
        q: dict = {}
        ci = lambda v: {"$regex": f"^{re.escape(v)}$", "$options": "i"}  # noqa: E731
        if flt.country:
            q["country"] = ci(flt.country)
        if flt.state:
            q["state"] = ci(flt.state)
        if flt.council:
            q["$or"] = [{"council": ci(flt.council)}, {"region": ci(flt.council)}]
        if flt.business_type:
            q["business_types"] = flt.business_type
        if flt.search:
            q["name"] = {"$regex": re.escape(flt.search), "$options": "i"}
        if flt.has_phone is not None:
            q["phone"] = {"$nin": [None, ""]} if flt.has_phone else {"$in": [None, ""]}
        if flt.has_website is not None:
            q["website"] = {"$nin": [None, ""]} if flt.has_website else {"$in": [None, ""]}
        if flt.place_ids is not None:
            q["place_id"] = {"$in": list(flt.place_ids)}
        return q

    @staticmethod
    def _normalise(doc: dict) -> dict:
        doc.pop("_id", None)
        loc = doc.pop("location", None) or {}
        doc.setdefault("latitude", loc.get("latitude", loc.get("lat")))
        doc.setdefault("longitude", loc.get("longitude", loc.get("lng")))
        doc.setdefault("council", doc.get("region"))
        doc.setdefault("review_count", doc.get("total_reviews"))
        doc.setdefault("last_seen", doc.get("retrieved_at"))
        if doc.get("business_type") and doc["business_type"] not in (doc.get("business_types") or []):
            doc["business_types"] = [*(doc.get("business_types") or []), doc["business_type"]]
        lead = {f: doc.get(f) for f in LEAD_FIELDS}
        for f in ("types", "business_types", "opening_hours"):
            lead[f] = list(lead.get(f) or [])
        for f in ("first_seen", "last_seen"):
            if lead[f] is not None and not isinstance(lead[f], str):
                lead[f] = lead[f].isoformat()
        return lead

    def query_leads(self, flt: LeadFilter, offset: int = 0, limit: int | None = 100) -> tuple[int, list[dict]]:
        q = self._query(flt)
        total = self.leads.count_documents(q)
        cursor = self.leads.find(q).sort([("name", 1), ("place_id", 1)]).skip(int(offset))
        if limit is not None:
            cursor = cursor.limit(int(limit))
        return total, [self._normalise(d) for d in cursor]

    def summary(self, flt: LeadFilter) -> dict:
        q = self._query(flt)

        def grouped(field: str) -> dict:
            rows = self.leads.aggregate([{"$match": q}, {"$group": {"_id": f"${field}", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}])
            return {(r["_id"] or "Unknown"): r["n"] for r in rows}

        by_type = self.leads.aggregate([
            {"$match": q}, {"$unwind": "$business_types"},
            {"$group": {"_id": "$business_types", "n": {"$sum": 1}}}, {"$sort": {"n": -1}},
        ])
        return {
            "total": self.leads.count_documents(q),
            "with_phone": self.leads.count_documents({**q, "phone": {"$nin": [None, ""]}}),
            "with_website": self.leads.count_documents({**q, "website": {"$nin": [None, ""]}}),
            "by_country": grouped("country"), "by_state": grouped("state"), "by_council": grouped("council"),
            "by_business_type": {r["_id"]: r["n"] for r in by_type},
        }

    def count(self) -> int:
        return self.leads.estimated_document_count()

    # --- crawl history -------------------------------------------------------
    def start_run(self, run: dict) -> str:
        doc = dict(run)
        doc.setdefault("started_at", now_iso())
        doc.setdefault("status", "running")
        doc["dense"] = bool(doc.get("dense"))
        return str(self.runs.insert_one(doc).inserted_id)

    def finish_run(self, run_id: str, updates: dict) -> None:
        from bson import ObjectId
        updates = dict(updates)
        updates.setdefault("finished_at", now_iso())
        self.runs.update_one({"_id": ObjectId(run_id)}, {"$set": updates})

    def list_runs(self, country: str | None = None, state: str | None = None, limit: int = 200) -> list[dict]:
        q = {}
        if country:
            q["country"] = country
        if state:
            q["state"] = {"$regex": f"^{re.escape(state)}$", "$options": "i"}
        out = []
        for d in self.runs.find(q).sort("_id", self._desc).limit(limit):
            d["id"] = str(d.pop("_id"))
            out.append(d)
        return out

    def completed_areas(self, country: str, level: str, types_key: str, dense: bool) -> set[tuple[str, str]]:
        q = {"country": country, "level": level, "business_types": types_key, "dense": bool(dense),
             "status": "completed", "mode": {"$ne": "nearby"}}
        return {(d.get("state"), d.get("area")) for d in self.runs.find(q, {"state": 1, "area": 1})}

    def close(self) -> None:
        self._client.close()
