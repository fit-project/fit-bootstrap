from __future__ import annotations

import platform
from typing import Any

from fit_bootstrap.caller import CallerProfile

from .models import ReleaseAsset


def find_matching_asset(
    payload: dict[str, Any],
    version: str,
    *,
    get_platform_fn,
    machine_fn,
    normalized_arch_fn,
    expected_suffix_fn,
) -> dict[str, Any] | None:
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        return None

    current_platform = get_platform_fn()
    arch = normalized_arch_fn(machine_fn())
    suffix = expected_suffix_fn(current_platform)
    contains = [version, current_platform, arch]

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        if not isinstance(name, str):
            continue
        lowered = name.lower()
        if suffix and not lowered.endswith(suffix):
            continue
        if all(token and token in lowered for token in contains):
            return asset
    return None


def resolve_release_asset(
    caller: CallerProfile,
    *,
    repo_by_caller,
    display_name_by_caller,
    get_latest_release_payload_fn,
    request_exception_cls,
    debug_fn,
    log_context: str,
    extract_version_from_tag_fn,
    normalize_version_for_compare_fn,
    find_matching_asset_fn,
) -> ReleaseAsset | None:
    repo = repo_by_caller.get(caller)

    if repo is None:
        return None

    try:
        payload = get_latest_release_payload_fn(repo)
    except request_exception_cls as exc:
        debug_fn(
            f"⚠️ latest release lookup failed for repo={repo}: {exc}",
            context=log_context,
        )
        payload = {}

    version = extract_version_from_tag_fn(str(payload.get("tag_name", "")))
    if not version:
        return None
    if not normalize_version_for_compare_fn(version):
        return None

    asset = find_matching_asset_fn(payload, version)
    if asset is None:
        normalized_version = normalize_version_for_compare_fn(version)
        if normalized_version and normalized_version != version:
            asset = find_matching_asset_fn(payload, normalized_version)

    if asset is None:
        return None

    name = asset.get("name")
    download_url = asset.get("browser_download_url")
    if not isinstance(name, str) or not isinstance(download_url, str):
        return None

    content_type = asset.get("content_type")
    if not isinstance(content_type, str):
        content_type = None

    return ReleaseAsset(
        repo=repo,
        app_name=display_name_by_caller.get(caller, repo),
        version=version,
        name=name,
        download_url=download_url,
        content_type=content_type,
    )


def machine() -> str:
    return platform.machine()
