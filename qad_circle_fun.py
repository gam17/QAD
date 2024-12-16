# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per creare cerchi
 
                              -------------------
        begin                : 2018-04-08
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
from .qad_geom_relations import *


# ============================================================================
# circleFrom3Pts
# ============================================================================
def circleFrom3Pts(firstPt, secondPt, thirdPt):
   """
   crea un cerchio attraverso:
   punto iniziale
   secondo punto (intermedio)
   punto finale
   """
   l = QadLine()
   l.set(firstPt, secondPt)
   InfinityLinePerpOnMiddle1 = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l)
   l.set(secondPt, thirdPt)
   InfinityLinePerpOnMiddle2 = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l)
   if InfinityLinePerpOnMiddle1 is None or InfinityLinePerpOnMiddle2 is None:
      return None
   center = QadIntersections.twoInfinityLines(InfinityLinePerpOnMiddle1, InfinityLinePerpOnMiddle2)
   if center is None: return None # linee parallele
   radius = center.distance(firstPt)
   
   return QadCircle().set(center, radius)

   
# ===========================================================================
# circleFrom2IntPtsCircleTanPts
# ===========================================================================
def circleFrom2IntPtsCircleTanPts(pt1, pt2, circle, pt):
   """
   crea un cerchio attraverso 2 punti di intersezione e un cerchio tangente:
   punto1 di intersezione
   punto2 di intersezione
   cerchio di tangenza (oggetto QadCircle)
   punto di selezione cerchio
   """
   # http://www.batmath.it/matematica/a_apollonio/ppc.htm
   circleList = []
   
   if pt1 == pt2: return None
      
   dist1 = pt1.distance(circle.center) # distanza del punto 1 dal centro
   dist2 = pt2.distance(circle.center) # distanza del punto 2 dal centro
   
   # entrambi i punti devono essere esterni o interni a circle
   if (dist1 > circle.radius and dist2 < circle.radius) or \
      (dist1 < circle.radius and dist2 > circle.radius):
      return None 
   
   l = QadLine()
   l.set(pt1, pt2)
   
   if dist1 == dist2: # l'asse di pt1 e pt2 passa per il centro di circle
      if dist1 == circle.radius: # entrambi i punti sono sulla circonferenza di circle
         return None
      
      axis = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l) # asse di pt1 e pt2
      intPts = QadIntersections.infinityLineWithCircle(axis, circle) # punti di intersezione tra l'asse e circle
      for intPt in intPts:
         circleTan = circleFrom3Pts(pt1, pt2, intPt)
         if circleTan is not None:
            circleList.append(circleTan)         
   elif dist1 > circle.radius and dist2 > circle.radius : # entrambi i punti sono esterni a circle
      # mi ricavo una qualunque circonferenza passante per p1 e p2 ed intersecante circle
      circleInt = circleFrom3Pts(pt1, pt2, circle.center)
      if circleInt is None: return None
      
      intPts = QadIntersections.twoCircles(circle, circleInt)
      l1 = QadLine().set(pt1, pt2)
      l2 = QadLine().set(intPts[0], intPts[1])
      intPt = QadIntersections.twoInfinityLines(l1, l2)
      tanPts = QadTangency.fromPointToCircle(intPt, circle)
      for tanPt in tanPts:
         circleTan = circleFrom3Pts(pt1, pt2, tanPt)
         if circleTan is not None:
            circleList.append(circleTan)         
   elif dist1 < circle.radius and dist2 < circle.radius : # entrambi i punti sono interni a circle
      # mi ricavo una qualunque circonferenza passante per p1 e p2 ed intersecante circle
      ptMiddle = qad_utils.getMiddlePoint(pt1, pt2)
      angle = qad_utils.getAngleBy2Pts(pt1, pt2) + math.pi / 2
      pt3 = qad_utils.getPolarPointByPtAngle(ptMiddle, angle, 2 * circle.radius)
      circleInt = circleFrom3Pts(pt1, pt2, pt3)
      if circleInt is None:
         return None
      intPts = QadIntersections.twoCircles(circle, circleInt)
      l1 = QadLine().set(pt1, pt2)
      l2 = QadLine().set(intPts[0], intPts[1])
      intPt = QadIntersections.twoInfinityLines(l1, l2)
      tanPts = QadTangency.fromPointToCircle(intPt, circle)
      for tanPt in tanPts:
         circleTan = circleFrom3Pts(pt1, pt2, tanPt)
         if circleTan is not None:
            circleList.append(circleTan)
   elif dist1 == radius: # il punto1 sulla circonferenza di circle
      # una sola circonferenza avente come centro l'intersezione tra l'asse pt1 e pt2 e la retta
      # passante per il centro di circle e pt1
      axis = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l) # asse di pt1 e pt2      
      l1 = QadLine().set(circle.center, pt1)
      intPt = QadIntersections.twoInfinityLines(axis, l1)
      circleTan = QadCircle().set(intPt, qad_utils.getDistance(pt1, intPt))
      circleList.append(circleTan)
   elif dist2 == radius: # il punto3 é sulla circonferenza di circle
      # una sola circonferenza avente come centro l'intersezione tra l'asse pt1 e pt2 e la retta
      # passante per il centro di circle e pt2
      axis = QadPerpendicularity.getInfinityLinePerpOnMiddleLine(l) # asse di pt1 e pt2      
      l2 = QadLine().set(circle.center, pt2)
      intPt = QadIntersections.twoInfinityLines(axis, l2)
      circleTan = QadCircle().set(intPt, qad_utils.getDistance(pt2, intPt))
      circleList.append(circleTan)
               
   if len(circleList) == 0:
      return None
   
   result = QadCircle()
   minDist = sys.float_info.max
   for circleTan in circleList:        
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle.center)
      if qad_utils.getDistance(circleTan.center, circle.center) < circle.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      dist = qad_utils.getDistance(ptInt, pt)
      
      if dist < minDist: # mediamente più vicino
         minDist = dist
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return result


