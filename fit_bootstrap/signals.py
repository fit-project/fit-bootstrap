from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class BootstrapSignal(str, Enum):
    OK = "ok"
    ADMIN_DENIED = "admin_denied"
    CERTIFICATE_NOT_INSTALLED = "certificate_not_installed"
    UNSUPPORTED_OS = "unsupported_os"
    FFMPEG_PATH_NOT_FOUND = "ffmpeg_path_not_found"
    FFMPEG_LIST_DEVICES_FAILED = "ffmpeg_list_devices_failed"
    FFMPEG_NO_SCREEN_CAPTURE_DEVICE_DETECTED = (
        "ffmpeg_no_screen_capture_device_detected"
    )
    ERROR = "error"


@dataclass(frozen=True)
class BootstrapResult:
    code: int
    signal: BootstrapSignal
    message: Optional[str] = None


SignalHandler = Callable[[BootstrapResult], None]
