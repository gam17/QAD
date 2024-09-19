# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando HELP che apre la guida di QAD
 
                              -------------------
        begin                : 2015-08-31
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
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QDir
import pathlib

from ..qad_utils import getMacAddress, getQADPath
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg, qadShowPluginPDFHelp, qadShowSupportersPage


# Classe che gestisce il comando HELP
class QadHELPCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadHELPCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "HELP")

   def getEnglishName(self):
      return "HELP"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runHELPCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/help.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_HELP", "The QAD manual will be showed.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
        
   def run(self, msgMapTool = False, msg = None):
      qadShowPluginPDFHelp()       
      return True


# Classe che gestisce il comando SUPPORTERS
class QadSUPPORTERSCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadSUPPORTERSCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "SUPPORTERS")

   def getEnglishName(self):
      return "SUPPORTERS"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSUPPORTERSCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/supporters.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_SUPPORTERS", "The QAD supporting members page will be showed.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
        
   def run(self, msgMapTool = False, msg = None):
      self.showMsg("\nYour mac address is " + getMacAddress() + ". QAD installation path is " + getQADPath())
      qadShowSupportersPage()       
      return True
