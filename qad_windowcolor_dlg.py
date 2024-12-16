# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Gestione dei colori di QAD
 
                              -------------------
        begin                : 2016-17-02
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
from qgis.PyQt.QtCore import Qt, QObject, QItemSelectionModel, QRectF
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import QgsColorButton
from qgis.core import QgsApplication


from . import qad_windowcolor_ui


from .qad_variables import QadVariable, QadVariableTypeEnum, QadVariables, QadVariablesClass
from .qad_msg import QadMsg, qadShowPluginPDFHelp
from . import qad_utils


# ===============================================================================
# QadColorContextEnum class.
# ===============================================================================
class QadColorContextEnum():
   NONE           = 0
   MODEL_SPACE_2D = 1 # finestra grafica
   COMMAND_LINE   = 2 # finestra di comando


# ===============================================================================
# QadColorElementEnum class.
# ===============================================================================
class QadColorElementEnum():
   NONE                       =  0
   CROSSHAIRS                 =  1 # Puntatori a croce
   PICKBOX                    =  2 # Quadratino di selezione degli oggetti
   AUTOTRECK_VECTOR           =  3 # Vettore autotrack
   AUTOSNAP_MARKER            =  4 # Contrassegno di autosnap
   COMMAND_HISTORY_BACKGROUND =  5 # Sfondo cronologia comandi
   COMMAND_HISTORY_TEXT       =  6 # Testo cronologia comandi
   PROMPT_BACKGROUND          =  7 # Sfondo prompt attivo
   PROMPT_TEXT                =  8 # Testo prompt attivo
   COMMAND_OPTION_KEYWORD     =  9 # Parola chiave opzione di comando
   COMMAND_OPTION_BACKGROUND  = 10 # Sfondo opzione di comando
   COMMAND_OPTION_HIGHLIGHTED = 11 # Opzione di comando evidenziata
   DI_AUTOTRECK_VECTOR        = 12 # Dynamic input - Linne di quota dinamiche
   DI_COMMAND_DESCR           = 13 # Dynamic input - Descrizione comando
   DI_COMMAND_DESCR_BACKGROUND = 14 # Dynamic input - Sfondo descrizione comando
   DI_COMMAND_DESCR_BORDER    = 15 # Dynamic input - Bordo descrizione comando
   

