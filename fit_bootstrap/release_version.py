"""Bootstrap adapter for release checks and updater handoff."""

from __future__ import annotations

from fit_bootstrap.caller import CallerProfile
from fit_bootstrap.lang import load_translations
from fit_bootstrap.signals import BootstrapResult, BootstrapSignal
from fit_bootstrap.updater import UpdaterOutcome, get_available_update, run_updater


def ensure_latest_release_version(
    caller: CallerProfile,
) -> BootstrapResult | None:
    update = get_available_update(caller)
    if update is None:
        return None

    updater_result = run_updater(update)
    if updater_result.outcome in {
        UpdaterOutcome.DECLINED,
        UpdaterOutcome.DOWNLOAD_FAILED_CONTINUE,
        UpdaterOutcome.HELPER_FAILED_CONTINUE,
        UpdaterOutcome.INSTALL_FAILED_ROLLBACK,
    }:
        return None

    if updater_result.outcome == UpdaterOutcome.UPDATED:
        return BootstrapResult(
            code=0,
            signal=BootstrapSignal.OK,
            message=None,
        )

    __translations = load_translations()
    return BootstrapResult(
        code=1,
        signal=BootstrapSignal.ERROR,
        message=__translations.get(
            "BOOSTSTRAP_UPDATER_UNEXPECTED_ERROR_MESSAGE",
            "",
        ),
    )
