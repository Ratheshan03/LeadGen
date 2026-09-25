"""Shared helpers for the dashboard pages."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cli.api_client import BackendClient, BackendError  # noqa: E402

FINISHED = ("completed", "quota_reached", "cancelled", "failed")
STATUS_LABELS = {
    "queued": "Waiting to start", "running": "Running", "completed": "Completed",
    "quota_reached": "Stopped - monthly request cap reached", "cancelled": "Cancelled", "failed": "Failed",
}


def page(title: str, icon: str = "📍") -> None:
    st.set_page_config(page_title=f"{title} - LeadGen", page_icon=icon, layout="wide")


@st.cache_resource
def client() -> BackendClient:
    return BackendClient()


def api_get(path: str, **params):
    return client().get(path, **params)


def api_post(path: str, body: dict, timeout: float = 900):
    return client().post(path, body, timeout=timeout)


@st.cache_data(ttl=300, show_spinner=False)
def meta() -> dict:
    return api_get("/api/meta")


@st.cache_data(ttl=300, show_spinner=False)
def lookup(country: str, level: str) -> dict:
    return api_get("/api/areas/lookup", country=country, level=level)


def require_backend() -> dict:
    """Show a friendly message and stop the page if the backend is not running."""
    try:
        return api_get("/api/status")
    except BackendError as exc:
        st.error("The LeadGen backend is not running.")
        st.markdown(f"{exc}\n\nStart it with **start_backend.bat** (or `python -m backend`), then refresh this page.")
        st.stop()


def money(value) -> str:
    return f"${float(value or 0):,.2f}"


def country_picker(key: str, label: str = "Country") -> dict:
    countries = [c for c in meta()["countries"] if c["has_data"]]
    names = [c["name"] for c in countries]
    return countries[names.index(st.selectbox(label, names, key=key))]


def level_picker(country: dict, key: str) -> str:
    levels = [lv for lv in country["levels"] if lv["has_data"]]
    levels.sort(key=lambda lv: lv["key"] != country["default_level"])
    labels = [lv["label"] for lv in levels]
    return levels[labels.index(st.selectbox("Area type", labels, key=key))]["key"]


def business_type_picker(key: str):
    bt = meta()["business_types"]
    choice = st.radio("Business types", ["ALL", "A category", "Specific types"], horizontal=True, key=f"{key}_mode",
                      help=f"ALL = every type in config/business_types.yaml ({len(bt['all'])} types).")
    if choice == "A category":
        return st.selectbox("Category", list(bt["categories"]), key=f"{key}_cat")
    if choice == "Specific types":
        picked = st.multiselect("Types", bt["all"], key=f"{key}_types")
        return picked or None
    return "ALL"


def show_estimate(est: dict) -> None:
    q = est["quota"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Areas", f"{est['areas']:,}")
    c2.metric("Search tiles", f"{est['tiles']:,}")
    c3.metric("Google requests", f"{est['min_requests']:,}+", help=est.get("note"))
    c4.metric("Estimated cost (USD)", f"{money(est['min_cost_usd'])} - {money(est['likely_max_cost_usd'])}")
    if est.get("skipped"):
        st.info(f"{len(est['skipped']):,} area(s) already crawled with these settings will be skipped.")
    st.caption(f"Monthly quota: {q['used']:,} of {q['cap']:,} requests used ({q['remaining']:,} left).")
    if est["min_requests"] > q["remaining"]:
        st.warning("This needs more requests than are left this month. The crawl will stop cleanly at the cap - "
                   "run it again next month to continue.")


def job_monitor(session_key: str) -> None:
    """Live view of the job stored in st.session_state[session_key]; refreshes while it runs."""
    job_id = st.session_state.get(session_key)
    if not job_id:
        return
    try:
        job = api_get(f"/api/crawl/jobs/{job_id}", since=0)
    except BackendError as exc:
        st.warning(f"Could not load the crawl: {exc}")
        st.session_state.pop(session_key, None)
        return

    st.subheader(job["title"])
    status = job["status"]
    progress = job.get("progress") or {}
    summary = job["summary"]
    cols = st.columns([3, 1])
    cols[0].markdown(f"**Status:** {STATUS_LABELS.get(status, status)}")
    if status not in FINISHED and cols[1].button("Stop crawl", key=f"{session_key}_cancel", type="secondary"):
        api_post(f"/api/crawl/jobs/{job_id}/cancel", {})
        st.rerun()
    if progress:
        areas_total = max(progress.get("areas_total") or 1, 1)
        types_total = max(progress.get("types_total") or 1, 1)
        done = (progress.get("area_index", 1) - 1 + progress.get("types_done", 0) / types_total) / areas_total
        st.progress(min(done if status not in FINISHED else 1.0, 1.0),
                    text=f"Area {progress.get('area_index', 1)} of {areas_total}: {progress.get('area', '')} - "
                         f"{progress.get('business_type') or 'finishing'} "
                         f"({progress.get('types_done', 0)}/{progress.get('types_total', 0)} types)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Areas done", f"{summary['areas_done']} / {summary['areas_total']}")
    m2.metric("Businesses", f"{summary['leads_found']:,}", f"{summary['leads_new']:,} new")
    m3.metric("Google requests", f"{summary['requests']:,}")
    m4.metric("Cost so far (USD)", money(summary["cost_usd"]))
    if job.get("error"):
        st.error(job["error"])
    st.code("\n".join(job["logs"][-400:]) or "Starting...", language=None)

    if status in FINISHED:
        files = [Path(f) for f in summary.get("excel_files") or []]
        for f in files[-20:]:
            if f.exists():
                st.download_button(f"Download {f.name}", f.read_bytes(), file_name=f.name, key=f"dl_{session_key}_{f.name}")
        if files:
            st.caption(f"All files are in: {files[0].parent.parent.parent}")
        if st.button("Close", key=f"{session_key}_close"):
            st.session_state.pop(session_key, None)
            st.rerun()
    else:
        time.sleep(2)
        st.rerun()
