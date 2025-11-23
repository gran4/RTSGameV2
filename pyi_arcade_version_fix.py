"""PyInstaller runtime hook to ensure arcade can read its version when frozen."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import arcade


def _ensure_arcade_version_file() -> None:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    version_path = Path(meipass) / "arcade" / "VERSION"
    version_text = getattr(arcade, "__version__", "0.0.0")
    try:
        if version_path.exists() and version_path.is_dir():
            # Remove stray directory so we can write a file.
            try:
                version_path.rmdir()
            except OSError:
                return
        version_path.parent.mkdir(parents=True, exist_ok=True)
        if not version_path.exists():
            version_path.write_text(str(version_text), encoding="utf-8")
    except Exception:
        # Silent failure: arcade will fall back to its own __version__ if present.
        pass


_ensure_arcade_version_file()
