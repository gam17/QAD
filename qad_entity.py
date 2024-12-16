# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione delle entità
 
                              -------------------
        begin                : 2013-08-22
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
from qgis.core import *
from qgis.utils import iface
import sys


from . import qad_label
from . import qad_layer
from . import qad_stretch_fun
from . import qad_utils
from .qad_multi_geom import *


# ===============================================================================
# QadEntityTypeEnum class.
# ===============================================================================
class QadEntityTypeEnum():
   NONE                = 0
   SYMBOL              = 1
   TEXT                = 2
   LINEAROBJ           = 3 # linea, arco, cerchio, arco di ellisse, ellisse, polilinea (e multi) 
   POLYGON             = 4 # poligono (e multi)


# ===============================================================================
# QadEntity entity class
# ===============================================================================
class QadEntity():
    
   def __init__(self, entity = None):
      self.entityType = QadEntityTypeEnum.NONE
      
      if entity is not None:
         self.set(entity)
      else:    
         self.layer = None
         self.featureId = None
         # geometria di qad singola (punto, linea, arco, cerchio, arco di ellisse, ellisse, polilinea, poligono)      
         # oppure multipla (multipunto, multi oggetto lineare, multi poligono)
         self.qadGeom = None # in crs del canvas per lavorare con coordinate piane xy
         self.isTextualLayer = False
         self.isSymbolLayer = False
         self.rotFldName = "" # campo usato per la rotazione di testi o simboli


   def whatIs(self):
      return "ENTITY"


   # ===============================================================================
   # set
   # ===============================================================================
   def set(self, layer_or_entity, featureId = None):
      self.clear()
      if type(layer_or_entity) == QgsVectorLayer:
         self.layer = layer_or_entity # il layer non si può copiare
         self.featureId = featureId # copio l'identificativo di feature
      else: # layer è una entità
         self.layer = layer_or_entity.layer
         self.featureId = layer_or_entity.featureId
            
         self.entityType = layer_or_entity.entityType
         self.qadGeom = None if layer_or_entity.qadGeom is None else layer_or_entity.qadGeom.copy() # copio la geometria
         self.isTextualLayer = layer_or_entity.isTextualLayer
         self.isSymbolLayer = layer_or_entity.isSymbolLayer
         self.rotFldName = layer_or_entity.rotFldName
            
      return self


   def __initQadInfo(self):
      # inizializza entityType, qadGeom, dimStyle, dimId, isTextualLayer, isSymbolLayer
      if self.qadGeom is not None:
         return self.entityType 

      if self.isInitialized() == False:
         return QadEntityTypeEnum.NONE
      
      self.entityType = QadEntityTypeEnum.NONE
      self.isTextualLayer = False
      self.isSymbolLayer = False
      self.rotFldName = "" # campo usato per la rotazione di testi o simboli

      layerGeomType = self.layer.geometryType()

      if layerGeomType == QgsWkbTypes.PointGeometry:
         if qad_layer.isTextLayer(self.layer):
            self.isTextualLayer = True
            self.entityType = QadEntityTypeEnum.TEXT
            # se la rotazione dipende da un solo campo
            rotFldNames = qad_label.get_labelRotationFieldNames(self.layer)
            if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
               self.rotFldName = rotFldNames[0]         
            
         elif qad_layer.isSymbolLayer(self.layer):
            self.isSymbolLayer = True
            self.entityType = QadEntityTypeEnum.SYMBOL
            self.rotFldName = qad_layer.get_symbolRotationFieldName(self.layer)
            
      elif layerGeomType == QgsWkbTypes.LineGeometry:
            self.entityType = QadEntityTypeEnum.LINEAROBJ
      elif layerGeomType == QgsWkbTypes.PolygonGeometry:
            self.entityType = QadEntityTypeEnum.POLYGON
      
      g = self.getGeometry()
      if g is None:
         return QadEntityTypeEnum.NONE

      self.qadGeom = fromQgsGeomToQadGeom(g, self.layer.crs())
      if self.qadGeom is None: return QadEntityTypeEnum.NONE
      
      qadGeomType = self.qadGeom.whatIs()
      layerGeomType = self.layer.geometryType()
            
      return self.entityType


   def getEntityType(self):
      return self.entityType
   

   def getQadGeom(self, atGeom = None, atSubGeom = None):
      self.__initQadInfo()
      if atGeom is None and atSubGeom is None:
         return self.qadGeom
      else:
         return getQadGeomAt(self.qadGeom, atGeom, atSubGeom)
      

   def isInitialized(self):
      if (self.layer is None) or (self.featureId is None):
         return False
      else:
         return True


   def clear(self):
      self.layer = None
      self.featureId = None
      self.entityType = QadEntityTypeEnum.NONE
      self.qadGeom = None
      self.isTextualLayer = False
      self.isSymbolLayer = False
      self.rotFldName = ""
      
      
   def __eq__(self, entity):
      """self == other"""
      if self.isInitialized() == False or entity.isInitialized() == False :
         return False

      if self.layerId() == entity.layerId() and self.featureId == entity.featureId:
         return True
      else:
         return False    
  
  
   def __ne__(self, entity):
      """self != other"""
      if self.isInitialized() == False or entity.isInitialized() == False:
         return True

      if self.layerId() != entity.layerId() or self.featureId != entity.featureId:      
         return True
      else:
         return False


   def layerId(self):
      if self.isInitialized() == False:
         return None
      return self.layer.id()


   def crs(self):
      if self.isInitialized() == False:
         return None
      return self.layer.crs()


   def copy(self):
      return QadEntity(self)
   
   
   def getFeature(self):
      if self.isInitialized() == False:
         return None
      
      return qad_utils.getFeatureById(self.layer, self.featureId)
      

   def exists(self):
      if self.getFeature() is None:
         return False
      else:
         return True


   def getGeometry(self, destCRS = None):
      feature = self.getFeature()
      if feature is None:
         return None      
      g = QgsGeometry(feature.geometry()) # fa una copia
      if destCRS is not None and destCRS != self.crs():
         coordTransform = QgsCoordinateTransform(self.crs(), destCRS, QgsProject.instance()) # trasformo la geometria in destCRS coordinate
         g.transform(coordTransform)
         
      return g
   


