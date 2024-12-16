# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 classe per gestire il map tool in ambito del comando rotate
 
                              -------------------
        begin                : 2013-09-27
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
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting, QadDimEntity
from ..qad_highlight import QadHighlight
from ..qad_entity import QadCacheEntitySetIterator, QadEntityTypeEnum
from ..qad_multi_geom import fromQadGeomToQgsGeom


# ===============================================================================
# Qad_rotate_maptool_ModeEnum class.
# ===============================================================================
class Qad_rotate_maptool_ModeEnum():
   # noto niente si richiede il punto base
   NONE_KNOWN_ASK_FOR_BASE_PT = 1     
   # noto il punto base si richiede il secondo punto per l'angolo di rotazione
   BASE_PT_KNOWN_ASK_FOR_ROTATION_PT = 2     
   # si richiede il primo punto per l'angolo di riferimento
   ASK_FOR_FIRST_PT_REFERENCE_ANG = 3     
   # noto il primo punto si richiede il secondo punto per l'angolo di riferimento
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG = 4     
   # noto il punto base si richiede il secondo punto per il nuovo angolo
   BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT = 5
   # si richiede il primo punto per il nuovo angolo
   ASK_FOR_FIRST_NEW_ROTATION_PT = 6
   # noto il primo punto si richiede il secondo punto per il nuovo angolo
   FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT = 7     

# ===============================================================================
# Qad_rotate_maptool class
# ===============================================================================
class Qad_rotate_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.basePt = None
      self.Pt1ReferenceAng = None
      self.ReferenceAng = 0
      self.Pt1NewAng = None
      self.cacheEntitySet = None
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
   
   
   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, entity, basePt, angle):
      # verifico se l'entità appartiene ad uno stile di quotatura
      if entity.whatIs() == "ENTITY":
         # ruoto la geometria dell'entità
         qadGeom = entity.getQadGeom().copy() # la copio
         qadGeom.rotate(basePt, angle)
         self.__highlight.addGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer), entity.layer)
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # la copio
         # ruoto la quota
         newDimEntity.rotate(basePt, angle)
         self.__highlight.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         self.__highlight.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         self.__highlight.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())
   
   
   # ============================================================================
   # addRotatedGeometries
   # ============================================================================
   def addRotatedGeometries(self, angle):
      self.__highlight.reset()            
      
      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)         
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         self.rotate(entity, self.basePt, angle)
      

   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
                     
      # noto il punto base si richiede il secondo punto per l'angolo di rotazione
      if self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_ROTATION_PT:
         angle = qad_utils.getAngleBy2Pts(self.basePt, self.tmpPoint)
         self.addRotatedGeometries(angle)                           
      # noto il punto base si richiede il secondo punto per il nuovo angolo
      elif self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT:
         angle = qad_utils.getAngleBy2Pts(self.basePt, self.tmpPoint)
         diffAngle = angle - self.ReferenceAng
         self.addRotatedGeometries(diffAngle)                           
      # noto il primo punto si richiede il secondo punto per il nuovo angolo
      elif self.mode == Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT:
         angle = qad_utils.getAngleBy2Pts(self.Pt1NewAng, self.tmpPoint)
         diffAngle = angle - self.ReferenceAng
         self.addRotatedGeometries(diffAngle)                           
         
    
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
      if self.mode == Qad_rotate_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_BASE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # noto il punto base si richiede il secondo punto per l'angolo di rotazione
      elif self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
      # si richiede il primo punto per l'angolo di riferimento
      elif self.mode == Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_PT_REFERENCE_ANG:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()            
      # noto il primo punto si richiede il secondo punto per l'angolo di riferimento
      elif self.mode == Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT_REFERENCE_ANG:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.Pt1ReferenceAng)
      # noto il punto base si richiede il secondo punto per il nuovo angolo
      elif self.mode == Qad_rotate_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_NEW_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.basePt)
      # si richiede il primo punto per il nuovo angolo
      elif self.mode == Qad_rotate_maptool_ModeEnum.ASK_FOR_FIRST_NEW_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # noto il primo punto si richiede il secondo punto per il nuovo angolo
      elif self.mode == Qad_rotate_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_NEW_ROTATION_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.Pt1NewAng)
