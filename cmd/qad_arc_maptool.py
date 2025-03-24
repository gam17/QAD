# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool di richiesta di un punto in ambito del comando arco
 
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


from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProject, QgsWkbTypes


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_line import QadLine
from ..qad_polyline import QadPolyline
from ..qad_arc import QadArc
from ..qad_rubberband import QadRubberBand
from ..qad_highlight import QadHighlight
from ..qad_entity import QadEntity


# ===============================================================================
# Qad_arc_maptool_ModeEnum class.
# ===============================================================================
class Qad_arc_maptool_ModeEnum():
   # noto niente si richiede il primo punto
   NONE_KNOWN_ASK_FOR_START_PT = 1     
   # noto il punto iniziale dell'arco si richiede il secondo punto
   START_PT_KNOWN_ASK_FOR_SECOND_PT = 2     
   # noti il punto iniziale e il secondo punto dell'arco si richiede il punto finale
   START_SECOND_PT_KNOWN_ASK_FOR_END_PT = 3     
   # noto il punto iniziale dell'arco si richiede il centro
   START_PT_KNOWN_ASK_FOR_CENTER_PT = 4     
   # noti il punto iniziale e il centro dell'arco si richiede il punto finale
   START_CENTER_PT_KNOWN_ASK_FOR_END_PT = 5     
   # noti il punto iniziale e il centro dell'arco si richiede l'angolo inscritto
   START_CENTER_PT_KNOWN_ASK_FOR_ANGLE = 6     
   # noti il punto iniziale e il centro dell'arco si richiede la lunghezza della corda
   START_CENTER_PT_KNOWN_ASK_FOR_CHORD = 7
   # noto il punto iniziale dell'arco si richiede il punto finale
   START_PT_KNOWN_ASK_FOR_END_PT = 8     
   # noti il punto iniziale e finale dell'arco si richiede il centro
   START_END_PT_KNOWN_ASK_FOR_CENTER = 9
   # noti il punto iniziale e finale dell'arco si richiede l'angolo inscritto
   START_END_PT_KNOWN_ASK_FOR_ANGLE = 10
   # noti il punto iniziale e finale dell'arco si richiede la direzione della tangente al punto iniziale
   START_END_PT_KNOWN_ASK_FOR_TAN = 11
   # noti il punto iniziale e finale dell'arco si richiede il raggio
   START_END_PT_KNOWN_ASK_FOR_RADIUS = 12        
   # noto niente si richiede il centro
   NONE_KNOWN_ASK_FOR_CENTER_PT = 13
   # noto il centro dell'arco si richiede il punto iniziale
   CENTER_PT_KNOWN_ASK_FOR_START_PT = 14      
   # noti il punto iniziale e la tangente al punto iniziale si richiede il punto finale
   START_PT_TAN_KNOWN_ASK_FOR_END_PT = 15
   # noto il punto iniziale dell'arco si richiede l'angolo inscritto
   START_PT_KNOWN_ASK_FOR_ANGLE = 16     
   # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il punto finale
   START_PT_ANGLE_KNOWN_ASK_FOR_END_PT = 17     
   # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il centro
   START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT = 18
   # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il raggio
   START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS = 19
   # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il secondo punto per misurare il raggio
   START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS = 20
   # noti il punto iniziale, l'angolo inscritto e il raggio dell'arco si richiede la direzione della corda
   START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION = 21
   # noti il punto iniziale e il raggio dell'arco si richiede il punto finale
   START_PT_RADIUS_KNOWN_ASK_FOR_END_PT = 22        


