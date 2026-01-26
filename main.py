from __future__ import annotations

import argparse
import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from fit_common.core import DebugLevel, debug, get_platform, set_debug_level

from fit_bootstrap.bootstrap import Bootstrap
from fit_bootstrap.macos.certificate import CertificateManager
from fit_bootstrap.macos.proxy import MacProxyManager, ProxyState
from fit_bootstrap.privilege import ensure_root_or_relaunch
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

_STAGE_ENV = "FIT_BOOTSTRAP_STAGE"
_STAGE_GUI = "gui"
_OUTPUT_DIR = Path("/Users/zitelog/Developer/Workspace/fit-bootstrap/mimtproxy")
_MITM_PID_FILE = _OUTPUT_DIR / "mitmproxy.pid"
_MITM_HAR_FILE = _OUTPUT_DIR / "capture.har"


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


def _is_bundled() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def _bundle_root() -> Path | None:
    if not _is_bundled():
        return None
    app_path = Path(sys.executable).resolve()
    app_bundle = app_path
    while app_bundle.name != "Contents" and app_bundle.parent != app_bundle:
        app_bundle = app_bundle.parent
    if app_bundle.name != "Contents":
        return None
    return app_bundle.parent


def _ensure_not_quarantined_if_bundled() -> bool:
    bundle_root = _bundle_root()
    if not bundle_root:
        debug("PRE-FLIGHT: not a bundled macOS app, skipping quarantine check")
        return True

    result = subprocess.run(
        ["xattr", "-p", "com.apple.quarantine", str(bundle_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        debug("PRE-FLIGHT: app bundle is not quarantined")
        return True

    debug("PRE-FLIGHT: removing quarantine attributes from app bundle")
    remove = subprocess.run(
        ["xattr", "-dr", "com.apple.quarantine", str(bundle_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if remove.returncode != 0:
        debug(
            f"❌ Unable to clear quarantine: {remove.stderr.strip() or remove.stdout.strip()}"
        )
        return False
    debug("✅ Quarantine attributes removed")
    return True


def _write_mitm_pid(pid: int) -> None:
    try:
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        _MITM_PID_FILE.write_text(str(pid))
    except OSError as exc:
        debug(f"❌ Unable to write mitmproxy pid file: {exc}")


def _read_mitm_pid() -> int | None:
    try:
        return int(_MITM_PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return None


def _clear_mitm_pid() -> None:
    try:
        _MITM_PID_FILE.unlink()
    except OSError:
        pass


def _start_mitmproxy() -> subprocess.Popen[str] | None:
    try:
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            ["mitmdump", "--set", f"hardump={_MITM_HAR_FILE}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        debug("❌ mitmdump not found in PATH")
        return None

    time.sleep(0.2)
    if proc.poll() is not None:
        debug("❌ mitmproxy exited immediately after start")
        return None
    _write_mitm_pid(proc.pid)
    debug(f"✅ mitmproxy started (pid={proc.pid})")
    return proc


def _stop_mitmproxy(proc: subprocess.Popen[str] | None) -> None:
    if not proc or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    _clear_mitm_pid()


def _stop_mitmproxy_by_pid() -> bool:
    pid = _read_mitm_pid()
    if not pid:
        debug("❌ mitmproxy pid not found")
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        _clear_mitm_pid()
        debug("ℹ️ mitmproxy process already stopped")
        return True
    except OSError as exc:
        debug(f"❌ Unable to stop mitmproxy: {exc}")
        return False
    _clear_mitm_pid()
    return True


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
        if _stop_mitmproxy_by_pid():
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
    args = parse_args()
    set_debug_level(
        {
            "none": DebugLevel.NONE,
            "log": DebugLevel.LOG,
            "verbose": DebugLevel.VERBOSE,
        }[args.debug]
    )

    platform = get_platform()
    if platform == "macos":
        if os.environ.get(_STAGE_ENV) == _STAGE_GUI:
            if os.geteuid() != 0:
                debug("❌ GUI stage requires root privileges")
                return 1
            return _run_gui()

        if not _ensure_not_quarantined_if_bundled():
            return 1

        cert_manager = CertificateManager()
        debug("PRE-FLIGHT: verifying CA certificate")
        if cert_manager.add_cert() != 0:
            debug("❌ Certificate installation failed")
            return 1

        debug("PRE-FLIGHT: starting mitmproxy")
        mitm_process = _start_mitmproxy()
        if not mitm_process:
            return 1
        atexit.register(_stop_mitmproxy, mitm_process)

        if os.geteuid() == 0:
            return _run_gui()

        debug("PRE-FLIGHT: relaunching as root via osascript")
        relaunch_code = ensure_root_or_relaunch(
            list(sys.argv),
            prefer_osascript=True,
            env_overrides={_STAGE_ENV: _STAGE_GUI},
        )
        if relaunch_code != 0:
            debug("❌ Elevation failed")
            _stop_mitmproxy(mitm_process)
        return relaunch_code

    bootstrap = Bootstrap()
    result = bootstrap._dispatch(on_signal=__log_bootstrap_result)
    return result.code


if __name__ == "__main__":
    raise SystemExit(main())
