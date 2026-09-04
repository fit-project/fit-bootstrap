from __future__ import annotations

import pytest

import main as main_module
from fit_bootstrap.linux.mitm_ca import MitmCAOutcome, MitmCAResult
from fit_bootstrap.signals import BootstrapSignal


@pytest.mark.unit
def test_linux_ca_ui_skips_confirmation_when_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "ensure_linux_mitm_ca",
        lambda **_kwargs: MitmCAResult(MitmCAOutcome.READY),
    )
    monkeypatch.setattr(
        main_module,
        "_confirm_linux_install",
        lambda *_args: pytest.fail("ready CA must not prompt"),
    )

    assert main_module._install_linux_mitm_ca_from_ui() is None


@pytest.mark.unit
def test_linux_ca_ui_installs_after_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = iter(
        [
            MitmCAResult(MitmCAOutcome.INSTALL_REQUIRED),
            MitmCAResult(MitmCAOutcome.READY),
        ]
    )
    calls: list[bool] = []

    def ensure(**kwargs):
        calls.append(kwargs.get("allow_install", True))
        return next(results)

    monkeypatch.setattr(main_module, "ensure_linux_mitm_ca", ensure)
    monkeypatch.setattr(main_module, "_confirm_linux_install", lambda *_args: True)

    assert main_module._install_linux_mitm_ca_from_ui() is None
    assert calls == [False, True]


@pytest.mark.unit
def test_linux_ca_ui_does_not_install_without_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def ensure(**kwargs):
        calls.append(kwargs.get("allow_install", True))
        return MitmCAResult(MitmCAOutcome.INSTALL_REQUIRED)

    monkeypatch.setattr(main_module, "ensure_linux_mitm_ca", ensure)
    monkeypatch.setattr(main_module, "_confirm_linux_install", lambda *_args: False)

    result = main_module._install_linux_mitm_ca_from_ui()

    assert result is not None
    assert result.signal == BootstrapSignal.ERROR
    assert calls == [False]
