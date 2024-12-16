# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 map tool per lo stato di quiete
 
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


from qgis.core import QgsMapLayer, QgsPointXY
from qgis.gui import QgsMapTool
from qgis.PyQt.QtCore import Qt, QTimer, QPoint, QEvent
from qgis.PyQt.QtGui import QCursor, QKeyEvent
from qgis.PyQt.QtWidgets import QAction, QMenu

import datetime


from . import qad_utils
from .qad_variables import QadVariables
from .qad_rubberband import QadCursorRubberBand, QadCursorTypeEnum
from .qad_getpoint import QadGetPointDrawModeEnum
from .qad_entity import QadEntitySet, QadEntity
from .qad_grip import QadEntitySetGripPoints, QadGripStatusEnum
from .qad_dynamicinput import QadDynamicCmdInput, QadDynamicInputContextEnum

from .cmd.qad_generic_cmd import QadCommandClass
from .cmd.qad_ssget_cmd import QadSSGetClass
from .cmd.qad_arc_cmd import QadGRIPCHANGEARCRADIUSCommandClass
from .cmd.qad_generic_cmd import QadCommandClass
from .cmd.qad_lengthen_cmd import QadGRIPLENGTHENCommandClass
from .cmd.qad_mirror_cmd import QadGRIPMIRRORCommandClass
from .cmd.qad_move_cmd import QadGRIPMOVECommandClass
from .cmd.qad_pedit_cmd import QadGRIPINSERTREMOVEVERTEXCommandClass, QadGRIPARCLINECONVERTCommandClass
from .cmd.qad_rotate_cmd import QadGRIPROTATECommandClass
from .cmd.qad_scale_cmd import QadGRIPSCALECommandClass
from .cmd.qad_ssget_cmd import QadSSGetClass
from .cmd.qad_stretch_cmd import QadGRIPSTRETCHCommandClass
from .qad_dim import QadDimStyles
from .qad_msg import QadMsg


