from __future__ import annotations

import sys

from PySide6 import QtCore, QtWidgets

from fit_common.gui.dialog import Dialog, DialogButtonTypes

from fit_bootstrap.lang import load_translations


class LinuxAskpassDialog(Dialog):
    def __init__(self) -> None:
        translations = load_translations()
        super().__init__(
            translations.get("LINUX_ASKPASS_DIALOG_TITLE", ""),
            translations.get("LINUX_ASKPASS_DIALOG_MESSAGE", ""),
            severity=QtWidgets.QMessageBox.Icon.Question,
        )
        self.setMinimumWidth(440)
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.text_box.addWidget(self.password)

        self.set_buttons_type(DialogButtonTypes.QUESTION)
        self.left_button.setText(translations.get("OK_BUTTON", "OK"))
        self.right_button.setText(translations.get("CANCEL_BUTTON", "Cancel"))
        self.left_button.clicked.connect(self.accept)
        self.right_button.clicked.connect(self.reject)
        self.password.returnPressed.connect(self.accept)
        QtCore.QTimer.singleShot(0, self.password.setFocus)
        self.adjustSize()

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
