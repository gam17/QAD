# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe base per un comando
 
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
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.core import QgsPointXY, QgsGeometry, QgsCoordinateTransform, QgsProject


from ..qad_msg import QadMsg
from ..qad_utils import pointToStringFmt
from ..qad_variables import QadVariables
from ..qad_textwindow import QadInputModeEnum, QadInputTypeEnum
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPoint
from ..qad_dynamicinput import QadDynamicInputContextEnum
from ..qad_dsettings_dlg import QadDSETTINGSDialog, QadDSETTINGSTabIndexEnum
from ..qad_snapper import QadSnapTypeEnum, snapTypeEnum2Str


# Classe che gestisce un comando generico
class QadCommandClass(QObject): # derivato da QObject per gestire il metodo sender()
   def showMsg(self, msg, displayPromptAfterMsg = False):
      if self.plugIn is not None:
         self.plugIn.showMsg(msg, displayPromptAfterMsg)
         
   def showErr(self, err):
      if self.plugIn is not None:
         self.plugIn.showErr(err)

   def showInputMsg(self, inputMsg, inputType, default = None, keyWords = "", \
                    inputMode = QadInputModeEnum.NONE):
      if self.plugIn is not None:
         self.plugIn.showInputMsg(inputMsg, inputType, default, keyWords, inputMode)

      # inizializzo il menu contestuale
      self.initContextualMenu(inputType, keyWords)


   def initContextualMenu(self, inputType, keyWords):
      if self.plugIn is None:
         return
      
      if self.contextualMenu:
         del self.contextualMenu
         self.contextualMenu = None

