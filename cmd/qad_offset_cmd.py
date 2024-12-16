# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando OFFSET per fare l'offset di un oggetto
 
                              -------------------
        begin                : 2013-10-04
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
from qgis.core import QgsPointXY, QgsWkbTypes, QgsGeometry, QgsFeature
from qgis.PyQt.QtGui import QIcon


from .qad_offset_maptool import Qad_offset_maptool, Qad_offset_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum   
from ..qad_entity import QadEntity
from ..qad_variables import QadVariables
from .. import qad_utils
from .. import qad_layer
from ..qad_rubberband import createRubberBand
from ..qad_offset_fun import offsetPolyline, offsetQGSGeom
from ..qad_geom_relations import getQadGeomClosestPart
from ..qad_multi_geom import getQadGeomAt, fromQgsGeomToQadGeom


# Classe che gestisce il comando OFFSET
class QadOFFSETCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadOFFSETCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "OFFSET")

   def getEnglishName(self):
      return "OFFSET"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runOFFSETCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/offset.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_OFFSET", "Creates concentric circles, parallel lines, and parallel curves.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.subGeom = None
      self.partNum = None
      self.offset = QadVariables.get(QadMsg.translate("Environment variables", "OFFSETDIST"))
      self.lastOffSetOnLeftSide = 0
      self.lastOffSetOnRightSide = 0
      self.firstPt = QgsPointXY()
      self.eraseEntity = False
      self.multi = False
      self.OnlySegment = False
      self.gapType = QadVariables.get(QadMsg.translate("Environment variables", "OFFSETGAPTYPE"))
      
      self.featureCache = [] # lista di (layer, feature)
      self.undoFeatureCacheIndexes = [] # posizioni in featureCache dei punti di undo
      self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
      self.rubberBandPolygon = createRubberBand(self.plugIn.canvas, QgsWkbTypes.PolygonGeometry)

   def __del__(self):
      QadCommandClass.__del__(self)
      self.rubberBand.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBand)
      self.rubberBandPolygon.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBandPolygon)
      
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_offset_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None

   # ============================================================================
   # addFeatureCache
   # ============================================================================
   def addFeatureCache(self, newPt):
      featureCacheLen = len(self.featureCache)
      layer = self.entity.layer
      f = self.entity.getFeature()