# Main Map Tool class.
class QadMapTool(QgsMapTool):
      
   def __init__(self, plugIn):        
      QgsMapTool.__init__(self, plugIn.iface.mapCanvas())
      self.plugIn = plugIn
      self.iface = self.plugIn.iface
      self.canvas = self.plugIn.iface.mapCanvas()      
      self.cursor = QCursor(Qt.BlankCursor)
      self.__csrRubberBand = QadCursorRubberBand(self.canvas, QadCursorTypeEnum.BOX | QadCursorTypeEnum.CROSS)
      self.entitySet = QadEntitySet()
      self.entitySetGripPoints = QadEntitySetGripPoints(plugIn)
   
      self.gripPopupMenu = None
      self.timerForGripMenu = QTimer()
      self.timerForGripMenu.setSingleShot(True)
      
      self.startDateTimeForRightClick = 0
      
      # input dinamico
      self.dynamicCmdInput = QadDynamicCmdInput(plugIn)
      

   def __del__(self):
      self.removeItems()


   def removeItems(self):      
      if self.__csrRubberBand is not None:
         self.__csrRubberBand.removeItems() # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
         del self.__csrRubberBand
         __csrRubberBand = None
      self.entitySet.clear()
      self.entitySetGripPoints.removeItems()
      
      if self.dynamicCmdInput is not None:
         self.dynamicCmdInput.removeItems()
         del self.dynamicCmdInput
         self.dynamicCmdInput = None


   # ============================================================================
   # getDynamicInput
   # ============================================================================
   def getDynamicInput(self):
      return self.dynamicCmdInput


   # ============================================================================
   # UpdatedVariablesEvent
   # ============================================================================
   def UpdatedVariablesEvent(self):
      # aggiorna in base alle nuove impostazioni delle variabili
      self.removeItems() 
      self.__csrRubberBand = QadCursorRubberBand(self.canvas, QadCursorTypeEnum.BOX | QadCursorTypeEnum.CROSS)
      if self.dynamicCmdInput is not None:
         del self.dynamicCmdInput
      self.dynamicCmdInput = QadDynamicCmdInput(self.plugIn)


   # ============================================================================
   # clearEntitySet
   # ============================================================================
   def clearEntitySet(self):
      self.entitySet.deselectOnLayer()
      self.entitySet.clear()


   # ============================================================================
   # clearEntityGripPoints
   # ============================================================================
   def clearEntityGripPoints(self):
      self.entitySetGripPoints.removeItems() # svuoto la lista


   # ============================================================================
   # refreshEntityGripPoints
   # ============================================================================
   def refreshEntityGripPoints(self, entitySet = None):
      if entitySet is None:
         entitySet = self.entitySet
      
      gripObjLimit = QadVariables.get(QadMsg.translate("Environment variables", "GRIPOBJLIMIT"))
      if gripObjLimit != 0: #  When set to 0, grips are always displayed.
         if entitySet.count() > gripObjLimit:
            # Suppresses the display of grips when the selection set includes more than the specified number of objects
            self.clearEntityGripPoints()
            return
      
      # cancello i grip delle entità che non sono in entitySet o che non sono in layer vettoriali modificabili
      i = self.entitySetGripPoints.count() - 1
      while i >= 0:
         entityGripPoint = self.entitySetGripPoints.entityGripPoints[i]
         if entitySet.containsEntity(entityGripPoint.entity) == False or \
            entityGripPoint.entity.layer.type() != QgsMapLayer.VectorLayer or entityGripPoint.entity.layer.isEditable() == False:
            self.entitySetGripPoints.entityGripPoints[i].removeItems() # lo stacco dal canvas
            del self.entitySetGripPoints.entityGripPoints[i]
         i = i - 1
      
      entity = QadEntity()
      for layerEntitySet in entitySet.layerEntitySetList:
         # considero solo i layer vettoriali che sono modificabili
         layer = layerEntitySet.layer
         if layer.type() == QgsMapLayer.VectorLayer and layer.isEditable():
            for featureId in layerEntitySet.featureIds:
               entity.set(layer, featureId)
               self.entitySetGripPoints.addEntity(entity, QadVariables.get(QadMsg.translate("Environment variables", "GRIPS")))
      

   # ============================================================================
   # INIZIO - eventi per il mouse
   # ============================================================================

   
   # ============================================================================
   # canvasPressEvent
   # ============================================================================
   def canvasPressEvent(self, event):
      if event.button() == Qt.RightButton:
         self.startDateTimeForRightClick = datetime.datetime.now()
      elif event.button() == Qt.LeftButton:
         # verifico se tasto shift premuto
         shiftKey = True if event.modifiers() & Qt.ShiftModifier else False
         # posizione corrente del mouse
         point = self.toMapCoordinates(event.pos())
         # leggo il punto grip che si interseca alla posizione del mouse
         entityGripPoints, entityGripPoint = self.entitySetGripPoints.isIntersecting(point)
         if entityGripPoint is not None:
            if shiftKey == False: # lancio il comando
               selectedEntityGripPoints = self.entitySetGripPoints.getSelectedEntityGripPoints()
               # se non ci sono già grip selezionati
               if len(selectedEntityGripPoints) == 0:
                  # seleziono il corrente
                  if self.entitySetGripPoints.selectIntersectingGripPoints(point) > 0:
                     selectedEntityGripPoints = self.entitySetGripPoints.getSelectedEntityGripPoints()

               # lancio il comando
               self.plugIn.runCommand("QadVirtualGripCommandsClass", [QadVirtualGripCommandsEnum.STRECTH, \
                                      self.entitySetGripPoints, entityGripPoint.getPoint()])
            else: # shift premuto
               # inverto lo stato ai grip che intersecano il punto 
               self.entitySetGripPoints.toggleSelectIntersectingGripPoints(point)
         else:
            result = qad_utils.getEntSel(event.pos(), self, \
                                         QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")))
            if result is not None:
               feature = result[0]
               layer = result[1]
               tmpEntity = QadEntity()
               tmpEntity.set(layer, feature.id())
               SSGetClass = QadSSGetClass(self.plugIn)
               SSGetClass.entitySet.set(self.entitySet)
               SSGetClass.elaborateEntity(tmpEntity, shiftKey)
               self.plugIn.showMsg("\n", True) # ripete il prompt
               self.entitySet.set(SSGetClass.entitySet)
               del SSGetClass # che deseleziona gli oggetti
               self.entitySet.selectOnLayer(False)
               self.refreshEntityGripPoints(self.entitySet)
            else:
               self.plugIn.runCommand("QadVirtualSelCommandClass", point)
               

   # ============================================================================
   # canvasDoubleClickEvent
   # ============================================================================
   def canvasDoubleClickEvent(self,event):
      pass


   # ============================================================================
   # canvasMoveEvent
   # ============================================================================
   def canvasMoveEvent(self, event):
      self.timerForGripMenu.stop()
      point = self.toMapCoordinates(event.pos())
      self.__csrRubberBand.moveEvent(point)
      
      if self.dynamicCmdInput.prevPart is not None or self.dynamicCmdInput.nextPart is not None:
         changedPart = True
      else:
         changedPart = False
      self.dynamicCmdInput.setPrevPart(None)
      self.dynamicCmdInput.setNextPart(None)

      # hover grip points
      if self.entitySetGripPoints.hoverIntersectingGripPoints(point) == 1:
         for entityGripPoint in self.entitySetGripPoints.entityGripPoints:
            for gripPoint in entityGripPoint.gripPoints:
               if gripPoint.isIntersecting(point) and gripPoint.getStatus() == QadGripStatusEnum.HOVER:
                  self.dynamicCmdInput.setPrevNextPart(entityGripPoint.entity, gripPoint)
                  self.dynamicCmdInput.show(True, self.canvas.mouseLastXY())

                  # Specifica i metodi di accesso per le opzioni dei grip multifunzionali.
                  # se > 1 devono essere mostrati i menu dinamici 
                  if QadVariables.get(QadMsg.translate("Environment variables", "GRIPMULTIFUNCTIONAL")) > 1:
                     pos = QPoint(event.pos().x(), event.pos().y())
                     shot = lambda: self.displayPopupMenuOnGrip(pos, entityGripPoint.entity, gripPoint)
                     
                     del self.timerForGripMenu
                     self.timerForGripMenu = QTimer()
                     self.timerForGripMenu.setSingleShot(True)
                     self.timerForGripMenu.timeout.connect(shot)
                     self.timerForGripMenu.start(1000) # 1 sec tempo per il grip
                     return
      else:
         if changedPart == True:
            self.dynamicCmdInput.show(True, self.canvas.mouseLastXY())
         else:
            self.dynamicCmdInput.mouseMoveEvent(event.pos())
               

   # ============================================================================
   # canvasReleaseEvent
   # ============================================================================
   def canvasReleaseEvent(self, event):
      if event.button() == Qt.RightButton:
         shortCutMenu = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENU"))
         if shortCutMenu == 0:
            # equivale a premere INVIO
            return self.plugIn.showEvaluateMsg(None)
         else:
            if self.entitySet.count() == 0: # nessun oggetto selezionato (modalità Default)
               # 16 = Enables the display of a shortcut menu when the right button on the pointing device is held down long enough
               if shortCutMenu & 16:
                  now = datetime.datetime.now()
                  value = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION"))
                  shortCutMenuDuration = datetime.timedelta(0, 0, 0, value)
                  # se supera il numero di millisecondi impostato da SHORTCUTMENUDURATION
                  if now - self.startDateTimeForRightClick > shortCutMenuDuration:
                     return self.displayPopupMenuOnQuiescentState(event.pos())
                  else:
                     # se click veloce equivale a premere INVIO
                     return self.plugIn.showEvaluateMsg(None)
               else:
                  # 1 = Enables Default mode shortcut menus
                  if shortCutMenu & 1:
                     return self.displayPopupMenuOnQuiescentState(event.pos())
                  else:
                     # equivale a premere INVIO
                     return self.plugIn.showEvaluateMsg(None)
            else: # ci sono degli oggetti selezionati
               # 2 = Enables Edit mode shortcut menus
               if shortCutMenu & 2: 
                  return self.displayPopupMenuOnQuiescentState(event.pos())
               else:
                  # equivale a premere INVIO
                  return self.plugIn.showEvaluateMsg(None)
               
   
   # ============================================================================
   # FINE - eventi per il mouse
   # INIZIO - eventi per la tastiera
   # ============================================================================


   # ============================================================================
   # keyPressEvent
   # ============================================================================
   def keyPressEvent(self, e):
      myEvent = e
      
      if self.plugIn.shortCutManagement(myEvent): # se è stata gestita una sequenza di tasti scorciatoia
         return
       
      if myEvent.text() != "" and self.dynamicCmdInput.show(True, self.canvas.mouseLastXY(), self.dynamicCmdInput.getPrompt()) == True:
         self.dynamicCmdInput.keyPressEvent(myEvent)
      else:      
         self.plugIn.keyPressEvent(myEvent)


   # ============================================================================
   # FINE - eventi per la tastiera
   # INIZIO - eventi per la rotella
   # ============================================================================


   # ============================================================================
   # wheelEvent
   # ============================================================================
   def wheelEvent(self, event):
      QgsMapTool.wheelEvent(self, event)
      self.__csrRubberBand.moveEvent(self.toMapCoordinates(event.pos()))


   # ============================================================================
   # FINE - eventi per la rotella
   # ============================================================================

   
   # ============================================================================
   # activate
   # ============================================================================
   def activate(self):
      self.canvas.setToolTip("")
      self.canvas.setCursor(self.cursor)
      # posizione corrente del mouse
      self.__csrRubberBand.moveEvent(self.toMapCoordinates(self.canvas.mouseLastXY()))
      self.__csrRubberBand.show()
      self.entitySet.initByCurrentQgsSelectedFeatures(qad_utils.getVisibleVectorLayers(self.canvas)) # Tutti i layer vettoriali visibili
      self.refreshEntityGripPoints(self.entitySet)

      self.plugIn.QadCommands.continueCommandFromMapTool()
      self.plugIn.disableShortcut()
      
      self.dynamicCmdInput.setPrevPart(None)
      self.dynamicCmdInput.setNextPart(None)
      self.dynamicCmdInput.show(True, self.canvas.mouseLastXY())
      

   # ============================================================================
   # deactivate
   # ============================================================================
   def deactivate(self):
      self.__csrRubberBand.hide()
      self.timerForGripMenu.stop()
      self.plugIn.enableShortcut()
      
      self.dynamicCmdInput.show(False)


   # ============================================================================
   # isTransient
   # ============================================================================
   def isTransient(self):
      return False # questo tool non fa zoom o pan


   # ============================================================================
   # isEditTool
   # ============================================================================
   def isEditTool(self):
      return False # questo tool non fa editing


   # ============================================================================
   # displayPopupMenuOnQuiescentState
   # ============================================================================
   def displayPopupMenuOnQuiescentState(self, pos):
      popupMenu = QMenu(self.canvas)
      history = self.plugIn.cmdsHistory
      isLastCmdToInsert = True
      isRecentMenuToInsert = True
      
      historyLen = len(history)
      i = historyLen - 1
      cmdInputHistoryMax = QadVariables.get(QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX"))
      while i >= 0 and (historyLen - i) <= cmdInputHistoryMax:
         cmdName = history[i]
         i = i - 1
         cmd = self.plugIn.QadCommands.getCommandObj(cmdName)
         if cmd is not None:
            if isLastCmdToInsert:
               isLastCmdToInsert = False
               msg = QadMsg.translate("Popup_menu_graph_window", "Repeat ") + cmd.getName()
               icon = cmd.getIcon()
               if icon is None:
                  lastCmdAction = QAction(msg, popupMenu)
               else:
                  lastCmdAction = QAction(icon, msg, popupMenu)
               cmd.connectQAction(lastCmdAction)
               popupMenu.addAction(lastCmdAction)
            else:
               if isRecentMenuToInsert:
                  isRecentMenuToInsert = False
                  recentCmdsMenu = popupMenu.addMenu(QadMsg.translate("Popup_menu_graph_window", "Recent commands"))

               icon = cmd.getIcon()
               if icon is None:
                  recentCmdAction = QAction(cmd.getName(), recentCmdsMenu)
               else:
                  recentCmdAction = QAction(icon, cmd.getName(), recentCmdsMenu)                  
               cmd.connectQAction(recentCmdAction)      
               recentCmdsMenu.addAction(recentCmdAction)

            
      if isLastCmdToInsert == False: # menu non vuoto
         popupMenu.addSeparator()

      # aggiungo comando "OPTIONS"
      cmd = self.plugIn.QadCommands.getCommandObj(QadMsg.translate("Command_list", "OPTIONS"))
      icon = cmd.getIcon()
      if icon is None:
         optionsCmdAction = QAction(cmd.getName(), popupMenu)
      else:
         optionsCmdAction = QAction(icon, cmd.getName(), popupMenu)
      cmd.connectQAction(optionsCmdAction)
      popupMenu.addAction(optionsCmdAction)
         
      popupMenu.popup(self.canvas.mapToGlobal(pos))


   # ============================================================================
   # runCmdFromPopupMenuOnGrip
   # ============================================================================
   def runCmdFromPopupMenuOnGrip(self, virtualGripCommand, gripPoint):
      # seleziona il grip
      gripPoint.select()
      # lancio il comando
      self.plugIn.runCommand("QadVirtualGripCommandsClass", [virtualGripCommand, self.entitySetGripPoints, gripPoint.getPoint()])


   # ============================================================================
   # displayPopupMenuOnGrip
   # ============================================================================
   def displayPopupMenuOnGrip(self, pos, entity, gripPoint):
      if self.gripPopupMenu is not None:
         self.gripPopupMenu.hide()
         del self.gripPopupMenu
         self.gripPopupMenu = None
         
      popupMenu = QadGripPopupMenu(self.canvas)
      
      found = False
      
      # verifico se l'entità appartiene ad uno stile di quotatura
      if QadDimStyles.isDimEntity(entity):
         pass
      else:
         qadGeom = entity.getQadGeom(gripPoint.atGeom, gripPoint.atSubGeom)
         qadGeomType = qadGeom.whatIs()
         if qadGeomType == "ARC":
            qadGeom = entity.getQadGeom(gripPoint.atGeom, gripPoint.atSubGeom)
            
            # se punti finali
            if gripPoint.isIntersecting(qadGeom.getStartPt()) or gripPoint.isIntersecting(qadGeom.getEndPt()):
               found = True
               msg = QadMsg.translate("Popup_menu_grip_window", "Stretch")
               action = QAction(msg, popupMenu)
               f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.STRECTH, gripPoint)
               action.triggered.connect(f)
               popupMenu.addAction(action)

               msg = QadMsg.translate("Popup_menu_grip_window", "Lengthen")
               action = QAction(msg, popupMenu)
               f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.LENGTHEN, gripPoint)
               action.triggered.connect(f)
               popupMenu.addAction(action)
            # se punto medio
            elif gripPoint.isIntersecting(qadGeom.getMiddlePt()):
               found = True
               msg = QadMsg.translate("Popup_menu_grip_window", "Stretch")
               action = QAction(msg, popupMenu)
               f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.STRECTH, gripPoint)
               action.triggered.connect(f)
               popupMenu.addAction(action)
               
               msg = QadMsg.translate("Popup_menu_grip_window", "Radius")
               action = QAction(msg, popupMenu)
               f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.CHANGE_RADIUS, gripPoint)
               action.triggered.connect(f)
               popupMenu.addAction(action)
            
               msg = QadMsg.translate("Popup_menu_grip_window", "Convert to line")
               action = QAction(msg, popupMenu)
               f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ARC_TO_LINE, gripPoint)
               action.triggered.connect(f)
               popupMenu.addAction(action)

         if qadGeomType == "LINE":
            qadGeom = entity.getQadGeom(gripPoint.atGeom, gripPoint.atSubGeom)
            
            # se punti finali
            if gripPoint.isIntersecting(qadGeom.getStartPt()) or gripPoint.isIntersecting(qadGeom.getEndPt()):
               found = True
               msg = QadMsg.translate("Popup_menu_grip_window", "Stretch")
               action = QAction(msg, popupMenu)
               f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.STRECTH, gripPoint)
               action.triggered.connect(f)
               popupMenu.addAction(action)

               msg = QadMsg.translate("Popup_menu_grip_window", "Lengthen")
               action = QAction(msg, popupMenu)
               f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.LENGTHEN, gripPoint)
               action.triggered.connect(f)
               popupMenu.addAction(action)
               
         elif qadGeomType == "POLYLINE":
            isClosed = qadGeom.isClosed()
            nVertex = 0
            found = False
            while nVertex < qadGeom.qty():
               linearObject = qadGeom.getLinearObjectAt(nVertex)

               if gripPoint.isIntersecting(linearObject.getStartPt()):
                  found = True
                  msg = QadMsg.translate("Popup_menu_grip_window", "Stretch vertex")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.STRECTH, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)
                  
                  # punto iniziale
                  if isClosed == False and nVertex == 0:
                     msg = QadMsg.translate("Popup_menu_grip_window", "Lengthen")
                     action = QAction(msg, popupMenu)
                     f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.LENGTHEN, gripPoint)
                     action.triggered.connect(f)
                     popupMenu.addAction(action)

                  msg = QadMsg.translate("Popup_menu_grip_window", "Add vertex")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ADD_VERTEX, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)

                  msg = QadMsg.translate("Popup_menu_grip_window", "Add vertex before")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ADD_VERTEX_BEFORE, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)
                  break
               
               # punto medio
               if gripPoint.isIntersecting(linearObject.getMiddlePt()):
                  found = True
                  msg = QadMsg.translate("Popup_menu_grip_window", "Stretch")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.STRECTH, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)

                  msg = QadMsg.translate("Popup_menu_grip_window", "Add vertex")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ADD_VERTEX, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)

                  msg = QadMsg.translate("Popup_menu_grip_window", "Add vertex before")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ADD_VERTEX_BEFORE, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)
                  
                  gType = linearObject.whatIs()
                  if gType == "LINE":
                     msg = QadMsg.translate("Popup_menu_grip_window", "Convert to arc")
                     action = QAction(msg, popupMenu)
                     f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.LINE_TO_ARC, gripPoint)
                  elif gType == "ARC":
                     msg = QadMsg.translate("Popup_menu_grip_window", "Convert to line")
                     action = QAction(msg, popupMenu)
                     f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ARC_TO_LINE, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)
                  break
               
               nVertex = nVertex + 1
               
            linearObject = qadGeom.getLinearObjectAt(-1) # ultima parte
            if not found and isClosed == False:
               # punto finale
               if gripPoint.isIntersecting(linearObject.getEndPt()):
                  found = True
                  msg = QadMsg.translate("Popup_menu_grip_window", "Stretch vertex")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.STRECTH, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)

                  msg = QadMsg.translate("Popup_menu_grip_window", "Lengthen")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.LENGTHEN, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)

                  msg = QadMsg.translate("Popup_menu_grip_window", "Add vertex")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ADD_VERTEX, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)

                  msg = QadMsg.translate("Popup_menu_grip_window", "Add vertex before")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.ADD_VERTEX_BEFORE, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)

            if isClosed == False: # polyline
               # ci devono essere almeno 2 parti
               if qadGeom.qty() >= 2:
                  msg = QadMsg.translate("Popup_menu_grip_window", "Remove vertex")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.REMOVE_VERTEX, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)
            else: # polygon
               # ci devono essere almeno 4 parti
               if qadGeom.qty() >= 4:
                  msg = QadMsg.translate("Popup_menu_grip_window", "Remove vertex")
                  action = QAction(msg, popupMenu)
                  f = lambda : self.runCmdFromPopupMenuOnGrip(QadVirtualGripCommandsEnum.REMOVE_VERTEX, gripPoint)
                  action.triggered.connect(f)
                  popupMenu.addAction(action)
                     
      if found: # menu non vuoto
         popupMenu.popup(self.canvas.mapToGlobal(pos))
         self.gripPopupMenu = popupMenu
         
      return None


