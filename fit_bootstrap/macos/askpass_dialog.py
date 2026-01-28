from __future__ import annotations

import sys

from fit_assets import resources  # noqa: F401
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
)

from fit_bootstrap.lang import load_translations
from fit_bootstrap.macos.ui_askpass_dialog import Ui_askpass_dialog


class AskpassDialog(QtWidgets.QDialog, Ui_askpass_dialog):
    def __init__(self) -> None:
        super().__init__()
        # Inizializza l'interfaccia da ui_multipurpose.py
        self.setupUi(self)

        # HIDE STANDARD TITLE BAR
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.__translations = load_translations()

        self.message.setText(self.__translations["ASKPASS_DIALOG_MESSAGE"])

        self.cancel_button.setText(self.__translations["CANCEL_BUTTON"])
        self.ok_button.setText(self.__translations["OK_BUTTON"])
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        self.cancel_button.clicked.connect(self.reject)
        self.password.returnPressed.connect(self.accept)

    def get_password(self) -> str:
        return self.password.text()


def main() -> int:
    app = QApplication(sys.argv)
    dialog = AskpassDialog()
    result = dialog.exec()
    if result != QDialog.Accepted:
        return 1
    password = dialog.get_password()
    if not password:
        return 1
    sys.stdout.write(password + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
