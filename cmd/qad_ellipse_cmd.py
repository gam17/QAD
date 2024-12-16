# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando ELLIPSE per disegnare una ellisse
 
                              -------------------
        begin                : 2018-05-22
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
from qgis.core import QgsWkbTypes, QgsPointXY
from qgis.PyQt.QtGui import QIcon
import math


from ..qad_ellipse import QadEllipse
from ..qad_ellipse_arc import QadEllipseArc
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_ellipse_maptool import Qad_ellipse_maptool, Qad_ellipse_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from .. import qad_utils
from .. import qad_layer


# ===============================================================================
# QadMELLIPSECommandClassStepEnum class.
# ===============================================================================
class QadELLIPSECommandClassStepEnum():
   ASK_FOR_FIRST_FINAL_AXIS_PT      = 1 # richiede il primo punto finale dell'asse (0 è l'inizio del comando)
   ASK_FOR_SECOND_FINAL_AXIS_PT     = 2 # richiede il secondo punto finale dell'asse
   ASK_DIST_TO_OTHER_AXIS           = 3 # richiede di specificare la distanza dal secondo asse
   ASK_ROTATION_ROUND_MAJOR_AXIS    = 4 # richiede la rotazione attorno all'asse maggiore
   ASK_START_ANGLE                  = 5 # richiede l'angolo iniziale
   ASK_END_ANGLE                    = 6 # richiede l'angolo finale
   ASK_INCLUDED_ANGLE               = 7 # richiede l'angolo incluso
   ASK_START_PARAMETER              = 8 # richiede l'angolo parametrico iniziale
   ASK_END_PARAMETER                = 9 # richiede l'angolo parametrico finale
   ASK_FOR_CENTER                   = 10 # richiede il centro
   ASK_FOR_FIRST_FOCUS              = 11 # richiede il primo punto di fuoco
   ASK_FOR_SECOND_FOCUS             = 12 # richiede il secondo punto di fuoco
   ASK_FOR_PT_ON_ELLIPSE            = 13 # richiede un punto sull'ellisse
   ASK_AREA                         = 14 # richede l'area dell'ellisse

