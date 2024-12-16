# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 funzioni per fillet
 
                              -------------------
        begin                : 2019-08-20
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

import math

from .qad_arc import QadArc
from .qad_multi_geom import *
from .qad_geom_relations import *
from .qad_entity import *
from .qad_offset_fun import offsetBridgeTheGapBetweenLines


# ============================================================================
# isStartedPtChanged
# ============================================================================
def isStartedPtChanged(oldQadGeom, newQadGeom, filletQadGeom, nearNewQadGeom):
   """
   Funzione di ausilio alle funzioni filletQadGeometry e fillet2QadGeometries.
   
   Data una geometria qad e le nuove geometrie ricavate dall'operazione di raccordo, 
   la funzione ritorna True se è stato variato il punto iniziale della geoemtria qad e False 
   se ne è stato variato il punto di finale.
   """
   # se la nuova geometria rispetto a oldQadGeom non è cambiata
   if qad_utils.ptNear(oldQadGeom.getStartPt(), newQadGeom.getStartPt()) and \
      qad_utils.ptNear(oldQadGeom.getEndPt(), newQadGeom.getEndPt()):
      if filletQadGeom is not None: # se esiste un elemento di raccordo
         # verifico se il punto iniziale di oldQadGeom è collegato con questo elemento di raccordo
         if qad_utils.ptNear(oldQadGeom.getStartPt(), filletQadGeom.getStartPt()) or \
            qad_utils.ptNear(oldQadGeom.getStartPt(), filletQadGeom.getEndPt()):
            changedStartPt = True
         else:
            changedStartPt = False
      else: # se non esiste un elemento di raccordo
         # verifico se il punto iniziale di oldQadGeom è collegato alla nuova geometria vicina nearNewQadGeom
         if qad_utils.ptNear(oldQadGeom.getStartPt(), nearNewQadGeom.getStartPt()) or \
            qad_utils.ptNear(oldQadGeom.getStartPt(), nearNewQadGeom.getEndPt()):
            changedStartPt = True
         else:
            changedStartPt = False
   else: # se la nuova geometria è cambiata verifico in quale punto
      if qad_utils.ptNear(oldQadGeom.getStartPt(), newQadGeom.getStartPt()) == False:
         changedStartPt = True
      else:
         changedStartPt = False

   return changedStartPt


# ============================================================================
# filletQadGeometry
# ============================================================================
def filletQadPolyline(qadPolyline, partAt1, pointAt1, partAt2, pointAt2, \
                      filletMode, radius):
   """
   Date una geometria qad, 2 parti e due 2 punti in cui bisogna fare il raccordo tra le due
   parti, la funzione ritorna una polilinea risultato del raccordo.
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   <radius> raggio di raccordo
   """
   if partAt1 == partAt2: return None
   
   basicQadGeom1 = qadPolyline.getLinearObjectAt(partAt1)      
   basicQadGeom2 = qadPolyline.getLinearObjectAt(partAt2)

   res = filletBridgeTheGapBetween2BasicQadGeometries(basicQadGeom1, pointAt1, basicQadGeom2, pointAt2, filletMode, radius)   
   
   if res is None: # raccordo non possibile
      return None

   filletPolyline = qadPolyline.copy()
        
   if res[0] is not None:
      filletPolyline.remove(partAt1)
      filletPolyline.insert(partAt1, res[0])
      
      # se è stato variato il punto iniziale di basicQadGeom1
      if isStartedPtChanged(basicQadGeom1, res[0], res[1], res[2]):
         # può essere variato solo il punto finale di partAt1 (se è minore di partAt2)
         if partAt1 < partAt2: return None
      else: # se è stato variato il punto finale di basicQadGeom1
         # può essere variato solo il punto iniziale di partAt1 (se è maggiore di partAt2)
         if partAt1 > partAt2: return None
      
   if res[2] is not None:
      filletPolyline.remove(partAt2)
      filletPolyline.insert(partAt2, res[2])
      
      # se è stato variato il punto iniziale di basicQadGeom2
      if isStartedPtChanged(basicQadGeom2, res[2], res[1], res[0]):
         # può essere variato solo il punto finale di partAt2 (se è minore di partAt1)
         if partAt2 < partAt1: return None
      else: # se è stato variato il punto finale di basicQadGeom1
         # può essere variato solo il punto iniziale di partAt2 (se è maggiore di partAt1)
         if partAt2 > partAt1: return None

   # rimuovo tutte le parti che sono fra partAt1 e partAt2
   if partAt1 < partAt2:
      for i in range(partAt1 + 1, partAt2):
         filletPolyline.remove(i)
      if res[1] is not None: # inserisco arco di raccordo
         filletPolyline.insert(partAt1 + 1, res[1])
   else:
      for i in range(partAt2 + 1, partAt1):
         filletPolyline.remove(i)
      if res[1] is not None: # inserisco arco di raccordo
         filletPolyline.insert(partAt2 + 1, res[1])

   # verifico e correggo i versi delle parti della polilinea 
   filletPolyline.reverseCorrection()

   return filletPolyline


