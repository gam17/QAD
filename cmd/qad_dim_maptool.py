# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool in ambito dei comandi di quotatura
 
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


import math


from .. import qad_utils
from ..qad_variables import QadVariables
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_dim import QadDimStyleAlignmentEnum
from ..qad_rubberband import QadRubberBand


# ===============================================================================
# Qad_dim_maptool_ModeEnum class.
# ===============================================================================
class Qad_dim_maptool_ModeEnum():
   # noto niente si richiede il primo punto di quotatura
   NONE_KNOWN_ASK_FOR_FIRST_PT = 1     
   # noto il primo punto si richiede il secondo punto di quotatura
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 2     
   # noto i punti di quotatura si richiede la posizione della linea di quota lineare
   FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS = 3     
   # si richiede il testo di quota
   ASK_FOR_TEXT = 4
   # noto i punti di quotatura si richiede la posizione della linea di quota allineata
   FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS = 5
   # si richiede un punto sull'arco per la quota arco
   ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC = 6
   # noto i punti di quotatura si richiede la posizione della linea di quota arco
   FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS = 7
   # noto l'oggetto da quotare (arco o cerchio) si richiede la posizione della linea di quota raggio
   OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS = 8


# ===============================================================================
# Qad_dim_maptool class
# ===============================================================================
class Qad_dim_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      dimStyle = None
      self.dimPt1 = None
      self.dimPt2 = None
      self.dimCircle = None
      
      self.dimArc = None # per quotatura arco
      
      self.forcedTextRot = None # rotazione del testo di quota
      self.measure = None # misura della quota (se None viene calcolato)
      self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL # allineamento della linea di quota
      self.forcedDimLineAlignment = None # allineamento della linea di quota forzato
      self.forcedDimLineRot = 0.0 # rotazione della linea di quota forzato
      self.leader = None # per disegnare la linea direttrice nella quotatura arco
      
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
            

   def setDimLineAlignment(self, LinePosPt, horizLine1, horizLine2, verticalLine1, verticalLine2):
      # < 0 se a sinistra della linea
      sxOfHorizLine1 = True if qad_utils.leftOfLine(LinePosPt, horizLine1[0], horizLine1[1]) < 0 else False
      sxOfHorizLine2 = True if qad_utils.leftOfLine(LinePosPt, horizLine2[0], horizLine2[1]) < 0 else False
      
      sxOfVerticalLine1 = True if qad_utils.leftOfLine(LinePosPt, verticalLine1[0], verticalLine1[1]) < 0 else False
      sxOfVerticalLine2 = True if qad_utils.leftOfLine(LinePosPt, verticalLine2[0], verticalLine2[1]) < 0 else False
      
      # se LinePosPt é tra le linee di limite orizzontale e non é tra le linee di limite verticale      
      if sxOfHorizLine1 != sxOfHorizLine2 and sxOfVerticalLine1 == sxOfVerticalLine2:
         self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
      # se LinePosPt non é tra le linee di limite orizzontale ed é tra le linee di limite verticale      
      elif sxOfHorizLine1 == sxOfHorizLine2 and sxOfVerticalLine1 != sxOfVerticalLine2:
         self.preferredAlignment = QadDimStyleAlignmentEnum.VERTICAL
      
      return
            

   # ============================================================================
   # setLinearDimPtsAndDimLineAlignmentOnCircle
   # ============================================================================
   def setLinearDimPtsAndDimLineAlignmentOnCircle(self, LinePosPt, circle):
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot + math.pi / 2, circle.radius)
      horizLine1 = [pt1, pt2]
      
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot, -1 * circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot + math.pi / 2, circle.radius)
      horizLine2 = [pt1, pt2]
      
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot + math.pi / 2, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot, circle.radius)
      verticalLine1 = [pt1, pt2]
      
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, self.forcedDimLineRot + math.pi / 2, -1 * circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.forcedDimLineRot, circle.radius)
      verticalLine2 = [pt1, pt2]
      
      # se non é stato impostato un allineamento forzato, lo calcolo in automatico
      if self.forcedDimLineAlignment is None:         
         self.setDimLineAlignment(LinePosPt, horizLine1, horizLine2, verticalLine1, verticalLine2)
      else:
         self.preferredAlignment = self.forcedDimLineAlignment
         
      if self.preferredAlignment == QadDimStyleAlignmentEnum.HORIZONTAL:
         self.dimPt1 = horizLine1[0]
         self.dimPt2 = horizLine2[0]
      else:
         self.dimPt1 = verticalLine1[0]
         self.dimPt2 = verticalLine2[0]
         

   # ============================================================================
   # setLinearDimLineAlignmentOnDimPts
   # ============================================================================
   def setLinearDimLineAlignmentOnDimPts(self, LinePosPt):      
      # se non é stato impostato un allineamento forzato, lo calcolo in automatico
      if self.forcedDimLineAlignment is None:         
         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt1, self.forcedDimLineRot + math.pi / 2, 1)
         horizLine1 = [self.dimPt1, pt2]
         
         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt2, self.forcedDimLineRot + math.pi / 2, 1)
         horizLine2 = [self.dimPt2, pt2]
         
         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt1, self.forcedDimLineRot, 1)
         verticalLine1 = [self.dimPt1, pt2]
         
         pt2 = qad_utils.getPolarPointByPtAngle(self.dimPt2, self.forcedDimLineRot, 1)
         verticalLine2 = [self.dimPt2, pt2]
         
         self.setDimLineAlignment(LinePosPt, horizLine1, horizLine2, verticalLine1, verticalLine2)
      else:
         self.preferredAlignment = self.forcedDimLineAlignment
            
            
   # ============================================================================
   # canvasMoveEvent
   # ============================================================================
   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()            
         
      dimEntity = None
      
      # noti i punti di quotatura si richiede la posizione della linea di quota lineare
      if self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS:
         if self.dimCircle is not None:
            self.setLinearDimPtsAndDimLineAlignmentOnCircle(self.tmpPoint, self.dimCircle)
         else:
            self.setLinearDimLineAlignmentOnDimPts(self.tmpPoint)
                     
         dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(self.canvas, \
                                                                        self.dimPt1, \
                                                                        self.dimPt2, \
                                                                        self.tmpPoint, \
                                                                        self.measure, \
                                                                        self.preferredAlignment, \
                                                                        self.forcedDimLineRot)
      # noti i punti di quotatura si richiede la posizione della linea di quota allineata
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS:
         dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(self.canvas, \
                                                                         self.dimPt1, \
                                                                         self.dimPt2, \
                                                                         self.tmpPoint, \
                                                                         self.measure)
      # noti i punti di quotatura si richiede la posizione della linea di quota arco
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS:
         dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(self.canvas, \
                                                                     self.dimArc, \
                                                                     self.tmpPoint, \
                                                                     self.measure)
      # noto l'oggetto da quotare (arco o cerchio) si richiede la posizione della linea di quota raggio
      elif self.mode == Qad_dim_maptool_ModeEnum.OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS:
         dimObj = self.dimCircle if (self.dimCircle is not None) else self.dimArc
         dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(self.canvas, \
                                                                        dimObj, \
                                                                        self.tmpPoint, \
                                                                        self.measure)

      if dimEntity is not None:
         # testo di quota
         self.__rubberBand.addGeometry(dimEntity.textualFeature.geometry(), self.dimStyle.getTextualLayer()) # geom e layer
         self.__rubberBand.addGeometry(textOffsetRect, self.dimStyle.getTextualLayer()) # geom e layer
         for g in dimEntity.getLinearGeometryCollection():
            self.__rubberBand.addGeometry(g, self.dimStyle.getLinearLayer()) # geom e layer
         for g in dimEntity.getSymbolGeometryCollection():
            self.__rubberBand.addGeometry(g, self.dimStyle.getSymbolLayer()) # geom e layer
         
          
   def activate(self):
      QadGetPoint.activate(self)            
      if self.__rubberBand is not None:
         self.__rubberBand.show()

   def deactivate(self):
      try: # necessario perché se si chiude QGIS parte questo evento nonostante non ci sia più l'oggetto maptool !
         QadGetPoint.deactivate(self)
         if self.__rubberBand is not None:
            self.__rubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode
      # noto niente si richiede il primo punto di quotatura
      if self.mode == Qad_dim_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto il primo punto si richiede il secondo punto di quotatura
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.dimPt1)
      # noto i punti di quotatura si richiede la posizione della linea di quota
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setStartPoint(None)        
      # si richiede il testo di quota
      elif self.mode == Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT:     
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)         
      # noti i punti di quotatura si richiede la posizione della linea di quota allineata
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.setStartPoint(None) 
      # si richiede un punto sull'arco per la quota arco
      elif self.mode == Qad_dim_maptool_ModeEnum.ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto i punti di quotatura si richiede la posizione della linea di quota
      elif self.mode == Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto l'oggetto da quotare (arco o cerchio) si richiede la posizione della linea di quota raggio
      elif self.mode == Qad_dim_maptool_ModeEnum.OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
