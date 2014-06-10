# -*- coding: latin1 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando da inserire in altri comandi per la richiesta di un angolo
 
                              -------------------
        begin                : 2013-12-04
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
from qad_generic_cmd import QadCommandClass
from qad_msg import QadMsg
from qad_textwindow import *
from qad_entity import *
from qad_getpoint import *
import qad_utils


#===============================================================================
# QadGetAngleClass
#===============================================================================
class QadGetAngleClass(QadCommandClass):
      
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entity = QadEntity()
      self.startPt = None            
      self.msg = QadMsg.translate("QAD", "Specificare angolo: ")
      self.angle = None # in radianti
            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapRenderer().destinationCrs().geographicFlag():
         self.showMsg(QadMsg.translate("QAD", "\nIl sistema di riferimento del progetto deve essere un sistema di coordinate proiettate.\n"))
         return True # fine comando

      #=========================================================================
      # RICHIESTA PUNTO o ENTITA'
      if self.step == 0: # inizio del comando
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori non nulli
         self.waitFor(self.msg, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      self.angle, "", \
                      QadInputModeEnum.NOT_NULL)
         
         if self.startPt is not None:            
            # imposto il map tool
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
            self.getPointMapTool().setStartPoint(self.startPt)
                           
         self.step = 1
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO O NUMERO REALE
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         #qad_debug.breakPoint()
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # � stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool � stato attivato senza un punto
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
         elif type(value) == QgsPoint:
            if self.startPt is not None:
               self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
               return True # fine comando
            else:            
               self.startPt = value            
               # imposto il map tool
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.startPt)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("QAD", "Specificare secondo punto: "))
               self.step = 2

         return False
         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO DELLA ANGOLO (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # � stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool � stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if qad_utils.ptNear(self.startPt, value):
            self.showMsg(QadMsg.translate("QAD", "\nI punti devono essere distinti."))
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("QAD", "Specificare secondo punto: "))
            return False
         else:
            self.angle = qad_utils.getAngleBy2Pts(self.startPt, value)
            return True # fine comando