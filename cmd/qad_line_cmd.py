# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando PLINE per disegnare una linea
 
                              -------------------
        begin                : 2013-07-15
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
from qgis.core import QgsWkbTypes, QgsGeometry, QgsCoordinateTransform


from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_line import QadLine
from .qad_line_maptool import Qad_line_maptool, Qad_line_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_snapper import QadSnapTypeEnum, QadSnapper
from ..qad_geom_relations import *
from .. import qad_layer
from .. import qad_utils
from ..qad_rubberband import createRubberBand
from ..qad_entity import QadEntity
from ..qad_geom_relations import getQadGeomClosestPart


# Classe che gestisce il comando LINE
class QadLINECommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadLINECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "LINE")

   def getEnglishName(self):
      return "LINE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runLINECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/line.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_LINE", "Creates straight line segments.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.vertices = []
      self.rubberBand = createRubberBand(self.plugIn.canvas, QgsWkbTypes.LineGeometry)
      self.firstPtTan = None
      self.firstPtPer = None      
      self.firstEntity = None
      self.firstQadGeomPart = None
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
      # che non verrà salvata su un layer
      self.virtualCmd = False

   def __del__(self):
      QadCommandClass.__del__(self)
      self.rubberBand.hide()
      self.plugIn.canvas.scene().removeItem(self.rubberBand)


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_line_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None       


   def addVertex(self, point):
      self.vertices.append(point)     
      self.addPointToRubberBand(point)            
      self.plugIn.setLastPointAndSegmentAng(self.vertices[-1])            
      self.setTmpGeometriesToMapTool()
      
   def delLastVertex(self):
      if len(self.vertices) > 0:
         del self.vertices[-1] # cancello ultimo vertice
         self.removeLastPointToRubberBand()
         if len(self.vertices) > 0:
            self.plugIn.setLastPointAndSegmentAng(self.vertices[-1])
         self.setTmpGeometriesToMapTool()      
         

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

   def addLinesToLayer(self, layer):
      i = 1
      line = QadLine()
      while i < len(self.vertices):
         line.set(self.vertices[i - 1], self.vertices[i])
         geom = line.asGeom(layer.wkbType())
         if geom is not None:
            qad_layer.addGeomToLayer(self.plugIn, layer, self.mapToLayerCoordinates(layer, geom), None, True, False, \
                                     True if len(self.vertices) == 2 else False)
         i = i + 1


   # ============================================================================
   # setTmpGeometriesToMapTool
   # ============================================================================
   def setTmpGeometriesToMapTool(self):
      self.getPointMapTool().clearTmpGeometries()
      i = 1
      while i < len(self.vertices):                     
         # per lo snap aggiungo questa geometria temporanea
         self.getPointMapTool().appendTmpGeometry(QgsGeometry.fromPolylineXY([self.vertices[i - 1], self.vertices[i]]))
         i = i + 1

            
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
         # imposto il map tool
         self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
         # si appresta ad attendere un punto o enter
         self.waitForPoint(QadMsg.translate("Command_LINE", "Specify first point: "))
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
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.virtualCmd == False: # se si vuole veramente salvare in un layer   
                     self.addLinesToLayer(currLayer)
                  return True # fine comando
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            snapTypeOnSel = self.getPointMapTool().snapTypeOnSelection
            value = self.getPointMapTool().point
            entity = self.getPointMapTool().entity           
         else: # il punto arriva come parametro della funzione
            value = msg
            snapTypeOnSel = QadSnapTypeEnum.NONE

         if type(value) == unicode:
            if value == QadMsg.translate("Command_LINE", "Undo") or value == "Undo":               
               self.delLastVertex() # cancello ultimo vertice
               # imposto il map tool
               if len(self.vertices) == 0:
                  self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)
                  # si appresta ad attendere un punto o enter
                  #                        msg, inputType,              default, keyWords, nessun controllo
                  self.waitFor(QadMsg.translate("Command_LINE", "Specify first point: "), \
                               QadInputTypeEnum.POINT2D, None, "", QadInputModeEnum.NONE)
                  return False                  
               else:
                  self.getPointMapTool().firstPt = self.vertices[-1]
                  self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)
            elif value == QadMsg.translate("Command_LINE", "Close") or value == "Close":
               newPt = self.vertices[0]
               self.addVertex(newPt) # aggiungo un nuovo vertice
               if self.virtualCmd == False: # se si vuole veramente salvare in un layer   
                  self.addLinesToLayer(currLayer)
               return True # fine comando
         else:
            if len(self.vertices) == 0: # primo punto
               if value is None:
                  if self.plugIn.lastPoint is not None:
                     value = self.plugIn.lastPoint
                  else:
                     return True # fine comando
   
               # se é stato selezionato un punto con la modalità TAN_DEF é un punto differito
               if snapTypeOnSel == QadSnapTypeEnum.TAN_DEF and entity.isInitialized():
                  # se era stato selezionato un punto esplicito
                  if (self.firstPtTan is None) and (self.firstPtPer is None):                     
                     self.firstPtPer = None
                     self.firstPtTan = value
                     self.firstEntity = QadEntity(entity) # duplico l'entità
                     
                     # la funzione ritorna una lista con 
                     # (<minima distanza>
                     #  <punto più vicino>
                     #  <indice della geometria più vicina>
                     #  <indice della sotto-geometria più vicina>
                     #   se geometria chiusa è tipo polyline la lista contiene anche
                     #  <indice della parte della sotto-geometria più vicina>
                     #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
                     # )
                     result = getQadGeomClosestPart(self.firstEntity.getQadGeom(), self.firstPtTan)
                     self.firstQadGeomPart = getQadGeomPartAt(self.firstEntity.getQadGeom(), result[2], result[3], result[4])

                     # imposto il map tool
                     self.getPointMapTool().tan1 = self.firstPtTan
                     self.getPointMapTool().entity1 = self.firstEntity
                     self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_TAN_KNOWN_ASK_FOR_SECOND_PT)
                     
                  # se era stato selezionato un punto con la modalità TAN_DEF   
                  elif self.firstPtTan is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
                                             
                     tangent = QadTangency.bestTwoBasicGeomObjects(self.firstQadGeomPart, self.firstPtTan, secondQadGeomPart, value)
                     if tangent is not None:
                        # prendo il punto più vicino a valueself.firstEntity
                        if qad_utils.getDistance(tangent.getStartPt(), value) < qad_utils.getDistance(tangent.getEndPt(), value):                              
                           self.addVertex(tangent.getEndPt()) # aggiungo un nuovo vertice
                           self.addVertex(tangent.getStartPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = tangent.getStartPt()
                        else:
                           self.addVertex(tangent.getStartPt()) # aggiungo un nuovo vertice
                           self.addVertex(tangent.getEndPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = tangent.getEndPt()
                        # imposto il map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)         
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo tangent possible"))
                        
                  # se era stato selezionato un punto con la modalità PER_DEF              
                  elif self.firstPtPer is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
                     
                     tangent = QadTangPerp.bestTwoBasicGeomObjects(secondQadGeomPart, value, self.firstQadGeomPart, self.firstPtPer)
                     if tangent is not None:
                        # prendo il punto più vicino a value
                        if qad_utils.getDistance(tangent.getStartPt(), value) < qad_utils.getDistance(tangent.getEndPt(), value):                              
                           self.addVertex(tangent.getEndPt()) # aggiungo un nuovo vertice
                           self.addVertex(tangent.getStartPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = tangent.getStartPt()
                        else:
                           self.addVertex(tangent.getStartPt()) # aggiungo un nuovo vertice
                           self.addVertex(tangent.getEndPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = tangent.getEndPt()
                        # imposto il map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)         
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo tangent possible"))                        
                        
               # se é stato selezionato un punto con la modalità PER_DEF é un punto differito
               elif snapTypeOnSel == QadSnapTypeEnum.PER_DEF and entity.isInitialized():
                  # se era stato selezionato un punto esplicito
                  if (self.firstPtTan is None) and (self.firstPtPer is None):
                     self.firstPtTan = None
                     self.firstPtPer = value
                     self.firstEntity = QadEntity(entity) # duplico l'entità
                     
                     # la funzione ritorna una lista con 
                     # (<minima distanza>
                     #  <punto più vicino>
                     #  <indice della geometria più vicina>
                     #  <indice della sotto-geometria più vicina>
                     #   se geometria chiusa è tipo polyline la lista contiene anche
                     #  <indice della parte della sotto-geometria più vicina>
                     #  <"a sinistra di" se il punto é alla sinista della parte (< 0 -> sinistra, > 0 -> destra)
                     # )
                     result = getQadGeomClosestPart(self.firstEntity.getQadGeom(), self.firstPtPer)
                     self.firstQadGeomPart = getQadGeomPartAt(self.firstEntity.getQadGeom(), result[2], result[3], result[4])
                     
                     # imposto il map tool
                     self.getPointMapTool().per1 = self.firstPtPer
                     self.getPointMapTool().entity1 = self.firstEntity
                     self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PER_KNOWN_ASK_FOR_SECOND_PT)
                                    
                  # se era stato selezionato un punto con la modalità TAN_DEF   
                  elif self.firstPtTan is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
                     
                     tangent = QadTangPerp.bestTwoBasicGeomObjects(self.firstQadGeomPart, self.firstPtTan, secondQadGeomPart, value)
                     if tangent is not None:
                        # prendo il punto più vicino a value
                        if qad_utils.getDistance(tangent.getStartPt(), value) < qad_utils.getDistance(tangent.getEndPt(), value):                              
                           self.addVertex(tangent.getEndPt()) # aggiungo un nuovo vertice
                           self.addVertex(tangent.getStartPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = tangent.getStartPt()
                        else:
                           self.addVertex(tangent.getStartPt()) # aggiungo un nuovo vertice
                           self.addVertex(tangent.getEndPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = tangent.getEndPt()
                        # imposto il map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)         
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo perpendicular possible"))
                        
                  # se era stato selezionato un punto con la modalità PER_DEF              
                  elif self.firstPtPer is not None:
                     result = getQadGeomClosestPart(entity.getQadGeom(), value)
                     secondQadGeomPart = getQadGeomPartAt(entity.getQadGeom(), result[2], result[3], result[4])
                     
                     line = QadPerpPerp.bestTwoBasicGeomObjects(self.firstQadGeomPart, self.firstPtPer, secondQadGeomPart, value)
                     if line is not None:
                        # prendo il punto più vicino a value
                        if qad_utils.getDistance(line.getStartPt(), value) < qad_utils.getDistance(line.getEndPt(), value):                              
                           self.addVertex(line.getEndPt()) # aggiungo un nuovo vertice
                           self.addVertex(line.getStartPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = line.getStartPt()
                        else:
                           self.addVertex(line.getStartPt()) # aggiungo un nuovo vertice
                           self.addVertex(line.getEndPt()) # aggiungo un nuovo vertice
                           self.getPointMapTool().firstPt = line.getEndPt()
                        # imposto il map tool
                        self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)         
                     else:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo perpendicular possible"))
               else: # altrimenti é un punto esplicito
                  # se era stato selezionato un punto con la modalità TAN_DEF
                  if self.firstPtTan is not None:
                     snapper = QadSnapper()
                     snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.plugIn.canvas))
                     snapper.setSnapType(QadSnapTypeEnum.TAN)
                     snapper.setStartPoint(value)
                     oSnapPoints = snapper.getSnapPoint(self.firstEntity, self.firstPtTan)
                     # memorizzo il punto di snap in point (prendo il primo valido)
                     for item in oSnapPoints.items():
                        points = item[1]
                        if points is not None:
                           self.addVertex(points[0]) # aggiungo un nuovo vertice
                           self.addVertex(value) # aggiungo un nuovo vertice
                           break

                     if len(self.vertices) == 0:
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo tangent possible"))                                          
                  # se era stato selezionato un punto con la modalità PER_DEF
                  elif self.firstPtPer is not None:
                     snapper = QadSnapper()
                     snapper.setSnapLayers(qad_utils.getSnappableVectorLayers(self.plugIn.canvas))
                     snapper.setSnapType(QadSnapTypeEnum.PER)
                     snapper.setStartPoint(value)
                     oSnapPoints = snapper.getSnapPoint(self.firstEntity, self.firstPtPer)
                     # memorizzo il punto di snap in point (prendo il primo valido)
                     for item in oSnapPoints.items():
                        points = item[1]
                        if points is not None:
                           self.addVertex(points[0]) # aggiungo un nuovo vertice
                           self.addVertex(value) # aggiungo un nuovo vertice
                           break

                     if len(self.vertices) == 0:                        
                        self.showMsg(QadMsg.translate("Command_LINE", "\nNo perpendicular possible"))
                  else:
                     self.addVertex(value) # aggiungo un nuovo vertice

                  if len(self.vertices) > 0:                         
                     # imposto il map tool
                     self.getPointMapTool().firstPt = value
                     self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)         
            else: # secondo punto
               if value is None:
                  if self.virtualCmd == False: # se si vuole veramente salvare in un layer   
                     self.addLinesToLayer(currLayer)
                  return True # fine comando
               # se il primo punto é esplicito
               if len(self.vertices) > 0 is not None:
                  self.addVertex(value) # aggiungo un nuovo vertice    
                  # imposto il map tool
                  self.getPointMapTool().firstPt = value
                  self.getPointMapTool().setMode(Qad_line_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)         

         if len(self.vertices) > 2:
            keyWords = QadMsg.translate("Command_LINE", "Close") + "/" + \
                       QadMsg.translate("Command_LINE", "Undo")
            englishKeyWords = "Close" + "/" + "Undo"
         else:
            keyWords = QadMsg.translate("Command_LINE", "Undo")
            englishKeyWords = "Undo"
         prompt = QadMsg.translate("Command_LINE", "Specify next point or [{0}]: ").format(keyWords)
            
         keyWords += "_" + englishKeyWords
         # si appresta ad attendere un punto o enter o una parola chiave         
         # msg, inputType, default, keyWords, nessun controllo
         self.waitFor(prompt, \
                      QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                      None, \
                      keyWords, QadInputModeEnum.NONE)
         
         return False
      