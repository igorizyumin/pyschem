# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PropTextInspector.ui'
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
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
    QFontComboBox, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_PropTextInspector(object):
    def setupUi(self, PropTextInspector):
        if not PropTextInspector.objectName():
            PropTextInspector.setObjectName(u"PropTextInspector")
        PropTextInspector.resize(221, 309)
        self.verticalLayout = QVBoxLayout(PropTextInspector)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.cbShowName = QCheckBox(PropTextInspector)
        self.cbShowName.setObjectName(u"cbShowName")
        self.cbShowName.setEnabled(False)

        self.gridLayout_2.addWidget(self.cbShowName, 3, 0, 1, 2)

        self.leValue = QLineEdit(PropTextInspector)
        self.leValue.setObjectName(u"leValue")

        self.gridLayout_2.addWidget(self.leValue, 1, 1, 1, 1)

        self.label_3 = QLabel(PropTextInspector)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_2.addWidget(self.label_3, 1, 0, 1, 1)

        self.cbProp = QComboBox(PropTextInspector)
        self.cbProp.setObjectName(u"cbProp")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbProp.sizePolicy().hasHeightForWidth())
        self.cbProp.setSizePolicy(sizePolicy)
        self.cbProp.setEditable(True)

        self.gridLayout_2.addWidget(self.cbProp, 0, 1, 1, 1)

        self.label = QLabel(PropTextInspector)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.cbVis = QCheckBox(PropTextInspector)
        self.cbVis.setObjectName(u"cbVis")

        self.gridLayout_2.addWidget(self.cbVis, 2, 0, 1, 2)


        self.verticalLayout.addLayout(self.gridLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.fontFace = QFontComboBox(PropTextInspector)
        self.fontFace.setObjectName(u"fontFace")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.fontFace.sizePolicy().hasHeightForWidth())
        self.fontFace.setSizePolicy(sizePolicy1)
        self.fontFace.setMinimumSize(QSize(100, 0))
        self.fontFace.setMaxVisibleItems(99)

        self.horizontalLayout_3.addWidget(self.fontFace)

        self.fontSize = QComboBox(PropTextInspector)
        self.fontSize.setObjectName(u"fontSize")
        sizePolicy1.setHeightForWidth(self.fontSize.sizePolicy().hasHeightForWidth())
        self.fontSize.setSizePolicy(sizePolicy1)
        self.fontSize.setEditable(True)

        self.horizontalLayout_3.addWidget(self.fontSize)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(PropTextInspector)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.gridLayout = QGridLayout()
        self.gridLayout.setSpacing(4)
        self.gridLayout.setObjectName(u"gridLayout")
        self.btnMidCtr = QPushButton(PropTextInspector)
        self.alignGroup = QButtonGroup(PropTextInspector)
        self.alignGroup.setObjectName(u"alignGroup")
        self.alignGroup.addButton(self.btnMidCtr)
        self.btnMidCtr.setObjectName(u"btnMidCtr")
        self.btnMidCtr.setMaximumSize(QSize(15, 15))
        self.btnMidCtr.setCheckable(True)
        self.btnMidCtr.setChecked(True)

        self.gridLayout.addWidget(self.btnMidCtr, 2, 3, 1, 1)

        self.btnMidLeft = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnMidLeft)
        self.btnMidLeft.setObjectName(u"btnMidLeft")
        self.btnMidLeft.setMaximumSize(QSize(15, 15))
        self.btnMidLeft.setCheckable(True)

        self.gridLayout.addWidget(self.btnMidLeft, 2, 2, 1, 1)

        self.btnTopLeft = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnTopLeft)
        self.btnTopLeft.setObjectName(u"btnTopLeft")
        self.btnTopLeft.setEnabled(True)
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.btnTopLeft.sizePolicy().hasHeightForWidth())
        self.btnTopLeft.setSizePolicy(sizePolicy2)
        self.btnTopLeft.setMaximumSize(QSize(15, 15))
        self.btnTopLeft.setCheckable(True)

        self.gridLayout.addWidget(self.btnTopLeft, 1, 2, 1, 1)

        self.btnTopRight = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnTopRight)
        self.btnTopRight.setObjectName(u"btnTopRight")
        self.btnTopRight.setMaximumSize(QSize(15, 15))
        self.btnTopRight.setCheckable(True)

        self.gridLayout.addWidget(self.btnTopRight, 1, 4, 1, 1)

        self.btnTopCtr = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnTopCtr)
        self.btnTopCtr.setObjectName(u"btnTopCtr")
        self.btnTopCtr.setMaximumSize(QSize(15, 15))
        self.btnTopCtr.setCheckable(True)

        self.gridLayout.addWidget(self.btnTopCtr, 1, 3, 1, 1)

        self.btnBotCtr = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnBotCtr)
        self.btnBotCtr.setObjectName(u"btnBotCtr")
        self.btnBotCtr.setMaximumSize(QSize(15, 15))
        self.btnBotCtr.setCheckable(True)

        self.gridLayout.addWidget(self.btnBotCtr, 3, 3, 1, 1)

        self.btnMidRight = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnMidRight)
        self.btnMidRight.setObjectName(u"btnMidRight")
        self.btnMidRight.setMaximumSize(QSize(15, 15))
        self.btnMidRight.setCheckable(True)

        self.gridLayout.addWidget(self.btnMidRight, 2, 4, 1, 1)

        self.btnBotLeft = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnBotLeft)
        self.btnBotLeft.setObjectName(u"btnBotLeft")
        self.btnBotLeft.setMaximumSize(QSize(15, 15))
        self.btnBotLeft.setCheckable(True)

        self.gridLayout.addWidget(self.btnBotLeft, 3, 2, 1, 1)

        self.btnBotRight = QPushButton(PropTextInspector)
        self.alignGroup.addButton(self.btnBotRight)
        self.btnBotRight.setObjectName(u"btnBotRight")
        self.btnBotRight.setMaximumSize(QSize(15, 15))
        self.btnBotRight.setCheckable(True)

        self.gridLayout.addWidget(self.btnBotRight, 3, 4, 1, 1)


        self.horizontalLayout_2.addLayout(self.gridLayout)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(PropTextInspector)
        self.cbVis.toggled.connect(self.cbShowName.setEnabled)

        QMetaObject.connectSlotsByName(PropTextInspector)
    # setupUi

    def retranslateUi(self, PropTextInspector):
        PropTextInspector.setWindowTitle(QCoreApplication.translate("PropTextInspector", u"Form", None))
        self.cbShowName.setText(QCoreApplication.translate("PropTextInspector", u"Show attribute name", None))
        self.label_3.setText(QCoreApplication.translate("PropTextInspector", u"Value", None))
        self.label.setText(QCoreApplication.translate("PropTextInspector", u"Attribute", None))
        self.cbVis.setText(QCoreApplication.translate("PropTextInspector", u"Visible", None))
        self.label_2.setText(QCoreApplication.translate("PropTextInspector", u"Alignment", None))
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

