from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping

from .constants import (
    ENV_APP_NAME,
    ENV_ASSET_NAME,
    ENV_CONTENT_TYPE,
    ENV_DOWNLOAD_URL,
    ENV_REPO,
    ENV_VERSION,
    UPDATER_DIALOG_ENV,
)
from .models import ReleaseAsset, UpdaterOutcome, UpdaterResult


def dialog_command(*, sys_executable: str, is_frozen: bool, main_file: str | None) -> list[str]:
    if is_frozen:
        return [sys_executable]
    if isinstance(main_file, str):
        return [sys_executable, str(Path(main_file).resolve())]
    return [sys_executable, "main.py"]


def serialize_asset(asset: ReleaseAsset) -> dict[str, str]:
    env = {
        ENV_APP_NAME: asset.app_name,
        ENV_REPO: asset.repo,
        ENV_VERSION: asset.version,
        ENV_ASSET_NAME: asset.name,
        ENV_DOWNLOAD_URL: asset.download_url,
    }
    if asset.content_type is not None:
        env[ENV_CONTENT_TYPE] = asset.content_type
    return env


def deserialize_asset_from_env(
    env: Mapping[str, str | None],
) -> ReleaseAsset | None:
    repo = env.get(ENV_REPO)
    app_name = env.get(ENV_APP_NAME)
    version = env.get(ENV_VERSION)
    name = env.get(ENV_ASSET_NAME)
    download_url = env.get(ENV_DOWNLOAD_URL)
    if not isinstance(repo, str) or not repo:
        return None
    if not isinstance(app_name, str) or not app_name:
        return None
    if not isinstance(version, str) or not version:
        return None
    if not isinstance(name, str) or not name:
        return None
    if not isinstance(download_url, str) or not download_url:
        return None
    content_type = env.get(ENV_CONTENT_TYPE)
    return ReleaseAsset(
        repo=repo,
        app_name=app_name,
        version=version,
        name=name,
        download_url=download_url,
        content_type=content_type,
    )


def parse_updater_outcome(value: str) -> UpdaterOutcome | None:
    try:
        return UpdaterOutcome(value)
    except ValueError:
        return None


def run_updater(
    asset: ReleaseAsset,
    *,
    env_base: Mapping[str, str],
    dialog_command_fn,
    serialize_asset_fn,
    subprocess_run_fn,
    parse_updater_outcome_fn,
    debug_fn,
    log_context: str,
) -> UpdaterResult:
    env = dict(env_base)
    env[UPDATER_DIALOG_ENV] = "1"
    env.update(serialize_asset_fn(asset))
    process = subprocess_run_fn(
        dialog_command_fn(),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    outcome_text = (process.stdout or "").strip()
    detail_text = (process.stderr or "").strip() or None
    outcome = parse_updater_outcome_fn(outcome_text)
    if outcome is None:
        debug_fn(
            f"⚠️ updater dialog returned unexpected output rc={process.returncode} stdout={outcome_text!r}",
            context=log_context,
        )
        return UpdaterResult(UpdaterOutcome.ERROR, detail_text)
    return UpdaterResult(outcome=outcome, detail=detail_text)


def current_dialog_command() -> list[str]:
    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    return dialog_command(
        sys_executable=sys.executable,
        is_frozen=getattr(sys, "frozen", False),
        main_file=main_file if isinstance(main_file, str) else None,
    )


def env_dict() -> dict[str, str]:
    return dict(os.environ)


def subprocess_run(*args, **kwargs):
    return subprocess.run(*args, **kwargs)