# ============================================================================
# fillet2QadGeometries
# ============================================================================
def fillet2QadGeometries(qadGeom1, atGeom1, atSubGeom1, partAt1, pointAt1, \
                         qadGeom2, atGeom2, atSubGeom2, partAt2, pointAt2, \
                         filletMode, radius):
   """
   Date due geometrie qad, la parte e il punto in cui bisogna fare il raccordo tra le due
   polilinee, la funzione ritorna una polilinea risultato del raccordo e due flag che
   danno indicazioni su ciò che deve essere fatto alle polilinee originali:
   (0=niente, 1=modificare, 2=cancellare)
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   <radius> raggio di raccordo
   """
   gType1 = qadGeom1.whatIs()
   gType2 = qadGeom2.whatIs()
   
   if gType1 == "POLYLINE" or gType1 == "MULTI_LINEAR_OBJ" or gType1 == "POLYGON" or gType1 == "MULTI_POLYGON":
      subQadGeom1 = getQadGeomAt(qadGeom1, atGeom1, atSubGeom1)
      if subQadGeom1.whatIs() == "POLYLINE":
         basicQadGeom1 = subQadGeom1.getLinearObjectAt(partAt1)
      else:
         basicQadGeom1 = subQadGeom1         
      
   else:
      subQadGeom1 = basicQadGeom1 = qadGeom1
   subQadGeomType1 = subQadGeom1.whatIs()
      
   if gType2 == "POLYLINE" or gType2 == "MULTI_LINEAR_OBJ" or gType2 == "POLYGON" or gType2 == "MULTI_POLYGON":
      subQadGeom2 = getQadGeomAt(qadGeom2, atGeom2, atSubGeom2)
      if subQadGeom2.whatIs() == "POLYLINE":
         basicQadGeom2 = subQadGeom2.getLinearObjectAt(partAt2)
      else:
         basicQadGeom2 = subQadGeom2         
   else:
      subQadGeom2 = basicQadGeom2 = qadGeom2
   subQadGeomType2 = subQadGeom2.whatIs()

   res = filletBridgeTheGapBetween2BasicQadGeometries(basicQadGeom1, pointAt1, basicQadGeom2, pointAt2, filletMode, radius)   
   
   if res is None: # raccordo non possibile
      return None

   filletPolyline = QadPolyline()
   
   if res[0] is None or \
      subQadGeomType1 == "CIRCLE" or subQadGeomType1 == "ELLIPSE" or subQadGeomType1 == "POLYGON":
      whatToDoGeom1 = 0 # 0=niente
   else:
      whatToDoGeom1 = 1 # 0=niente, 1=modificare, 2=cancellare
      if subQadGeomType1 == "POLYLINE":
         # se è stato variato il punto iniziale di basicQadGeom1
         if isStartedPtChanged(basicQadGeom1, res[0], res[1], res[2]):
            # prendo tutte le parti successive a partAt1
            for i in range(subQadGeom1.qty() - 1, partAt1, -1):
               filletPolyline.append(subQadGeom1.getLinearObjectAt(i))
         else:
            # prendo tutte le parti precedenti a partAt1
            for i in range(0, partAt1):
               filletPolyline.append(subQadGeom1.getLinearObjectAt(i))
      filletPolyline.append(res[0])      
      
   if res[1] is not None: # arco di raccordo
      filletPolyline.append(res[1])

   if res[2] is None or \
      subQadGeomType2 == "CIRCLE" or subQadGeomType2 == "ELLIPSE" or subQadGeomType2 == "POLYGON":
      whatToDoGeom2 = 0 # 0=niente
   elif res[2] is not None:
      # 0=niente, 1=modificare, 2=cancellare
      if whatToDoGeom1 == 1: # se la geometria1 è stata modificata
         whatToDoGeom2 = 2 # la geometria2 si unisce alla 1 e va cancellata
      else:
         whatToDoGeom2 = 1
                  
      filletPolyline.append(res[2])
      if subQadGeomType2 == "POLYLINE":
         # se è stato variato il punto iniziale di basicQadGeom2
         if isStartedPtChanged(basicQadGeom2, res[2], res[1], res[0]):
            # prendo tutte le parti successive a partAt2
            for i in range(partAt2 + 1, subQadGeom2.qty()):
               filletPolyline.append(subQadGeom2.getLinearObjectAt(i))
         else:
            # prendo tutte le parti precedenti a partAt2
            for i in range(partAt2 - 1, -1, -1):
               filletPolyline.append(subQadGeom2.getLinearObjectAt(i))
      
   # verifico e correggo i versi delle parti della polilinea 
   filletPolyline.reverseCorrection()

   # 1=modificare
   if whatToDoGeom1 == 1 and (gType1 == "MULTI_LINEAR_OBJ" or gType1 == "POLYGON" or gType1 == "MULTI_POLYGON"):
      updGeom = setQadGeomAt(qadGeom1, filletPolyline, atGeom1, atSubGeom1)
      return updGeom, whatToDoGeom1, whatToDoGeom2
   elif whatToDoGeom2 == 1 and (gType2 == "MULTI_LINEAR_OBJ" or gType2 == "POLYGON" or gType2 == "MULTI_POLYGON"):
      updGeom = setQadGeomAt(qadGeom2, filletPolyline, atGeom2, atSubGeom2)
      return updGeom, whatToDoGeom1, whatToDoGeom2
   else:
      return filletPolyline, whatToDoGeom1, whatToDoGeom2