#       if keyWords == "":
#          if self.contextualMenu:
#             del self.contextualMenu
#             self.contextualMenu = None
#          return

      self.contextualMenu = QadContextualMenuClass(self.plugIn, inputType, keyWords)


   def enterActionByContextualMenu(self):
      self.plugIn.showEvaluateMsg(None)

   
   def cancelActionByContextualMenu(self):
      self.plugIn.abortCommand()


   def showEvaluateMsgByContextualMenu(self):
      sender = self.sender()
      self.plugIn.showEvaluateMsg(sender.text())


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = QadGetPoint(self.plugIn, drawMode) # per selezione di un punto
         return self.PointMapTool
      else:
         return None

      
   def getCurrentContextualMenu(self):
      return self.contextualMenu


   def hidePointMapToolMarkers(self):
      if self.PointMapTool is not None:
         self.PointMapTool.hidePointMapToolMarkers()

   def setMapTool(self, mapTool):
      if self.plugIn is not None:
         # setto il maptool per l'input via finestra grafica
         self.plugIn.canvas.setMapTool(mapTool)
         self.plugIn.mainAction.setChecked(True)     


   def waitForPoint(self, msg = None, \
                    default = None, inputMode = QadInputModeEnum.NOT_NULL):
      if msg is None:
          msg = QadMsg.translate("QAD", "Specify point: ")
      self.setMapTool(self.getPointMapTool())
      # setto l'input via finestra di testo
      self.showInputMsg(msg, QadInputTypeEnum.POINT2D, default, "", inputMode)
      

   def waitForString(self, msg, default = None, inputMode = QadInputModeEnum.NONE):
      self.setMapTool(self.getPointMapTool())
      # setto l'input via finestra di testo
      self.showInputMsg(msg, QadInputTypeEnum.STRING, default, "", inputMode)


   def waitForInt(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # setto l'input via finestra di testo
      self.showInputMsg(msg, QadInputTypeEnum.INT, default, "", inputMode)


   def waitForLong(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # setto l'input via finestra di testo
      self.showInputMsg(msg, QadInputTypeEnum.LONG, default, "", inputMode)


   def waitForFloat(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # setto l'input via finestra di testo
      self.showInputMsg(msg, QadInputTypeEnum.FLOAT, default, "", inputMode)


   def waitForBool(self, msg, default = None, inputMode = QadInputModeEnum.NOT_NULL):
      self.setMapTool(self.getPointMapTool())
      # setto l'input via finestra di testo
      self.showInputMsg(msg, QadInputTypeEnum.BOOL, default, "", inputMode)


   def waitForSelSet(self, msg = QadMsg.translate("QAD", "Select objects: ")):
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
      self.setMapTool(self.getPointMapTool())
      self.getPointMapTool().getDynamicInput().context = QadDynamicInputContextEnum.NONE
      # setto l'input via finestra di testo
      self.showInputMsg(msg, QadInputTypeEnum.POINT2D)


   def waitFor(self, msg, inputType, default = None, keyWords = "", \
               inputMode = QadInputModeEnum.NONE):
      self.setMapTool(self.getPointMapTool())
      # setto l'input via finestra di testo
      self.showInputMsg(msg, inputType, default, keyWords, inputMode)


   def getCurrMsgFromTxtWindow(self):
      if self.plugIn is not None:
         return self.plugIn.getCurrMsgFromTxtWindow()
      else:
         return None
         
   def showEvaluateMsg(self, msg = None):
      if self.plugIn is not None:
         self.plugIn.showEvaluateMsg(msg)

   def runCommandAbortingTheCurrent(self):
      self.plugIn.runCommandAbortingTheCurrent(self.getName())
      
   def getToolTipText(self):
      text = self.getName()
      if len(self.getNote()) > 0:
         text = text + "\n\n" + self.getNote()
      return text
      
   # ============================================================================
   # funzioni da sovrascrivere con le classi ereditate da questa
   # ============================================================================
   def getName(self):
      """ impostare il nome del comando in maiuscolo """
      return ""

   def getEnglishName(self):
      """ impostare il nome del comando in inglese maiuscolo """
      return ""

   def connectQAction(self, action):
      pass     
      #action.triggered.connect(self.plugIn.runPLINECommand) ad esempio

   def getIcon(self):
      # impostare l'icona  del comando (es. QIcon(":/plugins/qad/icons/pline.svg"))
      # ricordarsi di inserire l'icona in resources.qrc e di ricompilare le risorse
      return None

   def getNote(self):
      """ impostare le note esplicative del comando """
      return ""
   
   def __init__(self, plugIn):
      QObject.__init__(self)      
      self.plugIn       = plugIn
      self.PointMapTool = None
      self.step         = 0      
      self.isValidPreviousInput = True # per gestire il comando anche in macro
      self.contextualMenu = None
      
      # inizializzare tutti i maptool necessari al comando
      # esempio di struttura di un comando che richiede
      # 1) un punto
      # self.mapTool = QadGetPoint(self.plugIn) # per selezione di un punto


   def __del__(self):
      """ distruttore """
      self.hidePointMapToolMarkers()
      
      if self.PointMapTool:
         self.PointMapTool.removeItems()
         del self.PointMapTool
         self.PointMapTool = None
         
      if self.contextualMenu:
         #QObject.disconnect(enterAction, SIGNAL("triggered()"), self.enterActionByContextualMenu)

         del self.contextualMenu
         self.contextualMenu = None
      
      
   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return None
   
   def run(self, msgMapTool = False, msg = None):
      """
      Esegue il comando. 
      - msgMapTool; se True significa che arriva un valore da MapTool del comando
                    se false significa che il valore é nel parametro msg
      - msg;        valore in input al comando (usato quando msgMapTool = False)
      
      ritorna True se il comando é terminato altrimenti False
      """
      # esempio di struttura di un comando che richiede
      # 1) un punto
      if self.step == 0: # inizio del comando
         self.waitForPoint() # si appresta ad attendere un punto
         self.step = self.step + 1
         return False
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               self.setMapTool(self.getPointMapTool()) # riattivo il maptool
               return False

            pt = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            pt = msg
            
         return True

   def mapToLayerCoordinates(self, layer, point_geom):
      # transform point o geometry coordinates from output CRS to layer's CRS 
      if self.plugIn is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.plugIn.canvas.mapSettings().mapToLayerCoordinates(layer, point_geom)
      
      fromCrs = self.plugIn.canvas.mapSettings().destinationCrs()
      toCrs = layer.crs()
         
      if type(point_geom) == QgsGeometry:
         if fromCrs == toCrs:
            return QgsGeometry(point_geom)
         
         # trasformo la geometria nel crs del canvas per lavorare con coordinate piane xy
         coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      elif (type(point_geom) == list or type(point_geom) == tuple): # lista di punti o di geometrie
         res = []
         if fromCrs == toCrs:
            for pt in point_geom:
               if type(pt) == QgsPointXY:
                  res.append(QgsPointXY(pt))
               elif type(pt) == QgsGeometry:
                  res.append(QgsGeometry(pt))
            return res
            
         coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         for pt in point_geom:
            if type(pt) == QgsPointXY:
               res.append(coordTransform.transform(pt))
            elif type(pt) == QgsGeometry:
               g = QgsGeometry(pt)
               g.transform(coordTransform)
               res.append(g)
         return res
      else:
         return None

   def layerToMapCoordinates(self, layer, point_geom):
      # transform point o geometry coordinates from layer's CRS to output CRS 
      if self.plugIn is None:
         return None
      if type(point_geom) == QgsPointXY:
         return self.plugIn.canvas.mapSettings().layerToMapCoordinates(layer, point_geom)
      elif type(point_geom) == QgsGeometry:
         # trasformo la geometria nel crs del canvas per lavorare con coordinate piane xy
         coordTransform = QgsCoordinateTransform(layer.crs(), \
                                                 self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 QgsProject.instance())
         g = QgsGeometry(point_geom)
         g.transform(coordTransform)
         return g
      elif (type(point_geom) == list or type(point_geom) == tuple): # lista di punti o di geometrie
         coordTransform = QgsCoordinateTransform(self.plugIn.canvas.mapSettings().destinationCrs(), \
                                                 layer.crs(), \
                                                 QgsProject.instance())
         res = []
         for pt in point_geom:
            if type(pt) == QgsPointXY:
               res.append(coordTransform.transform(pt))
            elif type(point_geom) == QgsGeometry:
               g = QgsGeometry(point_geom)
               g.transform(coordTransform)
               res.append(g)
         return res
      else:
         return None


# Classe che gestisce il menu contestuale dei comandi di Qad
class QadContextualMenuClass(QMenu):

   def __init__(self, plugIn, inputType, keyWords):
      self.plugIn = plugIn
      QMenu.__init__(self, self.plugIn.canvas)
      self.connections = []
      self.localEnglishKeyWords = []
      self.localKeyWords = []
      self.initActions(inputType, keyWords)

   def __del__(self):
      """ distruttore """
      self.delActions()


   def delActions(self):
      # cancello e disconnetto tutte le azioni per gli eventi
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.disconnect(slot)
      del self.connections[:]


   def initActions(self, inputType, keyWords):
      self.delActions()
         
      msg = QadMsg.translate("ContextualCmdMenu", "Enter")
      action = QAction(msg, self)
      self.addAction(action)
      self.connections.append([action, self.enterActionByContextualMenu])

      msg = QadMsg.translate("ContextualCmdMenu", "Cancel")
      action = QAction(msg, self)
      self.addAction(action)
      self.connections.append([action, self.cancelActionByContextualMenu])
         
      if inputType & QadInputTypeEnum.POINT2D or inputType & QadInputTypeEnum.POINT3D:
         msg = QadMsg.translate("ContextualCmdMenu", "Recent Input")
         recentPtsMenu = self.addMenu(msg)
         
         ptsHistory = self.plugIn.ptsHistory
         ptsHistoryLen = len(ptsHistory)
         i = ptsHistoryLen - 1
         cmdInputHistoryMax = QadVariables.get(QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX"))
         # ciclo sulla storia degli ultimi punti usati
         while i >= 0 and (ptsHistoryLen - i) <= cmdInputHistoryMax:
            strPt = pointToStringFmt(ptsHistory[i])
            i = i - 1
            action = QAction(strPt, recentPtsMenu)
            recentPtsMenu.addAction(action)
            self.connections.append([action, self.showEvaluateMsgByContextualMenu])
                    
      # ciclo sulle opzioni correnti del comando in uso
      if len(keyWords) > 0:
         # inizializzo la lista di parole chiave contestuale al comando corrente (lingua locale)
         # carattere separatore tra le parole chiave in lingua locale e quelle in inglese 
         self.localEnglishKeyWords = keyWords.split("_")
         self.localKeyWords = self.localEnglishKeyWords[0].split("/") # carattere separatore delle parole chiave

         self.addSeparator()
         for keyWord in self.localKeyWords:
            action = QAction(keyWord, self)
            self.addAction(action)
            self.connections.append([action, self.showEvaluateMsgByContextualMenu])
      else: # non ci sono opzioni
         del self.localEnglishKeyWords[:] # svuoto la lista
         del self.localKeyWords[:] # svuoto la lista

      if inputType & QadInputTypeEnum.POINT2D or inputType & QadInputTypeEnum.POINT3D:
         self.addSeparator()
         osnapMenu = QadOsnapContextualMenuClass(self.plugIn)
         self.addMenu(osnapMenu)

      # creo tutte le connessioni per gli eventi
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.connect(slot)


   def enterActionByContextualMenu(self):
      actualCmd = self.plugIn.QadCommands.actualCommand
      if actualCmd is not None:
         pointMapTool = actualCmd.getPointMapTool()
         if pointMapTool is not None:
            dynInput = pointMapTool.getDynamicInput()
            if dynInput is not None:
               if dynInput.anyLockedValueEdit() == True:
                  if dynInput.refreshResult() == True:
                     dynInput.showEvaluateMsg(dynInput.resStr)
                     return
               
      self.plugIn.showEvaluateMsg(None)

   
   def cancelActionByContextualMenu(self):
      self.plugIn.abortCommand()


   def showEvaluateMsgByContextualMenu(self):
      sender = self.sender()
      self.plugIn.showEvaluateMsg(sender.text())


# Classe che gestisce il menu contestuale di osnap dei comandi di Qad
class QadOsnapContextualMenuClass(QMenu):

   def __init__(self, plugIn):
      self.plugIn = plugIn
      title = QadMsg.translate("ContextualCmdMenu", "Snap Overrides")
      QMenu.__init__(self, title, self.plugIn.canvas)
      self.connections = []
      self.initActions()

   def __del__(self):
      """ distruttore """
      self.delActions()


   def delActions(self):
      # cancello e disconnetto tutte le azioni per gli eventi
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.disconnect(slot)
      del self.connections[:]


   def initActions(self):
      self.delActions()

      msg = QadMsg.translate("Snap", "Midpoint between 2 points")
      icon = QIcon(":/plugins/qad/icons/osnap_mid2p.svg")
      if icon is None:
         M2PAction = QAction(msg, self)
      else:
         M2PAction = QAction(icon, msg, self)
      self.addAction(M2PAction)
      self.connections.append([M2PAction, self.addM2PActionByPopupMenu])
      
      self.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_endLine.svg")
      if icon is None:
         addEndLineSnapTypeAction = QAction(msg, self)
      else:
         addEndLineSnapTypeAction = QAction(icon, msg, self)
      self.addAction(addEndLineSnapTypeAction)
      self.connections.append([addEndLineSnapTypeAction, self.addEndLineSnapTypeByPopupMenu])
      
      msg = QadMsg.translate("DSettings_Dialog", "Segment Start / End")
      icon = QIcon(":/plugins/qad/icons/osnap_end.svg")
      if icon is None:
         addEndSnapTypeAction = QAction(msg, self)
      else:
         addEndSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addEndSnapTypeAction)
      self.connections.append([addEndSnapTypeAction, self.addEndSnapTypeByPopupMenu])
      
      msg = QadMsg.translate("DSettings_Dialog", "Middle point")
      icon = QIcon(":/plugins/qad/icons/osnap_mid.svg")
      if icon is None:
         addMidSnapTypeAction = QAction(msg, self)
      else:
         addMidSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addMidSnapTypeAction)
      self.connections.append([addMidSnapTypeAction, self.addMidSnapTypeByPopupMenu])
      
      msg = QadMsg.translate("DSettings_Dialog", "Intersection")
      icon = QIcon(":/plugins/qad/icons/osnap_int.svg")
      if icon is None:
         addIntSnapTypeAction = QAction(msg, self)
      else:
         addIntSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addIntSnapTypeAction)
      self.connections.append([addIntSnapTypeAction, self.addIntSnapTypeByPopupMenu])
      
      msg = QadMsg.translate("DSettings_Dialog", "Intersection on extension")
      icon = QIcon(":/plugins/qad/icons/osnap_extInt.svg")
      if icon is None:
         addExtIntSnapTypeAction = QAction(msg, self)
      else:
         addExtIntSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addExtIntSnapTypeAction)
      self.connections.append([addExtIntSnapTypeAction, self.addExtIntSnapTypeByPopupMenu])
      
      msg = QadMsg.translate("DSettings_Dialog", "Extend")
      icon = QIcon(":/plugins/qad/icons/osnap_ext.svg")
      if icon is None:
         addExtSnapTypeAction = QAction(msg, self)
      else:
         addExtSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addExtSnapTypeAction)
      self.connections.append([addExtSnapTypeAction, self.addExtSnapTypeByPopupMenu])

      self.addSeparator()
     
      msg = QadMsg.translate("DSettings_Dialog", "Center")
      icon = QIcon(":/plugins/qad/icons/osnap_cen.svg")
      if icon is None:
         addCenSnapTypeAction = QAction(msg, self)
      else:
         addCenSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addCenSnapTypeAction)
      self.connections.append([addCenSnapTypeAction, self.addCenSnapTypeByPopupMenu])
     
      msg = QadMsg.translate("DSettings_Dialog", "Quadrant")
      icon = QIcon(":/plugins/qad/icons/osnap_qua.svg")
      if icon is None:
         addQuaSnapTypeAction = QAction(msg, self)
      else:
         addQuaSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addQuaSnapTypeAction)
      self.connections.append([addQuaSnapTypeAction, self.addQuaSnapTypeByPopupMenu])
     
      msg = QadMsg.translate("DSettings_Dialog", "Tangent")
      icon = QIcon(":/plugins/qad/icons/osnap_tan.svg")
      if icon is None:
         addTanSnapTypeAction = QAction(msg, self)
      else:
         addTanSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addTanSnapTypeAction)
      self.connections.append([addTanSnapTypeAction, self.addTanSnapTypeByPopupMenu])

      self.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Perpendicular")
      icon = QIcon(":/plugins/qad/icons/osnap_per.svg")
      if icon is None:
         addPerSnapTypeAction = QAction(msg, self)
      else:
         addPerSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addPerSnapTypeAction)     
      self.connections.append([addPerSnapTypeAction, self.addPerSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Parallel")
      icon = QIcon(":/plugins/qad/icons/osnap_par.svg")
      if icon is None:
         addParSnapTypeAction = QAction(msg, self)
      else:
         addParSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addParSnapTypeAction)     
      self.connections.append([addParSnapTypeAction, self.addParSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Node")
      icon = QIcon(":/plugins/qad/icons/osnap_nod.svg")
      if icon is None:
         addNodSnapTypeAction = QAction(msg, self)
      else:
         addNodSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addNodSnapTypeAction)     
      self.connections.append([addNodSnapTypeAction, self.addNodSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Near")
      icon = QIcon(":/plugins/qad/icons/osnap_nea.svg")
      if icon is None:
         addNeaSnapTypeAction = QAction(msg, self)
      else:
         addNeaSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addNeaSnapTypeAction)     
      self.connections.append([addNeaSnapTypeAction, self.addNeaSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "Progressive")
      icon = QIcon(":/plugins/qad/icons/osnap_pr.svg")
      if icon is None:
         addPrSnapTypeAction = QAction(msg, self)
      else:
         addPrSnapTypeAction = QAction(icon, msg, self)        
      self.addAction(addPrSnapTypeAction)     
      self.connections.append([addPrSnapTypeAction, self.addPrSnapTypeByPopupMenu])

      msg = QadMsg.translate("DSettings_Dialog", "None")
      icon = QIcon(":/plugins/qad/icons/osnap_disable.svg")
      if icon is None:
         setSnapTypeToDisableAction = QAction(msg, self)
      else:
         setSnapTypeToDisableAction = QAction(icon, msg, self)        
      self.addAction(setSnapTypeToDisableAction)     
      self.connections.append([setSnapTypeToDisableAction, self.setSnapTypeToDisableByPopupMenu])

      self.addSeparator()

      msg = QadMsg.translate("DSettings_Dialog", "Object snap settings...")
      icon = QIcon(":/plugins/qad/icons/dsettings.svg")
      if icon is None:
         DSettingsAction = QAction(msg, self)
      else:
         DSettingsAction = QAction(icon, msg, self)        
      self.addAction(DSettingsAction)     
      self.connections.append([DSettingsAction, self.showDSettingsByPopUpMenu])

      # creo tutte le connessioni per gli eventi
      for connection in self.connections:
         action = connection[0]
         slot = connection[1]
         action.triggered.connect(slot)


   # ============================================================================
   # addSnapTypeByPopupMenu
   # ============================================================================
   def addSnapTypeByPopupMenu(self, _snapType):
      # la funzione deve impostare lo snap ad oggetto solo temporaneamente
      str = snapTypeEnum2Str(_snapType)
      self.plugIn.showEvaluateMsg(str)
      return
#       value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
#       if value & QadSnapTypeEnum.DISABLE:
#          value =  value - QadSnapTypeEnum.DISABLE      
#       QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | _snapType)
#       QadVariables.save()
#       self.plugIn.refreshCommandMapToolSnapType()
         
   def addM2PActionByPopupMenu(self):
      self.plugIn.showEvaluateMsg("_M2P")      
   def addEndLineSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END_PLINE)
   def addEndSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.END)
   def addMidSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.MID)
   def addIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.INT)      
   def addExtIntSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT_INT)
   def addExtSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.EXT)   
   def addCenSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.CEN)      
   def addQuaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.QUA)
   def addTanSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.TAN)
   def addPerSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PER)
   def addParSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PAR)
   def addNodSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NOD)
   def addNeaSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.NEA)
   def addPrSnapTypeByPopupMenu(self):
      self.addSnapTypeByPopupMenu(QadSnapTypeEnum.PR)

   def setSnapTypeToDisableByPopupMenu(self):
      value = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
      QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), value | QadSnapTypeEnum.DISABLE)
      QadVariables.save()      
      self.plugIn.refreshCommandMapToolSnapType()

   def showDSettingsByPopUpMenu(self):
      d = QadDSETTINGSDialog(self.plugIn)
      d.exec_()
      self.plugIn.refreshCommandMapToolSnapType()
      self.plugIn.refreshCommandMapToolAutoSnap()
      self.plugIn.refreshCommandMapToolDynamicInput()
