# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando da inserire in altri comandi per la selezione di una feature
 
                              -------------------
        begin                : 2013-09-18
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
from qgis.core import QgsWkbTypes, QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntity
from ..qad_getpoint import QadGetPointSelectionModeEnum
from .. import qad_utils
from ..qad_dim import QadDimStyles
from ..qad_variables import QadVariables


# ===============================================================================
# QadEntSelClass
# ===============================================================================
class QadEntSelClass(QadCommandClass):
   """
      Questa classe seleziona un'entità. Non è in grado di selezionare una quotatura ma solo un componente di una quotatura.
   """

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadEntSelClass(self.plugIn)
      
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.point = None
      # opzioni per limitare gli oggetti da selezionare
      self.onlyEditableLayers = False     
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.checkDimLayers = True
      self.selDimEntity = False # per restituire o meno un oggetto QadDimEntity
      self.msg = QadMsg.translate("QAD", "Select object: ")
      self.deselectOnFinish = False
      self.canceledByUsr = False # diventa true se l'utente non vuole scegliere niente (es. se usato il tasto destro del mouse)
      
   def __del__(self):
      QadCommandClass.__del__(self)
      if self.deselectOnFinish:
         self.entity.deselectOnLayer()


   # ============================================================================
   # setEntity
   # ============================================================================
   def setEntity(self, layer, fid):
      del self.entity
      if self.selDimEntity: # se è possibile restituire un oggetto QadDimEntity
         # verifico se l'entità appartiene ad uno stile di quotatura
         self.entity = QadDimStyles.getDimEntity(layer, fid)
         if self.entity is None: # se non è una quota
            self.entity = QadEntity()
            self.entity.set(layer, fid)
      else:
         self.entity = QadEntity()
         self.entity.set(layer, fid)
      
      self.entity.selectOnLayer()


   # ============================================================================
   # getLayersToCheck
   # ============================================================================
   def getLayersToCheck(self):
      layerList = []
      for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
         # considero solo i layer vettoriali che sono filtrati per tipo
         if ((layer.geometryType() == QgsWkbTypes.PointGeometry and self.checkPointLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.LineGeometry and self.checkLineLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.PolygonGeometry and self.checkPolygonLayer == True)) and \
             (self.onlyEditableLayers == False or layer.isEditable()):
            # se devo includere i layers delle quotature
            if self.checkDimLayers == True or \
               len(QadDimStyles.getDimListByLayer(layer)) == 0:
               layerList.append(layer)
         
      return layerList

            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      # =========================================================================
      # RICHIESTA PUNTO o ENTITA'
      if self.step == 0: # inizio del comando
         # imposto il map tool
         self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         # imposto i layer da controllare sul maptool
         self.getPointMapTool().layersToCheck = self.getLayersToCheck()
                  
         keyWords = QadMsg.translate("Command_ENTSEL", "Last")
                  
         englishKeyWords = "Last"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o enter o una parola chiave         
         # msg, inputType, default, keyWords, nessun controllo
         self.waitFor(self.msg, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)
         
         self.step = 1
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO o ENTITA'
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         entity = None
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.canceledByUsr = True
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
               
            value = self.getPointMapTool().point
            if self.getPointMapTool().entity.isInitialized():
               entity = self.getPointMapTool().entity               
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None:
            self.canceledByUsr = True
            return True # fine comando
         
         if type(value) == unicode:
            if value == QadMsg.translate("Command_ENTSEL", "Last") or value == "Last":
               # Seleziona l'ultima entità inserita
               lastEnt = self.plugIn.getLastEntity()
               if lastEnt is not None:
                  # controllo sul layer
                  if self.onlyEditableLayers == False or lastEnt.layer.isEditable() == True:
                     # controllo sul tipo
                     if (self.checkPointLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.PointGeometry) or \
                        (self.checkLineLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.LineGeometry) or \
                        (self.checkPolygonLayer == True and lastEnt.layer.geometryType() == QgsWkbTypes.PolygonGeometry):
                        # controllo su layer delle quotature
                        if self.checkDimLayers == True or QadDimStyles.isDimEntity(lastEnt) == False:
                           self.setEntity(lastEnt.layer, lastEnt.featureId)
         elif type(value) == QgsPointXY:
            if entity is None:
               # cerco se ci sono entità nel punto indicato
               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value),
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            self.getLayersToCheck())
               if result is not None:
                  feature = result[0]
                  layer = result[1]
                  self.setEntity(layer, feature.id())               
            else:
               self.setEntity(entity.layer, entity.featureId)

            self.point = value
                                   
         if self.deselectOnFinish:
            self.entity.deselectOnLayer()

         return True # fine comando
