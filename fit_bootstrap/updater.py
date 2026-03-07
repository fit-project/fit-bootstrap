"""Bootstrap-specific update discovery, GUI handoff, and asset download helpers."""

from __future__ import annotations

import json
import os
import platform
import shlex
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from html import escape
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]
from fit_common.core import debug, get_platform
from fit_common.core.versions import (
    extract_version,
    get_latest_release_payload,
    get_local_version,
)
from packaging.version import InvalidVersion, Version

from fit_bootstrap.caller import CallerProfile
from fit_bootstrap.constants import FIT_LOG_APP_PATH, FIT_USER_APP_PATH
from fit_bootstrap.lang import load_translations

_LOG_CONTEXT = "fit_bootstrap.updater"

_REPO_BY_CALLER = {
    CallerProfile.FIT: "fit",
    CallerProfile.FIT_WEB: "fit-web",
    CallerProfile.FIT_BOOTSTRAP: "fit-bootstrap",
}

_DISPLAY_NAME_BY_CALLER = {
    CallerProfile.FIT: "FIT",
    CallerProfile.FIT_WEB: "FIT Web",
    CallerProfile.FIT_BOOTSTRAP: "FIT Bootstrap",
}

_UPDATER_DIALOG_ENV = "FIT_UPDATE_DIALOG"
_ENV_APP_NAME = "FIT_UPDATE_APP_NAME"
_ENV_REPO = "FIT_UPDATE_REPO"
_ENV_VERSION = "FIT_UPDATE_VERSION"
_ENV_ASSET_NAME = "FIT_UPDATE_ASSET_NAME"
_ENV_DOWNLOAD_URL = "FIT_UPDATE_DOWNLOAD_URL"
_ENV_CONTENT_TYPE = "FIT_UPDATE_CONTENT_TYPE"
_ENV_TARGET_APP = "FIT_UPDATE_TARGET_APP"


@dataclass(frozen=True)
class ReleaseAsset:
    repo: str
    app_name: str
    version: str
    name: str
    download_url: str
    content_type: str | None = None


class UpdaterOutcome(str, Enum):
    DECLINED = "declined"
    UPDATED = "updated"
    DOWNLOAD_FAILED_CONTINUE = "download_failed_continue"
    HELPER_FAILED_CONTINUE = "helper_failed_continue"
    INSTALL_FAILED_ROLLBACK = "install_failed_rollback"
    ERROR = "error"


@dataclass(frozen=True)
class UpdaterResult:
    outcome: UpdaterOutcome
    detail: str | None = None


def get_available_update(caller: CallerProfile) -> ReleaseAsset | None:
    asset = resolve_release_asset(caller)
    if asset is None:
        return None
    if not _is_newer_than_local(asset.version):
        return None
    return asset


def resolve_release_asset(caller: CallerProfile) -> ReleaseAsset | None:
    repo = _REPO_BY_CALLER.get(caller)
    if repo is None:
        return None

    try:
        payload = get_latest_release_payload(repo)
    except requests.RequestException as exc:
        debug(
            f"⚠️ latest release lookup failed for repo={repo}: {exc}",
            context=_LOG_CONTEXT,
        )
        payload = {}
    version = extract_version(str(payload.get("tag_name", "")))
    if not version:
        return None

    asset = _find_matching_asset(payload, version)

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
        app_name=_DISPLAY_NAME_BY_CALLER.get(caller, repo),
        version=version,
        name=name,
        download_url=download_url,
        content_type=content_type,
    )


