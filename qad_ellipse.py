# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione delle ellissi
 
                              -------------------
        begin                : 2018-05-15
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
from copy import deepcopy

from . import qad_utils
from .qad_variables import QadVariables
from .qad_msg import QadMsg
from .qad_point import QadPoint


#===============================================================================
# QadEllipse ellipse class
#===============================================================================
class QadEllipse():
    
   def __init__(self, ellipse = None):
      if ellipse is not None:
         self.set(ellipse.center, ellipse.majorAxisFinalPt, ellipse.axisRatio)
      else:    
         self.center = None
         self.majorAxisFinalPt = None # punto finale dell'asse maggiore (a dx)
         self.axisRatio = 0 # rapporto tra asse minore e asse maggiore

   def whatIs(self):
      # obbligatoria
      return "ELLIPSE"

   
   #============================================================================
   # isClosed
   #============================================================================
   def isClosed(self):
      return True


   def set(self, center, majorAxisFinalPt = None, axisRatio = None):
      if isinstance(center, QadEllipse):
         ellipse = center
         return self.set(ellipse.center, ellipse.majorAxisFinalPt, ellipse.axisRatio)
      
      if center == majorAxisFinalPt: return None
      self.center = QgsPointXY(center)
      self.majorAxisFinalPt = QgsPointXY(majorAxisFinalPt)
      self.axisRatio = axisRatio
      return self


   def transform(self, coordTransform):
      """Transform this geometry as described by CoordinateTranasform ct."""
      self.center = coordTransform.transform(self.center)      
      self.majorAxisFinalPt = coordTransform.transform(self.majorAxisFinalPt)      

   
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """Transform this geometry as described by CRS."""
      if (sourceCRS is not None) and (destCRS is not None) and sourceCRS != destCRS:       
         coordTransform = QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()) # trasformo le coord
         self.center =  coordTransform.transform(self.center)
         self.majorAxisFinalPt =  coordTransform.transform(self.majorAxisFinalPt)

   
   def __eq__(self, ellipse):
      # obbligatoria
      """self == other"""
      if ellipse.whatIs() != "ELLIPSE": return False
      if self.center != ellipse.center or self.majorAxisFinalPt != ellipse.majorAxisFinalPt or self.axisRatio != ellipse.axisRatio:
         return False
      else:
         return True    

  
   def __ne__(self, ellipse):
      """self != other"""
      return not self.__eq__(ellipse)


   def equals(self, ellipse):
      # uguali geometricamente (NON conta il verso)
      return self.__eq__(ellipse)


   def copy(self):
      # obbligatoria
      return QadEllipse(self)


   def length(self):
      a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
      b = a * self.axisRatio # semiasse minore
      numerator = a * a + b * b
      if numerator == 0: return 0
      return 2 * math.pi * math.sqrt(numerator / 2)


   def area(self):
      a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
      b = a * self.axisRatio # semiasse minore
      return  math.pi * a * b


   #============================================================================
   # getRotation
   #============================================================================
   def getRotation(self):
      return qad_utils.getAngleBy2Pts(self.center, self.majorAxisFinalPt)


   #===============================================================================
   # getBoundingBox
   #===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude l'ellisse.
      """
      angle = self.getRotation()
      a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
      b = a * self.axisRatio # semiasse minore
 
      pt1 = qad_utils.getPolarPointByPtAngle(self.majorAxisFinalPt, angle - math.pi / 2, b)
      pt2 = qad_utils.getPolarPointByPtAngle(self.majorAxisFinalPt, angle + math.pi / 2, b)
      pt3 = qad_utils.getPolarPointByPtAngle(pt1, angle + math.pi, 2 * a)
      pt4 = qad_utils.getPolarPointByPtAngle(pt2, angle + math.pi, 2 * a)
       
      xMin = pt1.x()
      yMin = pt1.y()
      xMax = pt1.x()
      yMax = pt1.y()
      for pt in (pt2, pt3, pt4):
         if pt.x() < xMin: xMin = pt.x()
         if pt.y() < yMin: yMin = pt.y()
         if pt.x() > xMax: xMax = pt.x()
         if pt.y() > yMax: yMax = pt.y()
          
      return QgsRectangle(xMin, yMin, xMax, yMax)


   #============================================================================
   # getFocus
   #============================================================================
   def getFocus(self):
      # restituisce una lista di 2 punti che sono i fuochi dell'ellisse
      # http://www.softschools.com/math/calculus/finding_the_foci_of_an_ellipse/
      angle = qad_utils.getAngleBy2Pts(self.center, self.majorAxisFinalPt)
      a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
      b = a * self.axisRatio # semiasse minore
      numerator = a * a - b * b
      if numerator == 0: return []
      c = math.sqrt(numerator)
      pt1 = qad_utils.getPolarPointByPtAngle(self.center, angle, c)
      pt2 = qad_utils.getPolarPointByPtAngle(self.center, angle, -c)
      return [pt1, pt2]
      
      
   #============================================================================
   # containsPt
   #============================================================================
   def containsPt(self, point):
      return True if self.whereIsPt(point) == 0 else False # -1 interno, 0 sull'ellisse, 1 esterno:


   #============================================================================
   # whereIsPt
   #============================================================================
   def whereIsPt(self, point):
      # ritorna -1 se il punto è interno, 0 se è sull'ellisse, 1 se è esterno
      foci = self.getFocus()
      if len(foci) == 0: return False
      dist1 = qad_utils.getDistance(foci[0], self.majorAxisFinalPt)
      dist2 = qad_utils.getDistance(foci[1], self.majorAxisFinalPt)
      distSumEllipse = dist1 + dist2
      dist1 = qad_utils.getDistance(foci[0], point)
      dist2 = qad_utils.getDistance(foci[1], point)
      distSum = dist1 + dist2
      if qad_utils.doubleNear(distSumEllipse, distSum):
         return 0
      elif distSum < distSumEllipse:
         return -1
      else:
         return 1


   #============================================================================
   # getQuadrantPoints
   #============================================================================
   def getQuadrantPoints(self):
      # ritorna i punti quadranti: partendo da majorAxisFinalPt in ordine antiorario
      angle = qad_utils.getAngleBy2Pts(self.center, self.majorAxisFinalPt)
      a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
      b = a * self.axisRatio # semiasse minore

      pt1 = QgsPointXY(self.majorAxisFinalPt)
      pt2 = qad_utils.getPolarPointByPtAngle(self.center, angle + math.pi / 2, b)
      pt3 = qad_utils.getPolarPointByPtAngle(self.center, angle + math.pi, a)
      pt4 = qad_utils.getPolarPointByPtAngle(self.center, angle - math.pi / 2, b)

      return [pt1, pt2, pt3, pt4]


   #============================================================================
   # translateAndRotatePtForNormalEllipse
   #============================================================================
   def translateAndRotatePtForNormalEllipse(self, point, inverse):
      # poichè è conveniente fare i calcoli considerando una ellisse con centro in 0,0 e rotazione 0
      # traslo e ruoto il punto con cui devo fare i calcoli per adattarlo a questo tipo di ellisse
      # il parametro inverse, se uguale a True, fa il calcolo inverso per riottenere il punto originale
      rot = self.getRotation()
      if rot > math.pi/2 and rot < math.pi*3/2: rot = rot - math.pi
      if inverse == False:
         myPoint = QgsPointXY(point.x() - self.center.x(), point.y() - self.center.y())
         myPoint = qad_utils.rotatePoint(myPoint, QgsPointXY(0,0), -1 * rot)
      else:
         myPoint = qad_utils.rotatePoint(point, QgsPointXY(0,0), rot)
         myPoint = QgsPointXY(myPoint.x() + self.center.x(), myPoint.y() + self.center.y())
   
      return myPoint


   def getNormalAngleToAPointOnEllipse(self, p):
      # https://www3.ul.ie/~rynnet/swconics/TC.htm
      # 1. Join the point P to the two focal points
      # 2. Bisect the angle formed to get the normal (the normal is a line perpendicular to the tangent at the point of contact (p.o.c.)).
      
      # trovo i fuochi
      foci = self.getFocus()
      if len(foci) == 0: return None
      # punto 1 e 2
      bisectorLine = qad_utils.getBisectorInfinityLine(foci[0], p, foci[1])
      return qad_utils.getAngleBy2Pts(bisectorLine[1], bisectorLine[0]) # verso l'esterno dell'ellisse


   def getTanDirectionOnPt(self, p):
      # https://www3.ul.ie/~rynnet/swconics/TC.htm
      # 1. Join the point P to the two focal points
      # 2. Bisect the angle formed to get the normal (the normal is a line perpendicular to the tangent at the point of contact (p.o.c.)).
      # 3. Construct the tangent perpendicular to the normal at the p.o.c.
      
      normal = self.getNormalAngleToAPointOnEllipse(p)
      # punto 3
      angle = normal + math.pi / 2
      
      return qad_utils.normalizeAngle(angle)
   

   #============================================================================
   # getAngleFromParam
   #============================================================================
   def getAngleFromParam(self, param):
      """
      L'equazione parametrica per l'ellisse è x=a*cos(param), y=b*sin(param).
      E' importante capire che param non è l'angolo al centro.
      Questa funzione ottiene l'angolo al centro partendo da param
      arctan(b/a * tan(param)) dove
      a = asse maggiore
      b = asse minore      
      """
      angle = math.atan(self.axisRatio * math.tan(param))
      myParam = param % (math.pi * 2) # modulo
      if myParam > math.pi / 2 and myParam < math.pi * 3 / 2:
         angle = angle + math.pi
      
      return angle
      
      
   #============================================================================
   # getParamFromAngle
   #============================================================================
   def getParamFromAngle(self, angle):
      """
      L'equazione parametrica per l'ellisse è x=a*cos(param), y=b*sin(param).
      E' importante capire che param non è l'angolo al centro.
      Questa funzione ottiene param partendo dall'angolo al centro
      arctan(a/b * tan(angle)) dove
      a = asse maggiore
      b = asse minore      
      """        
      param = math.atan(1.0 / self.axisRatio * math.tan(angle))
      myAngle = angle % (math.pi * 2) # modulo
      if myAngle > math.pi / 2 and myAngle < math.pi * 3 / 2:
      #if myAngle > math.pi and myAngle < 2 * math.pi:
         param = param + math.pi
      return param


   
   #============================================================================
   # asPolyline
   #============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      ritorna una lista di punti che definisce l'ellisse
      """
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve
         
      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      param = 0
      endParam = 2 * math.pi
      pt = self.getPointAt(param)
      
      angleStep = 2 * math.pi / _atLeastNSegment
      
      points = []
      points.append(pt)
      while True:
         param, pt = self.getNextParamPt(param, pt, angleStep, tolerance)
         if param > endParam: break
         points.append(pt)
      
      if points[-1] != points[0]: # se l'ultimo punto non coincide con il primo
         if qad_utils.ptNear(points[-1], points[0]): # se l'ultimo punto è abbastanza vicino al primo
            points[-1].set(points[0].x(), points[0].y()) # sposto l'ultimo punto e lo faccio coincidere con il primo
         else:
            points.append(QgsPointXY(points[0])) # aggiungo l'ultimo punto coincidente al primo
         
      return points

   
   #===============================================================================
   # asLineString
   #===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna l'ellisse in forma di lineString.
      """
      return QgsLineString(self.asPolyline(tolerance2ApproxCurve, atLeastNSegment))


   #===============================================================================
   # asAbstractGeom
   #===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna l'ellisse in forma di QgsGeometry.
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
         
      elif flatType == QgsWkbTypes.CurvePolygon:
         linestring = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         curvePolygon = QgsCurvePolygon()
         curvePolygon.setExteriorRing(linestring)
         return curvePolygon
         
      elif flatType == QgsWkbTypes.MultiSurface: # Geometry that is combined from several CurvePolygon is called MultiSurface
         curvePolygon = self.asAbstractGeom(QgsWkbTypes.CurvePolygon, tolerance2ApproxCurve, atLeastNSegment)
         multiSurface = QgsMultiSurface()
         multiSurface.addGeometry(curvePolygon)
         return multiSurface

      elif flatType == QgsWkbTypes.Polygon:
         lineString = self.asLineString(tolerance2ApproxCurve, atLeastNSegment)
         polygon = QgsPolygon()
         polygon.setExteriorRing(lineString)
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


   #===============================================================================
   # asGeom
   #===============================================================================
   def asGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna l'ellisse in forma di QgsGeometry.
      """
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment));


   #============================================================================
   # getPointAt
   #============================================================================
   def getPointAt(self, param):
      """
      L'equazione parametrica per l'ellisse è x=a*cos(param), y=b*sin(param).
      E' importante capire che param non è l'angolo al centro.     
      Ritorna un punto dell'ellisse usando l'equazione parametrica (0 = punto finale dell'asse -> majorAxisFinalPt)
      n.b. La funzione non tiene conto se si tratta di un arco di ellisse
      """
      axis_a = qad_utils.getDistance(self.center, self.majorAxisFinalPt)
      axis_b = axis_a * self.axisRatio
      rot = qad_utils.getAngleBy2Pts(self.center, self.majorAxisFinalPt)
      x = self.center.x() + \
                   axis_a * math.cos(param) * math.cos(rot) - \
                   axis_b * math.sin(param) * math.sin(rot)
      y = self.center.y() + \
                   axis_a * math.cos(param) * math.sin(rot) + \
                   axis_b * math.sin(param) * math.cos(rot)
                   
      return QgsPointXY(x, y)
   

   #============================================================================
   # getPointAtAngle
   #============================================================================
   def getPointAtAngle(self, angle):
      """
      Trova il punto sull'ellisse
      n.b. La funzione non tiene conto se si tratta di un arco di ellisse
      """
      axis_a = qad_utils.getDistance(self.center, self.majorAxisFinalPt)
      axis_b = axis_a * self.axisRatio
      rot = qad_utils.getAngleBy2Pts(self.center, self.majorAxisFinalPt)
      
      x = axis_a * math.cos(rot)
      y = axis_b * math.sin(rot)
      
      cos_angle = math.cos(angle)
      sin_angle = math.sin(angle)
      
      x_new = x * cos_angle - y * sin_angle
      y_new = x * sin_angle + y * cos_angle      
      
      pt = QadPoint()
      pt.setX(x_new)
      pt.setY(y_new)
      pt.move(self.center.x(), self.center.y())
                   
      return pt


   #============================================================================
   # getNextParamPt
   #============================================================================
   def getNextParamPt(self, param1, pt1, angleStep, tolerance):
      """
      La funzione cerca l'angolo (dell'equazione parametrica) successivo all'angolo param1 
      e il punto successivo a p1 (p2) in modo che il segmento p1-p2 non si distacchi 
      oltre la tolleranza dalla curva reale dell'ellisse.
      n.b. La funzione non tiene conto se si tratta di un arco di ellisse
      """
      #rot = qad_utils.getAngleBy2Pts(self.center, self.majorAxisFinalPt)
      param2 = param1 + angleStep
      pt2 = self.getPointAt(param2)
      paramMiddle = (param1 + param2) / 2 
      ptMiddleSegment = qad_utils.getMiddlePoint(pt1, pt2)
      ptMiddleEllipse = self.getPointAt(paramMiddle)
      error = qad_utils.getDistance(ptMiddleSegment, ptMiddleEllipse)
      while error > tolerance:
         angleStep = angleStep / 2
         param2 = param1 + angleStep
         pt2 = self.getPointAt(param2)
         paramMiddle = (param1 + param2) / 2 
         ptMiddleSegment = qad_utils.getMiddlePoint(pt1, pt2)
         ptMiddleEllipse = self.getPointAt(paramMiddle)
         error = qad_utils.getDistance(ptMiddleSegment, ptMiddleEllipse)
         
      return param2, pt2
      
   
   #============================================================================
   # fromPolyline
   #============================================================================
   def fromPolyline(self, points, atLeastNSegment = None):
      """
      setta le caratteristiche dell'ellisse incontrata nella lista di punti.
      Ritorna True se é stato trovato un'ellissa altrimenti False.
      N.B. in punti NON devono essere in coordinate geografiche
      """
      # se il punto iniziale e quello finale non coincidono non é un'ellisse
      if points[0] != points[-1]:
         return False

      totPoints = len(points) - 1 # l'ultimo dovrebbe essere uguale al primo quindi non lo conto
   
      if atLeastNSegment is None:
         _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEMINSEGMENTQTY"), 12)
      else:
         _atLeastNSegment = atLeastNSegment
      
      # perché sia una ellisse ci vogliono almeno _atLeastNSegment segmenti e almeno 5 punti
      if (totPoints - 1) < _atLeastNSegment or totPoints < 5:
         return False

      everyNPts = int(totPoints / 5)
      
      # sposto i 5 punti di valutazione vicino a 0,0 per migliorare la precisione dei calcoli
      dx = points[0].x()
      dy = points[0].y()
      first5Points = []
      first5Points.append(qad_utils.movePoint(points[0], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[everyNPts], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[everyNPts * 2], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[everyNPts * 3], -dx, -dy))
      first5Points.append(qad_utils.movePoint(points[everyNPts * 4], -dx, -dy))
      
      #first5Points = [QgsPointXY(20.0, 0.0), QgsPointXY(6.18034,9.51057), QgsPointXY(-16.1803,5.87785), QgsPointXY(-16.1803,-5.87785), QgsPointXY(6.18034,-9.51057)]

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
         return False
      cX = (b*e - 2*c*d) / (4*a*c - b*b)
      cY = (d*b - 2*a*e) / (4*a*c - b*b)
      center = (cX, cY)        
      res = MathTools.ellipseAxes(conic)
      if res is None: return False
      axisDir1 = res[0]
      axisDir2 = res[1]
      axisLen1 = MathTools.ellipseAxisLen(conic, center, axisDir1)
      if axisLen1 is None: return false
      axisLen2 = MathTools.ellipseAxisLen(conic, center, axisDir2)
      if axisLen2 is None: return false
          
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
      
      #majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, rotAngle, majorLen)
      #if majorAxisFinalPt.x() < center.x(): 
      #   majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, -rotAngle, majorLen)
      axisRatio = minorLen / majorLen;

      center = QgsPointXY(center[0] + baryC[0], center[1] + baryC[1])
      
      testEllipse = QadEllipse()
      testEllipse.set(center, majorAxisFinalPt, axisRatio)
      foci = testEllipse.getFocus()
      if len(foci) == 0: return False
      dist1 = qad_utils.getDistance(foci[0], testEllipse.majorAxisFinalPt)
      dist2 = qad_utils.getDistance(foci[1], testEllipse.majorAxisFinalPt)
      distSumEllipse = dist1 + dist2
      
      # per problemi di approssimazione dei calcoli
      tolerance = distSumEllipse * 1.e-2 # percentuale della somma delle distanze dai fuochi
      
      # sposto i punti vicino a 0,0 per migliorare la precisione dei calcoli
      myPoints = []
      i = 0
      while i < totPoints:
         myPoints.append(qad_utils.movePoint(points[i], -dx, -dy))
         i = i + 1
     
      # se il punto finale dell'arco è a sinistra del
      # segmento che unisce i punti iniziale e intermedio allora il verso è antiorario
      startClockWise = False if qad_utils.leftOfLine(myPoints[2], myPoints[0], myPoints[1]) < 0 else True
      angle = 0

      # verifico che i punti siano sull'ellisse
      i = 0
      while i < totPoints:
         dist1 = qad_utils.getDistance(foci[0], myPoints[i])
         dist2 = qad_utils.getDistance(foci[1], myPoints[i])
         distSum = dist1 + dist2
         # calcolo la somma delle distanze dai fuochi e verifico che sia abbastanza simile a quella originale
         if qad_utils.doubleNear(distSumEllipse, distSum, tolerance) == False:
            return False
         # calcolo il verso dell'arco e l'angolo
         clockWise = False if qad_utils.leftOfLine(myPoints[i], myPoints[i - 2], myPoints[i - 1]) < 0 else True
            
         # il verso deve essere lo stesso di quello originale
         if startClockWise != clockWise:
            return False
         angle = angle + qad_utils.getAngleBy3Pts(myPoints[i-1], center, myPoints[i], startClockWise)
         # l'angolo inscritto non può essere > di 360
         if angle < 2 * math.pi or qad_utils.doubleNear(angle, 2 * math.pi):
            i = i + 1
         else:
            return False

      self.center = center
      self.majorAxisFinalPt = majorAxisFinalPt
      self.axisRatio = axisRatio
      # traslo la geometria per riportarla alla sua posizione originale
      self.move(dx, dy)

      return True


   #============================================================================
   # move
   #============================================================================
   def move(self, offsetX, offsetY):
      self.center = qad_utils.movePoint(self.center, offsetX, offsetY)
      self.majorAxisFinalPt = qad_utils.movePoint(self.majorAxisFinalPt, offsetX, offsetY)


   #============================================================================
   # rotate
   #============================================================================
   def rotate(self, basePt, angle):
      self.center = qad_utils.rotatePoint(self.center, basePt, angle)
      self.majorAxisFinalPt = qad_utils.rotatePoint(self.majorAxisFinalPt, basePt, angle)


   #============================================================================
   # scale
   #============================================================================
   def scale(self, basePt, scale):
      self.center = qad_utils.scalePoint(self.center, basePt, scale)
      self.majorAxisFinalPt = qad_utils.scalePoint(self.majorAxisFinalPt, basePt, scale)


   #============================================================================
   # mirror
   #============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      self.center = qad_utils.mirrorPoint(self.center, mirrorPt, mirrorAngle)
      self.majorAxisFinalPt = qad_utils.mirrorPoint(self.center, mirrorPt, mirrorAngle)


   #============================================================================
   # getNextParamPtForOffset
   #============================================================================
   def getNextParamPtForOffset(self, param1, pt1Offset, angleStep, tolerance, dist):
      """
      La funzione cerca l'angolo (dell'equazione parametrica) successivo all'angolo param1 
      e il punto successivo a p1 (p2) in modo che il segmento p1-p2 non si distacchi 
      oltre la tolleranza dalla curva do offset dell'ellisse.
      n.b. La funzione non tiene conto se si tratta di un arco di ellisse
      """
      rot = self.getRotation()
      param2 = param1 + angleStep
      pt2 = self.getPointAt(param2)     
      pt2Offset = qad_utils.getPolarPointByPtAngle(pt2, self.getNormalAngleToAPointOnEllipse(pt2), dist)      
      paramMiddle = (param1 + param2) / 2 
      ptMiddleSegment = qad_utils.getMiddlePoint(pt1Offset, pt2Offset)
      ptMiddle = self.getPointAt(paramMiddle)
      ptMiddleOffset = qad_utils.getPolarPointByPtAngle(ptMiddle, self.getNormalAngleToAPointOnEllipse(ptMiddle), dist)      
      error = qad_utils.getDistance(ptMiddleSegment, ptMiddleOffset)
      while error > tolerance:
         angleStep = angleStep / 2
         param2 = param1 + angleStep
         pt2 = self.getPointAt(param2)
         pt2Offset = qad_utils.getPolarPointByPtAngle(pt2, self.getNormalAngleToAPointOnEllipse(pt2), dist)      
         paramMiddle = (param1 + param2) / 2 
         ptMiddleSegment = qad_utils.getMiddlePoint(pt1Offset, pt2Offset)
         ptMiddle = self.getPointAt(paramMiddle)
         ptMiddleOffset = qad_utils.getPolarPointByPtAngle(ptMiddle, self.getNormalAngleToAPointOnEllipse(ptMiddle), dist)      
         error = qad_utils.getDistance(ptMiddleSegment, ptMiddleOffset)
         
      return param2, pt2Offset


   #===============================================================================
   # offset
   #===============================================================================
   def offset(self, offsetDist, offsetSide, tolerance2ApproxCurve = None):
      """
      la funzione restituisce l'ellisse facendone l'offset.
      poichè l'offset di una ellisse non è una ellisse, restituisce una lista di punti o None
      secondo una distanza e un lato di offset ("internal" o "external")        
      """
      if offsetSide == "internal":
         # offset verso l'interno dell'ellisse
         dist = -offsetDist
         a = qad_utils.getDistance(self.center, self.majorAxisFinalPt) # semiasse maggiore
         b = a * self.axisRatio # semiasse minore
         if a > b:
            if b <= offsetDist: return None
         else:
            if a <= offsetDist: return None
      else:
         # offset verso l'esterno dell'ellisse
         dist = offsetDist

      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve
         
      _atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEMINSEGMENTQTY"), 12)
      
      param = 0
      endParam = 2 * math.pi
      pt = self.getPointAt(param)
      ptOffset = qad_utils.getPolarPointByPtAngle(pt, self.getNormalAngleToAPointOnEllipse(pt), dist)
      
      angleStep = 2 * math.pi / _atLeastNSegment
      
      points = []
      points.append(ptOffset)
      while True:
         param, ptOffset = self.getNextParamPtForOffset(param, ptOffset, angleStep, tolerance, dist)
         if param > endParam: break
         points.append(ptOffset)
      
      lastPt = self.getPointAt(endParam)
      lastPtOffset = qad_utils.getPolarPointByPtAngle(lastPt, self.getNormalAngleToAPointOnEllipse(lastPt), dist)      
      if qad_utils.ptNear(points[-1], lastPtOffset) == False: points.append(lastPtOffset) # ultimo elemento della lista
      
      if points[-1] != points[0]:             
         points.append(QgsPointXY(points[0]))
         
      return points


   #============================================================================
   # fromFoci
   #============================================================================
   def fromFoci(self, f1, f2, ptOnEllipse):
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
      dist_f1f2 = qad_utils.getDistance(f1, f2)
      dist_f1PtOnEllipse = qad_utils.getDistance(f1, ptOnEllipse)
      dist_f2PtOnEllipse = qad_utils.getDistance(f2, ptOnEllipse)
      if dist_f1f2 == 0 or dist_f1PtOnEllipse == 0 or dist_f2PtOnEllipse == 0: return None

      dist_tot = dist_f1PtOnEllipse + dist_f2PtOnEllipse
      angle = qad_utils.getAngleBy2Pts(f1, f2)
      ptCenter = qad_utils.getMiddlePoint(f1, f2)
      
      majorAxisLen = dist_tot / 2.0 # semiasse maggiore
      minorAxisLen = math.sqrt((dist_tot/2.0)**2.0 - (dist_f1f2/2.0)**2.0) # semiasse minore
      axisRatio = minorAxisLen / majorAxisLen
      majorAxisPt = qad_utils.getPolarPointByPtAngle(ptCenter, angle, majorAxisLen)

      return self.set(ptCenter, majorAxisPt, axisRatio)
   

   #============================================================================
   # fromExtent
   #============================================================================
   def fromExtent(self, pt1, pt2, rot = 0):
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
      ptCenter = qad_utils.getMiddlePoint(pt1, pt2)
      halfDist = qad_utils.getDistance(pt1, pt2) / 2
      if halfDist == 0: return None
      angle = qad_utils.getAngleBy2Pts(pt1, pt2)
      angle = angle - rot
      projPt1 = qad_utils.getPolarPointByPtAngle(pt1, angle, halfDist)
      projPt2 = qad_utils.getPolarPointByPtAngle(pt1, angle, halfDist)

      majorAxisLen = abs(projPt1.x() - projPt2.x()) / 2.0 # semiasse maggiore
      minorAxisLen = abs(projPt1.y() - projPt2.y()) / 2.0 # semiasse minore
      axisRatio = minorAxisLen / majorAxisLen
      majorAxisPt = qad_utils.getPolarPointByPtAngle(ptCenter, rot, majorAxisLen)

      return self.set(ptCenter, majorAxisPt, axisRatio)


   #============================================================================
   # fromCenterAxis1FinalPtAxis2FinalPt
   #============================================================================
   def fromCenterAxis1FinalPtAxis2FinalPt(self, ptCenter, axis1FinalPt, axis2FinalPt):
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
      distAxis2 = qad_utils.getDistance(ptCenter, axis2FinalPt)
      return fromCenterAxis1FinalPtDistAxis2(cls, ptCenter, axis1FinalPt, distAxis2)


   #============================================================================
   # fromCenterAxis1FinalPtDistAxis2
   #============================================================================
   def fromCenterAxis1FinalPtDistAxis2(self, ptCenter, axis1FinalPt, distAxis2):
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
      axis1Len = qad_utils.getDistance(ptCenter, axis1FinalPt)
      if axis1Len == 0 or distAxis2 == 0: return None
      axisRatio = axis1Len / distAxis2
      return self.set(ptCenter, axis1FinalPt, axisRatio)


   #============================================================================
   # fromCenterAxis1FinalPtAxis2FinalPt
   #============================================================================
   def fromCenterAxis1FinalPtAxis2FinalPt(self, axis1Finalpt1, axis1Finalpt2, axis2FinalPt):
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
      ptCenter = qad_utils.getMiddlePoint(xis1FinalPt1, axis1FinalPt2)
      axis2Len = qad_utils.getDistance(ptCenter, axis2FinalPt)
      return self.fromCenterAxis1FinalPtDistAxis2(ptCenter, axis1FinalPt, axis2Len)


   #============================================================================
   # fromAxis1FinalPtsAxis2Len
   #============================================================================
   def fromAxis1FinalPtsAxis2Len(self, axis1FinalPt1, axis1FinalPt2, distAxis2):
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
      if distAxis2 == 0: return None
      ptCenter = qad_utils.getMiddlePoint(axis1FinalPt1, axis1FinalPt2)
      dist = qad_utils.getDistance(axis1FinalPt1, axis1FinalPt2)
      if dist == 0: return None
      axisRatio = (2 * distAxis2) / dist
      return self.set(ptCenter, axis1FinalPt1, axisRatio)


   #============================================================================
   # fromAxis1FinalPtsArea
   #============================================================================
   def fromAxis1FinalPtsArea(self, axis1FinalPt1, axis1FinalPt2, area):
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
      if area == 0: return None
      ptCenter = qad_utils.getMiddlePoint(axis1FinalPt1, axis1FinalPt2)
      dist = qad_utils.getDistance(axis1FinalPt1, axis1FinalPt2) / 2
      if dist == 0: return None
      b = area / (math.pi * dist)
      return self.fromAxis1FinalPtsAxis2Len(axis1FinalPt1, axis1FinalPt2, b)

   
    