# ============================================================================
# filletBridgeTheGapBetween2BasicQadGeometries
# ============================================================================
def filletBridgeTheGapBetween2BasicQadGeometries(qadGeom1, pointAt1, qadGeom2, pointAt2, filletMode, radius):
   """
   Date due geometrie di base di qad, la parte e il punto in cui bisogna fare il raccordo tra le due
   polilinee, la funzione ritorna una polilinea risultato del raccordo e due flag che
   danno indicazioni su ciò che deve essere fatto alle polilinee originali:
   (0=niente, 1=modificare, 2=cancellare)
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   <radius> raggio di raccordo
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una geometria 1 che sostituisce <qadGeom1>, se = None <qadGeom1> va rimossa
   un arco, se = None non c'é arco di raccordo tra le due linee
   una geometria 2 che sostituisce <qadGeom2>, se = None <qadGeom2> va rimossa
   
   """
   gType1 = qadGeom1.whatIs()
   gType2 = qadGeom2.whatIs()

   if gType1 == "CIRCLE":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircles(qadGeom1, pointAt1, qadGeom2, pointAt2, radius)
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenCircleEllipse(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcCircle(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenCircleEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenCircleLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
         
   elif gType1 == "ELLIPSE":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircleEllipse(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenEllipses(qadGeom1, pointAt1, qadGeom2, pointAt2, radius)
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcEllipse(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenEllipseEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenEllipseLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)

   elif gType1 == "ARC":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenArcCircle(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenArcEllipse(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcs(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenArcEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenArcLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)

   elif gType1 == "ELLIPSE_ARC":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircleEllipsearc(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenEllipseEllipsearc(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenEllipsearcs(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         res = filletBridgeTheGapBetweenLineEllipsearc(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
         
   elif gType1 == "LINE":
      if gType2 == "CIRCLE":
         res = filletBridgeTheGapBetweenCircleLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE":
         res = filletBridgeTheGapBetweenEllipseLine(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ARC":
         res = filletBridgeTheGapBetweenArcLine(qadGeom2, pointAt2, qadGeom1, pointAt1, radius, filletMode)
         if res is not None:
            dummy = res[0] # inverto il primo e il terzo elemento
            res[0] = res[2]
            res[2] = dummy
      elif gType2 == "ELLIPSE_ARC":
         res = filletBridgeTheGapBetweenLineEllipsearc(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, filletMode)
      elif gType2 == "LINE":
         if radius == 0:         
            res = filletBridgeTheGapBetweenLines(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, 0)
         else:
            res = filletBridgeTheGapBetweenLines(qadGeom1, pointAt1, qadGeom2, pointAt2, radius, 1)

   return res


# ===============================================================================
# INIZIO - 2 CERCHI
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircles
# ===============================================================================
def filletBridgeTheGapBetweenCircles(circle1, ptOnCircle1, circle2, ptOnCircle2, radius):
   """
   la funzione raccorda due cerchi attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sui cerchi.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # ricavo i possibili archi di raccordo
   filletArcs = getFilletArcsBetweenCircles(circle1, circle2, radius)
   
   # cerco l'arco valido più vicino a ptOnCircle1 e ptOnCircle2
   AvgList = []
   Avg = sys.float_info.max   

   resFilletArc = QadArc()
   for filletArc in filletArcs:
      if circle1.isPtOnCircle(filletArc.getStartPt()):
         distFromPtOnCircle1 = circle1.lengthBetween2Points(filletArc.getStartPt(), \
                                                            ptOnCircle1, \
                                                            filletArc.getTanDirectionOnStartPt() + math.pi)
         distFromPtOnCircle2 = circle2.lengthBetween2Points(filletArc.getEndPt(), \
                                                            ptOnCircle2, \
                                                            filletArc.getTanDirectionOnEndPt())
      else:
         distFromPtOnCircle1 = circle1.lengthBetween2Points(filletArc.getEndPt(), \
                                                            ptOnCircle1, \
                                                            filletArc.getTanDirectionOnEndPt())
         distFromPtOnCircle2 = circle2.lengthBetween2Points(filletArc.getStartPt(), \
                                                            ptOnCircle2, \
                                                            filletArc.getTanDirectionOnStartPt()+ math.pi)

      del AvgList[:]              
      AvgList.append(distFromPtOnCircle1)
      AvgList.append(distFromPtOnCircle2)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         resFilletArc.set(filletArc)
      
   if Avg == sys.float_info.max:
      return None   

   return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenCircles
# ===============================================================================
def getFilletArcsBetweenCircles(circle1, circle2, radius):
   """
   la funzione raccorda due cerchi attraverso un arco di raccordo di raggio <radius>.
   
   Ritorna una lista dei possibili archi
   """
   res = []
        
   # caso 1: raccordo tra <circle1> e <circle2> formando un flesso con ciascuno dei cerchi
   # creo un nuovo cerchio concentrico a circle1 con raggio aumentato di <radius>
   newCircle1 = QadCircle(circle1)
   newCircle1.radius = newCircle1.radius + radius
   # creo un nuovo cerchio concentrico a circle2 con raggio aumentato di <radius>
   newCircle2 = QadCircle(circle2)
   newCircle2.radius = newCircle2.radius + radius
  
   res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))
   
   # caso 2: raccordo tra <circle1> e <circle2> senza formare un flesso con ciascuno dei cerchi      
   if radius - circle1.radius > 0 and radius - circle2.radius > 0: 
      # creo un nuovo cerchio concentrico a circle1 con raggio = <radius> - raggio di circle1
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = radius - newCircle1.radius
      # creo un nuovo cerchio concentrico a circle2 con raggio = <radius> - raggio di circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = radius - newCircle2.radius
       
      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # caso 3: raccordo tra <circle1> e <circle2> formando un flesso solo con circle1
   if radius - circle2.radius > 0: 
      # creo un nuovo cerchio concentrico a circle1 con raggio aumentato di <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius + radius
      # creo un nuovo cerchio concentrico a circle2 con raggio = <radius> - raggio di circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = radius - newCircle2.radius
 
      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))
                  
   # caso 4: raccordo tra <circle1> e <circle2> formando un flesso solo con circle2
   if radius - circle1.radius > 0: 
      # creo un nuovo cerchio concentrico a circle1 con raggio aumentato di <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = radius - newCircle1.radius
      # creo un nuovo cerchio concentrico a circle2 con raggio = <radius> - raggio di circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = newCircle2.radius + radius
 
      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))
                  
   # caso 5: raccordo tra <circle1> e <circle2> interno a <circle1> formando un flesso solo con circle2
   if qad_utils.getDistance(circle1.center, circle2.center) + circle2.radius <= circle1.radius and \
      circle1.radius - radius > 0: 
      # creo un nuovo cerchio concentrico a circle1 con raggio diminuito di <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius - radius
      # creo un nuovo cerchio concentrico a circle2 con raggio aumentato di <radius>
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = newCircle2.radius + radius
 
      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))
                  
   # caso 6: raccordo tra <circle1> interno a <circle2> e <circle2> formando un flesso solo con circle1
   if qad_utils.getDistance(circle1.center, circle2.center) + circle1.radius <= circle2.radius and \
      circle2.radius - radius > 0: 
      # creo un nuovo cerchio concentrico a circle1 con raggio aumentato di <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius + radius
      # creo un nuovo cerchio concentrico a circle2 con raggio diminuito di <radius>
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = newCircle2.radius - radius
 
      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   # caso 7: raccordo tra <circle1> e <circle2> interno a <circle1> senza formare alcun flesso
   if qad_utils.getDistance(circle1.center, circle2.center) + circle2.radius <= circle1.radius and \
      circle1.radius - radius > 0 and radius - circle2.radius: 
      # creo un nuovo cerchio concentrico a circle1 con raggio diminuito di <radius>
      newCircle1 = QadCircle(circle1)
      newCircle1.radius = newCircle1.radius - radius
      # creo un nuovo cerchio concentrico a circle2 con raggio = <radius> - raggio di circle2
      newCircle2 = QadCircle(circle2)
      newCircle2.radius = radius - newCircle2.radius
 
      res.extend(auxFilletArcsBetweenCircles(newCircle1, newCircle2, radius))

   return res


# ===============================================================================
# auxFilletArcsBetweenCircles
# ===============================================================================
def auxFilletArcsBetweenCircles(circle1, circle2, radius, both = True):
   """
   la funzione di ausilio a getFilletArcsBetweenCircles   
   Ritorna una lista dei possibili archi di raccordo tra i cerchi <circle1> e <circle2>
   """
   res = []
   # calcolo le intersezioni tra le due circonferenze 
   # che daranno origine ai centri degli archi di raccordo
   intPts = QadIntersections.twoCircles(circle1, circle2)

   if len(intPts) > 0:
      # un punto di tangenza é dato dal punto a distanza radius dal centro dell'arco di raccordo
      # in direzione centro dell'arco <circle1>
      angle = qad_utils.getAngleBy2Pts(intPts[0], circle1.center)
      tanC1Pt = qad_utils.getPolarPointByPtAngle(intPts[0], angle, radius)
      # un punto di tangenza é dato dal punto a distanza radius dal centro dell'arco di raccordo
      # in direzione centro dell'arco <circle2>
      angle = qad_utils.getAngleBy2Pts(intPts[0], circle2.center)
      tanC2Pt = qad_utils.getPolarPointByPtAngle(intPts[0], angle, radius)
      filletArc = QadArc()
      if filletArc.fromStartCenterEndPts(tanC1Pt, intPts[0], tanC2Pt) == True:
         res.append(filletArc)
      if both:
         # inverto angolo iniziale-finale
         filletArc = QadArc(filletArc)
         filletArc.inverseAngles()
         res.append(filletArc)

      if len(intPts) > 1:
         # un punto di tangenza é dato dal punto a distanza radius dal centro dell'arco di raccordo
         # in direzione centro dell'arco <circle1>
         angle = qad_utils.getAngleBy2Pts(intPts[1], circle1.center)
         tanC1Pt = qad_utils.getPolarPointByPtAngle(intPts[1], angle, radius)
         # un punto di tangenza é dato dal punto a distanza radius dal centro dell'arco di raccordo
         # in direzione centro dell'arco <circle2>
         angle = qad_utils.getAngleBy2Pts(intPts[1], circle2.center)
         tanC2Pt = qad_utils.getPolarPointByPtAngle(intPts[1], angle, radius)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(tanC1Pt, intPts[1], tanC2Pt) == True:
            res.append(filletArc)
         if both:
            # inverto angolo iniziale-finale
            filletArc = QadArc(filletArc)
            filletArc.inverseAngles()
            res.append(filletArc)
            
   return res


# ===============================================================================
# FINE - 2 CERCHI
# INIZIO - CERCHIO ED ELLISSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircleEllipse
# ===============================================================================
def filletBridgeTheGapBetweenCircleEllipse(circle, ptOnCircle, ellipse, ptOnEllipse, radius):
   """
   la funzione raccorda un cerchio con una ellisse attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle due geometrie.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - CERCHIO ED ELLISSE
# INIZIO - 2 LINEE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenLines
# ===============================================================================
def filletBridgeTheGapBetweenLines(line1, ptOnLine1, line2, ptOnLine2, radius, filletMode):
   """   
   la funzione raccorda 2 segmenti retti (QadLine) attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sul segmento 1 <ptOnLine1> e sul segmento 2 <ptOnLine2>.
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una linea che sostituisce <line1>, se = None <line1> va rimossa
   un arco, se = None non c'é arco di raccordo tra le due linee
   una linea che sostituisce <line2>, se = None <line2> va rimossa
   """   
   if radius == 0: # Estende i segmenti     
      # cerco il punto di intersezione tra le due linee
      ptInt = QadIntersections.twoInfinityLines(line1, line2)
      if ptInt is None: # linee parallele
         return None
      
      distBetweenLine1Pt1AndPtInt = qad_utils.getDistance(line1.getStartPt(), ptInt)
      distBetweenLine1Pt2AndPtInt = qad_utils.getDistance(line1.getEndPt(), ptInt)
      distBetweenLine2Pt1AndPtInt = qad_utils.getDistance(line2.getStartPt(), ptInt)
      distBetweenLine2Pt2AndPtInt = qad_utils.getDistance(line2.getEndPt(), ptInt)
      
      if distBetweenLine1Pt1AndPtInt > distBetweenLine1Pt2AndPtInt:
         # secondo punto di line1 più vicino al punto di intersezione
         resLine1 = QadLine().set(line1.getStartPt(), ptInt)
      else:
         # primo punto di line1 più vicino al punto di intersezione
         resLine1 = QadLine().set(ptInt, line1.getEndPt())
         
      if distBetweenLine2Pt1AndPtInt > distBetweenLine2Pt2AndPtInt:
         # secondo punto di line2 più vicino al punto di intersezione
         resLine2 = QadLine().set(line2.getStartPt(), ptInt)
      else:
         # primo punto di line2 più vicino al punto di intersezione
         resLine2 = QadLine().set(ptInt, line2.getEndPt())
      
      return [resLine1, None, resLine2]
   else: # Raccorda i segmenti
      filletArcs = getFilletArcsBetweenLines(line1, line2, radius)

      # cerco l'arco valido più vicino a ptOnLine1 e ptOnLine2
      AvgList = []
      Avg = sys.float_info.max   
   
      resLine1 = QadLine()
      resFilletArc = QadArc()
      resLine2 = QadLine()
      for filletArc in filletArcs:
         # ricavo il nuovo segmento in modo che sia tangente con l'arco di raccordo       
         newLine1, distFromPtOnLine1 = getNewLineAccordingFilletArc(line1, filletArc, ptOnLine1)
         if newLine1 is None:
            continue           
         # ricavo il nuovo segmento in modo che sia tangente con l'arco di raccordo       
         newLine2, distFromPtOnLine2 = getNewLineAccordingFilletArc(line2, filletArc, ptOnLine2)
         if newLine2 is None:
            continue           
   
         del AvgList[:]              
         AvgList.append(distFromPtOnLine1)
         AvgList.append(distFromPtOnLine2)
   
         currAvg = qad_utils.numericListAvg(AvgList)
         if currAvg < Avg: # mediamente più vicino
            Avg = currAvg
            resLine1.set(newLine1)
            resFilletArc.set(filletArc)
            resLine2.set(newLine2)
         
      if Avg == sys.float_info.max:
         return None   
   
      if filletMode == 1: # 1=Taglia-estendi
         return [resLine1, resFilletArc, resLine2]
      else:
         return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenLines
# ===============================================================================
def getFilletArcsBetweenLines(line1, line2, radius):
   """
   la funzione raccorda due linee rette (QadLine) attraverso 
   un arco di raccordo di raggio <radius>.
   
   Ritorna una lista dei possibili archi
   """
   res = []
   
   # cerco il punto di intersezione tra le due linee
   intPt = QadIntersections.twoInfinityLines(line1, line2)
   if intPt is None: # linee parallele
      # calcolo la proiezione perpendicolare del punto iniziale di <line1> su <line2> 
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(line1.getStartPt(), line2)
      d = qad_utils.getDistance(line1.getStartPt(), ptPerp)
      # d deve essere 2 volte <radius>
      if qad_utils.doubleNear(radius * 2, d):
         angle = qad_utils.getAngleBy2Pts(line1.getStartPt(), ptPerp)
         ptCenter = gad_utils.getPolarPointByPtAngle(line1.getStartPt(), angle, radius)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(line1.getStartPt(), ptCenter, ptPerp) == True:
            res.append(filletArc)
         # stesso arco con il punto iniziale e finale invertiti
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(ptPerp, ptCenter, line1.getStartPt()) == True:
            res.append(filletArc)
      
         ptPerp = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, d)
         ptCenter = qad_utils.getPolarPointByPtAngle(line1.getEndPt(), angle, radius)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(line1.getEndPt(), ptCenter, ptPerp) == True:
            res.append(filletArc)
         # stesso arco con il punto iniziale e finale invertiti
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(ptPerp, ptCenter, line1.getEndPt()) == True:
            res.append(filletArc)      
   else: # linee non parallele
      angleLine1 = line1.getTanDirectionOnPt()
      angleLine2 = line2.getTanDirectionOnPt()

      ptLine1 = qad_utils.getPolarPointByPtAngle(intPt, angleLine1, 1)
      ptLine2 = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, 1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))

      ptLine2 = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, -1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))
      
      ptLine1 = qad_utils.getPolarPointByPtAngle(intPt, angleLine1, -1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))

      ptLine2 = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, 1)
      res.extend(auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius))

   return res


# ===============================================================================
# getNewLineAccordingFilletArc
# ===============================================================================
def getNewLineAccordingFilletArc(line, filletArc, ptOnLine):
   """
   dato un segmento retto (<line>) e un arco che si 
   raccorda ad esso (<filleArc>), la funzione restituisce un nuovo segmento retto
   modificando <line> in modo che sia tangente all'arco di raccordo. 
   Inoltre, usando un punto indicato sul segmento <ptOnLine> restituisce 
   la distanza di quel punto dal punto di tangenza con l'arco di raccordo.
   """
   newLine = QadLine()

   # determino quale punto (iniziale o finale) dell'arco di raccordo 
   # si interseca sul prolugamento del segmento retto
   if line.isPtOnInfinityLine(filletArc.getStartPt()):
      filletPtOnLine = filletArc.getStartPt()
      isStartFilletPtOnLine = True
   else:
      filletPtOnLine = filletArc.getEndPt()
      isStartFilletPtOnLine = False

   if line.containsPt(filletPtOnLine) == True: # se il punto é all'interno del segmento  
      newLine.set(filletPtOnLine, line.getEndPt())
      
      if isStartFilletPtOnLine: # se il punto iniziale dell'arco di raccordo é sulla linea
         # se il nuovo segmento non é un segmento valido
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()):          
            # se l'arco di raccordo é tangente sul punto finale del nuovo segmento
            if qad_utils.TanDirectionNear(line.getTanDirectionOnEndPt(), \
                                          qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt())) == True:
               newLine.set(line) # ripristino il segmento originale
         else:
            # se l'arco di raccordo non é tangente sul punto iniziale del nuovo segmento            
            if qad_utils.TanDirectionNear(newLine.getTanDirectionOnStartPt(), \
                                          qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt() + math.pi)) == False:
               newLine.set(line.getStartPt(), filletPtOnLine)
            
         # se il nuovo segmento non é un segmento valido
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()) or \
            newLine.containsPt(ptOnLine) == False:
            return None, None          
         
         # calcolo la distanza dal punto ptOnLine
         distFromPtOnLine = qad_utils.getDistance(ptOnLine, filletPtOnLine)
      else: # se il punto finale dell'arco di raccordo é sulla linea
         # se il nuovo segmento non é un segmento valido
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()):          
            # se l'arco di raccordo é tangente sul punto finale del nuovo segmento
            if qad_utils.TanDirectionNear(line.getTanDirectionOnEndPt(), \
                                          qad_utils.normalizeAngle(filletArc.getTanDirectionOnEndPt() + math.pi)) == True:
               newLine.set(line) # ripristino il segmento originale
         else:
            # se l'arco di raccordo non é tangente sul punto iniziale del nuovo segmento            
            if qad_utils.TanDirectionNear(newLine.getTanDirectionOnStartPt(), \
                                          filletArc.getTanDirectionOnEndPt()) == False:
               newLine.set(line.getStartPt(), filletPtOnLine)
            
         # se il nuovo segmento non é un segmento valido
         if qad_utils.ptNear(newLine.getStartPt(), newLine.getEndPt()) or \
            newLine.containsPt(ptOnLine) == False:
            return None, None          
         
         # calcolo la distanza dal punto ptOnLine
         distFromPtOnLine = qad_utils.getDistance(ptOnLine, filletPtOnLine)
         
      return newLine, distFromPtOnLine
   else: # se il punto é all'esterno del segmento 
      if qad_utils.getDistance(line.getStartPt(), filletPtOnLine) < qad_utils.getDistance(line.getEndPt(), filletPtOnLine):
         newLine.set(filletPtOnLine, line.getEndPt())
      else:
         newLine.set(line.getStartPt(), filletPtOnLine)

      return getNewLineAccordingFilletArc(newLine, filletArc, ptOnLine)


