from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
from pathlib import Path

from fit_common.core import debug, get_platform

from fit_bootstrap.macos.proxy import MacProxyManager, ProxyState
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


class MacBootstrap:
    def __init__(self):
        self._proxy_manager: MacProxyManager | None = None
        self._proxy_state: ProxyState | None = None
        self._proxy_restored = False

    def __is_bundled(self) -> bool:
        return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))

    def __is_macos(self) -> bool:
        return get_platform() == "macos"

    def __ensure_authorized_if_bundled(self) -> None:
        if not self.__is_bundled() or not self.__is_macos():
            return
        app_path = Path(sys.executable).resolve()
        app_bundle = app_path
        while app_bundle.name != "Contents" and app_bundle.parent != app_bundle:
            app_bundle = app_bundle.parent
        bundle_root = app_bundle.parent
        subprocess.run(
            ["xattr", "-dr", "com.apple.quarantine", str(bundle_root)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def __setup_phase(self) -> tuple[int, str | None]:
        debug("SETUP PHASE: starting tcpdump")

        debug("SETUP PHASE: configuring network proxy")
        proxy_service = MacProxyManager.detect_service()
        if not proxy_service:
            message = "No active network service found for proxy setup"
            debug(message)
            return 1, message

        proxy_manager = MacProxyManager(proxy_service)
        proxy_state = proxy_manager.snapshot()
        if proxy_state is None:
            message = "Unable to read current proxy settings"
            debug(message)
            return 1, message

        debug(f"SETUP PHASE: snapshot proxy state for {proxy_service}")
        self._proxy_manager = proxy_manager
        self._proxy_state = proxy_state
        self.__register_proxy_restore()
        proxy_manager.enable_capture_proxy("127.0.0.1", 8080)
        debug("SETUP PHASE: proxy set to 127.0.0.1:8080 with local bypass")

        return 0, None

    def __result_from_code(
        self, code: int, message: str | None = None
    ) -> BootstrapResult:
        if code == 0:
            return BootstrapResult(code=0, signal=BootstrapSignal.OK)
        return BootstrapResult(code=code, signal=BootstrapSignal.ERROR, message=message)

    def run(self) -> BootstrapResult:
        self.__ensure_authorized_if_bundled()

        if os.geteuid() != 0:
            return BootstrapResult(
                code=1,
                signal=BootstrapSignal.ADMIN_DENIED,
                message="Admin privileges required",
            )

        code, message = self.__setup_phase()
        return self.__result_from_code(code, message)

    def __restore_proxy(self) -> None:
        if self._proxy_restored or not self._proxy_manager or not self._proxy_state:
            return
        self._proxy_restored = True
        debug("RESTORE PHASE: restoring network proxy")
        self._proxy_manager.restore(self._proxy_state)

    def __register_proxy_restore(self) -> None:
        atexit.register(self.__restore_proxy)

        def _handle_signal(signum: int, _frame) -> None:
            self.__restore_proxy()
            raise SystemExit(128 + signum)

        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, _handle_signal)
