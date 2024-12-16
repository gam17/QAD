# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per join tra elementi lineari
 
                              -------------------
        begin                : 2019-09-04
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


from .qad_msg import QadMsg
from .qad_variables import QadVariables
from .qad_geom_relations import *
from .qad_layer import createMemoryLayer
from .qad_polyline import *


# ============================================================================
# join2polyline
# ============================================================================
def join2polyline(polyline, polylineToJoinTo, toleranceDist = None, mode = 1):
   """
   la funzione unisce la polilinea <polyline> con un'altra polilinea <polylineToJoinTo> secondo la modalità <mode>.
   In caso di successo ritorna True altrimenti False.
   <polyline> = polilinea da unire (sarà modificata)
   <polylineToJoinTo> = polilinea con cui unirsi
   <toleranceDist> = distanza di tolleranza perché 2 punti siano considerati coincidenti  
   <mode> = Imposta il metodo di unione (usato se toleranceDist > 0):
            1 -> Estendi;  Consente di unire polilinee selezionate estendendo o tagliando 
                           i segmenti nei punti finali più vicini.
            2 -> Aggiungi; Consente di unire polilinee selezionate aggiungendo un segmento 
                           retto tra i punti finali più vicini.
            3 -> Entrambi;Consente di unire polilinee selezionate estendendo o tagliando, se possibile.
                 In caso contrario, consente di unire polilinee selezionate aggiungendo 
                 un segmento retto tra i punti finali più vicini. 
   """
   if toleranceDist is None:
      myToleranceDist = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myToleranceDist = toleranceDist
      
   # cerco il punto più vicino al punto iniziale della polilinea
   ptToJoin = polyline.getStartPt()
   isStartPt = True
   minDist = sys.float_info.max
   # considero il punto iniziale della polilinea a cui unirsi
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getStartPt())
   if dist < minDist:
      isStartPtToJoinTo = True
      minDist = dist
   # considero il punto finale della polilinea a cui unirsi
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getEndPt())
   if dist < minDist:
      isStartPtToJoinTo = False
      minDist = dist

   # cerco il punto più vicino al punto finale della polilinea
   ptToJoin = polyline.getEndPt()
   # considero il punto iniziale della polilinea a cui unirsi
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getStartPt())
   if dist < minDist:
      isStartPt = False
      isStartPtToJoinTo = True
      minDist = dist
   # considero il punto finale della polilinea a cui unirsi
   dist = qad_utils.getDistance(ptToJoin, polylineToJoinTo.getEndPt())
   if dist < minDist:
      isStartPt = False
      isStartPtToJoinTo = False
      minDist = dist

   if minDist <= myToleranceDist: # trovato un punto
      # se il punto iniziale della polilinea da unire é uguale a quello iniziale della polilinea a cui unirsi
      if isStartPt == True and isStartPtToJoinTo == True:            
         part1 = polyline.getLinearObjectAt(0).copy()
         part1.reverse()
         part2 = polylineToJoinTo.getLinearObjectAt(0).copy()
         part2.reverse()
                     
         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:
            # elimino la prima parte
            polyline.remove(0)
            res.reverse()
            polyline.insertPolyline(0, res)
            
            # aggiungo le parti di <polylineToJoinTo> tranne la prima
            i = 1
            tot = polylineToJoinTo.qty()
            while i < tot:
               polyline.insert(0, polylineToJoinTo.getLinearObjectAt(i).copy().reverse())
               i = i + 1
            return True
         
      # se il punto iniziale della polilinea da unire é uguale a quello finale della polilinea a cui unirsi
      elif isStartPt == True and isStartPtToJoinTo == False:
         part1 = polyline.getLinearObjectAt(0).copy()
         part1.reverse()
         part2 = polylineToJoinTo.getLinearObjectAt(-1)
         
         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:
            # elimino la prima parte
            polyline.remove(0)
            res.reverse()
            polyline.insertPolyline(0, res)
            
            # aggiungo le parti di <polylineToJoinTo> tranne l'ultima
            i = polylineToJoinTo.qty() - 2
            while i >= 0:
               polyline.insert(0, polylineToJoinTo.getLinearObjectAt(i))
               i = i - 1
            return True

      # se il punto finale della polilinea da unire é uguale a quello iniziale della polilinea a cui unirsi
      elif isStartPt == False and isStartPtToJoinTo == True:
         part1 = polyline.getLinearObjectAt(-1)
         part2 = polylineToJoinTo.getLinearObjectAt(0).copy()
         part2.reverse()
         
         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:              
            # elimino l'ultima parte
            polyline.remove(-1)
            polyline.appendPolyline(res)

            # aggiungo le parti di <polylineToJoinTo> tranne la prima
            i = 1
            tot = polylineToJoinTo.qty()
            while i < tot:
               polyline.append(polylineToJoinTo.getLinearObjectAt(i))
               i = i + 1
            return True
         
      # se il punto finale della polilinea da unire é uguale a quello finale della polilinea a cui unirsi         
      elif isStartPt == False and isStartPtToJoinTo == False:
         part1 = polyline.getLinearObjectAt(-1)
         part2 = polylineToJoinTo.getLinearObjectAt(-1)
         
         res = joinEndPtsLinearParts(part1, part2, mode)
         if res is not None:            
            # elimino l'ultima parte
            polyline.remove(-1)
            polyline.appendPolyline(res)

            # aggiungo le parti di <polylineToJoinTo> tranne l'ultima
            i = polylineToJoinTo.qty() - 2
            while i >= 0:
               polyline.append(polylineToJoinTo.getLinearObjectAt(i).reverse())
               i = i - 1
            return True

   return False


