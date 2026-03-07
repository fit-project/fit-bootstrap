from __future__ import annotations

import pytest

from fit_bootstrap import connectivity as connectivity_module
from fit_bootstrap.signals import BootstrapSignal


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False


@pytest.mark.unit
def test_ensure_connectivity_available_returns_none_when_online(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        connectivity_module.socket,
        "create_connection",
        lambda *_args, **_kwargs: _FakeConnection(),
    )

    result = connectivity_module.ensure_connectivity_available()

    assert result is None


@pytest.mark.unit
def test_ensure_connectivity_available_returns_error_when_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        connectivity_module.socket,
        "create_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    monkeypatch.setattr(
        connectivity_module,
        "load_translations",
        lambda: {"BOOSTSTRAP_ERROR_CONNECTION_MESSAGE": "no internet"},
    )

    result = connectivity_module.ensure_connectivity_available()

    assert result is not None
    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR
    assert result.message == "no internet"
