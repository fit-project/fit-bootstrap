from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from fit_common.core import debug, get_platform

from fit_bootstrap.constants import FIT_LOG_APP_PATH, FIT_USER_APP_PATH

from .constants import ENV_TARGET_APP, LOG_CONTEXT
from .helpers import render_helper_script
from .models import ReleaseAsset


def default_download_path(filename: str) -> Path:
    base_dir = Path(os.environ.get("FIT_USER_APP_PATH", str(Path.home())))
    return base_dir / "downloads" / filename


def download_release_asset(
    asset: ReleaseAsset,
    *,
    requests_module,
    destination: str | Path | None = None,
) -> Path:
    target = Path(destination) if destination is not None else default_download_path(asset.name)
    target.parent.mkdir(parents=True, exist_ok=True)

    response = requests_module.get(asset.download_url, stream=True, timeout=30)
    response.raise_for_status()
    with target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    return target


def helper_workspace_path() -> Path:
    return Path(os.environ.get(FIT_USER_APP_PATH, str(Path.home()))) / "update-helper"


def helper_log_path() -> Path:
    base_logs = Path(
        os.environ.get(
            FIT_LOG_APP_PATH,
            str(Path(os.environ.get(FIT_USER_APP_PATH, str(Path.home()))) / "logs"),
        )
    )
    return base_logs / "update-helper.log"


def current_app_bundle_path(*, platform_name: str | None = None) -> Path | None:
    current_platform = platform_name or get_platform()
    executable = Path(sys.executable).resolve()
    if current_platform == "macos":
        for candidate in (executable, *executable.parents):
            if candidate.name.endswith(".app"):
                return candidate
        return None
    return executable if executable.exists() else None


def resolved_target_app_bundle_path(*, platform_name: str | None = None) -> Path | None:
    explicit_target = os.environ.get(ENV_TARGET_APP)
    if explicit_target:
        return Path(explicit_target).expanduser().resolve()
    return current_app_bundle_path(platform_name=platform_name)


def _helper_script_name_for_platform(current_platform: str) -> str:
    return {
        "macos": "install_update_macos.sh",
        "lin": "install_update_linux.sh",
        "win": "install_update_windows.cmd",
    }.get(current_platform, f"install_update_{current_platform}.sh")


def _helper_command_for_platform(current_platform: str, script_path: Path) -> list[str]:
    if current_platform == "win":
        return ["cmd.exe", "/c", str(script_path)]
    return ["/bin/sh", str(script_path)]


def read_mitmproxy_pid() -> int | None:
    base_path = os.environ.get(FIT_USER_APP_PATH)
    if not base_path:
        return None
    pid_path = Path(base_path) / "mitmproxy" / "mitmproxy.pid"
    try:
        return int(pid_path.read_text().strip())
    except (OSError, ValueError):
        return None


def launch_external_helper(
    asset: ReleaseAsset,
    downloaded_path: str | Path,
    *,
    bundle_path: Path | None = None,
    get_platform_fn=get_platform,
) -> None:
    current_platform = get_platform_fn()
    helper_dir = helper_workspace_path()
    helper_dir.mkdir(parents=True, exist_ok=True)
    log_path = helper_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = helper_dir / "update-manifest.json"
    script_path = helper_dir / _helper_script_name_for_platform(current_platform)

    if bundle_path is None:
        bundle_path = resolved_target_app_bundle_path(platform_name=current_platform)
    if bundle_path is None:
        raise RuntimeError(
            "target app bundle path is not available; set FIT_UPDATE_TARGET_APP when running outside the app bundle"
        )

    manifest = {
        "app_name": asset.app_name,
        "repo": asset.repo,
        "version": asset.version,
        "asset_name": asset.name,
        "downloaded_package_path": str(Path(downloaded_path)),
        "app_bundle_path": str(bundle_path),
        "log_path": str(log_path),
        "updater_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "mitm_pid": read_mitmproxy_pid() or "",
        "platform": current_platform,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    script_path.write_text(
        render_helper_script(
            platform=current_platform,
            manifest=manifest,
            script_path=script_path,
            manifest_path=manifest_path,
            helper_dir=helper_dir,
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    debug(
        f"Launching external update helper {script_path} for {downloaded_path}",
        context=LOG_CONTEXT,
    )
    with log_path.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            _helper_command_for_platform(current_platform, script_path),
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    debug(
        f"External update helper started with pid={process.pid}",
        context=LOG_CONTEXT,
    )
