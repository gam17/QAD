# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per i layer
 
                              -------------------
        begin                : 2013-11-15
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
from qgis.gui import *
import re # regular expression


from .qad_msg import QadMsg
from .qad_label import get_labelFieldNames


#===============================================================================
# layerGeometryTypeToStr
#===============================================================================
def layerGeometryTypeToStr(geomType):
   """
   restituisce la stringa corrispondente al tipo di geometria del layer
   """
   msg = ""
   if (type(geomType) == list or type(geomType) == tuple): # se lista di tipi
      for gType in geomType:
         if len(msg) > 0:
            msg = msg + ", " 
         msg = msg + layerGeometryTypeToStr(gType)
   else:
      if geomType == QgsWkbTypes.PointGeometry:
         msg = QadMsg.translate("QAD", "point") 
      elif geomType == QgsWkbTypes.LineGeometry:      
         msg = QadMsg.translate("QAD", "line") 
      elif geomType == QgsWkbTypes.PolygonGeometry:      
         msg = QadMsg.translate("QAD", "polygon") 

   return msg


#===============================================================================
# getCurrLayerEditable
#===============================================================================
def getCurrLayerEditable(canvas, geomType = None):
   """
   Ritorna il layer corrente se é aggiornabile e compatibile con il tipo geomType +
   eventuale messaggio di errore.
   Se <geomType> é una lista allora verifica che sia compatibile con almeno un tipo nella lista <geomType>
   altrimenti se <> None verifica che sia compatibile con il tipo <geomType>
   """
   vLayer = canvas.currentLayer()
   if vLayer is None:
      return None, QadMsg.translate("QAD", "\nNo current layer.\n")
   
   if (vLayer.type() != QgsMapLayer.VectorLayer):
      return None, QadMsg.translate("QAD", "\nThe current layer is not a vector layer.\n")

   if geomType is not None:
      if (type(geomType) == list or type(geomType) == tuple): # se lista di tipi
         if vLayer.geometryType() not in geomType:
            errMsg = QadMsg.translate("QAD", "\nThe geometry type of the current layer is {0} and it is not valid.\n")
            errMsg = errMsg + QadMsg.translate("QAD", "Admitted {1} layer type only.\n")
            errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))
            return None, errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))
      else:
         if vLayer.geometryType() != geomType:
            errMsg = QadMsg.translate("QAD", "\nThe geometry type of the current layer is {0} and it is not valid.\n")
            errMsg = errMsg + QadMsg.translate("QAD", "Admitted {1} layer type only.\n")
            errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))
            return None, errMsg.format(layerGeometryTypeToStr(vLayer.geometryType()), layerGeometryTypeToStr(geomType))

   provider = vLayer.dataProvider()
   if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
      return None, QadMsg.translate("QAD", "\nThe current layer is not editable.\n")
   
   if not vLayer.isEditable():
      return None, QadMsg.translate("QAD", "\nThe current layer is not editable.\n")

   return vLayer, None
  

#===============================================================================
# addPointToLayer
#===============================================================================
def addPointToLayer(plugIn, layer, point, transform = True, refresh = True, check_validity = False, openForm = True):
   """
   Aggiunge un punto ad un layer. Se il punto é già 
   nel sistema di coordinate del layer allora non va trasformato se invece é nel
   sistema map-coordinate allora transform deve essere = True
   """
   if transform:
      transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
      g = QgsGeometry.fromPointXY(transformedPoint)
   else:
      g = QgsGeometry.fromPointXY(point)

   return addGeomToLayer(plugIn, layer, g, None, refresh, check_validity, openForm)
   
#    f = QgsFeature()
#    
#    if transform:
#       transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
#       g = QgsGeometry.fromPointXY(transformedPoint)
#    else:
#       g = QgsGeometry.fromPointXY(point)
# 
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#       
#    f.setGeometry(g)
#    
#    # Add attributefields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
# 
#    # assegno i valori di default
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
# 
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f, True) == False:
#             return False
# 
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
# 
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#       
#    return result


