"""
End-to-end: a real backend server (fake Google API, temp storage) driven by
custom_crawl.py / full_crawl.py exactly as a user would run them.
"""
import socket
import sys
import threading
import time
from pathlib import Path

import openpyxl
import pytest
import uvicorn

import custom_crawl
import full_crawl
from backend import jobs as jobs_module
from backend.config import settings
from backend.crawler.places import PlacesClient
from backend.storage import reset_store
from backend.storage.sqlite_store import SQLiteLeadStore
from cli.api_client import BackendClient
from tests.fakes import FakeGoogle, make_place


@pytest.fixture(scope="module")
def backend(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cli")
    mp = pytest.MonkeyPatch()
    mp.setattr(settings, "OUTPUT_DIR", tmp / "output")
    mp.setattr(settings, "QUOTA_FILE", tmp / "quota.json")
    fake = FakeGoogle(places={
        "cafe": [make_place("w1", -34.8930, 138.6186, "Walkerville Cafe"),
                 make_place("h1", -42.8821, 147.3272, "Hobart Cafe")],
        "bakery": [make_place("w2", -34.8935, 138.6190, "Walkerville Bakery")],
    })
    mp.setattr(jobs_module, "PlacesClient", lambda quota: PlacesClient(keys=["k"], quota=quota, session=fake, page_delay=0))
    reset_store(SQLiteLeadStore(tmp / "leads.db"))

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    from backend.main import app
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    mp.setattr(custom_crawl, "BackendClient", lambda: BackendClient(url))
    mp.setattr(full_crawl, "BackendClient", lambda: BackendClient(url))
    yield tmp
    server.should_exit = True
    thread.join(5)
    reset_store(None)
    mp.undo()


def run(module, *args, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [f"{module.__name__}.py", *args])
    code = module.main()
    return code, capsys.readouterr().out


def test_custom_crawl_one_area(backend, monkeypatch, capsys):
    code, out = run(custom_crawl, "--state", "South Australia", "--area", "Walkerville", "--types", "cafe,bakery",
                    "--yes", monkeypatch=monkeypatch, capsys=capsys)
    assert code == 0, out
    assert "Completed" in out and "Businesses      : 2" in out
    assert "[1/2] cafe" in out and "[2/2] bakery" in out          # detailed per-type log lines, in the order given
    excel = next((backend / "output" / "Australia" / "South Australia" / "Walkerville").glob("*.xlsx"))
    rows = list(openpyxl.load_workbook(excel)["Leads"].iter_rows(values_only=True))
    assert len(rows) == 3  # header + 2 businesses


def test_state_crawl_resumes(backend, monkeypatch, capsys):
    args = ["--state", "Tasmania", "--all-areas", "--areas", "Hobart,Glenorchy", "--types", "cafe", "--yes"]
    code, out = run(custom_crawl, *args, monkeypatch=monkeypatch, capsys=capsys)
    assert code == 0 and "Areas finished  : 2 of 2" in out, out
    code, out = run(custom_crawl, *args, monkeypatch=monkeypatch, capsys=capsys)
    assert "Nothing to do" in out


def test_full_crawl_estimate_and_search_history_export(backend, monkeypatch, capsys):
    code, out = run(full_crawl, "--country", "AU", "--states", "Tasmania", "--types", "cafe", "--estimate",
                    monkeypatch=monkeypatch, capsys=capsys)
    assert code == 0 and "LeadGen - Full Crawl" in out and "skipping 2 already done" in out
    code, out = run(custom_crawl, "--search", "walker", monkeypatch=monkeypatch, capsys=capsys)
    assert "Walkerville" in out
    code, out = run(custom_crawl, "--history", monkeypatch=monkeypatch, capsys=capsys)
    assert "Walkerville, South Australia" in out and "Hobart, Tasmania" in out
    code, out = run(custom_crawl, "--export", "--state", "Tasmania", monkeypatch=monkeypatch, capsys=capsys)
    saved = Path(out.split("Saved:")[1].strip())
    assert code == 0 and saved.exists() and saved.suffix == ".xlsx"


def test_friendly_error_when_backend_is_down(monkeypatch, capsys):
    monkeypatch.setattr(custom_crawl, "BackendClient", lambda: BackendClient("http://127.0.0.1:9"))
    code, out = run(custom_crawl, "--history", monkeypatch=monkeypatch, capsys=capsys)
    assert code == 1 and "start_backend.bat" in out
