# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando ARRAY per copiare serie di oggetti
 
                              -------------------
        begin                : 2016-05-03
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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsPointXY


import math


from .. import qad_array_fun
from .. import qad_layer
from .. import qad_utils
from .qad_array_maptool import Qad_array_maptool, Qad_array_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_polyline import QadPolyline
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass
from .qad_entsel_cmd import QadEntSelClass
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_ssget_cmd import QadSSGetClass
from ..qad_entity import QadCacheEntitySet, QadCacheEntitySetIterator, QadEntityTypeEnum
from ..qad_variables import QadVariables, QadDELOBJEnum
from ..qad_dim import QadDimStyles, appendDimEntityIfNotExisting
from ..qad_geom_relations import getQadGeomClosestPart
from ..qad_multi_geom import getQadGeomAt


#===============================================================================
# QadARRAYCommandClassSeriesTypeEnum class.
#===============================================================================
class QadARRAYCommandClassSeriesTypeEnum():
   RECTANGLE = 1 # serie rettangolare
   PATH      = 2 # serie lungo una traiettoria
   POLAR     = 3 # serie polare


#===============================================================================
# QadARRAYCommandClassPathMethodTypeEnum class.
#===============================================================================
class QadARRAYCommandClassPathMethodTypeEnum():
   DIVIDE  = 1 # metodo dividi
   MEASURE = 2 # metodo misura


#===============================================================================
# QadARRAYCommandClassStepEnum class.
#===============================================================================
class QadARRAYCommandClassStepEnum():
   ASK_FOR_SELSET                = 0  # richiede il gruppo di selezione ogggetti (deve essere = 0 perchè è l'inizio del comando)
   ASK_FOR_ARRAYTYPE             = 1  # richiede il tipo di serie
   ASK_FOR_ROW_N                 = 2  # richiede il numero di righe (per rettangolo, traiettoria, polare)
   ASK_FOR_ROW_SPACE_OR_TOT      = 3  # richiede la distanza tra le righe o il totale (per rettangolo, traiettoria, polare)
   ASK_FOR_ROW_SPACE_TOT         = 4  # richiede il totale della spaziatura delle righe (per rettangolo, traiettoria)
   ASK_FOR_ROW_SPACE_2PT         = 5  # richiede il secondo punto per misurare la distanza tra le righe
   ASK_FOR_BASE_PT               = 6  # richiede il punto base (per rettangolo, traiettoria, polare)
   ASK_FOR_MAIN_OPTIONS          = 7  # richiede di selezionare un'opzione (per rettangolo, traiettoria, polare)
   ASK_FOR_ITEM_N                = 8  # richiede il numero di elementi lungo la traiettoria (per traiettoria, polare)
   ASK_FOR_ITEM_ROTATION         = 9  # richiede se gli elementi devono essere allineati (per traiettoria, polare)
   ASK_FOR_DEL_ORIG_OBJS         = 10 # richiede se gli elementi originali devono essere cancellati (per rettangolo, traiettoria, polare)
   ASK_FOR_BASE_PT_BEFORE_MAIN_OPTIONS = 29 # richiede il punto base prima delle opzioni (per polare)
   # RETTANGOLO
   ASK_FOR_ANGLE                 = 11 # richiede l'angolo di rotazione dell'asse delle righe
   ASK_FOR_COLUMN_COUNT          = 12 # richiede il numero di colonne dall'opzione COUNT
   ASK_FOR_COLUMN_N              = 13 # richiede il numero di colonne dall'opzione COLUMN
   ASK_FOR_COLUMN_SPACE_OR_CELL  = 14 # richiede la distanza tra le colonne o l'unità di cella
   ASK_FOR_COLUMN_SPACE_2PT      = 15 # richiede il secondo punto per misurare la distanza tra le colonne
   ASK_FOR_ROW_COUNT             = 16 # richiede il numero di righe dall'opzione COUNT
   ASK_FOR_ROW_SPACE             = 17 # richiede la distanza tra le righe
   ASK_FOR_1PT_CELL              = 18 # richiede il primo angolo della cella
   ASK_FOR_2PT_CELL              = 19 # richiede il secondo angolo della cella
   ASK_FOR_COLUMN_SPACE_OR_TOT   = 20 # richiede la distanza tra le colonne o il totale
   ASK_FOR_COLUMN_SPACE_TOT      = 21 # richiede il totale della spaziatura delle colonne
   # TRAIETTORIA
   ASK_FOR_PATH_OBJ              = 22 # richiede la selezione dell'oggetto traiettoria
   ASK_FOR_PATH_METHOD           = 23 # richiede il metodo
   ASK_FOR_TAN_DIRECTION         = 24 # richiede la selezione della direzione della tangente
   ASK_FOR_ITEM_SPACE            = 25 # richiede la distanza tra gli elementi
   # POLARE
   ASK_FOR_CENTER_PT             = 26 # richiede la selezione del punto centrale della serie
   ASK_FOR_ANGLE_BETWEEN_ITEMS   = 27 # richiede la selezione dell'angolo tra gli elementi
   ASK_FOR_FULL_ANGLE            = 28 # richiede la selezione dell'angolo da riempire
   


