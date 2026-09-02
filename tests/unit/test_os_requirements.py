from __future__ import annotations

import subprocess
from unittest.mock import Mock

import pytest

from fit_bootstrap import os_requirements as os_requirements_module
from fit_bootstrap.context import AcquisitionContext
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
    monkeypatch.setattr(
        os_requirements_module, "_can_access_gnome_proxy_settings", lambda: True
    )
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


@pytest.mark.unit
def test_gnome_proxy_settings_rejects_missing_gsettings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(os_requirements_module.shutil, "which", lambda _name: None)
    run = Mock()
    monkeypatch.setattr(os_requirements_module.subprocess, "run", run)

    assert not os_requirements_module._can_access_gnome_proxy_settings()
    run.assert_not_called()


@pytest.mark.unit
def test_gnome_proxy_settings_reads_all_required_keys_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gsettings_path = "/usr/bin/gsettings"
    monkeypatch.setattr(
        os_requirements_module.shutil, "which", lambda name: gsettings_path
    )
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(os_requirements_module.subprocess, "run", run)

    assert os_requirements_module._can_access_gnome_proxy_settings()

    expected_settings = (
        ("org.gnome.system.proxy", "mode"),
        ("org.gnome.system.proxy", "autoconfig-url"),
        ("org.gnome.system.proxy", "ignore-hosts"),
        ("org.gnome.system.proxy.http", "enabled"),
        ("org.gnome.system.proxy.http", "host"),
        ("org.gnome.system.proxy.http", "port"),
        ("org.gnome.system.proxy.https", "host"),
        ("org.gnome.system.proxy.https", "port"),
    )
    commands = [call.args[0] for call in run.call_args_list]
    assert commands == [
        [gsettings_path, "get", schema, key] for schema, key in expected_settings
    ]
    assert all(command[0] == gsettings_path for command in commands)
    assert all(command[1] == "get" for command in commands)
    assert not {"set", "sudo", "pkexec"}.intersection(
        argument for command in commands for argument in command
    )
    assert all(call.kwargs.get("shell") is not True for call in run.call_args_list)
    assert all(call.kwargs.get("timeout") is not None for call in run.call_args_list)


@pytest.mark.unit
@pytest.mark.parametrize(
    "failed_call",
    [
        0,  # main schema
        3,  # HTTP schema
        6,  # HTTPS schema
    ],
)
def test_gnome_proxy_settings_rejects_unavailable_key(
    failed_call: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [subprocess.CompletedProcess([], 0) for _ in range(8)]
    results[failed_call] = subprocess.CompletedProcess([], 1)
    run = Mock(side_effect=results)
    monkeypatch.setattr(os_requirements_module.subprocess, "run", run)

    assert not os_requirements_module._can_access_gnome_proxy_settings(
        "/usr/bin/gsettings"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(),
        OSError(),
        subprocess.TimeoutExpired(["/usr/bin/gsettings"], 3),
    ],
)
def test_gnome_proxy_settings_handles_command_errors(
    error: BaseException,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        os_requirements_module.subprocess, "run", Mock(side_effect=error)
    )

    assert not os_requirements_module._can_access_gnome_proxy_settings(
        "/usr/bin/gsettings"
    )


@pytest.mark.unit
def test_linux_configuration_rejects_missing_gnome_proxy_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supported_linux(monkeypatch)
    monkeypatch.setattr(
        os_requirements_module, "_can_access_gnome_proxy_settings", lambda: False
    )

    result = os_requirements_module._ensure_supported_linux_configuration()

    assert result is not None
    assert result.signal == BootstrapSignal.ERROR
    assert "GNOME/GSettings proxy support" in (result.message or "")


@pytest.mark.unit
def test_linux_configuration_accepts_gnome_proxy_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supported_linux(monkeypatch)

    assert os_requirements_module._ensure_supported_linux_configuration() is None
