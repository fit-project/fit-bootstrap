from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

from fit_common.core import debug, get_platform


def ensure_root_or_relaunch(
    argv: Sequence[str],
    *,
    prefer_osascript: bool = False,
    env_overrides: Mapping[str, str] | None = None,
) -> int:
    if _is_elevated():
        return 0

    platform = get_platform()
    if platform == "macos":
        return _relaunch_macos(
            argv, prefer_osascript=prefer_osascript, env_overrides=env_overrides
        )
    if platform == "lin":
        return _relaunch_linux(argv, env_overrides=env_overrides)
    if platform == "win":
        return _relaunch_windows(argv)

    debug(f"❌ Unsupported platform for elevation: {platform}")
    return 1


def _is_elevated() -> bool:
    platform = get_platform()
    if platform in {"macos", "lin"}:
        return os.geteuid() == 0
    if platform == "win":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return False


def _build_command(
    argv: Sequence[str], env_overrides: Mapping[str, str] | None = None
) -> str:
    parts: list[str] = []
    if env_overrides:
        parts.append("env")
        for key, value in env_overrides.items():
            parts.append(f"{key}={value}")
    parts += [sys.executable, *argv]
    return " ".join(shlex.quote(str(part)) for part in parts)


def _relaunch_macos(
    argv: Sequence[str],
    prefer_osascript: bool,
    env_overrides: Mapping[str, str] | None = None,
) -> int:
    if prefer_osascript:
        cmd = _build_command(argv, env_overrides=env_overrides)
        cmd_escaped = cmd.replace('"', '\\"')
        osa = f'do shell script "{cmd_escaped}" with administrator privileges'
        return subprocess.call(["osascript", "-e", osa])

    # Prefer SUDO_ASKPASS for non-interactive elevation to avoid osascript issues.
    askpass = Path(__file__).parent / "macos" / "askpass.sh"
    if askpass.exists():
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = str(askpass)
        env["DISPLAY"] = env.get("DISPLAY", ":0")
        if env_overrides:
            env.update(env_overrides)
        return subprocess.call(
            ["sudo", "-A", sys.executable, *argv],
            env=env,
        )

    if sys.stdin.isatty() and sys.stdout.isatty():
        return subprocess.call(["sudo", sys.executable, *argv])

    cmd = _build_command(argv, env_overrides=env_overrides)
    cmd_escaped = cmd.replace('"', '\\"')
    osa = f'do shell script "{cmd_escaped}" with administrator privileges'
    return subprocess.call(["osascript", "-e", osa])


def _relaunch_linux(
    argv: Sequence[str], env_overrides: Mapping[str, str] | None = None
) -> int:
    cmd = _build_command(argv, env_overrides=env_overrides)
    return subprocess.call(["sudo", "sh", "-c", cmd])


def _relaunch_windows(argv: Sequence[str]) -> int:
    try:
        import ctypes

        params = " ".join(shlex.quote(str(arg)) for arg in argv)
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1,
        )
        return 0 if result > 32 else 1
    except Exception as exc:
        debug(f"❌ Unable to elevate on Windows: {exc}")
        return 1
