import argparse
import atexit
import os
import sys

from fit_assets import resources  # noqa: F401
from fit_common.core import (
    DebugLevel,
    debug,
    get_platform,
    is_admin,
    is_bundled,
    resolve_path,
    set_debug_level,
)
from fit_common.gui.utils import show_dialog

from fit_bootstrap.app_lock import acquire_app_lock, release_app_lock
from fit_bootstrap.bootstrap import Bootstrap
from fit_bootstrap.caller import CallerProfile
from fit_bootstrap.constants import FIT_MITM_PORT, STAGE_ENV, STAGE_GUI
from fit_bootstrap.lang import load_translations
from fit_bootstrap.macos.proxy import MacProxyManager, ProxyState
from fit_bootstrap.mitmproxy_runner import MitmproxyRunner
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


def _log_bootstrap_result(result: BootstrapResult) -> None:
    __translations = load_translations()
    title = __translations.get("BOOSTSTRAP_ERROR_DIALOG_TITLE")
    if result.signal == BootstrapSignal.OK:
        debug("✅ Bootstrap completed", context="main.fit_bootstrap")
    else:
        debug(f"❌ Bootstrap error: {result.message}", context="main.fit_bootstrap")
        show_dialog("error", title, result.message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FIT Bootstrap")
    parser.add_argument(
        "--debug",
        choices=["none", "log", "verbose"],
        default="none",
        help="Set the debug level (default: none)",
    )
    return parser.parse_args()


def _run_gui() -> int:
    debug(
        f"_run_gui uid={os.getuid()} euid={os.geteuid()}", context="main.fit_bootstrap"
    )
    debug(
        f"_run_gui user={os.environ.get('LOGNAME')} sudo_user={os.environ.get('SUDO_USER')}",
        context="main.fit_bootstrap",
    )
    debug(f"_run_gui DISPLAY={os.environ.get('DISPLAY')}", context="main.fit_bootstrap")
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QLabel,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError:
        debug(
            "❌ PySide6 is not installed in this environment",
            context="main.fit_bootstrap",
        )
        return 1

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("FIT Bootstrap GUI 1.0.15")
    layout = QVBoxLayout(window)
    euid = os.geteuid()
    status = "root" if euid == 0 else "user"
    layout.addWidget(QLabel(f"EUID: {euid} ({status})"))
    layout.addWidget(QLabel(f"PID: {os.getpid()}"))
    status_label = QLabel("Bootstrap status: idle")
    layout.addWidget(status_label)
    start_button = QPushButton("Start Proxy")
    stop_button = QPushButton("Stop Proxy")
    start_capture_button = QPushButton("Start Capture")
    stop_capture_button = QPushButton("Stop Capture")
    stop_button.setEnabled(False)
    start_capture_button.setEnabled(False)
    stop_capture_button.setEnabled(False)
    proxy_manager: MacProxyManager | None = None
    proxy_state: ProxyState | None = None
    mitm_runner = MitmproxyRunner(window)

    def _restore_proxy() -> None:
        nonlocal proxy_manager, proxy_state
        if proxy_manager and proxy_state:
            proxy_manager.restore(proxy_state)
        proxy_manager = None
        proxy_state = None

    atexit.register(_restore_proxy)

    def _start_proxy() -> None:
        nonlocal proxy_manager, proxy_state
        start_button.setEnabled(False)
        status_label.setText("Proxy status: starting...")

        proxy_service = MacProxyManager.detect_service()
        if not proxy_service:
            status_label.setText("Proxy status: no active network service")
            start_button.setEnabled(True)
            return

        proxy_manager = MacProxyManager(proxy_service)
        proxy_state = proxy_manager.snapshot()
        if proxy_state is None:
            status_label.setText("Proxy status: snapshot failed")
            proxy_manager = None
            start_button.setEnabled(True)
            return

        mitm_port = os.environ.get(FIT_MITM_PORT, "8080")
        debug(
            f"mitm_port env={os.environ.get(FIT_MITM_PORT)} resolved={mitm_port}",
            context="main.fit_bootstrap",
        )
        try:
            port_value = int(mitm_port)
        except ValueError:
            port_value = 8080
        proxy_manager.enable_capture_proxy("127.0.0.1", port_value)
        status_label.setText(f"Proxy status: enabled ({proxy_service})")
        stop_button.setEnabled(True)

    def _stop_proxy() -> None:
        stop_button.setEnabled(False)
        status_label.setText("Proxy status: stopping...")
        _restore_proxy()
        status_label.setText("Proxy status: disabled")
        start_button.setEnabled(True)

    start_button.clicked.connect(_start_proxy)
    stop_button.clicked.connect(_stop_proxy)
    layout.addWidget(start_button)
    layout.addWidget(stop_button)
    layout.addWidget(start_capture_button)
    layout.addWidget(stop_capture_button)

    def _start_capture() -> None:
        start_capture_button.setEnabled(False)
        status_label.setText("Capture status: starting...")
        if mitm_runner.start_capture():
            status_label.setText("Capture status: active")
            stop_capture_button.setEnabled(True)
        else:
            status_label.setText("Capture status: start failed")
            start_capture_button.setEnabled(True)

    def _stop_capture() -> None:
        stop_capture_button.setEnabled(False)
        status_label.setText("Capture status: stopping...")
        if mitm_runner.stop_capture():
            status_label.setText("Capture status: stopped")
            start_capture_button.setEnabled(True)
        else:
            status_label.setText("Capture status: stop failed")
            stop_capture_button.setEnabled(True)

    start_capture_button.clicked.connect(_start_capture)
    stop_capture_button.clicked.connect(_stop_capture)
    start_capture_button.setEnabled(True)

    def _on_close(event) -> None:
        mitm_runner.stop_capture()
        mitm_runner.stop_by_pid()
        event.accept()

    window.closeEvent = _on_close
    window.setLayout(layout)
    window.resize(320, 120)
    window.show()
    return app.exec()


def main() -> int:

    if get_platform() == "macos" and os.environ.get("FIT_MITM_LAUNCH") == "1":
        from mitmproxy.tools.main import mitmdump

        return mitmdump()

    if get_platform() == "macos" and os.environ.get("FIT_ASKPASS_DIALOG") == "1":
        from fit_bootstrap.macos.askpass_dialog import main as askpass_main

        return askpass_main()

    if os.environ.get("FIT_UPDATE_DIALOG") == "1":
        from fit_bootstrap.updater import main as updater_main

        return updater_main()

    args = parse_args()
    debug_enabled = args.debug != "none"

    set_debug_level(
        {
            "none": DebugLevel.NONE,
            "log": DebugLevel.LOG,
            "verbose": DebugLevel.VERBOSE,
        }[args.debug]
    )
    debug(f"Freeze directory: {resolve_path("")}", context="main.fit_web")
    debug(f"argv: {sys.argv}", context="main.fit_bootstrap")
    debug(f"bundled: {is_bundled()}", context="main.fit_bootstrap")

    if os.environ.get(STAGE_ENV) == STAGE_GUI:
        debug(f"GUI stage admin: {is_admin()}", context="main.fit_bootstrap")
        if not is_admin():
            debug("❌ GUI stage requires root privileges", context="main.fit_bootstrap")
            return 1
        if not acquire_app_lock():
            debug(
                "❌ Another instance is already running", context="main.fit_bootstrap"
            )
            return 1
        atexit.register(release_app_lock)
        return _run_gui()

    bootstrap = Bootstrap(
        debug_enabled=debug_enabled, caller=CallerProfile.FIT_BOOTSTRAP
    )

    preflight_result = bootstrap.run_preflight_checks(
        argv=list(sys.argv),
        stage_env=STAGE_ENV,
        stage_gui=STAGE_GUI,
    )
    if preflight_result is not None:
        _log_bootstrap_result(preflight_result)
        return preflight_result.code

    mitm_runner = MitmproxyRunner()
    if not mitm_runner.start():
        debug("❌ mitmproxy start failed", context="main.fit_bootstrap")
        return 1

    dispatch_result = bootstrap._dispatch(
        on_signal=_log_bootstrap_result,
        argv=list(sys.argv),
        stage_env=STAGE_ENV,
        stage_gui=STAGE_GUI,
        preflight_completed=True,
    )

    if dispatch_result.code != 0:
        pass
        # mitm_runner.stop_by_pid()
    return dispatch_result.code


if __name__ == "__main__":
    raise SystemExit(main())
