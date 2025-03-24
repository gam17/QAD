# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per offset
 
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
from qgis.gui import *
import qgis.utils

import math

from . import qad_utils
from .qad_geom_relations import *
from .qad_join_fun import selfJoinPolyline
from .qad_arc import QadArc
from .qad_polyline import *
from .qad_variables import QadVariables


# ===============================================================================
# offsetQGSGeom
# ===============================================================================
def offsetQGSGeom(qgsGeom, offsetDistOrPoint, gapType, forcedOffsetDist = None):
   """
   la funzione fa l'offset di una geometria di QGIS
   
   secondo una distanza o un punto (da cui calcolare la distanza)
   - per poligoni un valore positivo è verso l'esterno, negativo è verso l'interno
   - per linee un valore positivo è verso la sinistra, negativo è verso destra rispetto il verso della linea
   
    un modo <gapType>:
   0 = Estende i segmenti di linea alle relative intersezioni proiettate
   1 = Raccorda i segmenti di linea in corrispondenza delle relative intersezioni proiettate.
       Il raggio di ciascun segmento di arco é uguale alla distanza di offset
   2 = Cima i segmenti di linea in corrispondenza delle intersezioni proiettate.
       La distanza perpendicolare da ciascuna cima al rispettivo vertice
       sull'oggetto originale é uguale alla distanza di offset.
       
   se <offsetDistOrPoint> è un punto e forcedDist <> None
   la distanza viene forzata con questo parametro (che deve essere sempre positivo) mentre il lato di offset viene preso dal punto
   
   La funzione ritorna una lista di geometrie qgis risultato dell'offset
   """
   if type(offsetDistOrPoint) == QgsPointXY:
      # ritorna una tupla (<The squared cartesian distance>,
      #                    <minDistPoint>
      #                    <afterVertex>
      #                    <leftOf>)
      dummy = qgsGeom.closestSegmentWithContext(offsetDistOrPoint)
      if dummy is None or dummy[0] <= 0:
         return []
      if forcedOffsetDist is None:
         offsetDist = math.sqrt(dummy[0])  # radice quadrata
      else:
         offsetDist = forcedOffsetDist
      
      if offsetDist == 0:
         return []

      leftOf = dummy[3]
      if qgsGeom.type() == QgsWkbTypes.LineGeometry:
         # se leftOf > 0 il punto è a destra della linea quindi offsetDist deve essere negativo
         if leftOf > 0: 
            offsetDist = -offsetDist
      else:
         # se il punto è interno alla geometria offsetDist deve essere negativo
         if QgsGeometry.fromPointXY(offsetDistOrPoint).within(qgsGeom) == True:
            offsetDist = -offsetDist  
   else:
      offsetDist = offsetDistOrPoint

   atLeastNSegment = QadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), 12)
   if gapType == 0:
      joinStyle = Qgis.JoinStyle.Miter
   elif gapType == 1:
      joinStyle = Qgis.JoinStyle.Round
   elif gapType == 1:
      joinStyle = Qgis.JoinStyle.Bevel
      
   miterLimit= 20
   if qgsGeom.type() == QgsWkbTypes.LineGeometry:
      resultGeom = qgsGeom.offsetCurve(offsetDist, atLeastNSegment, joinStyle, miterLimit)
   else:
      capStyle = Qgis.EndCapStyle.Round
      resultGeom = qgsGeom.buffer(offsetDist, atLeastNSegment, capStyle, joinStyle, miterLimit)
      
   result = []
   if resultGeom is not None:            
      for part in resultGeom.parts():
         result.append(QgsGeometry.fromWkt(part.asWkt())) # se aggiungo direttamente part poi si pianta qgis

   return result


# ===============================================================================
# offsetPolyline
# ===============================================================================
def offsetPolyline(qadGeom, offsetDist, offsetSide, gapType):
   """
   la funzione fa l'offset di una geometria QAD
   secondo una distanza e un lato di offset ("right" o "left") 
   ed un modo <gapType>:
   0 = Estende i segmenti di linea alle relative intersezioni proiettate
   1 = Raccorda i segmenti di linea in corrispondenza delle relative intersezioni proiettate.
       Il raggio di ciascun segmento di arco é uguale alla distanza di offset
   2 = Cima i segmenti di linea in corrispondenza delle intersezioni proiettate.
       La distanza perpendicolare da ciascuna cima al rispettivo vertice
       sull'oggetto originale é uguale alla distanza di offset.
       
   La funzione ritorna una lista di geometrie qad risultato dell'offset
   """
   result = []
   
   linearObj = qadGeom.copy() # ne faccio una copia
   gType = linearObj.whatIs()
   if gType == "CIRCLE":
      # se offsetSide = "right" significa verso l'esterno del cerchio
      # se offsetSide = "left" significa verso l'interno del cerchio
      if offsetSide == "left":
         # offset verso l'interno del cerchio
         if linearObj.offset(offsetDist, "internal") == True: result.append(linearObj)
      else:
         # offset verso l'esterno del cerchio
         if linearObj.offset(offsetDist, "external") == True: result.append(linearObj)
   elif gType == "ELLIPSE":
      # l'offset di una ellisse non è una ellisse
      # se offsetSide = "right" significa verso l'esterno dell'ellisse
      # se offsetSide = "left" significa verso l'interno dell'ellisse
      if offsetSide == "left":
         # offset verso l'interno dell'ellisse
         pts = linearObj.offset(offsetDist, "internal")
      else:
         # offset verso l'esterno dell'ellisse
         pts = linearObj.offset(offsetDist, "external")
      
      if pts is not None:      
         polyline = QadPolyline()
         polyline.fromPolyline(pts)
         result.append(polyline)
   elif gType == "LINE" or gType == "ARC":
      if linearObj.offset(offsetDist, offsetSide) == True: result.append(linearObj)
   elif gType == "ELLIPSE_ARC":
      # l'offset di una ellisse non è una ellisse
      pts = linearObj.offset(offsetDist, offsetSide)
      if pts is not None:      
         polyline = QadPolyline()
         polyline.fromPolyline(pts)
         result.append(polyline)
   elif gType == "POLYLINE":
      # attualmente gli archi di ellisse in una polilinea non sono supportati quindi li trasformo in segmenti
      if linearObj.segmentizeEllipseArcs() == False:
         return []
      # ottengo la polilinea di offset non tagliata
      untrimmedOffsetPolyline = getUntrimmedOffSetPolyline(linearObj, offsetDist, offsetSide, gapType)
      # test
      #return [untrimmedOffsetPolyline]

      # inverto il senso dei punti x ottenere la polilinea di offset non tagliata invertita
      reversedPolyline = linearObj.copy() # duplico la polilinea
      reversedPolyline.reverse()   
      untrimmedReversedOffsetPolyline = getUntrimmedOffSetPolyline(reversedPolyline, offsetDist, offsetSide, gapType)

      # test
      #return [untrimmedReversedOffsetPolyline]
            
      # taglio la polilinea dove necessario
      result = getTrimmedOffSetPolyline(linearObj, \
                                        untrimmedOffsetPolyline, \
                                        untrimmedReversedOffsetPolyline, \
                                        offsetDist)

   return result



