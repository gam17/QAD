# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool in ambito del comando pedit
 
                              -------------------
        begin                : 2013-05-22
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


from qgis.core import QgsPointXY, QgsWkbTypes, QgsGeometry


from .. import qad_utils
from ..qad_snapper import *
from ..qad_variables import QadVariables
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_polyline import QadPolyline
from ..qad_rubberband import QadRubberBand
from ..qad_highlight import QadHighlight
from ..qad_dim import QadDimStyles
from ..qad_msg import QadMsg


# ===============================================================================
# Qad_pedit_maptool_ModeEnum class.
# ===============================================================================
class Qad_pedit_maptool_ModeEnum():
   # si richiede la selezione di un'entità
   ASK_FOR_ENTITY_SEL = 1     
   # non si richiede niente
   NONE = 2     
   # si richiede il primo punto per calcolo distanza di approssimazione 
   ASK_FOR_FIRST_TOLERANCE_PT = 3     
   # noto il primo punto per calcolo distanza di approssimazione si richiede il secondo punto
   FIRST_TOLERANCE_PT_KNOWN_ASK_FOR_SECOND_PT = 4
   # si richiede un nuovo vertice da inserire
   ASK_FOR_NEW_VERTEX = 5   
   # si richiede la nuova posizione di un vertice da spostare
   ASK_FOR_MOVE_VERTEX = 6     
   # si richiede la posizione più vicina ad un vertice
   ASK_FOR_VERTEX = 7
   # si richede il punto base (grip mode)
   ASK_FOR_BASE_PT = 8


# ===============================================================================
# Qad_pedit_maptool class
# ===============================================================================
class Qad_pedit_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.firstPt = None
      self.mode = None
                       
      self.layer = None
      self.polyline = QadPolyline()
      self.tolerance2ApproxCurve = None
      self.vertexAt = 0
      self.vertexPt = None
      self.after = True 
      self.basePt = None
      self.__highlight = QadHighlight(self.canvas)


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__highlight.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__highlight.show()
                             
   def clear(self):
      QadGetPoint.clear(self)
      self.__highlight.reset()
      self.mode = None
      if self.basePt is not None:
         del(self.basePt)
         self.basePt = None

   def setPolyline(self, polyline, layer):
      self.polyline.set(polyline)
      self.layer = layer
      self.tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))


   def setVertexAt(self, vertexAt, after = None):
      if vertexAt == self.polyline.qty():
         self.firstPt = self.polyline.getLinearObjectAt(-1).getEndPt()
      else:
         self.firstPt = self.polyline.getLinearObjectAt(vertexAt).getStartPt()
      
      self.vertexPt = QgsPointXY(self.firstPt)
      self.vertexAt = vertexAt
      self.after = after      
    
      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__highlight.reset()
      tmpPolyline = None
       
      # si richiede un nuovo vertice da inserire
      if self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_NEW_VERTEX:
         if self.basePt is not None:
            offsetX = self.tmpPoint.x() - self.basePt.x()
            offsetY = self.tmpPoint.y() - self.basePt.y()
            newPt = QgsPointXY(self.vertexPt.x() + offsetX, self.vertexPt.y() + offsetY)
         else:
            newPt = QgsPointXY(self.tmpPoint)
            
         tmpPolyline = self.polyline.copy()
         
         if self.after: # dopo
            if self.vertexAt == tmpPolyline.qty() and tmpPolyline.isClosed():
               tmpPolyline.insertPoint(0, newPt)
            else:
               tmpPolyline.insertPoint(self.vertexAt, newPt)
         else: # prima
            if self.vertexAt == 0 and tmpPolyline.isClosed():
               tmpPolyline.insertPoint(tmpPolyline.qty() - 1, newPt)
            else:
               tmpPolyline.insertPoint(self.vertexAt - 1, newPt)
               
      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_MOVE_VERTEX:
         newPt = QgsPointXY(self.tmpPoint)
         tmpPolyline = self.polyline.copy()
         tmpPolyline.movePoint(self.vertexAt, newPt)
      
      if tmpPolyline is not None:
         if self.layer is not None:
            geom = tmpPolyline.asGeom(self.layer.wkbType())
         else:
            geom = tmpPolyline.asGeom(QgsWkbTypes.CurvePolygon)           

         # trasformo la geometria nel crs del layer
         self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, geom), self.layer)
         
