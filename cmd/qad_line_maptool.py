# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool di richiesta di un punto in ambito del comando line
 
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


from .. import qad_utils
from ..qad_snapper import QadSnapper, QadSnapTypeEnum
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_line_maptool_ModeEnum class.
# ===============================================================================
class Qad_line_maptool_ModeEnum():
   # noto niente si richiede il primo punto
   NONE_KNOWN_ASK_FOR_FIRST_PT = 1
   # noto il primo punto si richiede il secondo punto
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 2      
   # nota l'entita del primo punto di tangenza si richiede il secondo punto
   FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT = 3
   # nota l'entita del primo punto di perpendicolarità si richiede il secondo punto
   FIRST_PER_KNOWN_ASK_FOR_SECOND_PT = 4
   

# ===============================================================================
# Qad_line_maptool class
# ===============================================================================
class Qad_line_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.firstPt = None
      self.tan1 = None
      self.per1 = None
      self.entity1 = None
      self.__rubberBand = QadRubberBand(self.canvas)   

   def __del__(self):
      QadGetPoint.__del__(self)
      
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
         
      line = None
      
      # noto il primo punto si richiede il secondo punto
      if self.mode == Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         if (self.firstPt is not None):
            line = [self.firstPt, self.tmpPoint]
      # nota l'entita del primo punto di tangenza si richiede il secondo punto
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT:
         snapper = QadSnapper()
         snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.canvas))
         snapper.setSnapType(QadSnapTypeEnum.TAN)
         snapper.setStartPoint(self.tmpPoint)
         oSnapPoints = snapper.getSnapPoint(self.entity1, self.tan1)
         # memorizzo il punto di snap in point (prendo il primo valido)
         for item in oSnapPoints.items():
            points = item[1]
            if points is not None:
               line = [points[0], self.tmpPoint]
               break
      # nota l'entita del primo punto di perpendicolarità si richiede il secondo punto
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_PER_KNOWN_ASK_FOR_SECOND_PT:
         snapper = QadSnapper()
         snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.canvas))
         snapper.setSnapType(QadSnapTypeEnum.PER)
         snapper.setStartPoint(self.tmpPoint)
         oSnapPoints = snapper.getSnapPoint(self.entity1, self.per1)
         # memorizzo il punto di snap in point (prendo il primo valido)
         for item in oSnapPoints.items():
            points = item[1]
            if points is not None:
               line = [points[0], self.tmpPoint]
               break
      
      if line is not None:
         self.__rubberBand.setLine(line)
      
    
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
      # noto niente si richiede il primo punto
      if self.mode == Qad_line_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE) 
         self.setStartPoint(None)
      # noto il primo punto si richiede il secondo punto
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstPt)
      # nota l'entita del primo punto di tangenza si richiede il secondo punto
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE) 
      # nota l'entita del primo punto di perpendicolarità si richiede il secondo punto
      elif self.mode == Qad_line_maptool_ModeEnum.FIRST_PER_KNOWN_ASK_FOR_SECOND_PT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE) 