def run_updater(asset: ReleaseAsset) -> UpdaterResult:
    env = os.environ.copy()
    env[_UPDATER_DIALOG_ENV] = "1"
    env.update(_serialize_asset(asset))
    process = subprocess.run(
        _dialog_command(),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    outcome_text = (process.stdout or "").strip()
    detail_text = (process.stderr or "").strip() or None
    outcome = _parse_updater_outcome(outcome_text)
    if outcome is None:
        debug(
            f"⚠️ updater dialog returned unexpected output rc={process.returncode} stdout={outcome_text!r}",
            context=_LOG_CONTEXT,
        )
        return UpdaterResult(UpdaterOutcome.ERROR, detail_text)
    return UpdaterResult(outcome=outcome, detail=detail_text)


def download_release_asset(
    asset: ReleaseAsset,
    destination: str | Path | None = None,
) -> Path:
    target = (
        Path(destination)
        if destination is not None
        else _default_download_path(asset.name)
    )
    target.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(asset.download_url, stream=True, timeout=30)
    response.raise_for_status()
    with target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    return target


def main() -> int:
    try:
        from PySide6.QtCore import QObject, Qt, QThread, Signal
        from PySide6.QtWidgets import (
            QApplication,
            QDialog,
        )

        from fit_bootstrap.updater_ui import Ui_askpass_dialog
    except Exception as exc:
        sys.stderr.write(str(exc))
        sys.stderr.flush()
        sys.stdout.write(UpdaterOutcome.ERROR.value + "\n")
        sys.stdout.flush()
        return 1
    try:
        from fit_assets import resources  # noqa: F401
    except Exception:
        pass

    asset = _deserialize_asset_from_env()
    if asset is None:
        sys.stdout.write(UpdaterOutcome.ERROR.value + "\n")
        sys.stdout.flush()
        return 1

    class UpdateWorker(QObject):
        status_changed = Signal(str)
        download_ready = Signal(str)
        finished = Signal(str, str)

        def __init__(self, update_asset: ReleaseAsset) -> None:
            super().__init__()
            self._asset = update_asset

        def run(self) -> None:
            self.status_changed.emit(translations.get("UPDATER_STATUS_DOWNLOADING", ""))
            try:
                downloaded_path = download_release_asset(self._asset)
                debug(
                    f"Installing macOS update from {downloaded_path}",
                    context=_LOG_CONTEXT,
                )
            except Exception as exc:  # pragma: no cover - exercised via GUI workflow
                self.finished.emit(
                    UpdaterOutcome.DOWNLOAD_FAILED_CONTINUE.value,
                    str(exc),
                )
                return

            self.download_ready.emit(str(downloaded_path))
            self.status_changed.emit(translations.get("UPDATER_STATUS_INSTALLING", ""))
            try:
                launch_external_helper(self._asset, downloaded_path)
            except Exception as exc:  # pragma: no cover - exercised via GUI workflow
                self.finished.emit(
                    UpdaterOutcome.HELPER_FAILED_CONTINUE.value,
                    str(exc),
                )
                return

            self.finished.emit(UpdaterOutcome.UPDATED.value, "")

    class UpdateDialog(QDialog, Ui_askpass_dialog):
        def __init__(self, update_asset: ReleaseAsset) -> None:
            super().__init__()
            self.setupUi(self)
            self._asset = update_asset
            self._outcome = UpdaterOutcome.DECLINED
            self._detail: str | None = None
            self._thread: QThread | None = None
            self._worker: UpdateWorker | None = None

            # Match the frameless style used by other bootstrap dialogs.
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setWindowTitle(translations.get("UPDATER_DIALOG_TITLE", "Update"))
            self.title_right_info.setText(
                translations.get("UPDATER_DIALOG_TITLE", "Update")
            )
            heading = translations.get("UPDATER_DIALOG_HEADING", "").format(
                update_asset.app_name,
                update_asset.version,
            )
            description = translations.get("UPDATER_DIALOG_BODY", "").format(
                update_asset.name
            )
            self._body_message = (
                f"{escape(heading)}<br><br>{description}" if heading else description
            )
            self._set_status(translations.get("UPDATER_STATUS_WAITING", ""))

            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)

            self.cancel_button.setText(translations.get("UPDATER_SKIP_BUTTON", "Skip"))
            self.ok_button.setText(
                translations.get("UPDATER_INSTALL_BUTTON", "Install")
            )
            self.cancel_button.clicked.connect(self._decline_update)
            self.ok_button.clicked.connect(self._start_update)
            self.ok_button.setDefault(True)

        def result_value(self) -> UpdaterResult:
            return UpdaterResult(self._outcome, self._detail)

        def _set_status(self, status: str) -> None:
            self.message.setText(f"{self._body_message}<br><br><b>{escape(status)}</b>")

        def _set_completion_state(
            self,
            *,
            status_text: str,
            detail: str | None,
            close_handler: Any,
            status_is_html: bool = False,
        ) -> None:
            detail_html = ""
            if detail:
                escaped_detail = escape(detail).replace("\n", "<br>")
                detail_html = f"<br><br><small>{escaped_detail}</small>"
            rendered_status = status_text if status_is_html else escape(status_text)
            self.message.setText(
                f"{self._body_message}<br><br><b>{rendered_status}</b>{detail_html}"
            )
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
            self.cancel_button.hide()
            self.ok_button.show()
            self.ok_button.setEnabled(True)
            self.ok_button.setText(translations.get("OK_BUTTON", "OK"))
            self.ok_button.setDefault(True)
            try:
                self.ok_button.clicked.disconnect()
            except TypeError:
                pass
            self.ok_button.clicked.connect(close_handler)

        def _decline_update(self) -> None:
            self._outcome = UpdaterOutcome.DECLINED
            self.reject()

        def _start_update(self) -> None:
            if self._thread is not None and self._thread.isRunning():
                return
            self.cancel_button.setEnabled(False)
            try:
                self.cancel_button.clicked.disconnect(self._decline_update)
            except TypeError:
                pass
            self.ok_button.setEnabled(False)
            self.progress_bar.setRange(0, 0)
            self._set_status(translations.get("UPDATER_STATUS_STARTING", ""))

            self._thread = QThread(self)
            self._worker = UpdateWorker(self._asset)
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run)
            self._worker.status_changed.connect(self._set_status)
            self._worker.finished.connect(self._finish_update)
            self._worker.finished.connect(self._thread.quit)
            self._worker.finished.connect(self._worker.deleteLater)
            self._thread.finished.connect(self._thread.deleteLater)
            self._thread.start()

        def _show_download_path(self, downloaded_path: str) -> None:
            self._set_completion_state(
                status_text=escape(f"Downloaded package path:\n{downloaded_path}"),
                detail=None,
                close_handler=self.reject,
                status_is_html=True,
            )

        def _finish_update(self, outcome_text: str, detail: str) -> None:
            outcome = _parse_updater_outcome(outcome_text) or UpdaterOutcome.ERROR
            self._outcome = outcome
            self._detail = detail or None

            if outcome == UpdaterOutcome.UPDATED:
                self._set_completion_state(
                    status_text=translations.get("UPDATER_STATUS_UPDATED", ""),
                    detail=None,
                    close_handler=self.accept,
                    status_is_html=True,
                )
                return

            if outcome == UpdaterOutcome.DOWNLOAD_FAILED_CONTINUE:
                self._set_completion_state(
                    status_text=translations.get("UPDATER_STATUS_DOWNLOAD_FAILED", ""),
                    detail=detail,
                    close_handler=self.reject,
                    status_is_html=True,
                )
                return

            if outcome == UpdaterOutcome.HELPER_FAILED_CONTINUE:
                self._set_completion_state(
                    status_text=translations.get("UPDATER_STATUS_HELPER_FAILED", ""),
                    detail=detail,
                    close_handler=self.reject,
                    status_is_html=True,
                )
                return

            if outcome == UpdaterOutcome.INSTALL_FAILED_ROLLBACK:
                self._set_completion_state(
                    status_text=translations.get("UPDATER_STATUS_INSTALL_FAILED", ""),
                    detail=detail,
                    close_handler=self.reject,
                    status_is_html=True,
                )
                return

            self._set_completion_state(
                status_text=translations.get("UPDATER_STATUS_ERROR", ""),
                detail=detail,
                close_handler=self.reject,
                status_is_html=True,
            )

    translations = load_translations()
    if QApplication.instance() is None:
        QApplication(sys.argv)
    dialog = UpdateDialog(asset)
    dialog.exec()
    result = dialog.result_value()
    sys.stdout.write(result.outcome.value + "\n")
    sys.stdout.flush()
    if result.detail:
        sys.stderr.write(result.detail + "\n")
        sys.stderr.flush()
    return 0 if result.outcome != UpdaterOutcome.ERROR else 1


