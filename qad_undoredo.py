# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per undo e redo
 
                              -------------------
        begin                : 2014-04-24
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
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *


# ===============================================================================
# QadUndoRecordTypeEnum class.
# ===============================================================================
class QadUndoRecordTypeEnum():
   NONE     = 0     # nessuno
   COMMAND  = 1     # singolo comando
   BEGIN    = 2     # inizio di un gruppo di comandi
   END      = 3     # fine di un gruppo di comandi
   BOOKMARK = 4     # flag di segnalibro, significa che si tratta di un segno a cui
                     # si può ritornare


# ===============================================================================
# QadUndoRecord classe x gestire un registrazione di UNDO
# ===============================================================================
class QadUndoRecord():


   def __init__(self):
      self.text = "" # descrizione operazione
      self.undoType = QadUndoRecordTypeEnum.NONE # tipo di undo (vedi QadUndoRecordTypeEnum)
      self.layerList = None # lista di layer coinvolti nel comando di editazione

      
   def setUndoType(self, text = "", undoType = QadUndoRecordTypeEnum.NONE):
      # si sta impostando una tipologia di marcatore di undo
      self.text = text
      self.layerList = None # lista di layer coinvolti nel comando di editazione
      self.undoType = undoType


   def layerAt(self, layerId):
      # ritorna la posizione nella lista 0-based), -1 se non trovato
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for j in range(0, len(self.layerList), 1):
            if self.layerList[j].id() == layerId:
               return j
      return -1


   def clearByLayer(self, layerId):
      # elimino dalla lista il layer <layerId>
      pos = self.layerAt(layerId)
      if pos >= 0:
         del self.layerList[pos]


   def beginEditCommand(self, text, layerList):
      # si sta iniziando un comando che coinvolge una lista di layer
      self.text = text # descrizione operazione     
      self.undoType = QadUndoRecordTypeEnum.COMMAND
      # <parameter> contiene la lista dei layer coinvolti nel comando di editazione
      self.layerList = []
      for layer in layerList: # copio la lista
         if self.layerAt(layer.id()) == -1: # non ammetto duplicazioni di layer
            layer.beginEditCommand(text)
            self.layerList.append(layer)
               
               
   def destroyEditCommand(self):
      # si sta distruggendo un comando che coinvolge una lista di layer
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.destroyEditCommand() # Destroy active command and reverts all changes in it
         return True
      else:
         return False


   def endEditCommand(self, canvas):
      # si sta concludendo un comando che coinvolge una lista di layer
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.endEditCommand()
            layer.triggerRepaint()
         canvas.refresh()
  
      
   def undoEditCommand(self, canvas = None):
      # si sta facendo un UNDO di un comando che coinvolge una lista di layer
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.undoStack().undo()
         if canvas is not None:
            canvas.refresh()
 
      
   def redoEditCommand(self, canvas = None):
      # si sta facendo un REDO di un comando che coinvolge una lista di layer
      if self.layerList is not None and self.undoType == QadUndoRecordTypeEnum.COMMAND:
         for layer in self.layerList:
            layer.undoStack().redo()
         if canvas is not None:
            canvas.refresh()

     
   def addLayer(self, layer):
      # si sta aggiungendo un layer al comando corrente
      if self.undoType != QadUndoRecordTypeEnum.COMMAND: # si deve trattare di un comando
         return False
      if self.layerAt(layer.id()) == -1: # non ammetto duplicazioni di layer
         layer.beginEditCommand(self.text)
         self.layerList.append(layer)


