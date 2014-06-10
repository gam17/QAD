# -*- coding: latin1 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando RECTANGLE per disegnare un rettangolo
 
                              -------------------
        begin                : 2013-12-02
        copyright            : (C) 2013 IREN Acqua Gas SpA
        email                : geosim.dev@irenacquagas.it
        developers           : roberto poltini (roberto.poltini@irenacquagas.it)
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *


import qad_debug
from qad_rectangle_maptool import *
from qad_generic_cmd import QadCommandClass
from qad_msg import QadMsg
from qad_textwindow import *
import qad_utils
import qad_layer
from qad_getdist_cmd import QadGetDistClass
from qad_getangle_cmd import QadGetAngleClass


# Classe che gestisce il comando RECTANGLE
class QadRECTANGLECommandClass(QadCommandClass):
   
   def getName(self):
      return QadMsg.translate("Command_list", "RETTANGOLO")

   def connectQAction(self, action):
      QObject.connect(action, SIGNAL("triggered()"), self.plugIn.runRECTANGLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/rectangle.png")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_RECTANGLE", "Crea una polilinea rettangolare.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare un rettangolo
      # che non verr� salvato su un layer
      self.virtualCmd = False
      self.firstCorner = None
      self.gapType = 0 # 0 = Angoli retti; 1 = Raccorda i segmenti; 2 = Cima i segmenti
      self.gapValue1 = 0 # se gapType = 1 -> raggio di curvatura; se gapType = 2 -> prima distanza di cimatura
      self.gapValue2 = 0 # se gapType = 2 -> seconda distanza di cimatura
      self.area = 100
      self.dim1 = 10
      self.rot = 0
      self.vertices = []
      
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
      # quando si � in fase di richiesta distanza
      if self.step == 3 or self.step == 4 or self.step == 5 or \
         self.step == 8 or self.step == 9 or self.step == 10 or self.step == 11:
         return self.GetDistClass.getPointMapTool()
      # quando si � in fase di richiesta rotazione
      elif self.step == 13:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_rectangle_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None       

      
   def addRectangleToLayer(self, layer):
      if layer.geometryType() == QGis.Line:
         qad_layer.addLineToLayer(self.plugIn, layer, self.vertices)
      elif layer.geometryType() == QGis.Polygon:                          
         qad_layer.addPolygonToLayer(self.plugIn, layer, self.vertices)
      
         
   #============================================================================
   # WaitForFirstCorner
   #============================================================================
   def WaitForFirstCorner(self):
      self.step = 1         
      self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER)
      
      keyWords = QadMsg.translate("Command_RECTANGLE", "Cima") + " " + \
                 QadMsg.translate("Command_RECTANGLE", "Raccordo")
     
      # si appresta ad attendere un punto o enter
      #                        msg, inputType,              default, keyWords, nessun controllo         
      self.waitFor(QadMsg.translate("Command_RECTANGLE", "Specificare primo angolo o [Cima/Raccordo]: "), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)
         
   #============================================================================
   # WaitForSecondCorner
   #============================================================================
   def WaitForSecondCorner(self, layer):
      self.step = 2
      self.getPointMapTool().rot = self.rot
      self.getPointMapTool().gapType = self.gapType
      self.getPointMapTool().gapValue1 = self.gapValue1
      self.getPointMapTool().gapValue2 = self.gapValue2
      self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.FIRST_CORNER_KNOWN_ASK_FOR_SECOND_CORNER)
      if layer is not None:
         self.getPointMapTool().geomType = layer.geometryType()
      
      keyWords = QadMsg.translate("Command_RECTANGLE", "Area") + " " + \
                 QadMsg.translate("Command_RECTANGLE", "Quote") + " " + \
                 QadMsg.translate("Command_RECTANGLE", "Rotazione")
     
      # si appresta ad attendere un punto o enter
      #                        msg, inputType,              default, keyWords, nessun controllo         
      self.waitFor(QadMsg.translate("Command_RECTANGLE", "Specificare angolo opposto o [Area/Quote/Rotazione]: "), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, keyWords, QadInputModeEnum.NONE)
         
   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapRenderer().destinationCrs().geographicFlag():
         self.showMsg(QadMsg.translate("QAD", "\nIl sistema di riferimento del progetto deve essere un sistema di coordinate proiettate.\n"))
         return True # fine comando

      currLayer = None
      if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
         # il layer corrente deve essere editabile e di tipo linea o poligono
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QGis.Line, QGis.Polygon])
         if currLayer is None:
            self.showMsg(errMsg)
            return True # fine comando
      
      #=========================================================================
      # RICHIESTA PRIMO PUNTO 
      if self.step == 0: # inizio del comando
         self.WaitForFirstCorner()         
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO DEL RETTANGOLO (da step = 0)
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # � stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool � stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.showMsg(QadMsg.translate("Command_RECTANGLE", "La finestra non � stata specificata correttamente."))
                  self.WaitForFirstCorner()
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Cima"):
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specificare prima distanza di cimatura del rettangolo <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue1))
               self.GetDistClass.dist = self.gapValue1
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 4
               self.GetDistClass.run(msgMapTool, msg)     
            elif value == QadMsg.translate("Command_RECTANGLE", "Raccordo"):
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specificare raggio di raccordo del rettangolo <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue1))
               self.GetDistClass.dist = self.gapValue1
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 3
               self.GetDistClass.run(msgMapTool, msg)     
         elif type(value) == QgsPoint:
            self.firstCorner = value
            self.getPointMapTool().firstCorner = self.firstCorner
            self.WaitForSecondCorner(currLayer)         

         return False # continua


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DEL RETTANGOLO (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # � stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool � stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.showMsg(QadMsg.translate("Command_RECTANGLE", "La finestra non � stata specificata correttamente."))
                  self.WaitForSecondCorner(currLayer)
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_RECTANGLE", "Area"):
               msg = QadMsg.translate("Command_RECTANGLE", "Digitare l'area del rettangolo in unit� correnti <{0}>: ")
               # si appresta ad attendere un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(msg.format(str(self.area)), QadInputTypeEnum.FLOAT, \
                            self.area, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER)
                  
               self.step = 6
            elif value == QadMsg.translate("Command_RECTANGLE", "Quote"):
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specificare lunghezza del rettangolo <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.dim1))
               self.GetDistClass.dist = self.dim1
               self.step = 10
               self.GetDistClass.run(msgMapTool, msg)              
            elif value == QadMsg.translate("Command_RECTANGLE", "Rotazione"):
               keyWords = QadMsg.translate("Command_RECTANGLE", "SCegli")
               self.defaultValue = self.rot
               msg = QadMsg.translate("Command_RECTANGLE", "Specificare l'angolo di rotazione o [SCegli punti] <{0}>: ")
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori non nulli
               self.waitFor(msg.format(str(qad_utils.toDegrees(self.rot))), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT | QadInputTypeEnum.KEYWORDS, \
                            self.rot, keyWords, \
                            QadInputModeEnum.NOT_NULL)
               self.getPointMapTool().setMode(Qad_rectangle_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_CORNER)
               
               self.step = 12
         elif type(value) == QgsPoint:
            self.vertices.extend(qad_utils.getRectByCorners(self.firstCorner, value, self.rot, \
                                                            self.gapType, self.gapValue1, self.gapValue2))

            if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
               self.addRectangleToLayer(currLayer)
            return True       

         return False # continua

      #=========================================================================
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
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che pu� essere variato dal maptool di distanza                     
         return False # fine comando

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMA DISTANZA DI CIMATURA (da step = 1)
      elif self.step == 4:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.gapValue1 = self.GetDistClass.dist
               
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_RECTANGLE", "Specificare seconda distanza di cimatura del rettangolo <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.gapValue2))
               self.GetDistClass.dist = self.gapValue2
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 5
               self.GetDistClass.run(msgMapTool, msg)  
            else:   
               self.WaitForFirstCorner()
               self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che pu� essere variato dal maptool di distanza                                 
         return False # fine comando
 
      #=========================================================================
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
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che pu� essere variato dal maptool di distanza                     
         return False # fine comando
 
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA AREA RETTANGOLO (da step = 2)
      elif self.step == 6: # dopo aver atteso un punto si riavvia il comando
         #qad_debug.breakPoint()
         keyWords = QadMsg.translate("Command_RECTANGLE", "Lunghezza") + " " + \
                    QadMsg.translate("Command_RECTANGLE", "lArghezza")
         prompt = QadMsg.translate("Command_RECTANGLE", "Calcolare le quote rettangolo in base alla [Lunghezza/lArghezza] <Lunghezza>: ")
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # � stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool � stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.defaultValue = QadMsg.translate("Command_RECTANGLE", "Lunghezza")      
                  # si appresta ad attendere una parola chiave         
                  # msg, inputType, default, keyWords, valori positivi
                  self.waitFor(msg, QadInputTypeEnum.KEYWORDS, \
                               QadMsg.translate("Command_RECTANGLE", "Lunghezza"), \
                               keyWords, QadInputModeEnum.NONE)                  
                  
                  self.step = 7
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == float: # � stata inserita l'area
            self.area = value
            self.defaultValue = QadMsg.translate("Command_RECTANGLE", "Lunghezza")      
            # si appresta ad attendere una parola chiave         
            # msg, inputType, default, keyWords, valori positivi
            self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, \
                         self.defaultValue, \
                         keyWords, QadInputModeEnum.NONE)
            self.step = 7
         return False
            
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' (LUNGHEZZA / LARGHEZZA) DATA L'AREA (da step = 6)
      elif self.step == 7: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # � stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool � stato attivato senza un punto
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

         if value == QadMsg.translate("Command_RECTANGLE", "Lunghezza"):
            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Digitare la lunghezza rettangolo <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 8
            self.GetDistClass.run(msgMapTool, msg)              
         elif value == QadMsg.translate("Command_RECTANGLE", "lArghezza"):
            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Digitare la larghezza rettangolo <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 9
            self.GetDistClass.run(msgMapTool, msg)              
            
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA LUNGHEZZA RETTANGOLO DATA L'AREA (da step = 7)
      elif self.step == 8:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
					self.vertices.extend(qad_utils.getRectByAreaAndLength(self.firstCorner, self.area, self.GetDistClass.dist, \
																							self.rot, self.gapType, self.gapValue1, self.gapValue2))	
					if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
						self.addRectangleToLayer(currLayer)
					return True # fine comando		
         return False
            
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA LARGHEZZA RETTANGOLO DATA L'AREA (da step = 7)
      elif self.step == 9:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
					self.vertices.extend(qad_utils.getRectByAreaAndWidth(self.firstCorner, self.area, self.GetDistClass.dist, \
																							self.rot, self.gapType, self.gapValue1, self.gapValue2))	
					if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
						self.addRectangleToLayer(currLayer)
					return True # fine comando		
         return False
            
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA LUNGHEZZA RETTANGOLO (da step = 2)
      elif self.step == 10:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.dim1 = self.GetDistClass.dist

            if self.GetDistClass is not None:
               del self.GetDistClass
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_RECTANGLE", "Digitare la larghezza rettangolo <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.dim1))
            self.GetDistClass.dist = self.dim1
            self.step = 11
            self.GetDistClass.run(msgMapTool, msg)              
                         
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA LARGHEZZA RETTANGOLO (da step = 10)
      elif self.step == 11:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.vertices.extend(qad_utils.getRectByCornerAndDims(self.firstCorner, self.dim1, self.GetDistClass.dist, \
                                                                     self.rot, self.gapType, self.gapValue1, self.gapValue2))   
               if self.virtualCmd == False: # se si vuole veramente salvare i buffer in un layer
                  self.addRectangleToLayer(currLayer)
               return True # fine comando      
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE RETTANGOLO (da step = 2)
      elif self.step == 12: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # � stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool � stato attivato senza un punto
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
            if value == QadMsg.translate("Command_RECTANGLE", "SCegli"):
               # si appresta ad attendere l'angolo di rotazione                      
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                  
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               self.GetAngleClass.msg = QadMsg.translate("Command_RECTANGLE", "Specificare primo punto: ")
               self.GetAngleClass.angle = self.rot
               self.step = 13
               self.GetAngleClass.run(msgMapTool, msg)               
         elif type(value) == QgsPoint:
            self.rot = qad_utils.getAngleBy2Pts(self.firstCorner, value)
            self.WaitForSecondCorner(currLayer)
         elif type(value) == float:
            self.rot = qad_utils.toRadians(value)
            self.WaitForSecondCorner(currLayer)
            
         return False # continua
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE RETTANGOLO (da step = 12)
      elif self.step == 13:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.rot = self.GetAngleClass.angle
               self.plugIn.setLastRot(self.rot)
               self.WaitForSecondCorner(currLayer)
               self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che pu� essere variato dal maptool di rotazione                     