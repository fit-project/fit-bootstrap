from __future__ import annotations

import os

from fit_common.core import debug, get_platform

from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


class MacBootstrap:
    def __init__(self):
        pass

    def __is_macos(self) -> bool:
        return get_platform() == "macos"

    def __result_from_code(
        self, code: int, message: str | None = None
    ) -> BootstrapResult:
        if code == 0:
            return BootstrapResult(code=0, signal=BootstrapSignal.OK)
        return BootstrapResult(code=code, signal=BootstrapSignal.ERROR, message=message)

    def run(self) -> BootstrapResult:
        if os.geteuid() != 0:
            return BootstrapResult(
                code=1,
                signal=BootstrapSignal.ADMIN_DENIED,
                message="Admin privileges required",
            )

        debug("SETUP PHASE: proxy handling moved to main")
        return self.__result_from_code(0)
