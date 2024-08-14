# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire gli snap
 
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


from qgis.core import *

import math
import sys

from . import qad_utils
from .qad_multi_geom import *
from .qad_geom_relations import *
from .qad_entity import *
from .qad_msg import QadMsg
from .qad_variables import QadVariables

   
#===============================================================================
# QadSnapTypeEnum class.
#===============================================================================
class QadSnapTypeEnum():
   NONE      = 0       # nessuno
   END       = 1       # punti finali di ogni segmento
   MID       = 2       # punto medio 
   CEN       = 4       # centro (centroide)
   NOD       = 8       # oggetto punto
   QUA       = 16      # punto quadrante
   INT       = 32      # intersezione
   INS       = 64      # punto di inserimento
   PER       = 128     # punto perpendicolare
   TAN       = 256     # tangente
   NEA       = 512     # punto più vicino
   C         = 1024    # pulisci all object snaps
   APP       = 2048    # intersezione apparente
   EXT       = 4096    # estensione
   PAR       = 8192    # parallelo
   DISABLE   = 16384   # osnap off                      
   PR        = 65536   # distanza progressiva
   EXT_INT   = 131072  # intersezione sull'estensione
   PER_DEF   = 262144  # perpendicolare differita (come NEA)
   TAN_DEF   = 524288  # tangente differita (come NEA)
   POLAR     = 1048576 # puntamento polare
   END_PLINE = 2097152 # punti finali dell'intera polilinea

#===============================================================================
# QadSnapModeEnum class.
#===============================================================================
class QadSnapModeEnum():
   ONE_RESULT           = 0 # Viene restituito solo il punto più vicino
   ALL_RESULTS          = 2 # Tutti i punti

#===============================================================================
# QadVertexSearchModeEnum class.
#===============================================================================
class QadVertexSearchModeEnum():
   ALL               = 0 # tutti i vertici
   EXCLUDE_START_END = 1 # escludi il punto iniziale e finale
   ONLY_START_END    = 2 # solo il punto iniziale e finale


#===============================================================================
# Qad snapper class.
#===============================================================================
class QadSnapper():
   """
   Classe che gestisce i punti di snap, i punti di snap sono sempre memorizzati nel sistema di coordinate del canvas
   che utilizza un sistema piano (no coordinate geografiche)
   """


   #============================================================================
   # __init__
   #============================================================================
   def __init__(self):
      self.__snapType = QadSnapTypeEnum.NONE
      self.__snapLayers = None      
      self.__snapMode = QadSnapModeEnum.ONE_RESULT
      
      # sistema di coordinate del canvas in cui memorizzare i punti di snap (per lavorare con coordinate piane xy)
      self.__snapPointCRS = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
      self.__startPoint = None
      self.__toleranceExtParLines = 0
      
      self.__extLinearObjs = [] # lista degli oggetti lineari da estendere (QadLine o QadArc o QadEllipseArc)
      self.__parLines = [] # lista delle linee per modo parallelo (ogni elemento é un QadLine)
      self.__intExtLinearObjs = [] # lista degli oggetti lineari per intersezione su estensione (QadLine o QadArc o QadEllipseArc)
            
      self.__cacheEntitySet = QadCacheEntitySet() # cache delle entità qad
      self.__oSnapPointsForPolar = dict() # dictionary di punti di osnap selezionati per l'opzione polare
      self.__oSnapLinesForPolar = [] # lista delle linee (QadLine) per l'opzione polare
      self.__progressDistance = 0.0 # distanza progressiva dall'inizio della linea
      self.__distToExcludeNea = 0.0 # distanza entro la quale se ci sono dei punti di snap
                                    # diversi da nearest questi hanno priorità su nearest
                                    # altrimenti nearest vincerebbe sempre
      self.tmpGeometries = [] # lista di geometrie qad non ancora esistenti ma da contare per i punti di osnap (in map coordinates)


   #============================================================================
   # SnapType
   #============================================================================
   def setSnapType(self, snapType):
      """
      Imposta il tipo di snapping
      """            
      if self.__snapType != snapType:
         self.__snapType = snapType
         self.removeReferenceLines()
   def getSnapType(self):
      """
      Restituisce il tipo di snapping
      """
      return self.__snapType


   #============================================================================
   # SnapType
   #============================================================================
   def getGeometryTypesAccordingToSnapType(self):
      """
      Verifica quali geometrie vengono coinvolte dal tipo di snap impostato
      Ritorna una lista di 3 elementi: (point, line, polygon)
      - se il primo elemento é vero il tipo punto é coinvolto altrimenti falso
      - se il secondo elemento é vero il tipo linea é coinvolto altrimenti falso
      - se il terzo elemento é vero il tipo poligono é coinvolto altrimenti falso
      """
      if self.getSnapType() == QadSnapTypeEnum.NONE or \
         self.getSnapType() & QadSnapTypeEnum.DISABLE:
         return False, False, False
      
      point = False
      line = False
      polygon = False

      # <oggetto punto> o <punto di inserimento> o <punto più vicino>
      if self.getSnapType() & QadSnapTypeEnum.NOD or \
         self.getSnapType() & QadSnapTypeEnum.INS or \
         self.getSnapType() & QadSnapTypeEnum.NEA:
         point = True
      
      # <punto finale> o <punto medio> o <centro (centroide o centro arco)> o 
      # <intersezione> o <punto perpendicolare> o <tangente> o
      # <punto più vicino> o <intersezione apparente> o <estensione>
      # <parallelo> o <distanza progressiva> o <intersezione sull'estensione>
      if self.getSnapType() & QadSnapTypeEnum.END or \
         self.getSnapType() & QadSnapTypeEnum.END_PLINE or \
         self.getSnapType() & QadSnapTypeEnum.MID or \
         self.getSnapType() & QadSnapTypeEnum.CEN or \
         self.getSnapType() & QadSnapTypeEnum.QUA or \
         self.getSnapType() & QadSnapTypeEnum.INT or \
         self.getSnapType() & QadSnapTypeEnum.PER or \
         self.getSnapType() & QadSnapTypeEnum.TAN or \
         self.getSnapType() & QadSnapTypeEnum.NEA or \
         self.getSnapType() & QadSnapTypeEnum.APP or \
         self.getSnapType() & QadSnapTypeEnum.EXT or \
         self.getSnapType() & QadSnapTypeEnum.PAR or \
         self.getSnapType() & QadSnapTypeEnum.PR or \
         self.getSnapType() & QadSnapTypeEnum.EXT_INT or \
         self.getSnapType() & QadSnapTypeEnum.PER_DEF or \
         self.getSnapType() & QadSnapTypeEnum.TAN_DEF:
         line = True
         
      # <punto finale> o <punto medio> o <centro (centroide o centro arco)> o 
      # <punto quadrante> o <intersezione> o <punto perpendicolare> o <tangente> o
      # <punto più vicino> o <intersezione apparente> o <estensione>
      # <parallelo> o <distanza progressiva> o <intersezione sull'estensione>
      if self.getSnapType() & QadSnapTypeEnum.END or \
         self.getSnapType() & QadSnapTypeEnum.MID or \
         self.getSnapType() & QadSnapTypeEnum.CEN or \
         self.getSnapType() & QadSnapTypeEnum.QUA or \
         self.getSnapType() & QadSnapTypeEnum.INT or \
         self.getSnapType() & QadSnapTypeEnum.PER or \
         self.getSnapType() & QadSnapTypeEnum.TAN or \
         self.getSnapType() & QadSnapTypeEnum.NEA or \
         self.getSnapType() & QadSnapTypeEnum.APP or \
         self.getSnapType() & QadSnapTypeEnum.EXT or \
         self.getSnapType() & QadSnapTypeEnum.PAR or \
         self.getSnapType() & QadSnapTypeEnum.PR or \
         self.getSnapType() & QadSnapTypeEnum.EXT_INT or \
         self.getSnapType() & QadSnapTypeEnum.PER_DEF or \
         self.getSnapType() & QadSnapTypeEnum.TAN_DEF:
         polygon = True

      return point, line, polygon


   #============================================================================
   # Snapmode
   #============================================================================
   def setSnapMode(self, snapMode):
      """
      Imposta la modalità di snapping
      """      
      self.__snapMode = snapMode
   def getSnapMode(self):
      """
      Restituisce il modo di snapping
      """
      return self.__snapMode


   #============================================================================
   # SnapLayers
   #============================================================================
   def setSnapLayers(self, snapLayers):
      """
      Imposta i layer da considerare nello snapping
      """      
      self.__snapLayers = snapLayers
   def getSnapLayers(self):
      """
      Restituisce la lista dei layer da considerare per lo snapping
      """
      return self.__snapLayers


   #============================================================================
   # setStartPoint
   #============================================================================
   def setStartPoint(self, startPoint):
      """
      setta il punto di partenza usato per calcolare i punti di snap
      """
      self.__startPoint = startPoint     


   #============================================================================
   # setDistToExcludeNea
   #============================================================================
   def setDistToExcludeNea(self, distToExcludeNea):
      """
      setta la distanza entro la quale se ci sono dei punti di snap diversi da nearest 
      questi hanno priorità su nearest altrimenti nearest vincerebbe sempre
      """
      self.__distToExcludeNea = distToExcludeNea


   #===========================================================================
   # getOsnapPtAndLinesForPolar
   #===========================================================================
   def getOsnapPtAndLinesForPolar(self, point, polarAng, polarAngOffset, polarAddAngles):
      # calcola i punti polari per tutti i punti di osnap selezionati per l'opzione polare e per per il punto corrente
      # i punti vanno in result, le linee vanno in self.__oSnapLinesForPolar
       
      result = []
      del self.__oSnapLinesForPolar[:]
      # per tutti i punti di osnap selezionati per l'opzione polare
      for item in self.__oSnapPointsForPolar.items():
         # salto il tipo POLAR
         if item[0] != QadSnapTypeEnum.POLAR:
            for startPoint in item[1]:
               pts = self.getPolarCoord(startPoint, point, polarAng, polarAngOffset, polarAddAngles) # ritorna una lista con un solo punto
               if len(pts) > 0:
                  self.__appendUniquePoint(result, pts[0]) # senza duplicazione
                  l = QadLine().set(startPoint, pts[0])
                  self.__oSnapLinesForPolar.append(l)

      # per il punto di partenza
      if self.__startPoint is not None:
         pts = self.getPolarCoord(self.__startPoint, point, polarAng, polarAngOffset, polarAddAngles) # ritorna una lista con un solo punto
         if len(pts) > 0:
            self.__appendUniquePoint(result, pts[0]) # senza duplicazione
            l = QadLine().set(self.__startPoint, pts[0])
            self.__oSnapLinesForPolar.append(l)
      
      return result


   #============================================================================
   # getIntPtsBetweenOSnapLinesForPolar
   #============================================================================      
   def getIntPtsBetweenOSnapLinesForPolar(self):
      # calcolo le intersezioni delle linee polari
      result = []
      i = 0
      totLines = len(self.__oSnapLinesForPolar)
      while i < totLines:
         line1 = self.__oSnapLinesForPolar[i]
         j = i + 1
         while j < totLines:
            line2 = self.__oSnapLinesForPolar[j]
            point = QadIntersections.twoInfinityLines(line1, line2)
            if point is not None:
               self.__appendUniquePoint(result, point) # senza duplicazione
            j = j + 1
         i = i + 1
         
      return result
   

   #============================================================================
   # OSnapPointsForPolar
   #============================================================================      
   def __toggleOSnapPointsForPolar(self, mousePoint, oSnapPointsForPolar, snapMarkerSizeInMapUnits = None):
      """
      Aggiunge un punto di osnap usati per l'opzione polare
      se non ancora inserito in lista altrimenti lo rimuove dalla lista
      __oSnapPointsForPolar é un dizionario di liste di punti di snap
      suddivisi per tipi di snap (es. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """
      del self.__oSnapLinesForPolar[:]
      
      markerSize = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE")) if snapMarkerSizeInMapUnits is None else snapMarkerSizeInMapUnits

      for itemToToggle in oSnapPointsForPolar.items():                  
         for ptToToggle in itemToToggle[1]: # per ogni punto
            # se il punto <point> è dentro il marker del punto di snap che ha dimensioni markerSize
            if mousePoint.x() >= ptToToggle.x() - markerSize and mousePoint.x() <= ptToToggle.x() + markerSize and \
               mousePoint.y() >= ptToToggle.y() - markerSize and mousePoint.y() <= ptToToggle.y() + markerSize: 
               add = True
               for item in self.__oSnapPointsForPolar.items():
                  polarPts = item[1]
                  for i in range(len(polarPts) - 1, -1, -1):
                     polarPt = polarPts[i]
                     # se il punto <point> è dentro il marker del punto di snap polare che ha dimensioni markerSize
                     if mousePoint.x() >= polarPt.x() - markerSize and mousePoint.x() <= polarPt.x() + markerSize and \
                        mousePoint.y() >= polarPt.y() - markerSize and mousePoint.y() <= polarPt.y() + markerSize: 
                        del polarPts[i]
                        add = False
   
               if add:
                  key = itemToToggle[0]
                  if key in self.__oSnapPointsForPolar: # se già presente
                     self.__oSnapPointsForPolar[key].append(ptToToggle)
                  else:
                     self.__oSnapPointsForPolar[key] = [ptToToggle]
      
