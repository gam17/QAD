# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per extend e trim
 
                              -------------------
        begin                : 2019-05-20
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

from .qad_multi_geom import *
from .qad_geom_relations import *
from .qad_entity import *
from .qad_arc import *
from .qad_ellipse_arc import *


# ===============================================================================
# extendQadGeometry
# ===============================================================================
def extendQadGeometry(qadGeom, pt, limitEntitySet, edgeMode):
   """
   la funzione estende una geometria QAD (lineare) nella parte iniziale o finale fino ad
   incontrare l'oggetto più vicino nel gruppo <limitEntitySet> secondo la modalità <edgeMode>.
   <qadGeom> = geometria lineare QAD da estendere
   <pt> = punto che indica la parte di quell'oggetto che deve essere estesa
   <QadEntitySet> = gruppo di entità che serve da limite di estensione
   <edgeMode> se = 0 si deve estendere la geometria fino ad incontrare l'oggetto più vicino
              se = 1 si deve estendere la geometria fino ad incontrare l'oggetto più vicino o 
              anche il suo prolungamento
   """
   # la funzione ritorna una lista con 
   # (<minima distanza>
   # <punto del vertice più vicino>
   # <indice della geometria più vicina>
   # <indice della sotto-geometria più vicina>
   # <indice della parte della sotto-geometria più vicina>
   # <indice del vertice più vicino>
   result = getQadGeomClosestVertex(qadGeom, pt)
   nearPt = result[1]
   atGeom = result[2]
   atSubGeom = result[3]
   subGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom)

   if not isLinearQadGeom(subGeom): return None
   middleLength = subGeom.length() / 2
   distFromStart = subGeom.getDistanceFromStart(nearPt)
   
   if subGeom.whatIs() == "POLYLINE":
      if subGeom.isClosed(): # non si può fare con polilinea chiusa
         return None
      if distFromStart > middleLength:
         # parte finale
         linearObjectToExtend = subGeom.getLinearObjectAt(-1).copy()
      else:
         # parte iniziale
         linearObjectToExtend = subGeom.getLinearObjectAt(0).copy()
         linearObjectToExtend.reverse()
   else:
      linearObjectToExtend = subGeom.copy()
      if distFromStart < middleLength:
         # parte iniziale
         linearObjectToExtend.reverse()

   # per ciascun entità di limitEntitySet cerco i punti di intersezione
   intPts = []                                                               
   entityIterator = QadEntitySetIterator(limitEntitySet)
   for limitEntity in entityIterator:
      intPts.extend(getIntersectionPtsExtendQadGeometry(linearObjectToExtend, limitEntity.getQadGeom(), edgeMode))
   
   # cerco il punto di intersezione più vicino al punto finale di linearObject
   testGeom = linearObjectToExtend.copy()
   newEndPt = None
   minDist = sys.float_info.max
   
   for intPt in intPts:
      testGeom.setEndPt(intPt)
      length = testGeom.length()
      if length < minDist:
         minDist = length
         newEndPt = intPt
   
   if newEndPt is None:
      return None

   result = subGeom.copy()
   if distFromStart > middleLength:
      # punto finale
      result.setEndPt(newEndPt)
   else:
      # punto iniziale
      result.setStartPt(newEndPt)
      
   return setQadGeomAt(qadGeom, result, atGeom, atSubGeom)


# ===============================================================================
# getIntersectionPtsExtendQadGeometry
# ===============================================================================
def getIntersectionPtsExtendQadGeometry(linearObject, limitGeom, edgeMode):
   """
   la funzione calcola i punti di intersezione tra il prolungamento della parte lineare
   oltre il punto finale fino ad incontrare la geometria <limitGeom> secondo la modalità <edgeMode>.
   Vengono restituiti i punti che stanno oltre al punto finale di <linearObject>.
   <linearObject> = geometria base QAD da estendere (linea, arco, arco di ellisse, cerchio, ellisse)
   <limitGeom> = geometria QAD da usare come limite di estensione
   <edgeMode> se = 0 si deve estendere la geometria fino ad incontrare l'oggetto più vicino
              se = 1 si deve estendere la geometria fino ad incontrare l'oggetto più vicino o 
              anche il suo prolungamento
   """
   intPts = []

   intPts = QadIntersections.twoGeomObjectsExtensions(linearObject, limitGeom)
   if edgeMode == 0: # senza estendere limitGeom
      # cancello i punti di intersezione che non sono su limitGeom
      for i in range(len(intPts) - 1, -1, -1):
         if limitGeom.containsPt(intPts[i]) == False: del intPts[i]
   
   # cancello i punti di intersezione che sono su linearObject
   for i in range(len(intPts) - 1, -1, -1):
      if linearObject.containsPt(intPts[i]) == True: del intPts[i]
      
   # cancello i punti di intersezione che non sono oltre la fine di linearObject
   if linearObject.whatIs() == "LINE":
      angle = linearObject.getTanDirectionOnPt()
      for i in range(len(intPts) - 1, -1, -1):
         if qad_utils.doubleNear(angle, qad_utils.getAngleBy2Pts(linearObject.getStartPt(), intPts[i])) == False:
            del intPts[i]
   
   return intPts
         


