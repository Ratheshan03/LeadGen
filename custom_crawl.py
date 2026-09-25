"""
LeadGen - Custom Crawl
======================

Crawl one area, or every area of a state/region one by one, and get an Excel
file + map per area in the output folder.

The backend must be running first (double-click start_backend.bat, or run
`python -m backend` in another window).

Guided mode (recommended) - just run it and answer the questions:
    python custom_crawl.py

Direct mode - everything on the command line:
    python custom_crawl.py --state "South Australia" --area Walkerville
    python custom_crawl.py --state "South Australia" --area Walkerville --types "cafe,bakery"
    python custom_crawl.py --state Queensland --area Brisbane --dense          (dense-city mode)
    python custom_crawl.py --state Tasmania --all-areas                        (every council, resumable)
    python custom_crawl.py --country NZ --state Canterbury --area "Christchurch City"
    python custom_crawl.py --nearby --state "South Australia" --city Adelaide  (Nearby Search)
    python custom_crawl.py --state Victoria --area Melbourne --estimate        (cost estimate only)

Other:
    python custom_crawl.py --search walker          find an area by name
    python custom_crawl.py --export --state "South Australia" --council Walkerville
    python custom_crawl.py --history                recent crawls
    python custom_crawl.py --attach JOB_ID          watch a running crawl again
"""
from __future__ import annotations

import argparse
import sys

from backend.config.settings import OUTPUT_DIR
from cli.api_client import BackendClient, BackendError
from cli.terminal import (
    ask, choose, confirm, follow_job, init_console, open_folder, pick_business_types, pick_name, print_estimate,
    print_job_result, rule,
)


# ---------------------------------------------------------------- helpers ---
def header(client: BackendClient, title: str = "LeadGen - Custom Crawl") -> dict:
    status = client.get("/api/status")
    q = status["quota"]
    rule(title)
    print(f"  Backend : {client.base}   Storage: {status['storage']}")
    print(f"  Leads   : {status['total_leads']:,} stored   Google requests this month: {q['used']:,} / {q['cap']:,}")
    if not status["google_keys_configured"]:
        print("  WARNING : no Google API key in .env (GOOGLE_API_KEYS) - crawls will fail.")
    if status.get("active_job"):
        print(f"  Running : {status['active_job']['title']}  (new crawls will wait for it)")
    return status


def pick_country(meta: dict, requested: str | None = None) -> dict:
    countries = [c for c in meta["countries"] if c["has_data"]]
    if requested:
        for c in meta["countries"]:
            if requested.lower() in (c["code"].lower(), c["name"].lower()):
                return c
        raise BackendError(f"Unknown country '{requested}'.")
    if len(countries) == 1:
        return countries[0]
    return countries[choose("Country:", [c["name"] for c in countries])]


def pick_level(country: dict, allow_all: bool = True) -> str:
    levels = [lv for lv in country["levels"] if lv["has_data"]]
    levels.sort(key=lambda lv: lv["key"] != country["default_level"])
    if len(levels) == 1 or not allow_all:
        return levels[0]["key"]
    return levels[choose("Area type:", [lv["label"] + (" (recommended)" if lv["key"] == country["default_level"] else "")
                                        for lv in levels])]["key"]


def pick_state(client: BackendClient, country: dict, level: str) -> tuple[str, dict]:
    lookup = client.get("/api/areas/lookup", country=country["code"], level=level)
    states = list(lookup)
    return states[choose(f"{country['state_label']}:", [f"{s} ({len(lookup[s])} areas)" for s in states])], lookup


