# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione dei punti
 
                              -------------------
        begin                : 2018-12-27
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
from qgis.core import *
from qgis.gui import *
import math


from . import qad_utils 


# ===============================================================================
# QadPoint point class derivato da QgsPointXY
# ===============================================================================
class QadPoint(QgsPointXY):
    
   def __init__(self, point = None):
      QgsPointXY.__init__(self)
      if point is not None:
         self.set(point)


   def whatIs(self):
      # obbligatoria
      return "POINT"

   
   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return False

   
   def set(self, point):
      QgsPointXY.set(self, point.x(), point.y())
      return self


   def transform(self, coordTransform):
      # obbligatoria
      """Transform this geometry as described by CoordinateTransform ct."""
      self.set(coordTransform.transform(self))


   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      # obbligatoria
      """Transform this geometry as described by CRS."""
      if (sourceCRS is not None) and (destCRS is not None) and sourceCRS != destCRS:       
         coordTransform = QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()) # trasformo le coord
         self.transform(coordTransform)

      
   def __eq__(self, point):
      # obbligatoria
      """self == other"""
      return qad_utils.ptNear(self, point)

  
   def __ne__(self, point):
      """self != other"""
      return not qad_utils.ptNear(self, point)


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude il punto.
      """
      return QgsRectangle(self.x(), self.y(), self.x(), self.y())


   def equals(self, pt):
      # uguali geometricamente
      return self.__eq__(pt)


   def copy(self):
      # obbligatoria
      return QadPoint(self)
      

   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna il punto in forma di QgsGeometry.
      wkbType, tolerance2ApproxCurve e atLeastNSegment sono dichiarati solo per compatibilità
      """
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.MultiPoint:
         multiPoint = QgsMultiPoint()
         multiPoint.addGeometry(QgsPoint(self))   
         return QgsGeometry(multiPoint)
      
      return QgsGeometry.fromPointXY(self)


   # ===============================================================================
   # fromGeom
   # ===============================================================================
   def fromGeom(self, geom):
      """
      la funzione ritorna il punto in forma di QgsGeometry.
      """
      return self.set(geom.asPoint())


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      return self.set(qad_utils.movePoint(self, offsetX, offsetY))


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      self.set(qad_utils.rotatePoint(self, basePt, angle))
   

   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      return self.set(qad_utils.scalePoint(self, basePt, scale))


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      return self.set(qad_utils.mirrorPoint(self, mirrorPt, mirrorAngle))
