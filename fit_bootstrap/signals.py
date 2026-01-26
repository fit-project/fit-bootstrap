from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class BootstrapSignal(str, Enum):
    OK = "ok"
    ADMIN_DENIED = "admin_denied"
    UNSUPPORTED_OS = "unsupported_os"
    ERROR = "error"


@dataclass(frozen=True)
class BootstrapResult:
    code: int
    signal: BootstrapSignal
    message: Optional[str] = None


SignalHandler = Callable[[BootstrapResult], None]
