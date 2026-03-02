"""Bundled fit-screen-recoder helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fit_common.core import debug, get_platform, resolve_path

from fit_bootstrap.constants import FIT_SCREEN_RECODER_PATH

_LOG_CONTEXT = "fit_bootstrap.screen_recorder"


def ensure_screen_recoder_available() -> Optional[Path]:
    recorder_path = _env_path()
    if recorder_path and recorder_path.exists():
        return recorder_path

    recorder_path = _bundle_screen_recorder_path()
    if recorder_path:
        _set_env(recorder_path)
        return recorder_path

    debug("❌ fit-screen-recoder bundle not found", context=_LOG_CONTEXT)
    return None


def _env_path() -> Optional[Path]:
    value = os.environ.get(FIT_SCREEN_RECODER_PATH)
    if not value:
        return None
    return Path(value)


def _set_env(path: Path) -> None:
    os.environ[FIT_SCREEN_RECODER_PATH] = str(path)


def _bundle_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(resolve_path("fit_bootstrap"))
    return Path(__file__).resolve().parent


def _bundle_screen_recorder_path() -> Optional[Path]:
    platform_map = {
        "macos": "macos_arm64",
        "lin": "linux_x86_64",
        "win": "windows_x86_64",
    }
    suffix = platform_map.get(get_platform())
    if not suffix:
        return None

    bin_name = (
        "fit-screen-recoder.exe" if get_platform() == "win" else "fit-screen-recoder"
    )
    candidate = _bundle_base_path() / "fit_screen_recorder_binaries" / suffix / bin_name
    if not candidate.exists():
        debug(
            f"ℹ️ No bundled fit-screen-recoder found at {candidate}",
            context=_LOG_CONTEXT,
        )
        return None

    if get_platform() == "macos":
        if not _ensure_quarantine_removed(candidate):
            debug(
                f"⚠️ quarantine check failed for {candidate}, not using bundle",
                context=_LOG_CONTEXT,
            )
            return None

    debug(f"✅ fit-screen-recoder bundle found at {candidate}", context=_LOG_CONTEXT)
    return candidate


def _ensure_quarantine_removed(path: Path) -> bool:
    xattr_bin = shutil.which("xattr")
    if not xattr_bin:
        debug(
            "ℹ️ xattr not available; cannot inspect quarantine flags",
            context=_LOG_CONTEXT,
        )
        return False

    try:
        proc = subprocess.run(
            [xattr_bin, "-p", "com.apple.quarantine", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        debug(f"⚠️ failed to query quarantine attribute: {exc}", context=_LOG_CONTEXT)
        return False

    if proc.returncode != 0:
        debug(
            f"ℹ️ quarantine attribute absent (rc={proc.returncode}); nothing to clear",
            context=_LOG_CONTEXT,
        )
        return True

    remove_proc = subprocess.run(
        [xattr_bin, "-d", "com.apple.quarantine", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if remove_proc.returncode != 0:
        debug(
            f"⚠️ unable to remove quarantine (rc={remove_proc.returncode}): {remove_proc.stderr.strip()}",
            context=_LOG_CONTEXT,
        )
        return False
    debug(f"✅ removed quarantine flag from {path}", context=_LOG_CONTEXT)
    return True
