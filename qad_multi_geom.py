# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione delle multi geometrie (multipoligoni)
 
                             -------------------
        begin                : 2019-03-15
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
from qgis.core import *
from qgis.gui import *
import qgis.utils


from .qad_point import *
from .qad_line import QadLine
from .qad_circle import QadCircle
from .qad_ellipse import QadEllipse
from .qad_polyline import QadPolyline
from .qad_polygon import QadPolygon
from .qad_layer import createMemoryLayer


#===============================================================================
# QadLinearObject class
# restituiesce un oggetto lineare linea, arco, arco di ellisse, polilinea ma anche
# cerchio ed ellisse (impropriamente) perchè possono esistere in layer LINESTRING
#===============================================================================
class QadLinearObject():
    
   def __init__(self):
      pass

   
   #============================================================================
   # fromPolyline
   #============================================================================
   @staticmethod
   def fromPolyline(points):
      """
      la funzione restituisce un oggetto lineare che può essere: 
      linea, arco, arco di ellisse, polilinea ma anche
      cerchio ed ellisse (impropriamente) perchè possono esistere in layer LINESTRING
      """
      tot_points = len(points)
      if tot_points == 2:
         line = QadLine()
         line.set(points[0], points[1])
         return line
      
      # verifico se è un cerchio
      circle = QadCircle()
      if circle.fromPolyline(points): return circle
      del circle
      # verifico se è una ellisse
      ellipse = QadEllipse()
      if ellipse.fromPolyline(points): return ellipse
      del ellipse
      # verifico se è una polilinea
      polyline = QadPolyline()
      if polyline.fromPolyline(points):
         if polyline.qty() == 1: # se è composto da solo 1 oggetto
            return polyline.getLinearObjectAt(0)
         else:
            return polyline
      del polyline
   
      return None


   #============================================================================
   # fromGeom
   #============================================================================
   @staticmethod
   def fromGeom(geom):
      """
      la funzione restituisce un oggetto lineare che può essere: 
      linea, arco, arco di ellisse, polilinea ma anche
      cerchio ed ellisse (impropriamente) perchè possono esistere in layer LINESTRING
      """
      return QadLinearObject.fromPolyline(geom.asPolyline())