#       # la funzione ritorna una lista con 
#       # (<minima distanza>
#       # <punto più vicino>
#       # <indice della geometria più vicina>
#       # <indice della sotto-geometria più vicina>
#       # <indice della parte della sotto-geometria più vicina>
#       # <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
#       # -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
#       # -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
#       result = getQadGeomClosestPart(self.subGeom, newPt)
#       leftOf = result[5]
# 
#       if self.offset < 0:
#          offsetDistance = result[0] # minima distanza
#       else:        
#          offsetDistance = self.offset                     
#          if self.multi == True:
#             if leftOf < 0: # a sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
#                offsetDistance = offsetDistance + self.lastOffSetOnLeftSide
#                self.lastOffSetOnLeftSide = offsetDistance
#                self.getPointMapTool().lastOffSetOnLeftSide = self.lastOffSetOnLeftSide
#             else: # alla destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
#                offsetDistance = offsetDistance + self.lastOffSetOnRightSide
#                self.lastOffSetOnRightSide = offsetDistance            
#                self.getPointMapTool().lastOffSetOnRightSide = self.lastOffSetOnRightSide
# 
#       lines = offsetPolyline(self.subGeom, \
#                              offsetDistance, \
#                              "left" if leftOf < 0 else "right", \
#                              self.gapType)
#       added = False
#       for line in lines:
#          pts = line.asPolyline()
#          if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
#             if line.isClosed(): # se é una linea chiusa
#                offsetGeom = QgsGeometry.fromPolygonXY([pts])
#             else:
#                offsetGeom = QgsGeometry.fromPolylineXY(pts)
#          else:
#             offsetGeom = QgsGeometry.fromPolylineXY(pts)
# 
#          if offsetGeom.type() == QgsWkbTypes.LineGeometry or offsetGeom.type() == QgsWkbTypes.PolygonGeometry:           
#             offsetFeature = QgsFeature(f)
#             # trasformo la geometria nel crs del layer
#             offsetFeature.setGeometry(self.mapToLayerCoordinates(layer, offsetGeom))
#             self.featureCache.append([layer, offsetFeature])
#             self.addFeatureToRubberBand(layer, offsetFeature)            
#             added = True           
# 
#       if added:      
#          self.undoFeatureCacheIndexes.append(featureCacheLen)

      offsetDistance = None
      if self.offset > 0:
         offsetDistance = self.offset                     
         if self.multi == True:
            # la funzione ritorna una lista con 
            # (<minima distanza>
            # <punto più vicino>
            # <indice della geometria più vicina>
            # <indice della sotto-geometria più vicina>
            # <indice della parte della sotto-geometria più vicina>
            # <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
            # -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
            # -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
            dummy = getQadGeomClosestPart(self.subGeom, newPt)
            leftOf = dummy[5]         
                 
            if leftOf < 0: # a sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)            
               offsetDistance = self.offset + self.lastOffSetOnLeftSide
               self.lastOffSetOnLeftSide = offsetDistance
               self.getPointMapTool().lastOffSetOnLeftSide = self.lastOffSetOnLeftSide
            else: # alla destra
               offsetDistance = self.offset + self.lastOffSetOnRightSide         
               self.lastOffSetOnRightSide = offsetDistance            
               self.getPointMapTool().lastOffSetOnRightSide = self.lastOffSetOnRightSide

      # se self.subGeom implementa il metodo isClosed
      closed = self.subGeom.isClosed() if hasattr(self.subGeom, "isClosed") and callable(getattr(self.subGeom, "isClosed")) else False

      if layer.geometryType() == QgsWkbTypes.PolygonGeometry or closed == True:
         qgsGeom = QgsGeometry.fromPolygonXY([self.subGeom.asPolyline()])
      else:
         qgsGeom = QgsGeometry.fromPolylineXY(self.subGeom.asPolyline())

      offsetQGSGeomList = offsetQGSGeom(qgsGeom, \
                                        newPt, \
                                        self.gapType, \
                                        offsetDistance)

      added = False
      for g in offsetQGSGeomList:
         # converto in QAD geometry per riconoscere le curve
         g = fromQgsGeomToQadGeom(g).asGeom(layer.wkbType())        
         
         if g.type() == QgsWkbTypes.LineGeometry or g.type() == QgsWkbTypes.PolygonGeometry:           
            offsetFeature = QgsFeature(f)
            # trasformo la geometria nel crs del layer
            offsetFeature.setGeometry(self.mapToLayerCoordinates(layer, g))
            self.featureCache.append([layer, offsetFeature])
            self.addFeatureToRubberBand(layer, offsetFeature)            
            added = True           

      if added:      
         self.undoFeatureCacheIndexes.append(featureCacheLen)


   # ============================================================================
   # undoGeomsInCache
   # ============================================================================
   def undoGeomsInCache(self):
      tot = len(self.featureCache)
      if tot > 0:
         iEnd = self.undoFeatureCacheIndexes[-1]
         i = tot - 1
         
         del self.undoFeatureCacheIndexes[-1] # cancello ultimo undo
         while i >= iEnd:
            del self.featureCache[-1] # cancello feature
            i = i - 1
         self.refreshRubberBand()

            
   # ============================================================================
   # addFeatureToRubberBand
   # ============================================================================
   def addFeatureToRubberBand(self, layer, feature):
      if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
         if feature.geometry().type() == QgsWkbTypes.PolygonGeometry:
            self.rubberBandPolygon.addGeometry(feature.geometry(), layer)
         else:
            self.rubberBand.addGeometry(feature.geometry(), layer)
      else:
         self.rubberBand.addGeometry(feature.geometry(), layer)
      
      
   # ============================================================================
   # refreshRubberBand
   # ============================================================================
   def refreshRubberBand(self):
      self.rubberBand.reset(QgsWkbTypes.LineGeometry)
      self.rubberBandPolygon.reset(QgsWkbTypes.PolygonGeometry)
      for f in self.featureCache:
         layer = f[0]
         feature = f[1]
         if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            if feature.geometry().type() == QgsWkbTypes.PolygonGeometry:
               self.rubberBandPolygon.addGeometry(feature.geometry(), layer)
            else:
               self.rubberBand.addGeometry(feature.geometry(), layer)            
         else:
            self.rubberBand.addGeometry(feature.geometry(), layer)            


   # ============================================================================
   # addToLayer
   # ============================================================================
   def addToLayer(self, currLayer):
      featuresLayers = [] # lista di (layer, features)
      
      for f in self.featureCache:
         layer = f[0]
         feature = f[1]
         found = False
         for featuresLayer in featuresLayers:
            if featuresLayer[0].id() == layer.id():
               found = True
               featuresLayer[1].append(feature)
               break
         # se non c'era ancora il layer
         if not found:
            featuresLayers.append([layer, [feature]])

      layerList = []
      for featuresLayer in featuresLayers:
         layerList.append(featuresLayer[0])

      PointTempLayer = None
      LineTempLayer = None
      PolygonTempLayer = None
      self.plugIn.beginEditCommand("Feature offseted", layerList)

      for featuresLayer in featuresLayers:
         # filtro le features per tipo
         pointGeoms, lineGeoms, polygonGeoms = qad_utils.filterFeaturesByType(featuresLayer[1], \
                                                                              currLayer.geometryType())
         # aggiungo le features con geometria del tipo corretto
         if currLayer.geometryType() == QgsWkbTypes.LineGeometry:
            polygonToLines = []
            # Riduco le geometrie in linee
            for g in polygonGeoms:
               lines = qad_utils.asPointOrPolyline(g)
               for l in lines:
                  if l.type() == QgsWkbTypes.LineGeometry:
                      polygonToLines.append(l)
            # plugIn, layer, geoms, coordTransform , refresh, check_validity
            if qad_layer.addGeomsToLayer(self.plugIn, currLayer, polygonToLines, None, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
               
            del polygonGeoms[:] # svuoto la lista

         # plugIn, layer, features, coordTransform, refresh, check_validity
         if qad_layer.addFeaturesToLayer(self.plugIn, currLayer, featuresLayer[1], None, False, False) == False:
            self.plugIn.destroyEditCommand()
            return

         if pointGeoms is not None and len(pointGeoms) > 0 and PointTempLayer is None:
            PointTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PointGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature offseted", PointTempLayer)
         
         if lineGeoms is not None and len(lineGeoms) > 0 and LineTempLayer is None:
            LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature offseted", LineTempLayer)
            
         if polygonGeoms is not None and len(polygonGeoms) > 0 and PolygonTempLayer is None:
            PolygonTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PolygonGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature offseted", PolygonTempLayer)
         
         # aggiungo gli scarti nei layer temporanei di QAD
         # trasformo la geometria in quella dei layer temporanei 
         # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
         if qad_layer.addGeometriesToQADTempLayers(self.plugIn, pointGeoms, lineGeoms, polygonGeoms, \
                                                 featuresLayer[0].crs(), False) == False:
            self.plugIn.destroyEditCommand()
            return

      self.plugIn.endEditCommand()

 
   # ============================================================================
   # waitForDistance
   # ============================================================================
   def waitForDistance(self):      
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.ASK_FOR_FIRST_OFFSET_PT)
      self.getPointMapTool().gapType = self.gapType                        

      keyWords = QadMsg.translate("Command_OFFSET", "Through") + "/" + \
                 QadMsg.translate("Command_OFFSET", "Erase")                
      if self.offset < 0:
         default = QadMsg.translate("Command_OFFSET", "Through")
      else:
         default = self.offset
      prompt = QadMsg.translate("Command_OFFSET", "Specify the offset distance or [{0}] <{1}>: ").format(keyWords, unicode(default))

      englishKeyWords = "Through" + "/" + "Erase"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave o un numero reale     
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)      
      self.step = 1      
   
   # ============================================================================
   # waitForObjectSel
   # ============================================================================
   def waitForObjectSel(self):      
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.ASK_FOR_ENTITY_SELECTION)                                      
      self.lastOffSetOnLeftSide = 0
      self.getPointMapTool().lastOffSetOnLeftSide = self.lastOffSetOnLeftSide
      self.lastOffSetOnRightSide = 0
      self.getPointMapTool().lastOffSetOnRightSide = self.lastOffSetOnRightSide
      
      # "Esci" "ANnulla"      
      keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                 QadMsg.translate("Command_OFFSET", "Undo")
      default = QadMsg.translate("Command_OFFSET", "Exit")
      prompt = QadMsg.translate("Command_OFFSET", "Select object to offset or [{0}] <{1}>: ").format(keyWords, default)
      
      englishKeyWords = "Exit" + "/" + "Undo"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NONE)      
      self.step = 2      
        
   # ============================================================================
   # waitForSidePt
   # ============================================================================
   def waitForSidePt(self):      
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.OFFSET_KNOWN_ASK_FOR_SIDE_PT)                                

      if self.multi == False:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Multiple") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "Exit")        
         default = QadMsg.translate("Command_OFFSET", "Exit")
         englishKeyWords = "Exit" + "/" + "Multiple" + "/" + "Undo"
      else:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "next object")
         default = None
         englishKeyWords = "Exit" + "/" + "Undo"

      if self.OnlySegment == False:
         keyWords = keyWords + "/" + \
                    QadMsg.translate("Command_OFFSET", "Segment")
         englishKeyWords = englishKeyWords + "/" + "Segment"

      prompt = QadMsg.translate("Command_OFFSET", "Specify point on side to offset or [{0}] <{1}>: ").format(keyWords, default)

      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, valore nullo non permesso
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NONE)      
      self.step = 3
        
   # ============================================================================
   # waitForPassagePt
   # ============================================================================
   def waitForPassagePt(self):
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.ASK_FOR_PASSAGE_PT)                                

      if self.multi == False:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Multiple") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "Exit")
         default = QadMsg.translate("Command_OFFSET", "Exit")
         englishKeyWords = "Exit" + "/" + "Multiple" + "/" + "Undo"
      else:
         keyWords = QadMsg.translate("Command_OFFSET", "Exit") + "/" + \
                    QadMsg.translate("Command_OFFSET", "Undo")
         defaultMsg = QadMsg.translate("Command_OFFSET", "next object")
         default = None
         englishKeyWords = "Exit" + "/" + "Undo"

      if self.OnlySegment == False:
         keyWords = keyWords + "/" + \
                    QadMsg.translate("Command_OFFSET", "Segment")
         englishKeyWords = englishKeyWords + "/" + "Segment"

      prompt = QadMsg.translate("Command_OFFSET", "Specify through point or [{0}] <{1}>: ").format(keyWords, defaultMsg)

      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, valore nullo non permesso
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   default, \
                   keyWords, QadInputModeEnum.NONE)      
      self.step = 4

   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      # il layer corrente deve essere editabile e di tipo linea o poligono
      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
      if currLayer is None:
         self.showErr(errMsg)
         return True # fine comando

      # =========================================================================
      # RICHIESTA DISTANZA DI OFFSET
      if self.step == 0: # inizio del comando
         CurrSettingsMsg = QadMsg.translate("QAD", "\nCurrent settings: ")
         CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", "OFFSETGAPTYPE = ") + str(self.gapType)                        
         if self.gapType == 0:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", " (extends the segments)")
         elif self.gapType == 1:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", " (fillets the segments)")
         elif self.gapType == 2:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_OFFSET", " (chamfers the segments)")
         
         self.showMsg(CurrSettingsMsg)         

         self.waitForDistance()
            
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DISTANZA DI OFFSET (da step = 0)
      elif self.step == 1: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.offset < 0:
                     value = QadMsg.translate("Command_OFFSET", "Through")
                  else:
                     value = self.offset
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg
         
         if type(value) == unicode:
            if value == QadMsg.translate("Command_OFFSET", "Through") or value == "Through":
               self.offset = -1
               self.getPointMapTool().offset = self.offset
               QadVariables.set(QadMsg.translate("Environment variables", "OFFSETDIST"), self.offset)
               QadVariables.save()               
               # si appresta ad attendere la selezione di un oggetto
               self.waitForObjectSel()
            elif value == QadMsg.translate("Command_OFFSET", "Erase") or value == "Erase":
               keyWords = QadMsg.translate("QAD", "Yes") + "/" + \
                          QadMsg.translate("QAD", "No")
              
               if self.eraseEntity == True:
                  default = QadMsg.translate("QAD", "Yes")
               else: 
                  default = QadMsg.translate("QAD", "No")
               prompt = QadMsg.translate("Command_OFFSET", "Erase source object after offsetting ? [{0}] <{1}>: ").format(keyWords, default)
                   
               englishKeyWords = "Yes" + "/" + "No"
               keyWords += "_" + englishKeyWords
               # si appresta ad attendere enter o una parola chiave
               # msg, inputType, default, keyWords, nessun controllo
               self.waitFor(prompt, \
                            QadInputTypeEnum.KEYWORDS, \
                            default, \
                            keyWords, QadInputModeEnum.NONE)
               self.step = 5
            elif value == QadMsg.translate("Command_OFFSET", "Multiple") or value == "Multiple":
               self.multi = True
               self.waitForBasePt()                         
         elif type(value) == QgsPointXY: # se é stato inserito il primo punto per il calcolo della distanza
            self.firstPt.set(value.x(), value.y())
            # imposto il map tool
            self.getPointMapTool().firstPt = self.firstPt           
            self.getPointMapTool().setMode(Qad_offset_maptool_ModeEnum.FIRST_OFFSET_PT_KNOWN_ASK_FOR_SECOND_PT)
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_OFFSET", "Specify second point: "))
            self.step = 6
         elif type(value) == float:
            self.offset = value
            self.getPointMapTool().offset = self.offset
            QadVariables.set(QadMsg.translate("Environment variables", "OFFSETDIST"), self.offset)
            QadVariables.save()
            # si appresta ad attendere la selezione di un oggetto
            self.waitForObjectSel()
         
         return False 

      # =========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN OGGETTO
      elif self.step == 2:
         entity = None
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = QadMsg.translate("Command_OFFSET", "Exit")
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               entity = self.getPointMapTool().entity
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg
         
         if type(value) == unicode:
            if value == QadMsg.translate("Command_OFFSET", "Exit") or value == "Exit":
               self.addToLayer(currLayer)
               return True
            elif value == QadMsg.translate("Command_OFFSET", "Undo") or value == "Undo":
               self.undoGeomsInCache()
               # si appresta ad attendere la selezione di un oggetto
               self.waitForObjectSel()
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            if entity is not None and entity.isInitialized(): # se é stata selezionata una entità
               self.entity.set(entity)
               self.getPointMapTool().layer = self.entity.layer
               
               qadGeom = self.entity.getQadGeom()
               
               # la funzione ritorna una lista con 
               # (<minima distanza>
               # <punto più vicino>
               # <indice della geometria più vicina>
               # <indice della sotto-geometria più vicina>
               # <indice della parte della sotto-geometria più vicina>
               # <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
               result = getQadGeomClosestPart(qadGeom, value)
               self.atGeom = result[2]
               self.atSubGeom = result[3]
               self.subGeom = getQadGeomAt(qadGeom, self.atGeom, self.atSubGeom)
               self.partNum = result[4]
               
               self.getPointMapTool().subGeom = self.subGeom
               if self.offset < 0: # richiesta di punto di passaggio
                  self.waitForPassagePt()
               else:  # richiesta la parte dell'oggetto
                  self.waitForSidePt()
            else:
               # si appresta ad attendere la selezione di un oggetto
               self.waitForObjectSel()

         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI UN PUNTO PER STABILIRE LA PARTE DI OFFSET  (da step = 2)
      elif self.step == 3:
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.multi == False: # default = esci                     
                     self.addToLayer(currLayer)
                     return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None: # oggetto successivo
            # si appresta ad attendere la selezione di un oggetto
            self.waitForObjectSel()
         else:
            if type(value) == unicode:
               if value == QadMsg.translate("Command_OFFSET", "Exit") or value == "Exit":
                  self.addToLayer(currLayer)
                  return True # fine comando
               elif value == QadMsg.translate("Command_OFFSET", "Multiple") or value == "Multiple":
                  self.multi = True
                  self.waitForSidePt()               
               elif value == QadMsg.translate("Command_OFFSET", "Undo") or value == "Undo":
                  self.undoGeomsInCache()               
                  # si appresta ad attendere la selezione di un oggetto
                  self.waitForObjectSel()
               elif value == QadMsg.translate("Command_OFFSET", "Segment") or value == "Segment":
                  self.OnlySegment = True
                  if self.subGeom.whatIs() == "POLYLINE":
                     self.subGeom = self.subGeom.getLinearObjectAt(self.partNum)
                     self.getPointMapTool().subGeom = self.subGeom
                  
                  self.waitForSidePt()                  
            elif type(value) == QgsPointXY: # se é stato selezionato un punto            
               self.addFeatureCache(value) 
               if self.multi == False:
                  # si appresta ad attendere la selezione di un oggetto
                  self.waitForObjectSel()
               else:
                  # richiesta la parte dell'oggetto
                  self.waitForSidePt()

         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI UN PUNTO DI PASSAGGIO DI OFFSET  (da step = 2)
      elif self.step == 4:
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.multi == False: # default = esci                     
                     self.addToLayer(currLayer)
                     return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None: # oggetto successivo
            # si appresta ad attendere la selezione di un oggetto
            self.waitForObjectSel()
         else:
            if type(value) == unicode:
               if value == QadMsg.translate("Command_OFFSET", "Exit") or value == "Exit":
                  self.addToLayer(currLayer)
                  return True # fine comando
               elif value == QadMsg.translate("Command_OFFSET", "Multiple") or value == "Multiple":
                  self.multi = True
                  self.waitForPassagePt()     
               elif value == QadMsg.translate("Command_OFFSET", "Undo") or value == "Undo":
                  self.undoGeomsInCache()               
                  # si appresta ad attendere la selezione di un oggetto
                  self.waitForObjectSel()
               elif value == QadMsg.translate("Command_OFFSET", "Segment") or value == "Segment":
                  self.OnlySegment = True
                  if self.subGeom.whatIs() == "POLYLINE":
                     self.subGeom = self.subGeom.getLinearObjectAt(self.partNum)
                     self.getPointMapTool().subGeom = self.subGeom
                  
                  self.waitForPassagePt()     
            elif type(value) == QgsPointXY: # se é stato selezionato un punto            
               self.addFeatureCache(value)       
               if self.multi == False:
                  # si appresta ad attendere la selezione di un oggetto
                  self.waitForObjectSel()
               else:
                  # richiesta di punto di passaggio
                  self.waitForPassagePt()

         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI CANCELLAZIONE OGGETTO SORGENTE (da step = 1)
      elif self.step == 5: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = QadMsg.translate("QAD", "No")   
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else: # il valore arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
               self.eraseEntity = True
               self.waitForDistance()
            elif value == QadMsg.translate("QAD", "No") or value == "No":
               self.eraseEntity = False
               self.waitForDistance()
         
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER LUNGHEZZA OFFSET (da step = 1)
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

         if type(value) == QgsPointXY: # se é stato selezionato un punto
            if value == self.firstPt:
               self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_OFFSET", "Specify second point: "))
               return False
                  
            self.offset = qad_utils.getDistance(self.firstPt, value)
            self.getPointMapTool().offset = self.offset
            QadVariables.set(QadMsg.translate("Environment variables", "OFFSETDIST"), self.offset)
            QadVariables.save()
            # si appresta ad attendere la selezione di un oggetto
            self.waitForObjectSel()

         return False
                  
               