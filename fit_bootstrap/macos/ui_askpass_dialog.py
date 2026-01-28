# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
            "QWidget{\n"
            "	color: rgb(221, 221, 221);\n"
            "}\n"
            "\n"
            "/* Content App */\n"
            "#content_top_bg{	\n"
            "	background-color: rgb(33, 37, 43);\n"
            "}\n"
            "\n"
            "/* Top Buttons */\n"
            "#right_buttons .QPushButton { background-color: rgba(255, 255, 255, 0); border: none;  border-radius: 5px; }\n"
            "#right_buttons .QPushButton:hover { background-color: rgb(44, 49, 57); border-style: solid; border-radius: 4px; }\n"
            "#right_buttons .QPushButton:pressed { background-color: rgb(23, 26, 30); border-style: solid; border-radius: 4px; }\n"
            ""
        )
        self.content_box = QFrame(askpass_dialog)
        self.content_box.setObjectName("content_box")
        self.content_box.setGeometry(QRect(0, 50, 500, 300))
        self.content_box.setMinimumSize(QSize(400, 0))
        self.content_box.setStyleSheet("background-color: rgb(40, 44, 52);")
        self.content_box_layout = QVBoxLayout(self.content_box)
        self.content_box_layout.setObjectName("content_box_layout")
        self.content_box_layout.setContentsMargins(12, 12, 12, 12)
        self.content_box_horizontal_layout = QHBoxLayout()
        self.content_box_horizontal_layout.setObjectName(
            "content_box_horizontal_layout"
        )
        self.content_box_horizontal_layout.setContentsMargins(-1, -1, -1, 0)
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

        self.password_box = QHBoxLayout()
        self.password_box.setObjectName("password_box")
        self.password_box.setContentsMargins(-1, 0, -1, -1)
        self.password = QLineEdit(self.content_box)
        self.password.setObjectName("password")
        self.password.setMinimumSize(QSize(0, 30))
        self.password.setEchoMode(QLineEdit.Password)

        self.password_box.addWidget(self.password)

        self.content_box_layout.addLayout(self.password_box)

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
            ":disabled {background-color: rgb(52, 59, 72); color: rgba(255, 255, 255, 10%) }"
        )

        self.horizontalLayout_6.addWidget(self.ok_button)

        self.content_box_layout.addWidget(self.navigation_buttons)

        self.content_top_bg = QFrame(askpass_dialog)
        self.content_top_bg.setObjectName("content_top_bg")
        self.content_top_bg.setGeometry(QRect(0, 0, 500, 50))
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

        self.retranslateUi(askpass_dialog)

        QMetaObject.connectSlotsByName(askpass_dialog)

    # setupUi

    def retranslateUi(self, askpass_dialog):
        askpass_dialog.setWindowTitle(
            QCoreApplication.translate("askpass_dialog", "Dialog", None)
        )
        self.message.setText(
            QCoreApplication.translate(
                "askpass_dialog",
                '<html><head/><body><p>Sembra che il certificato di <span style=" font-weight:600;">mitmproxy</span> non sia installato.<br/><br/><span style=" font-weight:600; color:#ff0000;">Senza questo certificato, FIT Web non pu\u00f2 intercettare il traffico HTTPS e quindi non pu\u00f2 funzionare. Per questo motivo verr\u00e0 chiusa.</span><br/><br/>Per installarlo servono i privilegi di amministratore: ti verr\u00e0 richiesta la password di root (anche pi\u00f9 volte).</p><p><br/>Questa operazione avviene solo la prima volta. </p></body></html>',
                None,
            )
        )
        self.password.setPlaceholderText(
            QCoreApplication.translate("askpass_dialog", "password", None)
        )
        self.cancel_button.setText(
            QCoreApplication.translate("askpass_dialog", "Annula", None)
        )
        self.ok_button.setText(QCoreApplication.translate("askpass_dialog", "Ok", None))
        self.top_logo.setText("")
        self.title_right_info.setText(
            QCoreApplication.translate(
                "askpass_dialog", "Installazione certificato mimtproxy", None
            )
        )

    # retranslateUi
