# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'InspectorDock.ui'
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

class Ui_InspectorDock(object):
    def setupUi(self, InspectorDock):
        if not InspectorDock.objectName():
            InspectorDock.setObjectName(u"InspectorDock")
        InspectorDock.resize(236, 312)
        InspectorDock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.contents = QWidget()
        self.contents.setObjectName(u"contents")
        self.verticalLayout = QVBoxLayout(self.contents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        InspectorDock.setWidget(self.contents)

        self.retranslateUi(InspectorDock)

        QMetaObject.connectSlotsByName(InspectorDock)
    # setupUi

    def retranslateUi(self, InspectorDock):
        InspectorDock.setWindowTitle(QCoreApplication.translate("InspectorDock", u"Object Properties", None))
    # retranslateUi

