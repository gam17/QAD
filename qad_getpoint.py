# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool di richiesta di un punto
 
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


from qgis.PyQt.QtCore import Qt, QTimer, QEvent
from qgis.PyQt.QtGui import QColor, QCursor, QIcon, QKeyEvent
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.core import QgsWkbTypes, QgsGeometry, QgsCoordinateTransform, QgsPointXY, QgsProject
from qgis.gui import QgsMapTool

import math
import time # profiling
import datetime


from . import qad_utils
from .qad_snapper import QadSnapper, QadSnapModeEnum, QadSnapTypeEnum, snapTypeEnum2Str
from .qad_snappointsdisplaymanager import QadSnapPointsDisplayManager
from .qad_entity import QadEntity
from .qad_variables import QadVariables, QadAUTOSNAPEnum, QadPOLARMODEnum, POLARADDANG_to_list
from .qad_rubberband import createRubberBand, getColorForCrossingSelectionArea, \
                            getColorForWindowSelectionArea, QadCursorTypeEnum, QadCursorRubberBand
from .qad_cacheareas import QadLayerCacheGeomsDict
from .qad_textwindow import QadInputTypeEnum
from .qad_dynamicinput import QadDynamicEditInput, QadDynamicInputContextEnum
from .qad_msg import QadMsg


#===============================================================================
# QadGetPointSelectionModeEnum class.
#===============================================================================
class QadGetPointSelectionModeEnum():
   NONE                     = 0  # nessuna selezione (usato quando in un comando si chiede solo la scelta di opzioni)
   POINT_SELECTION          = 1  # selezione di un punto
   ENTITY_SELECTION         = 2  # selezione di una entità in modo statico (cerca l'entità solo con l'evento click)
   ENTITYSET_SELECTION      = 3  # selezione di un gruppo di entità  
   ENTITY_SELECTION_DYNAMIC = 4  # selezione di una entità in modo dinamico (cerca l'entità con l'evento click e 
                                 # con l'evento mouse move)


#===============================================================================
# QadGetPointDrawModeEnum class.
#===============================================================================
class QadGetPointDrawModeEnum():
   NONE              = 0     # nessuno
   ELASTIC_LINE      = 1     # linea elastica dal punto __startPoint
   ELASTIC_RECTANGLE = 2     # rettangolo elastico dal punto __startPoint   


from .qad_dsettings_dlg import QadDSETTINGSDialog, QadDSETTINGSTabIndexEnum


