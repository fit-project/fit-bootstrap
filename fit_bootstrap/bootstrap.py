import os
import sys
from pathlib import Path
from typing import Optional

from fit_common.core import (
    debug,
    find_free_port,
    get_context,
    get_platform,
    get_system_lang,
    get_version,
    is_bundled,
)
from fit_common.core.paths import resolve_app_path, resolve_log_path

from fit_bootstrap.caller import CallerProfile
from fit_bootstrap.constants import (
    FIT_DEBUG_ENABLED,
    FIT_DNS,
    FIT_EXECUTION_ENV,
    FIT_HOST_IP,
    FIT_LOG_APP_PATH,
    FIT_MITM_PORT,
    FIT_OS_TYPE,
    FIT_OS_VERSION,
    FIT_PUBLIC_IP,
    FIT_SCREEN_RECODER_PATH,
    FIT_USER_APP_PATH,
    FIT_USER_SYSTEM_LANG,
    FIT_USERNAME,
    FIT_VERSION,
)
from fit_bootstrap.context import AcquisitionContext
from fit_bootstrap.lang import load_translations
from fit_bootstrap.macos.bootstrap import MacBootstrap
from fit_bootstrap.os_requirements import ensure_supported_os_configuration
from fit_bootstrap.privilege import ensure_root_or_relaunch
from fit_bootstrap.screen_recorder import ensure_screen_recoder_available
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal, SignalHandler


class Bootstrap:
    def __init__(
        self,
        debug_enabled: bool = False,
        caller: CallerProfile = CallerProfile.FIT,
    ) -> None:
        self.caller = caller
        os.environ[FIT_DEBUG_ENABLED] = "1" if debug_enabled else "0"
        os.environ[FIT_USER_APP_PATH] = resolve_app_path()
        os.environ[FIT_LOG_APP_PATH] = resolve_log_path()
        self.acquisition_context = AcquisitionContext.collect()
        os.environ[FIT_OS_TYPE] = self.acquisition_context.os_type
        os.environ[FIT_OS_VERSION] = self.acquisition_context.os_version
        os.environ[FIT_USERNAME] = self.acquisition_context.username
        os.environ[FIT_HOST_IP] = self.acquisition_context.host_ip
        os.environ[FIT_PUBLIC_IP] = self.acquisition_context.public_ip
        os.environ[FIT_DNS] = ",".join(self.acquisition_context.dns_servers)
        os.environ[FIT_USER_SYSTEM_LANG] = get_system_lang()
        os.environ[FIT_EXECUTION_ENV] = "LOCAL_PC"
        os.environ[FIT_VERSION] = get_version()

        self.__translations = load_translations()

        self._apply_caller_profile()

    def _apply_caller_profile(self) -> None:
        if self.caller in {CallerProfile.FIT, CallerProfile.FIT_WEB}:
            try:
                os.environ.setdefault(FIT_MITM_PORT, str(find_free_port()))
            except Exception as exc:
                debug(
                    f"❌ Unable to select free mitm port: {exc}",
                    context=get_context(self),
                )
                os.environ.setdefault(FIT_MITM_PORT, "8080")

    def _dispatch(
        self,
        on_signal: Optional[SignalHandler] = None,
        *,
        argv: list[str] | None = None,
        stage_env: str | None = None,
        stage_gui: str | None = None,
    ) -> BootstrapResult:
        result = self._run_common_checks(argv, stage_env, stage_gui)
        if result is None:
            platform = get_platform()
            if platform == "macos":
                result = self._dispatch_macos(argv, stage_env, stage_gui)
            elif platform == "win":
                result = BootstrapResult(
                    code=1,
                    signal=BootstrapSignal.UNSUPPORTED_OS,
                    message="Windows is not supported yet",
                )
            elif platform == "lin":
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

    def _run_common_checks(
        self,
        argv: list[str] | None,
        stage_env: str | None,
        stage_gui: str | None,
    ) -> BootstrapResult | None:
        if argv is None or stage_env is None or stage_gui is None:
            return BootstrapResult(
                code=1,
                signal=BootstrapSignal.ERROR,
                message=self.__translations.get(
                    "BOOSTSTRAP_MISSING_PARAMETERS_MESSAGE", ""
                ),
            )

        os_requirements_result = ensure_supported_os_configuration(
            self.acquisition_context
        )
        if os_requirements_result is not None:
            return os_requirements_result

        screen_recorder_result = ensure_screen_recoder_available()
        if screen_recorder_result is not None:
            return screen_recorder_result

        return None

    def _dispatch_macos(
        self,
        argv: list[str],
        stage_env: str,
        stage_gui: str,
    ) -> BootstrapResult:
        mac_bootstrap = MacBootstrap()
        if self.caller in {CallerProfile.FIT, CallerProfile.FIT_WEB}:
            cert_result = mac_bootstrap.install_certificate()
        else:
            cert_result = BootstrapResult(
                code=0, signal=BootstrapSignal.OK, message=None
            )

        if cert_result.code != 0:
            return cert_result

        permission_result = mac_bootstrap.ensure_permissions()
        if permission_result.code != 0:
            return permission_result

        if is_bundled():
            relaunch_argv = list(argv[1:])
        else:
            relaunch_argv = list(argv)
            if relaunch_argv:
                relaunch_argv[0] = str(Path(relaunch_argv[0]).resolve())

        relaunch_code = ensure_root_or_relaunch(
            relaunch_argv,
            env_overrides={
                stage_env: stage_gui,
                "PATH": os.environ.get("PATH", ""),
                FIT_DEBUG_ENABLED: os.environ.get(FIT_DEBUG_ENABLED, "0"),
                FIT_USER_APP_PATH: os.environ.get(FIT_USER_APP_PATH, ""),
                FIT_LOG_APP_PATH: os.environ.get(FIT_LOG_APP_PATH, ""),
                FIT_OS_TYPE: os.environ.get(FIT_OS_TYPE, ""),
                FIT_OS_VERSION: os.environ.get(FIT_OS_VERSION, ""),
                FIT_USERNAME: os.environ.get(FIT_USERNAME, ""),
                FIT_HOST_IP: os.environ.get(FIT_HOST_IP, ""),
                FIT_PUBLIC_IP: os.environ.get(FIT_PUBLIC_IP, ""),
                FIT_DNS: os.environ.get(FIT_DNS, ""),
                FIT_MITM_PORT: os.environ.get(FIT_MITM_PORT, ""),
                FIT_USER_SYSTEM_LANG: os.environ.get(FIT_USER_SYSTEM_LANG, ""),
                FIT_EXECUTION_ENV: os.environ.get(FIT_EXECUTION_ENV, ""),
                FIT_VERSION: os.environ.get(FIT_VERSION, ""),
                FIT_SCREEN_RECODER_PATH: os.environ.get(FIT_SCREEN_RECODER_PATH, ""),
            },
        )

        if relaunch_code != 0:
            debug("❌ Elevation failed", context=get_context(self))

        return BootstrapResult(
            code=relaunch_code,
            signal=(
                BootstrapSignal.OK
                if relaunch_code == 0
                else BootstrapSignal.ADMIN_DENIED
            ),
            message=None if relaunch_code == 0 else "Elevation failed",
        )