# ===============================================================================
# joinEndPtsLinearParts
# ===============================================================================
def joinEndPtsLinearParts(part1, part2, mode):
   """
   la funzione effettua il join (unione) tra 2 parti lineari di base considerando il punto finale di part1
   e il punto iniziale di part2.
   La funzione riceve:
   <part1> = prima parte lineare  
   <part2> = seconda parte parte lineare  
   <mode> = Imposta il metodo di unione:
            1 -> Estendi;  Consente di unire polilinee selezionate estendendo o tagliando 
                           i segmenti nei punti finali più vicini.
            2 -> Aggiungi; Consente di unire polilinee selezionate aggiungendo un segmento 
                           retto tra i punti finali più vicini.
            3 -> Entrambi; Consente di unire polilinee selezionate estendendo o tagliando, se possibile.
                           In caso contrario, consente di unire polilinee selezionate aggiungendo 
                           un segmento retto tra i punti finali più vicini. 
   La funzione restituisce una QadPolyline che comprende:
   part1 (eventualmente modificata nel punto finale) + 
   eventuale segmento + 
   part2 (eventualmente modificata nel punto finale)
   oppure restituisce None se non é possibile l'unione delle parti
   """
   polyline = QadPolyline()
   endPt1 = part1.getEndPt()
   endPt2 = part2.getEndPt()
   
   if qad_utils.ptNear(endPt1, endPt2): # le 2 parti sono già  unite
      polyline.append(part1.copy())
      p = part2.copy()
      p.reverse()
      polyline.append(p)
      return polyline

   if mode == 1: # Estendi/Taglia
      IntPtList = QadIntersections.twoBasicGeomObjects(part1, part2)
      if len(IntPtList) > 0: # Taglia
         polyline.append(part1.copy())
         polyline.getLinearObjectAt(-1).setEndPt(IntPtList[0])
         p = part2.copy()
         p.reverse()
         polyline.append(p)
         polyline.getLinearObjectAt(-1).setStartPt(IntPtList[0])
         return polyline
      else: # estendi
         IntPtList = QadIntersections.twoBasicGeomObjectExtensions(part1, part2)
         # considero solo i punti oltre l'inizio delle parti
         for i in range(len(IntPtList) - 1, -1, -1):
            if part1.getDistanceFromStart(IntPtList[i]) < 0 or \
               part2.getDistanceFromStart(IntPtList[i]) < 0:
               del IntPtList[i]               
               
         if len(IntPtList) > 0:
            IntPt = IntPtList[0]   
            polyline.append(part1.copy())
            polyline.getLinearObjectAt(-1).setEndPt(IntPtList[0])
            p = part2.copy()
            p.reverse()           
            polyline.append(p)
            polyline.getLinearObjectAt(-1).setStartPt(IntPtList[0])
            return polyline
   
   if mode == 2 or mode == 3: # Aggiungi
      polyline.append(part1.copy())
      polyline.append([endPt1, endPt2])
      p = part2.copy()
      p.reverse()     
      polyline.append(p)
      return polyline

   return None


