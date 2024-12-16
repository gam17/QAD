# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool in ambito del comando lengthen
 
                              -------------------
        begin                : 2015-10-06
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


from qgis.core import QgsWkbTypes


import math


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum
from ..qad_rubberband import QadRubberBand
from ..qad_dim import QadDimStyles
from ..qad_geom_relations import getQadGeomClosestVertex
from ..qad_multi_geom import getQadGeomAt, fromQadGeomToQgsGeom
from ..qad_snapper import QadSnapTypeEnum


# ===============================================================================
# Qad_lengthen_maptool_ModeEnum class.
# ===============================================================================
class Qad_lengthen_maptool_ModeEnum():
   # si richiede la selezione dell'oggetto da misurare
   ASK_FOR_OBJ_TO_MISURE = 1
   # si richiede il delta
   ASK_FOR_DELTA = 2
   # non si richiede niente
   NONE = 3
   # si richiede la selezione dell'oggetto da allungare
   ASK_FOR_OBJ_TO_LENGTHEN = 4
   # si richiede la percentuale 
   ASK_FOR_PERCENT = 5
   # si richiede il totale
   ASK_FOR_TOTAL = 6
   # si richiede il nuovo punto dell'estremità in modalità dinamica
   ASK_FOR_DYNAMIC_POINT = 7

# ===============================================================================
# Qad_lengthen_maptool class
# ===============================================================================
class Qad_lengthen_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.OpMode = None # "DElta" o "Percent" o "Total" o "DYnamic"
      self.OpType = None # "length" o "Angle"
      self.value = None
      self.tmpLinearObject = None

      self.__rubberBand = QadRubberBand(self.canvas)


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__rubberBand.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__rubberBand.show()
                             
   def clear(self):
      QadGetPoint.clear(self)
      self.__rubberBand.reset()
      self.mode = None

   def setInfo(self, entity, point):
      # setta: self.layer, self.tmpLinearObject e self.move_startPt

      if self.tmpLinearObject is not None:
         del self.tmpLinearObject
         self.tmpLinearObject = None
      
      if entity.isInitialized() == False:
         return False
         
      self.layer = entity.layer
      qadGeom = entity.getQadGeom()

      # la funzione ritorna una lista con 
      # (<minima distanza>
      # <punto del vertice più vicino>
      # <indice della geometria più vicina>
      # <indice della sotto-geometria più vicina>
      # <indice della parte della sotto-geometria più vicina>
      # <indice del vertice più vicino>
      result = getQadGeomClosestVertex(qadGeom, point)
      self.atGeom = result[2]
      self.tmpLinearObject = getQadGeomAt(qadGeom, self.atGeom, 0).copy()
                  
      if qad_utils.getDistance(self.tmpLinearObject.getStartPt(), point) <= \
         qad_utils.getDistance(self.tmpLinearObject.getEndPt(), point):
         # si allunga dal punto iniziale
         self.move_startPt = True
      else:
         # si allunga dal punto finale
         self.move_startPt = False

      return True


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()
      res = False
       
      # si richiede la selezione dell'oggetto da allungare
      if self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_LENGTHEN:
         if self.tmpEntity.isInitialized():
            if self.setInfo(self.tmpEntity, self.tmpPoint) == False:
               return

            newTmpLinearObject = self.tmpLinearObject.copy()
            if self.OpMode == "DElta":
               if self.OpType == "length":
                  res = newTmpLinearObject.lengthen_delta(self.move_startPt, self.value)
               elif self.OpType == "Angle":
                  res = newTmpLinearObject.lengthen_deltaAngle(self.move_startPt, self.value)
            elif self.OpMode == "Percent":
               value = newTmpLinearObject.length() * self.value / 100
               value = value - newTmpLinearObject.length()
               res = newTmpLinearObject.lengthen_delta(self.move_startPt, value)
            elif self.OpMode == "Total":
               if self.OpType == "length":
                  value = self.value - self.tmpLinearObject.length()
                  res = newTmpLinearObject.lengthen_delta(self.move_startPt, value)
               elif self.OpType == "Angle":
                  if newTmpLinearObject.whatIs() == "ARC":
                        value = self.value - linearObject.totalAngle()
                        res = newTmpLinearObject.lengthen_deltaAngle(self.move_startPt, value)
               
      # si richiede un punto per la nuova estremità
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_DYNAMIC_POINT:
         newTmpLinearObject = self.tmpLinearObject.copy()
         
         if newTmpLinearObject.whatIs() == "POLYLINE":
            if self.move_startPt:
               linearObject = newTmpLinearObject.getLinearObjectAt(0)
            else:
               linearObject = newTmpLinearObject.getLinearObjectAt(-1)
         else:
            linearObject = newTmpLinearObject
            
         gType = linearObject.whatIs()
         if gType == "LINE":
            newPt = qad_utils.getPerpendicularPointOnInfinityLine(linearObject.getStartPt(), linearObject.getEndPt(), self.tmpPoint)
            ang = linearObject.getTanDirectionOnStartPt()
         elif gType == "ARC":
            newPt = qad_utils.getPolarPointByPtAngle(linearObject.center, \
                                                     qad_utils.getAngleBy2Pts(linearObject.center, self.tmpPoint), \
                                                     linearObject.radius)                  
         elif gType == "ELLIPSE_ARC":
            pass

         if self.move_startPt:
            linearObject.setStartPt(newPt)
         else:
            linearObject.setEndPt(newPt)

         if gType == "LINE" and newTmpLinearObject.whatIs() == "POLYLINE" and \
            qad_utils.TanDirectionNear(ang, linearObject.getTanDirectionOnStartPt()) == False:
            res = False
         else:
            res = True
      
      if res == False: # allungamento impossibile
         return
      geom = fromQadGeomToQgsGeom(newTmpLinearObject, self.layer)
      self.__rubberBand.addGeometry(geom, self.layer)
      
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__rubberBand.show()          

   def deactivate(self):
      try: # necessario perché se si chiude QGIS parte questo evento nonostante non ci sia più l'oggetto maptool !
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode

      # si richiede la selezione dell'oggetto da misurare
      if self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_MISURE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)

         # solo layer di tipo lineari che non appartengano a quote o di tipo poligono 
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
            if layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry:
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.onlyEditableLayers = False
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # si richiede il delta
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_DELTA:
         self.OpMode = "DElta"
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
      # non si richiede niente
      elif self.mode == Qad_lengthen_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
      # si richiede la selezione dell'oggetto da allungare
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_OBJ_TO_LENGTHEN:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)

         # solo layer lineari editabili che non appartengano a quote
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
            if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.onlyEditableLayers = True
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # si richiede la percentuale
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_PERCENT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION) 
         self.OpMode = "Percent"
      # si richiede il totale
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_TOTAL:
         self.OpMode = "Total"
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
      # si richiede il nuovo punto dell'estremità in modalità dinamica
      elif self.mode == Qad_lengthen_maptool_ModeEnum.ASK_FOR_DYNAMIC_POINT:
         self.OpMode = "DYnamic"
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