# ===============================================================================
# dualClipping
# ===============================================================================
def dualClipping(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, offsetDist):
   """
   la funzione effettua il dual clipping su untrimmedOffsetPolyline.
   <polyline>: lista delle parti originali della polilinea 
   <untrimmedOffsetPolyline>: lista delle parti non tagliate derivate dall'offset
   <untrimmedReversedOffsetPolyline>: lista delle parti non tagliate derivate dall'offset in senso inverso
       
   La funzione ritorna una lista di parti risultato del dual clipping 
   """
   
   # inizio Dual Clipping
      
   # Calcolo i punti di intersezione tra <untrimmedOffsetPolyline> e <untrimmedReversedOffsetPolyline>
   intPtList = getIntersectionPointsWithPolyline(untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline)
   # Calcolo i punti di self intersection di <untrimmedOffsetPolyline>
   intSelfPtList = getSelfIntersectionPoints(untrimmedOffsetPolyline)
   """ 
      Le 2 funzioni precedenti restituiscono una lista in cui ogni elemento è una sottolista composta da:
      1) punto di intersezione della polilinea con se stessa
      2) distanza del punti di intersezione dall'inizio della polilinea
      3) numero della parte contenente il punto di intersezione
   """
   # Aggiungo alla lista di punti di intersezione quelli di tipo self intersection senza duplicare i punti
   # usando come chiave univoca le coordinate del punto e il numero di parte su cui si trova il punto
   lenOriginalIntPtList = len(intPtList)
   for intSelfPt in intSelfPtList:   
      found = False
      for i in range(lenOriginalIntPtList):
         intPt = intPtList[i]
         # se i punti sono così vicini da essere considerati uguali e si tratta della stessa parte
         if qad_utils.ptNear(intPt[0], intSelfPt[0]) == True and \
            intPt[2] == intSelfPt[2]:
            found = True
         
      if found == False:   
         intPtList.append(intSelfPt)
      
   # se non ci sono punti di intersezione nè quelli di tipo self intersection
   if len(intPtList) == 0:
      return untrimmedOffsetPolyline.defList
   
   # ordino i punti di intersezione per distanza dall'inizio di untrimmedOffsetPolyline
   intPtListOrderedByDistFromStart = []
   for intPt in intPtList: 
      insertAt = 0
      for intPtOrderedByDistFromStart in intPtListOrderedByDistFromStart:
         if intPtOrderedByDistFromStart[1] < intPt[1]:
            insertAt = insertAt + 1
         else:
            break
      intPtListOrderedByDistFromStart.insert(insertAt, intPt)
   
   # genero una nuova lista con le parti con intersezioni divise in tante sottoparti
   splittedPolyline = []
   for iPart in range(len(untrimmedOffsetPolyline.defList)):
      part = untrimmedOffsetPolyline.getLinearObjectAt(iPart)
      # verifico se la parte ha delle intersezioni
      subPartList = []
      for intPt in intPtListOrderedByDistFromStart:
         if (intPt[2] == iPart): # se l'intersezione si riferisce alla parte interessata
            if len(subPartList) == 0: # prima intersezione per questa parte
               subPartList.append(part.getGeomBetween2Pts(part.getStartPt(), intPt[0]))
            else: # dalla seconda intersezione in poi
               subPartList.append(part.getGeomBetween2Pts(lastIntPt[0], intPt[0]))
            lastIntPt = intPt
         else:
            if intPt[2] > iPart: # non continuo con le intersezioni delle parti successive
               break
      if len(subPartList) > 0: # se la parte è stata divisa in sotto-parti
         subPartList.append(part.getGeomBetween2Pts(lastIntPt[0], part.getEndPt()))                  
         splittedPolyline.extend(subPartList)
      else:
         splittedPolyline.append(part)
         
   # test
   #return splittedPolyline
   
   dualClippedPartList = []
   partListForClipByCircle = [] # lista di parti che devono essere sottoposte al taglio con un cerchio
   #nPenultimaParte = polyline.qty() - 2 # 0-indexed
   circle = QadCircle()
   
   # per tutte le parti di splittedPolyline
   for part in splittedPolyline:
      # calcolo le intersezioni della parte con tutte le parti di <polyline> (polilinea orginale)
      dummyPolyline = QadPolyline()
      dummyPolyline.append(part)
      intPtList = getIntersectionPointsWithPolyline(polyline, dummyPolyline)      
      # se non ci sono punti di intersezione aggiungo questa parte a dualClippedPartList
      if len(intPtList) == 0:
         dualClippedPartList.append(part)
      else: # se esistono punti di intersezione         
         # verifico se tutti i punti di intersezione non sono sul primo segmento o sul penultimo segmento di <polyline>
         reject = True
         for intPt in intPtList:
            if intPt[2] == 0 or intPt[2] == polyline.qty() - 1: # se almeno un punto di intersezione è sul primo o sull'ultimo segmento
               reject = False
               break
         
         if reject == False:
            # attengo le parti di <part> che sono esterne a tutti i cerchi 
            # con centro = i punti di intersezione e raggio = la distanza di offset
            partListForClipByCircle = [part]
            for intPt in intPtList:
               # Costruisco un cerchio il cui centro è il punto di intersezione e il raggio è la distanza di offset
               circle.set(intPt[0], offsetDist)
               
               i = 0
               while i < len(partListForClipByCircle):
                  externalPartsOfIntPt = getPartsExternalToCircle(partListForClipByCircle[i], circle)
                  del partListForClipByCircle[i]
                  for externalPartOfIntPt in externalPartsOfIntPt.defList:
                     partListForClipByCircle.insert(i, externalPartOfIntPt)
                     i = i + 1
            
            for partForClipByCircle in partListForClipByCircle:
               dualClippedPartList.append(partForClipByCircle)
      
   return dualClippedPartList


# ===============================================================================
# generalClosedPointPairClipping
# ===============================================================================
def generalClosedPointPairClipping(polyline, dualClippedPolyline, offsetDist):
   """
   la funzione effettua il general closed point pair clipping su dualClippedPolyline.
   <polyline>: lista delle parti originali della polilinea 
   <dualClippedPolyline>: lista delle parti risultato del dual clipping
   <offsetDist> distanza di offset
   
   Per ogni parte della polilinea originale cerco qual'è il punto più vicino per ogni
   parte di dualClippedPolyline. Se questo punto è più vicino di offsetDist allora faccio
   un cerchio con centro il punto della polilinea originale e cancello il
   pezzo di segmento di dualClippedPolyline iterno al cerchio. Questo per eliminare i pezzi di
   dualClippedPolyline più vicino di offsetDist a polyline.
       
   La funzione ritorna una lista di parti risultato del general closed point pair clipping
   """
   # inizio di General Closed Point Pair clipping
   GCPPCList = QadPolyline(dualClippedPolyline) # duplico la lista di parti      
   circle = QadCircle()
  
#    # per ogni parte di polyline
#    for part in polyline.defList:
#       # per ogni parte di GCPPCList
#       i = 0
#       while i < GCPPCList.qty():
#          GCPPCPart = GCPPCList.getLinearObjectAt(i)
#          # verifico quale é il punto di part più vicino a GCPPCPart
#          # la funzione ritorna <distanza minima><punto di distanza minima su object1><punto di distanza minima su object2>
#          MinDistancePts = QadMinDistance.fromTwoBasicGeomObjects(part, GCPPCPart)
#          # se la distanza é inferiore a offsetDist (e non così vicina da essere considerata uguale)
#          if qad_utils.doubleSmaller(MinDistancePts[0], offsetDist):
#             # creo un cerchio nel punto di part più vicino a GCPPCPart
#             circle.set(MinDistancePts[1], offsetDist)
#             # ottengo le parti di GCPPCPart esterne al cerchio 
#             splittedParts = getPartsExternalToCircle(GCPPCPart, circle)
#             # se la splittedParts è composta da una sola parte che è uguale a GCPPCPart
#             # ad es. se GCPPCPart è tangente al cerchio allora non faccio niente
#             if splittedParts.qty() == 1 and splittedParts.getLinearObjectAt(0) == GCPPCPart:
#                i = i + 1
#             else:
#                # le sostituisco a GCPPCPart
#                GCPPCList.remove(i)
#                for splittedPart in splittedParts.defList:
#                   GCPPCList.insert(i, splittedPart)
#                   i = i + 1
#          else:
#             i = i + 1   
   