# ============================================================================
# QadGripPopupMenu
# ============================================================================
class QadGripPopupMenu(QMenu):
   def __init__(self, parent):
      QMenu.__init__(self, parent)
      self.offset = 0


   # ============================================================================
   # popup
   # ============================================================================
   def popup(self, pos, action = None):
      newPos = QPoint(pos.x() + self.offset, pos.y() + self.offset)
      QMenu.popup(self, newPos, action)
   
#    def leaveEvent(self, event):
#       if event.pos().x() < -1 * self.offset or event.pos().y() < -1 * self.offset:
#          self.hide()
     #self.hide()


   # ============================================================================
   # mouseMoveEvent
   # ============================================================================
   def mouseMoveEvent(self, event):
      x = event.pos().x()
      y = event.pos().y()
      if x < -1 * self.offset or y < -1 * self.offset or \
         x > self.width() or y > self.height():
         self.hide()
      else:
         QMenu.mouseMoveEvent(self, event)


# ============================================================================
# QadVirtualSelCommandClass
# Classe che gestisce il comando di selezione quando QAD è in stato di quiete
# ============================================================================
class QadVirtualSelCommandClass(QadCommandClass):

   # ============================================================================
   # instantiateNewCmd
   # ============================================================================
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadVirtualSelCommandClass(self.plugIn)
   

   # ============================================================================
   # getName
   # ============================================================================
   def getName(self):
      return "QadVirtualSelCommandClass"


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.entitySet.set(plugIn.tool.entitySet) # da usare solo con QadMapTool
      self.SSGetClass.exitAfterSelection = True
      self.SSGetClass.step = 1
   

   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass
      

   # ============================================================================
   # getPointMapTool
   # ============================================================================
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      return self.SSGetClass.getPointMapTool(drawMode)


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      res = self.SSGetClass.run(msgMapTool, msg)
      if res == True:
         self.plugIn.tool.entitySet.set(self.SSGetClass.entitySet) # da usare solo con QadMapTool
         self.plugIn.tool.entitySet.selectOnLayer()
      return res