#       autoSnapSize = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE"))
#       
#       for itemToToggle in oSnapPointsForPolar.items():
#          key = itemToToggle[0]
#          # non considero alcuni tipi di snap
#          if key == QadSnapTypeEnum.INT or key == QadSnapTypeEnum.PER or key == QadSnapTypeEnum.TAN or \
#             key == QadSnapTypeEnum.NEA or key == QadSnapTypeEnum.APP or key == QadSnapTypeEnum.EXT or \
#             key == QadSnapTypeEnum.PAR or key == QadSnapTypeEnum.PR or key == QadSnapTypeEnum.EXT_INT or \
#             key == QadSnapTypeEnum.PER_DEF or key == QadSnapTypeEnum.TAN_DEF or key == QadSnapTypeEnum.POLAR:
#             continue
#          
#          for ptToToggle in itemToToggle[1]: # per ogni punto
#             # il punto <point> deve essere dentro il punto di snap che ha dimensioni snapMarkerSizeInMapUnits
#             if point.x() >= ptToToggle.x() - snapMarkerSizeInMapUnits and point.x() <= ptToToggle.x() + snapMarkerSizeInMapUnits and \
#                point.y() >= ptToToggle.y() - snapMarkerSizeInMapUnits and point.y() <= ptToToggle.y() + snapMarkerSizeInMapUnits: 
#                add = True
#                for item in self.__oSnapPointsForPolar.items():
#                   i = 0
#                   for pt in item[1]:
#                      if pt == ptToToggle:
#                         del item[1][i]
#                         add = False
#                         i = i + 1
#    
#                if add:
#                   if key in self.__oSnapPointsForPolar: # se già presente
#                      self.__oSnapPointsForPolar[key].append(ptToToggle)
#                   else:
#                      self.__oSnapPointsForPolar[key] = [ptToToggle]


   def removeOSnapPointsForPolar(self):
      """
      Elimina tutti punti di osnap usati per l'opzione polare
      """
      self.__oSnapPointsForPolar.clear() # svuoto il dizionario
      del self.__oSnapLinesForPolar[:] # svuoto la lista

   def getOSnapPointsForPolar(self):
      return self.__oSnapPointsForPolar

   def getOSnapLinesForPolar(self):
      return self.__oSnapLinesForPolar


   #===========================================================================
   # ReferenceLines
   #===========================================================================
   def toggleReferenceLines(self, geomEntity, point, oSnapPointsForPolar = None, snapMarkerSizeInMapUnits = None):
      """
      geomEntity può essere una QgsGeometry con coordinate del canvas oppure una QadEntity
      se si passa una QadEntity lo snapper utilizza la sua cache
      point è in coordinate del canvas
      """
      if oSnapPointsForPolar is not None:
         self.__toggleOSnapPointsForPolar(point, oSnapPointsForPolar, snapMarkerSizeInMapUnits)
         
      # usato solo per snap EXT o PAR
      if not(self.__snapType & QadSnapTypeEnum.EXT) and \
         not(self.__snapType & QadSnapTypeEnum.PAR):
         return
      
      if type(geomEntity) == QgsGeometry: # se è una geometria di QGIS
         qadGeom = fromQgsGeomToQadGeom(geomEntity)
      else: # è un'entità di QAD
         # uso la cache delle entità di QAD
         cacheEntity = self.__cacheEntitySet.getEntity(geomEntity.layerId(), geomEntity.featureId)
         if cacheEntity is None:
            cacheEntity = self.__cacheEntitySet.appendEntity(geomEntity) # la aggiungo alla cache
         qadGeom = cacheEntity.getQadGeom()
         
      # la funzione ritorna una lista con 
      # (<minima distanza>
      #  <punto più vicino>
      #  <indice della geometria più vicina>
      #  <indice della sotto-geometria più vicina>
      #   se geometria chiusa è tipo polyline la lista contiene anche
      #  <indice della parte della sotto-geometria più vicina>
      #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
      # )
      result = getQadGeomClosestPart(qadGeom, point)
      g = getQadGeomPartAt(qadGeom, result[2], result[3], result[4])
      
      geomType = g.whatIs()
      if self.__snapType & QadSnapTypeEnum.EXT:
         self.toggleExtLinearObj(g)
      if self.__snapType & QadSnapTypeEnum.PAR:
         self.toggleParLine(g)


   def removeReferenceLines(self):
      self.removeExtLinearObjs()
      self.removeParLines()
      self.removeIntExtLinearObj()
      self.removeOSnapPointsForPolar()


   #============================================================================
   # setToleranceExtParLines
   #============================================================================
   def setToleranceExtParLines(self, tolerance):
      self.__toleranceExtParlines = tolerance


   #============================================================================
   # tmpGeometries (le geometrie temporanee sono in crs del canvas
   #============================================================================
   def clearTmpGeometries(self):      
      del self.tmpGeometries[:] # svuoto la lista

   def setTmpGeometry(self, geom):      
      self.clearTmpGeometries()
      self.appendTmpGeometry(geom)

   def appendTmpGeometry(self, geom):
      if geom is None:
         return
      if type(geom) == QgsGeometry: # se è una geometria di QGIS
         qadGeom = fromQgsGeomToQadGeom(geom)
         self.tmpGeometries.append(qadGeom)
      else: # è una geometria di QAD
         self.tmpGeometries.append(geom)


   def setTmpGeometries(self, geoms, CRS = None):
      self.clearTmpGeometries()
      for g in geoms:
         self.appendTmpGeometry(g, CRS)


   #===========================================================================
   # getSnapPoint
   #===========================================================================
   def getSnapPoint(self, geomEntity, point, excludePoints = None, \
                    polarAng = None, polarAngOffset = None, polarAddAngles = None, isTemporaryGeom = False):
      """
      Data una geometria (QgsGeometry) o un'entita qad (QadEntity) ed un punto (posizione del cursore) nel sistema di coordinate map canvas 
      ottiene i punti di snap (con esclusione dei punti in excludePoints).
      Resituisce un dizionario di liste di punti di snap
      suddivisi per tipi di snap (es. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      - excludePoints = lista di punti da escludere espressa in __snapPointCRS
      - polarAng angolo in radianti per il puntamento polare
      - polarAngOffset angolo in radianti relativo all'ultimo segmento
      - polarAddAngles lista di angoli (in raduianti) in aggiunta a polarAng
      - isTemporaryGeom flag che indica se geom é un oggetto temporaneo che ancora non esiste
      """
      g = None
      gPart = None
      
      if geomEntity is not None:         
         cacheEntity = None
         qadGeom = None
         if type(geomEntity) == QgsGeometry: # se è una geometria di QGIS
            qadGeom = fromQgsGeomToQadGeom(geomEntity)
         else: # è un'entità di QAD
            # la geometria deve essere in un layer abilitato allo snapping
            if geomEntity.layer in self.__snapLayers:
               # uso la cache delle entità di QAD
               cacheEntity = self.__cacheEntitySet.getEntity(geomEntity.layerId(), geomEntity.featureId)
               if cacheEntity is None:
                  cacheEntity = self.__cacheEntitySet.appendEntity(geomEntity) # la aggiungo alla cache
               qadGeom = cacheEntity.getQadGeom()

         if qadGeom is not None:         
            # la funzione ritorna una lista con 
            # (<minima distanza>
            #  <punto più vicino>
            #  <indice della geometria più vicina>
            #  <indice della sotto-geometria più vicina>
            #   se geometria chiusa è tipo polyline la lista contiene anche
            #  <indice della parte della sotto-geometria più vicina>
            #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
            # )
            result = getQadGeomClosestPart(qadGeom, point)
            atGeom = result[2]
            atSubGeom = result[3]
            g = getQadGeomAt(qadGeom, atGeom, atSubGeom)
            if self.__snapMode == QadSnapModeEnum.ONE_RESULT:
               gPart = getQadGeomPartAt(qadGeom, atGeom, atSubGeom, result[4])
   
            # snap statici
            staticSnapPoints = self.getStaticSnapPoints(g, gPart, isTemporaryGeom)
         else:
            staticSnapPoints = dict()
      else:
         staticSnapPoints = dict()
      
      # snap dinamici
      dynamicSnapPoints = self.getDynamicSnapPoints(g, gPart, point)

      allSnapPoints = staticSnapPoints
      for item in dynamicSnapPoints.items():
         allSnapPoints[item[0]] = item[1]
         
      # puntamento polare oppure angoli in aggiunta a polarAng
      if polarAng is not None or polarAddAngles is not None:
         # per tutti i punti di osnap selezionati per l'opzione polare e per per il punto corrente
         allSnapPoints[QadSnapTypeEnum.POLAR] = self.getOsnapPtAndLinesForPolar(point, polarAng, polarAngOffset, polarAddAngles)
         # calcolo le intersezioni delle linee polari e le aggiungo in allSnapPoints[QadSnapTypeEnum.INT]
         intPts = self.getIntPtsBetweenOSnapLinesForPolar()
         if len(intPts) > 0:
            if QadSnapTypeEnum.INT in allSnapPoints:
               for intPt in intPts:
                  self.__appendUniquePoint(allSnapPoints[QadSnapTypeEnum.INT], point) # senza duplicazione
            else:
               allSnapPoints[QadSnapTypeEnum.INT] = intPts
                              
      if self.__snapMode == QadSnapModeEnum.ONE_RESULT:
         # Viene restituito solo il punto più vicino
         result = self.getNearestPoints(point, allSnapPoints)
      elif self.__snapMode == QadSnapModeEnum.ALL_RESULTS:
         result = allSnapPoints # Vengono restituiti tutti i punti
      
      if excludePoints is not None:
         for p in excludePoints:
            self.__delPoint(p, result)
            
      return result


   #============================================================================
   # getStaticSnapPoints
   #============================================================================
   def getStaticSnapPoints(self, geom, gPart, isTemporaryGeom = False):
      """
      Data una geometria qad, la geometria di una parte della geometria qad, ottiene i punti di snap statici che non dipendono dalla 
      posizione del cursore.
      La parte, se esistente viene usata per i punti di tipo: END, MID, INT, APP
      Restituisce un dizionario di liste di punti di snap
      suddivisi per tipi di snap (es. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      - isTemporaryGeom flag che indica se geom é  un oggetto temporaneo che ancora non esiste      
      """
     
      result = dict()

      if (self.__snapType & QadSnapTypeEnum.DISABLE) or geom is None:
         return result
                  
      if self.__snapType & QadSnapTypeEnum.END:
         if gPart is None: 
            result[QadSnapTypeEnum.END] = self.getEndPoints(geom, QadVertexSearchModeEnum.ALL)
         else:
            result[QadSnapTypeEnum.END] = self.getEndPoints(gPart, QadVertexSearchModeEnum.ALL)
                     
      if self.__snapType & QadSnapTypeEnum.END_PLINE:
         result[QadSnapTypeEnum.END_PLINE] = self.getEndPoints(geom, QadVertexSearchModeEnum.ONLY_START_END)
         
      if self.__snapType & QadSnapTypeEnum.MID:
         if gPart is None: 
            result[QadSnapTypeEnum.MID] = self.getMidPoints(geom)
         else:
            result[QadSnapTypeEnum.MID] = self.getMidPoints(gPart)
            
      if self.__snapType & QadSnapTypeEnum.NOD:
         result[QadSnapTypeEnum.NOD] = self.getNodPoint(geom)
         
      if self.__snapType & QadSnapTypeEnum.QUA:
         if gPart is None: 
            result[QadSnapTypeEnum.QUA] = self.getQuaPoints(geom)
         else:
            result[QadSnapTypeEnum.QUA] = self.getQuaPoints(gPart)
         
      if self.__snapType & QadSnapTypeEnum.INT:
         if gPart is None or isTemporaryGeom: 
            result[QadSnapTypeEnum.INT] = self.getIntPoints(geom, isTemporaryGeom)
         else:
            result[QadSnapTypeEnum.INT] = self.getIntPoints(gPart, isTemporaryGeom)
            
      if self.__snapType & QadSnapTypeEnum.INS:
         result[QadSnapTypeEnum.INS] = self.getNodPoint(geom)
         
      if self.__snapType & QadSnapTypeEnum.APP:
         if gPart is None or isTemporaryGeom: 
            result[QadSnapTypeEnum.APP] = self.getIntPoints(geom, isTemporaryGeom)
         else:
            result[QadSnapTypeEnum.APP] = self.getIntPoints(gPart, isTemporaryGeom)
            
      if self.__snapType & QadSnapTypeEnum.CEN:
         if gPart is None: 
            result[QadSnapTypeEnum.CEN] = self.getCenPoint(geom)
         else:
            result[QadSnapTypeEnum.CEN] = self.getCenPoint(gPart)

      return result
 
 
   #============================================================================
   # getDynamicSnapPoints
   #============================================================================
   def getDynamicSnapPoints(self, geom, gPart, point):
      """
      Data una geometria qad, la geometria di una parte della geometria qad, ottiene i punti di snap dinamici che dipendono dalla 
      posizione del cursore (nel sistema di coordinate del canvas) o
      da __startPoint (nel sistema di coordinate canvas).
      La parte, se esistente viene usata per i punti di tipo: NEA, MID, INT, APP
      Resituisce un dizionario di liste di punti di snap
      suddivisi per tipi di snap (es. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """
           
      result = dict()

      if (self.__snapType & QadSnapTypeEnum.DISABLE):
         return result
      
      if self.__snapType & QadSnapTypeEnum.PER:
         if gPart is None: 
            result[QadSnapTypeEnum.PER] = self.getPerPoints(geom)
         else:
            result[QadSnapTypeEnum.PER] = self.getPerPoints(gPart)
            
      if self.__snapType & QadSnapTypeEnum.TAN:
         if gPart is None: 
            result[QadSnapTypeEnum.TAN] = self.getTanPoints(geom)
         else:
            result[QadSnapTypeEnum.TAN] = self.getTanPoints(gPart)
         
      if self.__snapType & QadSnapTypeEnum.NEA:
         if gPart is None: 
            result[QadSnapTypeEnum.NEA] = self.getNeaPoints(geom, point)
         else:
            result[QadSnapTypeEnum.NEA] = self.getNeaPoints(gPart, point)
            
      if self.__snapType & QadSnapTypeEnum.EXT:
         result[QadSnapTypeEnum.EXT] = self.getExtPoints(point)
         
      if self.__snapType & QadSnapTypeEnum.PAR:
         result[QadSnapTypeEnum.PAR] = self.getParPoints(point)
         
      if self.__snapType & QadSnapTypeEnum.PR:
         if geom is not None: 
            geomType = geom.whatIs()
         else:
            geomType = "";
         # se la geometria principale è multi... devo considerare la parte selezionata   
         if geomType == "MULTI_LINEAR_OBJ" or geomType == "MULTI_POLYGON":
            result[QadSnapTypeEnum.PR] = self.getProgressPoint(gPart, point)[0]
         else:         
            result[QadSnapTypeEnum.PR] = self.getProgressPoint(geom, point)[0]
         
      if self.__snapType & QadSnapTypeEnum.EXT_INT:
         result[QadSnapTypeEnum.EXT_INT] = self.getIntExtPoint(geom, point)
         
      if self.__snapType & QadSnapTypeEnum.PER_DEF:
         if gPart is None: 
            result[QadSnapTypeEnum.PER_DEF] = self.getNeaPoints(geom, point)
         else:
            result[QadSnapTypeEnum.PER_DEF] = self.getNeaPoints(gPart, point)
         
      if self.__snapType & QadSnapTypeEnum.TAN_DEF:
         if gPart is None:
            g = geom
         else:
            g = gPart
            
         if g is not None:
            # solo per geometria curva
            geomType = g.whatIs()
            if geomType == "ARC" or geomType == "CIRCLE" or geomType == "ELLIPSE_ARC" or geomType == "ELLIPSE":
               result[QadSnapTypeEnum.TAN_DEF] = self.getNeaPoints(g, point)
         
      return result


   #============================================================================
   # getEndPoints
   #============================================================================
   def getEndPoints(self, geom, VertexSearchMode = QadVertexSearchModeEnum.ALL):
      """
      Cerca i punti iniziali e finali di una geometria qad.
      - VertexSearchMode = modalità di ricerca dei punti finali
      Ritorna una lista di punti QgsPointXY
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
         if VertexSearchMode == QadVertexSearchModeEnum.ONLY_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL:
            self.__appendUniquePoint(result, geom.getStartPt()) # aggiungo senza duplicazione
            self.__appendUniquePoint(result, geom.getEndPt()) # aggiungo senza duplicazione
      elif geomType == "POLYLINE":
         if VertexSearchMode == QadVertexSearchModeEnum.ONLY_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL:
            self.__appendUniquePoint(result, geom.getStartPt()) # aggiungo senza duplicazione

         if VertexSearchMode == QadVertexSearchModeEnum.EXCLUDE_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL: 
            i = 1 # secondo oggetto lineare della geometria polilinea
            while i < geom.qty():
               linearObject = geom.getLinearObjectAt(i)
               self.__appendUniquePoint(result, linearObject.getStartPt()) # aggiungo senza duplicazione
               i = i + 1
         
         if VertexSearchMode == QadVertexSearchModeEnum.ONLY_START_END or \
            VertexSearchMode == QadVertexSearchModeEnum.ALL:
            self.__appendUniquePoint(result, geom.getEndPt()) # aggiungo senza duplicazione

      return result


   #============================================================================
   # getMidPoints
   #============================================================================
   def getMidPoints(self, geom):
      """
      Cerca i punti medi dei segmenti di una geometria qad.
      Ritorna una lista di punti QgsPointXY
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "LINE" or geomType == "ARC" or geomType == "ELLIPSE_ARC":
         self.__appendUniquePoint(result, QgsPointXY(geom.getMiddlePt())) # aggiungo senza duplicazione
      elif geomType == "POLYLINE":
         i = 0
         while i < geom.qty():
            linearObject = self.getLinearObjectAt(i)
            self.__appendUniquePoint(result, QgsPointXY(linearObject.getMiddlePt())) # aggiungo senza duplicazione
            i = i + 1
            
      return result


   #============================================================================
   # getCenPoint
   #============================================================================
   def getCenPoint(self, geom):
      """
      Cerca i punti centrali di archi, cerchi, archi di ellisse, ellissi presenti nella geometria qad.
      Ritorna una lista di punti QgsPointXY
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "ARC" or geomType == "CIRCLE" or geomType == "ELLIPSE" or geomType == "ELLIPSE_ARC":
         self.__appendUniquePoint(result, geom.center) # aggiungo senza duplicazione
         
      elif geomType == "POLYLINE":
         i = 0
         while i < geom.qty():
            linearObject = geom.getLinearObjectAt(i)
            result.extend(self.getCenPoint(linearObject))
            i = i + 1

      return result


   #============================================================================
   # getNodPoint
   #============================================================================
   def getNodPoint(self, geom):
      """
      Cerca il punto di inserimento di un punto qad.
      Ritorna una lista di punti QgsPointXY
      """
      result = []

      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "POINT":
         self.__appendUniquePoint(result, QgsPointXY(geom)) # aggiungo senza duplicazione
      elif geomType == "MULTI_POINT":
         i = 0
         while i < geom.qty():
            self.__appendUniquePoint(result, self.getPointAt(i)) # aggiungo senza duplicazione
            i = i + 1

      return result


   #============================================================================
   # getQuaPoints
   #============================================================================
   def getQuaPoints(self, geom):
      """
      Cerca i punti quadrante della geometria qad.
      Ritorna una lista di punti QgsPointXY
      """
      result = []
      
      if geom is None:
         return result

      geomType = geom.whatIs()
      if geomType == "ARC" or geomType == "CIRCLE" or geomType == "ELLIPSE" or geomType == "ELLIPSE_ARC":
         points = geom.getQuadrantPoints()
         for point in points:
            if points is not None: # perchè l'arco di ellisse ritorna i punti quadrante nulli se non sono nell'arco 
               self.__appendUniquePoint(result, point) # senza duplicazione

      return result


   #============================================================================
   # getIntPoints
   #============================================================================
   def getIntPoints(self, geom, isTemporaryGeom = False):
      """
      Cerca i punti di intersezione di una geometria qad con altre geometrie sui layer __snapLayers.
      - isTemporaryGeom flag che indica se geom é un oggetto temporaneo che ancora non esiste
      Ritorna una lista di punti QgsPointXY
      """
      result = []

      if geom is None:
         return result
      
      geomBoundingBoxCache = QadGeomBoundingBoxCache(geom)
      boundingBox = geomBoundingBoxCache.getTotalBoundingBox()
     
      for iLayer in self.__snapLayers: # ciclo sui layer da controllare
         if (iLayer.type() == QgsMapLayer.VectorLayer):
            iLayerCRS = iLayer.crs()
            coordTransform = QgsCoordinateTransform(self.__snapPointCRS, iLayerCRS, QgsProject.instance()) # trasformo in coord ilayer
            iLayerBoundingBox = coordTransform.transformBoundingBox(boundingBox)
            
            feature = QgsFeature()
            # cerco le entità che intersecano il rettangolo
            # fetchAttributes, fetchGeometry, rectangle, useIntersect             
            for feature in iLayer.getFeatures(qad_utils.getFeatureRequest([], True, iLayerBoundingBox, True)):
               g2 = fromQgsGeomToQadGeom(feature.geometry(), iLayerCRS) # ottengo una geometria di qad
               if geom.whatIs() == g2.whatIs() and geom.equals(g2): continue # salta se stessa
               
               intersectionPoints = QadIntersections.twoGeomObjects(g2, geom, geomBoundingBoxCache)
               for point in intersectionPoints:
                  self.__appendUniquePoint(result, point) # senza duplicazione
                     
      if isTemporaryGeom:
         intersectionPoints = QadIntersections.twoGeomObjects(geom, geom, geomBoundingBoxCache)
         for point in intersectionPoints:
            self.__appendUniquePoint(result, point) # senza duplicazione

      # lista di geometria non ancora esistenti ma da contare per i punti di osnap (in map coordinates)
      for tmpGeometry in self.tmpGeometries:
         intersectionPoints = QadIntersections.twoGeomObjects(tmpGeometry, geom, geomBoundingBoxCache)
         for point in intersectionPoints:
            self.__appendUniquePoint(result, point) # senza duplicazione
         
      return result
            

   #============================================================================
   # Inizio punti dinamici
   #============================================================================

            
   #============================================================================
   # getPerPoints
   #============================================================================
   def getPerPoints(self, geom):
      """
      Cerca il punto proiezione perpendicolare di self.__startPoint 
      (espresso in __snapPointCRS) sul lato di geom più vicino a point.
      Ritorna una lista di punti QgsPointXY 
      """         
      result = []
      
      if geom is None:
         return result
      
      if self.__startPoint is None:
         return result
      
      PerpendicularPoints = QadPerpendicularity.fromPointToBasicGeomObjectExtensions(self.__startPoint, geom)
      for PerpendicularPoint in PerpendicularPoints:
         self.__appendUniquePoint(result, PerpendicularPoint) # senza duplicazione

      return result


   #============================================================================
   # getTanPoints
   #============================================================================
   def getTanPoints(self, geom):
      """
      Cerca i punti di un oggetto che sono tangenti alla retta passante per self.__startPoint 
      (espresso in __snapPointCRS).
      Ritorna una lista di punti QgsPointXY
      """
      result = []
      
      if geom is None:
         return result
      
      if self.__startPoint is None:
         return result
      
      result = []
      tangencyPoints = QadTangency.fromPointToBasicGeomObject(self.__startPoint, geom)
      for tangencyPoint in tangencyPoints:
         self.__appendUniquePoint(result, tangencyPoint) # senza duplicazione

      return result


   #============================================================================
   # getNeaPoints
   #============================================================================
   def getNeaPoints(self, geom, point):
      """
      Cerca il punto di un oggetto che é più vicino a point.
      Ritorna una lista di punti QgsPointXY
      """
      if geom is None: return []

      # la funzione ritorna una lista con 
      # (<minima distanza>
      #  <punto più vicino>
      #  <indice della geometria più vicina>
      #  <indice della sotto-geometria più vicina>
      #   se geometria chiusa è tipo polyline la lista contiene anche
      #  <indice della parte della sotto-geometria più vicina>
      #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
      # )
      result = getQadGeomClosestPart(geom, point)
      closestPoint = result[1]
      result = []
      self.__appendUniquePoint(result, closestPoint) # senza duplicazione
      
      return result


   #============================================================================
   # toggleExtLinearObj
   #============================================================================
   def toggleExtLinearObj(self, linearObj):
      """
      Aggiunge un oggetto lineare (QadLine o QadArc o QadEllipseArc) per la ricerca di punti con modalità EXT (estensione)
      se non ancora inserito in lista altrimenti lo rimuove dalla lista
      """
      geomType = linearObj.whatIs()
      if geomType == "ARC" or geomType == "ELLIPSE_ARC" or geomType == "LINE":
         # verifico che non ci sia già
         i = 0
         for iObj in self.__extLinearObjs:
            if geomType == iObj.whatIs():
               if geomType == "LINE":
                  if linearObj.equals(iObj): # uguali geometricamente (NON conta il verso)
                     # se esiste di già lo rimuovo
                     del self.__extLinearObjs[i]
                     return
               elif linearObj == iObj:
                  # se esiste di già lo rimuovo
                  del self.__extLinearObjs[i]
                  return
            i = i + 1

         # se non esiste ancora lo aggiungo
         self.__extLinearObjs.append(linearObj)
            

   def removeExtLinearObjs(self):
      """
      Elimina tutte gli oggetti lineari per la ricerca di punti con modalità EXT (estensione)
      """
      del self.__extLinearObjs[:] # svuoto la lista

   def getExtLinearObjs(self):
      return self.__extLinearObjs


   def getExtPoints(self, point):
      """
      Cerca i punti sui prolungamenti delle linee memorizzate nella lista __extLinearObjs.
      - point é un QgsPointXY
      Ritorna una lista di punti QgsPointXY
      """
      result = []
      
      for g in self.__extLinearObjs:
         ExtPoints = QadPerpendicularity.fromPointToBasicGeomObjectExtensions(point, g)
         for ExtPoint in ExtPoints:
            if qad_utils.getDistance(point, ExtPoint) <= self.__toleranceExtParlines:
               self.__appendUniquePoint(result, ExtPoint) # senza duplicazione

      return result

      
   #============================================================================
   # getParPoints
   #============================================================================      
   def toggleParLine(self, line):
      """
      Aggiunge una linea per la ricerca di punti con modalità PAR (parallela)
      se non ancora inserita in lista altrimenti la rimuove dalla lista
      """
      """
      Aggiunge una linea per la ricerca di punti con modalità EXT o PAR
      se non ancora inserita in lista altrimenti la rimuove dalla lista
      """
      if line.whatIs() != "LINE": return
      
      # verifico che non ci sia già
      i = 0
      for iObj in self.__parLines:
         if line.equals(iObj): # uguali geometricamente (NON conta il verso)
            # se esiste di già lo rimuovo
            del self.__parLines[i]
            return
         i = i + 1

      # se non esiste ancora lo aggiungo
      self.__parLines.append(line)
      

   def removeParLines(self):
      """
      Elimina tutte le linee per la ricerca di punti con modalità PAR (parallela)
      """
      del self.__parLines[:] # svuoto la lista

   def getParLines(self):
      return self.__parLines
   
   
   def getParPoints(self, point):
      """
      Cerca i punti sulle rette parallele alle linee memorizzate nella lista __partLines
      che passano per __startPoint e che sono più vicino a point.
      N.B. __parLines, __startPoint e point vanno espressi nello stesso sistema di coordinate
      - line é una lista di 2 punti
      - point é un QgsPointXY
      Ritorna una lista di punti QgsPointXY
      """
      result = []
      
      if (self.__startPoint is None) or len(self.__parLines) == 0:
         return result
            
      p2 = QgsPointXY()
     
      for line in self.__parLines:
         pt1 = line.getStartPt()
         pt2 = line.getEndPt()
         diffX = pt2.x() - pt1.x()
         diffY = pt2.y() - pt1.y()
                                                  
         if diffX == 0: # se la retta passante per pt1 e pt2 é verticale
            parPoint = QgsPointXY(self.__startPoint.x(), point.y())
         elif diffY == 0: # se la retta passante per pt1 e pt2 é orizzontle
            parPoint = QgsPointXY(point.x(), self.__startPoint.y())
         else:
            # Calcolo l'equazione della retta passante per __startPoint con coefficente angolare noto
            p2.setX(self.__startPoint.x() + diffX)
            p2.setY(self.__startPoint.y() + diffY)
            parPoint = qad_utils.getPerpendicularPointOnInfinityLine(self.__startPoint, p2, point)

         if qad_utils.getDistance(point, parPoint) <= self.__toleranceExtParlines:
            self.__appendUniquePoint(result, parPoint) # senza duplicazione

      return result


   #============================================================================
   # getProgressPoint
   #============================================================================
   def setProgressDistance(self, progressDistance):
      """
      Setta la distanza progressiva dall'inizio nel sistema __snapPointCRS 
      per la ricerca con modalità PR (progressiva)
      """
      self.__progressDistance = progressDistance


   def getProgressDistance(self,):
      return self.__progressDistance


   def getProgressPoint(self, geom, point):
      """
      Cerca il punto sulla geometria ad un certa distanza dal vertice più vicino al punto
      (se la distanza >=0 significa verso dall'inizio alla fine della linea,
      se la distanza < 0 significa verso dalla fine all'inizio della linea.
      Ritorna una lista di punti QgsPointXY + una lista di coefficienti angolari dei segmenti
      su cui ricadono i punti
      """
      result = [[],[]]
      if geom is None:
         return result     

      geomType = geom.whatIs()
      if geomType != "LINE" and geomType != "ARC" and geomType != "ELLIPSE_ARC" and geomType != "POLYLINE":
         return result
      
      g = geom.copy()
      ProgressPoints = []
      segmentAngles = []
     
      if self.__progressDistance < 0:
         g.reverse()
         progressDistance = -self.__progressDistance
      else:
         progressDistance = self.__progressDistance

      # la funzione ritorna una lista con 
      # (<minima distanza>
      # <punto del vertice più vicino>
      # <indice della geometria più vicina>
      # <indice della sotto-geometria più vicina>
      # <indice della parte della sotto-geometria più vicina>
      # <indice del vertice più vicino>
      result = getQadGeomClosestVertex(g, point)
      iVertex = result[5]
      
      lengthFromStart = 0
      if geomType == "POLYLINE":         
         # calcolo la distanza del vertice dall'inizio della geometria
         for i in range(0, iVertex, 1):
            lengthFromStart = lengthFromStart + g.getLinearObjectAt(i).length()
               
         delta = (lengthFromStart + progressDistance) - g.length()
         # la funzione sposta il punto finale di una distanza delta allungando (se delta > 0) o accorciando (se delta < 0) la polilinea
         if g.lengthen_delta(False, delta) == True:
            linearObject = g.getLinearObjectAt(-1) # ultimo oggetto lineare
            ProgressPoints.append(QgsPointXY(linearObject.getEndPt()))
            if self.__progressDistance < 0:
               linearObject.reverse()
               segmentAngles.append(linearObject.getTanDirectionOnStartPt())
            else:
               segmentAngles.append(linearObject.getTanDirectionOnEndPt())
      else:
         # calcolo la distanza del vertice dall'inizio della geometria
         if iVertex == 1: # punto finale
            lengthFromStart = g.length()
         delta = (lengthFromStart + progressDistance) - g.length()
         
         # la funzione sposta il punto finale di una distanza delta allungando (se delta > 0) o accorciando (se delta < 0) la polilinea
         if g.lengthen_delta(False, delta) == True:
            ProgressPoints.append(QgsPointXY(g.getEndPt()))
            if self.__progressDistance < 0:
               g.reverse()
               segmentAngles.append(g.getTanDirectionOnStartPt())
            else:
               segmentAngles.append(g.getTanDirectionOnEndPt())
      
      return (ProgressPoints, segmentAngles)


   #============================================================================
   # toggleIntExtLinearObj
   #============================================================================      
   def toggleIntExtLinearObj(self, geomEntity, point):
      """
      Aggiunge un oggetto lineare (QadLine o QadArc o QadEllipseArc) per la ricerca di punti con modalità EXT_INT (intersezione su estensione)
      se non ancora inserita altrimenti la rimuove dalla lista
      """
      # usato solo per snap EXT_INT
      if not (self.__snapType & QadSnapTypeEnum.EXT_INT):
         return

      if type(geomEntity) == QgsGeometry: # se è una geometria di QGIS
         qadGeom = fromQgsGeomToQadGeom(geomEntity)
      else: # è un'entità di QAD
         # uso la cache delle entità di QAD
         cacheEntity = self.__cacheEntitySet.getEntity(geomEntity.layerId(), geomEntity.featureId)
         if cacheEntity is None:
            cacheEntity = self.__cacheEntitySet.appendEntity(geomEntity) # la aggiungo alla cache
         qadGeom = cacheEntity.getQadGeom()

      # la funzione ritorna una lista con 
      # (<minima distanza>
      #  <punto più vicino>
      #  <indice della geometria più vicina>
      #  <indice della sotto-geometria più vicina>
      #   se la sotto-geometria è tipo polyline la lista contiene anche
      #  <indice della parte della sotto-geometria più vicina>
      #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
      # )
      geomType = qadGeom.whatIs()
      result = getQadGeomClosestPart(qadGeom, point)
      if len(result) > 4: # se la funzione restituisce il numero della parte
         linearObj = getQadGeomPartAt(qadGeom, result[2], result[3], result[4])
         geomType = linearObj.whatIs()
      else:
         linearObj = geom

      if geomType != "LINE" and geomType != "ARC" and geomType != "ELLIPSE_ARC": return
      
      # se non é stato selezionato alcun oggetto lineare lo aggiungo 
      if len(self.__intExtLinearObjs) == 0:
         self.__intExtLinearObjs.append(linearObj.copy())
      else:
         if geomType == self.__intExtLinearObjs[0].whatIs():
            if geomType == "LINE":
               if linearObj.equals(self.__intExtLinearObjs[0]): # uguali geometricamente (NON conta il verso)
                  # se esiste di già lo rimuovo
                  self.removeIntExtLinearObj()
                  return
            elif linearObj == self.__intExtLinearObjs[0]:
               # se esiste di già lo rimuovo
               self.removeIntExtLinearObj()
               return


   def removeIntExtLinearObj(self):
      """
      Elimina 'oggetto lineare per la ricerca di punti con modalità EXT_INT (intersezione su estensione)
      """
      del self.__intExtLinearObjs[:] # svuoto la lista


   def getIntExtLinearObjs(self):
      return self.__intExtLinearObjs

   
   def getIntExtPoint(self, geom, point):
      """
      Cerca il punto di intersezione tra la geometria e un oggetto lineare memorizzato in __intExtLinearObjs
      Ritorna una lista di punti QgsPointXY
      """
      if geom is None: return []
      
      # se non é stato selezionato alcun oggetto lineare 
      if len(self.__intExtLinearObjs) == 0: return []

      # la funzione ritorna una lista con 
      # (<minima distanza>
      #  <punto più vicino>
      #  <indice della geometria più vicina>
      #  <indice della sotto-geometria più vicina>
      #   se geometria chiusa è tipo polyline la lista contiene anche
      #  <indice della parte della sotto-geometria più vicina>
      #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
      # )
      result = getQadGeomClosestPart(geom, point)
      g = getQadGeomPartAt(geom, result[2], result[3], result[4])
      
      intExtPoints = QadIntersections.twoBasicGeomObjectExtensions(g, self.__intExtLinearObjs[0])

      result = []
      for intExtPoint in intExtPoints:
         self.__appendUniquePoint(result, intExtPoint) # senza duplicazione

      return result


   #============================================================================
   # utiliy functions
   #============================================================================
   def __appendUniquePoint(self, pointList, point):
      """
      Aggiunge un punto alla lista verificando che non sia già presente.
      Resituisce True se l'inserimento é avvenuto False se il punto c'era già.
      """
      # Si assume che la lista sia ordinata, l'inserimento avverà mantenendo l'ordinamento
      lo = 0
      hi = len(pointList)
      while lo < hi:
         mid = (lo + hi) // 2 # digits after the decimal point are removed
         
         if self.__comparePts(pointList[mid], point) == -1: lo = mid+1
         else: hi = mid

      if lo != len(pointList) and self.__comparePts(pointList[lo], point) == 0: # il punto c'era già
         return False
      pointList.insert(lo, point)
      return True
      
      #return qad_utils.appendUniquePointToList(pointList, _point)

   
   #============================================================================
   # __comparePts
   #============================================================================
   def __comparePts(self, p1, p2):
      # compara 2 punti, ritorna 0 se sono uguali, -1 se il primo < del secondo, 1 se il primo > del secondo 
      if p1.x() > p2.x(): return 1
      if p1.x() < p2.x(): return -1
      # le x sono uguali quindi verifici le y
      if p1.y() > p2.y(): return 1
      if p1.y() < p2.y(): return -1
      return 0 # numeri uguali
   
   
   #============================================================================
   # getNearestPoints
   #============================================================================
   def getNearestPoints(self, point, SnapPoints, tolerance = 0):
      """
      Ritorna una lista con il primo elemento che é il tipo di snap e 
      il secondo elemento é il punto più vicino a point.
      SnapPoints é un dizionario di liste di punti di snap
      suddivisi per tipi di snap (es. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """   
      result = dict()   
      minDist = sys.float_info.max
      
      if tolerance == 0: # solo il punto più vicino
         for item in SnapPoints.items():
            # escludo NEA e POLAR che tratto dopo
            if (item[0] != QadSnapTypeEnum.NEA and item[0] != QadSnapTypeEnum.POLAR) and (item[1] is not None):
               for pt in item[1]:
                  dist = qad_utils.getDistance(point, pt)
                  if dist < minDist:
                     minDist = dist
                     snapType = item[0]
                     NearestPoint = pt

         # se il punto trovato é più distante di <__distToExcludeNea> allora considero anche
         # eventuali punti NEA
         if minDist > self.__distToExcludeNea:
            # se é stato selezionato lo snap di tipo NEA
            if QadSnapTypeEnum.NEA in SnapPoints.keys():
               items = SnapPoints[QadSnapTypeEnum.NEA]
               if (items is not None):
                  for pt in items:
                     dist = qad_utils.getDistance(point, pt)
                     if dist < minDist:
                        minDist = dist
                        snapType = QadSnapTypeEnum.NEA
                        NearestPoint = pt

         # se il punto trovato é più distante di <__distToExcludeNea> allora considero anche
         # eventuali punti POLAR
         if minDist > self.__distToExcludeNea:            
            # se é stato selezionato lo snap di tipo POLAR
            if QadSnapTypeEnum.POLAR in SnapPoints.keys():
               items = SnapPoints[QadSnapTypeEnum.POLAR]
               if (items is not None):
                  for pt in items:
                     dist = qad_utils.getDistance(point, pt)
                     if dist < minDist:
                        minDist = dist
                        snapType = QadSnapTypeEnum.POLAR
                        NearestPoint = pt

         if minDist != sys.float_info.max: # trovato
            result[snapType] = [NearestPoint]

      else:
         nearest = self.getNearestPoints(point, SnapPoints) # punto più vicino
         dummy = nearest.items()
         dummy = dummy[0]
         NearestPoint = dummy[1]
         
         for item in SnapPoints.items():
            NearestPoints = []
            for pt in item[1]:
               dist = qad_utils.getDistance(NearestPoint, pt)
               if dist <= tolerance:
                  NearestPoints.append(pt)

            if len(NearestPoints) > 0:
               snapType = item[0]             
               result[snapType] = NearestPoint
      
      return result


   def __delPoint(self, point, SnapPoints):
      """
      Cancella dalla lista SnapPoints il punto point (se esiste) 
      SnapPoints é un dizionario di liste di punti di snap
      suddivisi per tipi di snap (es. {END : [pt1 .. ptn] MID : [pt1 .. ptn]})
      """   
      for item in SnapPoints.items():
         i = 0
         for pt in item[1]:
            if pt == point:
               del item[1][i]
            i = i + 1


   #============================================================================
   # getPolarCoord
   #============================================================================
   def getPolarCoord(self, startPoint, point, polarAng, polarAngOffset, polarAddAngles):
      result = []

      angle = qad_utils.getAngleBy2Pts(startPoint, point)
      offsetAngle = angle - polarAngOffset
      value = math.modf(offsetAngle / polarAng) # ritorna una lista -> (<parte decimale> <parte intera>)
      if value[0] >= 0.5: # prendo intervallo successivo
         offsetAngle = (value[1] + 1) * polarAng
      else:
         offsetAngle = value[1] * polarAng
      offsetAngle  = offsetAngle + polarAngOffset

      dist = qad_utils.getDistance(startPoint, point)
      pt2 = qad_utils.getPolarPointByPtAngle(startPoint, offsetAngle, dist)

      polarPt = qad_utils.getPerpendicularPointOnInfinityLine(startPoint, pt2, point)
      if qad_utils.getDistance(polarPt, point) <= self.__toleranceExtParlines:
         self.__appendUniquePoint(result, polarPt) # senza duplicazione
         
      if polarAddAngles is not None and len(polarAddAngles) > 0:
         for polarAddAngle in polarAddAngles:
            polarPt = qad_utils.getPolarPointByPtAngle(startPoint, polarAddAngle + polarAngOffset, dist)
            if qad_utils.getDistance(polarPt, point) <= self.__toleranceExtParlines:
               self.__appendUniquePoint(result, polarPt) # senza duplicazione
         
      return result


#============================================================================
# funzioni generiche
#============================================================================


#===============================================================================
# str2snapTypeEnum
#===============================================================================
def str2snapTypeEnum(s):
   """
   Ritorna la conversione di una stringa in una combinazione di tipi di snap
   oppure -1 se non ci sono snap indicati.
   """
   snapType = QadSnapTypeEnum.NONE
   snapTypeStrList = s.strip().split(",")
   for snapTypeStr in snapTypeStrList:
      snapTypeStr = snapTypeStr.strip().upper()
      
      # "NES" nessuno snap
      if snapTypeStr == QadMsg.translate("Snap", "NONE") or snapTypeStr == "_NONE":
         return QadSnapTypeEnum.NONE
      # "FIN" punti finali di ogni segmento
      elif snapTypeStr == QadMsg.translate("Snap", "END") or snapTypeStr == "_END":
         snapType = snapType | QadSnapTypeEnum.END
      # "FIN_PL" punti finali dell'intera polilinea
      elif snapTypeStr == QadMsg.translate("Snap", "END_PL") or snapTypeStr == "_END_PL":
         snapType = snapType | QadSnapTypeEnum.END_PLINE
      # "MED" punto medio
      elif snapTypeStr == QadMsg.translate("Snap", "MID") or snapTypeStr == "_MID":
         snapType = snapType | QadSnapTypeEnum.MID
      # "CEN" centro (centroide)
      elif snapTypeStr == QadMsg.translate("Snap", "CEN") or snapTypeStr == "_CEN":
         snapType = snapType | QadSnapTypeEnum.CEN
      # "NOD" oggetto punto
      elif snapTypeStr == QadMsg.translate("Snap", "NOD") or snapTypeStr == "_NOD":
         snapType = snapType | QadSnapTypeEnum.NOD
      # "QUA" punto quadrante
      elif snapTypeStr == QadMsg.translate("Snap", "QUA") or snapTypeStr == "_QUA":
         snapType = snapType | QadSnapTypeEnum.QUA
      # "INT" intersezione
      elif snapTypeStr == QadMsg.translate("Snap", "INT") or snapTypeStr == "_INT":
         snapType = snapType | QadSnapTypeEnum.INT
      # "INS" punto di inserimento
      elif snapTypeStr == QadMsg.translate("Snap", "INS") or snapTypeStr == "_INS":
         snapType = snapType | QadSnapTypeEnum.INS
      # "PER" punto perpendicolare
      elif snapTypeStr == QadMsg.translate("Snap", "PER") or snapTypeStr == "_PER":
         snapType = snapType | QadSnapTypeEnum.PER
      # "TAN" tangente
      elif snapTypeStr == QadMsg.translate("Snap", "TAN") or snapTypeStr == "_TAN":
         snapType = snapType | QadSnapTypeEnum.TAN
      # "VIC" punto più vicino
      elif snapTypeStr == QadMsg.translate("Snap", "NEA") or snapTypeStr == "_NEA":
         snapType = snapType | QadSnapTypeEnum.NEA
      # "APP" intersezione apparente
      elif snapTypeStr == QadMsg.translate("Snap", "APP") or snapTypeStr == "_APP":
         snapType = snapType | QadSnapTypeEnum.APP
      # "EST" Estensione
      elif snapTypeStr == QadMsg.translate("Snap", "EXT") or snapTypeStr == "_EXT":
         snapType = snapType | QadSnapTypeEnum.EXT
      # "PAR" Parallelo
      elif snapTypeStr == QadMsg.translate("Snap", "PAR") or snapTypeStr == "_PAR":
         snapType = snapType | QadSnapTypeEnum.PAR         
      # se inizia per "PR" distanza progressiva
      elif snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0 or \
           snapTypeStr.find("_PR") == 0:
         # la parte successiva PR può essere vuota o numerica
         if snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0:
            param = snapTypeStr[len(QadMsg.translate("Snap", "PR")):]
         else:
            param = snapTypeStr[len("_PR"):]
         if len(param) == 0 or qad_utils.str2float(param) is not None:
            snapType = snapType | QadSnapTypeEnum.PR
      # "EST_INT" intersezione su estensione
      elif snapTypeStr == QadMsg.translate("Snap", "EXT_INT") or snapTypeStr == "_EXT_INT":
         snapType = snapType | QadSnapTypeEnum.EXT_INT
   
   return snapType if snapType != QadSnapTypeEnum.NONE else -1


#===============================================================================
# snapTypeEnum2Str
#===============================================================================
def snapTypeEnum2Str(snapType):
   """
   Ritorna la conversione di un tipo di snap in una stringa.
   """
   # "FIN" punti finali di ogni segmento
   if snapType == QadSnapTypeEnum.END:
      return QadMsg.translate("Snap", "END")
   # "FIN_PL" punti finali dell'intera polilinea
   elif snapType == QadSnapTypeEnum.END_PLINE:
      return QadMsg.translate("Snap", "END_PL")
   # "MED" punto medio
   elif snapType == QadSnapTypeEnum.MID:
      return QadMsg.translate("Snap", "MID")
   # "CEN" centro (centroide)
   elif snapType == QadSnapTypeEnum.CEN:
      return QadMsg.translate("Snap", "CEN")
   # "NOD" oggetto punto
   elif snapType == QadSnapTypeEnum.NOD:
      return QadMsg.translate("Snap", "NOD")
   # "QUA" punto quadrante
   elif snapType == QadSnapTypeEnum.QUA:
      return QadMsg.translate("Snap", "QUA")
   # "INT" intersezione
   elif snapType == QadSnapTypeEnum.INT:
      return QadMsg.translate("Snap", "INT")
   # "INS" punto di inserimento
   elif snapType == QadSnapTypeEnum.INS:
      return QadMsg.translate("Snap", "INS")
   # "PER" punto perpendicolare
   elif snapType == QadSnapTypeEnum.PER:
      return QadMsg.translate("Snap", "PER")
   # "TAN" tangente
   elif snapType == QadSnapTypeEnum.TAN:
      return QadMsg.translate("Snap", "TAN")
   # "VIC" punto più vicino
   elif snapType == QadSnapTypeEnum.NEA:
      return QadMsg.translate("Snap", "NEA")
   # "APP" intersezione apparente
   elif snapType == QadSnapTypeEnum.APP:
      return QadMsg.translate("Snap", "APP")
   # "EST" Estensione
   elif snapType == QadSnapTypeEnum.EXT:
      return QadMsg.translate("Snap", "EXT")
   # "PAR" Parallelo
   elif snapType == QadSnapTypeEnum.PAR:
      return QadMsg.translate("Snap", "PAR")
   # "PR" distanza progressiva
   elif snapType == QadSnapTypeEnum.PR:
      return QadMsg.translate("Snap", "PR")
   # "EST_INT" intersezione su estensione
   elif snapType == QadSnapTypeEnum.EXT_INT:
      return QadMsg.translate("Snap", "EXT_INT")
   
   return ""


#===============================================================================
# snapTypeEnum2Descr
#===============================================================================
def snapTypeEnum2Descr(snapType):
   """
   Ritorna la conversione di un tipo di snap in una stringa descrittiva.
   """
   # "FIN" punti finali di ogni segmento
   if snapType == QadSnapTypeEnum.END:
      return QadMsg.translate("Snap", "Segment end point")
   # "FIN_PL" punti finali dell'intera polilinea
   elif snapType == QadSnapTypeEnum.END_PLINE:
      return QadMsg.translate("Snap", "Polyline end point")
   # "MED" punto medio
   elif snapType == QadSnapTypeEnum.MID:
      return QadMsg.translate("Snap", "Middle point")
   # "CEN" centro (centroide)
   elif snapType == QadSnapTypeEnum.CEN:
      return QadMsg.translate("Snap", "Center point")
   # "NOD" oggetto punto
   elif snapType == QadSnapTypeEnum.NOD:
      return QadMsg.translate("Snap", "Node")
   # "QUA" punto quadrante
   elif snapType == QadSnapTypeEnum.QUA:
      return QadMsg.translate("Snap", "Quadrant")
   # "INT" intersezione
   elif snapType == QadSnapTypeEnum.INT:
      return QadMsg.translate("Snap", "Intersection")
   # "INS" punto di inserimento
   elif snapType == QadSnapTypeEnum.INS:
      return QadMsg.translate("Snap", "Insertion point")
   # "PER" punto perpendicolare
   elif snapType == QadSnapTypeEnum.PER:
      return QadMsg.translate("Snap", "Perpendicular")
   # "TAN" tangente
   elif snapType == QadSnapTypeEnum.TAN:
      return QadMsg.translate("Snap", "Tangent")
   # "VIC" punto più vicino
   elif snapType == QadSnapTypeEnum.NEA:
      return QadMsg.translate("Snap", "Near")
   # "APP" intersezione apparente
   elif snapType == QadSnapTypeEnum.APP:
      return QadMsg.translate("Snap", "Apparent intersection")
   # "EST" Estensione
   elif snapType == QadSnapTypeEnum.EXT:
      return QadMsg.translate("Snap", "Extension")
   # "PAR" Parallelo
   elif snapType == QadSnapTypeEnum.PAR:
      return QadMsg.translate("Snap", "Parallel")
   # "PR" distanza progressiva
   elif snapType == QadSnapTypeEnum.PR:
      return QadMsg.translate("Snap", "Progressive distance")
   # "EST_INT" intersezione su estensione
   elif snapType == QadSnapTypeEnum.EXT_INT:
      return QadMsg.translate("Snap", "Intersection on extension")
   
   return ""


#===============================================================================
# str2snapParam
#===============================================================================
def str2snapParams(s):
   """
   Ritorna la conversione di una stringa in una lista di parametri per i tipi di snap
   """
   params = []
   snapTypeStrList = s.strip().split(",")
   for snapTypeStr in snapTypeStrList:
      snapTypeStr = snapTypeStr.strip().upper()
      # se inizia per "PR" distanza progressiva
      if snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0 or \
         snapTypeStr.find("_PR") == 0:
         # la parte successiva PR può essere vuota o numerica
         if snapTypeStr.find(QadMsg.translate("Snap", "PR")) == 0:
            param = qad_utils.str2float(snapTypeStr[len(QadMsg.translate("Snap", "PR")):]) # fino alla fine della stringa
         else:
            param = qad_utils.str2float(snapTypeStr[len("_PR"):]) # fino alla fine della stringa
         if param is not None:
            params.append([QadSnapTypeEnum.PR, param])         

   return params
