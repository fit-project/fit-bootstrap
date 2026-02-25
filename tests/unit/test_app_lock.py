from __future__ import annotations

from pathlib import Path

import pytest

from fit_bootstrap import app_lock as app_lock_module
from fit_bootstrap.constants import FIT_USER_APP_PATH


@pytest.mark.unit
def test_owner_from_path_extracts_user() -> None:
    assert app_lock_module._owner_from_path(Path("/Users/alice/.fit/app.lock")) == "alice"
    assert app_lock_module._owner_from_path(Path("/tmp/app.lock")) is None


@pytest.mark.unit
def test_acquire_app_lock_creates_lock_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    monkeypatch.setattr(app_lock_module.os, "getpid", lambda: 4321)
    calls: list[Path] = []
    monkeypatch.setattr(app_lock_module, "_relax_lock_permissions", lambda p: calls.append(p))

    acquired = app_lock_module.acquire_app_lock()
    lock_path = tmp_path / app_lock_module.APP_LOCK_NAME

    assert acquired is True
    assert lock_path.exists()
    assert lock_path.read_text() == "4321"
    assert calls == [lock_path]


@pytest.mark.unit
def test_acquire_app_lock_returns_false_when_live_pid_holds_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    lock_path = tmp_path / app_lock_module.APP_LOCK_NAME
    lock_path.write_text("9999")
    monkeypatch.setattr(app_lock_module, "_pid_alive", lambda pid: pid == 9999)

    assert app_lock_module.acquire_app_lock() is False


@pytest.mark.unit
def test_acquire_app_lock_replaces_stale_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    lock_path = tmp_path / app_lock_module.APP_LOCK_NAME
    lock_path.write_text("9999")
    monkeypatch.setattr(app_lock_module.os, "getpid", lambda: 7777)
    monkeypatch.setattr(app_lock_module, "_pid_alive", lambda _pid: False)
    monkeypatch.setattr(app_lock_module, "_relax_lock_permissions", lambda _p: None)

    assert app_lock_module.acquire_app_lock() is True
    assert lock_path.read_text() == "7777"


@pytest.mark.unit
def test_is_app_locked_handles_missing_and_invalid_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    lock_path = tmp_path / app_lock_module.APP_LOCK_NAME

    assert app_lock_module.is_app_locked() is False

    lock_path.write_text("")
    assert app_lock_module.is_app_locked() is False

    lock_path.write_text("1234")
    monkeypatch.setattr(app_lock_module, "_pid_alive", lambda pid: pid == 1234)
    assert app_lock_module.is_app_locked() is True


@pytest.mark.unit
def test_release_app_lock_removes_only_current_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))
    lock_path = tmp_path / app_lock_module.APP_LOCK_NAME
    lock_path.write_text("1111")
    monkeypatch.setattr(app_lock_module.os, "getpid", lambda: 2222)

    app_lock_module.release_app_lock()
    assert lock_path.exists()

    lock_path.write_text("2222")
    app_lock_module.release_app_lock()
    assert not lock_path.exists()
