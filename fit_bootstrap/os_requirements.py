"""Operating system compatibility checks for bootstrap."""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import platform
import re
import shutil
from pathlib import Path

from fit_common.core import get_platform

from fit_bootstrap.context import AcquisitionContext
from fit_bootstrap.lang import load_translations
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

_MIN_MACOS_MAJOR = 15
_REQUIRED_MACOS_ARCH = "arm64"
_REQUIRED_LINUX_ARCH = "x86_64"
_OS_RELEASE_PATH = Path("/etc/os-release")


def ensure_supported_os_configuration(
    context: AcquisitionContext,
) -> BootstrapResult | None:
    current_platform = get_platform()
    if current_platform == "lin":
        return _ensure_supported_linux_configuration()
    if current_platform != "macos":
        return None

    __translations = load_translations()
    macos_major = _extract_macos_major(context.os_version)
    machine = platform.machine().lower()
    if (
        macos_major is None
        or macos_major < _MIN_MACOS_MAJOR
        or machine != _REQUIRED_MACOS_ARCH
    ):
        return BootstrapResult(
            code=1,
            signal=BootstrapSignal.ERROR,
            message=(
                __translations.get(
                    "BOOSTSTRAP_OS_REQUIREMENTS_NOT_MET_MESSAGE", ""
                ).format(_MIN_MACOS_MAJOR, _REQUIRED_MACOS_ARCH)
            ),
        )

    return None


def _ensure_supported_linux_configuration() -> BootstrapResult | None:
    failures: list[str] = []

    os_release = _read_os_release()
    distro_family = {
        os_release.get("ID", "").lower(),
        *os_release.get("ID_LIKE", "").lower().split(),
    }
    if "debian" not in distro_family or shutil.which("dpkg") is None:
        failures.append("a Debian-compatible system with dpkg")

    machine = platform.machine().lower()
    if machine not in {_REQUIRED_LINUX_ARCH, "amd64"}:
        failures.append("x86_64 architecture")

    if not os.environ.get("DISPLAY"):
        failures.append("an active X11 display")
    elif os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        failures.append("an X11 session (native Wayland is not supported)")
    elif not _can_connect_to_x11():
        failures.append("a reachable X11 display")

    if not _library_available("gtk-3", ("libgtk-3.so.0",)):
        failures.append("GTK 3")
    if not _library_available("webkit2gtk-4.1", ("libwebkit2gtk-4.1.so.0",)):
        failures.append("WebKitGTK 4.1")

    if not failures:
        return None

    translations = load_translations()
    requirements = ", ".join(failures)
    return BootstrapResult(
        code=1,
        signal=BootstrapSignal.ERROR,
        message=translations.get(
            "BOOSTSTRAP_LINUX_REQUIREMENTS_NOT_MET_MESSAGE", ""
        ).format(requirements),
    )


def _read_os_release(path: Path = _OS_RELEASE_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values


def _library_available(name: str, sonames: tuple[str, ...]) -> bool:
    candidates = (ctypes.util.find_library(name), *sonames)
    for candidate in candidates:
        if not candidate:
            continue
        try:
            ctypes.CDLL(candidate)
            return True
        except OSError:
            continue
    return False


def _can_connect_to_x11() -> bool:
    library_name = ctypes.util.find_library("X11") or "libX11.so.6"
    try:
        x11 = ctypes.CDLL(library_name)
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        display = x11.XOpenDisplay(None)
        if not display:
            return False
        x11.XCloseDisplay(display)
        return True
    except (AttributeError, OSError):
        return False


def _extract_macos_major(os_version: str) -> int | None:
    match = re.search(r"(\d+)", os_version)
    if not match:
        return None
    return int(match.group(1))
