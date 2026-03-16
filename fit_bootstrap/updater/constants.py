from __future__ import annotations

from fit_bootstrap.caller import CallerProfile

LOG_CONTEXT = "fit_bootstrap.updater"

REPO_BY_CALLER = {
    CallerProfile.FIT: "fit",
    CallerProfile.FIT_WEB: "fit-web",
    CallerProfile.FIT_BOOTSTRAP: "fit-bootstrap",
}

DISPLAY_NAME_BY_CALLER = {
    CallerProfile.FIT: "FIT",
    CallerProfile.FIT_WEB: "FIT Web",
    CallerProfile.FIT_BOOTSTRAP: "FIT Bootstrap",
}

UPDATER_DIALOG_ENV = "FIT_UPDATE_DIALOG"
ENV_APP_NAME = "FIT_UPDATE_APP_NAME"
ENV_REPO = "FIT_UPDATE_REPO"
ENV_VERSION = "FIT_UPDATE_VERSION"
ENV_ASSET_NAME = "FIT_UPDATE_ASSET_NAME"
ENV_DOWNLOAD_URL = "FIT_UPDATE_DOWNLOAD_URL"
ENV_CONTENT_TYPE = "FIT_UPDATE_CONTENT_TYPE"
ENV_TARGET_APP = "FIT_UPDATE_TARGET_APP"
