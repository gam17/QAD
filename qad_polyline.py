# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione delle polilinee (lista di linee, archi, archi di ellisse) ok
 
                              -------------------
        begin                : 2019-02-26
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
import qgis.utils

import math


from . import qad_utils
from .qad_line import QadLine
from .qad_arc import QadArc
from .qad_ellipse_arc import QadEllipseArc
from .qad_layer import createMemoryLayer
from .qad_msg import QadMsg
from .qad_variables import QadVariables


# ===============================================================================
# QadPolyline class
# rappresenta una lista di oggetti lineari come: linee, archi, archi di ellisse
# ===============================================================================
class QadPolyline():
    
   def __init__(self, polyline=None):
      self.defList = []
      # deflist = (<linearObj1><linearObj2>...)
      if polyline is not None:
         self.set(polyline)


   # ============================================================================
   # whatIs
   # ============================================================================
   def whatIs(self):
      return "POLYLINE"
         

   # ============================================================================
   # set
   # ============================================================================
   def set(self, polyline):
      self.removeAll()
      if isinstance(polyline, QadPolyline) == True: # è una polilinea
         for linearObject in polyline.defList:
            self.append(linearObject)
      elif isinstance(polyline, list) == True: # è una lista di parti di polilinea
         for linearObject in polyline:         
            self.append(linearObject)
      return self


   def __eq__(self, polyline):
      # obbligatoria
      """self == other"""
      if polyline.whatIs() != "POLYLINE": return False
      if self.qty() != polyline.qty(): return False
      for i in range(0, self.qty()):
         if self.getLinearObjectAt(i) != polyline.getLinearObjectAt(i): return False
      return True
  
  
   def __ne__(self, polyline):
      """self != other"""
      return not self.__eq__(polyline)


   def equals(self, polyline):
      # uguali geometricamente (NON conta il verso)
      if polyline.whatIs() != "POLYLINE": return False
      if self.__eq__(polyline): return True
      dummy = polyline.copy()
      dummy.reverse()
      return self.__eq__(dummy)

   # ============================================================================
   # append
   # ============================================================================
   def append(self, linearObject):
      """
      la funzione aggiunge un oggetto lineare in fondo alla lista.
      Non viene fatto controllo di continuità geometrica.
      """
      if linearObject is None: return
      return self.defList.append(linearObject.copy())


   # ============================================================================
   # appendPolyline
   # ============================================================================
   def appendPolyline(self, polyline, start = None, qty = None):
      """
      la funzione aggiunge una polilinea in fondo alla lista.
      Se <start> diverso da None significa numero della parte di <polyline> da cui iniziare. 
      Se <qty> diverso da None significa numero delle parti di <polyline> da aggiungere, altrimenti significa fino alla fine di <polyline>.
      Non viene fatto controllo di continuità geometrica.
      """
      if start is None:
         for linearObject in polyline.defList:
            self.append(linearObject)
      else:
         i = start
         if qty is None:
            tot = polyline.qty()
         else:
            tot = polyline.qty() if qty > polyline.qty() else qty

         while i < tot:
            self.append(polyline.defList[i])
            i = i + 1

   
   # ============================================================================
   # insert
   # ============================================================================
   def insert(self, partAt, linearObject):
      """
      la funzione aggiunge un oggetto lineare nella posizione i-esima della lista degli oggetti lineari.
      Non viene fatto controllo di continuità geometrica.
      """
      if partAt >= self.qty():
         return self.append(linearObject)
      else:         
         return self.defList.insert(partAt, linearObject.copy())


   # ============================================================================
   # insertPolyline
   # ============================================================================
   def insertPolyline(self, i, polyline):
      """
      la funzione aggiunge una polilinea nella posizione i-esima della lista.
      """
      ndx = i 
      for linearObject in polyline.defList:
         self.insert(ndx, linearObject)
         ndx = ndx + 1


   # ============================================================================
   # insertPoint
   # ============================================================================
   def insertPoint(self, partAt, pt):
      """
      la funzione aggiunge un punto tra il punto iniziale e finale della parte i-esima della lista.
      se i < 0 aggiunge il punto all'inizio della polilinea
      se i >= qty() aggiunge il punto alla fine della polilinea
      """
      if partAt < 0: # inserisco una linea all'inizio
         line = QadLine()
         line.set(pt, self.getStartPt())
         self.insert(0, line)
      elif partAt >= self.qty(): # inserisco una linea in fondo
         line = QadLine()
         line.set(self.getEndPt(), pt)
         self.append(line)
      else:
         linearObject = self.getLinearObjectAt(partAt)

         if linearObject.whatIs() == "LINE":
            line = QadLine()
            line.set(linearObject.getStartPt(), pt)
            self.insert(partAt, line)           
            linearObject = self.getLinearObjectAt(partAt + 1)
            linearObject.set(pt, linearObject.getEndPt())
            
         elif linearObject.whatIs() == "ARC":
            arc1 = QadArc()
            arc2 = QadArc()
            totalAngle = linearObject.totalAngle()
            if linearObject.reversed:
               if arc1.fromStartEndPtsAngle(pt, linearObject.getStartPt(), totalAngle) == False:
                  return
               arc1.reversed = True
               if linearObject.fromStartEndPtsAngle(linearObject.getEndPt(), pt, totalAngle) == False:
                  return
               linearObject.reversed = True
            else:
               if arc1.fromStartEndPtsAngle(linearObject.getStartPt(), pt, totalAngle) == False:
                  return
               if linearObject.fromStartEndPtsAngle(pt, linearObject.getEndPt(), totalAngle) == False:
                  return
               
            self.insert(partAt, arc1)
            
         elif linearObject.whatIs() == "ELLIPSE_ARC":
            # da fare
            pass
         
         
   # ============================================================================
   # movePoint
   # ============================================================================
   def movePoint(self, vertexAt, pt):
      """
      la funzione sposta un punto tra il punto iniziale e finale della parte i-esima della lista.
      """
      prevLinearObject, nextLinearObject = self.getPrevNextLinearObjectsAtVertex(vertexAt)
      
      if prevLinearObject is not None:
         if prevLinearObject.whatIs() == "LINE":
            prevLinearObject.setEndPt(pt)
                        
         elif prevLinearObject.whatIs() == "ARC":
            if prevLinearObject.reversed:
               # sposto il punto iniziale dell'arco
               if prevLinearObject.fromStartEndPtsAngle(pt, \
                                                        prevLinearObject.getStartPt(), \
                                                        prevLinearObject.totalAngle()) == False:
                  return False
               prevLinearObject.reversed = True
            else:
               # sposto il punto finale dell'arco
               if prevLinearObject.fromStartEndPtsAngle(prevLinearObject.getStartPt(), \
                                                        pt, \
                                                        prevLinearObject.totalAngle()) == False:
                  return False
            
         elif prevLinearObject.whatIs() == "ELLIPSE_ARC":
            # da fare
            pass
            
      if nextLinearObject is not None:
         if nextLinearObject.whatIs() == "LINE":
            nextLinearObject.setStartPt(pt)
         
         elif nextLinearObject.whatIs() == "ARC":
            if nextLinearObject.reversed:
               # sposto il punto finale dell'arco
               if nextLinearObject.fromStartEndPtsAngle(nextLinearObject.getEndPt(), \
                                                        pt, \
                                                        nextLinearObject.totalAngle()) == False:
                  return False
               nextLinearObject.reversed = True
            else:
               # sposto il punto iniziale dell'arco
               if nextLinearObject.fromStartEndPtsAngle(pt, \
                                                        nextLinearObject.getEndPt(), \
                                                        nextLinearObject.totalAngle()) == False:
                  return False
               
         elif prevLinearObject.whatIs() == "ELLIPSE_ARC":
            # da fare
            pass
         
      return True


   # ============================================================================
   # remove
   # ============================================================================
   def remove(self, i):
      """
      la funzione cancella un oggetto lineare nella posizione i-esima della lista.
      """
      del self.defList[i]


   # ============================================================================
   # removeAll
   # ============================================================================
   def removeAll(self):
      """
      la funzione cancella gli oggetti lineari della lista.
      """
      del self.defList[:]
         

   # ============================================================================
   # getLinearObjectAt
   # ============================================================================
   def getLinearObjectAt(self, i):
      """
      la funzione restituisce l'oggetto lineare alla posizione i-esima 
      con numeri negativi parte dal fondo (es. -1 = ultima posizione)
      """
      if self.qty() == 0 or i > self.qty() - 1:
         return None
      return self.defList[i]


   # ============================================================================
   # getVertexPosAtPt
   # ============================================================================
   def getVertexPosAtPt(self, pt):
      """
      la funzione restituisce la posizione del vertice con coordinate <pt> (0-based),
      None se non trovato.
      """
      vertexAt = 0
      for linearObject in self.defList:
         if qad_utils.ptNear(linearObject.getStartPt(), pt):
            return vertexAt
         vertexAt = vertexAt + 1
      if self.isClosed() == False: # se non é chiusa verifico ultimo vertice dell'ultima parte
         if qad_utils.ptNear(self.defList[-1].getEndPt(), pt):
            return vertexAt
         
      return None


   # ============================================================================
   # getPrevNextLinearObjectsAtVertex
   # ============================================================================
   def getPrevNextLinearObjectsAtVertex(self, vertexAt):
      """
      la funzione restituisce l'oggetto lineare precedente e successivo al vertice vertexAt-esimo
      """
      prevLinearObject = None
      nextLinearObject = None
      
      if vertexAt == 0: # primo vertice
         nextLinearObject = self.getLinearObjectAt(0)
         if self.isClosed():
            prevLinearObject = self.getLinearObjectAt(-1)
      elif vertexAt == self.qty(): # ultimo vertice
         prevLinearObject = self.getLinearObjectAt(-1)          
         if self.isClosed():
            nextLinearObject = self.getLinearObjectAt(0)
      else:
         nextLinearObject = self.getLinearObjectAt(vertexAt)
         prevLinearObject = self.getLinearObjectAt(vertexAt - 1)

      return prevLinearObject, nextLinearObject


   # ============================================================================
   # getPointAtVertex
   # ============================================================================
   def getPointAtVertex(self, vertexAt):
      """
      la funzione restituisce il punto del vertice vertexAt-esimo che compone la polilinea (0-based).
      """
      if vertexAt == self.qty(): # ultimo vertice
         return self.getLinearObjectAt(-1).getEndPt()          
      else:
         return self.getLinearObjectAt(vertexAt).getStartPt()


   # ============================================================================
   # getNextPos
   # ============================================================================
   def getNextPos(self, i):
      """
      la funzione restituisce la posizione dell'oggetto lineare successiva all'i-esimo (0-based)
      tenendo conto che se la polilinea è chiusa dopo l'ultimo oggetto si torna all'inizio
      N.B: non sono sicuro che debba essere ciclico...
      """      
      if i == self.qty() - 1 or i == -1: # sono alla fine
         if self.isClosed(): # se é chiusa torno all'inizio
            return 0
         else:
            return None
      else:
         return i + 1


   # ============================================================================
   # getPrevPos
   # ============================================================================
   def getPrevPos(self, i):
      """
      la funzione restituisce la posizione della parte precedente all' i-esima (0-based) 
      tenendo conto che se la polilinea è chiusa prima del primo oggetto si va alla fine
      N.B: non sono sicuro che debba essere ciclico...
      """      
      if i == 0: # sono all'inizio
         if self.isClosed(): # se é chiusa torno alla fine
            return self.qty() - 1
         else:
            return None
      else:
         return i - 1


   # ============================================================================
   # fromPolyline
   # ============================================================================
   def fromPolyline(self, points):
      """
      la funzione inizializza una lista di linee, archi e archi di ellisse che compone la polilinea.
      Se un oggetto lineare ha punto iniziale e finale coincidenti (es. 2 vertici consecutivi 
      che si sovrappongono o arco con angolo totale = 0 oppure = 360)
      l'oggetto viene rimosso dalla lista.
      """
      pointsLen = len(points)
   
      self.removeAll()
      arc = QadArc()
      ellipseArc = QadEllipseArc()
      line = QadLine()
      
      i = 0
      while i < pointsLen - 1: # fino al penultimo punto
         # verifico se è un arco
         endVertex = arc.fromPolyline(points, i)
         if endVertex is not None and qad_utils.ptNear(arc.getStartPt(), points[i]) == True:
            self.append(arc)
            i = endVertex
         else:
            # verifico se è un arco di ellisse
            endVertex = ellipseArc.fromPolyline(points, i)
            if endVertex is not None and qad_utils.ptNear(ellipseArc.getStartPt(), points[i]) == True:
               self.append(ellipseArc)
               i = endVertex
            else: # allora è una linea
               line.set(points[i], points[i + 1])
               self.append(line)
               i = i + 1
   
      if self.qty() == 0: return False
   
      return True


   # ============================================================================
   # fromGeom
   # ============================================================================
   def fromGeom(self, geom):
      """
      la funzione inizializza la polilinea da un oggetto QgsGeometry.
      """
      return self.fromPolyline(geom.asPolyline())
   
   
   # ===============================================================================
   # asPolyline
   # ===============================================================================
   def asPolyline(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna una lista di punti che compone la polilinea formata da una lista di
      oggetti lineari consecutivi.
      """
      result = []
      firstPt = True
      for linearObject in self.defList:
         pts = linearObject.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
         ptsLen = len(pts)
         if firstPt:
            i = 0
            firstPt = False
         else:
             i = 1
         while i < ptsLen:
            result.append(pts[i])
            i = i + 1
                     
      return result

   
   # ===============================================================================
   # asLineString
   # ===============================================================================
   def asLineString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna la polilinea in forma di lineString.
      """
      pts = self.asPolyline(tolerance2ApproxCurve, atLeastNSegment)
      if pts is None or len(pts) == 0:
          return None
      return QgsLineString(pts)

   
   # ===============================================================================
   # asCompoundString
   # ===============================================================================
   def asCompoundString(self, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna la polilinea in forma di compoundString.
      """
      compoundCurve = QgsCompoundCurve()
      lastPt = None
      for linearObject in self.defList:
         if linearObject.whatIs() == "ARC":
            compoundCurve.addCurve(linearObject.asCircularString(lastPt))
         else:
            compoundCurve.addCurve(linearObject.asLineString(tolerance2ApproxCurve, atLeastNSegment, lastPt))
         lastPt = linearObject.getEndPt()
               
      return compoundCurve


   # ===============================================================================
   # asAbstractGeom
   # ===============================================================================
   def asAbstractGeom(self, wkbType = QgsWkbTypes.LineString, tolerance2ApproxCurve = None, atLeastNSegment = None):
      """
      la funzione ritorna la polilinea in forma di QgsAbstractGeometry.
      """
      flatType = QgsWkbTypes.flatType(wkbType)

      if flatType == QgsWkbTypes.CompoundCurve:
         compoundCurve = self.asCompoundString(tolerance2ApproxCurve, atLeastNSegment)
         return compoundCurve

      elif flatType == QgsWkbTypes.MultiCurve:
         compoundCurve = self.asCompoundString(tolerance2ApproxCurve, atLeastNSegment)
         multiCurve = QgsMultiCurve()
         multiCurve.addGeometry(compoundCurve)
         return multiCurve
         
      elif flatType == QgsWkbTypes.CurvePolygon:
         compoundCurve = self.asCompoundString(tolerance2ApproxCurve, atLeastNSegment)
         curvePolygon = QgsCurvePolygon()
         curvePolygon.setExteriorRing(compoundCurve)
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
      la funzione ritorna la polilinea in forma di QgsGeometry.
      """
      return QgsGeometry(self.asAbstractGeom(wkbType, tolerance2ApproxCurve, atLeastNSegment))


   # ===============================================================================
   # copy
   # ===============================================================================
   def copy(self):
      # obbligatoria
      return QadPolyline(self)


   # ===============================================================================
   # reverse
   # ===============================================================================
   def reverse(self):
      """
      la funzione rovescia il verso di una lista di oggetti lineari consecutivi.
      """
      self.defList.reverse()
      for linearObject in self.defList:
         linearObject.reverse()
      return self


   # ===============================================================================
   # reverseCorrection
   # ===============================================================================
   def reverseCorrection(self):
      """
      la funzione controlla e corregge i versi delle parti della polilinea.
      """
      totPart = self.qty()
      if totPart <= 1: return
      atPart = 0
      while atPart < totPart:
         linearObject = self.getLinearObjectAt(atPart)
         gType = linearObject.whatIs()
         if gType == "ARC" or gType == "ELLIPSE_ARC":
            startPt = linearObject.getStartPt(usingReversedFlag = False)
            if atPart == 0: # prima parte
               linearObject2 = self.getLinearObjectAt(atPart + 1) # parte successiva
               if qad_utils.ptNear(startPt, linearObject2.getStartPt()) or \
                  qad_utils.ptNear(startPt, linearObject2.getEndPt()):
                  linearObject.reversed = True
               else:
                  linearObject.reversed = False
            else: # parti successive alla prima
               linearObject2 = self.getLinearObjectAt(atPart - 1) # parte precedente
               if qad_utils.ptNear(startPt, linearObject2.getEndPt()):
                  linearObject.reversed = False
               else:
                  linearObject.reversed = True
         elif gType == "LINE":
            startPt = linearObject.getStartPt()
            if atPart == 0: # prima parte
               linearObject2 = self.getLinearObjectAt(atPart + 1) # parte successiva
               if qad_utils.ptNear(linearObject.getStartPt(), linearObject2.getStartPt()) or \
                  qad_utils.ptNear(startPt, linearObject2.getEndPt()):
                  linearObject.reverse()
            else:
               linearObject2 = self.getLinearObjectAt(atPart - 1) # parte precedente
               if qad_utils.ptNear(linearObject.getStartPt(), linearObject2.getEndPt()) == False:
                  linearObject.reverse()
         atPart = atPart + 1


   # ============================================================================
   # length
   # ============================================================================
   def length(self):
      """
      la funzione restituisce la somma delle lunghezze della parti.
      """
      tot = 0
      for linearObject in self.defList:
         tot = tot + linearObject.length()
      return tot


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      """
      la funzione sposta le parti secondo un offset X e uno Y
      """
      for linearObject in self.defList:
         linearObject.move(offsetX, offsetY)


   # ============================================================================
   # qty
   # ============================================================================
   def qty(self):
      """
      la funzione restituisce la quantità di oggetti lineari che compongono la polilinea.
      """
      return len(self.defList)
   

   # ============================================================================
   # getStartPt
   # ============================================================================
   def getStartPt(self):
      """
      la funzione restituisce il punto iniziale della polilinea.
      """
      linearObject = self.getLinearObjectAt(0) # primo oggetto lineare
      return None if linearObject is None else linearObject.getStartPt()


   # ============================================================================
   # setStartPt
   # ============================================================================
   def setStartPt(self, pt):
      """
      la funzione setta il punto iniziale della polilinea.
      """
      linearObject = self.getLinearObjectAt(0) # primo oggetto lineare
      return None if linearObject is None else linearObject.setStartPt(pt)


   # ============================================================================
   # getEndPt
   # ============================================================================
   def getEndPt(self):
      """
      la funzione restituisce il punto finale della polilinea.
      """
      linearObject = self.getLinearObjectAt(-1) # ultimo oggetto lineare
      return None if linearObject is None else linearObject.getEndPt()


   # ============================================================================
   # setEndPt
   # ============================================================================
   def setEndPt(self, pt):
      """
      la funzione setta il punto finale della polilinea.
      """
      linearObject = self.getLinearObjectAt(-1) # ultimo oggetto lineare
      return None if linearObject is None else linearObject.setEndPt(pt)


   # ============================================================================
   # getMiddlePt
   # ============================================================================
   def getMiddlePt(self):
      """
      la funzione restituisce il punto medio della polilinea.
      """
      return self.getPointFromStart(self.length() / 2)
   
   
   # ============================================================================
   # getCentroid
   # ============================================================================
   def getCentroid(self, tolerance2ApproxCurve = None):
      """
      la funzione restituisce il punto centroide di una polilinea chiusa.
      """
      if self.isClosed(): # verifico se polilinea chiusa
         ptList = self.asPolyline(tolerance2ApproxCurve)
         g =  QgsGeometry.fromPolygonXY([ptList])
         if g is not None:
            centroid = g.centroid()
            if centroid is not None:
               return g.centroid().asPoint()

      return None


   # ============================================================================
   # isClosed
   # ============================================================================
   def isClosed(self):
      """
      la funzione restituisce True se la polilinea (lista di parti segmenti-archi) é chiusa.
      """
      if len(self.defList) == 0:
         return False
      else:
         return True if qad_utils.ptNear(self.getStartPt(), self.getEndPt()) else False


   # ============================================================================
   # setClose
   # ============================================================================
   def setClose(self, toClose = True):
      """
      la funzione chiude o apre la polilinea.
      """      
      if toClose: # da chiudere
         if self.isClosed() == False:
            if self.qty() > 0:
               linearObject = self.getLinearObjectAt(-1)
               # verifico l'ultimo oggetto
               if linearObject.whatIs() == "LINE":
                  if self.qty() > 1:
                     self.append(QadLine().set(self.getEndPt(), self.getStartPt()))
               elif linearObject.whatIs() == "ARC":
                  arc = QadArc()
                  if arc.fromStartEndPtsTan(linearObject.getEndPt(), \
                                            self.getStartPt(), \
                                            linearObject.getTanDirectionOnEndPt()) == False:
                     return
                  self.append(arc)
               elif linearObject.whatIs() == "ELLIPSE_ARC":
                  # da fare
                  pass
                                 
      else: # da aprire
         if self.isClosed() == True:
            if self.qty() > 1:
               self.remove(-1)


   # ===============================================================================
   # getBoundingBox
   # ===============================================================================
   def getBoundingBox(self):
      """
      la funzione ritorna il rettangolo che racchiude la polilinea.
      """
      boundingBox = self.getLinearObjectAt(0).getBoundingBox()
      i = 1
      while i < self.qty():
         boundingBox.combineExtentWith(self.getLinearObjectAt(i).getBoundingBox())
         i = i + 1
         
      return boundingBox


   # ===============================================================================
   # isContainingEllipseArcs
   # ===============================================================================
   def segmentizeEllipseArcs(self, tolerance2ApproxCurve = None):
      """
      la funzione trasforma gli archi di ellisse in segmenti
      """
      if tolerance2ApproxCurve is None:
         tolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      else:
         tolerance = tolerance2ApproxCurve
               
      if self.isClosed() == True:
         prevPartEndPt = self.defList[-1].getEndPt()
      else:
         prevPartEndPt = None
         
      partAt = 0
      while partAt < len(self.defList):
         linearObject = self.defList[partAt]
         if linearObject.whatIs() == "ELLIPSE_ARC":
            points = linearObject.asPolyline(tolerance)
            if prevPartEndPt is not None:
               points[0] = prevPartEndPt
            prevPartEndPt = points[-1]
            
            self.remove(partAt)
            pointsLen = len(points)
            i = 0
            while i < pointsLen - 1: # fino al penultimo punto  
               line = QadLine()          
               line.set(points[i], points[i + 1])
               self.insert(partAt, line)
               partAt = partAt + 1
               i = i + 1
         else:
            prevPartEndPt = self.defList[partAt].getEndPt()
            partAt = partAt + 1
         
      return True


   # ============================================================================
   # getTanDirectionOnStartPt
   # ============================================================================
   def getTanDirectionOnStartPt(self):
      """
      la funzione ritorna la direzione della tangente al punto iniziale dell'oggetto.
      """
      linearObject = self.getLinearObjectAt(0) # primo oggetto lineare
      return None if linearObject is None else linearObject.getTanDirectionOnStartPt()


   # ============================================================================
   # getTanDirectionOnEndPt
   # ============================================================================
   def getTanDirectionOnEndPt(self):
      """
      la funzione ritorna la direzione della tangente al punto iniziale dell'oggetto.
      """
      linearObject = self.getLinearObjectAt(-1) # ultimo oggetto lineare
      return None if linearObject is None else linearObject.getTanDirectionOnEndPt()


   # ============================================================================
   # curve
   # ============================================================================
   def curve(self, toCurve = True):
      """
      se toCurve = True:
      la funzione curva ogni segmento per adattarlo alla polilinea
      facendo passare la nuova polilinea per i vertici.
      se toCurve = False:
      la funzione trasforma in segmento retto ogni arco della polilinea (lista di parti segmenti-archi).
      """
      if toCurve == False:
         i = 0 
         while i < self.qty():
            linearObject = self.defList[i]
            if linearObject.whatIs() != "LINE":
               self.insert(i, QadLine().set(linearObject.getStartPt(), linearObject.getEndPt()))
               self.remove(i + 1)
            i = i + 1
         return
            
      tot = self.qty()
      if tot < 2: return
      isClosed = self.isClosed() 

      newPolyline = QadPolyline()

      # primo oggetto lineare
      current = self.getLinearObjectAt(0)
      prev = None 
      tanDirectionOnStartPt = None
      if isClosed:
         prev = self.getLinearObjectAt(-1)
         arc = QadArc()
         if arc.fromStartSecondEndPts(prev.getStartPt(), current.getStartPt(), current.getEndPt()):
            if not arc.reversed: # arco non é inverso                  
               arc.setStartAngleByPt(current.getStartPt())
            else: # arco é inverso
               arc.setEndAngleByPt(current.getStartPt())
            tanDirectionOnStartPt = arc.getTanDirectionOnEndPt()
            
      next = self.getLinearObjectAt(1)
      newPolyline.defList.extend(getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next))
         
      i = 1
      while i < tot - 1:
         tanDirectionOnStartPt = newPolyline.getLinearObjectAt(-1).getTanDirectionOnEndPt()
         prev = current
         current = next         
         next = self.getLinearObjectAt(i + 1)
         newPolyline.defList.extend(getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next))
         i = i + 1

      # ultimo oggetto lineare
      tanDirectionOnStartPt = newPolyline.getLinearObjectAt(-1).getTanDirectionOnEndPt()
      prev = current
      current = next         
      next = self.getLinearObjectAt(0) if isClosed else None
      newPolyline.defList.extend(getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next))
          
      self.set(newPolyline)


   # ============================================================================
   # simplify
   # ============================================================================
   def simplify(self, tolerance):
      g = QgsGeometry.fromPolylineXY(self.asPolyline()).simplify(tolerance)
      return self.fromPolyline(g.asPolyline())


   # ============================================================================
   # getDistanceFromStart
   # ============================================================================
   def getDistanceFromStart(self, pt):
      """
      la funzione restituisce la distanza di <pt> (che deve essere sull'oggetto) dal punto iniziale.
      """
      tot = 0      
      for linearObject in self.defList:
         if linearObject.containsPt(pt) == True:
            return tot + linearObject.getDistanceFromStart(pt)
         else:
            tot = tot + linearObject.length()
         
      return -1


   # ============================================================================
   # getPointFromStart
   # ============================================================================
   def getPointFromStart(self, distance):
      """
      la funzione restituisce un punto (e la direzione della tangente) della polilinea alla distanza <distance>
      (che deve essere sull'oggetto) dal punto iniziale.
      """
      if distance < 0:
         return None, None
      d = distance
      for linearObject in self.defList:
         l = linearObject.length()
         if d > l:
            d = d - l
         else:
            return linearObject.getPointFromStart(d)

      return None, None


   # ============================================================================
   # lengthen_delta
   # ============================================================================
   def lengthen_delta(self, move_startPt, delta):
      """
      la funzione sposta il punto iniziale (se move_startPt = True) o finale (se move_startPt = False)
      di una distanza delta allungando (se delta > 0) o accorciando (se delta < 0) la polilinea
      """
      length = self.length()
      # lunghezza polilinea + delta non può essere <= 0
      if length + delta <= 0:         
         return False
      
      if move_startPt == False:
         # dal punto finale
         if delta >= 0: # allungo la polilinea
            # ultima parte
            return self.getLinearObjectAt(-1).lengthen_delta(False, delta)
         else: # accorcio la polilinea
            # cerco la parte in cui finirebbe la polilinea accorciata
            nPart = 0
            d = length + delta
            for linearObject in self.defList:
               l = linearObject.length()
               if d > l:
                  d = d - l
                  nPart = nPart + 1
               else:
                  if linearObject.lengthen_delta(False, -(l - d)) == False:
                     return False
                  # se non è l'ultima parte
                  if nPart+1 < len(self.defList):
                     # cancello le parti successive a nPart
                     del self.defList[nPart+1 :]
                  return True
      else: # dal punto iniziale
         # prima parte
         dummy = self.copy()
         dummy.reverse()
         if dummy.lengthen_delta(False, delta) == False:
            return False
         dummy.reverse()
         self.set(dummy)
         return True


   # ============================================================================
   # lengthen_deltaAngle
   # ============================================================================
   def lengthen_deltaAngle(self, move_startPt, delta):
      """
      la funzione sposta il punto iniziale (se move_startPt = True) o finale (se move_startPt = False)
      di un certo numero di gradi delta.
      """
      if move_startPt == False:
         # dal punto finale
         return self.getLinearObjectAt(-1).lengthen_deltaAngle(False, delta)
      else:
         # dal punto iniziale
         return self.getLinearObjectAt(0).lengthen_deltaAngle(True, delta)

   
   # ===============================================================================
   # transform
   # ===============================================================================
   def transform(self, coordTransform):
      """
      la funzione restituisce una nuova polilinea con le coordinate trasformate.
      """
      result = QadPolyline()
      for linearObject in self.defList:
         result.append(linearObject.transform(coordTransform))
      return result
   

   # ===============================================================================
   # transformFromCRSToCRS
   # ===============================================================================
   def transformFromCRSToCRS(self, sourceCRS, destCRS):
      """
      la funzione trasforma le coordinate dei punti che compone l'oggetto lineare.
      """
      return self.transform(QgsCoordinateTransform(sourceCRS, destCRS, QgsProject.instance()))


   # ============================================================================
   # containsPt
   # ============================================================================
   def containsPt(self, pt, startAt = 0):
      """
      la funzione ritorna True se il punto è sulla polilinea altrimenti False.
      Il controllo inizia dalla parte <startAt> (0-based)
      """
      tot = len(self.defList)
      if startAt < 0 or startAt >= tot:
         return False
      i = startAt      
      while i < tot:
         linearObject = self.defList[i]
         if linearObject.containsPt(pt):
            return True
         i = i + 1
      return False


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      for linearObject in self.defList:
         linearObject.move(offsetX, offsetY)


   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      for linearObject in self.defList:
         linearObject.rotate(basePt, angle)


   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      for linearObject in self.defList:
         linearObject.scale(basePt, scale)


   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      for linearObject in self.defList:
         linearObject.mirror(mirrorPt, mirrorAngle)


   # ===============================================================================
   # funzioni di creazione rettangoli
   # getRectByCorners
   # ===============================================================================
   def getRectByCorners(self, firstCorner, secondCorner, rot, gapType, \
                        gapValue1 = None, gapValue2 = None):
      """
      ritorna una polilinea che definisce il rettangolo costruito mediante 
      i due spigoli opposti firstCorner e secondCorner, la rotazione con punto base firstCorner e gapType 
      0 = gli spigoli del rettangolo hanno angoli retti
      1 = raccorda gli spigoli del rettangolo con un raggio di curvatura gapValue1
      2 = smussa gli spigoli del rettangolo con 2 distanze di cimatura gapValue1, gapValue2
      """
      self.removeAll()
      # creo un rettangolo ruotato con con angoli retti
      secondCornerProj = qad_utils.getPolarPointByPtAngle(firstCorner, rot, 10)
      pt2 = qad_utils.getPerpendicularPointOnInfinityLine(firstCorner, secondCornerProj, secondCorner)
      angle = qad_utils.getAngleBy2Pts(firstCorner, pt2)
      pt4 = qad_utils.getPolarPointByPtAngle(secondCorner, angle + math.pi, \
                                             qad_utils.getDistance(firstCorner, pt2))
      
      line = QadLine()
      if gapType == 0: # gli spigoli del rettangolo hanno angoli retti
         self.append(line.set(firstCorner, pt2))
         self.append(line.set(pt2, secondCorner))
         self.append(line.set(secondCorner, pt4))
         self.append(line.set(pt4, firstCorner))
         return True
      else:
         length = qad_utils.getDistance(firstCorner, pt2)
         width = qad_utils.getDistance(pt2, secondCorner)
                     
         if gapType == 1: # raccorda gli spigoli del rettangolo con un raggio di curvatura gapValue1
            if (gapValue1 * 2) > length or (gapValue1 * 2) > width: # il rettangolo é troppo piccolo
               self.append(line.set(firstCorner, pt2))
               self.append(line.set(pt2, secondCorner))
               self.append(line.set(secondCorner, pt4))
               self.append(line.set(pt4, firstCorner))
               return True
            
            arc = QadArc()
            
            diagonal = math.sqrt((gapValue1 * gapValue1) * 2)
            diagonal = gapValue1 - (diagonal / 2)
            
            # lato
            p1 = qad_utils.getPolarPointByPtAngle(firstCorner, angle, gapValue1)
            p2 = qad_utils.getPolarPointByPtAngle(pt2, angle + math.pi, gapValue1)
            self.append(line.set(p1, p2))
            # arco
            angle = qad_utils.getAngleBy2Pts(pt2, secondCorner)
            p3 = qad_utils.getPolarPointByPtAngle(pt2, angle, gapValue1)
            pMiddle = qad_utils.getMiddlePoint(p2, p3)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, pt2), diagonal) 
            arc.fromStartSecondEndPts(p2, pMiddle, p3)
            self.append(arc)
            # lato
            p4 = qad_utils.getPolarPointByPtAngle(secondCorner, angle + math.pi, gapValue1)
            self.append(line.set(p3, p4))
            # arco        
            angle = qad_utils.getAngleBy2Pts(secondCorner, pt4)
            p5 = qad_utils.getPolarPointByPtAngle(secondCorner, angle, gapValue1)
            pMiddle = qad_utils.getMiddlePoint(p4, p5)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, secondCorner), diagonal) 
            arc.fromStartSecondEndPts(p4, pMiddle, p5)
            self.append(arc)
            # lato
            p6 = qad_utils.getPolarPointByPtAngle(pt4, angle + math.pi, gapValue1)
            self.append(line.set(p5, p6))
            # arco
            angle = qad_utils.getAngleBy2Pts(pt4, firstCorner)
            p7 = qad_utils.getPolarPointByPtAngle(pt4, angle, gapValue1)
            pMiddle = qad_utils.getMiddlePoint(p6, p7)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, pt4), diagonal) 
            arc = QadArc()
            arc.fromStartSecondEndPts(p6, pMiddle, p7)
            self.append(arc)
            # lato
            p8 = qad_utils.getPolarPointByPtAngle(firstCorner, angle + math.pi, gapValue1)
            self.append(line.set(p7, p8))
            # arco
            pMiddle = qad_utils.getMiddlePoint(p8, p1)
            pMiddle = qad_utils.getPolarPointByPtAngle(pMiddle, qad_utils.getAngleBy2Pts(pMiddle, firstCorner), diagonal) 
            arc = QadArc()
            arc.fromStartSecondEndPts(p8, pMiddle, p1)
            self.append(arc)
            return True
         elif gapType == 2: # smussa gli spigoli del rettangolo con 2 distanze di cimatura gapValue1, gapValue2
            if (gapValue1 + gapValue2) > length or (gapValue1 + gapValue2) > width: # il rettangolo é troppo piccolo
               self.append(line.set(firstCorner, pt2))
               self.append(line.set(pt2, secondCorner))
               self.append(line.set(secondCorner, pt4))
               self.append(line.set(pt4, firstCorner))
               return True
   
            p1 = qad_utils.getPolarPointByPtAngle(firstCorner, angle, gapValue2)
            p2 = qad_utils.getPolarPointByPtAngle(pt2, angle + math.pi, gapValue1)
            angle = qad_utils.getAngleBy2Pts(pt2, secondCorner)
            p3 = qad_utils.getPolarPointByPtAngle(pt2, angle, gapValue2)
            p4 = qad_utils.getPolarPointByPtAngle(secondCorner, angle + math.pi, gapValue1)
            angle = qad_utils.getAngleBy2Pts(secondCorner, pt4)
            p5 = qad_utils.getPolarPointByPtAngle(secondCorner, angle, gapValue2)
            p6 = qad_utils.getPolarPointByPtAngle(pt4, angle+ math.pi, gapValue1)
            angle = qad_utils.getAngleBy2Pts(pt4, firstCorner)
            p7 = qad_utils.getPolarPointByPtAngle(pt4, angle, gapValue2)
            p8 = qad_utils.getPolarPointByPtAngle(firstCorner, angle + math.pi, gapValue1)
            
            self.append(line.set(p1, p2))
            self.append(line.set(p2, p3))
            self.append(line.set(p3, p4))
            self.append(line.set(p4, p5))
            self.append(line.set(p5, p6))
            self.append(line.set(p6, p7))
            self.append(line.set(p7, p8))
            self.append(line.set(p8, p1))
            return True
         
      return False


   # ===============================================================================
   # getRectByCornerAndDims
   # ===============================================================================
   def getRectByCornerAndDims(self, firstCorner, lengthDim, widthDim, rot, gapType, \
                              gapValue1 = None, gapValue2 = None):
      """
      ritorna una polilinea che definisce il rettangolo costruito mediante 
      uno spigolo , la lunghezza, la larghezza, la rotazione con punto base firstCorner e gapType 
      0 = gli spigoli del rettangolo hanno angoli retti
      1 = raccorda gli spigoli del rettangolo con un raggio di curvatura gapValue1
      2 = smussa gli spigoli del rettangolo con 2 distanze di cimatura gapValue1, gapValue2 
      """
      pt2 = qad_utils.getPolarPointByPtAngle(firstCorner, rot, lengthDim)
      secondCorner = qad_utils.getPolarPointByPtAngle(pt2, rot + (math.pi / 2), widthDim)
      return self.getRectByCorners(firstCorner, secondCorner, rot, gapType, gapValue1, gapValue2)


   # ===============================================================================
   # getRectByAreaAndLength
   # ===============================================================================
   def getRectByAreaAndLength(self, firstCorner, area, lengthDim, rot, gapType, \
                              gapValue1 = None, gapValue2 = None):
      """
      ritorna una polilinea che definisce il rettangolo costruito mediante 
      uno spigolo , l'area, la larghezza, la rotazione con punto base firstCorner e gapType 
      0 = gli spigoli del rettangolo hanno angoli retti
      1 = raccorda gli spigoli del rettangolo con un raggio di curvatura gapValue1
      2 = smussa gli spigoli del rettangolo con 2 distanze di cimatura gapValue1, gapValue2 
      """   
      if gapType == 0: # gli spigoli del rettangolo hanno angoli retti
         widthDim = area / lengthDim
         return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                            gapValue1, gapValue2)
      else:
         if gapType == 1: # raccorda gli spigoli del rettangolo con un raggio di curvatura gapValue1
            angleArea = ((2 * gapValue1) * (2 * gapValue1)) - (math.pi * gapValue1 * gapValue1)
            widthDim = (area + angleArea) / lengthDim
            if (gapValue1 * 2) > lengthDim or (gapValue1 * 2) > widthDim: # il rettangolo é troppo piccolo
               widthDim = area / lengthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)
         elif gapType == 2: # smussa gli spigoli del rettangolo con 2 distanze di cimatura gapValue1, gapValue2
            angleArea = 2 * (gapValue1 * gapValue2)
            widthDim = (area + angleArea) / lengthDim
            if (gapValue1 + gapValue2) > lengthDim or (gapValue1 + gapValue2) > widthDim: # il rettangolo é troppo piccolo
               widthDim = area / lengthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)


   # ===============================================================================
   # getRectByAreaAndWidth
   # ===============================================================================
   def getRectByAreaAndWidth(self, firstCorner, area, widthDim, rot, gapType, \
                              gapValue1 = None, gapValue2 = None):
      """
      ritorna una polilinea che definisce il rettangolo costruito mediante 
      uno spigolo , l'area, la larghezza, la rotazione con punto base firstCorner e gapType 
      0 = gli spigoli del rettangolo hanno angoli retti
      1 = raccorda gli spigoli del rettangolo con un raggio di curvatura gapValue1
      2 = smussa gli spigoli del rettangolo con 2 distanze di cimatura gapValue1, gapValue2 
      """   
      if gapType == 0: # gli spigoli del rettangolo hanno angoli retti
         lengthDim = area / widthDim
         return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                            gapValue1, gapValue2)
      else:                  
         if gapType == 1: # raccorda gli spigoli del rettangolo con un raggio di curvatura gapValue1
            angleArea = math.pi * gapValue1 * gapValue1
            lengthDim = (area + angleArea) / widthDim
            if (gapValue1 * 2) > lengthDim or (gapValue1 * 2) > widthDim: # il rettangolo é troppo piccolo
               lengthDim = area / widthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)
         elif gapType == 2: # smussa gli spigoli del rettangolo con 2 distanze di cimatura gapValue1, gapValue2
            angleArea = 2 * (gapValue1 * gapValue2)
            lengthDim = (area + angleArea) / widthDim
            if (gapValue1 + gapValue2) > lengthDim or (gapValue1 + gapValue2) > widthDim: # il rettangolo é troppo piccolo
               lengthDim = area / widthDim
            return self.getRectByCornerAndDims(firstCorner, lengthDim, widthDim, rot, gapType, \
                                               gapValue1, gapValue2)


   # ===============================================================================
   # funzioni di creazione poligoni
   # getPolygonByNsidesCenterRadius
   # ===============================================================================
   def getPolygonByNsidesCenterRadius(self, sideNumber, centerPt, radius, Inscribed, ptStart = None):
      """
      ritorna una polilinea che definisce il poligono costruito mediante 
      sideNumber = numero di lati 
      centerPt = centro del poligono
      radius = raggio del cerchio
      Inscribed = se True significa poligono inscritto altrimento circoscritto
      ptStart = punto da cui partire
      """
      self.removeAll()
      line = QadLine()
            
      angleIncrement = 2 * math.pi / sideNumber
      # poligono circoscritto
      if Inscribed == False:
         # calcolo il nuovo raggio 
         myRadius = radius / math.cos(angleIncrement / 2)
   
         if ptStart is None:
            myPtStart = qad_utils.getPolarPointByPtAngle(centerPt, math.pi / 2 * 3 + (angleIncrement / 2), myRadius)
            angle = qad_utils.getAngleBy2Pts(centerPt, myPtStart)
         else:
            angle = qad_utils.getAngleBy2Pts(centerPt, ptStart)      
            myPtStart = qad_utils.getPolarPointByPtAngle(centerPt, angle + (angleIncrement / 2), myRadius)
            angle = qad_utils.getAngleBy2Pts(centerPt, myPtStart)      
      else: # poligono inscritto
         myRadius = radius
         
         if ptStart is None:
            myPtStart = qad_utils.getPolarPointByPtAngle(centerPt, math.pi / 2 * 3 + (angleIncrement / 2), myRadius)
            angle = qad_utils.getAngleBy2Pts(centerPt, myPtStart)
         else:
            myPtStart = ptStart
            angle = qad_utils.getAngleBy2Pts(centerPt, ptStart)      
      
      previusPt = myPtStart
      for i in range(1, sideNumber, 1):
         angle = angle + angleIncrement
         pt = qad_utils.getPolarPointByPtAngle(centerPt, angle, myRadius)
         self.append(line.set(previusPt, pt))
         previusPt = pt
      self.append(line.set(previusPt, myPtStart))
      
      return True


   # ===============================================================================
   # getPolygonByNsidesEdgePts
   # ===============================================================================
   def getPolygonByNsidesEdgePts(self, sideNumber, firstEdgePt, secondEdgePt):
      """
      ritorna una polilinea che definisce il poligono costruito mediante 
      sideNumber = numero di lati 
      firstEdgePt = primo punto di un lato
      secondEdgePt = secondo punto di un lato
      """
      self.removeAll()
      line = QadLine()      

      angleIncrement = 2 * math.pi / sideNumber
      angle = qad_utils.getAngleBy2Pts(firstEdgePt, secondEdgePt)
      sideLength = qad_utils.getDistance(firstEdgePt, secondEdgePt)
            
      self.append(line.set(firstEdgePt, secondEdgePt))
      previusPt = secondEdgePt
      for i in range(1, sideNumber - 1, 1):
         angle = angle + angleIncrement
         pt = qad_utils.getPolarPointByPtAngle(previusPt, angle, sideLength)
         self.append(line.set(previusPt, pt))
         previusPt = pt
      self.append(line.set(previusPt, firstEdgePt))
      
      return True


   # ===============================================================================
   # getPolygonByNsidesArea
   # ===============================================================================
   def getPolygonByNsidesArea(self, sideNumber, centerPt, area):
      """
      ritorna una polilinea che definisce il poligono costruito mediante 
      sideNumber = numero di lati 
      centerPt = centro del poligono
      area = area del poligono
      """
      angle = 2 * math.pi / sideNumber
      triangleArea = area / sideNumber / 2
      # divido il poligono in sideNumber triangoli
      # ogni trinagolo viene diviso in 2 generando 2 trinagoli rettangoli in cui
      # "(base * altezza) / 2 = Area" che equivale a "base = 2 * Area / altezza"
      # "tan(alfa) = base / altezza" che equivale a "tan(alfa) * altezza = base
      # per sostituzione si ha
      # "tan(alfa) * altezza = 2 * Area / altezza" quindi
      # "altezza = sqrt(2 * Area / tan(alfa))"
      h = math.sqrt(2 * triangleArea / math.tan(angle / 2))
      
      return self.getPolygonByNsidesCenterRadius(sideNumber, centerPt, h, False)


   # ============================================================================
   # getPartPosAtPt
   # ============================================================================
   def getPartPosAtPt(self, pt, startAt = 0):
      """
      la funzione restituisce la posizione del parte contentente il punto <pt> (0-based),
      -1 se non trovato.
      Il controllo inizia dalla parte <startAt> (0-based)
      """
      tot = len(self.defList)
      if startAt < 0 or startAt >= tot:
         return -1
      i = startAt      
      while i < tot:
         linearObject = self.defList[i]
         if linearObject.containsPt(pt):
            return i
         i = i + 1
      return -1


   # ===============================================================================
   # getGeomBetween2Pts
   # ===============================================================================
   def getGeomBetween2Pts(self, startPt, endPt):
      """
      Ritorna una sotto geometria che parte dal punto startPt e finisce al punto endPt seguendo il tracciato della geometria.
      Se la polilinea è chiusa ritorna il percorso più breve per andare da startPt a endPt.
      """
      tot = self.qty()

      iStart = self.getPartPosAtPt(startPt) # numero della parte contenente startPt
      if iStart == -1: return None

      result1 = QadPolyline()
      i = iStart
      lastPt = startPt
      ok1 = False
      while i < tot:
         linearObj = self.getLinearObjectAt(i)
         if linearObj.containsPt(endPt):
            result1.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
            ok1 = True
            break
         elif i == iStart:
            result1.append(linearObj.getGeomBetween2Pts(lastPt, linearObj.getEndPt()))
         else:
            result1.append(linearObj)
            
         if result1.qty() > 0: lastPt = result1.getEndPt() # getGeomBetween2Pts potrebbe restituire None
         i = i + 1
      
      if ok1:
         if self.isClosed() == False: return result1
      else:
         # se non trovata la fine ed è una polilinea chiusa, riparto dall'inizio
         if self.isClosed():
            i = 0
            while i < iStart:
               linearObj = self.getLinearObjectAt(i)
               if linearObj.containsPt(endPt):
                  result1.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
                  ok1 = True
                  break
               else:
                  if linearObj.length() > 0: result1.append(linearObj)
               
               if result1.qty() > 0: lastPt = result1.getEndPt() # getGeomBetween2Pts potrebbe restituire None
               
               i = i + 1

      # cerco nel senso opposto
      inversedPolyline = QadPolyline(self).reverse()
      
      result2 = QadPolyline()
      iStart = tot - 1 - iStart
      i = iStart
      lastPt = startPt
      ok2 = False
      while i < tot:
         linearObj = inversedPolyline.getLinearObjectAt(i)
         if linearObj.containsPt(endPt):
            result2.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
            ok2 = True
            break
         elif i == iStart:
            result2.append(linearObj.getGeomBetween2Pts(lastPt, linearObj.getEndPt()))
         else:
            result2.append(linearObj)

         if result2.qty() > 0: lastPt = result2.getEndPt() # getGeomBetween2Pts potrebbe restituire None
         i = i + 1
      
      if ok2:
         if self.isClosed() == False: return result2
      else:
         # se non trovata la fine ed è una polilinea chiusa, riparto dall'inizio
         if self.isClosed():
            i = 0
            while i < iStart:
               linearObj = inversedPolyline.getLinearObjectAt(i)
               if linearObj.containsPt(endPt):
                  result2.append(linearObj.getGeomBetween2Pts(lastPt, endPt))
                  ok2 = True
                  break
               else:
                  if linearObj.length() > 0: result2.append(linearObj)

               if result2.qty() > 0: lastPt = result2.getEndPt() # getGeomBetween2Pts potrebbe restituire None
               i = i + 1

      if ok1:
         if ok2:
            return result1 if result1.length() < result2.length() else result2
         else:
            return result1
      else:
         if ok2:
            return result2
         else:
            return None


   # ===============================================================================
   # breakOnPts
   # ===============================================================================
   def breakOnPts(self, firstPt, secondPt):
      """
      la funzione spezza la geometria in un punto (se <secondPt> = None) o in due punti 
      come fa il trim. Ritorna una o due geometrie risultanti dall'operazione.
      <firstPt> = primo punto di divisione
      <secondPt> = secondo punto di divisione
      """
      if secondPt is None or firstPt == secondPt: # break su un punto
         if self.isClosed(): return None, None # se é chiusa
         return [self.getGeomBetween2Pts(self.getStartPt(), firstPt), self.getGeomBetween2Pts(firstPt, self.getEndPt())]
      else: # break su 2 punti
         dist1 = self.getDistanceFromStart(firstPt)
         dist2 = self.getDistanceFromStart(secondPt)
         if dist1 < dist2:
            g1 = self.getGeomBetween2Pts(self.getStartPt(), firstPt)
            g2 = self.getGeomBetween2Pts(secondPt, self.getEndPt())
         else:
            g1 = self.getGeomBetween2Pts(self.getStartPt(), secondPt)
            g2 = self.getGeomBetween2Pts(firstPt, self.getEndPt())
            
         if self.isClosed(): # se é chiusa
            g2.appendPolyline(g1)
            return [g2, None]
         else:
            return [g1, g2]


