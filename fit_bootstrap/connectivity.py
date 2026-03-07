"""Internet connectivity checks for bootstrap."""

from __future__ import annotations

import socket

from fit_common.core import debug

from fit_bootstrap.lang import load_translations
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

_LOG_CONTEXT = "fit_bootstrap.connectivity"
_CONNECTIVITY_ENDPOINTS: tuple[tuple[str, int], ...] = (
    ("1.1.1.1", 53),
    ("8.8.8.8", 53),
)


def ensure_connectivity_available(timeout: float = 2.0) -> BootstrapResult | None:
    if _has_connectivity(timeout=timeout):
        return None

    debug("❌ internet connectivity check failed", context=_LOG_CONTEXT)
    __translations = load_translations()
    return BootstrapResult(
        code=1,
        signal=BootstrapSignal.ERROR,
        message=__translations.get("BOOSTSTRAP_ERROR_CONNECTION_MESSAGE", ""),
    )


def _has_connectivity(timeout: float = 2.0) -> bool:
    for host, port in _CONNECTIVITY_ENDPOINTS:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False
