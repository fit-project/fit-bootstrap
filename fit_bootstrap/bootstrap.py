import sys
from typing import Optional

from fit_common.core import get_platform

from fit_bootstrap.macos.bootstrap import MacBootstrap
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal, SignalHandler


class Bootstrap:
    def _dispatch(self, on_signal: Optional[SignalHandler] = None) -> BootstrapResult:
        if get_platform() == "macos":
            result = MacBootstrap().run()
        elif get_platform() == "win":
            result = BootstrapResult(
                code=1,
                signal=BootstrapSignal.UNSUPPORTED_OS,
                message="Windows is not supported yet",
            )
        elif get_platform() == "lin":
            result = BootstrapResult(
                code=1,
                signal=BootstrapSignal.UNSUPPORTED_OS,
                message="Linux is not supported yet",
            )
        else:
            result = BootstrapResult(
                code=1,
                signal=BootstrapSignal.UNSUPPORTED_OS,
                message=f"Unsupported OS: {sys.platform}",
            )

        if on_signal is not None:
            on_signal(result)
        return result
