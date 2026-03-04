from __future__ import annotations

import pytest

from fit_bootstrap.caller import CallerProfile
from fit_bootstrap.release_version import ensure_latest_release_version
from fit_bootstrap.signals import BootstrapSignal
from fit_bootstrap.updater import ReleaseAsset, UpdaterOutcome, UpdaterResult


def _sample_asset() -> ReleaseAsset:
    return ReleaseAsset(
        repo="fit-web",
        app_name="FIT Web",
        version="1.1.0",
        name="pluto-desktop-1.1.0-macos-arm64.dmg",
        download_url="https://example.test/pluto.dmg",
    )


@pytest.mark.unit
def test_ensure_latest_release_version_returns_none_without_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fit_bootstrap.release_version.get_available_update",
        lambda _caller: None,
    )

    result = ensure_latest_release_version(CallerProfile.FIT_WEB)

    assert result is None


@pytest.mark.unit
def test_ensure_latest_release_version_returns_none_when_user_declines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fit_bootstrap.release_version.get_available_update",
        lambda _caller: _sample_asset(),
    )
    monkeypatch.setattr(
        "fit_bootstrap.release_version.run_updater",
        lambda _asset: UpdaterResult(UpdaterOutcome.DECLINED),
    )

    result = ensure_latest_release_version(CallerProfile.FIT_WEB)

    assert result is None


@pytest.mark.unit
def test_ensure_latest_release_version_returns_none_when_helper_fails_to_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fit_bootstrap.release_version.get_available_update",
        lambda _caller: _sample_asset(),
    )
    monkeypatch.setattr(
        "fit_bootstrap.release_version.run_updater",
        lambda _asset: UpdaterResult(UpdaterOutcome.HELPER_FAILED_CONTINUE),
    )

    result = ensure_latest_release_version(CallerProfile.FIT_WEB)

    assert result is None


@pytest.mark.unit
def test_ensure_latest_release_version_returns_ok_when_update_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fit_bootstrap.release_version.get_available_update",
        lambda _caller: _sample_asset(),
    )
    monkeypatch.setattr(
        "fit_bootstrap.release_version.run_updater",
        lambda _asset: UpdaterResult(UpdaterOutcome.UPDATED),
    )

    result = ensure_latest_release_version(CallerProfile.FIT_WEB)

    assert result is not None
    assert result.code == 0
    assert result.signal == BootstrapSignal.OK


@pytest.mark.unit
def test_ensure_latest_release_version_returns_error_on_unexpected_updater_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fit_bootstrap.release_version.get_available_update",
        lambda _caller: _sample_asset(),
    )
    monkeypatch.setattr(
        "fit_bootstrap.release_version.run_updater",
        lambda _asset: UpdaterResult(UpdaterOutcome.ERROR),
    )

    result = ensure_latest_release_version(CallerProfile.FIT_WEB)

    assert result is not None
    assert result.code == 1
    assert result.signal == BootstrapSignal.ERROR
