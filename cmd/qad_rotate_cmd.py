# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando ROTATE per ruotare oggetti
 
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
from qgis.core import QgsPointXY, NULL
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon


from .qad_rotate_maptool import Qad_rotate_maptool_ModeEnum, Qad_rotate_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import QadCacheEntitySet, QadCacheEntitySetIterator, QadEntityTypeEnum
from .. import qad_utils
from .. import qad_layer
from .. import qad_label
from ..qad_dim import QadDimStyles, QadDimEntity, appendDimEntityIfNotExisting
from ..qad_multi_geom import fromQadGeomToQgsGeom


# Classe che gestisce il comando RUOTA
class QadROTATECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadROTATECommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "ROTATE")

   def getEnglishName(self):
      return "ROTATE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runROTATECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/rotate.svg")

   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_ROTATE", "Rotates objects around a base point.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = None
      self.copyFeatures = False
      self.Pt1ReferenceAng = None
      self.ReferenceAng = 0
      self.Pt1NewAng = None

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_rotate_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   #============================================================================
   # rotate
   #============================================================================
   def rotate(self, entity, basePt, angle, openForm):
      # verifico se l'entità appartiene ad uno stile di quotatura
      if entity.whatIs() == "ENTITY":
         # ruoto la geometria dell'entità
         qadGeom = entity.getQadGeom().copy() # la copio
         qadGeom.rotate(basePt, angle)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         if len(entity.rotFldName) > 0:
            rotValue = f.attribute(entity.rotFldName)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # la rotazione é in gradi nel campo della feature
            rotValue = rotValue + angle
            f.setAttribute(entity.rotFldName, qad_utils.toDegrees(qad_utils.normalizeAngle(rotValue)))               

         if self.copyFeatures == False:
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False
         else:             
            # plugIn, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False, openForm) == False:
               return False
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # la copio
         # ruoto la quota
         if self.copyFeatures == False:
            if dimEntity.deleteToLayers(self.plugIn) == False:
               return False                      
         newDimEntity.rotate(basePt, angle)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False             
            
      return True


   def RotateGeoms(self, angle):      
      self.plugIn.beginEditCommand("Feature rotated", self.cacheEntitySet.getLayerList())
      
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

         if self.rotate(entity, self.basePt, angle, openForm) == False:  
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()


   def waitForRotation(self):
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_ROTATION_PT)

      keyWords = QadMsg.translate("Command_ROTATE", "Copy") + "/" + \
                 QadMsg.translate("Command_ROTATE", "Reference")
      prompt = QadMsg.translate("Command_ROTATE", "Specify rotation angle or [{0}] <{1}>: ").format(keyWords, \
               str(qad_utils.toDegrees(self.plugIn.lastRot)))
      
      englishKeyWords = "Copy" + "/" + "Reference"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto, un numero reale o enter o una parola chiave
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE | QadInputTypeEnum.KEYWORDS, \
                   self.plugIn.lastRot, \
                   keyWords, QadInputModeEnum.NONE)
      
      self.step = 3      


   def waitForReferenceRot(self):
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_ANG)
      
      msg = QadMsg.translate("Command_ROTATE", "Specify reference angle <{0}>: ")
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(msg.format(str(qad_utils.toDegrees(self.plugIn.lastReferenceRot))), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   self.plugIn.lastReferenceRot, \
                   "")               
      self.step = 4


   def waitForNewReferenceRot(self):
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT)
      
      keyWords = QadMsg.translate("Command_ROTATE", "Points")
      if self.plugIn.lastNewReferenceRot == 0:
         angle = self.plugIn.lastRot
      else:
         angle = self.plugIn.lastNewReferenceRot         
      prompt = QadMsg.translate("Command_ROTATE", "Specify new angle or [{0}] <{1}>: ").format(keyWords, str(qad_utils.toDegrees(angle)))                        
         
      englishKeyWords = "Points"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE | QadInputTypeEnum.KEYWORDS, \
                   angle, \
                   keyWords)
      self.step = 6
   

   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
            
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == 0: # inizio del comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selezione terminata
            self.step = 1
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di selezione entità                    
            return self.run(msgMapTool, msg)
      
      #=========================================================================
      # RUOTA OGGETTI
      elif self.step == 1:
         if self.SSGetClass.entitySet.count() == 0:
            return True # fine comando
         self.cacheEntitySet.appendEntitySet(self.SSGetClass.entitySet)

         # imposto il map tool
         self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify base point: "))
                  
         self.step = 2     
         return False
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO BASE (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

         self.basePt = QgsPointXY(value)

         self.getPointMapTool().basePt = self.basePt
         self.getPointMapTool().cacheEntitySet = self.cacheEntitySet
         # si appresta ad attendere l'angolo di rotazione                      
         self.waitForRotation()
         
         return False 
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER ANGOLO ROTAZIONE (da step = 2)
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ROTATE", "Copy") or value == "Copy":
               self.copyFeatures = True
               self.showMsg(QadMsg.translate("Command_ROTATE", "\nRotation of a copy of the selected objects."))
               # si appresta ad attendere l'angolo di rotazione               
               self.waitForRotation()                
            elif value == QadMsg.translate("Command_ROTATE", "Reference") or value == "Reference":
               # si appresta ad attendere l'angolo di riferimento                      
               self.waitForReferenceRot()
         elif type(value) == QgsPointXY or type(value) == float: # se é stato inserito l'angolo di rotazione
            if type(value) == QgsPointXY: # se é stato inserito l'angolo di rotazione con un punto
               angle = qad_utils.getAngleBy2Pts(self.basePt, value)
            else:
               angle = qad_utils.toRadians(value)
            self.plugIn.setLastRot(angle)

            self.RotateGeoms(angle)
            return True # fine comando
         
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMO PUNTO PER ANGOLO ROTAZIONE DI RIFERIMENTO (da step = 3)
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

         if type(value) == float: # se é stato inserito l'angolo di rotazione
            self.ReferenceAng = qad_utils.toRadians(value)
            self.getPointMapTool().ReferenceAng = self.ReferenceAng 
            # si appresta ad attendere il nuovo angolo                    
            self.waitForNewReferenceRot()

         elif type(value) == QgsPointXY: # se é stato inserito l'angolo di rotazione con un punto                                 
            self.Pt1ReferenceAng = QgsPointXY(value)
            self.getPointMapTool().Pt1ReferenceAng = self.Pt1ReferenceAng 
            # imposto il map tool
            self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG)
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify second point: "))
            self.step = 5           
            
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER ANGOLO ROTAZIONE DI RIFERIMENTO (da step = 4)
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

         angle = qad_utils.getAngleBy2Pts(self.Pt1ReferenceAng, value)
         self.ReferenceAng = angle
         self.getPointMapTool().ReferenceAng = self.ReferenceAng 
         # si appresta ad attendere il nuovo angolo                    
         self.waitForNewReferenceRot()
            
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER NUOVO ANGOLO ROTAZIONE (da step = 4 e 5)
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ROTATE", "Points") or value == "Points":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_NEW_ROTATION_PT)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify first point: "))
               self.step = 7
         elif type(value) == QgsPointXY or type(value) == float: # se é stato inserito l'angolo di rotazione
            if type(value) == QgsPointXY: # se é stato inserito l'angolo di rotazione con un punto                        
               angle = qad_utils.getAngleBy2Pts(self.basePt, value)
            else:
               angle = qad_utils.toRadians(value)
            
            angle = angle - self.ReferenceAng
            self.plugIn.setLastRot(angle)
            self.RotateGeoms(angle)
            return True # fine comando

         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMO PUNTO PER NUOVO ANGOLO ROTAZIONE (da step = 6)
      elif self.step == 7: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
      
         self.Pt1NewAng = value
         # imposto il map tool
         self.getPointMapTool().Pt1NewAng = self.Pt1NewAng
         self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT)
         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_ROTATE", "Specify second point: "))
         self.step = 8
            
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER NUOVO ANGOLO ROTAZIONE (da step = 7)
      elif self.step == 8: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
               
         angle = qad_utils.getAngleBy2Pts(self.Pt1NewAng, value)
         
         angle = angle - self.ReferenceAng
         self.plugIn.setLastRot(angle)
         self.RotateGeoms(angle)
         return True # fine comando


