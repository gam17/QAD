# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando STRETCH per stirare oggetti grafici ok
 
                              -------------------
        begin                : 2013-07-15
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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsPointXY, QgsCoordinateTransform, QgsGeometry, QgsRectangle


from ..qad_line import QadLine
from .qad_stretch_maptool import Qad_stretch_maptool, Qad_stretch_maptool_ModeEnum, Qad_gripStretch_maptool
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_mpolygon_cmd import QadMPOLYGONCommandClass
from .qad_rectangle_cmd import QadRECTANGLECommandClass
from .qad_generic_cmd import QadCommandClass
from ..qad_variables import QadVariables
from ..qad_msg import QadMsg
from .. import qad_utils
from .. import qad_layer
from .. import qad_stretch_fun
from .. import qad_grip
from ..qad_entity import QadEntitySet, getSelSet, QadEntityTypeEnum, QadEntity
from ..qad_dim import QadDimStyles, QadDimEntity
from ..qad_multi_geom import fromQadGeomToQgsGeom



# Classe che gestisce il comando STRETCH
class QadSTRETCHCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadSTRETCHCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "STRETCH")

   def getEnglishName(self):
      return "STRETCH"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSTRETCHCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/stretch.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_STRETCH", "Stretches objects.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.AddOnSelection = True # se = False significa remove
      self.points = []
      self.MPOLYGONCommand = None
      self.SSGeomList = [] # lista di entità da stirare con geom di selezione
      self.basePt = QgsPointXY()
   
   def __del__(self):
      QadCommandClass.__del__(self)
      if self.MPOLYGONCommand is not None:
         del self.MPOLYGONCommand      
      for SSGeom in self.SSGeomList:
         SSGeom[0].deselectOnLayer()


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 2: # quando si é in fase di disegno linea
         return self.MPOLYGONCommand.getPointMapTool(drawMode)
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_stretch_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 2: # quando si é in fase di disegno linea
         return self.MPOLYGONCommand.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def stretch(self, entity, containerGeom, offsetX, offsetY, tolerance2ApproxCurve, openForm = True):
      # entity = entità da stirare
      # ptList = lista dei punti da stirare
      # offsetX, offsetY = spostamento da applicare
      # tolerance2ApproxCurve = tolleranza per ricreare le curve
      
      if entity.whatIs() == "DIMENTITY":
         dimEntity = entity
      else:
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         
      if dimEntity is None:
         stretchedGeom = entity.getQadGeom()
         # controllo inserito perchè con le quote, questa viene cancellata e ricreata quindi alcuni oggetti potrebbero non esistere più
         if stretchedGeom is None: # se non c'è lo salto senza errore
            return True
         # stiro la feature
         stretchedGeom = qad_stretch_fun.stretchQadGeometry(stretchedGeom, containerGeom, \
                                                            offsetX, offsetY)
         
         if stretchedGeom is not None:
            # trasformo la geometria nel crs del layer
            f = entity.getFeature()
            f.setGeometry(fromQadGeomToQgsGeom(stretchedGeom, entity.layer))
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False

      else:
         # stiro la quota
         if dimEntity.deleteToLayers(self.plugIn) == False:
            return False
         newDimEntity = QadDimEntity(dimEntity) # la copio
         newDimEntity.stretch(containerGeom, offsetX, offsetY)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False             
            
      return True


   # ============================================================================
   # stretchFeatures
   # ============================================================================
   def stretchFeatures(self, newPt):
      # mi ricavo un unico QadEntitySet con le entità selezionate
      entitySet = QadEntitySet()
      for SSGeom in self.SSGeomList:
         entitySet.unite(SSGeom[0])
      self.plugIn.beginEditCommand("Feature stretched", entitySet.getLayerList())
      openForm = True if entitySet.count() == 1 else False
      
      dimElaboratedList = [] # lista delle quotature già elaborate

      tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()
      
      entity = QadEntity()
      for SSGeom in self.SSGeomList:
         # copio entitySet
         entitySet = QadEntitySet(SSGeom[0])
         geomSel = SSGeom[1]

         for layerEntitySet in entitySet.layerEntitySetList:
            layer = layerEntitySet.layer

            for featureId in layerEntitySet.featureIds:
               entity.set(layer, featureId)

               # verifico se l'entità appartiene ad uno stile di quotatura
               dimEntity = QadDimStyles.getDimEntity(entity)  
               if dimEntity is None:                        
                  if self.stretch(entity, geomSel, offsetX, offsetY, tolerance2ApproxCurve, openForm) == False:
                     self.plugIn.destroyEditCommand()
                     return
               else:
                  found = False
                  for dimElaborated in dimElaboratedList:
                     if dimElaborated == dimEntity:
                        found = True
                  
                  if found == False: # quota non ancora elaborata
                     # aggiungo i layer dei componenti della quota
                     self.plugIn.addLayerListToLastEditCommand("Feature stretched", 
                                                               [dimEntity.getSymbolLayer(), dimEntity.getLinearLayer(), dimEntity.getTextualLayer()])
                     
                     dimElaboratedList.append(dimEntity)
                     if self.stretch(dimEntity, geomSel, offsetX, offsetY, tolerance2ApproxCurve) == False:
                        self.plugIn.destroyEditCommand()
                        return

      self.plugIn.endEditCommand()


   # ============================================================================
   # setEntitySetGeom
   # ============================================================================
   def setEntitySetGeom(self, entitySet, selGeom):
      for SSGeom in self.SSGeomList:
         SSGeom[0].deselectOnLayer()
      del self.SSGeomList[:] # svuoto la lista  
      # aggiuge il gruppo di selezione con la geometria usata per la selezione
      self.SSGeomList.append([entitySet, selGeom])
      entitySet.selectOnLayer(False) # incremental = False

   # ============================================================================
   # addEntitySetGeom
   # ============================================================================
   def addEntitySetGeom(self, entitySet, selGeom):      
      # elimino dai gruppi precedenti gli oggetti presenti in entitySet
      self.removeEntitySet(entitySet)
      # aggiuge il gruppo di selezione con la geometria usata per la selezione
      self.SSGeomList.append([entitySet, selGeom])
      entitySet.selectOnLayer(True) # incremental = True
                                                      

   # ============================================================================
   # removeEntitySet
   # ============================================================================
   def removeEntitySet(self, entitySet):
      # elimino dai gruppi precedenti gli oggetti presenti in entitySet
      for SSGeom in self.SSGeomList:
         SSGeom[0].subtract(entitySet)
      for SSGeom in self.SSGeomList:
         SSGeom[0].selectOnLayer(False) # incremental = False


   # ============================================================================
   # SSGeomListIsEmpty
   # ============================================================================
   def SSGeomListIsEmpty(self):
      if len(self.SSGeomList) == 0:
         return True      
      for SSGeom in self.SSGeomList:
         if SSGeom[0].isEmpty() == False:
            return False
      return True

      
   # ============================================================================
   # waitForObjectSel
   # ============================================================================
   def waitForObjectSel(self):      
      self.step = 1     
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.ASK_FOR_FIRST_PT_RECTANGLE)                                
      
      keyWords = QadMsg.translate("Command_STRETCH", "Polygon") + "/" + \
                 QadMsg.translate("Command_STRETCH", "Add") + "/" + \
                 QadMsg.translate("Command_STRETCH", "Remove")

      if self.AddOnSelection == True:
         prompt = QadMsg.translate("Command_STRETCH", "Select vertices")
      else:
         prompt = QadMsg.translate("Command_STRETCH", "Remove vertices")
      prompt = prompt + QadMsg.translate("Command_STRETCH", " to stretch crossed by a selection window or [{0}]: ").format(keyWords)                        

      englishKeyWords = "Polygon" + "/" + "Add" + "/" + "Remove"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)      


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):      
      self.step = 4   
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)                                
      
      keyWords = QadMsg.translate("Command_STRETCH", "Displacement")
      prompt = QadMsg.translate("Command_STRETCH", "Specify base point or [{0}] <{0}>: ").format(keyWords)
         
      englishKeyWords = "Displacement"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)      


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
     
      # =========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == 0: # inizio del comando
         # si appresta ad attendere la selezione degli oggetti da stirare
         self.waitForObjectSel()
         return False
      
      # =========================================================================
      # RISPOSTA ALLA SELEZIONE OGGETTI DA STIRARE
      elif self.step == 1:
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = None
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_STRETCH", "Polygon") or value == "Polygon":
               # Seleziona tutti gli oggetti che sono interni al poligono
               self.MPOLYGONCommand = QadMPOLYGONCommandClass(self.plugIn)
               # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
               # che non verrà salvata su un layer
               self.MPOLYGONCommand.virtualCmd = True   
               self.MPOLYGONCommand.run(msgMapTool, msg)
               self.step = 2
               return False               
            elif value == QadMsg.translate("Command_SSGET", "Add") or value == "Add":
               # Passa al metodo Aggiungi: gli oggetti selezionati possono essere aggiunti al gruppo di selezione 
               self.AddOnSelection = True
            elif value == QadMsg.translate("Command_SSGET", "Remove") or value == "Remove":
               # Passa al metodo Rimuovi: gli oggetti possono essere rimossi dal gruppo di selezione
               self.AddOnSelection = False                        
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            del self.points[:] # svuoto la lista
            self.points.append(value)
            # imposto il map tool
            self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_RECTANGLE)                                            
            self.getPointMapTool().setStartPoint(value)
            
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_STRETCH", "Specify opposite corner: "))
            self.step = 3
            return False                  
         else:
            if self.SSGeomListIsEmpty():
               return True
            # si appresta ad attendere il punto base o lo spostamento
            self.waitForBasePt()
            return False                  
         
         # si appresta ad attendere la selezione degli oggetti da stirare
         self.waitForObjectSel()
                                          
         return False 

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO PER MODALITA' POLIGONO (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto si riavvia il comando
         if self.MPOLYGONCommand.run(msgMapTool, msg) == True:
            if self.MPOLYGONCommand.PLINECommand.polyline.qty() > 0:
               # cerco tutte le geometrie intersecanti il poligono
               # e considerando solo layer editabili
               selSet = getSelSet("CP", self.getPointMapTool(), self.MPOLYGONCommand.PLINECommand.polyline.asPolyline(), \
                                  None, True, True, True, \
                                  True)
               # se la selezione é avvenuta con shift premuto o se si deve rimuovere il gruppo selSet dal gruppo
               if self.AddOnSelection == False:
                  self.removeEntitySet(selSet)
               else:
                  self.setEntitySetGeom(selSet, QgsGeometry.fromPolygonXY([self.MPOLYGONCommand.PLINECommand.polyline.asPolyline()]))
                              
            del self.MPOLYGONCommand
            self.MPOLYGONCommand = None

            # si appresta ad attendere la selezione degli oggetti da stirare
            self.waitForObjectSel()                                 
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di mpolygon                     
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO PER MODALITA' FINESTRA (da step = 1)
      elif self.step == 3: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.showMsg(QadMsg.translate("Command_STRETCH", "Window not correct."))
                  # si appresta ad attendere un punto
                  self.waitForPoint(QadMsg.translate("Command_STRETCH", "Specify opposite corner: "))
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            shiftKey = self.getPointMapTool().shiftKey
            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            shiftKey = False
            value = msg


         if type(value) == QgsPointXY:
            self.points.append(value)   
            # cerco tutte le geometrie intersecanti il rettangolo
            # e considerando solo layer editabili
            selSet = getSelSet("C", self.getPointMapTool(), self.points, \
                               None, True, True, True, \
                               True)            
            # se si deve rimuovere il gruppo entitySet dal gruppo
            if self.AddOnSelection == False:
               self.removeEntitySet(selSet)
            else:
               if shiftKey: # se la selezione é avvenuta con shift premuto
                  self.addEntitySetGeom(selSet, QgsGeometry.fromRect(QgsRectangle(self.points[0], self.points[1])))
               else:
                  self.setEntitySetGeom(selSet, QgsGeometry.fromRect(QgsRectangle(self.points[0], self.points[1])))
            # si appresta ad attendere la selezione degli oggetti da stirare
            self.waitForObjectSel()                                 
         return False
              
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO BASE (da step = 1)
      elif self.step == 4: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  pass # opzione di default "spostamento"
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         # imposto il map tool
         self.getPointMapTool().SSGeomList = self.SSGeomList

         if value is None or type(value) == unicode:
            self.basePt.set(0, 0)
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)                                
            # si appresta ad attendere un punto
            msg = QadMsg.translate("Command_STRETCH", "Specify the displacement from the origin point 0,0 <{0}, {1}>: ")
            # msg, inputType, default, keyWords, nessun controllo
            self.waitFor(msg.format(str(self.plugIn.lastOffsetPt.x()), str(self.plugIn.lastOffsetPt.y())), \
                         QadInputTypeEnum.POINT2D, \
                         self.plugIn.lastOffsetPt, \
                         "", QadInputModeEnum.NONE)                                      
            self.step = 5      
         elif type(value) == QgsPointXY: # se é stato inserito il punto base
            self.basePt.set(value.x(), value.y())

            # imposto il map tool
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)                                
            
            # si appresta ad attendere un punto o enter o una parola chiave         
            # msg, inputType, default, keyWords, nessun controllo
            self.waitFor(QadMsg.translate("Command_STRETCH", "Specify second point or <use first point as displacement from origin point 0,0>: "), \
                         QadInputTypeEnum.POINT2D, \
                         None, \
                         "", QadInputModeEnum.NONE)      
            self.step = 6      
         
         return False 

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PUNTO DI SPOSTAMENTO (da step = 2)
      elif self.step == 5: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.plugIn.setLastOffsetPt(value)
         self.stretchFeatures(value)
         return True # fine comando     
         
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER SPOSTAMENTO (da step = 2)
      elif self.step == 6: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None:
            newPt = QgsPointXY(self.basePt.x() * 2, self.basePt.y() * 2)
            self.stretchFeatures(newPt)
         elif type(value) == QgsPointXY: # se é stato inserito lo spostamento con un punto
            self.stretchFeatures(value)
            
         return True # fine comando



