# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire l'input dinamico
 
                              -------------------
        begin                : 2017-07-27
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


from qgis.core import *
from qgis.gui import *

from qgis.PyQt.QtCore import Qt, QTimer, QPoint
from qgis.PyQt.QtGui import QColor, QFontMetrics, QTextCursor, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QTextEdit, QSizePolicy, QApplication, QLabel, QWidget

import math

from . import qad_utils
from .qad_arc import QadArc
from .qad_entity import QadEntity
from .qad_grip import QadGripPointTypeEnum, QadEntityGripPoint
from .qad_msg import QadMsg
from .qad_rubberband import createRubberBand
from .qad_snapper import *
from .qad_textwindow import QadCmdSuggestWindow, QadInputTypeEnum, QadInputModeEnum
from .qad_variables import *
from .qad_variables import QadVariables, QadINPUTSEARCHOPTIONSEnum
from .qad_vertexmarker import *
from .qad_dim import QadDimStyles


# ===============================================================================
# QadDynamicInputContextEnum class.
# ===============================================================================
class QadDynamicInputContextEnum():
   NONE               = 0
   COMMAND            = 1   # richiesta di un comando
   EDIT               = 2   # richiesta in editazione


# ===============================================================================
# QadDynamicInputEditEnum class.
# ===============================================================================
class QadDynamicInputEditEnum(): # vedi initGui che dichiara un vettore lungo quanto sono i valori di QadDynamicInputEditEnum
   CMD_LINE_EDIT        = 0 # usato per inserire un comando
   PROMPT_EDIT          = 1 # usato per messaggi e scelta opzioni di comando
   EDIT                 = 2 # usato per richiesta generica di un valore (es. raggio, scala, rotazione)
   EDIT_X               = 3 # usato per coordinata X
   EDIT_Y               = 4 # usato per coordinata Y
   EDIT_Z               = 5 # usato per coordinata Z
   # usato per distanza dal punto precedente se segmento, usato per lunghezza raggio nel punto finale della parte precedente se arco
   # oppure lunghezza raggio nel punto medio se parte precedente e successiva sono lo stesso arco
   EDIT_DIST_PREV_PT    = 6
   # usato per distanza relativa alla posizione precedente dello stesso punto nel verso dal punto precedente se segmento
   # usato per lunghezza raggio nel punto iniziale della parte precedente se arco
   EDIT_REL_DIST_PREV_PT = 7
   # usato per angolo dal punto precedente se segmento, usato per angolo arco nel punto finale della parte precedente se arco
   EDIT_ANG_PREV_PT     = 8
   # usato per angolo relativo all'angolo dal punto precedente se segmento
   # usato per angolo totale arco se parte precedente e successiva sono lo stesso arco
   EDIT_REL_ANG_PREV_PT = 9
   # usato per distanza dal punto successivo se segmento, 
   # usato per lunghezza raggio nel punto iniziale della parte successiva se arco
   EDIT_DIST_NEXT_PT    = 10 
   # usato per distanza relativa alla posizione precedente dello stesso punto nel verso dal punto successivo se segmento
   # usato per lunghezza raggio nel punto finale della parte successiva se arco
   EDIT_REL_DIST_NEXT_PT = 11 
   EDIT_ANG_NEXT_PT     = 12 # usato per angolo dal punto successivo, usato per angolo arco nel punto iniziale della parte successiva
   EDIT_REL_ANG_NEXT_PT = 13 # usato per angolo relativo all'angolo dal punto successivo se segmento
   EDIT_SYMBOL_COORD_TYPE = 14 # usato per indicare se coordinata assoluta "#" o relativa "@"


# ogni QadDynamicInputEdit è gestita dalle funzioni di QadDynamicEditInput:
# initGui, setFocus, setNextCurrentEdit, setPrevCurrentEdit, show, mouseMoveEvent, moveCtrls


# ===============================================================================
# QadDynamicEdit
# ===============================================================================
class QadDynamicEdit(QTextEdit):
#    """
#    Classe che gestisce l'input dinamico in una QTextEdit
#    """
   
   def __init__(self, QadDynamicInputObj):
      QTextEdit.__init__(self, QadDynamicInputObj.canvas)
      self.QadDynamicInputObj = QadDynamicInputObj
      self.plugIn = QadDynamicInputObj.plugIn
      self.canvas = QadDynamicInputObj.canvas
      
      self.font_size = 8 + QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPSIZE"))
      height = self.font_size + 15

      self.setTextInteractionFlags(Qt.TextEditorInteraction)
      self.setMinimumSize(height, height)
      self.setMaximumHeight(height)
      self.setUndoRedoEnabled(False)
      self.setAcceptRichText(False)
      self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.error = False # indica se il valore contenuto nella edit è errato
      self.lockedPos = False # indica se la posizione della edit è bloccata


   # ============================================================================
   # focusInEvent
   # ============================================================================
   def focusInEvent(self, e):
      pass
   
   
   # ============================================================================
   # reset
   # ============================================================================
   def reset(self):
      self.showMsg("")
      self.error = False
      self.lockedPos = False


   # ============================================================================
   # setColors
   # ============================================================================
   def setColors(self, foregroundColor = None, backGroundColor = None, borderColor = None, \
                 selectionColor = None, selectionBackGroundColor = None, opacity = 100):
      # se i colori sono None allora non vengono alterati
      # caso particolare per borderColor = "" non viene disegnato
      # opacity = 0-100      
      oldFmt = self.styleSheet().split(";")
      fmt = "rgba({0},{1},{2},{3}%)"
      
      if foregroundColor is not None:
         c = QColor(foregroundColor)
         rgbStrForeColor = "color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrForeColor = ""
         for f in oldFmt:
            if f.find("color:") == 0:
               rgbStrForeColor = f + ";"
               break
            
      if backGroundColor is not None:
         c = QColor(backGroundColor)
         rgbStrBackColor = "background-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrBackColor = ""
         for f in oldFmt:
            if f.find("background-color:") == 0:
               rgbStrBackColor = f + ";"
               break

      # se è in stato di errore il bordo deve essere rosso largo 2 pixel
      if self.error:
         c = QColor(Qt.red)
         rgbStrBorderColor = "border-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
         fmtBorder = "border:2px;border-style:solid;"
      else:
         if borderColor is not None:
            if borderColor == "": # senza bordo
               rgbStrBorderColor = ""
               fmtBorder = "border:0px;border-style:solid;"
            else:
               c = QColor(borderColor)
               rgbStrBorderColor = "border-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
               fmtBorder = "border:1px;border-style:solid;"
         else:
            rgbStrBorderColor = ""
            fmtBorder = ""
            for f in oldFmt:
               if f.find("border-color:") == 0:
                  rgbStrBorderColor = f + ";"
               elif f.find("border:") == 0:
                  fmtBorder = fmtBorder + f + ";"
               elif f.find("border-style:") == 0:
                  fmtBorder = fmtBorder + f + ";"

      if selectionColor is not None:
         c = QColor(selectionColor)
         rgbStrSelectionColor = "selection-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrSelectionColor = ""
         for f in oldFmt:
            if f.find("selection-color:") == 0:
               rgbStrSelectionColor = f + ";"
               break

      if selectionBackGroundColor is not None:
         c = QColor(selectionBackGroundColor)
         rgbStrSelectionBackColor = "selection-background-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      else:
         rgbStrSelectionBackColor = ""
         for f in oldFmt:
            if f.find("selection-background-color:") == 0:
               rgbStrSelectionBackColor = f + ";"
               break

      fmt = rgbStrForeColor + \
            rgbStrBackColor + \
            fmtBorder + \
            rgbStrBorderColor + \
            rgbStrSelectionColor + \
            rgbStrSelectionBackColor + \
            "font-size: " + str(self.font_size) + "pt;"
            
      self.setStyleSheet(fmt)


   def refreshWidth(self, updateCtrlsPos = True):
      fm = QFontMetrics(self.currentFont())
      boundingRect = fm.boundingRect(self.toPlainText())
      width = int(boundingRect.width() * 1.2) + 5
      height = boundingRect.height()
      
      canvasRect = self.canvas.rect()
      if width > canvasRect.width():
         width = canvasRect.width()
      
      self.resize(width, height)
      if updateCtrlsPos: self.QadDynamicInputObj.moveCtrls()


   # ============================================================================
   # selectAllText
   # ============================================================================
   def selectAllText(self):
      # seleziono tutto il testo
      cursor = self.textCursor()
      cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.Start, QTextCursor.KeepAnchor)
      self.setTextCursor(cursor)


   # ============================================================================
   # showMsg
   # ============================================================================
   def showMsg(self, msg, dummy1 = False, dummy2 = False, updateCtrlsPos = True):
      self.error = False
      cursor = self.textCursor()
      sep = msg.rfind("\n")
      if sep >= 0:
         newMsg = msg[sep + 1:]
         cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
         cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
      else:
         newMsg = msg
         cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
         cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)

      self.setTextCursor(cursor)
      self.insertPlainText(newMsg)
      self.refreshWidth(updateCtrlsPos)


   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      pass
   

# ===============================================================================
# QadDynamicInputCmdLineEdit
# ===============================================================================
class QadDynamicInputCmdLineEdit(QadDynamicEdit):
#    """
#    Classe che gestisce l'input dinamico della sola linea di comando
#    """
   
   def __init__(self, QadDynamicInputObj):
      QadDynamicEdit.__init__(self, QadDynamicInputObj)
      self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
             
      self.historyIndex = 0

      self.timerForCmdSuggestWindow = QTimer()
      self.timerForCmdSuggestWindow.setSingleShot(True)
      self.timerForCmdAutoComplete = QTimer()
      self.timerForCmdAutoComplete.setSingleShot(True)

      self.infoCmds = []
      self.infoVars = []

      self.cmdSuggestWindow = None
      
      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)
      self.show(False)


   def initCmdVarsList(self):
      # lista composta da elementi con:
      # <nome locale comando>, <nome inglese comando>, <icona>, <note>
      self.infoCmds = []
      for cmdName in self.plugIn.getCommandNames():
         cmd = self.plugIn.getCommandObj(cmdName[0])
         if cmd is not None:
            self.infoCmds.append([cmdName[0], cmd.getEnglishName(), cmd.getIcon(), cmd.getNote()])
            
      # Creo la finestra per il suggerimento delle variabili di ambiente
      # lista composta da elementi con:
      # <nome variabile>, "", <icona>, <note>
      self.infoVars = []
      icon = QIcon(":/plugins/qad/icons/variable.svg")
      for varName in QadVariables.getVarNames():
         var = QadVariables.getVariable(varName)
         self.infoVars.append([varName, "", icon, var.descr])
      

   def show(self, mode):
      if mode == False:
         self.timerForCmdAutoComplete.stop()
         self.lockedPos = False
         self.showCmdSuggestWindow(False) # hide suggestion window
         QTextEdit.setVisible(self, False)
      else:
#          if self.isVisible() == False:
#             self.showMsg("")
         QTextEdit.setVisible(self, True)
         self.setFocus()
         

   # ============================================================================
   # showMsg
   # ============================================================================
   def showMsg(self, msg, dummy1 = False, dummy2 = False, updateCtrlsPos = True):
      # la funzione showMsg viene usata da showMsg(self, cmd) nella classe QadCmdSuggestWindow
      # la quale comunica sia con QadEdit che con QadDynamicInputCmdLineEdit
      # per compatibilità con la showMsg di QadEdit devo aggiungere due parametri fittizi (dummy, dummy2)
      QadDynamicEdit.showMsg(self, msg, dummy1, dummy2, updateCtrlsPos)


   # ============================================================================
   # showEvaluateMsg
   # ============================================================================
   def showEvaluateMsg(self, msg, append = False): # per compatibilità con QadCmdSuggestListView.mouseReleaseEvent
      return self.QadDynamicInputObj.showEvaluateMsg(msg)


   # ============================================================================
   # showCmdSuggestWindow
   # ============================================================================
   def showCmdSuggestWindow(self, mode = True, filter = ""):
      if mode == False: # se spengo la finestra
         self.timerForCmdSuggestWindow.stop()
               
      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      # inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON = Turns on all automated keyboard features when typing at the Command prompt
      # inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_LIST = Displays a list of suggestions as keystrokes are entered
      if (inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_LIST) and \
          mode == True:
         if self.cmdSuggestWindow is None:
            # Creo la finestra per il suggerimento dei comandi
            self.initCmdVarsList()
            self.cmdSuggestWindow = QadCmdSuggestWindow(self.canvas, self, self.infoCmds, self.infoVars)
            self.cmdSuggestWindow.initGui()
         
         if self.cmdSuggestWindow.setFilter(filter) == 0:
            self.lockedPos = False;
            self.cmdSuggestWindow.show(False)
            return
            
         dataHeight = self.cmdSuggestWindow.getDataHeight()
         if dataHeight > 0:
            self.cmdSuggestWindow.cmdNamesListView.setMinimumHeight(self.cmdSuggestWindow.cmdNamesListView.sizeHintForRow(0))
         
         dataWidth = 200
      
         # Ricavo la posizione dell'angolo in alto a sin della QTextEdit relativa al suo parent
         editRect = self.geometry()
         ptEditRect = QPoint(editRect.left(), editRect.top())
         if self.parentWidget():
            ptEditRect = self.parentWidget().mapToGlobal(QPoint(editRect.left(), editRect.top()))
         ptUp = QApplication.desktop().mapFromGlobal(ptEditRect)
         
         spaceUp = ptUp.y() if ptUp.y() - dataHeight < 0 else dataHeight

         ptDown = QPoint(ptUp.x(), ptUp.y() + editRect.height())
         desktopRect = QApplication.desktop().screenGeometry()
         spaceDown = desktopRect.height() - ptDown.y() if ptDown.y() + dataHeight > desktopRect.height() else dataHeight

         # verifico se c'è più spazio sopra o sotto la finestra
         if spaceUp > spaceDown:
            pt = QPoint(ptUp.x(), ptUp.y() - spaceUp)
            dataHeight = spaceUp
         else:
            pt = QPoint(ptDown.x(), ptDown.y())
            dataHeight = spaceDown
         
         if pt.x() + dataWidth > desktopRect.width(): # se sborda oltre il limite di destra
            if desktopRect.width() - dataWidth < 0: # se anche spostando la finestra a sinistra sborda a sinisitra
               pt.setX(0)
               dataWidth = desktopRect.width()
            else:
               pt.setX(desktopRect.width() - dataWidth)
            
         pt = QApplication.desktop().mapToGlobal(pt)
         self.cmdSuggestWindow.move(pt)
         self.cmdSuggestWindow.resize(dataWidth, dataHeight)
            
         self.cmdSuggestWindow.show(True)
         self.lockedPos = True # quando la finestra dei suggerimenti è aperta la posizione si blocca
      else:
         if self.cmdSuggestWindow is not None:
            self.lockedPos = False
            self.cmdSuggestWindow.show(False)


   def showCmdAutoComplete(self, filter = ""):
      # autocompletamento
      self.timerForCmdAutoComplete.stop()
      
      # autocompletamento
      inputSearchOptions = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      filterLen = len(filter)
      if filterLen < 2:
         return
      
      # inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON = Turns on all automated keyboard features when typing at the Command prompt
      # inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.AUTOCOMPLETE = Automatically appends suggestions as each keystroke is entered after the second keystroke.
      if inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON and inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.AUTOCOMPLETE:
         if filterLen >= 2:
            cmdName, qty = self.plugIn.getMoreUsedCmd(filter)
         else:
            cmdName = ""

         self.appendCmdTextForAutoComplete(cmdName, filterLen)


   def appendCmdTextForAutoComplete(self, cmdName, filterLen):
      cursor = self.textCursor()
      #cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
      self.setTextCursor(cursor)
      if filterLen < len(cmdName): # se c'è qualcosa da aggiungere
         self.insertPlainText(cmdName[filterLen:])
      else:
         self.insertPlainText("")
      cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(cmdName) - filterLen)
      self.setTextCursor(cursor)
      self.refreshWidth()


   def showNextCmd(self):
      # mostra il comando successivo nella lista dei comandi usati
      cmdsHistory = self.plugIn.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if self.historyIndex < cmdsHistoryLen and cmdsHistoryLen > 0:
         self.historyIndex += 1
         if self.historyIndex < cmdsHistoryLen:
            self.showMsg(cmdsHistory[self.historyIndex])

                         
   def showPreviousCmd(self):
      # mostra il comando precedente nella lista dei comandi usati
      cmdsHistory = self.plugIn.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if self.historyIndex > 0 and cmdsHistoryLen > 0:
         self.historyIndex -= 1
         if self.historyIndex < cmdsHistoryLen:
            self.showMsg(cmdsHistory[self.historyIndex])


   def showLastCmd(self):
      # mostra e ritorna l'ultimo comando nella lista dei comandi usati
      cmdsHistory = self.plugIn.cmdsHistory
      cmdsHistoryLen = len(cmdsHistory)
      if cmdsHistoryLen > 0:
         self.showMsg(cmdsHistory[cmdsHistoryLen - 1])
         return cmdsHistory[cmdsHistoryLen - 1]
      else:
         return ""


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      
      if self.plugIn.shortCutManagement(e): # se è stata gestita una sequenza di tasti scorciatoia
         return
      
      # if Up or Down is pressed
      if self.isVisibleCmdSuggestWindow() and \
         (e.key() == Qt.Key_Down or e.key() == Qt.Key_Up or e.key() == Qt.Key_PageDown or e.key() == Qt.Key_PageUp or
          e.key() == Qt.Key_End or e.key() == Qt.Key_Home):
         self.cmdSuggestWindow.keyPressEvent(e)
         return
      else:  # nascondo la finestra di suggerimento
         self.lockedPos = False
         self.showCmdSuggestWindow(False)

      if e.key() == Qt.Key_Escape:
         cmdsHistory = self.plugIn.cmdsHistory
         self.historyIndex = len(cmdsHistory)
         self.QadDynamicInputObj.abort()
         return
      
      # if Return or Space is pressed, then perform the commands
      if e.key() == Qt.Key_Return or e.key() == Qt.Key_Space or e.key == Qt.Key_Enter:
         self.entered()
         return
      # if Up or Down is pressed
      elif e.key() == Qt.Key_Down:
         self.showNextCmd()
         return # per non far comparire la finestra di suggerimento
      elif e.key() == Qt.Key_Up:
         self.showPreviousCmd()
         return # per non far comparire la finestra di suggerimento
      else:
         if (e.key() != Qt.Key_Tab and e.key() != Qt.Key_Backtab) or \
            e.text() != "":
            # all other keystrokes get sent to the input line
            QTextEdit.keyPressEvent(self, e)
            self.refreshWidth()         
   
      # leggo il tempo di ritardo in msec
      inputSearchDelay = QadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHDELAY"))
      
      # lista suggerimento dei comandi simili
      currMsg = self.toPlainText()
      shot1 = lambda: self.showCmdSuggestWindow(True, currMsg)

      del self.timerForCmdSuggestWindow
      self.timerForCmdSuggestWindow = QTimer()
      self.timerForCmdSuggestWindow.setSingleShot(True)
      self.timerForCmdSuggestWindow.timeout.connect(shot1)
      self.timerForCmdSuggestWindow.start(inputSearchDelay)

      if e.text().isalnum(): # autocompletamento se è stato premuto un tasto alfanumerico
         shot2 = lambda: self.showCmdAutoComplete(self.toPlainText())
         del self.timerForCmdAutoComplete
         self.timerForCmdAutoComplete = QTimer()
         self.timerForCmdAutoComplete.setSingleShot(True)
         
         self.timerForCmdAutoComplete.timeout.connect(shot2)
         self.timerForCmdAutoComplete.start(inputSearchDelay)


   def entered(self):
      if self.QadDynamicInputObj.refreshResult() == True: # ricalcolo il risultato
         self.QadDynamicInputObj.showEvaluateMsg(self.QadDynamicInputObj.resStr) # uso il risultato in formato stringa
      self.reset()
      cmdsHistory = self.plugIn.cmdsHistory
      self.historyIndex = len(cmdsHistory)


   def isVisibleCmdSuggestWindow(self):
      if self.cmdSuggestWindow is None:
         return False
      return self.cmdSuggestWindow.isVisible()


# ===============================================================================
# QadDynamicInputPromptEdit
# ===============================================================================
class QadDynamicInputPromptEdit(QadDynamicEdit):
#    """
#    Classe che gestisce l'input dinamico del prompt dei messaggi e scelta opzioni di comando
#    """
    
   def __init__(self, QadDynamicInputObj):
      QadDynamicEdit.__init__(self, QadDynamicInputObj)
 
      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))      
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)
      self.show(False)


   def show(self, mode):
      if mode == False:
         QTextEdit.setVisible(self, False)
      else:
         QTextEdit.setVisible(self, True)
      
 
#    # ============================================================================
#    # keyPressEvent
#    # ============================================================================
#    def keyPressEvent(self, e):
#       pass
   

# ===============================================================================
# QadDynamicInputEdit
# ===============================================================================
class QadDynamicInputEdit(QadDynamicEdit):
#    """
#    Classe che gestisce l'input dinamico di un valore
#    """
    
   def __init__(self, QadDynamicInputObj):
      QadDynamicEdit.__init__(self, QadDynamicInputObj)
      self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

      # il default è un numero reale non nullo 
      self.inputMode = QadInputModeEnum.NOT_NULL
      self.inputType = QadInputTypeEnum.FLOAT
      
      self.lockable = True # indica se il valore della edit può essere bloccato
      self.__lockedValue = False # indica se il valore contenuto nella edit è bloccato

      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)

      # icona di lock      
      fm = QFontMetrics(self.currentFont())
      height = self.height() - 4
      self.LockedIcon = QLabel(self)
      self.LockedIcon.resize(height, height)
      self.LockedIcon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
      self.LockedIcon.setStyleSheet("border:0px;"); # senza bordo
      pixmap = QPixmap(":/plugins/qad/icons/locked.svg").scaled(height, height)
      self.LockedIcon.setPixmap(pixmap)

      self.lineMarkerColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNTRECKINGVECTORCOLOR")))
      self.lineMarkers = [] # lista dei RubberBand visualizzati

      self.show(False)


   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      self.removeItems()


   def setLockedValue(self, mode):
      # ritorna True e l'operazione ha avuto successo
      if self.lockable == False: return False
      if self.__lockedValue != mode:
         self.__lockedValue = mode
         self.LockedIcon.setVisible(self.__lockedValue)
      self.refreshWidth()
      

   def isLockedValue(self):
      return self.__lockedValue
      

   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      # svuoto la linea di marker rimuovendoli dal canvas
      for lineMarker in self.lineMarkers:
         lineMarker.hide()
         self.plugIn.canvas.scene().removeItem(lineMarker)
      del self.lineMarkers[:]


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self):
      QadDynamicEdit.reset(self)
      self.inputMode = QadInputModeEnum.NONE
      self.__lockedValue = False
      self.removeItems()


   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode):
      QTextEdit.setVisible(self, mode)
      for lineMarker in self.lineMarkers:
         lineMarker.setVisible(mode)
      if mode == False:
         self.LockedIcon.setVisible(False)
      else:
         if self.isLockedValue():
            self.LockedIcon.setVisible(True)
         else:
            self.LockedIcon.setVisible(False)


   # ============================================================================
   # refreshWidth
   # ============================================================================
   def refreshWidth(self, updateCtrlsPos = True):
      height = self.height()
      fm = QFontMetrics(self.currentFont())
      boundingRect = fm.boundingRect(self.toPlainText())
      width = int(boundingRect.width() * 1.2) + 5     
      
      dimLockedIcon = self.LockedIcon.height()
      offset = 2
      if self.isLockedValue():
         width = width + dimLockedIcon + offset # per icona di lock
      else:
         width = width + offset # per icona di lock
      
      canvasRect = self.canvas.rect()
      if width > canvasRect.width():
         width = canvasRect.width()
      
      self.resize(width, height)
      self.LockedIcon.move(width - dimLockedIcon - offset, height - dimLockedIcon - 2)
      if updateCtrlsPos: self.QadDynamicInputObj.moveCtrls()


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      if self.plugIn.shortCutManagement(e): # se è stata gestita una sequenza di tasti scorciatoia
         return
      
      if e.key() == Qt.Key_Tab:
         if self.checkValid() is not None:
            # mi sposto sulla edit successiva
            self.QadDynamicInputObj.setNextCurrentEdit()
         else: # valore errato
            pass
         
      elif e.key() == Qt.Key_Backtab:
         if self.checkValid() is not None:
            self.QadDynamicInputObj.setPrevCurrentEdit()
         else: # valore errato
            pass
         
      elif e.key() == Qt.Key_Return or e.key == Qt.Key_Enter:
         self.QadDynamicInputObj.keyPressEvent(e) # lo faccio gestire da QadDynamicInputObj
#          if self.isLockedValue() == True:
#             value = self.toPlainText()
#             snapType = str2snapTypeEnum(value)
#             if snapType != -1: # se é stato forzato uno snap
#                self.QadDynamicInputObj.keyPressEvent(e) # lo faccio gestire da QadDynamicInputObj
#             elif self.checkValid() is not None:
#                self.QadDynamicInputObj.keyPressEvent(e) # lo faccio gestire da QadDynamicInputObj
#          else:
#             self.QadDynamicInputObj.keyPressEvent(e) # lo faccio gestire da QadDynamicInputObj
            
      elif (e.key() == Qt.Key_Down or e.key() == Qt.Key_Up or e.key() == Qt.Key_PageDown or e.key() == Qt.Key_PageUp or \
            e.key() == Qt.Key_End or e.key() == Qt.Key_Home):
         pass # al momento si è deciso di non mostrare il menu delle opzioni del comando attivo da qui
      
      elif e.key() == Qt.Key_Comma: # ","
         self.QadDynamicInputObj.keyPressEvent(e) # lo faccio gestire da QadDynamicInputObj

      # se non si tratta di stringa e si tratta di un carattere speciale
      elif not (self.inputType & QadInputTypeEnum.STRING) and \
           (e.text() == "@" or e.text() == "#" or e.text() == "<"):
            self.QadDynamicInputObj.keyPressEvent(e) # lo faccio gestire da QadDynamicInputObj
                  
      elif e.key() == Qt.Key_Escape:
         self.QadDynamicInputObj.abort()
                        
      elif e.text() != "":
         previousTxt = self.toPlainText()
         QTextEdit.keyPressEvent(self, e)
         if self.lockable: # se è possibile modificare lo stato di lock
            currentTxt = self.toPlainText()
            if currentTxt == "":
               self.setLockedValue(False)
            elif currentTxt != previousTxt:
               self.setLockedValue(True)
         else:
            self.refreshWidth()
      
      
   # ============================================================================
   # focusInEvent
   # ============================================================================
   def focusInEvent(self, e):
      # cambio il colore
      foregroundColor = QColor(Qt.black)
      backGroundColor = QColor(Qt.white)
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      selectionColor = QColor(Qt.white)
      selectionBackGroundColor = QColor(51, 153, 255) # azzurro (R=51 G=153 B=255)
      self.setColors(foregroundColor, backGroundColor, borderColor, selectionColor, selectionBackGroundColor, opacity)
      self.selectAllText() # seleziono tutto il testo
      

   # ============================================================================
   # focusOutEvent
   # ============================================================================
   def focusOutEvent(self, e):
      # cambio il colore
      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)
      # seleziono il testo
      cursor = self.textCursor()
      cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
      self.setTextCursor(cursor)
 

   # ============================================================================
   # checkValid
   # ============================================================================
   def checkValid(self):
      # ritorna None in caso di errore
      value = self.toPlainText()
      self.error = False
      
      if value == "" and (self.inputMode & QadInputModeEnum.NOT_NULL): # non permesso input nullo
         self.error = True
         self.setColors() # ricolora con i bordi rossi perchè error=True
         self.selectAllText() # seleziono tutto il testo
         return None

      if self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
         self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         if self.inputType & QadInputTypeEnum.INT: # si aspetta un numero intero
            value = qad_utils.str2int(value)
            if value is None:
               self.error = True
               self.setColors() # ricolora con i bordi rossi perchè error=True
               self.selectAllText() # seleziono tutto il testo
               return None
         elif self.inputType & QadInputTypeEnum.LONG: # si aspetta un numero long
            value = qad_utils.str2long(value)
            if value is None:
               self.error = True
               self.setColors() # ricolora con i bordi rossi perchè error=True
               self.selectAllText() # seleziono tutto il testo
               return None
         elif self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE: # si aspetta un numero reale
            value = qad_utils.str2float(value)
            if value is None:
               self.error = True
               self.setColors() # ricolora con i bordi rossi perchè error=True
               self.selectAllText() # seleziono tutto il testo
               return None
         
         # non permesso valore = 0
         # non permesso valore < 0
         # non permesso valore > 0
         if (value == 0 and (self.inputMode & QadInputModeEnum.NOT_ZERO)) or \
            (value < 0 and (self.inputMode & QadInputModeEnum.NOT_NEGATIVE)) or \
            (value > 0 and (self.inputMode & QadInputModeEnum.NOT_POSITIVE)):
            self.error = True
            self.setColors() # ricolora con i bordi rossi perchè error=True
            self.selectAllText() # seleziono tutto il testo
            return None

         if self.inputType & QadInputTypeEnum.ANGLE: # si aspetta un angolo in gradi
            if value is not None:
               # i gradi vanno convertiti in radianti
               value = float(qad_utils.toRadians(value))
               
      elif self.inputType & QadInputTypeEnum.BOOL:
         value = qad_utils.str2bool(value)
         if value is None:
            self.error = True
            self.setColors() # ricolora con i bordi rossi perchè error=True
            self.selectAllText() # seleziono tutto il testo
            return None
   
      return value


   # ============================================================================
   # setLinesMarker
   # ============================================================================
   def setLinesMarker(self, points):
      """
      Crea un marcatore lineare x una lista di punti
      """
      # svuoto la linea di marker rimuovendoli dal canvas
      for lineMarker in self.lineMarkers:
         lineMarker.hide()
         self.plugIn.canvas.scene().removeItem(lineMarker)
      del self.lineMarkers[:]
      
      lineMarker = createRubberBand(self.canvas, QgsWkbTypes.LineGeometry, True)
      lineMarker.setColor(self.lineMarkerColor)
      lineMarker.setLineStyle(Qt.DotLine)
      if points is None:
         return None
      tot = len(points)
      i = 0
      while i < (tot - 1):
         lineMarker.addPoint(points[i], False)
         i = i + 1
      lineMarker.addPoint(points[i], True)
      self.lineMarkers.append(lineMarker)
   
   