# ===============================================================================
# auxFilletArcsBetweenLines
# ===============================================================================
def auxFilletArcsBetweenLines(ptLine1, ptLine2, intPt, radius, both = True):
   """
   la funzione di ausilio a getFilletArcsBetweenLines
   Ritorna una lista dei possibili archi di raccordo tra la 
   linea 1 che va da <ptLine1> fino al punto di intersezione con la linea 2 <intPt>
   e 
   linea2 che va da <ptLine2> fino al punto di intersezione con la linea 1 <intPt>
   """
   res = []

   angleLine1 = qad_utils.getAngleBy2Pts(intPt, ptLine1)
   angleLine2 = qad_utils.getAngleBy2Pts(intPt, ptLine2)

   line = QadLine().set(ptLine1, ptLine2)
   bisectorInfinityLinePts = qad_utils.getBisectorInfinityLine(ptLine1, intPt, ptLine2, True)
   bisectorLine = QadLine().set(bisectorInfinityLinePts[0], bisectorInfinityLinePts[1])
   # cerco il punto di intersezione tra la bisettrice e 
   # la retta che congiunge i punti più distanti delle due linee
   pt = QadIntersections.twoInfinityLines(bisectorLine, line)
   angleBisectorLine = qad_utils.getAngleBy2Pts(intPt, pt)

   # calcolo l'angolo (valore assoluto) tra un lato e la bisettrice            
   alfa = angleLine1 - angleBisectorLine
   if alfa < 0:
      alfa = angleBisectorLine - angleLine1      
   if alfa > math.pi:
      alfa = (2 * math.pi) - alfa 

   # calcolo l'angolo del triangolo rettangolo sapendo che la somma degli angoli interni = 180
   # - alfa - 90 gradi (angolo retto)
   distFromIntPt = math.tan(math.pi - alfa - (math.pi / 2)) * radius
   pt1Proj = qad_utils.getPolarPointByPtAngle(intPt, angleLine1, distFromIntPt)
   pt2Proj = qad_utils.getPolarPointByPtAngle(intPt, angleLine2, distFromIntPt)
   # Pitagora
   distFromIntPt = math.sqrt((distFromIntPt * distFromIntPt) + (radius * radius))      
   secondPt = qad_utils.getPolarPointByPtAngle(intPt, angleBisectorLine, distFromIntPt - radius)
   filletArc = QadArc()
   if filletArc.fromStartSecondEndPts(pt1Proj, secondPt, pt2Proj) == True:
      res.append(filletArc)
   if both:
      # inverto angolo iniziale-finale
      filletArc = QadArc(filletArc)
      filletArc.inverseAngles()
      res.append(filletArc)

   return res


