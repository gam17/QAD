# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 classe per gestire il map tool in ambito del comando mirror
 
                              -------------------
        begin                : 2013-12-11
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
from ..qad_getpoint import QadGetPoint, QadGetPointDrawModeEnum
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting, QadDimEntity
from ..qad_highlight import QadHighlight
from ..qad_entity import QadEntityTypeEnum, QadCacheEntitySetIterator
from ..qad_multi_geom import fromQadGeomToQgsGeom


# ===============================================================================
# Qad_copy_maptool_ModeEnum class.
# ===============================================================================
class Qad_mirror_maptool_ModeEnum():
   # noto niente si richiede il primo punto della linea speculare
   NONE_KNOWN_ASK_FOR_FIRST_PT = 1     
   # noto il primo punto si richiede il secondo punto della linea speculare
   FIRST_PT_KNOWN_ASK_FOR_SECOND_PT = 2     

# ===============================================================================
# Qad_mirror_maptool class
# ===============================================================================
class Qad_mirror_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.firstMirrorPt = None
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
   # mirror
   # ============================================================================
   def mirror(self, entity, mirrorPt, angle):
      # verifico se l'entità appartiene ad uno stile di quotatura
      if entity.whatIs() == "ENTITY":
         # ruoto la geometria dell'entità
         qadGeom = entity.getQadGeom().copy() # la copio
         qadGeom.mirror(mirrorPt, angle)
         self.__highlight.addGeometry(fromQadGeomToQgsGeom(qadGeom, entity.layer), entity.layer)
      elif entity.whatIs() == "DIMENTITY":
         newDimEntity = QadDimEntity(entity) # la copio
         # ruoto la quota
         newDimEntity.mirror(mirrorPt, angle)
         self.__highlight.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         self.__highlight.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         self.__highlight.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())
      
   
   def setMirroredGeometries(self, newPt):
      self.__highlight.reset()

      angle = qad_utils.getAngleBy2Pts(self.firstMirrorPt, newPt)

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

         self.mirror(entity, self.firstMirrorPt, angle)


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
                     
      # noto il primo punto si richiede il secondo punto della linea speculare
      if self.mode == Qad_mirror_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setMirroredGeometries(self.tmpPoint)                           
         
    
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
      # noto niente si richiede il primo punto della linea speculare
      if self.mode == Qad_mirror_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
         self.__highlight.reset()
      # noto il primo punto si richiede il secondo punto della linea speculare
      elif self.mode == Qad_mirror_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT:
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
         self.setStartPoint(self.firstMirrorPt)