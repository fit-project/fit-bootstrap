from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from fit_common.core import debug


class MitmproxyRunner:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.pid_file = self.output_dir / "mitmproxy.pid"
        self.har_file = self.output_dir / "capture.har"

    def start(self) -> subprocess.Popen[str] | None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            debug(f"❌ Unable to create output directory: {exc}")
            return None

        cmd = [
            sys.executable,
            "-m",
            "mitmproxy.tools.dump",
            "--set",
            f"hardump={self.har_file}",
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except FileNotFoundError:
            debug("❌ Unable to launch mitmproxy module")
            return None

        time.sleep(0.2)
        if proc.poll() is not None:
            debug("❌ mitmproxy exited immediately after start")
            return None

        self._write_pid(proc.pid)
        debug(f"✅ mitmproxy started (pid={proc.pid})")
        return proc

    def stop(self, proc: subprocess.Popen[str] | None) -> None:
        if not proc or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        self._clear_pid()

    def stop_by_pid(self) -> bool:
        pid = self._read_pid()
        if not pid:
            debug("❌ mitmproxy pid not found")
            return False
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            self._clear_pid()
            debug("ℹ️ mitmproxy process already stopped")
            return True
        except OSError as exc:
            debug(f"❌ Unable to stop mitmproxy: {exc}")
            return False
        self._clear_pid()
        return True

    def _write_pid(self, pid: int) -> None:
        try:
            self.pid_file.write_text(str(pid))
        except OSError as exc:
            debug(f"❌ Unable to write mitmproxy pid file: {exc}")

    def _read_pid(self) -> int | None:
        try:
            return int(self.pid_file.read_text().strip())
        except (OSError, ValueError):
            return None

    def _clear_pid(self) -> None:
        try:
            self.pid_file.unlink()
        except OSError:
            pass