# ===============================================================================
# FINE - 2 LINEE
# INIZIO - ARCO E CERCHIO
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcCircle
# ===============================================================================
def filletBridgeTheGapBetweenArcCircle(arc, ptOnArc, circle, ptOnCircle, radius, filletMode):
   """
   la funzione raccorda un arco e un cerchio attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sull'arco <ptOnArc> e sul cerchio <ptCircle>.
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una arco che sostituisce <arc>
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # ricavo i possibili archi di raccordo
   filletArcs = getFilletArcsBetweenArcCircle(arc, circle, radius)
   
   # cerco l'arco valido più vicino a ptOnArc e ptOnCircle
   AvgList = []
   Avg = sys.float_info.max   

   resFilletArc = QadArc()
   resArc = QadArc()
   for filletArc in filletArcs:
      # ricavo il nuovo arco in modo che sia tangente con l'arco di raccordo       
      newArc, distFromPtOnArc = getNewArcAccordingFilletArc(arc, filletArc, ptOnArc)
      if newArc is None:
         continue
         
      # calcolo la distanza dal punto ptOnCircle
      if circle.isPtOnCircle(filletArc.getStartPt()): # se il punto iniziale dell'arco di raccordo é sul cerchio
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getStartPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnStartPt() + math.pi)
      else: # se il punto finale dell'arco di raccordo é sul cerchio
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getEndPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnEndPt())

      del AvgList[:]              
      AvgList.append(distFromPtOnArc)
      AvgList.append(distFromPtOnCircle)

      currAvg = qad_utils.qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         resArc.set(newArc) 
         resFilletArc.set(filletArc)
      
   if Avg == sys.float_info.max:
      return None   

   if filletMode == 1: # 1=Taglia-estendi
      return [resArc, resFilletArc, None]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenArcCircle
# ===============================================================================
def getFilletArcsBetweenArcCircle(arc, circle, radius):
   """
   la funzione raccorda un arco e un cerchio attraverso 
   un arco di raccordo di raggio <radius>.
   
   Ritorna una lista dei possibili archi
   """  
   circle1 = QadCircle()
   circle1.set(arc.center, arc.radius)

   return getFilletArcsBetweenCircles(circle1, circle, radius)


# ===============================================================================
# getNewArcAccordingFilletArc
# ===============================================================================
def getNewArcAccordingFilletArc(arc, filletArc, ptOnArc):
   """
   dato un arco (<arc>) e un altro arco che si raccorda ad esso (<filleArc>),
   la funzione restituisce un nuovo arco modificando <arc> in modo che sia 
   tangente all'arco di raccordo. Inoltre, usando un punto indicato sull'arco
   <ptOnArc> restituisce la distanza di quel punto dal punto di tangenza con l'arco
   di raccordo usando la direzione della tangente dell'arco di raccordo.
   """
   circle = QadCircle()    
   circle.set(arc.center, arc.radius)  

   newArc = QadArc(arc)

   # determino quale punto (iniziale o finale) dell'arco di raccordo 
   # si interseca sul prolugamento dell'arco 
   if circle.isPtOnCircle(filletArc.getStartPt()):
      filletPtOnArc = filletArc.getStartPt()
      isStartFilletPtOnArc = True
   else:
      filletPtOnArc = filletArc.getEndPt()
      isStartFilletPtOnArc = False

   # verifico che l'arco di raccordo sia tangente con l'arco
   newArc.setStartAngleByPt(filletPtOnArc)
      
   if isStartFilletPtOnArc: # se il punto iniziale dell'arco di raccordo é sull'arco
      # se il nuovo arco non é un arco valido
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         # se l'arco di raccordo é tangente sul punto finale dell'arco
         if qad_utils.TanDirectionNear(arc.getTanDirectionOnEndPt(), \
                                       qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt())) == True:
            newArc.startAngle = arc.startAngle # ripristino l'arco originale
      else:
         # se l'arco di raccordo non é tangente sul punto iniziale del nuovo arco            
         if qad_utils.TanDirectionNear(newArc.getTanDirectionOnStartPt(), \
                                       qad_utils.normalizeAngle(filletArc.getTanDirectionOnStartPt() + math.pi)) == False:
            newArc.startAngle = arc.startAngle # ripristino l'arco originale
            newArc.setEndAngleByPt(filletPtOnArc)
         
      # se il nuovo arco non é un arco valido
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         return None, None
                   
      # calcolo la distanza dal punto ptOnArc
      distFromPtOnArc = circle.lengthBetween2Points(filletArc.getStartPt(), \
                                                    ptOnArc, \
                                                    filletArc.getTanDirectionOnStartPt() + math.pi)
   else: # se il punto finale dell'arco di raccordo é sull'arco
      # se il nuovo arco non é un arco valido
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         # se l'arco di raccordo é tangente sul punto finale dell'arco
         if qad_utils.TanDirectionNear(arc.getTanDirectionOnEndPt(), \
                                       qad_utils.normalizeAngle(filletArc.getTanDirectionOnEndPt() + math.pi)) == True:
            newArc.startAngle = arc.startAngle # ripristino l'arco originale
      else:
         # se l'arco di raccordo non é tangente sul punto iniziale del nuovo arco            
         if qad_utils.TanDirectionNear(newArc.getTanDirectionOnStartPt(), \
                                       filletArc.getTanDirectionOnEndPt()) == False:
            newArc.startAngle = arc.startAngle # ripristino l'arco originale
            newArc.setEndAngleByPt(filletPtOnArc)

      # se il nuovo arco non é un arco valido
      if qad_utils.doubleNear(newArc.startAngle, newArc.endAngle):
         return None, None

      # calcolo la distanza dal punto ptOnArc
      distFromPtOnArc = circle.lengthBetween2Points(filletArc.getEndPt(), \
                                                    ptOnArc, \
                                                    filletArc.getTanDirectionOnEndPt())

   return newArc, distFromPtOnArc


# ===============================================================================
# FINE - ARCO E CERCHIO
# INIZIO - CERCHIO E ARCO DI ELLISSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircleEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenCircleEllipsearc(circle, ptOnCircle, ellipseArc, ptOnEllipseArc, radius):
   """
   la funzione raccorda un cerchio ed un arco ellisse attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle 2 geometrie.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - CERCHIO E ARCO DI ELLISSE
