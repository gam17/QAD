# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando PEDIT per editare una polilinea o un poligono esistente
 
                              -------------------
        begin                : 2014-01-13
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


from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant
from qgis.core import *
import qgis.utils

from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_generic_cmd import QadCommandClass
from .qad_getdist_cmd import QadGetDistClass
from ..qad_polyline import QadPolyline
from .qad_pedit_maptool import Qad_pedit_maptool_ModeEnum, Qad_pedit_maptool
from .qad_ssget_cmd import QadSSGetClass
from ..qad_msg import QadMsg
from ..qad_textwindow import *
from .. import qad_utils
from .. import qad_layer
from ..qad_variables import QadVariables
from ..qad_snapper import QadSnapTypeEnum
from ..qad_snappointsdisplaymanager import QadSnapPointsDisplayManager
from ..qad_dim import QadDimStyles
from .. import qad_join_fun
from .. import qad_grip
from ..qad_entity import QadEntity, QadEntitySet, QadLayerEntitySetIterator
from ..qad_multi_geom import *
from ..qad_geom_relations import getQadGeomClosestVertex, getQadGeomClosestPart
from ..qad_layer import createMemoryLayer
from ..qad_multi_geom import fromQadGeomToQgsGeom


# Classe che gestisce il comando PEDIT
class QadPEDITCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadPEDITCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "PEDIT")
   
   def getEnglishName(self):
      return "PEDIT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runPEDITCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/pedit.svg")
   
   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_PEDIT", "Modifies existing polylines or polygon.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.SSGetClass.checkPointLayer = False # scarto i punto
      self.SSGetClass.checkLineLayer = True
      self.SSGetClass.checkDimLayers = False # scarto le quote
      
      self.entitySet = QadEntitySet()
      self.entity = QadEntity()
      self.atGeom = None
      self.atSubGeom = None
      self.polyline = QadPolyline()
      self.joinToleranceDist = plugIn.joinToleranceDist
      self.joinMode = plugIn.joinMode

      self.editVertexMode = None
      self.nOperationsToUndo = 0
         
      self.firstPt = QgsPointXY()
      self.vertexAt = 0
      self.secondVertexAt = 0
      self.after = True
      self.snapPointsDisplayManager = QadSnapPointsDisplayManager(self.plugIn.canvas)
      self.snapPointsDisplayManager.setIconSize(QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE")))
      self.snapPointsDisplayManager.setColor(QColor(QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPCOLOR"))))

      self.GetDistClass = None
      self.simplifyTolerance = None
   
   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass
      self.entity.deselectOnLayer()
      self.entitySet.deselectOnLayer()
      del self.snapPointsDisplayManager
      if self.GetDistClass is not None: del self.GetDistClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 2: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()           
      # quando si é in fase di richiesta distanza
      elif self.step == 12:
         return self.GetDistClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_pedit_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 2: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta distanza
      elif self.step == 12:
         return self.GetDistClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   # ============================================================================
   # setEntityInfo
   # ============================================================================
   def setEntityInfo(self, layer, featureId, point):
      """
      Setta self.entity, self.atSubGeom, self.polyline
      """     
      self.entity.set(layer, featureId)
      if isLinearQadGeom(self.entity.getQadGeom()):
         newQadGeom = convertToPolyline(self.entity.getQadGeom())
         if newQadGeom is not None: self.entity.qadGeom = newQadGeom

      # la funzione ritorna una lista con 
      # (<minima distanza>
      # <punto del vertice più vicino>
      # <indice della geometria più vicina>
      # <indice della sotto-geometria più vicina>
      # <indice della parte della sotto-geometria più vicina>
      # <indice del vertice più vicino>
      result = getQadGeomClosestVertex(self.entity.qadGeom, point)
      atGeom = result[2]
      atSubGeom = result[3]
      subGeom = getQadGeomAt(self.entity.qadGeom, atGeom, atSubGeom)
      polyline = convertToPolyline(subGeom)
      if polyline is None:
         self.entity.deselectOnLayer()
         return False
      self.polyline = polyline
      self.atGeom = atGeom
      self.atSubGeom = atSubGeom
         
      self.entity.selectOnLayer(False) # non incrementale
      return True
         

   # ============================================================================
   # getNextVertex
   # ============================================================================
   def getNextVertex(self, vertexAt):
      """
      Ritorna la posizione del vertice successivo rispetto vertexAt
      """
      tot = self.polyline.qty()
      if vertexAt == tot - 1: # se penultimo punto
         return 0 if self.polyline.isClosed() else vertexAt + 1
      elif vertexAt < tot: # se non é ultimo punto
         return vertexAt + 1
      else:
         return vertexAt


   # ============================================================================
   # getPrevVertex
   # ============================================================================
   def getPrevVertex(self, vertexAt):
      """
      Ritorna la posizione del vertice precedente rispetto vertexAt
      """
      if vertexAt == 0: # se primo punto
         if self.polyline.isClosed():
            return self.polyline.qty() - 1
         else:
            return vertexAt
      else:
         return vertexAt - 1


   # ============================================================================
   # displayVertexMarker
   # ============================================================================
   def displayVertexMarker(self, vertexAt):
      if vertexAt == self.polyline.qty():
         pt = self.polyline.getLinearObjectAt(-1).getEndPt()
      else:
         pt = self.polyline.getLinearObjectAt(vertexAt).getStartPt()
         
      # visualizzo il punto di snap
      snapPoint = dict()
      snapPoint[QadSnapTypeEnum.INT] = [pt]
      self.snapPointsDisplayManager.show(snapPoint)
         

   # ============================================================================
   # setClose
   # ============================================================================
   def setClose(self, toClose):
      if self.entity.isInitialized(): # selezionato solo un oggetto
         qadGeom = self.entity.getQadGeom()

         layer = self.entity.layer
         self.plugIn.beginEditCommand("Feature edited", layer)
         
         f = self.entity.getFeature()
         self.polyline.setClose(toClose)
         
         if layer.geometryType() == QgsWkbTypes.LineGeometry:
            newQadGeom = setQadGeomAt(qadGeom, self.polyline, self.atGeom, self.atSubGeom)
            f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
               
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
         else: # layer di tipo poligono
            if toClose == False: # apri
               # aggiungo le linee nei layer temporanei di QAD
               LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
               self.plugIn.addLayerToLastEditCommand("Feature edited", LineTempLayer)
                       
               # trasformo la geometria in quella dei layer temporanei
               lineGeoms = [fromQadGeomToQgsGeom(self.polyline, LineTempLayer)]
               
               # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
               if qad_layer.addGeometriesToQADTempLayers(self.plugIn, None, lineGeoms, None, \
                                                         None, False) == False:
                  self.plugIn.destroyEditCommand()
                  return
               
               if delQadGeomAt(g, self.atGeom, self.atSubGeom) == False: # da cancellare
                  # plugIn, layer, feature id, refresh
                  if qad_layer.deleteFeatureToLayer(self.plugIn, layer, f.id(), False) == False:
                     self.plugIn.destroyEditCommand()
                     return
               else:
                  editedFeature = QgsFeature(f)
                  # trasformo la geometria nel crs del layer
                  editedFeature.setGeometry(fromQadGeomToQgsGeom(qadGeom, layer))
                  
                  # plugIn, layer, feature, refresh, check_validity
                  if qad_layer.updateFeatureToLayer(self.plugIn, layer, editedFeature, False, False) == False:
                     self.plugIn.destroyEditCommand()
                     return
      else: # selezionati più oggetti
         self.plugIn.beginEditCommand("Feature edited", self.entitySet.getLayerList())
         
         for layerEntitySet in self.entitySet.layerEntitySetList:
            updObjects = []
            entityIterator = QadLayerEntitySetIterator(layerEntitySet)
            for entity in entityIterator:
               if isLinearQadGeom(entity.getQadGeom()):
                  entity.qadGeom = convertToPolyline(entity.getQadGeom())
                  entity.qadGeom.setClose(toClose)
                  updFeature = QgsFeature(entity.getFeature())
                  # trasformo la geometria nel crs del layer
                  updFeature.setGeometry(fromQadGeomToQgsGeom(entity.getQadGeom(), layerEntitySet.layer))
                  updObjects.append(updFeature)
                  
            # plugIn, layer, features, refresh, check_validity
            if qad_layer.updateFeaturesToLayer(self.plugIn, layerEntitySet.layer, updObjects, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
   
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1
      

   # ============================================================================
   # reverse
   # ============================================================================
   def reverse(self):
      if self.entity.isInitialized(): # selezionato solo un oggetto
         g = self.entity.getQadGeom()
         self.polyline.reverse()
         setQadGeomAt(g, self.polyline, self.atGeom, self.atSubGeom)
         f = self.entity.getFeature()
         # trasformo la geometria nel crs del layer
         f.setGeometry(fromQadGeomToQgsGeom(g, self.entity.layer))

         self.plugIn.beginEditCommand("Feature edited", self.entity.layer)

         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return
      else: # selezionati più oggetti
         self.plugIn.beginEditCommand("Feature edited", self.entitySet.getLayerList())

         for layerEntitySet in self.entitySet.layerEntitySetList:
            updObjects = []
            entityIterator = QadLayerEntitySetIterator(layerEntitySet)
            for entity in entityIterator:
               if isLinearQadGeom(g):
                  entity.qadGeom = convertToPolyline(entity.getQadGeom())
                  entity.qadGeom.reverse()
                  updFeature = QgsFeature(entity.getFeature())
                  # trasformo la geometria nel crs del layer
                  updFeature.setGeometry(fromQadGeomToQgsGeom(entity.getQadGeom(), layerEntitySet.layer))
                  updObjects.append(updFeature)

            # plugIn, layer, features, refresh, check_validity
            if qad_layer.updateFeaturesToLayer(self.plugIn, layerEntitySet.layer, updObjects, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
   
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1
      

   # ============================================================================
   # join
   # ============================================================================
   def join(self):
      tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      crs = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
      # creo un layer temporaneo in memoria con campo numerico per 
      # contenere la posizione dell'entità originale nella lista newIdFeatureList
      # creo un layer temporaneo in memoria   
      vectorLayer = createMemoryLayer("QAD_SelfJoinLines", "LineString", crs)
      
      provider = vectorLayer.dataProvider()
      provider.addAttributes([QgsField('index', QVariant.Int, 'Int')])
      vectorLayer.updateFields()

      if vectorLayer.startEditing() == False:
         return

      # inserisco nel layer i vari oggetti lineari (WKBLineString)
      layerList = []
      newIdFeatureList = [] # lista ((newId - layer - feature) ...)
      i = 0
      
      if self.entity.isInitialized(): # selezionato solo un oggetto
         self.entitySet.removeEntity(self.entity) # elimino dal gruppo l'entità da unire
         
         # aggiungo l'entità a cui unirsi
         layer = self.entity.layer
         
         if layer.geometryType() != QgsWkbTypes.LineGeometry:
            return

         f = self.entity.getFeature()
         g = f.geometry()
         # accetto linestring o multilinestring con una sola linea
         if g.type() != QgsWkbTypes.LineGeometry:
            return
         if g.isMultipart() == True:
            if len(g.asMultiPolyline()) != 1:
               return

         newFeature = QgsFeature()
         newFeature.initAttributes(1)
         newFeature.setAttribute(0, 0)
         geom = self.polyline.asGeom()
         geom.convertToSingleType() # in caso fosse multilinestring la converto in linestring
         newFeature.setGeometry(geom)
         i = i + 1
         
         if vectorLayer.addFeature(newFeature) == False:
            vectorLayer.destroyEditCommand()
            return
         newIdFeatureList.append([newFeature.id(), layer, f])
      
      
      for layerEntitySet in self.entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         
         if layer.geometryType() != QgsWkbTypes.LineGeometry:
            continue
                  
         for f in layerEntitySet.getFeatureCollection():
            g = f.geometry()
            # accetto linestring o multilinestring con una sola linea
            if g.type() != QgsWkbTypes.LineGeometry:
               continue
            if g.isMultipart() == True:
               if len(g.asMultiPolyline()) != 1:
                  continue
            
            newFeature = QgsFeature()
            newFeature.initAttributes(1)
            newFeature.setAttribute(0, i)

            # trasformo la geometria nel crs del canvas per lavorare con coordinate piane xy
            geom = self.layerToMapCoordinates(layer, f.geometry())
            geom.convertToSingleType() # in caso fosse multilinestring la converto in linestring
            newFeature.setGeometry(geom)
            i = i + 1
            
            if vectorLayer.addFeature(newFeature) == False:
               vectorLayer.destroyEditCommand()
               return
            newIdFeatureList.append([newFeature.id(), layer, f])
               
      vectorLayer.endEditCommand();
      vectorLayer.updateExtents()
        
      if provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
         provider.createSpatialIndex()
      
      deleteFeatures = []
      if self.entity.isInitialized(): # selezionato solo un oggetto
         featureIdToJoin = newIdFeatureList[0][0]
          
         #                         featureIdToJoin, vectorLayer, tolerance2ApproxCurve, toleranceDist, mode     
         deleteFeatures.extend(qad_join_fun.joinFeatureInVectorLayer(featureIdToJoin, vectorLayer, \
                                                                     tolerance2ApproxCurve, \
                                                                     self.joinToleranceDist, self.joinMode))
      else:         
         i = 0 
         tot = len(newIdFeatureList)
         while i < tot:
            featureIdToJoin = newIdFeatureList[i][0]
            #                         featureIdToJoin, vectorLayer, tolerance2ApproxCurve, toleranceDist, mode     
            deleteFeatures.extend(qad_join_fun.joinFeatureInVectorLayer(featureIdToJoin, vectorLayer, \
                                                                        tolerance2ApproxCurve, \
                                                                        self.joinToleranceDist, self.joinMode))
            i = i + 1
                       
      self.plugIn.beginEditCommand("Feature edited", self.entitySet.getLayerList())

      if self.entity.isInitialized(): # selezionato solo un oggetto
         newFeature = qad_utils.getFeatureById(vectorLayer, newIdFeatureList[0][0])
         if newFeature is None:
            self.plugIn.destroyEditCommand()
            return
         
         layer = newIdFeatureList[0][1]
         f = newIdFeatureList[0][2]

         g = self.entity.getQadGeom()
         newQadGeom = setQadGeomAt(g, fromQgsGeomToQadGeom(newFeature.geometry()), self.atGeom, self.atSubGeom)
         # trasformo la geometria nel crs del layer
         f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return
      else:      
         # aggiorno la geometria delle features rimaste nel layer temporaneo
         # fetchAttributes, fetchGeometry, rectangle, useIntersect             
         for newFeature in vectorLayer.getFeatures(qad_utils.getFeatureRequest([], True, None, False)):
            layer = newIdFeatureList[newFeature['index']][1]
            f = newIdFeatureList[newFeature['index']][2]
            
            coordTransform = QgsCoordinateTransform(vectorLayer.crs(), layer.crs(), QgsProject.instance())
            g = newFeature.geometry()
            g.transform(coordTransform)
            f.setGeometry(g)
               
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
                          
      # cancello le features rimosse dal layer temporaneo
      for newFeature in deleteFeatures:
         layer = newIdFeatureList[newFeature['index']][1]
         f = newIdFeatureList[newFeature['index']][2]                          
         # plugIn, layer, feature id, refresh
         if qad_layer.deleteFeatureToLayer(self.plugIn, layer, f.id(), False) == False:
            self.plugIn.destroyEditCommand()
            return      
   
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # curve
   # ============================================================================
   def curve(self, toCurve):
      if self.entity.isInitialized(): # selezionato solo un oggetto
         g = self.entity.getQadGeom()
         self.polyline.curve(toCurve)
         newQadGeom = setQadGeomAt(g, self.polyline, self.atGeom, self.atSubGeom)
         f = self.entity.getFeature()
         # trasformo la geometria nel crs del layer
         f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, self.entity.layer))
         
         self.plugIn.beginEditCommand("Feature edited", self.entity.layer)

         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return
      else:
         self.plugIn.beginEditCommand("Feature edited", self.entitySet.getLayerList())

         for layerEntitySet in self.entitySet.layerEntitySetList:
            updObjects = []
            entityIterator = QadLayerEntitySetIterator(layerEntitySet)
            for entity in entityIterator:
               if isLinearQadGeom(g):
                  entity.qadGeom = convertToPolyline(entity.getQadGeom())
                  entity.qadGeom.curve(toCurve)
                  updFeature = QgsFeature(entity.getFeature())
                  # trasformo la geometria nel crs del layer
                  updFeature.setGeometry(fromQadGeomToQgsGeom(entity.getQadGeom(), layerEntitySet.layer))
                  updObjects.append(updFeature)

            # plugIn, layer, features, refresh, check_validity
            if qad_layer.updateFeaturesToLayer(self.plugIn, layerEntitySet.layer, updObjects, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
   
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # simplify
   # ============================================================================
   def simplify(self):
      if self.entity.isInitialized(): # selezionato solo un oggetto
         self.plugIn.beginEditCommand("Feature edited", self.entity.layer)
         self.polyline.simplify(self.simplifyTolerance)
         g = self.entity.getQadGeom()
         newQadGeom = setQadGeomAt(g, self.polyline, self.atGeom, self.atSubGeom)
         f = self.entity.getFeature()
         # trasformo la geometria nel crs del layer
         f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, self.entity.layer))
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return
      else:
         self.plugIn.beginEditCommand("Feature edited", self.entitySet.getLayerList())

         for layerEntitySet in self.entitySet.layerEntitySetList:
            updObjects = []
            entityIterator = QadLayerEntitySetIterator(layerEntitySet)
            for entity in entityIterator:
               if isLinearQadGeom(entity.getQadGeom()):
                  entity.qadGeom = convertToPolyline(entity.getQadGeom())
                  entity.qadGeom.simplify(self.simplifyTolerance)
                  updFeature = QgsFeature(entity.getFeature())
                  # trasformo la geometria nel crs del layer
                  updFeature.setGeometry(fromQadGeomToQgsGeom(entity.getQadGeom(), layerEntitySet.layer))
                  updObjects.append(updFeature)
         
            # plugIn, layer, features, refresh, check_validity
            if qad_layer.updateFeaturesToLayer(self.plugIn, layerEntitySet.layer, updObjects, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
   
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # insertVertexAt
   # ============================================================================
   def insertVertexAt(self, pt):         
      layer = self.entity.layer

      if self.after: # dopo
         if self.vertexAt == self.polyline.qty() and self.polyline.isClosed():
            self.polyline.insertPoint(0, pt)
         else:
            self.polyline.insertPoint(self.vertexAt, pt)
      else: # prima
         if self.vertexAt == 0 and self.polyline.isClosed():
            self.polyline.insertPoint(self.polyline.qty() - 1, pt)
         else:
            self.polyline.insertPoint(self.vertexAt - 1, pt)
               
      g = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(g, self.polyline, self.atGeom, self.atSubGeom)
      f = self.entity.getFeature()
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
      
      self.plugIn.beginEditCommand("Feature edited", layer)
   
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # moveVertexAt
   # ============================================================================
   def moveVertexAt(self, pt):         
      layer = self.entity.layer

      self.polyline.movePoint(self.vertexAt, pt)
      g = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(g, self.polyline, self.atGeom, self.atSubGeom)
      f = self.entity.getFeature()
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
         
      self.plugIn.beginEditCommand("Feature edited", layer)
      
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # straightenFromVertexAtToSecondVertexAt
   # ============================================================================
   def straightenFromVertexAtToSecondVertexAt(self):
      if self.vertexAt == self.secondVertexAt:
         return
               
      if self.vertexAt < self.secondVertexAt:
         firstPt = self.polyline.getPointAtVertex(self.vertexAt)
         secondPt = self.polyline.getPointAtVertex(self.secondVertexAt)
         for i in range(self.vertexAt, self.secondVertexAt, 1):
            self.polyline.remove(self.vertexAt)
         self.polyline.insert(self.vertexAt, QadLine().set(firstPt, secondPt))
      elif self.vertexAt > self.secondVertexAt:
         if self.polyline.isClosed():
            firstPt = self.polyline.getPointAtVertex(self.vertexAt)
            secondPt = self.polyline.getPointAtVertex(self.secondVertexAt)
            for i in range(self.vertexAt, self.polyline.qty(), 1):
               self.polyline.remove(self.vertexAt)
            for i in range(0, self.secondVertexAt, 1):
               self.polyline.remove(0)
            
            self.polyline.insert(self.vertexAt, QadLine().set(firstPt, secondPt))
         else:
            firstPt = self.polyline.getPointAtVertex(self.secondVertexAt)
            secondPt = self.polyline.getPointAtVertex(self.vertexAt)
            for i in range(self.secondVertexAt, self.vertexAt, 1):
               self.polyline.remove(self.secondVertexAt)
            self.polyline.insert(self.secondVertexAt, QadLine().set(firstPt, secondPt))

      g = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(g, self.polyline, self.atGeom, self.atSubGeom)
      f = self.entity.getFeature()
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
      
      layer = self.entity.layer
      self.plugIn.beginEditCommand("Feature edited", layer)
            
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # breakFromVertexAtToSecondVertexAt
   # ============================================================================
   def breakFromVertexAtToSecondVertexAt(self):
      layer = self.entity.layer

      firstPt = self.polyline.getPointAtVertex(self.vertexAt)
      secondPt = self.polyline.getPointAtVertex(self.secondVertexAt)
      g1, g2 = self.polyline.breakOnPts(firstPt, secondPt)
      if g1 is None: return
      g = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(g, g1, self.atGeom, self.atSubGeom)
      f = self.entity.getFeature()
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))

      self.plugIn.beginEditCommand("Feature edited", layer)
      
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return
      
      if g2 is not None:
         brokenFeature2 = QgsFeature(f)
         # trasformo la geometria nel crs del layer
         brokenFeature2.setGeometry(fromQadGeomToQgsGeom(g2, layer))
         # plugIn, layer, feature, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(self.plugIn, layer, brokenFeature2, None, False, False, False) == False:
            self.plugIn.destroyEditCommand()
            return            

      self.polyline = g1
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # waitForEntsel
   # ============================================================================
   def waitForEntsel(self):      
      # imposto il map tool
      self.step = 1
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_ENTITY_SEL)
                        
      keyWords = QadMsg.translate("Command_PEDIT", "Last") + "/" + \
                 QadMsg.translate("Command_PEDIT", "Multiple")
      prompt = QadMsg.translate("Command_PEDIT", "Select polyline or [{0}]: ").format(QadMsg.translate("Command_PEDIT", "Multiple"))
               
      englishKeyWords = "Last" + "/" + "Multiple"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, valore nullo non permesso
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)      
      

   # ============================================================================
   # WaitForMainMenu
   # ============================================================================
   def WaitForMainMenu(self):
      # verifico se ci sono layer di tipo linea
      line = False
      if self.entity.isInitialized(): # selezionato solo un oggetto
         if self.entity.layer.geometryType() == QgsWkbTypes.LineGeometry:
            line = True
      else:            
         layerList = self.entitySet.getLayerList()
         for layer in layerList:
            if layer.geometryType() == QgsWkbTypes.LineGeometry:
               line = True
               break

      if line == True: # se ci sono dei layer linea
         if self.entity.isInitialized(): # selezionato solo un oggetto
            if self.polyline.isClosed(): # se é chiusa
               keyWords = QadMsg.translate("Command_PEDIT", "Open") + "/"
               englishKeyWords = "Open"
            else:
               keyWords = QadMsg.translate("Command_PEDIT", "Close") + "/"
               englishKeyWords = "Close"
         else: # selezionati più oggetti
            keyWords = QadMsg.translate("Command_PEDIT", "Close") + "/" + \
                       QadMsg.translate("Command_PEDIT", "Open") + "/"
            englishKeyWords = "Close" + "/" + "Open"
                  
         keyWords = keyWords + QadMsg.translate("Command_PEDIT", "Join") + "/"
         englishKeyWords = englishKeyWords + "Join"
      else: # se non ci sono dei layer linea
         keyWords = ""
         msg = ""
         englishKeyWords = ""

      if self.entity.isInitialized(): # selezionato solo un oggetto
         keyWords = keyWords + QadMsg.translate("Command_PEDIT", "Edit vertex") + "/"
         englishKeyWords = englishKeyWords + "Edit vertex"
         
      keyWords = keyWords + QadMsg.translate("Command_PEDIT", "Fit") + "/" + \
                            QadMsg.translate("Command_PEDIT", "Decurve") + "/" + \
                            QadMsg.translate("Command_PEDIT", "Reverse") + "/" + \
                            QadMsg.translate("Command_PEDIT", "Simplify") + "/" + \
                            QadMsg.translate("Command_PEDIT", "Undo")      
      englishKeyWords = englishKeyWords + "Fit" + "/" + "Decurve" + "/" + "Reverse" + "/" + "Simplify" + "/" + "Undo"
      prompt = QadMsg.translate("Command_PEDIT", "Enter an option [{0}]: ").format(keyWords)
      
      self.step = 3
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.NONE)

      keyWords += "_" + englishKeyWords
      # si appresta ad attendere enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      return False
      

   # ============================================================================
   # WaitForJoin
   # ============================================================================
   def WaitForJoin(self):
      CurrSettingsMsg = QadMsg.translate("QAD", "\nCurrent settings: ")
      CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_PEDIT", "Join type = ")
      if self.joinMode == 1:
         CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_PEDIT", "extends the segments")
      elif self.joinMode == 2:
         CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_PEDIT", "adds segments")
      elif self.joinMode == 3:
         CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_PEDIT", "extends and adds segments")
      
      self.showMsg(CurrSettingsMsg)
      self.waitForDistance()       
        

   # ============================================================================
   # waitForDistance
   # ============================================================================
   def waitForDistance(self):      
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_FIRST_TOLERANCE_PT)

      keyWords = QadMsg.translate("Command_PEDIT", "Join type")                 
      prompt = QadMsg.translate("Command_PEDIT", "Specify gap tolerance or [{0}] <{1}>: ").format(keyWords, str(self.joinToleranceDist))

      englishKeyWords = "Join type"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave o un numero reale     
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   self.joinToleranceDist, \
                   keyWords, \
                   QadInputModeEnum.NOT_NEGATIVE)      
      self.step = 4      
      
        
   # ============================================================================
   # waitForJoinType
   # ============================================================================
   def waitForJoinType(self):      
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("Command_PEDIT", "Extend") + "/" + \
                 QadMsg.translate("Command_PEDIT", "Add") + "/" + \
                 QadMsg.translate("Command_PEDIT", "Both")
      englishKeyWords = "Extend" + "/" + "Add" + "/" + "Both"
      if self.joinMode == 1:
         default = QadMsg.translate("Command_PEDIT", "Extend")
      elif self.joinMode == 2:
         default = QadMsg.translate("Command_PEDIT", "Add")
      elif self.joinMode == 3:
         default = QadMsg.translate("Command_PEDIT", "Both")
      prompt = QadMsg.translate("Command_PEDIT", "Specify join type [{0}] <{1}>: ").format(keyWords, default)

      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave o un numero reale     
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, default, \
                   keyWords)      
      self.step = 6


   # ============================================================================
   # WaitForVertexEditingMenu
   # ============================================================================
   def WaitForVertexEditingMenu(self):
      self.getPointMapTool().setPolyline(self.polyline, self.entity.layer)
      
      self.displayVertexMarker(self.vertexAt)
      
      keyWords = QadMsg.translate("Command_PEDIT", "Next") + "/" + \
                 QadMsg.translate("Command_PEDIT", "Previous")
      englishKeyWords = "Next" + "/" + "Previous"
      
      if self.entity.layer.geometryType() == QgsWkbTypes.LineGeometry:
         keyWords = keyWords + "/"  + QadMsg.translate("Command_PEDIT", "Break")
         englishKeyWords = englishKeyWords + "/" + "Break"

      keyWords = keyWords + "/" + QadMsg.translate("Command_PEDIT", "Insert") + "/" + \
                                  QadMsg.translate("Command_PEDIT", "INsert before") + "/" + \
                                  QadMsg.translate("Command_PEDIT", "Move") + "/" + \
                                  QadMsg.translate("Command_PEDIT", "Straighten") + "/" + \
                                  QadMsg.translate("Command_PEDIT", "eXit")
      englishKeyWords = englishKeyWords + "/" + "Insert" + "/" + "INsert before" + "/" + \
                                          "Move" + "/" + "Straighten" + "/" + "eXit"

      prompt = QadMsg.translate("Command_PEDIT", "Enter a vertex editing option [{0}] <{1}>: ").format(keyWords, self.default)
               
      self.step = 8
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_VERTEX)

      keyWords += "_" + englishKeyWords
      # si appresta ad attendere enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   self.default, \
                   keyWords, QadInputModeEnum.NONE)
      return False


   # ============================================================================
   # waitForNewVertex
   # ============================================================================
   def waitForNewVertex(self):      
      # imposto il map tool
      self.getPointMapTool().setVertexAt(self.vertexAt, self.after)
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_NEW_VERTEX)

      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_PEDIT", "Specify the position of the new vertex: "))
      self.step = 9   


   # ============================================================================
   # waitForMoveVertex
   # ============================================================================
   def waitForMoveVertex(self):      
      # imposto il map tool
      self.getPointMapTool().setVertexAt(self.vertexAt)            
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_MOVE_VERTEX)

      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_PEDIT", "Specify the new vertex position: "))
      self.step = 10   


   # ============================================================================
   # WaitForVertexEditingMenu
   # ============================================================================
   def WaitForSecondVertex(self):
      self.displayVertexMarker(self.secondVertexAt)
      
      keyWords = QadMsg.translate("Command_PEDIT", "Next") + "/"  + \
                 QadMsg.translate("Command_PEDIT", "Previous") + "/"  + \
                 QadMsg.translate("Command_PEDIT", "Go") + "/"  + \
                 QadMsg.translate("Command_PEDIT", "eXit")
      englishKeyWords = "Next" + "/" + "Previous" + "/" + "Go" + "/" + "eXit"
      prompt = QadMsg.translate("Command_PEDIT", "Enter a selection option for the second vertex [{0}] <{1}>: ").format(keyWords, self.default1)
               
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_VERTEX)
      
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   self.default1, \
                   keyWords, QadInputModeEnum.NONE)
      self.step = 11
      
      return False


   # ============================================================================
   # WaitForSimplifyTolerance
   # ============================================================================
   def WaitForSimplifyTolerance(self, msgMapTool, msg):
      if self.GetDistClass is not None:
         del self.GetDistClass
      self.GetDistClass = QadGetDistClass(self.plugIn)
      if self.simplifyTolerance is None:
         prompt = QadMsg.translate("Command_PEDIT", "Specify tolerance: ")
      else:
         prompt = QadMsg.translate("Command_PEDIT", "Specify tolerance <{0}>: ")
         self.GetDistClass.msg = prompt.format(str(self.simplifyTolerance))
         self.GetDistClass.dist = self.simplifyTolerance
      self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
      self.step = 12
      self.GetDistClass.run(msgMapTool, msg)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      if self.step == 0:     
         self.waitForEntsel()
         return False # continua
      
      # =========================================================================
      # RISPOSTA ALLA SELEZIONE OGGETTI
      elif self.step == 1:
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
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_PEDIT", "Multiple") or value == "Multiple":
               self.SSGetClass.checkPolygonLayer = True               
               self.SSGetClass.run(msgMapTool, msg)
               self.step = 2
               return False               
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            self.entity.clear()
            self.polyline.removeAll()

            if self.getPointMapTool().entity.isInitialized():
               if self.setEntityInfo(self.getPointMapTool().entity.layer, \
                                     self.getPointMapTool().entity.featureId, value) == True:
                  self.WaitForMainMenu()
                  return False
            else:               
               # cerco se ci sono entità nel punto indicato considerando
               # solo layer lineari o poligono editabili che non appartengano a quote
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
                  if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
                     layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)
               
               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value),
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  # result[0] = feature, result[1] = layer, result[0] = point
                  if self.setEntityInfo(result[1], result[0].id(), result[2]) == True:
                     self.WaitForMainMenu()
                     return False                  
         else:
            return True # fine comando
         
         # si appresta ad attendere la selezione degli oggetti
         self.waitForEntsel()
         return False 

      # =========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN GRUPPO OGGETTI
      elif self.step == 2:
         if self.SSGetClass.run(msgMapTool, msg) == True:         
            self.entitySet.set(self.SSGetClass.entitySet)
            
            if self.entitySet.count() == 0:
               self.waitForEntsel()
            else:
               self.WaitForMainMenu()
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di selezione entità                    
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL MENU PRINCIPALE (da step = 1 e 2)
      elif self.step == 3: # dopo aver atteso una opzione si riavvia il comando
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

            self.WaitForMainMenu()
            return False 
         else: # il punto arriva come parametro della funzione
            value = msg

         if value == QadMsg.translate("Command_PEDIT", "Close") or value == "Close":
            self.setClose(True) 
         elif value == QadMsg.translate("Command_PEDIT", "Open") or value == "Open":
            self.setClose(False) 
         elif value == QadMsg.translate("Command_PEDIT", "Edit vertex") or value == "Edit vertex":
            self.vertexAt = 0
            self.default = QadMsg.translate("Command_PEDIT", "Next")
            self.WaitForVertexEditingMenu()
            return False
         elif value == QadMsg.translate("Command_PEDIT", "Join") or value == "Join":
            qad_utils.deselectAll(self.plugIn.canvas.layers())
            if self.entity.isInitialized(): # selezionato solo un oggetto
               self.SSGetClass.checkPolygonLayer = False # scarto i poligoni
               self.SSGetClass.run(msgMapTool, msg)
               self.step = 7
               return False               
            else:
               self.WaitForJoin()
               return False
         elif value == QadMsg.translate("Command_PEDIT", "Fit") or value == "Fit":
            self.curve(True)
         elif value == QadMsg.translate("Command_PEDIT", "Decurve") or value == "Decurve":
            self.curve(False)
         elif value == QadMsg.translate("Command_PEDIT", "Reverse") or value == "Reverse":
            self.reverse()
         elif value == QadMsg.translate("Command_PEDIT", "Simplify") or value == "Simplify":
            self.WaitForSimplifyTolerance(msgMapTool, msg)
            return False
         elif value == QadMsg.translate("Command_PEDIT", "Undo") or value == "Undo":
            if self.nOperationsToUndo > 0: 
               self.nOperationsToUndo = self.nOperationsToUndo - 1           
               self.plugIn.undoEditCommand()
            else:
               self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
            
            if self.entity.isInitialized(): # selezionato solo un oggetto
               if self.atSubGeom is not None:
                  # ricarico la geometria ripristinata dall'annulla
                  self.entity.qadGeom = None
                  if isLinearQadGeom(self.entity.getQadGeom()):
                     self.entity.qadGeom = convertToPolyline(self.entity.getQadGeom())
                                
                  subGeom = getQadGeomAt(self.entity.qadGeom, self.atGeom, self.atSubGeom).copy()
                  self.polyline = convertToPolyline(subGeom)
         else:
            return True # fine comando
            
         self.entity.deselectOnLayer()
         self.entitySet.deselectOnLayer()
         self.WaitForMainMenu()
         return False      
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DISTANZA DI APPROSSIMAZIONE (da step = 3)
      elif self.step == 4: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.joinToleranceDist
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg
         
         if type(value) == unicode:
            if value == QadMsg.translate("Command_PEDIT", "Join type") or value == "Join type":
               # si appresta ad attendere il tipo di unione
               self.waitForJoinType()
         elif type(value) == QgsPointXY: # se é stato inserito il primo punto per il calcolo della distanza
            # imposto il map tool
            self.firstPt.set(value.x(), value.y())
            self.getPointMapTool().firstPt = self.firstPt
            self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.FIRST_TOLERANCE_PT_KNOWN_ASK_FOR_SECOND_PT)

            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_PEDIT", "Specify second point: "))
            self.step = 5
         elif type(value) == float:
            self.joinToleranceDist = value
            self.plugIn.setJoinToleranceDist(self.joinToleranceDist)
            self.join()
            self.entity.deselectOnLayer()
            self.entitySet.deselectOnLayer()
            self.WaitForMainMenu()
         
         return False 
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO PER DISTANZA DI APPROSSIMAZIONE (da step = 4)
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

         if value == self.firstPt:
            self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_PEDIT", "Specify second point: "))
            return False
         
         self.joinToleranceDist = qad_utils.getDistance(self.firstPt, value)
         self.plugIn.setJoinToleranceDist(self.joinToleranceDist)
         self.join()
         self.entity.deselectOnLayer()
         self.entitySet.deselectOnLayer()
         self.WaitForMainMenu()

         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI UNIONE (da step = 4)
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
            if value == QadMsg.translate("Command_PEDIT", "Extend") or value == "Extend":
               self.joinMode = 1
               self.plugIn.setJoinMode(self.joinMode)
            elif value == QadMsg.translate("Command_PEDIT", "Add") or value == "Add":
               self.joinMode = 2
               self.plugIn.setJoinMode(self.joinMode)
            elif value == QadMsg.translate("Command_PEDIT", "Both") or value == "Both":
               self.joinMode = 3
               self.plugIn.setJoinMode(self.joinMode)
            
         self.WaitForJoin()
         return False
      
      # =========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN GRUPPO OGGETTI DA UNIRE (da step = 3)
      elif self.step == 7:
         if self.SSGetClass.run(msgMapTool, msg) == True:         
            self.entitySet.set(self.SSGetClass.entitySet)
            
            if self.entitySet.count() > 0:
               self.joinToleranceDist = 0.0
               self.join()

            self.entity.deselectOnLayer()
            self.entitySet.deselectOnLayer()
            self.WaitForMainMenu()
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI OPZIONI EDITAZIONE VERTICI (da step = 3)
      elif self.step == 8: # dopo aver atteso un punto o una opzione si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.default
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto o l'opzione arriva come parametro della funzione
            value = msg
         
         if type(value) == unicode:
            if value == QadMsg.translate("Command_PEDIT", "Next") or value == "Next":
               self.default = value
               self.vertexAt = self.getNextVertex(self.vertexAt)                                 
               self.WaitForVertexEditingMenu()
            elif value == QadMsg.translate("Command_PEDIT", "Previous") or value == "Previous":
               self.default = value
               self.vertexAt = self.getPrevVertex(self.vertexAt)
               self.WaitForVertexEditingMenu()
            elif value == QadMsg.translate("Command_PEDIT", "Break") or value == "Break":
               self.editVertexMode = QadMsg.translate("Command_PEDIT", "Break")
               self.secondVertexAt = self.vertexAt
               self.default1 = QadMsg.translate("Command_PEDIT", "Next")
               self.WaitForSecondVertex()
               return False
            elif value == QadMsg.translate("Command_PEDIT", "Insert") or value == "Insert":
               self.after = True
               self.waitForNewVertex()      
            elif value == QadMsg.translate("Command_PEDIT", "INsert before") or value == "INsert before":
               self.after = False
               self.waitForNewVertex()
            elif value == QadMsg.translate("Command_PEDIT", "Move") or value == "Move":
               self.waitForMoveVertex()
            elif value == QadMsg.translate("Command_PEDIT", "Straighten") or value == "Straighten":
               self.editVertexMode = QadMsg.translate("Command_PEDIT", "Straighten")
               self.secondVertexAt = self.vertexAt
               self.default1 = QadMsg.translate("Command_PEDIT", "Next")
               self.WaitForSecondVertex()
               return False
            elif value == QadMsg.translate("Command_PEDIT", "eXit") or value == "eXit":
               self.WaitForMainMenu()
         elif type(value) == QgsPointXY: # se é stato inserito un punto
            # cerco l'indice del vertice più vicino al punto
            # la funzione ritorna una lista con 
            # (<minima distanza>
            #  <punto del vertice più vicino>
            #  <indice della geometria più vicina>
            #  <indice della sotto-geometria più vicina>
            #  <indice della parte della sotto-geometria più vicina>
            #  <indice del vertice più vicino>)
            self.vertexAt = getQadGeomClosestVertex(self.polyline, value)[5]
            self.WaitForVertexEditingMenu()
                                 
         return False 


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUOVO VERTICE DA INSERIRE (da step = 8)
      elif self.step == 9: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
         
         self.insertVertexAt(value)
         self.vertexAt = self.vertexAt + (1 if self.after else -1)
         self.WaitForVertexEditingMenu()

         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA POSIZIONE DEL VERTICE DA SPOSTARE (da step = 8)
      elif self.step == 10: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
         
         self.moveVertexAt(value)
         self.WaitForVertexEditingMenu()

         return False

      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO VERTICE (da step = 8)
      elif self.step == 11: # dopo aver atteso un punto o una opzione si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.default
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto o l'opzione arriva come parametro della funzione
            value = msg
         
         if type(value) == unicode:
            if value == QadMsg.translate("Command_PEDIT", "Next") or value == "Next":
               self.default1 = value
               self.secondVertexAt = self.getNextVertex(self.secondVertexAt)                                 
               self.WaitForSecondVertex()
            elif value == QadMsg.translate("Command_PEDIT", "Previous") or value == "Previous":
               self.default1 = value
               self.secondVertexAt = self.getPrevVertex(self.secondVertexAt)
               self.WaitForSecondVertex()
            elif value == QadMsg.translate("Command_PEDIT", "Go") or value == "Go":
               pt = self.polyline.getPointAtVertex(self.vertexAt)
               
               if self.editVertexMode == QadMsg.translate("Command_PEDIT", "Break"):
                  self.breakFromVertexAtToSecondVertexAt()
               elif self.editVertexMode == QadMsg.translate("Command_PEDIT", "Straighten"):
                  self.straightenFromVertexAtToSecondVertexAt()
                  
               self.vertexAt = self.polyline.getVertexPosAtPt(pt)
               self.WaitForVertexEditingMenu()
            elif value == QadMsg.translate("Command_PEDIT", "eXit") or value == "eXit":
               self.WaitForVertexEditingMenu()
         elif type(value) == QgsPointXY: # se é stato inserito il primo punto
            # cerco l'indice del vertice più vicino al punto
            # la funzione ritorna una lista con 
            # (<minima distanza>
            #  <punto del vertice più vicino>
            #  <indice della geometria più vicina>
            #  <indice della sotto-geometria più vicina>
            #  <indice della parte della sotto-geometria più vicina>
            #  <indice del vertice più vicino>)
            self.secondVertexAt = getQadGeomClosestVertex(self.polyline, value)[5]
            self.WaitForSecondVertex()
                                 
         return False 
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA TOLLERANZE PER SEMPLIFICAZIONE (da step = 3)
      elif self.step == 12:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.simplifyTolerance = self.GetDistClass.dist
               self.simplify()
               self.entity.deselectOnLayer()
               self.entitySet.deselectOnLayer()
               self.WaitForMainMenu()
         return False # fine comando


