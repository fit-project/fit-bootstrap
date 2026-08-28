from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from fit_bootstrap import screen_recorder as screen_recorder_module
from fit_bootstrap.signals import BootstrapSignal


def _patch_supported_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(screen_recorder_module, "get_platform", lambda: "lin")
    monkeypatch.setattr(
        screen_recorder_module,
        "_linux_platform_issue",
        lambda: None,
    )
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")


@pytest.mark.unit
def test_ensure_screen_recoder_available_returns_existing_env_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    existing = tmp_path / "fit-screen-recoder"
    existing.write_text("ok")
    monkeypatch.setattr(screen_recorder_module, "get_platform", lambda: "macos")
    monkeypatch.setenv("FIT_SCREEN_RECODER_PATH", str(existing))

    result = screen_recorder_module.ensure_screen_recoder_available()

    assert result is None


@pytest.mark.unit
def test_ensure_screen_recoder_available_sets_env_for_macos_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    binary = tmp_path / "fit_screen_recorder_binaries" / "macos_arm64" / "fit-screen-recoder"
    binary.parent.mkdir(parents=True)
    binary.write_text("ok")
    monkeypatch.delenv("FIT_SCREEN_RECODER_PATH", raising=False)
    monkeypatch.setattr(screen_recorder_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(screen_recorder_module, "_bundle_base_path", lambda: tmp_path)
    monkeypatch.setattr(
        screen_recorder_module,
        "_ensure_quarantine_removed",
        lambda path: path == binary,
    )

    result = screen_recorder_module.ensure_screen_recoder_available()

    assert result is None
    assert os.environ["FIT_SCREEN_RECODER_PATH"] == str(binary)


@pytest.mark.unit
def test_ensure_screen_recoder_available_returns_error_when_bundle_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("FIT_SCREEN_RECODER_PATH", raising=False)
    monkeypatch.setattr(screen_recorder_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(screen_recorder_module, "_bundle_base_path", lambda: tmp_path)

    result = screen_recorder_module.ensure_screen_recoder_available()

    assert result is not None
    assert result.signal == BootstrapSignal.ERROR


@pytest.mark.unit
def test_linux_package_installed_sets_package_binary_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_supported_linux(monkeypatch)
    binary = tmp_path / "fit-screen-recorder"
    binary.write_text("binary")
    monkeypatch.setattr(
        screen_recorder_module.shutil,
        "which",
        lambda name: "/usr/bin/dpkg-query" if name == "dpkg-query" else None,
    )
    monkeypatch.setattr(
        screen_recorder_module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, "install ok installed\n1.1.0\n", ""
        ),
    )
    monkeypatch.setattr(
        screen_recorder_module, "_installed_linux_binary_path", lambda _dpkg: binary
    )

    result = screen_recorder_module.ensure_screen_recoder_available()

    assert result is None
    assert os.environ["FIT_SCREEN_RECODER_PATH"] == str(binary)


@pytest.mark.unit
def test_linux_package_not_installed_does_not_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supported_linux(monkeypatch)
    monkeypatch.setattr(
        screen_recorder_module.shutil,
        "which",
        lambda name: "/usr/bin/dpkg-query" if name == "dpkg-query" else None,
    )
    calls: list[list[str]] = []

    def _run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 1, "", "dpkg-query: no packages found matching fit-screen-recorder"
        )

    monkeypatch.setattr(screen_recorder_module.subprocess, "run", _run)

    info = screen_recorder_module.inspect_linux_screen_recorder_package()

    assert info.status == screen_recorder_module.LinuxRecorderPackageStatus.NOT_INSTALLED
    assert len(calls) == 1
    assert calls[0][0] == "/usr/bin/dpkg-query"


@pytest.mark.unit
def test_linux_package_reports_missing_dpkg_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_supported_linux(monkeypatch)
    monkeypatch.setattr(screen_recorder_module.shutil, "which", lambda _name: None)

    info = screen_recorder_module.inspect_linux_screen_recorder_package()

    assert (
        info.status
        == screen_recorder_module.LinuxRecorderPackageStatus.DPKG_QUERY_UNAVAILABLE
    )


