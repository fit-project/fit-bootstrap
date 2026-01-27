import os
import sys
from pathlib import Path
from typing import Optional

from fit_common.core import debug, get_platform, is_bundled
from fit_common.core.paths import resolve_app_path, resolve_log_path

from fit_bootstrap.constants import (
    FIT_DEBUG_ENABLED,
    FIT_DNS,
    FIT_HOST_IP,
    FIT_LOG_APP_PATH,
    FIT_OS_TYPE,
    FIT_OS_VERSION,
    FIT_USER_APP_PATH,
    FIT_USERNAME,
)
from fit_bootstrap.context import AcquisitionContext
from fit_bootstrap.macos.bootstrap import MacBootstrap
from fit_bootstrap.privilege import ensure_root_or_relaunch
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal, SignalHandler


class Bootstrap:
    def __init__(
        self,
        debug_enabled: bool = False,
    ) -> None:
        os.environ[FIT_DEBUG_ENABLED] = "1" if debug_enabled else "0"
        os.environ[FIT_USER_APP_PATH] = resolve_app_path()
        os.environ[FIT_LOG_APP_PATH] = resolve_log_path()
        self.acquisition_context = AcquisitionContext.collect()
        os.environ[FIT_OS_TYPE] = self.acquisition_context.os_type
        os.environ[FIT_OS_VERSION] = self.acquisition_context.os_version
        os.environ[FIT_USERNAME] = self.acquisition_context.username
        os.environ[FIT_HOST_IP] = self.acquisition_context.host_ip
        os.environ[FIT_DNS] = ",".join(self.acquisition_context.dns_servers)

    def _dispatch(
        self,
        on_signal: Optional[SignalHandler] = None,
        *,
        argv: list[str] | None = None,
        stage_env: str | None = None,
        stage_gui: str | None = None,
    ) -> BootstrapResult:
        if get_platform() == "macos":
            if argv is None or stage_env is None or stage_gui is None:
                result = BootstrapResult(
                    code=1,
                    signal=BootstrapSignal.ERROR,
                    message="Missing macOS bootstrap parameters",
                )
            else:
                cert_result = MacBootstrap().run()
                if cert_result.code != 0:
                    result = cert_result
                else:
                    if is_bundled():
                        relaunch_argv = list(argv[1:])
                    else:
                        relaunch_argv = list(argv)
                        if relaunch_argv:
                            relaunch_argv[0] = str(Path(relaunch_argv[0]).resolve())
                    relaunch_code = ensure_root_or_relaunch(
                        relaunch_argv,
                        prefer_osascript=True,
                        env_overrides={
                            stage_env: stage_gui,
                            FIT_USER_APP_PATH: os.environ[FIT_USER_APP_PATH],
                        },
                    )
                    if relaunch_code != 0:
                        debug("❌ Elevation failed")
                    result = BootstrapResult(
                        code=relaunch_code,
                        signal=(
                            BootstrapSignal.OK
                            if relaunch_code == 0
                            else BootstrapSignal.ERROR
                        ),
                        message=None if relaunch_code == 0 else "Elevation failed",
                    )
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
