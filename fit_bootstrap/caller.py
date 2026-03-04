from __future__ import annotations

from enum import Enum


class CallerProfile(str, Enum):
    FIT = "fit"
    FIT_WEB = "fit_web"
    FIT_BOOTSTRAP = "fit_bootstrap"
