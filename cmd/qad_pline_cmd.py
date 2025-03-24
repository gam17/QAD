# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin OK

 comando PLINE per disegnare una polilinea
 
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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsWkbTypes, QgsGeometry, QgsPointXY


from ..qad_line import QadLine
from ..qad_polyline import QadPolyline
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_pline_maptool import Qad_pline_maptool, Qad_pline_maptool_ModeEnum
from .qad_arc_maptool import Qad_arc_maptool, Qad_arc_maptool_ModeEnum
from ..qad_arc import QadArc
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer
from ..qad_rubberband import createRubberBand
from ..qad_dim import QadDimStyles
from ..qad_multi_geom import getQadGeomAt, fromQgsGeomToQadGeom
from ..qad_geom_relations import getQadGeomClosestPart, getQadGeomBetween2Pts
from ..qad_variables import QadVariables

# Classe che gestisce il comando PLINE
class QadPLINECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadPLINECommandClass(self.plugIn)
      
   def getName(self):
      return QadMsg.translate("Command_list", "PLINE")

   def getEnglishName(self):
      return "PLINE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runPLINECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/pline.svg")

   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_PLINE", "Creates a polyline by many methods.\n\nA polyline is a single object that is composed of line,\nand arc segments.")
   
   def __init__(self, plugIn, asToolForMPolygon = False):
      QadCommandClass.__init__(self, plugIn)
      self.polyline = QadPolyline()
      self.firstVertex = None
      
      self.asToolForMPolygon = asToolForMPolygon
      if self.asToolForMPolygon:
         self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.PolygonGeometry, False)
      else:
         self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
         
      self.ArcPointMapTool = None
      self.mode = "LINE"
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
      # che non verrà salvata su un layer
      self.virtualCmd = False


   def __del__(self):
      QadCommandClass.__del__(self)
      if self.ArcPointMapTool is not None:
         self.ArcPointMapTool.removeItems()
         del self.ArcPointMapTool

      self.rubberBand.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBand)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.mode == "ARC":
            if self.ArcPointMapTool is None:
               self.ArcPointMapTool = Qad_arc_maptool(self.plugIn, self.asToolForMPolygon) # se True significa che è usato per disegnare un poligono
               if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
                  currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
                  if currLayer is not None:
                     self.ArcPointMapTool.layer = currLayer
               
            return self.ArcPointMapTool
         else:
            if self.PointMapTool is None:
               self.PointMapTool = Qad_pline_maptool(self.plugIn, self.asToolForMPolygon) # se True significa che è usato per disegnare un poligono
            return self.PointMapTool
      else:
         return None

   
   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      if rubberBandBorderColor is not None:
         self.rubberBand.setBorderColor(rubberBandBorderColor)
      if rubberBandFillColor is not None:
         self.rubberBand.setFillColor(rubberBandFillColor)


   def getLastSegmentAng(self):
      if self.polyline.qty() == 0:
         result = self.plugIn.lastSegmentAng
      else:
         result = self.polyline.getTanDirectionOnEndPt()
      
      return result


   def getFirstPt(self):
      if self.polyline.qty() == 0:
         return self.firstVertex
      else:
         return self.polyline.getStartPt()


   def getLastPt(self):
      if self.polyline.qty() == 0:
         return self.firstVertex
      else:
         return self.polyline.getEndPt()


   # ============================================================================
   # WaitForArcMenu
   # ============================================================================
   def WaitForArcMenu(self):
      # l'opzione CEnter viene tradotta in italiano in "CEntro" nel contesto "WaitForArcMenu"
      # l'opzione Undo viene tradotta in italiano in "ANNulla" nel contesto "WaitForArcMenu"
      keyWords = QadMsg.translate("Command_PLINE", "Angle") + "/" + \
                 QadMsg.translate("Command_PLINE", "CEnter", "WaitForArcMenu") + "/" + \
                 QadMsg.translate("Command_PLINE", "Close") +  "/" + \
                 QadMsg.translate("Command_PLINE", "Direction") + "/" + \
                 QadMsg.translate("Command_PLINE", "Line") + "/" + \
                 QadMsg.translate("Command_PLINE", "Radius") +  "/" + \
                 QadMsg.translate("Command_PLINE", "Second point") + "/" + \
                 QadMsg.translate("Command_PLINE", "Undo", "WaitForArcMenu")
      englishKeyWords = "Angle" + "/" + "CEnter" + "/" + "Close" + "/" + \
                        "Direction" + "/" + "Line" + "/" + "Radius" + "/" + \
                        "Second point"  + "/" + "Undo"
                 
      prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

      self.arcStartPt = self.getLastPt() # ultimo vertice
      self.arcTanOnStartPt = self.getLastSegmentAng()
   
      # Il segmento di arco é tangente al precedente segmento della polilinea
      # uso il map tool per l'arco
      self.mode = "ARC"
      self.getPointMapTool().arcStartPt = self.arcStartPt
      self.getPointMapTool().arcTanOnStartPt = self.arcTanOnStartPt
      self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT)
      if self.asToolForMPolygon:
         self.getPointMapTool().endVertex = self.polyline.getStartPt()
      
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      self.step = 101
      return

   # ============================================================================
   # WaitForLineMenu
   # ============================================================================
   def WaitForLineMenu(self):
      # l'opzione Undo viene tradotta in italiano in "ANnulla" nel contesto "WaitForLineMenu"
      if self.polyline.qty() >= 2:
         keyWords = QadMsg.translate("Command_PLINE", "Arc") + "/" + \
                    QadMsg.translate("Command_PLINE", "Close") + "/" + \
                    QadMsg.translate("Command_PLINE", "Length") + "/" + \
                    QadMsg.translate("Command_PLINE", "Undo", "WaitForLineMenu") + "/" + \
                    QadMsg.translate("Command_PLINE", "Trace")
         englishKeyWords = "Arc" + "/" + "Close" + "/" + "Length" + "/" + "Undo"+ "/" + "Trace"
      else:
         keyWords = QadMsg.translate("Command_PLINE", "Arc") + "/" + \
                    QadMsg.translate("Command_PLINE", "Length") + "/" + \
                    QadMsg.translate("Command_PLINE", "Undo", "WaitForLineMenu") + "/" + \
                    QadMsg.translate("Command_PLINE", "Trace")
         englishKeyWords = "Arc" + "/" + "Length"+ "/" + "Undo" + "/" + "Trace"

      prompt = QadMsg.translate("Command_PLINE", "Specify next point or [{0}]: ").format(keyWords)
         
      self.step = 1 # MENU PRINCIPLE

      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)


   # ============================================================================
   # waitForTracePt
   # ============================================================================
   def waitForTracePt(self, msgMapTool, msg):
      self.step = 3
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_pline_maptool_ModeEnum.ASK_FOR_TRACE_PT)
      self.getPointMapTool().firstPt = self.getLastPt() # ultimo vertice
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_PLINE", "Select the object in the trace end point: "))


   # ============================================================================
   # addPointToPolyline
   # ============================================================================
   def addPointToPolyline(self, pt):
      if self.firstVertex is None:
         self.firstVertex = QgsPointXY(pt)
         self.plugIn.setLastPoint(pt)
         self.getPointMapTool().setStartPoint(self.firstVertex)
         if self.asToolForMPolygon:
            self.getPointMapTool().endVertex = self.firstVertex
         return
      else:
         self.addLinearObjToPolyline(QadLine().set(self.getLastPt(), pt))


   # ============================================================================
   # addLinearObjToPolyline
   # ============================================================================
   def addLinearObjToPolyline(self, linearObj):
      pts = linearObj.asPolyline()
      tot = len(pts)
      if tot > 0:
         if self.rubberBand.numberOfVertices() > 0:
            i = 1
         else:
            i = 0
         tot = tot - 1
         while i < tot:
            self.addPointToRubberBand(pts[i], False)
            i = i + 1
         self.addPointToRubberBand(pts[-1], True)
         
         self.polyline.append(linearObj)
         self.plugIn.setLastPoint(pts[-1])
         self.plugIn.setLastSegmentAng(self.getLastSegmentAng())
         self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
         self.getPointMapTool().setStartPoint(pts[-1])
         self.getPointMapTool().setTmpGeometry(self.polyline.asGeom()) # per lo snap aggiungo questa geometria temporanea


   # ============================================================================
   # removeLastLinearObjToPolyline
   # ============================================================================
   def removeLastLinearObjToPolyline(self):
      totLinearObjs = self.polyline.qty()
      if totLinearObjs == 0: return
      linearObj = self.polyline.getLinearObjectAt(-1)
      lastPt = linearObj.getStartPt()
      pts = linearObj.asPolyline()
      tot = len(pts)
      if totLinearObjs == 1:
         i = 0
      else:
         i = 1
      while i < tot:
         self.rubberBand.removeLastPoint()
         i = i + 1

      self.polyline.remove(-1) # cancello ultima parte
      self.plugIn.setLastPoint(lastPt)
      self.plugIn.setLastSegmentAng(self.getLastSegmentAng())
      self.getPointMapTool().setTmpGeometry(self.polyline.asGeom()) # per lo snap aggiungo questa geometria temporanea
      self.getPointMapTool().setPolarAngOffset(self.plugIn.lastSegmentAng)
      self.getPointMapTool().setStartPoint(lastPt)
            
   
   # ============================================================================
   # addPointToRubberBand
   # ============================================================================
   def addPointToRubberBand(self, point, doUpdate = True):
      numberOfVertices = self.rubberBand.numberOfVertices()
         
      if numberOfVertices == 2:
         # per un baco non ancora capito: se la linea ha solo 2 vertici e 
         # hanno la stessa x o y (linea orizzontale o verticale) 
         # la linea non viene disegnata perciò sposto un pochino la x o la y                 
         adjustedPoint = qad_utils.getAdjustedRubberBandVertex(self.rubberBand.getPoint(0, 0), point)                                                               
         self.rubberBand.addPoint(adjustedPoint, doUpdate)
      else:
         self.rubberBand.addPoint(point, doUpdate)
      
      
   # ============================================================================
   # removeLastPointToRubberBand
   # ============================================================================
   def removeLastPointToRubberBand(self):
      self.rubberBand.removeLastPoint()
         
         
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
         currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
         if currLayer is None:
            self.showErr(errMsg)
            return True # fine comando
      
      # RICHIESTA PRIMO PUNTO 
      if self.step == 0: # inizio del comando        
         self.getPointMapTool().setMode(Qad_pline_maptool_ModeEnum.DRAW_LINE) # imposto la linea elastica
         # si appresta ad attendere un punto o enter
         #                        msg, inputType,              default, keyWords, nessun controllo
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify start point: "))
         self.step = 1
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO OPPURE MENU PRINCIPALE
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False
               
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer
                     geom = self.polyline.asGeom(currLayer.wkbType())
                     if geom is not None:
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg
         
         if value is None:
            if self.firstVertex is None:
               if self.plugIn.lastPoint is not None:
                  value = self.plugIn.lastPoint
               else:
                  return True # fine comando
            else:
               if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer
                  geom = self.polyline.asGeom(currLayer.wkbType())
                  if geom is not None:
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))                   
               return True # fine comando

         if type(value) == unicode:
            if value == QadMsg.translate("Command_PLINE", "Arc") or value == "Arc":
               self.WaitForArcMenu()
               return False
            elif value == QadMsg.translate("Command_PLINE", "Length") or value == "Length":
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               # "Specificare lunghezza della linea: " 
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify line length: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 2
               return False
            # l'opzione Undo viene tradotta in italiano in "ANnulla" nel contesto "WaitForLineMenu"
            elif value == QadMsg.translate("Command_PLINE", "Undo", "WaitForLineMenu") or value == "Undo":
               if self.polyline.qty() > 0:
                  self.getPointMapTool().clear()
                  self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
                  self.removeLastLinearObjToPolyline()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                                    
            elif value == QadMsg.translate("Command_PLINE", "Close") or value == "Close":
               self.polyline.setClose()
               if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
                  geom = self.polyline.asGeom(currLayer.wkbType())
                  if geom is not None:
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
            elif value == QadMsg.translate("Command_PLINE", "Trace") or value == "Trace":
               self.waitForTracePt(msgMapTool, msg)
               return False # continua

         elif type(value) == QgsPointXY:
            self.addPointToPolyline(value)
         
         self.WaitForLineMenu()
         
         return False
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Lunghezza" (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY:
            dist = qad_utils.getDistance(self.getLastPt(), value)
         else:
            dist = value

         newPt = qad_utils.getPolarPointByPtAngle(self.getLastPt(), self.getLastSegmentAng(), dist)
         self.addPointToPolyline(newPt)
         
         self.WaitForLineMenu()        
         
         self.step = 1 # torno al MENU PRINCIPLE
         
         return False

      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Selezionare l'oggetto nel punto finale di ricalco: " (da step = 1)
      elif self.step == 3:
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY:
            geom = None
            layer = None
            if self.getPointMapTool().entity.isInitialized(): # il punto arriva dal mouse
               entSelected = True
               layer = self.getPointMapTool().entity.layer
               geom = self.getPointMapTool().entity.getGeometry()
            else: # il punto arriva da tastiera
               # cerco se ci sono entità nel punto indicato considerando
               # solo layer lineari o poligono che non appartengano a quote
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
                  if layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)
                                     
               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value),
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  feature = result[0]
                  layer = result[1]
                  geom = feature.getGeometry()

            if geom is not None and layer is not None:
               qadGeom = fromQgsGeomToQadGeom(geom, layer.crs())
               # la funzione ritorna una lista con 
               # (<minima distanza>
               # <punto più vicino>
               # <indice della geometria più vicina>
               # <indice della sotto-geometria più vicina>
               # <indice della parte della sotto-geometria più vicina>
               # <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
               dummy = getQadGeomClosestPart(qadGeom, value)
               qadGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
               subGeom = getQadGeomBetween2Pts(qadGeom, self.getLastPt(), dummy[1])
               if subGeom is not None:
                  pl = QadPolyline()
                  pl.fromPolyline(subGeom.asPolyline())
                  tot = pl.qty()
                  i = 0
                  while i < tot:
                     self.addLinearObjToPolyline(pl.getLinearObjectAt(i))
                     i = i + 1

         self.WaitForLineMenu()
         self.getPointMapTool().setMode(Qad_pline_maptool_ModeEnum.DRAW_LINE)
         self.getPointMapTool().setTmpGeometry(self.polyline.asGeom()) # per lo snap aggiungo questa geometria temporanea
         self.getPointMapTool().setStartPoint(self.getLastPt())
         
         return False

      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare punto finale dell'arco o [Angolo/CEntro/CHiudi/Direzione/LInea/Raggio/Secondo punto/ANNulla]: " (da step = 1)
      elif self.step == 101: # dopo aver atteso un punto o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
                     geom = self.polyline.asGeom(currLayer.wkbType())
                     if geom is not None:
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if value is None:
            if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
               geom = self.polyline.asGeom(currLayer.wkbType())
               if geom is not None:
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
            return True # fine comando
         
         if type(value) == unicode:
            if value == QadMsg.translate("Command_PLINE", "Angle") or value == "Angle":
               self.arcStartPt = self.getLastPt()
               
               # imposto il map tool
               self.getPointMapTool().arcStartPt = self.arcStartPt
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_ANGLE)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 102
            # l'opzione CEnter viene tradotta in italiano in "CEntro" nel contesto "WaitForArcMenu"
            elif value == QadMsg.translate("Command_PLINE", "CEnter", "WaitForArcMenu") or value == "CEnter":
               self.arcStartPt = self.getLastPt()
               
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_CENTER_PT)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the center of the arc: "))
               self.step = 108
            elif value == QadMsg.translate("Command_PLINE", "Close") or value == "Close":
               arc = QadArc()

               if arc.fromStartEndPtsTan(self.arcStartPt, self.getFirstPt(), self.arcTanOnStartPt) == True:
                  self.addLinearObjToPolyline(arc)

                  if self.virtualCmd == False: # se si vuole veramente salvare la polylinea in un layer   
                     geom = self.polyline.asGeom(currLayer.wkbType())
                     if geom is not None:
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))

                  return True # fine comando
            elif value == QadMsg.translate("Command_PLINE", "Direction") or value == "Direction":
               self.arcStartPt = self.getLastPt()
               
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the tangent direction for the start point of the arc: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", QadInputModeEnum.NOT_NULL)
               self.step = 112
            elif value == QadMsg.translate("Command_PLINE", "Line") or value == "Line":
               self.mode = "LINE"
               self.getPointMapTool().refreshSnapType() # riagggiorno lo snapType che può essere variato dal maptool dell'arco
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
               self.getPointMapTool().setStartPoint(self.getLastPt())      
               self.WaitForLineMenu()              
            elif value == QadMsg.translate("Command_PLINE", "Radius") or value == "Radius":
               self.arcStartPt = self.getLastPt()
               
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the radius of the arc: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 114
            elif value == QadMsg.translate("Command_PLINE", "Second point") or value == "Second point":
               self.arcStartPt = self.getLastPt()
               
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_SECOND_PT)
               # si appresta ad attendere un punto               
               self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify second point of the arc: "))
               self.step = 119
            # l'opzione Undo viene tradotta in italiano in "ANNulla" nel contesto "WaitForArcMenu"
            elif value == QadMsg.translate("Command_PLINE", "Undo", "WaitForArcMenu") or value == "Undo":
               if self.polyline.qty() > 0:
                  self.getPointMapTool().clear()
                  self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_LINE)
                  self.removeLastLinearObjToPolyline()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))                                                      
               self.WaitForArcMenu()
         elif type(value) == QgsPointXY: # é stato inserito il punto finale dell'arco
            arc = QadArc()         
            if arc.fromStartEndPtsTan(self.arcStartPt, value, self.arcTanOnStartPt) == True:
               if ctrlPressed: # inverto angolo iniziale-finale
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)
                                       
            self.WaitForArcMenu()
                       
         return False                              


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare angolo inscritto: " (da step = 101)
      elif self.step == 102: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY:
            self.arcAngle = qad_utils.getAngleBy2Pts(self.arcStartPt, value)             
         else:
            self.arcAngle = value

         # imposto il map tool
         self.getPointMapTool().arcAngle = self.arcAngle
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_END_PT)

         # l'opzione CEnter viene tradotta in italiano in "Centro" nel contesto "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT"
         keyWords = QadMsg.translate("Command_PLINE", "CEnter", "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT") + "/" + \
                    QadMsg.translate("Command_PLINE", "Radius")
         englishKeyWords = "CEnter" + "/" + "Radius"
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
                    
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o una parola chiave         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         self.step = 103

         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare punto finale dell'arco o [Centro/Raggio]: : " (da step = 102)
      elif self.step == 103: # dopo aver atteso un punto o una parola chiave si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == unicode:
            # l'opzione CEnter viene tradotta in italiano in "Centro" nel contesto "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT"
            if value == QadMsg.translate("Command_PLINE", "CEnter", "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT") or value == "CEnter":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_CENTER_PT)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the center of the arc (hold Ctrl to switch direction): "))
               self.step = 104
            elif value == QadMsg.translate("Command_PLINE", "Radius") or value == "Radius":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_RADIUS)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the radius of the arc: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 105
         elif type(value) == QgsPointXY: # é stato inserito il punto finale dell'arco
            arc = QadArc()         
            if arc.fromStartEndPtsAngle(self.arcStartPt, value, self.arcAngle) == True:
               if ctrlPressed: # inverto angolo iniziale-finale
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)
                      
               self.WaitForArcMenu()
               return False

            # l'opzione CEnter viene tradotta in italiano in "Centro" nel contesto "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT"
            keyWords = QadMsg.translate("Command_PLINE", "CEnter", "START_PT_ANGLE_KNOWN_ASK_FOR_END_PT") + "/" + \
                       QadMsg.translate("Command_PLINE", "Radius")
            prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)

            englishKeyWords = "CEnter" + "/" + "Radius"
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere un punto o una parola chiave         
            # msg, inputType, default, keyWords, isNullable
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, \
                         keyWords, QadInputModeEnum.NOT_NULL)
            
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA CENTRO DELL'ARCO (da step = 103)
      elif self.step == 104: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         arc = QadArc()         
         if arc.fromStartCenterPtsAngle(self.arcStartPt, value, self.arcAngle) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)
                  
            self.WaitForArcMenu()
            return False      

         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the center of the arc: "))
                 
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA RAGGIO (da step = 103)
      elif self.step == 105: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY:
            self.arcStartPtForRadius = value
            
            # imposto il map tool
            self.getPointMapTool().arcStartPtForRadius = self.arcStartPtForRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS)
         
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify second point: "))
            self.step = 106
         else:
            self.arcRadius = value
            self.plugIn.setLastRadius(self.arcRadius)

            # imposto il map tool
            self.getPointMapTool().arcRadius = self.arcRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
            # si appresta ad attendere un punto o un numero reale         
            # msg, inputType, default, keyWords, isNullable
            msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
            self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                         None, "", QadInputModeEnum.NOT_NULL)
            self.step = 107
            
         return False                                          


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO DEL RAGGIO (da step = 105)
      elif self.step == 106: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.arcRadius = qad_utils.getDistance(self.arcStartPtForRadius, value)
         self.plugIn.setLastRadius(self.arcRadius)     

         # imposto il map tool
         self.getPointMapTool().arcRadius = self.arcRadius
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
         self.step = 107


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DIREZIONE DELLA CORDA DELL'ARCO (da step = 106 e 107)
      elif self.step == 107: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcChordDirection = qad_utils.getAngleBy2Pts(self.arcStartPt, value)             
         else:
            self.arcChordDirection = value
         
         arc = QadArc()
         if arc.fromStartPtAngleRadiusChordDirection(self.arcStartPt, self.arcAngle, \
                                                     self.arcRadius, self.arcChordDirection) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)
               
            self.WaitForArcMenu()
            return False      

         # imposto il map tool
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
                 
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA CENTRO DELL'ARCO (da step = 101)
      elif self.step == 108: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.arcCenterPt = value

         # imposto il map tool
         self.getPointMapTool().arcCenterPt = self.arcCenterPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_END_PT)

         keyWords = QadMsg.translate("Command_PLINE", "Angle") + "/" + \
                    QadMsg.translate("Command_PLINE", "chord Length")
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
         
         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords        
         # si appresta ad attendere un punto o una parola chiave         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         self.step = 109      
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare punto finale dell'arco o [Angolo/Lunghezza corda]: " (da step = 108)
      elif self.step == 109: # dopo aver atteso un punto o una parola chiave si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == unicode:  
            if value == QadMsg.translate("Command_PLINE", "Angle") or value == "Angle":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_ANGLE)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori != 0
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 110
               return False
            elif value == QadMsg.translate("Command_PLINE", "chord Length") or value == "chord Length":
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_CENTER_PT_KNOWN_ASK_FOR_CHORD)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, valori positivi
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the chord length (hold Ctrl to switch direction): "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)
               self.step = 111
               return False                              
         elif type(value) == QgsPointXY: # se é stato inserito il punto finale dell'arco
            self.arcEndPt = value
                     
            arc = QadArc()         
            if arc.fromStartCenterEndPts(self.arcStartPt, self.arcCenterPt, self.arcEndPt) == True:
               if ctrlPressed: # inverto angolo iniziale-finale
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)
                  
               self.WaitForArcMenu()
               return False      
            
         keyWords = QadMsg.translate("Command_PLINE", "Angle") + "/" + \
                    QadMsg.translate("Command_PLINE", "chord Length")
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
         
         englishKeyWords = "Angle" + "/" + "chord Length"
         keyWords += "_" + englishKeyWords         
         # si appresta ad attendere un punto o una parola chiave         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NOT_NULL)
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare angolo inscritto: " (da step = 109)
      elif self.step == 110: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcAngle = qad_utils.getAngleBy2Pts(self.arcCenterPt, value)             
         else:
            self.arcAngle = value

         arc = QadArc()         
         if arc.fromStartCenterPtsAngle(self.arcStartPt, self.arcCenterPt, self.arcAngle) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)
               
            self.WaitForArcMenu()
            return False      

         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)

         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare lunghezza della corda: " (da step = 109)
      elif self.step == 111: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcChord = qad_utils.getDistance(self.arcStartPt, value)             
         else:
            self.arcChord = value

         arc = QadArc()         
         if arc.fromStartCenterPtsChord(self.arcStartPt, self.arcCenterPt, self.arcChord) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)
               
            self.WaitForArcMenu()
            return False      

         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, valori positivi
         self.waitFor(QadMsg.translate("Command_PLINE", "Specify the chord length (hold Ctrl to switch direction): "), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.FLOAT, \
                      None, "", \
                      QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)

         return False

     
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare direzione tangente per il punto iniziale dell'arco: " (da step = 101)
      elif self.step == 112: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY:
            self.arcTanOnStartPt = qad_utils.getAngleBy2Pts(self.arcStartPt, value)             
         else:
            self.arcTanOnStartPt = value

         # imposto il map tool
         self.getPointMapTool().arcTanOnStartPt = self.arcTanOnStartPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_TAN_KNOWN_ASK_FOR_END_PT)

         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction): "))
         self.step = 113
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO FINALE DELL'ARCO (da step = 112)
      elif self.step == 113: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         arc = QadArc()
         if arc.fromStartEndPtsTan(self.arcStartPt, value, self.arcTanOnStartPt) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)
               
            self.WaitForArcMenu()
            return False      

         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction): "))
                 
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA RAGGIO (da step = 101)
      elif self.step == 114: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY:
            self.arcStartPtForRadius = value
            
            # imposto il map tool
            self.getPointMapTool().arcStartPtForRadius = self.arcStartPtForRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_KNOWN_ASK_FOR_SECONDPTRADIUS)
         
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify second point: "))
            self.step = 115
         else:
            self.arcRadius = value
            self.plugIn.setLastRadius(self.arcRadius)

            # imposto il map tool
            self.getPointMapTool().arcRadius = self.arcRadius
            self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT)
            
            keyWords = QadMsg.translate("Command_PLINE", "Angle")
            prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
            englishKeyWords = "Angle"
            keyWords += "_" + englishKeyWords
            # si appresta ad attendere un punto o un numero reale         
            # msg, inputType, default, keyWords, isNullable
            self.waitFor(prompt, \
                         QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                         None, keyWords, QadInputModeEnum.NOT_NULL)
            self.step = 116
            
         return False                                          


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO DEL RAGGIO (da step = 114)
      elif self.step == 115: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.arcRadius = qad_utils.getDistance(self.arcStartPtForRadius, value)
         self.plugIn.setLastRadius(self.arcRadius)     

         # imposto il map tool
         self.getPointMapTool().arcRadius = self.arcRadius
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_RADIUS_KNOWN_ASK_FOR_END_PT)
         
         keyWords = QadMsg.translate("Command_PLINE", "Angle")
         prompt = QadMsg.translate("Command_PLINE", "Specify the final point of the arc (hold Ctrl to switch direction) or [{0}]: ").format(keyWords)
         englishKeyWords = "Angle"
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, isNullable
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, keyWords, QadInputModeEnum.NOT_NULL)
         self.step = 116
      
         return False
      
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare punto finale dell'arco o [Angolo]: " (da step = 114 o 115)
      elif self.step == 116: # dopo aver atteso un punto o una parola chiave si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == unicode:
            if value == QadMsg.translate("Command_PLINE", "Angle") or value == "Angle":               
               # imposto il map tool
               self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_KNOWN_ASK_FOR_ANGLE)
               # si appresta ad attendere un punto o un numero reale         
               # msg, inputType, default, keyWords, isNullable
               self.waitFor(QadMsg.translate("Command_PLINE", "Specify the included angle: "), \
                            QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                            None, "", \
                            QadInputModeEnum.NOT_NULL | QadInputModeEnum.NOT_ZERO)
               self.step = 117
         elif type(value) == QgsPointXY: # é stato inserito il punto finale dell'arco
            arc = QadArc()         
            if arc.fromStartEndPtsRadius(self.arcStartPt, value, self.arcRadius) == True:
               if ctrlPressed: # inverto angolo iniziale-finale
                  arc.inverseAngles()
               self.addLinearObjToPolyline(arc)
                     
            self.WaitForArcMenu()
                       
         return False                              
      

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA "Specificare angolo inscritto: " (da step = 116)
      elif self.step == 117: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY:
            self.arcAngle = qad_utils.getAngleBy2Pts(self.arcStartPt, value)             
         else:
            self.arcAngle = value

         # imposto il map tool
         self.getPointMapTool().arcAngle = self.arcAngle
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
         self.step = 118

         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DIREZIONE DELLA CORDA DELL'ARCO (da step = 117)
      elif self.step == 118: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
            ctrlPressed = self.getPointMapTool().ctrlKey
         else: # il punto arriva come parametro della funzione
            value = msg
            ctrlPressed = False

         if type(value) == QgsPointXY:
            self.arcChordDirection = qad_utils.getAngleBy2Pts(self.arcStartPt, value)             
         else:
            self.arcChordDirection = value
         
         arc = QadArc()
         if arc.fromStartPtAngleRadiusChordDirection(self.arcStartPt, self.arcAngle, \
                                                     self.arcRadius, self.arcChordDirection) == True:
            if ctrlPressed: # inverto angolo iniziale-finale
               arc.inverseAngles()
            self.addLinearObjToPolyline(arc)
            
            self.WaitForArcMenu()
            return False      

         # imposto il map tool
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_PT_ANGLE_RADIUS_KNOWN_ASK_FOR_CHORDDIRECTION)
         # si appresta ad attendere un punto o un numero reale         
         # msg, inputType, default, keyWords, isNullable
         msg = QadMsg.translate("Command_PLINE", "Specify the direction for the chord of the arc (hold Ctrl to switch direction) <{0}>: ")
         self.waitFor(msg.format(str(self.getLastSegmentAng())), \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                      None, "", QadInputModeEnum.NOT_NULL)
                 
         return False
      
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA SECONDO PUNTO (da step = 101)
      elif self.step == 119: # dopo aver atteso un punto o una parola chiave si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.arcSecondPt = value
         # imposto il map tool
         self.getPointMapTool().arcSecondPt = self.arcSecondPt
         self.getPointMapTool().setMode(Qad_arc_maptool_ModeEnum.START_SECOND_PT_KNOWN_ASK_FOR_END_PT)

         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc: "))
         self.step = 120
                  
         return False
      
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO FINALE DELL'ARCO (da step = 119)
      elif self.step == 120: # dopo aver atteso un punto si riavvia il comando
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

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         self.arcEndPt = value
         
         arc = QadArc()         
         if arc.fromStartSecondEndPts(self.arcStartPt, self.arcSecondPt, self.arcEndPt) == True:
            self.addLinearObjToPolyline(arc)
               
            self.WaitForArcMenu()
            return False      
      
         # si appresta ad attendere un punto
         self.waitForPoint(QadMsg.translate("Command_PLINE", "Specify the final point of the arc: "))     
         return False      