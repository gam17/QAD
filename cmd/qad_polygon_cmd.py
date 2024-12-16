# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 comando POLYGON per disegnare un poligono regolare
 
                              -------------------
        begin                : 2014-11-17
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


from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_polyline import QadPolyline
from .qad_polygon_maptool import Qad_polygon_maptool_ModeEnum, Qad_polygon_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer


# Classe che gestisce il comando POLYGON
class QadPOLYGONCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadPOLYGONCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "POLYGON")

   def getEnglishName(self):
      return "POLYGON"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runPOLYGONCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/polygon.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_POLYGON", "Draws a regular polygon.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare un rettangolo
      # che non verrà salvato su un layer
      self.virtualCmd = False
      self.centerPt = None
      self.firstEdgePt = None
      self.polyline = QadPolyline()
      self.sideNumber = self.plugIn.lastPolygonSideNumber
      self.constructionModeByCenter = self.plugIn.lastPolygonConstructionModeByCenter
      self.area = 100

   def __del__(self):
      QadCommandClass.__del__(self)

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_polygon_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None       

      
   def addPolygonToLayer(self, layer):
      geom = self.polyline.asGeom(layer.wkbType())
      if geom is not None:
         qad_layer.addGeomToLayer(self.plugIn, layer, self.mapToLayerCoordinates(layer, geom))
      

   # ============================================================================
   # WaitForSideNumber
   # ============================================================================
   def WaitForSideNumber(self):
      self.step = 1
      prompt = QadMsg.translate("Command_POLYGON", "Enter number of sides <{0}>: ")
      self.waitForInt(prompt.format(str(self.sideNumber)), self.sideNumber, \
                      QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         
   # ============================================================================
   # WaitForCenter
   # ============================================================================
   def WaitForCenter(self):
      self.step = 2
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.ASK_FOR_CENTER_PT)
      
      keyWords = QadMsg.translate("Command_POLYGON", "Edge")
      prompt = QadMsg.translate("Command_POLYGON", "Specify center of polygon or [{0}]: ").format(keyWords)
     
      englishKeyWords = "Edge"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter
      #                        msg, inputType,              default, keyWords, nessun controllo         
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)
         
   # ============================================================================
   # WaitForInscribedCircumscribedOption
   # ============================================================================
   def WaitForInscribedCircumscribedOption(self):
      self.step = 3      
      keyWords = QadMsg.translate("Command_POLYGON", "Inscribed in circle") + "/" + \
                 QadMsg.translate("Command_POLYGON", "Circumscribed about circle") + "/" + \
                 QadMsg.translate("Command_POLYGON", "Area")
      prompt = QadMsg.translate("Command_POLYGON", "Enter an option [{0}] <{1}>: ").format(keyWords, \
                                                                                           self.constructionModeByCenter)

      englishKeyWords = "Inscribed in circle" + "/" + "Circumscribed about circle" + "/" + "Area"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere una parola chiave         
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, \
                   self.constructionModeByCenter, \
                   keyWords, QadInputModeEnum.NONE)                  

   # ============================================================================
   # WaitForRadius
   # ============================================================================
   def WaitForRadius(self, layer):
      self.step = 4
      if layer is not None:
         self.getPointMapTool().geomType = layer.geometryType()
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS)
      
      # si appresta ad attendere un punto o un numero reale         
      # msg, inputType, default, keyWords, valori positivi
      prompt = QadMsg.translate("Command_CIRCLE", "Specify the circle radius <{0}>: ")
      self.waitFor(prompt.format(str(self.plugIn.lastRadius)), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                   self.plugIn.lastRadius, "", \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

   # ============================================================================
   # WaitForFirstEdgePt
   # ============================================================================
   def WaitForFirstEdgePt(self):
      self.step = 5
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.ASK_FOR_FIRST_EDGE_PT)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_POLYGON", "Specify the first point of the edge: "))

   # ============================================================================
   # WaitForSecondEdgePt
   # ============================================================================
   def WaitForSecondEdgePt(self, layer):
      self.step = 6
      self.getPointMapTool().firstEdgePt = self.firstEdgePt

      if layer is not None:
         self.getPointMapTool().geomType = layer.geometryType()

      # imposto il map tool
      self.getPointMapTool().setMode(Qad_polygon_maptool_ModeEnum.FIRST_EDGE_PT_KNOWN_ASK_FOR_SECOND_EDGE_PT)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_POLYGON", "Specify the second point of the edge: "))

   # ============================================================================
   # WaitForArea
   # ============================================================================
   def WaitForArea(self):
      self.step = 7
         
      msg = QadMsg.translate("Command_POLYGON", "Enter the polygon area in current units <{0}>: ")
      # si appresta ad attendere un numero reale         
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(msg.format(str(self.area)), QadInputTypeEnum.FLOAT, \
                   self.area, "", \
                   QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

         
   # ============================================================================
   # run
   # ============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      currLayer = None
      if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
         # il layer corrente deve essere editabile e di tipo linea o poligono
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
         if currLayer is None:
            self.showErr(errMsg)
            return True # fine comando
      
      # =========================================================================
      # RICHIESTA NUMERO DI LATI DEL POLIGONO 
      if self.step == 0: # inizio del comando
         self.WaitForSideNumber()
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL NUMERO DI LATI DEL POLIGONO (da step = 0) 
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
               value = self.sideNumber
            else:
               return False
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == int:
            if value < 3:
               self.showErr(QadMsg.translate("Command_POLYGON", "\nEnter an integer greater than 2."))
            else:
               self.sideNumber = value
               self.getPointMapTool().sideNumber = self.sideNumber
               self.plugIn.setLastPolygonSideNumber(self.sideNumber)
               self.WaitForCenter()
         else:
            self.WaitForSideNumber()    

         return False # continua


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL CENTRO DEL POLIGONO (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.WaitForCenter()
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_POLYGON", "Edge") or value == "Edge":
               self.WaitForFirstEdgePt()
         elif type(value) == QgsPointXY:
            self.centerPt = value
            self.getPointMapTool().centerPt = self.centerPt
            self.WaitForInscribedCircumscribedOption() 
                       
         return False # continua

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI POLIGONO INSCRITTO O CIRCOSCRITTO (da step = 2)
      elif self.step == 3:
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.constructionModeByCenter
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # la parola chiave arriva come parametro della funzione
            value = msg
         
         if type(value) == unicode:
            self.constructionModeByCenter = value
            self.plugIn.setLastPolygonConstructionModeByCenter(self.constructionModeByCenter)
            self.getPointMapTool().constructionModeByCenter = self.constructionModeByCenter
            if self.constructionModeByCenter == QadMsg.translate("Command_POLYGON", "Area") or self.constructionModeByCenter == "Area":
               self.WaitForArea()
            else:
               self.WaitForRadius(currLayer)
               
         return False # fine comando

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL RAGGIO (da step = 3)
      elif self.step == 4:
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

         if type(value) == QgsPointXY or type(value) == float: # se é stato inserito il raggio del cerchio            
            if type(value) == QgsPointXY: # se é stato inserito il raggio del cerchio con un punto                        
               self.radius = qad_utils.getDistance(self.centerPt, value)
               ptStart = value
            else:
               self.radius = value
               ptStart = None
               
            self.plugIn.setLastRadius(self.radius)     

            if self.constructionModeByCenter == QadMsg.translate("Command_POLYGON", "Inscribed in circle") or \
               self.constructionModeByCenter == "Inscribed in circle":
               mode = True
            else:
               mode = False
               
            self.polyline.getPolygonByNsidesCenterRadius(self.sideNumber, self.centerPt, self.radius, mode, ptStart)

            if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
               self.addPolygonToLayer(currLayer)
            return True       
         
         return False # fine comando
 
 
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO DELLO SPIGOLO (da step = 2)
      elif self.step == 5: # dopo aver atteso un punto si riavvia il comando
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

         if type(value) == QgsPointXY:
            self.firstEdgePt = value
            self.WaitForSecondEdgePt(currLayer)

         return False
            
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DELLO SPIGOLO (da step = 5)
      elif self.step == 6: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

         if type(value) == QgsPointXY:
            self.polyline.getPolygonByNsidesEdgePts(self.sideNumber, self.firstEdgePt, value)

            if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
               self.addPolygonToLayer(currLayer)
            return True       

         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA AREA POLIGONO (da step = 3)
      elif self.step == 7: # dopo aver atteso un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.area
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               return False
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == float: # é stata inserita l'area
            self.polyline.getPolygonByNsidesArea(self.sideNumber, self.centerPt, value)

            if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
               self.addPolygonToLayer(currLayer)
            return True       
            
         return False
