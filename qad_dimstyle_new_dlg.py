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
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from . import qad_dimstyle_new_ui
from .qad_dimstyle_details_dlg import QadDIMSTYLE_DETAILS_Dialog

from .qad_dim import QadDimStyle, QadDimStyles
from .qad_msg import QadMsg, qadShowPluginPDFHelp
from . import qad_utils


#######################################################################################
# Classe che gestisce l'interfaccia grafica della funzione di creazione nuovo stile
class QadDIMSTYLE_NEW_Dialog(QDialog, QObject, qad_dimstyle_new_ui.Ui_DimStyle_New_Dialog):
   def __init__(self, plugIn, parent, fromDimStyleName = None):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self, parent)
      
      self.newDimStyle = QadDimStyle()
      self.newDimStyleNameChanged = False
      
      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
                 
      self.dimNameList = []
      for dimStyle in QadDimStyles.dimStyleList: # lista degli stili di quotatura caricati
         self.DimStyleNameFrom.addItem(dimStyle.name, dimStyle)
         self.dimNameList.append(dimStyle.name)
      
      # sort
      self.DimStyleNameFrom.model().sort(0)

      # seleziono un elemento della lista
      if fromDimStyleName is not None:
         index = self.DimStyleNameFrom.findText(fromDimStyleName)
         self.DimStyleNameFrom.setCurrentIndex(index)
         self.DimStyleNameFromChanged(index)
      
   def DimStyleNameFromChanged(self, index):
      # leggo l'elemento selezionato
      dimStyle = self.DimStyleNameFrom.itemData(index)
      if dimStyle is not None:
         self.newDimStyle.set(dimStyle)
         if self.newDimStyleNameChanged == False:
            newName = qad_utils.checkUniqueNewName(dimStyle.name, self.dimNameList, QadMsg.translate("QAD", "Copy of "))
            if newName is not None:
               self.newDimStyleName.setText(newName)

   def newStyleNameChanged(self, text):
      self.newDimStyleNameChanged = True
         
   def ButtonBOX_continue(self):
      if self.newDimStyleName.text() in self.dimNameList:
         QMessageBox.critical(self, QadMsg.getQADTitle(), \
                              QadMsg.translate("DimStyle_Dialog", "Dimension style name already existing. Specify a different name."))
         return False
      self.newDimStyle.name = self.newDimStyleName.text()
      self.newDimStyle.description = self.newDimStyleDescr.text()
      Form = QadDIMSTYLE_DETAILS_Dialog(self.plugIn, self, self.newDimStyle)
      title = QadMsg.translate("DimStyle_Dialog", "New dimension style: ") + self.newDimStyle.name
      Form.setWindowTitle(QadMsg.getQADTitle() + " - " + title)
      
      if Form.exec_() == QDialog.Accepted:
         self.dimStyle = Form.dimStyle
         QDialog.accept(self)
      else:
         self.dimStyle = None
         QDialog.reject(self)      

   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "Dimensioning"))