# ============================================================================
# Classe che gestisce il comando per inserire/cancellare un vertice per i grip
# ============================================================================
class QadGRIPINSERTREMOVEVERTEXCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadGRIPINSERTREMOVEVERTEXCommandClass(self.plugIn)

   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = None
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.basePt = QgsPointXY()
      self.nOperationsToUndo = 0

      self.after = True
      self.insert_mode = True
      self.vertexAt = 0
      self.firstPt = QgsPointXY()
      self.polyline = None

   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_pedit_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   def setInsertVertexAfter_Mode(self):
      self.after = True
      self.insert_mode = True
      
   def setInsertVertexBefore_Mode(self):
      self.after = False
      self.insert_mode = True

   def setRemoveVertex_mode(self):
      self.insert_mode = False
      
      
   # ============================================================================
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # lista delle entityGripPoint con dei grip point selezionati
      # setta la prima entità con un grip selezionato
      # setta: self.entity, self.polyline, self.atGeom, self.atSubGeom
      self.entity = None
      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         for gripPoint in entityGripPoints.gripPoints:
            # grip point selezionato
            if gripPoint.getStatus() == qad_grip.QadGripStatusEnum.SELECTED:
               self.firstPt.set(gripPoint.getPoint().x(), gripPoint.getPoint().y())
               
               # verifico se l'entità appartiene ad uno stile di quotatura
               if QadDimStyles.isDimEntity(entityGripPoints.entity):
                  return False
               if isLinearQadGeom(entityGripPoints.entity.getQadGeom()):
                  newQadGeom = convertToPolyline(entityGripPoints.entity.getQadGeom())
                  if newQadGeom is not None: entityGripPoints.entity.qadGeom = newQadGeom
                  
               # la funzione ritorna una lista con 
               # (<minima distanza>
               #  <punto più vicino>
               #  <indice della geometria più vicina>
               #  <indice della sotto-geometria più vicina>
               #   se geometria chiusa è tipo polyline la lista contiene anche
               #  <indice della parte della sotto-geometria più vicina>
               #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
               # )
               result = getQadGeomClosestPart(entityGripPoints.entity.getQadGeom(), self.firstPt)
               self.atGeom = result[2]
               self.atSubGeom = result[3]
               subGeom = getQadGeomAt(entityGripPoints.entity.getQadGeom(), self.atGeom, self.atSubGeom)
               polyline = convertToPolyline(subGeom)
               if polyline is None:
                  return False
               self.polyline = polyline
               self.entity = entityGripPoints.entity
               # setto il n. di vertice
               self.vertexAt = gripPoint.nVertex

               self.getPointMapTool().setPolyline(self.polyline, self.entity.layer)
               return True

      return False


   # ============================================================================
   # insertVertexAt
   # ============================================================================
   def insertVertexAt(self, pt):
      layer = self.entity.layer
      f = self.entity.getFeature()
      if f is None: # non c'è più la feature
         return False
      
      # faccio una copia locale
      polyline = self.polyline.copy()

      if self.after: # dopo
         # fromStartEndPtsAngle
         if self.vertexAt == polyline.qty() and polyline.isClosed():
            polyline.insertPoint(0, pt)
         else:
            polyline.insertPoint(self.vertexAt, pt)
      else: # prima
         if self.vertexAt == 0 and polyline.isClosed():
            polyline.insertPoint(self.polyline.qty() - 1, pt)
         else:
            polyline.insertPoint(self.vertexAt - 1, pt)

      qadGeom = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(qadGeom, polyline, self.atGeom, self.atSubGeom)
      
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
      
      self.plugIn.beginEditCommand("Feature edited", layer)
   
      if self.copyEntities == False:
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False
      else:
         # plugIn, layer, features, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, False, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # removeVertexAt
   # ============================================================================
   def removeVertexAt(self):
      if self.polyline.qty() == 1: return False # non si può cancellare l'unica parte della geometria
      
      layer = self.entity.layer
      f = self.entity.getFeature()
      if f is None: # non c'è più la feature
         return False

      # faccio una copia locale
      polyline = self.polyline.copy()
      
      if self.vertexAt == 0:
         polyline.remove(self.vertexAt) # rimuovo la prima parte
      elif self.vertexAt == self.polyline.qty():
         polyline.remove(self.vertexAt - 1) # rimuovo la ultima parte
      else:
         # modifico la parte successiva
         polyline.movePoint(self.vertexAt, polyline.getPointAtVertex(self.vertexAt - 1))
         polyline.remove(self.vertexAt - 1) # rimuovo la parte precedente

      qadGeom = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(qadGeom, polyline, self.atGeom, self.atSubGeom)
      
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
      
      self.plugIn.beginEditCommand("Feature edited", layer)

      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      self.plugIn.endEditCommand()


   # ============================================================================
   # waitForBasePt
   # ============================================================================
   def waitForBasePt(self):
      self.step = 2   
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_BASE_PT)

      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_GRIP", "Specify base point: "))


   # ============================================================================
   # waitForNewVertex
   # ============================================================================
   def waitForNewVertex(self):
      # imposto il map tool
      self.getPointMapTool().setVertexAt(self.vertexAt, self.after)
      if self.basePt is not None:
         self.getPointMapTool().firstPt = self.basePt
      self.getPointMapTool().setMode(Qad_pedit_maptool_ModeEnum.ASK_FOR_NEW_VERTEX)

      keyWords = QadMsg.translate("Command_GRIP", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIP", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIP", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIP", "eXit")
      prompt = QadMsg.translate("Command_GRIPINSERTREMOVEVERTEX", "Specify the position of the new vertex or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" "eXit"
      keyWords += "_" + englishKeyWords

      # si appresta ad attendere un punto o enter o una parola chiave
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      self.step = 1


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
         if self.entity is None: # non ci sono oggetti da stirare
            return True

         if self.insert_mode:
            self.showMsg(QadMsg.translate("Command_GRIPINSERTREMOVEVERTEX", "\n** ADD VERTEX **\n"))
            # si appresta ad attendere un nuovo punto
            self.waitForNewVertex()
         else:
            self.showMsg(QadMsg.translate("Command_GRIPINSERTREMOVEVERTEX", "\n** REMOVE VERTEX **\n"))
            self.removeVertexAt()
            return True
         
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUOVO VERTICE DA INSERIRE (da step = 1)
      elif self.step == 1:
         ctrlKey = False
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.copyEntities == False:
                     self.skipToNextGripCommand = True
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

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
               # si appresta ad attendere un nuovo punto
               self.waitForNewVertex()
            elif value == QadMsg.translate("Command_GRIP", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
               # si appresta ad attendere un nuovo punto
               self.waitForNewVertex()
            elif value == QadMsg.translate("Command_GRIP", "eXit") or value == "eXit":
               return True # fine comando
         elif type(value) == QgsPointXY:
            if ctrlKey:
               self.copyEntities = True
   
            offsetX = value.x() - self.basePt.x()
            offsetY = value.y() - self.basePt.y()
            value.set(self.firstPt.x() + offsetX, self.firstPt.y() + offsetY)
            self.insertVertexAt(value)

            if self.copyEntities == False:
               return True
            # si appresta ad attendere un nuovo punto
            self.waitForNewVertex()
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
                  pass # opzione di default
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
            self.getPointMapTool().firstPt = self.basePt
            
         # si appresta ad attendere un nuovo punto
         self.waitForNewVertex()

         return False
      

# ============================================================================
# Classe che gestisce il comando per convertire in arco o in linea un segmento per i grip
# ============================================================================
class QadGRIPARCLINECONVERTCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadGRIPARCLINECONVERTCommandClass(self.plugIn)

   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = None
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.nOperationsToUndo = 0
      self.basePt = QgsPointXY()

      self.lineToArc = True
      self.partAt = 0
      self.polyline = QadPolyline()


   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_gripLineToArcConvert_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   def setLineToArcConvert_Mode(self):
      self.lineToArc = True
      
   def setArcToLineConvert_Mode(self):
      self.lineToArc = False


   # ============================================================================
   # setSelectedEntityGripPoints
   # ============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # lista delle entityGripPoint con dei grip point selezionati
      # setta la prima entità con un grip selezionato
      self.entity = None
      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         for gripPoint in entityGripPoints.gripPoints:
            # grip point selezionato
            if gripPoint.getStatus() == qad_grip.QadGripStatusEnum.SELECTED and \
               (gripPoint.gripType == qad_grip.QadGripPointTypeEnum.LINE_MID_POINT or \
                gripPoint.gripType == qad_grip.QadGripPointTypeEnum.ARC_MID_POINT):
               # verifico se l'entità appartiene ad uno stile di quotatura
               if QadDimStyles.isDimEntity(entityGripPoints.entity):
                  return False
               if isLinearQadGeom(entityGripPoints.entity.getQadGeom()):
                  entityGripPoints.entity.qadGeom = convertToPolyline(entityGripPoints.entity.getQadGeom())
               
               # setta: self.entity, self.polyline, self.atSubGeom
               self.entity = entityGripPoints.entity

               firstPt = QgsPointXY(gripPoint.getPoint())
               
               # la funzione ritorna una lista con 
               # (<minima distanza>
               # <punto del vertice più vicino>
               # <indice della geometria più vicina>
               # <indice della sotto-geometria più vicina>
               # <indice della parte della sotto-geometria più vicina>
               # <indice del vertice più vicino>
               result = getQadGeomClosestVertex(entityGripPoints.entity.getQadGeom(), firstPt)
               atGeom = result[2]
               atSubGeom = result[3]
               subGeom = getQadGeomAt(entityGripPoints.entity.getQadGeom(), atGeom, atSubGeom)
               polyline = convertToPolyline(subGeom)
               if polyline is None:
                  return False
               self.polyline = polyline
               self.atGeom = atGeom
               self.atSubGeom = atSubGeom

               # setto il n. della parte
               self.partAt = gripPoint.nVertex

               self.getPointMapTool().setPolyline(self.polyline, self.entity.layer, self.partAt)
               
               return True

      return False


   # ============================================================================
   # convertLineToArc
   # ============================================================================
   def convertLineToArc(self, pt):
      layer = self.entity.layer
      f = self.entity.getFeature()
      if f is None: # non c'è più la feature
         return False
      
      # faccio una copia locale
      polyline = self.polyline.copy()

      tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      linearObject = polyline.getLinearObjectAt(self.partAt)
      if linearObject.whatIs() == "ARC": # se è già arco
         return False
      
      startPt = linearObject.getStartPt()
      endPt = linearObject.getEndPt()
      arc = QadArc()
      if arc.fromStartSecondEndPts(startPt, pt, endPt) == False:
         return False
         
      polyline.insert(self.partAt, arc)
      polyline.remove(self.partAt + 1)

      g = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(g, polyline, self.atGeom, self.atSubGeom)
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
         
      self.plugIn.beginEditCommand("Feature edited", layer)
   
      if self.copyEntities == False:
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False
      else:
         # plugIn, layer, features, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, False, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # convertArcToLine
   # ============================================================================
   def convertArcToLine(self):
      layer = self.entity.layer
      f = self.entity.getFeature()
      if f is None: # non c'è più la feature
         return False
      
      # faccio una copia locale
      polyline = self.polyline.copy()
      tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      linearObject = polyline.getLinearObjectAt(self.partAt)
      if linearObject.whatIs() == "LINE": # se è già segmento retto
         return False
      
      line = QadLine().set(linearObject.getStartPt(), linearObject.getEndPt())

      polyline.insert(self.partAt, line)
      polyline.remove(self.partAt + 1)

      g = self.entity.getQadGeom()
      newQadGeom = setQadGeomAt(g, polyline, self.atGeom, self.atSubGeom)
      # trasformo la geometria nel crs del layer
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))

      self.plugIn.beginEditCommand("Feature edited", layer)
   
      if self.copyEntities == False:
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False
      else:
         # plugIn, layer, features, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, False, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   # ============================================================================
   # waitForConvertToArc
   # ============================================================================
   def waitForConvertToArc(self):
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_gripLineToArcConvert_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_SECOND_PT)

      keyWords = QadMsg.translate("Command_GRIP", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIP", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIP", "eXit")
      prompt = QadMsg.translate("Command_GRIPARCLINECONVERT", "Specify the arc middle point or [{0}]: ").format(keyWords)

      englishKeyWords = "Copy" + "/" + "Undo" + "/" "eXit"
      keyWords += "_" + englishKeyWords

      # si appresta ad attendere un punto o enter o una parola chiave
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      self.step = 1


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
         if self.entity is None: # non ci sono oggetti da stirare
            return True

         if self.lineToArc:
            self.showMsg(QadMsg.translate("Command_GRIPINSERTREMOVEVERTEX", "\n** CONVERT TO ARC **\n"))
            # si appresta ad attendere un punto per definire l'arco
            self.waitForConvertToArc()
         else:
            self.showMsg(QadMsg.translate("Command_GRIPINSERTREMOVEVERTEX", "\n** CONVERT TO LINE **\n"))
            self.convertArcToLine()
            return True
         
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUOVO PUNTO PER DEFINIRE UN ARCO (da step = 1)
      elif self.step == 1:
         ctrlKey = False
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.copyEntities == False:
                     self.skipToNextGripCommand = True
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
            ctrlKey = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_GRIP", "Copy") or value == "Copy":
               # Copia entità lasciando inalterate le originali
               self.copyEntities = True                     
               # si appresta ad attendere un punto per definire l'arco
               self.waitForConvertToArc()
            elif value == QadMsg.translate("Command_GRIP", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
               # si appresta ad attendere un punto per definire l'arco
               self.waitForConvertToArc()
            elif value == QadMsg.translate("Command_GRIP", "eXit") or value == "eXit":
               return True # fine comando
         elif type(value) == QgsPointXY:
            if ctrlKey:
               self.copyEntities = True
   
            self.convertLineToArc(value)

            if self.copyEntities == False:
               return True
            # si appresta ad attendere un punto per definire l'arco
            self.waitForConvertToArc()
         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # fine comando

         return False
