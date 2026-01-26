import argparse
import atexit
import os
import sys
from pathlib import Path

from fit_common.core import DebugLevel, debug, get_platform, set_debug_level
from fit_common.core.paths import resolve_log_path

from fit_bootstrap.bootstrap import Bootstrap
from fit_bootstrap.macos.certificate import CertificateManager
from fit_bootstrap.macos.proxy import MacProxyManager, ProxyState
from fit_bootstrap.macos.mitmproxy_runner import MitmproxyRunner
from fit_bootstrap.privilege import ensure_root_or_relaunch
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

_STAGE_ENV = "FIT_BOOTSTRAP_STAGE"
_STAGE_GUI = "gui"
_OUTPUT_DIR = Path("/Users/zitelog/Developer/Workspace/fit-bootstrap/mimtproxy")
_IS_BUNDLED = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def __log_bootstrap_result(result: BootstrapResult) -> None:
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
    mitm_runner = MitmproxyRunner(_OUTPUT_DIR)

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
        if mitm_runner.stop_by_pid():
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
    if os.environ.get("FIT_ASKPASS_PYSIDE") == "1":
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
    if args.debug != "none":
        os.environ["FIT_BOOTSTRAP_DEBUG"] = "1"
        os.environ["FIT_ASKPASS_LOG"] = resolve_log_path("askpass.log")

    debug(f"argv: {sys.argv}")
    debug(f"bundled: {_IS_BUNDLED}")

    platform = get_platform()
    if platform == "macos":
        if os.environ.get(_STAGE_ENV) == _STAGE_GUI:
            if os.geteuid() != 0:
                debug("❌ GUI stage requires root privileges")
                return 1
            return _run_gui()

        cert_manager = CertificateManager()
        debug("PRE-FLIGHT: verifying CA certificate")
        if cert_manager.add_cert() != 0:
            debug("❌ Certificate installation failed")
            return 1

        debug("PRE-FLIGHT: starting mitmproxy")
        mitm_runner = MitmproxyRunner(_OUTPUT_DIR)
        mitm_process = mitm_runner.start()
        if not mitm_process:
            return 1
        atexit.register(mitm_runner.stop, mitm_process)

        if os.geteuid() == 0:
            return _run_gui()

        debug("PRE-FLIGHT: relaunching as root via osascript")
        relaunch_argv = list(sys.argv[1:] if _IS_BUNDLED else sys.argv)
        relaunch_code = ensure_root_or_relaunch(
            relaunch_argv,
            prefer_osascript=True,
            env_overrides={_STAGE_ENV: _STAGE_GUI},
        )
        if relaunch_code != 0:
            debug("❌ Elevation failed")
            mitm_runner.stop(mitm_process)
        return relaunch_code

    bootstrap = Bootstrap()
    result = bootstrap._dispatch(on_signal=__log_bootstrap_result)
    return result.code


if __name__ == "__main__":
    raise SystemExit(main())
