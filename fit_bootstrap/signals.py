from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class BootstrapSignal(str, Enum):
    OK = "ok"
    ADMIN_DENIED = "admin_denied"
    CERTIFICATE_NOT_INSTALLED = "certificate_not_installed"
    UNSUPPORTED_OS = "unsupported_os"
    SCREEN_RECODER_PATH_NOT_FOUND = "screen_recoder_path_not_found"
    ERROR = "error"


@dataclass(frozen=True)
class BootstrapResult:
    code: int
    signal: BootstrapSignal
    message: Optional[str] = None


SignalHandler = Callable[[BootstrapResult], None]