# ===============================================================================
class QadDynamicInput(QWidget):
# ===============================================================================
#    """
#    Classe base che gestisce l'input dinamico
#    """

   
   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn):
      QWidget.__init__(self, plugIn.canvas)
      self.plugIn = plugIn
      self.canvas = self.plugIn.canvas
      self.prevPart = None # parte precedente il punto da spostare in modo grip
      self.nextPart = None # parte successiva il punto da spostare in modo grip

      self.resValue = None    # valore risultante
      self.resStr = ""        # risultato in formato stringa
      
      self.default = None 
      self.mousePos = QPoint()
      self.isVisible = False
      
      self.initGui()
      self.currentEdit = None
      self.refreshOnEnvVariables()


   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      self.removeItems()

 
   # ============================================================================
   # getPrompt
   # ============================================================================
   def getPrompt(self):
       return self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].toPlainText()


   # ============================================================================
   # setPrevPart
   # ============================================================================
   def setPrevPart(self, linearObject):
      if linearObject is None:
         if self.prevPart is not None:
            del self.prevPart
            self.prevPart = None
      else:
         if self.prevPart is None:
            self.prevPart = linearObject.copy()
         else:
            self.prevPart.set(linearObject)


   # ============================================================================
   # setNextPart
   # ============================================================================
   def setNextPart(self, linearObject):
      if linearObject is None:
         if self.nextPart is not None:
            del self.nextPart
            self.nextPart = None
      else:
         if self.nextPart is None:
            self.nextPart = linearObject.copy()
         else:
            self.nextPart.set(linearObject)


   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      self.show(False)
      for edit in self.edits:
         edit.removeItems()

      self.setPrevPart(None)
      self.setNextPart(None)


   # ============================================================================
   # refreshOnEnvVariables
   # ============================================================================
   def refreshOnEnvVariables(self):
      # DYNDIGRIP = Controlla la visualizzazione delle quote dinamiche durante la modifica dello stiramento dei grip
      self.dynDiGrip = QadVariables.get(QadMsg.translate("Environment variables", "DYNDIGRIP"))
      # DYNDIVIS = Controlla il numero di quote dinamiche visualizzate durante la modifica dello stiramento dei grip
      self.dynDiVis = QadVariables.get(QadMsg.translate("Environment variables", "DYNDIVIS"))
      # DYNMODE = Attiva e disattiva le funzioni di input dinamico
      self.dynMode = QadVariables.get(QadMsg.translate("Environment variables", "DYNMODE"))
      # DYNPICOORDS = Determina se l'input del puntatore utilizza un formato relativo o assoluto per le coordinate
      self.dynPiCoords = QadVariables.get(QadMsg.translate("Environment variables", "DYNPICOORDS"))
      # DYNPIFORMAT = Determina se l'input del puntatore utilizza un formato polare o cartesiano per le coordinate
      self.dynPiFormat = QadVariables.get(QadMsg.translate("Environment variables", "DYNPIFORMAT"))
      # DYNPIVIS = Controlla quando è visualizzato l'input puntatore
      self.dynPiVis = QadVariables.get(QadMsg.translate("Environment variables", "DYNPIVIS"))
      # DYNPROMPT = Controlla la visualizzazione dei messaggi di richiesta nelle descrizioni di input dinamico
      self.dynPrompt = QadVariables.get(QadMsg.translate("Environment variables", "DYNPROMPT"))


   # ============================================================================
   # setColors
   # ============================================================================
   def setColors(self):
      opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))
      
      for i in range(0, len(self.edits), 1):
         if i == QadDynamicInputEditEnum.CMD_LINE_EDIT: # per CMD_LINE_EDIT
            cmdForegroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEFORECOLOR")))
            cmdBackGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CMDLINEBACKCOLOR")))      
            self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].setColors(cmdForegroundColor, cmdBackGroundColor, None, \
                                                                        cmdBackGroundColor, cmdForegroundColor, opacity)
         else: # tutti gli edit tranne CMD_LINE_EDIT
            self.edits[i].setColors(foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)


   def isActive(self):
      # ritorna True se input dinamico è attivato
      return True if self.dynMode > 0 else False


   def isPointInputOn(self): # ritorna True se input del puntatore attivato
      return True if self.dynMode & 1 else False
        
 
   def isDimensionalInputOn(self): # ritorna True se input di quota attivato
      return True if self.dynMode & 2 else False
   
   
   def isPromptActive(self):
      return True if self.isActive() and self.dynPrompt == 1 else False


   def hasFocus(self): # ritorna True se uno widget di input ha il fuoco
      for edit in self.edits:
         if edit.hasFocus(): return True
      return False

  
   # ============================================================================
   # initGui
   # ============================================================================
   def initGui(self):
      # creo un array di edit
      self.edits = [None] * 15 # vedi QadDynamicInputEditEnum quanti elementi ha
      
      # usato per inserire un comando
      self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT] = QadDynamicInputCmdLineEdit(self)
      # usato per messaggi e scelta opzioni di comando
      self.edits[QadDynamicInputEditEnum.PROMPT_EDIT] = QadDynamicInputPromptEdit(self)
      
      # usato per richiesta generica (es. raggio, scala, angolo)
      self.edits[QadDynamicInputEditEnum.EDIT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT].lockable == False # valore non bloccabile

      # usato per indicare se coordinata assoluta "#" o relativa "@" e se cartesiana o polare "<"
      self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].inputMode = QadInputModeEnum.NONE
      self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].inputType = QadInputTypeEnum.STRING      
      # usato per coordinata X
      self.edits[QadDynamicInputEditEnum.EDIT_X] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_X].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_X].inputType = QadInputTypeEnum.FLOAT
      # usato per coordinata Y
      self.edits[QadDynamicInputEditEnum.EDIT_Y] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_Y].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_Y].inputType = QadInputTypeEnum.FLOAT
      # usato per coordinata Z
      self.edits[QadDynamicInputEditEnum.EDIT_Z] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_Z].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_Z].inputType = QadInputTypeEnum.FLOAT

      # usato per distanza dal punto precedente
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].inputType = QadInputTypeEnum.FLOAT
      
      # usato per distanza in più o in meno rispetto la distanza dal punto precedente
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].inputType = QadInputTypeEnum.FLOAT
           
      # usato per angolo dal punto precedente
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].inputType = QadInputTypeEnum.ANGLE
      
      # usato per angolo in più o in meno rispetto l'angolo dal punto precedente
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].inputType = QadInputTypeEnum.ANGLE

      # usato per distanza dal punto successivo
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].inputType = QadInputTypeEnum.FLOAT
           
      # usato per distanza in più o in meno rispetto la distanza dal punto successivo
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].inputType = QadInputTypeEnum.FLOAT
           
      # usato per angolo dal punto successivo
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].inputType = QadInputTypeEnum.ANGLE
      
      # usato per angolo in più o in meno rispetto l'angolo dal punto successivo
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT] = QadDynamicInputEdit(self)
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].inputMode = QadInputModeEnum.NOT_NULL
      self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].inputType = QadInputTypeEnum.ANGLE


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self, default = None):
      return # da virtualizzare


   # ============================================================================
   # getInitialNdxEdit
   # ============================================================================
   # restituisce la posizione del controllo iniziale
   def getInitialNdxEdit(self):
      return # da virtualizzare
   
   
   # ============================================================================
   # setInitialFocus
   # ============================================================================
   def setInitialFocus(self):
      for edit in self.edits:
         edit.setReadOnly(True)
         
      self.currentEdit = self.getInitialNdxEdit()
            
      if self.currentEdit is not None:
         widget = self.edits[self.currentEdit]
         widget.setReadOnly(False)
         #widget.setWindowFlags(widget.windowFlags() | Qt.WindowStaysOnTopHint)
         if widget.hasFocus(): # se ha già il fuoco coloro la casella e basta
            widget.focusInEvent(None)
         else:
            widget.setFocus()
      else:
         self.canvas.setFocus()


   # ============================================================================
   # setFocus
   # ============================================================================
   def setFocus(self):
      if self.currentEdit is None: # se non è settato quale edit è il corrente
         self.setInitialFocus()
         return
      
      for edit in self.edits:
         edit.setReadOnly(True)
      
      self.edits[self.currentEdit].setReadOnly(False)
      self.edits[self.currentEdit].setFocus()


   # ============================================================================
   # getNextNdxEditSequence
   # ============================================================================
   # restituisce la posizione del controllo successivo usando la sequenza
   def getNextNdxEditSequence(self, currentEdit):
      return # da virtualizzare


   # ============================================================================
   # setNextCurrentEdit
   # ============================================================================
   def setNextCurrentEdit(self):
      return # da virtualizzare


   # ============================================================================
   # getPrevNdxEditSequence
   # ============================================================================
   # restituisce la posizione del controllo precedente usando la sequenza
   def getPrevNdxEditSequence(self, currentEdit):
      return # da virtualizzare


   # ============================================================================
   # setPrevCurrentEdit
   # ============================================================================
   def setPrevCurrentEdit(self):
      return # da virtualizzare


   # ============================================================================
   # isCoordWidgetVisib
   # ============================================================================
   def isCoordWidgetVisib(self):
      # ritorna se devono essere mostrati i widget relativi alle coordinate
      return # da virtualizzare


   # ============================================================================
   # isDimensionalWidgetVisib
   # ============================================================================
   def isDimensionalWidgetVisib(self):
      return # da virtualizzare


   # ============================================================================
   # anyLockedValueEdit
   # ============================================================================
   def anyLockedValueEdit(self):
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_Z].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isLockedValue(): return True
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isLockedValue(): return True
      return False
   
   
   # ============================================================================
   # setDefault
   # ============================================================================
   def setDefault(self, default):
      # da virtualizzare
      return


   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode, mousePos = None, prompt = None, default = None):
      # da virtualizzare
      return


   # ============================================================================
   # showErr
   # ============================================================================
   def showErr(self, err = ""):
      # da virtualizzare
      return


   # ============================================================================
   # showInputMsg
   # ============================================================================
   def showInputMsg(self, inputMsg = None, inputType = QadInputTypeEnum.COMMAND, \
                    default = None, keyWords = "", inputMode = QadInputModeEnum.NONE):
      # da virtualizzare
      return


   # ============================================================================
   # mouseMoveEvent
   # ============================================================================
   def mouseMoveEvent(self, mousePos):
      # da virtualizzare
      return


   # ============================================================================
   # moveCtrls
   # ============================================================================
   def moveCtrls(self, mousePos = None):
      # sposta tutti i widget visibili a seconda del contesto
      # da virtualizzare
      return


   # ============================================================================
   # getPosAndLineMarkerForLine
   # ============================================================================
   def getPosAndLineMarkerForLine(self, pt1, pt2, offset, editWidget):
      # Restituisce la posizione di un widget edit che verrà posto nel punto medio di una linea
      # avente pt1 come punto iniziale, pt2 come punto finale ma spostata di un offset.
      # La funzione restituisce anche le linee da usare come marker line
      # le coordinate devono essere espresse in map coordinate
      angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
      if angle >= 0 and angle < math.pi:
         angle = angle + math.pi / 2
      else:
         angle = angle - math.pi / 2
         
      pt = qad_utils.getMiddlePoint(pt1, pt2)
      
      editPt = qad_utils.getPolarPointByPtAngle(pt, angle, offset)
      editPt = self.canvas.getCoordinateTransform().transform(editPt) # Transform the point from map (world) coordinates to device coordinates
      
      editWidth = editWidget.width()
      editHeight = editWidget.height()
      x = editPt.x() - (editWidth / 2)
      y = editPt.y() - (editHeight / 2)
      
      x, y = self.adjustEditPosition(x, y, editWidth, editHeight)
      editPt = QPoint(x, y);
            
      pt1Corner = qad_utils.getPolarPointByPtAngle(pt1, angle, offset)
      pt2Corner = qad_utils.getPolarPointByPtAngle(pt2, angle, offset)
      
      return editPt, [pt1, pt1Corner, pt2Corner, pt2]


   # ============================================================================
   # getPosAndLineMarkerForArc
   # ============================================================================
   def getPosAndLineMarkerForArc(self, start, center, end, offset, editWidget, LineMarkerOnlyArc = False):
      # Restituisce la posizione di un widget edit che verrà posto nel punto medio di un arco
      # avente start, il punto iniziale, center come centro e end come punto finale
      # La funzione restituisce anche le linee che formano l'arco da usare come marker line
      # se LineMarkerOnlyArc = True allora verrà restituito solo l'arco altrimenti 
      # verrà aggiunta una linea che parte dal centro dell'arco
      arc1 = QadArc()
      if arc1.fromStartCenterEndPts(start, center, end) == False:
         return self.getPosAndLineMarkerForLine(center, end, offset, editWidget)
       
      arc2 = QadArc()
      if arc2.fromStartCenterEndPts(end, center, start) == False:
         return self.getPosAndLineMarkerForLine(center, end, offset, editWidget)
         
      if arc1.length() <= arc2.length():
         arc1.radius = arc1.radius + offset
         pos, lineMarker = self.getPosAndLineMarkerForArcObj(arc1, editWidget)
         if LineMarkerOnlyArc == False and lineMarker is not None:
            lineMarker.insert(0, center)
      else:
         arc2.radius = arc2.radius + offset
         pos, lineMarker = self.getPosAndLineMarkerForArcObj(arc2, editWidget)
         if LineMarkerOnlyArc == False and lineMarker is not None:
            lineMarker.append(center)
            
      return pos, lineMarker


   # ============================================================================
   # getPosAndLineMarkerForArcObj
   # ============================================================================
   def getPosAndLineMarkerForArcObj(self, arc, editWidget):
      # Restituisce la posizione di un widget edit che verrà posto nel punto medio di un arco
      # La funzione restituisce anche le linee che formano l'arco da usare come marker line
      editPt = arc.getMiddlePt()
      editPt = self.canvas.getCoordinateTransform().transform(editPt) # Transform the point from map (world) coordinates to device coordinates
      
      editWidth = editWidget.width()
      editHeight = editWidget.height()
      x = editPt.x() - (editWidth / 2)
      y = editPt.y() - (editHeight / 2)
      
      x, y = self.adjustEditPosition(x, y, editWidth, editHeight)
      editPt = QPoint(x, y)
      
      return editPt, arc.asPolyline()


   # ============================================================================
   # adjustEditPosition
   # ============================================================================
   def adjustEditPosition(self, x, y, width, height):
      # aggiusta la posizione di un widget edit in modo che non esca dalla finestra canvas
      canvasRect = self.plugIn.canvas.rect()
      offsetY = height

      if x < 0: x = 0
      else:
         overflow = x + width - canvasRect.width()
         if overflow > 0: x = x - overflow
      
      if y < 0: y = 0
      else:
         overflow = y + height + offsetY - canvasRect.height()
         if overflow > 0: y = y - overflow

      # per evitare che il mouse si sovrapponga sposto il widget sopra il mouse (mi tengo 5 pixel di offset intorno al widget)
      if self.mousePos is not None:
         if self.mousePos.x() >= x - 5 and self.mousePos.x() <= x + width + 5 and \
            self.mousePos.y() >= y - 5 and self.mousePos.y() <= y + height + 5:
            if canvasRect.bottom() - self.mousePos.y() < self.mousePos.y():
               y = self.mousePos.y() - height - offsetY
            else:
               y = self.mousePos.y() + offsetY
      
      return int(x), int(y)


   # ============================================================================
   # refreshResult
   # ============================================================================
   def refreshResult(self, mousePos = None):
      # calcola il risultato e restituisce True se l'operazione ha successo
      # il risultato è anche impostato in self.resValue e, in formato stringa, in self.resStr
      # da virtualizzare
      return


   # ============================================================================
   # showEvaluateMsg
   # ============================================================================
   def showEvaluateMsg(self, msg):
      if self.isActive() == False or self.isVisible == False: return
      self.plugIn.showEvaluateMsg(msg)


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      # da virtualizzare
      return


   # ============================================================================
   # abort
   # ============================================================================
   def abort(self):
      self.isVisible = False
      for edit in self.edits:
         edit.show(False)

      self.show(False)
      self.plugIn.abortCommand()
      self.plugIn.clearCurrentObjsSelection()
      self.canvas.setFocus()