#===============================================================================
# QadMultiPoint class
# rappresenta una lista di oggetti puntuali
#===============================================================================
class QadMultiPoint():
    
   def __init__(self, multiPoint=None):
      self.defList = []
      # deflist = (<point 1> <point 2>...)
      if multiPoint is not None:
         self.set(multiPoint)


   #============================================================================
   # whatIs
   #============================================================================
   def whatIs(self):
      return "MULTI_POINT"


   #============================================================================
   # set
   #============================================================================
   def set(self, multiPoint):
      self.removeAll()
      for point in multiPoint.defList:
         self.append(point)
      return self


   def __eq__(self, multiPoint):
      # obbligatoria
      """self == other"""
      if multiPoint.whatIs() != "MULTI_POINT": return False
      if self.qty() != multiPoint.qty(): return False
      for i in range(0, self.qty()):
         if self.getPointAt(i) != multiPoint.getPointAt(i): return False
      return True
  
  
   def __ne__(self, multiPoint):
      """self != other"""
      return not self.__eq__(multiPoint)


   #============================================================================
   # append
   #============================================================================
   def append(self, point):
      """
      la funzione aggiunge un punto lineare in fondo alla lista.
      """
      if point is None: return
      objectType = point.whatIs()
      if objectType != "POINT":
         return False
      self.defList.append(point.copy())
      return True

   
   #============================================================================
   # insert
   #============================================================================
   def insert(self, i, point):
      """
      la funzione aggiunge un punto nella posizione i-esima della lista dei punti.
      """
      if i >= self.qty():
         return self.append(point)
      else:         
         return self.defList.insert(i, point.copy())


   #============================================================================
   # remove
   #============================================================================
   def remove(self, i):
      """
      la funzione cancella un punto nella posizione i-esima della lista.
      """
      del self.defList[i]


   #============================================================================
   # removeAll
   #============================================================================
   def removeAll(self):
      """
      la funzione cancella i punti della lista.
      """
      del self.defList[:]


   #============================================================================
   # getPointAt
   #============================================================================
   def getPointAt(self, i):
      """
      la funzione restituisce il punto alla posizione i-esima 
      con numeri negativi parte dal fondo (es. -1 = ultima posizione)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]


   #============================================================================
   # setPointAt
   #============================================================================
   def setPointAt(self, pt, i):
      """
      la funzione setta il punto i-esimo
      """
      return self.getPointAt(i).set(pt)
   
   
   #============================================================================
   # fromMultiPoint
   #============================================================================
   def fromMultiPoint(self, pointList):
      """
      la funzione inizializza una lista di punti che compone il multiPoint passato in forma di lista di punti.
      """
      self.removeAll()
      for point in pointList:
         self.append(point)
   
      if self.qty() == 0: return False

      return True


   #============================================================================
   # fromGeom
   #============================================================================
   def fromGeom(self, geom):
      """
      la funzione inizializza una lista di punti QgsPointXY che compone il multiPoint da un oggetto QgsGeometry.
      """
      return self.fromMultiPoint(geom.asMultiPoint())


   #===============================================================================
   # asMultiPoint
   #===============================================================================
   def asMultiPoint(self):
      """
      la funzione ritorna una lista punti QgsPointXY che compongono un multiPoint.
      """
      result = []
      for point in self.defList:
         result.append(point)

      return result

   
   #===============================================================================
   # asGeom
   #===============================================================================
   def asGeom(self):
      """
      la funzione ritorna il multiPoint in forma di QgsGeometry.
      """
      return QgsGeometry.fromMultiPointXY(self.asMultiPoint())


   #===============================================================================
   # copy
   #===============================================================================
   def copy(self):
      # obbligatoria
      return QadMultiPoint(self)
   

   #============================================================================
   # move
   #============================================================================
   def move(self, offsetX, offsetY):
      """
      la funzione sposta i punti secondo un offset X e uno Y
      """
      for point in self.defList:
         point.move(offsetX, offsetY)


   #============================================================================
   # rotate
   #============================================================================
   def rotate(self, basePt, angle):
      for point in self.defList:
         point.rotate(basePt, angle)


   #============================================================================
   # scale
   #============================================================================
   def scale(self, basePt, scale):
      for point in self.defList:
         point.scale(basePt, scale)


   #============================================================================
   # mirror
   #============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for point in self.defList:
         point.mirror(mirrorPt, mirrorAngle)


   #============================================================================
   # qty
   #============================================================================
   def qty(self):
      """
      la funzione restituisce la quantità di punti che compongono il multipoint.
      """
      return len(self.defList)
         
  
   #===============================================================================
   # transform
   #===============================================================================
   def transform(self, coordTransform):
      """
      la funzione restituisce un nuovo multipoint con le coordinate trasformate.
      """
      result = QadMultiPoint()
      for point in self.defList:
         result.append(point.transform(coordTransform))
      return result
   

   #===============================================================================
   # transformFromCRSToCRS
   #===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """
      la funzione trasforma le coordinate dei punti che compongono il multipoint.
      """
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   #===============================================================================
   # closestPoint
   #===============================================================================
   def closestPoint(pt):
      """
      la funzione ritorna una lista con 
      (<minima distanza>
       <punto più vicino>
       <indice del punto più vicino>
      """
      dist = sys.float_info.max
      index = 0
      for point in self.defList:
         d = point.distance(pt)
         if d < dist:
            dist = d
            minDistPoint = point
            pointIndex = index
         
         index = index + 1
          
      return (dist, minDistPoint, pointIndex)


   #===============================================================================
   # getBoundingBox
   #===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude i punti.
      """
      boundingBox = self.getPointAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getPointAt(i).getBoundingBox())
         i = i + 1
         
      return boundingBox


