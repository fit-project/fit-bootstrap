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
    env_overrides: Mapping[str, str] | None = None,
) -> int:
    if _is_elevated():
        return 0

    platform = get_platform()
    if platform == "macos":
        return _relaunch_macos(argv, env_overrides=env_overrides)
    if platform == "lin":
        return _relaunch_linux(argv, env_overrides=env_overrides)
    if platform == "win":
        return _relaunch_windows(argv)

    debug(
        f"❌ Unsupported platform for elevation: {platform}",
        context="fit_bootstrap.privilege",
    )
    return 1


def _is_elevated() -> bool:
    platform = get_platform()
    if platform in {"macos", "lin"}:
        return os.geteuid() == 0
    if platform == "win":
        try:
            import ctypes

            windll = getattr(ctypes, "windll", None)
            if windll is None:
                return False
            return bool(windll.shell32.IsUserAnAdmin())
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
    env_overrides: Mapping[str, str] | None = None,
) -> int:
    def _sudo_argv() -> list[str]:
        cmd: list[str] = ["sudo", "-A"]
        if env_overrides:
            cmd.append("env")
            for key, value in env_overrides.items():
                cmd.append(f"{key}={value}")
        cmd += [sys.executable, *argv]
        return cmd

    # Prefer SUDO_ASKPASS for non-interactive elevation.
    askpass = Path(__file__).parent / "macos" / "askpass.sh"
    if askpass.exists():
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = str(askpass)
        env["FIT_ASKPASS_FORM_TYPE_ARGUMENT"] = "--launch-gui"
        env["FIT_ASKPASS_PYTHON"] = sys.executable
        if os.environ.get("FIT_BOOTSTRAP_DEBUG") == "1":
            env["FIT_ASKPASS_DEBUG"] = "1"
            if "FIT_ASKPASS_LOG" in os.environ:
                env["FIT_ASKPASS_LOG"] = os.environ["FIT_ASKPASS_LOG"]
        env["DISPLAY"] = env.get("DISPLAY", ":0")
        if env_overrides:
            env.update(env_overrides)

        debug("sys.executable: " + sys.executable, context="fit_bootstrap.privilege")
        debug(
            "argv: " + " ".join(shlex.quote(str(arg)) for arg in argv),
            context="fit_bootstrap.privilege",
        )

        rc = subprocess.call(_sudo_argv(), env=env)
        if rc != 0:
            debug(
                f"sudo failed, exit code: {rc}",
                context="fit_bootstrap.privilege",
            )
        return rc

    if sys.stdin.isatty() and sys.stdout.isatty():
        if env_overrides:
            return subprocess.call(_sudo_argv())
        return subprocess.call(["sudo", sys.executable, *argv])
    debug(
        "❌ No TTY available for sudo; osascript elevation disabled",
        context="fit_bootstrap.privilege",
    )
    return 1


def _relaunch_linux(
    argv: Sequence[str], env_overrides: Mapping[str, str] | None = None
) -> int:
    cmd = _build_command(argv, env_overrides=env_overrides)
    return subprocess.call(["sudo", "sh", "-c", cmd])


def _relaunch_windows(argv: Sequence[str]) -> int:
    try:
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is None:
            return 1
        params = " ".join(shlex.quote(str(arg)) for arg in argv)
        result = windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1,
        )
        return 0 if result > 32 else 1
    except Exception as exc:
        debug(
            f"❌ Unable to elevate on Windows: {exc}",
            context="fit_bootstrap.privilege",
        )
        return 1
