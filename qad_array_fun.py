# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 funzioni per fare serie di oggetti grafici
 
                              -------------------
        begin                : 2016-05-26
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


# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *
import qgis.utils

import math

from . import qad_utils
from . import qad_arc
from . import qad_circle
from .qad_snapper import *
from . import qad_layer
from .qad_highlight import QadHighlight
from .qad_entity import *
from .qad_dim import *
from . import qad_label
from .qad_multi_geom import fromQadGeomToQgsGeom

# ===============================================================================
# doMoveAndRotateGeom
# ===============================================================================
def doMoveAndRotateGeom(plugIn, entity, offsetX, offsetY, angle, basePt, addToLayer, highlightObj):
   # funzione di ausilio
   if entity.whatIs() == "ENTITY":   
      qadGeom = entity.getQadGeom().copy()
      qadGeom.move(offsetX, offsetY)
      if angle is not None:
         qadGeom.rotate(basePt, angle)
         
      g = fromQadGeomToQgsGeom(qadGeom, entity.layer)
      if addToLayer:
         newF = QgsFeature(entity.getFeature()) # la copio perchè altrimenti qgis si incarta
         newF.setGeometry(g)
         
         if len(entity.rotFldName) > 0:
            rotValue = newF.attribute(entity.rotFldName)
            # a volte vale None e a volte null (vai a capire...)
            rotValue = 0 if rotValue is None or rotValue == NULL else qad_utils.toRadians(rotValue) # la rotazione é in gradi nel campo della feature
            rotValue = rotValue + angle
            newF.setAttribute(entity.rotFldName, qad_utils.toDegrees(qad_utils.normalizeAngle(rotValue)))               
         
         # plugIn, layer, feature, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(plugIn, entity.layer, newF, None, False, False, False) == False:
            return False
   
      if highlightObj is not None:
         highlightObj.addGeometry(g, entity.layer)
   
      del qadGeom
      del g
      
   elif ent.whatIs() == "DIMENTITY": # se l'entità è una quotatura
      newDimEntity = QadDimEntity(dimEntity)
      newDimEntity.move(offsetX, offsetY)
      if angle is not None:
         newDimEntity.rotate(basePt, angle)
      
      if addToLayer:
         if newDimEntity.addToLayers(plugIn) == False:
            return False             
   
      if highlightObj is not None:
         highlightObj.addGeometry(newDimEntity.textualFeature.geometry(), newDimEntity.getTextualLayer())
         highlightObj.addGeometries(newDimEntity.getLinearGeometryCollection(), newDimEntity.getLinearLayer())
         highlightObj.addGeometries(newDimEntity.getSymbolGeometryCollection(), newDimEntity.getSymbolLayer())
      
      del newDimEntity      
   
   return True


# ===============================================================================
# arrayRectangleEntity
# ===============================================================================
def arrayRectangleEntity(plugIn, ent, basePt, rows, cols, distanceBetweenRows, distanceBetweenCols, angle, itemsRotation,
                         addToLayer, highlightObj):
   """
   serie rettangolare
   ent = entità QAD di cui fare la serie (QadEntity o QadDimEntity)
   basePt = punto base in map coordinate (QgsPointXY)
   rows = numero di righe
   cols = numero di colonne
   distanceBetweenRows = distanza tra le righe in map coordinate
   distanceBetweenCols = distanza tra le colonne in map coordinate
   angle = angolo della serie (radianti)
   itemsRotation = True se si vuole ruotare gli elementi come l'angolo della serie
   addToLayer = se è True aggiunge le nuove entità al layer
   highlightObj = se è diverso da None vengono aggiunge le geometrie all'oggetto QadHighlight
                
   la funzione restituisce True in caso di successo e Falso in caso di errore
   """
   for row in range(0, rows):
      firstBasePt = qad_utils.getPolarPointByPtAngle(basePt, angle + math.pi / 2, distanceBetweenRows * row)
      distX = 0
      for col in range(0, cols):
         newBasePt = qad_utils.getPolarPointByPtAngle(firstBasePt, angle, distanceBetweenCols * col)
         offsetX = newBasePt.x() - basePt.x()
         offsetY = newBasePt.y() - basePt.y()
         
         if doMoveAndRotateGeom(plugIn, ent, offsetX, offsetY, \
                                angle if itemsRotation else None, \
                                newBasePt, addToLayer, highlightObj) == False:
            return False

         distX = distX + distanceBetweenCols

   return True


