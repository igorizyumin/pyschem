# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PartInspector.ui'
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
from PySide6.QtWidgets import (QApplication, QButtonGroup, QLabel, QListWidget,
    QListWidgetItem, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_PartInspector(object):
    def setupUi(self, PartInspector):
        if not PartInspector.objectName():
            PartInspector.setObjectName(u"PartInspector")
        PartInspector.resize(221, 252)
        self.verticalLayout = QVBoxLayout(PartInspector)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_3 = QLabel(PartInspector)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout.addWidget(self.label_3)

        self.masterList = QListWidget(PartInspector)
        self.masterList.setObjectName(u"masterList")

        self.verticalLayout.addWidget(self.masterList)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(PartInspector)

        QMetaObject.connectSlotsByName(PartInspector)
    # setupUi

    def retranslateUi(self, PartInspector):
        PartInspector.setWindowTitle(QCoreApplication.translate("PartInspector", u"Form", None))
        self.label_3.setText(QCoreApplication.translate("PartInspector", u"Part master", None))
    # retranslateUi

