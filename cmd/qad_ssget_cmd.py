# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando da inserire in altri comandi per la selezione di un gruppo di feature
 
                              -------------------
        begin                : 2013-05-22
        copyright            : iiiii
        email                : hhhhh
        developers           : bbbbb aaaaa ggggg
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
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


from ..qad_variables import QadVariables
from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from ..qad_entity import QadEntitySet, getSelSet
from ..qad_dim import QadDimStyles
from ..qad_getpoint import QadGetPointDrawModeEnum, QadGetPointSelectionModeEnum
from .qad_pline_cmd import QadPLINECommandClass
from .qad_circle_cmd import QadCIRCLECommandClass, QadCircle
from .qad_mpolygon_cmd import QadMPOLYGONCommandClass
from ..qad_dynamicinput import QadDynamicInputContextEnum
# ho dovuto spostare in fondo questo import perché qad_mbuffer_cmd fa l'import di qad_ssget_cmd
#from qad_mbuffer_cmd import QadMBUFFERCommandClass
from ..qad_utils import getVisibleVectorLayers, distMapToLayerCoordinates
from ..qad_rubberband import getColorForCrossingSelectionArea, \
                             getColorForWindowSelectionArea

# ===============================================================================
# QadSSGetClass
# ===============================================================================
class QadSSGetClass(QadCommandClass):
# Classe che gestisce la selezione di oggetti geometrici

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadSSGetClass(self.plugIn)

   def __init__(self, plugIn):
      self.init(plugIn)

   def __del__(self):
      QadCommandClass.__del__(self)
      #self.entitySet.deselectOnLayer()
      if self.PLINECommand is not None: del self.PLINECommand
      if self.CIRCLECommand is not None: del self.CIRCLECommand
      if self.MPOLYGONCommand is not None: del self.MPOLYGONCommand
      if self.MBUFFERCommand is not None: del self.MBUFFERCommand
      if self.SSGetClass is not None: del self.SSGetClass


   def init(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.AddOnSelection = True # se = False significa remove
      self.entitySet = QadEntitySet()
      self.points = []
      self.currSelectionMode = ""
      # opzioni per limitare gli oggetti da selezionare
      self.onlyEditableLayers = False
      self.checkPointLayer = True
      self.checkLineLayer = True
      self.checkPolygonLayer = True
      self.checkDimLayers = True # include tutte le features che compongono le quotature selezionate
      
      self.help = False
      # se SingleSelection = True viene selezionato il primo oggetto o gruppo di oggetti indicato,
      # senza che vengano richieste altre selezioni.      
      self.SingleSelection = False
      self.pickAdd = QadVariables.get(QadMsg.translate("Environment variables", "PICKADD"))
      
      # se exitAfterSelection = True il comando viene terminato dopo una qualunque selezione 
      # indipendentemente che sia stato selezionato o meno un oggetto o gruppo di oggetti.
      # usato da QadVirtualSelCommandClass
      self.exitAfterSelection = False
      
      # selezione degli oggetti aggiunti più recentemente al gruppo di selezione (x opzione annulla)
      self.lastEntitySet = QadEntitySet()
      self.PLINECommand = None
      self.CIRCLECommand = None
      self.MPOLYGONCommand = None
      self.MBUFFERCommand = None
      self.SSGetClass = None

   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      if self.step == 4: # quando si é in fase di disegno linea
         return self.PLINECommand.getPointMapTool(drawMode)
      elif self.step == 5: # quando si é in fase di disegno cerchio
         return self.CIRCLECommand.getPointMapTool(drawMode)
      elif self.step == 6: # quando si é in fase di selezione entità
         return self.SSGetClass.getPointMapTool(drawMode)
      elif self.step == 7: # quando si é in fase di disegno polygono
         return self.MPOLYGONCommand.getPointMapTool(drawMode)
      elif self.step == 8: # quando si é in fase di disegno buffer 
         return self.MBUFFERCommand.getPointMapTool(drawMode)      
      else:
         ptMapTool = QadCommandClass.getPointMapTool(self, drawMode)
         #ptMapTool.setSnapType(QadSnapTypeEnum.DISABLE) non capisco perchè
         ptMapTool.setOrthoMode(0)
         return ptMapTool


   def getCurrentContextualMenu(self):
      if self.step == 4: # quando si é in fase di disegno linea
         return self.PLINECommand.getCurrentContextualMenu()
      elif self.step == 5: # quando si é in fase di disegno cerchio
         return self.CIRCLECommand.getCurrentContextualMenu()
      elif self.step == 6: # quando si é in fase di selezione entità
         return None # return self.SSGetClass.getCurrentContextualMenu()
      elif self.step == 7: # quando si é in fase di disegno polygono
         return self.MPOLYGONCommand.getCurrentContextualMenu()
      elif self.step == 8: # quando si é in fase di disegno buffer 
         return self.MBUFFERCommand.getCurrentContextualMenu()     
      else:
         return self.contextualMenu

   
   # ============================================================================
   # getLayersToCheck
   # ============================================================================
   def getLayersToCheck(self):
      layerList = []
      for layer in getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
         # considero solo i layer vettoriali che sono filtrati per tipo
         if ((layer.geometryType() == QgsWkbTypes.PointGeometry and self.checkPointLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.LineGeometry and self.checkLineLayer == True) or \
             (layer.geometryType() == QgsWkbTypes.PolygonGeometry and self.checkPolygonLayer == True)) and \
             (self.onlyEditableLayers == False or layer.isEditable()):
            # se devo includere i layers delle quotature
            if self.checkDimLayers == True or \
               len(QadDimStyles.getDimListByLayer(layer)) == 0:
               layerList.append(layer)
         
      return layerList


   # ============================================================================
   # showMsgOnAddRemove
   # ============================================================================
   def showMsgOnAddRemove(self, found):
      msg = QadMsg.translate("Command_SSGET", " found {0}, total {1}")
      self.showMsg(msg.format(found, self.entitySet.count()), False) # non ripete il prompt 2016


   # ============================================================================
   # elaborateEntity
   # ============================================================================
   def elaborateEntity(self, entity, shiftKey):
      if self.AddOnSelection == True: # aggiungi al gruppo di selezione
         if shiftKey: # se la selezione é avvenuta con shift premuto
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               if self.entitySet.containsEntity(entity): # se l'entità era già stata selezionata
                  self.AddRemoveEntity(entity, False) # rimuovo l'entità
               else:
                  self.AddRemoveEntity(entity, True) # aggiungo l'entità
            else:
               self.AddRemoveEntity(entity, False) # rimuovo l'entità
         else: # senza tasto shift
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               self.SetEntity(entity)
            else:
               self.AddRemoveEntity(entity, True) # aggiungo l'entità
      else: # se si deve rimuovere dal gruppo di selezione
         self.AddRemoveEntity(entity, False) # rimuovo l'entità


   # ============================================================================
   # SetEntity
   # ============================================================================
   def SetEntity(self, entity):
      # controllo sul layer
      if self.onlyEditableLayers == True and entity.layer.isEditable() == False:
         self.showMsgOnAddRemove(0)
         return
      # controllo sul tipo
      if (self.checkPointLayer == False and entity.layer.geometryType() == QgsWkbTypes.PointGeometry) or \
         (self.checkLineLayer == False and entity.layer.geometryType() == QgsWkbTypes.LineGeometry) or \
         (self.checkPolygonLayer == False and entity.layer.geometryType() == QgsWkbTypes.PolygonGeometry):
         self.showMsgOnAddRemove(0)
         return
      
      # controllo su layer delle quotature
      # verifico se l'entità appartiene ad uno stile di quotatura
      dimEntity = QadDimStyles.getDimEntity(entity)
      if self.checkDimLayers == False and dimEntity is not None:
         self.showMsgOnAddRemove(0)
         return

      self.entitySet.deselectOnLayer()
      self.entitySet.clear()
      self.entitySet.addEntity(entity)

      if self.checkDimLayers == True and dimEntity is not None:
         # Aggiungo i componenenti della quotatura a set <entitySet>
         self.entitySet.unite(dimEntity.getEntitySet())

      self.showMsgOnAddRemove(self.entitySet.count())
      self.entitySet.selectOnLayer(False) # incremental = False aaaaaaaaaaaaaaaaaaaaaaaaaa qui parte l'evento activate di qad_maptool (se il layer non è in modifica)
      self.lastEntitySet.clear()
      self.lastEntitySet.addEntity(entity)


   # ============================================================================
   # AddRemoveEntity
   # ============================================================================
   def AddRemoveEntity(self, entity, Add):
      # controllo sul layer
      if self.onlyEditableLayers == True and entity.layer.isEditable() == False:
         self.showMsgOnAddRemove(0)
         return
      # controllo sul tipo
      if (self.checkPointLayer == False and entity.layer.geometryType() == QgsWkbTypes.PointGeometry) or \
         (self.checkLineLayer == False and entity.layer.geometryType() == QgsWkbTypes.LineGeometry) or \
         (self.checkPolygonLayer == False and entity.layer.geometryType() == QgsWkbTypes.PolygonGeometry):
         self.showMsgOnAddRemove(0)
         return
      # controllo su layer delle quotature
      if self.checkDimLayers == False and len(QadDimStyles.getDimListByLayer(entity.layer)) > 0:
         self.showMsgOnAddRemove(0)
         return
      
      self.entitySet.deselectOnLayer()
      if Add == True: # aggiungi al gruppo di selezione
         self.entitySet.addEntity(entity)
      else: # rimuovi dal gruppo di selezione
         self.entitySet.removeEntity(entity)

      if self.checkDimLayers == True:
         dimEntitySet = QadEntitySet()
         dimEntitySet.addEntity(entity)
         # La funzione verifica se le entità che fanno parte di un entitySet sono anche parte di quotatura e,
         # in caso affermativo, aggiunge/rimuove tutti i componenti delle quotature all'entitySet.
         QadDimStyles.addAllDimComponentsToEntitySet(dimEntitySet, self.onlyEditableLayers)
         if Add == True: # aggiungi al gruppo di selezione
            self.entitySet.unite(dimEntitySet)
         else: # rimuovi dal gruppo di selezione
            self.entitySet.subtract(dimEntitySet)
         self.showMsgOnAddRemove(dimEntitySet.count())
      else:
         self.showMsgOnAddRemove(1)
         
      self.entitySet.selectOnLayer(False) # incremental = False
      self.lastEntitySet.clear()
      self.lastEntitySet.addEntity(entity)


   # ============================================================================
   # elaborateSelSet
   # ============================================================================
   def elaborateSelSet(self, selSet, shiftKey):
      if self.checkDimLayers == True:
         dimEntitySet = QadEntitySet(selSet)
         # La funzione verifica se le entità che fanno parte di un entitySet sono anche parte di quotatura e,
         # in caso affermativo, aggiunge tutti i componenti delle quotature all'entitySet.
         QadDimStyles.addAllDimComponentsToEntitySet(dimEntitySet, self.onlyEditableLayers)
         selSet.unite(dimEntitySet)

      if self.AddOnSelection == True: # aggiungi al gruppo di selezione
         if shiftKey: # se la selezione é avvenuta con shift premuto
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               # verifico se ci sono degli oggetti non ancora selezionati
               intersectSS = QadEntitySet(selSet)
               intersectSS.subtract(self.entitySet)
               if intersectSS.isEmpty(): # tutti gli oggetti erano già selezionati
                  self.AddRemoveSelSet(selSet, False) # rimuovo il gruppo di selezione
               else:
                  self.AddRemoveSelSet(selSet, True) # aggiungo il gruppo di selezione
            else:
               self.AddRemoveSelSet(selSet, False) # rimuovo il gruppo di selezione
         else: # senza tasto shift
            if self.pickAdd == 0: # The objects most recently selected become the selection set
               self.SetSelSet(selSet)
            else:
               self.AddRemoveSelSet(selSet, True) # aggiungo il gruppo di selezione
      else: # se si deve rimuovere dal gruppo di selezione
         self.AddRemoveSelSet(selSet, False) # rimuovo il gruppo di selezione

    
   # ============================================================================
   # SetSelSet
   # ============================================================================
   def SetSelSet(self, selSet):
      for layerEntitySet in self.entitySet.layerEntitySetList:
         # se il layer non é presente in selSet
         if selSet.findLayerEntitySet(layerEntitySet) is None:            
            layerEntitySet.deselectOnLayer()
         else:
            layerEntitySet.deselectOnLayer()

      self.entitySet.set(selSet)

      self.showMsgOnAddRemove(self.entitySet.count())
      self.entitySet.selectOnLayer(False) # incremental = False
      self.lastEntitySet.set(selSet)


   # ============================================================================
   # AddCurrentQgsSelectedFeatures
   # ============================================================================
   def AddCurrentQgsSelectedFeatures(self):
      # verifico se ci sono entità correntemente selezionate
      self.entitySet.initByCurrentQgsSelectedFeatures(self.getLayersToCheck())
      found = self.entitySet.count()
      if found > 0:
         msg = QadMsg.translate("Command_SSGET", "\nfound {0}")
         self.showMsg(msg.format(found), False) # non ripete il prompt
         return True
      else:
         return False


   # ============================================================================
   # AddRemoveSelSet
   # ============================================================================
   def AddRemoveSelSet(self, selSet, Add):
      self.entitySet.deselectOnLayer()
      if Add == True: # aggiungi al gruppo di selezione
         self.entitySet.unite(selSet)
      else: # rimuovi dal gruppo di selezione
         self.entitySet.subtract(selSet)

      self.showMsgOnAddRemove(selSet.count())

      self.entitySet.selectOnLayer(False) # incremental = False
      self.lastEntitySet.set(selSet)

   # ============================================================================
   # AddRemoveSelSetByFence
   # ============================================================================
   def AddRemoveSelSetByFence(self, points):
      if len(points) > 1:
         selSet = getSelSet("F", self.getPointMapTool(), points, \
                                      self.getLayersToCheck())
         self.elaborateSelSet(selSet, False)

   # ============================================================================
   # AddRemoveSelSetByPolygon
   # ============================================================================
   def AddRemoveSelSetByPolygon(self, mode, points):
      if len(points) > 2:
         selSet = getSelSet(mode, self.getPointMapTool(), points, \
                                      self.getLayersToCheck())
         self.elaborateSelSet(selSet, False)

   # ============================================================================
   # AddRemoveSelSetByGeometry
   # ============================================================================
   def AddRemoveSelSetByGeometry(self, mode, geom):
      if type(geom) == QgsGeometry: # singola geometria
         selSet = getSelSet(mode, self.getPointMapTool(), geom, \
                                      self.getLayersToCheck())
      else: # lista di geometrie
         selSet = QadEntitySet()
         for g in geom:
            partial = getSelSet(mode, self.getPointMapTool(), g, \
                                          self.getLayersToCheck())
            selSet.unite(partial)
      self.elaborateSelSet(selSet, False)

      
   # ============================================================================
   # WaitForFirstPoint
   # ============================================================================
   def WaitForFirstPoint(self):
      self.step = 1

      # "Finestra" "Ultimo" "Interseca"
      # "Riquadro" "Tutto" "iNTercetta"
      # "FPoligono" "IPoligono"
      # "FCerchio" "ICerchio"
      # "FOggetti" "IOggetti"
      # "FBuffer" "IBuffer"
      # "AGgiungi" "Elimina"
      # "Precedente" "Annulla"
      # "AUto" "SIngolo" "Help"
      keyWords = QadMsg.translate("Command_SSGET", "Window") + "/" + \
                 QadMsg.translate("Command_SSGET", "Last") + "/" + \
                 QadMsg.translate("Command_SSGET", "Crossing") + "/" + \
                 QadMsg.translate("Command_SSGET", "Box") + "/" + \
                 QadMsg.translate("Command_SSGET", "All") + "/" + \
                 QadMsg.translate("Command_SSGET", "Fence") + "/" + \
                 QadMsg.translate("Command_SSGET", "WPolygon") + "/" + \
                 QadMsg.translate("Command_SSGET", "CPolygon") + "/" + \
                 QadMsg.translate("Command_SSGET", "WCircle") + "/" + \
                 QadMsg.translate("Command_SSGET", "CCircle") + "/" + \
                 QadMsg.translate("Command_SSGET", "WObjects") + "/" + \
                 QadMsg.translate("Command_SSGET", "CObjects") + "/" + \
                 QadMsg.translate("Command_SSGET", "WBuffer") + "/" + \
                 QadMsg.translate("Command_SSGET", "CBuffer") + "/" + \
                 QadMsg.translate("Command_SSGET", "Add") + "/" + \
                 QadMsg.translate("Command_SSGET", "Remove") + "/" + \
                 QadMsg.translate("Command_SSGET", "Previous") + "/" + \
                 QadMsg.translate("Command_SSGET", "Undo") + "/" + \
                 QadMsg.translate("Command_SSGET", "AUto") + "/" + \
                 QadMsg.translate("Command_SSGET", "SIngle") + "/" + \
                 QadMsg.translate("Command_SSGET", "Help")
      englishKeyWords = "Window" + "/" + "Last" + "/" + "Crossing" + "/" + "Box" + "/" \
                         + "All" + "/" + "Fence" + "/" + "WPolygon" + "/" + "CPolygon" + "/" \
                         + "WCircle" + "/" + "CCircle" + "/" + "WObjects" + "/" + "CObjects" + "/" \
                         + "WBuffer" + "/" + "CBuffer" + "/" + "Add" + "/" + "Remove" + "/" \
                         + "Previous" + "/" + "Undo" + "/" + "AUto" + "/" + "SIngle" + "/" + "Help"
                 
      if self.AddOnSelection == True:
         prompt = QadMsg.translate("Command_SSGET", "Select Objects")
      else:
         prompt = QadMsg.translate("Command_SSGET", "Remove objects")
                           
      if self.help == True:         
         prompt = prompt + QadMsg.translate("Command_SSGET", " or [{0}]").format(keyWords)
         
      prompt = prompt + QadMsg.translate("Command_SSGET", ": ")
            
      # imposto il map tool
      self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
      self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
      # imposto i layer da controllare sul maptool
      self.getPointMapTool().layersToCheck = self.getLayersToCheck()
      self.points = []
           
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NONE)
      # input dinamico
      di = self.getPointMapTool().getDynamicInput()
      di.context = QadDynamicInputContextEnum.NONE
      di.showInputMsg(prompt, QadInputTypeEnum.NONE)
      return

   def run(self, msgMapTool = False, msg = None):
      # ritorna:
      # True per selezione non terminata
      # False per selezione terminata
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # errore
            
      # =========================================================================
      # RICHIESTA PRIMO PUNTO PER SELEZIONE OGGETTI
      if self.step == 0:
         # if you can also select objects before you start a command
         if QadVariables.get(QadMsg.translate("Environment variables", "PICKFIRST")) == 1:
            if self.AddCurrentQgsSelectedFeatures() == True:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True;
         self.WaitForFirstPoint()
         return False # continua
      
      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PRIMO PUNTO PER SELEZIONE OGGETTI
      elif self.step == 1: # dopo aver atteso un punto o enter o una parola chiave si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  if self.entitySet.count() > 0:
                     self.plugIn.setLastEntitySet(self.entitySet)
                  return True # fine
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False # continua
            
            shiftKey = self.getPointMapTool().shiftKey

            # se é stata selezionata un'entità
            if self.getPointMapTool().entity.isInitialized():
               value = self.getPointMapTool().entity
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            shiftKey = False
            value = msg

         if value is None:
            if self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
            return True # fine

         if type(value) == unicode:
            self.currSelectionMode = value
            
            if value == QadMsg.translate("Command_SSGET", "Window") or value == "Window" or \
               value == QadMsg.translate("Command_SSGET", "Crossing") or value == "Crossing":
               # "Finestra" = Seleziona tutti gli oggetti che si trovano completamente all'interno di un rettangolo definito da due punti
               # "Interseca" = Seleziona gli oggetti che intersecano o si trovano all'interno di un'area definita da due punti
               # imposto il map tool
               self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_SSGET", "First corner: "))
               self.step = 2
            if value == QadMsg.translate("Command_SSGET", "Last") or value == "Last": 
               # Seleziona l'ultima entità inserita
               if self.plugIn.getLastEntity() is None:
                  self.showMsgOnAddRemove(0)
               else:
                  self.AddRemoveEntity(self.plugIn.getLastEntity(), self.AddOnSelection)
                  if self.SingleSelection == True and self.entitySet.count() > 0:
                     self.plugIn.setLastEntitySet(self.entitySet)
                     return True # fine
               
               if self.exitAfterSelection == True:
                  return True # fine
               
               self.WaitForFirstPoint()                          
            elif value == QadMsg.translate("Command_SSGET", "Box") or value == "Box":
               # Seleziona tutti gli oggetti che intersecano o si trovano all'interno di un rettangolo specificato da due punti.
               # Se i punti del rettangolo sono specificati da destra a sinistra, Riquadro equivale ad Interseca,
               # altrimenti é equivalente a Finestra
               # imposto il map tool
               self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)
               self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.NONE)
               # si appresta ad attendere un punto
               self.waitForPoint(QadMsg.translate("Command_SSGET", "First corner: "))
               self.step = 2           
            elif value == QadMsg.translate("Command_SSGET", "All") or value == "All":
               # Seleziona tutti gli oggetti 
               selSet = getSelSet("X", self.getPointMapTool(), None, \
                                            self.getLayersToCheck())
               self.elaborateSelSet(selSet, False)
               if self.SingleSelection == True and self.entitySet.count() > 0:
                  self.plugIn.setLastEntitySet(self.entitySet)
                  return True # fine 

               if self.exitAfterSelection == True:
                  return True # fine

               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Fence") or value == "Fence":
               # Seleziona tutti gli oggetti che intersecano una polilinea
               self.PLINECommand = QadPLINECommandClass(self.plugIn)
               # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
               # che non verrà salvata su un layer
               self.PLINECommand.virtualCmd = True   
               self.PLINECommand.run(msgMapTool, msg)
               self.step = 4
            elif value == QadMsg.translate("Command_SSGET", "WPolygon") or value == "WPolygon" or \
                 value == QadMsg.translate("Command_SSGET", "CPolygon") or value == "CPolygon":
               # "FPoligono" = Seleziona oggetti che si trovano completamente all'interno di un poligono definito da punti
               # "IPoligono" = Seleziona gli oggetti che intersecano o si trovano all'interno di un poligono definito specificando dei punti
               self.MPOLYGONCommand = QadMPOLYGONCommandClass(self.plugIn)
               # se questo flag = True il comando serve all'interno di un altro comando per disegnare una linea
               # che non verrà salvata su un layer
               self.MPOLYGONCommand.virtualCmd = True
               
               if value == QadMsg.translate("Command_SSGET", "WPolygon") or value == "WPolygon":
                  self.MPOLYGONCommand.setRubberBandColor(None, getColorForWindowSelectionArea())
               else:
                  self.MPOLYGONCommand.setRubberBandColor(None, getColorForCrossingSelectionArea())
               
               self.MPOLYGONCommand.run(msgMapTool, msg)
               self.step = 7
            elif value == QadMsg.translate("Command_SSGET", "WCircle") or value == "WCircle" or \
                 value == QadMsg.translate("Command_SSGET", "CCircle") or value == "CCircle":
               # "FCerchio" = Seleziona oggetti che si trovano completamente all'interno di un cerchio
               # "ICerchio" = Seleziona oggetti che intersecano o si trovano all'interno di un cerchio
               self.CIRCLECommand = QadCIRCLECommandClass(self.plugIn)
               # se questo flag = True il comando serve all'interno di un altro comando per disegnare un cerchio
               # che non verrà salvata su un layer
               self.CIRCLECommand.virtualCmd = True
               
               if value == QadMsg.translate("Command_SSGET", "WCircle") or value == "WCircle":
                  self.CIRCLECommand.setRubberBandColor(None, getColorForWindowSelectionArea())
               else:
                  self.CIRCLECommand.setRubberBandColor(None, getColorForCrossingSelectionArea())
                  
               self.CIRCLECommand.run(msgMapTool, msg)
               self.step = 5
            elif value == QadMsg.translate("Command_SSGET", "WObjects") or value == "WObjects" or \
                 value == QadMsg.translate("Command_SSGET", "CObjects") or value == "CObjects":
               # "FOggetti" = Seleziona oggetti che si trovano completamente all'interno di oggetti da selezionare
               # "IOggetti" = Seleziona oggetti che intersecano o si trovano all'interno di oggetti da selezionare
               self.SSGetClass = QadSSGetClass(self.plugIn)
               self.SSGetClass.run(msgMapTool, msg)
               self.step = 6
            elif value == QadMsg.translate("Command_SSGET", "WBuffer") or value == "WBuffer" or \
                 value == QadMsg.translate("Command_SSGET", "CBuffer") or value == "CBuffer":
               # ho dovuto spostare questo import perché qad_mbuffer_cmd fa l'import di qad_ssget_cmd
               from .qad_mbuffer_cmd import QadMBUFFERCommandClass
               
               # "FBuffer" = Seleziona oggetti che si trovano completamente all'interno di buffer intorno ad oggetti da selezionare
               # "IBuffer" = Seleziona oggetti che intersecano o si trovano all'interno di buffer intorno ad oggetti da selezionare
               self.MBUFFERCommand = QadMBUFFERCommandClass(self.plugIn)
               # se questo flag = True il comando serve all'interno di un altro comando per disegnare un cerchio
               # che non verrà salvata su un layer
               self.MBUFFERCommand.virtualCmd = True   
               
               if value == QadMsg.translate("Command_SSGET", "WBuffer") or value == "WBuffer":
                  self.MBUFFERCommand.setRubberBandColor(None, getColorForWindowSelectionArea())
               else:
                  self.MBUFFERCommand.setRubberBandColor(None, getColorForCrossingSelectionArea())
               
               self.MBUFFERCommand.run(msgMapTool, msg)
               self.step = 8
            elif value == QadMsg.translate("Command_SSGET", "Add") or value == "Add":
               # Passa al metodo Aggiungi: gli oggetti selezionati possono essere aggiunti al gruppo di selezione 
               self.AddOnSelection = True
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Remove") or value == "Remove":
               # Passa al metodo Rimuovi: gli oggetti possono essere rimossi dal gruppo di selezione
               self.AddOnSelection = False
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Previous") or value == "Previous":
               # Seleziona il gruppo di selezione più recente
               if self.plugIn.lastEntitySet is None:
                  self.showMsgOnAddRemove(0)
               else:
                  entitySet = QadEntitySet()
                  entitySet.set(self.plugIn.lastEntitySet)
                  # controllo sul layer                  
                  if self.onlyEditableLayers == True:
                     entitySet.removeNotEditable()
                  # controllo sul tipo
                  if self.checkPointLayer == False:
                     entitySet.removeGeomType(QgsWkbTypes.PointGeometry)
                  if self.checkLineLayer == False:
                     entitySet.removeGeomType(QgsWkbTypes.LineGeometry)
                  if self.checkPolygonLayer == False:
                     entitySet.removeGeomType(QgsWkbTypes.PolygonGeometry)
                  # controllo sulle quotature
                  if self.checkDimLayers == False:
                     QadDimStyles.removeAllDimLayersFromEntitySet(entitySet)
                     
                  entitySet.removeNotExisting()
                  self.elaborateSelSet(entitySet, False)
                  if self.SingleSelection == True and self.entitySet.count() > 0:
                     self.plugIn.setLastEntitySet(self.entitySet)
                     return True # fine

               if self.exitAfterSelection == True:
                  return True # fine

               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Undo") or value == "Undo":
               # Annulla la selezione dell'oggetto aggiunto più recentemente al gruppo di selezione.
               # Inverto il tipo di selezione
               prevAddOnSelection = self.AddOnSelection
               self.AddOnSelection = not self.AddOnSelection
               self.elaborateSelSet(self.lastEntitySet, False)
               # Ripristino il tipo di selezione
               self.AddOnSelection = prevAddOnSelection
               if self.SingleSelection == True and self.entitySet.count() > 0:
                  self.plugIn.setLastEntitySet(self.entitySet)
                  return True # fine

               if self.exitAfterSelection == True:
                  return True # fine
               
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "AUto") or value == "AUto":
               # Passa alla selezione automatica: vengono selezionati gli oggetti sui quali si posiziona il puntatore.
               # Facendo clic su un'area vuota all'interno o all'esterno di un oggetto, 
               # si crea il primo angolo di un rettangolo di selezione, come per il metodo Riquadro
               self.SingleSelection = False
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "SIngle") or value == "SIngle":
               # Passa al metodo Singolo: viene selezionato il primo oggetto o gruppo di oggetti indicato,
               # senza che vengano richieste altre selezioni.
               self.SingleSelection = True
               if self.entitySet.count() > 0:
                  self.plugIn.setLastEntitySet(self.entitySet)
                  return True # fine               
               self.WaitForFirstPoint()
            elif value == QadMsg.translate("Command_SSGET", "Help") or value == "Help":
               self.help = True
               self.WaitForFirstPoint()
         elif type(value) == QgsPointXY: # se é stato inserito il punto iniziale del rettangolo
            self.currSelectionMode = QadMsg.translate("Command_SSGET", "Box")
            self.points.append(value)
            
            self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITYSET_SELECTION)
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
            self.getPointMapTool().setStartPoint(value)
            
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))
            self.step = 3
         else: # se é stata selezionata un'entità
            self.elaborateEntity(value, shiftKey)

            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # fine               

            if self.exitAfterSelection == True:
               return True # fine

            self.WaitForFirstPoint()
          
         return False # continua

      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL PRIMO PUNTO DEL RETTANGOLO DA OPZIONE 
      # FINESTRA, INTERSECA, RIQUADRO (da step = 1)
      elif self.step == 2: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
                  self.WaitForFirstPoint()
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg
                        
         if type(value) == QgsPointXY:
            self.points.append(value)           
            self.getPointMapTool().setSelectionMode(QadGetPointSelectionModeEnum.ENTITYSET_SELECTION)
            self.getPointMapTool().setDrawMode(QadGetPointDrawModeEnum.ELASTIC_RECTANGLE)
            
            # cambio il colore impostato da setDrawMode
            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "Window") or value == "Window":
               self.getPointMapTool().rectangleCrossingSelectionColor = self.getPointMapTool().rectangleWindowSelectionColor
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "Crossing") or value == "Crossing":
                self.getPointMapTool().rectangleWindowSelectionColor = self.getPointMapTool().rectangleCrossingSelectionColor
            
            self.rectangleCrossingSelectionColor = getColorForCrossingSelectionArea()
            self.rectangleWindowSelectionColor = getColorForWindowSelectionArea()
            
            self.getPointMapTool().setStartPoint(value)
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))
            self.step = 3
         else:
            self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
            self.WaitForFirstPoint()

         return False # continua


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DEL SECONDO PUNTO DEL RETTANGOLO (da step = 1)
      elif self.step == 3: # dopo aver atteso un punto si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
                  # si appresta ad attendere un punto
                  self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))
                  return False
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False

            shiftKey = self.getPointMapTool().shiftKey
            value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            shiftKey = False
            value = msg
                        
         if type(value) == QgsPointXY:
            self.getPointMapTool().clear()
            self.points.append(value)
            
            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "Box") or \
               self.currSelectionMode == "Box":
               if self.points[0].x() < value.x():
                  mode = "W"
               else:
                  mode = "C"
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "Window") or \
               self.currSelectionMode == "Window": 
               mode = "W"
            else: # "Interseca"
               mode = "C"
               
            selSet = getSelSet(mode, self.getPointMapTool(), self.points, \
                                         self.getLayersToCheck())
            self.elaborateSelSet(selSet, shiftKey)
         
            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # fine

            if self.exitAfterSelection == True:
               return True # fine

            self.WaitForFirstPoint()
         else:
            self.showMsg(QadMsg.translate("Command_SSGET", "Window not correct."))
            # si appresta ad attendere un punto
            self.waitForPoint(QadMsg.translate("Command_SSGET", "Specify opposite corner: "))

         return False # continua


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO PER MODALITA' INTERCETTA (da step = 1 o 4)
      elif self.step == 4: # dopo aver atteso un punto si riavvia il comando
         if self.PLINECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            self.AddRemoveSelSetByFence(self.PLINECommand.polyline.asPolyline())
            del self.PLINECommand
            self.PLINECommand = None
         
            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # fine

            if self.exitAfterSelection == True:
               return True # fine

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PER MODALITA' FCERCHIO e ICERCHIO (da step = 1 o 5)
      elif self.step == 5: # dopo aver atteso un punto si riavvia il comando
         if self.CIRCLECommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            if (self.CIRCLECommand.centerPt is not None) and \
               (self.CIRCLECommand.radius is not None):
               circle = QadCircle()
               circle.set(self.CIRCLECommand.centerPt, self.CIRCLECommand.radius)
               points = circle.asPolyline()
               if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WCircle") or \
                  self.currSelectionMode == "WCircle":
                  self.AddRemoveSelSetByPolygon("WP", points)
               elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CCircle") or \
                  self.currSelectionMode == "CCircle":
                  self.AddRemoveSelSetByPolygon("CP", points)               
            
            del self.CIRCLECommand
            self.CIRCLECommand = None
         
            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # fine

            if self.exitAfterSelection == True:
               return True # fine

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI SELEZIONE DI OGGETTI PER MODALITA' FOGGETTI e IOGGETTI (da step = 1 o 6)
      elif self.step == 6: # dopo aver atteso un punto si riavvia il comando
         if self.SSGetClass.run(msgMapTool, msg) == True:
            self.showMsg("\n")
            destCRS = self.SSGetClass.getPointMapTool().canvas.mapSettings().destinationCrs()
            geoms = self.SSGetClass.entitySet.getGeometryCollection(destCRS) # trasformo la geometria
            
            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WObjects") or \
               self.currSelectionMode == "WObjects":
               self.AddRemoveSelSetByGeometry("WO", geoms)
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CObjects") or \
               self.currSelectionMode == "CObjects":
               self.AddRemoveSelSetByGeometry("CO", geoms)
                                 
            del self.SSGetClass
            self.SSGetClass = None
         
            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # fine

            if self.exitAfterSelection == True:
               return True # fine

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA PER MODALITA' FPOLIGONO e IPOLIGONO (da step = 1 o 7)
      elif self.step == 7: # dopo aver atteso un punto si riavvia il comando
         if self.MPOLYGONCommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")              
            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WPolygon") or \
               self.currSelectionMode == "WPolygon":
               self.AddRemoveSelSetByPolygon("WP", self.MPOLYGONCommand.PLINECommand.polyline.asPolyline())
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CPolygon") or \
               self.currSelectionMode == "CPolygon":
               self.AddRemoveSelSetByPolygon("CP", self.MPOLYGONCommand.PLINECommand.polyline.asPolyline())
            
            del self.MPOLYGONCommand
            self.MPOLYGONCommand = None
         
            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # fine

            if self.exitAfterSelection == True:
               return True # fine

            self.WaitForFirstPoint()
         return False


      # =========================================================================
      # RISPOSTA ALLA RICHIESTA DI SELEZIONE DI OGGETTI PER MODALITA' FBUFFER e IBUFFER (da step = 1 o 8)
      elif self.step == 8: # dopo aver atteso un punto si riavvia il comando
         if self.MBUFFERCommand.run(msgMapTool, msg) == True:
            self.showMsg("\n")

            bufferGeoms = []
            for layerEntitySet in self.MBUFFERCommand.entitySet.layerEntitySetList:
               geoms = layerEntitySet.getGeometryCollection()
               width = distMapToLayerCoordinates(self.MBUFFERCommand.width, \
                                                           self.MBUFFERCommand.getPointMapTool().canvas,\
                                                           layerEntitySet.layer)
               for geom in geoms:
                  bufferGeoms.append(geom.buffer(width, self.MBUFFERCommand.segments))
                        
            if self.currSelectionMode == QadMsg.translate("Command_SSGET", "WBuffer") or \
               self.currSelectionMode == "WBuffer":
               self.AddRemoveSelSetByGeometry("WO", bufferGeoms)
            elif self.currSelectionMode == QadMsg.translate("Command_SSGET", "CBuffer") or \
               self.currSelectionMode == "CBuffer":
               self.AddRemoveSelSetByGeometry("CO", bufferGeoms)
                                 
            del self.MBUFFERCommand
            self.MBUFFERCommand = None
         
            if self.SingleSelection == True and self.entitySet.count() > 0:
               self.plugIn.setLastEntitySet(self.entitySet)
               return True # fine

            if self.exitAfterSelection == True:
               return True # fine

            self.WaitForFirstPoint()
         return False