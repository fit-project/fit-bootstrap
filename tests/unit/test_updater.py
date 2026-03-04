from __future__ import annotations

import json
import platform
from pathlib import Path
import subprocess

import pytest

from fit_bootstrap.caller import CallerProfile
from fit_bootstrap import updater as updater_module


class _FakeResponse:
    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self._chunks = chunks or []

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield from self._chunks


class _FakeCompletedProcess:
    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class _FakePopen:
    def __init__(self, pid: int = 4321) -> None:
        self.pid = pid


@pytest.mark.unit
def test_resolve_release_asset_returns_matching_macos_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(updater_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        updater_module,
        "get_latest_release_payload",
        lambda _repo: {
            "tag_name": "v1.2.3",
            "assets": [
                {
                    "name": "pluto-desktop-1.2.3-macos-arm64.dmg",
                    "browser_download_url": "https://example.test/pluto.dmg",
                    "content_type": "application/x-apple-diskimage",
                }
            ],
        },
    )

    asset = updater_module.resolve_release_asset(CallerProfile.FIT_WEB)

    assert asset is not None
    assert asset.repo == "fit-web"
    assert asset.version == "1.2.3"
    assert asset.name == "pluto-desktop-1.2.3-macos-arm64.dmg"
    assert asset.download_url == "https://example.test/pluto.dmg"


@pytest.mark.unit
def test_resolve_release_asset_returns_none_without_matching_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(updater_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        updater_module,
        "get_latest_release_payload",
        lambda _repo: {
            "tag_name": "v1.2.3",
            "assets": [
                {
                    "name": "pluto-desktop-1.2.3-macos-x86_64.dmg",
                    "browser_download_url": "https://example.test/pluto.dmg",
                }
            ],
        },
    )

    asset = updater_module.resolve_release_asset(CallerProfile.FIT)

    assert asset is None


@pytest.mark.unit
def test_resolve_release_asset_returns_none_when_latest_release_lookup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(updater_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")

    def _raise(_repo: str):
        raise updater_module.requests.RequestException("boom")

    monkeypatch.setattr(updater_module, "get_latest_release_payload", _raise)

    asset = updater_module.resolve_release_asset(CallerProfile.FIT_WEB)

    assert asset is None


@pytest.mark.unit
def test_get_available_update_returns_asset_when_remote_is_newer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        updater_module,
        "resolve_release_asset",
        lambda _caller: updater_module.ReleaseAsset(
            repo="fit-web",
            app_name="FIT Web",
            version="1.2.3",
            name="pluto-desktop-1.2.3-macos-arm64.dmg",
            download_url="https://example.test/pluto.dmg",
        ),
    )
    monkeypatch.setattr(updater_module, "get_local_version", lambda: "1.0.0")

    update = updater_module.get_available_update(CallerProfile.FIT_WEB)

    assert update is not None
    assert update.version == "1.2.3"


@pytest.mark.unit
def test_get_available_update_returns_none_when_remote_is_not_newer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        updater_module,
        "resolve_release_asset",
        lambda _caller: updater_module.ReleaseAsset(
            repo="fit-web",
            app_name="FIT Web",
            version="1.2.3",
            name="pluto-desktop-1.2.3-macos-arm64.dmg",
            download_url="https://example.test/pluto.dmg",
        ),
    )
    monkeypatch.setattr(updater_module, "get_local_version", lambda: "1.2.3")

    update = updater_module.get_available_update(CallerProfile.FIT_WEB)

    assert update is None


@pytest.mark.unit
def test_run_updater_serializes_asset_and_parses_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeCompletedProcess("updated\n")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    asset = updater_module.ReleaseAsset(
        repo="fit-web",
        app_name="FIT Web",
        version="1.2.3",
        name="pluto-desktop-1.2.3-macos-arm64.dmg",
        download_url="https://example.test/pluto.dmg",
    )

    result = updater_module.run_updater(asset)

    assert result.outcome == updater_module.UpdaterOutcome.UPDATED
    env = captured["kwargs"]["env"]  # type: ignore[index]
    assert env["FIT_UPDATE_DIALOG"] == "1"  # type: ignore[index]
    assert env["FIT_UPDATE_VERSION"] == "1.2.3"  # type: ignore[index]
    assert env["FIT_UPDATE_DOWNLOAD_URL"] == "https://example.test/pluto.dmg"  # type: ignore[index]


