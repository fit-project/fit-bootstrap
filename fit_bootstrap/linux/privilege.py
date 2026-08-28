from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from fit_common.core import is_bundled

from fit_bootstrap.constants import (
    FIT_LINUX_ASKPASS_BUNDLED,
    FIT_LINUX_ASKPASS_PYTHON,
    FIT_LINUX_SUDO_ASKPASS,
)


def configure_linux_askpass() -> str | None:
    """Expose the Linux askpass launcher for later privileged task execution."""
    if shutil.which("sudo") is None:
        return "sudo"

    askpass = Path(__file__).with_name("askpass.sh")
    if not askpass.is_file() or not os.access(askpass, os.X_OK):
        return "askpass"

    os.environ[FIT_LINUX_SUDO_ASKPASS] = str(askpass)
    os.environ[FIT_LINUX_ASKPASS_PYTHON] = sys.executable
    os.environ[FIT_LINUX_ASKPASS_BUNDLED] = "1" if is_bundled() else "0"
    return None
