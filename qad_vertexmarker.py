# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire i simboli marcatori
 
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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *


from .qad_msg import QadMsg
from .qad_variables import QadVariables


# ===============================================================================
# QadVertexmarkerIconTypeEnum class.
# ===============================================================================
class QadVertexmarkerIconTypeEnum():
   NONE             = 0  # nessuno
   CROSS            = 1  # croce
   X                = 2  # una X 
   BOX              = 3  # un quadrato
   TRIANGLE         = 4  # triangolo equilatero con punta in su
   CIRCLE           = 5  # cerchio
   CIRCLE_X         = 6  # cerchio con al centro una x
   RHOMBUS          = 7  # rombo
   INFINITY_LINE    = 8  # linea infinita (------ . .)
   DOUBLE_BOX       = 9  # due quadrati sfalsati
   PERP             = 10 # simbolo di "perpendicolare"
   TANGENT          = 11 # un cerchio con una retta tangente sopra
   DOUBLE_TRIANGLE  = 12 # due triangoli uno sull'altro con vertice al centro (clessidra)
   BOX_X            = 13 # quadrato con al centro una x
   PARALLEL         = 14 # due righe parallele a 45 gradi
   PROGRESS         = 15 # linea con X e i puntini (----X-- . .)
   X_INFINITY_LINE  = 16 # X e i puntini (X-- . .)
   PERP_DEFERRED    = 17 # come perpendicolare con i puntini 
   TANGENT_DEFERRED = 18 # come tangente con i puntini 


