# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione degli archi
 
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


from . import qad_utils
from .qad_circle import QadCircle
from .qad_variables import QadVariables
from .qad_msg import QadMsg


# ===============================================================================
# QadArc arc class
# ===============================================================================
class QadArc(QadCircle):
    
   def __init__(self, arc=None):
      if arc is not None:
         if arc.radius <= 0: return None
         self.set(arc.center, arc.radius, arc.startAngle, arc.endAngle, arc.reversed)
      else:
         self.center = None
         self.radius = None
         self.startAngle = None # come l'arco per il cerchio
         self.endAngle = None
         # if reversed is True the versus of the arc is from endAngle to startAngle
         self.reversed = False


   def whatIs(self):
      # obbligatoria
      return "ARC"
   
   
   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      return False
   
   
   def set(self, center, radius=None, startAngle=None, endAngle=None, reversed=False):
      if isinstance(center, QadArc):
         arc = center
         return self.set(arc.center, arc.radius, arc.startAngle, arc.endAngle, arc.reversed)
      
      if radius <= 0: return None
      self.center = QgsPointXY(center)
      self.radius = radius
      self.reversed = reversed
      if self.setArc(startAngle, endAngle) == False: return None
      return self

      
   def setArc(self, startAngle, endAngle):
      # set controllato degli angoli per inizializzare l'arco
      _startAngle = qad_utils.normalizeAngle(startAngle)
      _endAngle = qad_utils.normalizeAngle(endAngle)
      if _startAngle == _endAngle: return False # cerchio completo
      self.startAngle = _startAngle
      self.endAngle = _endAngle


   def __eq__(self, arc):
      # obbligatoria
      """self == other"""
      if arc.whatIs() != "ARC": return False
      if self.center != arc.center or self.radius != arc.radius or \
         self.startAngle != arc.startAngle or self.endAngle != arc.endAngle or self.reversed != arc.reversed:
         return False
      else:
         return True    

  
   def __ne__(self, arc):
      """self != other"""
      return not self.__eq__(arc)


   def equals(self, arc):
      # uguali geometricamente (NON conta il verso)
      return self.__eq__(arc)

   
   def copy(self):
      # obbligatoria
      return QadArc(self)


   def totalAngle(self):
      if self.startAngle < self.endAngle:
         return self.endAngle - self.startAngle
      else:
         return (2 * math.pi - self.startAngle) + self.endAngle


   # ===============================================================================
   # length
   # ===============================================================================
   def length(self):
      # obbligatoria
      return self.radius * self.totalAngle()


   # ============================================================================
   # reverse
   # ============================================================================
   def reverse(self):
      # inverto direzione dell'arco (punto iniziale-finale)
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
      if usingReversedFlag:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.endAngle if self.reversed else self.startAngle,
                                                 self.radius)
      else:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.startAngle,
                                                 self.radius)
      
   def setStartPt(self, pt):
      # obbligatoria
      if self.reversed:
         return self.setEndAngleByPt(pt)
      else:
         return self.setStartAngleByPt(pt)
      
      
   def setStartAngleByPt(self, pt):
      # da usare per modificare un arco già definito
      angle = qad_utils.getAngleBy2Pts(self.center, pt)
      if angle == self.endAngle: return False
      self.startAngle = angle
      return True


   # ============================================================================
   # getEndPt, setEndPt
   # ============================================================================
   def getEndPt(self, usingReversedFlag = True):
      # obbligatoria
      # usingReversedFlag è usato per sapere il punto iniziale nel caso l'arco abbia una direzione (nella polyline)
      if usingReversedFlag:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.startAngle if self.reversed else self.endAngle,
                                                 self.radius)
      else:
         return qad_utils.getPolarPointByPtAngle(self.center,
                                                 self.endAngle,
                                                 self.radius)
      
   def setEndPt(self, pt):
      # obbligatoria
      if self.reversed:
         return self.setStartAngleByPt(pt)
      else:
         return self.setEndAngleByPt(pt)


   def setEndAngleByPt(self, pt):
      # da usare per modificare un arco già definito
      angle = qad_utils.getAngleBy2Pts(self.center, pt)
      if angle == self.startAngle:
         return False
      self.endAngle = angle
      return True


   # ============================================================================
   # isPtOnArcOnlyByAngle
   # ============================================================================
   def isPtOnArcOnlyByAngle(self, point):
      # la funzione valuta se un punto è sull'arco considerando solo gli angoli iniziale/finale
      return self.isAngleBetweenAngles(qad_utils.getAngleBy2Pts(self.center, point))


   # ============================================================================
   # isAngleBetweenAngles
   # ============================================================================
   def isAngleBetweenAngles(self, angle):
      # la funzione valuta se un angolo è compreso tra gli angoli iniziale/finale
      return qad_utils.isAngleBetweenAngles(self.startAngle, self.endAngle, angle)
   

   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude l'arco.
      """
      circleBoundingBox = QadCircle.getBoundingBox(self)
      
      p1 = qad_utils.getPolarPointByPtAngle(self.center, self.startAngle, self.radius)
      p2 = qad_utils.getPolarPointByPtAngle(self.center, self.endAngle, self.radius)
      
      if p1.x() > p2.x():
         xMax = p1.x()
         xMin = p2.x()
      else:
         xMax = p2.x()
         xMin = p1.x()
         
      if p1.y() > p2.y():
         yMax = p1.y()
         yMin = p2.y()
      else:
         yMax = p2.y()
         yMin = p1.y()

      end = self.endAngle
      if end < self.startAngle: end = end + 2 * math.pi
      
      if end > math.pi / 2:
         if self.startAngle < math.pi / 2: yMax = circleBoundingBox.yMaximum()
         if end > math.pi:
            if self.startAngle < math.pi: xMin = circleBoundingBox.xMinimum()
            if end > math.pi * 3 / 4:
               if self.startAngle < math.pi * 3 / 4: yMin = circleBoundingBox.yMinimum()
               if end > math.pi * 2:
                  xMax = circleBoundingBox.xMaximum()
                  if end > math.pi * 2 + math.pi / 2:
                     yMax = circleBoundingBox.yMaximum()
                     if end > math.pi * 2 + math.pi:
                        xMin = circleBoundingBox.xMinimum()
                        if end > math.pi * 2 + math.pi * 3 / 4:
                           yMin = circleBoundingBox.yMinimum()
      
      return QgsRectangle(xMin, yMin, xMax, yMax)


   # ===============================================================================
   # containsPt
   # ===============================================================================
   def containsPt(self, point):
      # obbligatoria
      """
      la funzione ritorna true se il punto é sull'arco (estremi compresi).
      point è di tipo QgsPointXY.
      """      
      dist = qad_utils.getDistance(self.center, point)
      if qad_utils.doubleNear(self.radius, dist):
         return self.isPtOnArcOnlyByAngle(point)
      else:
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
      dummy = QadArc(self)
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
      if distance < 0:
         return None, None
      l = self.length()
      if distance > l:
         return None, None

      # (2*pi) : (2*pi*r) = angle : delta            
      angle = distance / self.radius
      
      if self.reversed:
         angle = self.endAngle - angle
      else:
         angle = self.startAngle + angle
      
      pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
      return pt, self.getTanDirectionOnPt(pt)


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
      circle = QadCircle().set(self.center, self.radius)
      # lunghezza arco + delta non può essere >= alla circonferenza del cerchio
      if length + delta >= circle.length():
         return False
      # (2*pi) : (2*pi*r) = angle : delta            
      angle = delta / self.radius
      
      if move_startPt == True:
         if self.reversed:
            self.endAngle = self.endAngle + angle
         else:
            self.startAngle = self.startAngle - angle
      else:
         if self.reversed:
            self.startAngle = self.startAngle - angle
         else:
            self.endAngle = self.endAngle + angle
      return True


   # ============================================================================
   # lengthen_deltaAngle
   # ============================================================================
   def lengthen_deltaAngle(self, move_startPt, delta):
      # obbligatoria
      """
      la funzione sposta il punto iniziale (se move_startPt = True) o finale (se move_startPt = False)
      dell'arco di un certo numero di gradi delta
      """
      totalAngle = self.totalAngle()
      # angolo dell'arco + delta non può essere >= 2 * pi
      if totalAngle + delta >= 2 * math.pi:
         return False
      # angolo dell'arco + delta non può essere <= 0
      if totalAngle + delta <= 0:
         return False
      
      if move_startPt == True:
         if self.reversed:
            self.endAngle = self.endAngle + delta
         else:
            self.startAngle = self.startAngle - delta
      else:
         if self.reversed:
            self.startAngle = self.startAngle - delta
         else:
            self.endAngle = self.endAngle + delta
      return True


   # ============================================================================
   # getQuadrantPoints
   # ============================================================================
   def getQuadrantPoints(self):
      result = []      

      angle = 0
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x() + self.radius, self.center.y()))
         
      angle = math.pi / 2
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x(), self.center.y() + self.radius))
         
      angle = math.pi
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x() - self.radius, self.center.y()))

      angle = math.pi * 3 / 2
      if self.isAngleBetweenAngles(angle) == True:
         result.append(QgsPointXY(self.center.x(), self.center.y() - self.radius))

      return result


   # ===============================================================================
   # getMiddlePoint
   # ===============================================================================
   def getMiddlePt(self):
      halfAngle = self.totalAngle() / 2
      return qad_utils.getPolarPointByPtAngle(self.center,
                                              self.startAngle + halfAngle,
                                              self.radius)


   # ============================================================================
   # getTanDirectionOnPt
   # ============================================================================
   def getTanDirectionOnPt(self, pt):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto dell'oggetto.
      """
      angle = qad_utils.getAngleBy2Pts(self.center, pt)
      if self.reversed:  # la direzione dell'arco è invertita
         return qad_utils.normalizeAngle(angle - math.pi / 2)
      else: 
         return qad_utils.normalizeAngle(angle + math.pi / 2)

   
   # ============================================================================
   # getTanDirectionOnStartPt, getTanDirectionOnEndPt, getTanDirectionOnMiddlePt
   # ============================================================================
   def getTanDirectionOnStartPt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto iniziale dell'oggetto.
      """
      return self.getTanDirectionOnPt(self.getStartPt())

   def getTanDirectionOnEndPt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto finale dell'oggetto.
      """
      return self.getTanDirectionOnPt(self.getEndPt()) 


   def getTanDirectionOnMiddlePt(self):
      # obbligatoria
      """
      la funzione ritorna la direzione della tangente al punto medio dell'oggetto.
      """
      return self.getTanDirectionOnPt(self.getMiddlePt()) 


   # ===============================================================================
   # leftOf
   # ===============================================================================
   def leftOf(self, pt):
      # obbligatoria
      """
      la funzione ritorna una numero < 0 se il punto pt é alla sinistra dell'arco ptStart -> ptEnd
      """
      if qad_utils.getDistance(self.center, pt) - self.radius > 0:
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
   def asPolyline(self, tolerance2ApproxCurve=None, atLeastNSegment=None):
      # obbligatoria
      """
      ritorna una lista di punti che definisce l'arco
      """
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve
      
      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      # Calcolo la lunghezza del segmento con pitagora
      dummy = self.radius - tolerance
      if dummy <= 0:  # se la tolleranza é troppo bassa rispetto al raggio
         SegmentLen = self.radius
      else:
         dummy = (self.radius * self.radius) - (dummy * dummy)
         SegmentLen = math.sqrt(dummy)  # radice quadrata
         SegmentLen = SegmentLen * 2
      
      if SegmentLen == 0:  # se la tolleranza é troppo bassa la lunghezza del segmento diventa zero  
         return None
         
      # calcolo quanti segmenti ci vogliono (non meno di _atLeastNSegment)
      SegmentTot = math.ceil(self.length() / SegmentLen)
      if SegmentTot < _atLeastNSegment:
         SegmentTot = _atLeastNSegment

      if SegmentTot > 99999: # metto un limite al numero di segmenti
         SegmentTot = _atLeastNSegment

      points = []
      if self.reversed:  # la direzione dell'arco è invertita
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.endAngle, self.radius)
         points.append(pt)
   
         i = 1
         angle = self.endAngle
         offsetAngle = self.totalAngle() / SegmentTot
         while i < SegmentTot:
            angle = angle - offsetAngle
            pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
            points.append(pt)         
            i = i + 1
   
         # ultimo punto
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.startAngle, self.radius)
      else:
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.startAngle, self.radius)
         points.append(pt)
   
         i = 1
         angle = self.startAngle
         offsetAngle = self.totalAngle() / SegmentTot
         while i < SegmentTot:
            angle = angle + offsetAngle
            pt = qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius)
            points.append(pt)         
            i = i + 1
   
         # ultimo punto
         pt = qad_utils.getPolarPointByPtAngle(self.center, self.endAngle, self.radius)
      points.append(pt)
      
      return points


   # ===============================================================================
   # asCircularString
   # ===============================================================================
   def asCircularString(self, forcedStartPt = None):
      """
      la funzione ritorna l'arco in forma di circularString.
      Quando l'arco fa parte di una polilinea è necessario che il suo punto iniziale coincida con quello finale della parte precedente
      percui il punto iniziale viene forzato.
      """
      if forcedStartPt is None:
         return QgsCircularString(QgsPoint(self.getStartPt()), QgsPoint(self.getMiddlePt()), QgsPoint(self.getEndPt()))
      else:
         return QgsCircularString(QgsPoint(forcedStartPt), QgsPoint(self.getMiddlePt()), QgsPoint(self.getEndPt()))


   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna l'arco in forma di lineString.
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
      la funzione ritorna l'arco in forma di QgsAbstractGeometry.
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
      la funzione ritorna l'arco in forma di QgsGeometry.
      """
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment));

   
   # ============================================================================
   # fromStartSecondEndPts
   # ============================================================================
   def fromStartSecondEndPts(self, startPt, secondPt, endPt):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      secondo punto (intermedio)
      punto finale
      """
      points = [startPt, secondPt, endPt]
      # lista di punti, parte dal punto 0, almeno 2 segmenti
      if self.fromPolyline(points, 0, 2) == None: return False
      return True


   # ============================================================================
   # fromStartCenterEndPts
   # ============================================================================
   def fromStartCenterEndPts(self, startPt, centerPt, endPt):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      centro
      punto finale
      """
      if startPt == centerPt or startPt == endPt or endPt == centerPt:
         return False
      
      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(centerPt, endPt)
      self.reversed = False
      return True
   

   # ============================================================================
   # fromStartCenterPtsAngle
   # ============================================================================
   def fromStartCenterPtsAngle(self, startPt, centerPt, angle):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      centro
      angolo inscritto
      """
      if startPt == centerPt or angle == 0:
         return False
      
      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)      
      self.endAngle = self.startAngle + angle
      if self.endAngle > math.pi * 2:
         self.endAngle = self.endAngle % (math.pi * 2)  # modulo
      self.reversed = False
      return True
   

   # ============================================================================
   # fromStartCenterPtsChord
   # ============================================================================
   def fromStartCenterPtsChord(self, startPt, centerPt, chord):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      centro
      lunghezza dela corda tra punto iniziale e finale
      """
      if startPt == centerPt or chord == 0:
         return False

      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      if chord > 2 * self.radius:
         return False
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)
      # Teorema della corda
      angle = 2 * math.asin(chord / (2 * self.radius))
      self.endAngle = self.startAngle + angle
      self.reversed = False
      return True
   

   # ============================================================================
   # fromStartCenterPtsLength
   # ============================================================================
   def fromStartCenterPtsLength(self, startPt, centerPt, length):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      centro
      lunghezza dela corda tra punto iniziale e finale
      """
      if startPt == centerPt or chord == 0:
         return False

      self.center = centerPt
      self.radius = qad_utils.getDistance(centerPt, startPt)
      circumference = 2 * math.pi * self.radius
      if length >= circumference:
         return False
      self.startAngle = qad_utils.getAngleBy2Pts(centerPt, startPt)
      
      # circumference : math.pi * 2 = length : angle
      angle = (math.pi * 2) * length / circumference
      self.endAngle = self.startAngle + angle
      self.reversed = False
      return True


   # ============================================================================
   # fromStartEndPtsAngle
   # ============================================================================
   def fromStartEndPtsAngle(self, startPt, endPt, angle):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      punto finale
      angolo inscritto
      """
      if startPt == endPt or angle == 0:
         return False

      chord = qad_utils.getDistance(startPt, endPt)
      half_chord = chord / 2   
      # Teorema della corda
      self.radius = half_chord / math.sin(angle / 2)
      
      angleSegment = qad_utils.getAngleBy2Pts(startPt, endPt)
      ptMiddle = qad_utils.getMiddlePoint(startPt, endPt)
            
      # Pitagora
      distFromCenter = math.sqrt((self.radius * self.radius) - (half_chord * half_chord))
      if angle < math.pi:  # se angolo < 180 gradi
         # aggiungo 90 gradi per cercare il centro a sinistra del segmento
         self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                        angleSegment + (math.pi / 2),
                                                        distFromCenter)
      else:
         # sottraggo 90 gradi per cercare il centro a destra del segmento
         self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                        angleSegment - (math.pi / 2),
                                                        distFromCenter)
      self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
      self.reversed = False
      return True


   # ============================================================================
   # fromStartEndPtsTan
   # ============================================================================
   def fromStartEndPtsTan(self, startPt, endPt, tan):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      punto finale
      direzione della tangente sul punto iniziale
      """
      if startPt == endPt:
         return False
      
      angleSegment = qad_utils.getAngleBy2Pts(startPt, endPt)
      if tan == angleSegment or tan == angleSegment - math.pi:
         return False
               
      chord = qad_utils.getDistance(startPt, endPt)
      half_chord = chord / 2
      ptMiddle = qad_utils.getMiddlePoint(startPt, endPt)

      angle = tan + (math.pi / 2)
      angle = angleSegment - angle
      distFromCenter = math.tan(angle) * half_chord
      self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                     angleSegment - (math.pi / 2),
                                                     distFromCenter)
      pt = qad_utils.getPolarPointByPtAngle(startPt, tan, chord)
      
      if qad_utils.leftOfLine(endPt, startPt, pt) < 0:
         # arco si sviluppa a sinistra della tangente
         self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
         self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
         self.reversed = False
      else:
         # arco si sviluppa a destra della tangente
         self.startAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
         self.endAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
         self.reversed = True
         
      self.radius = qad_utils.getDistance(startPt, self.center)
      return True


   # ============================================================================
   # fromStartEndPtsRadius
   # ============================================================================
   def fromStartEndPtsRadius(self, startPt, endPt, radius):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      punto finale
      raggio
      """
      if startPt == endPt or radius <= 0:
         return False

      chord = qad_utils.getDistance(startPt, endPt)
      half_chord = chord / 2
      if radius < half_chord:
         return False

      self.radius = radius
      angleSegment = qad_utils.getAngleBy2Pts(startPt, endPt)
      ptMiddle = qad_utils.getMiddlePoint(startPt, endPt)
            
      # Pitagora
      distFromCenter = math.sqrt((self.radius * self.radius) - (half_chord * half_chord))
      # aggiungo 90 gradi
      self.center = qad_utils.getPolarPointByPtAngle(ptMiddle,
                                                     angleSegment + (math.pi / 2),
                                                     distFromCenter)
      self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
      self.reversed = False
      return True


   # ============================================================================
   # fromStartPtAngleRadiusChordDirection
   # ============================================================================
   def fromStartPtAngleRadiusChordDirection(self, startPt, angle, radius, chordDirection):
      """
      setta le caratteristiche dell'arco attraverso:
      punto iniziale
      angolo inscritto
      raggio
      direzione della corda
      """
      if angle == 0 or angle == 2 * math.pi or radius <= 0:
         return False

      a = chordDirection + (math.pi / 2) - (angle / 2) 
      self.radius = radius
      self.center = qad_utils.getPolarPointByPtAngle(startPt, a, radius)
      endPt = qad_utils.getPolarPointByPtAngle(self.center, a + math.pi + angle, radius)
                 
      self.startAngle = qad_utils.getAngleBy2Pts(self.center, startPt)
      self.endAngle = qad_utils.getAngleBy2Pts(self.center, endPt)
      self.reversed = False
      return True
   

   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points, startVertex, atLeastNSegment=None):
      """
      setta le caratteristiche del primo arco incontrato nella lista di punti
      partendo dalla posizione startVertex (0-indexed).
      Ritorna la posizione nella lista del punto finale se é stato trovato un arco
      altrimenti None
      N.B. i punti NON devono essere in coordinate geografiche
      """
      # se il punto iniziale e quello finale coincidono non é un arco
      if points[startVertex] == points[-1]:
         return None

      i = startVertex

      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      totPoints = len(points) - startVertex
      nSegment = totPoints - 1
      # perché sia un arco ci vogliono almeno _atLeastNSegment segmenti e almeno 3 punti
      if nSegment < _atLeastNSegment or totPoints < 3:
         return None

      myPoints = []
      # sposto i primi 3 punti vicino a 0,0 per migliorare la precisione dei calcoli
      dx = points[startVertex].x()
      dy = points[startVertex].y()
      myPoints.append(qad_utils.movePoint(points[startVertex], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[startVertex + 1], -dx, -dy))
      myPoints.append(qad_utils.movePoint(points[startVertex + 2], -dx, -dy))
         
#       InfinityLinePerpOnMiddle1 = qd_utils.getInfinityLinePerpOnMiddle(myPoints[0], myPoints[1])
#       if InfinityLinePerpOnMiddle1 is None: return None
#       InfinityLinePerpOnMiddle2 = qad_utils.getInfinityLinePerpOnMiddle(myPoints[1], myPoints[2])
#       if InfinityLinePerpOnMiddle2 is None: return None
#  
#       # calcolo il presunto centro con 2 segmenti
#       center = qad_utils.getIntersectionPointOn2InfinityLines(InfinityLinePerpOnMiddle1[0], \
#                                                               InfinityLinePerpOnMiddle1[1], \
#                                                               InfinityLinePerpOnMiddle2[0], \
#                                                               InfinityLinePerpOnMiddle2[1])
#       if center is None: return None # linee parallele
      
      # se uso QgsCircle ottengo una miglior precisione
      circle = QgsCircle.from3Points(QgsPoint(myPoints[0]), QgsPoint(myPoints[1]), QgsPoint(myPoints[2]))
      if circle.isEmpty() == True:
         return None
      
      center = circle.center()
      center = QgsPointXY(center.x(), center.y())      
      radius = qad_utils.getDistance(center, myPoints[0])  # calcolo il presunto raggio
       
      # calcolo il verso dell'arco e l'angolo dell'arco
      # se un punto intermedio dell'arco è a sinistra del
      # segmento che unisce i due punti allora il verso è antiorario
      startClockWise = True if qad_utils.leftOfLine(myPoints[1], myPoints[0], myPoints[2]) < 0 else False
      angle = qad_utils.getAngleBy3Pts(myPoints[0], center, myPoints[2], startClockWise)
      
      # uso la distanza TOLERANCE2COINCIDENT / 2 perchè in una polilinea se ci sono 2 archi consecutivi
      # si vuole essere sicuri che il punto finale del primo arco sia distante dal punto iniziale del
      # secondo arco non più di TOLERANCE2COINCIDENT perchè siano considerato 2 punti coincidenti
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT")) / 2
      # myTolerance = 0 # test
      
      i = 3
      while i < totPoints:
         # sposto i punti vicino a 0,0 per migliorare la precisione dei calcoli
         myPoints.append(qad_utils.movePoint(points[i + startVertex], -dx, -dy))

         # se TOLERANCE2COINCIDENT = 0,001 viene riconosciuto un arco di 1000 m
         # se il punto calcolato non è abbastanza vicino al punto reale
         # altrimenti trovo problemi con le intersezioni con gli oggetti
         if qad_utils.ptNear(qad_utils.getPolarPointByPtAngle(center, qad_utils.getAngleBy2Pts(center, myPoints[i]), radius), \
                              myPoints[i], myTolerance) == False:
             break
                        
         # calcolo il verso dell'arco e l'angolo                 
         clockWise = True if qad_utils.leftOfLine(myPoints[i - 1], myPoints[i - 2], myPoints[i]) < 0 else False
         if startClockWise != clockWise: break # cambiata la direzione
         angle = angle + qad_utils.getAngleBy3Pts(myPoints[i - 1], center, myPoints[i], startClockWise)
         if angle >= 2 * math.pi: break # l'arco non può avere un angolo interno maggiore o uguale a 2 pi
                          
         i = i + 1

      # se non sono stati trovati un numero sufficiente di segmenti successivi
      i = i - 1 # ultimo punto valido dell'arco 
      if i < _atLeastNSegment: return None

      self.center = center
      self.radius = radius
      
      # se il verso é orario
      if startClockWise:
         # inverto l'angolo iniziale con quello finale
         self.endAngle = qad_utils.getAngleBy2Pts(center, myPoints[0])
         self.startAngle = qad_utils.getAngleBy2Pts(center, myPoints[i])
         self.reversed = True
      else:
         self.startAngle = qad_utils.getAngleBy2Pts(center, myPoints[0])
         self.endAngle = qad_utils.getAngleBy2Pts(center, myPoints[i])
         self.reversed = False

      # traslo la geometria per riportarla alla sua posizione originale
      self.move(dx, dy)

      return i + startVertex


   # ===============================================================================
   # sqrDist
   # ===============================================================================
   def sqrDist(self, point):
      # obbligatoria
      """
      la funzione ritorna una lista con 
      (<minima distanza al quadrato>
       <punto più vicino>)
      """
      minDistPoint = QgsPointXY()
      angle = qad_utils.getAngleBy2Pts(self.center, point)
      if self.isAngleBetweenAngles(angle):
         distFromArc = qad_utils.getDistance(self.center, point) - self.radius
         return (distFromArc * distFromArc, qad_utils.getPolarPointByPtAngle(self.center, angle, self.radius))
      else:      
         startPt = self.getStartPt()
         endPt = self.getEndPt()
         distFromStartPt = qad_utils.getSqrDistance(startPt, point)
         distFromEndPt = qad_utils.getSqrDistance(endPt, point)
         if distFromStartPt < distFromEndPt:
            return (distFromStartPt, startPt)
         else:
            return (distFromEndPt, endPt)



   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      # obbligatoria
      self.center = qad_utils.movePoint(self.center, offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      self.center = qad_utils.rotatePoint(self.center, basePt, angle)
      self.startAngle = qad_utils.normalizeAngle(self.startAngle + angle)
      self.endAngle = qad_utils.normalizeAngle(self.endAngle + angle)
   

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
      startPt = qad_utils.mirrorPoint(self.getStartPt(), mirrorPt, mirrorAngle)
      secondPt = qad_utils.mirrorPoint(self.getMiddlePt(), mirrorPt, mirrorAngle)
      endPt = qad_utils.mirrorPoint(self.getEndPt(), mirrorPt, mirrorAngle)
      self.fromStartSecondEndPts(startPt, secondPt, endPt)
      #self.reversed = not self.reversed  # cambio la direzione dell'arco


   # ===============================================================================
   # offset
   # ===============================================================================
   def offset(self, offsetDist, offsetSide):
      """
      la funzione modifica l'arco facendone l'offset
      secondo una distanza e un lato di offset ("right" o "left" o "internal" o "external")
      """
      side = ""
      if offsetSide == "right":
         if self.reversed: # direzione oraria
            side = "internal" # offset verso l'interno del cerchio
         else:
            side = "external" # offset verso l'esterno del cerchio
      elif offsetSide == "left":
         if self.reversed: # direzione oraria
            side = "external" # offset verso l'esterno del cerchio
         else:
            side = "internal" # offset verso l'interno del cerchio
      else:
         side = offsetSide
         
      if side == "internal": # offset verso l'interno del cerchio
         radius = self.radius - offsetDist
      elif side == "external": # offset verso l'esterno del cerchio
         radius = self.radius + offsetDist

      if radius <= 0: return False
      self.radius = radius
          
      return True


   # ============================================================================
   # extend
   # ============================================================================
   def extend(self, extend_startPt, limitPt, tolerance2ApproxCurve):
      """
      la funzione estende l'arco dalla parte del punto iniziale se extend_startPt = True (altrimenti finale) fino ad
      incontrare il punto <limitPt>.
      """
      if extend_startPt:
         if self.reversed:
            return self.setEndAngleByPt(limitPt)
         else:
            return self.setStartAngleByPt(limitPt)
      else:
         if self.reversed:
            return self.setStartAngleByPt(limitPt)
         else:
            return self.setEndAngleByPt(limitPt)


   # ===============================================================================
   # breakOnPts
   # ===============================================================================
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
      
      part1 = self.getGeomBetween2Pts(self.getStartPt(), myFirstPt)
      if mySecondPt is None:
         part2 = self.getGeomBetween2Pts(myFirstPt, self.getEndPt())
      else:
         part2 = self.getGeomBetween2Pts(mySecondPt, self.getEndPt())

      return [part1, part2]


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
