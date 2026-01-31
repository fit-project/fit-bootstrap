from __future__ import annotations

import argparse
import sys

from fit_assets import resources  # noqa: F401
from fit_common.core import get_platform
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
)

from fit_bootstrap.lang import load_translations
from fit_bootstrap.macos.ui_askpass_dialog import Ui_askpass_dialog


class AskpassDialog(QtWidgets.QDialog, Ui_askpass_dialog):
    def __init__(self, mode: str) -> None:
        super().__init__()
        # Inizializza l'interfaccia da ui_multipurpose.py
        self.setupUi(self)

        # HIDE STANDARD TITLE BAR
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumHeight(200)

        self.__translations = load_translations()
        title_key = "ASKPASS_DIALOG_TITLE"
        message_key = "ASKPASS_DIALOG_MESSAGE"
        if mode == "launch-gui":
            title_key = "USER_IS_NOT_ADMIN_TITLE"
            message_key = "USER_IS_NOT_ADMIN_MSG"

        message = self.__translations.get(message_key, "")
        if mode == "launch-gui":
            privilege_label = "root"
            if get_platform() == "win":
                privilege_label = "administrator"

            message = message.replace("{}", privilege_label)

        self.message.setText(message)
        self.title_right_info.setText(self.__translations.get(title_key, ""))
        self.setWindowTitle(self.__translations.get(title_key, ""))
        self._resize_to_message()

        self.cancel_button.setText(self.__translations["CANCEL_BUTTON"])
        self.ok_button.setText(self.__translations["OK_BUTTON"])
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        self.cancel_button.clicked.connect(self.reject)
        self.password.returnPressed.connect(self.accept)

    def get_password(self) -> str:
        return self.password.text()

    def _resize_to_message(self) -> None:
        if self.layout() is not None:
            self.layout().activate()
        self.content_box_layout.activate()
        self.message.adjustSize()
        self.adjustSize()

        target_height = max(200, self.sizeHint().height())
        self.setMinimumHeight(target_height)
        self.resize(self.width(), target_height)


def parse_args(argv: list[str]) -> tuple[str, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--install-certificate", action="store_true")
    group.add_argument("--launch-gui", action="store_true")
    args, remaining = parser.parse_known_args(argv)
    mode = "launch-gui" if args.launch_gui else "install-certificate"
    return mode, remaining


def main() -> int:
    mode, qt_args = parse_args(sys.argv[1:])
    app = QApplication([sys.argv[0], *qt_args])
    dialog = AskpassDialog(mode)
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
