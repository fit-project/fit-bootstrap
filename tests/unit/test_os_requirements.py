from __future__ import annotations

import pytest

from fit_bootstrap.context import AcquisitionContext
from fit_bootstrap import os_requirements as os_requirements_module
from fit_bootstrap.signals import BootstrapSignal


def _context(os_version: str) -> AcquisitionContext:
    return AcquisitionContext(
        os_type="Darwin",
        os_version=os_version,
        username="alice",
        host_ip="10.0.0.3",
        public_ip="198.51.100.22",
        dns_servers=["1.1.1.1"],
    )


@pytest.mark.unit
def test_ensure_supported_os_configuration_accepts_macos_15_arm64(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os_requirements_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(
        os_requirements_module.platform,
        "machine",
        lambda: "arm64",
    )

    result = os_requirements_module.ensure_supported_os_configuration(
        _context("macOS-15")
    )

    assert result is None


@pytest.mark.unit
def test_ensure_supported_os_configuration_rejects_old_macos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os_requirements_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(
        os_requirements_module.platform,
        "machine",
        lambda: "arm64",
    )

    result = os_requirements_module.ensure_supported_os_configuration(
        _context("macOS-14")
    )

    assert result is not None
    assert result.signal == BootstrapSignal.OS_REQUIREMENTS_NOT_MET


@pytest.mark.unit
def test_ensure_supported_os_configuration_rejects_non_arm64_macos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os_requirements_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(
        os_requirements_module.platform,
        "machine",
        lambda: "x86_64",
    )

    result = os_requirements_module.ensure_supported_os_configuration(
        _context("macOS-15")
    )

    assert result is not None
    assert result.signal == BootstrapSignal.OS_REQUIREMENTS_NOT_MET
