"""Synth — synthetic data platform.

Loading `.env` here means every entry point gets it: the server, the test
scripts, and anything importing the package directly. A documented `.env` that
nothing actually reads is worse than none at all.
"""
from __future__ import annotations

import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def load_env(path: Path = _ENV_FILE) -> None:
    """Minimal .env reader. A real variable always wins over the file."""
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            # Never override something the environment already set -- a
            # container's injected config must beat a file baked into the image.
            if key and value and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


load_env()
