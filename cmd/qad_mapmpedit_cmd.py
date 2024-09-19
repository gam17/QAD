# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 comando MAPMPEDIT per editare un poligono esistente
 
                              -------------------
        begin                : 2016-04-05
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


from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProject, QgsFeature


from .qad_generic_cmd import QadCommandClass
from ..qad_getpoint import *
from .qad_pline_cmd import QadPLINECommandClass
from .qad_ssget_cmd import QadSSGetClass
from ..qad_msg import QadMsg
from ..qad_textwindow import *
from .. import qad_utils
from .. import qad_layer
from .qad_entsel_cmd import QadEntSelClass
from ..qad_geom_relations import getQadGeomClosestVertex


#===============================================================================
# QadMAPMPEDITCommandOpTypeEnum class.
#===============================================================================
class QadMAPMPEDITCommandOpTypeEnum():
   UNION        = 1 # unione tra poligoni
   INTERSECTION = 2 # intersezione tra poligoni
   DIFFERENCE   = 3 # differenza tra poligoni


# Classe che gestisce il comando MAPMPEDIT
class QadMAPMPEDITCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadMAPMPEDITCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "MAPMPEDIT")
   
   def getEnglishName(self):
      return "MAPMPEDIT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMAPMPEDITCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/mapmpedit.svg")
   
   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_MAPMPEDIT", "Modifies existing polygon.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      
      self.poligonEntity = QadEntity()
      
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = False
      self.SSGetClass.checkDimLayers = False # scarto le quote
      
      self.entSelClass = None
      
      self.currAtGeom = None
      self.currAtSubGeom = None
     
      self.nOperationsToUndo = 0
   
   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass
      self.poligonEntity.deselectOnLayer()

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 1 or self.step == 4: # quando si é in fase di selezione entità
         return self.entSelClass.getPointMapTool(drawMode)
      elif self.step == 3 or self.step == 5 or \
           self.step == 6 or self.step == 7 or self.step == 8: # quando si é in fase di selezione gruppo entità
         return self.SSGetClass.getPointMapTool()           
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 1 or self.step == 4: # quando si é in fase di selezione entità
         return self.entSelClass.getCurrentContextualMenu()
      elif self.step == 3 or self.step == 5 or \
           self.step == 6 or self.step == 7 or self.step == 8: # quando si é in fase di selezione gruppo entità
         return None # return self.SSGetClass.getCurrentContextualMenu()           
      else:
         return self.contextualMenu


   def reinitSSGetClass(self):
      checkPointLayer = self.SSGetClass.checkPointLayer
      del self.SSGetClass
      self.SSGetClass = QadSSGetClass(self.plugIn)
      self.SSGetClass.onlyEditableLayers = False
      self.SSGetClass.checkDimLayers = False # scarto le quote
      self.SSGetClass.checkPointLayer = checkPointLayer


   #============================================================================
   # setCurrentSubGeom
   #============================================================================
   def setCurrentSubGeom(self, entSelClass):
      """
      Setta la sottogeometria corrente
      """
      self.currAtGeom = None
      self.currAtSubGeom = None

      # verifico che sia stata selezionata un'entità
      if entSelClass.entity.isInitialized() == False:
         self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
         return False
      # verifico che sia stata selezionata attraverso un punto
      # (per capire quale sottogeometria è stata selezionata)
      if entSelClass.point is None: return False
      # verifico che sia stato selezionato lo stesso polygono che è da modificare
      if self.poligonEntity != entSelClass.entity:
         self.showMsg(QadMsg.translate("Command_MAPMPEDIT", "The boundary doesn't belong to the selected polygon."))
         return False

      qadGeom = entSelClass.entity.getQadGeom()

      # la funzione ritorna una lista con 
      # (<minima distanza>
      # <punto del vertice più vicino>
      # <indice della geometria più vicina>
      # <indice della sotto-geometria più vicina>
      # <indice della parte della sotto-geometria più vicina>
      # <indice del vertice più vicino>
      result = getQadGeomClosestVertex(qadGeom, entSelClass.point)
      self.currAtGeom = result[2]
      self.currAtSubGeom = result[3]
      
      return True
   

   #============================================================================
   # addEntitySetToPolygon
   #============================================================================
   def addEntitySetToPolygon(self, entitySet, removeOriginals = False):
      """
      Aggiunge il set di entità al poligono da modificare
      """
      geom = self.poligonEntity.getGeometry()
      layerList = []
      layerList.append(self.poligonEntity.layer)
      
      for layerEntitySet in entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         if layer.geometryType() != QgsWkbTypes.PolygonGeometry and layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

         if removeOriginals: layerList.append(layer)
         coordTransform = QgsCoordinateTransform(layer.crs(), self.poligonEntity.layer.crs(), QgsProject.instance())

         for featureId in layerEntitySet.featureIds:
            # se la feature è quella di polygonEntity è errore 
            if layer.id() == self.poligonEntity.layerId() and featureId == self.poligonEntity.featureId:
               self.showMsg(QadMsg.translate("QAD", "Invalid object."))
               return False
            
            f = layerEntitySet.getFeature(featureId)
            # trasformo la geometria nel crs del layer del poligono da modificare
            geomToAdd = f.geometry()
            geomToAdd.transform(coordTransform)
            
            # se il poligono è contenuto nella geometria da aggiungere
            if geomToAdd.contains(geom):
               # Riduco la geometria in point o polyline
               simplifiedGeoms = qad_utils.asPointOrPolyline(geom)
               # deve essere un poligono senza ring
               if len(simplifiedGeoms) != 1 or \
                 (simplifiedGeoms[0].isMultipart() == True or simplifiedGeoms[0].type() != QgsWkbTypes.LineGeometry):
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               points = simplifiedGeoms[0].asPolyline() # vettore di punti
               # aggiungo un'isola
               if geomToAdd.addRing(points) != 0: # 0 in case of success
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               del geom
               geom = QgsGeometry.fromPolygonXY(geomToAdd.asPolygon())
            else: # se il poligono non è contenuto nella geometria da aggiungere
               # Riduco la geometria in point o polyline
               simplifiedGeoms = qad_utils.asPointOrPolyline(geomToAdd)
               for simplifiedGeom in simplifiedGeoms:
                  # se la geometria da aggiungere è contenuta nel poligono
                  if geom.contains(simplifiedGeom):
                     points = simplifiedGeom.asPolyline() # vettore di punti                     
                     # aggiungo un'isola
                     if geom.addRing(points) != 0: # 0 in case of success
                        self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                        return False
                  else:
                     # aggiungo una parte
                     if geom.addPartGeometry(simplifiedGeom) != QgsGeometry.Success:
                        self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                        return False

      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      layerList = entitySet.getLayerList()
      layerList.append(self.poligonEntity.layer)

      self.plugIn.beginEditCommand("Feature edited", layerList)
         
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:            
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return 

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True
   

   #============================================================================
   # delCurrentSubGeomToPolygon
   #============================================================================
   def delCurrentSubGeomToPolygon(self):
      """
      Cancella la sotto-geometria corrente dal poligono da modificare
      """
      geom = self.poligonEntity.getGeometry()

      # la posizione é espressa con una lista (<index ogg. princ> [<index ogg. sec.>])
      part = self.currAtGeom
      if self.currAtSubGeom > 0:
         ring = self.currAtSubGeom
         if geom.deleteRing(ring, part) == False: # cancello una isola (Ring 0 is outer ring and can't be deleted)
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False
      else:
         if geom.deletePart(part) == False: # cancello una parte
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      self.plugIn.beginEditCommand("Feature edited", self.poligonEntity.layer)
         
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1


   #============================================================================
   # unionIntersSubtractEntitySetToPolygon
   #============================================================================
   def unionIntersSubtractEntitySetToPolygon(self, entitySet, opType, removeOriginals = False):
      """
      Unisce o interseca i poligoni di entitySet al poligono corrente
      """
      geom = self.poligonEntity.getGeometry()
      layerList = []
      layerList.append(self.poligonEntity.layer)
      
      geomList = []
      geomList.append(geom)
      for layerEntitySet in entitySet.layerEntitySetList:
         del geomList[:]
         layer = layerEntitySet.layer
         coordTransform = QgsCoordinateTransform(layer.crs(), self.poligonEntity.layer.crs(), QgsProject.instance())
         
         if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            for featureId in layerEntitySet.featureIds:
               # se la feature è quella di polygonEntity è errore 
               if layer.id() == self.poligonEntity.layerId() and featureId == self.poligonEntity.featureId:
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               f = layerEntitySet.getFeature(featureId)
               # trasformo la geometria nel crs del layer del poligono da modificare
               geomToAdd = f.geometry()

               geomToAdd.transform(coordTransform)

               if opType == QadMAPMPEDITCommandOpTypeEnum.UNION: geom = geom.combine(geomToAdd)
               elif opType == QadMAPMPEDITCommandOpTypeEnum.INTERSECTION: geom = geom.intersection(geomToAdd)
               elif opType == QadMAPMPEDITCommandOpTypeEnum.DIFFERENCE: geom = geom.difference(geomToAdd)
               
               if geom is None:
                  self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                  return False
               
               if removeOriginals and layer.id() != self.poligonEntity.layerId():
                  layerList.append(layer)

         elif layer.geometryType() == QgsWkbTypes.LineGeometry:
            for featureId in layerEntitySet.featureIds:
               f = layerEntitySet.getFeature(featureId)
               # trasformo la geometria nel crs del layer del poligono da modificare
               geomToAdd = f.geometry()
               geomToAdd.transform(coordTransform)
               # Riduco la geometria in point o polyline
               simplifiedGeoms = qad_utils.asPointOrPolyline(geomToAdd)
               for simplifiedGeom in simplifiedGeoms:
                  if simplifiedGeoms.isMultipart() == True or simplifiedGeoms.type() != QgsWkbTypes.LineGeometry:
                     self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                     return False
                  points = simplifiedGeom.asPolyline() # vettore di punti
                  
                  if len(points) < 4 or points[0] != points[-1]: # polilinea chiusa con almeno 4 punti (primo e ultimo uguali)
                     self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                     return False
                  geomToAdd = QgsGeometry.fromPolygonXY([points])
                  
                  if opType == QadMAPMPEDITCommandOpTypeEnum.UNION: geom = geom.combine(geomToAdd)
                  elif opType == QadMAPMPEDITCommandOpTypeEnum.INTERSECTION: geom = geom.intersection(geomToAdd)
                  elif opType == QadMAPMPEDITCommandOpTypeEnum.DIFFERENCE: geom = geom.difference(geomToAdd)
                  
                  if geom is None or geom.type() != QgsWkbTypes.PolygonGeometry:
                     self.showMsg(QadMsg.translate("QAD", "Invalid object."))
                     return False
                  
               if removeOriginals: layerList.append(layer)
         else:
            self.showMsg(QadMsg.translate("QAD", "Invalid object."))
            return False

      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      self.plugIn.beginEditCommand("Feature edited", layerList)
         
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:            
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return 

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True

   
   #============================================================================
   # convexHullEntitySetToPolygon
   #============================================================================
   def convexHullEntitySetToPolygon(self, entitySet, removeOriginals = False):
      """
      modifica il poligono corrente in modo che includa tutti i punti delle geometrie di entitySet
      """
      layerList = []
      layerList.append(self.poligonEntity.layer)
      pointsForConvexHull = []
      
      for layerEntitySet in entitySet.layerEntitySetList:
         layer = layerEntitySet.layer
         coordTransform = QgsCoordinateTransform(layer.crs(), self.poligonEntity.layer.crs(), QgsProject.instance())
         
         for featureId in layerEntitySet.featureIds:
            f = layerEntitySet.getFeature(featureId)
            # trasformo la geometria nel crs del layer del poligono da modificare
            geom = f.geometry()
            geom.transform(coordTransform)

            # Riduco la geometria in point o polyline
            simplifiedGeoms = qad_utils.asPointOrPolyline(geom)
            for simplifiedGeom in simplifiedGeoms:
               gType = simplifiedGeom.type()
               if simplifiedGeom.isMultipart() == False and simplifiedGeom.isMultipart() == False:
                  pointsForConvexHull.extend(simplifiedGeom.asPolyline())
               else:
                  pointsForConvexHull.append(simplifiedGeom.asPoint())
               
            if removeOriginals and layer.id() != self.poligonEntity.layerId():
               layerList.append(layer)

      geom = QgsGeometry.fromMultiPointXY(pointsForConvexHull)
      geom = geom.convexHull()
      if geom is None:
         self.showMsg(QadMsg.translate("QAD", "Invalid object."))
         return False
         
      f = self.poligonEntity.getFeature()
      f.setGeometry(geom)

      self.plugIn.beginEditCommand("Feature edited", layerList)
         
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      if removeOriginals:
         for layerEntitySet in entitySet.layerEntitySetList:            
            if qad_layer.deleteFeaturesToLayer(self.plugIn, layerEntitySet.layer, layerEntitySet.featureIds, False) == False:
               self.plugIn.destroyEditCommand()
               return 

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True


   #============================================================================
   # dividePolygon
   #============================================================================
   def splitPolygon(self, splitLine, createNewEntities):
      """
      divide il poligono corrente usando una polilinea con i vertici in <plineVertices> in modo da generare o meno nuove entità
      """
      layerList = []
      layerList.append(self.poligonEntity.layer)
      
      splitLineTransformed = self.mapToLayerCoordinates(self.poligonEntity.layer, splitLine)
      f = self.poligonEntity.getFeature()
      oldGeom = f.geometry()
      result, newGeoms, topologyTestPts = oldGeom.splitGeometry(splitLineTransformed, False) # Set to true if you want to split a feature, otherwise set to false to split parts

      if result != QgsGeometry.Success or len(newGeoms) == 0:
         self.showMsg(QadMsg.translate("QAD", "Invalid object."))
         return False

      f.setGeometry(oldGeom)
      self.plugIn.beginEditCommand("Feature edited", layerList)
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False
      
      if len(newGeoms) > 0:
         newfeatures =[]
         if createNewEntities:
            for newGeom in newGeoms:
               newfeature = QgsFeature(f)
               newfeature.setGeometry(newGeom)
               newfeatures.append(newfeature)
               
            # plugIn, layer, features, coordTransform, refresh, check_validity
            if qad_layer.addFeaturesToLayer(self.plugIn, self.poligonEntity.layer, newfeatures, None, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
         else:
            for newGeom in newGeoms:
               if oldGeom.addPartGeometry(newGeom) != QgsGeometry.Success:
                  return False
            f.setGeometry(oldGeom)
            
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, self.poligonEntity.layer, f, False, False) == False:
               self.plugIn.destroyEditCommand()
               return False
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      self.plugIn.endEditCommand()

      return True



   #============================================================================
   # waitForEntsel
   #============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 1
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_MAPMPEDIT", "Select polygon: ")
      # scarto la selezione di punti e polilinee
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = False
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False     
      self.entSelClass.onlyEditableLayers = True

      self.entSelClass.run(msgMapTool, msg)
      

   #============================================================================
   # WaitForMainMenu
   #============================================================================
   def WaitForMainMenu(self):
      self.poligonEntity.selectOnLayer(False)
      keyWords = QadMsg.translate("Command_MAPMPEDIT", "Add") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "dElete") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "Union") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "Substract") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "Intersect") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "split Objects") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "split Parts") + "/" + \
                 QadMsg.translate("Command_MAPMPEDIT", "iNclude objs")
      englishKeyWords = "Add" + "/" + "dElete" + "/" + "Union" + "/" + "Substract" + "/" + "Intersect" "/" + \
                        "split Objects" + "/" + "split Parts" + "/" + "iNclude objs"

      if self.nOperationsToUndo > 0: # se c'è qualcosa che si può annullare
         keyWords = keyWords + "/" +  QadMsg.translate("Command_MAPMPEDIT", "unDo")
         englishKeyWords = englishKeyWords + "/" + "unDo"
      
      keyWords = keyWords + "/" + QadMsg.translate("Command_MAPMPEDIT", "eXit")
      englishKeyWords = englishKeyWords + "/" + "eXit"
                 
      default = QadMsg.translate("Command_MAPMPEDIT", "eXit")

      prompt = QadMsg.translate("Command_MAPMPEDIT", "Enter an option [{0}] <{1}>: ").format(keyWords, default)
      
      self.step = 2
      self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.NONE)
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
      
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      return False
      

   #============================================================================
   # waitForBoundary
   #============================================================================
   def waitForBoundary(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_MAPMPEDIT", "Select boundary: ")
      # scarto la selezione di punti e polilinee
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = False
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = True

      self.entSelClass.run(msgMapTool, msg)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      if self.step == 0:
         self.waitForEntsel(msgMapTool, msg) # seleziona il poligono da modificare
         return False # continua
      
      #=========================================================================
      # RISPOSTA ALLA SELEZIONE POLIGONO DA MODIFICARE
      elif self.step == 1:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               self.poligonEntity.set(self.entSelClass.entity.layer, self.entSelClass.entity.featureId)
               layer = self.entSelClass.entity.layer
               self.poligonEntity.deselectOnLayer()
               self.WaitForMainMenu()
            else:
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)

         return False # continua

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL MENU PRINCIPALE
      elif self.step == 2: # dopo aver atteso una opzione si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            self.WaitForMainMenu()
            return False 
         else: # l'opzione arriva come parametro della funzione
            value = msg

         self.poligonEntity.deselectOnLayer()

         if value == QadMsg.translate("Command_MAPMPEDIT", "Add") or value == "Add":
            self.SSGetClass.checkPointLayer = False # scarto i punto
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 3
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "dElete") or value == "Delete":
            self.waitForBoundary(msgMapTool, msg)
            self.step = 4
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "Union") or value == "Union":
            self.SSGetClass.checkPointLayer = False # scarto i layer puntuali
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 5
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "Substract") or value == "Substract":
            self.SSGetClass.checkPointLayer = False # scarto i layer puntuali
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 6
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "Intersect") or value == "Intersect":
            self.SSGetClass.checkPointLayer = False # scarto i layer puntuali
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 7
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "split Objects") or value == "split Objects":
            # Disegna una polilinea di divisione del poligono
            self.PLINECommand = QadPLINECommandClass(self.plugIn)
            # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
            # che non verrà salvata su un layer
            self.PLINECommand.virtualCmd = True   
            self.PLINECommand.run(msgMapTool, msg)
            self.step = 9
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "split Parts") or value == "split Parts":
            # Disegna una polilinea di divisione del poligono
            self.PLINECommand = QadPLINECommandClass(self.plugIn)
            # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
            # che non verrà salvata su un layer
            self.PLINECommand.virtualCmd = True   
            self.PLINECommand.run(msgMapTool, msg)
            self.step = 10
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "iNclude objs") or value == "iNclude objs":
            self.SSGetClass.checkPointLayer = True # includo i layer puntuali
            self.SSGetClass.run(msgMapTool, msg)
            self.step = 8
            return False
         elif value == QadMsg.translate("Command_MAPMPEDIT", "unDo") or value == "unDo":
            if self.nOperationsToUndo > 0: 
               self.nOperationsToUndo = self.nOperationsToUndo - 1           
               self.plugIn.undoEditCommand()
            else:
               self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
         elif value == QadMsg.translate("Command_MAPMPEDIT", "eXit") or value == "eXit":
            return True # fine comando
         else:
            return True # fine comando
         
         self.WaitForMainMenu()
         return False      

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI ADD (da step = 2)
      elif self.step == 3:
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.addEntitySetToPolygon(self.SSGetClass.entitySet)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI DELETE (da step = 2)
      elif self.step == 4:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.setCurrentSubGeom(self.entSelClass) == True:
               self.delCurrentSubGeomToPolygon()
               self.WaitForMainMenu()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # fine selezione entità
                  self.WaitForMainMenu()
               else:
                  self.waitForBoundary(msgMapTool, msg)
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI UNION (da step = 2)
      elif self.step == 5: # dopo aver atteso una entità si riavvia il comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.unionIntersSubtractEntitySetToPolygon(self.SSGetClass.entitySet, QadMAPMPEDITCommandOpTypeEnum.UNION)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI SUBTRACT (da step = 2)
      elif self.step == 6: # dopo aver atteso una entità si riavvia il comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.unionIntersSubtractEntitySetToPolygon(self.SSGetClass.entitySet, QadMAPMPEDITCommandOpTypeEnum.DIFFERENCE)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI INTERSECT (da step = 2)
      elif self.step == 7: # dopo aver atteso una entità si riavvia il comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.unionIntersSubtractEntitySetToPolygon(self.SSGetClass.entitySet, QadMAPMPEDITCommandOpTypeEnum.INTERSECTION)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI INCLUDE OBJS (da step = 2)
      elif self.step == 8: # dopo aver atteso una entità si riavvia il comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() > 0:
               self.convexHullEntitySetToPolygon(self.SSGetClass.entitySet)
            self.reinitSSGetClass()
            self.WaitForMainMenu()
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA LINEA DI DIVISIONE (da step = 2)
      elif self.step == 9: # dopo aver atteso un punto si riavvia il comando
         if self.PLINECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            self.splitPolygon(self.PLINECommand.polyline.asPolyline(), True)
            del self.PLINECommand
            self.PLINECommand = None
            self.WaitForMainMenu()
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA LINEA DI DIVISIONE (da step = 2)
      elif self.step == 10: # dopo aver atteso un punto si riavvia il comando
         if self.PLINECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            self.splitPolygon(self.PLINECommand.polyline.asPolyline(), False)
            del self.PLINECommand
            self.PLINECommand = None
            self.WaitForMainMenu()
         return False
      