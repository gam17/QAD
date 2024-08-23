# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per stirare oggetti grafici
 
                              -------------------
        begin                : 2013-11-11
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


from . import qad_utils
from .qad_variables import QadVariables
from .qad_msg import QadMsg
from .qad_snapper import *
from .qad_point import QadPoint
from .qad_ellipse import QadEllipse
from .qad_ellipse_arc import QadEllipseArc


#===============================================================================
# isPtContainedForStretch
#===============================================================================
def isPtContainedForStretch(point, containerGeom, tolerance=None):
   """
   Funzione di ausilio per le funzioni di stretch (stretchPoint e stretchQgsLineStringGeometry).
   Se containerGeom è un oggetto QgsGeometry allora ritorna True se il punto è contenuto a livello spaziale
   dalla geometria containerGeom.
   Se containerGeom è una lista di punti allora ritorna True se il punto è fra quelli della lista.
   """      
   if type(containerGeom) == QgsGeometry: # geometria   
      return containerGeom.contains(point)
   elif type(containerGeom) == list: # lista di punti
      if tolerance is None:
         myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
      else:
         myTolerance = tolerance
      
      for containerPt in containerGeom:
         if qad_utils.ptNear(containerPt, point, myTolerance): # se i punti sono sufficientemente vicini
            return True
   return False 


#===============================================================================
# stretchQadGeometry
#===============================================================================
def stretchQadGeometry(geom, ptListToStretch, offsetX, offsetY):
   """
   Stira una entità qad in coordinate piane mediante grip point
   geom = entità qad da stirare
   ptListToStretch = lista dei punti di geom da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   if type(geom) == list: # entità composta da più geometrie
      res = []
      iSub = 0
      for subGeom in geom:
         res.append(stretchQadGeometry(subGeom, ptListToStretch, offsetX, offsetY))
         iSub = iSub + 1
      return res
   else:
      gType = geom.whatIs()
      if gType == "POINT":
         return stretchPoint(geom, ptListToStretch, offsetX, offsetY)
      if gType == "MULTI_POINT":
         return stretchMultiPoint(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "LINE":
         return stretchLine(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "ARC":
         return stretchArc(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "CIRCLE":
         return stretchCircle(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "ELLIPSE":
         return stretchEllipse(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "ELLIPSE_ARC":
         return stretchEllipseArc(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "POLYLINE":
         return stretchPolyline(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "MULTI_LINEAR_OBJ":
         return stretchMultiLinearObj(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "POLYGON":
         return stretchPolygon(geom, ptListToStretch, offsetX, offsetY)
      elif gType == "MULTI_POLYGON":
         return stretchMultiPolygon(geom, ptListToStretch, offsetX, offsetY)

   return None


#===============================================================================
# stretchPoint
#===============================================================================
def stretchPoint(point, containerGeom, offsetX, offsetY):
   """
   Restituisce un nuovo punto stirato se è contenuto in containerGeom
   point = punto da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   stretchedGeom = QadPoint(point)
   if isPtContainedForStretch(point, containerGeom): # se il punto è contenuto in containerGeom
      stretchedGeom.move(offsetX, offsetY)

   return stretchedGeom


