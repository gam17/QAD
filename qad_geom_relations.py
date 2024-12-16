# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione delle relazioni (intersezioni, tangenza, 
 perpendicolarità, minima distanza) tra oggetti geometrici di base:
 linea , arco, arco di ellisse, cerchio, ellisse
 
                              -------------------
        begin                : 2019-02-28
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

try:
   import numpy as np
except:
   raise Exception("Need to have numpy installed")

try:
   from scipy.optimize import fsolve, minimize
   NO_SCIPY = False
except:
   NO_SCIPY = True
   # raise Exception("Need to have scipy installed")

from .qad_line import QadLine
from .qad_circle import QadCircle
from .qad_arc import QadArc
from .qad_ellipse import QadEllipse
from .qad_ellipse_arc import QadEllipseArc

from . import qad_utils
from .qad_multi_geom import *


# ===============================================================================
# QadIntersections class
# rappresenta una classe che calcola le intersezioni tra oggetti di base: linea, cerchio, arco, ellisse, arco di ellisse
# ===============================================================================
class QadIntersections():
    
   def __init__(self):
      pass

   # ===============================================================================
   # metodi per le linee infinite - inizio
   # ===============================================================================

   # ===============================================================================
   # twoInfinityLines
   # ===============================================================================
   @staticmethod
   def twoInfinityLines(line1, line2):
      """
      La funzione ritorna il punto di intersezione tra la linea1 e la linea2 considerate linee infinite.
      La funzione ritorna None se le linee non hanno intersezione.
      """
      return qad_utils.getIntersectionPointOn2InfinityLines(line1.pt1, line1.pt2, line2.pt1, line2.pt2)


   # ===============================================================================
   # infinityLineWithLine
   # ===============================================================================
   @staticmethod
   def infinityLineWithLine(infinityLine, line):
      """
      La funzione ritorna il punto di intersezione tra una linea infinita e un segmento <line>.
      La funzione ritorna None se non c'è intersezione.
      """
      ptInt = QadIntersections.twoInfinityLines(infinityLine, line)
      if ptInt is None: return None
      if line.containsPt(ptInt) != True:
         return None
      return ptInt


   # ===============================================================================
   # infinityLineWithCircle
   # ===============================================================================
   @staticmethod
   def infinityLineWithCircle(infinityLine, circle):
      """
      La funzione ritorna i punti di intersezione tra una linea infinita ed un cerchio.
      """
      # sposto le geometrie vicino a 0,0 per migliorare la precisione dei calcoli
      dx = circle.center.x()
      dy = circle.center.y()
      myInfinityLine = infinityLine.copy()
      myInfinityLine.move(-dx, -dy)
      myCircle = circle.copy()
      myCircle.move(-dx, -dy)
      
      if qad_utils.ptNear(myInfinityLine.pt1, myInfinityLine.pt2): return []

      x2_self = myCircle.center.x() * myCircle.center.x() # X del centro del cerchio <myCircle> al quadrato
      y2_self = myCircle.center.y() * myCircle.center.y() # Y del centro del cerchio <myCircle> al quadrato
      radius2_self = myCircle.radius * myCircle.radius # raggio del cerchio <myCircle> al quadrato
      
      diffX = myInfinityLine.pt2.x() - myInfinityLine.pt1.x()
      # se diffX è così vicino a zero 
      if qad_utils.doubleNear(diffX, 0.0): # se myInfinityLine è una retta verticale
         B = -2 * myCircle.center.y()
         C = x2_self + y2_self + (myInfinityLine.pt1.x() * myInfinityLine.pt1.x()) - (2* myInfinityLine.pt1.x() * myCircle.center.x()) - radius2_self
         D = (B * B) - (4 * C) 
         # se D è così vicino a zero 
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # non si può fare la radice quadrata di un numero negativo
            return []
         E = math.sqrt(D)
         
         y1 = (-B + E) / 2        
         x1 = myInfinityLine.pt1.x()
         
         y2 = (-B - E) / 2        
         x2 = myInfinityLine.pt1.x()
      else:
         m = (myInfinityLine.pt2.y() - myInfinityLine.pt1.y()) / diffX
         q = myInfinityLine.pt1.y() - (m * myInfinityLine.pt1.x())
         A = 1 + (m * m)
         B = (2 * m * q) - (2 * myCircle.center.x()) - (2 * m * myCircle.center.y())
         C = x2_self + (q * q) + y2_self - (2 * q * myCircle.center.y()) - radius2_self
              
         D = (B * B) - 4 * A * C
         # se D è così vicino a zero 
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # non si può fare la radice quadrata di un numero negativo
            return []
         E = math.sqrt(D)
      
         x1 = (-B + E) / (2 * A)
         y1 = myInfinityLine.pt1.y() + m * x1 - m * myInfinityLine.pt1.x()
   
         x2 = (-B - E) / (2 * A)
         y2 = myInfinityLine.pt1.y() + m * x2 - m * myInfinityLine.pt1.x()
      
      # traslo i punti per riportarli alla loro posizione originale
      result = []
      result.append(QgsPointXY(x1 + dx, y1 + dy))
      if x1 != x2 or y1 != y2: # i punti non sono coincidenti
         result.append(QgsPointXY(x2 + dx, y2 + dy))
      
      return result


   # ===============================================================================
   # infinityLineWithArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithArc(infinityLine, arc):
      """
      La funzione ritorna i punti di intersezione tra una linea infinita ed un cerchio.
      """
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      intPtList = QadIntersections.infinityLineWithCircle(infinityLine, circle)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # infinityLineWithEllipse
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipse(infinityLine, ellipse):
      """
      La funzione ritorna i punti di intersezione tra una linea infinita e un'ellisse.
      """
      # http://www.ambrsoft.com/TrigoCalc/Circles2/Ellipse/EllipseLine.htm
      # la formula dell'ellisse è:
      # (x - h)^2 / a^2 + (y - k)^2 / b^2 = 1
      # la formula della linea è:
      # y = mx + c
      # se h=0 e k=0 e c<>0 (ellisse orizzontale con centro in 0,0; linea che non passa da 0,0)
      
      # deltaForX = a * b * sqrt(a^2 * m^2 + b^2 - c^2)
      # deltaForY = a * b * m * sqrt(a^2 * m^2 + b^2 - c^2)
      # denom = a^2 * m^2 + b^2
      
      # x1 = (-a^2 * m * c + deltaForX) / denom
      # y1 = (b^2 * c + deltaForY) / denom
      # x2 = (-a^2 * m * c - deltaForX) / denom
      # y1 = (b^2 * c - deltaForY) / denom

      result = []
      # traslo e ruoto la linea per confrontarla con l'ellisse con centro in 0,0 e con rotazione = 0
      myP1 = ellipse.translateAndRotatePtForNormalEllipse(infinityLine.pt1, False)
      myP2 = ellipse.translateAndRotatePtForNormalEllipse(infinityLine.pt2, False)
      
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semiasse maggiore
      b = a * ellipse.axisRatio # semiasse minore

      # a lo chiamo m e b lo chiamo c nell'equazione della retta
      m, c = qad_utils.get_A_B_LineEquation(myP1.x(), myP1.y(), myP2.x(), myP2.y())
      
      dummy = a*a * m*m + b*b - c*c
      if dummy < 0: # non si può fare la radice quadrata di un numero negativo
         return result
      
      deltaForX = a * b * math.sqrt(dummy)
      deltaForY = a * b * m * math.sqrt(dummy)
      denom = a*a * m*m + b*b
      if denom == 0: return result
      
      x1 = (-(a*a) * m * c + deltaForX) / denom
      y1 = (b*b * c + deltaForY) / denom
      x2 = (-(a*a) * m * c - deltaForX) / denom
      y2 = (b*b * c - deltaForY) / denom
      
      # traslo e ruoto il punto per riportarlo nella posizione originale (con il centro e la rotazione dell'ellisse originale)
      myP1.set(x1, y1)
      myP1 = ellipse.translateAndRotatePtForNormalEllipse(myP1, True)
      result.append(myP1)
      
      # traslo e ruoto il punto per riportarlo nella posizione originale (con il centro e la rotazione dell'ellisse originale)
      myP2.set(x2, y2)
      myP2 = ellipse.translateAndRotatePtForNormalEllipse(myP2, True)
      result.append(myP2)

      return result


   # ===============================================================================
   # infinityLineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipseArc(infinityLine, ellipseArc):
      """
      La funzione ritorna i punti di intersezione tra una linea infinita ed un arco di ellisse.
      """
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.infinityLineWithEllipse(infinityLine, ellipse)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
            
      return result


   # ===============================================================================
   # metodi per le linee infinite - fine
   # metodi per i segmenti - inizio
   # ===============================================================================


   # ===============================================================================
   # twoLines
   # ===============================================================================
   @staticmethod
   def twoLines(line1, line2):
      """
      La funzione ritorna il punto di intersezione tra 2 segmenti.
      La funzione ritorna None se i segmenti non hanno intersezione.
      """
      intPt = QadIntersections.twoInfinityLines(line1, line2)
      if intPt is None: return None
      if line1.containsPt(intPt) == False or line2.containsPt(intPt) == False:
         return None
      return intPt


   # ===============================================================================
   # lineWithCircle
   # ===============================================================================
   @staticmethod
   def lineWithCircle(line, circle):
      """
      La funzione ritorna i punti di intersezione tra un segmento ed un cerchio.
      """
      result = []
      intPtList = QadIntersections.infinityLineWithCircle(line, circle)
      for intPt in intPtList:
         if line.containsPt(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # lineWithArc
   # ===============================================================================
   @staticmethod
   def lineWithArc(line, arc):
      """
      La funzione ritorna i punti di intersezione tra un segmento ed un arco.
      """
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      intPtList = QadIntersections.lineWithCircle(line, circle)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # lineWithEllipse
   # ===============================================================================
   @staticmethod
   def lineWithEllipse(line, ellipse):
      """
      La funzione ritorna i punti di intersezione tra un segmento e un'ellisse.
      """
      result = []
      intPtList = QadIntersections.infinityLineWithEllipse(line, ellipse)
      for intPt in intPtList:
         if line.containsPt(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # lineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def lineWithEllipseArc(line, ellipseArc):
      """
      La funzione ritorna i punti di intersezione tra un segmento e un arco di ellisse.
      """
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.lineWithEllipse(line, ellipse)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # metodi per i segmenti - fine
   # metodi per i cerchi - inizio
   # ===============================================================================


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def twoCircles(circle1, circle2):
      """
      La funzione ritorna i punti di intersezione tra 2 cerchi.
      """
      result = []
      # sposto le geometrie vicino a 0,0 per migliorare la precisione dei calcoli
      dx = circle1.center.x()
      dy = circle1.center.y()
      myCircle1 = circle1.copy()
      myCircle1.move(-dx, -dy)
      myCircle2 = circle2.copy()
      myCircle2.move(-dx, -dy)
      
      # se i punti sono così vicini da essere considerati uguali 
      if qad_utils.ptNear(myCircle1.center, myCircle2.center): # stesso centro
         return []
      distFromCenters = qad_utils.getDistance(myCircle1.center, myCircle2.center)
      distFromCirc = distFromCenters - myCircle1.radius - myCircle2.radius

      # se è così vicino allo zero da considerarlo = 0
      if qad_utils.doubleNear(distFromCirc, 0):
         angle = qad_utils.getAngleBy2Pts(myCircle1.center, myCircle2.center)
         pt = qad_utils.getPolarPointByPtAngle(myCircle1.center, angle, myCircle1.radius)
         # traslo il punto per riportarlo alla sua posizione originale
         pt.set(pt.x() + dx, pt.y() + dy)
         result.append(pt)
         return result
         
      if distFromCirc > 0: # i cerchi sono troppo distanti
         return []

      x2_myCircle1 = myCircle1.center.x() * myCircle1.center.x() # X del centro del cerchio <myCircle1> al quadrato
      x2_circle = myCircle2.center.x() * myCircle2.center.x() # Y del centro del cerchio <myCircle2> al quadrato
      radius2_myCircle1 = myCircle1.radius * myCircle1.radius # raggio del cerchio <myCircle1> al quadrato
      radius2_circle = myCircle2.radius * myCircle2.radius # raggio del cerchio <myCircle2> al quadrato
      
      if qad_utils.doubleNear(myCircle1.center.y(), myCircle2.center.y()):
         x1 = x2_circle - x2_myCircle1 + radius2_myCircle1 - radius2_circle
         x1 = x1 / (2 * (myCircle2.center.x() - myCircle1.center.x()))
         x2 = x1         
         D = radius2_myCircle1 - ((x1 - myCircle1.center.x()) * (x1 - myCircle1.center.x()))
         # se D è così vicino a zero 
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # non si può fare la radice quadrata di un numero negativo
            return []
         E = math.sqrt(D)
         
         y1 = myCircle1.center.y() + E
         y2 = myCircle1.center.y() - E
      else:
         y2_myCircle1 = myCircle1.center.y() * myCircle1.center.y() # Y del centro del cerchio <myCircle1> al quadrato
         y2_circle = myCircle2.center.y() * myCircle2.center.y() # Y del centro del cerchio <myCircle2> al quadrato
         
         a = (myCircle1.center.x() - myCircle2.center.x()) / (myCircle2.center.y() - myCircle1.center.y())
         b = x2_circle - x2_myCircle1 + y2_circle - y2_myCircle1 + radius2_myCircle1 - radius2_circle 
         b = b / (2 * (myCircle2.center.y() - myCircle1.center.y()))
         
         A = 1 + (a * a)
         B = (2 * a * b) - (2 * myCircle1.center.x()) - (2 * a * myCircle1.center.y())
         C = (b * b) - (2 * myCircle1.center.y() * b) + x2_myCircle1 + y2_myCircle1 - radius2_myCircle1
         D = (B * B) - (4 * A * C)
         # se D è così vicino a zero 
         if qad_utils.doubleNear(D, 0.0):
            D = 0
         elif D < 0: # non si può fare la radice quadrata di un numero negativo
            return []
         E = math.sqrt(D)
         
         x1 = (-B + E) / (2 * A)
         y1 = a * x1 + b
   
         x2 = (-B - E) / (2 * A)           
         y2 = a * x2 + b
      
      # traslo i punti per riportarli alla loro posizione originale
      result.append(QgsPointXY(x1 + dx, y1 + dy))
      if x1 != x2 or y1 != y2: # i punti non sono coincidenti
         result.append(QgsPointXY(x2 + dx, y2 + dy))
      
      return result


   # ===============================================================================
   # circleWithArc
   # ===============================================================================
   @staticmethod
   def circleWithArc(circle, arc):
      """
      La funzione ritorna i punti di intersezione tra un cerchio ed un arco.
      """
      result = []
      circle1 = QadCircle()
      circle1.set(arc.center, arc.radius)
      intPtList = QadIntersections.twoCircles(circle, circle1)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # generate_initial_guesses 
   # Funzione per generare i guess iniziali per i calcoli di intersezione cerchio con ellisse (chatgpt)
   # ===============================================================================
   def generate_initial_guesses(h, k, a, b, theta, num_points=20):
      t = np.linspace(0, 2 * np.pi, num_points)
      x_ellipse = a * np.cos(t)
      y_ellipse = b * np.sin(t)
      
      initial_guesses = []
      for x_e, y_e in zip(x_ellipse, y_ellipse):
          x_rotated = h + (x_e * np.cos(theta) - y_e * np.sin(theta))
          y_rotated = k + (x_e * np.sin(theta) + y_e * np.cos(theta))
          initial_guesses.append((x_rotated, y_rotated))
      
      return initial_guesses


   # ===============================================================================
   # rotate 
   # Funzione per la trasformazione di coordinate per i calcoli di intersezione cerchio con ellisse (chatgpt)
   # ===============================================================================
   def rotate(x, y, theta):
      x_prime = x * np.cos(theta) + y * np.sin(theta)
      y_prime = -x * np.sin(theta) + y * np.cos(theta)
      return x_prime, y_prime
   

# ============================================================================
   # getEquationForIntCicleEllipse
   # Definisce un sistema di equazioni non lineari per i calcoli di intersezione cerchio con ellisse (chatgpt)
   # x e y: centro
   # a e b: i semiassi dell'ellisse
   # theta: l'angolo di rotazione dell'ellisse
   # h e k: le traslazioni dell'ellisse rispetto all'origine.
   # ============================================================================
   @staticmethod
   def getEquationForIntCicleEllipse(xy, circle, ellipse):
      x, y = xy
      
      circle_eq = (x - circle.center.x())**2 + (y - circle.center.y())**2 - circle.radius**2
         
      return [circle_eq, QadIntersections.getEquationForEllipse(xy, ellipse)]      


   # ===============================================================================
   # circleWithEllipse
   # ===============================================================================
   @staticmethod
   def circleWithEllipse(circle, ellipse):
      """
      La funzione ritorna i punti di intersezione tra un cerchio ed una ellisse.
      """
      if NO_SCIPY == True: return []
      
      # Calcola la lunghezza dell'asse maggiore (a)
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt)
      # Calcola la lunghezza dell'asse minore (b)
      b = a * ellipse.axisRatio      
      # theta: l'angolo di rotazione dell'ellisse.
      theta = ellipse.getRotation()
      # h e k: le traslazioni dell'ellisse rispetto all'origine, coordinate centro
      h = ellipse.center.x()
      k = ellipse.center.y()

      args = (circle, ellipse)
      
      # Generiamo i guess iniziali
      initial_guesses = QadIntersections.generate_initial_guesses(h, k, a, b, theta)
      
      # Risoluzione del sistema di equazioni
      intersections = []
      for guess in initial_guesses:
          sol = fsolve(QadIntersections.getEquationForIntCicleEllipse, guess, args)
          if not any(np.isclose(sol, x).all() for x in intersections):
              intersections.append(sol)
      
      result = []
      for intersection in intersections:
         result.append(QgsPointXY(intersection[0], intersection[1]))
               
      return result
   
#       # http://it.scienza.matematica.narkive.com/cTzzSW1r/intersezione-tra-ellisse-e-circonferenza
#       result = []
# 
#       # traslo e ruoto il centro del cerchio per confrontarlo con l'ellisse con centro in 0,0 e con rotazione = 0
#       myCircle = QadCircle(circle)
#       myCircle.center = ellipse.translateAndRotatePtForNormalEllipse(circle.center, False)
# 
#       a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semiasse maggiore
#       b = a * ellipse.axisRatio # semiasse minore
#       
#       a2 = a * a # a al quadrato
#       a4 = a2 * a2 # a alla quarta
#       b2 = b * b # b al quadrato
#       c2 = (a / b) * (a / b)
#       c4 = c2 * c2
#       r = myCircle.radius
#       r2 = r * r
#       xc = myCircle.center.x() # x del centro del cerchio
#       xc2 = xc * xc # x cerchio al quadrato
#       yc = myCircle.center.y() # y del centro del cerchio
#       yc2 = yc * yc # y cerchio al quadrato
#       a2_b2 = a2 - b2
# 
# #       [a^4+(p^2+q^2-r^2)^2-2a^2(p^2-q^2+r^2] +
# #       y [4q(r^2-a^2-p^2-q^2)] +
# #       y^2 [2a^2-2a^2c^2+2p^2+2c^2p^2+6q^2-2c^2q^2-2r^2+2c^2r^2] +
# #       y^3 [4c^2q-4q]+
# #       y^4 [1-2c^2+c^4] = 0
#       
#       z0 = a4 + (xc2 + yc2 - r2) * (xc2 + yc2 - r2) - (2 * a2) * (xc2 - yc2 + r2)
#       z1 = (4 * yc2) * (r2 - a2 - xc2 - yc2)
#       z2 = (2 * a2) - (2 * a2 * c2) + 2 *xc2 + (2 * c2 * xc2) + (6 * yc2) - (2 *c2 * yc2) - (2 * r2) + (2 * c2 * r2)
#       z3 = (4 * c2 * yc) - (4 * yc)
#       z4 = 1 - (2 * c2) + c4
# 
#       y_result = np.roots([z4, z3, z2, z1, z0])
#       for y in y_result:
#          y = float(y)
#          n = (1.0 - y * y / b2) * a2 # data la Y calcolo la X
#          if qad_utils.doubleNear(n, 0): n = 0 # per problemi di precisione di calcolo (es. se x = 10 , n = -1.11022302463e-14 !)
#          if n >= 0:
#             x = math.sqrt(n)
#             p = QgsPointXY(x, y)
#             # verifico se il punto va bene
#             dist = qad_utils.getDistance(p, myCircle.center)
#             # se la distanza coincide con il raggio del cerchio
#             if qad_utils.doubleNear(dist, myCircle.radius, 1.e-1): # lo so che fa schifo ma l'approssimazione dei calcoli...
#                # traslo e ruoto il punto per riportarlo nella posizione originale (con il centro e la rotazione dell'ellisse originale)
#                p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
#                qad_utils.appendUniquePointToList(result, p)
#                
#             # verifico l'altra coordinata x
#             p = QgsPointXY(-x, y)
#             # verifico se il punto va bene
#             dist = qad_utils.getDistance(p, myCircle.center)
#             # se la distanza coincide con il raggio del cerchio
#             if qad_utils.doubleNear(dist, myCircle.radius, 1.e-1): # lo so che fa schifo ma l'approssimazione dei calcoli...
#                # traslo e ruoto il punto per riportarlo nella posizione originale (con il centro e la rotazione dell'ellisse originale)
#                p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
#                qad_utils.appendUniquePointToList(result, p)
# 
#       return result


   # ===============================================================================
   # circleWithEllipseArc
   # ===============================================================================
   @staticmethod
   def circleWithEllipseArc(circle, ellipseArc):
      """
      La funzione ritorna i punti di intersezione tra un cerchio ed un arco di ellisse.
      """
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.circleWithEllipse(circle, ellipse)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # metodi per i cerchi - fine
   # metodi per gli archi - inizio
   # ===============================================================================


   # ===============================================================================
   # twoArcs
   # ===============================================================================
   @staticmethod
   def twoArcs(arc1, arc2):
      """
      La funzione ritorna i punti di intersezione tra 2 archi.
      """
      result = []
      circle = QadCircle()
      circle.set(arc1.center, arc1.radius)
      intPtList = QadIntersections.circleWithArc(circle, arc2)
      for intPt in intPtList:
         if arc1.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # arcWithEllipseArc
   # ===============================================================================
   @staticmethod
   def arcWithEllipseArc(arc, ellipseArc):
      """
      La funzione ritorna i punti di intersezione tra un arco ed un arco di ellisse.
      """
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)     
      intPtList = QadIntersections.circleWithEllipseArc(circle, ellipseArc)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # metodi per gli archi - fine
   # metodi per le ellissi - inizio
   # ===============================================================================

  
   # ============================================================================
   # getEquationForEllipse
   # Definisce una funzione che rappresenta un'ellisse ruotata e traslata
   # x e y: centro
   # a e b: i semiassi dell'ellisse
   # theta: l'angolo di rotazione dell'ellisse
   # h e k: le traslazioni dell'ellisse rispetto all'origine.
   # ============================================================================
   @staticmethod
   def getEquationForEllipse(xy, ellipse):
      x, y = xy
      # Calcola la lunghezza dell'asse maggiore (a)
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt)
      # Calcola la lunghezza dell'asse minore (b)
      b = a * ellipse.axisRatio      
      # theta: l'angolo di rotazione dell'ellisse.
      theta = ellipse.getRotation()
      # h e k: le traslazioni dell'ellisse rispetto all'origine, coordinate centro
      h = ellipse.center.x()
      k = ellipse.center.y()

      cos_t = np.cos(theta)
      sin_t = np.sin(theta)
      term1 = ((x - h) * cos_t + (y - k) * sin_t) ** 2 / a ** 2
      term2 = ((x - h) * sin_t - (y - k) * cos_t) ** 2 / b ** 2
      return term1 + term2 - 1

   
   @staticmethod
   def sistema(xy, ellipse1, ellipse2):
      return [QadIntersections.getEquationForEllipse(xy, ellipse1), QadIntersections.getEquationForEllipse(xy, ellipse2)]

   
   # ===============================================================================
   # twoEllipses
   # ===============================================================================
   @staticmethod
   def twoEllipses(ellipse1, ellipse2):
      """
      La funzione ritorna i punti di intersezione tra 2 ellissi (chatGPT)
      """
      if NO_SCIPY == True: return []
      
      # test
