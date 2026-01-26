import atexit
import sys
from pathlib import Path
from typing import Optional

from fit_common.core import debug, get_platform, is_bundled

from fit_bootstrap.macos.bootstrap import MacBootstrap
from fit_bootstrap.mitmproxy_runner import MitmproxyRunner
from fit_bootstrap.privilege import ensure_root_or_relaunch
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal, SignalHandler

STAGE_ENV = "FIT_BOOTSTRAP_STAGE"
STAGE_GUI = "gui"


class Bootstrap:
    def _dispatch(
        self,
        on_signal: Optional[SignalHandler] = None,
        *,
        argv: list[str] | None = None,
        stage_env: str | None = None,
        stage_gui: str | None = None,
        debug_enabled: bool = False,
    ) -> BootstrapResult:
        if get_platform() == "macos":
            if argv is None or stage_env is None or stage_gui is None:
                result = BootstrapResult(
                    code=1,
                    signal=BootstrapSignal.ERROR,
                    message="Missing macOS bootstrap parameters",
                )
            else:
                cert_result = MacBootstrap().run(debug_enabled=debug_enabled)
                if cert_result.code != 0:
                    result = cert_result
                else:
                    debug("PRE-FLIGHT: starting mitmproxy")
                    mitm_runner = MitmproxyRunner()
                    mitm_process = mitm_runner.start()
                    if not mitm_process:
                        result = BootstrapResult(
                            code=1,
                            signal=BootstrapSignal.ERROR,
                            message="mitmproxy_start_failed",
                        )
                    else:
                        atexit.register(mitm_runner.stop, mitm_process)
                        if is_bundled():
                            relaunch_argv = list(argv[1:])
                        else:
                            relaunch_argv = list(argv)
                            if relaunch_argv:
                                relaunch_argv[0] = str(Path(relaunch_argv[0]).resolve())
                        relaunch_code = ensure_root_or_relaunch(
                            relaunch_argv,
                            prefer_osascript=True,
                            env_overrides={stage_env: stage_gui},
                        )
                        if relaunch_code != 0:
                            debug("❌ Elevation failed")
                            mitm_runner.stop(mitm_process)
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

    def stop_mitmproxy(self) -> bool:
        runner = MitmproxyRunner()
        return runner.stop_by_pid()

    def start_mitmproxy(self) -> bool:
        runner = MitmproxyRunner()
        proc = runner.start()
        return proc is not None