# ===============================================================================
# trimQadGeometry
# ===============================================================================
def trimQadGeometry(qadGeom, pt, limitEntitySet, edgeMode):
   """
   la funzione taglia la geometria QAD (lineare) in una parte i cui limiti sono le intersezioni più
   vicine a pt con gli oggetti del gruppo <limitEntitySet> secondo la modalità <edgeMode>.
   <qadGeom> = geometria QAD da tagliare
   <pt> = punto che indica la parte di quell'oggetto che deve essere tagliata
   <limitEntitySet> = gruppo di entità che serve da limite di taglio
   <edgeMode> se = 0 si deve estendere la geometria fino ad incontrare l'oggetto più vicino
              se = 1 si deve estendere la geometria fino ad incontrare l'oggetto più vicino o 
              anche il suo prolungamento

   Ritorna una lista:
   (<geometria 1 risultante dall'operazione> <geometria 2 risultante dall'operazione> <atGeom> <atSubGeom>)
   """
   gType = qadGeom.whatIs()
   if gType == "POINT" or gType == "MULTI_POINT": return None

   # la funzione ritorna una lista con 
   # (<minima distanza>
   # <punto più vicino>
   # <indice della geometria più vicina>
   # <indice della sotto-geometria più vicina>
   # <indice della parte della sotto-geometria più vicina>
   # <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
   # -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
   # -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
   # )
   result = getQadGeomClosestPart(qadGeom, pt)
   nearPt = result[1]
   atGeom = result[2]
   atSubGeom = result[3]
   subGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom)

   # per ciascun entità di limitEntitySet cerco i punti di intersezione
   intPts = []                                                               
   entityIterator = QadEntitySetIterator(limitEntitySet)
   for limitEntity in entityIterator:
      intPts.extend(getIntersectionPtsTrimQadGeometry(subGeom, limitEntity.getQadGeom(), edgeMode))

   # ordino i punti di intersezione per distanza dal punto iniziale
   distFromStartList = []
   subGeomType = subGeom.whatIs()
   if subGeomType == "CIRCLE" or subGeomType == "ELLIPSE":
      # uso gli angoli
      for intPt in intPts:
         distFromStartList.append(qad_utils.getAngleBy2Pts(subGeom.center, intPt))
   else:
      # uso le distanze
      for intPt in intPts:
         distFromStartList.append(subGeom.getDistanceFromStart(intPt))
      
   intPtSortedList = []
   distFromStartSortedList = []
   minDist = sys.float_info.max
   i = 0
   while i < len(distFromStartList):
      insertAt = 0
      while insertAt < len(distFromStartSortedList):
         if distFromStartList[i] > distFromStartSortedList[insertAt]:
            insertAt = insertAt + 1
         else:
            break
         
      intPtSortedList.insert(insertAt, intPts[i])
      distFromStartSortedList.insert(insertAt, distFromStartList[i])
      i = i + 1
   
   if subGeomType == "CIRCLE" or subGeomType == "ELLIPSE":
      if len(intPtSortedList) < 2: return None
      distFromStart = qad_utils.getAngleBy2Pts(subGeom.center, nearPt)
      if subGeomType == "ELLIPSE":
         ellipseAngle = qad_utils.getAngleBy2Pts(subGeom.center, subGeom.majorAxisFinalPt)

      # cerco gli angoli che contengono il punto selezionato      
      i = 0
      while i < len(distFromStartSortedList) - 1:
         if qad_utils.isAngleBetweenAngles(distFromStartSortedList[i], distFromStartSortedList[i + 1], distFromStart):
            if subGeomType == "CIRCLE":
               return [QadArc().set(subGeom.center, subGeom.radius, distFromStartSortedList[i + 1], distFromStartSortedList[i]), None, atGeom, atSubGeom]
            else:
               return [QadEllipseArc().set(subGeom.center, subGeom.majorAxisFinalPt, subGeom.axisRatio, distFromStartSortedList[i + 1] - ellipseAngle, distFromStartSortedList[i] - ellipseAngle), None, atGeom, atSubGeom]
         i = i + 1
      
      if qad_utils.isAngleBetweenAngles(distFromStartSortedList[-1], distFromStartSortedList[0], distFromStart):
         if subGeomType == "CIRCLE":
            return [QadArc().set(subGeom.center, subGeom.radius, distFromStartSortedList[0], distFromStartSortedList[-1]), None, atGeom, atSubGeom]
         else:
            return [QadEllipseArc().set(subGeom.center, subGeom.majorAxisFinalPt, subGeom.axisRatio, distFromStartSortedList[0] - ellipseAngle, distFromStartSortedList[-1] - ellipseAngle), None, atGeom, atSubGeom]
         
