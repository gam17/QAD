# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando MBUFFER per creare oggetti originati da buffer su altri oggetti
 
                              -------------------
        begin                : 2013-09-19
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


from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_mbuffer_maptool import Qad_mbuffer_maptool, Qad_mbuffer_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import *
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import *
from .. import qad_utils
from .. import qad_layer
from ..qad_dim import QadDimStyles
from ..qad_mbuffer_fun import buffer
from ..qad_multi_geom import fromQadGeomToQgsGeom


# Classe che gestisce il comando MBUFFER
class QadMBUFFERCommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadMBUFFERCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "MBUFFER")

   def getEnglishName(self):
      return "MBUFFER"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMBUFFERCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/mbuffer.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_MBUFFER", "Creates polygons by buffering selected objects.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare un buffer
      # che non verrà salvato su un layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None      
      self.SSGetClass = QadSSGetClass(plugIn)
      self.entitySet = QadEntitySet()
      self.width = 0
      self.segments = self.plugIn.segments # il numero di segmenti per l'approssimazione delle curve

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_mbuffer_maptool(self.plugIn)
               self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 0: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

   
   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PointMapTool is not None:
         self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)


   def AddGeoms(self, currLayer):
      bufferGeoms = []
            
      for layerEntitySet in self.entitySet.layerEntitySetList:
         entityIterator = QadLayerEntitySetIterator(layerEntitySet)
         for entity in entityIterator:
            bufferedQadGeom = buffer(entity.getQadGeom(), self.width)
            if bufferedQadGeom is not None:
               # trasformo la geometria nel crs del layer
               bufferGeoms.append(fromQadGeomToQgsGeom(bufferedQadGeom, currLayer))

      self.plugIn.beginEditCommand("Feature buffered", currLayer)
      
      # filtro le features per tipo
      pointGeoms, lineGeoms, polygonGeoms = qad_utils.filterGeomsByType(bufferGeoms, \
                                                                        currLayer.geometryType())
      # aggiungo le geometrie del tipo corretto
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

      # plugIn, layer, geoms, coordTransform , refresh, check_validity
      if qad_layer.addGeomsToLayer(self.plugIn, currLayer, bufferGeoms, None, False, False) == False:  
         self.plugIn.destroyEditCommand()
         return

      if pointGeoms is not None and len(pointGeoms) > 0:
         PointTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PointGeometry)
         self.plugIn.addLayerToLastEditCommand("Feature buffered", PointTempLayer)
      
      if lineGeoms is not None and len(lineGeoms) > 0:
         LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
         self.plugIn.addLayerToLastEditCommand("Feature buffered", LineTempLayer)
         
      if polygonGeoms is not None and len(polygonGeoms) > 0:
         PolygonTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.PolygonGeometry)
         self.plugIn.addLayerToLastEditCommand("Feature buffered", PolygonTempLayer)

      # aggiungo gli scarti nei layer temporanei di QAD
      # trasformo la geometria in quella dei layer temporanei 
      # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
      if qad_layer.addGeometriesToQADTempLayers(self.plugIn, pointGeoms, lineGeoms, polygonGeoms, \
                                                currLayer.crs(), False) == False:
         self.plugIn.destroyEditCommand()
         return

      self.plugIn.endEditCommand()


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      currLayer = None
      if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
         # il layer corrente deve essere editabile e di tipo linea o poligono
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
         if currLayer is None:
            self.showErr(errMsg)
            return True # fine comando
         
         # il layer corrente non deve appartenere a quotature
         dimStyleList = QadDimStyles.getDimListByLayer(currLayer)
         if len(dimStyleList) > 0:
            dimStyleNames = ""
            for i in range(0, len(dimStyleList), 1):
               if i > 0:
                  dimStyleNames += ", "
               dimStyleNames += dimStyleList[i].name
            errMsg = QadMsg.translate("QAD", "\nCurrent layer is a layer referenced to {0} dimension style and it is not valid.\n")                        
            self.showErr(errMsg.format(dimStyleNames))
            return True # fine comando
            
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == 0: # inizio del comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selezione terminata
            self.step = 1
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può  essere variato dal maptool di selezione entità                     
            return self.run(msgMapTool, msg)
      
      #=========================================================================
      # BUFFER OGGETTI
      elif self.step == 1:
         self.entitySet.set(self.SSGetClass.entitySet)
         
         if self.entitySet.count() == 0:
            return True # fine comando

         # imposto il map tool
         self.getPointMapTool().setMode(Qad_mbuffer_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
         if currLayer is not None:
            self.getPointMapTool().geomType = QgsWkbTypes.LineGeometry if currLayer.geometryType() == QgsWkbTypes.LineGeometry else QgsWkbTypes.PolygonGeometry                          
        
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori positivi
         msg = QadMsg.translate("Command_MBUFFER", "Specify the buffer length <{0}>: ")
         self.waitFor(msg.format(str(self.plugIn.lastRadius)), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      self.plugIn.lastRadius, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
                  
         self.step = 2     
         return False
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA LARGHEZZA (da step = 1)
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

         if type(value) == QgsPointXY:
            self.startPtForBufferWidth = value
            
            # imposto il map tool
            self.getPointMapTool().startPtForBufferWidth = self.startPtForBufferWidth
            self.getPointMapTool().entitySet.set(self.entitySet)
            self.getPointMapTool().segments = self.segments
            self.getPointMapTool().setMode(Qad_mbuffer_maptool_ModeEnum.FIRST_PT_ASK_FOR_BUFFER_WIDTH)
         
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_MBUFFER", "Specify second point: "), None, QadInputModeEnum.NOT_NULL)
            self.step = 3
            return False            
         else:
            self.width = value
            self.plugIn.setLastRadius(self.width)

            if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
               self.AddGeoms(currLayer)           

            return True # fine comando

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO DELLA LARGHEZZA BUFFER (da step = 2)
      elif self.step == 3: # dopo aver atteso un punto si riavvia il comando
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

         self.width = qad_utils.getDistance(self.startPtForBufferWidth, value)
         self.plugIn.setLastRadius(self.width)     

         if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
            self.AddGeoms(currLayer)               

         return True # fine comando