"""Platform-specific fit-screen-recorder availability and installation helpers."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from fit_common.core import debug, get_platform, resolve_path
from packaging.version import InvalidVersion, Version

from fit_bootstrap.constants import (
    FIT_SCREEN_RECODER_DEB_PATH,
    FIT_SCREEN_RECODER_PATH,
)
from fit_bootstrap.lang import load_translations
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

_LOG_CONTEXT = "fit_bootstrap.screen_recorder"
_LINUX_PACKAGE_NAME = "fit-screen-recorder"
_LINUX_BINARY_NAME = "fit-screen-recorder"
_REQUIRED_LINUX_PACKAGE_VERSION: str | None = None
_PKEXEC_CANCELLED_EXIT_CODE = 126

_SCREEN_RECODER_HELP_KEYS = {
    "macos": "BOOSTSTRAP_SCREEN_RECODER_PATH_NOT_FOUND_HELP_MACOS",
    "win": "BOOSTSTRAP_SCREEN_RECODER_PATH_NOT_FOUND_HELP_WINDOWS",
    "lin": "BOOSTSTRAP_SCREEN_RECODER_PATH_NOT_FOUND_HELP_LINUX",
}


class LinuxRecorderPackageStatus(str, Enum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    DPKG_QUERY_UNAVAILABLE = "dpkg_query_unavailable"
    QUERY_FAILED = "query_failed"
    VERSION_INCOMPATIBLE = "version_incompatible"
    BINARY_NOT_FOUND = "binary_not_found"
    UNSUPPORTED_SYSTEM = "unsupported_system"
    UNSUPPORTED_ARCHITECTURE = "unsupported_architecture"
    UNSUPPORTED_SESSION = "unsupported_session"


@dataclass(frozen=True)
class LinuxRecorderPackageInfo:
    status: LinuxRecorderPackageStatus
    version: str | None = None
    binary_path: Path | None = None


class LinuxRecorderInstallOutcome(str, Enum):
    INSTALLED = "installed"
    ALREADY_INSTALLED = "already_installed"
    DEB_NOT_FOUND = "deb_not_found"
    PKEXEC_UNAVAILABLE = "pkexec_unavailable"
    AUTHENTICATION_CANCELLED = "authentication_cancelled"
    INSTALL_FAILED = "install_failed"
    POST_INSTALL_VERIFICATION_FAILED = "post_install_verification_failed"
    UNSUPPORTED_SYSTEM = "unsupported_system"


@dataclass(frozen=True)
class LinuxRecorderInstallResult:
    outcome: LinuxRecorderInstallOutcome
    package_info: LinuxRecorderPackageInfo | None = None
    returncode: int | None = None


def ensure_screen_recoder_available() -> BootstrapResult | None:
    if get_platform() == "lin":
        return _ensure_linux_screen_recorder_available()

    recorder_path = _env_path()
    if recorder_path and recorder_path.exists():
        return None

    recorder_path = _bundle_screen_recorder_path()
    if recorder_path:
        _set_env(recorder_path)
        return None

    debug("❌ fit-screen-recoder bundle not found", context=_LOG_CONTEXT)
    __translations = load_translations()
    base_message = __translations.get(
        "BOOSTSTRAP_SCREEN_RECODER_PATH_NOT_FOUND_MESSAGE",
        "",
    )
    platform_key = get_platform()
    help_key = _SCREEN_RECODER_HELP_KEYS.get(platform_key)
    help_text = __translations.get(help_key, "") if help_key is not None else ""
    if base_message and "{}" in base_message:
        dialog_message = base_message.format(help_text)
    else:
        dialog_message = base_message
        if help_text:
            dialog_message = f"{dialog_message}<br><br>{help_text}"
    return BootstrapResult(
        code=1,
        signal=BootstrapSignal.ERROR,
        message=dialog_message,
    )


def inspect_linux_screen_recorder_package() -> LinuxRecorderPackageInfo:
    """Inspect the Debian package without changing system state."""
    platform_issue = _linux_platform_issue()
    if platform_issue is not None:
        return LinuxRecorderPackageInfo(platform_issue)

    dpkg_query = shutil.which("dpkg-query")
    if dpkg_query is None:
        return LinuxRecorderPackageInfo(
            LinuxRecorderPackageStatus.DPKG_QUERY_UNAVAILABLE
        )

    try:
        proc = subprocess.run(
            [
                dpkg_query,
                "-W",
                "-f=${Status}\\n${Version}",
                _LINUX_PACKAGE_NAME,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        debug(f"⚠️ dpkg-query failed: {exc}", context=_LOG_CONTEXT)
        return LinuxRecorderPackageInfo(LinuxRecorderPackageStatus.QUERY_FAILED)

    lines = proc.stdout.strip().splitlines()
    status = lines[0].strip().lower() if lines else ""
    version = lines[1].strip() if len(lines) > 1 else None
    if proc.returncode != 0:
        if "no packages found matching" in proc.stderr.lower():
            return LinuxRecorderPackageInfo(
                LinuxRecorderPackageStatus.NOT_INSTALLED
            )
        return LinuxRecorderPackageInfo(LinuxRecorderPackageStatus.QUERY_FAILED)
    if status != "install ok installed":
        return LinuxRecorderPackageInfo(LinuxRecorderPackageStatus.NOT_INSTALLED)
    if not _version_is_compatible(version, _REQUIRED_LINUX_PACKAGE_VERSION):
        return LinuxRecorderPackageInfo(
            LinuxRecorderPackageStatus.VERSION_INCOMPATIBLE,
            version=version,
        )

    binary_path = _installed_linux_binary_path(dpkg_query)
    if binary_path is None:
        return LinuxRecorderPackageInfo(
            LinuxRecorderPackageStatus.BINARY_NOT_FOUND,
            version=version,
        )
    return LinuxRecorderPackageInfo(
        LinuxRecorderPackageStatus.INSTALLED,
        version=version,
        binary_path=binary_path,
    )


def locate_linux_screen_recorder_deb() -> Path | None:
    """Locate the installer artifact without installing it."""
    configured_path = os.environ.get(FIT_SCREEN_RECODER_DEB_PATH)
    if configured_path:
        candidate = Path(configured_path).expanduser()
        if candidate.is_file():
            return candidate.resolve()

    package_dir = (
        _bundle_base_path() / "fit_screen_recorder_binaries" / "linux_x86_64"
    )
    candidates = sorted(package_dir.glob("fit-screen-recorder*.deb"))
    return candidates[0].resolve() if candidates else None


def install_linux_screen_recorder_package(
    deb_path: str | Path | None = None,
) -> LinuxRecorderInstallResult:
    """Install after explicit caller confirmation, delegating auth to PolicyKit."""
    current = inspect_linux_screen_recorder_package()
    if current.status == LinuxRecorderPackageStatus.INSTALLED:
        _set_installed_linux_env(current)
        return LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.ALREADY_INSTALLED,
            package_info=current,
        )
    if current.status in {
        LinuxRecorderPackageStatus.UNSUPPORTED_SYSTEM,
        LinuxRecorderPackageStatus.UNSUPPORTED_ARCHITECTURE,
        LinuxRecorderPackageStatus.UNSUPPORTED_SESSION,
        LinuxRecorderPackageStatus.DPKG_QUERY_UNAVAILABLE,
    }:
        return LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.UNSUPPORTED_SYSTEM,
            package_info=current,
        )

    resolved_deb = (
        Path(deb_path).expanduser().resolve()
        if deb_path is not None
        else locate_linux_screen_recorder_deb()
    )
    if resolved_deb is None or not resolved_deb.is_file():
        return LinuxRecorderInstallResult(LinuxRecorderInstallOutcome.DEB_NOT_FOUND)

    pkexec = shutil.which("pkexec")
    apt = shutil.which("apt")
    if pkexec is None:
        return LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.PKEXEC_UNAVAILABLE
        )
    if apt is None:
        return LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.UNSUPPORTED_SYSTEM
        )

    try:
        proc = subprocess.run(
            [pkexec, apt, "install", "-y", str(resolved_deb)],
            check=False,
        )
    except OSError as exc:
        debug(f"❌ package installation failed: {exc}", context=_LOG_CONTEXT)
        return LinuxRecorderInstallResult(LinuxRecorderInstallOutcome.INSTALL_FAILED)

    if proc.returncode == _PKEXEC_CANCELLED_EXIT_CODE:
        return LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.AUTHENTICATION_CANCELLED,
            returncode=proc.returncode,
        )
    if proc.returncode != 0:
        return LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.INSTALL_FAILED,
            returncode=proc.returncode,
        )

    installed = inspect_linux_screen_recorder_package()
    if installed.status != LinuxRecorderPackageStatus.INSTALLED:
        return LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.POST_INSTALL_VERIFICATION_FAILED,
            package_info=installed,
            returncode=proc.returncode,
        )
    _set_installed_linux_env(installed)
    return LinuxRecorderInstallResult(
        LinuxRecorderInstallOutcome.INSTALLED,
        package_info=installed,
        returncode=proc.returncode,
    )


def _ensure_linux_screen_recorder_available() -> BootstrapResult | None:
    package_info = inspect_linux_screen_recorder_package()
    if package_info.status == LinuxRecorderPackageStatus.INSTALLED:
        _set_installed_linux_env(package_info)
        return None

    translations = load_translations()
    message_key = {
        LinuxRecorderPackageStatus.NOT_INSTALLED: "BOOSTSTRAP_LINUX_SCREEN_RECORDER_NOT_INSTALLED_MESSAGE",
        LinuxRecorderPackageStatus.DPKG_QUERY_UNAVAILABLE: "BOOSTSTRAP_LINUX_DPKG_QUERY_NOT_FOUND_MESSAGE",
        LinuxRecorderPackageStatus.QUERY_FAILED: "BOOSTSTRAP_LINUX_SCREEN_RECORDER_QUERY_FAILED_MESSAGE",
        LinuxRecorderPackageStatus.VERSION_INCOMPATIBLE: "BOOSTSTRAP_LINUX_SCREEN_RECORDER_VERSION_MESSAGE",
        LinuxRecorderPackageStatus.BINARY_NOT_FOUND: "BOOSTSTRAP_LINUX_SCREEN_RECORDER_BINARY_MESSAGE",
        LinuxRecorderPackageStatus.UNSUPPORTED_SYSTEM: "BOOSTSTRAP_LINUX_SCREEN_RECORDER_UNSUPPORTED_MESSAGE",
        LinuxRecorderPackageStatus.UNSUPPORTED_ARCHITECTURE: "BOOSTSTRAP_LINUX_SCREEN_RECORDER_UNSUPPORTED_MESSAGE",
        LinuxRecorderPackageStatus.UNSUPPORTED_SESSION: "BOOSTSTRAP_LINUX_SCREEN_RECORDER_UNSUPPORTED_MESSAGE",
    }[package_info.status]
    return BootstrapResult(
        code=1,
        signal=BootstrapSignal.ERROR,
        message=translations.get(message_key, ""),
    )


def _linux_platform_issue() -> LinuxRecorderPackageStatus | None:
    try:
        os_release = platform.freedesktop_os_release()
    except OSError:
        os_release = {}
    distro_family = {
        os_release.get("ID", "").lower(),
        *os_release.get("ID_LIKE", "").lower().split(),
    }
    if "debian" not in distro_family:
        return LinuxRecorderPackageStatus.UNSUPPORTED_SYSTEM
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        return LinuxRecorderPackageStatus.UNSUPPORTED_ARCHITECTURE
    if not os.environ.get("DISPLAY"):
        return LinuxRecorderPackageStatus.UNSUPPORTED_SESSION
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return LinuxRecorderPackageStatus.UNSUPPORTED_SESSION
    return None


def _installed_linux_binary_path(dpkg_query: str) -> Path | None:
    standard_path = Path("/usr/bin") / _LINUX_BINARY_NAME
    if standard_path.is_file():
        return standard_path
    try:
        proc = subprocess.run(
            [dpkg_query, "-L", _LINUX_PACKAGE_NAME],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        candidate = Path(line.strip())
        if candidate.name == _LINUX_BINARY_NAME and candidate.is_file():
            return candidate
    return None


def _version_is_compatible(installed: str | None, required: str | None) -> bool:
    if required is None:
        return True
    if not installed:
        return False
    try:
        installed_version = installed.split("-", 1)[0]
        return Version(installed_version) >= Version(required)
    except InvalidVersion:
        return False


def _set_installed_linux_env(package_info: LinuxRecorderPackageInfo) -> None:
    if package_info.binary_path is None:
        raise ValueError("installed package info requires a binary path")
    _set_env(package_info.binary_path)


def _env_path() -> Path | None:
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


def _bundle_screen_recorder_path() -> Path | None:
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