#===============================================================================
# QadMultiLinearObject class
# rappresenta una lista di oggetti lineari compreso cerchio ed ellisse (impropriamente) perchè possono esistere in layer LINESTRING
#===============================================================================
class QadMultiLinearObject():
    
   def __init__(self, multiLinearObject=None):
      self.defList = []
      # deflist = (<obj 1> <obj 2>...)
      if multiLinearObject is not None:
         self.set(multiLinearObject)


   #============================================================================
   # whatIs
   #============================================================================
   def whatIs(self):
      return "MULTI_LINEAR_OBJ"


   #============================================================================
   # set
   #============================================================================
   def set(self, multiLinearObject):
      self.removeAll()
      for linearObject in multiLinearObject.defList:
         self.append(linearObject)
      return self


   def __eq__(self, multiLinearObject):
      # obbligatoria
      """self == other"""
      if multiLinearObject.whatIs() != "MULTI_LINEAR_OBJ": return False
      if self.qty() != multiLinearObject.qty(): return False
      for i in range(0, self.qty()):
         if self.getLinearObjectAt(i) != multiLinearObject.getLinearObjectAt(i): return False
      return True
  
  
   def __ne__(self, multiLinearObject):
      """self != other"""
      return not self.__eq__(multiLinearObject)


   #============================================================================
   # append
   #============================================================================
   def append(self, linearObject):
      """
      la funzione aggiunge un oggetto lineare in fondo alla lista.
      """
      if linearObject is None: return
      objectType = linearObject.whatIs()
      if objectType != "LINE" and objectType != "ARC" and objectType != "ELLIPSE_ARC" and \
         objectType != "POLYLINE" and objectType != "CIRCLE" and objectType != "ELLIPSE":
         return False
      self.defList.append(linearObject.copy())
      return True

   
   #============================================================================
   # insert
   #============================================================================
   def insert(self, i, linearObject):
      """
      la funzione aggiunge un pggetto lineare nella posizione i-esima della lista degli oggetti lineari.
      """
      if i >= self.qty():
         return self.append(linearObject)
      else:         
         return self.defList.insert(i, linearObject.copy())


   #============================================================================
   # remove
   #============================================================================
   def remove(self, i):
      """
      la funzione cancella un oggetto lineare nella posizione i-esima della lista.
      """
      del self.defList[i]


   #============================================================================
   # removeAll
   #============================================================================
   def removeAll(self):
      """
      la funzione cancella gli oggetti lineari della lista.
      """
      del self.defList[:]


   #============================================================================
   # getLinearObjectAt
   #============================================================================
   def getLinearObjectAt(self, i):
      """
      la funzione restituisce l'oggetto lineare alla posizione i-esima 
      con numeri negativi parte dal fondo (es. -1 = ultima posizione)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]
   
   
   #============================================================================
   # setLinearObjectAt
   #============================================================================
   def setLinearObjectAt(self, linearObject, i):
      """
      la funzione setta l'oggetto lineare i-esimo
      """
      return self.getLinearObjectAt(i).set(linearObject)
   
   
   #============================================================================
   # fromMultiLinearObject
   #============================================================================
   def fromMultiLinearObject(self, linearObjectList):
      """
      la funzione inizializza una lista di oggetti lineari che compone il multiLinearObject passato in forma di lista di punti.
      """
      self.removeAll()
      
      for points in linearObjectList:
         linearObject = QadLinearObject.fromPolyline(points)
         if linearObject is not None:
            self.append(linearObject)
   
      if self.qty() == 0: return False
      return True


   #============================================================================
   # fromGeom
   #============================================================================
   def fromGeom(self, geom):
      """
      la funzione inizializza una lista di oggetti lineari che compone il multiLinearObject da un oggetto QgsGeometry.
      """
      return self.fromMultiLinearObject(geom.asMultiPolyline())


   #===============================================================================
   # asMultiPolyline
   #===============================================================================
   def asMultiPolyline(self, tolerance2ApproxCurve = None):
      """
      la funzione ritorna una lista di liste di liste di punti che compongono un multiLinearObject.
      """
      result = []
      for linearObject in self.defList:
         result.append(linearObject.asPolyline(tolerance2ApproxCurve))

      return result

   
   #===============================================================================
   # asGeom
   #===============================================================================
   def asGeom(self, tolerance2ApproxCurve = None):
      """
      la funzione ritorna il multiLinearObject in forma di QgsGeometry.
      """
      return QgsGeometry.fromMultiPolylineXY(self.asMultiPolyline(tolerance2ApproxCurve))


   #===============================================================================
   # copy
   #===============================================================================
   def copy(self):
      # obbligatoria
      return QadMultiLinearObject(self)
   

   #============================================================================
   # move
   #============================================================================
   def move(self, offsetX, offsetY):
      """
      la funzione sposta il gli oggetti lineari secondo un offset X e uno Y
      """
      for linearObject in self.defList:
         linearObject.move(offsetX, offsetY)


   #============================================================================
   # rotate
   #============================================================================
   def rotate(self, basePt, angle):
      for linearObject in self.defList:
         linearObject.rotate(basePt, angle)


   #============================================================================
   # scale
   #============================================================================
   def scale(self, basePt, scale):
      for linearObject in self.defList:
         linearObject.scale(basePt, scale)


   #============================================================================
   # mirror
   #============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for linearObject in self.defList:
         linearObject.mirror(mirrorPt, mirrorAngle)


   #============================================================================
   # qty
   #============================================================================
   def qty(self):
      """
      la funzione restituisce la quantità di oggetti lineari che compongono il multilinea.
      """
      return len(self.defList)
         

   #============================================================================
   # getCentroid
   #============================================================================
   def getCentroid(self, tolerance2ApproxCurve = None):
      """
      la funzione restituisce il punto centroide.
      """
      g = self.asGeom(tolerance2ApproxCurve)
      if g is not None:
         centroid = g.centroid()
         if centroid is not None:
            return g.centroid().asPoint()

      return None

   
   #===============================================================================
   # transform
   #===============================================================================
   def transform(self, coordTransform):
      """
      la funzione restituisce un nuovo multilinea con le coordinate trasformate.
      """
      result = QadMultiLinearObject()
      for linearObject in self.defList:
         result.append(linearObject.transform(coordTransform))
      return result
   

   #===============================================================================
   # transformFromCRSToCRS
   #===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """
      la funzione trasforma le coordinate dei punti che compongono il multilinea.
      """
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   #===============================================================================
   # getBoundingBox
   #===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude gli elementi lineari.
      """
      boundingBox = self.getLinearObjectAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getLinearObjectAt(i).getBoundingBox())
         i = i + 1
         
      return boundingBox


   #===============================================================================
   # containsPt
   #===============================================================================
   def containsPt(self, pt):
      """
      la funzione ritorna True se il punto è sulla multilinea altrimenti False.
      """
      for linearObject in self.defList:
         if linearObject.containsPt(pt): return True
         
      return False


