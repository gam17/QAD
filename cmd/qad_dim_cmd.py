# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comandi per generare le quotature
 
                              -------------------
        begin                : 2014-02-19
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
from qgis.core import QgsCoordinateTransform, QgsPointXY
import math


from ..qad_snapper import QadSnapTypeEnum
from ..qad_arc import QadArc
from ..qad_dim import QadDimStyleAlignmentEnum, QadDimStyles, QadDimStyle, \
                      QadDimTypeEnum, QadDimStyleTxtRotModeEnum
from .qad_dim_maptool import Qad_dim_maptool, Qad_dim_maptool_ModeEnum
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_getpoint import QadGetPointDrawModeEnum
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .qad_entsel_cmd import QadEntSelClass
from .qad_getangle_cmd import QadGetAngleClass
from ..qad_variables import QadVariables
from .. import qad_utils
from ..qad_multi_geom import getQadGeomAt, getQadGeomPartAt
from ..qad_geom_relations import getQadGeomClosestPart, QadPerpendicularity, QadIntersections

#============================================================================
# FUNZIONI GENERICHE - INIZIO
#============================================================================


#============================================================================
# FUNZIONI GENERICHE - FINE
#============================================================================


# Classe che gestisce il comando DIMLINEAR
class QadDIMLINEARCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadDIMLINEARCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMLINEAR")

   def getEnglishName(self):
      return "DIMLINEAR"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMLINEARCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimLinear.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_DIM", "Creates an horizontal or vertical linear dimension.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
            
      self.dimPt1 = QgsPointXY() # primo punto di quotatura esplicito
      self.dimPt2 = QgsPointXY() # secondo punto di quotatura esplicito
      self.dimCircle = None    # oggetto cerchio da quotare
      
      self.measure = None # misura della quota (se None viene calcolato)
      self.preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL # allineamento della linea di quota
      # leggo lo stile di quotatura corrente
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      self.forcedDimLineAlignment = None # allineamento della linea di quota forzato
      self.forcedDimLineRot = 0.0 # rotazione della linea di quota forzato
      
      _dimStyle = QadDimStyles.findDimStyle(dimStyleName)
      if _dimStyle is not None:
         self.dimStyle = QadDimStyle(_dimStyle) # ne faccio una copia perché può venire modificato dal comando
         self.dimStyle.dimType = QadDimTypeEnum.LINEAR
      else:
         self.dimStyle = None
      

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 2: # quando si é in fase di selezione entità
         return self.entSelClass.getPointMapTool(drawMode)
      # quando si é in fase di richiesta rotazione
      elif self.step == 6 or self.step == 7:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 2: # quando si é in fase di selezione entità
         return self.entSelClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta rotazione
      elif self.step == 6 or self.step == 7:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

   
   #============================================================================
   # addDimToLayers
   #============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addLinearDimToLayers(self.plugIn, self.dimPt1, self.dimPt2, \
                                                linePosPt, self.measure, self.preferredAlignment, \
                                                self.forcedDimLineRot)
   
   
   #============================================================================
   # waitForFirstPt
   #============================================================================
   def waitForFirstPt(self):
      self.step = 1
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)                                

      msg = QadMsg.translate("Command_DIM", "Specify first extension line origin or <select object>: ")
      
      # si appresta ad attendere un punto o enter      
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(msg, \
                   QadInputTypeEnum.POINT2D, \
                   None, \
                   "", QadInputModeEnum.NONE)

   
   #============================================================================
   # waitForSecondPt
   #============================================================================
   def waitForSecondPt(self):
      self.step = 3
      # imposto il map tool
      self.getPointMapTool().dimPt1 = self.dimPt1
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)                                
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_DIM", "Specify second extension line origin: "))

   
   #============================================================================
   # waitForEntsel
   #============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 2         
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select the object to dimension: ")
      # scarto la selezione di punti
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)         
      self.entSelClass.run(msgMapTool, msg)

   
   #============================================================================
   # waitForDimensionLinePos
   #============================================================================
   def waitForDimensionLinePos(self):
      self.step = 4
      # imposto il map tool      
      self.getPointMapTool().dimPt2 = self.dimPt2
      if self.getPointMapTool().dimPt1 is None: # in caso di selezione oggetto dimPt1 non era stato inizializzato
         self.getPointMapTool().dimPt1 = self.dimPt1
         self.getPointMapTool().dimCircle = self.dimCircle
      self.getPointMapTool().preferredAlignment = self.preferredAlignment
      self.getPointMapTool().forcedDimLineAlignment = self.forcedDimLineAlignment
      self.getPointMapTool().forcedDimLineRot = self.forcedDimLineRot      
      self.getPointMapTool().dimStyle = self.dimStyle      
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_LINEAR_DIM_LINE_POS)                                
      
      # si appresta ad attendere un punto o una parola chiave
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle") + "/" + \
                 QadMsg.translate("Command_DIM", "Horizontal") + "/" + \
                 QadMsg.translate("Command_DIM", "Vertical") + "/" + \
                 QadMsg.translate("Command_DIM", "Rotated")      
      prompt = QadMsg.translate("Command_DIM", "Specify dimension line location or [{0}]: ").format(keyWords)
      
      englishKeyWords = "Text" + "/" + "Angle" + "/" + "Horizontal" + "/" + "Vertical" + "/" + "Rotated"
      keyWords += "_" + englishKeyWords
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      
      

   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # fine comando
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando


      #=========================================================================
      # RICHIESTA SELEZIONE ORIGINE PRIMA LINEA DI ESTENSIONE
      if self.step == 0: # inizio del comando         
         self.waitForFirstPt()
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ORIGINE PRIMA LINEA DI ESTENSIONE (da step = 0)
      elif self.step == 1:
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = None # opzione di default None
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None:
            self.waitForEntsel(msgMapTool, msg)
         else:
            self.dimPt1.set(value.x(), value.y())
            self.waitForSecondPt()

         return False

      #=========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN'ENTITA' (da step = 1)
      elif self.step == 2:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               g = self.entSelClass.entity.getQadGeom()
               res = getQadGeomClosestPart(g, self.entSelClass.point)
               g = getQadGeomPartAt(g, res[2], res[3], res[4])
               objType = g.whatIs()
               
               if objType == "LINE" or objType == "ARC" or objType == "ELLIPSE_ARC":
                  self.dimPt1 = g.getStartPt()                  
                  self.dimPt2 = g.getEndPt()
               elif objType == "CIRCLE": # se é cerchio
                  self.dimCircle = g.copy()
                  
               self.waitForDimensionLinePos()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continua

         
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ORIGINE SECONDA LINEA DI ESTENSIONE (da step = 1)
      elif self.step == 3: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None:
            return True

         if type(value) == QgsPointXY: # se é stato inserito il secondo punto
            self.dimPt2.set(value.x(), value.y())
            self.waitForDimensionLinePos()
         
         return False 
         
               
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA POSIZIONE DELLA LINEA DI QUOTA (da step = 2 e 3)
      elif self.step == 4: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = qad_utils.getDistance(self.dimPt1, self.dimPt2)
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = 5         
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # si appresta ad attendere l'angolo di rotazione del testo
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = 6
               self.GetAngleClass.run(msgMapTool, msg)               
            elif value == QadMsg.translate("Command_DIM", "Horizontal") or value == "Horizontal":
               # allineamento della linea di quota orizzontale
               self.forcedDimLineAlignment = QadDimStyleAlignmentEnum.HORIZONTAL # allineamento della linea di quota forzato               
               self.forcedDimLineRot = 0.0             
               self.waitForDimensionLinePos()
            elif value == QadMsg.translate("Command_DIM", "Vertical") or value == "Vertical":
               # allineamento della linea di quota verticale               
               self.forcedDimLineAlignment = QadDimStyleAlignmentEnum.VERTICAL # allineamento della linea di quota forzato
               self.forcedDimLineRot = 0.0             
               self.waitForDimensionLinePos()
            elif value == QadMsg.translate("Command_DIM", "Rotated") or value == "Rotated":
               # si appresta ad attendere l'angolo di rotazionedella linea di quotatura
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension line <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.forcedDimLineRot)))
               self.GetAngleClass.angle = self.forcedDimLineRot
               self.step = 7
               self.GetAngleClass.run(msgMapTool, msg)               
               pass
         elif type(value) == QgsPointXY: # se é stato inserito il punto di posizionamento linea quota
            self.preferredAlignment = self.getPointMapTool().preferredAlignment
            self.dimPt1 = self.getPointMapTool().dimPt1
            self.dimPt2 = self.getPointMapTool().dimPt2
            self.addDimToLayers(value)
            return True # fine comando
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL TESTO (da step = 4)
      elif self.step == 5: # dopo aver atteso una stringa si riavvia il comando
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False
      
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE DEL TESTO DI QUOTA (da step = 4)
      elif self.step == 6:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False
      
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE DELLA LINEA DI QUOTA (da step = 4)
      elif self.step == 7:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.forcedDimLineRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False

      
