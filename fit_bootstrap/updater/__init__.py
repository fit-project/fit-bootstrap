"""Bootstrap-specific update discovery, GUI handoff, and asset download helpers."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]
from fit_common.core import debug, get_platform
from fit_common.core.versions import get_latest_release_payload, get_local_version

from . import assets as _assets
from . import install as _install
from . import process as _process
from . import ui as _ui
from . import versioning as _versioning
from .constants import (
    DISPLAY_NAME_BY_CALLER,
    ENV_APP_NAME,
    ENV_ASSET_NAME,
    ENV_CONTENT_TYPE,
    ENV_DOWNLOAD_URL,
    ENV_REPO,
    ENV_TARGET_APP,
    ENV_VERSION,
    LOG_CONTEXT,
    REPO_BY_CALLER,
)
from .models import ReleaseAsset, UpdaterOutcome, UpdaterResult


def get_available_update(caller) -> ReleaseAsset | None:
    asset = resolve_release_asset(caller)
    if asset is None:
        return None
    if not _is_newer_than_local(asset.version):
        return None
    return asset


def resolve_release_asset(caller) -> ReleaseAsset | None:
    return _assets.resolve_release_asset(
        caller,
        repo_by_caller=REPO_BY_CALLER,
        display_name_by_caller=DISPLAY_NAME_BY_CALLER,
        get_latest_release_payload_fn=get_latest_release_payload,
        request_exception_cls=requests.RequestException,
        debug_fn=debug,
        log_context=LOG_CONTEXT,
        extract_version_from_tag_fn=_extract_version_from_tag,
        normalize_version_for_compare_fn=_normalize_version_for_compare,
        find_matching_asset_fn=_find_matching_asset,
    )


def run_updater(asset: ReleaseAsset) -> UpdaterResult:
    return _process.run_updater(
        asset,
        env_base=os.environ,
        dialog_command_fn=_dialog_command,
        serialize_asset_fn=_serialize_asset,
        subprocess_run_fn=subprocess.run,
        parse_updater_outcome_fn=_parse_updater_outcome,
        debug_fn=debug,
        log_context=LOG_CONTEXT,
    )


def download_release_asset(
    asset: ReleaseAsset,
    destination: str | Path | None = None,
) -> Path:
    return _install.download_release_asset(
        asset,
        requests_module=requests,
        destination=destination,
    )


def main() -> int:
    asset = _deserialize_asset_from_env()
    return _ui.run_dialog(
        asset=asset,
        parse_updater_outcome_fn=_parse_updater_outcome,
        download_release_asset_fn=download_release_asset,
        launch_external_helper_fn=launch_external_helper,
    )


def _dialog_command() -> list[str]:
    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    return _process.dialog_command(
        sys_executable=sys.executable,
        is_frozen=getattr(sys, "frozen", False),
        main_file=main_file if isinstance(main_file, str) else None,
    )


def _serialize_asset(asset: ReleaseAsset) -> dict[str, str]:
    return _process.serialize_asset(asset)


def _deserialize_asset_from_env() -> ReleaseAsset | None:
    return _process.deserialize_asset_from_env(os.environ)


def _parse_updater_outcome(value: str) -> UpdaterOutcome | None:
    return _process.parse_updater_outcome(value)


def _find_matching_asset(
    payload: dict[str, Any],
    version: str,
) -> dict[str, Any] | None:
    return _assets.find_matching_asset(
        payload,
        version,
        get_platform_fn=get_platform,
        machine_fn=platform.machine,
        normalized_arch_fn=_normalized_arch,
        expected_suffix_fn=_expected_suffix,
    )


def _extract_version_from_tag(tag_name: str) -> str:
    return _versioning.extract_version_from_tag(tag_name)


def _normalize_version_for_compare(value: str) -> str:
    return _versioning.normalize_version_for_compare(value)


def _expected_suffix(current_platform: str) -> str | None:
    return _versioning.expected_suffix(current_platform)


def _default_download_path(filename: str) -> Path:
    return _install.default_download_path(filename)


def launch_external_helper(asset: ReleaseAsset, downloaded_path: str | Path) -> None:
    bundle_path = _resolved_target_app_bundle_path()
    if bundle_path is None:
        raise RuntimeError(
            "target app bundle path is not available; set FIT_UPDATE_TARGET_APP when running outside the app bundle"
        )
    if get_platform() != "macos":
        raise RuntimeError("external update helper is implemented only for macOS")
    return _install.launch_external_helper(
        asset,
        downloaded_path,
        bundle_path=bundle_path,
        get_platform_fn=get_platform,
    )


def _helper_workspace_path() -> Path:
    return _install.helper_workspace_path()


def _helper_log_path() -> Path:
    return _install.helper_log_path()


def _current_app_bundle_path() -> Path | None:
    return _install.current_app_bundle_path()


def _resolved_target_app_bundle_path() -> Path | None:
    explicit_target = os.environ.get(ENV_TARGET_APP)
    if explicit_target:
        return Path(explicit_target).expanduser().resolve()
    return _current_app_bundle_path()


def _is_newer_than_local(remote_version: str) -> bool:
    return _versioning.is_newer_than_local(
        remote_version,
        get_local_version_fn=get_local_version,
        normalize_version_for_compare_fn=_normalize_version_for_compare,
    )


def _normalized_arch(machine: str) -> str:
    return _versioning.normalized_arch(machine)


__all__ = [
    "ReleaseAsset",
    "UpdaterOutcome",
    "UpdaterResult",
    "get_available_update",
    "resolve_release_asset",
    "run_updater",
    "download_release_asset",
    "launch_external_helper",
    "main",
    "_dialog_command",
    "_serialize_asset",
    "_deserialize_asset_from_env",
    "_parse_updater_outcome",
    "_find_matching_asset",
    "_extract_version_from_tag",
    "_normalize_version_for_compare",
    "_expected_suffix",
    "_default_download_path",
    "_helper_workspace_path",
    "_helper_log_path",
    "_current_app_bundle_path",
    "_resolved_target_app_bundle_path",
    "_is_newer_than_local",
    "_normalized_arch",
    "ENV_APP_NAME",
    "ENV_REPO",
    "ENV_VERSION",
    "ENV_ASSET_NAME",
    "ENV_DOWNLOAD_URL",
    "ENV_CONTENT_TYPE",
]
