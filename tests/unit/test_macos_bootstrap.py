from __future__ import annotations

import pytest

from fit_bootstrap.macos import bootstrap as macos_bootstrap_module
from fit_bootstrap.signals import BootstrapSignal


@pytest.mark.unit
def test_install_certificate_returns_ok_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        macos_bootstrap_module,
        "CertificateManager",
        lambda: type("_C", (), {"add_cert": lambda self: 0})(),  # noqa: ARG005
    )

    result = macos_bootstrap_module.MacBootstrap().install_certificate()

    assert result.code == 0
    assert result.signal == BootstrapSignal.OK


@pytest.mark.unit
def test_install_certificate_returns_specific_signal_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        macos_bootstrap_module,
        "CertificateManager",
        lambda: type("_C", (), {"add_cert": lambda self: 1})(),  # noqa: ARG005
    )

    result = macos_bootstrap_module.MacBootstrap().install_certificate()

    assert result.code == 1
    assert result.signal == BootstrapSignal.CERTIFICATE_NOT_INSTALLED
    assert result.message == "Certificate installation failed"