# Classe che gestisce il comando DIMALIGNED
class QadDIMALIGNEDCommandClass(QadCommandClass):
   
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadDIMALIGNEDCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMALIGNED")

   def getEnglishName(self):
      return "DIMALIGNED"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMALIGNEDCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimAligned.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_DIM", "Creates an aligned linear dimension.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
      
      self.dimPt1 = QgsPointXY()
      self.dimPt2 = QgsPointXY()
      self.dimCircle = None    # oggetto cerchio da quotare
      
      self.measure = None # misura della quota (se None viene calcolato)
      # leggo lo stile di quotatura corrente
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      _dimStyle = QadDimStyles.findDimStyle(dimStyleName)      
      if _dimStyle is not None:
         self.dimStyle = QadDimStyle(_dimStyle) # ne faccio una copia perché può venire modificato dal comando
         self.dimStyle.dimType = QadDimTypeEnum.ALIGNED
      else:
         self.dimStyle = None
      

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 2: # quando si é in fase di selezione entità
         return self.entSelClass.getPointMapTool(drawMode)
      # quando si é in fase di richiesta rotazione
      elif self.step == 6:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == 2: # quando si é in fase di selezione entità
         return self.entSelClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta rotazione
      elif self.step == 6:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu

   
   #============================================================================
   # addDimToLayers
   #============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addAlignedDimToLayers(self.plugIn, self.dimPt1, self.dimPt2, \
                                                 linePosPt, self.measure)

      
   #============================================================================
   # waitForFirstPt
   #============================================================================
   def waitForFirstPt(self):
      self.step = 1
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.NONE_KNOWN_ASK_FOR_FIRST_PT)                                

      msg = QadMsg.translate("Command_DIM", "Specify first extension line origin or <select object>: ")
      
      # si appresta ad attendere un punto o enter      
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(msg, \
                   QadInputTypeEnum.POINT2D, \
                   None, \
                   "", QadInputModeEnum.NONE)

   
   #============================================================================
   # waitForSecondPt
   #============================================================================
   def waitForSecondPt(self):
      self.step = 3
      # imposto il map tool
      self.getPointMapTool().dimPt1 = self.dimPt1
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_PT_KNOWN_ASK_FOR_SECOND_PT)                                
      # si appresta ad attendere un punto
      self.waitForPoint(QadMsg.translate("Command_DIM", "Specify second extension line origin: "))

   
   #============================================================================
   # waitForEntsel
   #============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = 2         
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select the object to dimension: ")
      # scarto la selezione di punti
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)         
      self.entSelClass.run(msgMapTool, msg)

   
   #============================================================================
   # waitForDimensionLinePos
   #============================================================================
   def waitForDimensionLinePos(self):
      self.step = 4
      # imposto il map tool      
      self.getPointMapTool().dimPt2 = self.dimPt2
      if self.getPointMapTool().dimPt1 is None: # in caso di selezione oggetto dimPt1 non era stato inizializzato
         self.getPointMapTool().dimPt1 = self.dimPt1
         self.getPointMapTool().dimCircle = self.dimCircle
      self.getPointMapTool().dimStyle = self.dimStyle      
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ALIGNED_DIM_LINE_POS)                                
      
      # si appresta ad attendere un punto o una parola chiave
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle")      
      prompt = QadMsg.translate("Command_DIM", "Specify dimension line location or [{0}]: ").format(keyWords)
      englishKeyWords = "Text" + "/" + "Angle"
      keyWords += "_" + englishKeyWords
      
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      
      

   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # fine comando
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando


      #=========================================================================
      # RICHIESTA SELEZIONE ORIGINE PRIMA LINEA DI ESTENSIONE
      if self.step == 0: # inizio del comando         
         self.waitForFirstPt()
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ORIGINE PRIMA LINEA DI ESTENSIONE (da step = 0)
      elif self.step == 1:
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = None # opzione di default None
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None:
            self.waitForEntsel(msgMapTool, msg)
         else:
            self.dimPt1.set(value.x(), value.y())
            self.waitForSecondPt()

         return False

      #=========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN'ENTITA' (da step = 1)
      elif self.step == 2:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               g = self.entSelClass.entity.getQadGeom()
               res = getQadGeomClosestPart(g, self.entSelClass.point)
               g = getQadGeomPartAt(g, res[2], res[3], res[4])
               objType = g.whatIs()
               
               if objType == "LINE" or objType == "ARC" or objType == "ELLIPSE_ARC":
                  self.dimPt1 = g.getStartPt()                  
                  self.dimPt2 = g.getEndPt()
               elif objType == "CIRCLE": # se é cerchio
                  self.dimCircle = g.copy()
                  l = QadLine().set(self.dimCircle.center, self.entSelClass.point)
                  intPts = QadIntersections.infinityLineWithCircle(l, self.dimCircle)
                  if len(intPts) == 2:
                     self.dimPt1 = intPts[0]
                     self.dimPt2 = intPts[1]                     
                  
               self.waitForDimensionLinePos()
               return False
            else:
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continua


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ORIGINE SECONDA LINEA DI ESTENSIONE (da step = 1)
      elif self.step == 3: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if value is None:
            return True

         if type(value) == QgsPointXY: # se é stato inserito il secondo punto
            self.dimPt2.set(value.x(), value.y())
            self.waitForDimensionLinePos()
         
         return False 
         
               
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA POSIZIONE DELLA LINEA DI QUOTA (da step = 2 e 3)
      elif self.step == 4: # dopo aver atteso un punto o un numero reale si riavvia il comando
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = qad_utils.getDistance(self.dimPt1, self.dimPt2)
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = 5         
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # si appresta ad attendere l'angolo di rotazione del testo
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = 6
               self.GetAngleClass.run(msgMapTool, msg)               
         elif type(value) == QgsPointXY: # se é stato inserito il punto di posizionamento linea quota
            self.dimPt1 = self.getPointMapTool().dimPt1
            self.dimPt2 = self.getPointMapTool().dimPt2
            self.addDimToLayers(value)
            return True # fine comando
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL TESTO (da step = 4)
      elif self.step == 5: # dopo aver atteso una stringa si riavvia il comando
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE DEL TESTO DI QUOTA (da step = 4)
      elif self.step == 6:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False