#    questa funzione non ha senso perchè feature è una variabile locale temporanea a cui viene settata la geometria
#    ma poi, a fine funzione, viene distrutta.
#    def setGeometry(self, geom):
#       feature = self.getFeature()
#       if feature is None:
#          return None      
#       return feature.setGeometry(geom)


   def getAttribute(self, attribName):
      feature = self.getFeature()
      if feature is None:
         return None
      try:
         return feature.attribute(attribName)
      except:
         return None

   
   def getAttributes(self):
      feature = self.getFeature()
      if feature is None:
         return None

      return feature.attributes()[:] # fa una copia


   def selectOnLayer(self, incremental = True):
      if self.isInitialized() == True:
         if incremental == False:
            self.layer.removeSelection()

         self.layer.select(self.featureId) # aaaaaaaaaaaaaaaaaaaaaaaaaa qui parte l'evento activate di qad_maptool


   def deselectOnLayer(self):
      if self.isInitialized() == False:
         return False

      self.layer.deselect(self.featureId)


# ===============================================================================
# QadCacheEntitySetIterator
# ===============================================================================
class QadCacheEntitySetIterator():
   # classe per iterare le entità di un QadCacheEntitySet
   def __init__(self, cacheEntitySet):
      self.i = 0
      self.cacheEntitySet = cacheEntitySet

   def __iter__(self):
      return self

   def __next__(self):
      if self.i < len(self.cacheEntitySet.entityList):
         ent = self.cacheEntitySet.entityList[self.i]
         self.i += 1
         return ent
      else:
         raise StopIteration