#===============================================================================
# QadMultiPolygon class
# rappresenta una lista di poligoni
#===============================================================================
class QadMultiPolygon():
    
   def __init__(self, multiPolygon=None):
      self.defList = []
      # deflist = (<poligono 1> <poligono 2>...)
      if multiPolygon is not None:
         self.set(multiPolygon)


   #============================================================================
   # whatIs
   #============================================================================
   def whatIs(self):
      return "MULTI_POLYGON"


   #============================================================================
   # set
   #============================================================================
   def set(self, multiPolygon):
      self.removeAll()
      for polygon in multiPolygon.defList:
         self.append(polygon)
      return self


   def __eq__(self, multiPolygon):
      # obbligatoria
      """self == other"""
      if multiPolygon.whatIs() != "MULTI_POLYGON": return False
      if self.qty() != multiPolygon.qty(): return False
      for i in range(0, self.qty()):
         if self.getPointAt(i) != multiPolygon.getPolygonAt(i): return False
      return True
  
  
   def __ne__(self, multiPolygon):
      """self != other"""
      return not self.__eq__(multiPolygon)


   #============================================================================
   # append
   #============================================================================
   def append(self, polygon):
      """
      la funzione aggiunge un poligono in fondo alla lista.
      """
      if polygon is None: return
      if polygon.whatIs() != "POLYGON": return False
      self.defList.append(polygon.copy())
      return True

   
   #============================================================================
   # insert
   #============================================================================
   def insert(self, i, polygon):
      """
      la funzione aggiunge un poligono nella posizione i-esima della lista dei poligoni.
      """
      if i >= self.qty():
         return self.append(polygon)
      else:         
         return self.defList.insert(i, polygon.copy())


   #============================================================================
   # remove
   #============================================================================
   def remove(self, i):
      """
      la funzione cancella un poligono nella posizione i-esima della lista.
      """
      del self.defList[i]


   #============================================================================
   # removeAll
   #============================================================================
   def removeAll(self):
      """
      la funzione cancella i poligoni della lista.
      """
      del self.defList[:]


   #============================================================================
   # getPolygonAt
   #============================================================================
   def getPolygonAt(self, i):
      """
      la funzione restituisce il poligono alla posizione i-esima 
      con numeri negativi parte dal fondo (es. -1 = ultima posizione)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]
   

   #============================================================================
   # setPolygonAt
   #============================================================================
   def setPolygonAt(self, polygon, i):
      """
      la funzione setta il poligono i-esimo
      """
      return self.getPolygonAt(i).set(polygon)

   
   #============================================================================
   # fromMultiPolygon
   #============================================================================
   def fromMultiPolygon(self, polygonList):
      """
      la funzione inizializza una lista di poligoni che compone il multipoligono passato in forma di lista di punti.
      """
      self.removeAll()
      polygon = QadPolygon()      
      
      for points in polygonList:
         # verifico se è un poligono
         if polygon.fromPolygon(points):
            self.append(polygon)
   
      if self.qty() == 0: return False
      return True


   #============================================================================
   # fromGeom
   #============================================================================
   def fromGeom(self, geom):
      """
      la funzione inizializza il multipoligono da un oggetto QgsGeometry.
      """
      return self.fromMultiPolygon(geom.asMultiPolygon())


   #===============================================================================
   # asMultiPolygon
   #===============================================================================
   def asMultiPolygon(self, tolerance2ApproxCurve = None):
      """
      la funzione ritorna una lista di liste di liste di punti che compongono un multipoligono.
      """
      result = []
      for polygon in self.defList:
         result.append(polygon.asPolygon(tolerance2ApproxCurve))

      return result

   
   #===============================================================================
   # asGeom
   #===============================================================================
   def asGeom(self, tolerance2ApproxCurve = None):
      """
      la funzione ritorna il poligono in forma di QgsGeometry.
      """
      return QgsGeometry.fromMultiPolygonXY(self.asMultiPolygon(tolerance2ApproxCurve))

   
   #===============================================================================
   # copy
   #===============================================================================
   def copy(self):
      # obbligatoria
      return QadMultiPolygon(self)
   

   #============================================================================
   # move
   #============================================================================
   def move(self, offsetX, offsetY):
      """
      la funzione sposta i poligoni secondo un offset X e uno Y
      """
      for polygon in self.defList:
         polygon.move(offsetX, offsetY)


   #============================================================================
   # rotate
   #============================================================================
   def rotate(self, basePt, angle):
      for polygon in self.defList:
         polygon.rotate(basePt, angle)


   #============================================================================
   # scale
   #============================================================================
   def scale(self, basePt, scale):
      for polygon in self.defList:
         polygon.scale(basePt, scale)


   #============================================================================
   # mirror
   #============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for polygon in self.defList:
         polygon.mirror(mirrorPt, mirrorAngle)


   #============================================================================
   # qty
   #============================================================================
   def qty(self):
      """
      la funzione restituisce la quantità di poligoni che compongono il multipoligono.
      """
      return len(self.defList)
         

   #============================================================================
   # getCentroid
   #============================================================================
   def getCentroid(self, tolerance2ApproxCurve = None):
      """
      la funzione restituisce il punto centroide.
      """
      g = self.asGeom(tolerance2ApproxCurve)
      if g is not None:
         centroid = g.centroid()
         if centroid is not None:
            return g.centroid().asPoint()

      return None

   
   #===============================================================================
   # transform
   #===============================================================================
   def transform(self, coordTransform):
      """
      la funzione restituisce un nuovo multipoligono con le coordinate trasformate.
      """
      result = QadMultiPolygon()
      for polygon in self.defList:
         result.append(polygon.transform(coordTransform))
      return result
   

   #===============================================================================
   # transformFromCRSToCRS
   #===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """
      la funzione trasforma le coordinate dei punti che compongono il multipoligono.
      """
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   #===============================================================================
   # getBoundingBox
   #===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude il multi poligono.
      """
      boundingBox = self.getPolygonAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getPolygonAt(i).getBoundingBox())
         i = i + 1
         
      return boundingBox


   #===============================================================================
   # containsPt
   #===============================================================================
   def containsPt(self, pt):
      """
      la funzione ritorna True se il punto è sul multi poligono altrimenti False.
      """
      for polygon in self.defList:
         if polygon.containsPt(pt): return True
         
      return False