# QadDIMARCCommandClassStepEnum class.
#===============================================================================
class QadDIMARCCommandClassStepEnum():
   START                = 0 # deve essere = 0 perchè è l'inizio del comando
   ASK_FOR_ENTSEL       = 1 # richiede la selezione di un'entità
   ASK_FOR_MAIN_OPTIONS = 2 # richiede di selezionare un'opzione
   ASK_FOR_TEXT_VALUE   = 3 # richiede il valore del testo della quota
   ASK_FOR_TEXT_ROT     = 4 # richiede la rotazione del testo della quota
   ASK_FOR_1PT_ARC      = 5 # richiede il primo punto dell'arco
   ASK_FOR_2PT_ARC      = 6 # richiede il secondo punto dell'arco


# Classe che gestisce il comando DIMARC
class QadDIMARCCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadDIMARCCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMARC")

   def getEnglishName(self):
      return "DIMARC"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMARCCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimArc.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_DIM", "Creates an arc length dimension.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
      self.dimPt1 = QgsPointXY()
      self.dimPt2 = QgsPointXY()
      self.dimArc = None    # oggetto arco da quotare
      self.dimPartialArc = QadArc()
      self.leader = False # opzione disponibile solo per archi > 90 gradi 
            
      self.measure = None # misura della quota (se None viene calcolato)
      # leggo lo stile di quotatura corrente
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      self.dimStyle = QadDimStyles.findDimStyle(dimStyleName)
      if self.dimStyle is not None:
         self.dimStyle.dimType = QadDimTypeEnum.ARC_LENTGH
      

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL: # quando si é in fase di selezione entità
         return self.entSelClass.getPointMapTool(drawMode)
      # quando si é in fase di richiesta rotazione
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL: # quando si é in fase di selezione entità
         return self.entSelClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta rotazione
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   #============================================================================
   # setArc
   #============================================================================
   def setArc(self, entity, point):
      """
      Setta self.dimArc che definisce l'arco da quotare
      """
      qadGeom = entity.getQadGeom()
      """
      la funzione ritorna una lista con 
      (<minima distanza>
       <punto più vicino>
       <indice della geometria più vicina>
       <indice della sotto-geometria più vicina>
       <indice della parte della sotto-geometria più vicina>
       <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
       -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
       -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
       )
      """
      dummy = getQadGeomClosestPart(qadGeom, point)
      # ritorna la sotto-geometria
      subGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
      
      gType = subGeom.whatIs()
      if gType == "POLYLINE":
         subGeom = subGeom.getLinearObjectAt(dummy[4])
         gType = subGeom.whatIs()
      
      if gType == "ARC":
         self.dimArc = subGeom
         self.dimPartialArc.set(self.dimArc.center, self.dimArc.radius, self.dimArc.startAngle, self.dimArc.endAngle)
         return True
      else:
         return False


   #============================================================================
   # getPartialPtOnArc
   #============================================================================
   def getPartialPtOnArc(self, pt):
      """
      calcola il punto sull'arco più vicino a pt che è un punto scelto dall'utente
      """
      
      perpPts = QadPerpendicularity.fromPointToArc(pt, self.dimArc)
      if len(perpPts) == 0: # cerco il punto più vicino a pt1 tra quello iniziale e finale
         startPt = self.dimArc.getStartPt()
         endPt = self.dimArc.getEndPt()
         if qad_utils.getDistance(startPt, pt) <= qad_utils.getDistance(endPt, pt):
            return startPt
         else:
            return endPt
      elif len(perpPts) == 1:
         return perpPts[0]
      elif len(perpPts) == 2: # cerco il punto più vicino a pt1
         if qad_utils.getDistance(perpPts[0], pt) <= qad_utils.getDistance(perpPts[1], pt):
            return perpPts[0]
         else:
            return perpPts[1]

      return None


   #============================================================================
   # setPartialArc
   #============================================================================
   def setPartialArc(self):
      """
      Calcola l'arco parziale di dimArc che ha i punti finali in dimPt1 e dimPt2
      """
      self.dimPartialArc.setEndAngleByPt(self.dimPt1)
      l1 = self.dimPartialArc.length()
      self.dimPartialArc.setEndAngleByPt(self.dimPt2)
      l2 = self.dimPartialArc.length()
      
      if l1 > l2: # se dimPt1 è più lontano di dimPt2 dal punto iniziale dell'arco
         self.dimPartialArc.setEndAngleByPt(self.dimPt1)
         self.dimPartialArc.setStartAngleByPt(self.dimPt2)
      else: # se dimPt1 è più vicino di dimPt2 dal punto iniziale dell'arco
         self.dimPartialArc.setStartAngleByPt(self.dimPt1)


   #============================================================================
   # addDimToLayers
   #============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addArcDimToLayers(self.plugIn, self.dimPartialArc, \
                                             linePosPt, self.measure, self.leader)

   
   #============================================================================
   # waitForEntsel
   #============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select arc or polyline arc segment: ")
      # scarto la selezione di punti e delle quote
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)
      self.entSelClass.run(msgMapTool, msg)

   
   #============================================================================
   # waitForDimensionLinePos
   #============================================================================
   def waitForDimensionLinePos(self):
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS
      # imposto il map tool      
      self.getPointMapTool().dimArc = self.dimPartialArc
      self.getPointMapTool().dimStyle = self.dimStyle
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.FIRST_SECOND_PT_KNOWN_ASK_FOR_ARC_DIM_LINE_POS)
      
      # si appresta ad attendere un punto o una parola chiave
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle") + "/" + \
                 QadMsg.translate("Command_DIM", "Partial")
      englishKeyWords = "Text" + "/" + "Angle" + "/" + "Partial"
      
      # se l'angolo dell'arco è > 90 gradi si usa anche l'opzione direttrice
      if self.dimArc.totalAngle() > math.pi / 2:
         if self.leader == False:
            keyWords = keyWords + "/" + QadMsg.translate("Command_DIM", "Leader")
            englishKeyWords = englishKeyWords + "/" + "Leader"
         else:
            keyWords = keyWords + "/" + QadMsg.translate("Command_DIM", "No leader")
            englishKeyWords = englishKeyWords + "/" + "No leader"
         
      prompt = QadMsg.translate("Command_DIM", "Specify dimension location or [{0}]: ").format(keyWords)
      keyWords += "_" + englishKeyWords

      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      
      

   #============================================================================
   # waitForFirstPt
   #============================================================================
   def waitForFirstPt(self):
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_1PT_ARC
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC)

      msg = QadMsg.translate("Command_DIM", "Specify first point on the arc: ")
      
      # si appresta ad attendere un punto
      self.waitForPoint(msg)
      

   #============================================================================
   # waitForSecondPt
   #============================================================================
   def waitForSecondPt(self):
      self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_2PT_ARC
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_PARTIAL_ARC_PT_FOR_DIM_ARC)

      msg = QadMsg.translate("Command_DIM", "Specify second point on the arc: ")
      
      # si appresta ad attendere un punto
      self.waitForPoint(msg)


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # fine comando
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando

      if self.step == QadDIMARCCommandClassStepEnum.START:
         self.waitForEntsel(msgMapTool, msg)
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN'ENTITA'
      if self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_ENTSEL:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               if self.setArc(self.entSelClass.entity, self.entSelClass.point) == True:
                  self.waitForDimensionLinePos()
               else:
                  self.showMsg(QadMsg.translate("Command_DIM", "Select an arc or polyline arc segment."))
            else:               
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continua


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA POSIZIONE DELLA LINEA DI QUOTA
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS: # dopo aver atteso un punto o una opzione si riavvia il comando
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = self.dimPartialArc.length()
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_VALUE
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # si appresta ad attendere l'angolo di rotazione del testo
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT
               self.GetAngleClass.run(msgMapTool, msg)
            elif value == QadMsg.translate("Command_DIM", "Partial") or value == "Partial":
               self.waitForFirstPt()
            elif value == QadMsg.translate("Command_DIM", "Leader") or value == "Leader":
               self.leader = True
               self.waitForDimensionLinePos()
            elif value == QadMsg.translate("Command_DIM", "No leader") or value == "No leader":
               self.leader = False
               self.waitForDimensionLinePos()
               
         elif type(value) == QgsPointXY: # se é stato inserito il punto di posizionamento linea quota
            self.addDimToLayers(value)
            return True # fine comando
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL TESTO (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_VALUE: # dopo aver atteso una stringa si riavvia il comando
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False
      
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE DEL TESTO DI QUOTA (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False
      

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO SULL'ARCO (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_1PT_ARC: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il secondo punto
            ptOnArc = self.getPartialPtOnArc(value)
            if ptOnArc is not None:
               self.dimPt1.set(ptOnArc.x(), ptOnArc.y())

         self.waitForSecondPt()
         
         return False 
      

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO SULL'ARCO (da step = ASK_FOR_1PT_ARC)
      elif self.step == QadDIMARCCommandClassStepEnum.ASK_FOR_2PT_ARC: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  return True
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == QgsPointXY: # se é stato inserito il secondo punto
            ptOnArc = self.getPartialPtOnArc(value)
            if ptOnArc is not None:
               self.dimPt2.set(ptOnArc.x(), ptOnArc.y())
            
            self.setPartialArc()
            self.waitForDimensionLinePos()
         
         return False 


#===============================================================================
# QadDIMRADIUSCommandClassStepEnum class.
#===============================================================================
class QadDIMRADIUSCommandClassStepEnum():
   START                = 0 # deve essere = 0 perchè è l'inizio del comando
   ASK_FOR_ENTSEL       = 1 # richiede la selezione di un'entità
   ASK_FOR_MAIN_OPTIONS = 2 # richiede di selezionare un'opzione
   ASK_FOR_TEXT_VALUE   = 3 # richiede il valore del testo della quota
   ASK_FOR_TEXT_ROT     = 4 # richiede la rotazione del testo della quota


# Classe che gestisce il comando DIMRADIUS
class QadDIMRADIUSCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadDIMRADIUSCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "DIMRADIUS")

   def getEnglishName(self):
      return "DIMRADIUS"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runDIMRADIUSCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/dimRadius.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_DIM", "Creates a radius dimension for a circle or an arc.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.entSelClass = None
      self.GetAngleClass = None
      self.dimObj = None    # oggetto arco o circle da quotare
            
      self.measure = None # misura della quota (se None viene calcolato)
      # leggo lo stile di quotatura corrente
      dimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      self.dimStyle = QadDimStyles.findDimStyle(dimStyleName)
      if self.dimStyle is not None:
         self.dimStyle.dimType = QadDimTypeEnum.ARC_LENTGH
      

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.entSelClass is not None:
         self.entSelClass.entity.deselectOnLayer()
         del self.entSelClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL: # quando si é in fase di selezione entità
         return self.entSelClass.getPointMapTool(drawMode)
      # quando si é in fase di richiesta rotazione
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getPointMapTool()
      else:
         if (self.plugIn is not None):
            if self.PointMapTool is None:
               self.PointMapTool = Qad_dim_maptool(self.plugIn)
            return self.PointMapTool
         else:
            return None


   def getCurrentContextualMenu(self):
      if self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL: # quando si é in fase di selezione entità
         return self.entSelClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta rotazione
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   #============================================================================
   # setArcOrCircle
   #============================================================================
   def setArcOrCircle(self, entity, point):
      """
      Setta self.dimObj che definisce l'arco o il cerchio da quotare
      """
      qadGeom = entity.getQadGeom()
      """
      la funzione ritorna una lista con 
      (<minima distanza>
       <punto più vicino>
       <indice della geometria più vicina>
       <indice della sotto-geometria più vicina>
       <indice della parte della sotto-geometria più vicina>
       <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
       -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
       -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
       )
      """
      dummy = getQadGeomClosestPart(qadGeom, point)
      # ritorna la sotto-geometria
      subGeom = getQadGeomAt(qadGeom, dummy[2], dummy[3])
      gType = subGeom.whatIs()
      
      if gType == "ARC" or gType == "CIRCLE":
         self.dimObj = subGeom
         return True
      else:
         return False
      

   #============================================================================
   # addDimToLayers
   #============================================================================
   def addDimToLayers(self, linePosPt):
      return self.dimStyle.addRadiusDimToLayers(self.plugIn, self.dimObj, \
                                                linePosPt, self.measure)

   
   #============================================================================
   # waitForEntsel
   #============================================================================
   def waitForEntsel(self, msgMapTool, msg):
      if self.entSelClass is not None:
         del self.entSelClass
      self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL
      self.entSelClass = QadEntSelClass(self.plugIn)
      self.entSelClass.msg = QadMsg.translate("Command_DIM", "Select arc or circle: ")
      # scarto la selezione di punti e delle quote
      self.entSelClass.checkPointLayer = False
      self.entSelClass.checkLineLayer = True
      self.entSelClass.checkPolygonLayer = True
      self.entSelClass.checkDimLayers = False
      self.entSelClass.getPointMapTool().setSnapType(QadSnapTypeEnum.DISABLE)
      self.entSelClass.run(msgMapTool, msg)
      
   
   #============================================================================
   # waitForDimensionLinePos
   #============================================================================
   def waitForDimensionLinePos(self):
      self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS
      # imposto il map tool
      if self.dimObj.whatIs() == "ARC":
         self.getPointMapTool().dimArc = self.dimObj
      else:
         self.getPointMapTool().dimCircle = self.dimObj

      self.getPointMapTool().dimStyle = self.dimStyle
      self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.OBJ_KNOWN_ASK_FOR_RADIUS_DIM_LINE_POS)
      
      # si appresta ad attendere un punto o una parola chiave
      # si appresta ad attendere un punto o una parola chiave
      keyWords = QadMsg.translate("Command_DIM", "Text") + "/" + \
                 QadMsg.translate("Command_DIM", "Angle")
      englishKeyWords = "Text" + "/" + "Angle"

      prompt = QadMsg.translate("Command_DIM", "Specify dimension location or [{0}]: ").format(keyWords)
      keyWords += "_" + englishKeyWords

      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, \
                   QadInputModeEnum.NONE)                                      


   #============================================================================
   # run
   #============================================================================
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando

      if self.dimStyle is None:
         self.showMsg(QadMsg.translate("QAD", "\nDimension style not valid.\nVerify the value of DIMSTYLE variable.\n"))
         return True # fine comando
         
      errMsg = self.dimStyle.getInValidErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando
      
      errMsg = self.dimStyle.getNotGraphEditableErrMsg()
      if errMsg is not None:
         self.showMsg(errMsg)
         return True # fine comando

      if self.step == QadDIMRADIUSCommandClassStepEnum.START:
         self.waitForEntsel(msgMapTool, msg)
         return False # continua

      #=========================================================================
      # RISPOSTA ALLA SELEZIONE DI UN'ENTITA'
      if self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_ENTSEL:
         if self.entSelClass.run(msgMapTool, msg) == True:
            if self.entSelClass.entity.isInitialized():
               if self.setArcOrCircle(self.entSelClass.entity, self.entSelClass.point) == True:
                  self.waitForDimensionLinePos()
               else:
                  self.showMsg(QadMsg.translate("Command_DIM", "Select an arc or polyline arc segment."))
            else:               
               if self.entSelClass.canceledByUsr == True: # fine comando
                  return True
               self.showMsg(QadMsg.translate("QAD", "No geometries in this position."))
               self.waitForEntsel(msgMapTool, msg)
         return False # continua


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA POSIZIONE DELLA LINEA DI QUOTA
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_MAIN_OPTIONS: # dopo aver atteso un punto o una opzione si riavvia il comando
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

         if type(value) == unicode:
            if value == QadMsg.translate("Command_DIM", "Text") or value == "Text":
               prompt = QadMsg.translate("Command_DIM", "Enter dimension text <{0}>: ")
               dist = self.dimObj.radius
               self.waitForString(prompt.format(str(dist)), dist)
               self.getPointMapTool().setMode(Qad_dim_maptool_ModeEnum.ASK_FOR_TEXT)
               self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_VALUE
            elif value == QadMsg.translate("Command_DIM", "Angle") or value == "Angle":
               # si appresta ad attendere l'angolo di rotazione del testo
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                                   
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_DIM", "Specify angle of dimension text <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.dimStyle.textForcedRot)))
               self.GetAngleClass.angle = self.dimStyle.textForcedRot
               self.step = QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT
               self.GetAngleClass.run(msgMapTool, msg)
               
         elif type(value) == QgsPointXY: # se é stato inserito il punto di posizionamento linea quota
            self.addDimToLayers(value)
            return True # fine comando
            
         return False


      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL TESTO (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_VALUE: # dopo aver atteso una stringa si riavvia il comando
         if type(msg) == unicode:
            text = msg.strip()
            if len(text) > 0:
               self.measure = text
               self.getPointMapTool().measure = self.measure
         self.waitForDimensionLinePos()
            
         return False
      
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE DEL TESTO DI QUOTA (da step = ASK_FOR_MAIN_OPTIONS)
      elif self.step == QadDIMRADIUSCommandClassStepEnum.ASK_FOR_TEXT_ROT:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
               self.dimStyle.textForcedRot = self.GetAngleClass.angle 
            self.waitForDimensionLinePos()

         return False
      