# Classe che gestisce il comando ROTATE per i grip
class QadGRIPROTATECommandClass(QadCommandClass):


   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadGRIPROTATECommandClass(self.plugIn)

   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.cacheEntitySet = QadCacheEntitySet()
      self.basePt = QgsPointXY()
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0
      self.Pt1ReferenceAng = None
      self.ReferenceAng = 0

   
   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_rotate_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   #============================================================================
   # setSelectedEntityGripPoints
   #============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # lista delle entityGripPoint con dei grip point selezionati
      self.cacheEntitySet.clear()

      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         self.cacheEntitySet.appendEntity(entityGripPoints.entity)

      self.getPointMapTool().cacheEntitySet = self.cacheEntitySet


   #============================================================================
   # rotate
   #============================================================================
   def rotate(self, entity, basePt, angle, rotFldName):
      # entity = entità da ruotare
      # basePt = punto base
      # angle = angolo di rotazione in gradi
      # verifico se l'entità appartiene ad uno stile di quotatura
      if entity.whatIs() == "ENTITY":
         # ruoto la geometria dell'entità
         qadGeom = entity.getQadGeom().copy() # la copio
         qadGeom.rotate(basePt, angle)
         f = entity.getFeature()
         f.setGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer))

         if len(entity.rotFldName) > 0 is not None:
            rotValue = f.attribute(entity.rotFldName)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # la rotazione é in gradi nel campo della feature
            rotValue = rotValue + angle
            f.setAttribute(entity.rotFldName, qad_utils.toDegrees(qad_utils.normalizeAngle(rotValue)))               

         if self.copyEntities == False:
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, entity.layer, f, False, False) == False:
               return False
         else:
            # plugIn, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, entity.layer, f, None, False, False) == False:
               return False
               
      elif entity.whatIs() == "DIMENTITY":
         # stiro la quota
         if self.copyEntities == False:
            if entity.deleteToLayers(self.plugIn) == False:
               return False           
         newDimEntity = QadDimEntity(entity) # la copio
         newDimEntity.rotate(basePt, angle)
         if newDimEntity.addToLayers(self.plugIn) == False:
            return False             

      return True


   #============================================================================
   # rotateFeatures
   #============================================================================
   def rotateFeatures(self, angle):
      self.plugIn.beginEditCommand("Feature rotated", self.cacheEntitySet.getLayerList())

      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)         
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if self.rotate(entity, self.basePt, angle) == False:  
            self.plugIn.destroyEditCommand()
            return
      
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1
   
                           
   #============================================================================
   # waitForRotatePoint
   #============================================================================
   def waitForRotatePoint(self):
      self.step = 1
      self.plugIn.setLastPoint(self.basePt)
      # imposto il map tool
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT)
      
      keyWords = QadMsg.translate("Command_GRIPROTATE", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "Reference") + "/" + \
                 QadMsg.translate("Command_GRIPROTATE", "eXit")

      prompt = QadMsg.translate("Command_GRIPROTATE", "Specify rotation angle or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" + "Reference" + "/" + "eXit"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto, un numero reale o enter o una parola chiave
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)      


   #============================================================================
   # waitForBasePt
   #============================================================================
   def waitForBasePt(self):
      self.step = 2   
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT)

      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_GRIPROTATE", "Specify base point: "))


   def waitForReferenceRot(self):
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_ANG)
      
      msg = QadMsg.translate("Command_GRIPROTATE", "Specify reference angle <{0}>: ")
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(msg.format(str(qad_utils.toDegrees(self.plugIn.lastReferenceRot))), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   self.plugIn.lastReferenceRot, \
                   "")               
      self.step = 3


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
     
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == 0: # inizio del comando
         if self.cacheEntitySet.isEmpty(): # non ci sono oggetti da ruotare
            return True
         self.showMsg(QadMsg.translate("Command_GRIPROTATE", "\n** ROTATE **\n"))
         # si appresta ad attendere un punto di rotazione
         self.waitForRotatePoint()
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DI UN PUNTO DI ROTAZIONE
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
            if value == QadMsg.translate("Command_GRIPROTATE", "Base point") or value == "Base point":
               # si appresta ad attendere il punto base
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIPROTATE", "Copy") or value == "Copy":
               # Copia entità lasciando inalterate le originali
               self.copyEntities = True                     
               # si appresta ad attendere un punto di rotazione
               self.waitForRotatePoint()
            elif value == QadMsg.translate("Command_GRIPROTATE", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
               # si appresta ad attendere un punto di rotazione
               self.waitForRotatePoint()
            elif value == QadMsg.translate("Command_GRIPROTATE", "Reference") or value == "Reference":
               # si appresta ad attendere l'angolo di riferimento                      
               self.waitForReferenceRot()
            elif value == QadMsg.translate("Command_GRIPROTATE", "eXit") or value == "eXit":
               return True # fine comando
         elif type(value) == QgsPointXY or type(value) == float: # se é stato inserito l'angolo di rotazione
            if type(value) == QgsPointXY: # se é stato inserito l'angolo di rotazione con un punto
               angle = qad_utils.getAngleBy2Pts(self.basePt, value)
            else:
               angle = qad_utils.toRadians(value)
            angle = angle - self.ReferenceAng
            self.plugIn.setLastRot(angle)

            if ctrlKey:
               self.copyEntities = True
            
            self.rotateFeatures(angle)

            if self.copyEntities == False:
               return True

            # si appresta ad attendere un punto di rotazione
            self.waitForRotatePoint()
          
         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # fine comando
                                          
         return False 

              
      #=========================================================================
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
            
         # si appresta ad attendere un punto di rotazione
         self.waitForRotatePoint()

         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMO PUNTO PER ANGOLO ROTAZIONE DI RIFERIMENTO (da step = 1)
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

         if type(value) == float: # se é stato inserito l'angolo di rotazione
            self.ReferenceAng = qad_utils.toRadians(value)
            self.getPointMapTool().ReferenceAng = self.ReferenceAng 
            # si appresta ad attendere un punto di rotazione
            self.waitForRotatePoint()

         elif type(value) == QgsPointXY: # se é stato inserito l'angolo di rotazione con un punto                                 
            self.Pt1ReferenceAng = QgsPointXY(value)
            self.getPointMapTool().Pt1ReferenceAng = self.Pt1ReferenceAng 
            # imposto il map tool
            self.getPointMapTool().setMode(Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG)
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_GRIPROTATE", "Specify second point: "))
            self.step = 4
            
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER NUOVO ANGOLO ROTAZIONE (da step = 3)
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

         if type(value) == QgsPointXY or type(value) == float: # se é stato inserito l'angolo di rotazione
            if type(value) == QgsPointXY: # se é stato inserito l'angolo di rotazione con un punto                        
               self.ReferenceAng = qad_utils.getAngleBy2Pts(self.Pt1ReferenceAng, value)
            else:
               self.ReferenceAng = qad_utils.toRadians(value)
            self.getPointMapTool().ReferenceAng = self.ReferenceAng 
            
         # si appresta ad attendere un punto di rotazione
         self.waitForRotatePoint()
         
         return False