#===============================================================================
# QadGetPoint get point class
#===============================================================================
class QadGetPoint(QgsMapTool):
    
   def __init__(self, plugIn, drawMode = QadGetPointDrawModeEnum.NONE):        
      QgsMapTool.__init__(self, plugIn.iface.mapCanvas())
      self.iface = plugIn.iface
      self.canvas = plugIn.iface.mapCanvas()
      self.plugIn = plugIn
      
      # cursore
      self.__csrRubberBand = None
      
      self.__QadSnapper = None
      self.__QadSnapPointsDisplayManager = None
      self.__oldSnapType = None
      self.__oldSnapProgrDist = None
      self.__geometryTypesAccordingToSnapType = (False, False, False)
      self.__startPoint = None
      self.tmpGeometries = [] # lista di geometria non ancora esistenti ma da contare per i punti di osnap (in map coordinates)
      # opzioni per limitare l'oggetto da selezionare
      self.onlyEditableLayers = False
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.layersToCheck = None
            
      self.__RubberBand = None
      self.__prevGeom = None
      
      self.__stopTimer = True

      # ottimizzazione per la ricerca degli oggetti
      # cache per selezione oggetti
      self.layerCacheGeomsDict = QadLayerCacheGeomsDict(self.canvas)
      self.lastLayerFound = None # layer ultimo oggetto trovato
      
      # setto la modalità di selezione
      self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)

      self.setDrawMode(drawMode)

      self.__QadSnapper = QadSnapper()
      self.__QadSnapper.setSnapMode(QadSnapModeEnum.ONE_RESULT) # Viene restituito solo il punto più vicino
      # Tutti i layer vettoriali visibili secondo le impostazioni QGIS
      # (solo layer corrente, un set di layer, tutti i layer)
      self.setSnapLayersFromQgis()
      self.canvas.snappingUtils().configChanged.connect(self.setSnapLayersFromQgis) # update snap layers whenever QGIS snap settings change

      
      self.__QadSnapper.setProgressDistance(QadVariables.get(QadMsg.translate("Environment variables", "OSPROGRDISTANCE")))
      self.setSnapType(QadVariables.get(QadMsg.translate("Environment variables", "OSMODE")))
            
      self.setOrthoMode() # setto secondo le variabili d'ambiente
      self.setAutoSnap() # setto secondo le variabili d'ambiente
      
      # leggo la tolleranza in unità di mappa
      ToleranceInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) * self.canvas.mapSettings().mapUnitsPerPixel()    
      self.__QadSnapper.setDistToExcludeNea(ToleranceInMapUnits)
      self.__QadSnapper.setToleranceExtParLines(ToleranceInMapUnits)

      self.__QadSnapPointsDisplayManager = QadSnapPointsDisplayManager(self.canvas)
      self.__QadSnapPointsDisplayManager.setIconSize(QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE")))
      self.__QadSnapPointsDisplayManager.setColor(QColor(QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPCOLOR"))))
      
      # output
      self.rightButton = False
      # tasto shift
      self.shiftKey = False
      self.tmpShiftKey = False
      # tasto ctrl
      self.ctrlKey = False
      self.tmpCtrlKey = False

      self.point = None # punto selezionato dal click
      self.tmpPoint = None # punto selezionato dal movimento del mouse
      
      self.entity = QadEntity() # entità selezionata dal click
      self.tmpEntity = QadEntity() # entità selezionata dal movimento del mouse
      
      self.snapTypeOnSelection = None # snap attivo al momento del click
      
      # profiling
      self.tempo_tot = 0
      self.tempo1 = 0
      self.tempo2 = 0

      self.startDateTimeForRightClick = 0

      # input dinamico
      self.dynamicEditInput = QadDynamicEditInput(plugIn, QadDynamicInputContextEnum.NONE)
      
      # gestione di punto medio tra 2 punto (M2P)
      self.M2P_Mode = False # se la modalità M2P è attivata o meno
      self.M2p_pt1 = None # primo punto


   def __del__(self):
      self.removeItems()
      self.canvas.snappingUtils().configChanged.disconnect(self.setSnapLayersFromQgis) # update snap layers whenever QGIS snap settings change

 
   def removeItems(self):
      if self.__csrRubberBand is not None:
         self.__csrRubberBand.removeItems() # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
         del self.__csrRubberBand
         self.__csrRubberBand = None
      
      if self.__RubberBand is not None:
         self.canvas.scene().removeItem(self.__RubberBand) # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
         del self.__RubberBand
         self.__RubberBand = None

      if self.__QadSnapper is not None:
         del self.__QadSnapper
         self.__QadSnapper = None
      
      if self.__QadSnapPointsDisplayManager is not None:
         self.__QadSnapPointsDisplayManager.removeItems() # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
         del self.__QadSnapPointsDisplayManager
         self.__QadSnapPointsDisplayManager = None
         
      if self.layerCacheGeomsDict is not None: # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas (eventi)
         del self.layerCacheGeomsDict
         self.layerCacheGeomsDict = None

      if self.dynamicEditInput is not None:
         self.dynamicEditInput.removeItems()
         del self.dynamicEditInput
         self.dynamicEditInput = None

   
   #============================================================================
   # getDynamicInput
   #============================================================================
   def getDynamicInput(self):
      return self.dynamicEditInput
   
   
   #============================================================================
   # setDrawMode
   #============================================================================
   def setDrawMode(self, drawMode):
      self.__drawMode = drawMode
      if self.__RubberBand is not None:
         self.__RubberBand.hide()
         self.canvas.scene().removeItem(self.__RubberBand) # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
         del self.__RubberBand
         self.__RubberBand = None
         
      if self.__drawMode == QadGetPointDrawModeEnum.ELASTIC_LINE:
         self.refreshOrthoMode() # setto il default
         self.__RubberBand = createRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
         self.__RubberBand.setLineStyle(Qt.DotLine)
      elif self.__drawMode == QadGetPointDrawModeEnum.ELASTIC_RECTANGLE:
         self.rectangleCrossingSelectionColor = getColorForCrossingSelectionArea()
         self.rectangleWindowSelectionColor = getColorForWindowSelectionArea()
            
         self.__RubberBand = createRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry, False, None, self.rectangleCrossingSelectionColor)
         self.__RubberBand.setLineStyle(Qt.DotLine)
         

   #============================================================================
   # getDrawMode
   #============================================================================
   def getDrawMode(self):
      return self.__drawMode


   #============================================================================
   # setSelectionMode
   #============================================================================
   def setSelectionMode(self, selectionMode):
      self.__selectionMode = selectionMode
      # setto il tipo di cursore
      if selectionMode == QadGetPointSelectionModeEnum.POINT_SELECTION:
         if QadVariables.get(QadMsg.translate("Environment variables", "APBOX")) == 0:
            self.setCursorType(QadCursorTypeEnum.CROSS) # una croce usata per selezionare un punto
         else:
            self.setCursorType(QadCursorTypeEnum.CROSS | QadCursorTypeEnum.APERTURE) # una croce + un quadratino usati per selezionare un punto
      elif selectionMode == QadGetPointSelectionModeEnum.ENTITY_SELECTION or \
           selectionMode == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC:
         self.entity.clear() # entità selezionata 
         self.setCursorType(QadCursorTypeEnum.BOX) # un quadratino usato per selezionare entità
      elif selectionMode == QadGetPointSelectionModeEnum.ENTITYSET_SELECTION:
         if QadVariables.get(QadMsg.translate("Environment variables", "APBOX")) == 0:
            self.setCursorType(QadCursorTypeEnum.CROSS) # una croce usata per selezionare un punto
         else:
            self.setCursorType(QadCursorTypeEnum.CROSS | QadCursorTypeEnum.APERTURE) # una croce + un quadratino usati per selezionare un punto
      elif selectionMode == QadGetPointSelectionModeEnum.NONE:
         self.setCursorType(QadCursorTypeEnum.NONE) # nessun cursore


   #============================================================================
   # getSelectionMode
   #============================================================================
   def getSelectionMode(self):
      return self.__selectionMode


   #============================================================================
   # hidePointMapToolMarkers
   #============================================================================
   def hidePointMapToolMarkers(self):
      if self.__QadSnapPointsDisplayManager is not None:
         self.__QadSnapPointsDisplayManager.hide()
      if self.__RubberBand is not None:
         self.__RubberBand.hide()


   #============================================================================
   # showPointMapToolMarkers
   #============================================================================
   def showPointMapToolMarkers(self):
      if self.__RubberBand is not None:
         self.__RubberBand.show()


   #============================================================================
   # getPointMapToolMarkersCount
   #============================================================================
   def getPointMapToolMarkersCount(self):
      if self.__RubberBand is None:
         return 0
      else:
         return self.__RubberBand.numberOfVertices()

                             
   #============================================================================
   # clear
   #============================================================================
   def clear(self):
      self.hidePointMapToolMarkers()
      if self.__RubberBand is not None:
         self.canvas.scene().removeItem(self.__RubberBand) # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
         del self.__RubberBand
         self.__RubberBand = None

      self.__QadSnapper.removeReferenceLines()
      self.__QadSnapper.setStartPoint(None)

      self.point = None # punto selezionato dal click
      self.tmpPoint = None # punto selezionato dal movimento del mouse
      
      self.entity.clear() # entità selezionata dal click
      self.tmpEntity.clear() # entità selezionata dal movimento del mouse
      
      self.snapTypeOnSelection = None # snap attivo al momento del click

      self.shiftKey = False
      self.tmpShiftKey = False # tasto shift premuto durante il movimento del mouse

      self.ctrlKey = False
      self.tmpCtrlKey = False # tasto ctrl premuto durante il movimento del mouse
       
      self.rightButton = False      
      # opzioni per limitare l'oggetto da selezionare
      self.onlyEditableLayers = False
      self.checkPointLayer = True # usato solo per ENTITY_SELECTION
      self.checkLineLayer = True # usato solo per ENTITY_SELECTION
      self.checkPolygonLayer = True # usato solo per ENTITY_SELECTION
      self.layersToCheck = None
      
      self.__oldSnapType = None
      self.__oldSnapProgrDist = None
      self.__startPoint = None
      self.clearTmpGeometries()


   #============================================================================
   # cache
   #============================================================================
   def updateLayerCacheOnMapCanvasExtent(self):
      if self.layerCacheGeomsDict is not None:
         del self.layerCacheGeomsDict
      # ottimizzazione per la ricerca degli oggetti
      self.layerCacheGeomsDict = QadLayerCacheGeomsDict(self.canvas)
      
      # se l'obiettivo é selezionare un'entità in modo dinamico
      if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC:
         if self.layerCacheGeomsDict.refreshOnMapCanvasExtent(self.layersToCheck, \
                                                              self.checkPointLayer, \
                                                              self.checkLineLayer, \
                                                              self.checkPolygonLayer, \
                                                              self.onlyEditableLayers) == False:
            del self.layerCacheGeomsDict
            self.layerCacheGeomsDict = None

      # se l'obiettivo é selezionare un punto
      elif self.getSelectionMode() == QadGetPointSelectionModeEnum.POINT_SELECTION:
         if self.layerCacheGeomsDict.refreshOnMapCanvasExtent(None, \
                                                              self.__geometryTypesAccordingToSnapType[0], \
                                                              self.__geometryTypesAccordingToSnapType[1], \
                                                              self.__geometryTypesAccordingToSnapType[2], \
                                                              False) == False:
            del self.layerCacheGeomsDict
            self.layerCacheGeomsDict = None


   #============================================================================
   # tmpGeometries
   #============================================================================
   def clearTmpGeometries(self):
      del self.tmpGeometries[:] # svuoto la lista
      self.__QadSnapper.clearTmpGeometries()


   #============================================================================
   # setTmpGeometry
   #============================================================================
   def setTmpGeometry(self, geom, CRS = None):
      self.clearTmpGeometries()
      self.appendTmpGeometry(geom, CRS)


   #============================================================================
   # appendTmpGeometry
   #============================================================================
   def appendTmpGeometry(self, geom, CRS = None):
      if geom is None:
         return
      if CRS is not None and CRS != self.canvas.mapSettings().destinationCrs():
         g = QgsGeometry(geom)
         coordTransform = QgsCoordinateTransform(CRS, \
                                                 self.canvas.mapSettings().destinationCrs(), \
                                                 QgsProject.instance()) # trasformo la geometria
         g.transform(coordTransform)
         self.tmpGeometries.append(g)
      else:
         self.tmpGeometries.append(geom)

      self.__QadSnapper.appendTmpGeometry(geom)
      

   #============================================================================
   # setTmpGeometries
   #============================================================================
   def setTmpGeometries(self, geoms, CRS = None):
      self.clearTmpGeometries()
      for g in geoms:
         self.appendTmpGeometry(g, CRS)
      

   #============================================================================
   # SnapType
   #============================================================================
   def setSnapLayersFromQgis(self):
      """
      Sets the layers to be snapped to from QGIS's settings
      """
      # Tutti i layer vettoriali visibili secondo le impostazioni QGIS
      # (solo layer corrente, un set di layer, tutti i layer)
      if self.__QadSnapper is not None:
         self.__QadSnapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.canvas))
      
      
   #============================================================================
   # SnapType
   #============================================================================
   def setSnapType(self, snapType = None):
      if snapType is None:      
         self.__QadSnapper.setSnapType(QadVariables.get(QadMsg.translate("Environment variables", "OSMODE")))
      else:
         self.__QadSnapper.setSnapType(snapType)
         
      self.__geometryTypesAccordingToSnapType = self.__QadSnapper.getGeometryTypesAccordingToSnapType()
      self.updateLayerCacheOnMapCanvasExtent()
      

   #============================================================================
   # getSnapType
   #============================================================================
   def getSnapType(self):
      return self.__QadSnapper.getSnapType()


   #============================================================================
   # forceSnapTypeOnce
   #============================================================================
   def forceSnapTypeOnce(self, snapType = None, snapParams = None):
      self.__oldSnapType = self.__QadSnapper.getSnapType()
      self.__oldSnapProgrDist = self.__QadSnapper.getProgressDistance()
      
      # se si vuole impostare lo snap perpendicolare e
      # non é stato impostato un punto di partenza
      if snapType == QadSnapTypeEnum.PER and self.__startPoint is None:
         # imposto lo snap perpendicolare differito
         self.setSnapType(QadSnapTypeEnum.PER_DEF)
         return
      # se si vuole impostare lo snap tangente e
      # non é stato impostato un punto di partenza
      if snapType == QadSnapTypeEnum.TAN and self.__startPoint is None:
         # imposto lo snap tangente differito
         self.setSnapType(QadSnapTypeEnum.TAN_DEF)
         return

      if snapParams is not None:
         for param in snapParams:
            if param[0] == QadSnapTypeEnum.PR:
               # se si vuole impostare una distanza lo snap progressivo
               self.__QadSnapper.setProgressDistance(param[1])
            
      self.setSnapType(snapType)


   #============================================================================
   # forceM2P
   #============================================================================
   def forceM2P(self):
      self.M2P_Mode = True
      self.plugIn.showMsg("\n" + QadMsg.translate("Snap", "First point of mid: "))

   #============================================================================
   # refreshSnapType
   #============================================================================
   def refreshSnapType(self):
      self.__oldSnapType = None
      self.__oldSnapProgrDist = None
      self.__QadSnapper.setProgressDistance(QadVariables.get(QadMsg.translate("Environment variables", "OSPROGRDISTANCE")))
      self.setSnapType(QadVariables.get(QadMsg.translate("Environment variables", "OSMODE")))


   #============================================================================
   # OrthoMode
   #============================================================================
   def setOrthoMode(self, orthoMode = None):
      if orthoMode is None:      
         self.__OrthoMode = QadVariables.get(QadMsg.translate("Environment variables", "ORTHOMODE"))
      else:
         self.__OrthoMode = orthoMode


   #============================================================================
   # getOrthoCoord
   #============================================================================
   def getOrthoCoord(self, point):
      if math.fabs(point.x() - self.__startPoint.x()) < \
         math.fabs(point.y() - self.__startPoint.y()):
         return QgsPointXY(self.__startPoint.x(), point.y())
      else:
         return QgsPointXY(point.x(), self.__startPoint.y())


   #============================================================================
   # refreshOrthoMode
   #============================================================================
   def refreshOrthoMode(self):
      self.setOrthoMode()


   #============================================================================
   # AutoSnap
   #============================================================================
   def setAutoSnap(self, autoSnap = None):
      # setta le variabili:
      # self.__AutoSnap, self.__PolarAng, self.__PolarMode, self.__PolarAngOffset, self.__snapMarkerSizeInMapUnits, self.__PolarAddAngles
      # self.__QadSnapper viene svuotato dai punti polari se "Object Snap Tracking off"
      
      if autoSnap is None:
         self.__AutoSnap = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))
      else:
         self.__AutoSnap = autoSnap
         
      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: # puntamento polare non attivato
         self.__PolarAng = None
         self.__PolarMode = None
         self.__PolarAngOffset = None
         self.__PolarAddAngles = None
      else:
         self.__PolarAng = math.radians(QadVariables.get(QadMsg.translate("Environment variables", "POLARANG")))
         self.__PolarMode = QadVariables.get(QadMsg.translate("Environment variables", "POLARMODE"))
         self.__PolarAngOffset = self.plugIn.lastSegmentAng
         if self.__PolarMode & QadPOLARMODEnum.ADDITIONAL_ANGLES:
            dummy = QadVariables.get(QadMsg.translate("Environment variables", "POLARADDANG"))   
            self.__PolarAddAngles = POLARADDANG_to_list(dummy, True) # es. "1;2.3" genera la lista in ordine crescente convertendo in radianti        
         else:
            self.__PolarAddAngles = None
            
         
      if (self.__AutoSnap & QadAUTOSNAPEnum.OBJ_SNAP_TRACKING) == False: # Object Snap Tracking off
         if self.__QadSnapper is not None:
            self.__QadSnapper.removeOSnapPointsForPolar()

      # calcolo la dimensione dei simboli di snap in map unit
      self.__snapMarkerSizeInMapUnits = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE")) * \
                                        self.canvas.mapSettings().mapUnitsPerPixel()


   def refreshAutoSnap(self):
      self.setAutoSnap()


   #============================================================================
   # Dynamic Input
   #============================================================================
   def refreshDynamicInput(self):
      self.dynamicEditInput.refreshOnEnvVariables()


   #============================================================================
   # AutoSnap
   #============================================================================
   def setPolarAngOffset(self, polarAngOffset):
      self.__PolarAngOffset = polarAngOffset # per gestire l'angolo relativo all'ultimo segmento

      
   #============================================================================
   # getRealPolarAng
   #============================================================================
   def getRealPolarAng(self):
      # ritorna l'angolo polare che veramente deve essere usato tenendo conto delle variabili di sistema
      if self.__AutoSnap is None: return None
      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: return None # puntamento polare non attivato

      # il comportamento di QAD è uguale sia per i punti della linea che si sta disegnando che per i punti di osanp
      if (self.__PolarMode & QadPOLARMODEnum.POLAR_TRACKING): # usa POLARANG
         return self.__PolarAng
      else:
         return math.pi / 2 # 90 gradi (ortogonale)

      
   #============================================================================
   # getRealPolarAddAngles
   #============================================================================
   def getRealPolarAddAngles(self):
      # ritorna la lista degli angoli polari aggiuntivi che veramente deve essere usato tenendo conto delle variabili di sistema
      if self.__AutoSnap is None: return None
      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: return None # puntamento polare non attivato

      # il comportamento di QAD è uguale sia per i punti della linea che si sta disegnando che per i punti di osanp
      if (self.__PolarMode & QadPOLARMODEnum.POLAR_TRACKING): # usa POLARANG
         return self.__PolarAng
      else:
         return math.pi / 2 # 90 gradi (ortogonale)


   #============================================================================
   # getRealPolarAngOffset
   #============================================================================
   def getRealPolarAngOffset(self):
      # ritorna l'angolo polare di offset che veramente deve essere usato tenendo conto delle variabili di sistema
      if self.__AutoSnap is None: return None
      if (self.__AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING) == False: return None # puntamento polare non attivato

      if (self.__PolarMode is not None and self.__PolarMode & QadPOLARMODEnum.MEASURE_RELATIVE_ANGLE): # (relativo al coeff angolare dell'ultimo segmento)
         return self.__PolarAngOffset 
      else:
         return 0 # 0 gradi (assoluto)
      

   #============================================================================
   # setCursorType
   #============================================================================
   def setCursorType(self, cursorType):
      if self.__csrRubberBand is not None:
         self.__csrRubberBand.removeItems() # prima lo stacco dal canvas altrimenti non si rimuove perchè usato da canvas
         del self.__csrRubberBand
      self.__csrRubberBand = QadCursorRubberBand(self.canvas, cursorType)
      
      if cursorType == QadCursorTypeEnum.NONE:
         self.__cursor = QCursor(Qt.ArrowCursor)
      else:
         self.__cursor = QCursor(Qt.BlankCursor)
      self.__cursorType = cursorType
      

   #============================================================================
   # getCursorType
   #============================================================================
   def getCursorType(self):
      return self.__cursorType

    
   #============================================================================
   # moveElastic
   #============================================================================
   def moveElastic(self, point):
      numberOfVertices = self.__RubberBand.numberOfVertices()
      if numberOfVertices > 0:
         if numberOfVertices == 2:
            # per un baco non ancora capito: se la linea ha solo 2 vertici e 
            # hanno la stessa x o y (linea orizzontale o verticale) 
            # la linea non viene disegnata perciò sposto un pochino la x o la y         
            adjustedPoint = qad_utils.getAdjustedRubberBandVertex(self.__RubberBand.getPoint(0, 0), point)                     
            self.__RubberBand.movePoint(numberOfVertices - 1, adjustedPoint)
         else:
            p1 = self.__RubberBand.getPoint(0, 0)

            # se l'obiettivo é selezionare un gruppo di selezione
            if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITYSET_SELECTION:
               if point.x() > p1.x(): # se il punto è a destra di p1 (punto iniziale)
                  self.__RubberBand.setFillColor(self.rectangleWindowSelectionColor)
               else:
                  self.__RubberBand.setFillColor(self.rectangleCrossingSelectionColor)
            
            adjustedPoint = qad_utils.getAdjustedRubberBandVertex(p1, point)                     
            self.__RubberBand.movePoint(numberOfVertices - 3, QgsPointXY(p1.x(), adjustedPoint.y()))
            self.__RubberBand.movePoint(numberOfVertices - 2, adjustedPoint)
            self.__RubberBand.movePoint(numberOfVertices - 1, QgsPointXY(adjustedPoint.x(), p1.y()))            

            
   #============================================================================
   # getStartPoint
   #============================================================================
   def getStartPoint(self):
      return None if self.__startPoint is None else QgsPointXY(self.__startPoint) # alloca
   
   
   #============================================================================
   # setStartPoint
   #============================================================================
   def setStartPoint(self, startPoint):
      self.__startPoint = startPoint
      self.__QadSnapper.setStartPoint(startPoint)
      
      if self.getDrawMode() == QadGetPointDrawModeEnum.ELASTIC_LINE:
         # previsto uso della linea elastica
         self.__RubberBand.reset(QgsWkbTypes.LineGeometry)
         #numberOfVertices = self.__RubberBand.numberOfVertices()
         #if numberOfVertices == 2:
         #   self.__RubberBand.removeLastPoint()
         #   self.__RubberBand.removeLastPoint()
         self.__RubberBand.addPoint(startPoint, False)
         
         point = self.toMapCoordinates(self.canvas.mouseLastXY()) # posizione
         # per un baco non ancora capito: se la linea ha solo 2 vertici e 
         # hanno la stessa x o y (linea orizzontale o verticale) 
         # la linea non viene disegnata perciò sposto un pochino la x o la y
         point = qad_utils.getAdjustedRubberBandVertex(startPoint, point)
                
         self.__RubberBand.addPoint(point, True)
         
         # input dinamico
         self.dynamicEditInput.setPrevPoint(startPoint)
         if self.dynamicEditInput.isActive() and self.dynamicEditInput.isVisible:
            self.dynamicEditInput.show(True, self.canvas.mouseLastXY()) # visualizzo e resetto input dinamico
      elif self.getDrawMode() == QadGetPointDrawModeEnum.ELASTIC_RECTANGLE:
         # previsto uso del rettangolo elastico
         point = self.toMapCoordinates(self.canvas.mouseLastXY())

         self.__RubberBand.reset(QgsWkbTypes.PolygonGeometry)
         self.__RubberBand.addPoint(startPoint, False)
         
         # per un baco non ancora capito: se la linea ha solo 2 vertici e 
         # hanno la stessa x o y (linea orizzontale o verticale) 
         # la linea non viene disegnata perciò sposto un pochino la x o la y
         point = qad_utils.getAdjustedRubberBandVertex(startPoint, point)
                
         self.__RubberBand.addPoint(QgsPointXY(startPoint.x(), point.y()), False)
         self.__RubberBand.addPoint(point, False)
         self.__RubberBand.addPoint(QgsPointXY(point.x(), startPoint.y()), True)

         # input dinamico
         self.dynamicEditInput.setPrevPoint(None)
      else:
         #input dinamico
         self.dynamicEditInput.setPrevPoint(None)
         
         
      self.__QadSnapPointsDisplayManager.setStartPoint(startPoint)


   #============================================================================
   # toggleReferenceLines
   #============================================================================
   def toggleReferenceLines(self, geom, oSnapPointsForPolar = None, shiftKey = None):
      if self.__stopTimer == False and (geom is not None):
         if self.__QadSnapper is not None:
            if self.__AutoSnap & QadAUTOSNAPEnum.OBJ_SNAP_TRACKING: # se abilitato l'utilizzo del modo i punti di snap per l'uso polare
               if self.__PolarMode is not None and self.__PolarMode & QadPOLARMODEnum.SHIFT_TO_ACQUIRE: # acquisisce i punti di snap per l'uso polare solo se premuto shift
                  useOSnapPointsForPolar = True if shiftKey else False
               else: # acquisisce i punti di snap per l'uso polare automaticamente               
                  useOSnapPointsForPolar = True
            else: # se NON abilitato l'utilizzo del modo i punti di snap per l'uso polare
               useOSnapPointsForPolar = False
            
            # prendo la posizione attuale del mouse perchè per attivare o disattivare i punti di snap per l'uso polare
            # devo essere dentro il simbolo di snap invece questa funzione viene attivata non appena sono in prossimità della geometria
            # (vedi variabile di sistema APERTURE) e quindi quando il mouse può essere ancora lontano dal punto di snap
            point = self.toMapCoordinates(self.canvas.mouseLastXY())
            if useOSnapPointsForPolar:
               self.__QadSnapper.toggleReferenceLines(geom, point, oSnapPointsForPolar, self.__snapMarkerSizeInMapUnits)
            else:
               self.__QadSnapper.toggleReferenceLines(geom, point)
               
            self.__QadSnapper.toggleIntExtLinearObj(geom, point)
      

   #============================================================================
   # magneticCursor
   #============================================================================
   def magneticCursor(self, oSnapPoints):
      if len(oSnapPoints) > 0:               
         for item in oSnapPoints.items():
            for pt in item[1]:
               # il punto <point> deve essere dentro il punto di snap che ha dimensioni snapMarkerSizeInMapUnits
               if self.tmpPoint.x() >= pt.x() - self.__snapMarkerSizeInMapUnits and \
                  self.tmpPoint.x() <= pt.x() + self.__snapMarkerSizeInMapUnits and \
                  self.tmpPoint.y() >= pt.y() - self.__snapMarkerSizeInMapUnits and \
                  self.tmpPoint.y() <= pt.y() + self.__snapMarkerSizeInMapUnits:
                  self.tmpPoint.set(pt.x(), pt.y())
                  if self.__csrRubberBand is not None: 
                     self.__csrRubberBand.moveEvent(self.tmpPoint)


   #============================================================================
   # canvasMoveEvent
   #============================================================================
   def canvasMoveEvent(self, event):
      self.tmpPoint = self.toMapCoordinates(event.pos())
      if self.__csrRubberBand is not None:
         self.__csrRubberBand.moveEvent(self.tmpPoint)

      # tasto shift premuto durante il movimento del mouse
      self.tmpShiftKey = True if event.modifiers() & Qt.ShiftModifier else False
      # tasto ctrl premuto durante il movimento del mouse
      self.tmpCtrlKey = True if event.modifiers() & Qt.ControlModifier else False
      
      # se l'obiettivo é selezionare un punto
      if self.getSelectionMode() == QadGetPointSelectionModeEnum.POINT_SELECTION or \
         self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITYSET_SELECTION:
         return self.canvasMoveEventOnPointSel(event)
      elif self.getSelectionMode() == QadGetPointSelectionModeEnum.NONE:
         self.dynamicEditInput.mouseMoveEvent(event.pos())
      # se l'obiettivo é selezionare una o più entità
      else: 
         return self.canvasMoveEventOnEntitySel(event)


   #============================================================================
   # canvasMoveEventOnEntitySel
   #============================================================================
   def canvasMoveEventOnEntitySel(self, event):
      self.dynamicEditInput.mouseMoveEvent(event.pos())
      # start = time.time() # test
      self.tmpEntity.clear()

      # start1 = time.time() # test
      
      # se l'obiettivo é selezionare un'entità in modo dinamico
      if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC:
         result = qad_utils.getEntSel(event.pos(), self, \
                                      QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                      self.layersToCheck, \
                                      self.checkPointLayer, \
                                      self.checkLineLayer, \
                                      self.checkPolygonLayer, \
                                      True, self.onlyEditableLayers, \
                                      self.lastLayerFound, self.layerCacheGeomsDict)
      else:
         result = None
         
      #self.tempo1 += ((time.time() - start1) * 1000) # test
              
      # se è stata trovata una geometria
      if result is not None:         
         feature = result[0]
         layer = result[1]
         self.lastLayerFound = layer
         self.tmpEntity.set(layer, feature.id())
                  
      if self.getDrawMode() != QadGetPointDrawModeEnum.NONE:
         # previsto uso della linea elastica o rettangolo elastico
         self.moveElastic(self.tmpPoint)

      # self.tempo_tot += ((time.time() - start) * 1000) # test


   #============================================================================
   # canvasMoveEventOnPointSel
   #============================================================================
   def canvasMoveEventOnPointSel(self, event):
      self.dynamicEditInput.mouseMoveEvent(event.pos())

      # start = time.time() # test     
      result = qad_utils.getEntSel(event.pos(), self, \
                                   QadVariables.get(QadMsg.translate("Environment variables", "APERTURE")), \
                                   None, \
                                   self.__geometryTypesAccordingToSnapType[0], \
                                   self.__geometryTypesAccordingToSnapType[1], \
                                   self.__geometryTypesAccordingToSnapType[2], \
                                   True, False, \
                                   self.lastLayerFound, self.layerCacheGeomsDict, True)
         
      #self.tempo1 += ((time.time() - start1) * 1000) # test

      # se è stata trovata una geometria
      if result is not None:
         feature = result[0]
         layer = result[1]
         self.lastLayerFound = layer
         if self.layerCacheGeomsDict is not None:
            self.tmpEntity.set(layer, feature.attribute("index")) # leggendo la feature dalla cache in index trovo il codice della feature reale
         else:
            self.tmpEntity.set(layer, feature.id()) # leggendo la feature direttamente dalla classe
         
         geometry = self.tmpEntity.getGeometry(self.canvas.mapSettings().destinationCrs()) # trasformo la geometria in map coordinate
         point = self.toMapCoordinates(event.pos()) # trasformo il punto da screen coordinate a map coordinate
         
         oSnapPoints = self.__QadSnapper.getSnapPoint(self.tmpEntity, point, \
                                                      None, \
                                                      self.getRealPolarAng(), \
                                                      self.getRealPolarAngOffset(), \
                                                      self.__PolarAddAngles)

         if self.__AutoSnap & QadAUTOSNAPEnum.MAGNET: # Turns on the AutoSnap magnet
            self.magneticCursor(oSnapPoints)
         
         # se é stata selezionata una geometria diversa da quella selezionata precedentemente
         if (self.__prevGeom is None) or not self.__prevGeom.equals(geometry):
            self.__prevGeom = QgsGeometry(geometry)
            runToggleReferenceLines = lambda: self.toggleReferenceLines(self.__prevGeom, oSnapPoints, self.tmpShiftKey)
            self.__stopTimer = False
            QTimer.singleShot(500, runToggleReferenceLines)      
      else: # se NON è stata trovata una geometria
         # start1 = time.time() # test
         
         # se non é stata trovato alcun oggetto allora verifico se una geometria di tmpGeometries rientra nella casella aperture
         boxSize = QadVariables.get(QadMsg.translate("Environment variables", "APERTURE")) # leggo la dimensione del quadrato (in pixel)
         tmpGeometry = qad_utils.getGeomInBox(event.pos(),
                                              self, \
                                              self.tmpGeometries, \
                                              boxSize, \
                                              None, \
                                              self.__geometryTypesAccordingToSnapType[0], \
                                              self.__geometryTypesAccordingToSnapType[1], \
                                              self.__geometryTypesAccordingToSnapType[2], \
                                              True)
         
         #self.tempo2 += ((time.time() - start1) * 1000) # test
         
         if tmpGeometry is not None:
            oSnapPoints = self.__QadSnapper.getSnapPoint(tmpGeometry, self.tmpPoint, \
                                                         None, \
                                                         self.getRealPolarAng(), \
                                                         self.getRealPolarAngOffset(), \
                                                         self.__PolarAddAngles, \
                                                         True)

            if self.__AutoSnap & QadAUTOSNAPEnum.MAGNET: # Turns on the AutoSnap magnet
               self.magneticCursor(oSnapPoints)

            # se é stata selezionata una geometria diversa da quella selezionata precedentemente
            if (self.__prevGeom is None) or not self.__prevGeom.equals(tmpGeometry):
               self.__prevGeom = QgsGeometry(tmpGeometry)
               runToggleReferenceLines = lambda: self.toggleReferenceLines(self.__prevGeom, \
                                                                           oSnapPoints, self.tmpShiftKey)
               self.__stopTimer = False
               QTimer.singleShot(500, runToggleReferenceLines)
         else: # se NON è stata trovata una geometria temporanea (la stessa che si sta disegnando)
            oSnapPoints = self.__QadSnapper.getSnapPoint(None, self.tmpPoint, \
                                                         None, \
                                                         self.getRealPolarAng(), \
                                                         self.getRealPolarAngOffset(), \
                                                        self.__PolarAddAngles)

            if self.__AutoSnap & QadAUTOSNAPEnum.MAGNET: # Turns on the AutoSnap magnet
               self.magneticCursor(oSnapPoints)

            self.__prevGeom = None
            self.__stopTimer = True

      oSnapPoint = None

      # visualizzo il punto di snap
      self.__QadSnapPointsDisplayManager.show(oSnapPoints, \
                                              self.__QadSnapper.getExtLinearObjs(), \
                                              self.__QadSnapper.getParLines(), \
                                              self.__QadSnapper.getIntExtLinearObjs(), \
                                              self.__QadSnapper.getOSnapPointsForPolar(), \
                                              self.__QadSnapper.getOSnapLinesForPolar())

      self.point = None
      self.tmpPoint = None
      # memorizzo il punto di snap in point (prendo il primo valido)
      for item in oSnapPoints.items():
         points = item[1]
         if points is not None:
            self.tmpPoint = points[0]
            oSnapPoint = points[0]
            break
      
      # se non è stato trovato alcun punto di osnap
      if self.tmpPoint is None:
         # se si sta usando input dinamico che restituisce un risultato puntuale
         if self.dynamicEditInput.isActive() and self.dynamicEditInput.isVisible and \
            (self.dynamicEditInput.inputType & QadInputTypeEnum.POINT2D or self.dynamicEditInput.inputType & QadInputTypeEnum.POINT3D) and \
            self.dynamicEditInput.refreshResult(event.pos()) == True:
            self.tmpPoint = QgsPointXY(self.dynamicEditInput.resPt)
         else: # prendo il punto direttamente dal mouse
            self.tmpPoint = self.toMapCoordinates(event.pos())

      if oSnapPoint is None: # se non c'è un punto di osnap
         if self.__startPoint is not None: # se c'é un punto di partenza
            if self.tmpShiftKey == False: # se non è premuto shift
               if self.__OrthoMode == 1: # orto attivato
                  self.tmpPoint = self.getOrthoCoord(self.tmpPoint)
            else: # se non è premuto shift devo fare il toggle di ortho
               if self.__OrthoMode == 0: # se orto disattivato lo attivo temporaneamente
                  self.tmpPoint = self.getOrthoCoord(self.tmpPoint)
                  
      if self.getDrawMode() != QadGetPointDrawModeEnum.NONE:
         # previsto uso della linea elastica o rettangolo elastico
         self.moveElastic(self.tmpPoint)

      # self.tempo_tot += ((time.time() - start) * 1000) # test


   #============================================================================
   # canvasPressEvent
   #============================================================================
   def canvasPressEvent(self, event):
      # tasto shift premuto durante il click del mouse
      self.shiftKey = True if event.modifiers() & Qt.ShiftModifier else False

      # tasto ctrl premuto durante il click del mouse
      self.ctrlKey = True if event.modifiers() & Qt.ControlModifier else False

      # volevo mettere questo evento nel canvasReleaseEvent
      # ma il tasto destro non genera quel tipo di evento
      if event.button() == Qt.RightButton:
         self.startDateTimeForRightClick = datetime.datetime.now()
         self.rightButton = True
         return # esco qui per non contiuare il comando dal maptool
      
      if event.button() == Qt.LeftButton:
         self.rightButton = False
              
         if self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC or \
            self.getSelectionMode() == QadGetPointSelectionModeEnum.ENTITY_SELECTION:
            self.tmpPoint = self.toMapCoordinates(event.pos())
            result = qad_utils.getEntSel(event.pos(), self, \
                                         QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                         self.layersToCheck, \
                                         self.checkPointLayer, \
                                         self.checkLineLayer, \
                                         self.checkPolygonLayer, \
                                         True, self.onlyEditableLayers, \
                                         self.lastLayerFound) # non uso self.layerCacheGeomsDict perchè se ho gli snap disattivati self.layerCacheGeomsDict è vuota
            if result is not None:
               feature = result[0]
               layer = result[1]
               self.tmpEntity.set(layer, feature.id())
         
         self.__QadSnapper.removeReferenceLines()
         self.__QadSnapPointsDisplayManager.hide()
   
         self.__setPoint(event)
            
         if self.__oldSnapType is not None:
            self.setSnapType(self.__oldSnapType) # riporto il valore precedente
            self.__QadSnapper.setProgressDistance(self.__oldSnapProgrDist)
            
      if self.M2P_Mode == True: # modo "punto medio tra 2 punti"
         if self.M2p_pt1 is None:
            self.M2p_pt1 = self.point
            self.plugIn.showMsg(QadMsg.translate("Snap", "Second point of mid: "))
         else:
            self.M2P_Mode = False
            self.point = qad_utils.getMiddlePoint(self.M2p_pt1, self.point)
            self.plugIn.setLastPoint(self.point)
            self.plugIn.QadCommands.continueCommandFromMapTool()
      else:
         self.plugIn.QadCommands.continueCommandFromMapTool()
         #self.plugIn.setStandardMapTool()


   #============================================================================
   # canvasReleaseEvent
   #============================================================================
   def canvasReleaseEvent(self, event):
      if event.button() == Qt.RightButton:
         self.rightButton = True
         # Se é stato premuto il tasto CTRL (o META)
         if ((event.modifiers() & Qt.ControlModifier) or (event.modifiers() & Qt.MetaModifier)):
            self.displayOsnapPopupMenu(event.pos())
            return # esco qui per non contiuare il comando dal maptool

         actualCommand = self.plugIn.QadCommands.actualCommand
         if actualCommand is not None:
            contextualMenu = actualCommand.getCurrentContextualMenu()
         else:
            contextualMenu = None
            
         shortCutMenu = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENU"))
         if shortCutMenu == 0 or contextualMenu is None:
            # equivale a premere INVIO
            return self.plugIn.showEvaluateMsg(None)
               
         # 16 = Enables the display of a shortcut menu when the right button on the pointing device is held down long enough
         if shortCutMenu & 16:
            now = datetime.datetime.now()
            value = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION"))
            shortCutMenuDuration = datetime.timedelta(0, 0, 0, value)
            # se supera il numero di millisecondi impostato da SHORTCUTMENUDURATION
            if now - self.startDateTimeForRightClick > shortCutMenuDuration:
               contextualMenu.popup(self.canvas.mapToGlobal(event.pos()))
               return # esco qui per non contiuare il comando dal maptool
            else:
               return self.plugIn.showEvaluateMsg(None)
         else:
            # 4 = Enables Command mode shortcut menus whenever a command is active. 
            if shortCutMenu & 4:
               contextualMenu.popup(self.canvas.mapToGlobal(event.pos()))
               return # esco qui per non contiuare il comando dal maptool
            else:
               # 8 = Enables Command mode shortcut menus only when command options are currently available at the Command prompt. 
               if shortCutMenu & 8 and contextualMenu is not None and len(contextualMenu.localKeyWords)>0:
                  contextualMenu.popup(self.canvas.mapToGlobal(event.pos()))
               else:
                  # equivale a premere INVIO
                  return self.plugIn.showEvaluateMsg(None)
      
      # se l'obiettivo é selezionare un rettangolo
      if self.getDrawMode() == QadGetPointDrawModeEnum.ELASTIC_RECTANGLE:                 
         if event.button() == Qt.LeftButton:
            p1 = self.__RubberBand.getPoint(0, 0)
            # se il mouse é in una posizione diversa dal punto iniziale del rettangolo
            if p1 != self.toMapCoordinates(event.pos()):
               self.__QadSnapper.removeReferenceLines()
               self.__QadSnapPointsDisplayManager.hide()
          
               self.__setPoint(event)
                   
               self.rightButton = False
                     
               if self.__oldSnapType is not None:
                  self.setSnapType(self.__oldSnapType) # riporto il valore precedente
                  self.__QadSnapper.setProgressDistance(self.__oldSnapProgrDist)
                   
               # tasto shift premuto durante il click del mouse
               self.shiftKey = True if event.modifiers() & Qt.ShiftModifier else False
         
               # tasto ctrl premuto durante il click del mouse
               self.ctrlKey = True if event.modifiers() & Qt.ControlModifier else False
               
               self.plugIn.QadCommands.continueCommandFromMapTool()
               #self.plugIn.setStandardMapTool()


   #============================================================================
   # __setPoint
   #============================================================================
   def __setPoint(self, event):
      # se non era mai stato mosso il mouse     
      if self.tmpPoint is None:        
         self.canvasMoveEvent(event)

      self.point = self.tmpPoint
      self.plugIn.setLastPoint(self.point)
      self.snapTypeOnSelection = self.getSnapType() # snap attivo al momento del click
      if self.tmpEntity.isInitialized():
         self.entity.set(self.tmpEntity.layer, self.tmpEntity.featureId)
      else:
         self.entity.clear()

   #============================================================================
   # keyPressEvent
   #============================================================================
   def keyPressEvent(self, e):
      myEvent = e
      # ALTGR non si può usare perchè è usato per indicare le coordinate
