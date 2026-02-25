from __future__ import annotations

from pathlib import Path

import pytest

from fit_bootstrap import app_lock as app_lock_module
from fit_bootstrap.constants import FIT_USER_APP_PATH


@pytest.mark.integration
def test_app_lock_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(FIT_USER_APP_PATH, str(tmp_path))

    assert app_lock_module.acquire_app_lock() is True
    assert app_lock_module.is_app_locked() is True

    app_lock_module.release_app_lock()

    assert app_lock_module.is_app_locked() is False
