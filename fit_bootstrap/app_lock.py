from __future__ import annotations

import grp
import os
import pwd
import time
from pathlib import Path

from fit_common.core import debug
from fit_common.core.paths import resolve_app_path

from fit_bootstrap.constants import APP_LOCK_NAME, FIT_USER_APP_PATH, FIT_USERNAME


def _lock_path() -> Path:
    base = os.environ.get(FIT_USER_APP_PATH) or resolve_app_path()
    return Path(base) / APP_LOCK_NAME


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except OSError:
        # On platforms where this is not reliable, assume alive.
        return True


def acquire_app_lock() -> bool:
    path = _lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = str(os.getpid())

    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as handle:
                handle.write(pid)
            _relax_lock_permissions(path)
            return True
        except FileExistsError:
            try:
                existing = path.read_text().strip()
                existing_pid = int(existing) if existing else None
            except OSError:
                existing_pid = None

            if existing_pid and _pid_alive(existing_pid):
                debug(
                    f"ℹ️ App lock already held by pid {existing_pid}", context="app_lock"
                )
                return False

            # Stale lock, remove and retry once.
            try:
                path.unlink()
            except OSError:
                return False
            time.sleep(0.05)


def is_app_locked() -> bool:
    path = _lock_path()
    if not path.exists():
        return False
    try:
        existing = path.read_text().strip()
        existing_pid = int(existing) if existing else None
    except OSError:
        return False
    if not existing_pid:
        return False
    return _pid_alive(existing_pid)


def release_app_lock() -> None:
    path = _lock_path()
    try:
        if not path.exists():
            return
        existing = path.read_text().strip()
        if existing and existing == str(os.getpid()):
            path.unlink()
    except OSError:
        pass


def _relax_lock_permissions(path: Path) -> None:
    if os.geteuid() != 0:
        return
    sudo_user = os.environ.get("SUDO_USER")
    owner = sudo_user or os.environ.get(FIT_USERNAME)
    if not owner:
        owner = _owner_from_path(path)
    try:
        if owner:
            user_info = pwd.getpwnam(owner)
            group_info = grp.getgrgid(user_info.pw_gid)
            os.chown(path, user_info.pw_uid, group_info.gr_gid)
        os.chmod(path, 0o600)
    except OSError:
        pass


def _owner_from_path(path: Path) -> str | None:
    parts = path.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "Users":
        return parts[2]
    return None