#    GCPPCList = QadPolyline()      
#    circle = QadCircle()
#   
#    # per ogni parte di GCPPCList cerco la coppia dei punti più vicini con <polyline> 
#    for part in dualClippedPolyline:
#       """
#       la funzione ritorna 
#       <distanza minima>
#       <punto di distanza minima su object1>
#       <geomIndex su object1>
#       <subGeomIndex su object1>
#       <partIndex su object1>
#       <punto di distanza minima su object2>
#       <geomIndex su object2>
#       <subGeomIndex su object2>
#       <partIndex su object2>
#       dei 2 oggetti geometrici.
#       """
#       for origPart in polyline.defList:
#          MinDistancePts = QadMinDistance.fromTwoGeomObjects(part, origPart)
#          # se la distanza é inferiore a offsetDist (per precisione dei calcoli potrebbe essere molto vicina quindi accetto una tolleranza)
#          if qad_utils.doubleSmaller(MinDistancePts[0], offsetDist) == True:
#             # creo un cerchio nel punto di polyline più vicino a part
#             circle.set(MinDistancePts[5], offsetDist)
#             # ottengo le parti di part esterne al cerchio 
#             splittedParts = getPartsExternalToCircle(part, circle)
#             for splittedPart in splittedParts.defList:
#                GCPPCList.append(splittedPart)         
#          else:
#             GCPPCList.append(part)
                       
   GCPPCList = QadPolyline()      
   circle = QadCircle()
   
   # per ogni parte di dualClippedPolyline cerco la coppia dei punti più vicini con <polyline> 
   for part in dualClippedPolyline:
      """
      la funzione ritorna 
      <distanza minima>
      <punto di distanza minima su object1>
      <punto di distanza minima su object2>
      """
      splittedParts = [part]
      for origPart in polyline.defList:
         while True:
            i = 0
            splitted = False
            while i < len(splittedParts):
               splittedPart = splittedParts[i]         
               MinDistancePts = QadMinDistance.fromTwoBasicGeomObjects(splittedPart, origPart)
               # se la distanza é inferiore a offsetDist (per precisione dei calcoli potrebbe essere molto vicina quindi accetto una tolleranza)
               if qad_utils.doubleSmaller(MinDistancePts[0], offsetDist) == True:
                  splitted = True
                  # creo un cerchio nel punto di polyline più vicino a part
                  circle.set(MinDistancePts[2], offsetDist)
                  # ottengo le parti di parti esterne al cerchio 
                  outsideParts = getPartsExternalToCircle(splittedPart, circle)
                  # le sostituisco a splittedPart
                  del splittedParts[i]
                  for outsidePart in outsideParts.defList:
                     splittedParts.insert(i, outsidePart)
                     i = i + 1            
               else:
                  i = i + 1
                  
            if splitted == False:
               break
      
      for splittedPart in splittedParts:       
         GCPPCList.append(splittedPart)                     
                       
   return GCPPCList


# ===============================================================================
# getTrimmedOffSetPolyline
# ===============================================================================
def getTrimmedOffSetPolyline(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, \
                             offsetDist):
   """
   la funzione taglia la polilinea dove necessario usando <dual clipping> e <general Closed Point Pair Clipping>.
   <polyline>: lista delle parti originali della polilinea 
   <untrimmedOffsetPolyline>: lista delle parti non tagliate derivate dall'offset
   <untrimmedReversedOffsetPolyline>: lista delle partinon tagliate derivate dall'offset in senso inverso
   <offsetDist> distanza di offset
       
   La funzione ritorna una lista di parti della polilinee (lista di segmenti o archi o archi di ellisse) 
   """
   
   # faccio il dual clipping
   dualClippedPolyline = dualClipping(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, offsetDist)   
   # test
   #return dualClippedPolyline
   #GCPPCList = untrimmedOffsetPolyline
   #GCPPCList = dualClipping(polyline, untrimmedOffsetPolyline, untrimmedReversedOffsetPolyline, offsetDist)
     
   # faccio il general closed point pair clipping
   GCPPCList = generalClosedPointPairClipping(polyline, dualClippedPolyline, offsetDist)
   # test
   #return GCPPCList.defList
   
   # faccio il join tra le parti
   return selfJoinPolyline(GCPPCList)