# ===========================================================================
# circleFrom2IntPtsLineTanPts
# ===========================================================================
def circleFrom2IntPtsLineTanPts(pt1, pt2, line, pt, AllCircles = False):
   """
   crea uno o più cerchi (vedi allCircles) attraverso 2 punti di intersezione e una linea tangente:
   punto1 di intersezione
   punto2 di intersezione
   linea di tangenza (QadLine)
   punto di selezione linea
   il parametro AllCircles se = True fa restituire tutti i cerchi altrimenti solo quello più vicino a pt1 e pt2
   """
   circleList = []
   
   pt1Line = line.getStartPt()
   pt2Line = line.getEndPt()

   A = (pt1.x() * pt1.x()) + (pt1.y() * pt1.y())
   B = (pt2.x() * pt2.x()) + (pt2.y() * pt2.y())

   E = - pt1.x() + pt2.x()
   F = pt1.y() - pt2.y()
   if F == 0:
      if AllCircles == True:
         return circleList
      else:
         return None

   G = (-A + B) / F 
   H = E / F
   
   if pt1Line.x() - pt2Line.x() == 0:
      # la linea é verticale
      e = pt1Line.x()
      I = H * H
      if I == 0:
         if AllCircles == True:
            return circleList
         else:
            return None
      J = (2 * G * H) - (4 * e) + (4 * pt2.x()) + (4 * H * pt2.y())
      K = (G * G) - (4 * e * e) + (4 * B) + (4 * G * pt2.y())
   else:
      # equazione della retta line -> y = dx + e
      d = (pt2Line.y() - pt1Line.y()) / (pt2Line.x() - pt1Line.x())
      e = - d * pt1Line.x() + pt1Line.y()
      C = 4 * (1 + d * d)
      D = 2 * d * e
      d2 = d * d
      I = 1 + (H * H * d2) + 2 * H * d
      if I == 0:
         if AllCircles == True:
            return circleList
         else:
            return None
      J = (2 * d2 * G * H) + (2 * D) + (2 * D * H * d) + (2 * G * d) - (e * C * H) + (pt2.x() * C) + H * pt2.y() * C
      K = (G * G * d2) + (2 * D * G * d) + (D * D) - (C * e * e) - (C * G * e) + (B * C) + (G * pt2.y() * C)
          
   L = (J * J) - (4 * I * K)
   if L < 0:
      if AllCircles == True:
         return circleList
      else:
         return None
         
   a1 = (-J + math.sqrt(L)) / (2 * I)
   b1 = (a1 * H) + G
   c1 = - B - (a1 * pt2.x()) - (b1 * pt2.y())
   center = QgsPointXY()
   center.setX(- (a1 / 2))
   center.setY(- (b1 / 2))
   radius = math.sqrt((a1 * a1 / 4) + (b1 * b1 / 4) - c1)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)
   
   a2 = (-J - math.sqrt(L)) / (2 * I) 
   b2 = (a2 * H) + G
   c2 = - B - (a2 * pt2.x()) - (b2 * pt2.y())
   center.setX(- (a2 / 2))
   center.setY(- (b2 / 2))
   radius = math.sqrt((a2 * a2 / 4) + (b2 * b2 / 4) - c2)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)
   
   if AllCircles == True:
      return circleList
   
   if len(circleList) == 0:
      return None

   result = QadCircle()
   minDist = sys.float_info.max
   for circle in circleList:
      ptInt = QadPerpendicularity.fromPointToInfinityLine(circle.center, line)      
      dist = ptInt.distance(pt)
      
      if dist < minDist: # mediamente più vicino
         minDist = dist
         result.center = circle.center
         result.radius = circle.radius
         
   return result


# ============================================================================
# circleFrom2IntPts1TanPt
# ============================================================================
def circleFrom2IntPts1TanPt(pt1, pt2, geom, pt):
   """
   crea un cerhcio attraverso 2 punti di intersezione ed un oggetto di tangenza:
   punto1 di intersezione
   punto2 di intersezione
   geometria di tangenza (linea, arco o cerchio)
   punto di selezione geometria
   """
   objType = geom.whatIs()

   if objType != "LINE" and objType != "ARC" and objType != "CIRCLE":
      return None
   
   if objType == "ARC": # se è arco lo trasformo in cerchio
      obj = QadCircle().set(geom.center, geom.radius)
      objType = "CIRCLE"
   else:
      obj = geom
   
   if objType == "LINE":
      return circleFrom2IntPtsLineTanPts(pt1, pt2, obj, pt)
   elif objType == "CIRCLE":
      return circleFrom2IntPtsCircleTanPts(pt1, pt2, obj, pt)
            
   return None