# ===============================================================================
# getCurveLinearObjects
# ===============================================================================
def getCurveLinearObjects(tanDirectionOnStartPt, prev, current, next):
   """
   Data la direzione della tangente nel punto iniziale della parte corrente e 
   una successione di 3 parti lineari,
   la funzione ritorna una lista di parti lineari
   da sostituire alla parte <current> per curvare la polilinea
   """
   # se non ci sono né la parte precedente né la parte successiva 
   if prev is None and next is None:
      return current

   arc = QadArc()
   if prev is None: # non c'é una parte precedente
      if arc.fromStartSecondEndPts(current.getStartPt(), current.getEndPt(), next.getEndPt()) == False:
         return [current]
      if not arc.reversed: # arco non é inverso                  
         arc.setEndAngleByPt(current.getEndPt())
         return [arc]
      else: # arco é inverso
         arc.setStartAngleByPt(current.getEndPt())
         return [arc]
   else: # c'é una parte precedente
      t = prev.getTanDirectionOnEndPt() if tanDirectionOnStartPt is None else tanDirectionOnStartPt
       
      if next is None: # non c'é una parte successiva          
         if arc.fromStartEndPtsTan(current.getStartPt(), current.getEndPt(), t) == False:
            return [current]
         return [arc]
      else: # c'é una parte precedente e successiva
         if arc.fromStartSecondEndPts(prev.getStartPt(), current.getStartPt(), current.getEndPt()) == False:
            return [current]
         if not arc.reversed: # arco non é inverso
            arc.setStartAngleByPt(current.getStartPt())
         else: # arco é inverso
            arc.setEndAngleByPt(current.getStartPt())
         arc2 = QadArc()
         if arc2.fromStartSecondEndPts(current.getStartPt(), current.getEndPt(), next.getEndPt()) == False:
            return [current]
         if not arc2.reversed: # arco non é inverso
            arc2.setEndAngleByPt(current.getEndPt())
         else: # arco é inverso
            arc2.setStartAngleByPt(current.getEndPt())

         midPt = qad_utils.getMiddlePoint(arc.getMiddlePt(), arc2.getMiddlePt())
         
         if arc.fromStartEndPtsTan(current.getStartPt(), midPt, t) == False:
            return [current]
                  
         if arc2.fromStartEndPtsTan(arc.getEndPt(), current.getEndPt(), \
                                    arc.getTanDirectionOnEndPt()) == False:
            return [current]

         return [arc, arc2]
