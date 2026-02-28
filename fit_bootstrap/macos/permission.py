"""Console helper that checks macOS screen-recording permissions via ffmpeg."""

from __future__ import annotations

import subprocess

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

from fit_bootstrap.ffmpeg import get_ffmpeg_path
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


class PermissionChecker:
    def __init__(self) -> None:
        self._ffmpeg_path = get_ffmpeg_path()

    def run(self) -> BootstrapResult:

        list_result = get_list_devices(self._ffmpeg_path)
        stderr = list_result.error or ""
        audio_index = find_audio_device_index(list_result.devices)
        if audio_index:
            debug(
                f"ℹ️ Detected audio device index: {audio_index}",
                context=get_context(self),
            )
        if not list_result.success:
            debug(
                f"❌ ffmpeg list devices failed (rc={list_result.returncode}).",
                context=get_context(self),
            )
            if stderr:
                debug(
                    f"ℹ️ ffmpeg list devices stderr: {stderr}", context=get_context(self)
                )

            return BootstrapResult(
                code=list_result.returncode,
                signal=BootstrapSignal.FFMPEG_LIST_DEVICES_FAILED,
                message=stderr,
            )
        debug(
            f"✅ Successfully listed ffmpeg devices ({len(list_result.devices)} total)",
            context=get_context(self),
        )
        screen_index = find_screen_device_index(list_result.devices)
        if screen_index is None:
            debug(
                "❌ No screen capture device detected by ffmpeg.",
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
            debug(
                "⚠️ ffmpeg exceeded the timeout: interrupted to show the issue",
                context=get_context(self),
            )
            if combined:
                debug(combined.strip(), context=get_context(self))
            return FFmpegResult(-1, combined, timed_out=True)

    def _interpret_capture_result(self, result: FFmpegResult) -> BootstrapResult:
        if result.returncode == 0:
            debug("✅ Screen recording permissions granted.", context=get_context(self))
            return BootstrapResult(code=0, signal=BootstrapSignal.OK, message=None)

        code = result.returncode if result.returncode != 0 else 1
        if self._permission_was_denied(result.stderr):
            debug("❌ Permissions denied by the system.", context=get_context(self))
            signal = BootstrapSignal.FFMPEG_SCREEN_RECORDING_PERMISSIONS_DENIED
        else:
            debug("⚠️ An error occurred during the test recording.")
            if result.timed_out:
                debug(
                    "⚠️ ffmpeg was interrupted because it would not finish; check permissions or restart the app."
                )
            signal = BootstrapSignal.FFMPEG_SCREEN_RECORDING_TEST_FAILED

        return BootstrapResult(
            code=code,
            signal=signal,
            message=None,
        )

    def _permission_was_denied(self, output: str) -> bool:
        return permission_was_denied(output)
