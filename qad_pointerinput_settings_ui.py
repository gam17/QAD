# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\qad_pointerinput_settings.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_PointerInput_Settings_Dialog(object):
    def setupUi(self, PointerInput_Settings_Dialog):
        PointerInput_Settings_Dialog.setObjectName("PointerInput_Settings_Dialog")
        PointerInput_Settings_Dialog.resize(300, 356)
        PointerInput_Settings_Dialog.setMinimumSize(QtCore.QSize(300, 356))
        PointerInput_Settings_Dialog.setMaximumSize(QtCore.QSize(300, 356))
        self.groupBox = QtWidgets.QGroupBox(PointerInput_Settings_Dialog)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 281, 181))
        self.groupBox.setObjectName("groupBox")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(10, 20, 231, 41))
        self.label.setTextFormat(QtCore.Qt.AutoText)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.groupBox_3 = QtWidgets.QGroupBox(self.groupBox)
        self.groupBox_3.setGeometry(QtCore.QRect(10, 60, 261, 51))
        self.groupBox_3.setTitle("")
        self.groupBox_3.setObjectName("groupBox_3")
        self.radioPolarFmt = QtWidgets.QRadioButton(self.groupBox_3)
        self.radioPolarFmt.setGeometry(QtCore.QRect(10, 10, 241, 17))
        self.radioPolarFmt.setObjectName("radioPolarFmt")
        self.radioCartesianFmt = QtWidgets.QRadioButton(self.groupBox_3)
        self.radioCartesianFmt.setGeometry(QtCore.QRect(10, 30, 241, 17))
        self.radioCartesianFmt.setObjectName("radioCartesianFmt")
        self.groupBox_4 = QtWidgets.QGroupBox(self.groupBox)
        self.groupBox_4.setGeometry(QtCore.QRect(10, 120, 261, 51))
        self.groupBox_4.setTitle("")
        self.groupBox_4.setObjectName("groupBox_4")
        self.radioRelativeCoord = QtWidgets.QRadioButton(self.groupBox_4)
        self.radioRelativeCoord.setGeometry(QtCore.QRect(10, 10, 241, 17))
        self.radioRelativeCoord.setObjectName("radioRelativeCoord")
        self.radioAbsoluteCoord = QtWidgets.QRadioButton(self.groupBox_4)
        self.radioAbsoluteCoord.setGeometry(QtCore.QRect(10, 30, 241, 17))
        self.radioAbsoluteCoord.setObjectName("radioAbsoluteCoord")
        self.groupBox_2 = QtWidgets.QGroupBox(PointerInput_Settings_Dialog)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 210, 281, 101))
        self.groupBox_2.setObjectName("groupBox_2")
        self.radioVisAlways = QtWidgets.QRadioButton(self.groupBox_2)
        self.radioVisAlways.setGeometry(QtCore.QRect(10, 80, 261, 17))
        self.radioVisAlways.setObjectName("radioVisAlways")
        self.radioVisWhenAsksPt = QtWidgets.QRadioButton(self.groupBox_2)
        self.radioVisWhenAsksPt.setGeometry(QtCore.QRect(10, 60, 261, 17))
        self.radioVisWhenAsksPt.setObjectName("radioVisWhenAsksPt")
        self.label_2 = QtWidgets.QLabel(self.groupBox_2)
        self.label_2.setGeometry(QtCore.QRect(10, 20, 261, 31))
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName("label_2")
        self.layoutWidget = QtWidgets.QWidget(PointerInput_Settings_Dialog)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 320, 281, 30))
        self.layoutWidget.setObjectName("layoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.layoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.okButton = QtWidgets.QPushButton(self.layoutWidget)
        self.okButton.setObjectName("okButton")
        self.horizontalLayout.addWidget(self.okButton)
        self.cancelButton = QtWidgets.QPushButton(self.layoutWidget)
        self.cancelButton.setObjectName("cancelButton")
        self.horizontalLayout.addWidget(self.cancelButton)
        self.helpButton = QtWidgets.QPushButton(self.layoutWidget)
        self.helpButton.setObjectName("helpButton")
        self.horizontalLayout.addWidget(self.helpButton)

        self.retranslateUi(PointerInput_Settings_Dialog)
        self.okButton.clicked.connect(PointerInput_Settings_Dialog.ButtonBOX_Accepted) # type: ignore
        self.helpButton.clicked.connect(PointerInput_Settings_Dialog.ButtonHELP_Pressed) # type: ignore
        self.cancelButton.clicked.connect(PointerInput_Settings_Dialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(PointerInput_Settings_Dialog)

    def retranslateUi(self, PointerInput_Settings_Dialog):
        _translate = QtCore.QCoreApplication.translate
        PointerInput_Settings_Dialog.setWindowTitle(_translate("PointerInput_Settings_Dialog", "Pointer Input Settings"))
        self.groupBox.setTitle(_translate("PointerInput_Settings_Dialog", "Format"))
        self.label.setText(_translate("PointerInput_Settings_Dialog", "For second or next points, default to:"))
        self.radioPolarFmt.setToolTip(_translate("PointerInput_Settings_Dialog", "Displays the tooltip for the second or next point in polar coordinate format. Enter a comma (,) to change to Cartesian format. (DYNPIFORMAT system variable)"))
        self.radioPolarFmt.setText(_translate("PointerInput_Settings_Dialog", "Polar format"))
        self.radioCartesianFmt.setToolTip(_translate("PointerInput_Settings_Dialog", "Displays the tooltip for the second or next point in Cartesian coordinate format. Enter an angle symbol (<) to change to polar format. (DYNPIFORMAT system variable)"))
        self.radioCartesianFmt.setText(_translate("PointerInput_Settings_Dialog", "Cartesian format"))
        self.radioRelativeCoord.setToolTip(_translate("PointerInput_Settings_Dialog", "Displays the tooltip for the second or next point in relative coordinate format. Enter a pound sign (#) to change to absolute format. (DYNPICOORDS system variable)"))
        self.radioRelativeCoord.setText(_translate("PointerInput_Settings_Dialog", "Relative coordinates"))
        self.radioAbsoluteCoord.setToolTip(_translate("PointerInput_Settings_Dialog", "Displays the tooltip for the second or next point in absolute coordinate format. Enter an \"at\" sign (@) to change to relative coordinates format. (DYNPICOORDS system variable)"))
        self.radioAbsoluteCoord.setText(_translate("PointerInput_Settings_Dialog", "Absolute coordinates"))
        self.groupBox_2.setTitle(_translate("PointerInput_Settings_Dialog", "Visibility"))
        self.radioVisAlways.setToolTip(_translate("PointerInput_Settings_Dialog", "Always displays tooltips when pointer input is turned on. ( DYNPIVIS system variable)"))
        self.radioVisAlways.setText(_translate("PointerInput_Settings_Dialog", "Always - even when not in command"))
        self.radioVisWhenAsksPt.setToolTip(_translate("PointerInput_Settings_Dialog", "When pointer input is turned on, displays tooltips whenever a command prompts you for a point. (DYNPIVIS system variable)"))
        self.radioVisWhenAsksPt.setText(_translate("PointerInput_Settings_Dialog", "When a command asks for a point"))
        self.label_2.setText(_translate("PointerInput_Settings_Dialog", "Show coordinate tooltips:"))
        self.okButton.setText(_translate("PointerInput_Settings_Dialog", "OK"))
        self.cancelButton.setText(_translate("PointerInput_Settings_Dialog", "Cancel"))
        self.helpButton.setText(_translate("PointerInput_Settings_Dialog", "?"))
