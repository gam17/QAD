# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 Gestione dei click destro del mouse di QAD
 
                              -------------------
        begin                : 2016-17-02
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
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.utils import *
from qgis.gui import *


from .qad_rightclick_ui import Ui_RightClick_Dialog


from .qad_variables import QadVariables, QadVariable
from .qad_msg import QadMsg, qadShowPluginPDFHelp
from . import qad_utils


#######################################################################################
# Classe che gestisce l'interfaccia grafica per il click destro del mouse
class QadRightClickDialog(QDialog, QObject, Ui_RightClick_Dialog):
   def __init__(self, plugIn, parent):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self, parent)

      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      
      # Inizializzazione dei valori
      self.init_values()

   
   def eventFilter(self, obj, event):
      if event is not None:
         if event.type() == QEvent.FocusOut:
            if obj == self.lineEdit_duration:
               return not self.lineEdit_SHORTCUTMENUDURATION_Validation()

      # standard event processing
      return QObject.eventFilter(self, obj, event);


   # ============================================================================
   # timeSensitive_clicked
   # ============================================================================
   def timeSensitive_clicked(self):
      if self.checkBox_timeSensitive.checkState() == Qt.Checked:
         self.lineEdit_duration.setEnabled(True)
         self.groupBox_default.setEnabled(False)
         self.groupBox_command.setEnabled(False)
      else:
         self.lineEdit_duration.setEnabled(False)
         self.groupBox_default.setEnabled(True)
         self.groupBox_command.setEnabled(True)


   def lineEdit_SHORTCUTMENUDURATION_Validation(self):
      varName = QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION")
      var = QadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_duration, \
                                                   var, \
                                                   QadMsg.translate("RightClick_Dialog", "Invalid duration time"))

   
   # ============================================================================
   # init_values
   # ============================================================================
   def init_values(self):
      # Inizializzazione dei valori
      shortCutMenu = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENU"))
      if shortCutMenu == 0:
         shortCutMenu = 11 # inizializzo questo default
      shortCutMenuDuration = QadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION"))

      self.lineEdit_duration.setText(str(shortCutMenuDuration))
      self.lineEdit_duration.setValidator(QIntValidator(self.lineEdit_duration))
      self.lineEdit_duration.installEventFilter(self)

      # 1 = Enables Default mode shortcut menus
      if shortCutMenu & 1:
         self.radioButton_default_shortcut.setChecked(True)
      else:
         self.radioButton_default_last_cmd.setChecked(True)
         
      # 2 = Enables Edit mode shortcut menus
      if shortCutMenu & 2:
         self.radioButton_edit_shortcut.setChecked(True)
      else:
         self.radioButton_edit_last_cmd.setChecked(True)

      # 4 = Enables Command mode shortcut menus whenever a command is active. 
      if shortCutMenu & 4:
         self.radioButton_cmd_shortcut.setChecked(True)
      else:
         # 8 = Enables Command mode shortcut menus only when command options are currently available at the Command prompt. 
         if shortCutMenu & 8:
            self.radioButton_cmd_shortcut_with_options.setChecked(True)
         else:
            self.radioButton_cmd_enter.setChecked(True)

      # 16 = Enables the display of a shortcut menu when the right button on the pointing device is held down long enough
      if shortCutMenu & 16:
         self.checkBox_timeSensitive.setChecked(True)

      self.timeSensitive_clicked()


   # ============================================================================
   # getShortCutMenuValue
   # ============================================================================   
   def getShortCutMenuValue(self):
      # ritorna la composizione bit a bit della variabile SHORTCUTMENU leggendo i valori dei vari widget della dialog
      shortCutMenu = 0
      # 1 = Enables Default mode shortcut menus
      if self.radioButton_default_shortcut.isChecked():
         shortCutMenu = shortCutMenu | 1
         
      # 2 = Enables Edit mode shortcut menus
      if self.radioButton_edit_shortcut.isChecked():
         shortCutMenu = shortCutMenu | 2
         
      # 4 = Enables Command mode shortcut menus whenever a command is active. 
      if self.radioButton_cmd_shortcut.isChecked():
         shortCutMenu = shortCutMenu | 4

      # 8 = Enables Command mode shortcut menus only when command options are currently available at the Command prompt. 
      if self.radioButton_cmd_shortcut_with_options.isChecked():
         shortCutMenu = shortCutMenu | 8

      # 16 = Enables the display of a shortcut menu when the right button on the pointing device is held down long enough
      if self.checkBox_timeSensitive.checkState() == Qt.Checked:
         shortCutMenu = shortCutMenu | 16

      return shortCutMenu


   # ============================================================================
   # getSysVariableList
   # ============================================================================
   def getSysVariableList(self):
      # ritorna una lista di variabili gestite da questa finestra
      variables = []
      
      variable = QadVariables.getVariable(QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION"))
      varValue = qad_utils.str2int(self.lineEdit_duration.text())
      variables.append(QadVariable(variable.name, varValue, variable.typeValue))

      variable = QadVariables.getVariable(QadMsg.translate("Environment variables", "SHORTCUTMENU"))
      varValue = self.getShortCutMenuValue()
      variables.append(QadVariable(variable.name, varValue, variable.typeValue))
      
      return variables


   # ============================================================================
   # applyClose_clicked
   # ============================================================================
   def applyClose_clicked(self):
      # Memorizzo il valore di SHORTCUTMENUDURATION
      value = self.lineEdit_duration.text()
      shortCutMenuDuration = qad_utils.str2int(value)
      QadVariables.set(QadMsg.translate("Environment variables", "SHORTCUTMENUDURATION"), shortCutMenuDuration)

      shortCutMenu = self.getShortCutMenuValue()
      QadVariables.set(QadMsg.translate("Environment variables", "SHORTCUTMENU"), shortCutMenu)

      QDialog.accept(self)


   # ============================================================================
   # cancel_clicked
   # ============================================================================
   def cancel_clicked(self):
      QDialog.reject(self)


   # ============================================================================
   # help_clicked
   # ============================================================================
   def help_clicked(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", ""))
