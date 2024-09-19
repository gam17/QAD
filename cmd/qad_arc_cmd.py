# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 comando ARC per disegnare un arco
 
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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsWkbTypes, QgsGeometry, QgsPointXY
import math


from ..qad_arc import QadArc
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_arc_maptool import Qad_arc_maptool, Qad_arc_maptool_ModeEnum, \
                              Qad_gripChangeArcRadius_maptool, Qad_gripChangeArcRadius_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer 
from ..qad_grip import QadGripStatusEnum
from ..qad_dim import QadDimStyles


# Classe che gestisce il comando ARC
class QadARCCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadARCCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ARC")

   def getEnglishName(self):
      return "ARC"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runARCCommand)
   
   def getIcon(self):
      return QIcon(":/plugins/qad/icons/arc.svg")

   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_ARC", "Draws an arc by many methods.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.vertices = []

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_arc_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None
         
   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # per gestire il comando anche in macro
           
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
      if currLayer is None:
         self.showErr(errMsg)
         return True # fine comando

      #=========================================================================
      # RICHIESTA PRIMO PUNTO o CENTRO
      if self.step == 0: # inizio del comando
         # imposto il map tool
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_START_PT)
         keyWords = QadMsg.translate("Command_ARC", "Center")
         
         prompt = QadMsg.translate("Command_ARC", "Specify the start point of the arc or [{0}]:").format(keyWords)                 
         
         englishKeyWords = "Center"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o enter o una parola chiave         
         # msg, inputType, default, keyWords, nessun controllo di modo
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)         
         self.step = 1
         
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMO PUNTO o CENTRO
      elif self.step == 1: # dopo aver atteso un punto o enter o una parola chiave si riavvia il comando
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

         if value is None:
            if self.plugIn.lastPoint is not None:
               value = self.plugIn.lastPoint
            else:
               return True # fine comando

         if type(value) == QgsPointXY: # se é stato inserito il punto iniziale dell'arco           
            self.startPt = value
            self.plugIn.setLastPoint(value)
            
            # imposto il map tool
            self.getPointMapTool().arcStartPt = self.startPt
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT)
                                
            keyWords = QadMsg.translate("Command_ARC", "Center") + "/" + \
                       QadMsg.translate("Command_ARC", "End")
            
            prompt = QadMsg.translate("Command_ARC", "Specify second point of the arc or [{0}]:").format(keyWords)                 
            
            englishKeyWords = "Center" + "/" + "End"
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere un punto o una parola chiave         
            # msg, inputType, default, keyWords
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NONE)
            
            self.step = 2
            return False
         else: # si vuole inserire il centro dell'arco
            # imposto il map tool
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the center of the arc: "))
            
            self.step = 13
            return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO o CENTRO o FINE
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
            if value == QadMsg.translate("Command_ARC", "Center") or value == "Center":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_CENTER_PT)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the center of the arc: "))
               self.step = 4           
            elif value == QadMsg.translate("Command_ARC", "End") or value == "End":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_END_PT)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the final point of the arc: "))
               self.step = 8     
         elif type(value) == QgsPointXY: # se é stato inserito il secondo punto dell'arco            
            self.secondPt = value
            # imposto il map tool
            self.getPointMapTool().arcSecondPt = self.secondPt
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT)

            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the final point of the arc: "))
            self.step = 3
                  
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO FINALE DELL'ARCO (da step = 2)
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

         self.endPt = value
         
         arc = QadArc()         
         if arc.fromStartSecondEndPts(self.startPt, self.secondPt, self.endPt) == True:
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # se i punti sono così vicini da essere considerati uguali
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
      
         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the final point of the arc: "))
         self.isValidPreviousInput = False # per gestire il comando anche in macro     
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA CENTRO DELL'ARCO (da step = 2)
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

         self.centerPt = value
         self.plugIn.setLastPoint(value)
         
         # imposto il map tool
         self.getPointMapTool().arcCenterPt = self.centerPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT)
         
         keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                    QadMsg.translate("Command_ARC", "chord Length")
                             
         prompt = QadMsg.translate("Command_ARC", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)                 
                         
         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o una parola chiave         
         # msg, inputType, default, keyWords, valori nulli non ammessi
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         
         self.step = 5
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare punto finale dell'arco o [Angolo/Lunghezza corda]: " (da step = 4)
      elif self.step == 5: # dopo aver atteso un punto o una parola chiave si riavvia il comando
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
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == unicode:  
            if value == QadMsg.translate("Command_ARC", "Angle") or value == "Angle":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori nulli non ammessi
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 6
               return False                              
            elif value == QadMsg.translate("Command_ARC", "chord Length") or value == "chord Length":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the chord length (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 7
               return False                              
         elif type(value) == QgsPointXY: # se é stato inserito il punto finale dell'arco
            self.endPt = value
                     
            arc = QadArc()
            if arc.fromStartCenterEndPts(self.startPt, self.centerPt, self.endPt) == True:
               if ctrlPressed: # inverto angolo iniziale-finale
                  arc.inverseAngles()
               
               self.plugIn.setLastPoint(arc.getEndPt())

               geom = arc.asGeom(currLayer.wkbType())
               if geom is not None:
                  # se i punti sono così vicini da essere considerati uguali
                  if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
                  else:
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                     
                  self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
                  
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # fine comando
                           
            keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                       QadMsg.translate("Command_ARC", "chord Length")
            prompt = QadMsg.translate("Command_ARC", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

            englishKeyWords = "Angle" + "/" + "chord Length"
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere un punto o una parola chiave         
            # msg, inputType, default, keyWords, valori nulli non ammessi
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_NULL)
            self.isValidPreviousInput = False # per gestire il comando anche in macro
            return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare angolo inscritto: " (da step = 5)
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
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.angle = qad_utils.getAngleBy2Pts(self.centerPt, value)             
         else:
            self.angle = value

         arc = QadArc()         
         if arc.fromStartCenterPtsAngle(self.startPt, self.centerPt, self.angle) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # se i punti sono così vicini da essere considerati uguali
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
            
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori nulli non ammessi
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
         self.isValidPreviousInput = False # per gestire il comando anche in macro         
         return False

      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare lunghezza della corda: " (da step = 5)
      elif self.step == 7: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.chord = qad_utils.getDistance(self.startPt, value)             
         else:
            self.chord = value

         arc = QadArc()         
         if arc.fromStartCenterPtsChord(self.startPt, self.centerPt, self.chord) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()

            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # se i punti sono così vicini da essere considerati uguali
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando

         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori positivi ammessi
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the chord length (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.isValidPreviousInput = False # per gestire il comando anche in macro         
         return False
                 
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare punto finale dell'arco: " (da step = 1)
      elif self.step == 8: # dopo aver atteso un punto si riavvia il comando
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

         self.endPt = value
         self.plugIn.setLastPoint(self.endPt)

         # imposto il map tool
         self.getPointMapTool().arcEndPt = self.endPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_CENTER)
      
         keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                    QadMsg.translate("Command_ARC", "Direction") + "/" + \
                    QadMsg.translate("Command_ARC", "Radius")
                    
         prompt = QadMsg.translate("Command_ARC", "Specify the center point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

         englishKeyWords = "Angle" + "/" + "Direction" + "/" + "Radius"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o una parola chiave         
         # msg, inputType, default, keyWords, valori nulli non ammessi
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         
         self.step = 9
         return False
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare centro dell'arco o [Angolo/Direzione/Raggio]: " (da step = 8)
      elif self.step == 9: # dopo aver atteso un punto o una parola chiave si riavvia il comando
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
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ARC", "Angle") or value == "Angle":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_ANGLE)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 10
               return False                              
            elif value == QadMsg.translate("Command_ARC", "Direction") or value == "Direction":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_TAN)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the tangent direction for the start point of the arc (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", QadInputModeEnum.NOT_NULL)
               self.step = 11
               return False            
            elif value == QadMsg.translate("Command_ARC", "Radius") or value == "Radius":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_END_PT_KNOWN_ASK_FOR_RADIUS)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_ARC", "Specify the radius of the arc (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 12
               return False                              
         elif type(value) == QgsPointXY: # se é stato inserito il centro dell'arco
            self.centerPt = value

            arc = QadArc()         
            if arc.fromStartCenterEndPts(self.startPt, self.centerPt, self.endPt) == True:
               if ctrlPressed: # inverto angolo iniziale-finale
                  arc.inverseAngles()
                  
               self.plugIn.setLastPoint(arc.getEndPt())
               geom = arc.asGeom(currLayer.wkbType())
               if geom is not None:
                  # se i punti sono così vicini da essere considerati uguali
                  if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
                  else:
                     self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                     
                  self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
                  
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # fine comando
                           
            keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                       QadMsg.translate("Command_ARC", "Direction") + "/" + \
                       QadMsg.translate("Command_ARC", "Radius")
                       
            prompt = QadMsg.translate("Command_ARC", "Specify the center point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
                      
            englishKeyWords = "Angle" + "/" + "Direction" + "/" + "Radius"
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere un punto o una parola chiave         
            # msg, inputType, default, keyWords, isNullable
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_NULL)
            self.isValidPreviousInput = False # per gestire il comando anche in macro                     
            return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare angolo inscritto: " (da step = 9)
      elif self.step == 10: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
         else:
            self.angle = value
            
         arc = QadArc()         
         if arc.fromStartEndPtsAngle(self.startPt, self.endPt, self.angle) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # se i punti sono così vicini da essere considerati uguali
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando

         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori non nulli
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the included angle (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
         self.isValidPreviousInput = False # per gestire il comando anche in macro         
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare direzione tangente per il punto iniziale dell'arco: " (da step = 9)
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
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False
            
         if type(value) == QgsPointXY:
            self.angleTan = qad_utils.getAngleBy2Pts(self.startPt, value)             
         else:
            self.angleTan = value

         arc = QadArc()         
         if arc.fromStartEndPtsTan(self.startPt, self.endPt, self.angleTan) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # se i punti sono così vicini da essere considerati uguali
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando

         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the tangent direction for the start point of the arc (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
         self.isValidPreviousInput = False # per gestire il comando anche in macro
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare raggio dell'arco: " (da step = 9)
      elif self.step == 12: # dopo aver atteso un punto o un numero reale si riavvia il comando
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
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.radius = qad_utils.getDistance(self.endPt, value)             
         else:
            self.radius = value

         self.plugIn.setLastRadius(self.radius)
         
         arc = QadArc()
         if arc.fromStartEndPtsRadius(self.startPt, self.endPt, self.radius) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
               
            self.plugIn.setLastPoint(arc.getEndPt())
            geom = arc.asGeom(currLayer.wkbType())
            if geom is not None:
               # se i punti sono così vicini da essere considerati uguali
               if qad_utils.ptNear(self.startPt, arc.getStartPt()):
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnEndPt())
               else:
                  self.plugIn.setLastSegmentAng(arc.getTanDirectionOnStartPt() + math.pi)
                  
               self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
               
               qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando

         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori positivi
         self.waitFor(QadMsg.translate("Command_ARC", "Specify the radius of the arc (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
         self.isValidPreviousInput = False # per gestire il comando anche in macro
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA CENTRO DELL'ARCO (da step = 1)
      elif self.step == 13: # dopo aver atteso un punto si riavvia il comando
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

         self.centerPt = value
         self.plugIn.setLastPoint(value)

         # imposto il map tool
         self.getPointMapTool().arcCenterPt = self.centerPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.CENTER_PT_KNOWN_ASK_FOR_START_PT)

         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_ARC", "Specify the start point of the arc: "))
         self.step = 14
         
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO INIZIALE DELL'ARCO (da step = 13)
      elif self.step == 14: # dopo aver atteso un punto si riavvia il comando
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

         self.startPt = value
         self.plugIn.setLastPoint(value)

         # imposto il map tool
         self.getPointMapTool().arcStartPt = self.startPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT)
         
         keyWords = QadMsg.translate("Command_ARC", "Angle") + "/" + \
                    QadMsg.translate("Command_ARC", "chord Length")
         
         prompt = QadMsg.translate("Command_ARC", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
                           
         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o una parola chiave         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         
         self.step = 5
         return False


#============================================================================
# Classe che gestisce il comando per cambiare il raggio di un arco per i grip
#============================================================================
class QadGRIPCHANGEARCRADIUSCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadGRIPCHANGEARCRADIUSCommandClass(self.plugIn)

   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = None
      self.skipToNextGripCommand = False
      self.copyEntities = False
      self.basePt = QgsPointXY()
      self.nOperationsToUndo = 0

   
   def __del__(self):
      QadCommandClass.__del__(self)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_gripChangeArcRadius_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None

   
   #============================================================================
   # setSelectedEntityGripPoints
   #============================================================================
   def setSelectedEntityGripPoints(self, entitySetGripPoints):
      # lista delle entityGripPoint con dei grip point selezionati
      # setta la prima entità con un grip selezionato
      self.entity = None
      for entityGripPoints in entitySetGripPoints.entityGripPoints:
         for gripPoint in entityGripPoints.gripPoints:
            # grip point selezionato
            if gripPoint.getStatus() == QadGripStatusEnum.SELECTED:
               # verifico se l'entità appartiene ad uno stile di quotatura
               if QadDimStyles.isDimEntity(entityGripPoints.entity):
                  return False
               if entityGripPoints.entity.getQadGeom().whatIs() != "ARC":
                  return False
               
               self.entity = entityGripPoints.entity
               arc = entityGripPoints.entity.getQadGeom() # arco in map coordinate
               self.basePt.set(arc.center.x(), arc.center.y())
               return True
      return False
   

   #============================================================================
   # changeRadius
   #============================================================================
   def changeRadius(self, radius):
      # radius = nuovo raggio dell'arco
      if radius <= 0:
         return False
      arc = self.entity.getQadGeom()
      arc.radius = radius
      points = arc.asPolyline()
      if points is None:
         return False
      
      g = QgsGeometry.fromPolylineXY(points)
      f = self.entity.getFeature()      
      f.setGeometry(g)
      
      self.plugIn.beginEditCommand("Feature stretched", [self.entity.layer])
      
      if self.copyEntities == False:
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False
      else:
         # plugIn, layer, features, coordTransform, refresh, check_validity
         if qad_layer.addFeatureToLayer(self.plugIn, self.entity.layer, f, None, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False

      self.plugIn.setLastRadius(radius)
      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True


   #============================================================================
   # waitForRadius
   #============================================================================
   def waitForRadius(self):
      keyWords = QadMsg.translate("Command_GRIP", "Base point") + "/" + \
                 QadMsg.translate("Command_GRIP", "Copy") + "/" + \
                 QadMsg.translate("Command_GRIP", "Undo") + "/" + \
                 QadMsg.translate("Command_GRIP", "eXit")
      prompt = QadMsg.translate("Command_GRIPCHANGEARCRADIUS", "Specify the radius or [{0}]: ").format(keyWords)

      englishKeyWords = "Base point" + "/" + "Copy" + "/" + "Undo" + "/" "eXit"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave
      # msg, inputType, default, keyWords, valori positivi
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
      self.step = 1
      # imposto il map tool
      self.getPointMapTool().setEntity(self.entity) # setta basePt nel centro dell'arco
      self.getPointMapTool().basePt = self.basePt
      self.getPointMapTool().setMode(Qad_gripChangeArcRadius_maptool_ModeEnum.BASE_PT_KNOWN_ASK_FOR_RADIUS_PT)


   #============================================================================
   # waitForBasePt
   #============================================================================
   def waitForBasePt(self):
      self.step = 2   
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_gripChangeArcRadius_maptool_ModeEnum.ASK_FOR_BASE_PT)

      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_GRIP", "Specify base point: "))


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
     
      #=========================================================================
      # RICHIESTA SELEZIONE OGGETTI
      if self.step == 0: # inizio del comando
         if self.entity is None: # non ci sono oggetti da stirare
            return True
         self.showMsg(QadMsg.translate("Command_GRIPCHANGEARCRADIUS", "\n** RADIUS **\n"))
         # si appresta ad attendere raggio
         self.waitForRadius()
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL RAGGIO DI RACCORDO (da step = 1)
      elif self.step == 1:
         ctrlKey = False
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.copyEntities == False:
                     self.skipToNextGripCommand = True
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
            ctrlKey = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_GRIP", "Base point") or value == "Base point":
               # si appresta ad attendere il punto base
               self.waitForBasePt()
            elif value == QadMsg.translate("Command_GRIP", "Copy") or value == "Copy":
               # Copia entità lasciando inalterate le originali
               self.copyEntities = True                     
               # si appresta ad attendere raggio
               self.waitForRadius()
            elif value == QadMsg.translate("Command_GRIP", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                  
               # si appresta ad attendere raggio
               self.waitForRadius()
            elif value == QadMsg.translate("Command_GRIP", "eXit") or value == "eXit":
               return True # fine comando
         elif type(value) == QgsPointXY or type(value) == float: # se é stato inserito il raggio
            if type(value) == QgsPointXY: # se é stato inserito il raggio con un punto
               if value == self.basePt:
                  self.showMsg(QadMsg.translate("QAD", "\nThe value must be positive and not zero."))
                  # si appresta ad attendere raggio
                  self.waitForRadius()
                  return False
                                      
               radius = qad_utils.getDistance(self.basePt, value)
            else:
               radius = value

            if ctrlKey:
               self.copyEntities = True
   
            self.changeRadius(radius)

            if self.copyEntities == False:
               return True
            # si appresta ad attendere raggio
            self.waitForRadius()
         else:
            if self.copyEntities == False:
               self.skipToNextGripCommand = True
            return True # fine comando

         return False
              
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO BASE (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  pass # opzione di default
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il punto base
            self.basePt.set(value.x(), value.y())
            # imposto il map tool
            self.getPointMapTool().basePt = self.basePt
            
         # si appresta ad attendere raggio
         self.waitForRadius()

         return False
