# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione degli archi di ellisse
 
                              -------------------
        begin                : 2019-02-18
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
from .qad_ellipse import QadEllipse, MathTools
from .qad_variables import QadVariables
from .qad_msg import QadMsg


# ===============================================================================
# QadEllipseArc arc of ellipse class
# ===============================================================================
class QadEllipseArc(QadEllipse):
    
   def __init__(self, ellipseArc = None):
      if ellipseArc is not None:
         self.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio, ellipseArc.startAngle, ellipseArc.endAngle, ellipseArc.reversed)
      else:    
         self.center = None
         self.majorAxisFinalPt = None # punto finale dell'asse maggiore (a dx)
         self.axisRatio = 0 # rapporto tra asse minore e asse maggiore
         self.startAngle = None # angolo iniziale rispetto l'asse che va dal centro a majorAxisFinalPt
         self.endAngle = None # angolo finale rispetto l'asse che va dal centro a majorAxisFinalPt
         # if reversed is True the versus of the arc of ellipse is from endAngle to startAngle
         self.reversed = None

   def whatIs(self):
      # obbligatoria
      return "ELLIPSE_ARC"


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return False
   
   
   def set(self, center, majorAxisFinalPt = None, axisRatio = None, startAngle = None, endAngle = None, reversed=False):
      if isinstance(center, QadEllipseArc):
         ellipseArc = center
         return self.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio, ellipseArc.startAngle, ellipseArc.endAngle, ellipseArc.reversed)
      
      if center == majorAxisFinalPt: return None
      self.center = QgsPointXY(center)
      self.majorAxisFinalPt = QgsPointXY(majorAxisFinalPt)
      self.axisRatio = axisRatio
      self.reversed = reversed
      if self.setArc(startAngle, endAngle) == False: return None
      return self


   def setArc(self, startAngle, endAngle):
      # set controllato degli angoli per inizializzare l'arco di ellisse
      _startAngle = qad_utils.normalizeAngle(startAngle)
      _endAngle = qad_utils.normalizeAngle(endAngle)
      if _startAngle == _endAngle: return False # ellisse completa
      self.startAngle = _startAngle
      self.endAngle = _endAngle

   
   def __eq__(self, ellipseArc):
      # obbligatoria
      """self == other"""
      if ellipseArc.whatIs() != "ELLIPSE_ARC": return False
      if self.center != ellipseArc.center or self.majorAxisFinalPt != ellipseArc.majorAxisFinalPt or self.axisRatio != ellipseArc.axisRatio or \
         self.startAngle != ellipseArc.startAngle or self.endAngle != ellipseArc.endAngle:
         return False
      return True

  
   def __ne__(self, ellipseArc):
      """self != other"""
      return not self.__eq__(ellipseArc)


   def equals(self, ellipseArc):
      # uguali geometricamente (NON conta il verso)
      return self.__eq__(ellipseArc)


   def copy(self):
      # obbligatoria
      return QadEllipseArc(self)


   # ===============================================================================
   # length
   # ===============================================================================
   def length(self):
      # obbligatoria
      # temporaneamente approssimo segmentando l'arco...
      pts = self.asPolyline()
      arcLen = 0 
      i = 0
      while i < len(pts) - 1:
         arcLen = arcLen + qad_utils.getDistance(pts[i], pts[i + 1])
         i = i + 1
      return arcLen
      # da fare
      a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
      b = a * self.axisRatio # semiasse minore
      return 0


   # ============================================================================
   # reverse
   # ============================================================================
   def reverse(self):
      # inverto direzione dell'arco di ellisse (punto iniziale-finale)
      self.reversed = not self.reversed
      return self

   # ============================================================================
   # inverseAngles
   # ============================================================================
   def inverseAngles(self):
      # inverto angolo iniziale-finale
      dummy = self.endAngle
      self.endAngle = self.startAngle 
      self.startAngle = dummy
      # per mantenere lo stesso punto iniziale inverto la direzione dei punti iniziale-finale
      self.reverse()


   # ============================================================================
   # getStartPt, setStartPt
   # ============================================================================
   def getStartPt(self, usingReversedFlag = True):
      # obbligatoria
      # usingReversedFlag è usato per sapere il punto iniziale nel caso l'arco abbia una direzione (nella polyline)
      # ritorna il punto iniziale
      if usingReversedFlag:
         param = self.getParamFromAngle(self.endAngle if self.reversed else self.startAngle)
      else:
         param = self.getParamFromAngle(self.startAngle)
      return self.getPointAt(param)
   
   def setStartPt(self, pt):
      # obbligatoria
      return self.setStartAngleByPt(pt)
      
      
   def setStartAngleByPt(self, pt):
      # da usare per modificare un arco di ellisse già definito
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, pt, False)
      if self.reversed:
         if angle == self.startAngle: return False
         self.endAngle = angle
      else:
         if angle == self.endAngle: return False
         self.startAngle = angle      
      return True


   # ============================================================================
   # getEndPt, setEndPt
   # ============================================================================
   def getEndPt(self, usingReversedFlag = True):
      # obbligatoria
      # usingReversedFlag è usato per sapere il punto iniziale nel caso l'arco abbia una direzione (nella polyline)
      # ritorna il punto finale
      if usingReversedFlag:
         param = self.getParamFromAngle(self.startAngle if self.reversed else self.endAngle)
      else:
         param = self.getParamFromAngle(self.endAngle)
      return self.getPointAt(param)
   
   def setEndPt(self, pt):
      # obbligatoria
      return self.setEndAngleByPt(pt)


   def setEndAngleByPt(self, pt):
      # da usare per modificare un arco di ellisse già definito
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, pt, False)
      if self.reversed:
         if angle == self.endAngle: return False
         self.startAngle = angle
      else:
         if angle == self.startAngle: return False
         self.endAngle = angle
         
      return True
   
   
   # ============================================================================
   # isPtOnEllipseArcOnlyByAngle
   # ============================================================================
   def isPtOnEllipseArcOnlyByAngle(self, point):
      # la funzione valuta se un punto è sull'arco di ellisse considerando solo gli angoli iniziale/finale
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, point, False)
      return qad_utils.isAngleBetweenAngles(self.startAngle, self.endAngle, angle)


   # ============================================================================
   # containsPt
   # ============================================================================
   def containsPt(self, point):
      # obbligatoria
      """
      la funzione ritorna true se il punto é sull'arco di ellisse (estremi compresi).
      point è di tipo QgsPointXY.
      """      
      if self.whereIsPt(point) == 0: # -1 interno, 0 sull'ellisse, 1 esterno:
         return self.isPtOnEllipseArcOnlyByAngle(point)
      return False


   # ============================================================================
   # getDistanceFromStart
   # ============================================================================
   def getDistanceFromStart(self, pt):
      # obbligatoria
      """
      la funzione restituisce la distanza di <pt> (che deve essere sull'oggetto o sua estensione)
      dal punto iniziale.
      """
      if qad_utils.ptNear(pt, self.getStartPt()): return 0.0
      dummy = QadEllipseArc(self)
      dummy.setEndPt(pt)
      return dummy.length()


   # ============================================================================
   # getPointFromStart
   # ============================================================================
   def getPointFromStart(self, distance):
      # obbligatoria
      """
      la funzione restituisce un punto (e la direzione della tangente) alla distanza <distance> 
      (che deve essere sull'oggetto) dal punto iniziale.
      """
      # temporaneamente segmento l'arco di ellisse...
      from .qad_line import QadLine
      if distance < 0:
         return None, None
      pts = self.asPolyline()
      d = distance
      i = 0
      while i < len(pts) - 1:
         linearObject = QadLine().set(pts[i], pts[i + 1])
         l = linearObject.length()
         if d > l:
            d = d - l
            i = i + 1
         else:
            return linearObject.getPointFromStart(d)
      return None, None

      # da fare
      
      if distance < 0:
         return None, None
      l = self.length()
      if distance > l:
         return None, None


   # ============================================================================
   # getDistanceFromEnd
   # ============================================================================
   def getDistanceFromEnd(self, pt):
      # obbligatoria
      """
      la funzione restituisce la distanza di <pt> (che deve essere sull'oggetto o sua estensione)
      dal punto finale.
      """
      return self.length() - self.getDistanceFromStart()


   # ===============================================================================
   # getPointFromEnd
   # ===============================================================================
   def getPointFromEnd(self, distance):
      """
      la funzione restituisce un punto (e la direzione della tangente) alla distanza <distance> 
      (che deve essere sull'oggetto) dal punto finale.
      """
      d = self.length() - distance
      return self.getPointFromStart(d)

   
   # ============================================================================
   # lengthen_delta
   # ============================================================================
   def lengthen_delta(self, move_startPt, delta):
      # obbligatoria
      """
      la funzione sposta il punto iniziale (se move_startPt = True) o finale (se move_startPt = False)
      di una distanza delta
      """
      length = self.length()
      ellipse = QadEllipse().set(self.center, self.majorAxisFinalPt, self.axisRatio)
      # lunghezza arco di ellisse + delta non può essere >= alla lunghezza dell'ellisse
      if length + delta >= ellipse.length() or length + delta <= 0:
         return False
      
      dummy = self.copy()

      if move_startPt == True:
         dummy.reverse()
         if dummy.lengthen_delta(False, delta) == False: return False
         self.setStartPt(dummy.getEndPt())
      else:
         if self.reversed:
            dummy.setArc(qad_utils.normalizeAngle(self.endAngle+0.001), self.endAngle)
         else:
            dummy.setArc(self.startAngle, qad_utils.normalizeAngle(self.startAngle-0.001))

         distFromStart = length + delta
         pt, angle = dummy.getPointFromStart(distFromStart)
         if pt is not None:
            self.setEndPt(pt)
      return True
      
      # da fare
      return False


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude l'arco di ellisse.
      """
      ellipseBoundingBox = QadEllipse.getBoundingBox(self)
      # da fare
      return ellipseBoundingBox


   # ============================================================================
   # getQuadrantPoints
   # ============================================================================
   def getQuadrantPoints(self):
      Pts = QadEllipse.getQuadrantPoints(self)
      # annullo i punti fuori dall'arco di ellisse ma restituisco una lista 4 per
      # sapere a cosa corrisponde ciascun punto quadrante
      if self.isPtOnEllipseArcOnlyByAngle(Pts[3]) == False: Pts[3] = None
      if self.isPtOnEllipseArcOnlyByAngle(Pts[2]) == False: Pts[2] = None
      if self.isPtOnEllipseArcOnlyByAngle(Pts[1]) == False: Pts[1] = None
      if self.isPtOnEllipseArcOnlyByAngle(Pts[0]) == False: Pts[0] = None

      return Pts


   # ===============================================================================
   # getMiddleParam
   # ===============================================================================
   def getMiddleParam(self):
      return self.getParamFromAngle(qad_utils.getMiddleAngle(self.startAngle, self.endAngle))


   # ===============================================================================
   # getMiddlePoint
   # ===============================================================================
   def getMiddlePt(self):
      return self.getPointAt(self.getMiddleParam())


   # ============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   # ============================================================================
   # ============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   # ============================================================================
   def getTanDirectionOnStartPt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto iniziale dell'oggetto.
      """
      result = self.getTanDirectionOnPt(self.getStartPt())
      if self.reversed:
         result = result + math.pi
      return result

   def getTanDirectionOnEndPt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto finale dell'oggetto.
      """
      result = self.getTanDirectionOnPt(self.getEndPt()) 
      if self.reversed:
         result = result + math.pi
      return result

   def getTanDirectionOnMiddlePt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto medio dell'oggetto.
      """
      result = self.getTanDirectionOnPt(self.getMiddlePt()) 
      if self.reversed:
         result = result + math.pi
      return result

   
   # ===============================================================================
   # leftOf
   # ===============================================================================
   def leftOf(self, pt):
      # obbligatoria
      """
      la funzione ritorna una numero < 0 se il punto pt é alla sinistra dell'arco di ellisse ptStart -> ptEnd
      """
      whereIs = self.whereIsPt(pt) # ritorna -1 se il punto è interno, 0 se è sull'ellisse, 1 se è esterno
      
      if self.whereIsPt(pt) == 1: # ritorna -1 se il punto è interno, 0 se è sull'ellisse, 1 se è esterno
         # esterno all'arco
         if self.reversed:  # l'arco é in senso inverso
            return -1  # a sinistra
         else:
            return 1  # a destra
      else: 
         # interno all'arco
         if self.reversed:  # l'arco é in senso inverso
            return 1  # a destra
         else:
            return -1  # a sinistra


   # ============================================================================
   # asPolyline
   # ============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      ritorna una lista di punti che definisce la tangente
      """
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve
         
      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      param = self.getParamFromAngle(self.startAngle)
      endParam = self.getParamFromAngle(self.endAngle)
      if param > endParam:
         param = param - (2 * math.pi)
      pt = self.getPointAt(param)
      
      angle = qad_utils.getAngleBy3Pts(self.getStartPt(False), self.center, self.getEndPt(False), False)
      if angle == 0: return None                          
      angleStep = angle / _atLeastNSegment
      
      points = []
      points.append(pt)
      while True:
         param, pt = self.getNextParamPt(param, pt, angleStep, tolerance)
         if param > endParam: break
         points.append(pt)
      
      lastPt = self.getPointAt(endParam)
      
      if points[-1] != lastPt: # se l'ultimo punto non coincide con il punto terminale dell'arco di ellisse
         if qad_utils.ptNear(points[-1], lastPt): # se l'ultimo punto è abbastanza vicino al punto terminale dell'arco di ellisse
            points[-1].set(lastPt.x(), lastPt.y()) # sposto l'ultimo punto e lo faccio coincidere con il punto terminale dell'arco di ellisse
         else:
            points.append(QgsPointXY(lastPt)) # aggiungo l'ultimo punto coincidente al punto terminale dell'arco di ellisse

      if self.reversed: points.reverse()
      return points

   
   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None, forcedStartPt = None):
      """
      la funzione ritorna l'ellisse in forma di lineString.
      Quando l'arco di ellisse fa parte di una polilinea è necessario che il suo punto iniziale coincida con quello finale della parte precedente
      percui il punto iniziale viene forzato.
      """
      pts = self.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
      if pts is None or len(pts) == 0:
          return None
      if forcedStartPt is not None:
         pts[0] = QgsPointXY(forcedStartPt)
      return QgsLineString(pts)


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna l'ellisse in forma di QgsAbstractGeometry.
      """
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CompoundCurve:
         linestring = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         compoundCurve = QgsCompoundCurve()
         compoundCurve.addCurve(linestring)
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         linestring = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(linestring)   
         return multiCurve
         
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
      la funzione ritorna l'ellisse in forma di QgsGeometry.
      """
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment));


   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points, startVertex, atLeastNSegment = None):
      """
      Setta le caratteristiche dell'arco di ellisse incontrato nella lista di punti
      partendo dalla posizione startVertex (0-indexed).
      Ritorna la posizione nella lista del punto finale se é stato trovato un arco di ellisse
      altrimenti None
      N.B. i punti NON devono essere in coordinate geografiche
      """
      # se il punto iniziale e quello finale coincidono non é un arco di ellisse
      if points[startVertex] == points[-1]: return None

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      totPoints = len(points) - startVertex
      nSegment = totPoints - 1
      # perché sia un arco ci vogliono almeno _atLeastNSegment segmenti e almeno 5 punti
      if nSegment < _atLeastNSegment or totPoints < 5:
         return None

      everyNPts = int(max(_atLeastNSegment, 5) / 5)
      
      # sposto i 5 punti di valutazione vicino a 0,0 per migliorare la precisione dei calcoli
      dx = points[startVertex].x()
      dy = points[startVertex].y()
      first5Points = []
      first5Points.append(qad_utils.movePoint(points[startVertex], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts * 2], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts * 3], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[startVertex + everyNPts * 4], -dx, -dy))
      
      # this translation is for avoiding floating point precision issues
      baryC = MathTools.barycenter(first5Points)
      
      pointListBC = []
      for pt in first5Points :
         pointListBC.append((pt[0] - baryC[0], pt[1] - baryC[1]))                         
      # find the center and the axes of by solving the conic equation :
      # ax2 + bxy + cy2 + dx + ey + f = 0
      conic = MathTools.conicEquation(pointListBC)
      [a, b, c, d, e, f] = conic
      # conditions for the existence of an ellipse 
      if MathTools.bareissDeterminant([[a, b/2, d/2], [b/2, c, e/2], [d/2, e/2, f]]) == 0 or a*c - b*b/4 <= 0:
         # Could not find the ellipse passing by these five points. 
         return None
      cX = (b*e - 2*c*d) / (4*a*c - b*b)
      cY = (d*b - 2*a*e) / (4*a*c - b*b)
      center = (cX, cY)        
      res = MathTools.ellipseAxes(conic)
      if res is None: return None
      axisDir1 = res[0]
      axisDir2 = res[1]
      axisLen1 = MathTools.ellipseAxisLen(conic, center, axisDir1)
      if axisLen1 is None: return None
      axisLen2 = MathTools.ellipseAxisLen(conic, center, axisDir2)
      if axisLen2 is None: return None
          
      if axisLen1 > axisLen2:
         majorDir = axisDir1
         majorLen = axisLen1
         minorLen = axisLen2
      else:
         majorDir = axisDir2
         majorLen = axisLen2
         minorLen = axisLen1
      rotAngle = math.atan2(majorDir[1], majorDir[0])
      
      center = QgsPointXY(center[0], center[1])
      majorAxisFinalPt = qad_utils.rotatePoint(QgsPointXY(majorLen + center[0], center[1]), center, rotAngle)
      majorAxisFinalPt.setX(majorAxisFinalPt.x() + baryC[0])
      majorAxisFinalPt.setY(majorAxisFinalPt.y() + baryC[1])
      
      axisRatio = minorLen / majorLen;

      center = QgsPointXY(center[0] + baryC[0], center[1] + baryC[1])
      
      testEllipse = QadEllipse()
      if testEllipse.set(center, majorAxisFinalPt, axisRatio) is None:
         return None
      foci = testEllipse.getFocus()
      if len(foci) == 0: return None
           
      myPoints = []
      # sposto i punti vicino a 0,0 per migliorare la precisione dei calcoli
      i = startVertex
      while i < len(points):
         myPoints.append(qad_utils.movePoint(points[i], -dx, -dy))
         i = i + 1

      # se il punto medio della linea (points[1]) è a sinistra del
      # segmento che unisce i punti iniziale (points[0]) e finale (points[2]) allora il verso è orario
      startClockWise = False if qad_utils.leftOfLine(myPoints[2], myPoints[0], myPoints[1]) < 0 else True
      angle = 0                                  
      
      # uso la distanza TOLERANCE2COINCIDENT / 2 perchè in una polilinea se ci sono 2 archi di ellisse consecutivi
      # si vuole essere sicuri che il punto finale del primo arco di ellisse sia distante dal punto iniziale del
      # secondo arco di ellisse non più di TOLERANCE2COINCIDENT perchè siano considerato 2 punti coincidenti
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT")) / 2
      
      # verifico che i punti siano sull'ellisse e mi fermo al primo punto fuori da essa
      i = 0
      while i < totPoints:        
         # se TOLERANCE2COINCIDENT = 0,001 viene riconosciuto un arco di 1000 m
         # se il punto calcolato non è abbastanza vicino al punto reale
         # altrimenti trovo problemi con le intersezioni con gli oggetti       
         relativeAngle = qad_utils.getAngleBy2Pts(center, myPoints[i]) - testEllipse.getRotation()
         if qad_utils.ptNear(testEllipse.getPointAt(testEllipse.getParamFromAngle(relativeAngle)), \
                             myPoints[i], myTolerance) == False:
            break
                  
         # calcolo il verso dell'arco e l'angolo
         if i < 2:
            clockWise = False if qad_utils.leftOfLine(myPoints[i], myPoints[i + 1], myPoints[i + 2]) < 0 else True
         else:
            clockWise = False if qad_utils.leftOfLine(myPoints[i], myPoints[i - 2], myPoints[i - 1]) < 0 else True
         # il verso deve essere lo stesso di quello originale
         if startClockWise != clockWise:
            break
         
         if i > 0: # salto il primo punto
            angle = angle + qad_utils.getAngleBy3Pts(myPoints[i-1], center, myPoints[i], startClockWise)
            # l'angolo incritto non può essere >= di 360
            if angle >= 2 * math.pi:
               break
         i = i + 1

      # se non sono stati trovati un numero sufficiente di segmenti successivi
      i = i - 1 # ultimo punto valido dell'arco 
      if i < _atLeastNSegment: return None
      
      self.center = center
      self.majorAxisFinalPt = majorAxisFinalPt
      self.axisRatio = axisRatio
      
      if startClockWise: # se è in senso orario
         self.endAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[0], False)
         self.startAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[i], False)
         self.reversed = True
      else:
         self.startAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[0], False)
         self.endAngle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, myPoints[i], False)
         self.reversed = False

      # traslo la geometria per riportarla alla sua posizione originale
      self.move(dx, dy)
      
      return i + startVertex


   # ===============================================================================
   # breakOnPts
   # ===============================================================================
   def breakOnPts(selfs, firstPt, secondPt):
      # obbligatoria
      """
      la funzione spezza la geometria in un punto (se <secondPt> = None) o in due punti 
      come fa il trim. Ritorna una o due geometrie risultanti dall'operazione.
      <firstPt> = primo punto di divisione
      <secondPt> = secondo punto di divisione
      """
      angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, firstPt, False)
      param = self.getParamFromAngle(angle)
      myFirstPt = self.getPointAt(param)

      mySecondPt = None
      if secondPt is not None:
         angle = qad_utils.getAngleBy3Pts(self.majorAxisFinalPt, self.center, secondPt, False)
         param = self.getParamFromAngle(angle)
         mySecondPt = self.getPointAt(param)

      part1 = self.getGeomBetween2Pts(self.getStartPt(), myFirstPt)
      if mySecondPt is None:
         part2 = self.getGeomBetween2Pts(myFirstPt, self.getEndPt())
      else:
         part2 = self.getGeomBetween2Pts(mySecondPt, self.getEndPt())

      return [part1, part2]


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      QadEllipse.mirror(self, mirrorPt, mirrorAngle)
      self.startAngle = (2 * math.pi) - self.startAngle
      self.endAngle = (2 * math.pi) - self.endAngle


   # ===============================================================================
   # offset
   # ===============================================================================
   def offset(self, offsetDist, offsetSide, tolerance2ApproxCurve = None):
      """
      la funzione restituisce l'arco di ellisse facendone l'offset.
      poichè l'offset di un arco di ellisse non è un arco di ellisse, restituisce una lista di punti o None
      secondo una distanza e un lato di offset ("right" o "left" o "internal" o "external")
      """
      side = ""
      if offsetSide == "right":
         if self.reversed: # direzione oraria
            side = "internal" # offset verso l'interno dell'ellisse
         else:
            side = "external" # offset verso l'esterno dell'ellisse
      elif offsetSide == "left":
         if self.reversed: # direzione oraria
            side = "external" # offset verso l'esterno dell'ellisse
         else:
            side = "internal" # offset verso l'interno dell'ellisse
      else:
         side = offsetSide
      
      if side == "internal": # offset verso l'interno dell'ellisse
         dist = -offsetDist
         a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
         b = a * self.axisRatio # semiasse minore
         if a > b:
            if b <= offsetDist: return None
         else:
            if a <= offsetDist: return None
      elif side == "external": # offset verso l'esterno dell'ellisse
         dist = offsetDist

      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve
         
      _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"), 12)
      
      param = self.getParamFromAngle(self.startAngle)
      endParam = self.getParamFromAngle(self.endAngle)
      if param > endParam:
         param = param - (2 * math.pi)
      pt = self.getPointAt(param)
      ptOffset = qad_utils.getPolarPointByPtAngle(pt, self.getNormalAngleToAPointOnEllipse(pt), dist)
      
      angle = qad_utils.getAngleBy3Pts(self.getStartPt(False), self.center, self.getEndPt(False), False)                                 
      angleStep = angle / _atLeastNSegment
      
      points = []
      points.append(ptOffset)
      while True:
         param, ptOffset = self.getNextParamPtForOffset(param, ptOffset, angleStep, tolerance, dist)
         if param > endParam: break
         points.append(ptOffset)
      
      lastPt = self.getPointAt(endParam)
      lastPtOffset = qad_utils.getPolarPointByPtAngle(lastPt, self.getNormalAngleToAPointOnEllipse(lastPt), dist)      
      if qad_utils.ptNear(points[-1], lastPtOffset) == False: points.append(lastPtOffset) # ultimo elemento della lista

      if self.reversed: points.reverse()
      return points


   # ============================================================================
   # fromFoci
   # ============================================================================
   def fromFoci(self, f1, f2, ptOnEllipse, startAngle, endAngle):
      """
      setta le caratteristiche dell'ellisse attraverso:
      i due fuochi
      un punto sull'ellisse
             /-ptOnEllipse-\
            /               \
            |   f1     f2   |
            \               /
             \-------------/
      """
      if QadEllipse.fromFoci(self, f1, f2, ptOnEllipse) == False: return False
      self.setArc(startAngle, endAngle)
      return True
   

   # ============================================================================
   # fromExtent
   # ============================================================================
   def fromExtent(self, pt1, pt2, rot, startAngle, endAngle):
      """
      setta le caratteristiche dell'ellisse attraverso:
      i due punti di estensione (angoli opposti) del rettangolo che racchiude l'ellisse
      rotazione del rettangolo di estensione
             /-------------\  pt2
            /               \
            |               |
            \               /
        pt1  \-------------/
      """
      if QadEllipse.fromExtent(self, pt1, pt2, rot) == False: return False
      self.setArc(startAngle, endAngle)
      return True
      

   # ============================================================================
   # fromCenterAxis1FinalPtAxis2FinalPt
   # ============================================================================
   def fromCenterAxis1FinalPtAxis2FinalPt(self, ptCenter, axis1FinalPt, axis2FinalPt, startAngle, endAngle):
      """
      setta le caratteristiche dell'ellisse attraverso:
      il punto centrale
      il punto finale dell'asse
      il punto finale dell'altro asse
             /--axis2FinalPt--\
            /                  \
            |     ptCenter axis1FinalPt
            \                  /
             \----------------/
      """
      if QadEllipse.fromCenterAxis1FinalPtAxis2FinalPt(self, ptCenter, axis1FinalPt, axis2FinalPt) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromCenterAxis1FinalPtDistAxis2
   # ============================================================================
   def fromCenterAxis1FinalPtDistAxis2(self, ptCenter, axis1FinalPt, distAxis2, startAngle, endAngle):
      """
      setta le caratteristiche dell'ellisse attraverso:
      il punto centrale
      il punto finale dell'asse
      distanza dal centro al punto finale dell'altro asse
             /-------|--------\
            /     distAxis2    \
            |     ptCenter axis1FinalPt
            \                  /
             \----------------/
      """
      if QadEllipse.fromCenterAxis1FinalPtDistAxis2(self, ptCenter, axis1FinalPt, distAxis2) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromCenterAxis1FinalPtAxis2FinalPt
   # ============================================================================
   def fromCenterAxis1FinalPtAxis2FinalPt(self, axis1Finalpt1, axis1Finalpt2, axis2FinalPt, startAngle, endAngle):
      """
      setta le caratteristiche dell'ellisse attraverso:
      i punti finali dell'asse
      il punto finale dell'altro asse
             /--axis2FinalPt--\
            /                  \
      axis1Finalpt2       axis1Finalpt1
            \                  /
             \----------------/
      """
      if QadEllipse.fromCenterAxis1FinalPtAxis2FinalPt(self, axis1Finalpt1, axis1Finalpt2, axis2FinalPt) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromAxis1FinalPtsAxis2Len
   # ============================================================================
   def fromAxis1FinalPtsAxis2Len(self, axis1FinalPt1, axis1FinalPt2, distAxis2, startAngle, endAngle):
      """
      setta le caratteristiche dell'ellisse attraverso:
      i punti finali dell'asse
      distanza dal centro al punto finale dell'altro asse
             /------|-------\
            /   distAxis2    \
         axis1pt2   |    axis1pt1
            \                /
             \--------------/
      """
      if QadEllipse.fromAxis1FinalPtsAxis2Len(self, axis1FinalPt1, axis1FinalPt2, distAxis2) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ============================================================================
   # fromAxis1FinalPtsArea
   # ============================================================================
   def fromAxis1FinalPtsArea(self, axis1FinalPt1, axis1FinalPt2, area, startAngle, endAngle):
      """
      setta le caratteristiche dell'ellisse attraverso:
      i punti finali dell'asse
      area dell'ellisse
             /--------------\
            /                \
         axis1pt2        axis1pt1
            \                /
             \--------------/
      """
      if QadEllipse.fromAxis1FinalPtsArea(self, axis1FinalPt1, axis1FinalPt2, area) == False: return False
      self.setArc(startAngle, endAngle)
      return True


   # ===============================================================================
   # getGeomBetween2Pts
   # ===============================================================================
   def getGeomBetween2Pts(self, startPt, endPt):
      """
      Ritorna una sotto geometria che parte dal punto startPt e finisce al punto endPt seguendo il tracciato della geometria.
      """
      if qad_utils.ptNear(startPt, endPt): return None
      if self.containsPt(startPt) == False: return None
      if self.containsPt(endPt) == False: return None
      
      result = self.copy()
      d1 = self.getDistanceFromStart(startPt)
      if d1 < self.getDistanceFromStart(endPt):
         result.setStartPt(startPt)
         result.setEndPt(endPt)
      else:
         result.setStartPt(endPt)
         result.setEndPt(startPt)
         result.reversed = True
         
      return result
