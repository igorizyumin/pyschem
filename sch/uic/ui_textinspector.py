# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'TextInspector.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QFontComboBox,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_TextInspector(object):
    def setupUi(self, TextInspector):
        if not TextInspector.objectName():
            TextInspector.setObjectName(u"TextInspector")
        TextInspector.resize(221, 252)
        self.verticalLayout = QVBoxLayout(TextInspector)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(TextInspector)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.text = QLineEdit(TextInspector)
        self.text.setObjectName(u"text")

        self.horizontalLayout.addWidget(self.text)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.fontFace = QFontComboBox(TextInspector)
        self.fontFace.setObjectName(u"fontFace")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fontFace.sizePolicy().hasHeightForWidth())
        self.fontFace.setSizePolicy(sizePolicy)
        self.fontFace.setMinimumSize(QSize(100, 0))
        self.fontFace.setMaxVisibleItems(99)

        self.horizontalLayout_3.addWidget(self.fontFace)

        self.fontSize = QComboBox(TextInspector)
        self.fontSize.setObjectName(u"fontSize")
        sizePolicy.setHeightForWidth(self.fontSize.sizePolicy().hasHeightForWidth())
        self.fontSize.setSizePolicy(sizePolicy)
        self.fontSize.setEditable(True)

        self.horizontalLayout_3.addWidget(self.fontSize)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(TextInspector)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.gridLayout = QGridLayout()
        self.gridLayout.setSpacing(4)
        self.gridLayout.setObjectName(u"gridLayout")
        self.btnMidCtr = QPushButton(TextInspector)
        self.alignGroup = QButtonGroup(TextInspector)
        self.alignGroup.setObjectName(u"alignGroup")
        self.alignGroup.addButton(self.btnMidCtr)
        self.btnMidCtr.setObjectName(u"btnMidCtr")
        self.btnMidCtr.setMaximumSize(QSize(15, 15))
        self.btnMidCtr.setCheckable(True)
        self.btnMidCtr.setChecked(True)

        self.gridLayout.addWidget(self.btnMidCtr, 2, 3, 1, 1)

        self.btnMidLeft = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnMidLeft)
        self.btnMidLeft.setObjectName(u"btnMidLeft")
        self.btnMidLeft.setMaximumSize(QSize(15, 15))
        self.btnMidLeft.setCheckable(True)

        self.gridLayout.addWidget(self.btnMidLeft, 2, 2, 1, 1)

        self.btnTopLeft = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnTopLeft)
        self.btnTopLeft.setObjectName(u"btnTopLeft")
        self.btnTopLeft.setEnabled(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.btnTopLeft.sizePolicy().hasHeightForWidth())
        self.btnTopLeft.setSizePolicy(sizePolicy1)
        self.btnTopLeft.setMaximumSize(QSize(15, 15))
        self.btnTopLeft.setCheckable(True)

        self.gridLayout.addWidget(self.btnTopLeft, 1, 2, 1, 1)

        self.btnTopRight = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnTopRight)
        self.btnTopRight.setObjectName(u"btnTopRight")
        self.btnTopRight.setMaximumSize(QSize(15, 15))
        self.btnTopRight.setCheckable(True)

        self.gridLayout.addWidget(self.btnTopRight, 1, 4, 1, 1)

        self.btnTopCtr = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnTopCtr)
        self.btnTopCtr.setObjectName(u"btnTopCtr")
        self.btnTopCtr.setMaximumSize(QSize(15, 15))
        self.btnTopCtr.setCheckable(True)

        self.gridLayout.addWidget(self.btnTopCtr, 1, 3, 1, 1)

        self.btnBotCtr = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnBotCtr)
        self.btnBotCtr.setObjectName(u"btnBotCtr")
        self.btnBotCtr.setMaximumSize(QSize(15, 15))
        self.btnBotCtr.setCheckable(True)

        self.gridLayout.addWidget(self.btnBotCtr, 3, 3, 1, 1)

        self.btnMidRight = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnMidRight)
        self.btnMidRight.setObjectName(u"btnMidRight")
        self.btnMidRight.setMaximumSize(QSize(15, 15))
        self.btnMidRight.setCheckable(True)

        self.gridLayout.addWidget(self.btnMidRight, 2, 4, 1, 1)

        self.btnBotLeft = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnBotLeft)
        self.btnBotLeft.setObjectName(u"btnBotLeft")
        self.btnBotLeft.setMaximumSize(QSize(15, 15))
        self.btnBotLeft.setCheckable(True)

        self.gridLayout.addWidget(self.btnBotLeft, 3, 2, 1, 1)

        self.btnBotRight = QPushButton(TextInspector)
        self.alignGroup.addButton(self.btnBotRight)
        self.btnBotRight.setObjectName(u"btnBotRight")
        self.btnBotRight.setMaximumSize(QSize(15, 15))
        self.btnBotRight.setCheckable(True)

        self.gridLayout.addWidget(self.btnBotRight, 3, 4, 1, 1)


        self.horizontalLayout_2.addLayout(self.gridLayout)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(TextInspector)

        QMetaObject.connectSlotsByName(TextInspector)
    # setupUi

    def retranslateUi(self, TextInspector):
        TextInspector.setWindowTitle(QCoreApplication.translate("TextInspector", u"Form", None))
        self.label.setText(QCoreApplication.translate("TextInspector", u"Text", None))
        self.label_2.setText(QCoreApplication.translate("TextInspector", u"Alignment", None))
        self.btnMidCtr.setText("")
        self.btnMidLeft.setText("")
        self.btnTopLeft.setText("")
        self.btnTopRight.setText("")
        self.btnTopCtr.setText("")
        self.btnBotCtr.setText("")
        self.btnMidRight.setText("")
        self.btnBotLeft.setText("")
        self.btnBotRight.setText("")
    # retranslateUi

