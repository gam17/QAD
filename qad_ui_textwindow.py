# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

                              -------------------
        begin                : 2013-05-22
        copyright            : iiiii
        email                : hhhhh
        developers           : bbbbb aaaaa ggggg
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""


from PyQt5 import QtCore, QtGui
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from .qad_msg import QadMsg


class Ui_QadTextWindow(object):
    def setupUi(self, QadTextWindow):
        #QadTextWindow.setObjectName("QadTextWindow")
        QadTextWindow.setWindowModality(QtCore.Qt.NonModal)
        QadTextWindow.setEnabled(True)
        QadTextWindow.resize(642, 193)
        QadTextWindow.setMinimumSize(100, 20)
        QadTextWindow.setMaximumSize(QtCore.QSize(524287, 524287))
                
        self.retranslateUi(QadTextWindow)
        QtCore.QMetaObject.connectSlotsByName(QadTextWindow)

    def retranslateUi(self, QadTextWindow):
       QadTextWindow.setWindowTitle(QadMsg.translate("Text_window", "Text window"))

class Ui_QadCmdSuggestWindow(object):
    def setupUi(self, QadCmdSuggestWindow):
        QadCmdSuggestWindow.setObjectName("QadCmdsListWindow")
        QadCmdSuggestWindow.setWindowModality(QtCore.Qt.NonModal)
        QadCmdSuggestWindow.setEnabled(True)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName("QadCmdsListWindowDockWidgetContents")
        self.vboxlayout = QVBoxLayout(self.dockWidgetContents)
        self.vboxlayout.setObjectName("QadCmdsListWindowVBoxLayout")
        self.vboxlayout.setMargin(0)
        QadCmdSuggestWindow.setLayout(self.vboxlayout)        
        QtCore.QMetaObject.connectSlotsByName(QadCmdSuggestWindow)


