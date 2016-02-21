# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/InspectorDock.ui'
#
# Created: Sat Feb 20 18:01:56 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_InspectorDock(object):
    def setupUi(self, InspectorDock):
        InspectorDock.setObjectName("InspectorDock")
        InspectorDock.resize(236, 312)
        InspectorDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.contents = QtWidgets.QWidget()
        self.contents.setObjectName("contents")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.contents)
        self.verticalLayout.setObjectName("verticalLayout")
        InspectorDock.setWidget(self.contents)

        self.retranslateUi(InspectorDock)
        QtCore.QMetaObject.connectSlotsByName(InspectorDock)

    def retranslateUi(self, InspectorDock):
        _translate = QtCore.QCoreApplication.translate
        InspectorDock.setWindowTitle(_translate("InspectorDock", "Object Properties"))