#===============================================================================
# stretchMultiPoint
#===============================================================================
def stretchMultiPoint(multiPoint, containerGeom, offsetX, offsetY):
   """
   Restituisce un nuovo multi punto stirato se è contenuto in containerGeom
   point = punto da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   multiPointToStretch = multiPoint.copy()
   i = 0
   while i < multiPointToStretch.qty():
      point = multiPointToStretch.getPointAt(i)
      newPoint = stretchPoint(point, containerGeom, offsetX, offsetY)
      point.set(newPoint)
      i = i + 1

   return multiPointToStretch


#===============================================================================
# stretchCircle
#===============================================================================
def stretchCircle(circle, containerGeom, offsetX, offsetY):
   """
   Stira un cerchio usando i punti che sono contenuti in containerGeom
   circle = cerchio da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """

   newCircle = circle.copy()
   newCenter = QgsPointXY(circle.center)
   newRadius = circle.radius

   if isPtContainedForStretch(circle.center, containerGeom): # se il centro è contenuto in containerGeom
      newCenter.set(circle.center.x() + offsetX, circle.center.y() + offsetY) # sposto il cerchio
   else:
      if type(containerGeom) == list: # lista di punti
         for containerPt in containerGeom:
            # whereIsPt ritorna -1 se il punto è interno, 0 se è sulla circonferenza, 1 se è esterno
            if circle.whereIsPt(containerPt) == 0:
               newPt = QgsPointXY(containerPt.x() + offsetX, containerPt.y() + offsetY)
               newRadius = qad_utils.getDistance(circle.center, newPt)
               break     
      else: # geometria     
         # ritorna i punti quadranti
         quadrants = circle.getQuadrantPoints()
         for quadrant in quadrants:         
            if isPtContainedForStretch(quadrant, containerGeom): # se il quandrante è contenuto in containerGeom
               newPt = QgsPointXY(quadrant.x() + offsetX, quadrant.y() + offsetY)
               newRadius = qad_utils.getDistance(circle.center, newPt)
               break

   return newCircle.set(newCenter, newRadius)


#===============================================================================
# stretchArc
#===============================================================================
def stretchArc(arc, containerGeom, offsetX, offsetY):
   """
   Stira i punti di grip di un arco che sono contenuti in containerGeom
   arc = arco da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   newArc = arc.copy()
   
   if isPtContainedForStretch(arc.center, containerGeom): # se il centro è contenuto in containerGeom
      newArc.center.set(arc.center.x() + offsetX, arc.center.y() + offsetY)
   else:
      startPt = arc.getStartPt()
      endPt = arc.getEndPt()
      middlePt = arc.getMiddlePt()
      newStartPt = QgsPointXY(startPt)
      newEndPt = QgsPointXY(endPt)
      newMiddlePt = QgsPointXY(middlePt)
      
      if isPtContainedForStretch(startPt, containerGeom): # se il punto iniziale è contenuto in containerGeom
         newStartPt.set(startPt.x() + offsetX, startPt.y() + offsetY)
   
      if isPtContainedForStretch(endPt, containerGeom): # se il punto finale è contenuto in containerGeom
         newEndPt.set(endPt.x() + offsetX, endPt.y() + offsetY)
   
      if isPtContainedForStretch(middlePt, containerGeom): # se il punto medio è contenuto in containerGeom
         newMiddlePt.set(middlePt.x() + offsetX, middlePt.y() + offsetY)
      
      if newArc.reversed:
         if newArc.fromStartSecondEndPts(newEndPt, newMiddlePt, newStartPt) == False:
            return None
      else:
         if newArc.fromStartSecondEndPts(newStartPt, newMiddlePt, newEndPt) == False:
            return None

   return newArc