# ===============================================================================
# Qad_arc_maptool class
# ===============================================================================
class Qad_arc_maptool(QadGetPoint):
    
   def __init__(self, plugIn, asToolForMPolygon = False):
      QadGetPoint.__init__(self, plugIn)
      self.arcStartPt = None
      self.arcSecondPt = None
      self.arcEndPt = None
      self.arcCenterPt = None
      self.arcTanOnStartPt = None
      self.arcAngle = None
      self.arcStartPtForRadius = None
      self.arcRadius = None
      self.__rubberBand = QadRubberBand(self.canvas)
 
      self.asToolForMPolygon = asToolForMPolygon # se True significa che è usato per disegnare un poligono
      if self.asToolForMPolygon:
         self.__polygonRubberBand = QadRubberBand(self.plugIn.canvas, True)
         self.endVertex = None # punta al vertice iniziale e finale del poligono di QadPLINECommandClass
      else:
         self.__polygonRubberBand = None
         
      self.layer = None


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__rubberBand.hide()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.hide()
 
   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__rubberBand.show()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.show()
                                   
   def clear(self):
      QadGetPoint.clear(self)
      self.__rubberBand.reset()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.reset()
      self.mode = None

      
   # ============================================================================
   # removeItems
   # ============================================================================
   def removeItems(self):
      QadGetPoint.removeItems(self)
      # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
      if self.__rubberBand is not None:
         del self.__rubberBand
         self.__rubberBand = None

      if self.__polygonRubberBand is not None:
         del self.__polygonRubberBand
         self.__polygonRubberBand = None

      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.reset()
      
      result = False
      arc = QadArc()    
       
      # noti il primo e il secondo punto dell'arco si richiede il terzo punto
      if self.mode == Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartSecondEndPts(self.arcStartPt, self.arcSecondPt, self.tmpPoint)
      # noti il primo punto e il centro dell'arco si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT:
         result = arc.fromStartCenterEndPts(self.arcStartPt, self.arcCenterPt, self.tmpPoint)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il primo punto e il centro dell'arco si richiede l'angolo inscritto
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE:
         angle = qad_utils.getAngleBy2Pts(self.arcCenterPt, self.tmpPoint)
         result = arc.fromStartCenterPtsAngle(self.arcStartPt, self.arcCenterPt, angle)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il primo punto e il centro dell'arco si richiede la lunghezza della corda
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD:     
         chord = qad_utils.getDistance(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartCenterPtsChord(self.arcStartPt, self.arcCenterPt, chord)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e finale dell'arco si richiede il centro
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER:     
         result = arc.fromStartCenterEndPts(self.arcStartPt, self.tmpPoint, self.arcEndPt)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e finale dell'arco si richiede l'angolo inscritto
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_ANGLE:     
         angle = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartEndPtsAngle(self.arcStartPt, self.arcEndPt, angle)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e finale dell'arco si richiede la direzione della tangente
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN:     
         tan = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartEndPtsTan(self.arcStartPt, self.arcEndPt, tan)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e finale dell'arco si richiede il raggio
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS:     
         radius = qad_utils.getDistance(self.arcEndPt, self.tmpPoint)
         result = arc.fromStartEndPtsRadius(self.arcStartPt, self.arcEndPt, radius)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e la tangente al punto iniziale si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT:     
         result = arc.fromStartEndPtsTan(self.arcStartPt, self.tmpPoint, self.arcTanOnStartPt)         
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT:     
         result = arc.fromStartEndPtsAngle(self.arcStartPt, self.tmpPoint, self.arcAngle)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il centro
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT:     
         result = arc.fromStartCenterPtsAngle(self.arcStartPt, self.tmpPoint, self.arcAngle)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale, l'angolo inscritto e il raggio dell'arco si richiede la direzione della corda
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION:     
         chordDirection = qad_utils.getAngleBy2Pts(self.arcStartPt, self.tmpPoint)
         result = arc.fromStartPtAngleRadiusChordDirection(self.arcStartPt, self.arcAngle, \
                                                           self.arcRadius, chordDirection)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      # noti il punto iniziale e il raggio dell'arco si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT:     
         result = arc.fromStartEndPtsRadius(self.arcStartPt, self.tmpPoint, self.arcRadius)
         if result == True and self.tmpCtrlKey: # inverto angolo iniziale-finale
            arc.inverseAngles()
      
      if result == True:
         if self.__polygonRubberBand is None: # significa che NON è usato per disegnare un poligono
            if self.layer is not None:
               g = arc.asGeom(self.layer.wkbType())
            else:
               g = arc.asGeom(QgsWkbTypes.CompoundCurve) # è un arco virtuale che non verrà salvato da questo comando

            if g is not None: self.__rubberBand.setGeometry(g) 
         else: # significa che è usato per disegnare un poligono
            pline = QadPolyline()
            pline.append(arc)
            
            if self.endVertex is not None:
               line = QadLine()
               line.set(arc.getEndPt(), self.endVertex)
               pline.append(line)
               line = QadLine()
               line.set(self.endVertex, arc.getStartPt())
               pline.append(line)
            else:
               line = QadLine()
               line.set(arc.getEndPt(), arc.getStartPt())
               pline.append(line)
               
            if self.layer is not None:
               g = pline.asGeom(self.layer.wkbType())
            else:
               g = pline.asGeom(QgsWkbTypes.CurvePolygon) # è un arco virtuale che non verrà salvato da questo comando            
            
            self.__polygonRubberBand.setGeometry(g)
                                 
#          points = arc.asPolyline()
#       
#          if points is not None:
#             self.__rubberBand.setLine(points)
#             if self.__polygonRubberBand is not None: # significa che è usato per disegnare un poligono
#                if self.endVertex is not None:
#                   points.insert(0, self.endVertex)
#                   self.__polygonRubberBand.setPolygon(points)

    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__rubberBand.show()
      if self.__polygonRubberBand is not None: self.__polygonRubberBand.show()
      
   def deactivate(self):
      try: # necessario perché se si chiude QGIS parte questo evento nonostante non ci sia più l'oggetto maptool !
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
         if self.__polygonRubberBand is not None: self.__polygonRubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # noto niente si richiede il primo punto
      if self.mode == Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_START_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto il primo punto dell'arco si richiede il secondo punto
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il primo e il secondo punto dell'arco si richiede il terzo punto
      elif self.mode == Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT:         
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcSecondPt)
      # noto il primo punto dell'arco si richiede il centro         
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_CENTER_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il primo punto e il centro dell'arco si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcCenterPt)
      # noti il primo punto e il centro dell'arco si richiede l'angolo inscritto
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcCenterPt)
      # noti il primo punto e il centro dell'arco si richiede la lunghezza della corda
      elif self.mode == Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noto il punto iniziale dell'arco si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il punto iniziale e finale dell'arco si richiede il centro
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noti il punto iniziale e finale dell'arco si richiede l'angolo inscritto
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_ANGLE:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il punto iniziale e finale dell'arco si richiede la direzione della tangente
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il punto iniziale e finale dell'arco si richiede il raggio
      elif self.mode == Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)                  
         self.setStartPoint(self.arcEndPt)
      # noto niente si richiede il centro
      elif self.mode == Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto il centro dell'arco si richiede il punto iniziale
      elif self.mode == Qad_arc_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_START_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)                  
         self.setStartPoint(self.arcCenterPt)
      # noti il punto iniziale e la tangente al punto iniziale si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)                  
         self.setStartPoint(self.arcStartPt)
      # noto il punto iniziale dell'arco si richiede l'angolo inscritto
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il centro
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il raggio
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noti il punto iniziale e l'angolo inscritto dell'arco si richiede il secondo punto per misurare il raggio
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPtForRadius)
      # noti il punto iniziale, l'angolo inscritto e il raggio dell'arco si richiede la direzione della corda
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
      # noti il punto iniziale e il raggio dell'arco si richiede il punto finale
      elif self.mode == Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.arcStartPt)
         


