from __future__ import annotations

import sys

from fit_assets import resources  # noqa: F401
from PySide6 import QtCore, QtWidgets

from fit_bootstrap.lang import load_translations
from fit_bootstrap.ui_askpass_dialog import Ui_askpass_dialog


class LinuxAskpassDialog(QtWidgets.QDialog, Ui_askpass_dialog):
    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)

        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumHeight(200)

        translations = load_translations()
        title = translations.get("LINUX_ASKPASS_DIALOG_TITLE", "")
        self.title_right_info.setText(title)
        self.setWindowTitle(title)
        self.message.setText(
            translations.get("LINUX_ASKPASS_DIALOG_MESSAGE", "")
        )

        self.ok_button.setText(translations.get("OK_BUTTON", "OK"))
        self.cancel_button.setText(translations.get("CANCEL_BUTTON", "Cancel"))
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        self.cancel_button.clicked.connect(self.reject)
        self.password.returnPressed.connect(self.accept)
        QtCore.QTimer.singleShot(0, self.password.setFocus)
        self._resize_to_message()

    def _resize_to_message(self) -> None:
        layout = self.layout()
        if layout is not None:
            layout.activate()
        self.content_box_layout.activate()
        self.message.adjustSize()
        self.adjustSize()

        target_height = max(200, self.sizeHint().height())
        self.setMinimumHeight(target_height)
        self.resize(self.width(), target_height)

    def get_password(self) -> str:
        return self.password.text()


def main() -> int:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    dialog = LinuxAskpassDialog()
    if dialog.exec() != int(QtWidgets.QDialog.DialogCode.Accepted):
        return 1
    password = dialog.get_password()
    if not password:
        return 1
    sys.stdout.write(password + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
