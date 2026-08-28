from __future__ import annotations

import os
from pathlib import Path

import pytest

from fit_bootstrap.constants import (
    FIT_LINUX_ASKPASS_BUNDLED,
    FIT_LINUX_ASKPASS_PYTHON,
    FIT_LINUX_SUDO_ASKPASS,
)
from fit_bootstrap.linux import privilege as privilege_module


@pytest.mark.unit
def test_configure_linux_askpass_exports_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(privilege_module.shutil, "which", lambda _name: "/usr/bin/sudo")
    monkeypatch.setattr(privilege_module.Path, "is_file", lambda _self: True)
    monkeypatch.setattr(privilege_module.os, "access", lambda *_args: True)
    monkeypatch.setattr(privilege_module, "is_bundled", lambda: False)
    monkeypatch.setattr(privilege_module.sys, "executable", "/venv/bin/python")

    result = privilege_module.configure_linux_askpass()

    assert result is None
    assert os.environ[FIT_LINUX_SUDO_ASKPASS].endswith("linux/askpass.sh")
    assert os.environ[FIT_LINUX_ASKPASS_PYTHON] == "/venv/bin/python"
    assert os.environ[FIT_LINUX_ASKPASS_BUNDLED] == "0"


@pytest.mark.unit
def test_configure_linux_askpass_requires_sudo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(privilege_module.shutil, "which", lambda _name: None)

    assert privilege_module.configure_linux_askpass() == "sudo"


@pytest.mark.unit
def test_configure_linux_askpass_requires_executable_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(privilege_module.shutil, "which", lambda _name: "/usr/bin/sudo")
    monkeypatch.setattr(privilege_module.Path, "is_file", lambda _self: True)
    monkeypatch.setattr(privilege_module.os, "access", lambda *_args: False)

    assert privilege_module.configure_linux_askpass() == "askpass"
