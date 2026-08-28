from __future__ import annotations

import pytest

import main as main_module
from fit_bootstrap.screen_recorder import (
    LinuxRecorderInstallOutcome,
    LinuxRecorderInstallResult,
    LinuxRecorderPackageInfo,
    LinuxRecorderPackageStatus,
)
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal


def _missing_result() -> BootstrapResult:
    return BootstrapResult(
        code=1,
        signal=BootstrapSignal.ERROR,
        message="installation required",
    )


@pytest.mark.unit
def test_linux_recorder_ui_installs_after_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "inspect_linux_screen_recorder_package",
        lambda: LinuxRecorderPackageInfo(LinuxRecorderPackageStatus.NOT_INSTALLED),
    )
    monkeypatch.setattr(
        main_module, "ensure_screen_recoder_available", _missing_result
    )
    confirmations: list[str] = []
    monkeypatch.setattr(
        main_module,
        "_confirm_linux_screen_recorder_install",
        lambda message: confirmations.append(message) or True,
    )
    install_calls: list[bool] = []
    monkeypatch.setattr(
        main_module,
        "install_linux_screen_recorder_package",
        lambda: install_calls.append(True)
        or LinuxRecorderInstallResult(LinuxRecorderInstallOutcome.INSTALLED),
    )

    result = main_module._install_linux_screen_recorder_from_ui()

    assert result is None
    assert confirmations == ["installation required"]
    assert install_calls == [True]


@pytest.mark.unit
def test_linux_recorder_ui_does_not_install_without_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "inspect_linux_screen_recorder_package",
        lambda: LinuxRecorderPackageInfo(LinuxRecorderPackageStatus.NOT_INSTALLED),
    )
    monkeypatch.setattr(
        main_module, "ensure_screen_recoder_available", _missing_result
    )
    monkeypatch.setattr(
        main_module, "_confirm_linux_screen_recorder_install", lambda _message: False
    )
    monkeypatch.setattr(
        main_module,
        "install_linux_screen_recorder_package",
        lambda: pytest.fail("installation must require confirmation"),
    )

    result = main_module._install_linux_screen_recorder_from_ui()

    assert result is not None
    assert result.signal == BootstrapSignal.ERROR


@pytest.mark.unit
def test_linux_recorder_ui_does_not_prompt_for_detection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = BootstrapResult(
        code=1,
        signal=BootstrapSignal.ERROR,
        message="dpkg-query unavailable",
    )
    monkeypatch.setattr(
        main_module,
        "inspect_linux_screen_recorder_package",
        lambda: LinuxRecorderPackageInfo(
            LinuxRecorderPackageStatus.DPKG_QUERY_UNAVAILABLE
        ),
    )
    monkeypatch.setattr(
        main_module, "ensure_screen_recoder_available", lambda: expected
    )
    monkeypatch.setattr(
        main_module,
        "_confirm_linux_screen_recorder_install",
        lambda _message: pytest.fail("detection errors must not prompt installation"),
    )

    result = main_module._install_linux_screen_recorder_from_ui()

    assert result == expected


@pytest.mark.unit
def test_linux_recorder_ui_maps_install_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "inspect_linux_screen_recorder_package",
        lambda: LinuxRecorderPackageInfo(LinuxRecorderPackageStatus.NOT_INSTALLED),
    )
    monkeypatch.setattr(
        main_module, "ensure_screen_recoder_available", _missing_result
    )
    monkeypatch.setattr(
        main_module, "_confirm_linux_screen_recorder_install", lambda _message: True
    )
    monkeypatch.setattr(
        main_module,
        "install_linux_screen_recorder_package",
        lambda: LinuxRecorderInstallResult(
            LinuxRecorderInstallOutcome.POST_INSTALL_VERIFICATION_FAILED
        ),
    )

    result = main_module._install_linux_screen_recorder_from_ui()

    assert result is not None
    assert result.signal == BootstrapSignal.ERROR
    assert result.message
