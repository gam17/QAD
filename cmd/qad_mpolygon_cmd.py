# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando MPOLYGON per disegnare un poligono
 
                              -------------------
        begin                : 2013-09-18
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
from qgis.core import QgsWkbTypes
from qgis.PyQt.QtGui import QIcon


from .qad_generic_cmd import QadCommandClass
from .qad_pline_cmd import QadPLINECommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_multi_geom import *
from .. import qad_layer


# Classe che gestisce il comando MPOLYGON
class QadMPOLYGONCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadMPOLYGONCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "MPOLYGON")

   def getEnglishName(self):
      return "MPOLYGON"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runMPOLYGONCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/mpolygon.svg")

   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_MPOLYGON", "Draws a polygon by many methods.\nA Polygon is a closed sequence of straight line segments,\narcs or a combination of two.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare un poligono
      # che non verrà salvato su un layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      self.PLINECommand = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.PLINECommand is not None:
         del self.PLINECommand


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.PLINECommand is not None:
         return self.PLINECommand.getPointMapTool(drawMode)
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      if self.PLINECommand is not None:
         return self.PLINECommand.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PLINECommand is not None:
         self.PLINECommand.setRubberBandColor(rubberBandBorderColor, rubberBandFillColor)


   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PolygonGeometry)
         if currLayer is None:
            self.showErr(errMsg)
            return True # fine comando

      # =========================================================================
      # RICHIESTA PRIMO PUNTO PER SELEZIONE OGGETTI
      if self.step == 0:
         self.PLINECommand = QadPLINECommandClass(self.plugIn, True)
         self.PLINECommand.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
         # che non verrà salvata su un layer
         self.PLINECommand.virtualCmd = True   
         self.PLINECommand.asToolForMPolygon = True # per rubberband tipo poligono
         self.PLINECommand.run(msgMapTool, msg)
         self.step = 1
         return False # continua     

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO (da step = 0 o 1)
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         if self.PLINECommand.run(msgMapTool, msg) == True:
            if self.PLINECommand.polyline.qty() >= 2: # se ci sono almeno 2 tratti
               polyline = self.PLINECommand.polyline.copy() # copio la polylinea
               # se la polilinea non è chiusa
               if polyline.isClosed() == False:
                  polyline.append(QadLine().set(polyline.getEndPt(), polyline.getStartPt())) # la chiudo con un segmento retto
               if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer 
                  geom = polyline.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom), None, True, True, True) == False:                     
                        self.showMsg(QadMsg.translate("Command_MPOLYGON", "\nPolygon not valid.\n"))
                        del polyline                     
            else:
               self.showMsg(QadMsg.translate("Command_MPOLYGON", "\nPolygon not valid.\n"))
                                        
            return True # fine
            
         return False
