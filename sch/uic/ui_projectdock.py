# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/ProjectDock.ui'
#
# Created: Sat Feb 20 17:41:17 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ProjectDock(object):
    def setupUi(self, ProjectDock):
        ProjectDock.setObjectName("ProjectDock")
        ProjectDock.resize(147, 261)
        ProjectDock.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable|QtWidgets.QDockWidget.DockWidgetMovable)
        ProjectDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.projectTree = QtWidgets.QTreeView(self.dockWidgetContents)
        self.projectTree.setAllColumnsShowFocus(False)
        self.projectTree.setExpandsOnDoubleClick(False)
        self.projectTree.setObjectName("projectTree")
        self.projectTree.header().setVisible(False)
        self.verticalLayout_2.addWidget(self.projectTree)
        ProjectDock.setWidget(self.dockWidgetContents)

        self.retranslateUi(ProjectDock)
        QtCore.QMetaObject.connectSlotsByName(ProjectDock)

    def retranslateUi(self, ProjectDock):
        _translate = QtCore.QCoreApplication.translate
        ProjectDock.setWindowTitle(_translate("ProjectDock", "Project"))

