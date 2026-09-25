"""
Background crawl jobs.

The backend runs one crawl at a time in a worker thread (so the monthly quota
and Google's rate limits are respected); further jobs wait in a queue. Each job
keeps a live log and progress that custom_crawl.py, full_crawl.py and the
dashboard poll.
"""
from __future__ import annotations

import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from backend.crawler.engine import CANCELLED, COMPLETED, FAILED, QUOTA_REACHED, Reporter, crawl_area, crawl_nearby
from backend.crawler.places import PlacesClient, PlacesError
from backend.crawler.planner import CrawlPlan
from backend.crawler.quota import QuotaManager
from backend.storage import get_store

log = logging.getLogger("leadgen.jobs")

QUEUED, RUNNING = "queued", "running"
FINISHED_STATES = (COMPLETED, QUOTA_REACHED, CANCELLED, FAILED)
MAX_LOG_LINES = 200_000


@dataclass
class Job:
    id: str
    title: str
    request: dict
    plan: CrawlPlan = field(repr=False)
    status: str = QUEUED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    started_at: str | None = None
    finished_at: str | None = None
    logs: list[str] = field(default_factory=list)
    progress: dict = field(default_factory=dict)
    results: list[dict] = field(default_factory=list)
    error: str | None = None
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def add_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        for line in str(message).splitlines() or [""]:
            self.logs.append(f"{stamp}  {line}")
        if len(self.logs) > MAX_LOG_LINES:
            del self.logs[: len(self.logs) - MAX_LOG_LINES]

    def summary(self) -> dict:
        total = lambda k: sum(r.get(k) or 0 for r in self.results)  # noqa: E731
        return {
            "areas_done": sum(1 for r in self.results if r["status"] == COMPLETED),
            "areas_total": len(self.plan.areas) or len(self.plan.cities),
            "areas_skipped": len(self.plan.skipped),
            "leads_found": total("leads_found"), "leads_new": total("leads_new"),
            "requests": total("requests"), "cost_usd": round(sum(r.get("cost_usd") or 0 for r in self.results), 2),
            "excel_files": [r["excel_file"] for r in self.results if r.get("excel_file")],
        }

    def to_dict(self, since: int = 0) -> dict:
        return {
            "id": self.id, "title": self.title, "status": self.status, "request": self.request,
            "created_at": self.created_at, "started_at": self.started_at, "finished_at": self.finished_at,
            "progress": self.progress, "error": self.error, "summary": self.summary(), "results": self.results,
            "log_total": len(self.logs), "logs": self.logs[max(0, since):],
        }


class _JobReporter(Reporter):
    def __init__(self, job: Job, area_index: int, areas_total: int, area_name: str):
        self.job, self.area_index, self.areas_total, self.area_name = job, area_index, areas_total, area_name

    def log(self, message: str, level: int = logging.INFO) -> None:
        log.log(level, "[job %s] %s", self.job.id, message)
        if level >= logging.INFO:
            prefix = "WARNING: " if level == logging.WARNING else "ERROR: " if level >= logging.ERROR else ""
            self.job.add_log(prefix + message)

    def progress(self, done: int, total: int, current: str = "") -> None:
        self.job.progress = {"area_index": self.area_index, "areas_total": self.areas_total, "area": self.area_name,
                             "types_done": done, "types_total": total, "business_type": current}

    def cancelled(self) -> bool:
        return self.job._cancel.is_set()


class JobManager:
    def __init__(self, quota: QuotaManager):
        self.quota = quota
        self._jobs: dict[str, Job] = {}
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._work, name="crawl-worker", daemon=True)
        self._worker.start()

    # -------------------------------------------------------------- public
    def submit(self, request: dict, plan: CrawlPlan) -> Job:
        job = Job(id=uuid.uuid4().hex[:10], title=plan.title, request=request, plan=plan)
        with self._lock:
            self._jobs[job.id] = job
        position = self._queue.qsize() + (1 if self.active() else 0)
        job.add_log(f"Job created: {plan.title}")
        if plan.skipped:
            job.add_log(f"Skipping {len(plan.skipped)} area(s) already crawled with these settings.")
        if position:
            job.add_log(f"Waiting for {position} earlier job(s) to finish...")
        self._queue.put(job.id)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def active(self) -> Job | None:
        return next((j for j in self._jobs.values() if j.status == RUNNING), None)

    def cancel(self, job_id: str) -> Job | None:
        job = self.get(job_id)
        if job and job.status in (QUEUED, RUNNING):
            job._cancel.set()
            job.add_log("Cancel requested - stopping after the current business type...")
            if job.status == QUEUED:
                job.status, job.finished_at = CANCELLED, datetime.now().isoformat(timespec="seconds")
        return job

    # -------------------------------------------------------------- worker
    def _work(self) -> None:
        while True:
            job = self.get(self._queue.get())
            if job is None or job.status != QUEUED:
                continue
            try:
                self._run(job)
            except Exception as exc:  # never let the worker die
                log.exception("Job %s crashed", job.id)
                job.status, job.error = FAILED, f"Unexpected error: {exc}"
                job.add_log(f"ERROR: {job.error}")
            finally:
                job.finished_at = datetime.now().isoformat(timespec="seconds")

    def _run(self, job: Job) -> None:
        job.status, job.started_at = RUNNING, datetime.now().isoformat(timespec="seconds")
        plan = job.plan
        try:
            client = PlacesClient(quota=self.quota)
        except PlacesError as exc:
            job.status, job.error = FAILED, str(exc)
            job.add_log(f"ERROR: {exc}")
            return
        store = get_store()
        items = plan.cities if plan.mode == "nearby" else plan.areas
        job.add_log(f"Monthly Google requests used so far: {self.quota.used:,} of {self.quota.max_requests:,}")
        status = COMPLETED
        for index, item in enumerate(items, 1):
            name = item["name"] if plan.mode == "nearby" else item.name
            reporter = _JobReporter(job, index, len(items), name)
            if reporter.cancelled():
                status = CANCELLED
                break
            if len(items) > 1:
                job.add_log("")
                job.add_log(f"=== Area {index}/{len(items)}: {name} ===")
            if plan.mode == "nearby":
                result = crawl_nearby(client=client, store=store, country=plan.country, city=item,
                                      business_types=plan.business_types, types_label=plan.types_label,
                                      radius_m=plan.radius_m, reporter=reporter, job_id=job.id)
            else:
                result = crawl_area(client=client, store=store, country=plan.country, area=item,
                                    business_types=plan.business_types, types_label=plan.types_label,
                                    dense=plan.dense, reporter=reporter, job_id=job.id, mode=plan.mode)
            job.results.append(result.to_dict())
            if result.status != COMPLETED:
                status = result.status
                if result.error:
                    job.error = result.error
                break
        job.status = status
        s = job.summary()
        job.add_log("")
        job.add_log(f"Job {status.replace('_', ' ')}: {s['areas_done']}/{s['areas_total']} area(s), "
                    f"{s['leads_found']:,} businesses ({s['leads_new']:,} new), {s['requests']:,} requests "
                    f"(~${s['cost_usd']:,.2f})")
        if status == QUOTA_REACHED:
            job.add_log("Run the same crawl again next month (or raise API_REQUEST_CAP) to continue where it stopped.")