# ============================================================================
# joinFeatureInVectorLayer
# ============================================================================
def joinFeatureInVectorLayer(featureIdToJoin, vectorLayer, tolerance2ApproxCurve, toleranceDist = None, \
                             mode = 2):
   """
   la funzione effettua il join (unione) di una polilinea con un gruppo di altre polilinee.
   Non sono ammesse geometrie multiLineString.
   Il layer deve essere in modifica (startEditing) e in una transazione (beginEditCommand)
   La funzione riceve:
   <featureIdToJoin> = un ID della feature da unire 
   <vectorLayer> = un QgsVectorLayer che deve contenere le feature da unire
                   (si usano gli indici spaziali del vettore x essere più veloci).
   <toleranceDist> = distanza di tolleranza perché 2 punti siano considerati coincidenti  
   <tolerance2ApproxCurve> = tolleranza di approssimazione per le curve (usato se toleranceDist > 0)
   <mode> = Imposta il metodo di unione (usato se toleranceDist > 0):
            1 -> Estendi;  Consente di unire polilinee selezionate estendendo o tagliando 
                           i segmenti nei punti finali più vicini.
            2 -> Aggiungi; Consente di unire polilinee selezionate aggiungendo un segmento 
                           retto tra i punti finali più vicini.
            3 -> Entrambi;Consente di unire polilinee selezionate estendendo o tagliando, se possibile.
                 In caso contrario, consente di unire polilinee selezionate aggiungendo 
                 un segmento retto tra i punti finali più vicini. 
   La funzione modifica il <vectorLayer> modificando la feature da unire e cancellando 
   quelle unite a featureIdToJoin . Ritorna la lista di features cancellate.
   """
   if toleranceDist is None:
      myToleranceDist = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myToleranceDist = toleranceDist
   
   featureToJoin = qad_utils.getFeatureById(vectorLayer, featureIdToJoin)
   if featureToJoin is None:
      return []
   
   g = QgsGeometry(featureToJoin.geometry())
   polyline = QadPolyline()
   polyline.fromPolyline(g.asPolyline())
   
   polylineToJoinTo = QadPolyline()
   
   deleteFeatures = []
   feature = QgsFeature()
   
   # Unisco usando il punto iniziale finché trovo feature da unire
   ptToJoin = polyline.getStartPt()
   found = True
   while found == True:
      found = False
      if ptToJoin is None: # test
         fermati = True
      # cerco le features nel punto iniziale usando un micro rettangolo secondo <myToleranceDist>
      selectRect = QgsRectangle(ptToJoin.x() - myToleranceDist, ptToJoin.y() - myToleranceDist, \
                                ptToJoin.x() + myToleranceDist, ptToJoin.y() + myToleranceDist)
      # cerco il punto più vicino al punto iniziale della polilinea
      minDist = sys.float_info.max
      # fetchAttributes, fetchGeometry, rectangle, useIntersect             
      for feature in vectorLayer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):                       
         if feature.id() != featureIdToJoin: # salto la feature da unire
            polylineToJoinTo.fromPolyline(feature.geometry().asPolyline())
            
            if join2polyline(polyline, polylineToJoinTo, myToleranceDist, mode) == True:
               found = True
               
               deleteFeatures.append(QgsFeature(feature))
               if vectorLayer.deleteFeature(feature.id()) == False:
                  return []
               
               ptToJoin = polyline.getStartPt()
               pts = polyline.asPolyline(tolerance2ApproxCurve)
               featureToJoin.setGeometry(QgsGeometry.fromPolylineXY(pts))
               if vectorLayer.updateFeature(featureToJoin) == False:
                  return []
               break
            
   # Unisco usando il punto finale finché trovo feature da unire
   ptToJoin = polyline.getEndPt()
   found = True
   while found == True:
      found = False
      # cerco le features nel punto finale usando un micro rettangolo secondo <myToleranceDist>
      selectRect = QgsRectangle(ptToJoin.x() - myToleranceDist, ptToJoin.y() - myToleranceDist, \
                                ptToJoin.x() + myToleranceDist, ptToJoin.y() + myToleranceDist)
      # fetchAttributes, fetchGeometry, rectangle, useIntersect             
      for feature in vectorLayer.getFeatures(qad_utils.getFeatureRequest([], True, selectRect, True)):                       
         if feature.id() != featureIdToJoin: # salto la feature da unire
            polylineToJoinTo.fromPolyline(feature.geometry().asPolyline())

            if join2polyline(polyline, polylineToJoinTo, myToleranceDist, mode) == True:
               found = True
               
               deleteFeatures.append(QgsFeature(feature))
               if vectorLayer.deleteFeature(feature.id()) == False:
                  return []
               
               ptToJoin = polyline.getEndPt()
               pts = polyline.asPolyline(tolerance2ApproxCurve)
               featureToJoin.setGeometry(QgsGeometry.fromPolylineXY(pts))
               if vectorLayer.updateFeature(featureToJoin) == False:
                  return []
               break
   
   return deleteFeatures


