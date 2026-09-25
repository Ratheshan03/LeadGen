"""Terminal helpers shared by custom_crawl.py and full_crawl.py."""
from __future__ import annotations

import os
import sys
import time

from cli.api_client import BackendClient, BackendError

FINISHED = ("completed", "quota_reached", "cancelled", "failed")


def init_console() -> None:
    """Never crash on characters the console can't show (e.g. Māori place names)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    if os.name == "nt":
        os.system("")  # enables ANSI handling in older Windows consoles


def rule(title: str = "") -> None:
    print(f"\n==== {title} " + "=" * max(4, 70 - len(title)) if title else "=" * 76)


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        value = ""
    return value or (default or "")


def confirm(prompt: str, default: bool = False) -> bool:
    answer = ask(f"{prompt} (y/n)", "y" if default else "n").lower()
    return answer in ("y", "yes")


def choose(prompt: str, options: list[str], default: int = 1, columns: int = 1) -> int:
    """Numbered menu. Returns the 0-based index."""
    print(f"\n{prompt}")
    width = max(len(o) for o in options) + 6 if options else 10
    per_row = max(1, columns)
    for i in range(0, len(options), per_row):
        print("".join(f"  {j + 1:>3}) {options[j]:<{width}}" for j in range(i, min(i + per_row, len(options)))))
    while True:
        raw = ask("Enter a number", str(default))
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print(f"  Please enter a number from 1 to {len(options)}.")


def pick_name(prompt: str, names: list[str], noun: str = "area") -> str:
    """Pick from a long list: type part of a name, then choose from the matches."""
    while True:
        text = ask(f"{prompt} (type part of the name, or ? to list all)").strip()
        if not text:
            continue
        if text == "?":
            matches = names
        else:
            exact = [n for n in names if n.lower() == text.lower()]
            if exact:
                return exact[0]
            matches = [n for n in names if text.lower() in n.lower()]
        if not matches:
            print(f"  No {noun} matches '{text}'. Try fewer letters, or ? to list all.")
            continue
        if len(matches) == 1:
            print(f"  -> {matches[0]}")
            return matches[0]
        return matches[choose(f"{len(matches)} matching {noun}s:", matches, columns=3 if len(matches) > 20 else 1)]


def pick_business_types(meta: dict) -> str | list[str]:
    cats = list(meta["business_types"]["categories"])
    total = len(meta["business_types"]["all"])
    options = [f"ALL business types ({total})"] + [f"Category: {c}" for c in cats] + ["Enter specific types"]
    i = choose("Which business types?", options)
    if i == 0:
        return "ALL"
    if i <= len(cats):
        return cats[i - 1]
    raw = ask("Type names separated by commas (e.g. plumber, electrician, cafe)")
    return [t.strip() for t in raw.split(",") if t.strip()] or "ALL"


def money(v) -> str:
    return f"${float(v):,.2f}"


def print_estimate(est: dict) -> None:
    q = est["quota"]
    print()
    print(f"  Areas to crawl     : {est['areas']:,}" + (f"   (skipping {len(est['skipped']):,} already done)" if est.get("skipped") else ""))
    print(f"  Search tiles       : {est['tiles']:,}")
    print(f"  Business types     : {est['business_types']:,}")
    print(f"  Google requests    : at least {est['min_requests']:,}  (busy areas up to ~{est['likely_max_requests']:,})")
    print(f"  Estimated cost     : {money(est['min_cost_usd'])} - {money(est['likely_max_cost_usd'])} USD")
    print(f"  Monthly quota      : {q['used']:,} used of {q['cap']:,}  ({q['remaining']:,} left this month)")
    if est["min_requests"] > q["remaining"]:
        print("  NOTE: this is more than your remaining quota. The crawl will stop cleanly at the cap;")
        print("        run the same crawl again next month to continue where it stopped.")


def follow_job(client: BackendClient, job_id: str) -> dict:
    """Print the job's log live until it finishes. Ctrl+C offers to cancel or detach."""
    seen, job = 0, {}
    print()
    while True:
        try:
            job = client.get(f"/api/crawl/jobs/{job_id}", since=seen)
            for line in job["logs"]:
                print(line)
            seen = job["log_total"]
            if job["status"] in FINISHED:
                return job
            time.sleep(1.5)
        except KeyboardInterrupt:
            print()
            if confirm("Stop this crawl? (n = leave it running in the backend and close this window)", False):
                client.post(f"/api/crawl/jobs/{job_id}/cancel")
                print("Cancelling after the current business type...")
            else:
                print(f"The crawl keeps running in the backend. Watch it again with:  python custom_crawl.py --attach {job_id}")
                return job
        except BackendError as exc:
            print(f"\n{exc}")
            return job


def print_job_result(job: dict) -> None:
    if not job:
        return
    s = job.get("summary", {})
    rule("Result")
    labels = {"completed": "Completed", "quota_reached": "Stopped - monthly request cap reached",
              "cancelled": "Cancelled", "failed": "Failed"}
    print(f"  Status          : {labels.get(job.get('status'), job.get('status'))}")
    if job.get("error"):
        print(f"  Problem         : {job['error']}")
    print(f"  Areas finished  : {s.get('areas_done', 0)} of {s.get('areas_total', 0)}")
    print(f"  Businesses      : {s.get('leads_found', 0):,}  ({s.get('leads_new', 0):,} new)")
    print(f"  Google requests : {s.get('requests', 0):,}  (~{money(s.get('cost_usd', 0))})")
    files = s.get("excel_files") or []
    if files:
        print("  Excel files     :")
        for f in files[-10:]:
            print(f"     {f}")
        if len(files) > 10:
            print(f"     ... and {len(files) - 10} more (see the output folder)")
    print("  Full log        : logs/leadgen.log")


def open_folder(path: str) -> None:
    try:
        if os.name == "nt":
            os.startfile(path)  # noqa: S606 - opens Explorer on the user's own output folder
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except OSError:
        pass