# ===============================================================================
# QadCacheEntitySet
# ===============================================================================
class QadCacheEntitySet():
   """
   Classe che gestisce una memoria cache per le entità
   """
   
   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self):
      self.entityList = []


   # ============================================================================
   # __del__
   # ============================================================================
   def __del__(self):
      self.clear()


   # ============================================================================
   # clear
   # ============================================================================
   def clear(self):
      # svuota la cache
      for entity in self.entityList: del entity
      del self.entityList[:]


   # ============================================================================
   # isEmpty
   # ============================================================================
   def isEmpty(self):
      return True if len(self.entityList) == 0 else False


   # ============================================================================
   # count
   # ============================================================================
   def count(self):
      return len(self.entityList)


   # ============================================================================
   # getEntity
   # ============================================================================
   def getEntity(self, layerId, featureId):
      for entity in self.entityList:
         if entity.layerId() == layerId and entity.featureId == featureId:
            return entity
      return None


   # ============================================================================
   # appendEntity
   # ============================================================================
   def appendEntity(self, entity):
      clonedEntity = QadEntity(entity)
      self.entityList.append(clonedEntity) # la copio
      return clonedEntity


   # ============================================================================
   # appendEntitySet
   # ============================================================================
   def appendEntitySet(self, entitySet):
      for layerEntitySet in entitySet.layerEntitySetList:
         entityIterator = QadLayerEntitySetIterator(layerEntitySet)
         for entity in entityIterator:
             self.appendEntity(entity)


   # ============================================================================
   # getLayerList
   # ============================================================================
   def getLayerList(self):
      layerList = []
      for entity in self.entityList:
         found = False
         for layer in layerList:
            if entity.layer.id() == layer.id():
               found = True
               break
         if found == False:
            layerList.append(entity.layer)
            
      return layerList
   

   # ============================================================================
   # getBoundingBox
   # ============================================================================
   def getBoundingBox(self):
      # ritorna il rettangolo di occupazione delle entità
      result = None
      for entity in self.entityList:
         entBouningBox = entity.getQadGeom().getBoundingBox()
         if result is None:
            result = entBouningBox
         else:
            result.combineExtentWith(entBouningBox)
      return result


# ===============================================================================
# QadLayerEntitySetIterator
# ===============================================================================
class QadLayerEntitySetIterator():
   # classe per iterare le entità di un QadLayerEntitySet
   def __init__(self, layerEntitySet):
      self.i = 0
      self.layerEntitySet = layerEntitySet
      self.ent = QadEntity()

   def __iter__(self):
      return self

   def __next__(self):
      if self.i < len(self.layerEntitySet.featureIds):
         self.ent.set(self.layerEntitySet.layer, self.layerEntitySet.featureIds[self.i])
         self.i += 1
         return self.ent
      else:
         raise StopIteration
      
   def next(self):
      return self.__next__()