# ============================================================================
# circleFrom1IntPt2TanPts
# ============================================================================
def circleFrom1IntPt2TanPts(pt, geom1, pt1, geom2, pt2):
   """
   crea un cerchio attraverso 1 punti di intersezione e 2 oggetti di tangenza:
   punto di intersezione
   geometria1 di tangenza (linea, arco o cerchio)
   punto di selezione geometria1
   geometria2 di tangenza (linea, arco o cerchio)
   punto di selezione geometria2     
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE"):
      return None

   if obj1Type == "ARC": # se è arco lo trasformo in cerchio
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1

   if obj2Type == "ARC": # se è arco lo trasformo in cerchio
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2

   if obj1Type == "LINE":
      if obj2Type == "LINE":
         return circleFrom1IntPtLineLineTanPts(pt, obj1, pt1, obj2, pt2)
      elif obj2Type == "CIRCLE":
         return circleFrom1IntPtLineCircleTanPts(pt, obj1, pt1, obj2, pt2)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         return circleFrom1IntPtLineCircleTanPts(pt, obj2, pt2, obj1, pt1)
      elif obj2Type == "CIRCLE":
         return circleFrom1IntPtCircleCircleTanPts(pt, obj1, pt1, obj2, pt2)
            
   return None


# ===========================================================================
# circleFrom1IntPtLineLineTanPts
# ===========================================================================
def circleFrom1IntPtLineLineTanPts(pt, line1, pt1, line2, pt2, AllCircles = False):
   """
   crea uno o più cerchi (vedi allCircles) attraverso 1 punti di intersezione e due linee tangenti:
   punto di intersezione     
   linea1 di tangenza (QLine)
   punto di selezione linea1
   linea2 di tangenza (QLine)
   punto di selezione linea2
   il parametro AllCircles se = True fa restituire tutti i cerchi e non sono quello più vicino a pt1 e pt2
   """
   # http://www.batmath.it/matematica/a_apollonio/prr.htm
   circleList = []
         
   # verifico se le rette sono parallele
   ptInt = QadIntersections.twoInfinityLines(line1, line2)
   if ptInt is None: # le rette sono parallele
      # Se le rette sono parallele il problema ha soluzioni solo se il punto 
      # é non esterno alla striscia individuata dalle due rette e basta considerare 
      # il simmetrico di A rispetto alla bisettrice della striscia.
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(line2.getStartPt(), line1)
      angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), ptPerp)
      dist = qad_utils.getDistance(line2.getStartPt(), ptPerp)
      pt1ParLine = qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle, dist / 2)
      angle = angle + math.pi / 2
      pt2ParLine = qad_utils.getPolarPointByPtAngle(pt1ParLine, angle, dist)
      l = QadLine().set(pt1ParLine, pt2ParLine)
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(pt, l)      
      dist = qad_utils.getDistance(pt, ptPerp)
      
      # trovo il punto simmetrico
      angle = qad_utils.getAngleBy2Pts(pt, ptPerp)
      ptSymmetric = qad_utils.getPolarPointByPtAngle(pt, angle, dist * 2)
      return circleFrom2IntPtsLineTanPts(pt, ptSymmetric, line1, pt1, AllCircles)
   else: # le rette non sono parallele
      if ptInt == pt:
         return None
      # se il punto é sulla linea1 o sulla linea2
      ptPerp1 = QadPerpendicularity.fromPointToInfinityLine(pt, line1)
      ptPerp2 = QadPerpendicularity.fromPointToInfinityLine(pt, line2)
      if ptPerp1 == pt or ptPerp2 == pt:
         # Se le rette sono incidenti ed il punto appartiene ad una delle due la costruzione
         # é quasi immediata: basta tracciare le bisettrici dei due angoli individuati dalle rette 
         # e la perpendicolare per pt alla retta cui appartiene pt stesso. Si avranno due circonferenze.            
         
         if ptPerp1 == pt: # se il punto é sulla linea1
            angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle, 10)
            Bisector1 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle + math.pi, 10)
            Bisector2 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
            ptPerp = qad_utils.getPolarPointByPtAngle(pt, angle + math.pi / 2, 10)               
         else: # se il punto é sulla linea2
            angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle, 10)
            Bisector1 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            ptLine = qad_utils.getPolarPointByPtAngle(ptInt, angle + math.pi, 10)
            Bisector2 = qad_utils.getBisectorInfinityLine(pt, ptInt, ptLine)
            angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
            ptPerp = qad_utils.getPolarPointByPtAngle(pt, angle + math.pi / 2, 10)
         
         l1 = QadLine().set(Bisector1[0], Bisector1[1])
         l2 = QadLine().set(pt, ptPerp)
         center = QadIntersections.twoInfinityLines(l1, l2)
         
         radius = qad_utils.getDistance(pt, center)
         circleTan = QadCircle()
         circleTan.set(center, radius)
         circleList.append(circleTan)       

         l1.set(Bisector2[0], Bisector2[1])
         center = QadIntersections.twoInfinityLines(l1, l2)
         radius = qad_utils.getDistance(pt, center)
         circleTan = QadCircle()
         circleTan.set(center, radius)
         circleList.append(circleTan)            
      else:         
         # Bisettrice dell'angolo interno del triangolo avente come vertice i punti di intersezione delle rette
         Bisector = qad_utils.getBisectorInfinityLine(ptPerp1, ptInt, ptPerp2)
         l = QadLine().set(Bisector[0], Bisector[1])
         ptPerp = QadPerpendicularity.fromPointToInfinityLine(pt, l)
         dist = qad_utils.getDistance(pt, ptPerp)
         
         # trovo il punto simmetrico
         angle = qad_utils.getAngleBy2Pts(pt, ptPerp)
         ptSymmetric = qad_utils.getPolarPointByPtAngle(pt, angle, dist * 2)
         return circleFrom2IntPtsLineTanPts(pt, ptSymmetric, line1, pt1, AllCircles)

   if AllCircles == True:
      return circleList
               
   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # svuoto la lista
               
      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line1)
      AvgList.append(qad_utils.getDistance(ptInt, pt1))

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line2)
      AvgList.append(qad_utils.getDistance(ptInt, pt2))
               
      currAvg = qad_utils.numericListAvg(AvgList)           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return result


# ===============================================================================
# solveCircleTangentTo2LinesAndCircle
# ===============================================================================
def solveCircleTangentTo2LinesAndCircle(line1, line2, circle, s1, s2):
   '''
   Trova i due cerchi tangenti a due rette e un cerchio (sarebbero 8 cerchi che si trovano con le 
   4 combinazioni di s1, s2 che assumo valore -1 o 1)
   e restituisce quello più vicino a pt
   '''
   circleList = []
   # http://www.batmath.it/matematica/a_apollonio/rrc.htm

   # Questa costruzione utilizza una particolare trasformazione geometrica, che alcuni chiamano dilatazione parallela:
   # si immagina che il raggio r del cerchio dato c si riduca a zero (il cerchio é ridotto al suo centro),
   # mentre le rette rimangono parallele con distanze dal centro del cerchio che si é ridotto a zero aumentate o
   # diminuite di r. Si é così ricondotti al caso di un punto e due rette e si può applicare una delle tecniche viste
   # in quel caso.  

   line1Par = []
   angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
   line1Par.append(qad_utils.getPolarPointByPtAngle(line1[0], angle + math.pi / 2, circle.radius * s1))
   line1Par.append(qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle + math.pi / 2, circle.radius * s1))

   line2Par = []
   angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
   line2Par.append(qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle + math.pi / 2, circle.radius * s2))
   line2Par.append(qad_utils.getPolarPointByPtAngle(line2.getEndPt(), angle + math.pi / 2, circle.radius * s2))
   
   circleList = circleFrom1IntPtLineLineTanPts(circle.center, line1Par, None, line2Par, None, True)

   for circleTan in circleList:
      ptPerp = qad_utils.getPerpendicularPointOnInfinityLine(line1.getStartPt(), line1.getEndPt(), circleTan.center)
      circleTan.radius = qad_utils.getDistance(ptPerp, circleTan.center)
   
   return circleList


# ============================================================================
# circleFromLineLineCircleTanPts
# ============================================================================
def circleFromLineLineCircleTanPts(line1, pt1, line2, pt2, circle, pt3):
   """
   crea un cerchio attraverso tre linee:
   linea1 di tangenza (QadLine)
   punto di selezione linea1
   linea2 di tangenza (QadLine)
   punto di selezione linea2
   cerchio di tangenza (oggetto QadCircle)
   punto di selezione cerchio
   """
   circleList = []
   
   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle, -1, -1))         
   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle, -1,  1))
   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle,  1, -1))
   circleList.extend(solveCircleTangentTo2LinesAndCircle(line1, line2, circle,  1,  1))

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # svuoto la lista
               
      ptInt = qad_utils.getPerpendicularPointOnInfinityLine(line1.getStartPt(), line1.getEndPt(), circleTan.center)
      AvgList.append(ptInt.distance(pt1))

      ptInt = qad_utils.getPerpendicularPointOnInfinityLine(line2.getStartPt(), line2.getEndPt(), circleTan.center)
      AvgList.append(ptInt.distance(pt2))
      
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle.center)
      if circleTan.center.distance(circle.center) < circle.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt3))
               
      currAvg = qad_utils.numericListAvg(AvgList)           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return True


# ============================================================================
# circleFrom3TanPts
# ============================================================================
def circleFrom3TanPts(geom1, pt1, geom2, pt2, geom3, pt3):
   """
   crea un cerchio attraverso tre oggetti di tangenza per le estremità del diametro:
   geometria 1 di tangenza (linea, arco o cerchio)
   punto di selezione geometria 1
   geometria 2 di tangenza (linea, arco o cerchio)
   punto di selezione geometria 2
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()
   obj3Type = geom3.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE") or \
      (obj3Type != "LINE" and obj3Type != "ARC" and obj3Type != "CIRCLE"):
      return None
   
   if obj1Type == "ARC": # se è arco lo trasformo in cerchio
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1

   if obj2Type == "ARC": # se è arco lo trasformo in cerchio
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2

   if obj3Type == "ARC": # se è arco lo trasformo in cerchio
      obj3 = QadCircle().set(geom3.center, geom3.radius)
      obj3Type = "CIRCLE"
   else:
      obj3 = geom3
   
   if obj1Type == "LINE":
      if obj2Type == "LINE":
         if obj3Type == "LINE":
            return circleFromLineLineLineTanPts(obj1, pt1, obj2, pt2, obj3, pt3)
         elif obj3Type == "CIRCLE":
            return circleFromLineLineCircleTanPts(obj1, pt1, obj2, pt2, obj3, pt3)
      elif obj2Type == "CIRCLE":
         if obj3Type == "LINE":
            return circleFromLineLineCircleTanPts(obj1, pt1, obj3, pt3, obj2, pt2)
         elif obj3Type == "CIRCLE":
            return circleFromLineCircleCircleTanPts(obj1, pt1, obj2, pt2, obj3, pt3)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         if obj3Type == "LINE":
            return circleFromLineLineCircleTanPts(obj2, pt2, obj3, pt3, obj1, pt1)
         elif obj3Type == "CIRCLE":
            return circleFromLineCircleCircleTanPts(obj2, pt2, obj1, pt1, obj3, pt3)
      elif obj2Type == "CIRCLE":
         if obj3Type == "LINE":
            return circleFromLineCircleCircleTanPts(obj3, pt3, obj1, pt1, obj2, pt2)
         elif obj3Type == "CIRCLE":
            return circleFromCircleCircleCircleTanPts(obj1, pt1, obj2, pt2, obj3, pt3)
            
   return None
            