#          pts = tmpPolyline.asPolyline(self.tolerance2ApproxCurve) 
#          if self.layer.geometryType() == QgsWkbTypes.PolygonGeometry:
#             geom = QgsGeometry.fromPolygonXY([pts])
#          else:
#             geom = QgsGeometry.fromPolylineXY(pts)
#             
#          # trasformo la geometria nel crs del layer
#          self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, geom), self.layer)
      
    
   def activate(self):
      QadGetPoint.activate(self)
      self.__highlight.show()          

   def deactivate(self):
      try: # necessario perché se si chiude QGIS parte questo evento nonostante non ci sia più l'oggetto maptool !
         QadGetPoint.deactivate(self)
         self.__highlight.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
            
      # si richiede la selezione di un'entità
      if self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_ENTITY_SEL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         
         # solo layer lineari o poligono editabili che non appartengano a quote
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
            if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
               layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # non si richiede niente
      elif self.mode == Qad_pedit_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # si richiede il primo punto per calcolo distanza di approssimazione
      # si richiede la posizione più vicina ad un vertice
      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_FIRST_TOLERANCE_PT:
         self.onlyEditableLayers = False
         self.checkPointLayer = True
         self.checkLineLayer = True
         self.checkPolygonLayer = True
         self.setSnapType()
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto il primo punto per calcolo distanza di approssimazione si richiede il secondo punto
      elif self.mode == Qad_pedit_maptool_ModeEnum.FIRST_TOLERANCE_PT_KNOWN_ASK_FOR_SECOND_PT or \
           self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_NEW_VERTEX or \
           self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_MOVE_VERTEX:         
         self.onlyEditableLayers = False
         self.checkPointLayer = True
         self.checkLineLayer = True
         self.checkPolygonLayer = True
         self.setSnapType()
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstPt)
      # si richiede la posizione più vicina ad un vertice
      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_VERTEX:
         self.setSnapType(QadSnapTypeEnum.DISABLE)
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setStartPoint(None)
      # si richede il punto base (grip mode)
      elif self.mode == Qad_pedit_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.setSnapType()
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)


# ===============================================================================
# Qad_gripLineToArcConvert_maptool_ModeEnum class.
# ===============================================================================
class Qad_gripLineToArcConvert_maptool_ModeEnum():
   # noti il punto iniziale e finale dell'arco si richiede il punto intermedio
   START_END_PT_KNOWN_ASK_FOR_SECOND_PT = 1
   # non si richiede niente
   NONE = 2     


# ===============================================================================
# Qad_gripLineToArcConvert_maptool class
# ===============================================================================
class Qad_gripLineToArcConvert_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.firstPt = None
      self.mode = None
                       
      self.layer = None 
      self.polyline = QadPolyline()
      self.linearObject = None
      self.startPt = None
      self.endPt = None
      self.tolerance2ApproxCurve = None
      self.__highlight = QadHighlight(self.canvas)


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__highlight.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__highlight.show()
                             
   def clear(self):
      QadGetPoint.clear(self)
      self.__highlight.reset()
      self.mode = None

   def setPolyline(self, polyline, layer, partAt):
      self.polyline.set(polyline)
      self.layer = layer
      self.tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))                            
      self.linearObject = self.polyline.getLinearObjectAt(partAt)
      self.firstPt = self.polyline.getMiddlePt()
      self.startPt = self.polyline.getStartPt()
      self.endPt = self.polyline.getEndPt()
    
      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__highlight.reset()
      ok = False
       
      # noti il punto iniziale e finale dell'arco si richiede il punto intermedio
      if self.mode == Qad_gripLineToArcConvert_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_SECOND_PT:
         if self.linearObject is None:
            return
         arc = QadArc()
         if arc.fromStartSecondEndPts(self.startPt, self.tmpPoint, self.endPt) == False:
            return
         if qad_utils.ptNear(self.startPt, arc.getStartPt()):
            self.linearObject.setArc(arc, False) # arco non inverso
         else:
            self.linearObject.setArc(arc, True) # arco inverso
         ok = True
      
      if ok:
         pts = self.polyline.asPolyline(self.tolerance2ApproxCurve)
         if self.layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            geom = QgsGeometry.fromPolygonXY([pts])
         else:
            geom = QgsGeometry.fromPolylineXY(pts)
         # trasformo la geometria nel crs del layer
         self.__highlight.addGeometry(self.mapToLayerCoordinates(self.layer, geom), self.layer)
      
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__highlight.show()

   def deactivate(self):
      try: # necessario perché se si chiude QGIS parte questo evento nonostante non ci sia più l'oggetto maptool !
         QadGetPoint.deactivate(self)
         self.__highlight.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
            
      # noti il punto iniziale e finale dell'arco si richiede il punto intermedio
      if self.mode == Qad_gripLineToArcConvert_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstPt)
      # non si richiede niente
      elif self.mode == Qad_pedit_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
