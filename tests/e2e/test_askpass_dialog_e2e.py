from __future__ import annotations

import io

import pytest

from fit_bootstrap.macos import askpass_dialog as askpass_dialog_module


@pytest.mark.e2e
def test_askpass_main_emits_password_to_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeDialog:
        def __init__(self, _mode: str) -> None:
            pass

        def exec(self) -> int:
            return askpass_dialog_module.QDialog.Accepted

        def get_password(self) -> str:
            return "super-secret"

    monkeypatch.setattr(askpass_dialog_module, "QApplication", lambda _args: object())
    monkeypatch.setattr(askpass_dialog_module, "AskpassDialog", _FakeDialog)
    monkeypatch.setattr(askpass_dialog_module.sys, "argv", ["askpass_dialog.py"])
    out = io.StringIO()
    monkeypatch.setattr(askpass_dialog_module.sys, "stdout", out)

    rc = askpass_dialog_module.main()

    assert rc == 0
    assert out.getvalue() == "super-secret\n"


@pytest.mark.e2e
def test_askpass_main_returns_error_on_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeDialog:
        def __init__(self, _mode: str) -> None:
            pass

        def exec(self) -> int:
            return 0

        def get_password(self) -> str:
            return ""

    monkeypatch.setattr(askpass_dialog_module, "QApplication", lambda _args: object())
    monkeypatch.setattr(askpass_dialog_module, "AskpassDialog", _FakeDialog)
    monkeypatch.setattr(askpass_dialog_module.sys, "argv", ["askpass_dialog.py"])
    monkeypatch.setattr(askpass_dialog_module.sys, "stdout", io.StringIO())

    assert askpass_dialog_module.main() == 1