#===============================================================================
# addLineToLayer
#===============================================================================
def addLineToLayer(plugIn, layer, points, transform = True, refresh = True, check_validity = False, openForm = True):
   """
   Aggiunge una linea (lista di punti) ad un layer. Se la lista di punti é già 
   nel sistema di coordinate del layer allora non va trasformata se invece é nel
   sistema  map-coordinate allora transform deve essere = True
   """
   if len(points) < 2: # almeno 2 punti
      return False
   
   if transform:
      layerPoints = []
      for point in points:
         transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
         layerPoints.append(transformedPoint)    
      g = QgsGeometry.fromPolylineXY(layerPoints)
   else:
      g = QgsGeometry.fromPolylineXY(points)
   
   return addGeomToLayer(plugIn, layer, g, None, refresh, check_validity, openForm)
   
#    if len(points) < 2: # almeno 2 punti
#       return False
#      
#    f = QgsFeature()
#    
#    if transform:
#       layerPoints = []
#       for point in points:
#          transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
#          layerPoints.append(transformedPoint)    
#       g = QgsGeometry.fromPolylineXY(layerPoints)
#    else:
#       g = QgsGeometry.fromPolylineXY(points)
# 
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#       
#    f.setGeometry(g)
#    
#    # Add attributefields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
# 
#    # assegno i valori di default
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
# 
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f, True) == False:
#             return False
#       
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
# 
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#       
#    return result


#===============================================================================
# addPolygonToLayer
#===============================================================================
def addPolygonToLayer(plugIn, layer, points, transform = True, refresh = True, check_validity = False, openForm = True):
   """
   Aggiunge un poligono (lista di punti) ad un layer. Se la lista di punti é già 
   nel sistema di coordinate del layer allora non va trasformata se invece é nel
   sistema  map-coordinate allora transform deve essere = True
   """
   if len(points) < 3: # almeno 4 punti (il primo e l'ultimo sono uguali)
      return False
          
   if transform:
      layerPoints = []
      for point in points:
         transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
         layerPoints.append(transformedPoint)      
      g = QgsGeometry.fromPolygonXY([layerPoints])
   else:
      g = QgsGeometry.fromPolygonXY([points])

   return addGeomToLayer(plugIn, layer, g, None, refresh, check_validity, openForm)
   
#    if len(points) < 3: # almeno 4 punti (il primo e l'ultimo sono uguali)
#       return False
#      
#    f = QgsFeature()
#    
#    if transform:
#       layerPoints = []
#       for point in points:
#          transformedPoint = plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point)
#          layerPoints.append(transformedPoint)      
#       g = QgsGeometry.fromPolygonXY([layerPoints])
#    else:
#       g = QgsGeometry.fromPolygonXY([points])
# 
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#          
#    f.setGeometry(g)
#    
#    # Add attributefields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
# 
#    # assegno i valori di default
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
# 
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f, True) == False:
#             return False
# 
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
# 
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#       
#    return result


#===============================================================================
# addGeomToLayer
#===============================================================================
def addGeomToLayer(plugIn, layer, geom, coordTransform = None, refresh = True, check_validity = False, openForm = True):
   """
   Aggiunge una geometria ad un layer. Se la geometria é da convertire allora
   deve essere passato il parametro <coordTransform> di tipo QgsCoordinateTransform.
   refresh controlla la transazione del comando e il refresh del canvas
   """     
   g = QgsGeometry(geom)
   if coordTransform is not None:
      g.transform(coordTransform)            

   if check_validity:
      if not g.isGeosValid():
         return False
   
   f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())
   if refresh == True: plugIn.beginEditCommand("Feature added", layer)
   if layer.addFeature(f) == False: 
      if refresh == True: plugIn.destroyEditCommand()
      return False
    
   if openForm == True:
      if get_Disable_enter_attribute_values_dialog() == False:
         if plugIn.iface.openFeatureForm(layer, f) == False:
            if refresh == True: plugIn.destroyEditCommand()
            re = layer.deleteFeature(f.id())
            return False

   if refresh == True: plugIn.endEditCommand()
   plugIn.setLastEntity(layer, f.id())
      
   return True