#       # if Key_AltGr is pressed, then perform the as return
#       if e.key() == Qt.Key_AltGr:
#          myEvent = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
#       else:
#          myEvent = e
      
      self.plugIn.keyPressEvent(myEvent)


   #============================================================================
   # activate
   #============================================================================
   def activate(self):
      self.canvas.setToolTip("")

      if self.__csrRubberBand is not None:
         # posizione corrente del mouse
         self.__csrRubberBand.moveEvent(self.toMapCoordinates(self.canvas.mouseLastXY()))
         self.__csrRubberBand.show()
            
      self.point = None
      self.tmpPoint = None

      self.entity = QadEntity() # entità selezionata dal click
      self.tmpEntity = QadEntity() # entità selezionata dal movimento del mouse
      
      self.snapTypeOnSelection = None # snap attivo al momento del click
      
      self.shiftKey = False
      self.tmpShiftKey = False # tasto shift premuto durante il movimento del mouse      

      self.ctrlKey = False
      self.tmpCtrlKey = False # tasto ctrl premuto durante il movimento del mouse      

      self.rightButton = False
      self.canvas.setCursor(self.__cursor)
      self.showPointMapToolMarkers()
      self.plugIn.disableShortcut()
      
      self.dynamicEditInput.show(True)


   #============================================================================
   # deactivate
   #============================================================================
   def deactivate(self):
      try: # necessario perché se si chiude QGIS parte questo evento nonostante non ci sia più l'oggetto maptool !
         if self.__csrRubberBand is not None:
            self.__csrRubberBand.hide()
         self.hidePointMapToolMarkers()
         self.plugIn.enableShortcut()
         
         self.dynamicEditInput.show(False)
      except:
         pass


   #============================================================================
   # isTransient
   #============================================================================
   def isTransient(self): # Check whether this MapTool performs a zoom or pan operation
      return False


   #============================================================================
   # isEditTool
   #============================================================================
   def isEditTool(self):
      # benchè questo tool faccia editing ritorno False perchè ogni volta che seleziono una feature
      # con la funzione QgsVectorLayer::select(QgsFeatureId featureId)
      # parte in sequenza la chiamata a isEditTool del tool corrente che se ritorna true viene disattivato
      # e poi riattivato QadMapTool che riprende il comando interrotto creando casino
      #return True # 2016
      return False
      

   #============================================================================
   # displayOsnapPopupMenu
   #============================================================================
   def displayOsnapPopupMenu(self, pos):
      popupMenu = QMenu(self.canvas)
      
      msg = QadMsg.translate("Snap", "Midpoint between 2 points")
      icon = QIcon(":/plugins/qad/icons/osnap_mid2p.svg")
      if icon is None:
         addEndLineSnapTypeAction = QAction(msg, popupMenu)
      else:
         addEndLineSnapTypeAction = QAction(icon, msg, popupMenu)
      addEndLineSnapTypeAction.triggered.connect(self.addM2PActionByPopupMenu)
      popupMenu.addAction(addEndLineSnapTypeAction)
      
      msg = QadMsg.translate("DSettings_Dialog", "Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_endLine.svg")
      if icon is None:
         addEndLineSnapTypeAction = QAction(msg, popupMenu)
      else:
         addEndLineSnapTypeAction = QAction(icon, msg, popupMenu)
      addEndLineSnapTypeAction.triggered.connect(self.addEndLineSnapTypeByPopupMenu)
      popupMenu.addAction(addEndLineSnapTypeAction)
      
      msg = QadMsg.translate("DSettings_Dialog", "Segment Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_end.svg")
      if icon is None:
         addEndSnapTypeAction = QAction(msg, popupMenu)
      else:
         addEndSnapTypeAction = QAction(icon, msg, popupMenu)        
      addEndSnapTypeAction.triggered.connect(self.addEndSnapTypeByPopupMenu)
      popupMenu.addAction(addEndSnapTypeAction)
      
      msg = QadMsg.translate("DSettings_Dialog", "Middle point")
      icon = QIcon(":/plugins/qad/icons/osnap_mid.svg")
      if icon is None:
         addMidSnapTypeAction = QAction(msg, popupMenu)
      else:
         addMidSnapTypeAction = QAction(icon, msg, popupMenu)        
      addMidSnapTypeAction.triggered.connect(self.addMidSnapTypeByPopupMenu)
      popupMenu.addAction(addMidSnapTypeAction)
      
      msg = QadMsg.translate("DSettings_Dialog", "Intersection")
      icon = QIcon(":/plugins/qad/icons/osnap_int.svg")
      if icon is None:
         addIntSnapTypeAction = QAction(msg, popupMenu)
      else:
         addIntSnapTypeAction = QAction(icon, msg, popupMenu)        
      addIntSnapTypeAction.triggered.connect(self.addIntSnapTypeByPopupMenu)
      popupMenu.addAction(addIntSnapTypeAction)
      
      msg = QadMsg.translate("DSettings_Dialog", "Intersection on extension")
      icon = QIcon(":/plugins/qad/icons/osnap_extInt.svg")
      if icon is None:
         addExtIntSnapTypeAction = QAction(msg, popupMenu)
      else:
         addExtIntSnapTypeAction = QAction(icon, msg, popupMenu)        
      addExtIntSnapTypeAction.triggered.connect(self.addExtIntSnapTypeByPopupMenu)
      popupMenu.addAction(addExtIntSnapTypeAction)
      
      msg = QadMsg.translate("DSettings_Dialog", "Extend")
      icon = QIcon(":/plugins/qad/icons/osnap_ext.svg")
      if icon is None:
         addExtSnapTypeAction = QAction(msg, popupMenu)
      else:
         addExtSnapTypeAction = QAction(icon, msg, popupMenu)        
      addExtSnapTypeAction.triggered.connect(self.addExtSnapTypeByPopupMenu)
      popupMenu.addAction(addExtSnapTypeAction)

      popupMenu.addSeparator()
     
      msg = QadMsg.translate("DSettings_Dialog", "Center")
      icon = QIcon(":/plugins/qad/icons/osnap_cen.svg")
      if icon is None:
         addCenSnapTypeAction = QAction(msg, popupMenu)
      else:
         addCenSnapTypeAction = QAction(icon, msg, popupMenu)        
      addCenSnapTypeAction.triggered.connect(self.addCenSnapTypeByPopupMenu)
      popupMenu.addAction(addCenSnapTypeAction)
     
      msg = QadMsg.translate("DSettings_Dialog", "Quadrant")
      icon = QIcon(":/plugins/qad/icons/osnap_qua.svg")
      if icon is None:
         addQuaSnapTypeAction = QAction(msg, popupMenu)
      else:
         addQuaSnapTypeAction = QAction(icon, msg, popupMenu)        
      addQuaSnapTypeAction.triggered.connect(self.addQuaSnapTypeByPopupMenu)
      popupMenu.addAction(addQuaSnapTypeAction)
     
      msg = QadMsg.translate("DSettings_Dialog", "Tangent")
      icon = QIcon(":/plugins/qad/icons/osnap_tan.svg")
      if icon is None:
         addTanSnapTypeAction = QAction(msg, popupMenu)
      else:
         addTanSnapTypeAction = QAction(icon, msg, popupMenu)        
      addTanSnapTypeAction.triggered.connect(self.addTanSnapTypeByPopupMenu)
      popupMenu.addAction(addTanSnapTypeAction)

      popupMenu.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Perpendicular")
      icon = QIcon(":/plugins/qad/icons/osnap_per.svg")
      if icon is None:
         addPerSnapTypeAction = QAction(msg, popupMenu)
      else:
         addPerSnapTypeAction = QAction(icon, msg, popupMenu)        
      addPerSnapTypeAction.triggered.connect(self.addPerSnapTypeByPopupMenu)
      popupMenu.addAction(addPerSnapTypeAction)     

      msg = QadMsg.translate("DSettings_Dialog", "Parallel")
      icon = QIcon(":/plugins/qad/icons/osnap_par.svg")
      if icon is None:
         addParSnapTypeAction = QAction(msg, popupMenu)
      else:
         addParSnapTypeAction = QAction(icon, msg, popupMenu)        
      addParSnapTypeAction.triggered.connect(self.addParSnapTypeByPopupMenu)
      popupMenu.addAction(addParSnapTypeAction)     

      msg = QadMsg.translate("DSettings_Dialog", "Node")
      icon = QIcon(":/plugins/qad/icons/osnap_nod.svg")
      if icon is None:
         addNodSnapTypeAction = QAction(msg, popupMenu)
      else:
         addNodSnapTypeAction = QAction(icon, msg, popupMenu)        
      addNodSnapTypeAction.triggered.connect(self.addNodSnapTypeByPopupMenu)
      popupMenu.addAction(addNodSnapTypeAction)     

      msg = QadMsg.translate("DSettings_Dialog", "Near")
      icon = QIcon(":/plugins/qad/icons/osnap_nea.svg")
      if icon is None:
         addNeaSnapTypeAction = QAction(msg, popupMenu)
      else:
         addNeaSnapTypeAction = QAction(icon, msg, popupMenu)        
      addNeaSnapTypeAction.triggered.connect(self.addNeaSnapTypeByPopupMenu)
      popupMenu.addAction(addNeaSnapTypeAction)     

      msg = QadMsg.translate("DSettings_Dialog", "Progressive")
      icon = QIcon(":/plugins/qad/icons/osnap_pr.svg")
      if icon is None:
         addPrSnapTypeAction = QAction(msg, popupMenu)
      else:
         addPrSnapTypeAction = QAction(icon, msg, popupMenu)        
      addPrSnapTypeAction.triggered.connect(self.addPrSnapTypeByPopupMenu)
      popupMenu.addAction(addPrSnapTypeAction)     

      msg = QadMsg.translate("DSettings_Dialog", "None")
      icon = QIcon(":/plugins/qad/icons/osnap_disable.svg")
      if icon is None:
         setSnapTypeToDisableAction = QAction(msg, popupMenu)
      else:
         setSnapTypeToDisableAction = QAction(icon, msg, popupMenu)        
      setSnapTypeToDisableAction.triggered.connect(self.setSnapTypeToDisableByPopupMenu)
      popupMenu.addAction(setSnapTypeToDisableAction)     

      popupMenu.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Object snap settings...")
      icon = QIcon(":/plugins/qad/icons/dsettings.svg")
      if icon is None:
         DSettingsAction = QAction(msg, popupMenu)
      else:
         DSettingsAction = QAction(icon, msg, popupMenu)        
      DSettingsAction.triggered.connect(self.showDSettingsByPopUpMenu)
      popupMenu.addAction(DSettingsAction)     
            
      popupMenu.popup(self.canvas.mapToGlobal(pos))
         

   #============================================================================
   # addSnapTypeByPopupMenu
   #============================================================================
   def addSnapTypeByPopupMenu(self, _snapType):
      # la funzione deve impostare lo snap ad oggetto solo temporaneamente
      str = snapTypeEnum2Str(_snapType)
      self.plugIn.showEvaluateMsg(str)
      return
