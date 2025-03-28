# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire in modalità cache le aree di un layer
 
                              -------------------
        begin                : 2013-03-08
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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *


from .qad_layer import createMemoryLayer


# ===============================================================================
# QadLayerCacheGeoms class.
# ===============================================================================
class QadLayerCacheGeoms():
   """
   Classe che gestisce la cache delle geometrie di un layer
   """
      
   
   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, layer):
      self.layer = layer
      self.cacheLayer = None
      self.IsEmpty = True
      # creo un layer temporaneo in memoria
      self.__create_internal_layer()

      self.layer.featureAdded.connect(self.onFeatureAdded)
      self.layer.featureDeleted.connect(self.onFeatureDeleted)
      self.layer.geometryChanged.connect(self.onGeometryChanged)


   def __create_internal_layer(self):
      if self.cacheLayer is not None:
         del self.cacheLayer
      # creo un layer temporaneo in memoria
      self.cacheLayer = createMemoryLayer("QadLayerCacheArea", getStrLayerGeomType(self.layer), self.layer.crs())
      
      provider = self.cacheLayer.dataProvider()
      provider.addAttributes([QgsField("index", QMetaType.Int, "Int")])
      self.cacheLayer.updateFields()
      
      if provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
         provider.createSpatialIndex()

   
   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      del self.cacheLayer
      self.layer.featureAdded.disconnect(self.onFeatureAdded)
      self.layer.featureDeleted.disconnect(self.onFeatureDeleted)
      self.layer.geometryChanged.disconnect(self.onGeometryChanged)


   # ============================================================================
   # insertFeature
   # ============================================================================
   def insertFeature(self, feature):
      # inserisce questa feature nella cache
      if self.cacheLayer.startEditing() == False:
         return False
      
      geom = feature.geometry()
      if geom is None:
         return
      newFeature = QgsFeature()
      newFeature.initAttributes(1)
      newFeature.setAttribute(0, feature.id())
      newFeature.setGeometry(geom)
      if self.cacheLayer.addFeature(newFeature):
         if self.cacheLayer.commitChanges():
            self.IsEmpty = False
            return True
         else:
            return False
      else:
         self.cacheLayer.rollBack()
         return False


   # ============================================================================
   # insertFeatures
   # ============================================================================
   def insertFeatures(self, features):
      if len(features) == 0:
         return
      
      # inserisce questa feature nella cache
      if self.cacheLayer.startEditing() == False:
         return False

      newFeature = QgsFeature()
      newFeature.initAttributes(1)
      
      for feature in features:
         geom = feature.geometry()
         if geom is None:
            continue
         newFeature.setAttribute(0, feature.id())
         newFeature.setGeometry(geom)
         if self.cacheLayer.addFeature(newFeature) == False:
            self.cacheLayer.rollBack()
            return False

      
      if self.cacheLayer.commitChanges():
         self.IsEmpty = False
         return True
      else:
         # prova a vedere i messaggi di errore con il debug self.cacheLayer.commitErrors()
         self.cacheLayer.rollBack()
         return False


   # ============================================================================
   # __deleteFeature
   # ============================================================================
   def __deleteFeature(self, fid):
      # inserisce questa feature nella cache
      if self.cacheLayer.startEditing() == False:
         return False

      if self.cacheLayer.deleteFeature(fid):
         return self.cacheLayer.commitChanges()
      else:
         self.cacheLayer.rollBack()
         return False


   # ============================================================================
   # __updateFeature
   # ============================================================================
   def __updateFeature(self, fid, geom):
      feature = QgsFeature()
      if self.cacheLayer.getFeatures(QgsFeatureRequest().setFilterFid(fid)).nextFeature(feature):
         # aggiorna la geometria di questa feature nella cache
         feature.setGeometry(geom)

         if self.cacheLayer.startEditing() == False:
            return False
         
         if self.cacheLayer.updateFeature(feature):
            return self.cacheLayer.commitChanges()
         else:
            self.cacheLayer.rollBack()
      
      return False


   # ============================================================================
   # getFeatures
   # ============================================================================
   def getFeatures(self, rect):
      if self.IsEmpty:
         return []
      feature = QgsFeature()
      featureList = []
      featureIterator = self.cacheLayer.getFeatures(getFeatureRequest(rect, True))
      for feature in featureIterator:
         featureList.append(QgsFeature(feature))
      
      return featureList


   # ============================================================================
   # extent
   # ============================================================================
   def extent(self, rect):
      return self.cacheLayer.extent()


   # ============================================================================
   # onFeatureAdded
   # ============================================================================
   def onFeatureAdded(self, fid):
      feature = QgsFeature()
      if self.layer.getFeatures(QgsFeatureRequest().setFilterFid(fid)).nextFeature(feature):
         return self.insertFeature(feature)
      return False
   
   
   # ============================================================================
   # onFeatureDeleted
   # ============================================================================
   def onFeatureDeleted(self, fid):
      feature = QgsFeature()
      if self.cacheLayer.getFeatures(QgsFeatureRequest().setFilterExpression("\"index\"=" + str(fid))).nextFeature(feature):
         return self.__deleteFeature(feature.id())
      return False


   # ============================================================================
   # onGeometryChanged
   # ============================================================================
   def onGeometryChanged(self, fid, geom):
      feature = QgsFeature()
      if self.cacheLayer.getFeatures(QgsFeatureRequest().setFilterFid(fid)).nextFeature(feature):
         return self.__updateFeature(feature.id(), geom)
      
      return False


