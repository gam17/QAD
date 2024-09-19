# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 comando TEXT per inserire un'etichetta
 
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
from qgis.core import QgsGeometry, QgsFeature, QgsFields, QgsField, QgsWkbTypes, QgsPointXY
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon


from .. import qad_utils
from .qad_generic_cmd import QadCommandClass
from .. import qad_layer
from .. import qad_label
from ..qad_getpoint import QadGetPointDrawModeEnum
from .qad_getdist_cmd import QadGetDistClass
from .qad_getangle_cmd import QadGetAngleClass
from ..qad_dim import QadDimStyles
from ..qad_textwindow import QadInputModeEnum
from ..qad_msg import QadMsg
from ..qad_point import QadPoint


# Classe che gestisce il comando TEXT
class QadTEXTCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadTEXTCommandClass(self.plugIn)

   def getName(self):
      return QadMsg.translate("Command_list", "TEXT")

   def getEnglishName(self):
      return "TEXT"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runTEXTCommand)
   
   def getIcon(self):
      return QIcon(":/plugins/qad/icons/text.svg")

   def getNote(self):
      # impostare le note esplicative del comando
      return QadMsg.translate("Command_TEXT", "Inserts a text.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.insPt = None
      self.hText = self.plugIn.lastHText
      self.rot = self.plugIn.lastRot
      self.GetDistClass = None
      self.GetAngleClass = None
      self.labelFields = None
      self.labelFieldNamesNdx = 0      
      self.labelFieldValues = []

   def __del__(self):
      QadCommandClass.__del__(self)
      if self.GetDistClass is not None:
         del self.GetDistClass
      if self.GetAngleClass is not None:
         del self.GetAngleClass


   def getPointMapTool(self, drawMode = QadGetPointDrawModeEnum.NONE):
      # quando si éin fase di richiesta distanza (altezza testo)
      if self.step == 2:
         return self.GetDistClass.getPointMapTool()
      # quando si éin fase di richiesta rotazione
      elif self.step == 3:
         return self.GetAngleClass.getPointMapTool()
      else:
         return QadCommandClass.getPointMapTool(self, drawMode)


   def getCurrentContextualMenu(self):
      # quando si éin fase di richiesta distanza (altezza testo)
      if self.step == 2:
         return self.GetDistClass.getCurrentContextualMenu()
      # quando si éin fase di richiesta rotazione
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
      
      # se l'altezza testo dipende da un solo campo 
      sizeFldNames = qad_label.get_labelSizeFieldNames(layer)
      if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
         f.setAttribute(sizeFldNames[0], self.hText)
      
      # se la rotazione dipende da un solo campo
      rotFldNames = qad_label.get_labelRotationFieldNames(layer)
      if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
         f.setAttribute(rotFldNames[0], qad_utils.toDegrees(self.rot))
         
      # setto i valori degli attributi che compongono l'etichetta
      i = 0
      tot = len(self.labelFields)
      while i < tot:
         f.setAttribute(self.labelFields[i].name(), self.labelFieldValues[i])
         i = i + 1
      
      return qad_layer.addFeatureToLayer(self.plugIn, layer, f, None, True, False, False)       

   def initLabelFields(self, layer):
      labelFieldNames = qad_label.get_labelFieldNames(layer)
      if len(labelFieldNames) > 0:
         self.labelFields = QgsFields()         
         for field in layer.dataProvider().fields():   
            if field.name() in labelFieldNames:
               self.labelFields.append(QgsField(field.name(), field.type()))
    
   #============================================================================
   # waitForFieldValue
   #============================================================================
   def waitForFieldValue(self):      
      self.step = 4      
      
      if self.labelFields is None:
         return False
      if self.labelFieldNamesNdx >= len(self.labelFields):
         return False
      field = self.labelFields[self.labelFieldNamesNdx]
      prompt = QadMsg.translate("Command_TEXT", "Enter the value of attribute \"{0}\": ").format(field.name())
      if field.type() == QVariant.Double: # si appresta ad attendere un double o valore nullo      
         self.waitForFloat(prompt, None, QadInputModeEnum.NONE)
      elif field.type() == QVariant.LongLong: # si appresta ad attendere un long a 64 bit o valore nullo       
         self.waitForLong(prompt, None, QadInputModeEnum.NONE)
      elif field.type() == QVariant.Int: # si appresta ad attendere un integer o valore nullo     
         self.waitForInt(prompt, None, QadInputModeEnum.NONE)
      elif field.type() == QVariant.Bool: # si appresta ad attendere un boolean o valore nullo
         self.waitForBool(prompt, None, QadInputModeEnum.NONE)
      else: # si appresta ad attendere una stringa o valore nullo
         self.waitForString(prompt, None, QadInputModeEnum.NONE)
                  
      return True
   
      
   def run(self, msgMapTool = False, msg = None):
      if self.plugIn.canvas.mapSettings().destinationCrs().isGeographic():
         self.showMsg(QadMsg.translate("QAD", "\nThe coordinate reference system of the project must be a projected coordinate system.\n"))
         return True # fine comando
      
      currLayer, errMsg = qad_layer.getCurrLayerEditable(self.plugIn.canvas, QgsWkbTypes.PointGeometry)
      if currLayer is None:
         self.showErr(errMsg)
         return True # fine comando

      if qad_layer.isTextLayer(currLayer) == False:
         errMsg = QadMsg.translate("QAD", "\nCurrent layer is not a textual layer.")
         errMsg = errMsg + QadMsg.translate("QAD", "\nA textual layer is a vector punctual layer having a label and the symbol transparency no more than 10%.\n")
         self.showErr(errMsg)         
         return True # fine comando

      if  len(QadDimStyles.getDimListByLayer(currLayer)) > 0:
         errMsg = QadMsg.translate("QAD", "\nThe current layer belongs to a dimension style.\n")
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
            # éstato attivato un altro plugin che ha disattivato Qad
            # quindi stato riattivato il comando che torna qui senza che il maptool
            # abbia selezionato un punto            
            if self.getPointMapTool().point is None: # il maptool éstato attivato senza un punto
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
         
         # se l'altezza testo dipende da un solo campo 
         sizeFldNames = qad_label.get_labelSizeFieldNames(currLayer)
         if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
            # si appresta ad attendere la scala                      
            self.GetDistClass = QadGetDistClass(self.plugIn)
            prompt = QadMsg.translate("Command_TEXT", "Specify the text height <{0}>: ")
            self.GetDistClass.msg = prompt.format(str(self.hText))
            self.GetDistClass.dist = self.hText
            self.GetDistClass.inputMode = QadInputModeEnum.NOT_NEGATIVE | QadInputModeEnum.NOT_ZERO
            self.GetDistClass.startPt = self.insPt
            self.step = 2
            self.GetDistClass.run(msgMapTool, msg)
            return False
         else: 
            # se la rotazione dipende da un solo campo
            rotFldNames = qad_label.get_labelRotationFieldNames(currLayer)
            if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
               if self.GetAngleClass is not None:
                  del self.GetAngleClass                  
               # si appresta ad attendere l'angolo di rotazione                      
               self.GetAngleClass = QadGetAngleClass(self.plugIn)
               prompt = QadMsg.translate("Command_TEXT", "Specify the text rotation <{0}>: ")
               self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
               self.GetAngleClass.angle = self.rot
               self.GetAngleClass.startPt = self.insPt               
               self.step = 3
               self.GetAngleClass.run(msgMapTool, msg)               
               return False
            else:
               self.initLabelFields(currLayer)
               if self.waitForFieldValue() == False:
                  self.addFeature(currLayer)
                  return True

         return False
      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA ALTEZZA TESTO (da step = 1)
      elif self.step == 2:
         if self.GetDistClass.run(msgMapTool, msg) == True:
            if self.GetDistClass.dist is not None:
               self.hText = self.GetDistClass.dist
               self.plugIn.setLastHText(self.hText)
               del self.GetDistClass
               self.GetDistClass = None
                
               # se la rotazione dipende da un solo campo
               rotFldNames = qad_label.get_labelRotationFieldNames(currLayer)
               if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
                  if self.GetAngleClass is not None:
                     del self.GetAngleClass                  
                  # si appresta ad attendere l'angolo di rotazione                      
                  self.GetAngleClass = QadGetAngleClass(self.plugIn)
                  prompt = QadMsg.translate("Command_TEXT", "Specify the text rotation <{0}>: ")
                  self.GetAngleClass.msg = prompt.format(str(qad_utils.toDegrees(self.rot)))
                  self.GetAngleClass.angle = self.rot
                  self.GetAngleClass.startPt = self.insPt               
                  self.step = 3
                  self.GetAngleClass.run(msgMapTool, msg)         
                  return False
               else:
                  self.initLabelFields(currLayer)
                  if self.waitForFieldValue() == False:
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
               self.initLabelFields(currLayer)
               if self.waitForFieldValue() == False:
                  self.addFeature(currLayer)
                  return True # fine comando               
            else:
               return True
         return False

      
      #=========================================================================
      # RISPOSTA ALLA RICHIESTA DEL VALORE DI UN CAMPO
      elif self.step == 4: # dopo aver atteso un valore si riavvia il comando
         if msgMapTool == True: # il punto arriva da una selezione grafica
            self.waitForFieldValue()
            return False
         # il valore arriva come parametro della funzione
         self.labelFieldValues.append(msg)
         self.labelFieldNamesNdx = self.labelFieldNamesNdx + 1 
         if self.waitForFieldValue() == False:
            self.addFeature(currLayer)
            return True # fine comando
         
         return False
         