# ===============================================================================
# getUntrimmedOffSetPolyline
# ===============================================================================
def getUntrimmedOffSetPolyline(polyline, offsetDist, offsetSide, gapType):
   """
   la funzione fa l'offset non pulito da eventuali tagli da apportare (vedi
   getTrimmedOffSetPolyline") di una polilinea
   secondo una distanza e un lato di offset ("right" o "left") 
   ed un modo <gapType>:
   0 = Estende i segmenti di linea alle relative intersezioni proiettate
   1 = Raccorda i segmenti di linea in corrispondenza delle relative intersezioni proiettate.
       Il raggio di ciascun segmento di arco é uguale alla distanza di offset
   2 = Cima i segmenti di linea in corrispondenza delle intersezioni proiettate.
       La distanza perpendicolare da ciascuna cima al rispettivo vertice
       sull'oggetto originale é uguale alla distanza di offset.
       
   La funzione ritorna una polilinea le cui parti non sono collegate
   """
   # verifico se polilinea chiusa
   isClosedPolyline = polyline.isClosed()

   # creo una lista dei segmenti e archi che formano la polilinea
   polyline = preTreatmentOffset(polyline)
     
   # faccio l'offset di ogni parte della polilinea
   newPolyline = QadPolyline()
   i = 0
   while i < polyline.qty():
      part = polyline.getLinearObjectAt(i)
      gType = part.whatIs()
      if gType == "LINE": # segmento
         newPart = part.copy()
         newPart.offset(offsetDist, offsetSide)
         newPolyline.append(newPart)
      elif gType == "ARC": # arco
         newPart = part.copy()
         if newPart.offset(offsetDist, offsetSide) == True:
            newPolyline.append(newPart)
      elif gType == "ELLIPSE_ARC": # arco di ellisse
         pts = part.offset(offsetDist, offsetSide)
         if pts is not None:
            offsetEllipseArc = QadPolyline()
            if offsetEllipseArc.fromPolyline(pts) == True:
               newPolyline.appendPolyline(offsetEllipseArc)
            del pts

      i = i + 1
      
   # test fino qui OK
   # return newPolyline
         
   # calcolo i punti di intersezione tra parti adiacenti
   # per ottenere una linea di offset non tagliata
   if isClosedPolyline == True:
      i = -1
   else:
      i = 0

   untrimmedOffsetPolyline = QadPolyline()
   virtualPartPositionList = []
   while i < newPolyline.qty() - 1:
      if i == -1: # polylinea chiusa quindi prendo in esame l'ultimo segmento e il primo
         part = newPolyline.getLinearObjectAt(-1) # ultima parte
         nextPart = newPolyline.getLinearObjectAt(0) # prima parte
      else:                  
         part = newPolyline.getLinearObjectAt(i)
         nextPart = newPolyline.getLinearObjectAt(i + 1)

      if untrimmedOffsetPolyline.qty() == 0:
         lastUntrimmedOffsetPt = part.getStartPt()
      else:
         lastUntrimmedOffsetPt = untrimmedOffsetPolyline.getLinearObjectAt(-1).getEndPt() # ultima parte
      
      IntPointInfo = getIntersectionPointInfoOffset(part, nextPart)
      if IntPointInfo is not None: # se c'é  un'intersezione
         IntPoint = IntPointInfo[0]
         IntPointTypeForPart = IntPointInfo[1]
         IntPointTypeForNextPart = IntPointInfo[2]

      if part.whatIs() == "LINE": # segmento
         if nextPart.whatIs() == "LINE": # segmento-segmento
            if IntPointInfo is not None: # se esiste un punto di intersezione
               if IntPointTypeForPart == 1: # TIP
                  if IntPointTypeForNextPart == 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))
                  else: # FIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # aggiungo la posizione di questa parte virtuale
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
               else: # FIP
                  if IntPointTypeForPart == 3: # PFIP
                     if gapType != 0:
                        newLines = offsetBridgeTheGapBetweenLines(part, nextPart, offsetDist, gapType)
                        untrimmedOffsetPolyline.append(newLines[0])                
                        untrimmedOffsetPolyline.append(newLines[1]) # arco o linea di raccordo
                     else:                    
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))
                  else: # NFIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # aggiungo la posizione di questa parte virtuale
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
                     
         elif nextPart.whatIs() == "ARC": # segmento-arco
            if IntPointInfo is not None: # se esiste un punto di intersezione
               if IntPointTypeForPart == 1: # TIP
                  if IntPointTypeForNextPart == 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))
                  else: # FIP
                     untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # aggiungo la posizione di questa parte virtuale
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
               else: # FIP
                  if IntPointTypeForPart == 3: # PFIP
                     if IntPointTypeForNextPart == 2: # FIP
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                        newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
                        if newPart is not None:
                           untrimmedOffsetPolyline.append(newPart)
                     elif IntPointTypeForNextPart == 1: # TIP
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, IntPoint))                           
                  else: # NFIP
                     if IntPointTypeForNextPart == 1: # TIP
                        untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
                        untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                        # aggiungo la posizione di questa parte virtuale
                        virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
            else: # non esiste un punto di intersezione
               untrimmedOffsetPolyline.append(QadLine().set(lastUntrimmedOffsetPt, part.getEndPt()))
               newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
               if newPart is not None:
                  untrimmedOffsetPolyline.append(newPart)
      elif part.whatIs() == "ARC": # arco
         if nextPart.whatIs() == "LINE": # arco-segmento
            if IntPointInfo is not None: # se esiste un punto di intersezione
               if IntPointTypeForPart == 1: # TIP
                  newPart = part.copy()
                  newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
                  newPart.setEndPt(IntPoint) # modifico l'arco
                  untrimmedOffsetPolyline.append(newPart)
                  
                  if IntPointTypeForNextPart != 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(IntPoint, nextPart.getStartPt()))
                     # aggiungo la posizione di questa parte virtuale
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
                     
               else: # FIP
                  newPart = part.copy()
                  newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
                  untrimmedOffsetPolyline.append(newPart)
                  
                  if IntPointTypeForNextPart == 4: # NFIP
                     newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
                     if newPart is not None:
                        untrimmedOffsetPolyline.append(newPart)               
                  elif IntPointTypeForNextPart == 1: # TIP
                     untrimmedOffsetPolyline.append(QadLine().set(part.getEndPt(), nextPart.getStartPt()))
                     # aggiungo la posizione di questa parte virtuale
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
            else: # non esiste un punto di intersezione
               newPart = part.copy()
               newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
               untrimmedOffsetPolyline.append(newPart)
               newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
               if newPart is not None:
                  untrimmedOffsetPolyline.append(newPart)

         elif nextPart.whatIs() == "ARC": # arco-arco
            if IntPointInfo is not None: # se esiste un punto di intersezione
               if IntPointTypeForPart == 1: # TIP
                  if IntPointTypeForNextPart == 1: # TIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
                     newPart.setEndPt(IntPoint) # modifico l'arco
                     untrimmedOffsetPolyline.append(newPart)
                  else : # FIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
                     untrimmedOffsetPolyline.append(newPart)
                     
                     if part.reversed == False:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.endAngle, part.radius - offsetDist)
                     else:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.startAngle, part.radius - offsetDist)
                        
                     secondPtNewArc = qad_utils.getPolarPointByPtAngle(center, \
                                                                       qad_utils.getAngleBy2Pts(center, IntPoint), \
                                                                       offsetDist)                     
                     newArc = QadArc()
                     newArc.fromStartSecondEndPts(part.getEndPt(), \
                                                  secondPtNewArc, \
                                                  nextPart.getStartPt())

                     untrimmedOffsetPolyline.append(newArc)
                     # aggiungo la posizione di questa parte virtuale
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
               else: # FIP
                  if IntPointTypeForNextPart == 1: # TIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
                     untrimmedOffsetPolyline.append(newPart)
                     
                     if reversed == False:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.endAngle, part.radius - offsetDist)
                     else:
                        center = qad_utils.getPolarPointByPtAngle(part.center, part.startAngle, part.radius - offsetDist)
                        
                     secondPtNewArc = qad_utils.getPolarPointByPtAngle(center, \
                                                                       qad_utils.getAngleBy2Pts(center, IntPoint), \
                                                                       offsetDist)                     
                     newArc = QadArc()
                     newArc.fromStartSecondEndPts(part.getEndPt(), \
                                                  secondPtNewArc, \
                                                  nextPart.getStartPt())
                     untrimmedOffsetPolyline.append(newArc)
                     # aggiungo la posizione di questa parte virtuale
                     virtualPartPositionList.append(untrimmedOffsetPolyline.qty() - 1)
                  else: # FIP
                     newPart = part.copy()
                     newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
                     newPart.setEndPt(IntPoint) # modifico l'arco
                     untrimmedOffsetPolyline.append(newPart)                     
            else: # non esiste un punto di intersezione
               newPart = part.copy()
               newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'arco
               untrimmedOffsetPolyline.append(newPart)
               
               # prima di raccordare verifico se l'arco <part> si trova interamente dentro la zona di offset
               # dell'arco <nextPart> e viceversa. 
               # Per replicare questa eccezione fare una polilinea composta da 2 archi:
               # il primo con centro in ..., raggio..., angolo iniziale ... angolo finale ...
               # il secondo con centro in ..., raggio..., angolo iniziale ... angolo finale ...
               # offset a destra = 8
               dist = qad_utils.getDistance(part.center, nextPart.center)               
               minDistArc, maxDistArc = getOffsetDistancesFromCenterOnOffsetedArc(part, offsetDist, offsetSide)
               minDistNextArc, maxDistNextArc = getOffsetDistancesFromCenterOnOffsetedArc(nextPart, offsetDist, offsetSide)
               
               if (dist + nextPart.radius <= maxDistArc and dist - nextPart.radius >= minDistArc) or \
                  (dist + part.radius <= maxDistNextArc and dist - part.radius >= minDistNextArc):
                  untrimmedOffsetPolyline.append(QadLine().set(newPart.getEndPt(), nextPart.getStartPt()))
               else:
                  newPart = fillet2PartsOffset(part, nextPart, offsetSide, offsetDist)
                  if newPart is not None:
                     untrimmedOffsetPolyline.append(newPart)
               
      i = i + 1

   if newPolyline.qty() > 0:
      if isClosedPolyline == False:
         if untrimmedOffsetPolyline.qty() == 0:
            # primo punto della prima parte di newPolyline
            lastUntrimmedOffsetPt = newPolyline.getLinearObjectAt(0).getStartPt()
         else:
            # ultimo punto dell'ultima parte di untrimmedOffsetPolyline
            lastUntrimmedOffsetPt = untrimmedOffsetPolyline.getLinearObjectAt(-1).getEndPt()
            
         newPart = newPolyline.getLinearObjectAt(-1).copy()
         newPart.setStartPt(lastUntrimmedOffsetPt) # modifico l'inizio
         untrimmedOffsetPolyline.append(newPart)
      else:
         # primo punto = ultimo punto
         untrimmedOffsetPolyline.getLinearObjectAt(0).setStartPt(untrimmedOffsetPolyline.getLinearObjectAt(-1).getEndPt()) # modifico l'inizio

   # faccio un pre-clipping sulle parti virtuali
   #return virtualPartClipping(untrimmedOffsetPolyline, virtualPartPositionList)
   # test
   return untrimmedOffsetPolyline


# ===============================================================================
# preTreatmentOffset
# ===============================================================================
def preTreatmentOffset(polyline):
   """
   la funzione controlla le "local self intersection"> :
   se il segmento (o arco o arco di ellisse) i-esimo e il successivo hanno 2 intersezioni allora si inserisce un vertice
   nel segmento (o arco o arco di ellisse) i-esimo tra i 2 punti di intersezione.
   La funzione riceve una lista di segmenti, archi ed archi di ellisse e ritorna una nuova lista di parti
   """
   # verifico se polilinea chiusa
   i = -1 if polyline.isClosed() else 0   
   
   result = QadPolyline()
   while i < polyline.qty() - 1:
      if i == -1: # polilinea chiusa quindi prendo in esame l'ultimo segmento e il primo
         part = polyline.getLinearObjectAt(-1)
         nextPart = polyline.getLinearObjectAt(0)
      else:                  
         part = polyline.getLinearObjectAt(i)
         nextPart = polyline.getLinearObjectAt(i + 1)

      ptIntList = QadIntersections.twoBasicGeomObjects(part, nextPart)
      if len(ptIntList) == 2: # 2 punti di intersezione
         # calcolo il punto medio tra i 2 punti di intersezione in part
         gType = part.whatIs()
         if gType == "LINE": # segmento
            ptMiddle = qad_utils.getMiddlePoint(ptIntList[0], ptIntList[1])
            result.append(QadLine().set(part.getStartPt(), ptMiddle))
            result.append(QadLine().set(ptMiddle, part.getEndPt()))
         elif gType == "ARC": # arco
            arc1 = part.copy()
            arc2 = part.copy()
            # se i punti sono così vicini da essere considerati uguali
            if qad_utils.ptNear(part.getEndPt(), ptIntList[0]):
               ptInt = part.getEndPt()
            else:
               ptInt = part.getStartPt()
            
            arc1.setEndPt(ptInt)
            arc2.setStartPt(ptInt)
            result.append(arc1)
            result.append(arc2)
      else: # un solo punto di intersezione
         result.append(part)
      
      i = i + 1
   
   if polyline.isClosed() == False: # se non é chiusa aggiungo l'ultima parte
      if polyline.qty() > 1:
         result.append(nextPart)   
      else:
         result.append(polyline.getLinearObjectAt(0))
   
   return result