#       if qad_utils.isAngleBetweenAngles(distFromStartList[0], distFromStartList[1], distFromStart):
#          firstAngle = distFromStartList[0]
#          secondAngle = distFromStartList[1]
#       else:
#          firstAngle = distFromStartList[1]
#          secondAngle = distFromStartList[0]
         
#       if subGeomType == "CIRCLE":
#          return [QadArc().set(subGeom.center, subGeom.radius, secondAngle, firstAngle), None, atGeom, atSubGeom]
#       else:
#          return [QadEllipseArc().set(subGeom.center, subGeom.majorAxisFinalPt, subGeom.axisRatio, secondAngle, firstAngle), None, atGeom, atSubGeom]

   distFromStart = subGeom.getDistanceFromStart(nearPt)
   
   i = 0
   firstPt = subGeom.getStartPt()
   while i < len(distFromStartSortedList):
      if distFromStart <= distFromStartSortedList[i]:
         break
      firstPt = intPtSortedList[i]
      i = i + 1
      
   if i < len(distFromStartSortedList):
      secondPt = intPtSortedList[i]
   else:
      secondPt = subGeom.getEndPt()
      
   if firstPt == subGeom.getStartPt() and secondPt == subGeom.getEndPt(): return None

   if firstPt == subGeom.getStartPt():
      return [subGeom.getGeomBetween2Pts(secondPt, subGeom.getEndPt()), None, atGeom, atSubGeom]
   elif secondPt == subGeom.getEndPt():
      return [subGeom.getGeomBetween2Pts(subGeom.getStartPt(), firstPt), None, atGeom, atSubGeom]
   else:
      g1 = subGeom.getGeomBetween2Pts(subGeom.getStartPt(), firstPt)
      g2 = subGeom.getGeomBetween2Pts(secondPt, subGeom.getEndPt())
      return [g1, g2, atGeom, atSubGeom]


# ===============================================================================
# getIntersectionPtsTrimQadGeometry
# ===============================================================================
def getIntersectionPtsTrimQadGeometry(qadGeom, limitGeom, edgeMode):
   """
   la funzione calcola i punti di intersezione tra <qadGeom> e la geometria <limitGeom> secondo la modalità <edgeMode>.
   <linearObject> = geometria base QAD da estendere (linea, arco, arco di ellisse, cerchio, ellisse)
   <limitGeom> = geometria QAD da usare come limite di estensione
   <edgeMode> se = 0 si deve estendere la geometria fino ad incontrare l'oggetto più vicino
              se = 1 si deve estendere la geometria fino ad incontrare l'oggetto più vicino o 
              anche il suo prolungamento
   """
   if edgeMode == 0: # senza estendere limitGeom
      return QadIntersections.twoGeomObjects(qadGeom, limitGeom)
   else: # estendendo limitGeom
      return QadIntersections.geomObjectWithGeomObjectExtensions(qadGeom, limitGeom)
