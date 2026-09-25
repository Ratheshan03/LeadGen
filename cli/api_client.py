"""Small HTTP client for the LeadGen backend, used by the crawl tools."""
from __future__ import annotations

import requests

from backend.config.settings import BACKEND_API_URL


class BackendError(RuntimeError):
    pass


class BackendClient:
    def __init__(self, base_url: str = BACKEND_API_URL):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()

    def _call(self, method: str, path: str, timeout: float = 120, **kwargs):
        try:
            r = self.session.request(method, f"{self.base}{path}", timeout=timeout, **kwargs)
        except requests.ConnectionError:
            raise BackendError(
                f"Cannot reach the LeadGen backend at {self.base}.\n"
                "Start it first: double-click start_backend.bat (or run: python -m backend) and keep that window open."
            ) from None
        except requests.Timeout:
            raise BackendError(f"The backend at {self.base} did not answer in time.") from None
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except ValueError:
                detail = r.text[:300]
            raise BackendError(detail if isinstance(detail, str) else str(detail))
        return r

    def get(self, path: str, **params):
        return self._call("GET", path, params={k: v for k, v in params.items() if v is not None}).json()

    def post(self, path: str, body: dict | None = None, timeout: float = 600):
        return self._call("POST", path, json=body or {}, timeout=timeout).json()

    def fetch_file(self, path: str, **params) -> tuple[str, bytes]:
        """GET a file; returns (filename, content)."""
        r = self._call("GET", path, timeout=900, params={k: v for k, v in params.items() if v is not None})
        name = r.headers.get("content-disposition", "").split("filename=")[-1].strip('"') or "download.xlsx"
        return name, r.content

    def download(self, path: str, dest, **params) -> None:
        with open(dest, "wb") as f:
            f.write(self.fetch_file(path, **params)[1])