# ===============================================================================
# getIntersectionPointInfoOffset
# ===============================================================================
def getIntersectionPointInfoOffset(part, nextPart):
   """
   la funzione restituisce il punto di intersezione tra le 2 parti e
   e il tipo di intersezione per <part> e per <nextPart>.
   Alle parti deve essere già stato fatto l'offset singolarmente:
   
   1 = TIP (True Intersection Point) se il punto di intersezione ottenuto estendendo 
   le 2 parti si trova su <part>
   
   2  = FIP (False Intersection Point) se il punto di intersezione ottenuto estendendo
   le 2 parti non si trova su <part>
   
   3 = PFIP (Positive FIP) se il punto di intersezione é nella stessa direzione di part

   4 = NFIP (Negative FIP) se il punto di intersezione é nella direzione opposta di part
   """

   ptIntList = QadIntersections.twoBasicGeomObjectExtensions(part, nextPart)

   if len(ptIntList) == 0:
      if qad_utils.ptNear(part.getEndPt(), nextPart.getStartPt()) == True:
      #if part.getEndPt() == nextPart.getStartPt(): # <nextPart> inizia dove finisce <part>
         return [part.getEndPt(), 1, 1] # TIP-TIP
      else:
         return None
   elif len(ptIntList) == 1:
      gType = part.whatIs()
      if gType == "LINE": # segmento
         if part.containsPt(ptIntList[0]):
            intTypePart = 1 # TIP
         else: # l'intersezione non é sul segmento (FIP)
            # se la direzione é la stessa del segmento
            if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(part.getStartPt(), part.getEndPt()), \
                                    qad_utils.getAngleBy2Pts(part.getStartPt(), ptIntList[0])):
               intTypePart = 3 # PFIP
            else:
               intTypePart = 4 # NFIP
      else: # arco o arco di ellisse
         if part.containsPt(ptIntList[0]):
            intTypePart = 1 # TIP
         else:
            intTypePart = 2 # FIP

      gType = nextPart.whatIs()
      if gType == "LINE": # segmento
         if nextPart.containsPt(ptIntList[0]):
            intTypeNextPart = 1 # TIP
         else: # l'intersezione non é sul segmento (FIP)
            # se la direzione é la stessa del segmento
            if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(nextPart.getStartPt(), nextPart.getEndPt()), \
                                    qad_utils.getAngleBy2Pts(nextPart.getStartPt(), ptIntList[0])):
               intTypeNextPart = 3 # PFIP
            else:
               intTypeNextPart = 4 # NFIP
      else: # arco o arco di ellisse
         if nextPart.containsPt(ptIntList[0]):
            intTypeNextPart = 1 # TIP
         else:
            intTypeNextPart = 2 # FIP

      return [ptIntList[0], intTypePart, intTypeNextPart]
   
   else: # 2 punti di intersezione
      # scelgo il punto più vicino al punto finale di part     
      gType = part.whatIs()
      if gType == "LINE": # segmento
         if qad_utils.getDistance(ptIntList[0], part.getEndPt()) < qad_utils.getDistance(ptIntList[1], part.getEndPt()):
            ptInt = ptIntList[0]
         else:
            ptInt = ptIntList[1]

         if part.containsPt(ptInt):
            intTypePart = 1 # TIP
         else: # l'intersezione non é sul segmento (FIP)
            # se la direzione é la stessa del segmento
            if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(part.getStartPt(), part.getEndPt()), \
                                    qad_utils.getAngleBy2Pts(part.getStartPt(), ptInt)):
               intTypePart = 3 # PFIP
            else:
               intTypePart = 4 # NFIP

         # la seconda parte é sicuramente un'arco
         if nextPart.containsPt(ptInt):
            intTypeNextPart = 1 # TIP
         else: # l'intersezione non é sull'arco (FIP)
            intTypeNextPart = 2 # FIP         

         return [ptInt, intTypePart, intTypeNextPart]
      else: # arco o arco di ellisse
         finalPt = part.getEndPt()

         if qad_utils.getDistance(ptIntList[0], finalPt) < qad_utils.getDistance(ptIntList[1], finalPt):
            ptInt = ptIntList[0]
         else:
            ptInt = ptIntList[1]

         if part.containsPt(ptInt):
            intTypePart = 1 # TIP
         else: # l'intersezione non é sull'arco (FIP)
            intTypePart = 2 # FIP         

         gType = nextPart.whatIs()
         if gType == "LINE": # segmento
            if nextPart.containsPt(ptInt):
               intTypeNextPart = 1 # TIP
            else: # l'intersezione non é sul segmento (FIP)
               # se la direzione é la stessa del segmento
               if qad_utils.doubleNear(qad_utils.getAngleBy2Pts(nextPart.getStartPt(), nextPart.getEndPt()), \
                                       qad_utils.getAngleBy2Pts(nextPart.getStartPt(), ptInt)):
                  intTypeNextPart = 3 # PFIP
               else:
                  intTypeNextPart = 4 # NFIP
         else: # arco o arco di ellisse
            if nextPart.containsPt(ptInt):
               intTypeNextPart = 1 # TIP
            else: # l'intersezione non é sull'arco (FIP)
               intTypeNextPart = 2 # FIP
                        
         return [ptInt, intTypePart, intTypeNextPart]


# ============================================================================
# getSelfIntersectionPoints
# ============================================================================
def getSelfIntersectionPoints(polyline):
   """
   la funzione restituisce una lista in cui ogni elemento è una sottolista composta da:
   1) punto di intersezione della polilinea con se stessa
   2) distanza del punti di intersezione dall'inizio della polilinea
   3) numero della parte contenente il punto di intersezione      
   """
   result = []
   distFromStartPrevPart = 0    
   for iPart in range(len(polyline.defList)):
      part = polyline.defList[iPart]
      startPtOfPart = part.getStartPt()
      endPtOfPart = part.getEndPt()
         
      # calcolo le intersezioni con tutte le parti ad eccezione di se stessa
      for jPart in range(len(polyline.defList)):
         if (iPart == jPart):
            continue
         partialIntPtList = QadIntersections.twoBasicGeomObjects(part, polyline.defList[jPart])
         for partialIntPt in partialIntPtList:
            # escludo i punti che sono all'inizio-fine di part
            # se i punti sono così vicini da essere considerati uguali         
            if qad_utils.ptNear(startPtOfPart, partialIntPt) == False and \
               qad_utils.ptNear(endPtOfPart, partialIntPt) == False:
               # inserisco il punto con lar distanza dall'inizio della polilinea e il numero di parte
               distFromStartPart = part.getDistanceFromStart(partialIntPt)
               result.append([partialIntPt, distFromStartPart + distFromStartPrevPart, iPart])
                              
      distFromStartPrevPart += part.length()
               
   return result