# INIZIO - CERCHIO E LINEA
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenCircleLine
# ===============================================================================
def filletBridgeTheGapBetweenCircleLine(circle, ptOnCircle, line, ptOnLine, radius, filletMode):
   """
   la funzione raccorda un cerchio e un segmento retto (QadLine) attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sul cerchio <ptOnCircle> e sul segmento retto <ptOnLine>.
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   una linea che sostituisce <line> se filleMode = 1 (Taglia-estendi) altrimenti None
   """
   # ricavo i possibili archi di raccordo
   filletArcs = getFilletArcsBetweenCircleLine(circle, line, radius)
   
   # cerco l'arco valido più vicino a ptOnArc e ptOnLine
   AvgList = []
   Avg = sys.float_info.max   

   resFilletArc = QadArc()
   resLine = QadLine()
   for filletArc in filletArcs:
      # ricavo il nuovo segmento in modo che sia tangente con l'arco di raccordo       
      newLine, distFromPtOnLine = getNewLineAccordingFilletArc(line, filletArc, ptOnLine)
      if newLine is None:
         continue           

      if circle.isPtOnCircle(filletArc.getStartPt()):
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getStartPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnStartPt() + math.pi)
      else:
         distFromPtOnCircle = circle.lengthBetween2Points(filletArc.getEndPt(), \
                                                          ptOnCircle, \
                                                          filletArc.getTanDirectionOnEndPt())

      del AvgList[:]              
      AvgList.append(distFromPtOnLine)
      AvgList.append(distFromPtOnCircle)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # mediamente piùvicino
         Avg = currAvg
         resLine.set(newLine)
         resFilletArc.set(filletArc)
      
   if Avg == sys.float_info.max:
      return None   

   if filletMode == 1: # 1=Taglia-estendi
      return [None, resFilletArc, resLine]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# auxFilletArcsBetweenCircleLine
# ===============================================================================
def auxFilletArcsBetweenCircleLine(circle, line, origCircle, origLine, both = True):
   """
   la funzione di ausilio a getFilletArcsBetweenArcLine
   Ritorna una lista dei possibili archi di raccordo tra <circle> e <line>
   """
   res = []
   # calcolo le intersezioni tra la circonferenza del cerchio e la retta parallela a <line> 
   # che daranno origine ai centri degli archi di raccordo
   intPts = QadIntersections.infinityLineWithCircle(line, circle)
   if len(intPts) > 0:
      # un punto di tangenza é dato dal punto a distanza radius dal centro di <origCircle> 
      # in direzione centro dell'arco di raccordo
      angle = qad_utils.getAngleBy2Pts(origCircle.center, intPts[0])
      tanCirclePt = qad_utils.getPolarPointByPtAngle(origCircle.center, angle, origCircle.radius)      
      # un punto di tangenza é la proiezione perpendicolare del centro dell'arco di raccordo
      # con <origLine>
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(intPts[0], origLine)
      filletArc = QadArc()
      if filletArc.fromStartCenterEndPts(tanCirclePt, \
                                         intPts[0], \
                                         ptPerp) == True:
         res.append(filletArc)
         if both:
            # inverto angolo iniziale-finale
            filletArc = QadArc(filletArc)
            filletArc.inverseAngles()
            res.append(filletArc)

      if len(intPts) > 1: # # due centri per i due archi di raccordo
         # un punto di tangenza é dato dal punto a distanza arc.radius dal centro di <arc> 
         # in direzione centro dell'arco di raccordo
         angle = qad_utils.getAngleBy2Pts(origCircle.center, intPts[1])
         tanCirclePt = qad_utils.getPolarPointByPtAngle(origCircle.center, angle, origCircle.radius)      
         # un punto di tangenza é la proiezione perpendicolare del centro dell'arco di raccordo
         # con <line> 
         ptPerp = QadPerpendicularity.fromPointToInfinityLine(intPts[1], origLine)
         filletArc = QadArc()
         if filletArc.fromStartCenterEndPts(tanCirclePt, \
                                            intPts[1], \
                                            ptPerp) == True:
            res.append(filletArc)
            if both:
               # inverto angolo iniziale-finale
               filletArc = QadArc(filletArc)
               filletArc.inverseAngles()
               res.append(filletArc)
               
   return res


