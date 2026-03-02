from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fit_common.core import debug, get_context

from fit_bootstrap.constants import FIT_SCREEN_RECODER_PATH
from fit_bootstrap.lang import load_translations
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


class PermissionChecker:
    def run(self) -> BootstrapResult:
        recorder_path = os.environ.get(FIT_SCREEN_RECODER_PATH, "")
        if not recorder_path:
            return BootstrapResult(
                code=1,
                signal=BootstrapSignal.ERROR,
                message="fit-screen-recoder path is not configured",
            )

        command = [str(Path(recorder_path)), "--check-permissions"]
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            debug(
                f"❌ failed to execute fit-screen-recoder: {exc}",
                context=get_context(self),
            )
            return BootstrapResult(
                code=1,
                signal=BootstrapSignal.ERROR,
                message=str(exc),
            )

        output = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
        debug(
            f"ℹ️ fit-screen-recoder --check-permissions rc={proc.returncode}",
            context=get_context(self),
        )
        if output:
            debug(output, context=get_context(self))

        if "screen_recording=denied" in output:
            translations = load_translations()
            return BootstrapResult(
                code=1,
                signal=BootstrapSignal.ERROR,
                message=translations.get(
                    "BOOSTSTRAP_MACOS_SCREEN_RECORDING_PERMISSIONS_DENIED_MESSAGE",
                    "",
                ),
            )

        return BootstrapResult(code=0, signal=BootstrapSignal.OK, message=None)
