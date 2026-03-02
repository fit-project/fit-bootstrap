"""Operating system compatibility checks for bootstrap."""

from __future__ import annotations

import platform
import re

from fit_common.core import get_platform

from fit_bootstrap.context import AcquisitionContext
from fit_bootstrap.lang import load_translations
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

_MIN_MACOS_MAJOR = 15
_REQUIRED_MACOS_ARCH = "arm64"


def ensure_supported_os_configuration(
    context: AcquisitionContext,
) -> BootstrapResult | None:
    if get_platform() != "macos":
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


def _extract_macos_major(os_version: str) -> int | None:
    match = re.search(r"(\d+)", os_version)
    if not match:
        return None
    return int(match.group(1))
