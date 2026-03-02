from __future__ import annotations

import os
from pathlib import Path

import pytest

from fit_bootstrap import screen_recorder as screen_recorder_module


@pytest.mark.unit
def test_ensure_screen_recoder_available_returns_existing_env_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    existing = tmp_path / "fit-screen-recoder"
    existing.write_text("ok")
    monkeypatch.setenv("FIT_SCREEN_RECODER_PATH", str(existing))

    resolved = screen_recorder_module.ensure_screen_recoder_available()

    assert resolved == existing


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

    resolved = screen_recorder_module.ensure_screen_recoder_available()

    assert resolved == binary
    assert os.environ["FIT_SCREEN_RECODER_PATH"] == str(binary)


@pytest.mark.unit
def test_ensure_screen_recoder_available_returns_none_when_bundle_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("FIT_SCREEN_RECODER_PATH", raising=False)
    monkeypatch.setattr(screen_recorder_module, "get_platform", lambda: "lin")
    monkeypatch.setattr(screen_recorder_module, "_bundle_base_path", lambda: tmp_path)

    resolved = screen_recorder_module.ensure_screen_recoder_available()

    assert resolved is None
