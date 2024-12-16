# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando CIRCLE per disegnare un cerchio
 
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


# Import the PyQt and QGIS libraries
from qgis.core import QgsWkbTypes, QgsPointXY, QgsGeometry, QgsCoordinateTransform
from qgis.PyQt.QtGui import QIcon


from .. import qad_layer
from .. import qad_utils
from .qad_circle_maptool import Qad_circle_maptool, Qad_circle_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_geom_relations import *
from ..qad_multi_geom import *
from ..qad_circle_fun import *
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_snapper import QadSnapTypeEnum


# Classe che gestisce il comando CIRCLE
class QadCIRCLECommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadCIRCLECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "CIRCLE")

   def getEnglishName(self):
      return "CIRCLE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runCIRCLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/circle.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_CIRCLE", "Draws a circle by many methods.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare un cerchio
      # che non verrà salvato su un layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      self.centerPt = None
      self.radius = None
      self.area = 100      

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_circle_maptool(self.plugIn)
            self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         return self.PointMapTool
      else:
         return None
   
   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PointMapTool is not None:
         self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         
   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # per gestire il comando anche in macro

      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      currLayer = None
      if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer   
         # il layer corrente deve essere editabile e di tipo linea o poligono
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
         if currLayer is None:
            self.showErr(errMsg)
            return True # fine comando
         self.getPointMapTool().layer = currLayer

      # =========================================================================
      # RICHIESTA PRIMO PUNTO o CENTRO
      if self.step == 0: # inizio del comando
         # imposto il map tool
         self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
         keyWords = QadMsg.translate("Command_CIRCLE", "3Points") + "/" + \
                    QadMsg.translate("Command_CIRCLE", "2POints") + "/" + \
                    QadMsg.translate("Command_CIRCLE", "Ttr (tangent tangent radius)")
         prompt = QadMsg.translate("Command_CIRCLE", "Specify the center point of the circle or [{0}]: ").format(keyWords)

         englishKeyWords = "3Points" + "/" + "2POints" + "/" + "Ttr (tangent tangent radius)"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o enter o una parola chiave         
         # msg, inputType, default, keyWords, nessun controllo
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)
         
         self.step = 1
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA CENTRO
      elif self.step == 1: # dopo aver atteso un punto o enter o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if value is None:
            if self.plugIn.lastPoint is not None:
               value = self.plugIn.lastPoint
            else:
               return True # fine comando

         if type(value) == unicode:
            if value == QadMsg.translate("Command_CIRCLE", "3Points") or value == "3Points":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first point on the circle: "))
               self.step = 4           
            elif value == QadMsg.translate("Command_CIRCLE", "2POints") or value == "2POints":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_DIAM_PT)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first end of the circle diameter: "))
               self.step = 7     
            elif value == QadMsg.translate("Command_CIRCLE", "Ttr (tangent tangent radius)") or \
                 value == "Ttr (tangent tangent radius)":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_TAN)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
               self.step = 9     
         elif type(value) == QgsPointXY: # se é stato inserito il centro del cerchio           
            self.centerPt = value
            self.plugIn.setLastPoint(value)
            
            # imposto il map tool
            self.getPointMapTool().centerPt = self.centerPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_RADIUS)                                
           
            keyWords = QadMsg.translate("Command_CIRCLE", "Diameter") + "/" + \
                       QadMsg.translate("Command_CIRCLE", "Area")
            prompt = QadMsg.translate("Command_CIRCLE", "Specify the circle radius or [{0}]: ").format(keyWords)
            
            englishKeyWords = "Diameter" + "/" + "Area"
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere un punto o una parola chiave         
            # msg, inputType, default, keyWords, valori positivi
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, \
                         QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
            
            self.step = 2
         
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA RAGGIO O DIAMETRO O AREA
      elif self.step == 2: # dopo aver atteso un punto o una parola chiave si riavvia il comando
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_CIRCLE", "Diameter") or value == "Diameter":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_DIAM)
               # si appresta ad attendere un punto o un numero reale   
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(QadMsg.translate("Command_CIRCLE", "Specify the circle diameter: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, \
                            "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 3           
            elif value == QadMsg.translate("Command_CIRCLE", "Area") or value == "Area":
               msg = QadMsg.translate("Command_CIRCLE", "Enter circle area in current unit <{0}>: ")
               # si appresta ad attendere un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(msg.format(str(self.area)), QadInputTypeEnum.FLOAT, \
                            self.area, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
               self.step = 13         
         elif type(value) == QgsPointXY or type(value) == float: # se é stato inserito il raggio del cerchio            
            if type(value) == QgsPointXY: # se é stato inserito il raggio del cerchio con un punto                        
               self.radius = qad_utils.getDistance(self.centerPt, value)
            else:
               self.radius = value
               
            self.plugIn.setLastRadius(self.radius)     

            circle = QadCircle()
            if circle.set(self.centerPt, self.radius) is not None:
               geom = circle.asGeom(currLayer.wkbType())
               if geom is not None:
                  if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # fine comando
            
            keyWords = QadMsg.translate("Command_CIRCLE", "Diameter") + "/" + \
                       QadMsg.translate("Command_CIRCLE", "Area")
            prompt = QadMsg.translate("Command_CIRCLE", "Specify the circle radius or [{0}]: ").format(keyWords)
                                 
            englishKeyWords = "Diameter" + "/" + "Area"
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere un punto o una parola chiave         
            # msg, inputType, default, keyWords, valori positivi
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
            self.isValidPreviousInput = False # per gestire il comando anche in macro                       
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DIAMETRO DEL CERCHIO (da step = 2)
      elif self.step == 3: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

         if type(value) == QgsPointXY: # se é stato inserito un punto          
            self.radius = qad_utils.getDistance(self.centerPt, value) / 2
         elif type(value) == float: # se é stato inserito un numero reale
            self.radius = value / 2

         self.plugIn.setLastRadius(self.radius)     
      
         circle = QadCircle()         
         if circle.set(self.centerPt, self.radius) is not None:
            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
                  
         # si appresta ad attendere un punto o un numero reale   
         # msg, inputType, default, keyWords, valori positivi
         self.waitFor(QadMsg.translate("Command_CIRCLE", "Specify the circle diameter: "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, \
                      "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.isValidPreviousInput = False # per gestire il comando anche in macro     
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO DEL CERCHIO (da step = 1)
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
               
            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # il punto arriva come parametro della funzione
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # se é stato selezionato un punto con la modalità TAN_DEF é un punto differito
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.firstPt = None
            self.firstPtTan = value
            
            # la funzione ritorna una lista con 
            # (<minima distanza>
            #  <punto più vicino>
            #  <indice della geometria più vicina>
            #  <indice della sotto-geometria più vicina>
            #   se geometria chiusa è tipo polyline la lista contiene anche
            #  <indice della parte della sotto-geometria più vicina>
            #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
            # )
            # parte più vicina al punto self.firstPtTan
            result = getQadGeomClosestPart(entity.getQadGeom(), self.firstPtTan)
            # duplico la geometria della parte
            self.firstGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
            
            # imposto il map tool
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
         else: # altrimenti é un punto esplicito 
            self.firstPt = value
            self.plugIn.setLastPoint(value)    
            # imposto il map tool
            self.getPointMapTool().firstPt = self.firstPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
   
         # si appresta ad attendere un punto         
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second point on the circle: "))
         
         self.step = 5
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DEL CERCHIO (da step = 4)
      elif self.step == 5:  # dopo aver atteso un punto si riavvia il comando
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # il punto arriva come parametro della funzione
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # se é stato selezionato un punto con la modalità TAN_DEF é un punto differito
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.secondPt = None
            self.secondPtTan = value
            
            # la funzione ritorna una lista con 
            # (<minima distanza>
            #  <punto più vicino>
            #  <indice della geometria più vicina>
            #  <indice della sotto-geometria più vicina>
            #   se geometria chiusa è tipo polyline la lista contiene anche
            #  <indice della parte della sotto-geometria più vicina>
            #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
            # )
            # parte più vicina al punto self.secondPtTan
            result = getQadGeomClosestPart(entity.getQadGeom(), self.secondPtTan)
            # duplico la geometria della parte
            self.secondGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
            # imposto il map tool
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT)
         else: # altrimenti é un punto esplicito 
            self.secondPt = value
            self.plugIn.setLastPoint(value)    
            # imposto il map tool
            self.getPointMapTool().secondPt = self.secondPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_THIRD_PT)
   
         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify the third point on the circle: "))
         
         self.step = 6
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL TERZO PUNTO DEL CERCHIO (da step = 5)
      elif self.step == 6:  # dopo aver atteso un punto si riavvia il comando
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # il punto arriva come parametro della funzione
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # se é stato selezionato un punto con la modalità TAN_DEF é un punto differito
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.thirdPt = None
            self.thirdPtTan = value
            
            # la funzione ritorna una lista con 
            # (<minima distanza>
            #  <punto più vicino>
            #  <indice della geometria più vicina>
            #  <indice della sotto-geometria più vicina>
            #   se geometria chiusa è tipo polyline la lista contiene anche
            #  <indice della parte della sotto-geometria più vicina>
            #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
            # )
            # parte più vicina al punto self.secondPtTan
            result = getQadGeomClosestPart(entity.getQadGeom(), self.thirdPtTan)
            # duplico la geometria della parte
            self.thirdGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
         else: # altrimenti é un punto esplicito 
            self.thirdPt = value
            self.plugIn.setLastPoint(value)    

         circle = None
         if self.firstPt is None: # se il primo punto é definito con un punto differito
            if self.secondPt is None: # se il secondo punto é definito con un punto differito
               if self.thirdPt is None: # se il terzo punto é definito con un punto differito
                  circle = circleFrom3TanPts(self.firstGeomTan, self.firstPtTan, \
                                             self.secondGeomTan, self.secondPtTan, \
                                             self.thirdGeomTan, self.thirdPtTan)
               else: # se il terzo punto é definito con un punto esplicito
                  circle = circleFrom1IntPt2TanPts(self.thirdPt, self.firstGeomTan, self.firstPtTan,
                                                   self.secondGeomTan, self.secondPtTan)
            else: # se il secondo punto é definito con un punto esplicito
               if self.thirdPt is None: # se il terzo punto é definito con un punto differito
                  circle = circleFrom1IntPt2TanPts(self.secondPt, self.firstGeomTan, self.firstPtTan,
                                                   self.thirdGeomTan, self.thirdPtTan)
               else: # se il terzo punto é definito con un punto esplicito
                  circle = circleFrom2IntPts1TanPt(self.secondPt, self.thirdPt, \
                                                   self.firstGeomTan, self.firstPtTan)
         else: # se il primo punto é definito con un punto esplicito
            if self.secondPt is None: # se il secondo punto é definito con un punto differito
               if self.thirdPt is None: # se il terzo punto é definito con un punto differito
                  circe = circleFrom1IntPt2TanPts(self.firstPt, self.secondGeomTan, self.secondPtTan,
                                                  self.thirdGeomTan, self.thirdPtTan)
               else: # se il terzo punto é definito con un punto esplicito
                  circe = circleFrom2IntPts1TanPt(self.firstPt, self.thirdPt, \
                                                  self.secondGeomTan, self.secondPtTan)
            else: # se il secondo punto é definito con un punto esplicito
               if self.thirdPt is None: # se il terzo punto é definito con un punto differito
                  circle = circleFrom2IntPts1TanPt(self.firstPt, self.secondPt, \
                                                   self.thirdGeomTan, self.thirdPtTan)
               else: # se il terzo punto é definito con un punto esplicito
                  circle = circleFrom3Pts(self.firstPt, self.secondPt, value)
                     
         if circle is not None:
            self.centerPt = circle.center
            self.radius = circle.radius
            
            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
                          
         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify the third point on the circle: "))
         self.isValidPreviousInput = False # per gestire il comando anche in macro     
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA PRIMA ESTREMITA' DIAM DEL CERCHIO (da step = 1)
      elif self.step == 7:  # dopo aver atteso un punto si riavvia il comando
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # il punto arriva come parametro della funzione
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # se é stato selezionato un punto con la modalità TAN_DEF é un punto differito
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.firstDiamPt = None
            self.firstDiamPtTan = value
            result = getQadGeomClosestPart(entity.getQadGeom(), self.firstDiamPtTan)
            # duplico la geometria della parte
            self.firstDiamGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
            # imposto il map tool
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT)
         else: # altrimenti é un punto esplicito 
            self.firstDiamPt = value        
            # imposto il map tool
            self.getPointMapTool().firstDiamPt = self.firstDiamPt
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_DIAM_PT_KNOWN_ASK_FOR_SECOND_DIAM_PT)
   
         # si appresta ad attendere un punto         
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second end of the circle diameter: "))
         
         self.step = 8
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA SECONDA ESTREMITA' DIAM DEL CERCHIO (da step = 7)
      elif self.step == 8:  # dopo aver atteso un punto si riavvia il comando
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

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity
         else: # il punto arriva come parametro della funzione
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         # se é stato selezionato un punto con la modalità TAN_DEF é un punto differito
         if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
            self.secondDiamPt = None
            self.secondDiamPtTan = value
            result = getQadGeomClosestPart(entity.getQadGeom(), self.secondDiamPtTan)
            # duplico la geometria della parte
            self.secondDiamGeomTan = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4]).copy()
         else: # altrimenti é un punto esplicito 
            self.secondDiamPt = value  
         
         circle = None
         if self.firstDiamPt is None: # se il diametro é definito con il primo punto differito
            if self.secondDiamPt is None: # il diametro é definito con il secondo punto differito
               circle = circleFromDiamEnds2TanPts(self.firstDiamGeomTan, self.firstDiamPtTan, \
                                                  self.secondDiamGeomTan, self.secondDiamPtTan)
            else: # se il diametro è definito con il secondo punto esplicito
               circle = circleFromDiamEndsPtTanPt(self.secondDiamPt, self.firstDiamGeomTan, self.firstDiamPtTan)
         else: # se il diametro è definito con il primo punto esplicito
            if self.secondDiamPt is None: # il diametro è definito con il secondo punto differito
               circle = circleFromDiamEndsPtTanPt(self.firstDiamPt, self.secondDiamGeomTan, self.secondDiamPtTan)
            else: # se il diametro è definito con il secondo punto esplicito
               circle = QadCircle().fromDiamEnds(self.firstDiamPt, self.secondDiamPt)
                  
         if circle is not None:
            self.centerPt = circle.center
            self.radius = circle.radius
            
            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
                     
         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second end of the circle diameter: "))
         self.isValidPreviousInput = False # per gestire il comando anche in macro     
         return False

                 
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMA TANGENTE (da step = 1)
      elif self.step == 9: # dopo aver atteso un punto si riavvia il comando
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

            entity = self.getPointMapTool().entity
         else: # il punto arriva come parametro della funzione
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
            self.isValidPreviousInput = False # per gestire il comando anche in macro     
            return False

         if not entity.isInitialized(): # se non è stata selezionata una entità
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
            self.isValidPreviousInput = False # per gestire il comando anche in macro     
            return False
         
         result = getQadGeomClosestPart(entity.getQadGeom(), self.getPointMapTool().point)
         g = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
         gType = g.whatIs()
         if gType != "LINE" and gType != "ARC" and gType != "CIRCLE":
            self.showErr(QadMsg.translate("Command_CIRCLE", "\nSelect a circle, an arc or a line."))
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify first tangent element of the circle: "))
            self.isValidPreviousInput = False # per gestire il comando anche in macro
            return False
         
         self.tanPt1 = self.getPointMapTool().point
         # duplico la geometria della parte
         self.tanGeom1 = g.copy()
         
         # imposto il map tool
         self.getPointMapTool().tanGeom1 = self.tanGeom1
         self.getPointMapTool().tanPt1 = self.tanPt1
         self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_TAN)
      
         # si appresta ad attendere un punto         
         self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
         self.step = 10
         return False
         
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDA TANGENTE (da step = 9)
      elif self.step == 10: # dopo aver atteso un punto si riavvia il comando
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

            entity = self.getPointMapTool().entity
         else: # il punto arriva come parametro della funzione
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
            self.isValidPreviousInput = False # per gestire il comando anche in macro
            return False

         if not entity.isInitialized(): # se non è stata selezionata una entità
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
            self.isValidPreviousInput = False # per gestire il comando anche in macro
            return False

         result = getQadGeomClosestPart(entity.getQadGeom(), self.getPointMapTool().point)
         g = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
         gType = g.whatIs()
         if gType != "LINE" and gType != "ARC" and gType != "CIRCLE":
            self.showErr(QadMsg.translate("Command_CIRCLE", "\nSelect a circle, an arc or a line."))
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second tangent element of the circle: "))
            self.isValidPreviousInput = False # per gestire il comando anche in macro
            return False

         self.tanPt2 = self.getPointMapTool().point
         # duplico la geometria della parte
         self.tanGeom2 = g.copy()
         
         # imposto il map tool
         self.getPointMapTool().tanGeom2 = self.tanGeom2
         self.getPointMapTool().tanPt2 = self.tanPt2
         self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_KNOWN_ASK_FOR_RADIUS)
      
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori positivi
         msg = QadMsg.translate("Command_CIRCLE", "Specify the circle radius <{0}>: ")
         self.waitFor(msg.format(str(self.plugIn.lastRadius)), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      self.plugIn.lastRadius, "", \
                      QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.step = 11
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA RAGGIO (da step = 10)
      elif self.step == 11: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
            self.startPtForRadius = value
            
            # imposto il map tool
            self.getPointMapTool().startPtForRadius = self.startPtForRadius
            self.getPointMapTool().setMode(Qad_circle_maptool_ModeEnum.FIRST_SECOND_TAN_FIRSTPTRADIUS_KNOWN_ASK_FOR_SECONDPTRADIUS)
         
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_CIRCLE", "Specify second point: "))
            self.step = 12
            return False            
         else:
            self.plugIn.setLastRadius(value)

            circle = circleFrom2TanPtsRadius(self.tanGeom1, self.tanPt1, \
                                             self.tanGeom2, self.tanPt2, value)
            if circle is not None:
               geom = circle.asGeom(currLayer.wkbType())
               if geom is not None:
                  self.centerPt = circle.center
                  self.radius = circle.radius
                  if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               else:
                  self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))
            else:
               self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))
                  
            return True # fine comando

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO DEL RAGGIO (da step = 11)
      elif self.step == 12: # dopo aver atteso un punto si riavvia il comando
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

         self.radius = qad_utils.getDistance(self.startPtForRadius, value)
         self.plugIn.setLastRadius(self.radius)     

         circle = circleFrom2TanPtsRadius(self.tanGeom1, self.tanPt1, \
                                           self.tanGeom2, self.tanPt2, self.radius)
         if circle is not None:
            geom = circle.asGeom(currLayer.wkbType())
            if geom is not None:
               self.centerPt = circle.center
               self.radius = circle.radius
               if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
            else:
               self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))
         else:
            self.showMsg(QadMsg.translate("Command_CIRCLE", "\nThe circle doesn't exist."))
         return True # fine comando

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA AREA DEL CERCHIO (da step = 2)
      elif self.step == 13: # dopo aver atteso un numero si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton != True: # se NON usato il tasto destro del mouse
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == float: # è stata inserita l'area
            self.area = value
      
            circle = QadCircle().fromCenterArea(self.centerPt, self.area)
            if circle is not None:
               self.radius = circle.radius 
               self.plugIn.setLastRadius(self.radius)                    
               geom = circle.asGeom(currLayer.wkbType())
               if geom is not None:
                  if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # fine comando
               
         self.isValidPreviousInput = False # per gestire il comando anche in macro      
         return False