#===============================================================================
# fromQgsGeomtoQadGeom
#===============================================================================
def fromQgsGeomToQadGeom(QgsGeom, crs = None):
   """
   la funzione ritorna una geometria di QAD da una geometria di QGIS e il suo sistema di coordinate.
   Le coordinate della geometria di QAD sono quelle del canvas per lavorare con coordinate piane xy
   """
   
   QgsMessageLog.logMessage('fromQgsGeomToQadGeom', "DEBUG_QAD")  


   g = QgsGeometry(QgsGeom)
   
   if crs is None:
      g = QgsGeom
   else:
      # trasformo la geometria nel crs del canvas per lavorare con coordinate piane xy
      canvasCrs = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
      if crs != canvasCrs:
         coordTransform = QgsCoordinateTransform(crs, canvasCrs, QgsProject.instance())
         g.transform(coordTransform)

   # commentato perchè se ho un poligono e lo divido in 2 parti diventa non valido ma lo si vuole gestire comunque
   # a volte la trasformazione di coordinate genera oggetti non validi
   #if g.isGeosValid() == False: return None
   baseType = QgsWkbTypes.geometryType(g.wkbType())
   isMulti = QgsWkbTypes.isMultiType(g.wkbType())

   if baseType == QgsWkbTypes.PointGeometry and not isMulti:
      qadGeom = QadPoint()
      if qadGeom.fromGeom(g): return qadGeom
   elif baseType == QgsWkbTypes.PointGeometry and isMulti:
      qadGeom = QadMultiPoint()
      if qadGeom.fromGeom(g): return qadGeom
         
   elif baseType == QgsWkbTypes.LineGeometry and not isMulti:
      return QadLinearObject.fromGeom(g)
   elif baseType == QgsWkbTypes.LineGeometry and isMulti:
      qadGeom = QadMultiLinearObject()
      if qadGeom.fromGeom(g): return qadGeom
         
   elif baseType == QgsWkbTypes.PolygonGeometry and not isMulti:
      qadGeom = QadPolygon()
      if qadGeom.fromGeom(g): return qadGeom
   elif baseType == QgsWkbTypes.PolygonGeometry and isMulti:
      qadGeom = QadMultiPolygon()
      if qadGeom.fromGeom(g): return qadGeom
   
   return None