def run_crawl(client: BackendClient, body: dict, assume_yes: bool, estimate_only: bool) -> None:
    rule("Plan")
    est = client.post("/api/crawl/estimate", body)
    print(f"  {est['title']}")
    print_estimate(est)
    if est["areas"] == 0:
        print("\n  Nothing to do - every selected area was already crawled with these settings.")
        print("  Use --recrawl (or answer 'yes' to crawl again) to repeat them.")
        return
    if estimate_only:
        return
    if not assume_yes and not confirm("\nStart this crawl?", False):
        print("Not started.")
        return
    job = client.post("/api/crawl/jobs", body)
    rule(f"Crawling (job {job['id']})  -  press Ctrl+C to stop or detach")
    job = follow_job(client, job["id"])
    print_job_result(job)
    files = (job.get("summary") or {}).get("excel_files") or []
    if files and not assume_yes and confirm("\nOpen the output folder?", True):
        open_folder(str(OUTPUT_DIR))


# ------------------------------------------------------------ interactive ---
def interactive(client: BackendClient) -> None:
    meta = client.get("/api/meta")
    while True:
        header(client)
        action = choose("What would you like to do?", [
            "Crawl one area (council / suburb area)",
            "Crawl every area in a state or region, one by one (resumable)",
            "Nearby Search around a city centre",
            "Export leads from the database to Excel",
            "Show recent crawls",
            "Exit",
        ])
        if action == 5:
            return
        try:
            if action in (0, 1):
                country = pick_country(meta)
                level = pick_level(country)
                state, lookup = pick_state(client, country, level)
                body = {"country": country["code"], "level": level, "state": state}
                if action == 0:
                    body.update(mode="area", area=pick_name("Area name", lookup[state]))
                else:
                    body.update(mode="state")
                    body["skip_completed"] = not confirm("Re-crawl areas that were already crawled?", False)
                body["business_types"] = pick_business_types(meta)
                body["dense"] = confirm("Use dense-city mode? (splits big cities into neighbourhoods - "
                                        "far more complete, costs more)", False)
                run_crawl(client, body, assume_yes=False, estimate_only=False)
            elif action == 2:
                country = pick_country(meta)
                cities = client.get("/api/cities", country=country["code"])
                states = sorted({c["state"] for c in cities})
                state = states[choose(f"{country['state_label']}:", states)]
                names = [c["name"] for c in cities if c["state"] == state]
                chosen = choose("City:", ["ALL cities in this " + country["state_label"].lower()] + names)
                radius = float(ask("Search radius in km (max 50)", "5") or 5)
                body = {"mode": "nearby", "country": country["code"], "state": state,
                        "cities": None if chosen == 0 else [names[chosen - 1]],
                        "business_types": pick_business_types(meta), "radius_m": int(radius * 1000)}
                run_crawl(client, body, assume_yes=False, estimate_only=False)
            elif action == 3:
                export_interactive(client, meta)
            elif action == 4:
                show_history(client)
        except BackendError as exc:
            print(f"\n  Problem: {exc}")
        ask("\nPress Enter to return to the menu")


def export_interactive(client: BackendClient, meta: dict) -> None:
    country = pick_country(meta)
    summary = client.get("/api/leads/summary", country=country["code"])
    states = [s for s in summary["by_state"] if s != "Unknown"]
    if not states:
        print("  No leads stored for this country yet.")
        return
    i = choose(f"{country['state_label']}:", ["ALL"] + [f"{s} ({summary['by_state'][s]:,} leads)" for s in states])
    state = None if i == 0 else states[i - 1]
    council = None
    if state:
        by_council = client.get("/api/leads/summary", country=country["code"], state=state)["by_council"]
        councils = [c for c in by_council if c != "Unknown"]
        j = choose("Council:", ["ALL"] + [f"{c} ({by_council[c]:,})" for c in councils])
        council = None if j == 0 else councils[j - 1]
    do_export(client, country["code"], state, council, None)


def do_export(client: BackendClient, country: str | None, state: str | None, council: str | None, btype: str | None) -> None:
    from backend.crawler.export import export_path
    label = "_".join(v for v in (country, state, council, btype) if v) or "all"
    dest = export_path(label)
    client.download("/api/leads/export", dest, country=country, state=state, council=council, business_type=btype)
    print(f"\n  Saved: {dest}")