# ===============================================================================
# getFilletArcsBetweenCircleLine
# ===============================================================================
def getFilletArcsBetweenCircleLine(circle, line, radius):
   """
   la funzione raccorda un cerchio e una linea retta (QadLine) attraverso 
   un arco di raccordo di raggio <radius>.
   
   Ritorna una lista dei possibili archi
   """
   res = []
   
   offsetCircle = circle.copy()

   intPts = QadIntersections.infinityLineWithCircle(line, circle)
   if len(intPts) == 0:
      # se il cerchio e la retta generata dall'estensione di line
      # non hanno punti in comune
      leftOfLine = line.leftOf(circle.center)
      # creo una retta parallela a <line> ad una distanza <radius> verso il centro di <circle>  
      linePar = QadLine()
      angle = line.getTanDirectionOnStartPt()
      if leftOfLine < 0: # a sinistra
         linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle + math.pi / 2, radius), \
                     qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle + math.pi / 2, radius))
      else :# a destra
         linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle - math.pi / 2, radius), \
                     qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle - math.pi / 2, radius))
         
      # Calcolo la distanza dal centro di <circle> a <line>
      ptPerp = QadPerpendicularity.fromPointToInfinityLine(circle.center, line)
      d = qad_utils.getDistance(circle.center, ptPerp)
      # <radius> deve essere >= (d - raggio cerchio) / 2
      if radius >= (d - circle.radius) / 2:
         
         # caso 1: raccordo tra <circle> e <line> formando un flesso con <circle>
         
         # creo un cerchio con raggio aumentato di <radius> 
         offsetCircle.radius = circle.radius + radius
         res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))
         
         # caso 2: raccordo tra <circle> e <line> senza formare un flesso con <circle>
         
         # <radius> deve essere > raggio cerchio
         if radius > circle.radius:         
            # creo un cerchio con raggio = <radius> - circle.radius
            offsetCircle.radius = radius - circle.radius
            res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))
   else:
      # se il cerchio e la retta generata dall'estensione di line
      # hanno punti in comune
      # creo una retta parallela a <line> ad una distanza <radius> verso sinistra  
      linePar = QadLine()
      angle = line.getTanDirectionOnStartPt()
      linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle + math.pi / 2, radius), \
                  qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle + math.pi / 2, radius))

      # creo un cerchio con raggio aumentato di <radius> 
      offsetCircle.radius = circle.radius + radius
      res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))
      
      if circle.radius > radius: 
         # creo un cerchio con raggio diminuito di <radius>
         offsetCircle.radius = circle.radius - radius
         res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))

      # creo una retta parallela a <line> ad una distanza <radius> verso destra
      linePar.set(qad_utils.getPolarPointByPtAngle(line.getStartPt(), angle - math.pi / 2, radius), \
                  qad_utils.getPolarPointByPtAngle(line.getEndPt(), angle - math.pi / 2, radius))

      # creo un cerchio con raggio aumentato di <radius> 
      offsetCircle.radius = circle.radius + radius
      res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))
      # calcolo le intersezioni tra la circonferenza del cerchio e la retta parallela a <line> 

      if circle.radius > radius: 
         # creo un cerchio con raggio diminuito di <radius>
         offsetCircle.radius = circle.radius - radius
         res.extend(auxFilletArcsBetweenCircleLine(offsetCircle, linePar, circle, line))

   return res


# ===============================================================================
# FINE - CERCHIO E LINEA
# INIZIO - 2 ELLISSI
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipses
# ===============================================================================
def filletBridgeTheGapBetweenEllipses(ellipse1, ptOnEllipse1, ellipse2, ptOnEllipse2, radius):
   """
   la funzione raccorda due ellissi attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle ellissi.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - 2 ELLISSI
# INIZIO - ARCO ED ELLISSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcEllipse
# ===============================================================================
def filletBridgeTheGapBetweenArcEllipse(arc, ptOnArc, ellipse, ptOnEllipse, radius):
   """
   la funzione raccorda un arco con una ellisse attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle geometrie.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - ARCO ED ELLISSE
# INIZIO - ELLISSE ED ARCO DI ELLISSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipseEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenEllipseEllipsearc(ellipse, ptOnEllipse, ellipseArc, ptOnEllipseArc, radius):
   """
   la funzione raccorda una ellisse con un arco di ellisse attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle geometrie.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - ELLISSE ED ARCO DI ELLISSE
# INIZIO - ELLISSE E LINEA
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipseLine
# ===============================================================================
def filletBridgeTheGapBetweenEllipseLine(ellipse, ptOnEllipse, line, ptOnLine, radius):
   """
   la funzione raccorda una ellisse con una linea attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle geometrie.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - ELLISSE E LINEA
# INIZIO - 2 ARCHI
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcs
# ===============================================================================
def filletBridgeTheGapBetweenArcs(arc1, ptOnArc1, arc2, ptOnArc2, radius, filletMode):
   """
   la funzione raccorda due archi attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sull'arco1 <ptOnArc1> e sull'arco2 <ptOnArc2>.
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una arco che sostituisce <arc1>
   un arco, se = None non c'é arco di raccordo tra le due linee
   una arco che sostituisce <arc2>
   """
   # ricavo i possibili archi di raccordo
   filletArcs = getFilletArcsBetweenArcs(arc1, arc2, radius)
   
   # cerco l'arco valido più vicino a ptOnArc1 e ptOnArc2
   AvgList = []
   Avg = sys.float_info.max   

   resFilletArc = QadArc()
   resArc1 = QadArc()
   resArc2 = QadArc()
   for filletArc in filletArcs:
      # ricavo il nuovo arco1 in modo che sia tangente con l'arco di raccordo       
      newArc1, distFromPtOnArc1 = getNewArcAccordingFilletArc(arc1.getArc(), filletArc, ptOnArc1)
      if newArc1 is None:
         continue
      # ricavo il nuovo arco in modo che sia tangente con l'arco di raccordo       
      newArc2, distFromPtOnArc2 = getNewArcAccordingFilletArc(arc2.getArc(), filletArc, ptOnArc2)
      if newArc2 is None:
         continue

      del AvgList[:]              
      AvgList.append(distFromPtOnArc1)
      AvgList.append(distFromPtOnArc2)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         resArc1.set(newArc1) 
         resFilletArc.set(filletArc)
         resArc2.set(newArc2) 
      
   if Avg == sys.float_info.max:
      return None   

   if filletMode == 1: # 1=Taglia-estendi
      return [resArc1, resFilletArc, resArc2]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenArcs
