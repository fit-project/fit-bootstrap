from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class AskpassDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FIT Bootstrap")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("FIT Bootstrap needs administrator privileges."))
        self._input = QLineEdit()
        self._input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self._input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def password(self) -> str:
        return self._input.text()


def main() -> int:
    app = QApplication(sys.argv)
    dialog = AskpassDialog()
    result = dialog.exec()
    if result != QDialog.Accepted:
        return 1
    password = dialog.password()
    if not password:
        return 1
    sys.stdout.write(password + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
