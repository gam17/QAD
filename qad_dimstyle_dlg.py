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
from qgis.PyQt.QtCore import Qt, QObject, QItemSelectionModel
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QInputDialog, QMenu, QAction


from . import qad_dimstyle_ui
from .qad_variables import QadVariables
from .qad_dim import QadDimStyles
from .qad_msg import QadMsg, qadShowPluginPDFHelp
from .qad_dimstyle_new_dlg import QadDIMSTYLE_NEW_Dialog
from .qad_dimstyle_details_dlg import QadDIMSTYLE_DETAILS_Dialog, QadPreviewDim
from .qad_dimstyle_diff_dlg import QadDIMSTYLE_DIFF_Dialog
from . import qad_utils


#######################################################################################
# Classe che gestisce l'interfaccia grafica del comando DIMSTYLE
class QadDIMSTYLEDialog(QDialog, QObject, qad_dimstyle_ui.Ui_DimStyle_Dialog):
   def __init__(self, plugIn):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self)
      # non passo il parent perchè altrimenti il font e la sua dimensione verrebbero ereditati dalla dialog scombinando tutto 
      #QDialog.__init__(self, self.iface)
      
      self.selectedDimStyle = None
      
      self.setupUi(self)
      self.retranslateUi(self) # aggiungo alcune traduzioni personalizzate
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      
      self.dimStyleList.setContextMenuPolicy(Qt.CustomContextMenu)
      
      # aggiungo il canvans di preview della quota chiamato QadPreviewDim 
      # che eredita la posizione di previewDummy (che viene nascosto)      
      self.previewDummy.setHidden(True)
      self.previewDim = QadPreviewDim(self.previewDummy.parent(), self.plugIn)
      self.previewDim.setGeometry(self.previewDummy.geometry())
      self.previewDim.setObjectName("previewDim")
      
      self.init()


   def closeEvent(self, event):
      del self.previewDim # cancello il canvans di preview della quota chiamato QadPreviewDim 
      return QDialog.closeEvent(self, event)

   def init(self):
      # Inizializzazione dello stile corrente
      currDimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      self.currentDimStyle.setText("" if currDimStyleName is None else currDimStyleName)
      
      # Inizializzazione della lista degli stili
      model = QStandardItemModel(self.dimStyleList)
      for dimStyle in QadDimStyles.dimStyleList: # lista degli stili di quotatura caricati
         # Create an item with a caption
         item = QStandardItem(dimStyle.name)
         item.setEditable(True)
         item.setData(dimStyle)
         model.appendRow(item)

      self.dimStyleList.setModel(model)
      # sort
      self.dimStyleList.model().sort(0)
      # collego l'evento "cambio di selezione" alla funzione dimStyleListCurrentChanged
      self.dimStyleList.selectionModel().selectionChanged.connect(self.dimStyleListCurrentChanged)
      
      self.dimStyleList.itemDelegate().closeEditor.connect(self.dimStyleListcloseEditor)
      
      # seleziono il primo elemento della lista
      index = self.dimStyleList.model().index(0,0)
      items = None
      if self.selectedDimStyle is not None:
         # seleziono l'elemento precedentemente selezionato
         items = self.dimStyleList.model().findItems(self.selectedDimStyle.name)
      elif len(currDimStyleName) > 0:
         items = self.dimStyleList.model().findItems(currDimStyleName)
         
      if (items is not None) and len(items) > 0:
         item = items[0]
         if item is not None:
            index = self.dimStyleList.model().indexFromItem(item)
         
      self.dimStyleList.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectCurrent)

   
   def retranslateUi(self, DimStyle_Dialog):
      qad_dimstyle_ui.Ui_DimStyle_Dialog.retranslateUi(self, self)
      # "none" viene tradotto in italiano in "nessuno" nel contesto "currentDimStyle"
      # "none" viene tradotto in italiano in "nessuna" nel contesto "descriptionSelectedStyle"
      # "none" viene tradotto in italiano in "nessuno" nel contesto "selectedStyle"
      self.currentDimStyle.setText(QadMsg.translate("DimStyle_Dialog", "none", "currentDimStyle"))
      self.descriptionSelectedStyle.setText(QadMsg.translate("DimStyle_Dialog", "none", "descriptionSelectedStyle"))
      self.selectedStyle.setText(QadMsg.translate("DimStyle_Dialog", "none", "selectedStyle"))
      
      
   def dimStyleListCurrentChanged(self, current, previous):
      # leggo l'elemento selezionato
      index = current.indexes()[0]
      item = self.dimStyleList.model().itemFromIndex(index)
      self.selectedDimStyle = item.data()
      self.selectedStyle.setText(self.selectedDimStyle.name)
      self.descriptionSelectedStyle.setText(self.selectedDimStyle.description)
      
      self.previewDim.drawDim(self.selectedDimStyle)


   def dimStyleListcloseEditor(self, editor, hint):
      self.renSelectedDimStyle(editor.text())

   def setCurrentStyle(self):
      if self.selectedDimStyle is None:
         return
      QadVariables.set(QadMsg.translate("Environment variables", "DIMSTYLE"), self.selectedDimStyle.name)
      QadVariables.save()
      self.currentDimStyle.setText(self.selectedDimStyle.name)

   def renSelectedDimStyle(self, newName):
      if self.selectedDimStyle is None:
         return
      if QadDimStyles.renameDimStyle(self.selectedDimStyle.name, newName) == False:
         QMessageBox.critical(self, QadMsg.getQADTitle(), \
                              QadMsg.translate("DimStyle_Dialog", "Dimension style not renamed."))
      else:
         self.init()

   def updDescrSelectedDimStyle(self):
      if self.selectedDimStyle is None:
         return
      title = QadMsg.translate("DimStyle_Dialog", "Editing dimension style description: ") + self.selectedDimStyle.name
      inputDlg = QInputDialog(self)
      inputDlg.setWindowTitle(QadMsg.getQADTitle() + " - " + title)                 
      inputDlg.setInputMode(QInputDialog.TextInput) 
      inputDlg.setLabelText(QadMsg.translate("DimStyle_Dialog", "New description:"))
      inputDlg.setTextValue(self.selectedDimStyle.description)
      inputDlg.resize(600,100)                             
      if inputDlg.exec_():                         
         self.selectedDimStyle.description = inputDlg.textValue()      
         self.selectedDimStyle.save()
         self.init()
         
   def delSelectedDimStyle(self):
      if self.selectedDimStyle is None:
         return
      msg = QadMsg.translate("DimStyle_Dialog", "Remove dimension style {0} ?").format(self.selectedDimStyle.name)
      res = QMessageBox.question(self, QadMsg.getQADTitle(), msg, \
                                 QMessageBox.Yes | QMessageBox.No)
      if res == QMessageBox.Yes:
         if QadDimStyles.removeDimStyle(self.selectedDimStyle.name, True) == False:
            QMessageBox.critical(self, QadMsg.getQADTitle(), \
                                 QadMsg.translate("DimStyle_Dialog", "Dimension style not removed."))
         else:
            self.selectedDimStyle = None
            self.init()

   def createNewStyle(self):
      self.previewDim.eraseDim()

      Form = QadDIMSTYLE_NEW_Dialog(self.plugIn, self, self.selectedDimStyle.name if self.selectedDimStyle is not None else None)
      if Form.exec_() == QDialog.Accepted:
         Form.dimStyle.path = ""
         QadDimStyles.addDimStyle(Form.dimStyle, True)
         self.selectedDimStyle = QadDimStyles.findDimStyle(Form.dimStyle.name)
         # setto lo stile corrente
         QadVariables.set(QadMsg.translate("Environment variables", "DIMSTYLE"), self.selectedDimStyle.name)
         self.init()      
      
      self.previewDim.drawDim(self.selectedDimStyle)

   def modStyle(self):
      if self.selectedDimStyle is None:
         return
      self.previewDim.eraseDim()
      
      Form = QadDIMSTYLE_DETAILS_Dialog(self.plugIn, self, self.selectedDimStyle)
      title = QadMsg.translate("DimStyle_Dialog", "Modify dimension style: ") + self.selectedDimStyle.name
      Form.setWindowTitle(QadMsg.getQADTitle() + " - " + title)
      if Form.exec_() == QDialog.Accepted:
         self.selectedDimStyle.set(Form.dimStyle)
         self.selectedDimStyle.save()
         self.init()
      del Form # forzo la chiamata al distruttore per rimuovere il preview della quota
      
      self.previewDim.drawDim(self.selectedDimStyle)


   def temporaryModStyle(self):
      if self.selectedDimStyle is None:
         return
      self.previewDim.eraseDim()

      Form = QadDIMSTYLE_DETAILS_Dialog(self.plugIn, self, self.selectedDimStyle)
      title = QadMsg.translate("DimStyle_Dialog", "Set temporary overrides to dimension style: ") + self.selectedDimStyle.name
      Form.setWindowTitle(QadMsg.getQADTitle() + " - " + title)
      if Form.exec_() == QDialog.Accepted:
         self.selectedDimStyle.set(Form.dimStyle)
         self.init()
         
      self.previewDim.drawDim(self.selectedDimStyle)


   def showDiffBetweenStyles(self):
      if self.selectedDimStyle is None:
         return
      Form = QadDIMSTYLE_DIFF_Dialog(self.plugIn, self, self.selectedDimStyle.name)
      Form.exec_()


   # ============================================================================
   # startEditingItem
   # ============================================================================
   def startEditingItem(self):
      if self.selectedDimStyle is None:
         return

      items = self.dimStyleList.model().findItems(self.selectedDimStyle.name)
      if len(items) > 0:
         item = items[0]
         if item is not None:
            index = self.dimStyleList.model().indexFromItem(item)
            self.dimStyleList.edit(index)

            
   def ButtonBOX_Accepted(self):
      QDialog.accept(self)


   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "Dimensioning"))


   # ============================================================================
   # displayPopupMenu
   # ============================================================================
   def displayPopupMenu(self, pos):
      if self.selectedDimStyle is None:
         return
      
      popupMenu = QMenu(self)
      action = QAction(QadMsg.translate("DimStyle_Dialog", "Set current"), popupMenu)
      popupMenu.addAction(action)
      action.triggered.connect(self.setCurrentStyle)

      action = QAction(QadMsg.translate("DimStyle_Dialog", "Rename"), popupMenu)
      popupMenu.addAction(action)
      action.triggered.connect(self.startEditingItem)

      action = QAction(QadMsg.translate("DimStyle_Dialog", "Modify description"), popupMenu)
      popupMenu.addAction(action)
      action.triggered.connect(self.updDescrSelectedDimStyle)

      action = QAction(QadMsg.translate("DimStyle_Dialog", "Remove"), popupMenu)
      currDimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      if self.selectedDimStyle.name == currDimStyleName:
         action.setDisabled(True)
      popupMenu.addAction(action)
      action.triggered.connect(self.delSelectedDimStyle)

      popupMenu.popup(self.dimStyleList.mapToGlobal(pos))

      