#       value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
#       if value & QadSnapTypeEnum.DISABLE:
#          value =  value - QadSnapTypeEnum.DISABLE      
#       QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | _snapType)
#       QadVariables.save()      
#       self.refreshSnapType()
         
   def addM2PActionByPopupMenu(self):
      self.plugIn.showEvaluateMsg("_M2P")          
   def addEndLineSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END_PLINE)
   def addEndSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END)
   def addMidSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.MID)
   def addIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.INT)      
   def addExtIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT_INT)
   def addExtSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT)   
   def addCenSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.CEN)      
   def addQuaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.QUA)
   def addTanSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.TAN)
   def addPerSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PER)
   def addParSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PAR)
   def addNodSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NOD)
   def addNeaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NEA)
   def addPrSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PR)


   #============================================================================
   # setSnapTypeToDisableByPopupMenu
   #============================================================================
   def setSnapTypeToDisableByPopupMenu(self):      
      value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
      QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | QadSnapTypeEnum.DISABLE)
      QadVariables.save()      
      self.refreshSnapType()


   #============================================================================
   # showDSettingsByPopUpMenu
   #============================================================================
   def showDSettingsByPopUpMenu(self):
      d = QadDSETTINGSDialog(self.plugIn, QadDSETTINGSTabIndexEnum.OBJECT_SNAP)
      d.exec_()
      self.refreshSnapType()
      self.refreshAutoSnap()
      self.setPolarAngOffset(self.plugIn.lastSegmentAng)
      self.refreshDynamicInput()


   #============================================================================
   # mapToLayerCoordinates
   #============================================================================
   def mapToLayerCoordinates(self, layer, point_geom):
      # transform point o geometry coordinates from output CRS to layer's CRS 
      if self.canvas is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.canvas.mapSettings().mapToLayerCoordinates(layer, point_geom)
      elif type(point_geom) == QgsGeometry:         
         fromCrs = self.canvas.mapSettings().destinationCrs()
         toCrs = layer.crs()
         
         if fromCrs == toCrs:
            return QgsGeometry(point_geom)
                  
         # trasformo la geometria nel crs del canvas per lavorare con coordinate piane xy
         coordTransform = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      else:
         return None


   #============================================================================
   # layerToMapCoordinates
   #============================================================================
   def layerToMapCoordinates(self, layer, point_geom):
      # transform point o geometry coordinates from layer's CRS to output CRS 
      if self.canvas is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.canvas.mapSettings().layerToMapCoordinates(layer, point_geom)
      elif type(point_geom) == QgsGeometry:
         # trasformo la geometria nel crs del canvas per lavorare con coordinate piane xy
         coordTransform = QgsCoordinateTransform(layer.crs(), \
                                                 self.canvas.mapSettings().destinationCrs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      else:
         return None