class QadVertexMarker(QgsMapCanvasItem):
   """
   Classe che gestisce i marcatori dei vertici
   """
      

   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, mapCanvas):
      QgsMapCanvasItem.__init__(self, mapCanvas)
      self.__canvas = mapCanvas
      self.__iconType = QadVertexmarkerIconTypeEnum.X # icon to be shown
      self.__iconSize = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPSIZE"))
      self.__center = QgsPointXY(0, 0) #  coordinates of the point in the center
      self.__color = QColor(255, 0, 0) # color of the marker
      self.__penWidth = 2 # pen width

      
   def __del__(self):     
      self.removeItem()


   def removeItem(self):     
      self.__canvas.scene().removeItem(self)
      

   def setCenter(self, point):
      self.__center = point
      pt = self.toCanvasCoordinates(self.__center)
      self.setPos(pt)


   def setIconType(self, iconType):
      self.__iconType = iconType


   def setIconSize(self, iconSize):
      self.__iconSize = iconSize


   def setColor(self, color):
      self.__color = color


   def setPenWidth(self, width):
      self.__penWidth = width

      
   def paint(self, painter, option, widget):
      """
      p é un QPainter
      """

      s = self.__iconSize

      pen = QPen(self.__color)
      pen.setWidth(self.__penWidth)
      painter.setPen(pen)

      if self.__iconType == QadVertexmarkerIconTypeEnum.NONE:
         pass
      elif self.__iconType == QadVertexmarkerIconTypeEnum.CROSS:
         # croce
         painter.drawLine(QLineF(-s,  0,  s,  0))
         painter.drawLine(QLineF( 0, -s,  0,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.X:
         # una X 
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF(-s,  s,  s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.BOX:
         # un quadrato
         painter.drawLine(QLineF(-s, -s,  s, -s))
         painter.drawLine(QLineF( s, -s,  s,  s))
         painter.drawLine(QLineF( s,  s, -s,  s))
         painter.drawLine(QLineF(-s,  s, -s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.TRIANGLE:
         # triangolo equilatero con punta in su
         painter.drawLine(QLineF(-s,  s,  s,  s))
         painter.drawLine(QLineF( s,  s,  0, -s))
         painter.drawLine(QLineF( 0, -s, -s,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.CIRCLE:
         # cerchio
         # la linea é più sottile
         pen.setWidth(int(self.__penWidth / 2))      
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), s, s)
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.CIRCLE_X:
         # cerchio con al centro una x
         # la linea é più sottile
         pen.setWidth(int(self.__penWidth / 2))     
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), s, s)
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF(-s,  s,  s, -s))        
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.RHOMBUS:
         # rombo
         painter.drawLine(QLineF( 0, -s, -s,  0))
         painter.drawLine(QLineF(-s,  0,  0,  s))
         painter.drawLine(QLineF( 0,  s,  s,  0))
         painter.drawLine(QLineF( s,  0,  0, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.INFINITY_LINE:
         # linea infinita (------ . .)
         l = self.__penWidth
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF(2 * l,  0,  2 * l,  0))
         painter.drawLine(QLineF(4 * l,  0,  4 * l,  0))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.DOUBLE_BOX:
         # due quadrati sfalsati
         l = (s / 4)
         painter.drawLine(QLineF(-s, -s, -s,  l))
         painter.drawLine(QLineF(-s,  l, -l,  l))
         painter.drawLine(QLineF(-l,  l, -l,  s))
         painter.drawLine(QLineF(-l,  s,  s,  s))
         painter.drawLine(QLineF( s,  s,  s, -l))
         painter.drawLine(QLineF( s, -l,  l, -l))
         painter.drawLine(QLineF( l, -l,  l, -s))
         painter.drawLine(QLineF( l, -s, -s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PERP:
         # simbolo di "perpendicolare"
         painter.drawLine(QLineF(-s, -s, -s,  s))
         painter.drawLine(QLineF(-s,  s,  s,  s))
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF( 0,  0,  0,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.TANGENT:
         # un cerchio con una retta tangente sopra
         # la linea é più sottile
         l = s - self.__penWidth
         pen.setWidth(int(self.__penWidth / 2))  
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), l + 1, l + 1)
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s, -s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.DOUBLE_TRIANGLE:
         # due triangoli uno sull'altro con vertice al centro (clessidra)
         # le linee oblique sono più sottili
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF( s, -s, -s,  s))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s, -s))
         painter.drawLine(QLineF(-s,  s,  s,  s))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.BOX_X:
         # quadrato con al centro una x
         painter.drawLine(QLineF(-s, -s,  s, -s))
         painter.drawLine(QLineF( s, -s,  s,  s))
         painter.drawLine(QLineF( s,  s, -s,  s))
         painter.drawLine(QLineF(-s,  s, -s, -s))
         # le linee oblique della x sono più sottili
         pen.setWidth(int(self.__penWidth / 2))
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s,  s))
         painter.drawLine(QLineF(-s,  s,  s, -s))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PARALLEL:
         # due righe parallele a 45 gradi
         painter.drawLine(QLineF(-s,  0,  0, -s))
         painter.drawLine(QLineF( 0,  s,  s,  0))
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PROGRESS:
         # linea con X e i puntini (----X-- . .)
         l = self.__penWidth
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF(2 * l,  0,  2 * l,  0))
         painter.drawLine(QLineF(4 * l,  0,  4 * l,  0))
         # le linee oblique della x sono più sottili
         pen.setWidth(int(self.__penWidth / 2))
         l = s / 2
         painter.setPen(pen)
         painter.drawLine(QLineF(-l, -l,  l,  l))
         painter.drawLine(QLineF(-l,  l,  l, -l))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.X_INFINITY_LINE:
         # linea con X e i puntini (X-- . .)
         l = self.__penWidth
         painter.drawLine(QLineF(2 * l,  0,  2 * l,  0))
         painter.drawLine(QLineF(4 * l,  0,  4 * l,  0))
         # le linee oblique della x sono più sottili
         pen.setWidth(int(self.__penWidth / 2))
         l = s / 2
         painter.setPen(pen)
         painter.drawLine(QLineF(-l, -l,  l,  l))
         painter.drawLine(QLineF(-l,  l,  l, -l))
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
      elif self.__iconType == QadVertexmarkerIconTypeEnum.PERP_DEFERRED:
         painter.drawLine(QLineF(-s, -s, -s,  s))
         painter.drawLine(QLineF(-s,  s,  s,  s))
         painter.drawLine(QLineF(-s,  0,  0,  0))
         painter.drawLine(QLineF( 0,  0,  0,  s))
         # simbolo di "perpendicolare" con i puntini
         l = s - self.__penWidth
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))         
      elif self.__iconType == QadVertexmarkerIconTypeEnum.TANGENT_DEFERRED:
         # un cerchio con una retta tangente sopra
         # la linea é più sottile
         l = s - self.__penWidth
         pen.setWidth(int(self.__penWidth / 2))     
         painter.setPen(pen)
         painter.drawEllipse(QPointF(0, 0), l + 1, l + 1)
         pen.setWidth(self.__penWidth)
         painter.setPen(pen)
         painter.drawLine(QLineF(-s, -s,  s, -s))
         # come tangente con i puntini
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))
         l = l + (self.__penWidth * 2)
         painter.drawLine(QLineF(l,  0,  l,  0))         
         

   def boundingRect(self):
      a = self.__iconSize / 2.0 + 1
      width = 2 * a + self.__penWidth * 2
      height = 2 * a
      return QRectF(-a, -a, width, height)


   def updatePosition(self):
      self.setCenter(self.__center)