# ============================================================================
# circleFromLineLineLineTanPts
# ============================================================================
def circleFromLineLineLineTanPts(line1, pt1, line2, pt2, line3, pt3):
   """
   Crea un cerchio attraverso tre linee:
   linea1 di tangenza (QadLine)
   punto di selezione linea1
   linea2 di tangenza (QadLine)
   punto di selezione linea2
   linea3 di tangenza (QadLine)
   punto di selezione linea3
   """
   circleList = []
   
   # Punti di intersezione delle rette (line1, line2, line3)
   ptInt1 = QadIntersections.twoInfinityLines(line1, line2)
   ptInt2 = QadIntersections.twoInfinityLines(line2, line3)
   ptInt3 = QadIntersections.twoInfinityLines(line3, line1)

   # tre rette parallele
   if (ptInt1 is None) and (ptInt2 is None):
      return circleList
      
   if (ptInt1 is None): # la linea1 e linea2 sono parallele
      circleList.extend(circleFrom2ParLinesLineTanPts(line1, line2, line3))        
   elif (ptInt2 is None): # la linea2 e linea3 sono parallele
      circleList.extend(circleFrom2ParLinesLineTanPts(line2, line3, line1))        
   elif (ptInt3 is None): # la linea3 e linea1 sono parallele
      circleList.extend(circleFrom2ParLinesLineTanPts(line3, line1, line2))        
   else:
      # Bisettrici degli angoli interni del triangolo avente come vertici i punti di intersezione delle rette
      Bisector123 = qad_utils.getBisectorInfinityLine(ptInt1, ptInt2, ptInt3)
      Bisector231 = qad_utils.getBisectorInfinityLine(ptInt2, ptInt3, ptInt1)
      Bisector312 = qad_utils.getBisectorInfinityLine(ptInt3, ptInt1, ptInt2)
      # Punto di intersezione delle bisettrici = centro delle circonferenza inscritta al triangolo
      l1 = QadLine().set(Bisector123[0], Bisector123[1])
      l2 = QadLine().set(Bisector231[0], Bisector231[1])
      center = QadIntersections.twoInfinityLines(l1, l2)
      
      # Perpendicolari alle rette line1 passanti per il centro della circonferenza inscritta
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, line1)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)
      
      # Bisettrici degli angoli esterni del triangolo
      angle = qad_utils.getAngleBy2Pts(Bisector123[0], Bisector123[1]) + math.pi / 2
      Bisector123 = QadLine().set(ptInt2, qad_utils.getPolarPointByPtAngle(ptInt2, angle, 10))
      
      angle = qad_utils.getAngleBy2Pts(Bisector231[0], Bisector231[1]) + math.pi / 2
      Bisector231 = QadLine().set(ptInt3, qad_utils.getPolarPointByPtAngle(ptInt3, angle, 10))

      angle = qad_utils.getAngleBy2Pts(Bisector312[0], Bisector312[1]) + math.pi / 2
      Bisector312 = QadLine().set(ptInt1, qad_utils.getPolarPointByPtAngle(ptInt1, angle, 10))
      
      # Punti di intersezione delle bisettrici = centro delle circonferenze ex-inscritte
      center = QadIntersections.twoInfinityLines(Bisector123, Bisector231)
      l = QadLine().set(ptInt2, ptInt3)
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, l)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)
      
      center = QadIntersections.twoInfinityLines(Bisector231, Bisector312)
      l.set(ptInt3, ptInt1)
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, l)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)

      center = QadIntersections.twoInfinityLines(Bisector312, Bisector123)
      l.set(ptInt1, ptInt2)
      ptPer = QadPerpendicularity.fromPointToInfinityLine(center, l)
      radius = center.distance(ptPer)
      circle = QadCircle()
      circle.set(center, radius)
      circleList.append(circle)
   
   if len(circleList) == 0:
      return None
   
   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # svuoto la lista

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line1)
      AvgList.append(ptInt.distance(pt1))

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line2)
      AvgList.append(ptInt.distance(pt2))

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line3)
      AvgList.append(ptInt.distance(pt3))

      currAvg = qad_utils.numericListAvg(AvgList)           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return result


# ===========================================================================
# circleFrom2ParLinesLineTanPts
# ===========================================================================
def circleFrom2ParLinesLineTanPts(parLine1, parLine2, line3):
   """
   Crea due cerchi attraverso 2 linee parallele e una terza linea non parallela:
   linea1 di tangenza (QadLine) parallela a linea2
   linea2 di tangenza (QadLine) parallela a linea1
   linea3 di tangenza (QadLine)
   """
   circleList = []

   ptInt2 = QadIntersections.twoInfinityLines(parLine2, line3)
   ptInt3 = QadIntersections.twoInfinityLines(line3, parLine1)

   if parLine1.getStartPt() == ptInt3:
      pt = parLine1.getEndPt()
   else:
      pt = parLine1.getStartPt()
   Bisector123 = qad_utils.getBisectorInfinityLine(pt, ptInt2, ptInt3)
   
   if parLine2.getStartPt() == ptInt2:
      pt = parLine2.getEndPt()
   else:
      pt = parLine2.getStartPt()
   Bisector312 = qad_utils.getBisectorInfinityLine(pt, ptInt3, ptInt2)
   
   # Punto di intersezione delle bisettrici = centro delle circonferenza
   center = qad_utils.getIntersectionPointOn2InfinityLines(Bisector123[0], Bisector123[1], \
                                                           Bisector312[0], Bisector312[1])
   ptPer = QadPerpendicularity.fromPointToInfinityLine(center, parLine1)
   radius = center.distance(ptPer)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)
      
   # Bisettrici degli angoli esterni
   Bisector123 = Bisector123 + math.pi / 2
   Bisector312 = Bisector312 + math.pi / 2        
   # Punto di intersezione delle bisettrici = centro delle circonferenza
   center = qad_utils.getIntersectionPointOn2InfinityLines(Bisector123[0], Bisector123[1], \
                                                           Bisector312[0], Bisector312[1])
   ptPer = QadPerpendicularity.fromPointToInfinityLine(center, parLine1)
   radius = center.distance(ptPer)
   circle = QadCircle()
   circle.set(center, radius)
   circleList.append(circle)

   return circleList
   
   
