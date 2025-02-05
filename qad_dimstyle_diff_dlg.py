# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire la dialog per DIMSTYLE
 
                              -------------------
        begin                : 2015-05-19
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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import Qt, QObject
from qgis.PyQt.QtWidgets import QDialog, QHeaderView, QTableWidgetItem, QApplication
from qgis.utils import *

from . import qad_dimstyle_diff_ui

from .qad_dim import QadDimStyles
from .qad_msg import QadMsg, qadShowPluginPDFHelp
from . import qad_utils


#######################################################################################
# Classe che gestisce l'interfaccia grafica della funzione di comparazione tra stili di quotatura
class QadDIMSTYLE_DIFF_Dialog(QDialog, QObject, qad_dimstyle_diff_ui.Ui_DimStyle_Diff_Dialog):
   def __init__(self, plugIn, parent, dimStyleName1 = None, dimStyleName2 = None):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()
      
      QDialog.__init__(self, parent)
      
      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
                 
      self.dimNameList = []
      for dimStyle in QadDimStyles.dimStyleList: # lista degli stili di quotatura caricati
         self.dimStyle1.addItem(dimStyle.name, dimStyle)
         self.dimStyle2.addItem(dimStyle.name, dimStyle)
      
      # sort
      self.dimStyle1.model().sort(0)
      self.dimStyle2.model().sort(0)

      # seleziono un elemento della lista
      if dimStyleName1 is not None:
         index = self.dimStyle1.findText(dimStyleName1)
         self.dimStyle1.setCurrentIndex(index)
      else:
         self.dimStyle1.setCurrentIndex(0)
      
      # seleziono un elemento della lista
      if dimStyleName2 is not None:
         index = self.dimStyle2.findText(dimStyleName2)
         self.dimStyle2.setCurrentIndex(index)
         self.DimStyleName2Changed(index)
      else:
         self.dimStyle2.setCurrentIndex(0)
         
   def DimStyleName1Changed(self, index):
      # leggo l'elemento selezionato
      dimStyle1 = self.dimStyle1.itemData(index)
      index = self.dimStyle2.currentIndex()
      dimStyle2 = self.dimStyle2.itemData(index) if index >= 0 else None
      self.showProps(dimStyle1, dimStyle2)

   def DimStyleName2Changed(self, index):
      # leggo l'elemento selezionato
      dimStyle2 = self.dimStyle2.itemData(index)
      index = self.dimStyle1.currentIndex()
      dimStyle1 = self.dimStyle1.itemData(index) if index >= 0 else None
      self.showProps(dimStyle1, dimStyle2)

   def showProps(self, dimStyle1, dimStyle2):
      self.tableWidget.clear()
      if dimStyle1 is None:
         return
     
      if dimStyle2 is None or dimStyle1.name == dimStyle2.name:
         self.showAllProps(dimStyle1)
      else:   
         self.showDiffProps(dimStyle1, dimStyle2)
      
   def showAllProps(self, dimStyle):
      if self.tableWidget.model() is not None:
         # Pulisce la tabella
         self.tableWidget.clear()
         self.tableWidget.setRowCount(0)
         
      self.tableWidget.setColumnCount(2)
      headerLabels = []
      headerLabels.append(QadMsg.translate("DimStyle_Diff_Dialog", "Description"))
      headerLabels.append(dimStyle.name)
      self.tableWidget.setHorizontalHeaderLabels(headerLabels)
      self.tableWidget.horizontalHeader().show()

      self.count = 0
      propsDict = dimStyle.getPropList().items()
      for prop in propsDict:
         propName = prop[0]
         propDescr = prop[1][0]
         propValue = prop[1][1]
         self.insertProp(propDescr, propValue)
      
      self.tableWidget.sortItems(0)

      self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
      self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
           
      self.msg.setText(QadMsg.translate("DimStyle_Diff_Dialog", "All properties of dimension style: ") + dimStyle.name)


   def showDiffProps(self, dimStyle1, dimStyle2):
      if self.tableWidget.model() is not None:
         # Pulisce la tabella
         self.tableWidget.clear()
         self.tableWidget.setRowCount(0)
      
      self.tableWidget.setColumnCount(3)
      headerLabels = []
      headerLabels.append(QadMsg.translate("DimStyle_Diff_Dialog", "Description"))
      headerLabels.append(dimStyle1.name)
      headerLabels.append(dimStyle2.name)
      self.tableWidget.setHorizontalHeaderLabels(headerLabels)
      self.tableWidget.horizontalHeader().show()
      
      self.count = 0
      prop1Items = dimStyle1.getPropList().items() # lista di nome con lista [descrizione, valore]
      props2Dict = dimStyle2.getPropList() # dizionario di nome con lista [descrizione, valore]
      for prop1 in prop1Items:
         propName = prop1[0]
         propDescr = prop1[1][0]
         prop1Value = prop1[1][1]
         prop2 = props2Dict[propName]
         prop2Value = prop2[1]
         if prop1Value is None:
            prop1Value = ""
         if prop2Value is None:
            prop2Value = ""
         if unicode(prop1Value) != unicode(prop2Value):
            self.insertProp(propDescr, prop1Value, prop2Value)
      
      self.tableWidget.sortItems(0)
      
      self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
      self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
      self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
           
      self.msg.setText(QadMsg.translate("DimStyle_Diff_Dialog", "Found {0} differences: ").format(str(self.count)))


   def insertProp(self, description, val1, val2 = None):
      self.tableWidget.insertRow(self.count)
      
      item = QTableWidgetItem(unicode(description))
      item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
      self.tableWidget.setItem(self.count, 0, item)
      
      item = QTableWidgetItem(unicode(val1))
      item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
      self.tableWidget.setItem(self.count, 1, item)
      
      if val2 is not None:
         item = QTableWidgetItem(unicode(val2))
         item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
         self.tableWidget.setItem(self.count, 2, item)
      self.count += 1
      
   
   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "Dimensioning"))

   def resizeEvent(self, event):
      QDialog.resizeEvent(self, event)
      if event.oldSize().width() == -1: # non c'era una dimensione precedente
         return
      tableWidgetSize = self.tableWidget.size()
      newWidth = tableWidgetSize.width() + event.size().width() - event.oldSize().width()
      newHeight = tableWidgetSize.height() + event.size().height() - event.oldSize().height()
      tableWidgetSize.setWidth(newWidth)
      tableWidgetSize.setHeight(newHeight)      
      self.tableWidget.resize(tableWidgetSize)
      
   
   def copyToClipboard(self):
      buffer = ""
      
      # intestazione
      for col in range(0, self.tableWidget.columnCount(), 1):
         if col > 0:
            buffer += '\t' # aggiungo un TAB
         buffer += self.tableWidget.horizontalHeaderItem(col).text()
      buffer += '\n' # vado a capo
      
      # valori delle righe
      for row in range(0, self.tableWidget.rowCount(), 1):
         for col in range(0, self.tableWidget.columnCount(), 1):
            if col > 0:
               buffer += '\t' # aggiungo un TAB
            buffer += self.tableWidget.item(row, col).text()
         buffer += '\n' # vado a capo

      QApplication.clipboard().setText(buffer)
      