"""Console helper that checks macOS screen-recording permissions via ffmpeg."""

from __future__ import annotations

import subprocess
import sys

from fit_common.core import debug, get_context
from fit_common.core.ffmpeg import (
    FFmpegResult,
    combine_timeout_output,
    execute_ffmpeg_command,
    find_audio_device_index,
    find_screen_device_index,
    get_list_devices,
    permission_was_denied,
)
from PySide6.QtWidgets import QApplication, QMessageBox

from fit_bootstrap.ffmpeg import get_ffmpeg_path
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal

_LOG_CONTEXT = "fit_bootstrap.macos.permission"


class PermissionChecker:
    def __init__(self) -> None:
        self._ffmpeg_path = get_ffmpeg_path()

    def run(self) -> BootstrapResult:

        list_result = get_list_devices(self._ffmpeg_path)
        stderr = list_result.error or ""
        audio_index = find_audio_device_index(list_result.devices)
        if audio_index:
            debug(
                f"Detected audio device index: {audio_index}",
                context=get_context(self),
            )
        if not list_result.success:
            debug(
                f"ffmpeg list devices failed (rc={list_result.returncode}).",
                context=get_context(self),
            )
            if stderr:
                debug(
                    f"ffmpeg list devices stderr: {stderr}", context=get_context(self)
                )

            return BootstrapResult(
                code=list_result.returncode,
                signal=BootstrapSignal.FFMPEG_LIST_DEVICES_FAILED,
                message=stderr,
            )

        screen_index = find_screen_device_index(list_result.devices)
        if screen_index is None:
            debug(
                "No screen capture device detected by ffmpeg.",
                context=get_context(self),
            )
            return BootstrapResult(
                code=list_result.returncode,
                signal=BootstrapSignal.FFMPEG_NO_SCREEN_CAPTURE_DEVICE_DETECTED,
                message=stderr,
            )

        capture_result = self._capture_screen(screen_index)
        return self._interpret_capture_result(capture_result)

    def _capture_screen(self, device_index: str) -> FFmpegResult:
        args = [
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "avfoundation",
            "-capture_cursor",
            "1",
            "-framerate",
            "5",
            "-pixel_format",
            "nv12",
            "-i",
            device_index,
            "-t",
            "1",
            "-f",
            "null",
            "-",
        ]
        try:
            proc = execute_ffmpeg_command(self._ffmpeg_path, args, timeout=8)
            return FFmpegResult(proc.returncode, proc.stderr)
        except subprocess.TimeoutExpired as exc:
            combined = combine_timeout_output(exc)
            self._log("ffmpeg exceeded the timeout: interrupted to show the issue")
            if combined:
                self._log(combined.strip())
            return FFmpegResult(-1, combined, timed_out=True)

    def _interpret_capture_result(self, result: FFmpegResult) -> BootstrapResult:
        if result.returncode == 0:
            self._log("Screen recording permissions granted.")
            return BootstrapResult(code=0, signal=BootstrapSignal.OK)

        code = result.returncode if result.returncode != 0 else 1
        if self._permission_was_denied(result.stderr):
            self._log("Permissions denied by the system.")
            self._prompt_open_privacy(
                "Permesso negato",
                "Il sistema ha bloccato la registrazione dello schermo. Vuoi aprire le preferenze di sicurezza per concedere l'autorizzazione?",
            )
            message = "Screen recording permissions denied"
        else:
            self._log("An error occurred during the test recording.")
            if result.timed_out:
                self._log(
                    "ffmpeg was interrupted because it would not finish; check permissions or restart the app."
                )
            self._prompt_open_privacy(
                "Errore di registrazione",
                "L'accesso allo schermo ha restituito un errore. Vuoi aprire le preferenze privacy per controllare i permessi?",
            )
            message = "Screen recording test failed"

        return BootstrapResult(
            code=code,
            signal=BootstrapSignal.ERROR,
            message=message,
        )

    def _permission_was_denied(self, output: str) -> bool:
        return permission_was_denied(output)

    def _prompt_open_privacy(self, title: str, text: str) -> None:
        answer = QMessageBox.question(
            None,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._open_privacy_settings()

    def _open_privacy_settings(self) -> None:
        url = "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
        try:
            subprocess.run(["open", url], check=False)
        except OSError as exc:
            self._log(f"Unable to open System Preferences: {exc}")

    def _log(self, message: str) -> None:
        debug(message, context=_LOG_CONTEXT)


def main() -> int:
    app = QApplication(sys.argv)
    checker = PermissionChecker()
    result = checker.run()
    return 0 if result.code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
