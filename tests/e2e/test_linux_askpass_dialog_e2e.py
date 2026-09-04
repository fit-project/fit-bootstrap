from __future__ import annotations

import io

import pytest

from fit_bootstrap.linux import askpass_dialog as askpass_dialog_module


@pytest.mark.e2e
def test_linux_askpass_main_emits_password_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDialog:
        def exec(self) -> int:
            return int(askpass_dialog_module.QtWidgets.QDialog.DialogCode.Accepted)

        def get_password(self) -> str:
            return "super-secret"

    monkeypatch.setattr(
        askpass_dialog_module.QtWidgets.QApplication,
        "instance",
        lambda: object(),
    )
    monkeypatch.setattr(askpass_dialog_module, "LinuxAskpassDialog", _FakeDialog)
    out = io.StringIO()
    monkeypatch.setattr(askpass_dialog_module.sys, "stdout", out)

    assert askpass_dialog_module.main() == 0
    assert out.getvalue() == "super-secret\n"


@pytest.mark.e2e
def test_linux_askpass_main_returns_error_on_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeDialog:
        def exec(self) -> int:
            return int(askpass_dialog_module.QtWidgets.QDialog.DialogCode.Rejected)

        def get_password(self) -> str:
            return ""

    monkeypatch.setattr(
        askpass_dialog_module.QtWidgets.QApplication,
        "instance",
        lambda: object(),
    )
    monkeypatch.setattr(askpass_dialog_module, "LinuxAskpassDialog", _FakeDialog)
    monkeypatch.setattr(askpass_dialog_module.sys, "stdout", io.StringIO())

    assert askpass_dialog_module.main() == 1
