from __future__ import annotations

import subprocess

import pytest

from fit_bootstrap.macos.permission import PermissionChecker
from fit_bootstrap.signals import BootstrapSignal


@pytest.mark.unit
def test_permission_checker_returns_error_when_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIT_SCREEN_RECODER_PATH", "/tmp/fit-screen-recoder")
    monkeypatch.setattr(
        "fit_bootstrap.macos.permission.load_translations",
        lambda: {
            "BOOSTSTRAP_FFMPEG_SCREEN_RECORDING_PERMISSIONS_DENIED_MESSAGE": "denied"
        },
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["fit-screen-recoder", "--check-permissions"],
            returncode=0,
            stdout="screen_recording=denied\n",
            stderr="",
        ),
    )

    result = PermissionChecker().run()

    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR
    assert result.message == "denied"


@pytest.mark.unit
def test_permission_checker_returns_ok_when_granted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIT_SCREEN_RECODER_PATH", "/tmp/fit-screen-recoder")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["fit-screen-recoder", "--check-permissions"],
            returncode=0,
            stdout="screen_recording=granted\n",
            stderr="",
        ),
    )

    result = PermissionChecker().run()

    assert result.code == 0
    assert result.signal == BootstrapSignal.OK
    assert result.message is None
