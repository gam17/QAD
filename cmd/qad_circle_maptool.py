# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool di richiesta di un punto in ambito del comando cerchio
 
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


from qgis.core import QgsWkbTypes


from .. import qad_utils
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_circle import QadCircle
from ..qad_circle_fun import *
from ..qad_rubberband import QadRubberBand
from ..qad_snapper import QadSnapTypeEnum


# ===============================================================================
# Qad_circle_maptool_ModeEnum class.
# ===============================================================================
class Qad_circle_maptool_ModeEnum():
   # noto niente si richiede il centro
   NONE_KNOWN_ASK_FOR_CENTER_PT = 1     
   # noto il centro del cerchio si richiede il raggio
   CENTER_PT_KNOWN_ASK_FOR_RADIUS = 2     
   # noto il centro del cerchio si richiede il diametro
   CENTER_PT_KNOWN_ASK_FOR_DIAM = 3     
   # noto niente si richiede il primo punto
   NONE_KNOWN_ASK_FOR_FIRST_PT = 4
   # noto il primo punto si richiede il secondo punto
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 5
   # noto il primo e il secondo punto si richiede il terzo punto
   FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT = 6
   # noto niente si richiede il primo punto di estremità diam
   NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT = 7
   # noto il primo punto di estremità diam si richiede il secondo punto di estremità diam
   FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT = 8
   # noto niente si richiede l'entita del primo punto di tangenza
   NONE_KNOWN_ASK_FOR_FIRST_TAN = 9
   # nota l'entita del primo punto di tangenza si richiede quella del secondo punto di tangenza
   FIRST_TAN_KNOWN_ASK_FOR_SECOND_TAN = 10
   # note la prima e la seconda entita dei punti di tangenza si richiede il raggio
   FIRST_SECOND_TAN_KNOWN_ASK_FOR_RADIUS = 11
   # noto note la prima, la seconda entita dei punti di tangenza e il primo punto per misurare il raggio
   # si richiede il secondo punto per misurare il raggio
   FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS = 12

# ===============================================================================
# Qad_circle_maptool class
# ===============================================================================
class Qad_circle_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.centerPt = None
      self.radius = None
      self.firstPt = None
      self.secondPt = None
      self.firstDiamPt = None
      self.tan1 = None
      self.tan2 = None
      self.startPtForRadius = None
            
      self.__rubberBand = QadRubberBand(self.canvas, False)
      self.layer = None
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
         
      circle = None
      
      # noto il centro del cerchio si richiede il raggio
      if self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS:
         radius = qad_utils.getDistance(self.centerPt, self.tmpPoint)
         circle = QadCircle().set(self.centerPt, radius)
      # noto il centro del cerchio si richiede il diametro
      elif self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_DIAM:
         diam = qad_utils.getDistance(self.centerPt, self.tmpPoint)
         circle = QadCircle().set(self.centerPt, diam / 2)
      # noto il primo e il secondo punto si richiede il terzo punto
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT:
         if (self.firstPt is not None) and (self.secondPt is not None):
            circle = circleFrom3Pts(self.firstPt, self.secondPt, self.tmpPoint)
      # noto il primo punto di estremità diam si richiede il secondo punto di estremità diam
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT:
         if self.firstDiamPt is not None:
            circle = QadCircle().fromDiamEnds(self.firstDiamPt, self.tmpPoint)
      # noto note la prima, la seconda entita dei punti di tangenza e il primo punto per misurare il raggio
      # si richiede il secondo punto per misurare il raggio
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS:
         radius = qad_utils.getDistance(self.startPtForRadius, self.tmpPoint)
         circle = circleFrom2TanPtsRadius(self.tanGeom1, self.tanPt1, \
                                          self.tanGeom2, self.tanPt2, radius)
      
      if circle is not None:
         if self.layer is not None:
            g = circle.asGeom(self.layer.wkbType())
         else:
            g = circle.asGeom(QgsWkbTypes.CompoundCurve) # è un cerchio virtuale che non verrà salvato da questo comando
            
         if g is not None:
            self.__rubberBand.setGeometry(g)
               
                      
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
      # noto niente si richiede il centro
      if self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto il centro del cerchio si richiede il raggio
      elif self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # noto il centro del cerchio si richiede il diametro
      elif self.mode == Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_DIAM:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.centerPt)
      # noto niente si richiede il primo punto
      elif self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)         
      # noto il primo punto si richiede il secondo punto
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)         
      # noto il primo e il secondo punto si richiede il terzo punto
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)         
      # noto niente si richiede il primo punto di estremità diam
      elif self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)                 
      # noto il primo punto di estremità diam si richiede il secondo punto di estremità diam
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto niente si richiede l'entita del primo punto di tangenza
      elif self.mode == Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_TAN:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         self.forceSnapTypeOnce(QadSnapTypeEnum.TAN_DEF)         
      # nota l'entita del primo punto di tangenza si richiede quella del secondo punto di tangenza
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_TAN:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         self.forceSnapTypeOnce(QadSnapTypeEnum.TAN_DEF)         
      # note la prima e la seconda entita dei punti di tangenza si richiede il raggio
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_KNOWN_ASK_FOR_RADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         # siccome il puntatore era stato variato in ENTITY_SELECTION dalla selez precedente
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)         
      # noto note la prima, la seconda entita dei punti di tangenza e il primo punto per misurare il raggio
      # si richiede il secondo punto per misurare il raggio
      elif self.mode == Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.startPtForRadius)