# adopted from ArcheEngine.py from ArchoCAD plugin 
class MathTools(object):
    """Contains static methods that are used for creating ellipses."""
        
    # adopted from Inkscape's "Ellipse by 5 Points Extension" 
    # Copyright (c) 2012 Stuart Pernsteiner
    # Algorithm from:
    # Yap, Chee, "Linear Systems", Fundamental Problems of Algorithmic Algebra    
    # http://cs.nyu.edu/~yap/book/alge/ftpSite/l10.ps.gz
    @staticmethod
    def bareissDeterminant(inMatrix):
        """Computes the determinant of the matrix using Bareiss algorithm.""" 
      
        matrix = deepcopy(inMatrix)
        size = len(matrix)
        lastAkk = 1
        for k in range(size - 1):
            if lastAkk == 0:
                return 0
            for i in range(k + 1, size):
                for j in range(k + 1, size):
                    matrix[i][j] = (matrix[i][j]*matrix[k][k] - matrix[i][k]*matrix[k][j])/lastAkk
            lastAkk = matrix[k][k]
        return matrix[size - 1][size - 1]
                
    # adopted from Inkscape's "Ellipse by 5 Points Extension" 
    # Copyright (c) 2012 Stuart Pernsteiner
    # developed using : 
    # http://math.fullerton.edu/mathews/n2003/conicfit/ConicFitMod/Links/ConicFitMod_lnk_9.html
    @staticmethod
    def conicEquation(points):
        """Computes the equation of the conic section passing through five given points."""
        
        rowMajorMatrix = []
        for i in range(5):            
            (x, y) = points[i]
            row = [x*x, x*y, y*y, x, y, 1]
            rowMajorMatrix.append(row)
        fullMatrix = []
        for i in range(6):
            col = []
            for j in range(5):
                col.append(rowMajorMatrix[j][i])
            fullMatrix.append(col)
        coeffs = []
        sign = 1
        for i in range(6):
            matrix = []
            for j in range(6):
                if j == i:
                    continue
                matrix.append(fullMatrix[j])
            coeffs.append(MathTools.bareissDeterminant(matrix)*sign)
            sign = -sign
        return coeffs
    
    # adopted from Inkscape's "Ellipse by 5 Points Extension" 
    # Copyright (c) 2012 Stuart Pernsteiner   
    @staticmethod
    def ellipseAxes(conic):
        """Compute the axis directions of the ellipse."""
    
        [a, b, c, d, e, f] = conic
        # Compute the eigenvalues of
        #    /  a   b/2 \
        #    \ b/2   c  /
        # This algorithm is from
        # http://www.math.harvard.edu/archive/21b_fall_04/exhibits/2dmatrices/index.html
        ma = a
        mb = b/2
        mc = b/2
        md = c
        mDet = ma*md - mb*mc
        mTrace = ma + md
    
        res = MathTools.solveQuadratic(1, -mTrace, mDet);
        if res is None: return None
        l1 = res[0]
        l2 = res[1]
        
        if mb == 0:
            return [(0, 1), (1, 0)]
        else:
            return [(mb, l1 - ma), (mb, l2 - ma)]
    
    # adopted from Inkscape's "Ellipse by 5 Points Extension" 
    # Copyright (c) 2012 Stuart Pernsteiner
    @staticmethod
    def ellipseAxisLen(conic, center, direction):
        """ Compute the axis length as a multiple of the magnitude of 'direction'"""
        
        [a, b, c, d, e, f] = conic
        (cx, cy) = center
        (dx, dy) = direction
    
        dLen = math.sqrt(dx*dx + dy*dy)
        dx /= dLen
        dy /= dLen
    
        # Solve for t:
        #   a*x^2 + b*x*y + c*y^2 + d*x + e*y + f = 0
        #   x = cx + t * dx
        #   y = cy + t * dy
        # by substituting, we get  qa*t^2 + qb*t + qc = 0, where:
        qa = a*dx*dx + b*dx*dy + c*dy*dy
        qb = a*2*cx*dx + b*(cx*dy + cy*dx) + c*2*cy*dy + d*dx + e*dy
        qc = a*cx*cx + b*cx*cy + c*cy*cy + d*cx + e*cy + f    
        res = MathTools.solveQuadratic(qa, qb, qc)
        if res is None: return None
        t1 = res[0]
        t2 = res[1]
        
        return max(t1, t2)

    @staticmethod        
    def solveQuadratic(a, b, c):
        
        if (b*b - 4*a*c) < 0:
           return None
        discRoot = math.sqrt(b*b - 4*a*c)
        x1 = (-b + discRoot) / (2*a)
        x2 = (-b - discRoot) / (2*a)
        return [x1, x2]
    
    @staticmethod
    def rotation(p, rotAngle, c):       
        # translation
        xT = p[0] - c[0]
        yT = p[1] - c[1]
        # rotation over the origin
        xR = xT*math.cos(rotAngle) - yT*math.sin(rotAngle)
        yR = xT*math.sin(rotAngle) + yT*math.cos(rotAngle)
        # translation back
        newX = xR + c[0]
        newY = yR + c[1]
        return (newX, newY)
    
    @staticmethod
    def barycenter(points):
        
        nPts = len(points)
        sumX = 0
        sumY = 0
        for pt in points :
            sumX += pt.x()
            sumY += pt.y()           
        return (sumX/nPts, sumY/nPts)