#######################################################################################
# Classe che gestisce l'interfaccia grafica per i colori di QAD
class QadWindowColorDialog(QDialog, QObject, qad_windowcolor_ui.Ui_WindowColor_Dialog):
   def __init__(self, plugIn, parent, contextEnum = QadColorContextEnum.NONE, elementEnum = QadColorElementEnum.NONE):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self, parent)

      self.tempQadVariables = QadVariablesClass()
      QadVariables.copyTo(self.tempQadVariables)
      self.currentVarName = ""
      self.currentContext = contextEnum
      self.currentElement = elementEnum

      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      
      # Inizializzazione dei colori
      self.init_colors()
      
      if contextEnum != QadColorContextEnum.NONE:
         # contesti      
         index = self.listView_Context.model().index(0,0) # seleziono il primo elemento della lista
         context = self.contextList[contextEnum] # context = (<contextEnum>, (<contextDescr>, <elementDict>))
         contextDescr = context[0]
         items = self.listView_Context.model().findItems(contextDescr)
         if len(items) > 0:
            item = items[0]
            if item is not None:
               index = self.listView_Context.model().indexFromItem(item)
               self.listView_Context.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectCurrent)

               if elementEnum != QadColorElementEnum.NONE:
                  # elementi
                  elementDict = context[1]
                  element = elementDict[elementEnum] # element = (<elementEnum>, (<elementDescr>, <sys var name>))
                  elementDescr = element[0]
                  items = self.listView_Element.model().findItems(elementDescr)
                  if len(items) > 0:
                     item = items[0]
                     if item is not None:
                        index = self.listView_Element.model().indexFromItem(item)         
                        self.listView_Element.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectCurrent)


   # ============================================================================
   # setupUi
   # ============================================================================
   def setupUi(self, Dialog):
      qad_windowcolor_ui.Ui_WindowColor_Dialog.setupUi(self, self)
      # aggiungo il bottone di qgis QgsColorButton chiamato buttonColor 
      # che eredita la posizione di Button_ColorDummy (che viene nascosto)
      self.Button_ColorDummy.setHidden(True)
      self.buttonColor = QgsColorButton(self.Button_ColorDummy.parent())
      self.buttonColor.setGeometry(self.Button_ColorDummy.geometry())
      self.buttonColor.setObjectName("buttonColor")
      self.buttonColor.colorChanged.connect(self.colorChanged)

      # aggiungo il QWidget chiamato QadPreview
      # che eredita la posizione di widget_Preview (che viene nascosto)
      self.widget_Preview.setHidden(True)
      self.preview = QadPreview(self.plugIn, self.widget_Preview.parent(), self.tempQadVariables, self.currentContext)
      self.preview.setGeometry(self.widget_Preview.geometry())
      self.preview.setObjectName("preview")


   # ============================================================================
   # init_context_list
   # ============================================================================
   def init_context_list(self):
      self.contextList = dict()

      # description, element dictionary
      contextDescr = QadMsg.translate("WindowColor_Dialog", "Model Space") # x lupdate
      self.contextList[QadColorContextEnum.MODEL_SPACE_2D] = [contextDescr, self.get_MODEL_SPACE_2D_element_dict()]
      contextDescr = QadMsg.translate("WindowColor_Dialog", "Command line") # x lupdate
      self.contextList[QadColorContextEnum.COMMAND_LINE] = [contextDescr, self.get_COMMAND_LINE_element_dict()]


   # ============================================================================
   # get_MODEL_SPACE_2D_element_dict
   # ============================================================================
   def get_MODEL_SPACE_2D_element_dict(self):
      elementList = dict()
      
      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Crosshairs") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CURSORCOLOR") # x lupdate
      elementList[QadColorElementEnum.CROSSHAIRS] = [elementDescr, elementVarName]
      
      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Pickbox") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "PICKBOXCOLOR") # x lupdate
      elementList[QadColorElementEnum.PICKBOX] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Autotreck vector") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "AUTOTRECKINGVECTORCOLOR") # x lupdate
      elementList[QadColorElementEnum.AUTOTRECK_VECTOR] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Autosnap marker") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "AUTOSNAPCOLOR") # x lupdate
      elementList[QadColorElementEnum.AUTOSNAP_MARKER] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Dynamic dimension lines") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "DYNTRECKINGVECTORCOLOR") # x lupdate
      elementList[QadColorElementEnum.DI_AUTOTRECK_VECTOR] = [elementDescr, elementVarName]
      
      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Drafting tool tip") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "DYNEDITFORECOLOR") # x lupdate
      elementList[QadColorElementEnum.DI_COMMAND_DESCR] = [elementDescr, elementVarName]
      
      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Drafting tool tip contour") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR") # x lupdate
      elementList[QadColorElementEnum.DI_COMMAND_DESCR_BACKGROUND] = [elementDescr, elementVarName]
      
      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Drafting tool tip background") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR") # x lupdate
      elementList[QadColorElementEnum.DI_COMMAND_DESCR_BORDER] = [elementDescr, elementVarName]
      
      
      return elementList


   # ============================================================================
   # get_COMMAND_LINE_element_dict
   # ============================================================================
   def get_COMMAND_LINE_element_dict(self):
      elementList = dict()
      
      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Command history background") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CMDHISTORYBACKCOLOR") # x lupdate
      elementList[QadColorElementEnum.COMMAND_HISTORY_BACKGROUND] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Command history text") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CMDHISTORYFORECOLOR") # x lupdate    
      elementList[QadColorElementEnum.COMMAND_HISTORY_TEXT] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Active prompt background") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR") # x lupdate
      elementList[QadColorElementEnum.PROMPT_BACKGROUND] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Active prompt text") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CMDLINEFORECOLOR") # x lupdate
      elementList[QadColorElementEnum.PROMPT_TEXT] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Command option keyword") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CMDLINEOPTCOLOR") # x lupdate
      elementList[QadColorElementEnum.COMMAND_OPTION_KEYWORD] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Command option keyword background") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CMDLINEOPTBACKCOLOR") # x lupdate
      elementList[QadColorElementEnum.COMMAND_OPTION_BACKGROUND] = [elementDescr, elementVarName]

      # description, system variable
      elementDescr = QadMsg.translate("WindowColor_Dialog", "Command option highlighted") # x lupdate
      elementVarName = QadMsg.translate("Environment variables", "CMDLINEOPTHIGHLIGHTEDCOLOR") # x lupdate
      elementList[QadColorElementEnum.COMMAND_OPTION_HIGHLIGHTED] = [elementDescr, elementVarName]

      return elementList


   # ============================================================================
   # init_colors
   # ============================================================================
   def init_colors(self):
      self.init_context_list()

      # Inizializzazione della lista dei contesti
      model = QStandardItemModel(self.listView_Context)
      contexts = self.contextList.items() # lista dei contesti
      for context in contexts:
         # context = (<contextEnum>, (<contextDescr>, <elementDict>))
         contextDescr = context[1][0]
         # Create an item with a caption
         item = QStandardItem(contextDescr)
         item.setData(context)
         model.appendRow(item)
         
      self.listView_Context.setModel(model)
      
      # collego l'evento "cambio di selezione" alla funzione self.contextChanged
      self.listView_Context.selectionModel().selectionChanged.connect(self.contextChanged)
  
  
   # ============================================================================
   # contextChanged
   # ============================================================================
   def contextChanged(self, current, previous):
      # leggo ciò che selezionato
      index = current.indexes()[0]
      item = self.listView_Context.model().itemFromIndex(index)
      context = item.data() # context = (<contextEnum>, (<contextDescr>, <elementDict>))
      self.currentContext = context[0]
      elementDict = context[1][1]
      self.preview.refreshColors(self.currentContext, self.tempQadVariables) # forzo il disegno del preview
      self.currentVarName = ""
      
      # Inizializzazione della lista dei contesti
      model = QStandardItemModel(self.listView_Element)
      elements = elementDict.items() # lista degli elementi
      for element in elements:
         # element = (<elementEnum>, (<elementDescr>, <sys var name>))
         elementDescr = element[1][0]
         # Create an item with a caption
         item = QStandardItem(elementDescr)
         item.setData(element)
         model.appendRow(item)
         
      self.listView_Element.setModel(model)
      # collego l'evento "cambio di selezione" alla funzione self.elementChanged
      self.listView_Element.selectionModel().selectionChanged.connect(self.elementChanged)


   # ============================================================================
   # elementChanged
   # ============================================================================
   def elementChanged(self, current, previous):
      # leggo ciò che selezionato
      index = current.indexes()[0]
      item = self.listView_Element.model().itemFromIndex(index)
      element = item.data() # element = (<elementEnum>, (<elementDescr>, <sys var name>))
      self.currentElement = element[0]
      self.currentVarName = element[1][1]     
      self.buttonColor.setColor(QColor(self.tempQadVariables.get(self.currentVarName)))
      
      
   # ============================================================================
   # colorChanged
   # ============================================================================
   def colorChanged(self, value):
      self.tempQadVariables.set(self.currentVarName, self.buttonColor.color().name())
      self.preview.refreshColors(self.currentContext, self.tempQadVariables) # forzo il disegno del preview


   # ============================================================================
   # restoreVarValueElement
   # ============================================================================
   def restoreVarValueElement(self, varName):
      variable = QadVariables.getVariable(varName)
      if variable is None:
         return False
      self.tempQadVariables.set(varName, variable.default)
      return True
      

   # ============================================================================
   # restoreContext
   # ============================================================================
   def restoreContext(self, context):
      context = self.contextList[context] # context = (<contextEnum>, (<contextDescr>, <elementDict>))
      elementDict = context[1]
      elements = elementDict.items() # lista degli elementi
      for element in elements:
         # element = (<elementEnum>, (<elementDescr>, <sys var name>))
         varName = element[1][1]
         self.restoreVarValueElement(varName)


   # ============================================================================
   # Button_RestoreCurrElement_clicked
   # ============================================================================
   def Button_RestoreCurrElement_clicked(self):
      if self.restoreVarValueElement(self.currentVarName):
         self.preview.refreshColors(self.currentContext, self.tempQadVariables) # forzo il disegno del preview
         self.buttonColor.setColor(QColor(self.tempQadVariables.get(self.currentVarName)))


   # ============================================================================
   # Button_RestoreCurrContext_clicked
   # ============================================================================
   def Button_RestoreCurrContext_clicked(self):
      self.restoreContext(self.currentContext)
      self.preview.refreshColors(self.currentContext, self.tempQadVariables) # forzo il disegno del preview
      if self.currentVarName != "":
         self.buttonColor.setColor(QColor(self.tempQadVariables.get(self.currentVarName)))


   # ============================================================================
   # Button_RestoreAllContext_clicked
   # ============================================================================
   def Button_RestoreAllContext_clicked(self):
      contexts = self.contextList.keys() # lista dei contesti
      for context in contexts:
         self.restoreContext(context)

      self.preview.refreshColors(self.currentContext, self.tempQadVariables) # forzo il disegno del preview
      if self.currentVarName != "":
         self.buttonColor.setColor(QColor(self.tempQadVariables.get(self.currentVarName)))



   # ============================================================================
   # getSysVariableList
   # ============================================================================
   def getSysVariableList(self):
      # ritorna una lista di variabili di sistema dei colori gestiti da questa finestra
      variables = []
      contexts = self.contextList.items() # lista dei contesti
      for context in contexts:
         # context = (<contextEnum>, (<contextDescr>, <elementDict>))
         elementDict = context[1][1]
         elements = elementDict.items() # lista degli elementi
         for element in elements:
            # element = (<elementEnum>, (<elementDescr>, <sys var name>))
            varName = element[1][1]
            varValue = self.tempQadVariables.get(varName)
            variables.append(QadVariable(varName, varValue, QadVariableTypeEnum.COLOR))
      return variables


   def Button_ApplyClose_Pressed(self):
      # copio i valori dei colori in QadVariables e li salvo
      variables = self.getSysVariableList()
      for variable in variables:
         QadVariables.set(variable.name, variable.value)
      QadVariables.save()
      self.plugIn.TextWindow.refreshColors()
      
      QDialog.accept(self)


   def Button_Cancel_Pressed(self):
      QDialog.reject(self)


   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", ""))