# Classe che gestisce il comando ELLIPSE
class QadELLIPSECommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadELLIPSECommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "ELLIPSE")

   def getEnglishName(self):
      return "ELLIPSE"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runELLIPSECommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/ellipse.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_ELLIPSE", "Draws an ellipse by many methods.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      # se questo flag = True il comando serve all'interno di un altro comando per disegnare un cerchio
      # che non verrà salvato su un layer
      self.virtualCmd = False
      self.rubberBandBorderColor = None
      self.rubberBandFillColor = None
      
      self.arc = False # flag che stabilisce se si vuole disegnare un arco di ellisse o un ellisse intera
      self.axis1Pt1 = None # primo punto finale dell'asse
      self.axis1Pt2 = None # secondo punto finale dell'asse
      self.distToOtherAxis = 0.0 # distanza dall'altro asse
      self.centerPt = None # punto centrale dell'ellisse
      self.ellipse = QadEllipse()
      self.ellipseArc = QadEllipseArc()
      self.rot = 0 # rotazione intorno all'asse
      self.startAngle = 0.0 # l'ellisse può essere incompleta (come l'arco per il cerchio)
      self.endAngle = math.pi * 2 # A startAngle of 0 and endAngle of 2pi will produce a closed Ellipse.
      self.includedAngle = 0.0
      self.focus1 = None # primo punto di fuoco
      self.focus2 = None # secondo punto di fuoco


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_ellipse_maptool(self.plugIn)
            self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)
         return self.PointMapTool
      else:
         return None


   def setRubberBandColor(self, rubberBandBorderColor, rubberBandFillColor):
      self.rubberBandBorderColor = rubberBandBorderColor
      self.rubberBandFillColor = rubberBandFillColor
      if self.PointMapTool is not None:
         self.PointMapTool.setRubberBandColor(self.rubberBandBorderColor, self.rubberBandFillColor)

         
   # ============================================================================
   # waitForFirstFinalAxisPt
   # ============================================================================
   def waitForFirstFinalAxisPt(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FINAL_AXIS_PT
      # imposto il map tool
      self.getPointMapTool().setSelectionMode(Qad_ellipse_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_FINAL_AXIS_PT)
      if self.arc == False: # si vuole disegnare un ellisse intera
         keyWords = QadMsg.translate("Command_ELLIPSE", "Arc") + "/" + \
                    QadMsg.translate("Command_ELLIPSE", "Center") + "/" + \
                    QadMsg.translate("Command_ELLIPSE", "Foci")
         prompt = QadMsg.translate("Command_ELLIPSE", "Specify axis endpoint of ellipse or [{0}]: ").format(keyWords)
         englishKeyWords = "Arc" + "/" + "Center" + "/" + "Foci"
         keyWords += "_" + englishKeyWords
      else: # si vuole disegnare un arco di ellisse
         keyWords = QadMsg.translate("Command_ELLIPSE", "Center") + "/" + \
                    QadMsg.translate("Command_ELLIPSE", "Foci")
         prompt = QadMsg.translate("Command_ELLIPSE", "Specify axis endpoint of elliptical arc or [{0}]: ").format(keyWords)
         englishKeyWords = "Center" + "/" + "Foci"
         keyWords += "_" + englishKeyWords
      
      # si appresta ad attendere un punto o enter o una parola chiave
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
         
         
   # ============================================================================
   # waitForSecondFinalAxisPt
   # ============================================================================
   def waitForSecondFinalAxisPt(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FINAL_AXIS_PT
      # imposto il map tool
      self.getPointMapTool().axis1Pt1 = self.axis1Pt1
      self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.FIRST_FINAL_AXIS_PT_KNOWN_ASK_FOR_SECOND_FINAL_AXIS_PT)                                
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify other endpoint of axis: "))

         
   # ============================================================================
   # waitForDistanceToOtherAxis
   # ============================================================================
   def waitForDistanceToOtherAxis(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_DIST_TO_OTHER_AXIS
      # imposto il map tool
      if self.getPointMapTool().axis1Pt1 is None: # si è partiti dal centro dell'ellisse'
         self.getPointMapTool().axis1Pt1 = self.axis1Pt1
      else:
         self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().axis1Pt2 = self.axis1Pt2
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_DIST_TO_OTHER_AXIS)                                
      keyWords = QadMsg.translate("Command_ELLIPSE", "Rotation") + "/" + \
                 QadMsg.translate("Command_ELLIPSE", "Area")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify distance to other axis or [{0}]: ").format(keyWords)

      englishKeyWords = "Rotation" + "/" + "Area"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto, un numero reale o una parola chiave
      # msg, inputType, default, keyWords, valore non nullo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.FLOAT, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForRotationAroundMajorAxis
   # ============================================================================
   def waitForRotationAroundMajorAxis(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_ROTATION_ROUND_MAJOR_AXIS
      # imposto il map tool
      self.getPointMapTool().axis1Pt2 = self.axis1Pt2
      self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_ROTATION_ROUND_MAJOR_AXIS)                                

      # si appresta ad attendere un punto o un angolo
      # msg, inputType, default, keyWords, valore non nullo
      self.waitFor(QadMsg.translate("Command_ELLIPSE", "Specify rotation around major axis: "), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   None, \
                   "", QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForArea
   # ============================================================================
   def waitArea(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_AREA
      # imposto il map tool
      self.getPointMapTool().axis1Pt2 = self.axis1Pt2
      self.getPointMapTool().centerPt = self.centerPt
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_AREA)                                

      # si appresta ad attendere un valore  o un angolo
      # msg, inputType, default, keyWords, valore non nullo
      self.waitForFloat(QadMsg.translate("Command_ELLIPSE", "Specify ellipse area: "), \
                        None, \
                        QadInputModeEnum.NOT_ZERO | QadInputModeEnum.NOT_NEGATIVE)


   # ============================================================================
   # waitForStartAngle
   # ============================================================================
   def waitForStartAngle(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_START_ANGLE
      # imposto il map tool
      self.getPointMapTool().ellipse = self.ellipse
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_START_ANGLE)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Parameter")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify start angle or [{0}]: ").format(keyWords)

      englishKeyWords = "Parameter"
      keyWords += "_" + englishKeyWords

      # si appresta ad attendere un punto o un angolo o una parola chiave
      # msg, inputType, default, keyWords, valore non nullo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForEndAngle
   # ============================================================================
   def waitForEndAngle(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_END_ANGLE
      # imposto il map tool
      self.getPointMapTool().startAngle = self.startAngle
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_END_ANGLE)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Parameter") + "/" + \
                 QadMsg.translate("Command_ELLIPSE", "Included angle")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify end angle or [{0}]: ").format(keyWords)
      englishKeyWords = "Parameter" + "/" + "Included angle"
      keyWords += "_" + englishKeyWords

      # si appresta ad attendere un punto o un angolo o una parola chiave
      # msg, inputType, default, keyWords, valore non nullo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForIncludedAngle
   # ============================================================================
   def waitForIncludedAngle(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_INCLUDED_ANGLE
      # imposto il map tool
      self.getPointMapTool().startAngle = self.startAngle
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_INCLUDED_ANGLE)                                

      # si appresta ad attendere un punto o un angolo
      # msg, inputType, default, keyWords, valore non nullo
      self.waitFor(QadMsg.translate("Command_ELLIPSE", "Specify included angle for arc: "), \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.ANGLE, \
                   None, \
                   "", QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForStartParameter
   # ============================================================================
   def waitForStartParameter(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_START_PARAMETER
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_START_PARAMETER)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Angle")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify start parameter [{0}]: ").format(keyWords)
      englishKeyWords = "Angle"
      keyWords += "_" + englishKeyWords

      # si appresta ad attendere un punto o un angolo o una parola chiave
      # msg, inputType, default, keyWords, valore non nullo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForEndParameter
   # ============================================================================
   def waitForEndParameter(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_END_PARAMETER
      # imposto il map tool
      self.getPointMapTool().startAngle = self.startAngle
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_END_PARAMETER)                                

      keyWords = QadMsg.translate("Command_ELLIPSE", "Angle") + "/" + \
                 QadMsg.translate("Command_ELLIPSE", "Included angle")
      prompt = QadMsg.translate("Command_ELLIPSE", "Specify end parameter or [{0}]: ").format(keyWords)
      englishKeyWords = "Angle" + "/" + "Included angle"
      keyWords += "_" + englishKeyWords

      # si appresta ad attendere un punto o un angolo o una parola chiave
      # msg, inputType, default, keyWords, valore non nullo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS | QadInputTypeEnum.ANGLE, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)


   # ============================================================================
   # waitForCenter
   # ============================================================================
   def waitForCenter(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_CENTER
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_CENTER)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify center of ellipse: "))


   # ============================================================================
   # waitForFirstFocus
   # ============================================================================
   def waitForFirstFocus(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FOCUS
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_FIRST_FOCUS)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify first focus point of ellipse: "))


   # ============================================================================
   # waitForSecondFocus
   # ============================================================================
   def waitForSecondFocus(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FOCUS
      # imposto il map tool
      self.getPointMapTool().focus1 = self.focus1
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_SECOND_FOCUS)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify second focus point of ellipse: "))


   # ============================================================================
   # waitForPtOnEllipse
   # ============================================================================
   def waitForPtOnEllipse(self):
      self.step = QadELLIPSECommandClassStepEnum.ASK_FOR_PT_ON_ELLIPSE
      # imposto il map tool
      self.getPointMapTool().focus2 = self.focus2
      self.getPointMapTool().setMode(Qad_ellipse_maptool_ModeEnum.ASK_FOR_PT_ON_ELLIPSE)
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_ELLIPSE", "Specify a point on ellipse: "))


   def run(self, msgMapTool = False, msg = None):
      self.isValidPreviousInput = True # per gestire il comando anche in macro

      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      currLayer = None
      if self.virtualCmd == False: # se si vuole veramente salvare l'ellisse in un layer
         if self.arc == True:
            # il layer corrente deve essere editabile e di tipo linea
            currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry])
            if currLayer is None:
               self.showErr(errMsg)
               return True # fine comando
         else:
            # il layer corrente deve essere editabile e di tipo linea o poligono
            currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry])
            if currLayer is None:
               self.showErr(errMsg)
               return True # fine comando
         self.getPointMapTool().geomType = QgsWkbTypes.LineGeometry if currLayer.geometryType() == QgsWkbTypes.LineGeometry else QgsWkbTypes.PolygonGeometry
         
      if self.step == 0:     
         self.waitForFirstFinalAxisPt()
         return False # continua

         
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO FINALE DELL'ASSE (da step = 0)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FINAL_AXIS_PT: # dopo aver atteso un punto o enter o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if value is None:
            if self.plugIn.lastPoint is not None:
               value = self.plugIn.lastPoint
            else:
               return True # fine comando

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Arc") or value == "Arc":
               self.arc = True
               self.waitForFirstFinalAxisPt()
            elif value == QadMsg.translate("Command_ELLIPSE", "Center") or value == "Center":
               self.waitForCenter()
            elif value == QadMsg.translate("Command_ELLIPSE", "Foci") or value == "Foci":
               self.waitForFirstFocus()
         elif type(value) == QgsPointXY: # se é stato inserito il primo punto finale dell'asse
            self.axis1Pt1 = value
            self.plugIn.setLastPoint(value)                       
            self.waitForSecondFinalAxisPt()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO FINALE DELL'ASSE (da step = ASK_FOR_FIRST_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FINAL_AXIS_PT: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY: # se é stato inserito il secondo punto finale dell'asse
            self.axis1Pt2 = value
            if self.centerPt is None: # non è noto il centro
               self.centerPt = qad_utils.getMiddlePoint(self.axis1Pt1, self.axis1Pt2)
            else: # non è noto il primo punto dell'asse -> self.axis1Pt1
               axis1Len = qad_utils.getDistance(self.centerPt, self.axis1Pt2)
               angle = qad_utils.getAngleBy2Pts(self.axis1Pt2, self.centerPt)
               self.axis1Pt1 = qad_utils.getPolarPointByPtAngle(self.centerPt, angle, axis1Len)
               
            self.plugIn.setLastPoint(value)
            self.waitForDistanceToOtherAxis()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA DISTANZA DALL'ALTRO ASSE (da step = ASK_FOR_SECOND_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_DIST_TO_OTHER_AXIS: # dopo aver atteso un punto o enter o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Rotation") or value == "Rotation":
               self.waitForRotationAroundMajorAxis()
            elif value == QadMsg.translate("Command_ELLIPSE", "Area") or value == "Area":
               self.waitArea()            
         elif type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # se é stato inserito il primo punto finale dell'asse
               self.distToOtherAxis = qad_utils.getDistance(self.centerPt, value)
            else: # se é stato inserito un numero reale
               self.distToOtherAxis = value

            if self.ellipse.fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, self.distToOtherAxis) is not None:
               if self.arc == False: # se si vuole disegnare un'ellisse intera
                  geom = self.ellipse.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                     return True # fine comando
               else: # se si vuole disegnare un arco di ellisse
                  self.waitForStartAngle()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA ROTAZIONE INTORNO ALL'ASSE MAGGIORE (da step = ASK_FOR_SECOND_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_ROTATION_ROUND_MAJOR_AXIS: # dopo aver atteso un punto o un angolo si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # se é stato inserito un punto
               angle = qad_utils.getAngleBy2Pts(self.centerPt, value)
            else: # se é stato inserito un numero reale
               angle = value
            self.distToOtherAxis = math.fabs(qad_utils.getDistance(self.axis1Pt1, self.axis1Pt2) / 2 * math.cos(angle))

            if self.ellipse.fromAxis1FinalPtsAxis2Len(self.axis1Pt2, self.axis1Pt1, self.distToOtherAxis) is not None:
               if self.arc == False: # se si vuole disegnare un'ellisse intera
                  geom = self.ellipse.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                     return True # fine comando
               else: # se si vuole disegnare un arco di ellisse
                  self.waitForStartAngle()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'AREA DELL'ELLISSE (da step = ASK_FOR_SECOND_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_AREA: # dopo aver atteso un numeroi riavvia il comando
         if msgMapTool == True: # il valore arriva da una selezione grafica
            self.setMapTool(self.getPointMapTool()) # riattivo il maptool
            return False
         else: # il punto arriva come parametro della funzione
            value = msg

         if self.ellipse.fromAxis1FinalPtsArea(self.axis1Pt2, self.axis1Pt1, value) is not None:
            if self.arc == False: # se si vuole disegnare un'ellisse intera
               geom = self.ellipse.asGeom(currLayer.wkbType())
               if geom is not None:
                  if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                     qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                  return True # fine comando
            else: # se si vuole disegnare un arco di ellisse
               self.waitForStartAngle()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO INIZIALE DELL'ARCO DI ELLISSE
      # (da step = ASK_DIST_TO_OTHER_AXIS oppure )
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_START_ANGLE: # dopo aver atteso un punto o un angolo si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # se é stato inserito il primo punto finale dell'asse
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.startAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle
            else: # se é stato inserito un numero reale
               self.startAngle = value
           
            self.waitForEndAngle()
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Parameter") or value == "Parameter":
               self.waitForStartParameter()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO FINALE DELL'ARCO DI ELLISSE (da step = ASK_START_ANGLE)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_END_ANGLE: # dopo aver atteso un punto o un angolo si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # se é stato inserito il primo punto finale dell'asse
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.endAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle
            else: # se é stato inserito un numero reale
               self.endAngle = value

            self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
            geom = self.ellipseArc.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
           
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Parameter") or value == "Parameter":
               self.waitForEndParameter()
            elif value == QadMsg.translate("Command_ELLIPSE", "Included angle") or value == "Included angle":
               self.waitForIncludedAngle()

         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO INCLUSO (da step = ASK_END_ANGLE)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_INCLUDED_ANGLE: # dopo aver atteso un punto o un angolo si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # se é stato inserito un punto
               self.endAngle = self.startAngle + qad_utils.getAngleBy2Pts(self.ellipse.center, value)
            else: # se é stato inserito un numero reale
               self.endAngle = self.startAngle + value
            
            self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
            geom = self.ellipseArc.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
         
         return False

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO PARAMETRICO INIZIALE DELL'ARCO DI ELLISSE
      # (da step = ASK_START_ANGLE oppure )
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_START_PARAMETER: # dopo aver atteso un punto o un angolo si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # se é stato inserito il primo punto finale dell'asse
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.startAngle = self.ellipse.getAngleFromParam(qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle)
            else: # se é stato inserito un numero reale
               self.startAngle = self.ellipse.getAngleFromParam(value)
           
            self.waitForEndParameter()
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Angle") or value == "Angle":
               self.waitForStartAngle()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DELL'ANGOLO PARAMETRICO FINALE DELL'ARCO DI ELLISSE (da step = ASK_START_PARAMETER)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_END_PARAMETER: # dopo aver atteso un punto o un angolo si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY or type(value) == float:
            if type(value) == QgsPointXY: # se é stato inserito il primo punto finale dell'asse
               ellipseAngle = qad_utils.getAngleBy2Pts(self.ellipse.center, self.ellipse.majorAxisFinalPt)
               self.endAngle = self.ellipse.getAngleFromParam(qad_utils.getAngleBy2Pts(self.ellipse.center, value) - ellipseAngle)
            else: # se é stato inserito un numero reale
               self.endAngle = self.ellipse.getAngleFromParam(value)

            self.ellipseArc.set(self.ellipse.center, self.ellipse.majorAxisFinalPt, self.ellipse.axisRatio, self.startAngle, self.endAngle)
            geom = self.ellipseArc.asGeom(currLayer.wkbType())
            if geom is not None:
               if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                  qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
               return True # fine comando
           
         elif type(value) == unicode:
            if value == QadMsg.translate("Command_ELLIPSE", "Angle") or value == "Angle":
               self.waitForEndAngle()
            elif value == QadMsg.translate("Command_ELLIPSE", "Included angle") or value == "Included angle":
               self.waitForIncludedAngle()

         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL CENTRO DELL'ELLISSE (da step = ASK_FOR_FIRST_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_CENTER: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY: # se é stato inserito il centro
            self.centerPt = value
            self.axis1Pt1 = None
            self.plugIn.setLastPoint(value)
            self.waitForSecondFinalAxisPt()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO DI FUOCO DELL'ELLISSE (da step = ASK_FOR_FIRST_FINAL_AXIS_PT)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_FIRST_FOCUS: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY: # se é stato inserito il punto di fuoco
            self.focus1 = value
            self.plugIn.setLastPoint(value)
            self.waitForSecondFocus()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DI FUOCO DELL'ELLISSE (da step = ASK_FOR_FIRST_FOCUS)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_SECOND_FOCUS: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY: # se é stato inserito il punto di fuoco
            self.focus2 = value
            self.plugIn.setLastPoint(value)
            self.waitForPtOnEllipse()
         
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI UN PUNTO SULL'ELLISSE (da step = ASK_FOR_SECOND_FOCUS)
      elif self.step == QadELLIPSECommandClassStepEnum.ASK_FOR_PT_ON_ELLIPSE: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi é stato riattivato il comando che torna qui senza che il maptool
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

         if type(value) == QgsPointXY: # se é stato inserito il punto di fuoco
            self.plugIn.setLastPoint(value)
            
            if self.ellipse.fromFoci(self.focus1, self.focus2, value) is not None:
               if self.arc == False: # se si vuole disegnare un'ellisse intera
                  geom = self.ellipse.asGeom(currLayer.wkbType())
                  if geom is not None:
                     if self.virtualCmd == False: # se si vuole veramente salvare il cerchio in un layer
                        qad_layer.addGeomToLayer(self.plugIn, currLayer, self.mapToLayerCoordinates(currLayer, geom))
                     return True # fine comando                  
               else: # se si vuole disegnare un arco di ellisse
                  self.waitForStartAngle()
         
         return False


      return True                                   


