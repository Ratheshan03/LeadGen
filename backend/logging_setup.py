"""Console + daily log files in logs/ (kept for 30 days)."""
from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler

from backend.config import settings

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = TimedRotatingFileHandler(settings.LOG_DIR / "leadgen.log", when="midnight", backupCount=30,
                                            encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root = logging.getLogger("leadgen")
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console)
    root.propagate = False
    _configured = True
