# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ProjectDock.ui'
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
from PySide6.QtWidgets import (QApplication, QDockWidget, QHeaderView, QSizePolicy,
    QTreeView, QVBoxLayout, QWidget)

class Ui_ProjectDock(object):
    def setupUi(self, ProjectDock):
        if not ProjectDock.objectName():
            ProjectDock.setObjectName(u"ProjectDock")
        ProjectDock.resize(147, 261)
        ProjectDock.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        ProjectDock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_2 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.projectTree = QTreeView(self.dockWidgetContents)
        self.projectTree.setObjectName(u"projectTree")
        self.projectTree.setAllColumnsShowFocus(False)
        self.projectTree.setExpandsOnDoubleClick(False)
        self.projectTree.header().setVisible(False)

        self.verticalLayout_2.addWidget(self.projectTree)

        ProjectDock.setWidget(self.dockWidgetContents)

        self.retranslateUi(ProjectDock)

        QMetaObject.connectSlotsByName(ProjectDock)
    # setupUi

    def retranslateUi(self, ProjectDock):
        ProjectDock.setWindowTitle(QCoreApplication.translate("ProjectDock", u"Project", None))
    # retranslateUi

