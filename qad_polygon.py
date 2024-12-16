# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione dei poligoni (lista di polilinee)
 
                              -------------------
        begin                : 2019-03-14
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


from . import qad_utils
from .qad_circle import QadCircle
from .qad_ellipse import QadEllipse
from .qad_polyline import QadPolyline


# ===============================================================================
# QadPolygon class
# rappresenta una lista di geometrie chiuse: QadPolyline, QadCircle, QadEllipse
# ===============================================================================
class QadPolygon():
    
   def __init__(self, polygon=None):
      self.defList = []
      # deflist = (<geometria chiusa 1> <geometria chiusa 2>...)
      if polygon is not None:
         self.set(polygon)


   # ============================================================================
   # whatIs
   # ============================================================================
   def whatIs(self):
      return "POLYGON"

   
   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return True


   # ============================================================================
   # set
   # ============================================================================
   def set(self, polygon):
      self.removeAll()
      for closedObject in polygon.defList:
         self.append(closedObject)
      return self


   def __eq__(self, polygon):
      # obbligatoria
      """self == other"""
      if polygon.whatIs() != "POLYLINE": return False
      if self.qty() != polygon.qty(): return False
      for i in range(0, self.qty()):
         if self.getClosedObjectAt(i) != polygon.getClosedObjectAt(i): return False
      return True
  
  
   def __ne__(self, polygon):
      """self != other"""
      return not self.__eq__(polygon)


   # ============================================================================
   # append
   # ============================================================================
   def append(self, closedObject):
      """
      la funzione aggiunge una geometria chiusa in fondo alla lista.
      """
      if closedObject is None: return
      objectType = closedObject.whatIs()
      if objectType == "POLYLINE":
         if closedObject.isClosed() == False: return False
      elif objectType != "CIRCLE" and objectType != "ELLIPSE":
         return False
      self.defList.append(closedObject.copy())
      return True

   
   # ============================================================================
   # insert
   # ============================================================================
   def insert(self, i, closedObject):
      """
      la funzione aggiunge una geometria chiusa nella posizione i-esima della lista delle geometrie chiuse.
      """
      if i >= self.qty():
         return self.append(closedObject)
      else:         
         return self.defList.insert(i, closedObject.copy())


   # ============================================================================
   # remove
   # ============================================================================
   def remove(self, i):
      """
      la funzione cancella una geometria chiusa nella posizione i-esima della lista.
      """
      del self.defList[i]


   # ============================================================================
   # removeAll
   # ============================================================================
   def removeAll(self):
      """
      la funzione cancella le geometrie chiuse della lista.
      """
      del self.defList[:]


   # ============================================================================
   # getClosedObjectAt
   # ============================================================================
   def getClosedObjectAt(self, i):
      """
      la funzione restituisce la geometria chiusa alla posizione i-esima 
      con numeri negativi parte dal fondo (es. -1 = ultima posizione)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]
   
   
   # ============================================================================
   # fromPolygon
   # ============================================================================
   def fromPolygon(self, lineList):
      """
      la funzione inizializza una lista di geometrie chiuse che compone il poligono passato in liste di punti.
      """
      self.removeAll()
      ellipse = QadEllipse()
      circle = QadCircle()
      polyline = QadPolyline()
      
      for points in lineList:
         # verifico se è un cerchio
         if circle.fromPolyline(points):
            self.append(circle)
         else:
            # verifico se è una ellisse
            if ellipse.fromPolyline(points):
               self.append(ellipse)
            else:
               # verifico se è una polilinea
               if polyline.fromPolyline(points):
                  if polyline.isClosed():
                     self.append(polyline)
   
      if self.qty() == 0: return None
      return True


   # ============================================================================
   # fromGeom
   # ============================================================================
   def fromGeom(self, geom):
      """
      la funzione inizializza il poligono da un oggetto QgsGeometry.
      """
      return self.fromPolygon(geom.asPolygon())


   # ===============================================================================
   # asPolygon
   # ===============================================================================
   def asPolygon(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna una lista di liste di punti che compongono un poligono.
      """
      result = []
      for closedObject in self.defList:
         result.append(closedObject.asPolyline(tolerance2ApproxCurve, atLeastNSegment))

      return result

   
   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna il poligono in forma di QgsAbstractGeometry.
      """
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CurvePolygon:
         curvePolygon = QgsCurvePolygon()
         exteriorRing = True
         for closedObject in self.defList:
            if exteriorRing == True:
               curvePolygon.setExteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.CompoundCurve , tolerance2ApproxCurve, atLeastNSegment))
               exteriorRing = False
            else:
               curvePolygon.addInteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.CompoundCurve , tolerance2ApproxCurve, atLeastNSegment))               
         return curvePolygon
         
      elif flatType == QgsWkbTypes.MultiSurface: # Geometry that is combined from several Curvepolygons is called MultiSurface
         curvedPolygon = self.asAbstractGeom(QgsWkbTypes.CurvePolygon, tolerance2ApproxCurve, atLeastNSegment)
         multiSurface = QgsMultiSurface()
         multiSurface.addGeometry(curvedPolygon)
         return multiSurface

      elif flatType == QgsWkbTypes.MultiPolygon:
         polygon = self.asAbstractGeom(QgsWkbTypes.Polygon, tolerance2ApproxCurve, atLeastNSegment)
         multiPolygon = QgsMultiPolygon()
         multiPolygon.addGeometry(polygon)
         return multiPolygon
             
      polygon = QgsPolygon()
      exteriorRing = True
      for closedObject in self.defList:
         if exteriorRing == True:
            polygon.setExteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.LineString , tolerance2ApproxCurve, atLeastNSegment))
            exteriorRing = False
         else:
            polygon.addInteriorRing(closedObject.asAbstractGeom(QgsWkbTypes.LineString , tolerance2ApproxCurve, atLeastNSegment))               
      return polygon

   
   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna il poligono in forma di QgsGeometry.
      """
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))

   
   # ===============================================================================
   # copy
   # ===============================================================================
   def copy(self):
      # obbligatoria
      return QadPolygon(self)
   

   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      """
      la funzione sposta le geometrie chiuse secondo un offset X e uno Y
      """
      for closedObject in self.defList:
         closedObject.move(offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      for closedObject in self.defList:
         closedObject.rotate(basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      for closedObject in self.defList:
         closedObject.scale(basePt, scale)


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for closedObject in self.defList:
         closedObject.mirror(mirrorPt, mirrorAngle)


   # ============================================================================
   # qty
   # ============================================================================
   def qty(self):
      """
      la funzione restituisce la quantità di geometrie chiuse che compongono il poligono.
      """
      return len(self.defList)
         

   # ============================================================================
   # getCentroid
   # ============================================================================
   def getCentroid(self, tolerance2ApproxCurve = None):
      """
      la funzione restituisce il punto centroide.
      """
      g = self.asGeom(QgsWkbTypes.LineString, tolerance2ApproxCurve)
      if g is not None:
         centroid = g.centroid()
         if centroid is not None:
            return g.centroid().asPoint()

      return None

   
   # ===============================================================================
   # transform
   # ===============================================================================
   def transform(self, coordTransform):
      """
      la funzione restituisce un nuovo poligono con le coordinate trasformate.
      """
      result = QadPolygon()
      for closedObject in self.defList:
         result.append(closedObject.transform(coordTransform))
      return result
   

   # ===============================================================================
   # transformFromCRSToCRS
   # ===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """
      la funzione trasforma le coordinate dei punti che compone il poligono.
      """
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude il poligono.
      """
      boundingBox = self.getClosedObjectAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getClosedObjectAt(i).getBoundingBox())
         i = i + 1
         
      return boundingBox


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, pt):
      """
      la funzione ritorna True se il punto è sul poligono altrimenti False.
      """
      for closedObject in self.defList:
         if closedObject.containsPt(pt): return True
         
      return False
