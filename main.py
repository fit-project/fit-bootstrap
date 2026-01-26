import argparse
import atexit
import os
import sys

from fit_common.core import (
    DebugLevel,
    debug,
    get_platform,
    is_admin,
    is_bundled,
    set_debug_level,
)

from fit_bootstrap.bootstrap import STAGE_ENV, STAGE_GUI, Bootstrap
from fit_bootstrap.macos.proxy import MacProxyManager, ProxyState
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


def _log_bootstrap_result(result: BootstrapResult) -> None:
    if result.signal == BootstrapSignal.OK:
        debug("✅ Bootstrap completed")
    elif result.signal == BootstrapSignal.ADMIN_DENIED:
        debug("❌ Admin permissions denied")
    elif result.signal == BootstrapSignal.UNSUPPORTED_OS:
        debug(f"❌ Unsupported operating system: {result.message}")
    else:
        debug(f"❌ Bootstrap error: {result.message}")


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
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QLabel,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError:
        debug("❌ PySide6 is not installed in this environment")
        return 1

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("FIT Bootstrap GUI")
    layout = QVBoxLayout(window)
    euid = os.geteuid()
    status = "root" if euid == 0 else "user"
    layout.addWidget(QLabel(f"EUID: {euid} ({status})"))
    layout.addWidget(QLabel(f"PID: {os.getpid()}"))
    status_label = QLabel("Bootstrap status: idle")
    layout.addWidget(status_label)
    start_button = QPushButton("Start Proxy")
    stop_button = QPushButton("Stop Proxy")
    stop_mitm_button = QPushButton("Stop mitmproxy")
    stop_button.setEnabled(False)
    proxy_manager: MacProxyManager | None = None
    proxy_state: ProxyState | None = None
    bootstrap = Bootstrap()

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

        proxy_manager.enable_capture_proxy("127.0.0.1", 8080)
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
    layout.addWidget(stop_mitm_button)

    def _stop_mitm() -> None:
        stop_mitm_button.setEnabled(False)
        status_label.setText("Mitmproxy status: stopping...")
        if bootstrap.stop_mitmproxy():
            status_label.setText("Mitmproxy status: stopped")
        else:
            status_label.setText("Mitmproxy status: stop failed")
        stop_mitm_button.setEnabled(True)

    stop_mitm_button.clicked.connect(_stop_mitm)
    window.setLayout(layout)
    window.resize(320, 120)
    window.show()
    return app.exec()


def main() -> int:
    if get_platform() == "macos" and os.environ.get("FIT_MITM_LAUNCH") == "1":
        from mitmproxy.tools.main import mitmdump

        return mitmdump()

    if get_platform() == "macos" and os.environ.get("FIT_ASKPASS_PYSIDE") == "1":
        from fit_bootstrap.macos.askpass_pyside import main as askpass_main

        return askpass_main()

    args = parse_args()
    set_debug_level(
        {
            "none": DebugLevel.NONE,
            "log": DebugLevel.LOG,
            "verbose": DebugLevel.VERBOSE,
        }[args.debug]
    )
    debug(f"argv: {sys.argv}")
    debug(f"bundled: {is_bundled()}")

    if os.environ.get(STAGE_ENV) == STAGE_GUI:
        debug(f"GUI stage admin: {is_admin()}")
        if not is_admin():
            debug("❌ GUI stage requires root privileges")
            return 1
        return _run_gui()

    if is_admin():
        return _run_gui()

    preflight_result = Bootstrap()._dispatch(
        on_signal=_log_bootstrap_result,
        argv=list(sys.argv),
        stage_env=STAGE_ENV,
        stage_gui=STAGE_GUI,
        debug_enabled=args.debug != "none",
    )

    return preflight_result.code


if __name__ == "__main__":
    raise SystemExit(main())
