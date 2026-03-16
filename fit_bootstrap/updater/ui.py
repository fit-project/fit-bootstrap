from __future__ import annotations

import sys
from html import escape
from typing import Any

from fit_common.core import debug

from fit_bootstrap.lang import load_translations

from .constants import LOG_CONTEXT
from .models import ReleaseAsset, UpdaterOutcome, UpdaterResult


def run_dialog(
    *,
    asset: ReleaseAsset | None,
    parse_updater_outcome_fn,
    download_release_asset_fn,
    launch_external_helper_fn,
) -> int:
    try:
        from PySide6.QtCore import QObject, Qt, QThread, Signal
        from PySide6.QtWidgets import QApplication, QDialog

        from fit_bootstrap.updater.updater_dialog_ui import Ui_updater_dialog
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
                downloaded_path = download_release_asset_fn(self._asset)
                debug(
                    f"Installing macOS update from {downloaded_path}",
                    context=LOG_CONTEXT,
                )
            except Exception as exc:  # pragma: no cover - exercised via GUI workflow
                self.finished.emit(
                    UpdaterOutcome.DOWNLOAD_FAILED_CONTINUE.value, str(exc)
                )
                return

            self.download_ready.emit(str(downloaded_path))
            self.status_changed.emit(translations.get("UPDATER_STATUS_INSTALLING", ""))
            try:
                launch_external_helper_fn(self._asset, downloaded_path)
            except Exception as exc:  # pragma: no cover - exercised via GUI workflow
                self.finished.emit(
                    UpdaterOutcome.HELPER_FAILED_CONTINUE.value, str(exc)
                )
                return

            self.finished.emit(UpdaterOutcome.UPDATED.value, "")

    class UpdateDialog(QDialog, Ui_updater_dialog):
        def __init__(self, update_asset: ReleaseAsset) -> None:
            super().__init__()
            self.setupUi(self)
            self._asset = update_asset
            self._outcome = UpdaterOutcome.DECLINED
            self._detail: str | None = None
            self._thread: QThread | None = None
            self._worker: UpdateWorker | None = None

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

        def _finish_update(self, outcome_text: str, detail: str) -> None:
            outcome = parse_updater_outcome_fn(outcome_text) or UpdaterOutcome.ERROR
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
