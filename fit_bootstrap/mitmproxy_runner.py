from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from fit_common.core import debug

from fit_bootstrap.constants import (
    FIT_DEBUG_ENABLED,
    FIT_LOG_APP_PATH,
    FIT_USER_APP_PATH,
)


class MitmproxyRunner:
    def __init__(self) -> None:
        base_path = os.environ.get(FIT_USER_APP_PATH)
        if not base_path:
            debug("❌ FIT_USER_APP_PATH not set; cannot start mitmproxy")
            self.output_dir = None
            self.pid_file = None
            self.har_file = None
            return
        self.output_dir = Path(base_path) / "mitmproxy"
        self.pid_file = self.output_dir / "mitmproxy.pid"
        self.har_file = self.output_dir / "capture.har"

    def start(self) -> subprocess.Popen[str] | None:
        if self.output_dir is None or self.pid_file is None or self.har_file is None:
            return None

        debug(f"FIT_DEBUG_ENABLED={os.environ.get(FIT_DEBUG_ENABLED)}")

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            debug(f"❌ Unable to create output directory: {exc}")
            return None

        existing_pid = self._read_pid()
        if existing_pid:
            try:
                os.kill(existing_pid, 0)
                debug(f"❌ mitmproxy already running (pid={existing_pid})")
                return None
            except ProcessLookupError:
                self._clear_pid()

        log_file = None
        if os.environ.get(FIT_DEBUG_ENABLED) == "1":
            try:
                log_base = os.environ.get(FIT_LOG_APP_PATH)
                if not log_base:
                    debug("❌ FIT_LOG_APP_PATH not set; cannot open mitmproxy log")
                    return None
                log_file = (Path(log_base) / "mitmproxy.log").open("a")
            except OSError as exc:
                debug(f"❌ Unable to open mitmproxy log file: {exc}")

        base_cmd: list[str]
        extra_env = None
        if getattr(sys, "frozen", False):
            base_cmd = [sys.executable]
            extra_env = {"FIT_MITM_LAUNCH": "1"}
        else:
            base_cmd = [
                sys.executable,
                "-c",
                "from mitmproxy.tools.main import mitmdump; mitmdump()",
            ]

        cmd = [
            *base_cmd,
            "--set",
            f"hardump={self.har_file}",
        ]
        if os.environ.get(FIT_DEBUG_ENABLED) == "1":
            cmd += ["--set", "termlog_verbosity=debug"]
        debug(f"mitm cmd: {cmd}")
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
            os.kill(pid, signal.SIGINT)
            debug("Waiting for mitmproxy to handle SIGINT...")
            for _ in range(12):
                time.sleep(0.25)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    self._clear_pid()
                    if self.har_file:
                        debug(f"HAR exists: {self.har_file.exists()}")
                    return True
            debug("mitmproxy still running after SIGINT; sending SIGTERM")
            os.kill(pid, signal.SIGTERM)
            for _ in range(12):
                time.sleep(0.25)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    self._clear_pid()
                    if self.har_file:
                        debug(f"HAR exists: {self.har_file.exists()}")
                    return True
            debug("mitmproxy still running after SIGTERM; forcing SIGKILL")
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            self._clear_pid()
            debug("ℹ️ mitmproxy process already stopped")
            return True
        except OSError as exc:
            debug(f"❌ Unable to stop mitmproxy: {exc}")
            return False
        self._clear_pid()
        if self.har_file:
            debug(f"HAR exists: {self.har_file.exists()}")
        return True

    def _write_pid(self, pid: int) -> None:
        try:
            if self.pid_file is None:
                return
            self.pid_file.write_text(str(pid))
        except OSError as exc:
            debug(f"❌ Unable to write mitmproxy pid file: {exc}")

    def _read_pid(self) -> int | None:
        try:
            if self.pid_file is None:
                return None
            return int(self.pid_file.read_text().strip())
        except (OSError, ValueError):
            return None

    def _clear_pid(self) -> None:
        try:
            if self.pid_file is None:
                return
            self.pid_file.unlink()
        except OSError:
            pass
