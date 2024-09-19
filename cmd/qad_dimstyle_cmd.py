# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando DSETTINGS per impostazione stili di quotatura
 
                              -------------------
        begin                : 2015-05-19
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
from qgis.PyQt.QtGui  import *
from qgis.core import *


from ..qad_dimstyle_dlg import QadDIMSTYLEDialog


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg


# Classe che gestisce il comando DIMSTYLE
class QadDIMSTYLECommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadDIMSTYLECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMSTYLE")

   def getEnglishName(self):
      return "DIMSTYLE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMSTYLECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimStyle.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_DIMSTYLE", "Creates new styles, sets the current style, modifies styles, sets overrides on the current style, and compares styles.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
            
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      Form = QadDIMSTYLEDialog(self.plugIn)
      Form.exec_()
      return True