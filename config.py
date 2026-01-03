from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from storage import load_config


def resolve_base_url(arg_base_url: Optional[str], config_path: Path) -> str:
    if arg_base_url:
        return arg_base_url
    cfg = load_config(config_path)
    if "base_url" in cfg:
        return cfg["base_url"]
    env_base = os.environ.get("MADELIN_BASE_URL")
    if env_base:
        return env_base
    raise RuntimeError("Base URL not configured. Run `python3 main.py init --base-url <url>` first.")