@pytest.mark.unit
def test_linux_install_reports_missing_pkexec(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    deb = tmp_path / "fit-screen-recorder.deb"
    deb.write_text("deb")
    not_installed = screen_recorder_module.LinuxRecorderPackageInfo(
        screen_recorder_module.LinuxRecorderPackageStatus.NOT_INSTALLED
    )
    monkeypatch.setattr(
        screen_recorder_module,
        "inspect_linux_screen_recorder_package",
        lambda: not_installed,
    )
    monkeypatch.setattr(
        screen_recorder_module.shutil,
        "which",
        lambda name: "/usr/bin/apt" if name == "apt" else None,
    )

    result = screen_recorder_module.install_linux_screen_recorder_package(deb)

    assert (
        result.outcome
        == screen_recorder_module.LinuxRecorderInstallOutcome.PKEXEC_UNAVAILABLE
    )


@pytest.mark.unit
def test_linux_install_reports_missing_deb(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        screen_recorder_module,
        "inspect_linux_screen_recorder_package",
        lambda: screen_recorder_module.LinuxRecorderPackageInfo(
            screen_recorder_module.LinuxRecorderPackageStatus.NOT_INSTALLED
        ),
    )

    result = screen_recorder_module.install_linux_screen_recorder_package(
        tmp_path / "missing.deb"
    )

    assert (
        result.outcome
        == screen_recorder_module.LinuxRecorderInstallOutcome.DEB_NOT_FOUND
    )


@pytest.mark.unit
def test_locate_linux_deb_from_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_dir = (
        tmp_path / "fit_screen_recorder_binaries" / "linux_x86_64"
    )
    package_dir.mkdir(parents=True)
    deb = package_dir / "fit-screen-recorder_1.1.0_amd64.deb"
    deb.write_text("deb")
    monkeypatch.delenv("FIT_SCREEN_RECORDER_DEB_PATH", raising=False)
    monkeypatch.setattr(screen_recorder_module, "_bundle_base_path", lambda: tmp_path)

    result = screen_recorder_module.locate_linux_screen_recorder_deb()

    assert result == deb.resolve()


@pytest.mark.unit
def test_linux_install_succeeds_and_rechecks_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    deb = tmp_path / "fit-screen-recorder.deb"
    deb.write_text("deb")
    binary = tmp_path / "fit-screen-recorder"
    binary.write_text("binary")
    package_infos = iter(
        [
            screen_recorder_module.LinuxRecorderPackageInfo(
                screen_recorder_module.LinuxRecorderPackageStatus.NOT_INSTALLED
            ),
            screen_recorder_module.LinuxRecorderPackageInfo(
                screen_recorder_module.LinuxRecorderPackageStatus.INSTALLED,
                version="1.1.0",
                binary_path=binary,
            ),
        ]
    )
    monkeypatch.setattr(
        screen_recorder_module,
        "inspect_linux_screen_recorder_package",
        lambda: next(package_infos),
    )
    monkeypatch.setattr(
        screen_recorder_module.shutil,
        "which",
        lambda name: f"/usr/bin/{name}",
    )
    calls: list[list[str]] = []

    def _run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(screen_recorder_module.subprocess, "run", _run)

    result = screen_recorder_module.install_linux_screen_recorder_package(deb)

    assert result.outcome == screen_recorder_module.LinuxRecorderInstallOutcome.INSTALLED
    assert calls == [
        [
            "/usr/bin/pkexec",
            "/usr/bin/apt",
            "install",
            "-y",
            str(deb.resolve()),
        ]
    ]
    assert os.environ["FIT_SCREEN_RECODER_PATH"] == str(binary)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("returncode", "expected"),
    [
        (126, "AUTHENTICATION_CANCELLED"),
        (1, "INSTALL_FAILED"),
    ],
)
def test_linux_install_handles_cancelled_or_failed_installation(
    returncode: int,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    deb = tmp_path / "fit-screen-recorder.deb"
    deb.write_text("deb")
    monkeypatch.setattr(
        screen_recorder_module,
        "inspect_linux_screen_recorder_package",
        lambda: screen_recorder_module.LinuxRecorderPackageInfo(
            screen_recorder_module.LinuxRecorderPackageStatus.NOT_INSTALLED
        ),
    )
    monkeypatch.setattr(
        screen_recorder_module.shutil,
        "which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        screen_recorder_module.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, returncode),
    )

    result = screen_recorder_module.install_linux_screen_recorder_package(deb)

    assert result.outcome.name == expected


@pytest.mark.unit
def test_linux_install_fails_when_post_install_check_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    deb = tmp_path / "fit-screen-recorder.deb"
    deb.write_text("deb")
    not_installed = screen_recorder_module.LinuxRecorderPackageInfo(
        screen_recorder_module.LinuxRecorderPackageStatus.NOT_INSTALLED
    )
    monkeypatch.setattr(
        screen_recorder_module,
        "inspect_linux_screen_recorder_package",
        lambda: not_installed,
    )
    monkeypatch.setattr(
        screen_recorder_module.shutil,
        "which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        screen_recorder_module.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0),
    )

    result = screen_recorder_module.install_linux_screen_recorder_package(deb)

    assert (
        result.outcome
        == screen_recorder_module.LinuxRecorderInstallOutcome.POST_INSTALL_VERIFICATION_FAILED
    )


@pytest.mark.unit
def test_linux_package_version_comparison() -> None:
    assert screen_recorder_module._version_is_compatible("1.2.0-1", "1.1.0")
    assert not screen_recorder_module._version_is_compatible("1.0.0", "1.1.0")
