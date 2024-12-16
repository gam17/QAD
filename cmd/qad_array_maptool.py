# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 classe per gestire il map tool in ambito del comando array
 
                              -------------------
        begin                : 2016-05-31
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
from ..qad_variables import QadVariables
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_highlight import QadHighlight
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting
from ..qad_entity import QadCacheEntitySetIterator, QadEntityTypeEnum
from .. import qad_array_fun


# ===============================================================================
# Qad_array_maptool_ModeEnum class.
# ===============================================================================
class Qad_array_maptool_ModeEnum():
   # non si richiede niente
   NONE = 0
   # si richiede il punto base
   ASK_FOR_BASE_PT = 1
   # si richiede il primo punto per la distanza tra colonne
   ASK_FOR_COLUMN_SPACE_FIRST_PT = 2
   # si richiede il primo punto per la dimensione della cella
   ASK_FOR_1PT_CELL = 3
   # si richiede il psecondo punto per la dimensione della cella
   ASK_FOR_2PT_CELL = 4
   # si richiede il primo punto per la distanza tra righe
   ASK_FOR_ROW_SPACE_FIRST_PT = 5


# ===============================================================================
# Qad_array_maptool class
# ===============================================================================
class Qad_array_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)
                        
      self.cacheEntitySet = None
      self.basePt = None
      self.arrayType = None
      self.distanceBetweenRows = None
      self.distanceBetweenCols = None
      self.itemsRotation = None

      # serie rettangolare
      self.rectangleAngle = None
      self.rectangleCols = None
      self.rectangleRows = None
      self.firstPt = None

      # serie traiettoria
      self.pathTangentDirection = None
      self.pathRows = None
      self.pathItemsNumber = None
      self.pathPolyline = None

      # serie polare
      self.centerPt = None
      self.polarItemsNumber = None
      self.polarAngleBetween = None
      self.polarRows = None

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
   # doRectangleArray
   # ============================================================================
   def doRectangleArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if qad_array_fun.arrayRectangleEntity(self.plugIn, entity, self.basePt, self.rectangleRows, self.rectangleCols, \
                                               self.distanceBetweenRows, self.distanceBetweenCols, self.rectangleAngle, self.itemsRotation,
                                               False, self.__highlight) == False:
            return


   # ============================================================================
   # doPathArray
   # ============================================================================
   def doPathArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if qad_array_fun.arrayPathEntity(self.plugIn, entity, self.basePt, self.pathRows, self.pathItemsNumber, \
                                          self.distanceBetweenRows, self.distanceBetweenCols, self.pathTangentDirection, self.itemsRotation, \
                                          self.pathPolyline, self.distanceFromStartPt, \
                                          False, self.__highlight) == False:
            return


   # ============================================================================
   # doPolarArray
   # ============================================================================
   def doPolarArray(self):
      self.__highlight.reset()

      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom().copy() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if qad_array_fun.arrayPolarEntity(self.plugIn, entity, self.basePt, self.centerPt, self.polarItemsNumber, \
                                           self.polarAngleBetween, self.polarRows, self.distanceBetweenRows, self.itemsRotation, \
                                           False, self.__highlight) == False:
            return


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
#       # noto il punto base si richiede il secondo punto
#       if self.mode == Qad_array_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_COPY_PT:
#          self.setCopiedGeometries(self.tmpPoint)                           
         
    
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
      # non si richiede niente
      if self.mode == Qad_array_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.NONE)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # si richiede il punto base
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_BASE_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # si richiede il primo punto per la distanza tra colonne
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_FIRST_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # si richiede il primo punto per la dimensione della cella
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_1PT_CELL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # si richiede il psecondo punto per la dimensione della cella
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_2PT_CELL:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
         self.setStartPoint(self.firstPt)
      # si richiede il primo punto per la distanza tra righe
      elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_ROW_SPACE_FIRST_PT:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)


      # si richiede il secondo punto per la distanza tra colonne
#       elif self.mode == Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_SECOND_PT:
#          self.setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
#          self.setStartPoint(self.firstPt)