#===============================================================================
# fromQadGeomToQgsGeom
#===============================================================================
def fromQadGeomToQgsGeom(qadGeom, crs):
   """
   la funzione ritorna una geometria di QGIS da una geometria di QAD.
   Le coordinate della geometria di QAD sono quelle del canvas per lavorare con coordinate piane xy
   """
   g = qadGeom.asGeom()
   if g is None: return None
   
   if crs is not None:
      # trasformo la geometria nel crs del layer (la geometria di QAD è nel sistema del canvas per lavorare con coordinate piane xy)
      canvasCrs = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
      if crs != canvasCrs:
         coordTransform = QgsCoordinateTransform(canvasCrs, crs, QgsProject.instance())
         g.transform(coordTransform)
   
   return g


#===============================================================================
# getQadGeomAt
#===============================================================================
def getQadGeomAt(qadGeom, atGeom = 0, atSubGeom = 0):
   """
   la funzione ritorna la geometria alla posizione specificata
   """
   qadGeomType = qadGeom.whatIs()
   if qadGeomType == "MULTI_POINT":
      return None if atSubGeom != 0 else qadGeom.getPointAt(atGeom)
   elif qadGeomType == "MULTI_LINEAR_OBJ":
      return None if atSubGeom != 0 else qadGeom.getLinearObjectAt(atGeom)
   elif qadGeomType == "MULTI_POLYGON":
      g = qadGeom.getPolygonAt(atGeom)
      if g is None: return None
      return g.getClosedObjectAt(atSubGeom)
   elif qadGeomType == "POLYGON":
      return None if atGeom != 0 else qadGeom.getClosedObjectAt(atSubGeom)
   else:
      return None if atGeom != 0 or atSubGeom != 0 else qadGeom