# ===============================================================================
# QadLayerEntitySet entities of a layer class
# ===============================================================================
class QadLayerEntitySet():
    
   def __init__(self, layerEntitySet = None):
      
      if layerEntitySet is not None:
         self.set(layerEntitySet.layer, layerEntitySet.featureIds)
      else:    
         self.layer = None
         self.featureIds = []


   def whatIs(self):
      return "LAYERENTITYSET"


   def isInitialized(self):
      if self.layer is None:
         return False
      else:
         return True


   def isEmpty(self):
      if self.isInitialized() == False:
         return True
      return not self.featureIds


   def count(self):
      if self.isInitialized() == False:
         return 0
      return len(self.featureIds)


   def clear(self):
      if self.isInitialized() == False:
         return 0
      self.layer = None
      del self.featureIds[:] 


   def getEntities(self): # ritorna un iterator
      return QadLayerEntitySetIterator(self)
   
      
   def layerId(self):
      if self.isInitialized() == False:
         return None
      return self.layer.id()

   def crs(self):
      if self.isInitialized() == False:
         return None
      return self.layer.crs()

   def set(self, layer, features = None):
      if type(layer) == QgsVectorLayer:
         self.layer = layer # il layer non si può copiare
         self.featureIds = []       
         if features is not None:
            self.addFeatures(features)
      else: # layer è una entità
         return self.set(layer.layer, layer.featureIds)


   def initByCurrentQgsSelectedFeatures(self, layer):
      self.clear()
      self.layer = layer
      self.featureIds = self.layer.selectedFeatureIds()


   def getFeature(self, featureId):
      if self.isInitialized() == False:
         return None
      return qad_utils.getFeatureById(self.layer, featureId)
   

   def getGeometry(self, featureId):
      feature = self.getFeature(featureId)
      if feature is None:
         return None      
      return QgsGeometry(feature.geometry()) # fa una copia

   def setGeometry(self, featureId, geom):
      feature = self.getFeature(featureId)
      if feature is None:
         return None
      return feature.setGeometry(geom)


   def getGeometryCollection(self, destCRS = None):
      result = []
      if destCRS is not None:
         coordTransform = QgsCoordinateTransform(self.layer.crs(), destCRS, QgsProject.instance()) # trasformo la geometria
      for featureId in self.featureIds:
         g = self.getGeometry(featureId)
         if g is not None:
            if destCRS is not None:
               g.transform(coordTransform)

               # Per un baco sconosciuto quando trasformo la geometria se poi ne faccio un buffer
               # il calcolo dà un risultato sbagliato quando la geometria é nuova o modificata
               # (in cache del layer) e il sistema di coordinate é diverso de quello della mappa corrente
               gType = g.type()
               if g.isMultipart() == False:
                  if gType == QgsWkbTypes.PointGeometry:
                     g = QgsGeometry().fromPointXY(g.asPoint())
                  elif gType == QgsWkbTypes.LineGeometry:
                     g = QgsGeometry().fromPolylineXY(g.asPolyline())
                  elif gType == QgsWkbTypes.PolygonGeometry:
                     g = QgsGeometry().fromPolygonXY(g.asPolygon())
               else:
                  if gType == QgsWkbTypes.PointGeometry:
                     g = QgsGeometry().fromMultiPointXY(g.asMultiPoint())
                  elif gType == QgsWkbTypes.LineGeometry:
                     g = QgsGeometry().fromMultiPolylineXY(g.asMultiPolyline())         
                  elif gType == QgsWkbTypes.PolygonGeometry:
                     g = QgsGeometry().fromMultiPolygonXY(g.asMultiPolygon())                     
                                   
            result.append(g)
      return result


   def getFeatureCollection(self):
      result = []
      for featureId in self.featureIds:
         f = self.getFeature(featureId)
         if f is not None:
            result.append(f)
      return result

   
   def selectOnLayer(self, incremental = True):
      if self.isInitialized() == True:            
         if len(self.featureIds) > 0:
            if incremental == False:
               self.layer.removeSelection()
            
            self.layer.select(self.featureIds)
         else:
            if incremental == False:
               self.layer.removeSelection()
               

   def deselectOnLayer(self):
      if self.isInitialized() == True:
         if len(self.featureIds) > 0:
            self.layer.deselect(self.featureIds)

   
   def containsFeature(self, feature):
      if self.isInitialized() == False:
         return False

      if type(feature) == QgsFeature:     
         return feature.id() in self.featureIds
      else:
         return feature in self.featureIds
           

   def containsEntity(self, entity):
      if self.isInitialized() == False:
         return False
      
      if self.layerId() != entity.layerId(): 
         return False
      return containsFeature(entity.featureId)
   
                                      
   def addFeature(self, feature):
      if self.isInitialized() == False:
         return False
      
      if type(feature) == QgsFeature:
         if self.containsFeature(feature.id()) == False:    
            self.featureIds.append(feature.id())
            return True
         else:
            return False
      else:
         if self.containsFeature(feature) == False:    
            self.featureIds.append(feature)
            return True
         else:
            return False


   def removeFeature(self, feature):
      if self.isInitialized() == False:
         return False
      
      try:
         if type(feature) == QgsFeature:     
            return self.featureIds.remove(feature.id())
         else:
            return self.featureIds.remove(feature)
      except:
         return None


   def addEntity(self, entity):
      if self.isInitialized() == False:
         self.set(entity.layer)
      else:
         if self.layerId() != entity.layerId(): 
            return
      
      self.addFeature(entity.featureId)


   def removeEntity(self, entity):
      if self.isInitialized() == False:
         return False

      if self.layerId() != entity.layerId(): 
         return False
         
      return self.removeFeature(entity.featureId)


   def addFeatures(self, features):
      if self.isInitialized() == False:
         return None
      for feature in features:
         if type(feature) == QgsFeature:
            self.addFeature(feature.id())
         else:
            self.addFeature(feature) # featureId


   def addLayerEntitySet(self, layerEntitySet):
      if self.isInitialized() == False:
         self.set(layerEntitySet.layer)
      else:
         if self.layerId() != layerEntitySet.layerId():
            return
      self.addFeatures(layerEntitySet.featureIds)
      
      
   def unite(self, layerEntitySet):
      if self.isInitialized() == False:
         return
      
      if self.layerId() == layerEntitySet.layerId():
         self.featureIds = list(set.union(set(self.featureIds), set(layerEntitySet.featureIds)))


   def intersect(self, layerEntitySet):
      if self.isInitialized() == False:
         return
      
      if self.layerId() == layerEntitySet.layerId():
         self.featureIds = list(set(self.featureIds) & set(layerEntitySet.featureIds))    


   def subtract(self, layerEntitySet):
      if self.isInitialized() == False:
         return
      
      if self.layerId() == layerEntitySet.layerId():      
         self.featureIds = list(set(self.featureIds) - set(layerEntitySet.featureIds)) 


   def getNotExistingFeaturedIds(self):
      featureIds = []
      if self.isInitialized() == True:
         feature = QadEntity()
         for featureId in self.featureIds:
            feature.set(self.layer, featureId)
            if not feature.exists():
               featureIds.append(featureId)
      return featureIds
      

   def removeNotExisting(self):
      featureIds = self.getNotExistingFeaturedIds()
      self.featureIds = list(set(self.featureIds) - set(featureIds))    


   def boundingBox(self):
      # ritorna il rettangolo di occupazione delle entita dl layer
      result = None
      geoms = self.getGeometryCollection()
      for g in geoms:
         if result is None:
            result = g.boundingBox()
         else:
            result.combineExtentWith(g.boundingBox())
      return result