# ============================================================================
# getIntersectionPointsWithPolyline
# ============================================================================
def getIntersectionPointsWithPolyline(polyline1, polyline2):
   """
   la funzione restituisce una lista in cui ogni elemento è una sottolista composta da:
   1) punto di intersezione della polilinea con <polyline2>
   2) distanza del punti di intersezione dall'inizio della polilinea
   3) numero della parte contenente il punto di intersezione      
   """
   result = []
   distFromStartPrevPart = 0    
   for iPart in range(len(polyline1.defList)):
      part = polyline1.defList[iPart]
      startPtOfPart = part.getStartPt()
      endPtOfPart = part.getEndPt()
         
      # calcolo le intersezioni con tutte le parti di <polyline2>
      for jPart in range(len(polyline2.defList)):
         partialIntPtList = QadIntersections.twoBasicGeomObjects(part, polyline2.defList[jPart])
         for partialIntPt in partialIntPtList:
            # escludo i punti che sono all'inizio-fine di part
            # se i punti sono così vicini da essere considerati uguali         
            if qad_utils.ptNear(startPtOfPart, partialIntPt) == False and \
               qad_utils.ptNear(endPtOfPart, partialIntPt) == False:
               # inserisco il punto con lar distanza dall'inizio della polilinea e il numero di parte
               distFromStartPart = part.getDistanceFromStart(partialIntPt)
               result.append([partialIntPt, distFromStartPart + distFromStartPrevPart, iPart])
            
      distFromStartPrevPart += part.length()
               
   return result



# ===============================================================================
# offsetBridgeTheGapBetweenLines
# ===============================================================================


def offsetBridgeTheGapBetweenLines(line1, line2, offset, gapType):
   """   
   la funzione colma il vuoto tra 2 segmenti retti (QadLine) nel comando offset
   secondo una distanza <offset> (che corrisponde alla distanza di offset s 
   chiamata da tale comando) ed un modo <gapType>:
   0 = Estende i segmenti alle relative intersezioni proiettate
   1 = Raccorda i segmenti attraverso un arco di raccordo di raggio <offset>
   2 = Cima i segmenti di linea in corrispondenza delle intersezioni proiettate.
       La distanza perpendicolare da ciascuna cima al rispettivo vertice
       sull'oggetto originale é uguale alla distanza <offset>.
   
   Se 
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una linea che sostituisce <line1>, se = None <line1> va rimossa
   un arco, se = None non c'é arco di raccordo tra le due linee
   una linea che sostituisce <line2>, se = None <line2> va rimossa
   """
   # cerco il punto di intersezione tra le due linee
   ptInt = QadIntersections.twoInfinityLines(line1, line2)
   if ptInt is None: # linee parallele
      return None
   distBetweenLine1Pt1AndPtInt = qad_utils.getDistance(line1.getStartPt(), ptInt)
   distBetweenLine1Pt2AndPtInt = qad_utils.getDistance(line1.getEndPt(), ptInt)
   distBetweenLine2Pt1AndPtInt = qad_utils.getDistance(line2.getStartPt(), ptInt)
   distBetweenLine2Pt2AndPtInt = qad_utils.getDistance(line2.getEndPt(), ptInt)
   
   if gapType == 0: # Estende i segmenti     
      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # secondo punto di line1 più vicino al punto di intersezione
         newLine1 = QadLine().set(line1.getStartPt(), ptInt)
      else:
         # primo punto di line1 più vicino al punto di intersezione
         newLine1 = QadLine().set(ptInt, line1.getEndPt())
         
      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # secondo punto di line2 più vicino al punto di intersezione
         newLine2 = QadLine().set(line2.getStartPt(), ptInt)
      else:
         # primo punto di line2 più vicino al punto di intersezione
         newLine2 = QadLine().set(ptInt, line2.getEndPt())
      
      return [newLine1, None, newLine2]
   elif gapType == 1: # Raccorda i segmenti
      pt1Distant = line1.getStartPt() if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt else line1.getEndPt()
      angleLine1 = qad_utils.getAngleBy2Pts(ptInt, pt1Distant)
         
      pt2Distant = line2.getStartPt() if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt else line2.getEndPt()
      angleLine2 = qad_utils.getAngleBy2Pts(ptInt, pt2Distant)

      bisectorInfinityLinePts = qad_utils.getBisectorInfinityLine(pt1Distant, ptInt, pt2Distant, True)
      bisectorLine = QadLine().set(bisectorInfinityLinePts[0], bisectorInfinityLinePts[1])
      
      # cerco il punto di intersezione tra la bisettrice e 
      # la retta che congiunge i punti più distanti delle due linee
      pt = QadIntersections.twoInfinityLines(bisectorLine, \
                                             QadLine().set(pt1Distant, pt2Distant))
      angleBisectorLine = qad_utils.getAngleBy2Pts(ptInt, pt)

      # calcolo l'angolo (valore assoluto) tra un lato e la bisettrice            
      alfa = angleLine1 - angleBisectorLine
      if alfa < 0:
         alfa = angleBisectorLine - angleLine1      
      if alfa > math.pi:
         alfa = (2 * math.pi) - alfa 

      # calcolo l'angolo del triangolo rettangolo sapendo che la somma degli angoli interni = 180
      # - alfa - 90 gradi (angolo retto)
      distFromPtInt = math.tan(math.pi - alfa - (math.pi / 2)) * offset
      pt1Proj = qad_utils.getPolarPointByPtAngle(ptInt, angleLine1, distFromPtInt)
      pt2Proj = qad_utils.getPolarPointByPtAngle(ptInt, angleLine2, distFromPtInt)
      # Pitagora
      distFromPtInt = math.sqrt((distFromPtInt * distFromPtInt) + (offset * offset))      
      secondPt = qad_utils.getPolarPointByPtAngle(ptInt, angleBisectorLine, distFromPtInt - offset)
      arc = QadArc()
      arc.fromStartSecondEndPts(pt1Proj, secondPt, pt2Proj)
      
      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # secondo punto di line1 più vicino al punto di intersezione
         newLine1 = QadLine().set(pt1Distant, pt1Proj)
      else:
         # primo punto di line1 più vicino al punto di intersezione
         newLine1 = QadLine().set(pt1Proj, pt1Distant)

      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # secondo punto di line2 più vicino al punto di intersezione
         newLine2 = QadLine().set(pt2Distant, pt2Proj)
      else:
         # primo punto di line2 più vicino al punto di intersezione
         newLine2 = QadLine().set(pt2Proj, pt2Distant)
      
      # se i punti sono così vicini da essere considerati uguali
      if qad_utils.ptNear(newLine1.getEndPt(), arc.getStartPt()) == False:
         arc.reverse()
      return [newLine1, arc, newLine2]
   elif gapType == 2: # Cima i segmenti
      bisectorInfinityLinePts = qad_utils.getBisectorInfinityLine(line1.getEndPt(), ptInt, line2.getEndPt(), True)
      bisectorLine = QadLine().set(bisectorInfinityLinePts[0], bisectorInfinityLinePts[1])
      
      angleBisectorLine = qad_utils.getAngleBy2Pts(bisectorLine[0], bisectorLine[1])
      ptProj = qad_utils.getPolarPointByPtAngle(ptInt, angleBisectorLine, offset)

      pt1Proj = QadPerpendicularity.fromPointToInfinityLine(ptProj, line1)
      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # secondo punto di line1 più vicino al punto di intersezione
         newLine1 = QadLine().set(line1.getStartPt(), pt1Proj)
      else:
         # primo punto di line1 più vicino al punto di intersezione
         newLine1 = QadLine().set(pt1Proj, line1.getEndPt())

      pt2Proj = QadPerpendicularity.fromPointToInfinityLine(ptProj, line2)
      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # secondo punto di line2 più vicino al punto di intersezione
         newLine2 = QadLine().set(line2.getStartPt(), pt2Proj)
      else:
         # primo punto di line2 più vicino al punto di intersezione
         newLine2 = QadLine().set(pt2Proj, line2.getEndPt())

      return [newLine1, QadLine().set(pt1Proj, pt2Proj), newLine2]

   return None


