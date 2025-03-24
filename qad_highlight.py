# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Classe per gestire l'evidenziazione delle geometrie
 
                              -------------------
        begin                : 2015-12-12
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
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *


# ===============================================================================
# getQGISColorForHighlight
# ===============================================================================
def getQGISColorForHighlight():
   """
   La funzione legge il colore impostato da QGIS per il rubber band di tipo <geometryType>.
   Se <alternativeBand> = True, il rubber band sarà impostato con più trasparenza
   """
   settings = QSettings()
   color = QColor(int(settings.value( "/qgis/digitizing/line_color_red", 1)), \
                  int(settings.value( "/qgis/digitizing/line_color_green", 1)), \
                  int(settings.value( "/qgis/digitizing/line_color_blue", 1)))
   alpha = float(int(settings.value( "/qgis/digitizing/line_color_alpha", 200)) / 255.0)

   color.setAlphaF(alpha)
   return color


# ===============================================================================
# createHighlight
# ===============================================================================
def createHighlight(mapCanvas, geometry_feature, layer, borderColor = None, fillColor = None):
   """
   la funzione crea un rubber band di tipo <geometryType> con le impostazioni di QGIS.
   Se <alternativeBand> = True, il rubber band sarà impostato con più trasparenza e tipolinea punteggiato   
   """
   settings = QSettings()
   width = int(settings.value( "/qgis/digitizing/line_width", 1))

   hl = QgsHighlight(mapCanvas, geometry_feature, layer)
   
   if borderColor is None:
      borderColor = getQGISColorForHighlight()
   hl.setColor(borderColor)

   if fillColor is None:
      hl.setFillColor(borderColor)
   else:
      hl.setFillColor(fillColor)
   
   return hl


# Classe che gestisce l'evidenziazione delle geometrie
class QadHighlight():
   def __init__(self, mapCanvas, borderColor = None, fillColor = None):
      self.mapCanvas = mapCanvas
      self.__highlight = []

   def __del__(self):
      self.reset()
      
      for highlight in self.__highlight:
         self.mapCanvas.scene().removeItem(highlight)

      del self.__highlight[:]
   
   def hide(self):
      for highlight in self.__highlight:
         highlight.hide()

   def show(self):
      for highlight in self.__highlight:
         highlight.show()
      
   def addGeometry(self, geom, layer, borderColor = None, fillColor = None):
      highlight = createHighlight(self.mapCanvas, geom, layer, borderColor, fillColor)
      highlight.show()
      self.__highlight.append(highlight)

   def addGeometries(self, geoms, layer, borderColor = None, fillColor = None):
      for g in geoms:
         self.addGeometry(g, layer, borderColor, fillColor)         
         
   def reset(self):
      self.hide()
      for highlight in self.__highlight:
         self.mapCanvas.scene().removeItem(highlight)
      del self.__highlight[:]
