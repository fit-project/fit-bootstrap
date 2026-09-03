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


def _patch_supported_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os_requirements_module, "get_platform", lambda: "lin")
    monkeypatch.setattr(
        os_requirements_module,
        "_read_os_release",
        lambda: {"ID": "ubuntu", "ID_LIKE": "debian"},
    )
    monkeypatch.setattr(
        os_requirements_module.shutil, "which", lambda _name: "/usr/bin/dpkg"
    )
    monkeypatch.setattr(os_requirements_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(os_requirements_module, "_can_connect_to_x11", lambda: True)
    monkeypatch.setattr(os_requirements_module, "_library_available", lambda *_args: True)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")


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
    assert result.signal == BootstrapSignal.ERROR


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
    assert result.signal == BootstrapSignal.ERROR


@pytest.mark.unit
def test_ensure_supported_os_configuration_accepts_debian_linux_x11(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supported_linux(monkeypatch)

    result = os_requirements_module.ensure_supported_os_configuration(
        _context("Linux-6.8")
    )

    assert result is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("distro", "Debian-compatible"),
        ("architecture", "x86_64"),
        ("display", "X11"),
        ("wayland", "Wayland"),
        ("gtk", "GTK 3"),
        ("webkit", "WebKitGTK 4.1"),
    ],
)
def test_ensure_supported_os_configuration_rejects_invalid_linux(
    failure: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supported_linux(monkeypatch)
    if failure == "distro":
        monkeypatch.setattr(
            os_requirements_module, "_read_os_release", lambda: {"ID": "fedora"}
        )
    elif failure == "architecture":
        monkeypatch.setattr(
            os_requirements_module.platform, "machine", lambda: "aarch64"
        )
    elif failure == "display":
        monkeypatch.delenv("DISPLAY")
    elif failure == "wayland":
        monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    elif failure == "gtk":
        monkeypatch.setattr(
            os_requirements_module,
            "_library_available",
            lambda name, _sonames: name != "gtk-3",
        )
    elif failure == "webkit":
        monkeypatch.setattr(
            os_requirements_module,
            "_library_available",
            lambda name, _sonames: name != "webkit2gtk-4.1",
        )

    result = os_requirements_module.ensure_supported_os_configuration(
        _context("Linux-6.8")
    )

    assert result is not None
    assert result.signal == BootstrapSignal.ERROR
    assert expected in (result.message or "")
