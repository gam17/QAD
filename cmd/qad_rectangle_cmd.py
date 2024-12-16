# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 comando RECTANGLE per disegnare un rettangolo
 
                              -------------------
        begin                : 2013-12-02
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
from qgis.core import QgsWkbTypes, QgsPointXY
from qgis.PyQt.QtGui import QIcon


from ..qad_polyline import QadPolyline
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_rectangle_maptool import Qad_rectangle_maptool_ModeEnum, Qad_rectangle_maptool
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass


# Classe che gestisce il comando RECTANGLE
class QadRECTANGLECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadRECTANGLECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "RECTANGLE")

   def getEnglishName(self):
      return "RECTANGLE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runRECTANGLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/rectangle.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_RECTANGLE", "Creates a rectangle.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare un rettangolo
      # che non verrà salvato su un layer
      self.virtualCmd = False
      self.firstCorner = None
      self.gapType = 0 # 0 = Angoli retti; 1 = Raccorda i segmenti; 2 = Cima i segmenti
      self.gapValue1 = 0 # se gapType = 1 -> raggio di curvatura; se gapType = 2 -> prima distanza di cimatura
      self.gapValue2 = 0 # se gapType = 2 -> seconda distanza di cimatura
      self.area = 100
      self.dim1 = 10
      self.rot = 0
      self.polyline = QadPolyline()
      
      self.GetDistClass = None
      self.GetAngleClass = None
      self.defaultValue = None # usato per gestire il tasto dx del mouse

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      # quando si é in fase di richiesta distanza
      if self.step == 3 or self.step == 4 or self.step == 5 or \
         self.step == 8 or self.step == 9 or self.step == 10 or self.step == 11:
         return self.GetDistClass.getPointMapTool()
      # quando si é in fase di richiesta rotazione
      elif self.step == 13:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_rectangle_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None       


   def getCurrentContextualMenu(self):
      # quando si é in fase di richiesta distanza
      if self.step == 3 or self.step == 4 or self.step == 5 or \
         self.step == 8 or self.step == 9 or self.step == 10 or self.step == 11:
         return self.GetDistClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta rotazione
      elif self.step == 13:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

      
   def addRectangleToLayer(self, layer):
      vertices = self.polyline.asPolyline()
      if layer.geometryType() == QgsWkbTypes.LineGeometry:
         qad_layer.addLineToLayer(self.plugIn, layer, vertices)
      elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:                          
         qad_layer.addPolygonToLayer(self.plugIn, layer, vertices)
      
         
   # ============================================================================
   # WaitForFirstCorner
   # ============================================================================
   def WaitForFirstCorner(self):
      self.step = 1         
      self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER)
      
      keyWords = QadMsg.translate("Command_RECTANGLE", "Chamfer") + "/" + \
                 QadMsg.translate("Command_RECTANGLE", "Fillet")
      prompt = QadMsg.translate("Command_RECTANGLE", "Specify first corner or [{0}]: ").format(keyWords)

      englishKeyWords = "Chamfer" + "/" + "Fillet"
      keyWords += "_" + englishKeyWords     
      # si appresta ad attendere un punto o enter
      #                        msg, inputType,              default, keyWords, nessun controllo         
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)
         
   # ============================================================================
   # WaitForSecondCorner
   # ============================================================================
   def WaitForSecondCorner(self, layer):
      self.step = 2
      self.getPointMapTool().rot = self.rot
      self.getPointMapTool().gapType = self.gapType
      self.getPointMapTool().gapValue1 = self.gapValue1
      self.getPointMapTool().gapValue2 = self.gapValue2
      self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_SECOND_CORNER)
      if layer is not None:
         self.getPointMapTool().geomType = layer.geometryType()
      
      keyWords = QadMsg.translate("Command_RECTANGLE", "Area") + "/" + \
                 QadMsg.translate("Command_RECTANGLE", "Dimensions") + "/" + \
                 QadMsg.translate("Command_RECTANGLE", "Rotation")
      prompt = QadMsg.translate("Command_RECTANGLE", "Specify other corner or [{0}]: ").format(keyWords)

      englishKeyWords = "Area" + "/" + "Dimensions" + "/" + "Rotation"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter
      #                        msg, inputType,              default, keyWords, nessun controllo         
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)
         
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
      # RICHIESTA PRIMO PUNTO 
      if self.step == 0: # inizio del comando
         self.WaitForFirstCorner()         
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO DEL RETTANGOLO (da step = 0)
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.showMsg(QadMsg.translate("Command_RECTANGLE", "Window not correct."))
                  self.WaitForFirstCorner()
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Chamfer") or value == "Chamfer":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify first chamfer distance for rectangle <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue1))
               self.GetDistClass.dist = self.gapValue1
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 4
               self.GetDistClass.run(msgMapTool, msg)     
            elif value == QadMsg.translate("Command_RECTANGLE", "Fillet") or value == "Fillet":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify rectangle fillet radius <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue1))
               self.GetDistClass.dist = self.gapValue1
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 3
               self.GetDistClass.run(msgMapTool, msg)     
         elif type(value) == QgsPointXY:
            self.firstCorner = value
            self.getPointMapTool().firstCorner = self.firstCorner
            self.WaitForSecondCorner(currLayer)         

         return False # continua


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DEL RETTANGOLO (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.showMsg(QadMsg.translate("Command_RECTANGLE", "Window not correct."))
                  self.WaitForSecondCorner(currLayer)
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Area") or value == "Area":
               msg = QadMsg.translate("Command_RECTANGLE", "Enter rectangle area in current units <{0}>: ")
               # si appresta ad attendere un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(msg.format(str(self.area)), QadInputTypeEnum.FLOAT, \
                            self.area, "", \
                            QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER)
                  
               self.step = 6
            elif value == QadMsg.translate("Command_RECTANGLE", "Dimensions") or value == "Dimensions":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify length for rectangle <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.dim1))
               self.GetDistClass.dist = self.dim1
               self.step = 10
               self.GetDistClass.run(msgMapTool, msg)              
            elif value == QadMsg.translate("Command_RECTANGLE", "Rotation") or value == "Rotation":
               keyWords = QadMsg.translate("Command_RECTANGLE", "Points")
               self.defaultValue = self.rot
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify rotation angle or [{0}] <{1}>: ").format(keyWords, str(qad_utils.toDegrees(self.rot)))
               
               englishKeyWords = "Points"
               keyWords += "_" + englishKeyWords
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori non nulli
               self.waitFor(prompt, \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                            self.rot, keyWords)
               self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_ROTATION)
               
               self.step = 12
         elif type(value) == QgsPointXY:
            self.polyline.getRectByCorners(self.firstCorner, value, self.rot, \
                                           self.gapType, self.gapValue1, self.gapValue2)

            if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
               self.addRectangleToLayer(currLayer)
            return True       

         return False # continua

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA RAGGIO DI CURVATURA (da step = 1)
      elif self.step == 3:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.gapValue1 = self.GetDistClass.dist
               if self.gapValue1 == 0:
                  self.gapType = 0 # 0 = Angoli retti
               else:
                  self.gapType = 1 # 1 = Raccorda i segmenti

            self.WaitForFirstCorner()
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di distanza                     
         return False # fine comando

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMA DISTANZA DI CIMATURA (da step = 1)
      elif self.step == 4:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.gapValue1 = self.GetDistClass.dist
               
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specify second chamfer distance for rectangle <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue2))
               self.GetDistClass.dist = self.gapValue2
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 5
               self.GetDistClass.run(msgMapTool, msg)  
            else:   
               self.WaitForFirstCorner()
               self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di distanza                                 
         return False # fine comando
 
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDA DISTANZA DI CIMATURA (da step = 1)
      elif self.step == 5:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.gapValue2 = self.GetDistClass.dist               
               if self.gapValue1 == 0 or self.gapValue2 == 0:
                  self.gapType = 0 # 0 = Angoli retti
               else:
                  self.gapType = 2 # 2 = Cima i segmenti
                                   
            self.WaitForFirstCorner()
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di distanza                     
         return False # fine comando
 
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA AREA RETTANGOLO (da step = 2)
      elif self.step == 6: # dopo aver atteso un punto si riavvia il comando
         keyWords = QadMsg.translate("Command_RECTANGLE", "Length") + "/" + \
                    QadMsg.translate("Command_RECTANGLE", "Width")
         englishKeyWords = "Length" + "/" + "Width"
         
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.defaultValue = QadMsg.translate("Command_RECTANGLE", "Length")
                  prompt = QadMsg.translate("Command_RECTANGLE", "Calcolate the rectangle dimensions based on [{0}] <{1}>: ").format(keyWords, self.defaultValue)
                        
                  keyWords += "_" + englishKeyWords
                  # si appresta ad attendere una parola chiave         
                  # msg, inputType, default, keyWords, valori positivi
                  self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, \
                               self.defaultValue, \
                               keyWords, QadInputModeEnum.NONE)                  
                  
                  self.step = 7
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == float: # é stata inserita l'area
            self.area = value
            self.defaultValue = QadMsg.translate("Command_RECTANGLE", "Length")
            prompt = QadMsg.translate("Command_RECTANGLE", "Calcolate the rectangle dimensions based on [{0}] <{1}>: ").format(keyWords, self.defaultValue)
                  
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere una parola chiave         
            # msg, inputType, default, keyWords, valori positivi
            self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, \
                         self.defaultValue, \
                         keyWords, QadInputModeEnum.NONE)
            self.step = 7
         return False
            
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' (LUNGHEZZA / LARGHEZZA) DATA L'AREA (da step = 6)
      elif self.step == 7: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.defaultValue
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               return False
         else: # il punto arriva come parametro della funzione
            value = msg

         if value == QadMsg.translate("Command_RECTANGLE", "Length") or value == "Length":
            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Enter length for rectangle <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 8
            self.GetDistClass.run(msgMapTool, msg)              
         elif value == QadMsg.translate("Command_RECTANGLE", "Width") or value == "Width":
            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Enter width for rectangle <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 9
            self.GetDistClass.run(msgMapTool, msg)              
            
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA LUNGHEZZA RETTANGOLO DATA L'AREA (da step = 7)
      elif self.step == 8:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.polyline.getRectByAreaAndLength(self.firstCorner, self.area, self.GetDistClass.dist, \
                                                    self.rot, self.gapType, self.gapValue1, self.gapValue2)
               
               if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
                  self.addRectangleToLayer(currLayer)
               return True # fine comando
         return False
            
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA LARGHEZZA RETTANGOLO DATA L'AREA (da step = 7)
      elif self.step == 9:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.polyline.getRectByAreaAndWidth(self.firstCorner, self.area, self.GetDistClass.dist, \
                                                   self.rot, self.gapType, self.gapValue1, self.gapValue2)
               if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
                  self.addRectangleToLayer(currLayer)
               return True # fine comando		
         return False
            
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA LUNGHEZZA RETTANGOLO (da step = 2)
      elif self.step == 10:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.dim1 = self.GetDistClass.dist

            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Enter width for rectangle <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 11
            self.GetDistClass.run(msgMapTool, msg)              
                         
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA LARGHEZZA RETTANGOLO (da step = 10)
      elif self.step == 11:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.polyline.getRectByCornerAndDims(self.firstCorner, self.dim1, self.GetDistClass.dist, \
                                                    self.rot, self.gapType, self.gapValue1, self.gapValue2)
               if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
                  self.addRectangleToLayer(currLayer)
               return True # fine comando      
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE RETTANGOLO (da step = 2)
      elif self.step == 12: # dopo aver atteso un punto si riavvia il comando
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Points") or value == "Points":
               # si appresta ad attendere l'angolo di rotazione                      
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                  
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               self.GetAngleClass.msg = QadMsg.translate("Command_RECTANGLE", "Specify first point: ")
               self.GetAngleClass.angle = self.rot
               self.step = 13
               self.GetAngleClass.run(msgMapTool, msg)               
         elif type(value) == QgsPointXY:
            self.rot = qad_utils.getAngleBy2Pts(self.firstCorner, value)
            self.WaitForSecondCorner(currLayer)
         elif type(value) == float:
            self.rot = qad_utils.toRadians(value)
            self.WaitForSecondCorner(currLayer)
            
         return False # continua
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE RETTANGOLO (da step = 12)
      elif self.step == 13:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.rot = self.GetAngleClass.angle
               self.plugIn.setLastRot(self.rot)
               self.WaitForSecondCorner(currLayer)
               self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di rotazione                     