# ===============================================================================
# QadPreview class.
# ===============================================================================
class QadPreview(QWidget):
   def __init__(self, plugIn, parent, tempQadVariables, context, windowFlags = Qt.Widget):
      self.plugIn = plugIn
      self.context = context
      self.tempQadVariables = tempQadVariables
      QWidget.__init__(self, parent, windowFlags)

   def refreshColors(self, context, tempQadVariables):
      self.context = context
      self.tempQadVariables = tempQadVariables
      self.update() # forzo il disegno del preview

   def paintEvent(self, event):
      if self.context == QadColorContextEnum.MODEL_SPACE_2D:
         self.paint_MODEL_SPACE_2D()
      elif self.context == QadColorContextEnum.COMMAND_LINE:
         self.paint_COMMAND_LINE()
      
   def paint_MODEL_SPACE_2D(self):
      rect = self.rect()
      painter = QPainter(self)
      painter.fillRect(rect, self.plugIn.canvas.canvasColor())
      painter.setRenderHint(QPainter.Antialiasing)
      
      # PICKBOX
      x1 = rect.width() / 3
      y1 = rect.height() - rect.height() / 3
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
      pickSize = 5
      painter.setPen(QPen(color, 1, Qt.SolidLine))
      painter.drawRect(x1 - pickSize, y1 - pickSize, 2 * pickSize, 2 * pickSize)

      # CROSSHAIRS
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "CURSORCOLOR")))
      cursorSize = 20
      painter.setPen(QPen(color, 1, Qt.SolidLine))
      painter.drawLine(x1 - pickSize, y1, x1 - pickSize - cursorSize, y1)
      painter.drawLine(x1 + pickSize, y1, x1 + pickSize + cursorSize, y1)
      painter.drawLine(x1, y1 - pickSize, x1, y1 - pickSize - cursorSize)
      painter.drawLine(x1, y1 + pickSize, x1, y1 + pickSize + cursorSize)
      
      # AUTOTRECK_VECTOR
      x1 = rect.width() / 3
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "AUTOTRECKINGVECTORCOLOR")))
      painter.setPen(QPen(color, 1, Qt.DashLine))
      painter.drawLine(x1, 0, x1, rect.height())
      painter.drawLine(x1 + rect.height() * 2 / 3, 0, x1 - rect.height() / 3, rect.height())

      # AUTOSNAP
      x1 = rect.width() / 3
      y1 = rect.height() / 3
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPCOLOR")))
      pickSize = 5
      painter.setPen(QPen(color, 2, Qt.SolidLine))
      painter.drawRect(x1 - pickSize, y1 - pickSize, 2 * pickSize, 2 * pickSize)

      # DYNAMIC INPUT
      x1 = rect.width() / 3
      y1 = rect.height() - rect.height() / 3
      cursorSize = 20
      fMetrics = painter.fontMetrics()
      msg1 = "12.3456"
      sz1 = fMetrics.size(Qt.TextSingleLine, msg1 + "__")
      dynInputRect1 = QRectF(x1 + cursorSize, y1 + cursorSize, sz1.width(), sz1.height() + 2) 
      msg2 = "78.9012"
      sz2 = fMetrics.size(Qt.TextSingleLine, msg2 + "__")
      dynInputRect2 = QRectF(dynInputRect1.right() + sz1.height() / 3, dynInputRect1.top(), sz2.width(), sz2.height() + 2) 
      # DYNAMIC INPUT COMMAND DESCR BACKGROUND
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      painter.fillRect(dynInputRect1, color)
      painter.fillRect(dynInputRect2, color)
      # DYNAMIC INPUT COMMAND DESCR BORDER
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      painter.setPen(QPen(color, 1, Qt.SolidLine))
      painter.drawRect(dynInputRect1)
      painter.drawRect(dynInputRect2)
      # DYNAMIC INPUT COMMAND DESCR FOREGROUND
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      painter.setPen(QPen(color, 1, Qt.SolidLine))
      painter.drawText(dynInputRect1, msg1)
      painter.drawText(dynInputRect2, msg2)
      

   def paint_COMMAND_LINE(self):
      rect = self.rect()
      sep = rect.height() * 2 / 3
      painter = QPainter(self)
      
      # CMDHISTORYBACKCOLOR
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "CMDHISTORYBACKCOLOR")))
      painter.fillRect(0, 0, rect.width(), sep, color)
      
      # CMDHISTORYFORECOLOR
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "CMDHISTORYFORECOLOR")))
      painter.setPen(QPen(color))
      painter.drawText(QRectF(0, 0, rect.width(), sep), Qt.AlignCenter, QadMsg.translate("QAD", "Command: "))
      
      # CMDLINEBACKCOLOR
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR")))
      painter.fillRect(0, sep, rect.width(), rect.height(), color)
      
      # CMDLINEFORECOLOR
      color = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "CMDLINEFORECOLOR")))
      painter.setPen(QPen(color))
      painter.drawText(QRectF(0, sep, rect.width(), rect.height() - sep), Qt.AlignCenter, QadMsg.translate("QAD", "Command: "))