# ===============================================================================
# arrayPathEntity
# ===============================================================================
def arrayPathEntity(plugIn, ent, basePt, rows, cols, distanceBetweenRows, distanceBetweenCols, tangentDirection, itemsRotation, \
                    pathPolyline, distanceFromStartPt, addToLayer, highlightObj):
   """
   serie traiettoria
   ent = entità QAD di cui fare la serie (QadEntity o QadDimEntity)
   basePt = punto base in map coordinate (QgsPointXY)
   rows = numero di righe
   cols = numero di colonne
   distanceBetweenRows = distanza tra le righe in map coordinate
   distanceBetweenCols = distanza tra le colonne in map coordinate
   tangentDirection = specifica il modo in cui gli elementi disposti in serie sono allineati rispetto alla direzione iniziale della traiettoria 
   itemsRotation = True se si vuole ruotare gli elementi come l'angolo della serie
   pathPolyline = traiettoria da seguire (QadPolyline) in map coordinate
   distanceFromStartPt = distanza dal punto iniziale della traccia
   addToLayer = se è True aggiunge le nuove entità al layer
   highlightObj = se è diverso da None vengono aggiunge le geometrie all'oggetto QadHighlight
   
   la funzione restituisce True in caso di successo e Falso in caso di errore
   """
   firstBasePt = basePt
   firstTanDirection = pathPolyline.getTanDirectionOnStartPt()
   for col in range(0, cols):
      distX = (distanceBetweenCols * col) + distanceFromStartPt
      firstBasePt, angle = pathPolyline.getPointFromStart(distX) # ritorna il punto e la direzione della tang in quel punto
      if firstBasePt is not None:
         for row in range(0, rows):
            newBasePt = qad_utils.getPolarPointByPtAngle(firstBasePt, angle + math.pi/2, distanceBetweenRows * row)
            offsetX = newBasePt.x() - basePt.x()
            offsetY = newBasePt.y() - basePt.y()
            
            if doMoveAndRotateGeom(plugIn, ent, offsetX, offsetY, \
                                   angle - tangentDirection if itemsRotation else -tangentDirection, \
                                   newBasePt, addToLayer, highlightObj) == False:
               return False

      distX = distX + distanceBetweenCols

   return True


# ===============================================================================
# arrayPolarEntity
# ===============================================================================
def arrayPolarEntity(plugIn, ent, basePt, centerPt, itemsNumber, angleBetween, rows, distanceBetweenRows, itemsRotation, \
                     addToLayer, highlightObj):
   """
   serie polare
   ent = entità QAD di cui fare la serie (QadEntity o QadDimEntity)
   basePt = punto base in map coordinate (QgsPointXY)
   centerPt = punto centrale in map coordinate (QgsPointXY)
   itemsNumber = numero di copie da creare
   angleBetween = angolo tra un elemento e l'altro (radianti)
   rows = numero di righe
   distanceBetweenRows = distanza tra le righe in map coordinate
   itemsRotation = True se si vuole ruotare gli elementi intorno al cerchio
   addToLayer = se è True aggiunge le nuove entità al layer
   highlightObj = se è diverso da None vengono aggiunge le geometrie all'oggetto QadHighlight
   """
   firstAngle = qad_utils.getAngleBy2Pts(centerPt, basePt)
   dist = qad_utils.getDistance(centerPt, basePt)
   for row in range(0, rows):
      angle = firstAngle
      for i in range(0, itemsNumber):
         newBasePt = qad_utils.getPolarPointByPtAngle(centerPt, angle, dist)
         offsetX = newBasePt.x() - basePt.x()
         offsetY = newBasePt.y() - basePt.y()
      
         if doMoveAndRotateGeom(plugIn, ent, offsetX, offsetY, \
                                i * angleBetween if itemsRotation else None, \
                                newBasePt, addToLayer, highlightObj) == False:
            return False
         angle = angle + angleBetween

      dist = dist + distanceBetweenRows

   return True

