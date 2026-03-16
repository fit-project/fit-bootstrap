from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
