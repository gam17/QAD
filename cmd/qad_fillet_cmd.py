# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando FILLET per raccordare due oggetti grafici ok
 
                              -------------------
        begin                : 2014-01-30
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


from qgis.core import QgsGeometry, QgsPointXY, QgsWkbTypes
from qgis.PyQt.QtGui import QIcon


from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_generic_cmd import QadCommandClass
from .qad_getdist_cmd import QadGetDistClass
from .qad_fillet_maptool import Qad_fillet_maptool, Qad_fillet_maptool_ModeEnum
from ..qad_msg import QadMsg
from ..qad_textwindow import QadInputTypeEnum, QadInputModeEnum
from .. import qad_utils
from .. import qad_layer
from ..qad_variables import QadVariables
from ..qad_polyline import QadPolyline
from ..qad_dim import QadDimStyles
from ..qad_fillet_fun import fillet2QadGeometries, filletAllPartsQadPolyline, filletQadPolyline
from ..qad_entity import QadEntity
from ..qad_multi_geom import fromQadGeomToQgsGeom, getQadGeomAt, setQadGeomAt
from ..qad_geom_relations import getQadGeomClosestPart


# Classe che gestisce il comando FILLET
class QadFILLETCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadFILLETCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "FILLET")

   def getEnglishName(self):
      return "FILLET"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runFILLETCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/fillet.svg")
   
   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_FILLET", "Rounds and fillets the edges of objects.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)      
      self.GetDistClass = None

      self.entity1 = QadEntity()
      self.atGeom1 = None
      self.atSubGeom1 = None
      self.partAt1 = 0
      self.pointAt1 = None
      
      self.entity2 = QadEntity()
      self.atGeom2 = None
      self.atSubGeom2 = None
      self.qadPolyline2 = QadPolyline()
      self.partAt2 = 0
      self.pointAt2 = None

      self.filletMode = plugIn.filletMode # modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
      self.radius = QadVariables.get(QadMsg.translate("Environment variables", "FILLETRAD"))
      self.multi = False
      self.nOperationsToUndo = 0
            
   
   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass
      self.entity1.deselectOnLayer()
      self.entity2.deselectOnLayer()


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      # quando si é in fase di richiesta distanza
      if self.step == 3 or self.step == 5 or self.step == 7:
         return self.GetDistClass.getPointMapTool()
      elif (self.plugIn is not None):
         if self.PointMapTool is None:
            self.PointMapTool = Qad_fillet_maptool(self.plugIn)
         return self.PointMapTool
      else:
         return None


   def getCurrentContextualMenu(self):
      # quando si é in fase di richiesta distanza
      if self.step == 3 or self.step == 5 or self.step == 7:
         return self.GetDistClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   #============================================================================
   # setEntityInfo
   #============================================================================
   def setEntityInfo(self, firstObj, layer, featureId, point):
      """
      Setta self.entity, self.atGeom, self.atSubGeom, self.partAt, self.pointAt
      di primo o del secondo oggetto da raccordare (vedi <firstObj>)
      """
      if firstObj:
         e = self.entity1
      else:
         e = self.entity2
         
      e.set(layer, featureId)
      qadGeom = e.getQadGeom()
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
      res = getQadGeomClosestPart(qadGeom, point)
      
      if firstObj:
         self.pointAt1 = res[1]
         self.atGeom1 = res[2]
         self.atSubGeom1 = res[3]
         self.partAt1 = res[4]
      else:
         self.pointAt2 = res[1]
         self.atGeom2 = res[2]
         self.atSubGeom2 = res[3]
         self.partAt2 = res[4]
   
      e.selectOnLayer(False) # non incrementale
      return True


   #============================================================================
   # filletPolyline
   #============================================================================
   def filletPolyline(self):         
      layer = self.entity1.layer
      f = self.entity1.getFeature()
      qadGeom = self.entity1.getQadGeom()
      subQadGeom = getQadGeomAt(qadGeom, self.atGeom1, self.atSubGeom1)
            
      if filletAllPartsQadPolyline(subQadGeom, self.radius) == False: return False
      newQadGeom = setQadGeomAt(qadGeom, subQadGeom, self.atGeom1, self.atSubGeom1)
      if newQadGeom is None:
         return False
      f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, layer))
                              
      self.plugIn.beginEditCommand("Feature edited", layer)
      
      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(self.plugIn, layer, f, False, False) == False:
         self.plugIn.destroyEditCommand()
         return False

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1
      
      return True
   

   #============================================================================
   # fillet
   #============================================================================
   def fillet(self):
      tolerance2ApproxCurve = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE")) 
      
      # stessa entità e stessa geometria
      if self.entity1.layer.id() == self.entity2.layer.id() and \
         self.entity1.featureId == self.entity2.featureId and \
         self.atGeom1 == self.atGeom2 and self.atSubGeom1 == self.atSubGeom2:
         # se anche stessa parte
         if self.partAt1 == self.partAt2: return False
         subQadGeom = getQadGeomAt(self.entity1.getQadGeom(),self.atGeom1, self.atSubGeom1)
         if subQadGeom.whatIs() == "POLYLINE":
            newQadGeom = filletQadPolyline(subQadGeom, self.partAt1, self.pointAt1, self.partAt2, self.pointAt2, \
                                    self.filletMode, self.radius)

         if newQadGeom is None: # raccordo non possibile
            msg = QadMsg.translate("Command_FILLET", "\nFillet with radius <{0}> impossible.")
            #showMsg
            self.showMsg(msg.format(str(self.radius)))
            return False

         self.plugIn.beginEditCommand("Feature edited", [self.entity1.layer])
   
         f = self.entity1.getFeature()
         # trasformo la geometria nel crs del layer
         f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, self.entity1.layer))
         
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity1.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False

         self.plugIn.endEditCommand()
         self.nOperationsToUndo = self.nOperationsToUndo + 1
   
         return True

      # geometrie diverse
      res = fillet2QadGeometries(self.entity1.getQadGeom(), self.atGeom1, self.atSubGeom1, self.partAt1, self.pointAt1, \
                                 self.entity2.getQadGeom(), self.atGeom2, self.atSubGeom2, self.partAt2, self.pointAt2, \
                                 self.filletMode, self.radius)
         
      if res is None: # raccordo non possibile
         msg = QadMsg.translate("Command_FILLET", "\nFillet with radius <{0}> impossible.")
         #showMsg
         self.showMsg(msg.format(str(self.radius)))
         return False
      
      newQadGeom = res[0]
      whatToDoPoly1 = res[1]
      whatToDoPoly2 = res[2]

      self.plugIn.beginEditCommand("Feature edited", [self.entity1.layer, self.entity2.layer])

      if whatToDoPoly1 == 1: # 1=modificare       
         f = self.entity1.getFeature()
         # trasformo la geometria nel crs del layer
         f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, self.entity1.layer))
         
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity1.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False
      elif whatToDoPoly1 == 2: # 2=cancellare
         # se non si tratta della stessa entità
         if self.entity1 != self.entity2:
            # plugIn, layer, featureId, refresh
            if qad_layer.deleteFeatureToLayer(self.plugIn, self.entity1.layer, \
                                              self.entity1.featureId, False) == False:
               self.plugIn.destroyEditCommand()
               return False

      if whatToDoPoly2 == 1: # 1=modificare
         f = self.entity2.getFeature()
         # trasformo la geometria nel crs del layer
         f.setGeometry(fromQadGeomToQgsGeom(newQadGeom, self.entity2.layer))
         
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(self.plugIn, self.entity2.layer, f, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False
      elif whatToDoPoly2 == 2: # 2=cancellare 
         # se non si tratta della stessa entità
         if self.entity1 != self.entity2:
            # plugIn, layer, featureId, refresh
            if qad_layer.deleteFeatureToLayer(self.plugIn, self.entity2.layer, \
                                              self.entity2.featureId, False) == False:
               self.plugIn.destroyEditCommand()
               return False

      if whatToDoPoly1 == 0 and whatToDoPoly2 == 0: # 0=niente      
         geom = QgsGeometry.fromPolylineXY(filletLinearObjectList.asPolyline(tolerance2ApproxCurve))
         # trasformo la geometria nel crs del layer
         geom = fromQadGeomToQgsGeom(newQadGeom, self.entity1.layer)
         
         # plugIn, layer, geom, coordTransform, refresh, check_validity
         if qad_layer.addGeomToLayer(self.plugIn, self.entity1.layer, geom, None, False, False) == False:
            self.plugIn.destroyEditCommand()
            return False

      self.plugIn.endEditCommand()
      self.nOperationsToUndo = self.nOperationsToUndo + 1

      return True
      

   #============================================================================
   # waitForFirstEntSel
   #============================================================================
   def waitForFirstEntSel(self):      
      self.step = 1
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_fillet_maptool_ModeEnum.ASK_FOR_FIRST_LINESTRING)

      # l'opzione Radius viene tradotta in italiano in "RAggio" nel contesto "waitForFirstEntSel"
      keyWords = QadMsg.translate("Command_FILLET", "Undo") + "/" + \
                 QadMsg.translate("Command_FILLET", "Polyline") + "/" + \
                 QadMsg.translate("Command_FILLET", "Radius", "waitForFirstEntSel") + "/" + \
                 QadMsg.translate("Command_FILLET", "Trim") + "/" + \
                 QadMsg.translate("Command_FILLET", "Multiple")
      prompt = QadMsg.translate("Command_FILLET", "Select first object or [{0}]: ").format(keyWords)
               
      englishKeyWords = "Undo" + "/" + "Polyline" + "/" + "Radius" + "/" + "Trim" + "/" + "Multiple"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, valore nullo non permesso
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)      
      

   #============================================================================
   # WaitForPolyline
   #============================================================================
   def WaitForPolyline(self):
      self.step = 2
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_fillet_maptool_ModeEnum.ASK_FOR_POLYLINE)
      self.getPointMapTool().radius = self.radius      

      # l'opzione Radius viene tradotta in italiano in "Raggio" nel contesto "WaitForPolyline"
      keyWords = QadMsg.translate("Command_FILLET", "Radius", "WaitForPolyline")
      prompt = QadMsg.translate("Command_FILLET", "Select polyline or [{0}]: ").format(keyWords)

      englishKeyWords = "Radius"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, valore nullo non permesso
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)      
            
        
   #============================================================================
   # waitForFilletMode
   #============================================================================
   def waitForFilletMode(self):      
      self.step = 4
      # imposto il map tool
      self.getPointMapTool().setMode(Qad_fillet_maptool_ModeEnum.NONE)

      keyWords = QadMsg.translate("Command_FILLET", "Trim-extend") + "/" + \
                 QadMsg.translate("Command_FILLET", "No trim-extend")

      if self.filletMode == 1:
         default = QadMsg.translate("Command_FILLET", "Trim-extend")
      elif self.filletMode == 2:
         default = QadMsg.translate("Command_FILLET", "No trim-extend") 
                         
      prompt = QadMsg.translate("Command_FILLET", "Specify trim mode [{0}] <{1}>: ").format(keyWords, default)

      englishKeyWords = "Trim-extend" + "/" + "No trim-extend"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave o un numero reale     
      # msg, inputType, default, keyWords, nessun controllo
      self.waitFor(prompt, QadInputTypeEnum.KEYWORDS, default, \
                   keyWords)      


   #============================================================================
   # waitForSecondEntSel
   #============================================================================
   def waitForSecondEntSel(self):      
      self.step = 6      
      # imposto il map tool
      self.getPointMapTool().filletMode = self.filletMode
      self.getPointMapTool().radius = self.radius
      self.getPointMapTool().setEntityInfo(self.entity1, self.atGeom1, self.atSubGeom1, \
                                           self.partAt1, self.pointAt1)      
      self.getPointMapTool().setMode(Qad_fillet_maptool_ModeEnum.ASK_FOR_SECOND_LINESTRING)

      # l'opzione Radius viene tradotta in italiano in "RAggio" nel contesto "waitForSecondEntSel"
      keyWords = QadMsg.translate("Command_FILLET", "Radius", "waitForSecondEntSel")           
      prompt = QadMsg.translate("Command_FILLET", "Select second object or shift-select to apply corner or [{0}]: ").format(keyWords)

      englishKeyWords = "Radius"
      keyWords += "_" + englishKeyWords
      # si appresta ad attendere un punto o enter o una parola chiave         
      # msg, inputType, default, keyWords, valore nullo non permesso
      self.waitFor(prompt, \
                   QadInputTypeEnum.POINT2D | QadInputTypeEnum.KEYWORDS, \
                   None, \
                   keyWords, QadInputModeEnum.NOT_NULL)      

        
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      if self.step == 0:
         CurrSettingsMsg = QadMsg.translate("QAD", "\nCurrent settings: ")
         if self.filletMode == 1:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_FILLET", "Mode = Trim-extend")
         else:
            CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_FILLET", "Mode = No trim-extend")
               
         CurrSettingsMsg = CurrSettingsMsg + QadMsg.translate("Command_FILLET", ", Radius = ") + str(self.radius)
         self.showMsg(CurrSettingsMsg)         
            
         self.waitForFirstEntSel()
         return False # continua
      
      #=========================================================================
      # RISPOSTA ALLA SELEZIONE PRIMO OGGETTO
      elif self.step == 1:
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
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_FILLET", "Undo") or value == "Undo":
               if self.nOperationsToUndo > 0: 
                  self.nOperationsToUndo = self.nOperationsToUndo - 1
                  self.plugIn.undoEditCommand()
               else:
                  self.showMsg(QadMsg.translate("QAD", "\nThe command has been canceled."))
                  
               self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
            elif value == QadMsg.translate("Command_FILLET", "Polyline") or value == "Polyline":
               self.WaitForPolyline()
            # l'opzione Radius viene tradotta in italiano in "RAggio" nel contesto "waitForFirstEntSel"
            elif value == QadMsg.translate("Command_FILLET", "Radius", "waitForFirstEntSel") or value == "Radius":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_FILLET", "Specify fillet radius <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.radius))
               self.GetDistClass.dist = self.radius
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 3
               self.GetDistClass.run(msgMapTool, msg)
            elif value == QadMsg.translate("Command_FILLET", "Trim") or value == "Trim":
               self.waitForFilletMode()
            elif value == QadMsg.translate("Command_FILLET", "Multiple") or value == "Multiple":
               self.multi = True
               self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
                           
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            self.entity1.clear()
            if self.getPointMapTool().entity.isInitialized():
               if self.setEntityInfo(True, self.getPointMapTool().entity.layer, \
                                     self.getPointMapTool().entity.featureId, value) == True:
                  self.waitForSecondEntSel() # si appresta ad attendere la selezione del secondo oggetto
                  return False
            else:
               # cerco se ci sono entità nel punto indicato considerando
               # solo layer lineari o poligono editabili che non appartengano a quote
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
                  if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
                     layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)
               
               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value), \
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  # result[0] = feature, result[1] = layer, result[0] = point
                  if self.setEntityInfo(True, result[1], result[0].id(), result[2]) == True:
                     self.waitForSecondEntSel() # si appresta ad attendere la selezione del secondo oggetto
                     return False
            self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto                                    
         else:
            return True # fine comando
         
         return False 

      #=========================================================================
      # RISPOSTA ALLA SELEZIONE DI UNA POLILINEA (da step = 1)
      elif self.step == 2:
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
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            # l'opzione Radius viene tradotta in italiano in "Raggio" nel contesto "WaitForPolyline"
            if value == QadMsg.translate("Command_FILLET", "Radius", "WaitForPolyline") or value == "Radius":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_FILLET", "Specify fillet radius <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.radius))
               self.GetDistClass.dist = self.radius
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 5
               self.GetDistClass.run(msgMapTool, msg)                           
               return False
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            self.entity1.clear()
            if self.getPointMapTool().entity.isInitialized():
               if self.setEntityInfo(True, self.getPointMapTool().entity.layer, \
                                     self.getPointMapTool().entity.featureId, value) == True:
                  if self.filletPolyline() == False or self.multi:
                     self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
                     return False
                  else:
                     return True
            else:
               # cerco se ci sono entità nel punto indicato considerando
               # solo layer lineari o poligono editabili che non appartengano a quote
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
                  if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
                     layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)

               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value), \
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  # result[0] = feature, result[1] = layer, result[0] = point
                  if self.setEntityInfo(True, result[1], result[0].id(), result[2]) == True:
                     if self.filletPolyline() == False or self.multi:
                        self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
                        return False
                     else:
                        return True
         else:
            return True # fine comando

         self.WaitForPolyline()
         return False

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL RAGGIO DI RACCORDO (da step = 1)
      elif self.step == 3:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.radius = self.GetDistClass.dist
               QadVariables.set(QadMsg.translate("Environment variables", "FILLETRAD"), self.radius)
               QadVariables.save()
            self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di distanza                     
         return False # fine comando
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DELLA MODALITA' DI TAGLIO (da step = 1)
      elif self.step == 4: # dopo aver atteso un punto o un numero reale si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            # la condizione seguente si verifica se durante la selezione di un punto
            # é stato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool é stato attivato senza un punto
               if self.getPointMapTool().rightButton == True: # se usato il tasto destro del mouse
                  value = self.filletMode
               else:
                  self.setMapTool(self.getPointMapTool()) # riattivo il maptool
                  return False
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            if value == QadMsg.translate("Command_FILLET", "Trim-extend") or value == "Trim-extend":
               self.filletMode = 1
            elif value == QadMsg.translate("Command_FILLET", "No trim-extend") or value == "No trim-extend":
               self.filletMode = 2
            self.plugIn.setFilletMode(self.filletMode)
            
         self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL RAGGIO DI RACCORDO (da step = 3)
      elif self.step == 5:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.radius = self.GetDistClass.dist
               QadVariables.set(QadMsg.translate("Environment variables", "FILLETRAD"), self.radius)
               QadVariables.save()
            self.WaitForPolyline()
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di distanza                     
         return False # fine comando
      
      #=========================================================================
      # RISPOSTA ALLA SELEZIONE SECONDO OGGETTO
      elif self.step == 6:
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
            else:
               value = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            value = msg

         if type(value) == unicode:
            # l'opzione Radius viene tradotta in italiano in "RAggio" nel contesto "waitForSecondEntSel"
            if value == QadMsg.translate("Command_FILLET", "Radius", "waitForSecondEntSel") or value == "Radius":
               if self.GetDistClass is not None:
                  del self.GetDistClass
               self.GetDistClass = QadGetDistClass(self.plugIn)
               prompt = QadMsg.translate("Command_FILLET", "Specify fillet radius <{0}>: ")
               self.GetDistClass.msg = prompt.format(str(self.radius))
               self.GetDistClass.dist = self.radius
               self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE
               self.step = 7
               self.GetDistClass.run(msgMapTool, msg)
               return False
                           
         elif type(value) == QgsPointXY: # se é stato selezionato un punto
            self.entity2.clear()
            self.qadPolyline2.removeAll()            

            if self.getPointMapTool().entity.isInitialized():
               if self.setEntityInfo(False, self.getPointMapTool().entity.layer, \
                                     self.getPointMapTool().entity.featureId, value) == True:
                  if self.getPointMapTool().shiftKey == True:
                     dummyRadius = self.radius
                     self.radius = 0
                     dummyFilletMode = self.filletMode
                     self.filletMode = 1 # modalità di raccordo; 1=Taglia-estendi
                     result = self.fillet()
                     self.radius = dummyRadius
                     self.filletMode = dummyFilletMode
                  else:
                     result = self.fillet()
                  
                  if result == False:
                     self.waitForSecondEntSel() # si appresta ad attendere la selezione del secondo oggetto         
                     return False 
                     
                  if self.multi:
                     self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
                     return False
                  else:
                     return True
            else:
               # cerco se ci sono entità nel punto indicato considerando
               # solo layer lineari o poligono editabili che non appartengano a quote
               layerList = []
               for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
                  if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
                     layer.isEditable():
                     if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                        layerList.append(layer)

               result = qad_utils.getEntSel(self.getPointMapTool().toCanvasCoordinates(value), \
                                            self.getPointMapTool(), \
                                            QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")), \
                                            layerList)
               if result is not None:
                  # result[0] = feature, result[1] = layer, result[0] = point
                  if self.setEntityInfo(False, result[1], result[0].id(), result[2]) == True:
                     if self.fillet() == False:
                        self.waitForSecondEntSel() # si appresta ad attendere la selezione del secondo oggetto         
                        return False 
               
                     if self.multi:
                        self.waitForFirstEntSel() # si appresta ad attendere la selezione del primo oggetto
                        return False
                     else:
                        return True
         else:
            return True # fine comando
         
         self.waitForSecondEntSel() # si appresta ad attendere la selezione del secondo oggetto         
         return False 

      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL RAGGIO DI RACCORDO (da step = 6)
      elif self.step == 7:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.radius = self.GetDistClass.dist
               QadVariables.set(QadMsg.translate("Environment variables", "FILLETRAD"), self.radius)
               QadVariables.save()      
            self.waitForSecondEntSel() # si appresta ad attendere la selezione del secondo oggetto
            self.getPointMapTool().refreshSnapType() # aggiorno lo snapType che può essere variato dal maptool di distanza                     
         return False # fine comando