#===============================================================================
# getQadGeomPartAt
#===============================================================================
def getQadGeomPartAt(qadGeom, atGeom = 0, atSubGeom = 0, atPart = 0):
   """
   la funzione ritorna la parte della geometria alla posizione specificata
   """
   subQadGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom)
   if subQadGeom is None: return None
   qadSubGeomType = subQadGeom.whatIs()
   if qadSubGeomType == "POLYLINE":
      return subQadGeom.getLinearObjectAt(atPart)
   else:
      return subQadGeom
   

#===============================================================================
# setQadGeomAt
#===============================================================================
def setQadGeomAt(qadGeom, newGeom, atGeom = 0, atSubGeom = 0):
   """
   la funzione retituisce la nuova geometria modificata alla posizione specificata
   """
   qadGeomType = qadGeom.whatIs()
   if qadGeomType == "MULTI_POINT" or qadGeomType == "MULTI_LINEAR_OBJ":
      if atSubGeom != 0: return None
      newQadGeom = qadGeom.copy()
      newQadGeom.remove(atGeom)
      newQadGeom.insert(atGeom, newGeom)
   elif qadGeomType == "MULTI_POLYGON":
      newQadGeom = qadGeom.copy()
      if atSubGeom == 0:
         newQadGeom.remove(atGeom)
         newQadGeom.insert(atGeom, newGeom)
      else:
         g = newQadGeom.getPolygonAt(atGeom)
         g.remove(atSubGeom)
         g.insert(atSubGeom, newGeom)
   elif qadGeomType == "POLYGON":
      if atGeom != 0: return None
      newQadGeom = qadGeom.copy()
      newQadGeom.remove(atSubGeom)
      newQadGeom.insert(atSubGeom, newGeom)
   else:
      if atGeom != 0 or atSubGeom != 0: return None
      newQadGeom = newGeom
      
   return newQadGeom


#===============================================================================
# delQadGeomAt
#===============================================================================
def delQadGeomAt(qadGeom, atGeom = 0, atSubGeom = 0):
   """
   la funzione cancella la sotto-geometria alla posizione specificata
   """
   qadGeomType = qadGeom.whatIs()
   if qadGeomType == "MULTI_POINT":
      if atSubGeom != 0:
         return False
      else:
         del qadGeom.defList[atGeom]
         return True
   elif qadGeomType == "MULTI_LINEAR_OBJ":
      if atSubGeom != 0:
         return False
      else:
         del qadGeom.defList[atGeom]
         return True
   elif qadGeomType == "MULTI_POLYGON":
      g = qadGeom.getPolygonAt(atGeom)
      if g is None:
         return False
      del g.defList[atSubGeom]
      return True
   elif qadGeomType == "POLYGON":
      if atGeom != 0:
         return False
      else:
         del qadGeom.defList[atSubGeom]
      return True
   else:
      return False


#===============================================================================
# isLinearQadGeom
#===============================================================================
def isLinearQadGeom(qadGeom):
   """
   la funzione retituisce True se si tratta di una geometria lineare
   """
   gType = qadGeom.whatIs()
   if gType == "POLYLINE" or gType == "LINE" or gType == "ARC" or gType == "ELLIPSE_ARC":
      return True
   else:
      return False


#===============================================================================
# convertToPolyline
#===============================================================================
def convertToPolyline(qadGeom):
   """
   la funzione trasforma una geometria in QadPolyline, se possibile
   """
   gType = qadGeom.whatIs()
   if gType != "POLYLINE" and gType != "LINE" and gType != "ARC" and gType != "ELLIPSE_ARC":
      return None
   if gType == "POLYLINE":
      polyline = qadGeom.copy()
   else:
      polyline = QadPolyline()
      polyline.append(qadGeom)
   
   return polyline


