from __future__ import annotations

from types import SimpleNamespace

import pytest

from fit_bootstrap import privilege as privilege_module


@pytest.mark.unit
def test_ensure_root_or_relaunch_returns_zero_when_already_elevated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(privilege_module, "_is_elevated", lambda: True)
    called: list[str] = []
    monkeypatch.setattr(privilege_module, "_relaunch_macos", lambda *_a, **_k: called.append("mac") or 1)

    rc = privilege_module.ensure_root_or_relaunch(["main.py"])

    assert rc == 0
    assert called == []


@pytest.mark.unit
def test_ensure_root_or_relaunch_dispatches_by_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(privilege_module, "_is_elevated", lambda: False)
    monkeypatch.setattr(privilege_module, "_relaunch_macos", lambda *_a, **_k: 11)
    monkeypatch.setattr(privilege_module, "_relaunch_linux", lambda *_a, **_k: 22)
    monkeypatch.setattr(privilege_module, "_relaunch_windows", lambda *_a, **_k: 33)

    monkeypatch.setattr(privilege_module, "get_platform", lambda: "macos")
    assert privilege_module.ensure_root_or_relaunch(["x.py"]) == 11

    monkeypatch.setattr(privilege_module, "get_platform", lambda: "lin")
    assert privilege_module.ensure_root_or_relaunch(["x.py"]) == 22

    monkeypatch.setattr(privilege_module, "get_platform", lambda: "win")
    assert privilege_module.ensure_root_or_relaunch(["x.py"]) == 33

    monkeypatch.setattr(privilege_module, "get_platform", lambda: "other")
    assert privilege_module.ensure_root_or_relaunch(["x.py"]) == 1


@pytest.mark.unit
def test_build_command_includes_env_and_quotes() -> None:
    cmd = privilege_module._build_command(
        ["script.py", "--name", "A B"],
        env_overrides={"KEY": "value with space"},
    )

    assert "env 'KEY=value with space'" in cmd
    assert "script.py --name 'A B'" in cmd


@pytest.mark.unit
def test_relaunch_linux_calls_sudo_with_shell_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_call(argv):
        captured["argv"] = argv
        return 7

    monkeypatch.setattr(privilege_module.subprocess, "call", _fake_call)

    rc = privilege_module._relaunch_linux(["main.py"], env_overrides={"A": "B"})

    assert rc == 7
    assert captured["argv"][0:3] == ["sudo", "sh", "-c"]  # type: ignore[index]


@pytest.mark.unit
def test_relaunch_macos_uses_askpass_when_script_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(privilege_module.Path, "exists", lambda _self: True)
    monkeypatch.setenv("FIT_BOOTSTRAP_DEBUG", "1")
    monkeypatch.setenv("FIT_ASKPASS_LOG", "/tmp/askpass.log")

    captured: dict[str, object] = {}

    def _fake_call(argv, env):
        captured["argv"] = argv
        captured["env"] = env
        return 5

    monkeypatch.setattr(privilege_module.subprocess, "call", _fake_call)

    rc = privilege_module._relaunch_macos(["main.py"], env_overrides={"A": "B"})

    assert rc == 5
    call_argv = captured["argv"]  # type: ignore[assignment]
    assert call_argv[0:2] == ["sudo", "-A"]  # type: ignore[index]
    call_env = captured["env"]  # type: ignore[assignment]
    assert call_env["SUDO_ASKPASS"]  # type: ignore[index]
    assert call_env["FIT_ASKPASS_FORM_TYPE_ARGUMENT"] == "--launch-gui"  # type: ignore[index]
    assert call_env["A"] == "B"  # type: ignore[index]


@pytest.mark.unit
def test_relaunch_macos_returns_one_without_tty_and_without_askpass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(privilege_module.Path, "exists", lambda _self: False)
    monkeypatch.setattr(privilege_module.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(privilege_module.sys, "stdout", SimpleNamespace(isatty=lambda: False))

    assert privilege_module._relaunch_macos(["main.py"]) == 1
