"""macOS updater helper script renderer."""

from __future__ import annotations

import shlex
from pathlib import Path


def render_macos_helper_script(
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
    mitm_pid = shlex.quote(str(manifest.get("mitm_pid", "")))
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
MITM_PID={mitm_pid}
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

stop_mitmproxy() {{
  pid="$1"
  if [ -z "$pid" ]; then
    log "mitm pid not provided, skipping stop"
    return
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    log "mitm pid $pid not running"
    return
  fi
  log "stopping mitm pid $pid"
  kill -INT "$pid" 2>/dev/null || true
  i=0
  while kill -0 "$pid" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge 10 ]; then
      log "mitm pid $pid still running, sending SIGKILL"
      kill -KILL "$pid" 2>/dev/null || true
      break
    fi
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
stop_mitmproxy "$MITM_PID"
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
# Ensure relaunch starts in normal mode, not updater-dialog mode.
unset FIT_UPDATE_DIALOG FIT_UPDATE_APP_NAME FIT_UPDATE_REPO FIT_UPDATE_VERSION FIT_UPDATE_ASSET_NAME FIT_UPDATE_DOWNLOAD_URL FIT_UPDATE_CONTENT_TYPE FIT_UPDATE_TARGET_APP
open "$APP_BUNDLE_PATH" >/dev/null 2>&1 || log "warning: unable to relaunch app"
cleanup_workspace
log "helper completed"
exit 0
"""