# ============================================================================
# Classe che gestisce il comando STRETCH per i grip
# ============================================================================
class QadGRIPSTRETCHCommandClass(QadCommandClass):


   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadGRIPSTRETCHCommandClass(self.plugIn)

   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.selectedEntityGripPoints = [] # lista in cui ogni elemento è una entità + una lista di punti da stirare
      self.basePt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0

   
   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_gripStretch_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   # ============================================================================
   # addToSelectedEntityGripPoints
   # ============================================================================
   def addToSelectedEntityGripPoints(self, entityGripPoints):
      # entità con lista dei grip point
      i = 0
      gripPoints = entityGripPoints.gripPoints
      gripPointsLen = len(gripPoints)
      ptList = []
      while i < gripPointsLen:
         gripPoint = gripPoints[i]
         # grip point selezionato
         if gripPoint.getStatus() == qad_grip.QadGripStatusEnum.SELECTED:
            if gripPoint.gripType == qad_grip.QadGripPointTypeEnum.CENTER:
               ptList.append(gripPoint.getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.LINE_MID_POINT:
               # aggiungo il vertice precedente e successivo di quello intermedio
               if i > 0:
                  ptList.append(gripPoints[i - 1].getPoint())
               if i < gripPointsLen - 1:
                  # se il grip successivo è center si tratta dell'ultimo tratto di un poligono
                  if gripPoints[i + 1].gripType == qad_grip.QadGripPointTypeEnum.CENTER:
                     ptList.append(gripPoints[0].getPoint()) # prendo il primo punto
                  else:
                     ptList.append(gripPoints[i + 1].getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.QUA_POINT:
               ptList.append(gripPoint.getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.VERTEX or \
                 gripPoint.gripType == qad_grip.QadGripPointTypeEnum.END_VERTEX:
               ptList.append(gripPoint.getPoint())
            elif gripPoint.gripType == qad_grip.QadGripPointTypeEnum.ARC_MID_POINT:
               ptList.append(gripPoint.getPoint())
         i = i + 1
      
      if len(ptList) > 0:
         self.selectedEntityGripPoints.append([entityGripPoints.entity, ptList])

   
   # ============================================================================
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # lista delle entityGripPoint con dei grip point selezionati
      # ritorna una lista in cui ogni elemento è una entità + una lista di punti da stirare
      del self.selectedEntityGripPoints[:] # svuoto la lista

      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         self.addToSelectedEntityGripPoints(entityGripPoints)
      self.getPointMapTool().setSelectedEntityGripPoints(self.selectedEntityGripPoints)
      
      # input : self.basePt e entitySetGripPoints
      # cerco in entitySetGripPoints l'entità che ha un solo grip selezionato corrispondente a basePt
      entityGripPoints, entityGripPoint = entitySetGripPoints.isIntersecting(self.basePt)
      if entityGripPoint.getStatus() == qad_grip.QadGripStatusEnum.SELECTED and \
         len(entityGripPoints.getSelectedGripPoints()) == 1:
         
         entity = entityGripPoints.entity
         # verifico se l'entità appartiene ad uno stile di quotatura
         if QadDimStyles.isDimEntity(entity):
            pass
         else:
            qadGeom = entity.getQadGeom(entityGripPoint.atGeom, entityGripPoint.atSubGeom)
            qadGeomType = qadGeom.whatIs()
            if qadGeomType == "POLYLINE":
               self.getPointMapTool().prevPart, self.getPointMapTool().nextPart = qadGeom.getPrevNextLinearObjectsAtVertex(entityGripPoint.nVertex)               
            elif qadGeomType == "CIRCLE":
               if qadGeom.isPtOnCircle(entityGripPoint.getPoint()):
                  line = QadLine()
                  line.set(qadGeom.center, entityGripPoint.getPoint())
                  self.getPointMapTool().prevPart = line
            elif qadGeomType == "ELLIPSE":
               if qadGeom.containsPt(entityGripPoint.getPoint()):
                  line = QadLine()
                  line.set(qadGeom.center, entityGripPoint.getPoint())
                  self.getPointMapTool().prevPart = line


   # ============================================================================
   # getSelectedEntityGripPointNdx
   # ============================================================================
   def getSelectedEntityGripPointNdx(self, entity):
      # lista delle entityGripPoint con dei grip point selezionati
      # cerca la posizione di un'entità nella lista in cui ogni elemento è una entità + una lista di punti da stirare
      i = 0
      tot = len(self.selectedEntityGripPoints)
      while i < tot:
         selectedEntityGripPoint = self.selectedEntityGripPoints[i]
         if selectedEntityGripPoint[0] == entity:
            return i
         i = i + 1
      return -1


   # ============================================================================
   # stretch
   # ============================================================================
   def stretch(self, entity, ptList, offsetX, offsetY, tolerance2ApproxCurve, openForm):
      # entity = entità da stirare
      # ptList = lista dei punti da stirare
      # offsetX, offsetY = spostamento da applicare
      # tolerance2ApproxCurve = tolleranza per ricreare le curve
      
      if entity.whatIs() == "DIMENTITY":
         dimEntity = entity
      else:
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
      
      if dimEntity is None:
         stretchedGeom = entity.getQadGeom()
         # controllo inserito perchè con le quote, questa viene cancellata e ricreata quindi alcuni oggetti potrebbero non esistere più
         if stretchedGeom is None: # se non c'è lo salto senza errore
            return True

         # stiro la feature
         stretchedGeom = qad_stretch_fun.stretchQadGeometry(stretchedGeom, ptList, \
                                                            offsetX, offsetY)
         
         if stretchedGeom is not None:
            # trasformo la geometria QAD in geometria GSIS nel crs del layer
            f = entity.getFeature()
            f.setGeometry(fromQadGeomToQgsGeom(stretchedGeom, entity.layer))
            if self.copyEntities == False:
               # plugIn, layer, feature, refresh, check_validity
               if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
                  return False
            else:
               # plugIn, layer, features, coordTransform, refresh, check_validity
               if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
                  return False
               
      else:
         # stiro la quota
         if self.copyEntities == False:
            if dimEntity.deleteToLayers(self.plugIn) == False:
               return False                      
         newDimEntity = QadDimEntity(dimEntity) # la copio
         newDimEntity.stretch(ptList, offsetX, offsetY)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False
         # non so per quale motivo a volte non si aggiorna la mappa quindi forzo l'aggiornamento
         self.plugIn.canvas.refresh()
            
      return True


   # ============================================================================
   # stretchFeatures
   # ============================================================================
   def stretchFeatures(self, newPt):
      # mi ricavo un unico QadEntitySet con le entità selezionate
      entitySet = QadEntitySet()
      for selectedEntity in self.selectedEntityGripPoints:
         entitySet.addEntity(selectedEntity[0])
      self.plugIn.beginEditCommand("Feature stretched", entitySet.getLayerList())
      openForm = True if len(self.selectedEntityGripPoints) == 1 else False
      
      dimElaboratedList = [] # lista delle quotature già elaborate
      
      for selectedEntity in self.selectedEntityGripPoints:
         entity = selectedEntity[0]
         ptList = selectedEntity[1]
         layer = entity.layer
         
         tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
         offsetX = newPt.x() - self.basePt.x()
         offsetY = newPt.y() - self.basePt.y()

         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is None:
            if self.stretch(entity, ptList, offsetX, offsetY, tolerance2ApproxCurve, openForm) == False:
               self.plugIn.destroyEditCommand()
               return
         else:
            found = False
            for dimElaborated in dimElaboratedList:
               if dimElaborated == dimEntity:
                  found = True
            
            if found == False: # quota non ancora elaborata
               # aggiungo i layer dei componenti della quota
               self.plugIn.addLayerListToLastEditCommand("Feature stretched", 
                                                         [dimEntity.getSymbolLayer(), dimEntity.getLinearLayer(), dimEntity.getTextualLayer()])
                        
               dimEntitySet = dimEntity.getEntitySet()
               # creo un'unica lista contenente i grip points di tutti i componenti della quota
               dimPtlist = []
               for layerEntitySet in dimEntitySet.layerEntitySetList:
                  for featureId in layerEntitySet.featureIds:
                     componentDim = QadEntity()
                     componentDim.set(layerEntitySet.layer, featureId)
                     i = self.getSelectedEntityGripPointNdx(componentDim)
                     if i >= 0:
                        dimPtlist.extend(self.selectedEntityGripPoints[i][1])

               dimElaboratedList.append(dimEntity)
               if self.stretch(dimEntity, dimPtlist, offsetX, offsetY, tolerance2ApproxCurve, False) == False:
                  self.plugIn.destroyEditCommand()
                  return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1
                           
                           
   # ============================================================================
   # waitForStretchPoint
   # ============================================================================
   def waitForStretchPoint(self):
      self.step = 1
      self.plugIn.setLastPoint(self.basePt)
      # imposto il map tool
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)
      
      keyWords = QadMsg.translate("Command_GRIP", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIP", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIP", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIP", "eXit")

      prompt = QadMsg.translate("Command_GRIPSTRETCH", "Specify stretch point or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" + "eXit"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)      


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 2   
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_stretch_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)                                

      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_GRIPSTRETCH", "Specify base point: "))


   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
     
      # =========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == 0: # inizio del comando
         if len(self.selectedEntityGripPoints) == 0: # non ci sono oggetti da stirare
            return True
         self.showMsg(QadMsg.translate("Command_GRIPSTRETCH", "\n** STRETCH **\n"))
         # si appresta ad attendere un punto di stiramento
         self.waitForStretchPoint()
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI UN PUNTO DI STIRAMENTO
      elif self.step == 1:
         ctrlKey = False
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = None
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point

            ctrlKey = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_GRIP", "Base point") or value == "Base point":
               # si appresta ad attendere il punto base
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIP", "Copy") or value == "Copy":
               # Copia entità lasciando inalterate le originali
               self.copyEntities = True                     
               # si appresta ad attendere un punto di stiramento
               self.waitForStretchPoint()
            elif value == QadMsg.translate("Command_GRIP", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
               # si appresta ad attendere un punto di stiramento
               self.waitForStretchPoint()
            elif value == QadMsg.translate("Command_GRIP", "eXit") or value == "eXit":
               return True # fine comando
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            if ctrlKey:
               self.copyEntities = True
               
            self.stretchFeatures(value)

            if self.copyEntities == False:
               return True
            # si appresta ad attendere un punto di stiramento
            self.waitForStretchPoint()
          
         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # fine comando
                                          
         return False 

              
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO BASE (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  pass # opzione di default "spostamento"
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il punto base
            self.basePt.set(value.x(), value.y())
            # imposto il map tool
            self.getPointMapTool().basePt = self.basePt
            
         # si appresta ad attendere un punto di stiramento
         self.waitForStretchPoint()

         return False