# ============================================================================
# circleFromLineCircleCircleTanPts
# ============================================================================
def circleFromLineCircleCircleTanPts(line, pt, circle1, pt1, circle2, pt2):
   """
   setta le caratteristiche del cerchio attraverso tre linee:
   linea di tangenza (QadLine)
   punto di selezione linea
   cerchio1 di tangenza (oggetto QadCircle)
   punto di selezione cerchio1
   cerchio2 di tangenza (oggetto QadCircle)
   punto di selezione cerchio2
   """
   circleList = []
   
   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2, -1, -1))
   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2, -1,  1))
   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2,  1, -1))
   circleList.extend(solveCircleTangentToLineAnd2Circles(line, circle1, circle2,  1,  1))

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # svuoto la lista

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line)
      AvgList.append(ptInt.distance(t))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle1.center)
      if circleTan.center.distance(circle1.center) < circle1.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt1))
      
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if circleTan.center.distance(circle2.center) < circle2.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt2))
               
      currAvg = qad_utils.numericListAvg(AvgList)           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return result
            

# ============================================================================
# circleFromCircleCircleCircleTanPts
# ============================================================================
def circleFromCircleCircleCircleTanPts(circle1, pt1, circle2, pt2, circle3, pt3):
   """
   Crea un cerchio attraverso tre cerchi tangenti:
   cerchio1 di tangenza (oggetto QadCircle)
   punto di selezione cerchio1
   cerchio2 di tangenza (oggetto QadCircle)
   punto di selezione cerchio2
   cerchio3 di tangenza (oggetto QadCircle)
   punto di selezione cerchio3
   """
   circleList = []
   circle = solveApollonius(circle1, circle2, circle3, -1, -1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3, -1, -1,  1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3, -1,  1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3, -1,  1,  1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1, -1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1, -1,  1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1,  1, -1)
   if circle is not None:
      circleList.append(circle)
   circle = solveApollonius(circle1, circle2, circle3,  1,  1,  1)
   if circle is not None:
      circleList.append(circle)
   
   if len(circleList) == 0:
      return None
   
   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # svuoto la lista
               
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle1.center)
      if circleTan.center.distance(circle1.center) < circle1.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt1))
   
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if circleTan.center.distance(circle2.center) < circle2.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt2))
   
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle3.center)
      if circleTan.center.distance(circle3.center) < circle3.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(ptInt.distance(pt3))
      
      currAvg = qad_utils.numericListAvg(AvgList)           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return result
   
   
# ===========================================================================
# circleFrom1IntPtLineCircleTanPts
# ===========================================================================
def circleFrom1IntPtLineCircleTanPts(pt, line1, pt1, circle2, pt2, AllCircles = False):
   """
   crea uno o più cerchi (vedi AllCircles) attraverso 1 punto di intersezione, 1 linea e 1 cerchio tangenti:
   punto di intersezione     
   linea di tangenza (QadLine)
   punto di selezione linea
   cerchio di tangenza (QadLine)
   punto di selezione cerchio
   il parametro AllCircles se = True fa restituire tutti i cerchi e non sono quello più vicino a pt1 e pt2
   """
   # http://www.batmath.it/matematica/a_apollonio/prc.htm
   circleList = []
   
   # Sono dati un cerchio circle2, un punto pt ed una retta line1 nell'ipotesi che pt
   # non stia nè sulla retta line1 nè sul circolo.
   # Si vogliono trovare le circonferenze passanti per il punto e tangenti alla retta e al cerchio dato.
   # Il problema si può risolvere facilmente utilizzando un'inversione di centro pt e raggio qualunque.
   # Trovate le circonferenze inverse della retta data e del circolo dato, se ne trovano le tangenti comuni.
   # Le inverse di queste tangenti comuni sono le circonferenze cercate. 

   if line1.getYOnInfinityLine(pt.x()) == pt.y() or \
      qad_utils.getDistance(pt, circle2.center) == circle2.radius:
      if AllCircles == True:
         return circleList
      else:
         return None
   
   c = QadCircle()
   c.set(pt, 10)
   
   circularInvLine = getCircularInversionOfLine(c, line1)
   circularInvCircle = getCircularInversionOfCircle(c, circle2)
   tangents = QadTangency.twoCircles(circularInvCircle, circularInvLine)
   for tangent in tangents:
      circleList.append(getCircularInversionOfLine(c, tangent))
      
   if AllCircles == True:
      return circleList

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # svuoto la lista

      ptInt = QadPerpendicularity.fromPointToInfinityLine(circleTan.center, line1)
      AvgList.append(qad_utils.getDistance(ptInt, pt1))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if qad_utils.getDistance(circleTan.center, circle2.center) < circle2.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(qad_utils.getDistance(ptInt, pt2))
               
      currAvg = qad_utils.numericListAvg(AvgList)           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return result


# ===========================================================================
# circleFrom1IntPtCircleCircleTanPts
# ===========================================================================
def circleFrom1IntPtCircleCircleTanPts(pt, circle1, pt1, circle2, pt2):
   """
   Crea dei cerchi attraverso 1 punto di intersezione, 2 cerchi tangenti:
   punto di intersezione     
   cerchio1 di tangenza (oggetto QadCircle)
   punto di selezione cerchio1
   cerchio2 di tangenza (oggetto QadCircle)
   punto di selezione cerchio2
   """
   # http://www.batmath.it/matematica/a_apollonio/prc.htm
   circleList = []

   # Sono dati un punto pt e due circonferenze circle1 e circle2;
   # si devono determinare le circonferenze passanti per pt e tangenti alle due circonferenze.
   # Proponiamo una costruzione che utilizza l'inversione, in quanto ci pare la più elegante.
   # In realtà si potrebbe anche fare una costruzione utilizzando i centri di omotetia dei due cerchi dati
   # ma, nella sostanza, é solo un modo per mascherare l'uso dell'inversione.
   # Si considera un circolo di inversione di centro pt e raggio qualunque.
   # Si determinano i circoli inversi dei due circoli dati e le loro tangenti comuni.
   # Le circonferenze inverse di queste tangenti comuni sono quelle che soddisfano il problema. 

   c = QadCircle()
   c.set(pt, 10)
   
   circularInvCircle1 = getCircularInversionOfCircle(c, circle1)
   circularInvCircle2 = getCircularInversionOfCircle(c, circle2)
   tangents = QadTangency.twoCircles(circularInvCircle1, circularInvCircle2)
   for tangent in tangents:
      circleList.append(getCircularInversionOfLine(c, tangent))

   if len(circleList) == 0:
      return None

   result = QadCircle()
   AvgList = []
   Avg = sys.float_info.max
   for circleTan in circleList:
      del AvgList[:] # svuoto la lista
               
      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle1.center)
      if qad_utils.getDistance(circleTan.center, circle1.center) < circle1.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(qad_utils.getDistance(ptInt, pt1))

      angle = qad_utils.getAngleBy2Pts(circleTan.center, circle2.center)
      if qad_utils.getDistance(circleTan.center, circle2.center) < circle2.radius: # cerchio interno
         angle = angle + math.pi / 2
      ptInt = qad_utils.getPolarPointByPtAngle(circleTan.center, angle, circleTan.radius)
      AvgList.append(qad_utils.getDistance(ptInt, pt2))
               
      currAvg = qad_utils.numericListAvg(AvgList)           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result.center = circleTan.center
         result.radius = circleTan.radius
         
   return result


