# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'updater.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, Qt
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)


class Ui_askpass_dialog(object):
    def setupUi(self, askpass_dialog):
        if not askpass_dialog.objectName():
            askpass_dialog.setObjectName("askpass_dialog")
        askpass_dialog.resize(500, 350)
        askpass_dialog.setMinimumSize(QSize(400, 0))
        askpass_dialog.setMaximumSize(QSize(16777215, 16777215))
        askpass_dialog.setStyleSheet(
            "\n"
            "\n"
            "        QWidget{\n"
            "        color: rgb(221, 221, 221);\n"
            "        font: 13px;\n"
            "        }\n"
            "        /* Content App */\n"
            "        #content_top_bg{\n"
            "        background-color: rgb(33, 37, 43);\n"
            "        }\n"
            "        /* Title Menu */\n"
            "        #title_right_info { font: 13px; }\n"
            "        #title_right_info { padding-left: 10px; }\n"
            "\n"
            "        /* Content App */\n"
            "        #content_top_bg{\n"
            "        background-color: rgb(33, 37, 43);\n"
            "        }\n"
            "        #content_bottom{\n"
            "        border-top: 3px solid rgb(44, 49, 58);\n"
            "        }\n"
            "\n"
            "        QLineEdit {\n"
            "        background-color: rgb(33, 37, 43);\n"
            "        border-radius: 5px;\n"
            "        border: 2px solid rgb(33, 37, 43);\n"
            "        padding-left: 10px;\n"
            "        selection-color: rgb(255, 255, 255);\n"
            "        selection-background-color: rgb(255, 121, 198);\n"
            "        }\n"
            "        QLineEdit:hover {\n"
            "        border: 2px solid rgb(64, 71, 88);\n"
            "        }\n"
            "        QLineEdit:focus {\n"
            "        border: 2p"
            "x solid rgb(91, 101, 124);\n"
            "        }\n"
            "\n"
            "        QLineEdit::disabled {\n"
            "        color: rgba(255, 255, 255, 10%);\n"
            "        }\n"
            "\n"
            "        QLabel::disabled {\n"
            "        color: rgba(255, 255, 255, 10%);\n"
            "        }\n"
            "\n"
            "        /* Top Buttons */\n"
            "        #right_buttons .QPushButton { background-color: rgba(255, 255, 255, 0); border: none;\n"
            "        border-radius: 5px; }\n"
            "        #right_buttons .QPushButton:hover { background-color: rgb(44, 49, 57); border-style: solid;\n"
            "        border-radius: 4px; }\n"
            "        #right_buttons .QPushButton:pressed { background-color: rgb(23, 26, 30); border-style:\n"
            "        solid; border-radius: 4px; }\n"
            ""
        )
        self.main_layout = QVBoxLayout(askpass_dialog)
        self.main_layout.setSpacing(0)
        self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.content_top_bg = QFrame(askpass_dialog)
        self.content_top_bg.setObjectName("content_top_bg")
        self.content_top_bg.setMinimumSize(QSize(400, 50))
        self.content_top_bg.setMaximumSize(QSize(16777215, 50))
        self.content_top_bg.setFrameShape(QFrame.NoFrame)
        self.content_top_bg.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.content_top_bg)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 10, 0)
        self.left_box = QFrame(self.content_top_bg)
        self.left_box.setObjectName("left_box")
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.left_box.sizePolicy().hasHeightForWidth())
        self.left_box.setSizePolicy(sizePolicy)
        self.left_box.setFrameShape(QFrame.NoFrame)
        self.left_box.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.left_box)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.logo_container = QFrame(self.left_box)
        self.logo_container.setObjectName("logo_container")
        self.logo_container.setMinimumSize(QSize(60, 0))
        self.logo_container.setMaximumSize(QSize(60, 16777215))
        self.horizontalLayout_8 = QHBoxLayout(self.logo_container)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.top_logo = QLabel(self.logo_container)
        self.top_logo.setObjectName("top_logo")
        self.top_logo.setMinimumSize(QSize(42, 42))
        self.top_logo.setMaximumSize(QSize(42, 42))
        self.top_logo.setPixmap(QPixmap(":/images/images/logo-42x42.png"))

        self.horizontalLayout_8.addWidget(self.top_logo)

        self.horizontalLayout_3.addWidget(self.logo_container)

        self.title_right_info = QLabel(self.left_box)
        self.title_right_info.setObjectName("title_right_info")
        sizePolicy1 = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.title_right_info.sizePolicy().hasHeightForWidth()
        )
        self.title_right_info.setSizePolicy(sizePolicy1)
        self.title_right_info.setMaximumSize(QSize(16777215, 45))
        self.title_right_info.setStyleSheet("font: 12pt;")
        self.title_right_info.setAlignment(
            Qt.AlignLeading | Qt.AlignLeft | Qt.AlignVCenter
        )

        self.horizontalLayout_3.addWidget(self.title_right_info)

        self.horizontalLayout.addWidget(self.left_box)

        self.right_buttons = QFrame(self.content_top_bg)
        self.right_buttons.setObjectName("right_buttons")
        self.right_buttons.setMinimumSize(QSize(0, 28))
        self.right_buttons.setFrameShape(QFrame.NoFrame)
        self.right_buttons.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.right_buttons)
        self.horizontalLayout_2.setSpacing(5)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout.addWidget(self.right_buttons, 0, Qt.AlignRight)

        self.main_layout.addWidget(self.content_top_bg)

        self.content_box = QFrame(askpass_dialog)
        self.content_box.setObjectName("content_box")
        self.content_box.setMinimumSize(QSize(400, 0))
        self.content_box.setStyleSheet("background-color: rgb(40, 44, 52);")
        self.content_box_layout = QVBoxLayout(self.content_box)
        self.content_box_layout.setObjectName("content_box_layout")
        self.content_box_layout.setContentsMargins(12, 12, 12, 12)
        self.content_box_horizontal_layout = QHBoxLayout()
        self.content_box_horizontal_layout.setObjectName(
            "content_box_horizontal_layout"
        )
        self.content_box_horizontal_layout.setContentsMargins(10, -1, 10, 0)
        self.text_box = QVBoxLayout()
        self.text_box.setObjectName("text_box")
        self.text_box.setContentsMargins(0, -1, -1, 0)
        self.message = QLabel(self.content_box)
        self.message.setObjectName("message")
        self.message.setStyleSheet("font-size: 13px;")
        self.message.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignTop)
        self.message.setWordWrap(True)

        self.text_box.addWidget(self.message)

        self.content_box_horizontal_layout.addLayout(self.text_box)

        self.content_box_layout.addLayout(self.content_box_horizontal_layout)

        self.verticalSpacer = QSpacerItem(
            20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.content_box_layout.addItem(self.verticalSpacer)

        self.progress_bar_box = QHBoxLayout()
        self.progress_bar_box.setObjectName("progress_bar_box")
        self.progress_bar_box.setContentsMargins(10, 0, 10, 0)
        self.progress_bar = QProgressBar(self.content_box)
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setMinimumSize(QSize(200, 0))
        self.progress_bar.setMaximumSize(QSize(16777215, 20))
        self.progress_bar.setStyleSheet(
            "QProgressBar\n"
            "{\n"
            "    color: #ffffff;\n"
            "    border-style: outset;\n"
            "border-width: 2px;\n"
            "    border-radius: 5px;\n"
            "    text-align: left;\n"
            "}\n"
            "QProgressBar::chunk\n"
            "{\n"
            "    background-color:#e06133;\n"
            "}"
        )
        self.progress_bar.setValue(24)

        self.progress_bar_box.addWidget(self.progress_bar)

        self.content_box_layout.addLayout(self.progress_bar_box)

        self.vertical_spacer = QSpacerItem(
            20, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.content_box_layout.addItem(self.vertical_spacer)

        self.navigation_buttons = QFrame(self.content_box)
        self.navigation_buttons.setObjectName("navigation_buttons")
        self.navigation_buttons.setMaximumSize(QSize(16777215, 40))
        self.horizontalLayout_6 = QHBoxLayout(self.navigation_buttons)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.left_spacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_6.addItem(self.left_spacer)

        self.cancel_button = QPushButton(self.navigation_buttons)
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setEnabled(True)
        self.cancel_button.setMinimumSize(QSize(80, 30))
        self.cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_button.setLayoutDirection(Qt.LeftToRight)
        self.cancel_button.setStyleSheet(
            "QPushButton:disabled {background-color: rgb(52, 59, 72); color: rgba(255, 255, 255, 10%) }"
        )

        self.horizontalLayout_6.addWidget(self.cancel_button)

        self.between_spacer = QSpacerItem(
            5, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_6.addItem(self.between_spacer)

        self.ok_button = QPushButton(self.navigation_buttons)
        self.ok_button.setObjectName("ok_button")
        self.ok_button.setEnabled(True)
        self.ok_button.setMinimumSize(QSize(80, 30))
        self.ok_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.ok_button.setLayoutDirection(Qt.LeftToRight)
        self.ok_button.setStyleSheet(
            ":disabled {background-color: rgb(52, 59, 72); color:\n"
            "                          rgba(255, 255, 255, 10%) }"
        )

        self.horizontalLayout_6.addWidget(self.ok_button)

        self.content_box_layout.addWidget(self.navigation_buttons)

        self.main_layout.addWidget(self.content_box)

        self.retranslateUi(askpass_dialog)

        QMetaObject.connectSlotsByName(askpass_dialog)

    # setupUi

    def retranslateUi(self, askpass_dialog):
        askpass_dialog.setWindowTitle(
            QCoreApplication.translate("askpass_dialog", "Dialog", None)
        )
        self.top_logo.setText("")
        self.title_right_info.setText(
            QCoreApplication.translate(
                "askpass_dialog", "Aggiornamento disponibile", None
            )
        )
        self.message.setText(
            QCoreApplication.translate(
                "askpass_dialog",
                '<html><head/><body><p>"\u00c8 disponibile un aggiornamento di FIT Bootstrap alla versione 2.0.0.<br/><br/>\n'
                "Vuoi scaricare e installare ora il pacchetto <code>fit-bootstrap-portable-2.0.0-macos-arm64.dmg</code>? <br/><br/>Durante l'operazione l'app attuale potrebbe interrompersi.<br/><br/>Vuoi procedere con il download e installazione?</p></body></html>",
                None,
            )
        )
        self.cancel_button.setText(
            QCoreApplication.translate(
                "askpass_dialog", "Continua con questa versione", None
            )
        )
        self.ok_button.setText(
            QCoreApplication.translate("askpass_dialog", "Aggiorna", None)
        )

    # retranslateUi