# ===============================================================================
class QadDynamicCmdInput(QadDynamicInput):
# ===============================================================================
#    """
#    Classe base che gestisce l'input dinamico per input di un nuovo comando
#    """


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn):
      QadDynamicInput.__init__(self, plugIn)
      
      self.resValue = None    # valore risultante
      self.resStr = ""        # risultato in formato stringa
      
      self.default = None 
      self.mousePos = QPoint()
      self.isVisible = False
      
      self.initGui()
      self.currentEdit = None


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self, default = None):
      # la funzione non deve resettare self.prevPart, self.nextPart
      self.currentEdit = None

      for i in range(0, len(self.edits), 1):
         self.edits[i].reset()
         
      # aggiorno tutti i colori dei controlli
      self.setColors()
      # se esiste un valore di default lo imposto
      if default is not None:
         self.setDefault(default)

      # commentato perchè crea problemi quando si seleziona un oggetto e si va con il mouse un un punto di grip (deseleziona l'oggetto)
      #self.plugIn.clearCurrentObjsSelection() 


   # ============================================================================
   # getInitialNdxEdit
   # ============================================================================
   # restituisce la posizione del controllo iniziale
   def getInitialNdxEdit(self):
      return QadDynamicInputEditEnum.CMD_LINE_EDIT


   # ============================================================================
   # getNextNdxEditSequence
   # ============================================================================
   # restituisce la posizione del controllo successivo usando la sequenza
   def getNextNdxEditSequence(self, currentEdit):
      return QadDynamicInputEditEnum.CMD_LINE_EDIT


   # ============================================================================
   # setNextCurrentEdit
   # ============================================================================
   def setNextCurrentEdit(self):
      if self.currentEdit is None: # se non è settato quale edit è il corrente
         self.setInitialFocus()
         return

      self.currentEdit = self.getNextNdxEditSequence(self.currentEdit)

      self.setFocus()


   # ============================================================================
   # getPrevNdxEditSequence
   # ============================================================================
   # restituisce la posizione del controllo precedente usando la sequenza
   def getPrevNdxEditSequence(self, currentEdit):
      return QadDynamicInputEditEnum.CMD_LINE_EDIT


   # ============================================================================
   # setPrevCurrentEdit
   # ============================================================================
   def setPrevCurrentEdit(self):
      if self.currentEdit is None: # se non è settato quale edit è il corrente
         self.setInitialFocus()
         return

      self.currentEdit = self.getNextNdxEditSequence(self.currentEdit)

      self.setFocus()


   # ============================================================================
   # isCoordWidgetVisib
   # ============================================================================
   def isCoordWidgetVisib(self):
      # ritorna se devono essere mostrati i widget relativi alle coordinate
      # se è abilitato l'input del puntatore e la visualizzazione delle coordinate è impostata da dynPiVis = 2 (visualizza sempre)
      if self.isPointInputOn() and self.dynPiVis == 2:
         return True
      else:
         return False


   # ============================================================================
   # isDimensionalWidgetVisib
   # ============================================================================
   def isDimensionalWidgetVisib(self):
      # se non è abilitato l'input di quota
      if self.isDimensionalInputOn() == False: return False
      # se esiste una parte precedente o una parte successiva
      if self.prevPart is not None or self.nextPart is not None:
         return True
      else:
         return False


   # ============================================================================
   # setDefault
   # ============================================================================
   def setDefault(self, default):
      self.default = default
      self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].showMsg(self.default)


   # ============================================================================
   # setPrevNextPart
   # ============================================================================
   def setPrevNextPart(self, entity, gripPoint):
      # entity è di tipo QadEntity
      # gripPoint è di tipo QadEntityGripPoint
      prevPart = None
      nextPart = None
      # verifico se l'entità appartiene ad uno stile di quotatura
      if QadDimStyles.isDimEntity(entity):
         pass
      else:
         qadGeom = entity.getQadGeom(gripPoint.atGeom, gripPoint.atSubGeom)
         qadGeomType = qadGeom.whatIs()
         if qadGeomType == "ARC" or qadGeomType == "ELLIPSE_ARC":
            if gripPoint.gripType == QadGripPointTypeEnum.ARC_MID_POINT:
               prevPart = qadGeom.copy()
               nextPart = qadGeom.copy()
            else:
               if qad_utils.ptNear(qadGeom.getStartPt(), gripPoint.getPoint()):
                  nextPart = qadGeom.copy()
               elif qad_utils.ptNear(qadGeom.getEndPt(), gripPoint.getPoint()):
                  prevPart = qadGeom.copy()
                  
         elif qadGeomType == "POLYLINE":
            prevPart, nextPart = qadGeom.getPrevNextLinearObjectsAtVertex(gripPoint.nVertex)
            if (gripPoint.gripType == QadGripPointTypeEnum.LINE_MID_POINT or \
                gripPoint.gripType == QadGripPointTypeEnum.ARC_MID_POINT) and \
               nextPart is not None:
               prevPart = nextPart.copy()
            
         elif qadGeomType == "CIRCLE":
            if qadGeom.isPtOnCircle(gripPoint.getPoint()):
               prevPart = QadLine()
               prevPart.set(qadGeom.center, gripPoint.getPoint())
            
         elif qadGeomType == "ELLIPSE":
            if qadGeom.containsPt(gripPoint.getPoint()):
               prevPart = QadLine()
               prevPart.set(qadGeom.center, gripPoint.getPoint())
               
      self.setPrevPart(prevPart)
      self.setNextPart(nextPart)
      

   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode, mousePos = None, prompt = None, default = None):
      # se si tratta di rendere invisibile lo faccio indipendentemente dal fatto che sia attivo o meno
      # (serve per gestire F12)
      if mode == False:
         self.isVisible = False
         for edit in self.edits:
            edit.show(False)
         return False

      if self.isActive() == False: return False

      # se viene passata la posizione del mouse la funzione
      # resetta lo stato dell'input dinamico (errori, fuoco)
      if mousePos is not None:
         self.reset(default)

      if prompt is not None:
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].showMsg(prompt, False, False, False) # senza aggiornare la posizione dei controlli
      
      self.isVisible = True

      visibList = [False] * len(self.edits)
      
      if self.isPromptActive() and len(self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].toPlainText()) > 0:
         visibList[QadDynamicInputEditEnum.PROMPT_EDIT] = True

      if len(self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].toPlainText()) > 0:
         visibList[QadDynamicInputEditEnum.CMD_LINE_EDIT] = True
      else:
         # se devo visualizzare i widget delle coordinate
         if self.isCoordWidgetVisib():
            visibList[QadDynamicInputEditEnum.EDIT_X] = True
            visibList[QadDynamicInputEditEnum.EDIT_Y] = True
         # se devo mostrare i widget delle quote
         if self.isDimensionalWidgetVisib():
            if self.prevPart is not None:
               gType = self.prevPart.whatIs()
               if gType == "LINE":
                  visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True # usato per lunghezza segmento precedente
               elif gType == "ARC": # arco
                  visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True # usato per lunghezza raggio arco
                  visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = True # usato per lunghezza raggio arco                  
                  visibList[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = True # usato per angolo arco nel punto finale della parte precedente
   
            if self.nextPart is not None:
               gType = self.nextPart.whatIs()
               if gType == "LINE":
                  visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True # usato per lunghezza segmento successivo
               elif gType == "ARC": # arco
                  # se nextPart e prevPart sono uguali 
                  if self.prevPart is not None and self.nextPart == self.prevPart:
                     visibList[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT] = True # usato per angolo totale arco
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = False # usato per lunghezza raggio arco parte precedente                                                   
                  else:
                     visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True # usato per lunghezza raggio arco
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = True # usato per lunghezza raggio arco                                       
                  visibList[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT] = True # usato per angolo arco nel punto iniziale della parte successiva
                     
      for i in range(0, len(self.edits), 1):
         self.edits[i].show(visibList[i])
      
      self.setFocus()
      
      # riposiziono i widget
      if mousePos is None:
         self.mouseMoveEvent(self.canvas.mouseLastXY())
      else:
         self.mouseMoveEvent(mousePos)
      
      return self.isVisible


   # ============================================================================
   # showErr
   # ============================================================================
   def showErr(self, err = ""):
      if self.isActive() == False: return
      
      self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].show(False)
      if self.isPromptActive():
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].error = True
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].setColors() # ricolora con i bordi rossi perchè error=True
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].show(True)
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].showMsg(err)
      
         self.canvas.setFocus()

      self.moveCtrls() # per riposizionare i controlli

   
   # ============================================================================
   # mouseMoveEvent
   # ============================================================================
   def mouseMoveEvent(self, mousePos):
      if self.isActive() == False or self.isVisible == False: return

      point = self.canvas.getCoordinateTransform().toMapCoordinates(mousePos) # posizione
            
      # se i widget delle coordinate sono visibili
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
         self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(point.x()), False, False, False) # senza aggiornare la posizione dei controlli
         self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(point.y()), False, False, False) # senza aggiornare la posizione dei controlli
               
      if self.prevPart is not None:
         gType = self.prevPart.whatIs()
         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # usato per lunghezza segmento precedente
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.length()), False, False, False) # senza aggiornare la posizione dei controlli
         elif gType == "ARC":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # usato per lunghezza raggio arco
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # senza aggiornare la posizione dei controlli
               
            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
               # usato per lunghezza raggio arco
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # senza aggiornare la posizione dei controlli
               
            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible():
               # usato per angolo arco nel punto finale della parte precedente
               if self.prevPart.reversed:
                  angle = self.prevPart.startAngle
               else:
                  angle = self.prevPart.endAngle
                  
               if angle >= math.pi and angle < 2 * math.pi:
                  angle = 2 * math.pi - angle
               msg = qad_utils.numToStringFmt(qad_utils.toDegrees(angle)) + u'\N{DEGREE SIGN}' # simbolo dei gradi
               self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].showMsg(msg, False, False, False) # senza aggiornare la posizione dei controlli
               
      if self.nextPart is not None:
         gType = self.nextPart.whatIs()
         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # usato per lunghezza segmento successivo
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.length()), False, False, False) # senza aggiornare la posizione dei controlli
         elif gType == "ARC":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # usato per lunghezza raggio arco
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # senza aggiornare la posizione dei controlli
               
            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
               # usato per lunghezza raggio arco
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # senza aggiornare la posizione dei controlli
               
            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible():
               # usato per angolo arco nel punto iniziale della parte successiva
               if self.nextPart.reversed:
                  angle = self.nextPart.endAngle
               else:
                  angle = self.nextPart.startAngle
                  
               if angle >= math.pi and angle < 2 * math.pi:
                  angle = 2 * math.pi - angle
               msg = qad_utils.numToStringFmt(qad_utils.toDegrees(angle)) + u'\N{DEGREE SIGN}' # simbolo dei gradi
               self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].showMsg(msg, False, False, False) # senza aggiornare la posizione dei controlli

            # se nextPart e prevPart sono uguali 
            if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible():
               # usato per angolo totale arco
               msg = qad_utils.numToStringFmt(qad_utils.toDegrees(self.nextPart.totalAngle())) + u'\N{DEGREE SIGN}' # simbolo dei gradi
               self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].showMsg(msg, False, False, False) # senza aggiornare la posizione dei controlli


      if self.currentEdit is not None:
         self.edits[self.currentEdit].focusInEvent(None) # riporto il fuoco sul controllo corrente

      self.moveCtrls(mousePos)
      
      return

      
   # ============================================================================
   # moveCtrls
   # ============================================================================
   def moveCtrls(self, mousePos = None):
      # sposta tutti i widget visibili a seconda del contesto
      if mousePos is not None:         
         self.mousePos.setX(mousePos.x())
         self.mousePos.setY(mousePos.y())

      height = self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].height()
      offset = 5
      
      width = 0
      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         width += self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].width()

      x = self.mousePos.x() + height
      y = self.mousePos.y() + height

      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].lockedPos or \
         self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].lockedPos:
         return;
      if self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].isVisible():
         if width > 0 : width += offset
         offsetX_cmdLineEdit = width
         width += self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].width()
         
      x, y = self.adjustEditPosition(x, y, width, height)
                  
      if self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].isVisible():
         self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].move(x + offsetX_cmdLineEdit, y)

      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible() or \
         self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible():
         
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
            if width > 0 : width += offset
            offsetX_editX = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_X].width()
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible():
            if width > 0 : width += offset
            offsetX_editY = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_Y].width()
            
         x, y = self.adjustEditPosition(x, y, width, height)
            
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_X].move(x + offsetX_editX, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_Y].move(x + offsetX_editY, y)

      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         x, y = self.adjustEditPosition(x, y, width, height)
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].move(x, y)

      if self.prevPart is not None:
         p1 = None
         offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
         gType = self.prevPart.whatIs() 

         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # usato per lunghezza segmento precedente
               p1 = self.prevPart.getStartPt()
               p2 = self.prevPart.getEndPt()
         elif gType == "ARC":
            center = self.prevPart.center
            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible():
               # usato per angolo arco nel punto finale della parte precedente
               p2 = self.prevPart.getEndPt()
               p1 = QgsPointXY(center.x() + self.prevPart.radius, center.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(p1, center, p2, offset, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT])
               
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # se non nullo disegno la linea di marker aggiugendo una linea
                  if qad_utils.ptNear(lineMarkers[0], center):
                     lineMarkers.append(center)
                  else:
                     lineMarkers.insert(0, center)
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
               # usato per lunghezza raggio arco nel punto iniziale della parte precedente
               p1 = self.prevPart.center
               p2 = self.prevPart.getStartPt()
               editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                     0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT])
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].move(editPt.x(), editPt.y())
               del editPt
               # disegno la linea di marker
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].setLinesMarker(lineMarkers)
               del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               # usato per lunghezza raggio arco nel punto finale della parte precedente
               # oppure lunghezza raggio nel punto medio se parte precedente e successiva coincidono
               p1 = self.prevPart.center
               # se nextPart e prevPart sono uguali 
               if self.nextPart is not None and self.nextPart == self.prevPart:
                  p2 = self.prevPart.getMiddlePt()
               else:
                  p2 = self.prevPart.getEndPt()
               offset = 0
            else:
               p1 = None


         if p1 is not None:
            editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                  offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].move(editPt.x(), editPt.y())
            del editPt
            # disegno la linea di marker
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].setLinesMarker(lineMarkers)
            del lineMarkers
               
      if self.nextPart is not None:
         p1 = None
         offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
         gType = self.nextPart.whatIs()
         
         if gType == "LINE":
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # usato per lunghezza segmento precedente
               p1 = self.nextPart.getStartPt()
               p2 = self.nextPart.getEndPt()
         elif gType == "ARC":
            center = self.nextPart.center
            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible():
               # usato per angolo arco nel punto iniziale della parte successiva
               p2 = self.nextPart.getStartPt()
               p1 = QgsPointXY(center.x() + self.nextPart.radius, center.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(p1, center, p2, offset, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT])
               
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # se non nullo disegno la linea di marker aggiugendo una linea
                  if qad_utils.ptNear(lineMarkers[0], center):
                     lineMarkers.append(center)
                  else:
                     lineMarkers.insert(0, center)
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

            # se nextPart e prevPart sono uguali 
            if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible():
               # usato per angolo totale arco
               offsetArc = height * self.canvas.mapSettings().mapUnitsPerPixel()
               totalArc = QadArc(self.nextPart)
               totalArc.radius = totalArc.radius + offsetArc
               editPt, lineMarkers = self.getPosAndLineMarkerForArcObj(totalArc, self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT])
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # se non nullo disegno la linea di marker aggiugendo una linea
                  lineMarkers.append(center)
                  lineMarkers.insert(0, center)
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

            if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
               # usato per lunghezza raggio arco nel punto finale della parte successiva
               p1 = self.nextPart.center
               p2 = self.nextPart.getEndPt()
               editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                     0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT])
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].move(editPt.x(), editPt.y())
               del editPt
               # disegno la linea di marker
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].setLinesMarker(lineMarkers)
               del lineMarkers
               
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
               # usato per lunghezza raggio arco nel punto iniziale della parte successiva
               p1 = self.nextPart.center
               p2 = self.nextPart.getStartPt()
               offset = 0
            else:
               p1 = None
               
         if p1 is not None:
            editPt, lineMarkers = self.getPosAndLineMarkerForLine(p1, p2, \
                                                                  offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT])
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].move(editPt.x(), editPt.y())
            del editPt
            # disegno la linea di marker
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].setLinesMarker(lineMarkers)
            del lineMarkers


   # ============================================================================
   # refreshResult
   # ============================================================================
   def refreshResult(self, mousePos = None):
      # calcola il risultato e restituisce True se l'operazione ha successo
      # il risultato è anche impostato in self.resValue e, in formato stringa, in self.resStr
      self.resStr = self.resValue = self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].toPlainText()
      return True


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      if self.currentEdit is None:
         return
               
      if e.key() == Qt.Key_Return or e.key == Qt.Key_Enter:
         msg = self.resStr if self.refreshResult() == True else "" # ricalcolo il risultato e lo uso in formato stringa
         self.showEvaluateMsg(msg)
      else:
         if e.text() != "":
            self.edits[self.currentEdit].keyPressEvent(e)
            self.show(True)