# ===============================================================================
# QadVirtualGripCommandsEnum class.   
# ===============================================================================
class QadVirtualGripCommandsEnum():
   NONE            = 0
   STRECTH         = 1
   MOVE            = 2
   ROTATE          = 3
   SCALE           = 4
   MIRROR          = 5
   LENGTHEN        = 6
   ADD_VERTEX      = 7
   REMOVE_VERTEX   = 8
   LINE_TO_ARC     = 9
   ARC_TO_LINE     = 10
   CHANGE_RADIUS   = 11
   ADD_VERTEX_BEFORE = 12


# ============================================================================
# QadVirtualGripCommandsClass
# ============================================================================
# Classe che gestisce i comando disponibili sui grip quando QAD è in stato di quiete
class QadVirtualGripCommandsClass(QadCommandClass):

   # ============================================================================
   # instantiateNewCmd
   # ============================================================================
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadVirtualGripCommandsClass(self.plugIn)
   

   # ============================================================================
   # getName
   # ============================================================================
   def getName(self):
      return "QadVirtualGripCommandsClass"


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, plugIn):      
      QadCommandClass.__init__(self, plugIn)
      self.commandNum = QadVirtualGripCommandsEnum.NONE
      self.currentCommand = None
      self.entitySetGripPoints = None
      self.basePt = QgsPointXY()

   
   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      QadCommandClass.__del__(self)
      del self.currentCommand

      
   # ============================================================================
   # getPointMapTool
   # ============================================================================
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.currentCommand is not None:
         return self.currentCommand.getPointMapTool(drawMode)
      else:
         return None


   # ============================================================================
   # getCurrentContextualMenu
   # ============================================================================
   def getCurrentContextualMenu(self):
      if self.currentCommand is not None:
         return self.currentCommand.getCurrentContextualMenu()
      else:
         return None


   # ============================================================================
   # getCommand
   # ============================================================================
   def getCommand(self):
      if self.commandNum == QadVirtualGripCommandsEnum.STRECTH:
         return QadGRIPSTRETCHCommandClass(self.plugIn)
      elif self.commandNum == QadVirtualGripCommandsEnum.MOVE:
         return QadGRIPMOVECommandClass(self.plugIn)
      elif self.commandNum == QadVirtualGripCommandsEnum.ROTATE:
         return QadGRIPROTATECommandClass(self.plugIn)
      elif self.commandNum == QadVirtualGripCommandsEnum.SCALE:
         return QadGRIPSCALECommandClass(self.plugIn)
      elif self.commandNum == QadVirtualGripCommandsEnum.MIRROR:
         return QadGRIPMIRRORCommandClass(self.plugIn)
      elif self.commandNum == QadVirtualGripCommandsEnum.CHANGE_RADIUS:
         return QadGRIPCHANGEARCRADIUSCommandClass(self.plugIn)
      elif self.commandNum == QadVirtualGripCommandsEnum.LENGTHEN:
         return QadGRIPLENGTHENCommandClass(self.plugIn)
      elif self.commandNum == QadVirtualGripCommandsEnum.ADD_VERTEX:
         cmd = QadGRIPINSERTREMOVEVERTEXCommandClass(self.plugIn)
         cmd.setInsertVertexAfter_Mode()
         return cmd
      elif self.commandNum == QadVirtualGripCommandsEnum.ADD_VERTEX_BEFORE:
         cmd = QadGRIPINSERTREMOVEVERTEXCommandClass(self.plugIn)
         cmd.setInsertVertexBefore_Mode()
         return cmd
      elif self.commandNum == QadVirtualGripCommandsEnum.REMOVE_VERTEX:
         cmd = QadGRIPINSERTREMOVEVERTEXCommandClass(self.plugIn)
         cmd.setRemoveVertex_mode()
         return cmd
      elif self.commandNum == QadVirtualGripCommandsEnum.LINE_TO_ARC:
         cmd = QadGRIPARCLINECONVERTCommandClass(self.plugIn)
         cmd.setLineToArcConvert_Mode()
         return cmd
      elif self.commandNum == QadVirtualGripCommandsEnum.ARC_TO_LINE:
         cmd = QadGRIPARCLINECONVERTCommandClass(self.plugIn)
         cmd.setArcToLineConvert_Mode()
         return cmd
      
      return None


   # ============================================================================
   # initStartCommand
   # ============================================================================
   def initStartCommand(self, commandNum):
      if self.currentCommand is not None:
         del self.currentCommand
         self.currentCommand = None
         
      self.commandNum = commandNum
      self.currentCommand = self.getCommand()

      if self.currentCommand is not None:
         self.currentCommand.basePt.set(self.basePt.x(), self.basePt.y())
         self.currentCommand.setSelectedEntityGripPoints(self.entitySetGripPoints)
         return True
      else:
         return False


   # ============================================================================
   # initNextCommand
   # ============================================================================
   def initNextCommand(self):
      if self.currentCommand is not None:
         del self.currentCommand
         self.currentCommand = None
         
      if self.commandNum == QadVirtualGripCommandsEnum.STRECTH or \
         self.commandNum == QadVirtualGripCommandsEnum.LENGTHEN or \
         self.commandNum == QadVirtualGripCommandsEnum.ADD_VERTEX or \
         self.commandNum == QadVirtualGripCommandsEnum.ADD_VERTEX_BEFORE or \
         self.commandNum == QadVirtualGripCommandsEnum.REMOVE_VERTEX or \
         self.commandNum == QadVirtualGripCommandsEnum.LINE_TO_ARC or \
         self.commandNum == QadVirtualGripCommandsEnum.ARC_TO_LINE or \
         self.commandNum == QadVirtualGripCommandsEnum.CHANGE_RADIUS:
         self.commandNum = QadVirtualGripCommandsEnum.MOVE
      elif self.commandNum == QadVirtualGripCommandsEnum.MOVE:
         self.commandNum = QadVirtualGripCommandsEnum.ROTATE
      elif self.commandNum == QadVirtualGripCommandsEnum.ROTATE:
         self.commandNum = QadVirtualGripCommandsEnum.SCALE
      elif self.commandNum == QadVirtualGripCommandsEnum.SCALE:
         self.commandNum = QadVirtualGripCommandsEnum.MIRROR
      elif self.commandNum == QadVirtualGripCommandsEnum.MIRROR:
         self.commandNum = QadVirtualGripCommandsEnum.MOVE

      self.currentCommand = self.getCommand()

      if self.currentCommand is not None:
         self.currentCommand.basePt.set(self.basePt.x(), self.basePt.y())
         self.currentCommand.setSelectedEntityGripPoints(self.entitySetGripPoints)
         return True
      else:
         return False
         
         
   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.currentCommand is None:
         return True
      res = self.currentCommand.run(msgMapTool, msg)
      if res == True:
         if self.currentCommand.skipToNextGripCommand == True:
            if self.initNextCommand(): # attivo comando successivo
               return self.currentCommand.run(msgMapTool, msg)
         else:
            # ridisegno i grip point nelle nuove posizioni resettando quelli selezionati
            self.plugIn.tool.clearEntityGripPoints()
            self.plugIn.tool.refreshEntityGripPoints()

      return res

