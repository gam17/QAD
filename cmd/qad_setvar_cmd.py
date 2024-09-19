# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando SETVAR per settare le variabili di ambiente di QAD
 
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


from .qad_generic_cmd import QadCommandClass
from ..qad_msg import QadMsg
from ..qad_variables import QadVariables, QadVariableTypeEnum


# Classe che gestisce il comando SETVAR
class QadSETVARCommandClass(QadCommandClass):

   def instantiateNewCmd(self):
      """ istanzia un nuovo comando dello stesso tipo """
      return QadSETVARCommandClass(self.plugIn)
   
   def getName(self):
      return QadMsg.translate("Command_list", "SETVAR")

   def getEnglishName(self):
      return "SETVAR"

   def connectQAction(self, action):
      action.triggered.connect(self.plugIn.runSETVARCommand)

   def getIcon(self):
      return QIcon(":/plugins/qad/icons/variable.svg")

   def getNote(self):
      # impostare le note esplicative del comando      
      return QadMsg.translate("Command_SETVAR", "Sets the QAD environment variables.")
   
   def __init__(self, plugIn):
      QadCommandClass.__init__(self, plugIn)
      self.varName = ""

         
   def run(self, msgMapTool = False, msg = None):
      if self.step == 0: # inizio del comando
         # si appresta ad attendere una stringa
         self.waitForString(QadMsg.translate("Command_SETVAR", "Enter the variable name or [?]: "), \
                            QadMsg.translate("Command_SETVAR", "?"))
         self.step = 1
         return False
      elif self.step == 1: # dopo aver atteso il nome della variabile si riavvia il comando
         if msgMapTool == True: # niente può arrivare da grafica
            return False
         #  il nome della variabile arriva come parametro della funzione
         self.varName = msg
         if self.varName == QadMsg.translate("Command_SETVAR", "?"): # lista delle variabili            
            # si appresta ad attendere una stringa            
            self.waitForString(QadMsg.translate("Command_SETVAR", "Enter variable(s) to list <*>: "), \
                               QadMsg.translate("Command_SETVAR", "*"))
            self.step = 3
            return False
         else:
            variable = QadVariables.getVariable(self.varName)
            if variable is None:               
               msg = QadMsg.translate("Command_SETVAR", "\nUnknown variable. Enter {0} ? to list variable names.")
               self.showErr(msg.format(QadMsg.translate("Command_list", "SETVAR")))
               return False
            else:
               varValue = variable.value
               varDescr = variable.descr
               varType  = variable.typeValue
               
               if len(varDescr) > 0:
                  self.showMsg("\n" + varDescr)
               
               msg = QadMsg.translate("Command_SETVAR", "Enter new value for variable {0} <{1}>: ")
               if varType == QadVariableTypeEnum.STRING:
                  # si appresta ad attendere una stringa
                  self.waitForString(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.INT:
                  # si appresta ad attendere un numero intero
                  self.waitForInt(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.FLOAT:
                  # si appresta ad attendere un numero reale
                  self.waitForFloat(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.BOOL:
                  # si appresta ad attendere un numero reale
                  self.waitForBool(msg.format(self.varName, varValue), varValue)
               elif varType == QadVariableTypeEnum.COLOR:
                  # si appresta ad attendere un COLORE #RRGGBB
                  self.waitForString(msg.format(self.varName, varValue), varValue)
               self.step = 2
               return False
      elif self.step == 2: # dopo aver atteso il valore della variabile si riavvia il comando
         if msgMapTool == True: # niente può arrivare da grafica
            return False
         # il valore della variabile arriva come parametro della funzione
         if QadVariables.set(self.varName, msg) == False: # valore non valido
            msg = QadMsg.translate("Command_SETVAR", "\nValue not valid.")
            self.showErr(msg)
            return False
         else: # valore valido
            QadVariables.save()
            self.plugIn.UpdatedVariablesEvent()
            return True
      elif self.step == 3: # dopo aver atteso il nome della variabile si riavvia il comando
         if msgMapTool == True: # niente può arrivare da grafica
            return False

         if msg == "*":
            varNames = QadVariables.getVarNames()
         else:
            #  il nome della variabile arriva come parametro della funzione
            varNames = msg.strip().split(",")
            
         varNames.sort()
         for self.varName in varNames:
            self.varName = self.varName.strip()
            varValue = QadVariables.get(self.varName)
            if varValue is not None:
               msg = "\n" + self.varName + "=" + str(varValue)
               self.showMsg(msg)
               
         self.plugIn.UpdatedVariablesEvent()
               
         return True