# ===============================================================================
class QadDynamicEditInput(QadDynamicInput):
# ===============================================================================
#    """
#    Classe che gestisce l'input dinamico
#    """

   
   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn, context = QadDynamicInputContextEnum.NONE):
      QadDynamicInput.__init__(self, plugIn)

      self.context = context
      self.prevPoint = None # punto usato come punto precedente durante la digitazione dei punti di un nuovo oggetto (in map coordinate)
      
      self.resPt = QgsPointXY() # punto risultante
      
      self.inputMode = QadInputModeEnum.NONE
      self.inputType = QadInputTypeEnum.NONE
      self.keyWords = []
      self.englishKeyWords = []
      
      self.initGui()
      # flag che determina se la forzatura della visibilità dei widget per l'inserimento delle coordinate di un punto (x,y,z)
      self.forcedCoordWidgetVisib = False


   # ============================================================================
   # setPrevPoint
   # ============================================================================
   def setPrevPoint(self, pt):
      if pt is None:
         if self.prevPoint is not None:
            del self.prevPoint
            self.prevPoint = None
      else:
         if self.prevPoint is None:
            self.prevPoint = QgsPointXY(pt)
         else:
            self.prevPoint.setX(pt.x())
            self.prevPoint.setY(pt.y())
         
          
   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      QadDynamicInput.removeItems(self)
      self.setPrevPoint(None)


   # ============================================================================
   # reset
   # ============================================================================
   def reset(self, default = None):
      # la funzione non deve resettare self.prevPoint, self.prevPart, self.nextPart
      self.currentEdit = None
      self.forcedCoordWidgetVisib = False

      for i in range(0, len(self.edits), 1):
         self.edits[i].reset()
         
      self.edits[QadDynamicInputEditEnum.EDIT].inputType = self.inputType
      self.edits[QadDynamicInputEditEnum.EDIT].inputMode = self.inputMode
         
      # aggiorno tutti i colori dei controlli
      self.setColors()
      # se esiste un valore di default lo imposto
      if default is not None:
         self.setDefault(default)


   # ============================================================================
   # getInitialNdxEdit
   # ============================================================================
   # restituisce la posizione del controllo iniziale
   def getInitialNdxEdit(self):
      if self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
         self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
         self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         return QadDynamicInputEditEnum.EDIT
         
      elif self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D:
         # se devo visualizzare i widget delle coordinate
         if self.isCoordWidgetVisib():
            return QadDynamicInputEditEnum.EDIT_X
         # se devo mostrare i widget delle quote
         elif self.isDimensionalWidgetVisib():
            # se esiste un punto precedente
            if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
               return QadDynamicInputEditEnum.EDIT_DIST_PREV_PT
            else: # spostamento di un punto in modalità grip
               if self.dynDiVis == 0 or self.dynDiVis == 1: # solo una quota alla volta (0) o due quota alla volta (1)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     return QadDynamicInputEditEnum.EDIT_DIST_PREV_PT
                  elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     return QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT
               elif self.dynDiVis == 2: # come definito dalla variabile dynDiGrip
                  if self.dynDiGrip & 1: # quota risultante (distanza dal punto precedente)
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_DIST_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT
                  elif self.dynDiGrip & 2: # quota modifica lunghezza (distanza dalla posizione precedente dello stesso punto)
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT
                  elif self.dynDiGrip & 4: # quota angolo assoluto
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_ANG_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT
                  elif self.dynDiGrip & 8: # quota modifica angolo (angolo relativo all'angolo con il punto precedente)
                     if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT
                     elif self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                        return QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT

      return None


   # ============================================================================
   # getNextNdxEditSequence
   # ============================================================================
   # restituisce la posizione del controllo successivo usando la sequenza
   def getNextNdxEditSequence(self, currentEdit):
      editSequence = [QadDynamicInputEditEnum.CMD_LINE_EDIT, \
                      QadDynamicInputEditEnum.EDIT, \
                      QadDynamicInputEditEnum.EDIT_X, \
                      QadDynamicInputEditEnum.EDIT_Y, \
                      QadDynamicInputEditEnum.EDIT_Z, \
                      QadDynamicInputEditEnum.EDIT_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_Z]
      start = i = editSequence.index(currentEdit)
      maxLimit = len(editSequence) - 1
      while True:
         i = 0 if i >= maxLimit else i + 1 # ciclico
         if i == start: break
         
         # se i widgets di quota sono visibili come definito dalla variabile dynDiGrip o
         # si stanno visualizzando i widgets delle coordinate
         # allora i widgets sono già tutti visibili
         if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
            self.isCoordWidgetVisib(): 
            if self.edits[editSequence[i]].isVisible(): # controllo visibile successivo
               return editSequence[i]
         else:
            if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
               # si tratta di inserimento di un nuovo punto a fine linea
               if self.prevPoint is not None:
                  if editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                     editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT:
                     return editSequence[i]
               else: # se si era in modalità grip
                  if (self.prevPart is not None and self.prevPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT)) or \
                     (self.nextPart is not None and self.nextPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT or \
                       editSequence[i]== QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT)):
                     return editSequence[i]
                  
      return editSequence[currentEdit]
      
      
   # ============================================================================
   # setNextCurrentEdit
   # ============================================================================
   def setNextCurrentEdit(self):
      if self.currentEdit is None: # se non è settato quale edit è il corrente
         self.setInitialFocus()
         return

      nextEdit = self.getNextNdxEditSequence(self.currentEdit)
      
      # se i widgets di quota sono visibili come definito dalla variabile dynDiGrip o
      # si stanno visualizzando i widgets delle coordinate
      # allora i widgets sono già tutti visibili
      if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
         self.isCoordWidgetVisib(): 
         self.currentEdit = nextEdit
      else:
         if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
            if self.dynDiVis == 0: # solo una quota alla volta
               # spengo il controllo corrente
               self.edits[self.currentEdit].show(False)
               self.currentEdit = nextEdit
               # visualizzo il controllo successivo
               self.edits[self.currentEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # posiziono gli attributi che, essendo prima spenti, hanno una posizione non aggiornata  
            elif self.dynDiVis == 1: # solo due quota alla volta
               # spengo il controllo corrente
               self.edits[self.currentEdit].show(False)
               self.currentEdit = nextEdit
               nextEdit = self.getNextNdxEditSequence(nextEdit)
               # visualizzo il controllo successivo del successivo
               self.edits[nextEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # posiziono gli attributi che, essendo prima spenti, hanno una posizione non aggiornata
               
      self.setFocus()


   # ============================================================================
   # getPrevNdxEditSequence
   # ============================================================================
   # restituisce la posizione del controllo precedente usando la sequenza
   def getPrevNdxEditSequence(self, currentEdit):
      editSequence = [QadDynamicInputEditEnum.CMD_LINE_EDIT, \
                      QadDynamicInputEditEnum.EDIT, \
                      QadDynamicInputEditEnum.EDIT_X, \
                      QadDynamicInputEditEnum.EDIT_Y, \
                      QadDynamicInputEditEnum.EDIT_Z, \
                      QadDynamicInputEditEnum.EDIT_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT, \
                      QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT, \
                      QadDynamicInputEditEnum.EDIT_Z]
      start = i = editSequence.index(self.currentEdit)
      maxLimit = len(editSequence) - 1
      while True:
         i = maxLimit if i <= 0 else i - 1 # ciclico
         if i == start: break
         
         # se i widgets di quota sono visibili come definito dalla variabile dynDiGrip o
         # si stanno visualizzando i widgets delle coordinate
         # allora i widgets sono già tutti visibili
         if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
            self.isCoordWidgetVisib(): 
            if self.edits[editSequence[i]].isVisible(): # controllo visibile successivo
               return editSequence[i]
         else:
            if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
               if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
                  if editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                     editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT:
                     return editSequence[i]
               else: # se si era in modalità grip
                  if (self.prevPart is not None and self.prevPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_PREV_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT)) or \
                     (self.nextPart is not None and self.nextPart.whatIs() == "LINE" and \
                      (editSequence[i] == QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT or \
                       editSequence[i]== QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT or \
                       editSequence[i] == QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT)):
                     return editSequence[i]
                  
      return editSequence[currentEdit]


   # ============================================================================
   # setPrevCurrentEdit
   # ============================================================================
   def setPrevCurrentEdit(self):
      if self.currentEdit is None: # se non è settato quale edit è il corrente
         self.setInitialFocus()
         return

      prevEdit = self.getPrevNdxEditSequence(self.currentEdit)
      
      # se i widgets di quota sono visibili come definito dalla variabile dynDiGrip o
      # si stanno visualizzando i widgets delle coordinate
      # allora i widgets sono già tutti visibili
      if (self.isDimensionalWidgetVisib() == False and self.dynDiVis == 2) or \
         self.isCoordWidgetVisib(): 
         self.currentEdit = prevEdit
      else:
         if self.isDimensionalWidgetVisib() and self.dynDiVis != 2:
            if self.dynDiVis == 0: # solo una quota alla volta
               # spengo il controllo corrente
               self.edits[self.currentEdit].show(False)
               self.currentEdit = prevEdit
               # visualizzo il controllo successivo
               self.edits[self.currentEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # posiziono gli attributi che, essendo prima spenti, hanno una posizione non aggiornata
            elif self.dynDiVis == 1: # solo due quota alla volta
               # spengo il controllo corrente
               self.edits[self.currentEdit].show(False)
               self.currentEdit = prevEdit
               prevEdit = self.getNextNdxEditSequence(prevEdit)
               # visualizzo il controllo precedente del precedente
               self.edits[prevEdit].show(True)
               self.mouseMoveEvent(self.canvas.mouseLastXY()) # posiziono gli attributi che, essendo prima spenti, hanno una posizione non aggiornata
               
      self.setFocus()


   # ============================================================================
   # isCoordWidgetVisib
   # ============================================================================
   def isCoordWidgetVisib(self):
      # ritorna se devono essere mostrati i widget relativi alle coordinate
      
      # se non è ammessa la restituzione di un punto
      if not (self.inputType & QadInputTypeEnum.POINT2D) and not(self.inputType & QadInputTypeEnum.POINT3D):
         return False
      # se la visualizzazione delle coordinate è forzata 
      if self.forcedCoordWidgetVisib: return True
      # se (non esiste nè un punto precedente, una parte precedente, una successiva oppure non è abilitato l'input di quota) ed è abilitato l'input del puntatore oppure se
      # la visualizzazione delle coordinate è forzata         
      if (((self.prevPoint is None and self.prevPart is None and self.nextPart is None) or self.isDimensionalInputOn() == False) and \
          self.isPointInputOn()):
         return True
      else:
         return False


   # ============================================================================
   # isDimensionalWidgetVisib
   # ============================================================================
   def isDimensionalWidgetVisib(self):
      # se non è ammessa la restituzione di un punto
      if not (self.inputType & QadInputTypeEnum.POINT2D) and not(self.inputType & QadInputTypeEnum.POINT3D):
         return False
      # se non è abilitato l'input di quota
      if self.isDimensionalInputOn() == False: return False

      # la visualizzazione delle coordinate non deve essere forzata
      if self.forcedCoordWidgetVisib: return False

      # se il widget di input generico deve essere invisibile
      if self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
         self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
         self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         return False
      
      # se esiste un punto precedente oppure una parte precedente o una parte successiva
      if self.prevPoint is not None or self.prevPart is not None or self.nextPart is not None:
         return True
      else:
         return False


   # ============================================================================
   # setDefault
   # ============================================================================
   def setDefault(self, default):
      self.default = default
      
      # se il risultato non dipende dalla posizione del mouse
      if self.context == QadDynamicInputContextEnum.COMMAND:
         self.edits[QadDynamicInputEditEnum.CMD_LINE_EDIT].showMsg(self.default)
         
      elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
           self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
           self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         # se si tratta di un numero
         if type(self.default) == int or type(self.default) == long or type(self.default) == float:
            if self.inputType & QadInputTypeEnum.ANGLE:
               self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(self.default)))
            else:
               self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(self.default))
         # se si tratta di un punto
         elif type(self.default) == QgsPointXY:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.pointToStringFmt(self.default))
         else:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(unicode(self.default))


   # ============================================================================
   # show
   # ============================================================================
   def show(self, mode, mousePos = None, prompt = None, default = None):
      # se si tratta di rendere invisibile lo faccio indipendentemente dal fatto che sia attivo o meno
      # (serve per gestire F12)
      if mode == False:
         self.isVisible = False
         for edit in self.edits:
            edit.show(False)
         return False

      if self.isActive() == False: return False

      # se viene passata la posizione del mouse la funzione
      # resetta lo stato dell'input dinamico (errori, fuoco)
      if mousePos is not None:
         self.reset(default)

      if prompt is not None:
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].showMsg(prompt, False, False, False) # senza aggiornare la posizione dei controlli
      
      self.isVisible = True

      visibList = [False] * len(self.edits)
      
      if self.isPromptActive() and len(self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].toPlainText()) > 0:
         visibList[QadDynamicInputEditEnum.PROMPT_EDIT] = True

      # se richiede un numero reale o un angolo e 
      # la visualizzazione delle coordinate non è forzata
      if (self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE) and \
            not self.forcedCoordWidgetVisib:
         visibList[QadDynamicInputEditEnum.EDIT] = True

      # se devo visualizzare i widget delle coordinate        
      elif self.isCoordWidgetVisib():
         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText() != "":
            visibList[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE] = True
            
         visibList[QadDynamicInputEditEnum.EDIT_X] = True
         visibList[QadDynamicInputEditEnum.EDIT_Y] = True
         if self.inputType & QadInputTypeEnum.POINT3D:
            visibList[QadDynamicInputEditEnum.EDIT_Z] = True
      # se devo mostrare i widget delle quote
      elif self.isDimensionalWidgetVisib():
         if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
            if self.dynDiVis == 0: # solo una quota alla volta
               if self.currentEdit is None:
                  visibList[self.getInitialNdxEdit()] = True
               else:
                  visibList[self.currentEdit] = True
            else:
               visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True
               visibList[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = True
         else: # spostamento di un punto in modalità grip
            if self.dynDiVis == 0: # solo una quota alla volta
               if self.currentEdit is None:
                  first = self.getInitialNdxEdit()
               else:
                  first = self.currentEdit
               
               if first is not None:
                  visibList[first] = True
                  
            elif self.dynDiVis == 1: # solo due quota alla volta               
               if self.currentEdit is None:
                  first = self.getInitialNdxEdit()
               else:
                  first = self.currentEdit
                  
               if first is not None:
                  visibList[first] = True
                  second = self.getNextNdxEditSequence(first)
                  if second is not None:
                     visibList[second] = True
                  
            elif self.dynDiVis == 2: # come definito dalla variabile dynDiGrip
               if self.dynDiGrip & 1: # quota risultante (distanza dal punto precedente)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True
               if self.dynDiGrip & 2: # quota modifica lunghezza (distanza dalla posizione precedente dello stesso punto)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = True
               if self.dynDiGrip & 4: # quota angolo assoluto
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT] = True
               if self.dynDiGrip & 8: # quota modifica angolo (angolo relativo all'angolo con il punto precedente)
                  if self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT] = True
                  if self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                     visibList[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT] = True
                     
