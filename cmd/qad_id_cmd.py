# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando ID che restituisce la coordinata di un punto selezionato
 
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

from qgis.core import QgsPointXY
from qgis.PyQt.QtGui import QIcon

from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg


# Classe che gestisce il comando ID
class QadIDCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadIDCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "ID")

   def getEnglishName(self):
      return "ID"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runIDCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/id.png")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_ID", "Displays the coordinate values of a specified location.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
        
   def run(self, msgMapTool = False, msg = None):           
      if self.step == 0: # inizio del comando
         self.waitForPoint() # si appresta ad attendere un punto
         self.step = self.step + 1
         return False
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

            pt = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            pt = msg

         if type(pt) == QgsPointXY:
            self.plugIn.setLastPoint(pt)            
            self.showMsg("\n" + pt.toString())
         return True