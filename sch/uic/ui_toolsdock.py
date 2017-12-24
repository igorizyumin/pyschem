# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './ui/ToolsDock.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ToolsDock(object):
    def setupUi(self, ToolsDock):
        ToolsDock.setObjectName("ToolsDock")
        ToolsDock.resize(103, 215)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ToolsDock.sizePolicy().hasHeightForWidth())
        ToolsDock.setSizePolicy(sizePolicy)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName("verticalLayout")
        # self.selectBtn = QtWidgets.QPushButton(self.dockWidgetContents)
        # self.selectBtn.setCheckable(True)
        # self.selectBtn.setChecked(True)
        # self.selectBtn.setAutoExclusive(True)
        # self.selectBtn.setObjectName("selectBtn")
        # self.verticalLayout.addWidget(self.selectBtn)
        # self.lineBtn = QtWidgets.QPushButton(self.dockWidgetContents)
        # self.lineBtn.setCheckable(True)
        # self.lineBtn.setAutoExclusive(True)
        # self.lineBtn.setFlat(False)
        # self.lineBtn.setObjectName("lineBtn")
        # self.verticalLayout.addWidget(self.lineBtn)
        # self.netBtn = QtWidgets.QPushButton(self.dockWidgetContents)
        # self.netBtn.setCheckable(True)
        # self.netBtn.setAutoExclusive(True)
        # self.netBtn.setFlat(False)
        # self.netBtn.setObjectName("netBtn")
        # self.verticalLayout.addWidget(self.netBtn)
        # self.textBtn = QtWidgets.QPushButton(self.dockWidgetContents)
        # self.textBtn.setCheckable(True)
        # self.textBtn.setAutoExclusive(True)
        # self.textBtn.setFlat(False)
        # self.textBtn.setObjectName("textBtn")
        # self.verticalLayout.addWidget(self.textBtn)
        # self.partBtn = QtWidgets.QPushButton(self.dockWidgetContents)
        # self.partBtn.setCheckable(True)
        # self.partBtn.setAutoExclusive(True)
        # self.partBtn.setFlat(False)
        # self.partBtn.setObjectName("partBtn")
        # self.verticalLayout.addWidget(self.partBtn)
        # spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        # self.verticalLayout.addItem(spacerItem)
        ToolsDock.setWidget(self.dockWidgetContents)

        self.retranslateUi(ToolsDock)
        QtCore.QMetaObject.connectSlotsByName(ToolsDock)

    def retranslateUi(self, ToolsDock):
        _translate = QtCore.QCoreApplication.translate
        ToolsDock.setWindowTitle(_translate("ToolsDock", "Tools"))
        #self.selectBtn.setText(_translate("ToolsDock", "Select"))
        #self.lineBtn.setText(_translate("ToolsDock", "Draw Line"))
        #self.netBtn.setText(_translate("ToolsDock", "Draw Net"))
        #self.textBtn.setText(_translate("ToolsDock", "Add Text"))
        #self.partBtn.setText(_translate("ToolsDock", "Add Part"))