# ============================================================================
# circleFromDiamEndsPtTanPt
# ============================================================================
def circleFromDiamEndsPtTanPt(startPt, geom, pt):
   """
   Crea un cerchio attraverso un punto di estremità del diametro e
   un oggetto di tangenza per l'altra estremità :
   punto iniziale
   geometria 1 di tangenza (linea, arco o cerchio)
   punto di selezione geometria 1
   """
   objype = geom.whatIs()

   if (objType != "LINE" and objType != "ARC" and objType != "CIRCLE"): return None
   
   if objType == "ARC": # se è arco lo trasformo in cerchio
      obj = QadCircle().set(geom.center, geom.radius)
      objType = "CIRCLE"
   else:
      obj = geom
   
   if objType == "LINE":
      ptPer = QadPerpendicularity.fromPointToInfinityLine(startPt, obj)
      return QadCircle().fromDiamEnds(startPt, ptPer)
   elif objType == "CIRCLE":
      l = QadLine().set(startPt, obj.center)
      intPts = QadIntersections.infinityLineWithCircle(l, obj)
      # scelgo il punto più vicino al punto pt
      ptTan = qad_utils.getNearestPoints(pt, ptIntList)[0]
      return QadCircle().fromDiamEnds(startPt, ptTan)


# ============================================================================
# circleFromDiamEnds2TanPts
# ============================================================================
def circleFromDiamEnds2TanPts(geom1, pt1, geom2, pt2):
   """
   Creo un cerchio attraverso due oggetto di tangenza per le estremità del diametro:
   geometria1 di tangenza (linea, arco o cerchio)
   punto di selezione geometria1
   geometria2 di tangenza (linea, arco o cerchio)
   punto di selezione geometria2
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE"):
      return None
   
   if obj1Type == "ARC": # se è arco lo trasformo in cerchio
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1
   
   if obj2Type == "ARC": # se è arco lo trasformo in cerchio
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2
   
   if obj1Type == "LINE":
      if obj2Type == "LINE":
         return None # Il diametro non può essere tangente a due linee
      elif obj2Type == "CIRCLE":
         return circleFromLineCircleTanPts(obj1, obj2, pt2)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         return circleFromLineCircleTanPts(obj2, obj1, pt1)
      elif obj2Type == "CIRCLE":
         return circleFromCircleCircleTanPts(obj1, pt1, obj2, pt2)
            
   return None
            

# ============================================================================
# circleFromLineCircleTanPts
# ============================================================================
def circleFromLineCircleTanPts(line, circle, ptCircle):
   """
   Creo un cerchio attraverso una linea, un cerchio di tangenza:
   linea di tangenza (QadLine)
   cerchio di tangenza (oggetto QadCircle)
   punto di selezione cerchio
   """
   ptPer = QadPerpendicularity.fromPointToInfinityLine(circle.center, line)
   tanPoints = []
   tanPoints.append(qad_utils.getPolarPointBy2Pts(circle.center, ptPer, circle.radius))
   tanPoints.append(qad_utils.getPolarPointBy2Pts(circle.center, ptPer, -circle.radius))
   # scelgo il punto più vicino al punto pt
   ptTan = qad_utils.getNearestPoints(ptCircle, tanPoints)[0]
   return QadCircle().fromDiamEnds(ptPer, ptTan)


# ============================================================================
# circleFromCircleCircleTanPts
# ============================================================================
def circleFromCircleCircleTanPts(circle1, pt1, circle2, pt2):
   """
   Crea un cerchio attraverso due cerchi di tangenza:
   cerchio1 di tangenza (oggetto QadCircle)
   punto di selezione cerchio1
   cerchio2 di tangenza (oggetto QadCircle)
   punto di selezione cerchio2
   """
   l = QadLine().set(circle1.center, circle2.center)
   ptIntList = QadIntersections.infinityLineWithCircle(l, circle1)
   # scelgo il punto più vicino al punto pt1
   ptTan1 = qad_utils.getNearestPoints(pt1, ptIntList)[0]
   
   ptIntList = QadIntersections.infinityLineWithCircle(l, circle2)
   # scelgo il punto più vicino al punto pt2
   ptTan2 = qad_utils.getNearestPoints(pt2, ptIntList)[0]
   
   return QadCircle().fromDiamEnds(ptTan1, ptTan2)


# ============================================================================
# circleFrom2TanPtsRadius
# ============================================================================
def circleFrom2TanPtsRadius(geom1, pt1, geom2, pt2, radius):
   """
   Crea un cerchio attraverso 2 oggetti di tangenza e un raggio:
   geometria1 di tangenza (linea, arco o cerchio)
   punto di selezione geometria1
   oggetto2 di tangenza (linea, arco o cerchio)
   punto di selezione geometria2
   raggio
   """
   obj1Type = geom1.whatIs()
   obj2Type = geom2.whatIs()

   if (obj1Type != "LINE" and obj1Type != "ARC" and obj1Type != "CIRCLE") or \
      (obj2Type != "LINE" and obj2Type != "ARC" and obj2Type != "CIRCLE"):
      return False
   
   if obj1Type == "ARC": # se è arco lo trasformo in cerchio
      obj1 = QadCircle().set(geom1.center, geom1.radius)
      obj1Type = "CIRCLE"
   else:
      obj1 = geom1
   
   if obj2Type == "ARC": # se è arco lo trasformo in cerchio
      obj2 = QadCircle().set(geom2.center, geom2.radius)
      obj2Type = "CIRCLE"
   else:
      obj2 = geom2

   if obj1Type == "LINE":
      if obj2Type == "LINE":
         return circleFromLineLineTanPtsRadius(obj1, pt1, obj2, pt2, radius)
      elif obj2Type == "CIRCLE":
         return circleFromLineCircleTanPtsRadius(obj1, pt1, obj2, pt2, radius)
   elif obj1Type == "CIRCLE":
      if obj2Type == "LINE":
         return circleFromLineCircleTanPtsRadius(obj2, pt2, obj1, pt1, radius)
      elif obj2Type == "CIRCLE":
         return circleFromCircleCircleTanPtsRadius(obj1, pt1, obj2, pt2, radius)
            
   return None


# ============================================================================
# circleFromLineLineTanPtsRadius
# ============================================================================
def circleFromLineLineTanPtsRadius(line1, pt1, line2, pt2, radius):
   """
   Crea un cerchio attraverso due linee di tangenza e un raggio:
   linea1 di tangenza (QadLine)
   punto di selezione linea1
   linea2 di tangenza (QadLine)
   punto di selezione linea2
   raggio
   """
   # calcolo il punto medio tra i due punti di selezione
   ptMiddle = qad_utils.getMiddlePoint(pt1, pt2)

   # verifico se le rette sono parallele
   ptInt = QadIntersections.twoInfinityLines(line1, line2)
   if ptInt is None: # le rette sono parallele
      ptPer = QadPerpendicularity.fromPointToInfinityLine(ptMiddle, line1)
      if qad_utils.doubleNear(radius, qad_utils.getDistance(ptPer, ptMiddle)):
         return QadCircle().set(ptMiddle, radius)
      else:
         return None
   
   # angolo linea1
   angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt())
   # retta parallela da un lato della linea1 distante radius
   angle = angle + math.pi / 2
   pt1Par1Line1 = qad_utils.getPolarPointByPtAngle(line1.getStartPt(), angle, radius)
   pt2Par1Line1 = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, radius)
   # retta parallela dall'altro lato della linea1 distante radius
   angle = angle - math.pi
   pt1Par2Line1 = qad_utils.getPolarPointByPtAngle(line1.getStartPt(), angle, radius)
   pt2Par2Line1 = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, radius)

   # angolo linea2
   angle = qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt())
   # retta parallela da un lato della linea2 distante radius
   angle = angle + math.pi / 2
   pt1Par1Line2 = qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle, radius)
   pt2Par1Line2 = qad_utils.getPolarPointByPtAngle(line2.getEndPt(), angle, radius)
   # retta parallela dall'altro lato della linea2 distante radius
   angle = angle - math.pi
   pt1Par2Line2 = qad_utils.getPolarPointByPtAngle(line2.getStartPt(), angle, radius)
   pt2Par2Line2 = qad_utils.getPolarPointByPtAngle(line2.getEndPt(), angle, radius)

   # calcolo le intersezioni
   ptIntList = []   
   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par1Line1, pt2Par1Line1, \
                                                          pt1Par1Line2, pt2Par1Line2)
   ptIntList.append(ptInt)
   
   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par1Line1, pt2Par1Line1, \
                                                          pt1Par2Line2, pt2Par2Line2)
   ptIntList.append(ptInt)

   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par2Line1, pt2Par2Line1, \
                                                          pt1Par1Line2, pt2Par1Line2)
   ptIntList.append(ptInt)

   ptInt = qad_utils.getIntersectionPointOn2InfinityLines(pt1Par2Line1, pt2Par2Line1, \
                                                          pt1Par2Line2, pt2Par2Line2)
   ptIntList.append(ptInt)

   # scelgo il punto più vicino al punto medio
   center = qad_utils.getNearestPoints(ptMiddle, ptIntList)[0]
   return QadCircle().set(center, radius)
            

# ============================================================================
# circleFromLineCircleTanPtsRadius
# ============================================================================
def circleFromLineCircleTanPtsRadius(line, ptLine, circle, ptCircle, radius):
   """
   Crea un cerchio attraverso una linea, un cerchio di tangenza e un raggio:
   linea di tangenza (QadLine)
   punto di selezione linea
   cerchio di tangenza (oggetto QadCircle)
   punto di selezione cerchio
   raggio
   """
   # calcolo il punto medio tra i due punti di selezione
   ptMiddle = qad_utils.getMiddlePoint(ptLine, ptCircle)

   # angolo linea1
   angle = qad_utils.getAngleBy2Pts(line.getStartPt(), line.getEndPt())
   # retta parallela da un lato della linea1 distante radius
   angle = angle + math.pi / 2
   pt1Par1Line = qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle, radius)
   pt2Par1Line = qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle, radius)
   # retta parallela dall'altro lato della linea1 distante radius
   angle = angle - math.pi
   pt1Par2Line = qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle, radius)
   pt2Par2Line = qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle, radius)
   
   # creo un cerchio con un raggio + grande
   circleTan = QadCircle()
   circleTan.set(circle.center, circle.radius + radius)
   
   l = QadLine().set(pt1Par1Line, pt2Par1Line)
   ptIntList = QadIntersections.infinityLineWithCircle(l, circleTan)
   
   l.set(pt1Par2Line, pt2Par2Line)
   ptIntList2 = QadIntersections.infinityLineWithCircle(l, circleTan)
   
   ptIntList.extend(ptIntList2)

   if len(ptIntList) == 0: # nessuna intersezione
      return None
   
   # scelgo il punto più vicino al punto medio
   center = qad_utils.getNearestPoints(ptMiddle, ptIntList)[0]
   return QadCircle().set(center, radius)


# ============================================================================
# circleFromCircleCircleTanPtsRadius
# ============================================================================
def circleFromCircleCircleTanPtsRadius(circle1, pt1, circle2, pt2, radius):
   """
   Crea un cerchio attraverso due cerchi di tangenza e un raggio:
   cerchio1 di tangenza (oggetto QadCircle)
   punto di selezione cerchio1
   cerchio2 di tangenza (oggetto QadCircle)
   punto di selezione cerchio2
   raggio
   """
   # calcolo il punto medio tra i due punti di selezione
   ptMiddle = qad_utils.getMiddlePoint(pt1, pt2)
   
   # creo due cerchi con un raggio + grande
   circle1Tan = QadCircle()
   circle1Tan.set(circle1.center, circle1.radius + radius)
   circle2Tan = QadCircle()
   circle2Tan.set(circle2.center, circle2.radius + radius)
   ptIntList = QadIntersections.twoCircles(circle1Tan, circle2Tan)

   if len(ptIntList) == 0: # nessuna intersezione
      return None
   
   # scelgo il punto più vicino al punto medio
   center = qad_utils.getNearestPoints(ptMiddle, ptIntList)[0]
   return QadCircle().set(center, radius)


# ===============================================================================
# solveCircleTangentToLineAnd2Circles
# ===============================================================================
def solveCircleTangentToLineAnd2Circles(line, circle1, circle2, s1, s2):
   '''
   Trova i due cerchi tangenti a una retta e due cerchi (sarebbero 8 cerchi che si trovano con le 
   4 combinazioni di s1, s2 che assumo valore -1 o 1)
   e restituisce quello più vicino a pt
   '''
   # http://www.batmath.it/matematica/a_apollonio/rcc.htm

   # Il modo più semplice per risolvere questo problema é quello di utilizzare una particolare 
   # trasformazione geometrica, che alcuni chiamano dilatazione parallela: si immagina che il raggio r 
   # del più piccolo dei cerchi in questione si riduca a zero (il cerchio é ridotto al suo centro), 
   # mentre le rette (risp. gli altri cerchi) rimangono parallele (risp. concentrici) con distanze
   # dal centro del cerchio che si é ridotto a zero (rispettivamente con raggi dei cerchi) aumentati o 
   # diminuiti di r. 
   # Se applichiamo questa trasformazione al nostro caso, riducendo a zero il raggio del cerchio più piccolo
   # (o di uno dei due se hanno lo stesso raggio) ci ritroveremo con un punto, un cerchio e una retta:
   # trovate le circonferenze passanti per il punto e tangenti alla retta e al cerchio (nel modo già noto)
   # potremo applicare la trasformazione inversa della dilatazione parallela precedente per determinare
   # le circonferenze richieste.
   if circle1.radius <= circle2.radius:
      smallerCircle = circle1
      greaterCircle = circle2
   else:
      smallerCircle = circle2
      greaterCircle = circle1
   
   linePar = []
   angle = qad_utils.getAngleBy2Pts(line[0], line[1])
   linePar.append(qad_utils.getPolarPointByPtAngle(line[0], angle + math.pi / 2, smallerCircle.radius * s1))
   linePar.append(qad_utils.getPolarPointByPtAngle(line[1], angle + math.pi / 2, smallerCircle.radius * s1))

   circlePar = QadCircle(greaterCircle)
   circlePar.radius = circlePar.radius + smallerCircle.radius * s1
   
   circleList = circleFrom1IntPtLineCircleTanPts(smallerCircle.center, linePar, None, circlePar, None, True)

   for circleTan in circleList:
      ptPerp = qad_utils.getPerpendicularPointOnInfinityLine(line[0], line[1], circleTan.center)
      circleTan.radius = qad_utils.getDistance(ptPerp, circleTan.center)
   
   return circleList


# ===============================================================================
# solveApollonius
# ===============================================================================
def solveApollonius(c1, c2, c3, s1, s2, s3):
   '''
   >>> solveApollonius((0, 0, 1), (4, 0, 1), (2, 4, 2), 1,1,1)
   Circle(x=2.0, y=2.1, r=3.9)
   >>> solveApollonius((0, 0, 1), (4, 0, 1), (2, 4, 2), -1,-1,-1)
   Circle(x=2.0, y=0.8333333333333333, r=1.1666666666666667) 
   Trova il cerchio tangente a tre cerchi (sarebbero 8 cerchi che si trovano con le 
   8 combinazioni di s1, s2, s3 che assumo valore -1 o 1)
   '''
   x1 = c1.center.x()
   y1 = c1.center.y()
   r1 = c1.radius
   x2 = c2.center.x()
   y2 = c2.center.y()
   r2 = c2.radius
   x3 = c3.center.x()
   y3 = c3.center.y()
   r3 = c3.radius
   
   v11 = 2*x2 - 2*x1
   v12 = 2*y2 - 2*y1
   v13 = x1*x1 - x2*x2 + y1*y1 - y2*y2 - r1*r1 + r2*r2
   v14 = 2*s2*r2 - 2*s1*r1
   
   v21 = 2*x3 - 2*x2
   v22 = 2*y3 - 2*y2
   v23 = x2*x2 - x3*x3 + y2*y2 - y3*y3 - r2*r2 + r3*r3
   v24 = 2*s3*r3 - 2*s2*r2
   
   if v11 == 0:
      return None
   
   w12 = v12/v11
   w13 = v13/v11
   w14 = v14/v11
   
   if v21 == 0:
      return None
   
   w22 = v22/v21-w12
   w23 = v23/v21-w13
   w24 = v24/v21-w14
   
   if w22 == 0:
      return None
   
   P = -w23/w22
   Q = w24/w22
   M = -w12*P-w13
   N = w14 - w12*Q
   
   a = N*N + Q*Q - 1
   b = 2*M*N - 2*N*x1 + 2*P*Q - 2*Q*y1 + 2*s1*r1
   c = x1*x1 + M*M - 2*M*x1 + P*P + y1*y1 - 2*P*y1 - r1*r1
   
   # Find a root of a quadratic equation. This requires the circle centers not to be e.g. colinear
   if a == 0:
      return None
   D = (b * b) - (4 * a * c)
   
   # se D é così vicino a zero 
   if qad_utils.doubleNear(D, 0.0):
      D = 0
   elif D < 0: # non si può fare la radice quadrata di un numero negativo
      return None
   
   rs = (-b-math.sqrt(D))/(2*a)
   
   xs = M+N*rs
   ys = P+Q*rs
   
   center = QgsPointXY(xs, ys)
   circle = QadCircle().set(center, rs)
   return circle


# ===============================================================================
# getCircularInversionOfPoint
# ===============================================================================
def getCircularInversionOfPoint(circleRef, pt):
   """
   la funzione ritorna l'inversione circolare di un punto
   """
   dist = qad_utils.getDistance(circleRef.center, pt)
   angle = qad_utils.getAngleBy2Pts(circleRef.center, pt)
   circInvDist = circleRef.radius * circleRef.radius / dist
   return qad_utils.getPolarPointByPtAngle(circleRef.center, angle, circInvDist)


# ===============================================================================
# getCircularInversionOfLine
# ===============================================================================
def getCircularInversionOfLine(circleRef, line):
   """
   la funzione ritorna l'inversione circolare di una linea (che é un cerchio)
   """
   angleLine = qad_utils.getAngleBy2Pts(line.getStartPt(), line.getEndPt())
   ptNearestLine = QadPerpendicularity.fromPointToInfinityLine(circleRef.center, line)
   dist = qad_utils.getDistance(circleRef.center, ptNearestLine)

   pt1 = getCircularInversionOfPoint(circleRef, ptNearestLine)

   pt = qad_utils.getPolarPointByPtAngle(ptNearestLine, angleLine, dist)
   pt2 = getCircularInversionOfPoint(circleRef, pt)

   pt = qad_utils.getPolarPointByPtAngle(ptNearestLine, angleLine + math.pi, dist)
   pt3 = getCircularInversionOfPoint(circleRef, pt)
   
   return circleFrom3Pts(pt1, pt2, pt3)


# ===============================================================================
# getCircularInversionOfCircle
# ===============================================================================
def getCircularInversionOfCircle(circleRef, circle):
   """
   la funzione ritorna l'inversione circolare di un cerchio (che é un cerchio)
   """

   angleLine = qad_utils.getAngleBy2Pts(circle.center, circleRef.center)
   ptNearestLine = qad_utils.getPolarPointByPtAngle(circle.center, angleLine, circle.radius)
   dist = qad_utils.getDistance(circleRef.center, circle.center)

   pt1 = getCircularInversionOfPoint(circleRef, ptNearestLine)

   pt = qad_utils.getPolarPointByPtAngle(circle.center, angleLine + math.pi / 2, circle.radius)
   pt2 = getCircularInversionOfPoint(circleRef, pt)

   pt = qad_utils.getPolarPointByPtAngle(circle.center, angleLine - math.pi / 2, circle.radius)
   pt3 = getCircularInversionOfPoint(circleRef, pt)
   
   return circleFrom3Pts(pt1, pt2, pt3)
