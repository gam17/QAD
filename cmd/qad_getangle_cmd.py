# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando da inserire in altri comandi per la richiesta di un angolo
 
                              -------------------
        begin                : 2013-12-04
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
from qgis.core import QgsPointXY


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntity
from ..qad_getpoint import QadGetPointDrawModeEnum
from .. import qad_utils


# ===============================================================================
# QadGetAngleClass
# ===============================================================================
class QadGetAngleClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadGetAngleClass(self.plugIn)
      
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.startPt = None            
      self.msg = QadMsg.translate("QAD", "Specify angle: ")
      self.angle = None # in radianti
      # memorizzo last point perchè il/i punto/i indicato/i da questa questa funzione non devono
      # alterare lastpoint 
      self.__prevLastPoint = self.plugIn.lastPoint
            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      # =========================================================================
      # RICHIESTA PUNTO o ENTITA'
      if self.step == 0: # inizio del comando
         if self.startPt is not None:
            # imposto il map tool
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
            self.getPointMapTool().setStartPoint(self.startPt)

         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori non nulli
         self.waitFor(self.msg, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      self.angle, "", \
                      QadInputModeEnum.NOT_NULL)

         self.step = 1
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO O NUMERO REALE
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
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
         else: # il punto o il numero reale arriva come parametro della funzione
            value = msg

         if value is None:
            return True # fine comando
         
         if type(value) == float:
            self.angle = qad_utils.toRadians(value)
            return True # fine comando
         elif type(value) == QgsPointXY:
            # il/i punto/i indicato/i da questa questa funzione non devono alterare lastpoint 
            self.plugIn.setLastPoint(self.__prevLastPoint)
            
            if self.startPt is not None:
               self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
               return True # fine comando
            else:            
               self.startPt = value            
               # imposto il map tool
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.startPt)
               prompt = QadMsg.translate("QAD", "Specify second point: ")
               # si appresta ad attendere un punto
               self.waitForPoint(prompt)
               self.step = 2

         return False
         
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO DELLA ANGOLO (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto si riavvia il comando
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

         # il/i punto/i indicato/i da questa questa funzione non devono alterare lastpoint 
         self.plugIn.setLastPoint(self.__prevLastPoint)
         
         if qad_utils.ptNear(self.startPt, value):
            self.showMsg(QadMsg.translate("QAD", "\nThe points must be different."))
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("QAD", "Specify second point: "))
            return False
         else:
            self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
            return True # fine comando