# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando SPEZZA per tagliare un oggetto 
 
                              -------------------
        begin                : 2014-01-09
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
from qgis.core import QgsWkbTypes, QgsFeature, QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_entsel_cmd import QadEntSelClass
from ..qad_msg import QadMsg
from .. import qad_layer
from .. import qad_utils
from ..qad_break_fun import breakQadGeometry
from ..qad_multi_geom import fromQadGeomToQgsGeom, setQadGeomAt


# Classe che gestisce il comando BREAK
class QadBREAKCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadBREAKCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "BREAK")

   def getEnglishName(self):
      return "BREAK"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runBREAKCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/break.svg")
   
   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_BREAK", "Breaks an object.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None      
      self.firstPt = None
      self.secondPt = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 1: # quando si é in fase di selezione entità
         return self.entSelClass.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 1: # quando si é in fase di selezione entità
         return self.entSelClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 1         
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_BREAK", "Select the object to break: ")
      # scarto la selezione di punti e poligoni
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = False
      self.entSelClass.checkDimLayers = False
      self.entSelClass.onlyEditableLayers = True

      self.entSelClass.run(msgMapTool, msg)


   #============================================================================
   # breakFeatures
   #============================================================================
   def breakFeatures(self):
      f = self.entSelClass.entity.getFeature()
      if f is None:
         return
      qadGeom = self.entSelClass.entity.getQadGeom()
      result = breakQadGeometry(qadGeom, self.firstPt, self.secondPt)
      if result is None: return
      
      layer = self.entSelClass.entity.layer
      LineTempLayer = None
      self.plugIn.beginEditCommand("Feature broken", layer)

      line1 = result[0]
      line2 = result[1]
      atGeom = result[2]
      atSubGeom = result[3]
      if layer.geometryType() == QgsWkbTypes.LineGeometry:
         if line1 is not None:
            updGeom = setQadGeomAt(qadGeom, line1, atGeom, atSubGeom)
            if updGeom is None:
               self.plugIn.destroyEditCommand()
               return
            brokenFeature1 = QgsFeature(f)
            # trasformo la geometria nel crs del layer
            brokenFeature1.setGeometry(fromQadGeomToQgsGeom(updGeom, layer))
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, layer, brokenFeature1, False, False) == False:
               self.plugIn.destroyEditCommand()
               return
         if line2 is not None:
            brokenFeature2 = QgsFeature(f)      
            # trasformo la geometria nel crs del layer
            brokenFeature2.setGeometry(fromQadGeomToQgsGeom(line2, layer))
            # plugIn, layer, feature, coordTransform, refresh, check_validity
            if qad_layer.addFeatureToLayer(self.plugIn, layer, brokenFeature2, None, False, False, False) == False:
               self.plugIn.destroyEditCommand()
               return            
      else:
         # aggiungo le linee nei layer temporanei di QAD
         if LineTempLayer is None:
            LineTempLayer = qad_layer.createQADTempLayer(self.plugIn, QgsWkbTypes.LineGeometry)
            self.plugIn.addLayerToLastEditCommand("Feature broken", LineTempLayer)
         
         lineGeoms = []
         if line1 is not None:
            lineGeoms.append(fromQadGeomToQgsGeom(line1, layer))
         if line2 is not None:
            lineGeoms.append(fromQadGeomToQgsGeom(line2, layer))

         # trasformo la geometria in quella dei layer temporanei
         # plugIn, pointGeoms, lineGeoms, polygonGeoms, coord, refresh
         if qad_layer.addGeometriesToQADTempLayers(self.plugIn, None, lineGeoms, None, None, False) == False:
            self.plugIn.destroyEditCommand()
            return
         
         updGeom = delQadGeomAt(qadGeom, atGeom, atSubGeom)

         if updGeom == False: # da cancellare
            # plugIn, layer, feature id, refresh
            if qad_layer.deleteFeatureToLayer(self.plugIn, layer, f.id(), False) == False:
               self.plugIn.destroyEditCommand()
               return
         else:
            brokenFeature1 = QgsFeature(f)
            # trasformo la geometria nel crs del layer
            brokenFeature1.setGeometry(fromQadGeomToQgsGeom(updGeom, layer))
            # plugIn, layer, feature, refresh, check_validity
            if qad_layer.updateFeatureToLayer(self.plugIn, layer, brokenFeature1, False, False) == False:
               self.plugIn.destroyEditCommand()
               return

      self.plugIn.endEditCommand()

       
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      if self.step == 0:     
         self.waitForEntsel(msgMapTool, msg)
         return False # continua
      
      #=========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN'ENTITA' (da step = 0)
      elif self.step == 1:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               layer = self.entSelClass.entity.layer
               self.firstPt = self.entSelClass.point
               self.plugIn.setLastPoint(self.firstPt)
               
               keyWords = QadMsg.translate("Command_BREAK", "First point")
               prompt = QadMsg.translate("Command_BREAK", "Specify second break point or [{0}]: ").format(keyWords)
               
               self.step = 2
               self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di selezione entità
                                   
               englishKeyWords = "First point"
               keyWords += "_" + englishKeyWords
               # si appresta ad attendere un punto o enter o una parola chiave         
               # msg, inputType, default, keyWords, nessun controllo
               self.waitFor(prompt, \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                            None, \
                            keyWords, QadInputModeEnum.NONE)      
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DI INTERRUZIONE (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  pass # opzione di default "secondo punto"
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None or type(value) == unicode:
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_BREAK", "Specify first break point: "))            
            self.step = 3
         elif type(value) == QgsPointXY: # se é stato inserito il secondo punto
            self.secondPt = value
            self.plugIn.setLastPoint(self.secondPt)
            self.breakFeatures()            
            return True
         
         return False 

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO DI INTERRUZIONE (da step = 2)
      elif self.step == 3: # dopo aver atteso un punto si riavvia il comando
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

         self.firstPt =  value
         self.plugIn.setLastPoint(self.firstPt)

         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_BREAK", "Specify second break point: "))
         self.step = 4
         
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DI INTERRUZIONE (da step = 3)
      elif self.step == 4: # dopo aver atteso un punto si riavvia il comando
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

         self.secondPt = value
         self.plugIn.setLastPoint(self.secondPt)
         self.breakFeatures()            
         
         return True
