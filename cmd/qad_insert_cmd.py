# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando INSERT per inserire un simbolo
 
                              -------------------
        begin                : 2013-12-31
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
from qgis.core import QgsGeometry, QgsFeature, QgsWkbTypes, QgsPointXY
from qgis.PyQt.QtGui import QIcon


from .. import qad_utils
from .qad_generic_cmd import QadCommandClass
from .. import qad_layer
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass
from ..qad_textwindow import QadInputModeEnum
from ..qad_msg import QadMsg
from ..qad_point import QadPoint


# Classe che gestisce il comando INSERT
class QadINSERTCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadINSERTCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "INSERT")

   def getEnglishName(self):
      return "INSERT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runINSERTCommand)
   
   def getIcon(self):
      return QIcon(":/plugins/qad/icons/insert.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_INSERT", "Insert a symbol.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.insPt = None
      self.scale = self.plugIn.lastScale
      self.rot = self.plugIn.lastRot
      self.GetDistClass = None
      self.GetAngleClass = None

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      # quando si é in fase di richiesta distanza (scala)
      if self.step == 2:
         return self.GetDistClass.getPointMapTool()
      # quando si é in fase di richiesta rotazione
      elif self.step == 3:
         return self.GetAngleClass.getPointMapTool()
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      # quando si é in fase di richiesta distanza (scala)
      if self.step == 2:
         return self.GetDistClass.getCurrentContextualMenu()
      # quando si é in fase di richiesta rotazione
      elif self.step == 3:
         return self.GetAngleClass.getCurrentContextualMenu()
      else:
         return self.contextualMenu


   def addFeature(self, layer):
      pt = QadPoint(self.insPt)
      g = self.mapToLayerCoordinates(layer, pt.asGeom(layer.wkbType()))
      f = QgsFeature()
      f.setGeometry(g)
      # Add attribute fields to feature.
      fields = layer.fields()
      f.setFields(fields)
      
      # assegno i valori di default
      provider = layer.dataProvider()
      for field in fields.toList():
         i = fields.indexFromName(field.name())
         f[field.name()] = provider.defaultValue(i)
      
      # se la scala dipende da un campo 
      scaleFldName = qad_layer.get_symbolScaleFieldName(layer)
      if len(scaleFldName) > 0:
         f.setAttribute(scaleFldName, self.scale)
      
      # se la rotazione dipende da un campo
      rotFldName = qad_layer.get_symbolRotationFieldName(layer)
      if len(rotFldName) > 0:
         f.setAttribute(rotFldName, qad_utils.toDegrees(self.rot))
      
      return qad_layer.addFeatureToLayer(self.plugIn, layer, f)               
      
      
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PointGeometry)
      if currLayer is None:
         self.showErr(errMsg)
         return True # fine comando

      if qad_layer.isSymbolLayer(currLayer) == False:
         errMsg = QadMsg.translate("QAD", "\nCurrent layer is not a symbol layer.")
         errMsg = errMsg + QadMsg.translate("QAD", "\nA symbol layer is a vector punctual layer without label.\n")
         self.showErr(errMsg)         
         return True # fine comando

               
      #=========================================================================
      # RICHIESTA PUNTO DI INSERIMENTO
      if self.step == 0: # inizio del comando
         self.waitForPoint() # si appresta ad attendere un punto
         self.step = self.step + 1
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA PUNTO DI INSERIMENTO
      elif self.step == 1: # dopo aver atteso un punto si riavvia il comando
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

            pt = self.getPointMapTool().point
         else: # il punto arriva come parametro della funzione
            pt = msg

         self.insPt = QgsPointXY(pt)
         self.plugIn.setLastPoint(self.insPt)
         
         # se la scala dipende da un campo 
         scaleFldName = qad_layer.get_symbolScaleFieldName(currLayer)
         if len(scaleFldName) > 0:
            # si appresta ad attendere la scala                      
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_INSERT", "Specify the symbol scale <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.scale))
            self.GetDistClass.dist = self.scale
            self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE | QadInputModeEnum.NOT_ZERO
            self.GetDistClass.startPt = self.insPt
            self.step = 2
            self.GetDistClass.run(msgMapTool, msg)
            return False
         else: 
            # se la rotazione dipende da un campo 
            rotFldName = qad_layer.get_symbolRotationFieldName(currLayer)
            if len(rotFldName) > 0:
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                  
               # si appresta ad attendere l'angolo di rotazione                      
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_INSERT", "Specify the symbol rotation <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
               self.GetAngleClass.angle = self.rot
               self.GetAngleClass.startPt = self.insPt               
               self.step = 3
               self.GetAngleClass.run(msgMapTool, msg)               
               return False
            else:
               self.addFeature(currLayer)

         return True
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA SCALA (da step = 1)
      elif self.step == 2:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.scale = self.GetDistClass.dist
               self.plugIn.setLastScale(self.scale)
               del self.GetDistClass
               self.GetDistClass = None
                
               # se la rotazione dipende da un campo 
               rotFldName = qad_layer.get_symbolRotationFieldName(currLayer)
               if len(rotFldName) > 0:
                  if self.GetAngleClass is not None:
                     del self.GetAngleClass                  
                  # si appresta ad attendere l'angolo di rotazione                      
                  self.GetAngleClass = QadGetAngleClass(self.plugIn)
                  prompt = QadMsg.translate("Command_INSERT", "Specify the symbol rotation <{0}>: ")
                  self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
                  self.GetAngleClass.angle = self.rot
                  self.GetAngleClass.startPt = self.insPt               
                  self.step = 3
                  self.GetAngleClass.run(msgMapTool, msg)         
                  return False
               else:
                  self.addFeature(currLayer)               
                  return True   
            else:
               return True   
         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ROTAZIONE (da step = 1 o 2)
      elif self.step == 3:
         if self.GetAngleClass.run(msgMapTool, msg) == True:
            if self.GetAngleClass.angle is not None:
               self.rot = self.GetAngleClass.angle
               self.plugIn.setLastRot(self.rot)
               self.addFeature(currLayer)
               return True # fine comando
            else:
               return True
         return False