# ===============================================================================
# QadEntitySetIterator
# ===============================================================================
class QadEntitySetIterator():
   # classe per iterare le entità di un QadEntitySet
   def __init__(self, entitySet):
      self.i = 0
      self.entitySet = entitySet
      self.layerEntitySetIterator = None
      self.ent = QadEntity()

   def __iter__(self):
      return self

   def __next__(self):
      while self.i < len(self.entitySet.layerEntitySetList):
         if self.layerEntitySetIterator is None:
            self.layerEntitySetIterator = QadLayerEntitySetIterator(self.entitySet.layerEntitySetList[self.i])
         try:
            return self.layerEntitySetIterator.next()
         except StopIteration:
            self.i += 1
            del self.layerEntitySetIterator
            self.layerEntitySetIterator = None
      raise StopIteration


# ===============================================================================
# QadEntitySet entities of a layers class
# ===============================================================================
class QadEntitySet():
    
   def __init__(self, entitySet = None):
      self.layerEntitySetList = []
      if entitySet is not None:
         self.set(entitySet)


   def whatIs(self):
      return "ENTITYSET"


   def isEmpty(self):
      for layerEntitySet in self.layerEntitySetList:
         if layerEntitySet.isEmpty() == False:
            return False
      return True


   def count(self):
      tot = 0
      for layerEntitySet in self.layerEntitySetList:
         tot = tot + layerEntitySet.count()
      return tot


   def clear(self):
      del self.layerEntitySetList[:] 


   def set(self, entitySet):      
      self.clear()
      for layerEntitySet in entitySet.layerEntitySetList:
         self.addLayerEntitySet(layerEntitySet)


   def initByCurrentQgsSelectedFeatures(self, layers):
      self.clear()

      for layer in layers:
         if layer.selectedFeatureCount() > 0:
            layerEntitySet = QadLayerEntitySet()
            layerEntitySet.initByCurrentQgsSelectedFeatures(layer)
            self.layerEntitySetList.append(layerEntitySet)


   def findLayerEntitySet(self, layer):
      if layer is None:
         return None
      if type(layer) == QgsVectorLayer: # layer
         return self.findLayerEntitySet(layer.id())     
      elif type(layer) == unicode: # id del layer
         for layerEntitySet in self.layerEntitySetList:
            if layerEntitySet.layerId() == layer:
               return layerEntitySet
         return None
      else: # QadLayerEntitySet
         return self.findLayerEntitySet(layer.layer)     


   def getLayerList(self):
      layerList = []
      for layerEntitySet in self.layerEntitySetList:
         layerList.append(layerEntitySet.layer)
      return layerList
   

   def getGeometryCollection(self, destCRS = None):
      result = []
      for layerEntitySet in self.layerEntitySetList:
         partial = layerEntitySet.getGeometryCollection(destCRS)
         if partial is not None:
            result.extend(partial)
      return result
   

   def getFeatureCollection(self):
      result = []
      for layerEntitySet in self.layerEntitySetList:
         partial = layerEntitySet.getFeatureCollection()
         if partial is not None:
            result.extend(partial)
      return result


   def selectOnLayer(self, incremental = True):
      for layerEntitySet in self.layerEntitySetList:
         layerEntitySet.selectOnLayer(incremental)


   def deselectOnLayer(self):
      for layerEntitySet in self.layerEntitySetList:
         layerEntitySet.deselectOnLayer()

   
   def containsEntity(self, entity):
      layerEntitySet = self.findLayerEntitySet(entity.layer)
      if layerEntitySet is None: 
         return False
      return layerEntitySet.containsFeature(entity.featureId)
      

   def addEntity(self, entity):
      if entity is None or entity.isInitialized() == False:
         return False
      layerEntitySet = self.findLayerEntitySet(entity.layer)
      if layerEntitySet is None: 
         layerEntitySet = QadLayerEntitySet()
         layerEntitySet.set(entity.layer)
         self.layerEntitySetList.append(layerEntitySet)
      return layerEntitySet.addFeature(entity.featureId)
         

   def removeEntity(self, entity):
      layerEntitySet = self.findLayerEntitySet(entity.layer)
      if layerEntitySet is None:
         return False
      return layerEntitySet.removeFeature(entity.featureId)
      
      
   def removeLayerEntitySet(self, layer):
      i = 0
      for layerEntitySet in self.layerEntitySetList:
         if layerEntitySet.id() == layer.id():
            del layerEntitySet[i]
            return True
         i = i + 1
      return False


   def addLayerEntitySet(self, layerEntitySet):      
      _layerEntitySet = self.findLayerEntitySet(layerEntitySet)
      if _layerEntitySet is None:
         _layerEntitySet = QadLayerEntitySet()
         _layerEntitySet.set(layerEntitySet.layer)
         self.layerEntitySetList.append(_layerEntitySet)
      _layerEntitySet.addFeatures(layerEntitySet.featureIds)
     
      
   def unite(self, entitySet):
      if entitySet is None:
         return
      for layerEntitySet in entitySet.layerEntitySetList:
         _layerEntitySet = self.findLayerEntitySet(layerEntitySet)
         if _layerEntitySet is None:
            _layerEntitySet = QadLayerEntitySet()
            _layerEntitySet.set(layerEntitySet.layer)
            self.layerEntitySetList.append(_layerEntitySet)
         _layerEntitySet.unite(layerEntitySet)
       

   def intersect(self, entitySet):
      if entitySet is None:
         return
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         _layerEntitySet = self.layerEntitySetList[i]
         layerEntitySet = entitySet.findLayerEntitySet(_layerEntitySet)
         if layerEntitySet is None:
            del self.layerEntitySetList[i]
         else:
            _layerEntitySet.intersect(layerEntitySet)


   def subtract(self, entitySet):
      if entitySet is None:
         return
      for _layerEntitySet in self.layerEntitySetList:         
         layerEntitySet = entitySet.findLayerEntitySet(_layerEntitySet)
         if layerEntitySet is not None:
            _layerEntitySet.subtract(layerEntitySet)


   def removeNotExisting(self):
      for layerEntitySet in self.layerEntitySetList:         
         layerEntitySet.removeNotExisting()


   def removeNotEditable(self):
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         layerEntitySet = self.layerEntitySetList[i]
         if layerEntitySet.layer.isEditable() == False:
            del self.layerEntitySetList[i]
                  

   def removeGeomType(self, type):
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         layerEntitySet = self.layerEntitySetList[i]
         if layerEntitySet.layer.geometryType() == type:
            del self.layerEntitySetList[i]


   def purge(self):
      # rimuove i layer con zero oggetti
      for i in range(len(self.layerEntitySetList) - 1, -1, -1):
         layerEntitySet = self.layerEntitySetList[i]
         if layerEntitySet.count() == 0:
            del self.layerEntitySetList[i]
                  

   def boundingBox(self, destCRS):
      # ritorna il rettangolo di occupazione del selset
      result = None
      for layerEntitySet in self.layerEntitySetList:
         partial = layerEntitySet.boundingBox()
         if partial is not None:
            coordTransform = QgsCoordinateTransform(layerEntitySet.crs(), destCRS, QgsProject.instance()) # trasformo la geometria
            if result is None:
               result = QgsRectangle(coordTransform.transform(partial.xMinimum(), partial.yMinimum()), \
                                     coordTransform.transform(partial.xMaximum(), partial.yMaximum()))
            else:
               result.combineExtentWith(QgsRectangle(coordTransform.transform(partial.xMinimum(), partial.yMinimum()), \
                                        coordTransform.transform(partial.xMaximum(), partial.yMaximum())))
      return result