# ===============================================================================
# Qad_scale_maptool_ModeEnum class.
# ===============================================================================
class Qad_gripChangeArcRadius_maptool_ModeEnum():
   # si richiede il punto base
   ASK_FOR_BASE_PT = 1     
   # noto il punto base si richiede il secondo punto per il raggio
   BASE_PT_KNOWN_ASK_FOR_RADIUS_PT = 2


# ===============================================================================
# Qad_gripChangeArcRadius_maptool class
# ===============================================================================
class Qad_gripChangeArcRadius_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.basePt = None
      self.entity = None
      self.arc = None 
      self.coordTransform = None
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

   def setEntity(self, entity):
      self.entity = QadEntity(entity)
      self.arc = self.entity.getQadGeom() # arco in map coordinate
      self.basePt = self.arc.center
      self.coordTransform = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), \
                                                   entity.layer.crs(), \
                                                   QgsProject.instance())


   # ============================================================================
   # stretch
   # ============================================================================
   def changeRadius(self, radius):
      self.__highlight.reset()
      # radius = nuovo raggio dell'arco
      # tolerance2ApproxCurve = tolleranza per ricreare le curve
      self.arc.radius = radius
      points = self.arc.asPolyline()
      if points is None:
         return False
      
      g = QgsGeometry.fromPolylineXY(points)
      # trasformo la geometria nel crs del layer
      g.transform(self.coordTransform)      
      self.__highlight.addGeometry(g, self.entity.layer)
            
      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)

      # noto il punto base si richiede il secondo punto per il raggio
      if self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT:
         radius = qad_utils.getDistance(self.basePt, self.tmpPoint)
         self.changeRadius(radius)                           
         
    
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
      # noto niente si richiede il punto base
      if self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.clear()
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # noto il punto base si richiede il secondo punto per il raggio
      elif self.mode == Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
      