#    f = QgsFeature()
#    
#    g = QgsGeometry(geom)
#    if coordTransform is not None:
#       g.transform(coordTransform)            
# 
#    if check_validity:
#       if not g.isGeosValid():
#          return False
#       
#    f.setGeometry(g)
#    
#    # Add attribute fields to feature.
#    fields = layer.fields()
#    f.setFields(fields)
# 
#    # assegno i valori di default
#    provider = layer.dataProvider()
#    for field in fields.toList():
#       i = fields.indexFromName(field.name())
#       f[field.name()] = provider.defaultValue(i)
#   
#    f = QgsVectorLayerUtils.createFeature(layer, g, {}, layer.createExpressionContext())
#     
#    if openForm == True:
#       if get_Disable_enter_attribute_values_dialog() == False:
#          if plugIn.iface.openFeatureForm(layer, f) == False:
#             return False
# 
#    if refresh == True:
#       plugIn.beginEditCommand("Feature added", layer)
# 
#    if layer.addFeature(f):
#       if refresh == True:
#          plugIn.endEditCommand()
#       plugIn.setLastEntity(layer, f.id())
#       result = True
#    else:
#       if refresh == True:
#          plugIn.destroyEditCommand()
#       result = False
#       
#    return result

#===============================================================================
# addGeomsToLayer
#===============================================================================
def addGeomsToLayer(plugIn, layer, geoms, coordTransform = None, refresh = True, check_validity = False):
   """
   Aggiunge le geometrie ad un layer. Se la geometria é da convertire allora
   deve essere passato il parametro <coordTransform> di tipo QgsCoordinateTransform.
   refresh controlla la transazione del comando e il refresh del canvas
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature added", layer)
      
   for geom in geoms:
      if addGeomToLayer(plugIn, layer, geom, coordTransform, False, check_validity) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False
         
   if refresh == True:
      plugIn.endEditCommand()

   return True


#===============================================================================
# addFeatureToLayer
#===============================================================================
def addFeatureToLayer(plugIn, layer, f, coordTransform = None, refresh = True, check_validity = False, openForm = True):
   """
   Aggiunge una feature ad un layer. Se la geometria é da convertire allora
   deve essere passato il parametro <coordTransform> di tipo QgsCoordinateTransform.
   <refresh> controlla la transazione del comando e il refresh del canvas
   """     
   
   if coordTransform is not None:
      g = QgsGeometry(f.geometry())
      g.transform(coordTransform)            
      f.setGeometry(g)

   if check_validity:
      if not f.geometry().isGeosValid():
         return False

   if openForm == True:
      if get_Disable_enter_attribute_values_dialog() == False:
         if plugIn.iface.openFeatureForm(layer, f, True) == False:
            return False
         
   if refresh == True:
      plugIn.beginEditCommand("Feature added", layer)

   # use default value for primary key fields if it's NOT NULL
   provider = layer.dataProvider()
   pkAttrList = layer.primaryKeyAttributes()
   count = layer.fields().count()
   i = 0
   while i < count:
      if i in pkAttrList:
         defVal = provider.defaultValue(i)
         f[i] = defVal
         # if defVal is not None or layer.providerType() == "spatialite":
         #    f[i] = provider.defaultValue(i)         
      i = i + 1
 
   if layer.addFeature(f):
      if refresh == True:
         plugIn.endEditCommand()
         layer.triggerRepaint()
         
      plugIn.setLastEntity(layer, f.id())
      result = True
   else:
      if refresh == True:
         plugIn.destroyEditCommand()
      result = False
      
   return result


#===============================================================================
# addFeaturesToLayer
#===============================================================================
def addFeaturesToLayer(plugIn, layer, features, coordTransform = None, refresh = True, check_validity = False):
   """
   Aggiunge le feature ad un layer. Se la geometria é da convertire allora
   deve essere passato il parametro <coordTransform> di tipo QgsCoordinateTransform.
   <refresh> controlla la transazione del comando e il refresh del canvas
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature added", layer)
      
   for f in features:
      if addFeatureToLayer(plugIn, layer, f, coordTransform, False, check_validity, False) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False
         
   if refresh == True:
      plugIn.endEditCommand()
   
   return True