# Classe che gestisce il comando ARRAY
class QadARRAYCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadARRAYCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ARRAY")

   def getEnglishName(self):
      return "ARRAY"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runARRAYCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/arrayRect.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_ARRAY", "Creates copies of objects in a regularly spaced rectangular, polar, or path array.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.entSelClass = None
      self.cacheEntitySet = QadCacheEntitySet()
      self.defaultValue = None
      
      self.basePt = QgsPointXY()      
      self.arrayType = self.plugIn.lastArrayType_array
      self.distanceBetweenRows = None
      self.distanceBetweenCols = None
      self.itemsRotation = self.plugIn.lastItemsRotation_array
      self.delObj = QadVariables.get(QadMsg.translate("Environment variables", "DELOBJ"))
      self.delOrigSelSet = False
      if self.delObj == QadDELOBJEnum.DELETE_ALL: # Delete all defining geometry
         self.delOrigSelSet = True

      # serie rettangolare
      self.rectangleAngle = self.plugIn.lastRectangleAngle_array
      self.rectangleCols = self.plugIn.lastRectangleCols_array
      self.rectangleRows = self.plugIn.lastRectangleRows_array
      self.firstPt = QgsPointXY() # primo punto per misurare la distanza tra righe
      
      # serie traiettoria
      self.pathTangentDirection = self.plugIn.lastPathTangentDirection_array
      self.pathRows = self.plugIn.lastPathRows_array
      self.pathItemsNumber = 1
      self.pathPolyline = QadPolyline()
      self.pathMethod = QadARRAYCommandClassPathMethodTypeEnum.MEASURE
      self.distanceFromStartPt = 0.0 # uso interno quando si imposta il metodo dividi
      
      # serie polare
      self.centerPt = QgsPointXY()
      self.polarItemsNumber = self.plugIn.lastPolarItemsNumber_array
      self.polarAngleBetween = self.plugIn.lastPolarAngleBetween_array
      self.polarRows = self.plugIn.lastPolarRows_array
      
      self.GetDistClass = None
      self.GetAngleClass = None
      
      self.featureCache = [] # lista di (layer, feature)

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.SSGetClass is not None:
         del self.SSGetClass
      
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()
      # quando si é in fase di richiesta rotazione
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_TAN_DIRECTION or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE_BETWEEN_ITEMS or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_FULL_ANGLE:
         return self.GetAngleClass.getPointMapTool()
      # quando si é in fase di richiesta distanza
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_2PT or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_TOT or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_TOT or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_SPACE or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_2PT:
         return self.GetDistClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_array_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta rotazione
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_TAN_DIRECTION or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE_BETWEEN_ITEMS or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_FULL_ANGLE:
         return self.GetAngleClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta distanza
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_2PT or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_TOT or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_TOT or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_SPACE or \
           self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_2PT:
         return self.GetDistClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   #============================================================================
   # updatePointMapToolParams
   #============================================================================
   def updatePointMapToolParams(self):
      self.step = -1 * self.step # trucchetto per prendere il map tool base
      self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato da altri maptool
      
      self.getPointMapTool().cacheEntitySet = self.cacheEntitySet
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().arrayType = self.arrayType
      self.getPointMapTool().distanceBetweenRows = self.distanceBetweenRows
      self.getPointMapTool().distanceBetweenCols = self.distanceBetweenCols
      self.getPointMapTool().itemsRotation = self.itemsRotation

      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE: # serie rettangolare
         self.getPointMapTool().rectangleAngle = self.rectangleAngle
         self.getPointMapTool().rectangleCols = self.rectangleCols
         self.getPointMapTool().rectangleRows = self.rectangleRows
         self.getPointMapTool().firstPt = self.firstPt
         self.getPointMapTool().doRectangleArray()
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH: # serie traiettoria
         self.getPointMapTool().pathTangentDirection = self.pathTangentDirection
         self.getPointMapTool().pathRows = self.pathRows
         self.getPointMapTool().pathItemsNumber = self.pathItemsNumber
         self.getPointMapTool().pathPolyline = self.pathPolyline
         self.getPointMapTool().distanceFromStartPt = self.distanceFromStartPt
         self.getPointMapTool().doPathArray()
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR: # serie polare
         self.getPointMapTool().centerPt = self.centerPt
         self.getPointMapTool().polarItemsNumber = self.polarItemsNumber
         self.getPointMapTool().polarAngleBetween = self.polarAngleBetween
         self.getPointMapTool().polarRows = self.polarRows
         self.getPointMapTool().doPolarArray()

      self.step = -1 * self.step # trucchetto per prendere il map tool base


   #============================================================================
   # setEntitySet
   #============================================================================
   def setEntitySet(self, ss):
      self.cacheEntitySet.clear()
      self.cacheEntitySet.appendEntitySet(ss)
      rect = self.cacheEntitySet.getBoundingBox()
      self.distanceBetweenRows = rect.height() + (rect.height() / 2) if rect.height() != 0 else 1
      self.distanceBetweenCols = rect.width() + (rect.width() / 2) if rect.width() != 0 else 1
      center = rect.center()
      self.basePt.setX(center.x())
      self.basePt.setY(center.y())


   #============================================================================
   # doRectangleArray
   #============================================================================
   def doRectangleArray(self):
      self.plugIn.beginEditCommand("Feature copied", self.cacheEntitySet.getLayerList())

      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if qad_array_fun.arrayRectangleEntity(self.plugIn, entity, self.basePt, self.rectangleRows, self.rectangleCols, \
                                               self.distanceBetweenRows, self.distanceBetweenCols, self.rectangleAngle, self.itemsRotation,
                                               True, None) == False:
            self.plugIn.destroyEditCommand()
            return

      if self.delOrigSelSet: # se devo rimuovere gli oggetti originali
         entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
         for entity in entityIterator:
            if qad_layer.deleteFeatureToLayer(self.plugIn, entity.layer, entity.featureId, False) == False:
               self.plugIn.destroyEditCommand()
               return
         
      self.plugIn.endEditCommand()


   #============================================================================
   # doPathArray
   #============================================================================
   def doPathArray(self):
      self.plugIn.beginEditCommand("Feature copied", self.cacheEntitySet.getLayerList())

      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if qad_array_fun.arrayPathEntity(self.plugIn, entity, self.basePt, self.pathRows, self.pathItemsNumber, \
                                          self.distanceBetweenRows, self.distanceBetweenCols, self.pathTangentDirection, self.itemsRotation, \
                                          self.pathPolyline, self.distanceFromStartPt, True, None) == False:
            self.plugIn.destroyEditCommand()
            return

      if self.delOrigSelSet: # se devo rimuovere gli oggetti originali
         entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
         for entity in entityIterator:
            if qad_layer.deleteFeatureToLayer(self.plugIn, entity.layer, entity.featureId, False) == False:
               self.plugIn.destroyEditCommand()
               return
         
      self.plugIn.endEditCommand()


   #============================================================================
   # doPolarArray
   #============================================================================
   def doPolarArray(self):
      self.plugIn.beginEditCommand("Feature copied", self.cacheEntitySet.getLayerList())

      dimElaboratedList = [] # lista delle quotature già elaborate
      entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
      for entity in entityIterator:
         qadGeom = entity.getQadGeom() # così inizializzo le info qad
         # verifico se l'entità appartiene ad uno stile di quotatura
         dimEntity = QadDimStyles.getDimEntity(entity)
         if dimEntity is not None:
            if appendDimEntityIfNotExisting(dimElaboratedList, dimEntity) == False: # quota già elaborata
               continue
            entity = dimEntity

         if qad_array_fun.arrayPolarEntity(self.plugIn, entity, self.basePt, self.centerPt, self.polarItemsNumber, \
                                           self.polarAngleBetween, self.polarRows, self.distanceBetweenRows, self.itemsRotation, \
                                           True, None) == False:
            self.plugIn.destroyEditCommand()
            return

      if self.delOrigSelSet: # se devo rimuovere gli oggetti originali
         entityIterator = QadCacheEntitySetIterator(self.cacheEntitySet)
         for entity in entityIterator:
            if qad_layer.deleteFeatureToLayer(self.plugIn, entity.layer, entity.featureId, False) == False:
               self.plugIn.destroyEditCommand()
               return
         
      self.plugIn.endEditCommand()


   #============================================================================
   # setPathPolyline
   #============================================================================
   def setPathPolyline(self, entity, point):
      """
      Setta self.pathPolyline che definisce la traiettoria
      """
      qadGeom = entity.getQadGeom()
      # la funzione ritorna una lista con 
      # (<minima distanza>
      # <punto più vicino>
      # <indice della geometria più vicina>
      # <indice della sotto-geometria più vicina>
      # se geometria chiusa è tipo polyline la lista contiene anche
      # <indice della parte della sotto-geometria più vicina>
      # <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
      dummy = getQadGeomClosestPart(qadGeom, point)
      # ritorna la sotto-geometria
      subGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
      self.pathPolyline = subGeom.copy()
      return True


   #============================================================================
   # setDistancesByPathItemNumberOnDivide
   #============================================================================
   def setDistancesByPathItemNumberOnDivide(self):
      # imposta le distanza dall'inizio della traccia e la distanza tra gli elementi
      # quando gli elementi devono essere distribuiti uniformemente
      self.distanceBetweenCols = self.pathPolyline.length() / (self.pathItemsNumber + 1)
      self.distanceFromStartPt = self.distanceBetweenCols


   #============================================================================
   # setItemNumberByDistanceBetweenColsOnMeasure
   #============================================================================
   def setItemNumberByDistanceBetweenColsOnMeasure(self):
      # imposta le distanza dall'inizio della traccia e il numero di elementi
      # quando gli elementi non devono essere distribuiti uniformemente ma a partire dall'inizio della traccia
      self.pathItemsNumber = int(self.pathPolyline.length() / self.distanceBetweenCols) + 1
      self.distanceFromStartPt = 0.0


   #============================================================================
   # waitForMainOptions
   #============================================================================
   def waitForMainOptions(self):          
      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
         self.waitForRectangleArrayOptions()
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
         self.waitForPathArrayOptions()
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
         self.waitForPolarArrayOptions()

      self.updatePointMapToolParams()


   #============================================================================
   # waitForArrayType
   #============================================================================
   def waitForArrayType(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ARRAYTYPE
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("Command_ARRAY", "Rectangular") + "/" + \
                 QadMsg.translate("Command_ARRAY", "PAth") + "/" + \
                 QadMsg.translate("Command_ARRAY", "POlar")
      englishKeyWords = "Rectangular" + "/" + "PAth" + "/" + "POlar"

      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
         self.defaultValue = QadMsg.translate("Command_ARRAY", "Rectangular")
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
         self.defaultValue = QadMsg.translate("Command_ARRAY", "PAth")
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
         self.defaultValue = QadMsg.translate("Command_ARRAY", "POlar")
         
      prompt = QadMsg.translate("Command_ARRAY", "Enter array type [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)      


   #============================================================================
   # waitForBasePt
   #============================================================================
   def waitForBasePt(self, nextStep = QadARRAYCommandClassStepEnum.ASK_FOR_BASE_PT):
      self.step = nextStep 
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.ASK_FOR_BASE_PT)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ARRAY", "Specify base point: "))


   #============================================================================
   # waitForItemsNumber
   #============================================================================
   def waitForItemsNumber(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_N
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
         self.defaultValue = self.pathItemsNumber
         if self.pathMethod == QadARRAYCommandClassPathMethodTypeEnum.MEASURE:
            keyWords = QadMsg.translate("Command_ARRAY", "Fill entire path")
            englishKeyWords = "Fill entire path"
            # si appresta ad attendere un numero intero
            prompt = QadMsg.translate("Command_ARRAY", "Number of Items to Array or [{0}] <{1}>: ").format(keyWords, str(self.defaultValue))
            keyWords += "_" + englishKeyWords
            inputType = QadInputTypeEnum.INT | QadInputTypeEnum.KEYWORDS
         else:
            keyWords = ""
            prompt = QadMsg.translate("Command_ARRAY", "Number of Items to Array <{0}>: ").format(str(self.defaultValue))
            inputType = QadInputTypeEnum.INT
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
         self.defaultValue = self.polarItemsNumber
         # si appresta ad attendere un numero intero
         keyWords = ""
         prompt = QadMsg.translate("Command_ARRAY", "Number of Items to Array <{0}>: ").format(str(self.defaultValue))
         inputType = QadInputTypeEnum.INT
      
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, \
                   inputType, \
                   self.defaultValue, \
                   keyWords, \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


   #============================================================================
   # waitForRows
   #============================================================================
   def waitForRows(self, nextStep):
      self.step = nextStep
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      # si appresta ad attendere un numero intero
      msg = QadMsg.translate("Command_ARRAY", "Specify number of rows <{0}>: ")
      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
         self.defaultValue = self.rectangleRows
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
         self.defaultValue = self.pathRows
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
         self.defaultValue = self.polarRows
      prompt = msg.format(str(self.defaultValue))
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, \
                   QadInputTypeEnum.INT, \
                   self.defaultValue, \
                   "", \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


   #============================================================================
   # waitForDistanceBetweenRows
   #============================================================================
   def waitForDistanceBetweenRows(self, totalOption, nextStep):
      self.step = nextStep
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.ASK_FOR_ROW_SPACE_FIRST_PT)

      self.defaultValue = self.distanceBetweenRows
      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
         inputMode = QadInputModeEnum.NOT_ZERO
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
         inputMode = QadInputModeEnum.NOT_ZERO
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
         inputMode = QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE

      if totalOption:
         keyWords = QadMsg.translate("Command_ARRAY", "Total")
         englishKeyWords = "Total"
         prompt = QadMsg.translate("Command_ARRAY", "Specify distance between rows or [{0}] <{1}>: ").format(keyWords, str(self.defaultValue))
         keyWords += "_" + englishKeyWords
         inputType = QadInputTypeEnum.FLOAT | QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS
      else:
         prompt = QadMsg.translate("Command_ARRAY", "Specify distance between rows <{0}>: ").format(str(self.defaultValue))
         keyWords = ""
         inputType = QadInputTypeEnum.FLOAT | QadInputTypeEnum.POINT2D
      
      # si appresta ad attendere un punto, un numero reale o enter o una parola chiave
      # msg, inputType, default, keyWords, inputMode
      self.waitFor(prompt, \
                   inputType, \
                   self.defaultValue, \
                   keyWords, \
                   inputMode)
      

   #=========================================================================
   # waitForDistanceBetweenRows2Pt
   #=========================================================================
   def waitForDistanceBetweenRows2Pt(self, startPt):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_2PT

      if self.GetDistClass is not None:
         del self.GetDistClass
      self.GetDistClass = QadGetDistClass(self.plugIn)
      
      self.GetDistClass.dist = self.distanceBetweenRows
      self.GetDistClass.inputMode = QadInputModeEnum.NOT_ZERO
      self.GetDistClass.startPt = startPt
      self.GetDistClass.run()
         
   
   #============================================================================
   # waitForTotalDistanceRows
   #============================================================================
   def waitForTotalDistanceRows(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_TOT

      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
         default = self.rectangleRows * self.distanceBetweenRows
         inputMode = QadInputModeEnum.NOT_ZERO
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
         default = self.pathRows * self.distanceBetweenRows
         inputMode = QadInputModeEnum.NOT_ZERO
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
         default = self.polarRows * self.distanceBetweenRows 
         inputMode = QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE
      
      if self.GetDistClass is not None:
         del self.GetDistClass
      self.GetDistClass = QadGetDistClass(self.plugIn)
      prompt = QadMsg.translate("Command_ARRAY", "Specifies the total distance between the start and end row <{0}>: ")
      self.GetDistClass.msg = prompt.format(str(default))
      self.GetDistClass.dist = default
      self.GetDistClass.inputMode = inputMode
      self.GetDistClass.run()


   #============================================================================
   # waitForDelOrigObjs
   #============================================================================
   def waitForDelOrigObjs(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_DEL_ORIG_OBJS
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("QAD", "Yes") + "/" + QadMsg.translate("QAD", "No")
      self.defaultValue = QadMsg.translate("QAD", "Yes")
      prompt = QadMsg.translate("Command_ARRAY", "Delete source objects of the array ? [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      
      englishKeyWords = "Yes" + "/" + "No"
      keyWords += "_" + englishKeyWords

      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)


   #============================================================================
   # waitForItemsRotation
   #============================================================================
   def waitForItemsRotation(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_ROTATION
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("QAD", "Yes") + "/" + QadMsg.translate("QAD", "No")
      if self.itemsRotation:
         self.defaultValue = QadMsg.translate("QAD", "Yes")
      else:
         self.defaultValue = QadMsg.translate("QAD", "No")
         
      if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
         prompt = QadMsg.translate("Command_ARRAY", "Rotate objects as they are arrayed ? [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
         prompt = QadMsg.translate("Command_ARRAY", "Align arrayed items to the path ? [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
         prompt = QadMsg.translate("Command_ARRAY", "Rotate objects as they are arrayed ? [{0}] <{1}>: ").format(keyWords, self.defaultValue)

      englishKeyWords = "Yes" + "/" + "No"
      keyWords += "_" + englishKeyWords
         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)


   #============================================================================
   # SERIE RETTANGOLARE - INIZIO
   #============================================================================


   #============================================================================
   # waitForRectangleArrayOptions
   #============================================================================
   def waitForRectangleArrayOptions(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("Command_ARRAY", "Base point") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Angle") + "/" + \
                 QadMsg.translate("Command_ARRAY", "COUnt") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Spacing") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Columns") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Rows") + "/" + \
                 QadMsg.translate("Command_ARRAY", "rotate Items") + "/" + \
                 QadMsg.translate("Command_ARRAY", "eXit")
      englishKeyWords = "Base point" + "/" + "Angle" + "/" + "COUnt" + "/" + "Spacing" + "/" + \
                        "Columns" + "/" + "Rows" + "/" + "rotate Items" + "/" + "eXit"

      self.defaultValue = QadMsg.translate("Command_ARRAY", "eXit")         
      prompt = QadMsg.translate("Command_ARRAY", "Select an option to edit array [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)


   #============================================================================
   # waitForRectangleAngle
   #============================================================================
   def waitForRectangleAngle(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE
      if self.GetAngleClass is not None:
         del self.GetAngleClass                  
      # si appresta ad attendere l'angolo di rotazione                      
      self.GetAngleClass = QadGetAngleClass(self.plugIn)
      prompt = QadMsg.translate("Command_ARRAY", "Specify the angle of rotation for the row axis <{0}>: ")
      self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rectangleAngle)))
      self.GetAngleClass.angle = self.rectangleAngle
      self.GetAngleClass.run()
      return False

   
   #============================================================================
   # waitForRectangleColumns
   #============================================================================
   def waitForRectangleColumns(self, nextStep):
      self.step = nextStep
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      # optionFrom può essere ASK_FOR_COLUMN_COUNT o ASK_FOR_COLUMN_N
      self.defaultValue = self.rectangleCols
      # si appresta ad attendere un numero intero
      msg = QadMsg.translate("Command_ARRAY", "Specify number of columns <{0}>: ")
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(msg.format(str(self.defaultValue)), \
                   QadInputTypeEnum.INT, \
                   self.defaultValue, \
                   "", \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


   #============================================================================
   # waitForRectangleColumnsSpacing
   #============================================================================
   def waitForRectangleColumnsSpacing(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_OR_CELL
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_FIRST_PT)

      self.defaultValue = self.distanceBetweenCols
      keyWords = QadMsg.translate("Command_ARRAY", "Unit cell")
      englishKeyWords = "Unit cell"
      prompt = QadMsg.translate("Command_ARRAY", "Specify distance between columns or [{0}] <{1}>: ")     
      prompt = prompt.format(keyWords, str(self.defaultValue))
      keyWords += "_" + englishKeyWords
      
      # si appresta ad attendere un punto, un numero reale o enter o una parola chiave
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, \
                   QadInputTypeEnum.FLOAT | QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, \
                   QadInputModeEnum.NOT_ZERO)


   #============================================================================
   # waitForRectangleColumnsSpacing2Pt
   #============================================================================
   def waitForRectangleColumnsSpacing2Pt(self, startPt):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_2PT
      
      if self.GetDistClass is not None:
         del self.GetDistClass
      self.GetDistClass = QadGetDistClass(self.plugIn)
      self.GetDistClass.dist = self.distanceBetweenCols
      self.GetDistClass.inputMode = QadInputModeEnum.NOT_ZERO
      self.GetDistClass.startPt = startPt
      self.GetDistClass.run()


   #============================================================================
   # waitForRectangleTotalDistanceCols
   #============================================================================
   def waitForRectangleTotalDistanceCols(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_TOT
      
      if self.GetDistClass is not None:
         del self.GetDistClass
      self.GetDistClass = QadGetDistClass(self.plugIn)
      prompt = QadMsg.translate("Command_ARRAY", "Specifies the total distance between the start and end columns <{0}>: ")
      default = self.rectangleCols * self.distanceBetweenCols
      self.GetDistClass.msg = prompt.format(str(default))
      self.GetDistClass.dist = default
      self.GetDistClass.inputMode = QadInputModeEnum.NOT_ZERO
      self.GetDistClass.run()


   #============================================================================
   # waitForRectangleDistanceBetweenCols
   #============================================================================
   def waitForRectangleDistanceBetweenCols(self, totalOption):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_OR_TOT
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.ASK_FOR_COLUMN_SPACE_FIRST_PT)

      self.defaultValue = self.distanceBetweenCols

      if totalOption:
         keyWords = QadMsg.translate("Command_ARRAY", "Total")
         englishKeyWords = "Total"
         prompt = QadMsg.translate("Command_ARRAY", "Specify distance between columns or [{0}] <{1}>: ").format(keyWords, str(self.defaultValue))
         keyWords += "_" + englishKeyWords
         inputType = QadInputTypeEnum.FLOAT | QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS
      else:
         prompt = QadMsg.translate("Command_ARRAY", "Specify distance between columns <{0}>: ").format(str(self.defaultValue))
         keyWords = ""
         inputType = QadInputTypeEnum.FLOAT | QadInputTypeEnum.POINT2D
      
      # si appresta ad attendere un punto, un numero reale o enter o una parola chiave
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, \
                   inputType, \
                   self.defaultValue, \
                   keyWords, \
                   QadInputModeEnum.NOT_ZERO)
      
      
   #============================================================================
   # waitForRectangleFirstCellCorner
   #============================================================================
   def waitForRectangleFirstCellCorner(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_1PT_CELL
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ARRAY", "Specify first cell corner: "))
      
      
   #============================================================================
   # waitForRectangleSecondCellCorner
   #============================================================================
   def waitForRectangleSecondCellCorner(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_2PT_CELL
      # imposto il map tool
      self.getPointMapTool().firstPt = self.firstPt
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.ASK_FOR_2PT_CELL)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ARRAY", "Specify second cell corner: "))


   #============================================================================
   # SERIE RETTANGOLARE - FINE
   # SERIE TRAIETTORIA  - INIZIO
   #============================================================================


   #============================================================================
   # waitForPathObject
   #============================================================================
   def waitForPathObject(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_PATH_OBJ
      
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_ARRAY", "Select the object to use for the path of the array: ")
      # scarto la selezione di punti e quote
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False

      self.entSelClass.run(msgMapTool, msg)
      

   #============================================================================
   # waitForPathArrayOptions
   #============================================================================
   def waitForPathArrayOptions(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("Command_ARRAY", "Method") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Base point") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Tangent direction") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Items") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Rows") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Align items") + "/" + \
                 QadMsg.translate("Command_ARRAY", "eXit")
      englishKeyWords = "Method" + "/" + "Base point" + "/" + "Tangent direction" + "/" + "Items" + "/" + \
                        "Rows" + "/" + "Align items" + "/" + "eXit"

      self.defaultValue = QadMsg.translate("Command_ARRAY", "eXit")         
      prompt = QadMsg.translate("Command_ARRAY", "Select an option to edit array [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)


   #============================================================================
   # waitForPathMethod
   #============================================================================
   def waitForPathMethod(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_PATH_METHOD

      keyWords = QadMsg.translate("Command_ARRAY", "Divide") + "/" + QadMsg.translate("Command_ARRAY", "Measure")
      if self.pathMethod == QadARRAYCommandClassPathMethodTypeEnum.DIVIDE:
         self.defaultValue = QadMsg.translate("Command_ARRAY", "Divide")
      elif self.pathMethod == QadARRAYCommandClassPathMethodTypeEnum.MEASURE:
         self.defaultValue = QadMsg.translate("Command_ARRAY", "Measure")
      prompt = QadMsg.translate("Command_ARRAY", "Specify path method [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      
      englishKeyWords = "Divide" + "/" + "Measure"
      keyWords += "_" + englishKeyWords

      # si appresta ad attendere enter o una parola chiave
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)


   #============================================================================
   # waitForPathTangentDirection
   #============================================================================
   def waitForPathTangentDirection(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_TAN_DIRECTION
      
      if self.GetAngleClass is not None:
         del self.GetAngleClass                  
      # si appresta ad attendere l'angolo di rotazione                      
      self.GetAngleClass = QadGetAngleClass(self.plugIn)
      prompt = QadMsg.translate("Command_ARRAY", "Specify the first point for array tangent direction: ")
      self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.pathTangentDirection)))
      self.GetAngleClass.angle = self.pathTangentDirection
      self.GetAngleClass.run()
      return False


   #============================================================================
   # waitForPathDistanceBetweenItems
   #============================================================================
   def waitForPathDistanceBetweenItems(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_SPACE
      
      if self.GetDistClass is not None:
         del self.GetDistClass
      self.GetDistClass = QadGetDistClass(self.plugIn)
      prompt = QadMsg.translate("Command_ARRAY", "Specify distance between items along path <{0}>: ")
      self.GetDistClass.msg = prompt.format(str(self.distanceBetweenCols))
      self.GetDistClass.dist = self.distanceBetweenCols
      self.GetDistClass.inputMode = QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE
      self.GetDistClass.run()


   #============================================================================
   # SERIE TRAIETTORIA  - FINE
   # SERIE POLARE       - INIZIO
   #============================================================================


   #============================================================================
   # waitForPolarCenterPt
   #============================================================================
   def waitForPolarCenterPt(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_CENTER_PT

      keyWords = QadMsg.translate("Command_ARRAY", "Base point")
      englishKeyWords = "Base point"
      prompt = QadMsg.translate("Command_ARRAY", "Specify center point of array or [{0}]: ").format(keyWords)
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)

   
   #============================================================================
   # waitForPolarArrayOptions
   #============================================================================
   def waitForPolarArrayOptions(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_array_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("Command_ARRAY", "Base point") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Items") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Angle between") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Fill angle") + "/" + \
                 QadMsg.translate("Command_ARRAY", "ROWs") + "/" + \
                 QadMsg.translate("Command_ARRAY", "Rotate items") + "/" + \
                 QadMsg.translate("Command_ARRAY", "eXit")
      englishKeyWords = "Base point" + "/" + "Items" + "/" + "Angle between" + "/" + "Angle between" + "/" + \
                        "Fill angle" + "/" + "ROWs" + "/" + "Rotate items" + "/" + "eXit"

      self.defaultValue = QadMsg.translate("Command_ARRAY", "eXit")         
      prompt = QadMsg.translate("Command_ARRAY", "Select an option to edit array [{0}] <{1}>: ").format(keyWords, self.defaultValue)
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.KEYWORDS, \
                   self.defaultValue, \
                   keyWords, QadInputModeEnum.NONE)      

   
   #============================================================================
   # waitForPolarAngleBetween
   #============================================================================
   def waitForPolarAngleBetween(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE_BETWEEN_ITEMS
      
      if self.GetAngleClass is not None:
         del self.GetAngleClass                  
      # si appresta ad attendere l'angolo di rotazione                      
      self.GetAngleClass = QadGetAngleClass(self.plugIn)
      prompt = QadMsg.translate("Command_ARRAY", "Specify the angle between items <{0}>: ")
      self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.polarAngleBetween)))
      self.GetAngleClass.angle = self.polarAngleBetween
      self.GetAngleClass.run()
      return False

   
   #============================================================================
   # waitForPolarAngleBetween
   #============================================================================
   def waitForPolarFillAngle(self):
      self.step = QadARRAYCommandClassStepEnum.ASK_FOR_FULL_ANGLE
      
      if self.GetAngleClass is not None:
         del self.GetAngleClass                  
      # si appresta ad attendere l'angolo di rotazione                      
      self.GetAngleClass = QadGetAngleClass(self.plugIn)
      default = self.polarItemsNumber * self.polarAngleBetween
      prompt = QadMsg.translate("Command_ARRAY", "Specify angle to fill (+ = CCW, - = CW) <{0}>: ")
      self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(default)))
      self.GetAngleClass.angle = default
      self.GetAngleClass.run()
      return False


   #============================================================================
   # SERIE POLARE - FINE
   #============================================================================


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
            
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # inizio del comando
         if self.cacheEntitySet.isEmpty() == False: # se era già stato impostato da codice tramite "self.setEntitySet"
            self.waitForArrayType()
            return False
            
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() == 0:
               return True # fine comando
            self.setEntitySet(self.SSGetClass.entitySet)
            
            del self.SSGetClass
            self.SSGetClass = None
            
            self.waitForArrayType()
            self.step = -1 * self.step # trucchetto per prendere il map tool base
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di selezione entità                    
            self.step = -1 * self.step # trucchetto per prendere il map tool base
            
         return False
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL TIPO DI SERIE (da step = ASK_FOR_SELSET)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ARRAYTYPE: # dopo aver atteso una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else: # la parola chiave arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ARRAY", "Rectangular") or value == "Rectangular":
               self.arrayType = QadARRAYCommandClassSeriesTypeEnum.RECTANGLE
               self.plugIn.setLastArrayType_array(self.arrayType)
               self.waitForMainOptions()
            elif value == QadMsg.translate("Command_ARRAY", "PAth") or value == "PAth":
               self.arrayType = QadARRAYCommandClassSeriesTypeEnum.PATH
               self.plugIn.setLastArrayType_array(self.arrayType)
               self.waitForPathObject(msgMapTool, msg)
            elif value == QadMsg.translate("Command_ARRAY", "POlar") or value == "POlar":
               self.arrayType = QadARRAYCommandClassSeriesTypeEnum.POLAR
               self.plugIn.setLastArrayType_array(self.arrayType)
               self.waitForPolarCenterPt()
         
         return False 
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DI UN OPZIONE DAL MENU PRINCIPALE (da step = ASK_FOR_ARRAYTYPE da tutte le opzioni)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS: # dopo aver atteso un punto o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None:
            value = QadMsg.translate("Command_ARRAY", "eXit")
         
         if type(value) == unicode:
            if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
               if value ==  QadMsg.translate("Command_ARRAY", "Base point") or value == "Base point":
                  self.waitForBasePt()
               elif value == QadMsg.translate("Command_ARRAY", "Angle") or value == "Angle":
                  self.waitForRectangleAngle()
               elif value == QadMsg.translate("Command_ARRAY", "COUnt") or value == "COUnt":
                  self.waitForRectangleColumns(QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_COUNT)
               elif value == QadMsg.translate("Command_ARRAY", "Spacing") or value == "Spacing":
                  self.waitForRectangleColumnsSpacing()
               elif value == QadMsg.translate("Command_ARRAY", "Columns") or value == "Columns":
                  self.waitForRectangleColumns(QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_N)
               elif value == QadMsg.translate("Command_ARRAY", "Rows") or value == "Rows":
                  self.waitForRows(QadARRAYCommandClassStepEnum.ASK_FOR_ROW_N)
               elif value ==  QadMsg.translate("Command_ARRAY", "rotate Items") or value == "rotate Items":
                  self.waitForItemsRotation()
               elif value == QadMsg.translate("Command_ARRAY", "eXit") or value == "eXit":
                  if self.delObj == QadDELOBJEnum.ASK_FOR_DELETE_ALL:
                     self.waitForDelOrigObjs()
                  else:                  
                     self.doRectangleArray()
                     return True # fine comando
               
            elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
               if value == QadMsg.translate("Command_ARRAY", "Method") or value == "Method":
                  self.waitForPathMethod()
               elif value ==  QadMsg.translate("Command_ARRAY", "Base point") or value == "Base point":
                  self.waitForBasePt()
               elif value ==  QadMsg.translate("Command_ARRAY", "Tangent direction") or value == "Tangent direction":
                  self.waitForPathTangentDirection()
               elif value ==  QadMsg.translate("Command_ARRAY", "Items") or value == "Items":
                  if self.pathMethod == QadARRAYCommandClassPathMethodTypeEnum.MEASURE:
                     self.waitForPathDistanceBetweenItems()
                  elif self.pathMethod == QadARRAYCommandClassPathMethodTypeEnum.DIVIDE:
                     self.waitForItemsNumber()
               elif value ==  QadMsg.translate("Command_ARRAY", "Rows") or value == "Rows":
                  self.waitForRows(QadARRAYCommandClassStepEnum.ASK_FOR_ROW_N)
               elif value ==  QadMsg.translate("Command_ARRAY", "Align items") or value == "Align items":
                  self.waitForItemsRotation()
               elif value == QadMsg.translate("Command_ARRAY", "eXit") or value == "eXit":
                  if self.delObj == QadDELOBJEnum.ASK_FOR_DELETE_ALL:
                     self.waitForDelOrigObjs()
                  else:                  
                     self.doPathArray()
                     return True # fine comando
                  
            elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
               if value ==  QadMsg.translate("Command_ARRAY", "Base point") or value == "Base point":
                  self.waitForBasePt()
               elif value ==  QadMsg.translate("Command_ARRAY", "Items") or value == "Items":
                  self.waitForItemsNumber()
               elif value ==  QadMsg.translate("Command_ARRAY", "Angle between") or value == "Angle between":
                  self.waitForPolarAngleBetween()
               elif value ==  QadMsg.translate("Command_ARRAY", "Fill angle") or value == "Fill angle":
                  self.waitForPolarFillAngle()
               elif value ==  QadMsg.translate("Command_ARRAY", "ROWs") or value == "ROWs":
                  self.waitForRows(QadARRAYCommandClassStepEnum.ASK_FOR_ROW_N)
               elif value ==  QadMsg.translate("Command_ARRAY", "Rotate items") or value == "Rotate items":
                  self.waitForItemsRotation()
               elif value == QadMsg.translate("Command_ARRAY", "eXit") or value == "eXit":
                  if self.delObj == QadDELOBJEnum.ASK_FOR_DELETE_ALL:
                     self.waitForDelOrigObjs()
                  else:                  
                     self.doPolarArray()
                     return True # fine comando                  
         elif type(value) == QgsPointXY: # se é stato indicato un punto
            pass
         
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PUNTO BASE (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_BASE_PT: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.basePt.set(value.x(), value.y())

         self.waitForMainOptions()
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DI CANCELLAZIONE DEGLI OGGETTI ORIGINALI (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_DEL_ORIG_OBJS: # dopo aver atteso una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # la parola chiave arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
               self.delOrigSelSet = True
            else:
               self.delOrigSelSet = False

            if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
               self.doRectangleArray()
            elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
               self.doPathArray()
            elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
               self.doPolarArray()

            return True
         
         return False 


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO DELLA SERIE (da step = ASK_FOR_MAIN_OPTIONS)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.rectangleAngle = self.GetAngleClass.angle
               self.plugIn.setLastRectangleAngle_array(self.rectangleAngle)
               self.plugIn.setLastRot(self.rectangleAngle)
            self.waitForMainOptions()
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUMERO DELLE COLONNE DELLA SERIE RETTANGOLO OPZIONE COUNT (da step = ASK_FOR_MAIN_OPTIONS)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_COUNT: # dopo aver atteso un numero intero si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # il numero di colonne arriva come parametro della funzione
            value = msg

         maxArray = QadVariables.get(QadMsg.translate("Environment variables", "MAXARRAY"))
         if value * self.rectangleRows > maxArray:
            errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
            self.showErr(errMsg.format(str(maxArray)))
         else:
            self.rectangleCols = value
            self.plugIn.setLastRectangleCols_array(self.rectangleCols)
            self.updatePointMapToolParams()
            self.waitForRows(QadARRAYCommandClassStepEnum.ASK_FOR_ROW_COUNT)
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUMERO DI RIGHE DELLA SERIE RETTANGOLO OPZIONE COUNT (da step = ASK_FOR_COLUMN_N)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_COUNT: # dopo aver atteso un numero intero si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # il numero di righe arriva come parametro della funzione
            value = msg

         maxArray = QadVariables.get(QadMsg.translate("Environment variables", "MAXARRAY"))
         if value * self.rectangleCols > maxArray:
            errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
            self.showErr(errMsg.format(str(maxArray)))
         else:
            self.rectangleRows = value
            self.plugIn.setLastRectangleRows_array(self.rectangleRows)
            self.waitForMainOptions()
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DISTANZA TRA COLONNE (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_OR_CELL: # dopo aver atteso un punto, un numero o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.defaultValue 
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il primo punto per misurare la distanza tra colonne
            self.waitForRectangleColumnsSpacing2Pt(value)
         elif type(value) == float: # se é stato inserita la distanza
            self.distanceBetweenCols = value
            self.updatePointMapToolParams()
            self.waitForDistanceBetweenRows(False, QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE) # senza opzione di "totale"
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ARRAY", "Unit cell") or value == "Unit cell":
               self.waitForRectangleFirstCellCorner()
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PT PER MISURARE LA DISTANZA TRA COLONNE (da step = ASK_FOR_COLUMN_SPACE_OR_CELL)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_2PT: # dopo aver atteso un punto si riavvia il comando
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.distanceBetweenCols = self.GetDistClass.dist

            del self.GetDistClass
            self.GetDistClass = None
            
            self.updatePointMapToolParams()
            self.waitForDistanceBetweenRows(False, QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE) # senza opzione di "totale"
         return False # fine comando


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DISTANZA TRA RIGHE (da step = ASK_FOR_COLUMN_SPACE_OR_CELL)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.defaultValue 
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il primo punto per misurare la distanza tra righe
            self.waitForDistanceBetweenRows2Pt(value)
         elif type(value) == float: # se é stato inserita la distanza
            self.distanceBetweenRows = value
            self.waitForMainOptions()
         return False # fine comando


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PT PER MISURARE LA DISTANZA TRA RIGHE (da step = ASK_FOR_ROW_SPACE)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_2PT: # dopo aver atteso un punto si riavvia il comando
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.distanceBetweenRows = self.GetDistClass.dist
               
            del self.GetDistClass
            self.GetDistClass = None
            self.waitForMainOptions()
         return False # fine comando


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO ANGOLO DELLA CELLA (da step = ASK_FOR_COLUMN_SPACE_OR_CELL)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_1PT_CELL: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il primo punto per misurare la distanza tra righe
            self.firstPt.set(value.x(), value.y())
            self.waitForRectangleSecondCellCorner()
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO ANGOLO DELLA CELLA (da step = ASK_FOR_1PT_CELL)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_2PT_CELL: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il primo punto per misurare la distanza tra righe
            if (value.y() - self.firstPt.y()) == 0 or (value.x() - self.firstPt.x()) == 0:
               self.showErr(QadMsg.translate("Command_ARRAY", "\nCell size must be greater than 0."))
            else:
               self.distanceBetweenRows = value.y() - self.firstPt.y()
               self.distanceBetweenCols = value.x() - self.firstPt.x()
               self.waitForMainOptions()
         else:
            self.waitForMainOptions()
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUMERO DELLE COLONNE DELLA SERIE RETTANGOLO OPZIONE COLUMN (da step = ASK_FOR_MAIN_OPTIONS)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_N: # dopo aver atteso un numero intero si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # il numero di righe arriva come parametro della funzione
            value = msg

         # il numero delle colonnne arriva come parametro della funzione
         maxArray = QadVariables.get(QadMsg.translate("Environment variables", "MAXARRAY"))
         if value * self.rectangleRows > maxArray:
            errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
            self.showErr(errMsg.format(str(maxArray)))
         else:         
            self.rectangleCols = value
            self.plugIn.setLastRectangleCols_array(self.rectangleCols)
            self.updatePointMapToolParams()
            self.waitForRectangleDistanceBetweenCols(True) # con opzione "TOTAL"
         return False
      
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DISTANZA TRA COLONNE (da step = ASK_FOR_COLUMN_N)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_OR_TOT: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.defaultValue 
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il primo punto per misurare la distanza tra righe
            self.waitForRectangleColumnsSpacing2Pt(value)
         elif type(value) == float: # se é stato inserita la distanza
            self.distanceBetweenCols = value
            self.waitForMainOptions()
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ARRAY", "Total") or value == "Total":
               self.waitForRectangleTotalDistanceCols()
         return False # fine comando


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PT PER MISURARE LA DISTANZA TOTALE TRA COLONNE (da step = ASK_FOR_COLUMN_SPACE_OR_TOT)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_COLUMN_SPACE_TOT: # dopo aver atteso un punto si riavvia il comando
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               if self.rectangleCols > 1:
                  self.distanceBetweenCols = self.GetDistClass.dist / (self.rectangleCols - 1)
               
            del self.GetDistClass
            self.GetDistClass = None
            self.waitForMainOptions()
         return False # fine comando


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUMERO DELLE RIGHE OPZIONE ROW (da step = ASK_FOR_MAIN_OPTIONS)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_N: # dopo aver atteso un numero intero si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # il numero di righe arriva come parametro della funzione
            value = msg

         maxArray = QadVariables.get(QadMsg.translate("Environment variables", "MAXARRAY"))
         # il numero di righe arriva come parametro della funzione
         if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
            if value * self.rectangleCols > maxArray:
               errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
               self.showErr(errMsg.format(str(maxArray)))
               return False
            else:
               self.rectangleRows = value
               self.plugIn.setLastRectangleRows_array(self.rectangleRows)
         elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
            if value * self.pathItemsNumber > maxArray:
               errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
               self.showErr(errMsg.format(str(maxArray)))
               return False
            else:
               self.pathRows = value
               self.plugIn.setLastPathRows_array(self.pathRows)
         elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
            if value * self.polarItemsNumber > maxArray:
               errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
               self.showErr(errMsg.format(str(maxArray)))
               return False
            else:
               self.polarRows = value
               self.plugIn.setLastPolarRows_array(self.polarRows)
         
         self.updatePointMapToolParams()
         self.waitForDistanceBetweenRows(True, QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_OR_TOT) # con opzione "TOTAL"
         return False
      
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DISTANZA TRA RIGHE (da step = ASK_FOR_ROW_N)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_OR_TOT: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.defaultValue 
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il primo punto per misurare la distanza tra righe
            self.waitForDistanceBetweenRows2Pt(value)
         elif type(value) == float: # se é stato inserita la distanza
            self.distanceBetweenRows = value
            self.waitForMainOptions()
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ARRAY", "Total") or value == "Total":
               self.waitForTotalDistanceRows()
         return False # fine comando


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PT PER MISURARE LA DISTANZA TOTALE TRA RIGHE (da step = ASK_FOR_ROW_SPACE)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ROW_SPACE_TOT: # dopo aver atteso un punto si riavvia il comando
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.RECTANGLE:
                  if self.rectangleRows > 1:
                     self.distanceBetweenRows = self.GetDistClass.dist / (self.rectangleRows - 1)
               elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
                  if self.pathRows > 1:
                     self.distanceBetweenRows = self.GetDistClass.dist / (self.pathRows - 1)
               elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
                  if self.polarRows > 1:
                     self.distanceBetweenRows = self.GetDistClass.dist / (self.polarRows - 1)

            del self.GetDistClass
            self.GetDistClass = None
            self.waitForMainOptions()
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUMERO DI ELEMENTI DELLA SERIE (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_N:
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # il numero di elementi arriva come parametro della funzione
            value = msg

         maxArray = QadVariables.get(QadMsg.translate("Environment variables", "MAXARRAY"))

         if self.arrayType == QadARRAYCommandClassSeriesTypeEnum.PATH:
            if self.pathMethod == QadARRAYCommandClassPathMethodTypeEnum.DIVIDE:
               if type(value) == int or type(value) == long: # se é stato inserito il numero di elementi
                  if value * self.pathRows > maxArray:
                     errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
                     self.showErr(errMsg.format(str(maxArray)))
                  else:
                     self.pathItemsNumber = value
                     self.setDistancesByPathItemNumberOnDivide()
                     self.waitForMainOptions()
            elif self.pathMethod == QadARRAYCommandClassPathMethodTypeEnum.MEASURE:
               if type(value) == int or type(value) == long: # se é stato inserito il numero di elementi
                  if value * self.pathRows > maxArray:
                     errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
                     self.showErr(errMsg.format(str(maxArray)))
                  elif (value - 1) * self.distanceBetweenCols > self.pathPolyline.length():
                     errMsg = QadMsg.translate("Command_ARRAY", "\nMaximun number of items = {0}.")
                     self.showErr(errMsg.format(str(int(self.pathPolyline.length() / self.distanceBetweenCols) + 1)))
                  else:
                     self.pathItemsNumber = value
                     self.distanceFromStartPt = 0.0
                     self.waitForMainOptions()
               elif type(value) == unicode:
                  if value == QadMsg.translate("Command_ARRAY", "Fill entire path") or value == "Fill entire path":
                     self.setItemNumberByDistanceBetweenColsOnMeasure()
                     self.waitForMainOptions()
         elif self.arrayType == QadARRAYCommandClassSeriesTypeEnum.POLAR:
            if msg * self.polarRows > maxArray:
               errMsg = QadMsg.translate("Command_ARRAY", "\nThe array size can't be greater than {0} elements. See MAXARRAY system variable.")
               self.showErr(errMsg.format(str(maxArray)))
            else:
               fillAngle = self.polarItemsNumber * self.polarAngleBetween
               self.polarItemsNumber = value
               self.polarAngleBetween = 2 * math.pi / value
               self.plugIn.setLastPolarItemsNumber_array(self.polarItemsNumber)
               self.plugIn.setLastPolarAngleBetween_array(self.polarAngleBetween)
               self.waitForMainOptions()
               
         return False # fine comando


   #============================================================================
   # SERIE TRAIETTORIA  - INIZIO
   #============================================================================


      #=========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN'ENTITA' DA USARE COME PERCORSO DELLA SERIE (da step = ASK_FOR_ARRAYTYPE)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_PATH_OBJ:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               if self.setPathPolyline(self.entSelClass.entity, self.entSelClass.point) == True:
                  self.setItemNumberByDistanceBetweenColsOnMeasure()
                  self.waitForMainOptions()
            else:               
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForPathObject(msgMapTool, msg)
               
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL METODO (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_PATH_METHOD: # dopo aver atteso una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # la parola chiave arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ARRAY", "Divide") or value == "Divide":
               self.pathMethod = QadARRAYCommandClassPathMethodTypeEnum.DIVIDE
               self.setDistancesByPathItemNumberOnDivide()
            elif value == QadMsg.translate("Command_ARRAY", "Measure") or value == "Measure":
               self.pathMethod = QadARRAYCommandClassPathMethodTypeEnum.MEASURE
               self.setItemNumberByDistanceBetweenColsOnMeasure()
            self.waitForMainOptions()
         
         return False 


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DIREZIONE DELLA TANGENTE (da step = ASK_FOR_MAIN_OPTIONS)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_TAN_DIRECTION:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.pathTangentDirection = self.GetAngleClass.angle
               self.plugIn.setLastPathTangentDirection_array(self.pathTangentDirection)
            self.waitForMainOptions()
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PT PER MISURARE LA DISTANZA TRA ELEMENTI (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_SPACE: 
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               l = self.pathPolyline.length()
               if self.GetDistClass.dist > l:
                  errMsg = QadMsg.translate("Command_ARRAY", "\nThe distance between items can't be greater than {0}.")
                  self.showErr(errMsg.format(str(l)))
               else:
                  self.distanceBetweenCols = self.GetDistClass.dist

            del self.GetDistClass
            self.GetDistClass = None
            self.updatePointMapToolParams()
            self.waitForItemsNumber()
         return False # fine comando


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ALLINEAMENTO DEGLI ELEMENTI (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ITEM_ROTATION: # dopo aver atteso una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.defaultValue 
            else:
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
         else:
            # la parola chiave arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("QAD", "Yes") or value == "Yes":
               self.itemsRotation = True
            elif value == QadMsg.translate("QAD", "No") or value == "No":
               self.itemsRotation = False
            self.plugIn.setLastItemsRotation_array(self.itemsRotation)
            self.waitForMainOptions()
         
         return False 


   #============================================================================
   # SERIE TRAIETTORIA  - FINE
   # SERIE POLARE       - INIZIO
   #============================================================================


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL CENTRO DELLA SERIE ((da step = ASK_FOR_ARRAYTYPE))
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_CENTER_PT: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il punto centrale della serie
            self.centerPt.set(value.x(), value.y())
            self.waitForMainOptions()
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ARRAY", "Base point") or value == "Base point":
               self.updatePointMapToolParams()
               self.waitForBasePt(QadARRAYCommandClassStepEnum.ASK_FOR_BASE_PT_BEFORE_MAIN_OPTIONS)
         return False # fine comando
         
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PUNTO BASE (da step = ASK_FOR_CENTER_PT)
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_BASE_PT_BEFORE_MAIN_OPTIONS: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.basePt.set(value.x(), value.y())
         self.updatePointMapToolParams()
         self.waitForPolarCenterPt()
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO TRA GLI ELEMENTI (da step = ASK_FOR_MAIN_OPTIONS)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_ANGLE_BETWEEN_ITEMS:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               if self.GetAngleClass.angle * self.polarItemsNumber > math.pi * 2:
                  errMsg = QadMsg.translate("Command_ARRAY", "\nThe angle between can't be greater than {0}.")
                  maxAngleBetween = math.pi * 2 / self.polarItemsNumber
                  self.showErr(errMsg.format(str(qad_utils.toDegrees(maxAngleBetween))))
               else:
                  self.polarAngleBetween = self.GetAngleClass.angle               
                  self.plugIn.setLastPolarAngleBetween_array(self.polarAngleBetween)
                  
            self.waitForMainOptions()
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO TRA GLI ELEMENTI (da step = ASK_FOR_MAIN_OPTIONS)
      #=========================================================================
      elif self.step == QadARRAYCommandClassStepEnum.ASK_FOR_FULL_ANGLE:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.polarAngleBetween = self.GetAngleClass.angle / self.polarItemsNumber
               self.plugIn.setLastPolarAngleBetween_array(self.polarAngleBetween)               
            self.waitForMainOptions()
            
         return False
         

###############################################################################
# Classe che gestisce il comando ARRAYRECT
class QadARRAYRECTCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadARRAYRECTCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ARRAYRECT")

   def getEnglishName(self):
      return "ARRAYRECT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runARRAYRECTCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/arrayRect.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_ARRAY", "Distributes object copies into any combination of rows and columns.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.arrayCmd = QadARRAYCommandClass(plugIn)

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.SSGetClass is not None:
         del self.SSGetClass
      del self.arrayCmd


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()
      else:
         return self.arrayCmd.getPointMapTool()


   def getCurrentContextualMenu(self):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.arrayCmd.getCurrentContextualMenu()


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
            
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # inizio del comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() == 0:
               return True # fine comando
            self.arrayCmd.setEntitySet(self.SSGetClass.entitySet)
            
            del self.SSGetClass
            self.SSGetClass = None
            
            self.step = -1
            self.arrayCmd.step = QadARRAYCommandClassStepEnum.ASK_FOR_ARRAYTYPE
            
            return self.arrayCmd.run(False, QadMsg.translate("Command_ARRAY", "Rectangular"))
            
         return False

      else:
         return self.arrayCmd.run(msgMapTool, msg)


###############################################################################
# Classe che gestisce il comando ARRAYPATH
class QadARRAYPATHCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadARRAYPATHCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ARRAYPATH")

   def getEnglishName(self):
      return "ARRAYPATH"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runARRAYPATHCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/arrayPath.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_ARRAY", "Evenly distributes object copies along a path or a portion of a path.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.arrayCmd = QadARRAYCommandClass(plugIn)

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.SSGetClass is not None:
         del self.SSGetClass
      del self.arrayCmd


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()
      else:
         return self.arrayCmd.getPointMapTool()


   def getCurrentContextualMenu(self):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.arrayCmd.getCurrentContextualMenu()


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
            
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # inizio del comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() == 0:
               return True # fine comando
            self.arrayCmd.setEntitySet(self.SSGetClass.entitySet)
            
            del self.SSGetClass
            self.SSGetClass = None
            
            self.step = -1
            self.arrayCmd.step = QadARRAYCommandClassStepEnum.ASK_FOR_ARRAYTYPE
            
            return self.arrayCmd.run(False, QadMsg.translate("Command_ARRAY", "PAth"))
            
         return False

      else:
         return self.arrayCmd.run(msgMapTool, msg)


###############################################################################
# Classe che gestisce il comando ARRAYPOLAR
class QadARRAYPOLARCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadARRAYPOLARCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ARRAYPOLAR")

   def getEnglishName(self):
      return "ARRAYPOLAR"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runARRAYPOLARCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/arrayPolar.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_ARRAY", "Evenly distributes object copies in a circular pattern around a center point.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.SSGetClass.onlyEditableLayers = True
      self.arrayCmd = QadARRAYCommandClass(plugIn)

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.SSGetClass is not None:
         del self.SSGetClass
      del self.arrayCmd

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool()
      else:
         return self.arrayCmd.getPointMapTool()


   def getCurrentContextualMenu(self):
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.arrayCmd.getCurrentContextualMenu()


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
            
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == QadARRAYCommandClassStepEnum.ASK_FOR_SELSET: # inizio del comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            if self.SSGetClass.entitySet.count() == 0:
               return True # fine comando
            self.arrayCmd.setEntitySet(self.SSGetClass.entitySet)
            
            del self.SSGetClass
            self.SSGetClass = None
            
            self.step = -1
            self.arrayCmd.step = QadARRAYCommandClassStepEnum.ASK_FOR_ARRAYTYPE
            
            return self.arrayCmd.run(False, QadMsg.translate("Command_ARRAY", "POlar"))
            
         return False

      else:
         return self.arrayCmd.run(msgMapTool, msg)