def _dialog_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]

    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    if isinstance(main_file, str):
        return [sys.executable, str(Path(main_file).resolve())]
    return [sys.executable, "main.py"]


def _serialize_asset(asset: ReleaseAsset) -> dict[str, str]:
    env = {
        _ENV_APP_NAME: asset.app_name,
        _ENV_REPO: asset.repo,
        _ENV_VERSION: asset.version,
        _ENV_ASSET_NAME: asset.name,
        _ENV_DOWNLOAD_URL: asset.download_url,
    }
    if asset.content_type is not None:
        env[_ENV_CONTENT_TYPE] = asset.content_type
    return env


def _deserialize_asset_from_env() -> ReleaseAsset | None:
    repo = os.environ.get(_ENV_REPO)
    app_name = os.environ.get(_ENV_APP_NAME)
    version = os.environ.get(_ENV_VERSION)
    name = os.environ.get(_ENV_ASSET_NAME)
    download_url = os.environ.get(_ENV_DOWNLOAD_URL)
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
    content_type = os.environ.get(_ENV_CONTENT_TYPE)
    return ReleaseAsset(
        repo=repo,
        app_name=app_name,
        version=version,
        name=name,
        download_url=download_url,
        content_type=content_type,
    )


def _parse_updater_outcome(value: str) -> UpdaterOutcome | None:
    try:
        return UpdaterOutcome(value)
    except ValueError:
        return None


