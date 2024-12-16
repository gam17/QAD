# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 classe per gestire il map tool di richiesta di un punto in ambito del comando ellisse
 
                              -------------------
        begin                : 2018-05-22
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
from qgis.core import QgsWkbTypes
import math


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_ellipse import QadEllipse
from ..qad_ellipse_arc import QadEllipseArc
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_ellipse_maptool_ModeEnum class.
# ===============================================================================
class Qad_ellipse_maptool_ModeEnum():
   # noto niente si richiede il primo punto finale dell'asse
   NONE_KNOWN_ASK_FOR_FIRST_FINAL_AXIS_PT = 1
   # noto il primo punto finale dell'asse si richiede il secondo punto finale dell'asse
   FIRST_FINAL_AXIS_PT_KNOWN_ASK_FOR_SECOND_FINAL_AXIS_PT = 2
   # si richiede di specificare la distanza dal secondo asse
   ASK_FOR_DIST_TO_OTHER_AXIS = 3
   # richiede la rotazione attorno all'asse maggiore
   ASK_ROTATION_ROUND_MAJOR_AXIS = 4
   # richiede l'angolo iniziale
   ASK_START_ANGLE = 5
   # richiede l'angolo finale
   ASK_END_ANGLE = 6
   # richiede l'angolo incluso
   ASK_INCLUDED_ANGLE = 7
   # richiede l'angolo parametrico iniziale
   ASK_START_PARAMETER = 8
   # richiede l'angolo parametrico finale
   ASK_END_PARAMETER = 9
   # richiede il centro
   ASK_FOR_CENTER = 10
   # richiede il primo punto di fuoco
   ASK_FOR_FIRST_FOCUS = 11
   # richiede il secondo punto di fuoco
   ASK_FOR_SECOND_FOCUS = 12
   # richiede un punto sull'ellisse
   ASK_FOR_PT_ON_ELLIPSE = 13
   # richede l'area dell'ellisse
   ASK_AREA = 14 
   

# ===============================================================================
# Qad_ellipse_maptool class
# ===============================================================================
class Qad_ellipse_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.axis1Pt1 = None # primo punto finale dell'asse
      self.axis1Pt2 = None # secondo punto finale dell'asse
      self.distToOtherAxis = 0.0 # distanza dall'altro asse
      self.rot = 0 # rotazione intorno all'asse
      self.centerPt = None # punto centrale dell'ellisse
      self.ellipse = None
      self.ellipseArc = QadEllipseArc()
      self.startAngle = 0.0 # l'ellisse può essere incompleta (come l'arco per il cerchio)
      self.endAngle = math.pi * 2 # A startAngle of 0 and endAngle of 2pi will produce a closed Ellipse.
      self.includedAngle = 0.0
      self.focus1 = None # primo punto di fuoco
      self.focus2 = None # secondo punto di fuoco
      
      self.__rubberBand = QadRubberBand(self.canvas, False)
      self.geomType = QgsWkbTypes.PolygonGeometry
      self.mode = None
      

   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      if rubberBandBorderColor is not None:
         self.__rubberBand.setBorderColor(rubberBandBorderColor)
      if rubberBandFillColor is not None:
         self.__rubberBand.setFillColor(rubberBandFillColor)

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
      
      
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()
         
      ellipse = None
      
      # noto il centro dell'ellisse, richiede di specificare la distanza dal secondo asse
      if self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_DIST_TO_OTHER_AXIS:
         dist = qad_utils.getDistance(self.centerPt, self.tmpPoint)
         ellipse = QadEllipse().fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, dist)
      # noto il centro dell'ellisse, richiede la rotazione attorno all'asse maggiore
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_ROTATION_ROUND_MAJOR_AXIS:
         angle = qad_utils.getAngleBy2Pts(self.centerPt, self.tmpPoint)
         dist = math.fabs(qad_utils.getDistance(self.axis1Pt1, self.axis1Pt2) / 2 * math.cos(angle))
         ellipse = QadEllipse().fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, dist)
      # nota l'ellisse, richiede l'angolo iniziale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_ANGLE:
         ellipse = self.ellipse
      # nota l'ellisse, richiede l'angolo finale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_ANGLE:
         ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
         self.endAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.tmpPoint) - ellipseAngle
         self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
         ellipse = self.ellipseArc
      # nota l'ellisse, richiede l'angolo incluso
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_INCLUDED_ANGLE:
         includedAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.tmpPoint)
         self.endAngle = self.startAngle + includedAngle
         self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
         ellipse = self.ellipseArc
      # nota l'ellisse, richiede l'angolo parametrico iniziale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_PARAMETER:
         ellipse = self.ellipse
      # nota l'ellisse, richiede l'angolo parametrico finale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_PARAMETER:
         ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
         self.endAngle = self.ellipse.getAngleFromParam(qad_utils.getAngleBy2Pts(self.ellipse.center, self.tmpPoint) - ellipseAngle)
         self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
         ellipse = self.ellipseArc
      # not i fuochi dell'ellisse, richiede di specificare un punto sull'ellisse
      if self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_PT_ON_ELLIPSE:
         ellipse = QadEllipse().fromFoci(self.focus1, self.focus2, self.tmpPoint)

      if ellipse is not None:
         points = ellipse.asPolyline()
      
         if points is not None:
            if self.geomType == QgsWkbTypes.PolygonGeometry:
               self.__rubberBand.setPolygon(points)
            else:
               self.__rubberBand.setLine(points)


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
      # noto niente si richiede il primo punto finale dell'asse
      if self.mode == Qad_ellipse_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_FINAL_AXIS_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # si richiede di specificare la distanza dal secondo asse
      elif self.mode == Qad_ellipse_maptool_ModeEnum.FIRST_FINAL_AXIS_PT_KNOWN_ASK_FOR_SECOND_FINAL_AXIS_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         if self.axis1Pt1 is not None:
            self.setStartPoint(self.axis1Pt1)
         else:
            self.setStartPoint(self.centerPt)
      # si richiede di specificare la distanza dal secondo asse
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_DIST_TO_OTHER_AXIS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # richiede la rotazione attorno all'asse maggiore
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_ROTATION_ROUND_MAJOR_AXIS:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)         
      # richiede l'angolo iniziale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # richiede l'angolo finale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # richiede l'angolo incluso
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_INCLUDED_ANGLE:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # richiede l'angolo parametrico iniziale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_START_PARAMETER:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # richiede l'angolo parametrico finale
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_END_PARAMETER:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.ellipse.center)
      # richiede il centro
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_CENTER:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # richiede il primo punto di fuoco
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_FIRST_FOCUS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # richiede il secondo punto di fuoco
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_SECOND_FOCUS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # richiede un punto sull'ellisse
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_FOR_PT_ON_ELLIPSE:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # richede l'area dell'ellisse
      elif self.mode == Qad_ellipse_maptool_ModeEnum.ASK_AREA:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