#       l1 = QadLine()
#       l1.set(QgsPointXY(1, 2), QgsPointXY(3, 4))
#       
#       center = QgsPointXY(0, 0)
#       a = 2
#       b = 1
#       axisRatio = b / a
#       theta = math.pi / 4
#       ellipse1 = QadEllipse()
#       majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, theta, a)
#       ellipse1.set(center, majorAxisFinalPt, axisRatio)
#       QadMinDistance.fromLineToEllipse(l1, ellipse1)
      
#             
#       
#       center = QgsPointXY(-1, -2)
#       a = 4
#       b = 2
#       axisRatio = b / a
#       theta = math.pi / 4
#       ellipse2 = QadEllipse()
#       majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, theta, a)
#       ellipse2.set(center, majorAxisFinalPt, axisRatio)

      
      args = (ellipse1, ellipse2)
      # Genera stime iniziali in una griglia intorno ai centri delle ellissi
      x_vals = np.linspace(-10, 10, 10)
      y_vals = np.linspace(-10, 10, 10)
      stima_iniziali = np.array(np.meshgrid(x_vals, y_vals)).T.reshape(-1, 2)
            
      # Trova le intersezioni utilizzando fsolve da diverse stime iniziali
      soluzioni = []
      for stima in stima_iniziali:
          soluzione = fsolve(QadIntersections.sistema, stima, args)
          if QadIntersections.sistema(soluzione, ellipse1, ellipse2)[0] < 1e-6 and QadIntersections.sistema(soluzione, ellipse1, ellipse2)[1] < 1e-6:
              soluzioni.append(soluzione)
      
      # Rimuovi soluzioni duplicate (vicine)
      tolleranza = 1e-4
      soluzioni_uniche = []
      for sol in soluzioni:
          if not any(np.linalg.norm(sol - s) < tolleranza for s in soluzioni_uniche):
              soluzioni_uniche.append(sol)
      
      result = []
      for sol in soluzioni_uniche:
         result.append(QgsPointXY(sol[0], sol[1]))
      
      return result


   # ===============================================================================
   # ellipseWithArc
   # ===============================================================================
   @staticmethod
   def ellipseWithArc(ellipse, arc):
      """
      La funzione ritorna i punti di intersezione tra un'ellisse ed un arco.
      """
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      intPtList = QadIntersections.circleWithEllipse(circle, ellipse)
      for intPt in intPtList:
         if arc.isPtOnArcOnlyByAngle(intPt):
            result.append(intPt)
      return result
   

   # ===============================================================================
   # ellipseWithEllipseArc
   # ===============================================================================
   @staticmethod
   def ellipseWithEllipseArc(ellipse, ellipseArc):
      """
      La funzione ritorna i punti di intersezione tra un'ellisse ed un arco di ellisse.
      """
      result = []
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      intPtList = QadIntersections.twoEllipses(ellipse, ellipse1)
      for intPt in intPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # metodi per le ellissi - fine
   # metodi per gli archi di ellisse - inizio
   # ===============================================================================


   # ===============================================================================
   # twoEllipseArcs
   # ===============================================================================
   @staticmethod
   def twoEllipseArcs(EllipseArc1, EllipseArc2):
      """
      La funzione ritorna i punti di intersezione tra 2 archi di ellisse.
      """
      result = []
      ellipse1 = QadEllipse()
      ellipse1.set(EllipseArc1.center, EllipseArc1.majorAxisFinalPt, EllipseArc1.axisRatio)
      intPtList = QadIntersections.ellipseWithEllipseArc(ellipse1, EllipseArc2)
      for intPt in intPtList:
         if EllipseArc1.isPtOnEllipseArcOnlyByAngle(intPt):
            result.append(intPt)
      return result


   # ===============================================================================
   # metodi per gli archi di ellisse - fine
   # metodi per gli oggetti geometrici di base - inizio
   # ===============================================================================


   # ============================================================================
   # twoBasicGeomObjects
   # ============================================================================
   @staticmethod   
   def twoBasicGeomObjects(object1, object2):
      """
      la funzione calcola i punti di intersezione tra 2 oggetti geometrici di base:
      linea, arco, arco di ellisse, cerchio, ellisse.
      """      
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            result = QadIntersections.twoLines(object1, object2)
            return [result] if result is not None else []
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.lineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadIntersections.lineWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.lineWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.lineWithEllipseArc(object1, object2)
         
      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadIntersections.circleWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.circleWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.circleWithEllipseArc(object1, object2)
         
      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadIntersections.twoArcs(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.arcWithEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadIntersections.ellipseWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.twoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.ellipseWithEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.lineWithEllipseArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadIntersections.arcWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadIntersections.twoEllipseArcs(object1, object2)
   
      return []


   # ============================================================================
   # twoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def twoBasicGeomObjectExtensions(object1, object2):
      """
      la funzione calcola i punti di intersezione tra le estensioni di 2 oggetti geometrici di base:
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      """      
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            result = QadIntersections.twoInfinityLines(object1, object2)
            return [result] if result is not None else ()         
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.infinityLineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.infinityLineWithCircle(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.infinityLineWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.infinityLineWithEllipse(object1, ellipse)
         
      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.twoCircles(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.circleWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.circleWithEllipse(object1, ellipse)
         
      elif object1.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object1.center, object1.radius)
         return QadIntersections.twoBasicGeomObjectExtensions(circle, object2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.circleWithEllipse(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.twoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.twoEllipses(object1, ellipse)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         return QadIntersections.twoBasicGeomObjectExtensions(ellipse, object2)
   
      return []


   # ============================================================================
   # basicGeomObjectWithBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def basicGeomObjectWithBasicGeomObjectExtensions(object1, object2):
      """
      la funzione calcola i punti di intersezione tra un oggetto geometrico di base (object1) e 
      le estensioni di oggetti geometrico (object2) di base:
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            result = QadIntersections.infinityLineWithLine(object2, object1)
            return [result] if result is not None else ()         
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.lineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.lineWithCircle(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.lineWithEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.lineWithEllipse(object1, ellipse)
         
      elif object1.whatIs() == "CIRCLE":
         return QadIntersections.twoBasicGeomObjectExtensions(object1, object2)
         
      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithArc(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.circleWithArc(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.ellipseWithArc(ellipse, object1)

      elif object1.whatIs() == "ELLIPSE":
         return QadIntersections.twoBasicGeomObjectExtensions(object1, object2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return QadIntersections.infinityLineWithEllipseArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadIntersections.circleWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadIntersections.circleWithEllipseArc(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadIntersections.ellipseWithEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadIntersections.ellipseWithEllipseArc(ellipse, object1)
   
      return []


   # ============================================================================
   # twoGeomObjects
   # ============================================================================
   @staticmethod   
   def twoGeomObjects(object1, object2, object2GeomBoundingBoxCache = None):
      """
      la funzione calcola i punti di intersezione tra 2 oggetti geometrici
      """
      geomType1 = object1.whatIs()
      result = []
      
      if object2GeomBoundingBoxCache is None:
         object2GeomBoundingBoxCache = QadGeomBoundingBoxCache(object2)
         
      if geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            pt = object1.getPointAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(pt, object2, object2GeomBoundingBoxCache))
         
      elif geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(linearObj, object2, object2GeomBoundingBoxCache))
            
      elif geomType1 == "POLYLINE":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(linearObj, object2, object2GeomBoundingBoxCache))
            
      elif geomType1 == "POLYGON":
         for geomAt in range(0, object1.qty()):
            closedObj = object1.getClosedObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(closedObj, object2, object2GeomBoundingBoxCache))
         
      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            polygon = object1.getPolygonAt(geomAt)
            result.extend(QadIntersections.twoGeomObjects(polygon, object2, object2GeomBoundingBoxCache))
         
      # oggetto 1 è una geometria base
      elif object1.whatIs() == "POINT" or object1.whatIs() == "LINE" or object1.whatIs() == "CIRCLE" or \
           object1.whatIs() == "ARC" or object1.whatIs() == "ELLIPSE" or object1.whatIs() == "ELLIPSE_ARC":
         geomType2 = object2.whatIs()
         
         if object2GeomBoundingBoxCache is not None and object2GeomBoundingBoxCache.cacheLayer is not None:
            # leggo solo le parti che si intersecano con il bounding box di object1
            boundingBox = object1.getBoundingBox()
            geomSubgeomPartAtList = object2GeomBoundingBoxCache.getIntersectionWithBoundingBox(boundingBox)
            for geomSubgeomPartAt in geomSubgeomPartAtList:
               part = getQadGeomPartAt(object2, geomSubgeomPartAt[0], geomSubgeomPartAt[1], geomSubgeomPartAt[2])
               result.extend(QadIntersections.twoBasicGeomObjects(object1, part))                  

         elif geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoBasicGeomObjects(object1, object2.getPointAt(geomAt)))
                  
         elif geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getLinearObjectAt(geomAt)))
            
         elif geomType2 == "POLYLINE":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getLinearObjectAt(geomAt)))
            
         elif geomType2 == "POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getClosedObjectAt(geomAt)))
            
         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getPolygonAt(geomAt)))
            
         # oggetto 1 è una geometria base
         elif object2.whatIs() == "POINT" or object2.whatIs() == "LINE" or object2.whatIs() == "CIRCLE" or \
              object2.whatIs() == "ARC" or object2.whatIs() == "ELLIPSE" or object2.whatIs() == "ELLIPSE_ARC":
            result = QadIntersections.twoBasicGeomObjects(object1, object2)
   
      return result


   # ============================================================================
   # twoGeomObjectsExtensions
   # ============================================================================
   @staticmethod   
   def twoGeomObjectsExtensions(object1, object2):
      """
      la funzione calcola i punti di intersezione tra tra le estensioni di 2 oggetti geometrici:
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse).
      """
      geomType1 = object1.whatIs()
      result = []
      
      if geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            pt = object1.getPointAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(pt, object2))
         
      elif geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(linearObj, object2))
            
      elif geomType1 == "POLYLINE":
         if object1.qty() > 0: # prima parte della polilinea
            linearObj = object1.getLinearObjectAt(0)
            pts = QadIntersections.twoGeomObjectsExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               reversedLine = linearObj.copy()
               appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
            else:
               result.extend(pts)
               
         for geomAt in range(1, object1.qty()-1):
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1.getLinearObjectAt(geomAt), object2))

         if object1.qty() > 1: # ultima parte della polilinea
            linearObj = object1.getLinearObjectAt(-1)
            pts = QadIntersections.twoGeomObjectsExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
            else:
               result.extend(pts)

      elif geomType1 == "POLYGON":
         for subGeomAt in range(0, object1.qty()):
            closedObj = object1.getClosedObjectAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(closedObj, object2))
         
      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            polygon = object1.getPolygonAt(geomAt)
            result.extend(QadIntersections.twoGeomObjectsExtensions(polygon, object2))
         
      # oggetto 1 è una geometria base
      elif object1.whatIs() == "POINT" or object1.whatIs() == "LINE" or object1.whatIs() == "CIRCLE" or \
           object1.whatIs() == "ARC" or object1.whatIs() == "ELLIPSE" or object1.whatIs() == "ELLIPSE_ARC":
         geomType2 = object2.whatIs()
         
         if geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoBasicGeomObjectExtensions(object1, object2.getPointAt(geomAt)))
                  
         elif geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjectsExtensions(object1, object2.getLinearObjectAt(geomAt)))
            
         elif geomType2 == "POLYLINE":
            if object2.qty() > 0: # prima parte della polilinea
               linearObj = object2.getLinearObjectAt(0)
               pts = QadIntersections.twoGeomObjectsExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  reversedLine = linearObj.copy()
                  appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
               else:
                  result.extend(pts)
            
            for geomAt in range(1, object2.qty()-1):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object2.getLinearObjectAt(geomAt), object1))

            if object2.qty() > 1: # ultima parte della polilinea
               linearObj = object2.getLinearObjectAt(-1)
               pts = QadIntersections.twoGeomObjectsExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
               else:
                  result.extend(pts)
            
         elif geomType2 == "POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjectsExtensions(object1, object2.getClosedObjectAt(geomAt)))
            
         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.twoGeomObjectsExtensions(object1, object2.getPolygonAt(geomAt)))
            
         # oggetto 2 è una geometria base
         elif object2.whatIs() == "POINT" or object2.whatIs() == "LINE" or object2.whatIs() == "CIRCLE" or \
              object2.whatIs() == "ARC" or object2.whatIs() == "ELLIPSE" or object2.whatIs() == "ELLIPSE_ARC":
            result = QadIntersections.twoBasicGeomObjectExtensions(object1, object2)
   
      return result


   # ============================================================================
   # geomObjectWithGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def geomObjectWithGeomObjectExtensions(object1, object2):
      """
      la funzione calcola i punti di intersezione tra un oggetto geometrico (object1) e 
      le estensioni di un oggetto geometrico (object2)
      """
      geomType1 = object1.whatIs()
      result = []
      
      if geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            pt = object1.getPointAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(pt, object2))
         
      elif geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            linearObj = object1.getLinearObjectAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(linearObj, object2))
            
      elif geomType1 == "POLYLINE":
         if object1.qty() > 0: # prima parte della polilinea
            linearObj = object1.getLinearObjectAt(0)
            pts = QadIntersections.geomObjectWithGeomObjectExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               reversedLine = linearObj.copy()
               appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
            else:
               result.extend(pts)
               
         for geomAt in range(1, object1.qty()-1):
            result.extend(QadIntersections.twoGeomObjects(object1.getLinearObjectAt(geomAt), object2))

         if object1.qty() > 1: # ultima parte della polilinea
            linearObj = object1.getLinearObjectAt(-1)
            pts = QadIntersections.geomObjectWithGeomObjectExtensions(linearObj, object2)
            if linearObj.whatIs() == "LINE":
               appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
            else:
               result.extend(pts)
            
      elif geomType1 == "POLYGON":
         for subGeomAt in range(0, object1.qty()):
            closedObj = object1.getClosedObjectAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(closedObj, object2))
         
      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            polygon = object1.getPolygonAt(geomAt)
            result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(polygon, object2))
         
      # oggetto 1 è una geometria base
      elif object1.whatIs() == "POINT" or object1.whatIs() == "LINE" or object1.whatIs() == "CIRCLE" or \
           object1.whatIs() == "ARC" or object1.whatIs() == "ELLIPSE" or object1.whatIs() == "ELLIPSE_ARC":
         geomType2 = object2.whatIs()
         
         if geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getPointAt(geomAt)))
                  
         elif geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getLinearObjectAt(geomAt)))
            
         elif geomType2 == "POLYLINE":
            if object2.qty() > 0: # prima parte della polilinea
               linearObj = object2.getLinearObjectAt(0)
               pts = QadIntersections.geomObjectWithGeomObjectExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  reversedLine = linearObj.copy()
                  appendPtOnTheSameTanDirectionOnly(reversedLine.reverse(), pts, result)
               else:
                  result.extend(pts)
            
            for geomAt in range(1, object2.qty()-1):
               result.extend(QadIntersections.twoGeomObjects(object1, object2.getLinearObjectAt(geomAt)))

            if object2.qty() > 1: # ultima parte della polilinea
               linearObj = object2.getLinearObjectAt(-1)
               pts = QadIntersections.geomObjectWithGeomObjectExtensions(object1, linearObj)
               if linearObj.whatIs() == "LINE":
                  appendPtOnTheSameTanDirectionOnly(linearObj, pts, result)
               else:
                  result.extend(pts)
            
         elif geomType2 == "POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getClosedObjectAt(geomAt)))
            
         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               result.extend(QadIntersections.geomObjectWithGeomObjectExtensions(object1, object2.getPolygonAt(geomAt)))
            
         # oggetto 2 è una geometria base
         elif object2.whatIs() == "POINT" or object2.whatIs() == "LINE" or object2.whatIs() == "CIRCLE" or \
              object2.whatIs() == "ARC" or object2.whatIs() == "ELLIPSE" or object2.whatIs() == "ELLIPSE_ARC":
            result = QadIntersections.basicGeomObjectWithBasicGeomObjectExtensions(object1, object2)
   
      return result


   # ===============================================================================
   # getOrderedPolylineIntersectionPtsWithBasicGeom
   # ===============================================================================
   @staticmethod
   def getOrderedPolylineIntersectionPtsWithBasicGeom(polyline, linearObject, orderByStartPtOfLinearObject = False):
      """
      La funzione restituisce diverse liste:
      - la prima é una lista di punti di intersezione tra la parte <linearObject> e la polilinea.
        La lista è ordinata per distanza dal punto iniziale di <linearObject> se <orderByStartPtOfLinearObject> = True 
        altrimenti è ordinata per distanza dal punto iniziale della polilinea
      - la seconda é una lista che contiene, rispettivamente per ogni punto di intersezione,
        il numero della parte (0-based) della polilinea in cui si trova quel punto.
      - la terza é una lista che contiene, rispettivamente per ogni punto di intersezione,
        la distanza dal punto iniziale di <linearObject> se <orderByStartPtOfLinearObject> = True o
        dal punto iniziale della polilinea se <orderByStartPtOfLinearObject> = False
      """         
      gType = linearObject.whatIs()
      if polyline.whatIs() != "POLYLINE" or \
         (gType != "LINE" and gType != "ARC" and gType != "ELLIPSE_ARC"):
         return [], [], []

      intPtSortedList = [] # lista di ((punto, distanza dall'inizio di linearObject) ...)
      partNumber = -1
      if orderByStartPtOfLinearObject == False:
         distFromStartPrevParts = 0
         
      # per ogni parte della lista
      i = 0
      while i < polyline.qty():
         linearObject2 = polyline.getLinearObjectAt(i)
         partNumber = partNumber + 1
         partialIntPtList = QadIntersections.twoBasicGeomObjects(linearObject, linearObject2)

         for partialIntPt in partialIntPtList:
            # escludo i punti che sono già in intPtSortedList
            found = False
            for intPt in intPtSortedList:
               if qad_utils.ptNear(intPt[0], partialIntPt):
                  found = True
                  break
               
            if found == False:
               if orderByStartPtOfLinearObject:
                  # inserisco il punto ordinato per distanza dall'inizio di linearObject
                  distFromStart = linearObject.getDistanceFromStart(partialIntPt)
               else:
                  distFromStart = distFromStartPrevParts + linearObject2.getDistanceFromStart(partialIntPt)
                  
               insertAt = 0
               for intPt in intPtSortedList:
                  if intPt[1] < distFromStart:
                     insertAt = insertAt + 1
                  else:
                     break                     
               intPtSortedList.insert(insertAt, [partialIntPt, distFromStart, partNumber])
            
         if orderByStartPtOfLinearObject == False:
            distFromStartPrevParts = distFromStartPrevParts + linearObject2.length()
         i = i + 1
         
      resultIntPt = []
      resultPartNumber = []
      resultDistanceFromStart = []
      for intPt in intPtSortedList:
         resultIntPt.append(intPt[0])
         resultPartNumber.append(intPt[2])
         resultDistanceFromStart.append(intPt[1])
   
      return resultIntPt, resultPartNumber, resultDistanceFromStart


   # ===============================================================================
   # getOrderedPolylineIntersectionPtsWithPolyline
   # ===============================================================================
   @staticmethod
   def getOrderedPolylineIntersectionPtsWithPolyline(polyline1, polyline2):
      """
      la funzione restituisce diverse liste:
      - la prima é una lista di punti di intersezione tra le 2 polilinee
      ordinata per distanza dal punto iniziale di <polyline2> .
      - la seconda é una lista che contiene, rispettivamente per ogni punto di intersezione,
      il numero della parte della <polyline2> (0-based) in cui si trova quel punto.
      - la terza é una lista che contiene, rispettivamente per ogni punto di intersezione,
      la distanza dal punto iniziale della polilinea2.
      """
      if polyline1.whatIs() != "POLYLINE" or polyline2.whatIs() != "POLYLINE":
         return [], [], []

      resultIntPt = []
      resultPartNumber = []
      resultDistanceFromStart = []
      
      # per ogni parte della lista
      i = 0
      while i < polyline1.qty():
         linearObject1 = polyline1.getLinearObjectAt(i)
         # lista di punti di intersezione ordinata per distanza dal punto iniziale di <linearObject1>
         partialResult = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(polyline2, linearObject1, orderByStartPtOfLinearObject = True)            
         resultIntPt.extend(partialResult[0])
         resultPartNumber.extend(partialResult[2])
         resultDistanceFromStart.extend(partialResult[1])
         i = i + 1
         
      return resultIntPt, resultPartNumber, resultDistanceFromStart


# ===============================================================================
# QadPerpendicularity class
# rappresenta una classe che calcola la perpendicolarità tra oggetti di base: punto, linea, arco, arco di ellisse, cerchio, ellisse
# ===============================================================================
class QadPerpendicularity():
    
   def __init__(self):
      pass


   # ===============================================================================
   # metodi per le linee infinite - inizio
   # ===============================================================================

   # ===============================================================================
   # fromPointToInfinityLine
   # ===============================================================================
   @staticmethod   
   def fromPointToInfinityLine(pt, line):
      """
      la funzione ritorna la proiezione perpendicolare di punto su una linea infinita
      """
      return qad_utils.getPerpendicularPointOnInfinityLine(line.pt1, line.pt2, pt)


   # ===============================================================================
   # metodi per le linee infinite - fine
   # metodi per i segmenti - inizio
   # ===============================================================================


   # ===============================================================================
   # fromPointToLine
   # ===============================================================================
   @staticmethod   
   def fromPointToLine(pt, line):
      """
      la funzione ritorna la proiezione perpendicolare di punto su un segmento
      """
      perpPt = QadPerpendicularity.fromPointToInfinityLine(pt, line)
      if line.containsPt(perpPt):
         return perpPt
      return None
   

   # ===============================================================================
   # getInfinityLinePerpOnMiddle
   # ===============================================================================
   @staticmethod   
   def getInfinityLinePerpOnMiddleLine(line):
      """
      la funzione trova una linea perpendicolare e passante per il punto medio della linea.
      """
      ptMiddle = line.getMiddlePt()
      dist = qad_utils.getDistance(line.pt1, ptMiddle)
      if dist == 0:
         return None
      angle = qad_utils.getAngleBy2Pts(line.pt1, line.pt2) + math.pi / 2
      pt2Middle = qad_utils.getPolarPointByPtAngle(ptMiddle, angle, dist)
      line = QadLine()
      line.set(ptMiddle, pt2Middle)
      return line
   

   # ===============================================================================
   # metodi per i segmenti - fine
   # metodi per i cerchi - inizio
   # ===============================================================================


   # ===============================================================================
   # fromPointToCircle
   # ===============================================================================
   @staticmethod   
   def fromPointToCircle(pt, circle):
      """
      la funzione ritorna le proiezioni perpendicolari di punto su un cerchio
      """
      angle = qad_utils.getAngleBy2Pts(circle.center, pt)
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(circle.center, angle + math.pi, circle.radius)
      return [pt1, pt2]      


   # ===============================================================================
   # metodi per i cerchi - fine
   # metodi per gli archi - inizio
   # ===============================================================================


   # ============================================================================
   # fromPointToArc
   # ============================================================================
   @staticmethod   
   def fromPointToArc(pt, arc):
      """
      la funzione ritorna la proiezione perpendicolare di punto su un arco
      """
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)     
      perpPtList = QadPerpendicularity.fromPointToCircle(pt, circle)
      for perpPt in perpPtList:
         if arc.isPtOnArcOnlyByAngle(perpPt):
            result.append(perpPt)
      return result

      
   # ===============================================================================
   # metodi per gli archi - fine
   # metodi per le ellissi - inizio
   # ===============================================================================
   
   
   # ============================================================================
   # fromPointToEllipse
   # ============================================================================
   @staticmethod   
   def fromPointToEllipse(pt, ellipse):
      """
      la funzione ritorna la proiezione perpendicolare di punto su un'ellisse (fino a 4 punti)
      """      
      # https://www.mathpages.com/home/kmath505/kmath505.htm (per punti esterni all'ellise)
      # https://math.stackexchange.com/questions/609351/number-of-normals-from-a-point-to-an-ellipse (per punti interni all'ellisse)
      result = []

      # ritorna -1 se il punto è interno, 0 se è sull'ellisse, 1 se è esterno
      whereIsPt = ellipse.whereIsPt(pt)
      if whereIsPt == 0: # pt è sull'ellisse
         result.append(QgsPointXY(pt.x(), pt.y()))
         return result

      # traslo e ruoto il punto per confrontarlo con l'ellisse con centro in 0,0 e con rotazione = 0
      myPoint = ellipse.translateAndRotatePtForNormalEllipse(pt, False)

      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semiasse maggiore
      b = a * ellipse.axisRatio # semiasse minore
      e = QadEllipse(ellipse)
      e.center.set(0.0, 0.0)
      e.majorAxisFinalPt.set(a, 0.0)
      
      a2 = a * a # a al quadrato
      b2 = b * b # b al quadrato
      xp = myPoint.x() # x del punto
      xp2 = xp * xp # xp al quadrato
      yp = myPoint.y()
      yp2 = yp * yp # yp al quadrato
      a2_b2 = a2 - b2
      
      c4 = a2_b2 * a2_b2
      c3 = -2 * a2 * xp * a2_b2
      c2 = a2 * (a2 * xp2 + b2 * yp2 - (a2_b2 * a2_b2))
      c1 = 2 * a2 * a2 * xp * a2_b2
      c0 = -1 * (a2 * a2 * a2) * xp2
      
      x_result = np.roots([c4, c3, c2, c1, c0])
      for x in x_result:
         n = (1.0 - x * x / a2) * b2 # data la X calcolo la Y
         if qad_utils.doubleNear(n, 0): n = 0 # per problemi di precisione di calcolo (es. se x = 10 , n = -1.11022302463e-14 !)
         if n >= 0:
            y = math.sqrt(n)
            p = QgsPointXY(x, y)
            # verifico se il punto va bene
            # calcolo la tangente su quel punto
            t = e.getTanDirectionOnPt(p)
            # se è perpendicolare con il segmento che unisce il punto trovato con quello fornito (myPoint)
            angSegment = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(p, myPoint) + math.pi / 2)
            if qad_utils.doubleNear(t, angSegment) or qad_utils.doubleNear(qad_utils.normalizeAngle(t + math.pi), angSegment):
               # traslo e ruoto il punto per riportarlo nella posizione originale (con il centro e la rotazione dell'ellisse originale)
               p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
               qad_utils.appendUniquePointToList(result, p)
               
            # verifico l'altra coordinata y
            p = QgsPointXY(x, -y)
            # verifico se il punto va bene
            # calcolo la tangente su quel punto
            t = e.getTanDirectionOnPt(p)
            # se è perpendicolare con il segmento che unisce il punto trovato con quello fornito (myPoint)
            angSegment = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(p, myPoint) + math.pi / 2)
            if qad_utils.doubleNear(t, angSegment) or qad_utils.doubleNear(qad_utils.normalizeAngle(t + math.pi), angSegment):
               # traslo e ruoto il punto per riportarlo nella posizione originale (con il centro e la rotazione dell'ellisse originale)
               p = ellipse.translateAndRotatePtForNormalEllipse(p, True)
               qad_utils.appendUniquePointToList(result, p)

      return result


   # ===============================================================================
   # metodi per le ellissi - fine
   # metodi per gli archi di ellisse - inizio
   # ===============================================================================


   # ============================================================================
   # fromPointToEllipseArc
   # ============================================================================
   @staticmethod   
   def fromPointToEllipseArc(pt, ellipseArc):
      """
      la funzione ritorna la proiezione perpendicolare di punto su un arco di ellisse
      """
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      perpPtList = QadPerpendicularity.fromPointToEllipse(pt, ellipse)
      for perpPt in perpPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(perpPt):
            result.append(perpPt)
      return result


   # ============================================================================
   # fromPointToBasicGeomObject
   # ============================================================================
   @staticmethod   
   def fromPointToBasicGeomObject(pt, object):
      """
      la funzione ritorna la proiezione perpendicolare di punto su un oggetto geometrico di base:
      linea, arco, arco di ellisse, cerchio, ellisse.
      """
      if object.whatIs() == "LINE":
         res = QadPerpendicularity.fromPointToLine(pt, object)
         return [] if res is None else [res]
      elif object.whatIs() == "CIRCLE":
         return QadPerpendicularity.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         return QadPerpendicularity.fromPointToArc(pt, object)
      elif object.whatIs() == "ELLIPSE":
         return QadPerpendicularity.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         return QadPerpendicularity.fromPointToEllipseArc(pt, object)
         
      return []


   # ============================================================================
   # fromPointToBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def fromPointToBasicGeomObjectExtensions(pt, object):
      """
      la funzione ritorna le proiezioni perpendicolari di punto su una estensione di un oggetto geometrico di base:
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      """      
      if object.whatIs() == "LINE":
         res = QadPerpendicularity.fromPointToInfinityLine(pt, object)
         return [] if res is None else [res]
      elif object.whatIs() == "CIRCLE":
         return QadPerpendicularity.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object.center, object.radius)
         return QadPerpendicularity.fromPointToCircle(pt, circle)
      elif object.whatIs() == "ELLIPSE":
         return QadPerpendicularity.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object.center, object.majorAxisFinalPt, object.axisRatio)
         return QadPerpendicularity.fromPointToEllipse(pt, ellipse)
         
      return []


   # ============================================================================
   # fromPointToGeomObject
   # ============================================================================
   @staticmethod   
   def fromPointToGeomObject(pt, object):
      """
      la funzione ritorna la proiezione perpendicolare di punto su un oggetto geometrico
      """
      geomType = object.whatIs()
      result = []
      
      if geomType == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToBasicGeomObject(pt, linearObj))
            
      elif geomType == "POLYLINE":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToBasicGeomObject(pt, linearObj))
            
      elif geomType == "POLYGON":
         for subGeomAt in range(0, object.qty()):
            closedObj = object.getClosedObjectAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToGeomObject(pt, closedObj))            
         
      elif geomType == "MULTI_POLYGON":
         for geomAt in range(0, object.qty()):
            polygon = object.getPolygonAt(geomAt)
            result.extend(QadPerpendicularity.fromPointToGeomObject(pt, polygon))
         
      # oggetto è una geometria base
      else:
         result.extend(QadPerpendicularity.fromPointToBasicGeomObject(pt, object))
   
      return result


# ===============================================================================
# QadMinDistance class
# rappresenta una classe che calcola la minima distanza tra oggetti di base: punto, linea, arco, arco di ellisse, cerchio, ellisse
# ===============================================================================
class QadMinDistance():
    
   def __init__(self):
      pass


   # ===============================================================================
   # metodi per le linee infinite - inizio
   # ===============================================================================


   # ===============================================================================
   # fromInfinityLineToPoint
   # ===============================================================================
   @staticmethod   
   def fromInfinityLineToPoint(infinityLine, pt):
      """
      la funzione ritorna la distanza minima e il punto di distanza minima tra una linea infinita ed un punto
      (<distanza minima><punto di distanza minima>)
      """
      if infinityLine.isPtOnInfinityLine(pt) == True:
         return [0, pt]
      perpPt = QadPerpendicularity.fromPointToInfinityLine(pt, infinityLine)
      return [qad_utils.getDistance(perpPt, pt), perpPt]
   

   # ===============================================================================
   # fromInfinityLineToLine
   # ===============================================================================
   @staticmethod   
   def fromInfinityLineToLine(infinityLine, line):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra una linea infinita ed un segmento
      (<distanza minima><punto di distanza minima su linea infinita><punto di distanza minima su segmento>)
      """
      intPt = QadIntersections.infinityLineWithLine(infinityLine, line)
      if intPt is not None:
         return [0, intPt, intPt]

      # ritorna una lista: (<distanza minima><punto di distanza minima>)
      dist, ptLine = QadMinDistance.fromInfinityLineToPoint(infinityLine, line.pt1)
      bestResult = [dist, ptLine, line.pt1]
      
      dist, ptLine = QadMinDistance.fromInfinityLineToPoint(infinityLine, line.pt2)
      if bestResult[0] > dist:
         bestResult = [dist, ptLine, line.pt2]
         
      return bestResult[0], bestResult[1], bestResult[2]


   # ===============================================================================
   # fromInfinityLineToCircle
   # ===============================================================================
   @staticmethod   
   def fromInfinityLineToCircle(infinityLine, circle):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra una linea infinita ed un cerchio
      (<distanza minima><punto di distanza minima su linea infinita><punto di distanza minima su cerchio>)
      """
      intPts = QadIntersections.infinityLineWithCircle(infinityLine, circle)
      if len(intPts) > 0:
         return [0, intPts[0], intPts[0]]

      perpPt = QadPerpendicularity.fromPointToInfinityLine(circle.center, infinityLine)
      angle = qad_utils.getAngleBy2Pts(circle.center, perpPt)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      
      return [qad_utils.getDistance(perpPt, ptOnCircle), perpPt, ptOnCircle]


   # ===============================================================================
   # fromInfinityLineToArc
   # ===============================================================================
   @staticmethod   
   def fromInfinityLineToArc(infinityLine, arc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra una linea infinita ed un arco
      (<distanza minima><punto di distanza minima su linea infinita><punto di distanza minima su arco>)
      """
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      result = QadMinDistance.fromInfinityLineToCircle(infinityLine, circle)
      ptArc = result[2]
      if arc.isPtOnArcOnlyByAngle(ptArc):
         return result
      
      d1 = qad_utils.getDistance(arc.gtStartPt(), ptOnCircle)
      res1 = QadMinDistance.fromInfinityLineToPoint(infinityLine, arc.getStartPt())
      res2 = QadMinDistance.fromInfinityLineToPoint(infinityLine, arc.getEndPt())
      if res1[0] < res2[0]:
         return [res1[0], res1[1], arc.getStartPt()]
      else:
         return [res2[0], res2[1], arc.getEndPt()]


   @staticmethod
   def distanza_infinityLine_ellipse(params, px, py, dx, dy, a, b, theta, h, k):
      t, phi = params
      # Parametri della retta: punto sulla retta (px, py) e vettore direzione (dx, dy)
      # Parametri dell'ellisse: semiassi a, b, angolo di rotazione theta, centro (h, k)
      # px, py, a, b, theta, h, k = line_ellipse
      # Punto sulla retta
      x_retta = px + t * dx
      y_retta = py + t * dy
      # Punto sull'ellisse (parametrizzato da phi)
      x_ellisse = h + a * np.cos(phi) * np.cos(theta) - b * np.sin(phi) * np.sin(theta)
      y_ellisse = k + a * np.cos(phi) * np.sin(theta) + b * np.sin(phi) * np.cos(theta)
      # Distanza quadratica
      distanza2 = (x_retta - x_ellisse)**2 + (y_retta - y_ellisse)**2
      return distanza2


   # ===============================================================================
   # fromInfinityLineToEllipse chatgpt
   # ===============================================================================
   @staticmethod
   def fromInfinityLineToEllipse(line, ellipse):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra una linea infinita ed un'ellisse
      (<distanza minima><punto di distanza minima su linea infinita><punto di distanza minima su ellisse>)
      """
      if NO_SCIPY == True: return []
      
      # test
#       line = QadLine()
#       line.set(QgsPointXY(1,1), QgsPointXY(2, 1))
# 
#       ellipse = QadEllipse()      
#       center = QgsPointXY(2, 1)
#       angle = np.pi / 6  # 30 gradi
#       a = 5
#       b = 3
#       majorAxisFinalPt = qad_utils.getPolarPointByPtAngle(center, angle, a)
#       ellipse.set(center, majorAxisFinalPt, b / a)
      
      
      
      # Parametri della retta: punto sulla retta (px, py) e vettore direzione (dx, dy)
      px, py = line.getStartPt().x(), line.getStartPt().y()
      dx, dy = line.getEndPt().x() - px, line.getEndPt().y() - py
      
      # Calcola la lunghezza dell'asse maggiore (a)
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt)
      # Calcola la lunghezza dell'asse minore (b)
      b = a * ellipse.axisRatio      
      # theta: l'angolo di rotazione dell'ellisse.
      theta = ellipse.getRotation()
      # h e k: le traslazioni dell'ellisse rispetto all'origine, coordinate centro
      h = ellipse.center.x()
      k = ellipse.center.y()      

      args = (px, py,  dx, dy, a, b, theta, h, k)
      
      # Stima iniziale per t e phi
      stima_iniziale = [0, 0]

      # Minimizzazione della funzione di distanza quadratica
      risultato = minimize(QadMinDistance.distanza_infinityLine_ellipse, stima_iniziale, args, method='Nelder-Mead')

      # Estrazione dei risultati
      t_min, phi_min = risultato.x
      
      # Calcolo dei punti di minima distanza
      x_retta_min = px + t_min * dx
      y_retta_min = py + t_min * dy
      x_ellisse_min = h + a * np.cos(phi_min) * np.cos(theta) - b * np.sin(phi_min) * np.sin(theta)
      y_ellisse_min = k + a * np.cos(phi_min) * np.sin(theta) + b * np.sin(phi_min) * np.cos(theta)
      
      ptRetta = QgsPointXY(x_retta_min, y_retta_min)
      ptEllisse = QgsPointXY(x_ellisse_min, y_ellisse_min)
      
      return qad_utils.getDistance(ptRetta, ptEllisse), ptRetta, ptEllisse



   # ===============================================================================
   # fromInfinityLineToEllipseArc
   # ===============================================================================
   @staticmethod   
   def fromInfinityLineToEllipseArc(line, ellipseArc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra una linea infinita ed un arco di ellisse
      (<distanza minima><punto di distanza minima su linea infinita><punto di distanza minima su un arco di ellisse>)
      """
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      result = QadMinDistance.fromInfinityLineToEllipse(infinityLine, ellipse)
      ptArc = result[2]
      if ellipseArc.isPtOnEllipseArcOnlyByAngle(ptArc):
         return result
      
      d1 = qad_utils.getDistance(arc.gtStartPt(), ptOnCircle)
      res1 = QadMinDistance.fromInfinityLineToPoint(infinityLine, ellipseArc.getStartPt())
      res2 = QadMinDistance.fromInfinityLineToPoint(infinityLine, ellipseArc.getEndPt())
      if res1[0] < res2[0]:
         return [res1[0], res1[1], ellipseArc.getStartPt()]
      else:
         return [res2[0], res2[1], ellipseArc.getEndPt()]


   # ===============================================================================
   # metodi per le linee infinite - fine
   # metodi per i segmenti - inizio
   # ===============================================================================


   # ===============================================================================
   # fromLineToPoint
   # ===============================================================================
   @staticmethod   
   def fromLineToPoint(line, pt):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un segmento ed un punto
      (<distanza minima><punto di distanza minima>)
      """
      if line.containsPt(pt) == True:
         return [0, pt]
      perpPt = QadPerpendicularity.fromPointToInfinityLine(pt, line)
      if perpPt is not None:
         if line.containsPt(perpPt) == True:
            return [qad_utils.getDistance(perpPt, pt), perpPt]
   
      distFromP1 = qad_utils.getDistance(line.pt1, pt)
      distFromP2 = qad_utils.getDistance(line.pt2, pt)
      if distFromP1 < distFromP2:
         return [distFromP1, line.pt1]
      else:
         return [distFromP2, line.pt2]


   # ===============================================================================
   # fromTwoLines
   # ===============================================================================
   @staticmethod
   def fromTwoLines(line1, line2):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra 2 segmenti
      (<distanza minima><punto di distanza minima su segmento1><punto di distanza minima su segmento2>)
      """
      intPt = QadIntersections.twoLines(line1, line2)
      if intPt is not None:
         return [0, intPt, intPt]
   
      # ritorna una lista: (<distanza minima><punto di distanza minima>)
      result = QadMinDistance.fromLineToPoint(line2, line1.pt1)
      dist = result[0]
      ptLine = result[1]
      bestResult = [dist, line1.pt1, ptLine]
      
      result = QadMinDistance.fromLineToPoint(line2, line1.pt2)
      dist = result[0]
      ptLine = result[1]
      if bestResult[0] > dist:
         bestResult = [dist, line1.pt2, ptLine]
         
      result = QadMinDistance.fromLineToPoint(line1, line2.pt1)
      dist = result[0]
      ptLine = result[1]
      if bestResult[0] > dist:
         bestResult = [dist, ptLine, line2.pt1]

      result = QadMinDistance.fromLineToPoint(line1, line2.pt2)
      dist = result[0]
      ptLine = result[1]
      if bestResult[0] > dist:
         bestResult = [dist, ptLine, line2.pt2]

      return [bestResult[0], bestResult[1], bestResult[2]]


   # ===============================================================================
   # fromLineToCircle
   # ===============================================================================
   @staticmethod
   def fromLineToCircle(line, circle):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un segmento ed un cerchio
      (<distanza minima><punto di distanza minima su linea><punto di distanza minima su cerchio>)
      """
      intPts = QadIntersections.lineWithCircle(line, circle)
      if len(intPts) > 0:
         return [0, intPts[0], intPts[0]]

      d1 = qad_utils.getDistance(line.getStartPt(), circle.center)
      if d1 < circle.radius: # linea interna al cerchio
         d2 = qad_utils.getDistance(line.getEndPt(), circle.center)
         if d1 > d2:
            ptLine = line.getStartPt()
         else:
            ptLine = line.getEndPt()
      else: # linea esterna al cerchio
         result = QadMinDistance.fromInfinityLineToCircle(line, circle)
         if line.containsPt(result[1]):
            return result
         else:
            d2 = qad_utils.getDistance(line.getEndPt(), circle.center)
            if d1 < d2:
               ptLine = line.getStartPt()
            else:
               ptLine = line.getEndPt()

      angle = qad_utils.getAngleBy2Pts(circle.center, ptLine)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      
      return [qad_utils.getDistance(ptLine, ptOnCircle), ptLine, ptOnCircle]


   # ===============================================================================
   # fromLineToArc
   # ===============================================================================
   @staticmethod
   def fromLineToArc(line, arc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un segmento ed un arco
      (<distanza minima><punto di distanza minima su linea><punto di distanza minima su arco>)
      """
      intPtList = QadIntersections.lineWithArc(line, arc)
      if len(intPtList) > 0:
         return [0, intPtList[0], intPtList[0]]

      p1Line = line.getStartPt()
      p2Line = line.getEndPt()
      resultP1 = QadMinDistance.fromArcToPoint(arc, p1Line) # ritorna (<distanza minima><punto di distanza minima su arco>)
      resultP2 = QadMinDistance.fromArcToPoint(arc, p2Line) # ritorna (<distanza minima><punto di distanza minima su arco>)
      
      # se il segmento é interno al cerchio orginato dall'estensione dell'arco
      if qad_utils.getDistance(p1Line, arc.center) < arc.radius and \
         qad_utils.getDistance(p2Line, arc.center) < arc.radius:
         if resultP1[0] < resultP2[0]: # se il punto iniziale della linea è più vicino all'arco
            return [resultP1[0], p1Line, resultP1[1]]
         else:
            return [resultP2[0], p2Line, resultP2[1]]
      
      else: # se il segmento é esterno al cerchio orginato dall'estensione dell'arco
         perpPt = QadPerpendicularity.fromPointToLine(arc.center, line)
         if perpPt is not None:
            angle = qad_utils.getAngleBy2Pts(arc.center, perpPt)
            # se il punto di perpendicolare al segmento <line> é compreso tra gli angoli dell'arco
            if arc.isAngleBetweenAngles(angle):
               ptOnArc = qad_utils.getPolarPointByPtAngle(arc.center, angle, arc.radius)
               return [qad_utils.getDistance(perpPt, ptOnArc), perpPt, ptOnArc]
         
         bestResult = resultP1 # (<distanza minima><punto di distanza minima su arco>)
         bestResult.insert(1, p1Line) # (<distanza minima><punto di distanza minima su linea><punto di distanza minima su arco>)
         resultP2.insert(1, p2Line)
         if bestResult[0] > resultP2[0]:
            bestResult = resultP2
   
         ptStart = arc.getStartPt()
         ptEnd = arc.getEndPt()
         
         resultStartPt = QadMinDistance.fromLineToPoint(line, ptStart) # (<distanza minima><punto di distanza minima su linea>
         resultStartPt.append(ptStart) # <distanza minima><punto di distanza minima><distanza minimasu linea><punto di distanza minima su arco>
         if bestResult[0] > resultStartPt[0]:
            bestResult = resultStartPt   

         resultEndPt = QadMinDistance.fromLineToPoint(line, ptEnd) # (<distanza minima><punto di distanza minimasu linea>
         resultEndPt.append(ptEnd) # <distanza minima><punto di distanza minima><distanza minimasu linea><punto di distanza minima su arco>
         if bestResult[0] > resultEndPt[0]:
            bestResult = resultEndPt
            
         return bestResult # (<distanza minima><punto di distanza minima su linea><punto di distanza minima su arco>)


   @staticmethod
   def distanza_line_ellipse(params, line, ellipse):
      t, theta = params
      x_segment = (1 - t) * line.getStartPt().x() + t * line.getEndPt().x()
      y_segment = (1 - t) * line.getStartPt().y() + t * line.getEndPt().y()
      
      pt_ellipse = ellipse.getPointAtAngle(theta)
      x_ellipse = pt_ellipse.x()
      y_ellipse = pt_ellipse.y()
        
      return np.sqrt((x_segment - x_ellipse) ** 2 + (y_segment - y_ellipse) ** 2)
   

   # ===============================================================================
   # fromLineToEllipse chatgpt
   # ===============================================================================
   @staticmethod
   def fromLineToEllipse(line, ellipse):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un segmento ed un'ellisse
      (<distanza minima><punto di distanza minima su linea><punto di distanza minima su ellisse>)
      """
      if NO_SCIPY == True: return []
      
      initial_guess = [0.5, 0]
      bounds = [(0, 1), (0, 2 * np.pi)]
    
      args = (line, ellipse)
      
      result = minimize(QadMinDistance.distanza_line_ellipse, initial_guess, args, bounds=bounds)
      
      if result.success:
        t_opt, theta_opt = result.x
        x_segment_opt = (1 - t_opt) * line.getStartPt().x() + t_opt * line.getEndPt().x()
        y_segment_opt = (1 - t_opt) * line.getStartPt().y() + t_opt * line.getEndPt().y()
        
        pt_ellipse = ellipse.getPointAtAngle(theta_opt)
        x_ellipse_opt = pt_ellipse.x()
        y_ellipse_opt = pt_ellipse.y()
        
        min_distance = result.fun
        
        return [min_distance, QgsPointXY(x_segment_opt, y_segment_opt), QgsPointXY(x_ellipse_opt, y_ellipse_opt)]
      else:
         raise []     

     
   # ===============================================================================
   # fromLineToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromLineToEllipseArc(line, ellipseArc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un segmento ed un arco di ellisse
      (<distanza minima><punto di distanza minima su linea><punto di distanza minima su arco di ellisse>)
      """
    
      pass # da fare


   # ===============================================================================
   # metodi per i segmenti - fine
   # metodi per i cerchi - inizio
   # ===============================================================================


   # ===============================================================================
   # fromCircleToPoint
   # ===============================================================================
   @staticmethod   
   def fromCircleToPoint(circle, pt):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un cerchio ed un punto
      (<distanza minima><punto di distanza minima>)
      """
      angle = qad_utils.getAngleBy2Pts(circle.center, pt)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      
      return [qad_utils.getDistance(pt, ptOnCircle), ptOnCircle]


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def fromTwoCircles(circle1, circle2):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra 2 cerchi
      (<distanza minima><punto di distanza minima su cerchio1><punto di distanza minima su cerchio2>)
      """
      intersections = QadIntersections.twoCircles(circle1, circle2)
      if len(intersections) > 0:
         return [0.0, intersections[0], intersections[0]]
      
      angle = qad_utils.getAngleBy2Pts(circle1.center, circle2.center)
      pt1Circle1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
      pt2Circle1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, -circle1.radius)
      pt1Circle2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, circle2.radius)
      pt2Circle2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, -circle2.radius)
      
      minDistance = qad_utils.getDistance(pt1Circle1, pt1Circle2)
      ptMinDistanceCircle1 = pt1Circle1
      ptMinDistanceCircle2 = pt1Circle2

      dist = qad_utils.getDistance(pt1Circle1, pt2Circle2)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle1 = pt1Circle1
         ptMinDistanceCircle2 = pt2Circle2
         
      dist = qad_utils.getDistance(pt2Circle1, pt1Circle2)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle1 = pt2Circle1
         ptMinDistanceCircle2 = pt1Circle2
         
      dist = qad_utils.getDistance(pt2Circle1, pt2Circle2)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle1 = pt2Circle1
         ptMinDistanceCircle2 = pt2Circle2

      return [minDistance, ptMinDistanceCircle1, ptMinDistanceCircle2]


   # ===============================================================================
   # fromCircleToArc
   # ===============================================================================
   @staticmethod
   def fromCircleToArc(circle, arc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un cerchio ed un arco
      (<distanza minima><punto di distanza minima su cerchio><punto di distanza minima su arco>)
      """
      intersections = QadIntersections.circleWithArc(circle, arc)
      if len(intersections) > 0:
         return [0.0, intersections[0], intersections[0]]

      pt1Arc = arc.getStartPt()
      pt2Arc = arc.getEndPt()
      
      angle = qad_utils.getAngleBy2Pts(circle.center, pt1Arc)
      ptCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      minDistance = qad_utils.getDistance(ptCircle, pt1Arc)
      ptMinDistanceCircle = ptCircle
      ptMinDistanceArc = pt1Arc      

      angle = qad_utils.getAngleBy2Pts(circle.center, pt2Arc)
      ptCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      dist = qad_utils.getDistance(ptCircle, pt2Arc)
      if dist < minDistance:
         minDistance = dist
         ptMinDistanceCircle = ptCircle
         ptMinDistanceArc = pt2Arc
                
      line = QadLine()
      line.set(circle.center, arc.center)
      intersections = QadIntersections.infinityLineWithArc(line, arc)
      if len(intersections) > 0:
         angle = qad_utils.getAngleBy2Pts(circle.center, arc.center)
         ptCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
         dist = qad_utils.getDistance(ptCircle, intersections[0])
         if dist < minDistance:
            minDistance = dist
            ptMinDistanceCircle = ptCircle
            ptMinDistanceArc = intersections[0]
      
      return [minDistance, ptMinDistanceCircle, ptMinDistanceArc]


   # ===============================================================================
   # fromCircleToEllipse
   # ===============================================================================
   @staticmethod
   def fromCircleToEllipse(circle, ellipse):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un cerchio ed un'ellisse
      (<distanza minima><punto di distanza minima su cerchio><punto di distanza minima su ellisse>)
      """
      pass # da fare


   # ===============================================================================
   # fromCircleToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromCircleToEllipseArc(circle, ellipseArc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un cerchio ed un arco di ellisse
      (<distanza minima><punto di distanza minima su cerchio><punto di distanza minima su arco di ellisse>)
      """
      pass # da fare


   # ===============================================================================
   # metodi per i cerchi - fine
   # metodi per gli archi - inizio
   # ===============================================================================


   # ===============================================================================
   # fromArcToPoint
   # ===============================================================================
   @staticmethod   
   def fromArcToPoint(arc, pt):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un arco ed un punto
      (<distanza minima><punto di distanza minima>)
      """
      if arc.isPtOnArcOnlyByAngle(pt):
         circle = QadCircle()
         circle.set(arc.center, arc.radius)
         return QadMinDistance.fromCircleToPoint(circle, pt)
      else:
         p1 = arc.getStartPt()
         p2 = arc.getEndPt()
         d1 = qad_utils.getDistance(p1, pt)
         d2 = qad_utils.getDistance(p2, pt)
         if d1 < d2:
            return [d1, p1]
         else:
            return [d2, p2]
         
      angle = qad_utils.getAngleBy2Pts(circle.center, pt)
      ptOnCircle = qad_utils.getPolarPointByPtAngle(circle.center, angle, circle.radius)
      
      return [qad_utils.getDistance(pt, ptOnCircle), ptOnCircle]


   # ===============================================================================
   # fromTwoArcs
   # ===============================================================================
   @staticmethod
   def fromTwoArcs(arc1, arc2):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra 2 archi
      (<distanza minima><punto di distanza minima su arco1><punto di distanza minima su arco2>)
      """
      intPtList = QadIntersections.twoArcs(arc1, arc2)
      if len(intPtList) > 0:
         return [0, intPtList[0], intPtList[0]]
      
      StartPtArc1 = arc1.getStartPt()
      EndPtArc1 = arc1.getEndPt()     
      StartPtArc2 = arc2.getStartPt()
      EndPtArc2 = arc2.getEndPt()     
      
      # calcolo la minima distanza tra gli estremi di un arco e l'altro arco e 
      # scelgo la migliore tra le quattro distanze
      # ritorna una lista: (<minima distanza><punto più vicino>)
      dummy = QadMinDistance.fromArcToPoint(arc2, StartPtArc1)
      bestResult = [dummy[0], StartPtArc1, dummy[1]]

      dummy = QadMinDistance.fromArcToPoint(arc2, EndPtArc1)
      resultArc2_EndPtArc1 = [dummy[0], EndPtArc1, dummy[1]]
      if bestResult[0] > resultArc2_EndPtArc1[0]:
         bestResult = resultArc2_EndPtArc1
            
      dummy = QadMinDistance.fromArcToPoint(arc1, StartPtArc2)
      resultArc1_StartPtArc2 = [dummy[0], dummy[1], StartPtArc2]
      if bestResult[0] > resultArc1_StartPtArc2[0]:
         bestResult = resultArc1_StartPtArc2
            
      dummy = QadMinDistance.fromArcToPoint(arc1, EndPtArc2)
      resultArc1_EndPtArc2 = [dummy[0], dummy[1], EndPtArc2]
      if bestResult[0] > resultArc1_EndPtArc2[0]:
         bestResult = resultArc1_EndPtArc2   

      # il cerchio1 e il cerchio 2 sono derivati rispettivamente dall'estensione dell'arco1 e arco2.
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)
      distanceBetweenCenters = qad_utils.getDistance(circle1.center, circle2.center)
      
      # considero i seguenti 2 casi:
      # i cerchi sono esterni
      if distanceBetweenCenters - circle1.radius - circle2.radius > 0:
         # creo un segmento che unisce i due centri e lo interseco con l'arco 1
         l = QadLine()
         l.set(arc1.center, arc2.center)
         intPtListArc1 = QadIntersections.lineWithArc(l, arc1)
         if len(intPtListArc1) > 0:
            intPtArc1 = intPtListArc1[0]
         
            # creo un segmento che unisce i due centri e lo interseco con l'arco 2
            intPtListArc2 = QadIntersections.lineWithArc(l, arc2)
            if len(intPtListArc2) > 0:
               intPtArc2 = intPtListArc2[0]
               
               distanceIntPts = qad_utils.getDistance(intPtArc1, intPtArc2)
               if bestResult[0] > distanceIntPts:
                  bestResult = [distanceIntPts, intPtArc1, intPtArc2]
      # il cerchio1 é interno al cerchio2 oppure
      # il cerchio2 é interno al cerchio1
      elif distanceBetweenCenters + circle1.radius < circle2.radius or \
           distanceBetweenCenters + circle2.radius < circle1.radius:
         # creo un segmento che unisce i due centri e lo interseco con l'arco 2
         l = QadLine()
         l.set(arc1.center, arc2.center)
         intPtListArc2 = QadIntersections.infinityLineWithArc(l, arc2)
         if len(intPtListArc2) > 0:
            # creo un segmento che unisce i due centri e lo interseco con l'arco 1
            intPtListArc1 = QadIntersections.infinityLineWithArc(l, arc1)
   
            for intPtArc2 in intPtListArc2:
               for intPtArc1 in intPtListArc1:
                  distanceIntPts = qad_utils.getDistance(intPtArc2, intPtArc1)
                  if bestResult[0] > distanceIntPts:
                     bestResult = [distanceIntPts, intPtArc1, intPtArc2]                                         
   
      return bestResult


   # ===============================================================================
   # fromArcToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromArcToEllipseArc(arc, ellipseArc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un arco ed un arco di ellisse
      (<distanza minima><punto di distanza minima su arco><punto di distanza minima su arco di ellisse>)
      """
      pass # da fare


   # ===============================================================================
   # metodi per gli archi - fine
   # metodi per le ellissi - inizio
   # ===============================================================================


   # ===============================================================================
   # fromEllipseToPoint
   # ===============================================================================
   @staticmethod   
   def fromEllipseToPoint(ellipse, pt):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un'ellisse ed un punto
      (<distanza minima><punto di distanza minima>)
      """
      perpPts = QadPerpendicularity.fromPointToEllipse(pt, ellipse)
      dist = sys.float_info.max
      for perpPt in perpPts:
         d = qad_utils.getDistance(pt, perpPt)
         if d < dist:
            dist = d
            bestPt = perpPt
            
      return [dist, bestPt]

   
   # ===============================================================================
   # fromTwoEllipses
   # ===============================================================================
   @staticmethod
   def fromTwoEllipses(ellipse1, ellipse2):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra 2 ellissi
      (<distanza minima><punto di distanza minima su ellisse1><punto di distanza minima su ellisse2>)
      """
      pass # da fare


   # ===============================================================================
   # fromEllipseToArc
   # ===============================================================================
   @staticmethod
   def fromEllipseToArc(ellipse, arc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un'ellisse ed un arco
      (<distanza minima><punto di distanza minima su ellisse><punto di distanza minima su arco>)
      """
      pass # da fare


   # ===============================================================================
   # fromEllipseToEllipseArc
   # ===============================================================================
   @staticmethod
   def fromEllipseToEllipseArc(ellipse, ellipseArc):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un'ellisse ed un arco di ellisse
      (<distanza minima><punto di distanza minima su ellisse><punto di distanza minima su arco di ellisse>)
      """
      pass # da fare


   # ===============================================================================
   # metodi per le ellissi - fine
   # metodi per gli archi di ellisse - inizio
   # ===============================================================================


   # ===============================================================================
   # fromEllipseArcToPoint
   # ===============================================================================
   @staticmethod   
   def fromEllipseArcToPoint(ellipseArc, pt):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra un arco di ellisse ed un punto
      (<distanza minima><punto di distanza minima>)
      """
      perpPts = QadPerpendicularity.fromPointToEllipseArc(pt, ellipseArc)
      dist = sys.float_info.max
      for perpPt in perpPts:
         d = qad_utils.getDistance(pt, perpPt)
         if d < dist:
            dist = d
            bestPt = perpPt
            
      if dist < sys.float_info.max: return [dist, bestPt]
      
      d1 = qad_utils.getDistance(pt, ellipseArc.getStartPt())
      d2 = qad_utils.getDistance(pt, ellipseArc.getEndPt())
      
      if d1 < d2:
         return [d1, ellipseArc.getStartPt()]
      else:
         return [d2, ellipseArc.getEndPt()]


   # ===============================================================================
   # fromTwoEllipseArcs
   # ===============================================================================
   @staticmethod
   def fromTwoEllipseArcs(ellipseArc1, ellipseArc2):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima tra 2 archi di ellisse
      (<distanza minima><punto di distanza minima su arco ellisse1><punto di distanza minima su arco di ellisse2>)
      """
      pass # da fare


   # ============================================================================
   # fromPointToBasicGeomObject
   # ============================================================================
   @staticmethod   
   def fromPointToBasicGeomObject(pt, object):
      """
      la funzione ritorna la distanza minima e il punto di distanza minima tra un oggetto geometrico di base ed un punto
      (<distanza minima><punto di distanza minima>)
      """
      if object.whatIs() == "POINT":
         return (object.distance(pt), object)
      elif object.whatIs() == "LINE":
         return QadMinDistance.fromLineToPoint(object, pt)
      elif object.whatIs() == "CIRCLE":
         return QadMinDistance.fromCircleToPoint(object, pt)
      elif object.whatIs() == "ARC":
         return QadMinDistance.fromArcToPoint(object, pt)
      elif object.whatIs() == "ELLIPSE":
         return QadMinDistance.fromEllipseToPoint(object, pt)
      elif object.whatIs() == "ELLIPSE_ARC":
         return QadMinDistance.fromEllipseArcToPoint(object, pt)
         
      return []


   # ============================================================================
   # fromPointToBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def fromPointToBasicGeomObjectExtensions(pt, object):
      """
      la funzione ritorna la distanza minima e il punto di distanza minima tra una estensione di oggetto geometrico di base ed un punto
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      """      
      if object.whatIs() == "LINE":
         return QadMinDistance.fromInfinityLineToPoint(object, pt)
      elif object.whatIs() == "CIRCLE":
         return QadMinDistance.fromCircleToPoint(object, pt)
      elif object.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object.center, object.radius)
         return QadMinDistance.fromCircleToPoint(circle, pt)
      elif object.whatIs() == "ELLIPSE":
         return QadMinDistance.fromEllipseToPoint(object, pt)
      elif object.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object.center, object.majorAxisFinalPt, object.axisRatio)
         return QadMinDistance.fromEllipseToPoint(object, pt)
         
      return []


   # ============================================================================
   # fromTwoBasicGeomObjects
   # ============================================================================
   @staticmethod   
   def fromTwoBasicGeomObjects(object1, object2):
      """
      la funzione ritorna 
      <distanza minima>
      <punto di distanza minima su object1>
      <punto di distanza minima su object2>
      dei 2 oggetti geometrici di base: linea, arco, arco di ellisse, cerchio, ellisse.
      """      
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            # <distanza minima><punto di distanza minima su segmento1><punto di distanza minima su segmento2>
            return QadMinDistance.fromTwoLines(object1, object2)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromLineToCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromLineToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromLineToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromLineToEllipseArc(object1, object2)
         
      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromTwoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromCircleToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromCircleToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromCircleToEllipseArc(object1, object2)
         
      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromTwoArcs(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromEllipseToArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromArcToEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromEllipseToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromTwoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromEllipseToEllipseArc(object1, object2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromLineToEllipseArc(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipseArc(object2, object1)
         elif object2.whatIs() == "ARC":
            return QadMinDistance.fromArcToEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromEllipseToEllipseArc(object2, object1)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromTwoEllipseArcs(object1, object2)
   
      return []


   # ============================================================================
   # fromTwoGeomObjects
   # ============================================================================
   @staticmethod   
   def fromTwoGeomObjects(object1, object2):
      """
      la funzione ritorna 
      <distanza minima>
      <punto di distanza minima su object1>
      <geomIndex su object1>
      <subGeomIndex su object1>
      <partIndex su object1>
      <punto di distanza minima su object2>
      <geomIndex su object2>
      <subGeomIndex su object2>
      <partIndex su object2>
      dei 2 oggetti geometrici.
      """
      minDistancePts = None
      geomType1 = object1.whatIs()
      
      if geomType1 == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getLinearObjectAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
            
      elif geomType1 == "POLYLINE":
         for partAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getLinearObjectAt(partAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[4] = partAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[4] = partAt
            
      elif geomType1 == "POLYGON":
         for subGeomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getClosedObjectAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[3] = subGeomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[3] = subGeomAt
         
      elif geomType1 == "MULTI_POLYGON":
         for geomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getPolygonAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
         
      elif geomType1 == "MULTI_POINT":
         for geomAt in range(0, object1.qty()):
            partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object.getPointAt(geomAt), object2)
            if minDistancePts is None:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
            elif partialMinDistancePts[0] < minDistancePts[0]:
               minDistancePts = partialMinDistancePts
               minDistancePts[2] = geomAt
         
      # oggetto1 è una geometria base
      else:
         geomType2 = object2.whatIs()
         
         if geomType2 == "MULTI_LINEAR_OBJ":
            for geomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getLinearObjectAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
               
         elif geomType2 == "POLYLINE":
            for partAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getLinearObjectAt(partAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[8] = partAt                  
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[8] = partAt                  
               
         elif geomType2 == "POLYGON":
            for subGeomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getClosedObjectAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[7] = subGeomAt                  
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[7] = subGeomAt                  
            
         elif geomType2 == "MULTI_POLYGON":
            for geomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getPolygonAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
            
         elif geomType2 == "MULTI_POINT":
            for geomAt in range(0, object2.qty()):
               partialMinDistancePts = QadMinDistance.fromTwoGeomObjects(object1, object2.getPointAt(geomAt))
               if minDistancePts is None:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt
               elif partialMinDistancePts[0] < minDistancePts[0]:
                  minDistancePts = partialMinDistancePts
                  minDistancePts[6] = geomAt

         # oggetto2 è una geometria base (e anche oggetto1 era una geometria base)
         else:            
            dummy = QadMinDistance.fromTwoBasicGeomObjects(object1, object2)
            minDistancePts = [dummy[0], dummy[1], 0, 0, 0, dummy[2], 0, 0, 0,]    
            
      return minDistancePts
      

   # ============================================================================
   # twoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def fromTwoBasicGeomObjectExtensions(object1, object2):
      """
      la funzione ritorna la distanza minima e i punti di distanza minima delle estensioni di 2 oggetti geometrici di base:
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      """      
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromInfinityLineToCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadMinDistance.fromInfinityLineToArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromInfinityLineToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return QadMinDistance.fromInfinityLineToEllipseArc(object1, object2)
         
      elif object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToCircle(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromTwoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadMinDistance.fromCircleToArc(object1, circle)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromCircleToEllipse(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromCircleToEllipse(object1, ellipse)
         
      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToCircle(object2, circle1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromTwoCircles(object2, circle1)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadMinDistance.fromTwoCircles(circle1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromCircleToEllipse(circle1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromCircleToEllipse(circle1, ellipse)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToEllipse(object2, object1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipse(object2, object1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return QadMinDistance.fromCircleToEllipse(circle, object1)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromTwoEllipses(object1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromEllipseToEllipseArc(object1, ellipse)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "LINE":
            return QadMinDistance.fromInfinityLineToEllipse(object2, ellipse1)
         elif object2.whatIs() == "CIRCLE":
            return QadMinDistance.fromCircleToEllipse(object2, ellipse1)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object.center, object.radius)
            return QadMinDistance.fromCircleToEllipse(circle, ellipse1)
         elif object2.whatIs() == "ELLIPSE":
            return QadMinDistance.fromTwoEllipses(ellipse1, object2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return QadMinDistance.fromTwoEllipseArcs(ellipse1, ellipse2)
   
      return []


# ===============================================================================
# QadTangency class
# rappresenta una classe che calcola la tangenza tra oggetti di base: punto, linea, cerchio, arco, ellisse, arco di ellisse
# ===============================================================================
class QadTangency():
    
   def __init__(self):
      pass


   # ===============================================================================
   # metodi per i cerchi - inizio
   # ===============================================================================


   # ===============================================================================
   # fromPointToCircle
   # ===============================================================================
   @staticmethod   
   def fromPointToCircle(point, circle):
      """
      la funzione ritorna una lista punti di tangenza sul cerchio di linee passanti per un punto
      """
      dist = circle.center.distance(point)
      if dist < circle.radius: return []
      
      angleOffSet = math.asin(circle.radius / dist)
      angleOffSet = (math.pi / 2) - angleOffSet
      angle = qad_utils.getAngleBy2Pts(circle.center, point)
      
      pt1 = qad_utils.getPolarPointByPtAngle(circle.center, angle + angleOffSet, circle.radius)
      pt2 = qad_utils.getPolarPointByPtAngle(circle.center, angle - angleOffSet, circle.radius)
      return [pt1, pt2]


   # ============================================================================
   # twoCircles
   # ============================================================================
   @staticmethod   
   def twoCircles(circle1, circle2):
      """
      la funzione ritorna una lista di linee che sono le tangenti ai due cerchi
      """      
      x1 = circle1.center[0]
      y1 = circle1.center[1]
      r1 = circle1.radius
      x2 = circle2.center[0]
      y2 = circle2.center[1]
      r2 = circle2.radius

      d_sq = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2)
      if (d_sq <= (r1-r2)*(r1-r2)):
          return []
 
      d = math.sqrt(d_sq);
      vx = (x2 - x1) / d;
      vy = (y2 - y1) / d;
 
      tangents = []
      # Let A, B be the centers, and C, D be points at which the tangent
      # touches first and second circle, and n be the normal vector to it.
      #
      # We have the system:
      #   n * n = 1          (n is a unit vector)          
      #   C = A + r1 * n
      #   D = B +/- r2 * n
      #   n * CD = 0         (common orthogonality)
      #
      # n * CD = n * (AB +/- r2*n - r1*n) = AB*n - (r1 -/+ r2) = 0,  <=>
      # AB * n = (r1 -/+ r2), <=>
      # v * n = (r1 -/+ r2) / d,  where v = AB/|AB| = AB/d
      # This is a linear equation in unknown vector n.
      sign1 = +1
      while sign1 >= -1:
         c = (r1 - sign1 * r2) / d;
 
         # Now we're just intersecting a line with a circle: v*n=c, n*n=1
 
         if (c*c > 1.0):
            sign1 = sign1 - 2
            continue
         
         h = math.sqrt(max(0.0, 1.0 - c*c));

         sign2 = +1
         while sign2 >= -1:
            nx = vx * c - sign2 * h * vy;
            ny = vy * c + sign2 * h * vx;

            tangent = QadLine()
            tangent.set(QgsPointXY(x1 + r1 * nx, y1 + r1 * ny), \
                        QgsPointXY(x2 + sign1 * r2 * nx, y2 + sign1 * r2 * ny))
            tangents.append(tangent)
            sign2 = sign2 - 2
            
         sign1 = sign1 - 2
 
      return tangents


   # ============================================================================
   # fromCircleToArc
   # ============================================================================
   @staticmethod   
   def fromCircleToArc(circle1, arc2):
      """
      la funzione ritorna una lista di linee che sono le tangenti al cerchio e all'arco
      """
      result = []
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)
      lines = QadTangency.twoCircles(circle1, circle2)
      for line in lines:
         if arc2.isPtOnArcOnlyByAngle(line.getEndPt()):
            result.append(line)
      return result


   # ============================================================================
   # fromCircleToEllipse
   # ============================================================================
   @staticmethod   
   def fromCircleToEllipse(circle1, ellipse2):
      """
      la funzione ritorna una lista di linee che sono le tangenti al cerchio e all'ellisse
      """
      return []


   # ============================================================================
   # fromCircleToEllipseArc
   # ============================================================================
   @staticmethod   
   def fromCircleToEllipseArc(circle1, ellipseArc2):
      """
      la funzione ritorna una lista di linee che sono le tangenti al cerchio e all'arco di ellisse
      """
      result = []
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadTangency.fromCircleToEllipse(circle1, ellipse2)
      for line in lines:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(line.getEndPt()):
            result.append(line)
      return result


   # ===============================================================================
   # metodi per i cerchi - fine
   # metodi per gli archi - inizio
   # ===============================================================================


   # ============================================================================
   # fromPointToArc
   # ============================================================================
   @staticmethod   
   def fromPointToArc(pt, arc):
      """
      la funzione ritorna una lista punti di tangenza sull'arco di linee passanti per un punto
      """
      result = []
      circle = QadCircle()
      circle.set(arc.center, arc.radius)
      tangPtList = QadTangency.fromPointToCircle(pt, circle)
      for tangPt in tangPtList:
         if arc.isPtOnArcOnlyByAngle(tangPt):
            result.append(tangPt)
      return result


   # ============================================================================
   # twoArcs
   # ============================================================================
   @staticmethod   
   def twoArcs(arc1, arc2):
      """
      la funzione ritorna una lista di linee che sono le tangenti ai due archi
      """      
      result = []
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadTangency.fromCircleToArc(circle1, arc2)
      for line in lines:
         if arc1.isPtOnArcOnlyByAngle(line.getStartPt()):
            result.append(line)
      return result


   # ============================================================================
   # fromArcToEllipse
   # ============================================================================
   @staticmethod   
   def fromArcToEllipse(arc1, ellipse2):
      """
      la funzione ritorna una lista di linee che sono le tangenti all'arco e all'ellisse
      """
      result = []
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadTangency.fromCircleToEllipse(circle1, ellipse2)
      for line in lines:
         if arc1.isPtOnArcOnlyByAngle(line.getStartPt()):
            result.append(tangPt)
      return result


   # ============================================================================
   # fromArcToEllipseArc
   # ============================================================================
   @staticmethod   
   def fromArcToEllipseArc(arc1, ellipseArc2):
      """
      la funzione ritorna una lista di linee che sono le tangenti all'arco e all'arco di ellisse
      """
      result = []
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadTangency.fromCircleToEllipseArc(circle1, ellipseArc2)
      for line in lines:
         if arc1.isPtOnArcOnlyByAngle(line.getStartPt()):
            result.append(line)
      return result


   # ===============================================================================
   # metodi per gli archi - fine
   # metodi per le ellissi - inizio
   # ===============================================================================
   
   
   # ============================================================================
   # fromPointToEllipse
   # ============================================================================
   @staticmethod   
   def fromPointToEllipse(pt, ellipse):
      """
      la funzione ritorna una lista punti di tangenza sull'ellisse di linee passanti per un punto
      """
      # https://www3.ul.ie/~rynnet/swconics/TC.htm
      # 1. With the radius set to the major axis, scribe an arc  from F.
      # 2. From P scribe an arc with radius set to F1
      # 3. Where this arc intersects the previous arc drawn, draw the lines back to the focal point F.
      # 4. The points where these lines intersect the curve will be the points of contact of the tangents from point P.
      
      result = []
      line = QadLine()
      # trovo i fuochi
      foci = ellipse.getFocus()
      if len(foci) == 0: return result
      a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) * 2 # asse maggiore
      b = a * ellipse.axisRatio # asse minore
      # punto 1 e 2      
      focus = foci[0] # provo prima con il primo fuoco
      circle1 = QadCircle()
      circle1.set(focus, a)
      circle2 = QadCircle()
      circle2.set(point, qad_utils.getDistance(foci[1], point))
      intPts = QadIntersections.twoCircles(circle1, circle2)      
      if len(intPts) == 0: # se non hanno intersezioni provo l'altro fuoco
         focus = foci[1]
         circle1.set(focus, a)
         circle2.set(point, qad_utils.getDistance(foci[0], point))
         intPts = QadIntersections.twoCircles(circle1, circle2)
         if len(intPts) == 0: # se non hanno intersezioni ciao
            return result
         
      if len(intPts) == 1:
         line.set(focus, intPts[0])
         tgPt1 = QadIntersections.lineWithEllipse(line, ellipse)
         if len(tgPt1) == 0: return result
         result.append(tgPt1[0])
      else:
         line.set(focus, intPts[0])
         tgPt1 = QadIntersections.lineWithEllipse(line, ellipse)
         line.set(focus, intPts[1])
         tgPt2 = QadIntersections.lineWithEllipse(line, ellipse)
         if len(tgPt1) == 0 or len(tgPt2) == 0: return result
         result.append(tgPt1[0])
         result.append(tgPt2[0])
      
      return result


   # ============================================================================
   # twoEllipses
   # ============================================================================
   @staticmethod   
   def twoEllipses(ellipse1, ellipse2):
      """
      la funzione ritorna una lista di linee che sono le tangenti a due ellissi
      """
      # da fare
      return []


   # ============================================================================
   # fromEllipseToEllipseArc
   # ============================================================================
   @staticmethod   
   def fromEllipseToEllipseArc(ellipse1, ellipseArc2):
      """
      la funzione ritorna una lista di linee che sono le tangenti all'ellisse e all'arco di ellisse
      """
      result = []
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadTangency.twoEllipses(ellipse1, ellipse2)
      for line in lines:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(line.getEndPt()):
            result.append(line)
      return result


   # ===============================================================================
   # metodi per le ellissi - fine
   # metodi per gli archi di ellisse - inizio
   # ===============================================================================


   # ============================================================================
   # fromPointToEllipseArc
   # ============================================================================
   @staticmethod   
   def fromPointToEllipseArc(pt, ellipseArc):
      """
      la funzione ritorna una lista punti di tangenza sull'arco di ellisse di linee passanti per un punto
      """
      result = []
      ellipse = QadEllipse()
      ellipse.set(ellipseArc.center, ellipseArc.majorAxisFinalPt, ellipseArc.axisRatio)
      tangPtList = QadTangency.fromPointToEllipse(pt, ellipse)
      for tangPt in tangPtList:
         if ellipseArc.isPtOnEllipseArcOnlyByAngle(tangPt):
            result.append(tangPt)
      return result


   # ============================================================================
   # twoEllipseArcs
   # ============================================================================
   @staticmethod   
   def twoEllipseArcs(ellipseArc1, ellipseArc2):
      """
      la funzione ritorna una lista di linee che sono le tangenti a due archi di ellissi
      """
      result = []
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)
      lines = QadTangency.fromEllipseToEllipseArc(ellipse1, ellipseArc2)
      for line in lines:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(line.getStartPt()):
            result.append(line)
      return result


   # ===============================================================================
   # metodi per gli archi di ellisse - fine
   # metodi per gli oggetti geometrici di base - inizio
   # ===============================================================================


   # ============================================================================
   # fromPointToBasicGeomObject
   # ============================================================================
   @staticmethod   
   def fromPointToBasicGeomObject(pt, object):
      """
      la funzione ritorna una lista punti di tangenza sull'oggetto passanti per un punto
      la funzione ritorna i punti di tangenza su un oggetto geometrico di base:
      linea, arco, arco di ellisse, cerchio, ellisse.
      """
      if object.whatIs() == "CIRCLE":
         return QadTangency.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         return QadTangency.fromPointToArc(pt, object)
      elif object.whatIs() == "ELLIPSE":
         return QadTangency.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         return QadTangency.fromPointToEllipseArc(pt, object)
         
      return []


   # ============================================================================
   # fromPointToBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def fromPointToBasicGeomObjectExtensions(pt, object):
      """
      la funzione ritorna una lista punti di tangenza su una estensione di un oggetto geometrico di base passanti per un punto
      arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      """      
      if object.whatIs() == "CIRCLE":
         return QadTangency.fromPointToCircle(pt, object)
      elif object.whatIs() == "ARC":
         circle = QadCircle()
         circle.set(object.center, object.radius)
         return QadTangency.fromPointToCircle(pt, circle)
      elif object.whatIs() == "ELLIPSE":
         return QadTangency.fromPointToEllipse(pt, object)
      elif object.whatIs() == "ELLIPSE_ARC":
         ellipse = QadEllipse()
         ellipse.set(object.center, object.majorAxisFinalPt, object.axisRatio)
         return QadTangency.fromPointToEllipse(pt, ellipse)
         
      return []


   # ============================================================================
   # fromPointToGeomObject
   # ============================================================================
   @staticmethod   
   def fromPointToGeomObject(pt, object):
      """
      la funzione ritorna una lista punti di tangenza sull'oggetto passanti per un punto
      """
      geomType = object.whatIs()
      result = []
      
      if geomType == "MULTI_LINEAR_OBJ":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadTangency.fromPointToBasicGeomObject(pt, linearObj))
            
      elif geomType == "POLYLINE":
         for geomAt in range(0, object.qty()):
            linearObj = object.getLinearObjectAt(geomAt)
            result.extend(QadTangency.fromPointToBasicGeomObject(pt, linearObj))
            
      elif geomType == "POLYGON":
         for subGeomAt in range(0, object.qty()):
            closedObj = object.getClosedObjectAt(geomAt)
            result.extend(QadTangency.fromPointToGeomObject(pt, closedObj))            
         
      elif geomType == "MULTI_POLYGON":
         for geomAt in range(0, object.qty()):
            polygon = object.getPolygonAt(geomAt)
            result.extend(QadTangency.fromPointToGeomObject(pt, polygon))            
         
      # oggetto è una geometria base
      else:
         result.extend(QadTangency.fromPointToBasicGeomObject(pt, object))
   
      return result


   # ============================================================================
   # bestTwoBasicGeomObjects
   # ============================================================================
   @staticmethod   
   def bestTwoBasicGeomObjects(object1, tanPt1, object2, tanPt2):
      """
      Trova la linea tangente a un oggetto geometrico di base e tangente ad un altro oggetto geometrico di base
      (che ha i punti inziale/finale che rispettivamente sono più vicini ai punti tanPt1 e tanPt2):
      arco, arco di ellisse, cerchio, ellisse.
      tanPt1 = punto di selezione geometria 1 di tangenza
      tanPt2 = punto di selezione geometria 2 di tangenza
      """     
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromCircleToArc(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromCircleToEllipse(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromCircleToEllipseArc(object1, object2), tanPt1, tanPt2)
         
      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.fromCircleToArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoArcs(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromArcToEllipse(object1, sobject2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromArcToEllipseArc(object1, object2), tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.fromCircleToEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            lines = QadTangency.fromArcToEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipses(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.fromEllipseToEllipseArc(object1, object2), tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.fromCircleToEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            lines = QadTangency.fromArcToEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            lines = QadTangency.fromEllipseToEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipseArcs(object1, object2), tanPt1, tanPt2)
   
      return None


   # ============================================================================
   # bestTwoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def bestTwoBasicGeomObjectExtensions(object1, tanPt1, object2, tanPt2):
      """
      Trova la linea tangente all'estensione di un oggetto geometrico di base e tangente ad un'estensione
      di un altro oggetto geometrico di base (che ha i punti inziale/finale che rispettivamente sono 
      più vicini ai punti tanPt1 e tanPt2):
      arco, arco di ellisse, cerchio, ellisse.
      tanPt1 = punto di selezione geometria 1 di tangenza
      tanPt2 = punto di selezione geometria 2 di tangenza
      """
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(object1, circle2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(object1, ellipse2), tanPt1, tanPt2)
         
      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         if object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(circle1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoCircles(circle1, circle2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(circle1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangency.circleWithEllipse(circle1, ellipse2), tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.circleWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadTangency.circleWithEllipse(circle2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipses(object1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            lines = QadTangency.ellipseWithEllipseArc(object1, ellipse2)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "CIRCLE":
            lines = QadTangency.circleWithEllipse(object2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadTangency.circleWithEllipse(circle2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipses(ellipse1, object2), tanPt1, tanPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangency.twoEllipseArcs(ellipse1, ellipse2), tanPt1, tanPt2)
   
      return None
      

# ===============================================================================
# QadTangPerp class
# rappresenta una classe che calcola le linee tangenti ad un oggetto e perpendicolari ad un altro oggetto
# ===============================================================================
class QadTangPerp():
    
   def __init__(self):
      pass


   # ===============================================================================
   # metodi per i cerchi - inizio
   # ===============================================================================


   # ===============================================================================
   # circleWithInfinityLine
   # ===============================================================================
   @staticmethod
   def circleWithInfinityLine(circle1, line2):
      """
      Trova la linee tangenti a un cerchio e perpendicolari ad una linea infinita
      """
      lines = []
      # linee tangenti ad un cerchio e perpendicolari ad una linea
      angle = line2.getTanDirectionOnStartPt()
      pt1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
      pt2 = QadPerpendicularity.fromPointToInfinityLine(pt1, line2)
      if pt2 is not None:
         line = QadLine()
         line.set(pt1, pt2) # primo punto tangente e secondo punto perpendicolare
         lines.append(line) 
         
      pt1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, -1 * circle1.radius)
      pt2 = QadPerpendicularity.fromPointToInfinityLine(pt1, line2)
      if pt2 is not None:
         line = QadLine()
         line.set(pt1, pt2) # primo punto tangente e secondo punto perpendicolare
         lines.append(line) 

      return lines


   # ===============================================================================
   # circleWithLine
   # ===============================================================================
   @staticmethod
   def circleWithLine(circle1, line2):
      """
      Trova le linee tangenti a un cerchio e perpendicolari ad una linea
      """
      lines = QadTangPerp.circleWithInfinityLine(circle1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def twoCircles(circle1, circle2):
      """
      Trova le linee tangenti a un cerchio e perpendicolari ad un altro cerchio
      """
      lines = []
      points = QadTangency.fromPointToCircle(circle2.center, circle1)
      for point in points:
         angle = qad_utils.getAngleBy2Pts(circle2.center, point)
         pt1 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, circle2.radius)
         line = QadLine()
         line.set(point, pt1) # primo punto tangente e secondo punto perpendicolare
         lines.append(line) 
         pt1 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, -1 * circle2.radius)         
         line = QadLine()
         line.set(point, pt1) # primo punto tangente e secondo punto perpendicolare
         lines.append(line) 

      return lines


   # ===============================================================================
   # circleWithArc
   # ===============================================================================
   @staticmethod
   def circleWithArc(circle1, arc2):
      """
      Trova la linee tangenti a un cerchio e perpendicolari ad un arco
      """
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)

      lines = QadTangPerp.twoCircles(circle1, circle2)

      if len(lines) == 2:
         if arc2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # circleWithEllipse
   # ===============================================================================
   @staticmethod
   def circleWithEllipse(circle1, ellipse2):
      """
      Trova le linee tangenti a un cerchio e perpendicolari ad un'ellisse
      """
      # da fare
      return []


   # ===============================================================================
   # circleWithEllipseArc
   # ===============================================================================
   @staticmethod
   def circleWithEllipseArc(circle1, ellipseArc2):
      """
      Trova la linee tangenti a un cerchio e perpendicolari ad un arc di ellisse
      """
      # da fare
      return []


   # ===============================================================================
   # metodi per i cerchi - fine
   # metodi per gli archi - inizio
   # ===============================================================================


   # ===============================================================================
   # arcWithInfinityLine
   # ===============================================================================
   @staticmethod
   def arcWithInfinityLine(arc1, line2):
      """
      Trova la linee tangenti a un arco e perpendicolari ad una linea infinita
      """
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)

      lines = QadTangPerp.circleWithInfinityLine(circle1, line2)

      if len(lines) == 2:
         if arc1.containsPt(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.containsPt(lines[0].getStartPt()) == False: del(lines[0])
         
      return lines


   # ===============================================================================
   # arcWithLine
   # ===============================================================================
   @staticmethod
   def arcWithLine(arc1, line2):
      """
      Trova la linee tangenti a un arco e perpendicolari ad una linea
      """
      lines = QadTangPerp.arcWithInfinityLines(arc1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])
         
      return lines


   # ===============================================================================
   # arcWithCircle
   # ===============================================================================
   @staticmethod
   def arcWithCircle(arc1, circle2):
      """
      Trova le linee tangenti a un arco e perpendicolari ad un cerchio
      """
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)

      lines = QadTangPerp.twoCircles(circle1, circle2)

      if len(lines) == 2:
         if arc1.containsPt(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.containsPt(lines[0].getStartPt()) == False: del(lines[0])
         
      return lines


   # ===============================================================================
   # twoArcs
   # ===============================================================================
   @staticmethod
   def twoArcs(arc1, arc2):
      """
      Trova le linee tangenti a un arco e perpendicolari ad un altro arco
      """
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)

      lines = QadTangPerp.arcWithCircle(arc1, circle2)

      if len(lines) == 2:
         if arc2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc2.containsPt(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # arcWithEllipse
   # ===============================================================================
   @staticmethod
   def arcWithEllipse(arc1, ellipse2):
      """
      Trova le linee tangenti a un arco e perpendicolari ad una ellisse
      """
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      
      lines = QadTangPerp.circleWithEllipse(circle1, ellipse2)

      if len(lines) == 2:
         if arc1.containsPt(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.containsPt(lines[0].getStartPt()) == False: del(lines[1])

      return lines


   # ===============================================================================
   # arcWithEllipseArc
   # ===============================================================================
   @staticmethod
   def arcWithEllipseArc(arc1, ellipseArc2):
      """
      Trova le linee tangenti a un arco e perpendicolari ad un arco di ellisse
      """
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      
      lines = QadTangPerp.arcWithEllipse(arc1, ellipse2)

      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc1.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # metodi per gli archi - fine
   # metodi per le ellissi - inizio
   # ===============================================================================


   # ===============================================================================
   # ellipseWithInfinityLine
   # ===============================================================================
   @staticmethod
   def ellipseWithInfinityLine(ellipse1, line2):
      """
      Trova le linee tangenti a un'ellisse e perpendicolari ad una linea infinita
      """
      # da fare
      return []


   # ===============================================================================
   # ellipseWithLine
   # ===============================================================================
   @staticmethod
   def ellipseWithLine(ellipse1, line2):
      """
      Trova le linee tangenti a un'ellisse e perpendicolari ad una linea
      """
      lines = QadTangPerp.ellipseWithInfinityLines(ellipse1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])
         
      return lines


   # ===============================================================================
   # ellipseWithCircle
   # ===============================================================================
   @staticmethod
   def ellipseWithCircle(ellipse1, circle2):
      """
      Trova le linee tangenti a un'ellisse e perpendicolari ad un cerchio
      """
      # da fare
      return []


   # ===============================================================================
   # ellipseWithArc
   # ===============================================================================
   @staticmethod
   def ellipseWithArc(ellipse1, arc2):
      """
      Trova le linee tangenti a un'ellisse e perpendicolari ad un arco
      """
      circle2 = QadCircle()
      circle2.set(arc2.center, arc2.radius)

      lines = QadTangPerp.ellipseWithCircle(ellipse1, tanPt1, circle2, perPt2)

      if len(lines) == 2:
         if arc2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if arc2.containsPt(lines[0].getEndPt()) == False: del(lines[0])
         
      return lines


   # ===============================================================================
   # twoEllipses
   # ===============================================================================
   @staticmethod
   def twoEllipses(ellipse1, ellipse2):
      """
      Trova le linee tangenti a un'ellisse e perpendicolari ad un altra ellisse
      """
      # da fare
      return []


   # ===============================================================================
   # ellipseWithEllipseArc
   # ===============================================================================
   @staticmethod
   def ellipseWithEllipseArc(ellipse1, ellipseArc2):
      """
      Trova le linee tangenti a un'ellisse e perpendicolari ad un arco di ellisse
      """
      ellipse2 = QadEllipse()
      ellipse2.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      
      lines = QadTangPerp.twoEllipses(ellipse1, ellipse2)

      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # metodi per le ellissi - fine
   # metodi per gli archi di ellisse - inizio
   # ===============================================================================


   # ===============================================================================
   # ellipseArcWithInfinityLine
   # ===============================================================================
   @staticmethod
   def ellipseArcWithInfinityLine(ellipseArc1, line2):
      """
      Trova le linee tangenti a un arco di ellisse e perpendicolari ad una linea infinita
      """
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)
      
      lines = QadTangPerp.ellipseWithInfinityLine(ellipse1, line2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseArcWithLine
   # ===============================================================================
   @staticmethod
   def ellipseArcWithLine(ellipseArc1, line2):
      """
      Trova le linee tangenti a un arco di ellisse e perpendicolari ad una linea
      """
      lines = QadTangPerp.ellipseArcWithInfinityLine(ellipseArc1, line2)

      if len(lines) == 2:
         if line2.containsPt(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if line2.containsPt(lines[0].getEndPt()) == False: del(lines[0])
         
      return lines


   # ===============================================================================
   # ellipseArcWithCircle
   # ===============================================================================
   @staticmethod
   def ellipseArcWithCircle(ellipseArc1, circle2):
      """
      Trova le linee tangenti a un arco di ellisse e perpendicolari ad un cerchio
      """
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)
      
      lines = QadTangPerp.ellipseWithCircle(ellipse1, line2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseArcWithArc
   # ===============================================================================
   @staticmethod
   def ellipseArcWithArc(ellipseArc1, arc2):
      """
      Trova le linee tangenti a un arco di ellisse e perpendicolari ad un arco
      """
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)
      
      lines = QadTangPerp.ellipseWithArc(ellipse1, arc2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # ellipseArcWithEllipse
   # ===============================================================================
   @staticmethod
   def ellipseArcWithEllipse(ellipseArc1, ellipse2):
      """
      Trova le linee tangenti a un arco di ellisse e perpendicolari ad un'ellisse
      """
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)
      
      lines = QadTangPerp.twoEllipses(ellipse1, ellipse2)

      if len(lines) == 2:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc1.isPtOnEllipseArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])

      return lines


   # ===============================================================================
   # twoEllipseArcs
   # ===============================================================================
   @staticmethod
   def twoEllipseArcs(ellipseArc1, ellipseArc2):
      """
      Trova le linee tangenti a un arco di ellisse e perpendicolari ad un altro arco di ellisse
      """
      ellipse1 = QadEllipse()
      ellipse1.set(ellipseArc1.center, ellipseArc1.majorAxisFinalPt, ellipseArc1.axisRatio)
      
      lines = QadTangPerp.ellipseWithEllipseArc(ellipse1, ellipseArc2)

      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])

      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])

      return lines


   # ============================================================================
   # bestTwoBasicGeomObjects
   # ============================================================================
   @staticmethod   
   def bestTwoBasicGeomObjects(object1, tanPt1, object2, perPt2):
      """
      Trova la linea tangente a un oggetto geometrico di base e perpendicolarie ad un altro oggetto geometrico di base
      (che ha i punti inziale/finale che rispettivamente sono più vicini ai punti tanPt1 e perPt2):
      linea, arco, arco di ellisse, cerchio, ellisse.
      tanPt1 = punto di selezione geometria di tangenza
      perPt2 = punto di selezione geometria di perpendicolarità
      """               
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoCircles(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithArc(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipseArc(object1, object2), tanPt1, perPt2)
         
      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoArcs(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.arcWithEllipseArc(object1, object2), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithArc(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithEllipseArc(object1, object2), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithArc(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseArcWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipseArcs(object1, object2), tanPt1, perPt2)
   
      return None


   # ============================================================================
   # bestTwoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def bestTwoBasicGeomObjectExtensions(object1, tanPt1, object2, perPt2):
      """
      Trova le linee tangenti all'estensione di un oggetto geometrico di base e perpendicolari ad un'estensione
      di un altro oggetto geometrico di base (che ha i punti inziale/finale che rispettivamente 
      sono più vicini ai punti tanPt1 e perPt2):
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      tanPt1 = punto di selezione geometria di tangenza
      perPt2 = punto di selezione geometria di perpendicolarità
      """      
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithInfinityLine(object2, object1), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoCircles(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoCircles(object1, circle), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipse(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.circleWithEllipse(object1, ellipse), tanPt1, perPt2)
         
      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         return getLineWithStartEndPtsClosestToPts(QadTangPerp.fromTwoBasicGeomObjectExtensions(circle1, object2), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithInfinityLine(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object2.center, object2.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(object1, circle), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(object1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse = QadEllipse()
            ellipse.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(object1, ellipse), tanPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "LINE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithInfinityLine(ellipse1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(ellipse1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle = QadCircle()
            circle.set(object.center, object.radius)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.ellipseWithCircle(ellipse1, circle), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(ellipse1, object2), tanPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadTangPerp.twoEllipses(ellipse1, ellipse2), tanPt1, perPt2)
   
      return None


# ===============================================================================
# QadPerpPerp class
# rappresenta una classe che calcola le linee perpendicolari ad un oggetto e perpendicolari ad un altro oggetto
# ===============================================================================
class QadPerpPerp():
    
   def __init__(self):
      pass


   # ===============================================================================
   # metodi per le linee infinite - inizio
   # ===============================================================================


   # ===============================================================================
   # infinityLineWithCircle
   # ===============================================================================
   @staticmethod
   def infinityLineWithCircle(infinityLine1, circle2):
      """
      La funzione ritorna la linea perpendicolare tra la linea1 considerata linea infinita ed un cerchio.
      """
      # linea perpendicolare ad una linea e ad un cerchio
      ptPer1 = QadPerpendicularity.fromPointToInfinityLine(circle2.center, infinityLine1)
      angle = qad_utils.getAngleBy2Pts(circle2.center, ptPer1)
      ptPer2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, circle2.radius)
      line = QadLine()
      line.set(ptPer1, ptPer2)
      return line 


   # ===============================================================================
   # infinityLineWithArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithArc(infinityLine1, arc2):
      """
      La funzione ritorna la linea perpendicolare alla linea1 considerata linea infinita ed un arco.
      """
      circle = QadCircle()
      circle.set(arc2.center, arc2.radius)
      line = QadPerpPerp.infinityLineWithCircle(infinityLine1, circle)
      if line is None: return None
      if arc2.isPtOnArcOnlyByAngle(line.getEndPt()): return line
      return None


   # ===============================================================================
   # infinityLineWithEllipse
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipse(infinityLine1, ellipse2):
      """
      La funzione ritorna le linee perpendicolari alla linea1 considerata linea infinita ed un'ellisse.
      (fino a 4 linee)
      """
      # da fare
      return []


   # ===============================================================================
   # infinityLineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def infinityLineWithEllipseArc(infinityLine1, ellipseArc2):
      """
      La funzione ritorna le linee perpendicolari alla linea 1 considerata linea infinita ed un arco di ellisse.
      (fino a 4 linee)
      """
      ellipse = QadEllipse()
      ellipse.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadPerpPerp.infinityLineWithEllipse(infinityLine1, ellipse)
      
      if len(lines) == 4:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[3].getEndPt()) == False: del(lines[3])
      if len(lines) == 3:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[2].getEndPt()) == False: del(lines[2])
      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])
      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])
      
      return lines


   # ===============================================================================
   # metodi per le linee infinite - fine
   # metodi per i segmenti - inizio
   # ===============================================================================

   # ===============================================================================
   # lineWithLine
   # ===============================================================================
   @staticmethod
   def lineWithLine(line1, perPt1, line2, perPt2):
      """
      La funzione ritorna la linea perpendicolare ad un segmento ad un segmento.
      """
      ang1 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(line1.getStartPt(), line1.getEndPt()), math.pi)
      ang2 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(line2.getStartPt(), line2.getEndPt()), math.pi)
      if qad_utils.TanDirectionNear(ang1, ang2) == True:
         result = QadLine()
         result.set(perPt1, perPt2)
         return result

      return None

   # ===============================================================================
   # lineWithCircle
   # ===============================================================================
   @staticmethod
   def lineWithCircle(line1, circle2):
      """
      La funzione ritorna la linea perpendicolare ad un segmento ed un cerchio.
      """
      line = QadPerpPerp.infinityLineWithCircle(line1, circle2)
      if line is None: return None
      if line1.containsPt(line.getStartPt()): return line
      return None


   # ===============================================================================
   # lineWithArc
   # ===============================================================================
   @staticmethod
   def lineWithArc(line1, arc2):
      """
      La funzione ritorna la linea perpendicolare ad un segmento ed un arco.
      """
      circle = QadCircle()
      circle.set(arc2.center, arc2.radius)
      line = QadPerpPerp.lineWithCircle(line1, circle)
      if line is None: return None
      if arc2.isPtOnArcOnlyByAngle(line.getEndPt()): return line
      return None


   # ===============================================================================
   # lineWithEllipse
   # ===============================================================================
   @staticmethod
   def lineWithEllipse(line1, ellipse2):
      """
      La funzione ritorna le linee perpendicolari ad un segmento ed un'ellisse.
      (fino a 4 linee)
      """
      lines = QadPerpPerp.infinityLineWithEllipse(line1, ellipse2)

      if len(lines) == 4:
         if line1.containsPt(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if line1.containsPt(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if line1.containsPt(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if line1.containsPt(lines[0].getStartPt()) == False: del(lines[0])
      
      return lines


   # ===============================================================================
   # lineWithEllipseArc
   # ===============================================================================
   @staticmethod
   def lineWithEllipseArc(line1, ellipseArc2):
      """
      La funzione ritorna le linee perpendicolari ad un segmento ed un arco di ellisse.
      (fino a 4 linee)
      """
      lines = QadPerpPerp.infinityLineWithEllipseArc(line1, ellipseArc)

      if len(lines) == 4:
         if line1.containsPt(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if line1.containsPt(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if line1.containsPt(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if line1.containsPt(lines[0].getStartPt()) == False: del(lines[0])
      
      return lines


   # ===============================================================================
   # metodi per i segmenti - fine
   # metodi per i cerchi - inizio
   # ===============================================================================


   # ===============================================================================
   # twoCircles
   # ===============================================================================
   @staticmethod
   def twoCircles(circle1, circle2):
      """
      La funzione ritorna la linea perpendicolare tra due cerchi
      """
      angle = qad_utils.getAngleBy2Pts(circle1.center, circle2.center)
      ptPer1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
      ptPer2 = qad_utils.getPolarPointByPtAngle(circle2.center, angle, -circle2.radius)
      line = QadLine()
      line.set(ptPer1, ptPer2)
      return line


   # ===============================================================================
   # circleWithArc
   # ===============================================================================
   @staticmethod
   def circleWithArc(circle1, arc2):
      """
      La funzione ritorna la linea perpendicolare ad un cerchio ed un arco
      """
      circle = QadCircle()
      circle.set(arc2.center, arc2.radius)
      line = QadPerpPerp.twoCircles(circle1, circle)
      if line is None: return None
      if arc2.isPtOnArcOnlyByAngle(line.getEndPt()): return line
      return None


   # ===============================================================================
   # circleWithEllipse
   # ===============================================================================
   @staticmethod
   def circleWithEllipse(circle1, ellipse2):
      """
      La funzione ritorna le linee perpendicolari tra un cerchio ed un'ellisse
      (fino a 4 linee)
      """
      perpPts = QadPerpendicularity.fromPointToEllipse(circle1.center, ellipse2)
      lines = []
      for perpPt2 in perpPts:
         angle = qad_utils.getAngleBy2Pts(circle1.center, perpPt2)
         perPt1 = qad_utils.getPolarPointByPtAngle(circle1.center, angle, circle1.radius)
         line = QadLine()
         line.set(perPt1, perpPt2)
         lines.append(line)
      return lines


   # ===============================================================================
   # circleWithEllipseArc
   # ===============================================================================
   @staticmethod
   def circleWithEllipseArc(circle1, ellipseArc2):
      """
      La funzione ritorna le linee perpendicolari ad un cerchio ed un'ellisse
      (fino a 4 linee)
      """
      ellipse = QadEllipse()
      ellipse.set(ellipseArc2.center, ellipseArc2.majorAxisFinalPt, ellipseArc2.axisRatio)
      lines = QadPerpPerp.circleWithEllipse(circle1, ellipse)
      
      if len(lines) == 4:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[3].getEndPt()) == False: del(lines[3])
      if len(lines) == 3:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[2].getEndPt()) == False: del(lines[2])
      if len(lines) == 2:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[1].getEndPt()) == False: del(lines[1])
      if len(lines) == 1:
         if ellipseArc2.isPtOnEllipseArcOnlyByAngle(lines[0].getEndPt()) == False: del(lines[0])
      
      return lines


   # ===============================================================================
   # metodi per i cerchi - fine
   # metodi per gli archi - inizio
   # ===============================================================================


   # ===============================================================================
   # twoArcs
   # ===============================================================================
   @staticmethod
   def twoArcs(arc1, arc2):
      """
      La funzione ritorna le linee perpendicolari a due archi
      """
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      line = QadPerpPerp.circleWithArc(circle1, arc2)
      if line is None: return None
      if arc1.isPtOnArcOnlyByAngle(line.getStartPt()): return line
      return None


   # ===============================================================================
   # arcWithEllipse
   # ===============================================================================
   @staticmethod
   def arcWithEllipse(arc1, ellipse2):
      """
      La funzione ritorna le linee perpendicolari ad un arco ed un'ellisse
      (fino a 4 linee)
      """
      circle = QadCircle()
      circle.set(arc1.center, arc1.radius)
      lines = QadPerpPerp.circleWithEllipse(circle, ellipse2)

      if len(lines) == 4:
         if arc1.isPtOnArcOnlyByAngle(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if arc1.isPtOnArcOnlyByAngle(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if arc1.isPtOnArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if arc1.isPtOnArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])
      
      return lines


   # ===============================================================================
   # arcWithEllipseArc
   # ===============================================================================
   @staticmethod
   def arcWithEllipseArc(arc1, ellipseArc2):
      """
      La funzione ritorna le linee perpendicolari ad un arco ed un arco di ellisse
      (fino a 4 linee)
      """
      circle1 = QadCircle()
      circle1.set(arc1.center, arc1.radius)
      lines = QadPerpPerp.circleWithEllipseArc(circle1, ellipseArc2)
      
      if len(lines) == 4:
         if arc1.isPtOnArcOnlyByAngle(lines[3].getStartPt()) == False: del(lines[3])
      if len(lines) == 3:
         if arc1.isPtOnArcOnlyByAngle(lines[2].getStartPt()) == False: del(lines[2])
      if len(lines) == 2:
         if arc1.isPtOnArcOnlyByAngle(lines[1].getStartPt()) == False: del(lines[1])
      if len(lines) == 1:
         if arc1.isPtOnArcOnlyByAngle(lines[0].getStartPt()) == False: del(lines[0])
      
      return lines


   # ===============================================================================
   # metodi per gli archi - fine
   # ===============================================================================


   # ============================================================================
   # bestTwoBasicGeomObjects
   # ============================================================================
   @staticmethod   
   def bestTwoBasicGeomObjects(object1, perPt1, object2, perPt2):
      """
      Trova la linea perpendicolare a un oggetto geometrico di base e perpendicolare ad un altro oggetto geometrico di base
      (che ha i punti inziale/finale che rispettivamente sono più vicini ai punti tanPt1 e perPt2):
      linea, arco, arco di ellisse, cerchio, ellisse.
      perPt1 = punto di selezione geometria 1 di perpendicolarità
      perPt2 = punto di selezione geometria 2 di perpendicolarità
      """
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "LINE":
            return QadPerpPerp.lineWithLine(object1, perPt1, object2, perPt2)         
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.lineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            result = QadPerpPerp.lineWithArc(object1, object2)
            if result is not None:
               pts = QadIntersections.infinityLineWithArc(result, object2)
               if len(pts) == 2:
                  if qad_utils.getDistance(perPt2, pts[0]) <= qad_utils.getDistance(perPt2, pts[1]):
                     result.setEndPt(pts[0])
                  else:
                     result.setEndPt(pts[1])
            return result
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.lineWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.lineWithEllipseArc(object1, object2), perPt1, perPt2)
         
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.lineWithCircle(object2, object1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            return QadPerpPerp.circleWithArc(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipseArc(object1, object2), perPt1, perPt2)
         
      elif object1.whatIs() == "ARC":
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.lineWithArc(object2, object1)
            if result is not None:
               pts = QadIntersections.infinityLineWithArc(result, object1)
               if len(pts) == 2:
                  if qad_utils.getDistance(perPt1, pts[0]) <= qad_utils.getDistance(perPt1, pts[1]):
                     result.setEndPt(pts[0])
                  else:
                     result.setEndPt(pts[1])

            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            result = QadPerpPerp.lineWithCircle(object2, object1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "ARC":
            return QadPerpPerp.twoArcs(object1, object2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.arcWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.arcWithEllipseArc(object1, object2), perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.lineWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            lines = QadPerpPerp.circleWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            lines = QadPerpPerp.arcWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.lineWithEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            QadPerpPerp.circleWithEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            lines = QadPerpPerp.arcWithEllipseArc(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
   
      return None


   # ============================================================================
   # bestTwoBasicGeomObjectExtensions
   # ============================================================================
   @staticmethod   
   def bestTwoBasicGeomObjectExtensions(object1, tanPt1, object2, perPt2):
      """
      Trova la linea perpendicolare all'estensione di un oggetto geometrico di base e perpendicolare ad un'estensione
      di un altro oggetto geometrico di base (che ha i punti inziale/finale che rispettivamente sono 
      più vicini ai punti perPt1 e perPt2):
      linea (diventa linea infinita), arco (diventa cerchio), arco di ellisse (diventa ellisse), cerchio, ellisse.
      perPt1 = punto di selezione geometria 1 di perpendicolarità
      perPt2 = punto di selezione geometria 2 di perpendicolarità
      """      
      if object1.whatIs() == "LINE":
         if object2.whatIs() == "CIRCLE":
            return QadPerpPerp.infinityLineWithCircle(object1, object2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadPerpPerp.infinityLineWithCircle(object1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.infinityLineWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.infinityLineWithEllipse(object1, ellipse2), perPt1, perPt2)
         
      if object1.whatIs() == "CIRCLE":
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.infinityLineWithCircle(object2, object1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.twoCircles(object1, object2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadPerpPerp.twoCircles(object1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(object1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(object1, ellipse2), perPt1, perPt2)
         
      elif object1.whatIs() == "ARC":
         circle1 = QadCircle()
         circle1.set(object1.center, object1.radius)
         if object2.whatIs() == "LINE":
            result = QadPerpPerp.infinityLineWithCircle(object2, circle1)
            if result is not None: result.reverse()
            return result
         elif object2.whatIs() == "CIRCLE":
            return QadPerpPerp.twoCircles(circle1, object2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            return QadPerpPerp.twoCircles(circle1, circle2)
         elif object2.whatIs() == "ELLIPSE":
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(circle1, object2), perPt1, perPt2)
         elif object2.whatIs() == "ELLIPSE_ARC":
            ellipse2 = QadEllipse()
            ellipse2.set(object2.center, object2.majorAxisFinalPt, object2.axisRatio)
            return getLineWithStartEndPtsClosestToPts(QadPerpPerp.circleWithEllipse(circle1, ellipse2), perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE":
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.infinityLineWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            lines = QadPerpPerp.circleWithEllipse(object2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadPerpPerp.circleWithEllipse(circle2, object1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)

      elif object1.whatIs() == "ELLIPSE_ARC":
         ellipse1 = QadEllipse()
         ellipse1.set(object1.center, object1.majorAxisFinalPt, object1.axisRatio)
         if object2.whatIs() == "LINE":
            lines = QadPerpPerp.infinityLineWithEllipse(object2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "CIRCLE":
            QadPerpPerp.circleWithEllipse(object2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
         elif object2.whatIs() == "ARC":
            circle2 = QadCircle()
            circle2.set(object2.center, object2.radius)
            lines = QadPerpPerp.circleWithEllipse(circle2, ellipse1)
            for line in lines: line.reverse()
            return getLineWithStartEndPtsClosestToPts(lines, perPt1, perPt2)
   
      return None


# ===============================================================================
# getLineWithStartEndPtsClosestToPts
# ===============================================================================
def getLineWithStartEndPtsClosestToPts(lines, pt1, pt2):
   """
   Data ua lista di linee ritorna la linea che ha punto iniziale e finale rispettivamente
   più vicini a pt1 e pt2 (la funzione usa la media delle distanze).
   """
   if len(lines) == 0:
      return None

   Avg = sys.float_info.max
   for line in lines:
      d1 = qad_utils.getDistance(line.getStartPt(), pt1)
      d2 = qad_utils.getDistance(line.getEndPt(), pt2)         
      currAvg = (d1 + d2) / 2.0           
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         result = line

   return result


# ===============================================================================
# getQadGeomClosestPart
# ===============================================================================
def getQadGeomClosestPart(qadGeom, pt):
   """
   la funzione ritorna una lista con 
   (<minima distanza>
    <punto più vicino>
    <indice della geometria più vicina>
    <indice della sotto-geometria più vicina>
    <indice della parte della sotto-geometria più vicina>
    <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
    -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
    -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
    )
   """
   geomType = qadGeom.whatIs()
   if geomType == "POINT" or geomType == "LINE" or geomType == "ARC" or \
      geomType == "CIRCLE" or geomType == "ELLIPSE_ARC" or geomType == "ELLIPSE":
      # la funzione ritorna una lista con (<distanza minima><punto di distanza minima>)
      result = QadMinDistance.fromPointToBasicGeomObject(pt, qadGeom)
      dist = result[0]
      minDistPoint = result[1]
      
      if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
         # < 0 "a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
         leftOf = qadGeom.leftOf(pt)
      elif geomType == "CIRCLE" or geomType == "ELLIPSE_ARC" or geomType == "ELLIPSE": # cerchio o ellisse
         leftOf = qadGeom.whereIsPt(pt) # -1 interno, 0 sulla circonferenza, 1 esterno
      else:
         leftOf = None
         
      return (dist, minDistPoint, 0, 0, 0, leftOf)
   
   elif qadGeom.whatIs() == "POLYLINE":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = i
            leftOf = result[5]
         i = i + 1 
      
      return (dist, minDistPoint, 0, 0, partIndex, leftOf)
   
   elif qadGeom.whatIs() == "POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getClosedObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = result[4]
            leftOf = result[5]
            subGeomIndex = i
         i = i + 1 
      
      return (dist, minDistPoint, 0, subGeomIndex, partIndex, leftOf)
   
   elif qadGeom.whatIs() == "MULTI_POINT":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getPointAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
         i = i + 1 

      return (dist, minDistPoint, geomIndex, 0, 0, None)

   elif qadGeom.whatIs() == "MULTI_LINEAR_OBJ":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            partIndex = result[4]
            leftOf = result[5]
         i = i + 1 

      return (dist, minDistPoint, geomIndex, 0, partIndex, leftOf)
      
   elif qadGeom.whatIs() == "MULTI_POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestPart(qadGeom.getPolygonAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            subGeomIndex = result[3]
            partIndex = result[4]
            leftOf = result[5]
         i = i + 1 
            
      return (dist, minDistPoint, geomIndex, subGeomIndex, partIndex, leftOf)
      
   else:
      return (None, None, None, None, None, None) 


# ===============================================================================
# getQadGeomClosestVertex
# ===============================================================================
def getQadGeomClosestVertex(qadGeom, pt):
   """
   la funzione ritorna una lista con 
   (<minima distanza>
    <punto del vertice più vicino>
    <indice della geometria più vicina>
    <indice della sotto-geometria più vicina>
    <indice della parte della sotto-geometria più vicina>
    <indice del vertice più vicino>
    )
   """
   geomType = qadGeom.whatIs()
   if geomType == "POINT":
      return (qad_utils.getDistance(qadGeom, pt), qadGeom, 0, 0, 0, 0)
   
   elif geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
      startPt = qadGeom.getStartPt()
      endPt = qadGeom.getEndPt()
      d1 = qad_utils.getDistance(startPt, pt)
      d2 = qad_utils.getDistance(endPt, pt)
      if d1 < d2:
         return (d1, startPt, 0, 0, 0, 0)
      else:
         return (d2, endPt, 0, 0, 0, 1)
   
   elif qadGeom.whatIs() == "POLYLINE":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = i
            vertexIndex = partIndex + result[5]
         i = i + 1 
      
      return (dist, minDistPoint, 0, 0, partIndex, vertexIndex)
   
   elif qadGeom.whatIs() == "POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getClosedObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            partIndex = result[4]
            vertexIndex = result[5]
            subGeomIndex = i
         i = i + 1 
      
      return (dist, minDistPoint, 0, subGeomIndex, partIndex, vertexIndex)
   
   elif qadGeom.whatIs() == "MULTI_POINT":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getPointAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
         i = i + 1

      return (dist, minDistPoint, geomIndex, 0, 0, 0)

   elif qadGeom.whatIs() == "MULTI_LINEAR_OBJ":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getLinearObjectAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            partIndex = result[4]
            vertexIndex = result[5]
         i = i + 1

      return (dist, minDistPoint, geomIndex, 0, partIndex, vertexIndex)
      
   elif qadGeom.whatIs() == "MULTI_POLYGON":
      dist = sys.float_info.max
      i = 0
      while i < qadGeom.qty():
         result = getQadGeomClosestVertex(qadGeom.getPolygonAt(i), pt)
         if result[0] < dist:
            dist = result[0]
            minDistPoint = result[1]
            geomIndex = i
            subGeomIndex = result[3]
            partIndex = result[4]
            vertexIndex = result[5]
         i = i + 1
            
      return (dist, minDistPoint, geomIndex, subGeomIndex, partIndex, vertexIndex)
      
   else:
      # la funzione ritorna una lista con (<distanza minima><punto di distanza minima>)
      result = QadMinDistance.fromPointToBasicGeomObject(pt, qadGeom)
      dist = result[0]
      minDistPoint = result[1]
      
      return (dist, minDistPoint, 0, 0, None, None)


# ===============================================================================
# getGeomBetween2Pts
# ===============================================================================
def getQadGeomBetween2Pts(qadGeom, startPt, endPt):
   """
   Ritorna una sotto geometria che parte dal punto startPt e finisce al punto endPt seguendo il tracciato della geometria.
   """
   # la funzione ritorna una lista con 
   # (<minima distanza>
   # <punto più vicino>
   # <indice della geometria più vicina>
   # <indice della sotto-geometria più vicina>
   # se geometria chiusa è tipo polyline la lista contiene anche
   # <indice della parte della sotto-geometria più vicina>
   # <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
   dummy = getQadGeomClosestPart(qadGeom, startPt)
   ptEnd = dummy[1]
   # ritorna la sotto-geometria
   g = getQadGeomAt(qadGeom, dummy[2], dummy[3])

   geomType = g.whatIs()  
   if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
      return g.getGeomBetween2Pts(startPt, endPt)
   
   elif qadGeom.whatIs() == "POLYLINE":
      return g.getGeomBetween2Pts(startPt, endPt)

   elif qadGeom.whatIs() == "CIRCLE":
      angle1 = qad_utils.getAngleBy2Pts(g.center, startPt)
      angle2 = qad_utils.getAngleBy2Pts(g.center, endPt)

      arc1 = QadArc()
      arc1.set(g.center, g.radius, angle1, angle2)
      arc2 = QadArc()
      arc2.set(g.center, g.radius, angle2, angle1)
      
      if arc1.length() < arc2.length():
         if qad_utils.ptNear(arc1.getStartPt(), startPt) == False: arc1.reversed = True
         return arc1
      else:
         if qad_utils.ptNear(arc2.getStartPt(), startPt) == False: arc2.reversed = True
         return arc2

   elif qadGeom.whatIs() == "ELLIPSE":
      angle1 = qad_utils.getAngleBy2Pts(g.center, startPt)
      angle2 = qad_utils.getAngleBy2Pts(g.center, endPt)

      arc1 = QadEllipseArc()
      arc1.set(g.center, g.majorAxisFinalPt, g.axisRatio, angle1, angle2)
      arc2 = QadEllipseArc()
      arc2.set(g.center, g.majorAxisFinalPt, g.axisRatio, angle2, angle1)
      
      if arc1.length() < arc2.length():
         if qad_utils.ptNear(arc1.getStartPt(), startPt) == False: arc1.reversed = True
         return arc1
      else:
         if qad_utils.ptNear(arc2.getStartPt(), startPt) == False: arc2.reversed = True
         return arc2


# ===============================================================================
# appendPtOnTheSameTanDirectionOnly
# ===============================================================================
def appendPtOnTheSameTanDirectionOnly(line, pts, resultList):
   """
   Aggiunge i punti della lista pts solo se sono nella stessa direzione della tangente della linea.
   Serve, ad esempio, per aggiungere i punti di intersezione sulla estensione della prima ed ultima linea diuna polilinea.
   """
   angle = line.getTanDirectionOnPt()
   for pt in pts:
      if qad_utils.ptNear(pt, line.pt1) or \
         qad_utils.doubleNear(angle, qad_utils.getAngleBy2Pts(line.pt1, pt)):
         resultList.append(pt)



