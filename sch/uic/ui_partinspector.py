# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './ui/PartInspector.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_PartInspector(object):
    def setupUi(self, PartInspector):
        PartInspector.setObjectName("PartInspector")
        PartInspector.resize(221, 252)
        self.verticalLayout = QtWidgets.QVBoxLayout(PartInspector)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_3 = QtWidgets.QLabel(PartInspector)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.masterList = QtWidgets.QListWidget(PartInspector)
        self.masterList.setObjectName("masterList")
        self.verticalLayout.addWidget(self.masterList)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(PartInspector)
        QtCore.QMetaObject.connectSlotsByName(PartInspector)

    def retranslateUi(self, PartInspector):
        _translate = QtCore.QCoreApplication.translate
        PartInspector.setWindowTitle(_translate("PartInspector", "Form"))
        self.label_3.setText(_translate("PartInspector", "Part master"))

