from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from fit_common.core import debug
from fit_common.core.paths import resolve_app_path, resolve_log_path


class MitmproxyRunner:
    def __init__(self, *, debug_enabled: bool = False) -> None:
        self.output_dir = Path(resolve_app_path()) / "mitmproxy"
        self.pid_file = self.output_dir / "mitmproxy.pid"
        self.har_file = self.output_dir / "capture.har"
        self.debug_enabled = debug_enabled

    def start(self) -> subprocess.Popen[str] | None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            debug(f"❌ Unable to create output directory: {exc}")
            return None

        log_file = None
        if self.debug_enabled:
            try:
                log_file = Path(resolve_log_path("mitmproxy.log")).open("a")
            except OSError as exc:
                debug(f"❌ Unable to open mitmproxy log file: {exc}")

        if getattr(sys, "frozen", False):
            cmd = [
                sys.executable,
                "--set",
                f"hardump={self.har_file}",
            ]
            extra_env = {"FIT_MITM_LAUNCH": "1"}
        else:
            cmd = [
                sys.executable,
                "-c",
                "from mitmproxy.tools.main import mitmdump; mitmdump()",
                "--set",
                f"hardump={self.har_file}",
            ]
            extra_env = None
        try:
            stdout = subprocess.PIPE if log_file else subprocess.DEVNULL
            stderr = subprocess.PIPE if log_file else subprocess.DEVNULL
            env = os.environ.copy()
            if extra_env:
                env.update(extra_env)
            proc = subprocess.Popen(
                cmd,
                stdout=stdout,
                stderr=stderr,
                text=True,
                bufsize=1,
                env=env,
            )
        except FileNotFoundError:
            if log_file:
                log_file.close()
            debug("❌ Unable to launch mitmproxy module")
            return None

        if log_file:
            self._pipe_to_file(proc.stdout, log_file)
            self._pipe_to_file(proc.stderr, log_file)

        time.sleep(0.2)
        exit_code = proc.poll()
        if exit_code is not None:
            if log_file:
                log_file.write(f"mitmproxy exited immediately (code={exit_code})\n")
                log_file.close()
            debug(f"❌ mitmproxy exited immediately after start (code={exit_code})")
            return None

        self._write_pid(proc.pid)
        debug(f"✅ mitmproxy started (pid={proc.pid})")
        return proc

    def _pipe_to_file(self, stream: subprocess.Popen[str] | None, log_file) -> None:
        if stream is None:
            return

        def _worker() -> None:
            for line in stream:
                log_file.write(line)
            log_file.flush()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

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