# ===============================================================================
# fillet2PartsOffset
# ===============================================================================
def fillet2PartsOffset(part, nextPart, offsetSide, offsetDist):
   """
   la funzione raccorda 2 parti nei seguenti casi:   
   1) segmento-arco (PFIP-FIP, nessuna intersezione)
   2) arco-segmento (FIP-NFIP, nessuna intersezione)
   3) arco-arco (nessuna intersezione)
   """
   gType = part.whatIs()
   # se la prima parte é un segmento
   if gType == "LINE":
      newNextPart = part.copy()
      newNextPart.reverse() # rovescio la direzione
      newPart = nextPart.copy()
      newPart.reverse() # rovescio la direzione
      newOffSetSide = "left" if offsetSide == "right" else "right"
      result = fillet2PartsOffset(newPart, newNextPart, newOffSetSide, offsetDist)
      if result is not None:
         result.reverse() # rovescio la direzione
      return result
   
   elif gType == "ARC": # se la prima parte é un arco
      AngleProjected = qad_utils.getAngleBy2Pts(part.center, part.getEndPt())
      if part.reversed == False: # l'arco gira verso sin
         if offsetSide == "right": # l'offset era verso l'esterno
            # calcolo il punto proiettato per ri-ottenere quello originale 
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius - offsetDist)
         else: # l'offset era verso l'interno
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius + offsetDist)
      else: # l'arco gira verso destra
         if offsetSide == "right": # l'offset era verso l'interno
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius + offsetDist)
         else: # l'offset era verso l'esterno
            center = qad_utils.getPolarPointByPtAngle(part.center, AngleProjected, part.radius - offsetDist)
      
      newArc = QadArc()
      # se il centro dell'arco di raccordo é interno all'arco di offset
      if qad_utils.getDistance(part.center, center) < part.radius:                           
         if part.reversed == False:
            if newArc.fromStartCenterEndPts(part.getEndPt(), center, nextPart.getStartPt()) == False:
               return None
            newArc.reversed = False
         else:
            if newArc.fromStartCenterEndPts(nextPart.getStartPt(), center, part.getEndPt()) == False:
               return None
            newArc.reversed = True
      else: # se il centro dell'arco di raccordo é esterno all'arco di offset
         if part.reversed == False:
            if newArc.fromStartCenterEndPts(nextPart.getStartPt(), center, part.getEndPt()) == False:
               return None
            newArc.reversed = True
         else:
            if newArc.fromStartCenterEndPts(part.getEndPt(), center, nextPart.getStartPt()) == False:
               return None
            newArc.reversed = False
                                                               
      return newArc


# ===============================================================================
# getOffsetDistancesFromCenterOnOffsetedArc
# ===============================================================================
def getOffsetDistancesFromCenterOnOffsetedArc(arc, offsetDist, offsetSide):
   """
   la funzione restituisce la distanza minima e massima dal centro dell'arco su cui è già stato fatto un offset.
   Queste distanze generano un'area di offset intorno all'arco originale.
   <arc> arco a cui è già stato fatto un offset
   <offsetDist> distanza di offset
   <offsetSide> parte in cui si vuole l'offset "right" o "left"
   """               
   if arc.reversed: # l'arco gira verso destra
      if offsetSide == "right": # offset sulla parte interna dell'arco
         minDist = arc.radius                     
         maxDist = arc.radius + 2 * offsetDist               
      else: # offset sulla parte esterna dell'arco
         maxDist = arc.radius                     
         minDist = arc.radius - 2 * offsetDist
   else: # l'arco gira verso sin
      if offsetSide == "right": # offset sulla parte esterna dell'arco
         maxDist = arc.radius                     
         minDist = arc.radius - 2 * offsetDist
      else: # offset sulla parte interna dell'arco
         minDist = arc.radius                     
         maxDist = arc.radius + 2 * offsetDist
                                    
   if minDist < 0: minDist = 0                                       

   return minDist, maxDist


# ===============================================================================
# virtualPartClipping
# ===============================================================================
def virtualPartClipping(untrimmedOffsetPolyline, virtualPartPositionList):
   """
   la funzione restituisce una lista di parti in cui vengono tagliate le isole generate
   da parti virtuali (che invertono il senso della linea).
   Per ogni parte virtuale, si verifica se le parti che precedono e che seguono formano un'isola.
   In caso affermativo, se possibile (vedi casi specifici), l'sola viene rimossa.
   <untrimmedOffsetPolyline> lista delle parti
   <virtualPartPositionList> lista delle posizioni delle parti virtuali (viene modificata)
   """
   result = untrimmedOffsetPolyline.copy()
   
   # per prima cosa elimino tutte le isole con parti virtuali che hanno le parti 
   # direttamente adiacenti intersecanti
   i = len(virtualPartPositionList) - 1
   while i >= 0:
      virtualPartPosition = virtualPartPositionList[i]
      # parte successiva a quella virtuale
      nextPos = result.getNextPos(virtualPartPosition)
      # parte precedente
      prevPos = result.getPrevPos(virtualPartPosition)
      
      if (prevPos is not None) and (nextPos is not None):
         nextPart = result.getLinearObjectAt(nextPos)
         prevPart = result.getLinearObjectAt(prevPos)
         # verifico se hanno un solo punto di intersezione
         ptIntList = QadIntersections.twoBasicGeomObjects(prevPart, nextPart)
         if len(ptIntList) == 1:
            nextPart.setStartPt(ptIntList[0]) # modifico l'inizio
            prevPart.setEndPt(ptIntList[0]) # modifico la fine
            result.remove(virtualPartPosition)
            del virtualPartPositionList[i]
            for j in range(i, len(virtualPartPositionList)):
               virtualPartPositionList[j] = virtualPartPositionList[j] - 1 # scalo tutto di uno 
      i = i - 1
          
   # elimino tutte le isole con parti virtuali che hanno le parti adiacenti intersecanti
   # ma che non formino con il resto della linea altre isole.
   # quando considero un lato adiacente alla parte virtuale da un lato devo considerare le intersezioni 
   # partendo dal lato successivo quello adicente nella parte opposta di quello virtuale 
   for i in range(len(virtualPartPositionList) - 1, -1, -1):      
      virtualPartPosition = virtualPartPositionList[i]
      # finché non trovo l'intersezione
      nPrevPartsToRemove = -1
      prevPos = virtualPartPosition
      ptIntList = []      
      while len(ptIntList) == 0:
         virtualPart = result.getLinearObjectAt(virtualPartPosition)
         # parte successiva a quella virtuale
         nextPos = result.getNextPos(virtualPartPosition)
         nNextPartsToRemove = 0
         # parte precedente
         prevPos = result.getPrevPos(prevPos)
         # se trovo una parte virtuale mi fermo
         if virtualPartPositionList.count(prevPos) > 0:
            break 
          
         # l'ultima condizione é nel caso la polilinea sia chiusa
         if (prevPos is None) or (nextPos is None) or prevPos == nextPos:
            break

         nPrevPartsToRemove = nPrevPartsToRemove + 1
         prevPart = result.getLinearObjectAt(prevPos)
 
         # ciclo finche non ci sono più parti successive
         while (nextPos is not None) and (prevPos != nextPos):
            # se trovo una parte virtuale mi fermo
            if virtualPartPositionList.count(nextPos) > 0:
               break 
            nextPart = result.getLinearObjectAt(nextPos)
            ptIntList = QadIntersections.twoBasicGeomObjects(prevPart, nextPart)
            if len(ptIntList) > 0:
               break
            nextPos = result.getNextPos(nextPos) # parte successiva
            nNextPartsToRemove = nNextPartsToRemove + 1
    
      if len(ptIntList) == 1 and \
         not qad_utils.ptNear(ptIntList[0], virtualPart.getStartPt()) and \
         not qad_utils.ptNear(ptIntList[0], virtualPart.getEndPt()):
         prevPart_1 = prevPart.copy()
         # se il punto iniziale della parte non coincide con quella del punto di intersezione
         if not qad_utils.ptNear(ptIntList[0], prevPart.getStartPt()):
            prevPart_1.setEndPt(ptIntList[0]) # modifico la fine 
            prevPart_2 = prevPart.copy()
            prevPart_2.setStartPt(ptIntList[0]) # modifico l'inizio 
         else:
            prevPart_2 = None
            
         nextPart_1 = nextPart.copy()
         # se il punto finale della parte non coincide con quella del punto di intersezione
         if not qad_utils.ptNear(ptIntList[0], nextPart.getEndPt()):
            nextPart_1.setEndPt(ptIntList[0]) # modifico la fine 
            nextPart_2 = nextPart.copy()            
            nextPart_2.setStartPt(ptIntList[0]) # modifico l'inizio 
         else:
            nextPart_2 = None
         
         ########################################################
         # Creo una lista di parti che definisce l'isola - inizio
         islandPolyline = QadPolyline()
         
         if prevPart_2 is None:
            islandPolyline.append(prevPart_1)
         else:
            islandPolyline.append(prevPart_2)
         
         pos = virtualPartPosition        
         for j in range(nPrevPartsToRemove, 0, - 1):
            pos = result.getPrevPos(pos) # parte precedente        
            islandPolyline.append(result.getLinearObjectAt(pos))

         islandPolyline.append(virtualPart)

         pos = virtualPartPosition        
         for j in range(1, nNextPartsToRemove + 1, 1):
            pos = result.getNextPos(pos) # parte successiva        
            islandPolyline.append(result.getLinearObjectAt(pos))

         islandPolyline.append(nextPart_1)
            
         # Creo una lista di parti che definisce l'isola - fine
         ########################################################

         # verifico se le parti seguenti formano con islandPolyline delle aree (più di 2 intersezioni)         
         if nextPart_2 is not None:
            nIntersections = 1
         else:
            nIntersections = 0

         for j in range(nextPos + 1, result.qty(), 1):
            dummy = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(islandPolyline, result.getLinearObjectAt(j))
            intPtList = dummy[0]                               
            nIntersections = nIntersections + len(intPtList)

         # se é positivo e minore o uguale a 2 verifico anche dall'altra parte
         if nIntersections > 0 and nIntersections <= 2:
            # verifico se le parti precedenti formano con islandPolyline delle aree (almeno 2 intersezioni)
            if prevPart_2 is not None:
               nIntersections = 1
            else:
               nIntersections = 0

            for j in range(prevPos - 1, -1, -1):            
               dummy = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(islandPolyline, result.getLinearObjectAt(j))
               intPtList = dummy[0]                    
               nIntersections = nIntersections + len(intPtList)

            # se é positivo e minore o uguale a 2 verifico anche dall'altra parte
            if nIntersections > 0 and nIntersections <= 2:
               # rimuovo island da result
               if nextPart_2 is not None:
                  nextPart.setStartPt(nextPart_2.getStartPt()) # modifico l'inizio
               else:
                  result.remove(nextPos)

               # cancello le parti inutili
               for j in range(0, nNextPartsToRemove, 1):
                  result.remove(virtualPartPosition + 1)
                   
               # cancello la parte virtuale
               result.remove(virtualPartPosition)
       
               # cancello le parti inutili
               for j in range(0, nPrevPartsToRemove, 1):
                  result.remove(virtualPartPosition - nPrevPartsToRemove)

               if prevPart_2 is not None:
                  prevPart.setEndPt(nextPart_2.getStartPt()) # modifico la fine 
               else:
                  result.remove(prevPos)

               del virtualPartPositionList[i]

   return result


