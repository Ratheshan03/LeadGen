"""
LeadGen - Full Crawl
====================

Crawl EVERY area of a country (optionally only some states/regions), one area
at a time. This is a big job: it can take days and cost thousands of dollars in
Google requests, so it always shows the estimate first and asks you to type
START.

It is resumable: areas that finish are recorded, and running the same command
again skips them. When the monthly request cap (API_REQUEST_CAP in .env) is
reached it stops cleanly - just run it again next month.

The backend must be running first (start_backend.bat or `python -m backend`).

Guided mode:
    python full_crawl.py

Direct mode:
    python full_crawl.py --country AU --estimate                     (cost estimate only)
    python full_crawl.py --country AU --states "Tasmania,Northern Territory"
    python full_crawl.py --country NZ --types "Food and Drink"
    python full_crawl.py --country AU --level sa2 --states Tasmania
"""
from __future__ import annotations

import argparse
import sys

from cli.api_client import BackendClient, BackendError
from cli.terminal import (
    ask, choose, confirm, follow_job, init_console, pick_business_types, print_estimate, print_job_result, rule,
)
from custom_crawl import header, pick_country, pick_level


def run(client: BackendClient, body: dict, estimate_only: bool, assume_yes: bool) -> None:
    rule("Full crawl plan")
    print("  Working out tiles for every area - this can take up to a minute...")
    est = client.post("/api/crawl/estimate", body, timeout=900)
    print(f"  {est['title']}")
    print_estimate(est)
    if est["areas"] == 0:
        print("\n  Every area is already done with these settings. Use --recrawl to crawl them again.")
        return
    if estimate_only:
        return
    print("\n  The crawl runs one area at a time and can be stopped at any time (Ctrl+C).")
    print("  Areas that finish are skipped next time, so you can continue later.")
    if not assume_yes and ask("\nType START to begin (anything else cancels)").strip().upper() != "START":
        print("Not started.")
        return
    job = client.post("/api/crawl/jobs", body, timeout=900)
    rule(f"Crawling (job {job['id']})  -  press Ctrl+C to stop or detach")
    print_job_result(follow_job(client, job["id"]))


TITLE = "LeadGen - Full Crawl"


def interactive(client: BackendClient) -> None:
    header(client, TITLE)
    meta = client.get("/api/meta")
    country = pick_country(meta)
    level = pick_level(country)
    lookup = client.get("/api/areas/lookup", country=country["code"], level=level)
    states = list(lookup)
    body = {"mode": "full", "country": country["code"], "level": level}
    if choose(f"Which {country['state_label'].lower()}s?", [f"ALL of {country['name']}", "Choose some"]) == 1:
        print()
        for i, s in enumerate(states, 1):
            print(f"  {i:>3}) {s} ({len(lookup[s])} areas)")
        raw = ask("Numbers separated by commas (e.g. 1,4)")
        picked = [states[int(x) - 1] for x in raw.replace(" ", "").split(",") if x.isdigit() and 0 < int(x) <= len(states)]
        body["states"] = picked or None
    body["business_types"] = pick_business_types(meta)
    body["dense"] = confirm("Use dense-city mode for every area? (much more complete in cities, much more expensive)", False)
    body["skip_completed"] = not confirm("Re-crawl areas that were already crawled?", False)
    run(client, body, estimate_only=False, assume_yes=False)


def main() -> int:
    init_console()
    p = argparse.ArgumentParser(description="LeadGen full-country crawl. Run without options for guided mode.",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("Direct mode")[1])
    p.add_argument("--country", default="AU", help="AU (default) or NZ")
    p.add_argument("--level", help="area type: lga / sa2 / gccsa (AU) or ta / sa2 / region (NZ); default council level")
    p.add_argument("--states", help="comma-separated states/regions (default: all)")
    p.add_argument("--types", default="ALL", help='ALL (default), a category, or comma-separated types')
    p.add_argument("--dense", action="store_true", help="dense-city mode for every area")
    p.add_argument("--recrawl", action="store_true", help="also crawl areas already done with the same settings")
    p.add_argument("--estimate", action="store_true", help="only show the estimate")
    p.add_argument("--yes", action="store_true", help="do not ask to type START")
    args = p.parse_args()

    client = BackendClient()
    try:
        if len(sys.argv) == 1:
            interactive(client)
            return 0
        types = args.types if "," not in args.types else [t.strip() for t in args.types.split(",") if t.strip()]
        body = {"mode": "full", "country": args.country, "level": args.level, "business_types": types,
                "dense": args.dense, "skip_completed": not args.recrawl,
                "states": [s.strip() for s in args.states.split(",")] if args.states else None}
        header(client, TITLE)
        run(client, body, estimate_only=args.estimate, assume_yes=args.yes)
        return 0
    except BackendError as exc:
        print(f"\nProblem: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