# ===============================================================================
# QadLayerCacheGeomsDict class.
# ===============================================================================
class QadLayerCacheGeomsDict():
   """
   Classe che gestisce un dizionario delle chache delle geometrie dei layer
   """


   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, canvas = None):
      self.canvas = canvas
      
      self.layersToCheck = None
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.onlyEditableLayers = False
      
      self.layerCacheAreaDict = dict() # dizionario delle chache delle aree dei layer
      if self.canvas is not None:
         self.canvas.extentsChanged.connect(self.onExtentsChanged)
         self.canvas.layersChanged.connect(self.onLayersChanged)
         #self.canvas.layerStyleOverridesChanged.connect(self.onLayerStyleOverridesChanged) da qgis 2.12

   
   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      del self.layerCacheAreaDict
      if self.canvas is not None:
         self.canvas.extentsChanged.disconnect(self.onExtentsChanged)
         self.canvas.layersChanged.disconnect(self.onLayersChanged)
         # self.canvas.layerStyleOverridesChanged.disconnect(self.onLayerStyleOverridesChanged) da qgis 2.12


   # ============================================================================
   # insertFeature
   # ============================================================================
   def insertFeature(self, layer, feature):
      # inserisce questa feature nella cache
      layerId = layer.id()
      # verifica se layer esiste già nel dizionario
      if layerId not in self.layerCacheAreaDict:
         cacheArea = QadLayerCacheGeoms(layer)
         self.layerCacheAreaDict[layerId] = cacheArea
      else:
         cacheArea = self.layerCacheAreaDict[layerId]
      cacheArea.insertFeature(feature)


   # ============================================================================
   # insertFeatures
   # ============================================================================
   def insertFeatures(self, layer, features):
      if len(features) == 0:
         return True
      # inserisce questa feature nella cache
      layerId = layer.id()
      # verifica se layer esiste già nel dizionario
      if layerId not in self.layerCacheAreaDict:
         cacheArea = QadLayerCacheGeoms(layer)
         self.layerCacheAreaDict[layerId] = cacheArea
      else:
         cacheArea = self.layerCacheAreaDict[layerId]
      return cacheArea.insertFeatures(features)


   # ============================================================================
   # refreshOnMapCanvasExtent
   # ============================================================================
   def refreshOnMapCanvasExtent(self, layersToCheck = None, \
                                checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True, \
                                onlyEditableLayers = False):
      """
      la funzione aggiorna la cache usando l'estensione dello schermo corrente.
      layersToCheck = opzionale, lista dei layer in cui cercare
      checkPointLayer = opzionale, considera i layer di tipo punto
      checkLineLayer = opzionale, considera i layer di tipo linea
      checkPolygonLayer = opzionale, considera i layer di tipo poligono
      onlyEditableLayers = per cercare solo nei layer modificabili
      """
      if self.canvas is None:
         return False
      
      self.layersToCheck = layersToCheck
      self.checkPointLayer = checkPointLayer
      self.checkLineLayer = checkLineLayer
      self.checkPolygonLayer = checkPolygonLayer
      self.onlyEditableLayers = onlyEditableLayers
      
      if checkPointLayer == False and checkLineLayer == False and checkPolygonLayer == False:
         return True

      boundBox = self.canvas.extent() # in map coordinate

      if layersToCheck is None:
         # Tutti i layer visibili
         _layers = self.canvas.layers()
      else:
         # solo la lista passata come parametro
         _layers = layersToCheck
      
      for layer in _layers: # ciclo sui layer
         # considero solo i layer vettoriali che sono filtrati per tipo
         if (layer.type() == QgsMapLayer.VectorLayer) and \
             ((layer.geometryType() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
              (layer.geometryType() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
              (layer.geometryType() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)) and \
              (onlyEditableLayers == False or layer.isEditable()):                      

            # se il layer non è visibile a questa scala
            if layer.hasScaleBasedVisibility() and \
               (self.canvas.mapSettings().scale() > layer.minimumScale() or self.canvas.mapSettings().scale() < layer.maximumScale()):
               continue

            rect = self.canvas.mapSettings().mapToLayerCoordinates(layer, boundBox) # map to layer coordinate
               
            if self.refreshOnRectOnLayer(layer, rect) == False:
               return False
            
      return True


   # ===============================================================================
   # refreshOnRectOnLayer
   # ===============================================================================
   def refreshOnRectOnLayer(self, layer, rect):
      featureList = []
      featureIterator = layer.getFeatures(getFeatureRequest(rect, False))
      feature = QgsFeature()
      for feature in featureIterator:
         featureList.append(QgsFeature(feature))
   
      # non ho trovato oggetti quindi lo segno in cache
      return self.insertFeatures(layer, featureList)

   
   # ============================================================================
   # onExtentsChanged
   # ============================================================================
   def onExtentsChanged(self):
      self.refreshOnMapCanvasExtent(self.layersToCheck, \
                                    self.checkPointLayer, self.checkLineLayer, self.checkPolygonLayer, \
                                    self.onlyEditableLayers)


   # ============================================================================
   # onLayersChanged
   # ============================================================================
   def onLayersChanged(self):
      self.refreshOnMapCanvasExtent(self.layersToCheck, \
                                    self.checkPointLayer, self.checkLineLayer, self.checkPolygonLayer, \
                                    self.onlyEditableLayers)


   # ============================================================================
   # onLayerStyleOverridesChanged
   # ============================================================================
   def onLayerStyleOverridesChanged(self):
      self.refreshOnMapCanvasExtent(self.layersToCheck, \
                                    self.checkPointLayer, self.checkLineLayer, self.checkPolygonLayer, \
                                    self.onlyEditableLayers)
      
      
   # ============================================================================
   # getFeatures
   # ============================================================================
   def getFeatures(self, layer, rect):
      layerId = layer.id()
      # verifica se layer esiste già nel dizionario
      if layerId in self.layerCacheAreaDict:
         return self.layerCacheAreaDict[layerId].getFeatures(rect)
      else:
         return []



################################
# funzioni generiche


# ============================================================================
# getFeatureRequest
# ============================================================================
def getFeatureRequest(rect, SubsetOfAttribute):
   request = QgsFeatureRequest()
   request.setFilterRect(rect)
   if SubsetOfAttribute == False:
      request.setSubsetOfAttributes([])
   return request


# ===============================================================================
# getStrLayerGeomType
# ===============================================================================
def getStrLayerGeomType(layer):
   wkbTypeLayer = layer.wkbType()   
   if wkbTypeLayer == QgsWkbTypes.NoGeometry:
      return "NoGeometry"
   
   gType = layer.geometryType()
   if QgsWkbTypes.isMultiType(wkbTypeLayer) == False:
      if gType == QgsWkbTypes.PointGeometry:
         return "Point"
      elif gType == QgsWkbTypes.LineGeometry:
         return "LineString"
      elif gType == QgsWkbTypes.PolygonGeometry:
         return "Polygon"
   else:
      if gType == QgsWkbTypes.PointGeometry:
         return "MultiPoint"
      elif gType == QgsWkbTypes.LineGeometry:
         return "MultiLineString"
      elif gType == QgsWkbTypes.PolygonGeometry:
         return "MultiPolygon"

   return "NoGeometry"     