#===============================================================================
# QadGeomBoundingBoxCache class
# classe per cercare velocemente quali parti di una polilinea o poligono o multi oggetto si intersecano con
# un boundingBox. 
#===============================================================================
class QadGeomBoundingBoxCache():

   def __init__(self, geom):
      # creo un layer temporaneo in memoria
      self.cacheLayer = createMemoryLayer("QadLayerCacheArea", "Polygon", qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())
      
      provider = self.cacheLayer.dataProvider()
      provider.addAttributes([QgsField("geom_at", QVariant.Int, "Int")]) # codice della geometria
      provider.addAttributes([QgsField("sub_geom_at", QVariant.Int, "Int")]) # codice della sotto geometria
      provider.addAttributes([QgsField("part_at", QVariant.Int, "Int")]) # codice della parte
      self.cacheLayer.updateFields()
      
      if provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
         provider.createSpatialIndex()

      if self.cacheLayer.startEditing() == False: return

      geomAt = 0
      subGeomAt = 0
      partAt = 0
      error = False
      geomType = geom.whatIs()
      
      if geomType == "MULTI_POINT":
         for geomAt in range(0, geom.qty()):
            if self.insertBoundingBox(self.getPointAt(geomAt).getBoundingBox(), geomAt, subGeomAt, partAt) == False:
               error = True
               break
            
      elif geomType == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, geom.qty()):
            linearObj =  geom.getLinearObjectAt(geomAt)
            if linearObj.whatIs() == "POLYLINE":
               for partAt in range(0, linearObj.qty()):
                  part = linearObj.getLinearObjectAt(partAt)
                  if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                     error = True
                     break
            else:
               if self.insertBoundingBox(linearObj.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                  error = True
            if error: break
            
      elif geomType == "POLYLINE":
         for partAt in range(0, geom.qty()):
            part = geom.getLinearObjectAt(partAt)
            if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
               error = True
               break
         
      elif geomType == "POLYGON":
         for subGeomAt in range(0, geom.qty()):
            closedObj = geom.getClosedObjectAt(geomAt)
            for partAt in range(0, closedObj.qty()):
               part = closedObj.getLinearObjectAt(partAt)
               if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                  error = True
                  break
            if error: break

      elif geomType == "MULTI_POLYGON":
         for geomAt in range(0, geom.qty()):
            polygon = geom.getPolygonAt(geomAt)
            for subGeomAt in range(0, polygon.qty()):
               closedObj =  subGeomAt.getClosedObjectAt(subGeomAt)
               for partAt in range(0, closedObj.qty()):
                  part = closedObj.getLinearObjectAt(partAt)
                  if self.insertBoundingBox(part.getBoundingBox(), geomAt, subGeomAt, partAt) == False:
                     error = True
                     break
               if error: break
            if error: break

      else:
         error = True if self.insertBoundingBox(geom.getBoundingBox(), geomAt, subGeomAt, partAt) == False else False 
      
      if error:
         self.cacheLayer.rollBack()
         del self.cacheLayer
         self.cacheLayer = None
      else:
         self.cacheLayer.commitChanges()

         
   #============================================================================
   # __del__
   #============================================================================
   def __del__(self):
      del self.cacheLayer
      self.cacheLayer = None


   #============================================================================
   # insertBoundingBox
   #============================================================================
   def insertBoundingBox(self, boundingBox, geomAt, subGeomAt, partAt):
      newFeature = QgsFeature()
      newFeature.initAttributes(3)
      newFeature.setAttribute(0, geomAt)
      newFeature.setAttribute(1, subGeomAt)
      newFeature.setAttribute(2, partAt)
      newFeature.setGeometry(QgsGeometry().fromRect(boundingBox))
      return self.cacheLayer.addFeature(newFeature)


   #============================================================================
   # getIntersectionWithBoundingBox
   #============================================================================
   def getIntersectionWithBoundingBox(self, boundingBox):
      request = QgsFeatureRequest()
      request.setFilterRect(boundingBox)
      request.setSubsetOfAttributes([])
      
      feature = QgsFeature()
      result = []
      featureIterator = self.cacheLayer.getFeatures(request)
      for feature in featureIterator:
         geom_at = feature.attribute("geom_at")
         sub_geom_at = feature.attribute("sub_geom_at")
         part_at = feature.attribute("part_at")
         result.append((geom_at, sub_geom_at, part_at))
      
      return result
   
   
   #============================================================================
   # getTotalBoundingBox
   #============================================================================
   def getTotalBoundingBox(self):
      feature = QgsFeature()
      featureIterator = self.cacheLayer.getFeatures(qad_utils.getFeatureRequest())
      result = None
      for feature in featureIterator:
         if result is None:
            result = feature.geometry().boundingBox()
         else:
            result.combineExtentWith(feature.geometry().boundingBox())
      return result