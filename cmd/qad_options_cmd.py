# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando OPTIONS per impostazione disegno
 
                              -------------------
        begin                : 2016-02-10
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


from ..qad_options_dlg import QadOPTIONSDialog
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg


# Classe che gestisce il comando OPTIONS
class QadOPTIONSCommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadOPTIONSCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "OPTIONS")

   def getEnglishName(self):
      return "OPTIONS"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runOPTIONSCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/options.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_OPTIONS", "QAD Options.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
            
   def run(self, msgMapTool = False, msg = None):
      Form = QadOPTIONSDialog(self.plugIn)
      Form.exec_()
      return True