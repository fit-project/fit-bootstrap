from __future__ import annotations

import json
from pathlib import Path

import pytest

from fit_bootstrap import lang as lang_module


@pytest.mark.unit
def test_load_translations_reads_requested_language() -> None:
    data = lang_module.load_translations("en")

    assert isinstance(data, dict)
    assert "ASKPASS_DIALOG_TITLE" in data


@pytest.mark.unit
def test_load_translations_falls_back_to_default_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "en.json").write_text(json.dumps({"HELLO": "world"}), encoding="utf-8")
    monkeypatch.setattr(lang_module, "LANG_DIR", tmp_path)
    monkeypatch.setattr(lang_module, "DEFAULT_LANG", "en")
    monkeypatch.setattr(lang_module, "get_system_lang", lambda: "xx")

    data = lang_module.load_translations()

    assert data == {"HELLO": "world"}
