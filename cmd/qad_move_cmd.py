# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando MOVE per spostare oggetti
 
                              -------------------
        begin                : 2013-09-27
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
from qgis.core import QgsPointXY


from .qad_move_maptool import Qad_move_maptool_ModeEnum, Qad_move_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import QadCacheEntitySet, QadEntityTypeEnum, QadCacheEntitySetIterator

from .. import qad_utils
from .. import qad_layer
from ..qad_dim import QadDimStyles, QadDimEntity, appendDimEntityIfNotExisting
from ..qad_multi_geom import fromQadGeomToQgsGeom

# Classe che gestisce il comando MOVE
class QadMOVECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadMOVECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "MOVE")

   def getEnglishName(self):
      return "MOVE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMOVECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/move.svg")

   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_MOVE", "Moves the selected objects.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass
      
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_move_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # move
   # ============================================================================
   def move(self, entity, offsetX, offsetY):
      # verifico se l'entità appartiene ad uno stile di quotatura
      if entity.whatIs() == "ENTITY":
         # sposto la geometria dell'entità
         qadGeom = entity.getQadGeom().copy() # la copio
         qadGeom.move(offsetX, offsetY)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
            return False
      elif entity.whatIs() == "DIMENTITY":
         if entity.deleteToLayers(self.plugIn) == False: return False # cancello vecchia quota 
         newDimEntity = QadDimEntity(entity) # la copio
         if newDimEntity.move(offsetX, offsetY) == False: return False # sposto la quota
         if newDimEntity.addToLayers(self.plugIn) == False: # ricreo nuva quota
            return False             
            
      return True


   # ============================================================================
   # moveGeoms
   # ============================================================================
   def moveGeoms(self, newPt):      
      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()
      
      self.plugIn.beginEditCommand("Feature moved", self.cacheEntitySet.getLayerList())
      
      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)         
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if self.move(entity, offsetX, offsetY) == False:
            self.plugIn.destroyEditCommand()
            return
               
      self.plugIn.endEditCommand()
      

   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
            
      # =========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == 0: # inizio del comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selezione terminata
            self.step = 1
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di selezione entità                    
            return self.run(msgMapTool, msg)
      
      # =========================================================================
      # SPOSTA OGGETTI
      elif self.step == 1:
         if self.SSGetClass.entitySet.count() == 0:
            return True # fine comando
         self.cacheEntitySet.appendEntitySet(self.SSGetClass.entitySet)

         # imposto il map tool
         self.getPointMapTool().cacheEntitySet = self.cacheEntitySet
         self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)                                
   
         keyWords = QadMsg.translate("Command_MOVE", "Displacement")
         prompt = QadMsg.translate("Command_MOVE", "Specify base point or [{0}] <{0}>: ").format(keyWords)
         
         englishKeyWords = "Displacement"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o enter o una parola chiave         
         # msg, inputType, default, keyWords, nessun controllo
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)      
         self.step = 2      
         return False
         
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO BASE (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

         if value is None or type(value) == unicode:
            self.basePt.set(0, 0)
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)                                
            # si appresta ad attendere un punto
            msg = QadMsg.translate("Command_MOVE", "Specify the displacement fom the origin point 0,0 <{0}, {1}>: ")
            # msg, inputType, default, keyWords, nessun controllo
            self.waitFor(msg.format(str(self.plugIn.lastOffsetPt.x()), str(self.plugIn.lastOffsetPt.y())), \
                         QadInputTypeEnum.POINT2D, \
                         self.plugIn.lastOffsetPt, \
                         "", QadInputModeEnum.NONE)                                      
            self.step = 4           
         elif type(value) == QgsPointXY: # se é stato inserito il punto base
            self.basePt.set(value.x(), value.y())

            # imposto il map tool
            self.getPointMapTool().basePt = self.basePt
            self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)                                
            
            # si appresta ad attendere un punto o enter o una parola chiave         
            # msg, inputType, default, keyWords, nessun controllo
            self.waitFor(QadMsg.translate("Command_MOVE", "Specify the second point or <use first point as displacement from the origin point 0,0>: "), \
                         QadInputTypeEnum.POINT2D, \
                         None, \
                         "", QadInputModeEnum.NONE)      
            self.step = 3      
         
         return False 
         
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER SPOSTAMENTO (da step = 2)
      elif self.step == 3: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
            self.moveGeoms(newPt)
         elif type(value) == QgsPointXY: # se é stato inserito lo spostamento con un punto
            self.moveGeoms(value)
            
         return True # fine comando
               
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PUNTO DI SPOSTAMENTO (da step = 2)
      elif self.step == 4: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
         self.moveGeoms(value)
         return True