def show_history(client: BackendClient, limit: int = 25) -> None:
    runs = client.get("/api/crawl/history", limit=limit)
    rule("Recent crawls")
    if not runs:
        print("  No crawls yet.")
    for r in runs:
        when = (r.get("started_at") or "")[:16].replace("T", " ")
        print(f"  {when}  {r.get('status', ''):<14} {r.get('area', '')}, {r.get('state', '')} "
              f"[{r.get('business_types', '')}{', dense' if r.get('dense') else ''}]  "
              f"{r.get('leads_found') or 0:,} leads, {r.get('requests') or 0:,} requests")


# ------------------------------------------------------------------- main ---
def main() -> int:
    init_console()
    p = argparse.ArgumentParser(description="LeadGen custom crawl. Run without options for guided mode.",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("Direct mode")[1])
    p.add_argument("--country", default="AU", help="AU (default) or NZ")
    p.add_argument("--level", help="area type: lga / sa2 / gccsa (AU) or ta / sa2 / region (NZ)")
    p.add_argument("--state", help="state (AU) or region (NZ)")
    p.add_argument("--area", help="area name, e.g. Walkerville")
    p.add_argument("--all-areas", action="store_true", help="crawl every area in --state, one by one")
    p.add_argument("--areas", help="comma-separated subset of areas in --state (with --all-areas)")
    p.add_argument("--recrawl", action="store_true", help="also crawl areas already done with the same settings")
    p.add_argument("--types", default="ALL", help='ALL (default), a category ("Food and Drink") or types ("cafe,bakery")')
    p.add_argument("--dense", action="store_true", help="dense-city mode: crawl big cities neighbourhood by neighbourhood")
    p.add_argument("--nearby", action="store_true", help="Nearby Search around city centres instead")
    p.add_argument("--city", help="comma-separated city names for --nearby (default: all in --state)")
    p.add_argument("--radius-km", type=float, default=5, help="Nearby Search radius in km (default 5)")
    p.add_argument("--estimate", action="store_true", help="only show the cost estimate, do not crawl")
    p.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    p.add_argument("--search", help="find areas whose name contains this text")
    p.add_argument("--export", action="store_true", help="export stored leads to Excel (use --state/--council/--type)")
    p.add_argument("--council", help="council filter for --export")
    p.add_argument("--type", help="business type filter for --export")
    p.add_argument("--history", action="store_true", help="show recent crawls")
    p.add_argument("--attach", metavar="JOB_ID", help="watch a crawl that is already running")
    args = p.parse_args()

    client = BackendClient()
    try:
        if len(sys.argv) == 1:
            interactive(client)
            return 0
        if args.attach:
            print_job_result(follow_job(client, args.attach))
            return 0
        if args.history:
            show_history(client, 50)
            return 0
        if args.search:
            for a in client.get("/api/areas/search", q=args.search, country=args.country, level=args.level):
                print(f"  {a['name']:<40} {a['state']:<30} {a['area_km2']:>12,.1f} km2")
            return 0
        if args.export:
            do_export(client, args.country, args.state, args.council, args.type)
            return 0

        types = args.types if "," not in args.types else [t.strip() for t in args.types.split(",") if t.strip()]
        body = {"country": args.country, "level": args.level, "state": args.state, "business_types": types,
                "dense": args.dense, "skip_completed": not args.recrawl}
        if args.nearby:
            body.update(mode="nearby", radius_m=int(args.radius_km * 1000),
                        cities=[c.strip() for c in args.city.split(",")] if args.city else None)
        elif args.all_areas:
            if not args.state:
                p.error("--all-areas needs --state")
            body.update(mode="state", areas=[a.strip() for a in args.areas.split(",")] if args.areas else None)
        else:
            if not args.area:
                p.error("give --area (or --all-areas / --nearby), or run without options for guided mode")
            body.update(mode="area", area=args.area)
        header(client)
        run_crawl(client, body, assume_yes=args.yes, estimate_only=args.estimate)
        return 0
    except BackendError as exc:
        print(f"\nProblem: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
