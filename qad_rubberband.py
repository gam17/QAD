# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Classe per gestire rubber band di oggetti geometricamente non omogenei
 
                              -------------------
        begin                : 2013-12-12
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
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import *
from qgis.gui import *


from .qad_variables import QadVariables
from .qad_msg import QadMsg


# ===============================================================================
# QadCursorTypeEnum class.
# ===============================================================================
class QadCursorTypeEnum():
   NONE     = 0   # nessun cursore
   BOX      = 1   # un quadratino usato per selezionare entità
   CROSS    = 2   # una croce usata per selezionare un punto
   APERTURE = 4   # un quadratino usato per selezionare i punti di snap


# ===============================================================================
# createCursorRubberBand
# ===============================================================================
# Classe che gestisce rubber band per disegnare il cursore a croce e il quadratino di pickbox
class QadCursorRubberBand():
   def __init__(self, mapCanvas, cursorType):
      self.mapCanvas = mapCanvas
      self.cursorType = cursorType
      
      if cursorType & QadCursorTypeEnum.BOX:
         self.__boxRubberBand = QgsRubberBand(mapCanvas, QgsWkbTypes.LineGeometry)
         self.__boxRubberBand.setColor(QColor(QadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR"))))
         self.__pickSize = QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX"))
      else:
         self.__boxRubberBand = None
     
      if cursorType & QadCursorTypeEnum.CROSS:
         csrColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CURSORCOLOR")))
         csrSize = QadVariables.get(QadMsg.translate("Environment variables", "CURSORSIZE"))
         self.__crosshairRubberBandSx = QgsRubberBand(mapCanvas, QgsWkbTypes.LineGeometry)
         self.__crosshairRubberBandSx.setColor(csrColor)
         self.__crosshairRubberBandDx = QgsRubberBand(mapCanvas, QgsWkbTypes.LineGeometry)
         self.__crosshairRubberBandDx.setColor(csrColor)
         self.__crosshairRubberBandDw = QgsRubberBand(mapCanvas, QgsWkbTypes.LineGeometry)
         self.__crosshairRubberBandDw.setColor(csrColor)
         self.__crosshairRubberBandUp = QgsRubberBand(mapCanvas, QgsWkbTypes.LineGeometry)
         self.__crosshairRubberBandUp.setColor(csrColor)
         screenRect = QApplication.desktop().screenGeometry(mapCanvas)
         self.__halfScreenSize = max(screenRect.height(), screenRect.width())
         if csrSize < 100:
            self.__halfScreenSize = self.__halfScreenSize / 2
         self.__halfScreenSize = self.__halfScreenSize * QadVariables.get(QadMsg.translate("Environment variables", "CURSORSIZE")) / 100
      else:
         self.__crosshairRubberBandSx = None
         self.__crosshairRubberBandDx = None
         self.__crosshairRubberBandDw = None
         self.__crosshairRubberBandUp = None

      if cursorType & QadCursorTypeEnum.APERTURE:
         self.__apertureRubberBand = QgsRubberBand(mapCanvas, QgsWkbTypes.LineGeometry)
         self.__apertureRubberBand.setColor(QColor(QadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR"))))
         self.__apertureRubberBand.setLineStyle(Qt.DotLine)
         self.__apertureSize = QadVariables.get(QadMsg.translate("Environment variables", "APERTURE"))
      else:
         self.__apertureRubberBand = None

   def __del__(self):
      self.removeItems()
      
   def removeItems(self):      
      if self.__boxRubberBand is not None:
         self.mapCanvas.scene().removeItem(self.__boxRubberBand)
         del self.__boxRubberBand
         self.__boxRubberBand = None
         
      if self.__crosshairRubberBandSx is not None:
         self.mapCanvas.scene().removeItem(self.__crosshairRubberBandSx)
         self.mapCanvas.scene().removeItem(self.__crosshairRubberBandDx)
         self.mapCanvas.scene().removeItem(self.__crosshairRubberBandDw)
         self.mapCanvas.scene().removeItem(self.__crosshairRubberBandUp)
         del self.__crosshairRubberBandSx
         self.__crosshairRubberBandSx = None
         del self.__crosshairRubberBandDx
         self.__crosshairRubberBandDx = None
         del self.__crosshairRubberBandDw
         self.__crosshairRubberBandDw = None
         del self.__crosshairRubberBandUp
         self.__crosshairRubberBandUp = None

      if self.__apertureRubberBand is not None:
         self.mapCanvas.scene().removeItem(self.__apertureRubberBand)
         del self.__apertureRubberBand
         self.__apertureRubberBand = None


   def moveEvent(self, point):
      # point è risultato di toMapCoordinates      
      if self.cursorType & QadCursorTypeEnum.BOX:
         pickSize = self.__pickSize * self.mapCanvas.mapUnitsPerPixel()

         self.__boxRubberBand.reset(QgsWkbTypes.LineGeometry)
         
         point1 = QgsPointXY(point.x() - pickSize, point.y() - pickSize)
         dblPickSize = pickSize * 2
         self.__boxRubberBand.addPoint(point1, False)
         point1.setX(point1.x() + dblPickSize)
         self.__boxRubberBand.addPoint(point1, False)
         point1.setY(point1.y() + dblPickSize)
         self.__boxRubberBand.addPoint(point1, False)
         point1.setX(point1.x() - dblPickSize)
         self.__boxRubberBand.addPoint(point1, False)
         point1.setY(point1.y() - dblPickSize)
         self.__boxRubberBand.addPoint(point1, True)

      if self.cursorType & QadCursorTypeEnum.CROSS:
         halfScreenSize = self.__halfScreenSize * self.mapCanvas.mapUnitsPerPixel()
         
         self.__crosshairRubberBandSx.reset(QgsWkbTypes.LineGeometry)
         self.__crosshairRubberBandDx.reset(QgsWkbTypes.LineGeometry)
         self.__crosshairRubberBandDw.reset(QgsWkbTypes.LineGeometry)
         self.__crosshairRubberBandUp.reset(QgsWkbTypes.LineGeometry)
         
         if self.cursorType & QadCursorTypeEnum.BOX:
            point1 = QgsPointXY(point.x() - halfScreenSize, point.y())
            point2 = QgsPointXY(point.x() - pickSize, point.y())
            self.__crosshairRubberBandSx.addPoint(point1, False)
            self.__crosshairRubberBandSx.addPoint(point2, True)

            point1.setX(point.x() + halfScreenSize)
            point2.setX(point.x() + pickSize)
            self.__crosshairRubberBandDx.addPoint(point1, False)
            self.__crosshairRubberBandDx.addPoint(point2, True)
            
            point1.set(point.x(), point.y() - halfScreenSize)
            point2.set(point.x(), point.y() - pickSize)
            self.__crosshairRubberBandDw.addPoint(point1, False)
            self.__crosshairRubberBandDw.addPoint(point2, True)
            
            point1.setY(point.y() + halfScreenSize)
            point2.setY(point.y() + pickSize)           
            self.__crosshairRubberBandUp.addPoint(point1, False)
            self.__crosshairRubberBandUp.addPoint(point2, True)            
         else:
            point1 = QgsPointXY(point.x() - halfScreenSize, point.y())
            self.__crosshairRubberBandSx.addPoint(point, False)
            self.__crosshairRubberBandSx.addPoint(point1, True)
            
            point1.setX(point.x() + halfScreenSize)
            self.__crosshairRubberBandDx.addPoint(point, False)
            self.__crosshairRubberBandDx.addPoint(point1, True)
            
            point1.set(point.x(), point.y() - halfScreenSize)
            self.__crosshairRubberBandDw.addPoint(point, False)
            self.__crosshairRubberBandDw.addPoint(point1, True)
            
            point1.setY(point.y() + halfScreenSize)
            self.__crosshairRubberBandUp.addPoint(point, False)
            self.__crosshairRubberBandUp.addPoint(point1, True)

      if self.cursorType & QadCursorTypeEnum.APERTURE:
         apertureSize = self.__apertureSize * self.mapCanvas.mapUnitsPerPixel()

         self.__apertureRubberBand.reset(QgsWkbTypes.LineGeometry)
         
         point1 = QgsPointXY(point.x() - apertureSize, point.y() - apertureSize)
         dblApertureSize = apertureSize * 2
         self.__apertureRubberBand.addPoint(point1, False)
         point1.setX(point1.x() + dblApertureSize)
         self.__apertureRubberBand.addPoint(point1, False)
         point1.setY(point1.y() + dblApertureSize)
         self.__apertureRubberBand.addPoint(point1, False)
         point1.setX(point1.x() - dblApertureSize)
         self.__apertureRubberBand.addPoint(point1, False)
         point1.setY(point1.y() - dblApertureSize)
         self.__apertureRubberBand.addPoint(point1, True)


   def hide(self):
      if self.__boxRubberBand is not None:
         self.__boxRubberBand.hide()
         
      if self.__crosshairRubberBandSx is not None:
         self.__crosshairRubberBandSx.hide()
         self.__crosshairRubberBandDx.hide()
         self.__crosshairRubberBandDw.hide()
         self.__crosshairRubberBandUp.hide()

      if self.__apertureRubberBand is not None:
         self.__apertureRubberBand.hide()

      
   def show(self):
      if self.__boxRubberBand is not None:
         self.__boxRubberBand.show()
         
      if self.__crosshairRubberBandSx is not None:
         self.__crosshairRubberBandSx.show()
         self.__crosshairRubberBandDx.show()
         self.__crosshairRubberBandDw.show()
         self.__crosshairRubberBandUp.show()

      if self.__apertureRubberBand is not None:
         self.__apertureRubberBand.show()


# ===============================================================================
# getQGISColorForRubberBand
# ===============================================================================
def getQGISColorForRubberBand(geometryType = QgsWkbTypes.LineGeometry, alternativeBand = False):
   """
   La funzione legge il colore impostato da QGIS per il rubber band di tipo <geometryType>.
   Se <alternativeBand> = True, il rubber band sarà impostato con più trasparenza
   """
   settings = QSettings()
   color = QColor(int(settings.value( "/qgis/digitizing/line_color_red", 1)), \
                  int(settings.value( "/qgis/digitizing/line_color_green", 1)), \
                  int(settings.value( "/qgis/digitizing/line_color_blue", 1)))
   alpha = float(int(settings.value( "/qgis/digitizing/line_color_alpha", 200)) / 255.0)
  
   if alternativeBand:
      alpha = alpha * float(settings.value( "/qgis/digitizing/line_color_alpha_scale", 0.75))
 
   if geometryType == QgsWkbTypes.PolygonGeometry:
      color.setAlphaF(alpha)

   color.setAlphaF(alpha)
   return color


# ===============================================================================
# getColorForWindowSelectionArea
# ===============================================================================
def getColorForWindowSelectionArea():
   """
   La funzione legge il colore (RGB) dell'area di selezione degli oggetti nel modo finestra.
   """
   if QadVariables.get(QadMsg.translate("Environment variables", "SELECTIONAREA")) == 0:
      color = QColor()
      color.setAlphaF(0) # trasparente      
   else:
      color = QColor(QadVariables.get(QadMsg.translate("Environment variables", "WINDOWAREACOLOR")))
      opacity = QadVariables.get(QadMsg.translate("Environment variables", "SELECTIONAREAOPACITY")) # 0 = trasparente [0-100] 
      color.setAlphaF(opacity / 100.0) # trasformo da 0-100 a 0-1
      
   return color


# ===============================================================================
# getColorForCrossingSelectionArea
# ===============================================================================
def getColorForCrossingSelectionArea():
   """
   La funzione legge il colore (RGB) dell'area di selezione degli oggetti nel modo intersezione.
   """
   if QadVariables.get(QadMsg.translate("Environment variables", "SELECTIONAREA")) == 0:
      color = QColor()
      color.setAlphaF(0) # trasparente      
   else:
      color = QColor(QadVariables.get(QadMsg.translate("Environment variables", "CROSSINGAREACOLOR")))
      opacity = QadVariables.get(QadMsg.translate("Environment variables", "SELECTIONAREAOPACITY")) # 0 = trasparente [0-100] 
      color.setAlphaF(opacity / 100.0) # trasformo da 0-100 a 0-1
      
   return color


# ===============================================================================
# createRubberBand
# ===============================================================================
def createRubberBand(mapCanvas, geometryType = QgsWkbTypes.LineGeometry, alternativeBand = False, borderColor = None, fillColor = None):
   """
   la funzione crea un rubber band di tipo <geometryType> con le impostazioni di QGIS.
   Se <alternativeBand> = True, il rubber band sarà impostato con più trasparenza e tipolinea punteggiato   
   """
   settings = QSettings()
   width = int(settings.value( "/qgis/digitizing/line_width", 1))

   rb = QgsRubberBand(mapCanvas, geometryType)
   
   if alternativeBand:
      rb.setLineStyle(Qt.DotLine)

   if borderColor is None:
      borderColor = getQGISColorForRubberBand(geometryType, alternativeBand)
   rb.setStrokeColor(borderColor)

   if fillColor is None:
      rb.setFillColor(borderColor)
   else:
      rb.setFillColor(fillColor)

   rb.setWidth(width)
   
   return rb


# Classe che gestisce rubber band di oggetti geometricamente non omogenei
class QadRubberBand():
   def __init__(self, mapCanvas, alternativeBand = False, borderColor = None, fillColor = None):
      """
      Se <alternativeBand> = True, il rubber band sarà impostato con più trasparenza e tipolinea punteggiato   
      """
      self.mapCanvas = mapCanvas
      self.__rubberBandPoint = createRubberBand(self.mapCanvas, QgsWkbTypes.PointGeometry, alternativeBand, borderColor, fillColor)
      self.__rubberBandLine = createRubberBand(self.mapCanvas, QgsWkbTypes.LineGeometry, alternativeBand, borderColor, fillColor)
      self.__rubberBandPolygon = createRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry, alternativeBand, borderColor, fillColor)

   def __del__(self):
      self.hide()
      
      self.mapCanvas.scene().removeItem(self.__rubberBandPoint)
      del self.__rubberBandPoint
      
      self.mapCanvas.scene().removeItem(self.__rubberBandLine)
      del self.__rubberBandLine
      
      self.mapCanvas.scene().removeItem(self.__rubberBandPolygon)
      del self.__rubberBandPolygon         
   
   def hide(self):
      self.__rubberBandPoint.hide()
      self.__rubberBandLine.hide()
      self.__rubberBandPolygon.hide()         

   def show(self):
      self.__rubberBandPoint.show()
      self.__rubberBandLine.show()
      self.__rubberBandPolygon.show()
      
   def addGeometry(self, geom, layer = None, doUpdate = True):
      if layer is not None:
         # uso la geometria del layer per risolvere il caso ambiguo in cui
         # si vuole inserire una linea chiusa in un layer poligono      
         geomType = layer.geometryType()
         #geomType = geom.type()
         if geomType == QgsWkbTypes.PointGeometry:
            self.__rubberBandPoint.addGeometry(geom, layer, doUpdate)
         elif geomType == QgsWkbTypes.LineGeometry:
            self.__rubberBandLine.addGeometry(geom, layer, doUpdate)
         elif geomType == QgsWkbTypes.PolygonGeometry:
            self.__rubberBandPolygon.addGeometry(geom, layer, doUpdate)
      else:
         geomType = QgsWkbTypes.geometryType(geom.wkbType())
         if geomType == QgsWkbTypes.PointGeometry:
            self.__rubberBandPoint.addGeometry(geom, QgsCoordinateReferenceSystem(), doUpdate)
         elif geomType == QgsWkbTypes.LineGeometry:
            self.__rubberBandLine.addGeometry(geom, QgsCoordinateReferenceSystem(), doUpdate)
         elif geomType == QgsWkbTypes.PolygonGeometry:
            self.__rubberBandPolygon.addGeometry(geom, QgsCoordinateReferenceSystem(), doUpdate)


   def addGeometries(self, geoms, layer = None):
      for g in geoms:
         self.addGeometry(g, layer, False)
      
      # After adding the final geometry updatePosition() should be called.
      self.__rubberBandPoint.updatePosition()
      self.__rubberBandLine.updatePosition()
      self.__rubberBandPolygon.updatePosition()  
         
         
   def setLine(self, points):
      self.__rubberBandLine.reset(QgsWkbTypes.LineGeometry)
      tot = len(points) - 1
      i = 0
      while i <= tot:
         if i < tot:
            self.__rubberBandLine.addPoint(points[i], False)
         else: # ultimo punto
            self.__rubberBandLine.addPoint(points[i], True)
         i = i + 1

   def setPolygon(self, points):
      self.__rubberBandPolygon.reset(QgsWkbTypes.PolygonGeometry)
      tot = len(points) - 1
      i = 0
      while i <= tot:
         if i < tot:
            self.__rubberBandPolygon.addPoint(points[i], False)
         else: # ultimo punto
            self.__rubberBandPolygon.addPoint(points[i], True)
         i = i + 1


   def setGeometry(self, geom):
      self.reset()
      self.addGeometry(geom)      


   def addLinePoint(self, point, doUpdate = True, geometryIndex = 0):
      self.__rubberBandLine.addPoint(point, doUpdate, geometryIndex)

   def addPolygonPoint(self, point, doUpdate = True, geometryIndex = 0):
      self.__rubberBandPolygon.addPoint(point, doUpdate, geometryIndex)

   def reset(self):
      self.__rubberBandPoint.reset(QgsWkbTypes.PointGeometry)
      self.__rubberBandLine.reset(QgsWkbTypes.LineGeometry)
      self.__rubberBandPolygon.reset(QgsWkbTypes.PolygonGeometry)      
      
   def setLineStyle(self, penStyle):      
      self.__rubberBandLine.setLineStyle(penStyle)
      self.__rubberBandPolygon.setLineStyle(penStyle)
      
   def setBorderColor(self, color):
      self.__rubberBandPoint.setSecondaryStrokeColor(color)
      self.__rubberBandLine.setSecondaryStrokeColor(color)
      self.__rubberBandPolygon.setSecondaryStrokeColor(color)
      
   def setFillColor(self, color):
      self.__rubberBandPolygon.setFillColor(color)

   def setWidth(self, width):
      self.__rubberBandPoint.setWidth(width)
      self.__rubberBandLine.setWidth(width)
      self.__rubberBandPolygon.setWidth(width)
   