# ============================================================================
# polylineAsQgsFeatureList
# ============================================================================
def polylineAsQgsFeatureList(polyline, polylineMode):
   """
   la funzione restituisce una lista di feature.
   Se polylineMode = True allora la lista degli oggetti lineari sarà considerata un'unica polilinea
   """
   fList = []
   if polylineMode == False:
      for linearObject in polyline.defList:
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPolylineXY(linearObject.asPolyline()))
        fList.append(f)
   else:
      f = QgsFeature()
      f.setGeometry(QgsGeometry.fromPolylineXY(polyline.asPolyline()))
      fList.append(f)
   
   return fList


# ============================================================================
# appendPolylineToTempQgsVectorLayer
# ============================================================================
def appendPolylineToTempQgsVectorLayer(polyline, vectorLayer, polylineMode, updateExtents = True):
   """
   la funzione inserisce gli oggetti lineari di una polyline in un QgsVectorLayer temporaneo già creato.
   Se polylineMode = True allora la lista degli oggetti lineari sarà considerata un'unica polilinea
   Ritorna la lista dei corrispettivi id di feature oppure None in caso di errore
   """
   fList = polylineAsQgsFeatureList(polyline, polylineMode)
   
   idList = []
   result = True
   if vectorLayer.startEditing() == False:
      return None
      
   vectorLayer.beginEditCommand("Feature added")
   
   for f in fList:
      if vectorLayer.addFeature(f):
         idList.append(f.id())
      else:
         result = False
         break

   if result == True:
      vectorLayer.endEditCommand();
      if updateExtents:
         vectorLayer.updateExtents()
      return idList
   else:
      vectorLayer.destroyEditCommand()
      return None


# ============================================================================
# selfJoinPolyline
# ============================================================================
def selfJoinPolyline(polyline):
   """
   la funzione viene usata quando la polilinea contiene parti lineari non connesse tra loro come una vera polyline.
   Restituisce una lista QadPolyline che contiene le polilinee
   generate dall'unione degli oggetti lineari.
   """
   crs = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs()
   # creo un layer temporaneo in memoria   
   vectorLayer = createMemoryLayer("QAD_SelfJoinLines", "LineString", crs)
   provider = vectorLayer.dataProvider()
              
   # unisco le parti della polilinea
   # inserisco nel layer i vari oggetti lineari
   idList = appendPolylineToTempQgsVectorLayer(polyline, vectorLayer, False)
   if idList is None:
      return []
   if provider.capabilities() & QgsVectorDataProvider.CreateSpatialIndex:
      provider.createSpatialIndex()
   
   vectorLayer.beginEditCommand("selfJoin")
   
   for featureIdToJoin in idList:
      #                         featureIdToJoin, vectorLayer, tolerance2ApproxCurve, tomyToleranceDist   
      joinFeatureInVectorLayer(featureIdToJoin, vectorLayer, QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE")))        
        
   vectorLayer.endEditCommand()
   vectorLayer.commitChanges()
   
   result = []
   feature = QgsFeature()
   
   # fetchAttributes, fetchGeometry, rectangle, useIntersect             
   for feature in vectorLayer.getFeatures(qad_utils.getFeatureRequest([], True, None, False)):                       
      polyline = QadPolyline()
      polyline.fromPolyline(feature.geometry().asPolyline())
      result.append(polyline)
 
   return result  