#===============================================================================
# stretchEllipse
#===============================================================================
def stretchEllipse(ellipse, containerGeom, offsetX, offsetY):
   """
   Stira i punti di grip di una ellisse che sono contenuti in containerGeom
   ellipse = ellisse da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   newCenter = QgsPointXY(ellipse.center)
   newMajorAxisFinalPt = QgsPointXY(ellipse.majorAxisFinalPt)
   a = qad_utils.getDistance(ellipse.center, ellipse.majorAxisFinalPt) # semiasse maggiore
   b = a * ellipse.axisRatio # semiasse minore
   angle = ellipse.getRotation()
   newAxisRatio = ellipse.axisRatio
      
   if isPtContainedForStretch(ellipse.center, containerGeom): # se il centro è contenuto in containerGeom
      newCenter.set(ellipse.center.x() + offsetX, ellipse.center.y() + offsetY)
      newMajorAxisFinalPt.set(ellipse.majorAxisFinalPt.x() + offsetX, ellipse.majorAxisFinalPt.y() + offsetY)
   else:
      # ritorna i punti quadranti: partendo da majorAxisFinalPt in ordine antiorario
      quadrants = ellipse.getQuadrantPoints()
      majorAxisFinalPt1 = quadrants[0]
      majorAxisFinalPt2 = quadrants[2]
      minorAxisFinalPt1 = quadrants[1]
      minorAxisFinalPt2 = quadrants[3]
      
      if isPtContainedForStretch(majorAxisFinalPt1, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(majorAxisFinalPt1.x() + offsetX, majorAxisFinalPt1.y() + offsetY)
         newA = qad_utils.getDistance(ellipse.center, pt) # nuovo semiasse maggiore
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipse.center, angle, newA)
         newAxisRatio = b / newA
      elif isPtContainedForStretch(majorAxisFinalPt2, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(majorAxisFinalPt2.x() + offsetX, majorAxisFinalPt2.y() + offsetY)
         newA = qad_utils.getDistance(ellipse.center, pt) # nuovo semiasse maggiore
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipse.center, angle, newA)
         newAxisRatio = b / newA
      elif isPtContainedForStretch(minorAxisFinalPt1, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(minorAxisFinalPt1.x() + offsetX, minorAxisFinalPt1.y() + offsetY)
         newB = qad_utils.getDistance(ellipse.center, pt) # nuovo semiasse minore
         newAxisRatio = newB / a
      elif isPtContainedForStretch(minorAxisFinalPt2, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(minorAxisFinalPt2.x() + offsetX, minorAxisFinalPt2.y() + offsetY)
         newB = qad_utils.getDistance(ellipse.center, pt) # nuovo semiasse minore
         newAxisRatio = newB / a

   newEllipse = QadEllipse()
   return newEllipse.set(newCenter, newMajorAxisFinalPt, newAxisRatio)


#===============================================================================
# stretchEllipseArc
#===============================================================================
def stretchEllipseArc(ellipseArc, containerGeom, offsetX, offsetY):
   """
   Stira i punti di grip di un arco di ellisse che sono contenuti in containerGeom
   ellipseArc = arco di ellisse da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   newCenter = QgsPointXY(ellipseArc.center)
   newMajorAxisFinalPt = QgsPointXY(ellipseArc.majorAxisFinalPt)
   a = qad_utils.getDistance(ellipseArc.center, ellipseArc.majorAxisFinalPt) # semiasse maggiore
   b = a * ellipseArc.axisRatio # semiasse minore
   angle = ellipseArc.getRotation()
   startPt = ellipseArc.getStartPt()
   endPt = ellipseArc.getEndPt()
   newAxisRatio = ellipseArc.axisRatio
   newStartAngle = ellipseArc.startAngle
   newEndAngle = ellipseArc.endAngle
      
   if isPtContainedForStretch(ellipseArc.center, containerGeom): # se il centro è contenuto in containerGeom
      newCenter.set(ellipseArc.center.x() + offsetX, ellipseArc.center.y() + offsetY)
      newMajorAxisFinalPt.set(ellipseArc.majorAxisFinalPt.x() + offsetX, ellipseArc.majorAxisFinalPt.y() + offsetY)
   else:
      # ritorna i punti quadranti: partendo da majorAxisFinalPt in ordine antiorario
      quadrants = ellipseArc.getQuadrantPoints()
      majorAxisFinalPt1 = quadrants[0]
      majorAxisFinalPt2 = quadrants[2]
      minorAxisFinalPt1 = quadrants[1]
      minorAxisFinalPt2 = quadrants[3]
      
      if majorAxisFinalPt1 is not None and isPtContainedForStretch(majorAxisFinalPt1, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(majorAxisFinalPt1.x() + offsetX, majorAxisFinalPt1.y() + offsetY)
         newA = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semiasse maggiore
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipseArc.center, angle, newA)
         newAxisRatio = b / newA
      elif majorAxisFinalPt2 is not None and isPtContainedForStretch(majorAxisFinalPt2, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(majorAxisFinalPt2.x() + offsetX, majorAxisFinalPt2.y() + offsetY)
         newA = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semiasse maggiore
         newMajorAxisFinalPt = qad_utils.getPolarPointByPtAngle(ellipseArc.center, angle, newA)
         newAxisRatio = b / newA
      elif minorAxisFinalPt1 is not None and isPtContainedForStretch(minorAxisFinalPt1, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(minorAxisFinalPt1.x() + offsetX, minorAxisFinalPt1.y() + offsetY)
         newB = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semiasse minore
         newAxisRatio = newB / a
      elif minorAxisFinalPt2 is not None and isPtContainedForStretch(minorAxisFinalPt2, containerGeom): # se il quandrante è contenuto in containerGeom
         pt = QgsPointXY(minorAxisFinalPt2.x() + offsetX, minorAxisFinalPt2.y() + offsetY)
         newB = qad_utils.getDistance(ellipseArc.center, pt) # nuovo semiasse minore
         newAxisRatio = newB / a
      elif isPtContainedForStretch(startPt, containerGeom): # se il punto iniziale è contenuto in containerGeom
         newStartPt = QgsPointXY()
         newStartPt.set(startPt.x() + offsetX, startPt.y() + offsetY)
         newStartAngle = qad_utils.getAngleBy2Pts(ellipseArc.center, newStartPt) - angle
      elif isPtContainedForStretch(endPt, containerGeom): # se il punto finale è contenuto in containerGeom
         newEndPt = QgsPointXY()
         newEndPt.set(endPt.x() + offsetX, endPt.y() + offsetY)
         newEndAngle = qad_utils.getAngleBy2Pts(ellipseArc.center, newEndPt) - angle

   newEllipseArc = QadEllipseArc()
   return newEllipseArc.set(newCenter, newMajorAxisFinalPt, newAxisRatio, newStartAngle, newEndAngle)


#===============================================================================
# stretchLine
#===============================================================================
def stretchLine(line, containerGeom, offsetX, offsetY):
   """
   Stira i punti di grip di una qadLine che sono contenuti in containerGeom
   line = geometria da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   lineToStretch = line.copy()
      
   pt = lineToStretch.getStartPt()
   if isPtContainedForStretch(pt, containerGeom): # se il punto è contenuto in containerGeom
      # cambio punto iniziale        
      pt.setX(pt.x() + offsetX)
      pt.setY(pt.y() + offsetY)
      lineToStretch.setStartPt(pt)
      
   pt = lineToStretch.getEndPt()
   if isPtContainedForStretch(pt, containerGeom): # se il punto è contenuto in containerGeom
      # cambio punto finale
      pt.setX(pt.x() + offsetX)
      pt.setY(pt.y() + offsetY)
      lineToStretch.setEndPt(pt)

   return lineToStretch


#===============================================================================
# stretchPolyline
#===============================================================================
def stretchPolyline(polyline, containerGeom, offsetX, offsetY):
   """
   Crea una nuova polyline stirando i punti di grip che sono contenuti in containerGeom
   polyline = polilinea da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   polylineToStretch = polyline.copy()

   pt = polylineToStretch.getCentroid() # verifico se polilinea ha un centroide
   if pt is not None and isPtContainedForStretch(pt, containerGeom): # se il punto è contenuto in containerGeom
      polylineToStretch.move(offsetX, offsetY)
   else:
      i = 0
      while i < polylineToStretch.qty():
         linearObject = polylineToStretch.getLinearObjectAt(i)
         newLinearObject = stretchQadGeometry(linearObject, containerGeom, offsetX, offsetY)
         if (newLinearObject is not None):
            polylineToStretch.insert(i, newLinearObject)
            polylineToStretch.remove(i + 1)
   
         i = i + 1

      # verifico e correggo i versi delle parti della polilinea 
      polylineToStretch.reverseCorrection()

   return polylineToStretch


#===============================================================================
# stretchMultiLinearObj
#===============================================================================
def stretchMultiLinearObj(multiLinear, containerGeom, offsetX, offsetY):
   """
   Crea un nuovo multi lineare stirando i punti di grip che sono contenuti in containerGeom
   polygon = multi lineare da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   multiLinearToStretch = multiLinear.copy()
   
   i = 0
   while i < multiLinearToStretch.qty():
      linearObject = multiLinearToStretch.getLinearObjectAt(i)
      newLinearObject = stretchQadGeometry(linearObject, containerGeom, offsetX, offsetY)
      multiLinearToStretch.insert(i, newLinearObject)
      multiLinearToStretch.remove(i + 1)
      
      i = i + 1

   return multiLinearToStretch


#===============================================================================
# stretchPolygon
#===============================================================================
def stretchPolygon(polygon, containerGeom, offsetX, offsetY):
   """
   Crea un nuovo poligono stirando i punti di grip che sono contenuti in containerGeom
   polygon = poligono da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   polygonToStretch = polygon.copy()

   pt = polygonToStretch.getCentroid() # verifico se polilinea ha un centroide
   if pt is not None and isPtContainedForStretch(pt, containerGeom): # se il punto è contenuto in containerGeom
         polygonToStretch.move(offsetX, offsetY)
   else:
      i = 0
      while i < polygonToStretch.qty():
         closedObject = polygonToStretch.getClosedObjectAt(i)
         newClosedObject = stretchQadGeometry(closedObject, containerGeom, offsetX, offsetY)
         polygonToStretch.insert(i, newClosedObject)
         polygonToStretch.remove(i + 1)
         
         i = i + 1

   return polygonToStretch


#===============================================================================
# stretchMultiPolygon
#===============================================================================
def stretchMultiPolygon(multiPolygon, containerGeom, offsetX, offsetY):
   """
   Crea un nuovo multi poligono stirando i punti di grip che sono contenuti in containerGeom
   multiPolygon = multi poligono da stirare
   containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                   oppure una lista dei punti da stirare
   offsetX = spostamento X
   offsetY = spostamento Y
   """
   multiPolygonToStretch = multiPolygon.copy()

   pt = multiPolygonToStretch.getCentroid() # verifico se polilinea ha un centroide
   if pt is not None and isPtContainedForStretch(pt, containerGeom): # se il punto è contenuto in containerGeom
         multiPolygonToStretch.move(offsetX, offsetY)
   else:
      i = 0
      while i < multiPolygonToStretch.qty():
         polygon = multiPolygonToStretch.getPolygonAt(i)
         newPolygon = stretchQadGeometry(polygon, containerGeom, offsetX, offsetY)
         multiPolygonToStretch.insert(i, newPolygon)
         multiPolygonToStretch.remove(i + 1)
            
         i = i + 1

   return multiPolygonToStretch