# ===============================================================================
def getFilletArcsBetweenArcs(arc1, arc2, radius):
   """
   la funzione raccorda due archi attraverso un arco di raccordo di raggio <radius>.
   
   Ritorna una lista dei possibili archi
   """  
   circle1 = QadCircle()
   circle1.set(arc1.center, arc1.radius)
   circle2 = QadCircle()
   circle2.set(arc2.center, arc2.radius)

   return getFilletArcsBetweenCircles(circle1, circle2, radius)


# ===============================================================================
# FINE - 2 ARCHI
# INIZIO - ARCO ED ARCO DI ELLISSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenArcEllipsearc(arc, ptOnArc, ellipseArc, ptOnEllipseArc, radius):
   """
   la funzione raccorda una acro con un rco di ellisse 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle geometrie.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   None
   un arco, se = None non c'é arco di raccordo tra le due linee
   None
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - ARCO ED ARCO DI ELLISSE
# INIZIO - ARCO E LINEA
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenArcLine
# ===============================================================================
def filletBridgeTheGapBetweenArcLine(arc, ptOnArc, line, ptOnLine, radius, filletMode):
   """
   la funzione raccorda un arco e un segmento retto attraverso 
   un arco di raccordo di raggio <radius> che piùsi avvicinza ai punti di selezione
   sull'arco <ptOnArc> e sul segmento retto <ptOnLine>.
   <filletMode> modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una arco che sostituisce <arc>
   un arco, se = None non c'é arco di raccordo tra le due linee
   una linea che sostituisce <line>
   """
   # ricavo i possibili archi di raccordo
   filletArcs = getFilletArcsBetweenArcLine(arc, line, radius)
   
   # cerco l'arco valido più vicino a ptOnArc e ptOnLine
   AvgList = []
   Avg = sys.float_info.max   

   resArc = QadArc()
   resFilletArc = QadArc()
   resLine = QadLine()
   for filletArc in filletArcs:
      # ricavo il nuovo segmento in modo che sia tangente con l'arco di raccordo       
      newLine, distFromPtOnLine = getNewLineAccordingFilletArc(line, filletArc, ptOnLine)
      if newLine is None:
         continue        
            
      # ricavo il nuovo arco in modo che sia tangente con l'arco di raccordo       
      newArc, distFromPtOnArc = getNewArcAccordingFilletArc(arc, filletArc, ptOnArc)
      if newArc is None:
         continue        

      del AvgList[:]              
      AvgList.append(distFromPtOnLine)
      AvgList.append(distFromPtOnArc)

      currAvg = qad_utils.numericListAvg(AvgList)
      if currAvg < Avg: # mediamente più vicino
         Avg = currAvg
         resLine.set(newLine)
         resFilletArc.set(filletArc)
         resArc.set(newArc) 
      
   if Avg == sys.float_info.max:
      return None   

   if filletMode == 1: # 1=Taglia-estendi
      return [resArc, resFilletArc, resLine]
   else:
      return [None, resFilletArc, None]


# ===============================================================================
# getFilletArcsBetweenArcLine
# ===============================================================================
def getFilletArcsBetweenArcLine(arc, line, radius):
   """
   la funzione raccorda un arco e una linea retta attraverso 
   un arco di raccordo di raggio <radius>.
   
   Ritorna una lista dei possibili archi
   """
   circle = QadCircle()
   circle.set(arc.center, arc.radius)
   
   return getFilletArcsBetweenCircleLine(circle, line, radius)


# ===============================================================================
# FINE - ARCO E LINEA
# INIZIO - 2 ARCHI DI ELLISSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenEllipsearcs
# ===============================================================================
def filletBridgeTheGapBetweenEllipsearcs(ellipseArc1, ptOnEllipseArc1, ellipseArc2, ptOnEllipseArc2, radius):
   """
   la funzione raccorda due archi di ellisse attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sugli archi di ellisse.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una arco di ellisse che sostituisce <ellipseArc1>
   un arco, se = None non c'é arco di raccordo tra le due linee
   una arco di ellisse che sostituisce <ellipseArc2>
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - 2 ARCHI DI ELLISSE
# INIZIO - LINEA E ARCO DI ELLISSE
# ===============================================================================


# ===============================================================================
# filletBridgeTheGapBetweenLineEllipsearc
# ===============================================================================
def filletBridgeTheGapBetweenLineEllipsearc(line, ptOnLine, ellipseArc, ptOnEllipseArc, radius):
   """
   la funzione raccorda una linea ed un arco di ellisse attraverso 
   un arco di raccordo di raggio <radius> che più si avvicinza ai punti di selezione
   sulle geometrie.
   
   Ritorna una lista di 3 elementi (None in caso di errore):   
   una linea che sostituisce <line>
   un arco, se = None non c'é arco di raccordo tra le due geometrie
   una arco di ellisse che sostituisce <ellipseArc>
   """
   # da fare
   return [None, None, None]


# ===============================================================================
# FINE - LINEA E ARCO DI ELLISSE
# INIZIO - POLILINEA
# ===============================================================================


# ============================================================================
# filletAllPartsQadPolyline
# ============================================================================
def filletAllPartsQadPolyline(polyline, radius):
   """
   la funzione raccorda ogni segmento al successivo con un raggio di curvatura noto,
   la nuova polilinea avrà i vertici cambiati.
   """
   if radius <= 0: return
   newPolyline = QadPolyline()

   part = polyline.getLinearObjectAt(0)
   i = 1
   tot = polyline.qty()
   while i <= tot - 1:
      nextPart = polyline.getLinearObjectAt(i)
      if part.whatIs() == "LINE" and nextPart.whatIs() == "LINE":
         # Ritorna una lista di 3 elementi (None in caso di errore):   
         # - una linea che sostituisce <part>, se = None <part> va rimossa
         # - un arco, se = None non c'é arco di raccordo tra le due linee
         # - una linea che sostituisce <nextPart>, se = None <nextPart> va rimossa
         res = offsetBridgeTheGapBetweenLines(part, nextPart, radius, 1)
         if res is None:
            return
         if res[0] is not None:
            part = res[0]
            newPolyline.append(part)
         if res[1] is not None:
            part = res[1]
            newPolyline.append(part)
         if res[2] is not None:
            part = res[2]
      i = i + 1

   if polyline.isClosed():
      nextPart = newPolyline.getLinearObjectAt(0)
      if part.whatIs() == "LINE" and nextPart.whatIs() == "LINE":
         
         # Ritorna una lista di 3 elementi (None in caso di errore):
         # - una linea che sostituisce <part>, se = None <part> va rimossa
         # - un arco, se = None non c'é arco di raccordo tra le due linee
         # - una linea che sostituisce <nextPart>, se = None <nextPart> va rimossa
         res = offsetBridgeTheGapBetweenLines(part, nextPart, radius, 1)
         if res is None:
            return
         if res[0] is not None:
            newPolyline.append(res[0])
         if res[1] is not None:
            newPolyline.append(res[1])
         if res[2] is not None:
            nextPart.set(res[2])
   else:
      newPolyline.append(part)
        
   polyline.set(newPolyline)
   
   return True
