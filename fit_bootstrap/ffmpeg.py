"""FFmpeg helpers for the bootstrap flow."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from fit_common.core import debug, get_platform, resolve_path

from fit_bootstrap.constants import FIT_FFMPEG_PATH

_LOG_CONTEXT = "fit_bootstrap.ffmpeg"


def ensure_ffmpeg_available() -> Optional[Path]:
    ffmpeg_path = _env_path()
    if ffmpeg_path and ffmpeg_path.exists():
        return ffmpeg_path

    ffmpeg_path = _bundle_ffmpeg_path()
    if ffmpeg_path:
        _set_env(ffmpeg_path)
        return ffmpeg_path

    ffmpeg_path = _which_ffmpeg()
    if ffmpeg_path:
        _set_env(ffmpeg_path)
        debug(f"✅ ffmpeg available at {ffmpeg_path}", context=_LOG_CONTEXT)
        return ffmpeg_path

    debug("❌ ffmpeg is not installed and not bundled", context=_LOG_CONTEXT)
    return None


def get_ffmpeg_path() -> Optional[Path]:
    env_path = _env_path()
    if env_path and env_path.exists():
        return env_path
    return _which_ffmpeg()


def _env_path() -> Optional[Path]:
    value = os.environ.get(FIT_FFMPEG_PATH)
    if not value:
        return None
    return Path(value)


def _which_ffmpeg() -> Optional[Path]:
    binary = shutil.which("ffmpeg")
    return Path(binary) if binary else None


def _set_env(path: Path) -> None:
    os.environ[FIT_FFMPEG_PATH] = str(path)


def _bundle_ffmpeg_path() -> Optional[Path]:
    bin_name = "ffmpeg.exe" if get_platform() == "win" else "ffmpeg"
    platform_map = {
        "macos": "macos_arm64",
        "lin": "linux_x86_64",
        "win": "windows_x86_64",
    }
    suffix = platform_map.get(get_platform())
    if not suffix:
        return None
    candidate = Path(
        resolve_path(os.path.join("fit_bootstrap", "ffmpeg_binaries", suffix, bin_name))
    )
    if candidate.exists():
        if get_platform() == "macos":
            if not _ensure_quarantine_removed(candidate):
                debug(
                    f"⚠️ quarantine check failed for {candidate}, not using bundle",
                    context=_LOG_CONTEXT,
                )
                return None
        debug(f"✅ ffmpeg bundle found at {candidate}", context=_LOG_CONTEXT)
        return candidate
    debug(f"ℹ️ No bundled ffmpeg found at {candidate}", context=_LOG_CONTEXT)
    return None


def _ensure_quarantine_removed(path: Path) -> bool:
    xattr_bin = shutil.which("xattr")
    if not xattr_bin:
        debug("ℹ️ xattr not available; cannot inspect quarantine flags", context=_LOG_CONTEXT)
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
