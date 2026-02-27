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
from PySide6.QtWidgets import (QApplication, QDockWidget, QSizePolicy, QVBoxLayout,
    QWidget)

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
        ToolsDock.setWidget(self.dockWidgetContents)

        self.retranslateUi(ToolsDock)

        QMetaObject.connectSlotsByName(ToolsDock)
    # setupUi

    def retranslateUi(self, ToolsDock):
        ToolsDock.setWindowTitle(QCoreApplication.translate("ToolsDock", u"Tools", None))
    # retranslateUi