# Classe che gestisce il comando MOVE per i grip
class QadGRIPMOVECommandClass(QadCommandClass):


   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadGRIPMOVECommandClass(self.plugIn)

   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0

   
   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_move_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   # ============================================================================
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # lista delle entityGripPoint con dei grip point selezionati
      self.cacheEntitySet.clear()

      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         self.cacheEntitySet.appendEntity(entityGripPoints.entity)
         
      self.getPointMapTool().cacheEntitySet = self.cacheEntitySet


   # ============================================================================
   # move
   # ============================================================================
   def move(self, entity, offsetX, offsetY, openForm = True):
      # verifico se l'entità appartiene ad uno stile di quotatura
      if entity.whatIs() == "ENTITY":
         # sposto la geometria dell'entità
         qadGeom = entity.getQadGeom().copy() # la copio
         qadGeom.move(offsetX, offsetY)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))
         if self.copyEntities == False:
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False
         else:
            # plugIn, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
               return False
      elif entity.whatIs() == "DIMENTITY":
         # stiro la quota
         if self.copyEntities == False:
            if entity.deleteToLayers(self.plugIn) == False:
               return False                      
         newDimEntity = QadDimEntity(entity) # la copio
         newDimEntity.move(offsetX, offsetY)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False             

      return True
      

   # ============================================================================
   # moveFeatures
   # ============================================================================
   def moveFeatures(self, newPt):
      offsetX = newPt.x() - self.basePt.x()
      offsetY = newPt.y() - self.basePt.y()
      
      self.plugIn.beginEditCommand("Feature moved", self.cacheEntitySet.getLayerList())

      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      openForm = True if self.cacheEntitySet.count() == 1 else False
      
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)         
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if self.move(entity, offsetX, offsetY, openForm) == False:
            self.plugIn.destroyEditCommand()
            return
               
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1
                           
                           
   # ============================================================================
   # waitForMovePoint
   # ============================================================================
   def waitForMovePoint(self):
      self.step = 1
      self.plugIn.setLastPoint(self.basePt)
      # imposto il map tool
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_MOVE_PT)
      
      keyWords = QadMsg.translate("Command_GRIPMOVE", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIPMOVE", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIPMOVE", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIPMOVE", "eXit")

      prompt = QadMsg.translate("Command_GRIPMOVE", "Specify move point or [{0}]: ").format(keyWords)

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
      self.getPointMapTool().setMode(Qad_move_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_GRIPMOVE", "Specify base point: "))


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
         if self.cacheEntitySet.isEmpty(): # non ci sono oggetti da spostare
            return True
         self.showMsg(QadMsg.translate("Command_GRIPMOVE", "\n** MOVE **\n"))
         # si appresta ad attendere un punto di spostamento
         self.waitForMovePoint()
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI UN PUNTO DI SPOSTAMENTO
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
            if value == QadMsg.translate("Command_GRIPMOVE", "Base point") or value == "Base point":
               # si appresta ad attendere il punto base
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIPMOVE", "Copy") or value == "Copy":
               # Copia entità lasciando inalterate le originali
               self.copyEntities = True                     
               # si appresta ad attendere un punto di spostamento
               self.waitForMovePoint()
            elif value == QadMsg.translate("Command_GRIPMOVE", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
               # si appresta ad attendere un punto di spostamento
               self.waitForMovePoint()
            elif value == QadMsg.translate("Command_GRIPMOVE", "eXit") or value == "eXit":
               return True # fine comando
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            if ctrlKey:
               self.copyEntities = True

            self.moveFeatures(value)

            if self.copyEntities == False:
               return True
            # si appresta ad attendere un punto di stiramento
            self.waitForMovePoint()
          
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
            
         # si appresta ad attendere un punto di spostamento
         self.waitForMovePoint()

         return False
