# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/TextInspector.ui'
#
# Created: Sat Feb 20 19:51:52 2016
#      by: PyQt5 UI code generator 5.2.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_TextInspector(object):
    def setupUi(self, TextInspector):
        TextInspector.setObjectName("TextInspector")
        TextInspector.resize(221, 252)
        self.verticalLayout = QtWidgets.QVBoxLayout(TextInspector)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(TextInspector)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.text = QtWidgets.QLineEdit(TextInspector)
        self.text.setObjectName("text")
        self.horizontalLayout.addWidget(self.text)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.fontFace = QtWidgets.QFontComboBox(TextInspector)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fontFace.sizePolicy().hasHeightForWidth())
        self.fontFace.setSizePolicy(sizePolicy)
        self.fontFace.setMinimumSize(QtCore.QSize(100, 0))
        self.fontFace.setMaxVisibleItems(99)
        self.fontFace.setObjectName("fontFace")
        self.horizontalLayout_3.addWidget(self.fontFace)
        self.fontSize = QtWidgets.QComboBox(TextInspector)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fontSize.sizePolicy().hasHeightForWidth())
        self.fontSize.setSizePolicy(sizePolicy)
        self.fontSize.setEditable(True)
        self.fontSize.setObjectName("fontSize")
        self.horizontalLayout_3.addWidget(self.fontSize)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(TextInspector)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setSpacing(4)
        self.gridLayout.setObjectName("gridLayout")
        self.btnMidCtr = QtWidgets.QPushButton(TextInspector)
        self.btnMidCtr.setMaximumSize(QtCore.QSize(15, 15))
        self.btnMidCtr.setText("")
        self.btnMidCtr.setCheckable(True)
        self.btnMidCtr.setChecked(True)
        self.btnMidCtr.setObjectName("btnMidCtr")
        self.alignGroup = QtWidgets.QButtonGroup(TextInspector)
        self.alignGroup.setObjectName("alignGroup")
        self.alignGroup.addButton(self.btnMidCtr)
        self.gridLayout.addWidget(self.btnMidCtr, 2, 3, 1, 1)
        self.btnMidLeft = QtWidgets.QPushButton(TextInspector)
        self.btnMidLeft.setMaximumSize(QtCore.QSize(15, 15))
        self.btnMidLeft.setText("")
        self.btnMidLeft.setCheckable(True)
        self.btnMidLeft.setObjectName("btnMidLeft")
        self.alignGroup.addButton(self.btnMidLeft)
        self.gridLayout.addWidget(self.btnMidLeft, 2, 2, 1, 1)
        self.btnTopLeft = QtWidgets.QPushButton(TextInspector)
        self.btnTopLeft.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btnTopLeft.sizePolicy().hasHeightForWidth())
        self.btnTopLeft.setSizePolicy(sizePolicy)
        self.btnTopLeft.setMaximumSize(QtCore.QSize(15, 15))
        self.btnTopLeft.setText("")
        self.btnTopLeft.setCheckable(True)
        self.btnTopLeft.setObjectName("btnTopLeft")
        self.alignGroup.addButton(self.btnTopLeft)
        self.gridLayout.addWidget(self.btnTopLeft, 1, 2, 1, 1)
        self.btnTopRight = QtWidgets.QPushButton(TextInspector)
        self.btnTopRight.setMaximumSize(QtCore.QSize(15, 15))
        self.btnTopRight.setText("")
        self.btnTopRight.setCheckable(True)
        self.btnTopRight.setObjectName("btnTopRight")
        self.alignGroup.addButton(self.btnTopRight)
        self.gridLayout.addWidget(self.btnTopRight, 1, 4, 1, 1)
        self.btnTopCtr = QtWidgets.QPushButton(TextInspector)
        self.btnTopCtr.setMaximumSize(QtCore.QSize(15, 15))
        self.btnTopCtr.setText("")
        self.btnTopCtr.setCheckable(True)
        self.btnTopCtr.setObjectName("btnTopCtr")
        self.alignGroup.addButton(self.btnTopCtr)
        self.gridLayout.addWidget(self.btnTopCtr, 1, 3, 1, 1)
        self.btnBotCtr = QtWidgets.QPushButton(TextInspector)
        self.btnBotCtr.setMaximumSize(QtCore.QSize(15, 15))
        self.btnBotCtr.setText("")
        self.btnBotCtr.setCheckable(True)
        self.btnBotCtr.setObjectName("btnBotCtr")
        self.alignGroup.addButton(self.btnBotCtr)
        self.gridLayout.addWidget(self.btnBotCtr, 3, 3, 1, 1)
        self.btnMidRight = QtWidgets.QPushButton(TextInspector)
        self.btnMidRight.setMaximumSize(QtCore.QSize(15, 15))
        self.btnMidRight.setText("")
        self.btnMidRight.setCheckable(True)
        self.btnMidRight.setObjectName("btnMidRight")
        self.alignGroup.addButton(self.btnMidRight)
        self.gridLayout.addWidget(self.btnMidRight, 2, 4, 1, 1)
        self.btnBotLeft = QtWidgets.QPushButton(TextInspector)
        self.btnBotLeft.setMaximumSize(QtCore.QSize(15, 15))
        self.btnBotLeft.setText("")
        self.btnBotLeft.setCheckable(True)
        self.btnBotLeft.setObjectName("btnBotLeft")
        self.alignGroup.addButton(self.btnBotLeft)
        self.gridLayout.addWidget(self.btnBotLeft, 3, 2, 1, 1)
        self.btnBotRight = QtWidgets.QPushButton(TextInspector)
        self.btnBotRight.setMaximumSize(QtCore.QSize(15, 15))
        self.btnBotRight.setText("")
        self.btnBotRight.setCheckable(True)
        self.btnBotRight.setObjectName("btnBotRight")
        self.alignGroup.addButton(self.btnBotRight)
        self.gridLayout.addWidget(self.btnBotRight, 3, 4, 1, 1)
        self.horizontalLayout_2.addLayout(self.gridLayout)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)

        self.retranslateUi(TextInspector)
        QtCore.QMetaObject.connectSlotsByName(TextInspector)

    def retranslateUi(self, TextInspector):
        _translate = QtCore.QCoreApplication.translate
        TextInspector.setWindowTitle(_translate("TextInspector", "Form"))
        self.label.setText(_translate("TextInspector", "Text"))
        self.label_2.setText(_translate("TextInspector", "Alignment"))