# ===============================================================================
# QadUndoStack classe x gestire lo stack delle operazioni
# ===============================================================================
class QadUndoStack():

    
   def __init__(self):
      self.UndoRecordList = [] # lista di record di undo
      self.index = -1
 
   
   def clear(self):
      del self.UndoRecordList[:] # svuoto la lista
      self.index = -1


   def clearByLayer(self, layerId):
      # elimino il layer <layerId> dalla lista dei record di undo
      for i in range(len(self.UndoRecordList) - 1, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            UndoRecord.clearByLayer(layerId)      
            if len(UndoRecord.layerList) == 0:
               # elimino la lista dei layer (vuota) coinvolta nel comando di editazione
               del self.UndoRecordList[i]
               if self.index >= i: # aggiorno il puntatore
                  self.index = self.index - 1


   def insertBeginGroup(self, text):
      UndoRecord = QadUndoRecord()
      UndoRecord.setUndoType(text, QadUndoRecordTypeEnum.BEGIN)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1
      return True


   def getOpenGroupPos(self, endGroupPos):
      # dalla posizione di fine gruppo <endgroupPos> cerca la posizione di inizio gruppo
      # -1 se non trovato
      openFlag = 0
      for i in range(endGroupPos, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN:
            openFlag = openFlag + 1
            if openFlag >= 0:
               return i
         elif UndoRecord.undoType == QadUndoRecordTypeEnum.END:
            openFlag = openFlag - 1
      return -1


   def getEndGroupPos(self, beginGroupPos):
      # dalla posizione di inizio gruppo <endgroupPos> cerca la posizione di inizio gruppo
      # -1 se non trovato
      closeFlag = 0
      for i in range(beginGroupPos, len(self.UndoRecordList), 1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN:
            closeFlag = closeFlag - 1
         elif UndoRecord.undoType == QadUndoRecordTypeEnum.END:
            closeFlag = closeFlag + 1
            if closeFlag >= 0:
               return i
      return -1
   

   def insertEndGroup(self):
      # non si può inserire un end gruppo se non si é rimasto aperto un gruppo
      openGroupPos = self.getOpenGroupPos(len(self.UndoRecordList) - 1)
      if openGroupPos == -1:
         return False

      UndoRecord = QadUndoRecord()
      UndoRecord.setUndoType(self.UndoRecordList[openGroupPos].text, QadUndoRecordTypeEnum.END)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1
      return True

      
   def beginEditCommand(self, text, layerList):
      tot = len(self.UndoRecordList)
      if tot > 0 and self.index < tot - 1:
         del self.UndoRecordList[self.index + 1 :] # cancello fino alla fine
         
      UndoRecord = QadUndoRecord()
      UndoRecord.beginEditCommand(text, layerList)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1

      
   def destroyEditCommand(self):
      if len(self.UndoRecordList) > 0:
         UndoRecord = self.UndoRecordList[-1]
         if UndoRecord.destroyEditCommand():
            del self.UndoRecordList[-1]
            self.index = self.index - 1


   def endEditCommand(self, canvas):
      if len(self.UndoRecordList) > 0:
         UndoRecord = self.UndoRecordList[-1]
         UndoRecord.endEditCommand(canvas)


   def moveOnFirstUndoRecord(self):
      # sposta il cursore dalla posizione attuale fino l'inizio
      # e si ferma quando trova un record di tipo END o COMMAND
      while self.index >= 0:
         UndoRecord = self.UndoRecordList[self.index]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.END or \
            UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
         self.index = self.index - 1
      return False 
         
   def undoEditCommand(self, canvas = None, nTimes = 1):
      for i in range(0, nTimes, 1):
         # cerco il primo record in cui ha senso fare UNDO
         if self.moveOnFirstUndoRecord() == False:
            break
         UndoRecord = self.UndoRecordList[self.index]
         # se incontro un end-group devo andare fino al begin-group
         if UndoRecord.undoType == QadUndoRecordTypeEnum.END:
            openGroupPos = self.getOpenGroupPos(self.index)           
            while self.index >= openGroupPos:
               UndoRecord.undoEditCommand(None) # senza fare refresh
               self.index = self.index - 1
               if self.moveOnFirstUndoRecord() == False:
                  break
               UndoRecord = self.UndoRecordList[self.index]
         else:
            UndoRecord.undoEditCommand(None)
            self.index = self.index - 1
      
      if canvas is not None:   
         canvas.refresh()


   def moveOnFirstRedoRecord(self):
      # sposta il cursore dalla posizione attuale fino alla fine
      # e si ferma quando trova un record di tipo BEGIN o COMMAND
      tot = len(self.UndoRecordList) - 1 
      while self.index < tot:
         self.index = self.index + 1                  
         UndoRecord = self.UndoRecordList[self.index]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN or \
            UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
      return False     
      
   def redoEditCommand(self, canvas = None, nTimes = 1):
      for i in range(0, nTimes, 1):         
         # cerco il primo record in cui ha senso fare REDO
         if self.moveOnFirstRedoRecord() == False:
            break
         UndoRecord = self.UndoRecordList[self.index]
         # se incontro un begin-group devo andare fino al end-group
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BEGIN:
            endGroupPos = self.getEndGroupPos(self.index)           
            while self.index <= endGroupPos:
               UndoRecord.redoEditCommand(None) # senza refresh
               if self.moveOnFirstRedoRecord() == False:
                  break
               UndoRecord = self.UndoRecordList[self.index]
         else:            
            UndoRecord.redoEditCommand(None)

      if canvas is not None:   
         canvas.refresh()

     
   def addLayerToLastEditCommand(self, text, layer):
      if len(self.UndoRecordList) > 0:     
         self.UndoRecordList[-1].addLayer(layer)


   def isUndoAble(self):
      # cerca un record di tipo COMMAND dalla posizione attuale fino l'inizio
      i = self.index
      while i >= 0:
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
         i = i - 1
      return False


   def isRedoAble(self):
      # cerca un record di tipo COMMAND dalla posizione attuale fino alla fine
      i = self.index + 1
      tot = len(self.UndoRecordList)
      while i < tot:
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.COMMAND:
            return True
         i = i + 1
      return False

   # ===============================================================================
   # BOOKMARK - INIZIO
   # ===============================================================================
   
   def undoUntilBookmark(self, canvas):
      if self.index == -1:
         return
      for i in range(self.index, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BOOKMARK:
            break
         
         UndoRecord.undoEditCommand(None) # senza refresh         
      self.index = i - 1        
      
      canvas.refresh()


   def redoUntilBookmark(self, canvas):
      for i in range(self.index + 1, len(self.UndoRecordList), 1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BOOKMARK:
            break
         UndoRecord.redoEditCommand(None) # senza refresh         
      self.index = i         
      
      canvas.refresh()


   def getPrevBookmarkPos(self, pos):
      # dalla posizione <pos> cerca la posizione di bookmark precedente
      # -1 se non trovato
      for i in range(pos - 1, -1, -1):
         UndoRecord = self.UndoRecordList[i]
         if UndoRecord.undoType == QadUndoRecordTypeEnum.BOOKMARK:
            return i
      return -1
 
      
   def insertBookmark(self, text):
      # non si può inserire un bookmark all'interno di un gruppo begin-end
      if self.getOpenGroupPos(self.index) >= 0:
         return False  
      
      tot = len(self.UndoRecordList)
      if tot > 0 and self.index < tot - 1:
         del self.UndoRecordList[self.index + 1 :] # cancello fino alla fine
      
      UndoRecord = QadUndoRecord()
      UndoRecord.setUndoType(text, QadUndoRecordTypeEnum.BOOKMARK)
      self.UndoRecordList.append(UndoRecord)
      self.index = len(self.UndoRecordList) - 1
      return True

   # ===============================================================================
   # BOOKMARK - FINE
   # ===============================================================================