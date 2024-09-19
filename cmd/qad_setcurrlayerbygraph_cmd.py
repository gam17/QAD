# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando SETCURRLAYERBYGRAPH per settare il layer corrente tramite selezione grafica
 comando SETCURRUPDATEABLELAYERBYGRAPH per settare il layer corrente e porlo in modifica 
                                       tramite selezione grafica
 
                              ------------------
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


from qgis.PyQt.QtGui import QIcon


from .qad_generic_cmd import QadCommandClass
from ..qad_snapper import QadSnapTypeEnum
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_entsel_cmd import QadEntSelClass
from .qad_ssget_cmd import QadSSGetClass
from ..qad_msg import QadMsg


# Classe che gestisce il comando SETCURRLAYERBYGRAPH
class QadSETCURRLAYERBYGRAPHCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadSETCURRLAYERBYGRAPHCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "SETCURRLAYERBYGRAPH")

   def getEnglishName(self):
      return "SETCURRLAYERBYGRAPH"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSETCURRLAYERBYGRAPHCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/setcurrlayerbygraph.svg")
   
   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_SETCURRLAYERBYGRAPH", "Sets a layer of a graphical object as current.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         del self.entSelClass            


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0 or self.step == 1: # quando si é in fase di selezione entità
         return self.entSelClass.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 0 or self.step == 1: # quando si é in fase di selezione entità
         return self.entSelClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

   
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
         self.entSelClass = None
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_SETCURRLAYERBYGRAPH", "Select object whose layer will be the current layer: ")
      self.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)
      self.entSelClass.run(msgMapTool, msg)
        
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      if self.step == 0:     
         self.waitForEntsel(msgMapTool, msg)
         self.step = 1
         return False # continua
      
      elif self.step == 1:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               layer = self.entSelClass.entity.layer
               if self.plugIn.canvas.currentLayer() is None or \
                  self.plugIn.canvas.currentLayer() != layer:                              
                  self.plugIn.canvas.setCurrentLayer(layer)
                  self.plugIn.iface.setActiveLayer(layer) # lancia evento di deactivate e activate dei plugin
                  msg = QadMsg.translate("Command_SETCURRLAYERBYGRAPH", "\nThe current layer is {0}.")
                  self.showMsg(msg.format(layer.name()))
               del self.entSelClass
               self.entSelClass = None
               return True
            else:               
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continua
         

# Classe che gestisce il comando SETCURRUPDATEABLELAYERBYGRAPH
class QadSETCURRUPDATEABLELAYERBYGRAPHCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadSETCURRUPDATEABLELAYERBYGRAPHCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "SETCURRUPDATEABLELAYERBYGRAPH")

   def getEnglishName(self):
      return "SETCURRUPDATEABLELAYERBYGRAPH"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSETCURRUPDATEABLELAYERBYGRAPHCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/setcurrupdateablelayerbygraph.svg")
   
   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_SETCURRUPDATEABLELAYERBYGRAPH", "Sets the layers of a graphical objects as editable.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.SSGetClass = QadSSGetClass(plugIn)
      self.firstTime = True

   def __del__(self):
      QadCommandClass.__del__(self)
      del self.SSGetClass
        
   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 0: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.step == 0 or self.step == 1: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def run(self, msgMapTool = False, msg = None):     
      if self.step == 0: # inizio del comando   
         if self.firstTime == True:
            self.showMsg(QadMsg.translate("Command_SETCURRUPDATEABLELAYERBYGRAPH", "\nSelect objects whose layers will be the editable: "))
            self.firstTime = False
            
         if self.SSGetClass.run(msgMapTool, msg) == True:
            # selezione terminata
            self.step = 1
            return self.run(msgMapTool, msg)
         else:
            return False # continua

      elif self.step == 1: # dopo aver atteso la selezione di oggetti
         message = ""    
         for layerEntitySet in self.SSGetClass.entitySet.layerEntitySetList:
            layer = layerEntitySet.layer       
            if layer.isEditable() == False:
               if layer.startEditing() == True:
                  self.showMsg(QadMsg.translate("Command_SETCURRUPDATEABLELAYERBYGRAPH", "\nThe layer {0} is editable.").format(layer.name()))

         if len(self.SSGetClass.entitySet.layerEntitySetList) == 1:
            layer = self.SSGetClass.entitySet.layerEntitySetList[0].layer
            if self.plugIn.canvas.currentLayer() is None or \
               self.plugIn.canvas.currentLayer() != layer:               
               self.plugIn.canvas.setCurrentLayer(layer)
               self.plugIn.iface.setActiveLayer(layer) # lancia evento di deactivate e activate dei plugin
               self.showMsg(QadMsg.translate("Command_SETCURRUPDATEABLELAYERBYGRAPH", "\nThe current layer is {0}.").format(layer.name()))
         
         return True
