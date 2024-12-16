# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione dei cerchi
 
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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *

import math
import sys

from . import qad_utils
from .qad_variables import QadVariables
from .qad_msg import QadMsg


# ===============================================================================
# QadCircle circle class
# ===============================================================================
class QadCircle():
    
   def __init__(self, circle = None):
      if circle is not None:
         self.set(circle.center, circle.radius)
      else:    
         self.center = None
         self.radius = None

   def whatIs(self):
      # obbligatoria
      return "CIRCLE"

   
   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return True
      

   def set(self, center, radius = None):
      if isinstance(center, QadCircle):
         circle = center
         return self.set(circle.center, circle.radius)
      
      if radius <= 0: return None
      self.center = QgsPointXY(center)
      self.radius = radius
      return self

   def transform(self, coordTransform):
      """Transform this geometry as described by CoordinateTranasform ct."""
      self.center = coordTransform.transform(self.center)      

   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """Transform this geometry as described by CRS."""
      if (sourceCRS is not None) and (destCRS is not None) and sourceCRS != destCRS:       
         coordTransform = QgsCoordinateTransform(sourceCRS, destCR, QgsProject.instance()) # trasformo le coord
         self.center =  coordTransform.transform(self.center)
   
   def __eq__(self, circle):
      # obbligatoria
      """self == other"""
      if circle.whatIs() != "CIRCLE": return False
      if self.center != circle.center or self.radius != circle.radius:
         return False
      else:
         return True    
  
   def __ne__(self, circle):
      """self != other"""
      return not self.__eq__(circle)


   def equals(self, circle):
      # uguali geometricamente (NON conta il verso)
      return self.__eq__(circle)


   def copy(self):
      # obbligatoria
      return QadCircle(self)

   
   def length(self):
      return 2 * math.pi * self.radius


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude il cerchio.
      """
      return QgsRectangle(self.center.x() - self.radius,
                          self.center.y() - self.radius,
                          self.center.x() + self.radius,
                          self.center.y() + self.radius)


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, point):
      # obbligatoria
      """
      la funzione ritorna true se il punto é sulla circonferenze del cerchio.
      """
      # whereIsPt ritorna -1 se il punto è interno, 0 se è sulla circonferenza, 1 se è esterno
      return True if self.whereIsPt(point) == 0 else 0


   # ===============================================================================
   # lengthBetween2Points
   # ===============================================================================
   def lengthBetween2Points(self, pt1, pt2, leftOfPt1):
      """
      Calcola la distanza tra 2 punti sulla circonferenza. L'arco considerato può essere
      quello a sinistra o a destra di <pt1> (vedi <leftOfPt1>)
      se <leftOfPt1> é boolean allora se = True viene considerato l'arco a sin di pt1
      se <leftOfPt1> é float allora significa che si tratta della direzione della tangente su pt1
                     e se la direzione è a sin viene considerato l'arco a sin di pt1
      """
      if qad_utils.ptNear(pt1, pt2): # se i punti sono così vicini da essere considerati uguali
         return 0
      
      if type(leftOfPt1) == float: # direzione della tangente su pt1 
         startAngle = qad_utils.getAngleBy2Pts(self.center, pt1)         
         if qad_utils.doubleNear(qad_utils.normalizeAngle(startAngle + math.pi / 2), 
                                 qad_utils.normalizeAngle(leftOfPt1)):
            _leftOfPt1 = True
         else:
            _leftOfPt1 = False
      else: # booolean
         _leftOfPt1 = leftOfPt1
      
      if _leftOfPt1: # arco a sinistra di pt1
         startAngle = qad_utils.getAngleBy2Pts(self.center, pt1)         
         endAngle = qad_utils.getAngleBy2Pts(self.center, pt2)
      else: # arco a destra di pt1
         startAngle = qad_utils.getAngleBy2Pts(self.center, pt2)
         endAngle = qad_utils.getAngleBy2Pts(self.center, pt1)         

      if startAngle < endAngle:
         totalAngle = endAngle - startAngle
      else:
         totalAngle =  (2 * math.pi - startAngle) + endAngle
      
      return self.radius * totalAngle


   def area(self):
      return math.pi * self.radius * self.radius


   def isPtOnCircle(self, point):
      return True if self.whereIsPt(point) == 0 else False # -1 interno, 0 sulla circonferenza, 1 esterno


   # ============================================================================
   # whereIsPt
   # ============================================================================
   def whereIsPt(self, point):
      # ritorna -1 se il punto è interno, 0 se è sulla circonferenza, 1 se è esterno
      dist = self.center.distance(point)
      if qad_utils.doubleNear(dist, self.radius): return 0
      elif dist < self.radius: return -1 # interno
      else: return 1 # esterno


   def getQuadrantPoints(self):
      # ritorna i punti quadranti: pt in alto, pt in basso, a destra, a sinistra del centro
      pt1 = QgsPointXY(self.center.x(), self.center.y() + self.radius)
      pt2 = QgsPointXY(self.center.x(), self.center.y()- self.radius)
      pt3 = QgsPointXY(self.center.x() + self.radius, self.center.y())
      pt4 = QgsPointXY(self.center.x() - self.radius, self.center.y())
      return [pt1, pt2, pt3, pt4]




   # ============================================================================
   # asPolyline
   # ============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      ritorna una lista di punti che definisce il cerchio
      """
      
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      # Calcolo la lunghezza del segmento con pitagora
      dummy      = self.radius - tolerance
      if dummy <= 0: # se la tolleranza è troppo bassa rispetto al raggio
         SegmentLen = self.radius
      else:
         dummy      = (self.radius * self.radius) - (dummy * dummy)
         SegmentLen = math.sqrt(dummy) # radice quadrata
         SegmentLen = SegmentLen * 2

      if SegmentLen == 0: # se la tolleranza è troppo bassa la lunghezza del segmento diventa zero  
         return None

      # calcolo quanti segmenti ci vogliono (non meno di _atLeastNSegment)
      SegmentTot = math.ceil(self.length() / SegmentLen)
      if SegmentTot < _atLeastNSegment:
         SegmentTot = _atLeastNSegment
      
      points = []
      # primo punto
      firsPt = qad_utils.getPolarPointByPtAngle(self.center, 0, self.radius)
      points.append(firsPt)

      i = 1
      angle = 0
      offsetAngle = 2 * math.pi / SegmentTot
      while i < SegmentTot:
         angle = angle + offsetAngle
         pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
         points.append(pt)         
         i = i + 1

      # ultimo punto (come il primo)
      points.append(firsPt)
      return points


   # ===============================================================================
   # asCircularString
   # ===============================================================================
   def asCircularString(self):
      """
      la funzione ritorna il cerchio in forma di circularString.
      """
      circle = QgsCircle(QgsPoint(self.center), self.radius)
      return circle.toCircularString()


   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna il cerchio in forma di lineString.
      """
      pts = self.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
      if pts is None or len(pts) == 0:
          return None
      return QgsLineString(pts)


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna il cerchio in forma di QgsAbstractGeometry.
      """
      flatType = QgsWkbTypes.flatType(wkbType)
      
      if flatType == QgsWkbTypes.CompoundCurve:
         circularString = self.asCircularString()
         compoundCurve = QgsCompoundCurve()
         compoundCurve.addCurve(circularString)   
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         circularString = self.asCircularString()
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(circularString)   
         return multiCurve
         
      elif flatType == QgsWkbTypes.CurvePolygon:
         circularString = self.asCircularString()
         curvePolygon = QgsCurvePolygon()
         curvePolygon.setExteriorRing(circularString)
         return curvePolygon

      elif flatType == QgsWkbTypes.MultiSurface: # Geometry that is combined from several CurvePolygon is called MultiSurface
         curvePolygon = self.asAbstractGeom(QgsWkbTypes.CurvePolygon, tolerance2ApproxCurve, atLeastNSegment)
         multiSurface = QgsMultiSurface()
         multiSurface.addGeometry(curvePolygon)
         return multiSurface

      elif flatType == QgsWkbTypes.Polygon:
         linestring = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         polygon = QgsPolygon()
         polygon.setExteriorRing(linestring)
         return polygon

      elif flatType == QgsWkbTypes.MultiPolygon:
         polygon = self.asAbstractGeom(QgsWkbTypes.Polygon, tolerance2ApproxCurve, atLeastNSegment)
         multiPolygon = QgsMultiPolygon()
         multiPolygon.addGeometry(polygon)
         return multiPolygon
            
      elif flatType == QgsWkbTypes.MultiLineString:
         lineString = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         multiLineString = QgsMultiLineString()
         multiLineString.addGeometry(lineString) 
         return multiLineString
            
      return self.asLineString(tolerance2ApproxCurve, atLeastNSegment)

   
   # ===============================================================================
   # asGeom
   # ===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna il cerchio in forma di QgsGeometry.
      """
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))
      

   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points, atLeastNSegment = None):
      """
      setta le caratteristiche del cerchio incontrato nella lista di punti
      ritorna True se é stato trovato un cerchio altrimenti False.
      N.B. in punti NON devono essere in coordinate geografiche
      """
      # se il punto iniziale e quello finale non coincidono non é un cerchio
      if points[0] != points[-1]:
         return False

      totPoints = len(points)
      
      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      # perché sia un cerchio ci vogliono almeno _atLeastNSegment segmenti
      if (totPoints - 1) < _atLeastNSegment or _atLeastNSegment < 2:
         return False

      # sposto i primi 3 punti vicino a 0,0 per migliorare la precisione dei calcoli
      dx = points[0].x()
      dy = points[0].y()
      myPoints = []
      myPoints.append(qad_utils.movePoint(points[0], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[1], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[2], -dx, -dy))

#       InfinityLinePerpOnMiddle1 = qad_utils.getInfinityLinePerpOnMiddle(myPoints[0], myPoints[1])
#       if InfinityLinePerpOnMiddle1 is None: return False
#       InfinityLinePerpOnMiddle2 = qad_utils.getInfinityLinePerpOnMiddle(myPoints[1], myPoints[2])
#       if InfinityLinePerpOnMiddle2 is None: return False
#       
#       # calcolo il presunto centro con 2 segmenti
#       center = qad_utils.getIntersectionPointOn2InfinityLines(InfinityLinePerpOnMiddle1[0], \
#                                                               InfinityLinePerpOnMiddle1[1], \
#                                                               InfinityLinePerpOnMiddle2[0], \
#                                                               InfinityLinePerpOnMiddle2[1])
#       if center is None: return False # linee parallele

      # se uso QgsCircle ottengo una miglior precisione
      circle = QgsCircle.from3Points(QgsPoint(myPoints[0]), QgsPoint(myPoints[1]), QgsPoint(myPoints[2]))
      if circle.isEmpty() == True:
         return False
      
      center = circle.center()
      center = QgsPointXY(center.x(), center.y())
      radius = center.distance(myPoints[0]) # calcolo il presunto raggio
     
      # se il punto finale dell'arco è a sinistra del
      # segmento che unisce i punti iniziale e intermedio allora il verso è antiorario
      startClockWise = False if qad_utils.leftOfLine(myPoints[2], myPoints[0], myPoints[1]) < 0 else True
      angle = qad_utils.getAngleBy3Pts(myPoints[0], center, myPoints[2], startClockWise)                                    

      i = 3
      while i < totPoints:
         # sposto i punti vicino a 0,0 per migliorare la precisione dei calcoli
         myPoints.append(qad_utils.movePoint(points[i], -dx, -dy))
         
         # se TOLERANCE2COINCIDENT = 0,001 viene riconosciuto un cerchio di 1000 m
         # se il punto calcolato non è abbastanza vicino al punto reale
         # altrimenti trovo problemi con le intersezioni con gli oggetti
         if qad_utils.ptNear(qad_utils.getPolarPointByPtAngle(center, qad_utils.getAngleBy2Pts(center, myPoints[i]), radius), \
                             myPoints[i]) == False:
            return False
                  
         # calcolo il verso dell'arco e l'angolo                 
         clockWise = True if qad_utils.leftOfLine(myPoints[i], myPoints[i - 1], myPoints[i - 2]) < 0 else False
         # il verso deve essere lo stesso di quello originale
         if startClockWise != clockWise: return False
         angle = angle + qad_utils.getAngleBy3Pts(myPoints[i-1], center, myPoints[i], startClockWise)
         # l'angolo incritto non può essere > di 360
         if qad_utils.doubleSmallerOrEquals(angle, 2 * math.pi):
            i = i + 1
         else:
            return False

      self.center = center
      self.radius = radius
      # traslo la geometria per riportarla alla sua posizione originale
      self.move(dx, dy)
      
      return True


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      self.center = qad_utils.movePoint(self.center, offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      self.center = qad_utils.rotatePoint(self.center, basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      self.center = qad_utils.scalePoint(self.center, basePt, scale)
      self.radius = self.radius * scale
   

   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      self.center = qad_utils.mirrorPoint(self.center, mirrorPt, mirrorAngle)


   # ===============================================================================
   # offset
   # ===============================================================================
   def offset(self, offsetDist, offsetSide):
      """
      la funzione modifica il cerchio facendone l'offset
      secondo una distanza e un lato di offset ("internal" o "external")
      """
      if offsetSide == "internal":
         # offset verso l'interno del cerchio
         radius = self.radius - offsetDist
         if radius <= 0:
            return False
      else:
         # offset verso l'esterno del cerchio
         radius = self.radius + offsetDist
   
      self.radius = radius
          
      return True


   # ============================================================================
   # fromCenterPtArea
   # ============================================================================
   def fromCenterArea(self, centerPt, area):
      """
      setta le caratteristiche del cerchio attraverso:
      il punto centrale
      area
      """
      if centerPt is None or area <= 0:
         return None
      self.center = centerPt
      self.radius = math.sqrt(area / math.pi)
      return self

   
   # ============================================================================
   # fromDiamEnds
   # ============================================================================
   def fromDiamEnds(self, startPt, endPt):
      """
      setta le caratteristiche del cerchio attraverso i punti estremità del diametro:
      punto iniziale
      punto finale
      """
      self.radius = qad_utils.getDistance(startPt, endPt) / 2
      if self.radius == 0:
         return None
      self.center = qad_utils.getMiddlePoint(startPt, endPt)
      return self
