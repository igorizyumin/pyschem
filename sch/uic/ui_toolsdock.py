# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ToolsDock.ui'
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
from PySide6.QtWidgets import (QApplication, QDockWidget, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_ToolsDock(object):
    def setupUi(self, ToolsDock):
        if not ToolsDock.objectName():
            ToolsDock.setObjectName(u"ToolsDock")
        ToolsDock.resize(103, 215)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ToolsDock.sizePolicy().hasHeightForWidth())
        ToolsDock.setSizePolicy(sizePolicy)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.selectBtn = QPushButton(self.dockWidgetContents)
        self.selectBtn.setObjectName(u"selectBtn")
        self.selectBtn.setCheckable(True)
        self.selectBtn.setChecked(True)
        self.selectBtn.setAutoExclusive(True)

        self.verticalLayout.addWidget(self.selectBtn)

        self.lineBtn = QPushButton(self.dockWidgetContents)
        self.lineBtn.setObjectName(u"lineBtn")
        self.lineBtn.setCheckable(True)
        self.lineBtn.setAutoExclusive(True)
        self.lineBtn.setFlat(False)

        self.verticalLayout.addWidget(self.lineBtn)

        self.netBtn = QPushButton(self.dockWidgetContents)
        self.netBtn.setObjectName(u"netBtn")
        self.netBtn.setCheckable(True)
        self.netBtn.setAutoExclusive(True)
        self.netBtn.setFlat(False)

        self.verticalLayout.addWidget(self.netBtn)

        self.textBtn = QPushButton(self.dockWidgetContents)
        self.textBtn.setObjectName(u"textBtn")
        self.textBtn.setCheckable(True)
        self.textBtn.setAutoExclusive(True)
        self.textBtn.setFlat(False)

        self.verticalLayout.addWidget(self.textBtn)

        self.partBtn = QPushButton(self.dockWidgetContents)
        self.partBtn.setObjectName(u"partBtn")
        self.partBtn.setCheckable(True)
        self.partBtn.setAutoExclusive(True)
        self.partBtn.setFlat(False)

        self.verticalLayout.addWidget(self.partBtn)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        ToolsDock.setWidget(self.dockWidgetContents)

        self.retranslateUi(ToolsDock)

        QMetaObject.connectSlotsByName(ToolsDock)
    # setupUi

    def retranslateUi(self, ToolsDock):
        ToolsDock.setWindowTitle(QCoreApplication.translate("ToolsDock", u"Tools", None))
        self.selectBtn.setText(QCoreApplication.translate("ToolsDock", u"Select", None))
        self.lineBtn.setText(QCoreApplication.translate("ToolsDock", u"Draw Line", None))
        self.netBtn.setText(QCoreApplication.translate("ToolsDock", u"Draw Net", None))
        self.textBtn.setText(QCoreApplication.translate("ToolsDock", u"Add Text", None))
        self.partBtn.setText(QCoreApplication.translate("ToolsDock", u"Add Part", None))
    # retranslateUi

