from __future__ import annotations

import os
from pathlib import Path

# Shared constants and default paths.
PREFIX = b"madelin-auth-v1"
DEFAULT_CONFIG_PATH = Path(os.environ.get("MADELIN_CONFIG_PATH", Path.home() / ".madelin" / "config.json"))
DEFAULT_KEY_PATH = Path(os.environ.get("MADELIN_KEY_PATH", Path.home() / ".madelin" / "keys.json"))