# ===============================================================================
# getSelSet
# ===============================================================================
def getSelSet(mode, mQgsMapTool, points = None, \
              layersToCheck = None, checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
              onlyEditableLayers = False):
   """
   dato un QgsMapTool, una modalità di selezione e una lista opzionale di punti (in map coordinates),
   la funzione cerca le entità.
   mode = "C"  -> Crossing selection (inside and crossing)
          "CO" -> Crossing objects (inside and crossing)
          "CP" -> Crossing polygon (inside and crossing)
          "F"  -> Fence selection (crossing)
          "W"  -> Window selection (inside)
          "WO" -> Window objects (inside)
          "WP" -> Windows polygon (inside)
          "X"  -> all          
   layersToCheck = opzionale, lista dei layer in cui cercare
   checkPointLayer = opzionale, considera i layer di tipo punto
   checkLineLayer = opzionale, considera i layer di tipo linea
   checkPolygonLayer = opzionale, considera i layer di tipo poligono
   onlyEditableLayers = opzionale, considera i layer editabili
   Restituisce un QadEntitySet in caso di successo altrimenti None 
   """
        
   if checkPointLayer == False and checkLineLayer == False and checkPolygonLayer == False:
      return None
   
   entity = QadEntity()
   result = QadEntitySet()
   feature = QgsFeature()
   
   #QApplication.setOverrideCursor(Qt.WaitCursor)
   
   if layersToCheck is None:
      # Tutti i layer visibili
      _layers = qad_utils.getVisibleVectorLayers(mQgsMapTool.canvas) # Tutti i layer vettoriali visibili
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
         provider = layer.dataProvider()  

         if mode.upper() == "X": # take all features
            # fetchAttributes, fetchGeometry, rectangle, useIntersect             
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True,  None, False)):
               entity.set(layer, feature.id())
               result.addEntity(entity)
               
         elif mode.upper() == "C": # crossing selection
            p1 = mQgsMapTool.toLayerCoordinates(layer, points[0])
            p2 = mQgsMapTool.toLayerCoordinates(layer, points[1])
            selectRect = QgsRectangle(p1, p2)
            # Select features in rectangle
            # fetchAttributes, fetchGeometry, rectangle, useIntersect             
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):
               entity.set(layer, feature.id())
               result.addEntity(entity)
               
         elif mode.upper() == "W": # window selection
            p1 = mQgsMapTool.toLayerCoordinates(layer, points[0])
            p2 = mQgsMapTool.toLayerCoordinates(layer, points[1])
            selectRect = QgsRectangle(p1, p2)
            g = QgsGeometry.fromRect(selectRect)
            # Select features in rectangle
            # fetchAttributes, fetchGeometry, rectangle, useIntersect             
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):            
               # solo le feature completamente interne al rettangolo
               if g.contains(feature.geometry()):
                  entity.set(layer, feature.id())
                  result.addEntity(entity)
                  
         elif mode.upper() == "CP": # crossing polygon
            polyline = []      
            for point in points:
               polyline.append(mQgsMapTool.toLayerCoordinates(layer, point))
            
            g = QgsGeometry.fromPolygonXY([polyline])
            # Select features in the polygon bounding box
            # fetchAttributes, fetchGeometry, rectangle, useIntersect             
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, g.boundingBox(), True)):            
               # solo le feature intersecanti il poligono
               if g.intersects(feature.geometry()):                     
                  entity.set(layer, feature.id())
                  result.addEntity(entity)
                  
         elif mode.upper() == "WP": # windows polygon
            polyline = []      
            for point in points:
               polyline.append(mQgsMapTool.toLayerCoordinates(layer, point))
            
            g = QgsGeometry.fromPolygonXY([polyline])
            # Select features in the polygon bounding box
            # fetchAttributes, fetchGeometry, rectangle, useIntersect             
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, g.boundingBox(), True)):
               # solo le feature completamente interne al poligono
               if g.contains(feature.geometry()):                     
                  entity.set(layer, feature.id())
                  result.addEntity(entity)
                  
         elif mode.upper() == "CO": # crossing object
            # points é in questo caso un QgsGeometry  
            g = QgsGeometry(points)
            if mQgsMapTool.canvas.mapSettings().destinationCrs() != layer.crs():       
               coordTransform = QgsCoordinateTransform(mQgsMapTool.canvas.mapSettings().destinationCrs(), \
                                                       layer.crs(), \
                                                       QgsProject.instance()) # trasformo la geometria
               g.transform(coordTransform)
                        
            # Select features in the object bounding box
            if g.isMultipart() == False and g.type() == QgsWkbTypes.PointGeometry:            
               Tolerance = QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) # leggo la tolleranza
               ToleranceInMapUnits = QgsTolerance.toleranceInMapUnits(Tolerance, layer, \
                                                                      mQgsMapTool.canvas.mapSettings(), \
                                                                      QgsTolerance.Pixels)
      
               pt = g.asPoint()
               # QgsRectangle (double xmin=0, double ymin=0, double xmax=0, double ymax=0)
               selectRect = QgsRectangle(pt.x() - ToleranceInMapUnits, pt.y() - ToleranceInMapUnits, \
                                         pt.x() + ToleranceInMapUnits, pt.y() + ToleranceInMapUnits)
               # fetchAttributes, fetchGeometry, rectangle, useIntersect             
               request = qad_utils.getFeatureRequest([], True, selectRect, True)
            else:
               # fetchAttributes, fetchGeometry, rectangle, useIntersect             
               request = qad_utils.getFeatureRequest([], True, g.boundingBox(), True)
               
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(request):
               # solo le feature intersecanti l'oggetto
               if g.intersects(feature.geometry()):
                  entity.set(layer, feature.id())
                  result.addEntity(entity)
                  
         elif mode.upper() == "WO": # windows object
            # points é in questo caso un QgsGeometry  
            g = QgsGeometry(points)
            if mQgsMapTool.canvas.mapSettings().destinationCrs() != layer.crs():       
               coordTransform = QgsCoordinateTransform(mQgsMapTool.canvas.mapSettings().destinationCrs(), \
                                                       layer.crs(), \
                                                       QgsProject.instance()) # trasformo la geometria
               g.transform(coordTransform)

            # Select features in the object bounding box
            if g.isMultipart() == False and g.type() == QgsWkbTypes.PointGeometry:            
               Tolerance = QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) # leggo la tolleranza
               ToleranceInMapUnits = QgsTolerance.toleranceInMapUnits(Tolerance, layer, \
                                                                      mQgsMapTool.canvas.mapSettings(), \
                                                                      QgsTolerance.Pixels)
      
               pt = g.asPoint()
               selectRect = QgsRectangle(pt.x() - ToleranceInMapUnits, pt.y() - ToleranceInMapUnits, \
                                         pt.x() + ToleranceInMapUnits, pt.y() + ToleranceInMapUnits)
               # fetchAttributes, fetchGeometry, rectangle, useIntersect             
               request = qad_utils.getFeatureRequest([], True, selectRect, True)
            else:
               # fetchAttributes, fetchGeometry, rectangle, useIntersect
               request = qad_utils.getFeatureRequest([], True, g.boundingBox(), True)
                  
            gList = []      
            if g.type() == QgsWkbTypes.LineGeometry:               
               polygon = QadPolygon()
               
               if g.isMultipart() == False:
                  # se g è una linestring allora provo a convertirla in un poligono
                  if polygon.fromPolygon([g.asPolyline()]) == True:
                     gList.append(QgsGeometry.fromPolygonXY(polygon.asPolygon()))
               else:               
                  # se g è una multilinestring allora provo a convertirla in una lista di poligoni se le linestring sono chiuse
                  multipolyline = g.asMultiPolyline()
                  for polyline in multipolyline:      
                     if polygon.fromPolygon([polyline]) == True:
                        gList.append(QgsGeometry.fromPolygonXY(polygon.asPolygon()))
            else: # se non è una linestring
               if g.type() == QgsWkbTypes.PolygonGeometry:
                  gList.append(g)    
            
            # solo le feature completamente interne all'oggetto
            for feature in layer.getFeatures(request):
               for g in gList:                         
                  if g.contains(feature.geometry()):                     
                     entity.set(layer, feature.id())
                     result.addEntity(entity)
                     
         elif mode.upper() == "F": # fence
            polyline = []      
            for point in points:
               polyline.append(mQgsMapTool.toLayerCoordinates(layer, point))
               
            g = QgsGeometry.fromPolylineXY(polyline)
            # Select features in the polyline bounding box
            # fetchAttributes, fetchGeometry, rectangle, useIntersect
            for feature in layer.getFeatures(qad_utils.getFeatureRequest([], True, g.boundingBox(), True)):                       
               # solo le feature che intersecano la polyline
               if g.intersects(feature.geometry()):                     
                  entity.set(layer, feature.id())
                  result.addEntity(entity)
            
   #QApplication.restoreOverrideCursor()
   return result