def _find_matching_asset(
    payload: dict[str, Any],
    version: str,
) -> dict[str, Any] | None:
    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        return None

    current_platform = get_platform()
    arch = _normalized_arch(platform.machine())
    suffix = _expected_suffix(current_platform)
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


def _expected_suffix(current_platform: str) -> str | None:
    if current_platform == "macos":
        return ".dmg"
    if current_platform == "win":
        return ".exe"
    if current_platform == "lin":
        return ".appimage"
    return None


def _default_download_path(filename: str) -> Path:
    base_dir = Path(os.environ.get("FIT_USER_APP_PATH", str(Path.home())))
    return base_dir / "downloads" / filename


def launch_external_helper(asset: ReleaseAsset, downloaded_path: str | Path) -> None:
    helper_dir = _helper_workspace_path()
    helper_dir.mkdir(parents=True, exist_ok=True)
    log_path = _helper_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = helper_dir / "update-manifest.json"
    script_path = helper_dir / "install_update_macos.sh"

    bundle_path = _resolved_target_app_bundle_path()
    if bundle_path is None:
        raise RuntimeError(
            "target app bundle path is not available; set FIT_UPDATE_TARGET_APP when running outside the app bundle"
        )
    if get_platform() != "macos":
        raise RuntimeError("external update helper is implemented only for macOS")

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
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    script_path.write_text(
        _render_macos_helper_script(
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
        context=_LOG_CONTEXT,
    )
    with log_path.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            ["/bin/sh", str(script_path)],
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    debug(
        f"External update helper started with pid={process.pid}",
        context=_LOG_CONTEXT,
    )


def _helper_workspace_path() -> Path:
    return Path(os.environ.get(FIT_USER_APP_PATH, str(Path.home()))) / "update-helper"


def _helper_log_path() -> Path:
    base_logs = Path(
        os.environ.get(
            FIT_LOG_APP_PATH,
            str(Path(os.environ.get(FIT_USER_APP_PATH, str(Path.home()))) / "logs"),
        )
    )
    return base_logs / "update-helper.log"


def _current_app_bundle_path() -> Path | None:
    executable = Path(sys.executable).resolve()
    for candidate in (executable, *executable.parents):
        if candidate.name.endswith(".app"):
            return candidate
    return None


def _resolved_target_app_bundle_path() -> Path | None:
    explicit_target = os.environ.get(_ENV_TARGET_APP)
    if explicit_target:
        return Path(explicit_target).expanduser().resolve()
    return _current_app_bundle_path()


def _render_macos_helper_script(
    *,
    manifest: dict[str, object],
    script_path: Path,
    manifest_path: Path,
    helper_dir: Path,
) -> str:
    app_bundle_path = shlex.quote(str(manifest["app_bundle_path"]))
    downloaded_package_path = shlex.quote(str(manifest["downloaded_package_path"]))
    log_path = shlex.quote(str(manifest["log_path"]))
    updater_pid = shlex.quote(str(manifest["updater_pid"]))
    parent_pid = shlex.quote(str(manifest["parent_pid"]))
    manifest_path_q = shlex.quote(str(manifest_path))
    script_path_q = shlex.quote(str(script_path))
    helper_dir_q = shlex.quote(str(helper_dir))

    return f"""#!/bin/sh
set -eu

APP_BUNDLE_PATH={app_bundle_path}
DMG_PATH={downloaded_package_path}
LOG_PATH={log_path}
UPDATER_PID={updater_pid}
PARENT_PID={parent_pid}
SCRIPT_PATH={script_path_q}
MANIFEST_PATH={manifest_path_q}
HELPER_DIR={helper_dir_q}
BACKUP_PATH="${{APP_BUNDLE_PATH}}.backup"
MOUNT_POINT=""

log() {{
  printf '%s %s\\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG_PATH"
}}

cleanup_workspace() {{
  rm -f "$SCRIPT_PATH" "$MANIFEST_PATH"
  rmdir "$HELPER_DIR" 2>/dev/null || true
}}

wait_for_pid() {{
  pid="$1"
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1
  done
}}

detach_dmg() {{
  if [ -n "$MOUNT_POINT" ]; then
    hdiutil detach "$MOUNT_POINT" -quiet >/dev/null 2>&1 || true
  fi
}}

restore_backup() {{
  if [ -d "$BACKUP_PATH" ]; then
    rm -rf "$APP_BUNDLE_PATH"
    mv "$BACKUP_PATH" "$APP_BUNDLE_PATH"
  fi
}}

log "helper started"
wait_for_pid "$UPDATER_PID"
wait_for_pid "$PARENT_PID"
log "application processes terminated"

if [ ! -f "$DMG_PATH" ]; then
  log "downloaded package missing: $DMG_PATH"
  cleanup_workspace
  exit 1
fi

ATTACH_OUTPUT=$(hdiutil attach "$DMG_PATH" -nobrowse 2>&1) || {{
  log "hdiutil attach failed: $ATTACH_OUTPUT"
  cleanup_workspace
  exit 1
}}
MOUNT_POINT=$(printf '%s\\n' "$ATTACH_OUTPUT" | awk '/\\/Volumes\\// {{print $NF}}' | tail -n 1)
if [ -z "$MOUNT_POINT" ] || [ ! -d "$MOUNT_POINT" ]; then
  log "unable to resolve mount point from attach output"
  cleanup_workspace
  exit 1
fi
log "mounted dmg at $MOUNT_POINT"

NEW_APP=$(find "$MOUNT_POINT" -maxdepth 1 -name '*.app' -print | head -n 1)
if [ -z "$NEW_APP" ] || [ ! -d "$NEW_APP" ]; then
  log "no app bundle found in mounted dmg"
  detach_dmg
  cleanup_workspace
  exit 1
fi

rm -rf "$BACKUP_PATH"
if [ -d "$APP_BUNDLE_PATH" ]; then
  mv "$APP_BUNDLE_PATH" "$BACKUP_PATH"
fi

if ! ditto "$NEW_APP" "$APP_BUNDLE_PATH"; then
  log "ditto copy failed, restoring backup"
  restore_backup
  detach_dmg
  cleanup_workspace
  exit 1
fi

rm -rf "$BACKUP_PATH"
detach_dmg
log "update installed, relaunching app"
open "$APP_BUNDLE_PATH" >/dev/null 2>&1 || log "warning: unable to relaunch app"
cleanup_workspace
log "helper completed"
exit 0
"""


def _is_newer_than_local(remote_version: str) -> bool:
    local_version = get_local_version()
    try:
        return Version(remote_version) > Version(local_version)
    except InvalidVersion:
        return False


def _normalized_arch(machine: str) -> str:
    normalized = machine.strip().lower()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "aarch64": "arm64",
    }
    return aliases.get(normalized, normalized)