#===============================================================================
# updateFeatureToLayer
#===============================================================================
def updateFeatureToLayer(plugIn, layer, f, refresh = True, check_validity = False):
   """
   Aggiorna la feature ad un layer.
   refresh controlla la transazione del comando e il refresh del canvas
   """        
   if check_validity:
      if not f.geometry().isGeosValid():
         return False
      
   if refresh == True:
      plugIn.beginEditCommand("Feature modified", layer)

   if layer.updateFeature(f):
      if refresh == True:
         plugIn.endEditCommand()
         
      result = True
   else:
      if refresh == True:
         plugIn.destroyEditCommand()
      result = False
      
   return result


#===============================================================================
# updateFeaturesToLayer
#===============================================================================
def updateFeaturesToLayer(plugIn, layer, features, refresh = True, check_validity = False):
   """
   Aggiorna le features ad un layer.
   refresh controlla la transazione del comando e il refresh del canvas
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature modified", layer)
      
   for f in features:
      if updateFeatureToLayer(plugIn, layer, f, False, check_validity) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False
         
   if refresh == True:
      plugIn.endEditCommand()
   
   return True


#===============================================================================
# deleteFeatureToLayer
#===============================================================================
def deleteFeatureToLayer(plugIn, layer, featureId, refresh = True):
   """
   Cancella la feature da un layer.
   refresh controlla la transazione del comando e il refresh del canvas
   """        
   if refresh == True:
      plugIn.beginEditCommand("Feature deleted", layer)

   if layer.deleteFeature(featureId):
      if refresh == True:
         plugIn.endEditCommand()
         
      result = True
   else:
      if refresh == True:
         plugIn.destroyEditCommand()
      result = False
      
   return result


#===============================================================================
# deleteFeaturesToLayer
#===============================================================================
def deleteFeaturesToLayer(plugIn, layer, featureIds, refresh = True):
   """
   Aggiorna le features ad un layer.
   refresh controlla la transazione del comando e il refresh del canvas
   """
   if refresh == True:
      plugIn.beginEditCommand("Feature deleted", layer)
      
   for featureId in featureIds:
      if deleteFeatureToLayer(plugIn, layer, featureId, False) == False:
         if refresh == True:
            plugIn.destroyEditCommand()
            return False
         
   if refresh == True:
      plugIn.endEditCommand()
   
   return True


#===============================================================================
# getLayersByName
#===============================================================================
def getLayersByName(regularExprName):
   """
   Ritorna la lista dei layer il cui nome soddisfa la regular expression di ricerca
   (per conversione da wildcards vedi la funzione wildCard2regularExpr)
   the regular expression to only match if the text is an exact match is
   (for example, to match for abc, then 1abc1, 1abc, and abc1 would not match):
   use the start and end delimiters: ^abc$
   """
   result = []
   regExprCompiled = re.compile(regularExprName)
   for layer in QgsProject.instance().mapLayers().values():
      if re.match(regExprCompiled, layer.name()):
         if layer.isValid():
            result.append(layer)

   return result


#===============================================================================
# getLayerById
#===============================================================================
def getLayerById(id):
   """
   Ritorna il layer con id noto
   """
   for layer in QgsProject.instance().mapLayers().values():
      if layer.id() == id:
         return layer
   return None


#===============================================================================
# get_symbolRotationFieldName
#===============================================================================
def get_symbolRotationFieldName(layer):
   """
   return rotation field name (or empty string if not set or not supported by renderer) 
   """
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return ""

   try:
      renderer = layer.renderer()
      expr = renderer.symbol().dataDefinedAngle().asExpression()
      expr = QgsSymbolLayerUtils.fieldOrExpressionToExpression(expr)
      columns = expr.referencedColumns()
      if len(columns) == 1:
         for column in columns:
            return column
      else:
         return ""
   except:
      return ""


#===============================================================================
# get_symbolScaleFieldName
#===============================================================================
def get_symbolScaleFieldName(layer):
   """
   return symbol scale field name (or empty string if not set or not supported by renderer) 
   """
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return ""
   
   try:
      renderer = layer.renderer()
      expr = renderer.symbol().dataDefinedSize().asExpression()
      expr = QgsSymbolLayerUtils.fieldOrExpressionToExpression(expr)
      columns = expr.referencedColumns()
      if len(columns) == 1:
         for column in columns:
            return column
      else:
         return ""
      
   except:
      return ""
   


#===============================================================================
# isTextLayer
#===============================================================================
def isTextLayer(layer):
   """
   return True se il layer é di tipo testo 
   """
   # deve essere un VectorLayer di tipo puntuale
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return False
   renderer = layer.renderer()
   if renderer is None: return False
   
   context = QgsRenderContext()
   # deve avere il-i simbolo-i trasparenti almeno entro il 10% 
   for symbol in renderer.symbols(context):
      if symbol.opacity() > 0.1: # 1 for opaque, 0 for invisible
         return False
   # deve avere etichette
   if layer.labeling() is None:
      return False
   
   # verifico che ci sia almeno un campo come etichetta
   labelFieldNames = get_labelFieldNames(layer)
   if len(labelFieldNames) == 0:
      return False
         
   return True


#===============================================================================
# isSymbolLayer
#===============================================================================
def isSymbolLayer(layer):
   """
   return True se il layer é di tipo simbolo 
   """   
   # deve essere un VectorLayer di tipo puntuale
   if (layer.type() != QgsMapLayer.VectorLayer) or (layer.geometryType() != QgsWkbTypes.PointGeometry):
      return False
   # se la rotazione é letta da un campo ricordarsi che per i simboli la rotazione é in senso orario
   # quindi usare l'espressione 360 - <campo rotazione>
   # se non é un layer di tipo testo é di tipo simbolo
   return False if isTextLayer(layer) else True 



#===============================================================================
# get_Disable_enter_attribute_values_dialog
#===============================================================================
def get_Disable_enter_attribute_values_dialog():
   value = QSettings().value('/qgis/digitizing/disable_enter_attribute_values_dialog', True)
   if type(value) == str:
      return False if value.lower() == 'false' else True
   elif type(value) == bool:
      return value
      
   return True 
   
#============================================================================
# INIZIO - Gestione layer temporanei di QAD
#============================================================================


#===============================================================================
# createQADTempLayer
#===============================================================================
def createQADTempLayer(plugIn, GeomType):
   """
   Aggiunge tre liste di geometrie rispettivamente a tre layer temporanei di QAD (uno per tipologia di
   geometria). Se le geometrie sono da convertire allora
   deve essere passato il parametro <coordTransform> di tipo QgsCoordinateTransform.
   <epsg> = the authority identifier for this srs    
   """
   layer = None
   crs = plugIn.iface.mapCanvas().mapSettings().destinationCrs()
   
   if GeomType == QgsWkbTypes.PointGeometry:
      layerName = QadMsg.translate("QAD", "QAD - Temporary points")
      layerList = QgsProject.instance().mapLayersByName(layerName)
      if len(layerList) == 0:
         layer = createMemoryLayer(layerName, "Point", crs)
         QgsProject.instance().addMapLayers([layer], True)
      else:
         layer = layerList[0]
   elif GeomType == QgsWkbTypes.LineGeometry:
      layerName = QadMsg.translate("QAD", "QAD - Temporary lines") 
      layerList = QgsProject.instance().mapLayersByName(layerName)
      if len(layerList) == 0:
         layer = createMemoryLayer(layerName, "LineString", crs)
         QgsProject.instance().addMapLayers([layer], True)
      else:
         layer = layerList[0]
   elif GeomType == QgsWkbTypes.PolygonGeometry:
      layerName = QadMsg.translate("QAD", "QAD - Temporary polygons") 
      layerList = QgsProject.instance().mapLayersByName(layerName)
      if len(layerList) == 0:
         layer = createMemoryLayer(layerName, "Polygon", crs)
         QgsProject.instance().addMapLayers([layer], True)
      else:
         layer = layerList[0]

   layer.startEditing()
   return layer


#===============================================================================
# createMemoryLayer
#===============================================================================
def createMemoryLayer(layerName, geomType, crs):
   """
   Crea un layer in memoria con indice spaziale.
   <layerName> = nome del layer    
   <geomType> = stringa rappresentante il tiipo di geometria:
   "LineString", "Polygon", "MultiPoint", "MultiLineString", or "MultiPolygon"
   <crs> = oggetto QgsCoordinateReferenceSystem che rappresenta il sistema di coordinate
   """   
   # prima creo un layer con un crs sicuramente valido
   # poi setto il sistema di coordinate corretto
   # faccio così perchè se il nome del sistema di coordinate contiene caratteri strani
   # allora il costruttore di QgsVectorLayer fa casino (a volta fa casino ad es. con "USER:100004")
   layer = QgsVectorLayer(geomType + "?crs=epsg:3003&index=yes", layerName, "memory")
   layer.setCrs(crs, False)
   return layer

   
#===============================================================================
# addGeometriesToQADTempLayers
#===============================================================================
def addGeometriesToQADTempLayers(plugIn, pointGeoms = None, lineGeoms = None, polygonGeoms = None, \
                               crs = None, refresh = True):
   """
   Aggiunge tre liste di geometrie rispettivamente a tre layer temporanei di QAD (uno per tipologia di
   geometria). Se le geometrie sono da convertire allora
   deve essere passato il parametro <csr> che definisce il sistema di coordinate delle geometrie.
   """   
   if pointGeoms is not None and len(pointGeoms) > 0:
      layer = createQADTempLayer(plugIn, QgsWkbTypes.PointGeometry)
      if layer is None:
         return False
      if crs is None:
         # plugIn, layer, geoms, coordTransform , refresh, check_validity
         if addGeomsToLayer(plugIn, layer, pointGeoms, None, refresh, False) == False:
            return False
      else:
         # plugIn, layer, geoms, coordTransform , refresh, check_validity
         if addGeomsToLayer(plugIn, layer, pointGeoms, QgsCoordinateTransform(crs, layer.crs(), QgsProject.instance()), \
                            refresh, False) == False:
            return False
      
   if lineGeoms is not None and len(lineGeoms) > 0:
      layer = createQADTempLayer(plugIn, QgsWkbTypes.LineGeometry)
      if layer is None:
         return False
      if crs is None:
         # plugIn, layer, geoms, coordTransform , refresh, check_validity
         if addGeomsToLayer(plugIn, layer, lineGeoms, None, refresh, False) == False:
            return False
      else:
         # plugIn, layer, geoms, coordTransform , refresh, check_validity
         if addGeomsToLayer(plugIn, layer, lineGeoms, QgsCoordinateTransform(crs, layer.crs(), QgsProject.instance()), \
                            refresh, False) == False:
            return False
      
   if polygonGeoms is not None and len(polygonGeoms) > 0:
      layer = createQADTempLayer(plugIn, QgsWkbTypes.PolygonGeometry)
      if layer is None:
         return False
      if crs is None:
         # plugIn, layer, geoms, coordTransform , refresh, check_validity
         if addGeomsToLayer(plugIn, layer, polygonGeoms, None, refresh, False) == False:
            return False
      else:
         # plugIn, layer, geoms, coordTransform , refresh, check_validity
         if addGeomsToLayer(plugIn, layer, polygonGeoms, QgsCoordinateTransform(crs, layer.crs(), QgsProject.instance()), \
                            refresh, False) == False:
            return False
        
   return True


#===============================================================================
# QadLayerStatusEnum class.
#===============================================================================
class QadLayerStatusEnum():
   UNKNOWN = 0
   COMMIT_BY_EXTERNAL = 1 # salvataggio quando questo è richiamato da eventi esterni a QAD
   COMMIT_BY_INTERNAL = 2 # salvataggio quando questo è richiamato da eventi interni a QAD

#===============================================================================
# QadLayerStatusListClass class.
#===============================================================================
class QadLayerStatusListClass():
   def __init__(self):
      self.layerStatusList = [] # lista di coppie (<id layer>-<stato layer>)

   def __del__(self):
      del self.layerStatusList

   def getStatus(self, layerId):
      for layerStatus in self.layerStatusList:
         if layerStatus[0] == layerId:
            return layerStatus[1]
      return QadLayerStatusEnum.UNKNOWN
   
   def setStatus(self, layerId, status):
      # verifico se c'era già in lista
      for layerStatus in self.layerStatusList:
         if layerStatus[0] == layerId:
            layerStatus[1] = status
            return
      # se non c'era lo aggiungo
      self.layerStatusList.append([layerId, status])
      return
   
   def remove(self, layerId):
      i = 0
      for layerStatus in self.layerStatusList:
         if layerStatus[0] == layerId:
            del self.layerStatusList[i]
            return
         else:
            i = i + 1
      return