# ===============================================================================
# getIntPtListBetweenPartAndPartListOffset
# ===============================================================================
def getIntPtListBetweenPartAndPartListOffset(part, polyline):
   """
   la funzione restituisce due liste:
   la prima é una lista di punti di intersezione tra la parte <part>
   e la polilinea <polyline> ordinata per distanza dal punto iniziale
   di part (scarta i doppioni e i punti iniziale-finale di part)
   la seconda é una lista che  contiene, rispettivamente per ogni punto di intersezione,
   il numero della parte (0-based) di <polyline> in cui si trova quel punto.
   <part>: un segmento o arco 
   <polyline>: lista delle parti di una polilinea 
   """
   startPtOfPart = part.getStartPt()
   endPtOfPart = part.getEndPt()
   intPtSortedList = [] # lista di ((punto, distanza dall'inizio della parte) ...)
   partNumber = -1
   # per ogni parte di polyline
   for part2 in polyline.defList:
      partNumber = partNumber + 1
      partialIntPtList = QadIntersections.twoBasicGeomObjects(part, part2)
      for partialIntPt in partialIntPtList:
         # escludo i punti che sono all'inizio-fine di part
         
         # se i punti sono così vicini da essere considerati uguali         
         if qad_utils.ptNear(startPtOfPart, partialIntPt) == False and \
            qad_utils.ptNear(endPtOfPart, partialIntPt) == False:
            # escludo i punti che sono già in intPtSortedList
            found = False
            for intPt in intPtSortedList:
               if qad_utils.ptNear(intPt[0], partialIntPt):
                  found = True
                  break
               
            if found == False:
               # inserisco il punto ordinato per distanza dal inizio di part
               distFromStart = part.getDistanceFromStart(partialIntPt)
               insertAt = 0
               for intPt in intPtSortedList:
                  if intPt[1] < distFromStart:
                     insertAt = insertAt + 1
                  else:
                     break                     
               intPtSortedList.insert(insertAt, [partialIntPt, distFromStart, partNumber])
   resultIntPt = []
   resultPartNumber = []
   for intPt in intPtSortedList:
      resultIntPt.append(intPt[0])
      resultPartNumber.append(intPt[2])

   return resultIntPt, resultPartNumber


# ============================================================================
# getPartsExternalToCircle
# ============================================================================
def getPartsExternalToCircle(linearObj, circle):
   """
   la funzione usa un cerchio per dividere l'oggetto lineare.
   Le parti esterne al cerchio vengono restituite
   nell'ordine dal punto iniziale a quello finale dell'oggetto lineare.
   """
   result = QadPolyline()

   startPt = linearObj.getStartPt()
   endPt = linearObj.getEndPt()
   intPtList = QadIntersections.twoBasicGeomObjects(circle, linearObj)
   
   intPtSortedList = []
   for pt in intPtList:
      # inserisco il punto ordinato per distanza dall'inizio di part
      distFromStart = linearObj.getDistanceFromStart(pt)
      insertAt = 0
      for intPt in intPtSortedList:
         if intPt[1] < distFromStart:
            insertAt = insertAt + 1
         else:
            break                     
      intPtSortedList.insert(insertAt, [pt, distFromStart])

   del intPtList[:] # svuoto la lista
   for intPt in intPtSortedList:
      intPtList.append(intPt[0])

   startPtFromCenter = qad_utils.getDistance(circle.center, startPt) 
   endPtFromCenter = qad_utils.getDistance(circle.center, endPt)
   intPtListLen = len(intPtList)
   if intPtListLen == 0: # se non ci sono punti di intersezione
      # se entrambi i punti terminali della parte sono esterni al cerchio
      if startPtFromCenter >= circle.radius and endPtFromCenter >= circle.radius:
         result.append(linearObj)
   elif intPtListLen == 1: # se c'é un solo punto di intersezione
      # se entrambi i punti terminali della parte sono esterni al cerchio
      if startPtFromCenter >= circle.radius and endPtFromCenter >= circle.radius:
         result.append(linearObj)
      # se il primo punto della parte é interno e il secondo esterno al cerchio
      elif startPtFromCenter < circle.radius and endPtFromCenter > circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setStartPt(intPtList[0]) 
         result.append(newLinearobj)      
      # se il primo punto della parte é esterno e il secondo interno al cerchio
      elif startPtFromCenter > circle.radius and endPtFromCenter < circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setEndPt(intPtList[0]) 
         result.append(newLinearobj)      
   else : # se ci sono due punti di intersezione
      # se il primo punto della parte é esterno al cerchio
      if startPtFromCenter > circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setEndPt(intPtList[0]) 
         result.append(newLinearobj)      
      # se il secondo punto della parte é esterno al cerchio
      if endPtFromCenter > circle.radius:
         newLinearobj = linearObj.copy()
         newLinearobj.setStartPt(intPtList[1]) 
         result.append(newLinearobj)      

   return result
