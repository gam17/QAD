# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione delle linee
 
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


#===============================================================================
# QadLine line class
#===============================================================================
class QadLine():
    
   def __init__(self, line = None):
      if line is not None:
         self.set(line.pt1, line.pt2)
      else:    
         self.pt1 = None
         self.pt2 = None


   def whatIs(self):
      # obbligatoria
      return "LINE"

   
   def set(self, pt1, pt2 = None):
      if isinstance(pt1, QadLine):
         line = pt1
         return self.set(line.pt1, line.pt2)
      
      self.pt1 = QgsPointXY(pt1)
      self.pt2 = QgsPointXY(pt2)
      return self

   def transform(self, coordTransform):
      # obbligatoria
      """Transform this geometry as described by CoordinateTransform ct."""
      self.pt1 = coordTransform.transform(self.pt1)
      self.pt2 = coordTransform.transform(self.pt2)


   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      # obbligatoria
      """Transform this geometry as described by CRS."""
      if (sourceCRS is not None) and (destCRS is not None) and sourceCRS != destCRS:       
         coordTransform = QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()) # trasformo le coord
         self.transform(coordTransform)

      
   def __eq__(self, line):
      # obbligatoria
      """self == other"""
      if line.whatIs() != "LINE": return False
      # strettamente uguali (conta il verso)
      if self.pt1 != line.pt1 or self.pt2 != line.pt2:
         return False
      else:
         return True    

  
   def __ne__(self, line):
      """self != other"""
      return not self.__eq__(line)


   def equals(self, line):
      # uguali geometricamente (NON conta il verso)
      if line.whatIs() != "LINE": return False
      if self.__eq__(line): return True
      dummy = line.copy()
      dummy.reverse()
      return self.__eq__(dummy)


   def copy(self):
      # obbligatoria
      return QadLine(self)


   #============================================================================
   # reverse
   #============================================================================
   def reverse(self):
      # obbligatoria
      # inverto direzione della linea
      dummy = self.pt1
      self.pt1 = self.pt2 
      self.pt2 = dummy
      return self

   #============================================================================
   # getStartPt, setStartPt
   #============================================================================
   def getStartPt(self):
      # obbligatoria
      return self.pt1
   
   def setStartPt(self, pt):
      # obbligatoria
      self.pt1 = QgsPointXY(pt)
   
   
   #============================================================================
   # getEndPt, setEndPt
   #============================================================================
   def getEndPt(self):
      # obbligatoria
      return self.pt2
   
   def setEndPt(self, pt):
      # obbligatoria
      self.pt2 = QgsPointXY(pt)
      

   #===============================================================================
   # getMiddlePt
   #===============================================================================
   def getMiddlePt(self):
      """
      la funzione ritorna il punto medio della linea (QgsPointXY)
      """
      x = (self.pt1.x() + self.pt2.x()) / 2
      y = (self.pt1.y() + self.pt2.y()) / 2
      
      return QgsPointXY(x, y)


   #===============================================================================
   # getBoundingBox
   #===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude il segmento.
      """
      if self.pt1.x() > self.pt2.x():
         xMaxLine = self.pt1.x()
         xMinLine = self.pt2.x()
      else:
         xMaxLine = self.pt2.x()
         xMinLine = self.pt1.x()
        
      if self.pt1.y() > self.pt2.y():
         yMaxLine = self.pt1.y()
         yMinLine = self.pt2.y()
      else:
         yMaxLine = self.pt2.y()
         yMinLine = self.pt1.y()
   
      return QgsRectangle(xMinLine, yMinLine, xMaxLine, yMaxLine)


   #============================================================================
   # getTanDirectionOnPt
   #============================================================================
   def getTanDirectionOnPt(self, pt = None):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto dell'oggetto.
      pt è usato solo per compatibilità con le altre classi lineari (es. arco)
      """
      return qad_utils.getAngleBy2Pts(self.getStartPt(), self.getEndPt())


   #============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   #============================================================================
   def getTanDirectionOnStartPt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto iniziale dell'oggetto.
      """
      return self.getTanDirectionOnPt()

   def getTanDirectionOnEndPt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto finale dell'oggetto.
      """
      return self.getTanDirectionOnPt()

   def getTanDirectionOnMiddlePt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto medio dell'oggetto.
      """
      return self.getTanDirectionOnPt()


   #============================================================================
   # fromPt1PolarPt2
   #============================================================================
   def fromPt1PolarPt2(self, pt1, angle, dist):
      """
      setta le caratteristiche della linea attraverso:
      punto iniziale
      angolo
      distanza dal punto iniziale
      """
      self.pt1 = QgsPointXY(pt1)
      self.pt2 = qad_utils.getPolarPointByPtAngle(pt1, angle, dist)
      return True


   #===============================================================================
   # getXOnInfinityLine
   #===============================================================================
   def getXOnInfinityLine(self, y):
      """
      data la coordinata Y di un punto la funzione ritorna la coordinata X dello stesso
      sulla linea 
      """
      
      diffX = self.pt2.x() - self.pt1.x()
      diffY = self.pt2.y() - self.pt1.y()
                             
      if qad_utils.doubleNear(diffX, 0): # se la retta passante per p1 e p2 é verticale
         return self.pt1.x()
      elif qad_utils.doubleNear(diffY, 0): # se la retta passante per p1 e p2 é orizzontale
         return None # infiniti punti
      else:
         coeff = diffY / diffX
         return self.pt1.x() + (y - self.pt1.y()) / coeff


   #===============================================================================
   # getYOnInfinityLine
   #===============================================================================
   def getYOnInfinityLine(self, x):
      """
      data la coordinata X di un punto la funzione ritorna la coordinata Y dello stesso
      sulla linea
      """
      
      diffX = self.pt2.x() - self.pt1.x()
      diffY = self.pt2.y() - self.pt1.y()
                             
      if qad_utils.doubleNear(diffX, 0): # se la retta passante per p1 e p2 é verticale
         return None # infiniti punti
      elif qad_utils.doubleNear(diffY, 0): # se la retta passante per p1 e p2 é orizzontale
         return self.pt1.y()
      else:
         coeff = diffY / diffX
         return self.pt1.y() + (x - self.pt1.x()) * coeff
   

   #===============================================================================
   # getSqrLength
   #===============================================================================
   def getSqrLength(self):
      """
      la funzione ritorna la lunghezza al quadrato della linea
      """
      dx = self.pt2.x() - self.pt1.x()
      dy = self.pt2.y() - self.pt1.y()
      
      return dx * dx + dy * dy


   #===============================================================================
   # length
   #===============================================================================
   def length(self):
      # obbligatoria
      return math.sqrt(self.getSqrLength())


   #===============================================================================
   # getMinDistancePtBetweenSegmentAndPt
   #===============================================================================
   def getMinDistancePtBetweenSegmentAndPt(self, pt):
      """
      la funzione ritorna il punto di distanza minima e la distanza minima tra un segmento ed un punto
      (<punto di distanza minima><distanza minima>)
      """
      if self.containsPt(pt) == True:
         return [pt, 0]
      perpPt = self.getPerpendicularPointOnInfinityLine(pt)
      if perpPt is not None:
         if self.containsPt(perpPt) == True:
            return [perpPt, perpPt.distance(pt)]
   
      distFromP1 = self.pt1.distance(pt)
      distFromP2 = self.pt2.distance(pt)
      if distFromP1 < distFromP2:
         return [self.pt1, distFromP1]
      else:
         return [self.pt2, distFromP2]


   #===============================================================================
   # getPerpendicularPointOnInfinityLine
   #===============================================================================
   def getPerpendicularPointOnInfinityLine(self, pt):
      """
      la funzione ritorna il punto di proiezione perpendicolare di pt alla linea.
      """
      
      diffX = self.pt2.x() - self.pt1.x()
      diffY = self.pt2.y() - self.pt1.y()
                             
      if qad_utils.doubleNear(diffX, 0): # se la retta passante per p1 e p2 é verticale
         return QgsPointXY(self.pt1.x(), pt.y())
      elif qad_utils.doubleNear(diffY, 0): # se la retta passante per p1 e p2 é orizzontale
         return QgsPointXY(self.pt.x(), pt1.y())
      else:
         coeff = diffY / diffX
         x = (coeff * self.pt1.x() - self.pt1.y() + pt.x() / coeff + pt.y()) / (coeff + 1 / coeff)
         y = coeff * (x - self.pt1.x()) + self.pt1.y()
         
         return QgsPointXY(x, y)


   #===============================================================================
   # getInfinityLinePerpOnMiddle
   #===============================================================================
   def getInfinityLinePerpOnMiddle(self):
      """
      la funzione trova una linea perpendicolare e passante per il punto medio della linea.
      """
      ptMiddle = self.getMiddlePt()
      dist = self.pt1.distance(ptMiddle)
      if dist == 0:
         return None
      angle = qad_utils.getAngleBy2Pts(self.pt1, self.pt2) + math.pi / 2
      pt2Middle = qad_utils.getPolarPointByPtAngle(ptMiddle, angle, dist)
      line = QadLine()
      line.set(ptMiddle, pt2Middle)
      return line


   #===============================================================================
   # isPtOnInfinityLine
   #===============================================================================
   def isPtOnInfinityLine(self, point):
      """
      la funzione ritorna true se il punto é sul segmento (estremi compresi).
      point è di tipo QgsPointXY.
      """
      y = self.getYOnInfinityLine(point.x())
      if y is None: # la linea infinita lineP1-lineP2 é verticale
         if qad_utils.doubleNear(point.x(), self.pt1.x()):
            return True
      else:
         # se il punto é sulla linea infinita che passa da p1-p2
         if qad_utils.doubleNear(point.y(), y):
            return True
            
      return False  

      
   #===============================================================================
   # containsPt
   #===============================================================================
   def containsPt(self, point):
      # obbligatoria
      """
      la funzione ritorna true se il punto é sul segmento (estremi compresi).
      point è di tipo QgsPointXY.
      """
      if self.pt1.x() < self.pt2.x():
         xMin = self.pt1.x()
         xMax = self.pt2.x()
      else:
         xMax = self.pt1.x()
         xMin = self.pt2.x()
        
      # verifico se il punto può essere sul segmento
      if qad_utils.doubleSmaller(point.x(), xMin) or qad_utils.doubleGreater(point.x(), xMax): return False
         
      if self.pt1.y() < self.pt2.y():
         yMin = self.pt1.y()
         yMax = self.pt2.y()
      else:
         yMax = self.pt1.y()
         yMin = self.pt2.y()
   
      # verifico se il punto può essere sul segmento
      if qad_utils.doubleSmaller(point.y(), yMin) or qad_utils.doubleGreater(point.y(), yMax): return False
        
      return self.isPtOnInfinityLine(point)
      

   #===============================================================================
   # leftOf
   #===============================================================================
   def leftOf(self, pt):
      # obbligatoria
      """
      la funzione ritorna una numero < 0 se il punto pt é alla sinistra della linea pt1 -> pt2
      """
      f1 = pt.x() - self.pt1.x()
      f2 = self.pt2.y() - self.pt1.y()
      f3 = pt.y() - self.pt1.y()
      f4 = self.pt2.x() - self.pt1.x()
      return f1*f2 - f3*f4


   #===============================================================================
   # get a and b for line equation (y = ax + b) 
   #===============================================================================
   def get_A_B_LineEquation(self):
      # dati 2 punti vengono calcolati a e b dell'equazione della retta passante per i due punti (y = ax + b)
      a = (self.pt2.y() - self.pt1.y()) / (self.pt2.x() - self.pt1.x())
      # y = ax + b -> b = y - ax
      b = self.pt1.y() - (a * self.pt1.x())
      
      return a, b


   #===============================================================================
   # sqrDist
   #===============================================================================
   def sqrDist(self, point):
      # obbligatoria
      """
      la funzione ritorna una lista con 
      (<minima distanza al quadrato>
       <punto più vicino>)
      """
      minDistPoint = QgsPointXY()
      
      if self.pt1.x() == self.pt2.x() and self.pt1.y() == self.pt2.y():
         minDistPoint.setX(self.pt1.x())
         minDistPoint.setY(self.pt1.y())
      else:
         nx = self.pt2.y() - self.pt1.y()
         ny = -( self.pt2.x() - self.pt1.x() )
      
         t = (point.x() * ny - point.y() * nx - self.pt1.x() * ny + self.pt1.y() * nx ) / \
             (( self.pt2.x() - self.pt1.x() ) * ny - ( self.pt2.y() - self.pt1.y() ) * nx )
      
         if t < 0.0:
            minDistPoint.setX(self.pt1.x())
            minDistPoint.setY(self.pt1.y())
         elif t > 1.0:
            minDistPoint.setX(self.pt2.x())
            minDistPoint.setY(self.pt2.y())
         else:
            minDistPoint.setX( self.pt1.x() + t *( self.pt2.x() - self.pt1.x() ) )
            minDistPoint.setY( self.pt1.y() + t *( self.pt2.y() - self.pt1.y() ) )
   
      dist = point.sqrDist(minDistPoint)
      # prevent rounding errors if the point is directly on the segment 
      if qad_utils.doubleNear(dist, 0.0):
         minDistPoint.setX( point.x() )
         minDistPoint.setY( point.y() )
         return (0.0, minDistPoint)
     
      return (dist, minDistPoint)


   #============================================================================
   # getDistanceFromStart
   #============================================================================
   def getDistanceFromStart(self, pt):
      # obbligatoria
      """
      la funzione restituisce la distanza di <pt> (che deve essere sull'oggetto o sua estensione)
      dal punto iniziale.
      """
      dummy = QadLine(self)
      dummy.setEndPt(pt)

      # se il punto é sull'estensione dalla parte del punto iniziale      
      if self.containsPt(pt) == False and \
         self.getStartPt().distance(pt) < self.getEndPt().distance(pt):
         return -dummy.length()
      else:
         return dummy.length()


   #============================================================================
   # getPointFromStart
   #============================================================================
   def getPointFromStart(self, distance):
      # obbligatoria
      """
      la funzione restituisce un punto (e la direzione della tangente) alla distanza <distance> 
      (che deve essere sull'oggetto) dal punto iniziale.
      """
      if distance < 0:
         return None, None
      l = self.length()
      if distance > l:
         return None, None
     
      angle = self.getTanDirectionOnStartPt()
      return qad_utils.getPolarPointByPtAngle(self.getStartPt(), angle, distance), angle


   #============================================================================
   # getDistanceFromEnd
   #============================================================================
   def getDistanceFromEnd(self, pt):
      # obbligatoria
      """
      la funzione restituisce la distanza di <pt> (che deve essere sull'oggetto o sua estensione)
      dal punto finale.
      """
      return self.length() - self.getDistanceFromStart()


   #===============================================================================
   # getPointFromEnd
   #===============================================================================
   def getPointFromEnd(self, distance):
      """
      la funzione restituisce un punto (e la direzione della tangente) alla distanza <distance> 
      (che deve essere sull'oggetto) dal punto finale.
      """
      d = self.length() - distance
      return self.getPointFromStart(d)


   #============================================================================
   # asPolyline
   #============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      # obbligatoria
      """
      ritorna una lista di punti che definisce la linea
      """
      return [self.getStartPt(), self.getEndPt()]


   #===============================================================================
   # asLineString
   #===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None, forcedStartPt = None):
      """
      la funzione ritorna la linea in forma di lineString.
      tolerance2ApproxCurve e atLeastNSegment sono usati solo per compatibilità
      Quando la linea fa parte di una polilinea è necessario che il suo punto iniziale coincida con quello finale della parte precedente
      percui il punto iniziale viene forzato.      
      """
      if forcedStartPt is None:
         return QgsLineString(QgsPoint(self.getStartPt()), QgsPoint(self.getEndPt()))
      else:
         return QgsLineString(QgsPoint(forcedStartPt), QgsPoint(self.getEndPt()))
      

   #===============================================================================
   # asAbstractGeom
   #===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna la linea in forma di QgsAbstractGeometry.
      """
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CompoundCurve:
         lineString = self.asLineString()
         compoundCurve = QgsCompoundCurve()
         compoundCurve.addCurve(lineString)
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         lineString = self.asLineString()
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(lineString)   
         return multiCurve

      elif flatType == QgsWkbTypes.MultiLineString:
         lineString = self.asLineString()
         multiLineString = QgsMultiLineString()
         multiLineString.addGeometry(lineString)   
         return multiLineString
      
      return self.asLineString()
      

   #===============================================================================
   # asGeom
   #===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna la linea in forma di QgsGeometry.
      tolerance2ApproxCurve e atLeastNSegment sono dichiarati solo per compatibilità
      """     
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))


   #============================================================================
   # lengthen_delta
   #============================================================================
   def lengthen_delta(self, move_startPt, delta):
      # obbligatoria
      """
      la funzione sposta il punto iniziale (se move_startPt = True) o finale (se move_startPt = False)
      di una distanza delta
      """
      length = self.length()
      # lunghezza della parte + delta non può essere <= 0
      if length + delta <= 0:
         return False
      
      angle = self.getTanDirectionOnPt()
      if move_startPt == True:
         self.setStartPt(qad_utils.getPolarPointByPtAngle(self.getStartPt(), angle + math.pi, delta))
      else:
         self.setEndPt(qad_utils.getPolarPointByPtAngle(self.getEndPt(), angle, delta))
      return True


   #============================================================================
   # lengthen_deltaAngle
   #============================================================================
   def lengthen_deltaAngle(self, move_startPt, delta):
      # obbligatoria
      """
      la funzione sposta il punto iniziale (se move_startPt = True) o finale (se move_startPt = False)
      della linea di un certo numero di gradi delta rispetto il coefficiente angolare precedente
      """
      angle = self.getTanDirectionOnPt()
      if move_startPt == True:
         self.setStartPt(qad_utils.getPolarPointByPtAngle(self.getEndPt(), angle + math.pi + delta, self.length()))
      else:
         self.setEndPt(qad_utils.getPolarPointByPtAngle(self.getStartPt(), angle + delta, self.length()))
      return True


   #============================================================================
   # move
   #============================================================================
   def move(self, offsetX, offsetY):
      # obbligatoria
      self.pt1 = qad_utils.movePoint(self.pt1, offsetX, offsetY)
      self.pt2 = qad_utils.movePoint(self.pt2, offsetX, offsetY)


   #============================================================================
   # rotate
   #============================================================================
   def rotate(self, basePt, angle):
      self.pt1 = qad_utils.rotatePoint(self.pt1, basePt, angle)
      self.pt2 = qad_utils.rotatePoint(self.pt2, basePt, angle)
   

   #============================================================================
   # scale
   #============================================================================
   def scale(self, basePt, scale):
      self.pt1 = qad_utils.scalePoint(self.pt1, basePt, scale)
      self.pt2 = qad_utils.scalePoint(self.pt2, basePt, scale)


   #============================================================================
   # mirror
   #============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      self.pt1 = qad_utils.mirrorPoint(self.pt1, mirrorPt, mirrorAngle)
      self.pt2 = qad_utils.mirrorPoint(self.pt2, mirrorPt, mirrorAngle)


   #===============================================================================
   # offset
   #===============================================================================
   def offset(self, offsetDist, offsetSide):
      """
      la funzione ritorna l'offset di una linea
      secondo una distanza e un lato di offset ("right" o "left")
      """
      if offsetSide == "right":
         AngleProjected = qad_utils.getAngleBy2Pts(self.pt1, self.pt2) - (math.pi / 2)
      else:
         AngleProjected = qad_utils.getAngleBy2Pts(self.pt1, self.pt2) + (math.pi / 2)
      # calcolo il punto proiettato
      self.pt1 = qad_utils.getPolarPointByPtAngle(self.pt1, AngleProjected, offsetDist)
      self.pt2 = qad_utils.getPolarPointByPtAngle(self.pt2, AngleProjected, offsetDist)
      return True


   #============================================================================
   # extend
   #============================================================================
   def extend(self, limitPt):
      """
      la funzione estende la linea (punto iniziale o finale della linea) fino ad incontrare il punto <limitPt>.
      """
      if self.pt1.distance(limitPt) < self.pt2.distance(limitPt):
         self.pt1.setX(limitPt.x())
         self.pt1.setY(limitPt.y())
      else:
         self.pt2.setX(limitPt.x())
         self.pt2.setY(limitPt.y())


   #===============================================================================
   # breakOnPts
   #===============================================================================
   def breakOnPts(self, firstPt, secondPt):
      # obbligatoria
      """
      la funzione spezza la geometria in un punto (se <secondPt> = None) o in due punti 
      come fa il trim. Ritorna una o due geometrie risultanti dall'operazione.
      <firstPt> = primo punto di divisione
      <secondPt> = secondo punto di divisione
      """
      # la funzione ritorna una lista con (<minima distanza al quadrato> <punto più vicino>)
      dummy = self.sqrDist(firstPt)
      myFirstPt = dummy[1]
      
      mySecondPt = None
      if secondPt is not None:
         dummy = self.sqrDist(secondPt)
         mySecondPt = dummy[1]
      
      # verifico se è il caso di invertire i punti
      if self.getDistanceFromStart(myFirstPt) > self.getDistanceFromStart(mySecondPt):
         dummy = myFirstPt
         myFirstPt = mySecondPt
         mySecondPt = dummy
      
      part1 = self.getGeomBetween2Pts(self.getStartPt(), myFirstPt)
      if mySecondPt is None:
         part2 = self.getGeomBetween2Pts(myFirstPt, self.getEndPt())
      else:
         part2 = self.getGeomBetween2Pts(mySecondPt, self.getEndPt())

      return [part1, part2]


   #===============================================================================
   # getGeomBetween2Pts
   #===============================================================================
   def getGeomBetween2Pts(self, startPt, endPt):
      """
      Ritorna una sotto geometria che parte dal punto startPt e finisce al punto endPt seguendo il tracciato della geometria.
      """
      if qad_utils.ptNear(startPt, endPt): return None
      if self.containsPt(startPt) == False: return None
      if self.containsPt(endPt) == False: return None
      
      return QadLine().set(startPt, endPt)
      
      
#===============================================================================
# getBoundingPtsOnOnInfinityLine
#===============================================================================
def getBoundingPtsOnOnInfinityLine(pts):
   """
   Data una lista di punti <pts> non ordinati su una linea infinita,
   la funzione ritorna i due punti estremi al fascio di punti (i due punti più lontani tra di loro).
   """
   tot = len(pts)
   if tot < 3:
      return pts[:] # copio la lista
   
   result = []  
   # elaboro i tratti intermedi
   # calcolo la direzione dal primo punto al secondo punto  
   angle = qad_utils.getAngleBy2Pts(pts[0], pts[1]) 
   # ciclo su tutti i punti considerando solo quelli che hanno la stessa direzione con il punto precedente (boundingPt1)
   i = 2
   boundingPt1 = pts[1]
   while i < tot:
      pt2 = pts[i]
      if qad_utils.TanDirectionNear(angle, qad_utils.getAngleBy2Pts(boundingPt1, pt2)):
         boundingPt1 = pt2
      i = i + 1

   # calcolo la direzione dal secondo punto al primo punto  
   angle = qad_utils.getAngleBy2Pts(pts[1], pts[0]) 
   # ciclo su tutti i punti considerando solo quelli che hanno la stessa direzione con il punto precedente (boundingPt2)
   i = 2
   boundingPt2 = pts[0]
   while i < tot:
      pt2 = pts[i]
      if qad_utils.TanDirectionNear(angle, qad_utils.getAngleBy2Pts(boundingPt2, pt2)):
         boundingPt2 = pt2
      i = i + 1

   return [QgsPointXY(boundingPt1), QgsPointXY(boundingPt2)]