@pytest.mark.unit
def test_run_updater_returns_error_for_unexpected_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: _FakeCompletedProcess("wat\n", returncode=1),
    )
    asset = updater_module.ReleaseAsset(
        repo="fit-web",
        app_name="FIT Web",
        version="1.2.3",
        name="pluto-desktop-1.2.3-macos-arm64.dmg",
        download_url="https://example.test/pluto.dmg",
    )

    result = updater_module.run_updater(asset)

    assert result.outcome == updater_module.UpdaterOutcome.ERROR


@pytest.mark.unit
def test_launch_external_helper_creates_workspace_and_starts_script(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("FIT_USER_APP_PATH", str(tmp_path / "FIT"))
    monkeypatch.setenv("FIT_LOG_APP_PATH", str(tmp_path / "FIT" / "logs"))
    monkeypatch.setattr(updater_module, "get_platform", lambda: "macos")
    monkeypatch.setattr(
        updater_module,
        "_current_app_bundle_path",
        lambda: Path("/Applications/FitWeb.app"),
    )
    captured: dict[str, object] = {}

    def _fake_popen(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakePopen()

    monkeypatch.setattr(subprocess, "Popen", _fake_popen)
    asset = updater_module.ReleaseAsset(
        repo="fit-web",
        app_name="FIT Web",
        version="1.2.3",
        name="pluto-desktop-1.2.3-macos-arm64.dmg",
        download_url="https://example.test/pluto.dmg",
    )
    downloaded_path = tmp_path / "FIT" / "downloads" / asset.name
    downloaded_path.parent.mkdir(parents=True, exist_ok=True)
    downloaded_path.write_bytes(b"x")

    updater_module.launch_external_helper(asset, downloaded_path)

    helper_dir = tmp_path / "FIT" / "update-helper"
    manifest_path = helper_dir / "update-manifest.json"
    script_path = helper_dir / "install_update_macos.sh"
    log_path = tmp_path / "FIT" / "logs" / "update-helper.log"
    assert manifest_path.exists()
    assert script_path.exists()
    assert log_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["app_bundle_path"] == "/Applications/FitWeb.app"
    assert manifest["downloaded_package_path"] == str(downloaded_path)

    args = captured["args"][0]  # type: ignore[index]
    assert args == ["/bin/sh", str(script_path)]
    kwargs = captured["kwargs"]  # type: ignore[assignment]
    assert kwargs["start_new_session"] is True  # type: ignore[index]
    assert kwargs["stdout"].name == str(log_path)  # type: ignore[index]


@pytest.mark.unit
def test_default_download_path_uses_local_downloads_dir_in_develop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIT_USER_APP_PATH", "/tmp/workspace")

    path = updater_module._default_download_path("update.dmg")

    assert path == Path("/tmp/workspace/downloads/update.dmg")


@pytest.mark.unit
def test_download_release_asset_writes_target_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        updater_module,
        "requests",
        type(
            "_Requests",
            (),
            {
                "get": staticmethod(
                    lambda *_args, **_kwargs: _FakeResponse([b"abc", b"def"])
                )
            },
        ),
    )
    asset = updater_module.ReleaseAsset(
        repo="fit-web",
        app_name="FIT Web",
        version="1.2.3",
        name="pluto-desktop-1.2.3-macos-arm64.dmg",
        download_url="https://example.test/pluto.dmg",
    )

    target = updater_module.download_release_asset(asset, tmp_path / "update.dmg")

    assert target == tmp_path / "update.dmg"
    assert target.read_bytes() == b"abcdef"


@pytest.mark.unit
def test_current_app_bundle_path_returns_none_for_non_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updater_module.sys, "executable", "/usr/bin/python3")

    path = updater_module._current_app_bundle_path()

    assert path is None


@pytest.mark.unit
def test_resolved_target_app_bundle_path_prefers_explicit_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIT_UPDATE_TARGET_APP", "/Applications/FitWeb.app")
    monkeypatch.setattr(updater_module, "_current_app_bundle_path", lambda: None)

    path = updater_module._resolved_target_app_bundle_path()

    assert path == Path("/Applications/FitWeb.app")