#             # eccezione per questo flag che viene considerato indipendentemente dal valore di self.dynDiVis
#             if self.dynDiGrip & 16: # lunghezza raggio
#                if self.prevPart is not None and self.prevPart.whatIs() == "ARC":
#                   # usato per lunghezza raggio nel punto finale della parte precedente
#                   # oppure lunghezza raggio nel punto medio se parte precedente e successiva sono lo stesso arco
#                   visibList[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT] = True
#                   # usato per lunghezza raggio nel punto iniziale della parte precedente
#                   visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = True
#                if self.nextPart is not None and self.nextPart.whatIs() == "ARC":
#                   # se nextPart e prevPart sono uguali 
#                   if self.prevPart is not None and self.nextPart == self.prevPart:
#                      # usato per lunghezza raggio nel punto iniziale della parte precedente
#                      visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT] = False
#                   else:
#                      # usato per lunghezza raggio nel punto iniziale della parte successiva
#                      visibList[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT] = True
#                      # usato per lunghezza raggio nel punto finale della parte successiva
#                      visibList[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT] = True
                     

      elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
           self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
           self.inputType & QadInputTypeEnum.FLOAT or self.inputType & QadInputTypeEnum.ANGLE:
         visibList[QadDynamicInputEditEnum.EDIT] = True

      for i in range(0, len(self.edits), 1):
         self.edits[i].show(visibList[i])
      
      self.setFocus()
      
      # riposiziono i widget
      if mousePos is None:
         self.mouseMoveEvent(self.canvas.mouseLastXY())
      else:
         self.mouseMoveEvent(mousePos)
      
      return self.isVisible


   # ============================================================================
   # showErr
   # ============================================================================
   def showErr(self, err = ""):
      if self.isActive() == False: return
      
      if self.currentEdit is not None:
         self.edits[self.currentEdit].error = True
         self.edits[self.currentEdit].setColors() # ricolora con i bordi rossi perchè error=True

      self.moveCtrls() # per riposizionare i controlli
   
   
   # ============================================================================
   # showInputMsg
   # ============================================================================
   def showInputMsg(self, inputMsg = None, inputType = QadInputTypeEnum.COMMAND, \
                    default = None, keyWords = "", inputMode = QadInputModeEnum.NONE):
      if self.isActive() == False: return False

      # context va inizializzato prima dal comando
      self.inputType = inputType
      self.inputMode = inputMode
      self.keyWords = []
      self.englishKeyWords = []
      
      if (keyWords is not None) and len(keyWords) > 0:
         # carattere separatore tra le parole chiave in lingua locale e quelle in inglese 
         localEnglishKeyWords = keyWords.split("_")
         self.keyWords = localEnglishKeyWords[0].split("/") # carattere separatore delle parole chiave
         if len(localEnglishKeyWords) > 1:
            self.englishKeyWords = localEnglishKeyWords[1].split("/") # carattere separatore delle parole chiave
         else:
            del self.englishKeyWords[:]

         initial = inputMsg.find("[")
         self.show(True, self.canvas.mouseLastXY(), inputMsg[0:initial], default) # resetta tutto
      else:
         self.show(True, self.canvas.mouseLastXY(), inputMsg, default) # resetta tutto


   # ============================================================================
   # mouseMoveEvent
   # ============================================================================
   def mouseMoveEvent(self, mousePos):
      if self.isActive() == False or self.isVisible == False: return

      self.refreshResult(mousePos)
            
      # se i widget delle coordinate sono visibili
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
         if self.prevPoint is None: # se non è settato nell'input dinamico lo cerco nel plugin (cosa che fa anche refreshResult)
            if self.plugIn.lastPoint is None:
               prevPt = QgsPointXY(0,0)
            else:
               prevPt = self.plugIn.lastPoint 
         else:
            prevPt = self.prevPoint
         
         # se si tratta di coordinate relative
         relative = True if self.dynPiCoords == 0 else False
         # se si tratta di coordinate polari
         polar = True if self.dynPiFormat == 0 else False
         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
            coordType = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
            if "@" in coordType: relative = True
            elif "#" in coordType: relative = False
            polar = True if "<" in coordType else False
         else: # se non è esplicito che sia relativo ma lo è per via di dynPiCoords
            prevPt = self.prevPoint # se non c'è il punto precedente impostato nell'input dinamico 
            if prevPt is None:
               relative = False
               polar = False

         if polar == False: # se sono coordinate cartesiane
            if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue() == False:
               # se si tratta di coordinate relative
               if relative:
                  self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(self.resPt.x() - prevPt.x()), False, False, False) # senza aggiornare la posizione dei controlli
               else:
                  self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(self.resPt.x()), False, False, False) # senza aggiornare la posizione dei controlli

            if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue() == False:
               # se si tratta di coordinate relative
               if relative:
                  self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(self.resPt.y() - prevPt.y()), False, False, False) # senza aggiornare la posizione dei controlli
               else:
                  self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(self.resPt.y()), False, False, False) # senza aggiornare la posizione dei controlli

            if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible() and \
               self.edits[QadDynamicInputEditEnum.EDIT_Z].isLockedValue() == False:
                  # se si tratta di coordinate relative
                  if relative:
                     self.edits[QadDynamicInputEditEnum.EDIT_Z].showMsg(qad_utils.numToStringFmt(self.resPt.z() - prevPt.z()), False, False, False) # senza aggiornare la posizione dei controlli
                  else:
                     self.edits[QadDynamicInputEditEnum.EDIT_Z].showMsg(qad_utils.numToStringFmt(self.resPt.z()), False, False, False) # senza aggiornare la posizione dei controlli
         elif prevPt is not None: # coordinate polari
            # nel caso di coordinate polari EDIT_X contiene la distanza dal punto precedente o da 0,0
            if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue() == False:
               if relative:
                  dist = qad_utils.getDistance(prevPt, self.resPt)
               else:
                  dist = qad_utils.getDistance(QgsPointXY(0, 0), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # senza aggiornare la posizione dei controlli
            
            # nel caso di coordinate polari EDIT_Y contiene l'angolo
            if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue() == False:
               if relative:
                  angle = qad_utils.getAngleBy2Pts(prevPt, self.resPt, 0) # senza tolleranza
               else:
                  angle = qad_utils.getAngleBy2Pts(QgsPointXY(0, 0), self.resPt, 0) # senza tolleranza
               
               self.edits[QadDynamicInputEditEnum.EDIT_Y].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # senza aggiornare la posizione dei controlli

      # se il widget delle quote "distanza dal punto precedente" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue() == False:        
         if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
            dist = qad_utils.getDistance(self.prevPoint, self.resPt)
            self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # senza aggiornare la posizione dei controlli
         elif self.prevPart is not None:
            gType = self.prevPart.whatIs()
            
            if gType == "LINE": # spostamento di un punto di un segmento in modalità grip
               dist = qad_utils.getDistance(self.prevPart.getStartPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # senza aggiornare la posizione dei controlli
            elif gType == "ARC": # spostamento di un punto di un arco in modalità grip
               # usato per lunghezza raggio nel punto finale della parte precedente
               # oppure lunghezza raggio nel punto medio se parte precedente e successiva sono lo stesso arco
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # senza aggiornare la posizione dei controlli
      
      # se il widget delle quote "angolo dal punto precedente" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue() == False:
         if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
            angle = qad_utils.getAngleBy2Pts(self.prevPoint, self.resPt, 0) # senza tolleranza
            if angle >= math.pi and angle < 2 * math.pi:
               angle = 2 * math.pi - angle
            self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # senza aggiornare la posizione dei controlli
         elif self.prevPart is not None and self.prevPart.whatIs() == "LINE": # spostamento di un punto di un segmento in modalità grip
            angle = qad_utils.getAngleBy2Pts(self.prevPart.getStartPt(), self.resPt, 0) # senza tolleranza
            if angle >= math.pi and angle < 2 * math.pi:
               angle = 2 * math.pi - angle
            self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # senza aggiornare la posizione dei controlli
            
      # se il widget delle quote nel modo grip "distanza rispetto la posizione precedente dello stesso punto nel verso dal punto precedente" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isLockedValue() == False:
         if self.prevPart is not None:
            gType = self.prevPart.whatIs()
            
            if gType == "LINE": # spostamento di un punto di un segmento in modalità grip
               dist = qad_utils.getDistance(self.prevPart.getEndPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # senza aggiornare la posizione dei controlli
            elif gType == "ARC": # spostamento di un punto di un arco in modalità grip
               # usato per lunghezza raggio nel punto iniziale della parte precedente se arco
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].showMsg(qad_utils.numToStringFmt(self.prevPart.radius), False, False, False) # senza aggiornare la posizione dei controlli
            
      # se il widget delle quote nel modo grip "angolo relativo all'angolo dal punto precedente" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isLockedValue() == False:
         if self.prevPart is not None and self.prevPart.whatIs() == "LINE": # spostamento di un punto di un segmento in modalità grip
            pt1 = self.prevPart.getStartPt()
            pt2 = self.prevPart.getEndPt()
            anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
            angleMouse = qad_utils.getAngleBy2Pts(pt1, self.resPt, 0) # senza tolleranza
            angle = qad_utils.normalizeAngle(angleMouse - anglePart)
            # se il mouse forma un angolo tra 180 e 360 allora l'angolo digitato va sottratto a 360 gradi 
            if angle >= math.pi and angle < (2 * math.pi):
               angle = (2 * math.pi) - angle
            self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # senza aggiornare la posizione dei controlli

      # se il widget delle quote nel modo grip "distanza dal punto successivo" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None:
            gType = self.nextPart.whatIs()
            if gType == "LINE": # spostamento di un punto di un segmento in modalità grip
               dist = qad_utils.getDistance(self.nextPart.getEndPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # senza aggiornare la posizione dei controlli
            elif gType == "ARC": # spostamento di un punto di un arco in modalità grip
               # usato per lunghezza raggio nel punto iniziale della parte successiva se arco
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # senza aggiornare la posizione dei controlli

      # se il widget delle quote nel modo grip "distanza rispetto la posizione precedente dello stesso punto nel verso dal punto successivo" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None:
            gType = self.nextPart.whatIs()

            if gType == "LINE": # spostamento di un punto di un segmento in modalità grip
               dist = qad_utils.getDistance(self.nextPart.getStartPt(), self.resPt)
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(dist), False, False, False) # senza aggiornare la posizione dei controlli
            elif gType == "ARC": # spostamento di un punto di un arco in modalità grip
               # usato per lunghezza raggio nel punto finale della parte successiva se arco
               self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].showMsg(qad_utils.numToStringFmt(self.nextPart.radius), False, False, False) # senza aggiornare la posizione dei controlli

      # se il widget delle quote "angolo dal punto successivo" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None and self.nextPart.whatIs() == "LINE": # spostamento di un punto di un segmento in modalità grip
            angle = qad_utils.getAngleBy2Pts(self.nextPart.getEndPt(), self.resPt, 0) # senza tolleranza
            if angle >= math.pi and angle < 2 * math.pi:
               angle = 2 * math.pi - angle            
            self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # senza aggiornare la posizione dei controlli
            
      # se il widget delle quote nel modo grip "distanza dal punto precedente" è visibile
      if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isLockedValue() == False:
         if self.nextPart is not None and self.nextPart.whatIs() == "LINE": # spostamento di un punto di un segmento in modalità grip
            pt1 = self.nextPart.getEndPt()
            pt2 = self.nextPart.getStartPt()
            anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
            angleMouse = qad_utils.getAngleBy2Pts(pt1, self.resPt, 0) # senza tolleranza
            angle = qad_utils.normalizeAngle(angleMouse - anglePart)
            # se il mouse forma un angolo tra 180 e 360 allora l'angolo digitato va sottratto a 360 gradi 
            if angle >= math.pi and angle < (2 * math.pi):
               angle = (2 * math.pi) - angle
            self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(angle)), False, False, False) # senza aggiornare la posizione dei controlli


      if self.edits[QadDynamicInputEditEnum.EDIT].isVisible() and \
         self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == False and \
         self.resValue is not None:
         if self.inputType & QadInputTypeEnum.ANGLE:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(qad_utils.toDegrees(self.resValue)), False, False, False) # senza aggiornare la posizione dei controlli
         elif self.inputType & QadInputTypeEnum.FLOAT:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(qad_utils.numToStringFmt(self.resValue), False, False, False) # senza aggiornare la posizione dei controlli
         elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
              self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG:
            self.edits[QadDynamicInputEditEnum.EDIT].showMsg(unicode(self.resValue), False, False, False) # senza aggiornare la posizione dei controlli
            
      if self.currentEdit is not None:
         self.edits[self.currentEdit].focusInEvent(None) # riporto il fuoco sul controllo corrente

      self.moveCtrls(mousePos)
      
      return

      
   # ============================================================================
   # moveCtrls
   # ============================================================================
   def moveCtrls(self, mousePos = None):
      # sposta tutti i widget visibili a seconda del contesto
      if mousePos is not None:         
         self.mousePos.setX(mousePos.x())
         self.mousePos.setY(mousePos.y())

      height = self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].height()
      offset = 5
      
      width = 0
      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         width += self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].width()

      x = self.mousePos.x() + height
      y = self.mousePos.y() + height

      # se si sta richiedendo un punto tramite una qualunque sua coordinata
      if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible() or \
         self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible() or \
         self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible():
         
         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
            if width > 0 : width += offset
            offsetX_editSymbolCoord = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].width()            
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
            if width > 0 : width += offset
            offsetX_editX = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_X].width()
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible():
            if width > 0 : width += offset
            offsetX_editY = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_Y].width()
         if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible():
            if width > 0 : width += offset
            offsetX_editZ = width
            width += self.edits[QadDynamicInputEditEnum.EDIT_Z].width()
            
         x, y = self.adjustEditPosition(x, y, width, height)
            
         if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].move(x + offsetX_editSymbolCoord, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_X].move(x + offsetX_editX, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_Y].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_Y].move(x + offsetX_editY, y)
         if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT_Z].move(x + offsetX_editZ, y)

      elif self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.BOOL or \
           self.inputType & QadInputTypeEnum.INT or self.inputType & QadInputTypeEnum.LONG or \
           self.inputType & QadInputTypeEnum.FLOAT:
         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible():
            if width > 0 : width += offset
            offsetX_edit = width
            width += self.edits[QadDynamicInputEditEnum.EDIT].width()
            
         x, y = self.adjustEditPosition(x, y, width, height)
         
         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible(): self.edits[QadDynamicInputEditEnum.EDIT].move(x + offsetX_edit, y)
         
      elif self.inputType & QadInputTypeEnum.ANGLE:
         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible():
            if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
               point = self.resPt # posizione
               start = QgsPointXY(self.prevPoint.x() + qad_utils.getDistance(self.prevPoint, point), self.prevPoint.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(start, self.prevPoint, point, 0, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT])
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # se non nullo disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT].setLinesMarker(lineMarkers)
                  del lineMarkers
            else:
               if width > 0 : width += offset
               offsetX_edit = width
               width += self.edits[QadDynamicInputEditEnum.EDIT].width()            
               x, y = self.adjustEditPosition(x, y, width, height)
               self.edits[QadDynamicInputEditEnum.EDIT].move(x + offsetX_edit, y)
         
      # se devo mostrare i widget delle quote
      elif self.isDimensionalWidgetVisib():
         if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
            x, y = self.adjustEditPosition(x, y, width, height)
         point = self.resPt # posizione

         if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
            prevPt = self.prevPoint
         elif self.prevPart is not None and self.prevPart.whatIs() == "LINE": # spostamento di un punto di un segmento in modalità grip
            prevPt = self.prevPart.getStartPt()
         else:
            prevPt = None
            
         if prevPt is not None:
            if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
               offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
               editPt, lineMarkers = self.getPosAndLineMarkerForLine(prevPt, point, \
                                                                     offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].move(editPt.x(), editPt.y())
               del editPt
               # disegno la linea di marker
               self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].setLinesMarker(lineMarkers)
               del lineMarkers
               
            if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible():
               start = QgsPointXY(prevPt.x() + qad_utils.getDistance(prevPt, point), prevPt.y())
               editPt, lineMarkers = self.getPosAndLineMarkerForArc(start, prevPt, point, 0, \
                                                                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT])
               if editPt is not None:
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
               if lineMarkers is not None: # se non nullo disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

         if self.prevPart is not None:
            gType = self.prevPart.whatIs()
            if gType == "LINE": # spostamento di un punto di un segmento in modalità grip
               prevCurrentPt = self.prevPart.getEndPt()
               angle = qad_utils.getAngleBy2Pts(prevPt, point, 0) # senza tolleranza
               pt = qad_utils.getPolarPointByPtAngle(prevPt, angle, self.prevPart.length())
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
                  offset = (height * 1) * self.canvas.mapSettings().mapUnitsPerPixel()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(pt, point, \
                                                                        offset, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
                  
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible():
                  editPt, lineMarkers = self.getPosAndLineMarkerForArc(prevCurrentPt, prevPt, pt, 0, \
                                                                       self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT], True) # LineMarker solo arco
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
            elif gType == "ARC": # spostamento di un punto di un arco in modalità grip
               center = self.prevPart.center
               
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible():
                  # usato per lunghezza raggio arco nel punto finale della parte precedente
                  # oppure lunghezza raggio nel punto medio se parte precedente e successiva coincidono
                  if self.nextPart is not None and self.nextPart == self.prevPart:
                     p2 = self.prevPart.getMiddlePt()
                  else:
                     p2 = self.prevPart.getEndPt()
                     
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
               
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible():
                  # usato per lunghezza raggio arco nel punto iniziale della parte precedente
                  p2 = self.prevPart.getStartPt()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].setLinesMarker(lineMarkers)
                  del lineMarkers

         if self.nextPart is not None:
            gType = self.nextPart.whatIs()
            if gType == "LINE": # spostamento di un punto di un segmento in modalità grip
               nextPt = self.nextPart.getEndPt()
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
                  offset = (height * 2) * self.canvas.mapSettings().mapUnitsPerPixel()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(nextPt, point, \
                                                                        offset, self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
                  
               if self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible():
                  start = QgsPointXY(nextPt.x() + qad_utils.getDistance(nextPt, point), nextPt.y())
                  editPt, lineMarkers = self.getPosAndLineMarkerForArc(start, nextPt, point, 0, \
                                                                       self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT])
                  if editPt is not None:
                     self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].move(editPt.x(), editPt.y())
                     del editPt
                  if lineMarkers is not None: # se non nullo disegno la linea di marker
                     self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].setLinesMarker(lineMarkers)
                     del lineMarkers
                  
               prevCurrentPt = self.nextPart.getStartPt()
               angle = qad_utils.getAngleBy2Pts(nextPt, point, 0) # senza tolleranza
               pt = qad_utils.getPolarPointByPtAngle(nextPt, angle, self.nextPart.length())           
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
                  offset = (height * 1) * self.canvas.mapSettings().mapUnitsPerPixel()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(pt, point, \
                                                                        offset, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
                  
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isVisible():
                  editPt, lineMarkers = self.getPosAndLineMarkerForArc(prevCurrentPt, nextPt, pt, 0, \
                                                                       self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT], True) # LineMarker solo arco
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
            elif gType == "ARC": # spostamento di un punto di un arco in modalità grip
               center = self.nextPart.center
               
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible():
                  # usato per lunghezza raggio arco nel punto iniziale della parte successiva
                  p2 = self.nextPart.getStartPt()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
               
               if self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible():
                  # usato per lunghezza raggio nel punto finale della parte successiva se arco
                  p2 = self.nextPart.getEndPt()
                  editPt, lineMarkers = self.getPosAndLineMarkerForLine(center, p2, \
                                                                        0, self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT])
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].move(editPt.x(), editPt.y())
                  del editPt
                  # disegno la linea di marker
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].setLinesMarker(lineMarkers)
                  del lineMarkers
               
      else:
         if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
            x, y = self.adjustEditPosition(x, y, width, height)
         
      if self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].isVisible():
         self.edits[QadDynamicInputEditEnum.PROMPT_EDIT].move(x, y)


   # ============================================================================
   # refreshResult
   # ============================================================================
   def refreshResult(self, mousePos = None):
      # calcola il risultato e restituisce True se l'operazione ha successo
      # a seconda del contesto può essere un punto -> self.resPt o un valore (numero, stringa, bool...) -> self.resValue
      # il risultato è anche impostato in formato stringa in self.resStr
      self.resValue = None
      self.resStr = ""
      
      # se il risultato può essere un punto
      if self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D:
         if mousePos is not None:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(mousePos) # posizione
         else:
            point = self.canvas.getCoordinateTransform().toMapCoordinates(self.canvas.mouseLastXY()) # posizione

         # se i widget delle coordinate sono visibili si sta cercando un punto
         if self.edits[QadDynamicInputEditEnum.EDIT_X].isVisible():
            # si sta cercando un punto attraverso le coordinate esplicite (relative al punto precedente o assolute)
            
            if self.prevPoint is None: # se non è settato nell'input dinamico lo cerco nel plugin
               if self.plugIn.lastPoint is None:
                  prevPt = QgsPointXY(0,0)
               else:
                  prevPt = self.plugIn.lastPoint 
            else:
               prevPt = self.prevPoint
            
            # se si tratta di coordinate relative
            relative = True if self.dynPiCoords == 0 else False
            # se si tratta di coordinate polari
            polar = True if self.dynPiFormat == 0 else False
            if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
               coordType = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
               if "@" in coordType: relative = True
               elif "#" in coordType: relative = False
               polar = True if "<" in coordType else False
            else: # se non è esplicito che sia relativo ma lo è per via di dynPiCoords
               prevPt = self.prevPoint # se non c'è il punto precedente impostato nell'input dinamico 
               if prevPt is None:
                  relative = False
                  polar = False
            
            if polar == False: # coordinate cartesiane
               # x
               if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue() == False:
                  self.resPt.setX(point.x())
               else:
                  value = self.edits[QadDynamicInputEditEnum.EDIT_X].checkValid() # ritorna il valore se valido
                  if value is None:
                     self.resPt.setX(point.x())
                  else:
                     if relative:
                        value = prevPt.x() + value
                     self.resPt.setX(value)
                     
               # y
               if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue() == False:
                  self.resPt.setY(point.y())
               else:
                  value = self.edits[QadDynamicInputEditEnum.EDIT_Y].checkValid() # ritorna il valore se valido
                  if value is None:
                     self.resPt.setY(point.y())
                  else:
                     if relative:
                        value = prevPt.y() + value
                     self.resPt.setY(value)
                  
               if self.edits[QadDynamicInputEditEnum.EDIT_Z].isVisible():
                  # z
                  if self.edits[QadDynamicInputEditEnum.EDIT_Z].isLockedValue() == False:
                     self.resPt.setZ(point.z())
                  else:
                     value = self.edits[QadDynamicInputEditEnum.EDIT_Z].checkValid() # ritorna il valore se valido
                     if value is None:
                        self.resPt.setZ(point.z())
                     else:
                        self.resPt.setZ(prevPt.z() + value if relative else value)
            elif prevPt is not None: # coordinate polari
               # nel caso di coordinate polari EDIT_X contiene la distanza dal punto precedente o da 0,0
               if self.edits[QadDynamicInputEditEnum.EDIT_X].isLockedValue():
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_X].checkValid() # ritorna il valore se valido
                  if dist is None:
                     if relative:
                        dist = qad_utils.getDistance(prevPt, point)
                     else:
                        dist = qad_utils.getDistance(QgsPointXY(0, 0), point)
               else:
                  if relative:
                     dist = qad_utils.getDistance(prevPt, point)
                  else:
                     dist = qad_utils.getDistance(QgsPointXY(0, 0), point)
               
               # nel caso di coordinate polari EDIT_Y contiene l'angolo
               if self.edits[QadDynamicInputEditEnum.EDIT_Y].isLockedValue():
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_Y].checkValid() # ritorna il valore se valido
                  if angle is None:
                     angle = qad_utils.getAngleBy2Pts(prevPt, point, 0) # senza tolleranza
               else:
                  angle = qad_utils.getAngleBy2Pts(prevPt, point, 0) # senza tolleranza
                  
               if relative:
                  pt = qad_utils.getPolarPointByPtAngle(prevPt, angle, dist)
               else:
                  pt = qad_utils.getPolarPointByPtAngle(QgsPointXY(0, 0), angle, dist)
                  
               self.resPt.setX(pt.x())
               self.resPt.setY(pt.y())
            
            self.resStr = self.resPt.toString()
            return True

         if self.isDimensionalWidgetVisib():
            if self.prevPoint is not None: # si tratta di inserimento di un nuovo punto a fine linea
               # si sta cercando un punto attraverso la distanza e l'angolo da punto precedente
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue() == False:
                  dist = qad_utils.getDistance(self.prevPoint, point)
               else:
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].checkValid() # ritorna il valore se valido
                  if dist is None: dist = qad_utils.getDistance(self.prevPoint, point)
                              
               if self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue() == False:
                  angle = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # senza tolleranza
               else:
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].checkValid() # ritorna il valore in radianti se valido               
                  if angle is None:
                     angle = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # senza tolleranza
                  else: 
                     angleMouse = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # senza tolleranza
                     # se il mouse forma un angolo tra 180 e 360 allora l'angolo digitato va sottratto a 360 gradi 
                     if angleMouse >= math.pi and angleMouse < 2 * math.pi:
                        angle = (2 * math.pi) - angle
      
               pt = qad_utils.getPolarPointByPtAngle(self.prevPoint, angle, dist)
               self.resPt.setX(pt.x())
               self.resPt.setY(pt.y())                                
               self.resStr = self.resPt.toString()
               return True
            else: # spostamento di un punto in modalità grip
               # se il widget delle quote "distanza dal punto precedente" è visibile
               if self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isVisible() and \
                  self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].isLockedValue() and \
                  self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_DIST_PREV_PT].checkValid() # ritorna il valore se valido
                  if dist is not None:
                     pt1 = self.prevPart.getStartPt()
                     pt2 = self.prevPart.getEndPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # se il widget delle quote nel modo grip "distanza dal punto successivo" è visibile
               elif self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_DIST_NEXT_PT].checkValid() # ritorna il valore se valido
                  if dist is not None:
                     pt1 = self.nextPart.getEndPt()
                     pt2 = self.nextPart.getStartPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True
                  
               # se il widget delle quote "angolo dal punto precedente" è visibile
               elif self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].isLockedValue() and \
                    self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_ANG_PREV_PT].checkValid() # ritorna il valore in radianti se valido               
                  if angle is not None:
                     pt1 = self.prevPart.getStartPt()
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # senza tolleranza
                     # se il mouse forma un angolo tra 180 e 360 allora l'angolo digitato va sottratto a 360 gradi 
                     if angleMouse >= math.pi and angleMouse < 2 * math.pi:
                        angle = (2 * math.pi) - angle                     
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, self.prevPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())                                
                     self.resStr = self.resPt.toString()
                     return True
               
               # se il widget delle quote "angolo dal punto successivo" è visibile
               elif self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_ANG_NEXT_PT].checkValid() # ritorna il valore in radianti se valido               
                  if angle is not None:
                     pt1 = self.nextPart.getEndPt()
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # senza tolleranza
                     # se il mouse forma un angolo tra 180 e 360 allora l'angolo digitato va sottratto a 360 gradi 
                     if angleMouse >= math.pi and angleMouse < 2 * math.pi:
                        angle = (2 * math.pi) - angle                     
                     pt = qad_utils.getPolarPointByPtAngle(pt1, angle, self.nextPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())                                
                     self.resStr = self.resPt.toString()
                     return True

               # se il widget delle quote nel modo grip "distanza rispetto la posizione precedente dello stesso punto nel verso dal punto precedente" è visibile
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].isLockedValue() and \
                    self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_PREV_PT].checkValid() # ritorna il valore se valido
                  if dist is not None:
                     pt1 = self.prevPart.getStartPt()
                     pt2 = self.prevPart.getEndPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
                     pt = qad_utils.getPolarPointByPtAngle(pt2, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # se il widget delle quote nel modo grip "distanza rispetto la posizione precedente dello stesso punto nel verso dal punto successivo" è visibile
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  dist = self.edits[QadDynamicInputEditEnum.EDIT_REL_DIST_NEXT_PT].checkValid() # ritorna il valore se valido
                  if dist is not None:
                     pt1 = self.nextPart.getEndPt()
                     pt2 = self.nextPart.getStartPt()
                     angle = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
                     pt = qad_utils.getPolarPointByPtAngle(pt2, angle, dist)
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())
                     self.resStr = self.resPt.toString()
                     return True

               # se il widget delle quote nel modo grip "angolo relativo all'angolo dal punto precedente" è visibile
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isVisible() and \
                    self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].isLockedValue() and \
                    self.prevPart is not None and self.prevPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_PREV_PT].checkValid() # ritorna il valore in radianti se valido               
                  if angle is not None:
                     pt1 = self.prevPart.getStartPt()
                     pt2 = self.prevPart.getEndPt()
                     anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # senza tolleranza
                     diffAngle = qad_utils.normalizeAngle(angleMouse - anglePart)
                     # se il mouse forma un angolo tra 180 e 360 allora l'angolo digitato va sottratto a 360 gradi 
                     if diffAngle >= math.pi and diffAngle < (2 * math.pi):
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart-angle, self.prevPart.length())
                     else:
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart+angle, self.prevPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())                                
                     self.resStr = self.resPt.toString()
                     return True
               
               # se il widget delle quote nel modo grip "distanza dal punto precedente" è visibile
               elif self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isVisible() and \
                  self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].isLockedValue() and \
                    self.nextPart is not None and self.nextPart.whatIs() == "LINE":
                  angle = self.edits[QadDynamicInputEditEnum.EDIT_REL_ANG_NEXT_PT].checkValid() # ritorna il valore in radianti se valido               
                  if angle is not None:
                     pt1 = self.nextPart.getEndPt()
                     pt2 = self.nextPart.getStartPt()
                     anglePart = qad_utils.getAngleBy2Pts(pt1, pt2, 0) # senza tolleranza
                     angleMouse = qad_utils.getAngleBy2Pts(pt1, point, 0) # senza tolleranza
                     diffAngle = qad_utils.normalizeAngle(angleMouse - anglePart)
                     # se il mouse forma un angolo tra 180 e 360 allora l'angolo digitato va sottratto a 360 gradi 
                     if diffAngle >= math.pi and diffAngle < (2 * math.pi):
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart-angle, self.nextPart.length())
                     else:
                        pt = qad_utils.getPolarPointByPtAngle(pt1, anglePart+angle, self.nextPart.length())
                     self.resPt.setX(pt.x())
                     self.resPt.setY(pt.y())                                
                     self.resStr = self.resPt.toString()
                     return True

               else: # se nessun valore era non bloccato
                  self.resPt.setX(point.x())
                  self.resPt.setY(point.y())
                  self.resStr = self.resPt.toString()
                  return True
               
         # si sta cercando un angolo attraverso il punto precedente
         if self.inputType & QadInputTypeEnum.ANGLE and self.prevPoint is not None:
            if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == False:
               self.resPt.setX(point.x())
               self.resPt.setY(point.y())
               self.resStr = self.resPt.toString()
               self.resValue = qad_utils.getAngleBy2Pts(self.prevPoint, self.resPt, 0) # senza tolleranza
               return True
            else:
               dist = qad_utils.getDistance(self.prevPoint, point)
               angle = self.edits[QadDynamicInputEditEnum.EDIT].checkValid() # ritorna il valore in radianti se valido
               if angle is not None:
                  pt = qad_utils.getPolarPointByPtAngle(self.prevPoint, angle, dist)
                  self.resPt.setX(pt.x())
                  self.resPt.setY(pt.y())
                  self.resStr = self.resPt.toString()
                  return True

         # si sta cercando un valore float attraverso il punto precedente
         if self.inputType & QadInputTypeEnum.FLOAT and self.prevPoint is not None:
            if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == False:
               self.resPt.setX(point.x())
               self.resPt.setY(point.y())
               self.resStr = self.resPt.toString()
               self.resValue = qad_utils.getDistance(self.prevPoint, self.resPt)
               return True
            else:
               angle = qad_utils.getAngleBy2Pts(self.prevPoint, point, 0) # senza tolleranza
               dist = self.edits[QadDynamicInputEditEnum.EDIT].checkValid() # ritorna il valore se valido
               if dist is not None:
                  pt = qad_utils.getPolarPointByPtAngle(self.prevPoint, angle, dist)
                  self.resPt.setX(pt.x())
                  self.resPt.setY(pt.y())
                  self.resStr = self.resPt.toString()
                  return True
               
            return True
               

      if self.inputType & QadInputTypeEnum.STRING or self.inputType & QadInputTypeEnum.INT or \
         self.inputType & QadInputTypeEnum.LONG or self.inputType & QadInputTypeEnum.FLOAT or \
         self.inputType & QadInputTypeEnum.BOOL or self.inputType & QadInputTypeEnum.ANGLE:
         if self.edits[QadDynamicInputEditEnum.EDIT].isVisible():
            if self.edits[QadDynamicInputEditEnum.EDIT].isLockedValue() == True:
               self.resValue = self.edits[QadDynamicInputEditEnum.EDIT].checkValid() # ritorna il valore se valido
               if self.resValue is None:
                  self.resStr = ""
                  return False
               else:
                  if self.inputType & QadInputTypeEnum.ANGLE:
                     self.resStr = unicode(qad_utils.toDegrees(self.resValue))
                  else:
                     self.resStr = unicode(self.resValue)
                  return True
            elif self.inputType & QadInputTypeEnum.ANGLE and self.prevPoint is not None:
               self.resValue = qad_utils.getAngleBy2Pts(self.prevPoint, self.resPt, 0) # senza tolleranza
               self.resStr = unicode(qad_utils.toDegrees(self.resValue))
               return True
         else:
            self.resValue = None
            self.resStr = ""

      return False
   

   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      if self.currentEdit is None:
         return
      if e.key() == Qt.Key_Comma: # ","
         # se il risultato può essere un punto
         if self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT2D: 
            self.forcedCoordWidgetVisib = True # editaz forzata delle coordinate
            if self.currentEdit != QadDynamicInputEditEnum.EDIT_X and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Y and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Z:
               coord = self.edits[self.currentEdit].toPlainText()
               self.currentEdit = QadDynamicInputEditEnum.EDIT_X
               self.edits[QadDynamicInputEditEnum.EDIT_X].setLockedValue(True) # se è possibile modifico lo stato di lock
               self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(coord)
            self.show(True)
            self.setNextCurrentEdit()
         else:
            QTextEdit.keyPressEvent(self.edits[self.currentEdit], e)
            #self.edits[self.currentEdit].keyPressEvent(e)
            
      elif e.text() == "@" or e.text() == "#" or e.text() == "<":
         # se il risultato può essere un punto
         if self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT2D: 
            self.forcedCoordWidgetVisib = True # editaz forzata delle coordinate
            value = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
            alreadyPolar = True if value.find("<") >= 0 else False
            if e.text() == "@" or e.text() == "#":
               value = e.text()
               if alreadyPolar: value = value + "<"
            else: # "<"
               if value.find("@") >= 0: value = "@"
               elif value.find("#") >= 0: value = "#"
               if alreadyPolar == False: value = value + "<"
               
            self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].showMsg(value)
            if self.currentEdit != QadDynamicInputEditEnum.EDIT_X and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Y and \
               self.currentEdit != QadDynamicInputEditEnum.EDIT_Z:
               coord = self.edits[self.currentEdit].toPlainText()
               self.currentEdit = QadDynamicInputEditEnum.EDIT_X
               self.edits[QadDynamicInputEditEnum.EDIT_X].showMsg(coord)
            self.show(True)
               
      elif e.key() == Qt.Key_Return or e.key == Qt.Key_Enter:
         # se non c'è alcun widget con valore bloccato
         if self.anyLockedValueEdit() == False:
            msg = ""
            # se era stato premuto @ o #
            if self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].isVisible():
               coordType = self.edits[QadDynamicInputEditEnum.EDIT_SYMBOL_COORD_TYPE].toPlainText()
               if "@" in coordType: msg = "@"
               elif "#" in coordType: msg = "#"
            self.showEvaluateMsg(msg)
         else:
            if self.currentEdit is not None:
               currentWidget = self.edits[self.currentEdit]
               # se il contenuto del widget è stato modificato dall'utente
               if currentWidget.isLockedValue() == True:
                  value = currentWidget.toPlainText()
                  # verifico se si tratta di una opzione del comando attivo
                  keyWord = self.evaluateKeyWords(value)
                  if keyWord is not None:
                     self.showEvaluateMsg(keyWord)
                  # altrimenti se ci si attendeva un punto e si tratta di un'opzione di osnap
                  elif (self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D) and \
                        str2snapTypeEnum(value) != -1:
                     currentWidget.showMsg("")
                     currentWidget.setLockedValue(False)
                     self.showEvaluateMsg(value)
                  # altrimenti se ci si attendeva un punto e si tratta dell'opzione M2P "punto medio tra 2 punti"
                  elif (self.inputType & QadInputTypeEnum.POINT2D or self.inputType & QadInputTypeEnum.POINT3D) and \
                        (value.upper() == QadMsg.translate("Snap", "M2P") or value.upper() == "_M2P"):
                     currentWidget.showMsg("")
                     currentWidget.setLockedValue(False)
                     self.showEvaluateMsg(value)                     
                  # altrimenti verifico la validità del valore
                  else:
                     if currentWidget.checkValid() is not None:
                        msg = self.resStr if self.refreshResult() == True else "" # ricalcolo il risultato e lo uso in formato stringa
                        self.showEvaluateMsg(msg)
            else:
               msg = self.resStr if self.refreshResult() == True else "" # ricalcolo il risultato e lo uso in formato stringa
               self.showEvaluateMsg(msg)
      else:
         self.edits[self.currentEdit].keyPressEvent(e)


   # ============================================================================
   # evaluateKeyWords
   # ============================================================================
   def evaluateKeyWords(self, cmd):
      # The required portion of the keyword is specified in uppercase characters, 
      # and the remainder of the keyword is specified in lowercase characters.
      # The uppercase abbreviation can be anywhere in the keyword
      if cmd[0] == "_": # versione inglese
         keyWord, Msg = qad_utils.evaluateCmdKeyWords(cmd[1:], self.englishKeyWords)
         if keyWord is None: return None
         # cerco la corrispondente parola chiave in lingua locale
         i = 0
         for k in self.englishKeyWords:
            if k == keyWord:
               return self.keyWords[i]
            i = i + 1
         return None
      else:
         keyWord, Msg = qad_utils.evaluateCmdKeyWords(cmd, self.keyWords)
         return keyWord
