# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando DSETTINGS per impostazione disegno
 
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
from qgis.PyQt.QtCore import Qt, QObject, QEvent
from qgis.PyQt.QtGui import QDoubleValidator, QIntValidator, QColor, QPainter, \
     QFontMetrics, QStandardItemModel, QStandardItem
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTextEdit, QSizePolicy, \
     QWidget, QInputDialog

from . import qad_dsettings_ui
from . import qad_dimensioninput_settings_ui
from . import qad_pointerinput_settings_ui
from . import qad_tooltip_appearance_ui


from .qad_variables import QadVariable, QadVariables, QadAUTOSNAPEnum, QadPOLARMODEnum, POLARADDANG_to_list
from .qad_snapper import QadSnapTypeEnum
from .qad_msg import QadMsg, qadShowPluginPDFHelp
from . import qad_utils
from .qad_windowcolor_dlg import QadColorContextEnum, QadColorElementEnum, QadWindowColorDialog


# ===============================================================================
# QadDSETTINGSTabIndexEnum class.
# ===============================================================================
class QadDSETTINGSTabIndexEnum():
   OBJECT_SNAP    = 0
   POLAR_TRACKING = 1
   DYNAMIC_INPUT = 2


#######################################################################################
# Classe che gestisce l'interfaccia grafica del comando DSETTINGS
class QadDSETTINGSDialog(QDialog, QObject, qad_dsettings_ui.Ui_DSettings_Dialog):
   def __init__(self, plugIn, dsettingsTabIndex = None):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self)
      # non passo il parent perchè altrimenti il font e la sua dimensione verrebbero ereditati dalla dialog scombinando tutto 
      #QDialog.__init__(self, self.iface)

      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      
      # Inizializzazione del TAB che riguarda gli SNAP ad oggetto
      self.init_osnap_tab()
      
      # Inizializzazione del TAB che riguarda il puntamento polare
      self.init_polar_tab()
      
      # Inizializzazione del TAB che riguarda l'input dinamico
      self.init_dynamic_input_tab()
      
      if dsettingsTabIndex is not None:
         self.tabWidget.setCurrentIndex(dsettingsTabIndex)
      else:
         if self.plugIn.dsettingsLastUsedTabIndex == -1: # non inizializzato
            self.plugIn.dsettingsLastUsedTabIndex = QadDSETTINGSTabIndexEnum.OBJECT_SNAP
         self.tabWidget.setCurrentIndex(self.plugIn.dsettingsLastUsedTabIndex)
            

   ######################################
   # TAB che riguarda gli SNAP ad oggetto
   def init_osnap_tab(self):
      # Inizializzazione del TAB che riguarda gli SNAP ad oggetto
      
      # Memorizzo il valore dell'OSMODE per determinare gli osnap impostati
      OsMode = QadVariables.get(QadMsg.translate("Environment variables", "OSMODE"))
      self.checkBox_CENP.setChecked(OsMode & QadSnapTypeEnum.CEN)
      self.checkBox_ENDP.setChecked(OsMode & QadSnapTypeEnum.END)
      self.checkBox_END_PLINE.setChecked(OsMode & QadSnapTypeEnum.END_PLINE)
      self.checkBox_EXTP.setChecked(OsMode & QadSnapTypeEnum.EXT)
      self.checkBox_INTP.setChecked(OsMode & QadSnapTypeEnum.INT)
      self.checkBox_MIDP.setChecked(OsMode & QadSnapTypeEnum.MID)
      self.checkBox_NODP.setChecked(OsMode & QadSnapTypeEnum.NOD)
      self.checkBox_QUADP.setChecked(OsMode & QadSnapTypeEnum.QUA)
      #self.checkBox_INSP.setChecked(OsMode & QadSnapTypeEnum.INS)
      #self.checkBox_INTAPP.setChecked(OsMode & QadSnapTypeEnum.APP)
      self.checkBox_NEARP.setChecked(OsMode & QadSnapTypeEnum.NEA)
      self.checkBox_PERP.setChecked(OsMode & QadSnapTypeEnum.PER)
      self.checkBox_PARALP.setChecked(OsMode & QadSnapTypeEnum.PAR)
      self.checkBox_PROGRESP.setChecked(OsMode & QadSnapTypeEnum.PR)
      self.checkBox_TANP.setChecked(OsMode & QadSnapTypeEnum.TAN)
      self.checkBox_EXT_INT.setChecked(OsMode & QadSnapTypeEnum.EXT_INT)
      self.checkBox_TANP.setChecked(OsMode & QadSnapTypeEnum.TAN)
      
      self.checkBox_IsOsnapON.setChecked(not(OsMode & QadSnapTypeEnum.DISABLE))

      AutoSnap = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))
      self.checkBox_ObjectSnapTracking.setChecked(AutoSnap & QadAUTOSNAPEnum.OBJ_SNAP_TRACKING)

      ProgrDistance = QadVariables.get(QadMsg.translate("Environment variables", "OSPROGRDISTANCE"))
      stringA = str(ProgrDistance)
      self.lineEdit_ProgrDistance.setText(stringA)
      self.lineEdit_ProgrDistance.setValidator(QDoubleValidator(self.lineEdit_ProgrDistance))
      self.lineEdit_ProgrDistance.installEventFilter(self)
      

   def accept_osnap_tab(self):
      # Memorizzo il valore di OSMODE
      newOSMODE = 0
      if self.checkBox_CENP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.CEN
      if self.checkBox_ENDP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.END
      if self.checkBox_END_PLINE.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.END_PLINE
      if self.checkBox_EXTP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.EXT
      if self.checkBox_INTP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.INT
      if self.checkBox_MIDP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.MID
      if self.checkBox_NODP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.NOD
      if self.checkBox_QUADP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.QUA
      #if self.checkBox_INSP.checkState() == Qt.Checked:
      #   newOSMODE = newOSMODE | QadSnapTypeEnum.INS
      #if self.checkBox_INTAPP.checkState() == Qt.Checked:
      #   newOSMODE = newOSMODE | QadSnapTypeEnum.APP
      if self.checkBox_NEARP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.NEA
      if self.checkBox_PARALP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.PAR
      if self.checkBox_PERP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.PER
      if self.checkBox_PROGRESP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.PR
      if self.checkBox_TANP.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.TAN
      if self.checkBox_EXT_INT.checkState() == Qt.Checked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.EXT_INT
      if self.checkBox_IsOsnapON.checkState() == Qt.Unchecked:
         newOSMODE = newOSMODE | QadSnapTypeEnum.DISABLE
      QadVariables.set(QadMsg.translate("Environment variables", "OSMODE"), newOSMODE)

      # Memorizzo il valore di OSPROGRDISTANCE
      SProgrDist = self.lineEdit_ProgrDistance.text()
      ProgrDist = qad_utils.str2float(SProgrDist)
      QadVariables.set(QadMsg.translate("Environment variables", "OSPROGRDISTANCE"), ProgrDist)
      
      # Memorizzo il valore di AUTOSNAP
      AutoSnap = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))      
      if self.checkBox_ObjectSnapTracking.checkState() == Qt.Checked:
         AutoSnap = AutoSnap | QadAUTOSNAPEnum.OBJ_SNAP_TRACKING
      elif AutoSnap & QadAUTOSNAPEnum.OBJ_SNAP_TRACKING:
         AutoSnap = AutoSnap - QadAUTOSNAPEnum.OBJ_SNAP_TRACKING
      QadVariables.set(QadMsg.translate("Environment variables", "AUTOSNAP"), AutoSnap)


   def ButtonSelectALL_Pressed(self):
      self.checkBox_CENP.setChecked(True)
      self.checkBox_ENDP.setChecked(True)
      self.checkBox_END_PLINE.setChecked(True)
      self.checkBox_EXTP.setChecked(True)
      self.checkBox_INTP.setChecked(True)
      self.checkBox_MIDP.setChecked(True)
      self.checkBox_NODP.setChecked(True)
      self.checkBox_QUADP.setChecked(True)
      #self.checkBox_INSP.setChecked(True)
      #self.checkBox_INTAPP.setChecked(True)
      self.checkBox_NEARP.setChecked(True)
      self.checkBox_PARALP.setChecked(True)
      self.checkBox_PERP.setChecked(True)
      self.checkBox_PROGRESP.setChecked(True)
      self.checkBox_TANP.setChecked(True)
      self.checkBox_EXT_INT.setChecked(True)
      return True
  

   def ButtonDeselectALL_Pressed(self):
      self.checkBox_CENP.setChecked(False)
      self.checkBox_ENDP.setChecked(False)
      self.checkBox_END_PLINE.setChecked(False)
      self.checkBox_EXTP.setChecked(False)
      self.checkBox_INTP.setChecked(False)
      self.checkBox_MIDP.setChecked(False)
      self.checkBox_NODP.setChecked(False)
      self.checkBox_QUADP.setChecked(False)
      #self.checkBox_INSP.setChecked(False)
      #self.checkBox_INTAPP.setChecked(False)
      self.checkBox_NEARP.setChecked(False)
      self.checkBox_PARALP.setChecked(False)
      self.checkBox_PERP.setChecked(False)
      self.checkBox_PROGRESP.setChecked(False)
      self.checkBox_TANP.setChecked(False)
      self.checkBox_EXT_INT.setChecked(False)
      return True


   def lineEdit_ProgrDistance_Validation(self):
      string = self.lineEdit_ProgrDistance.text()
      if qad_utils.str2float(string) is None or qad_utils.str2float(string) == 0:
         msg = QadMsg.translate("DSettings_Dialog", "Invalid progressive distance object snap: enter a number not zero.")
         QMessageBox.critical(self, QadMsg.getQADTitle(), msg)
         self.lineEdit_ProgrDistance.setFocus()
         self.lineEdit_ProgrDistance.selectAll()
         return False
      return True


   ######################################
   # TAB che riguarda il puntamento polare
   def init_polar_tab(self):
      # Inizializzazione del TAB che riguarda il puntamento polare
      UserAngle = QadVariables.get(QadMsg.translate("Environment variables", "POLARANG"))
      angoliDef = ["90", "45", "30", "22.5", "18", "15", "10", "5"]
      self.comboBox_increment_angle.addItems(angoliDef)
      stringA = str(UserAngle)
      self.comboBox_increment_angle.lineEdit().setText(stringA)
      self.comboBox_increment_angle.installEventFilter(self)
      
      AutoSnap = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))
      self.checkBox_PolarPickPoint.setChecked(AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING)

      PolarMode = QadVariables.get(QadMsg.translate("Environment variables", "POLARMODE"))
      if PolarMode & QadPOLARMODEnum.POLAR_TRACKING:
         self.radioButton_OsnapPolarAngle.setChecked(True)
      else:
         self.radioButton_OsnapOrtho.setChecked(True)

      if PolarMode & QadPOLARMODEnum.MEASURE_RELATIVE_ANGLE:
         self.radioButton_OsnapPolarRelative.setChecked(True)
      else:
         self.radioButton_OsnapPolarAbolute.setChecked(True)

      if PolarMode & QadPOLARMODEnum.ADDITIONAL_ANGLES:
         self.checkBox_AdditionaltAngles.setChecked(True)
      self.CheckAdditionalAngles()

      PolarAddAngles = QadVariables.get(QadMsg.translate("Environment variables", "POLARADDANG"))
      
      addAngleList = POLARADDANG_to_list(PolarAddAngles) # es. "1;2.3" genera la lista in ordine crescente 1 2.3
      model = QStandardItemModel()
      self.listView_AdditionalAngles.setModel(model)      
      for addAngle in addAngleList:
         item = QStandardItem(qad_utils.numToStringFmt(addAngle))
         item.setEditable(False)
         model.appendRow(item)
              

   def accept_polar_tab(self):
      # Memorizzo il valore di AUTOSNAP
      AutoSnap = QadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))
      if self.checkBox_PolarPickPoint.checkState() == Qt.Checked:
         AutoSnap = AutoSnap | QadAUTOSNAPEnum.POLAR_TRACKING
      elif AutoSnap & QadAUTOSNAPEnum.POLAR_TRACKING:
         AutoSnap = AutoSnap - QadAUTOSNAPEnum.POLAR_TRACKING
      QadVariables.set(QadMsg.translate("Environment variables", "AUTOSNAP"), AutoSnap)
      
      # Memorizzo il valore di POLARANG
      SUserAngle = self.comboBox_increment_angle.currentText()
      UserAngle = qad_utils.str2float(SUserAngle)
      QadVariables.set(QadMsg.translate("Environment variables", "POLARANG"), UserAngle)

      # Memorizzo il valore di POLARMODE
      PolarMode = 0
      if self.radioButton_OsnapPolarAngle.isChecked():
         PolarMode = PolarMode | QadPOLARMODEnum.POLAR_TRACKING
      if self.radioButton_OsnapPolarRelative.isChecked():
         PolarMode = PolarMode | QadPOLARMODEnum.MEASURE_RELATIVE_ANGLE
      if self.checkBox_AdditionaltAngles.isChecked():         
         PolarMode = PolarMode | QadPOLARMODEnum.ADDITIONAL_ANGLES
      QadVariables.set(QadMsg.translate("Environment variables", "POLARMODE"), PolarMode)
      
      # Memorizzo il valore di POLARADDANG
      PolarAddAngles = ""
      model = self.listView_AdditionalAngles.model()
      for row in range(0, model.rowCount()):
         index = model.index(row, 0)
         if row > 0:
            PolarAddAngles += ";"
         PolarAddAngles += index.data()         
      QadVariables.set(QadMsg.translate("Environment variables", "POLARADDANG"), PolarAddAngles)
    
    
   def comboBox_increment_angle_Validation(self):
      string = self.comboBox_increment_angle.lineEdit().text()
      if qad_utils.str2float(string) is None or qad_utils.str2float(string) <= 0 or qad_utils.str2float(string) >= 360:
         msg = QadMsg.translate("DSettings_Dialog", "Invalid increment angle: enter a number greater than zero and less than 360 degree.")
         QMessageBox.critical(self, QadMsg.getQADTitle(), msg) 
         self.comboBox_increment_angle.lineEdit().setFocus()
         self.comboBox_increment_angle.lineEdit().selectAll()
         return False
      return True


   def CheckAdditionalAngles(self):
      if self.checkBox_AdditionaltAngles.checkState() == Qt.Checked:
         self.pushButton_DelAngle.setEnabled(True)
         self.listView_AdditionalAngles.setEnabled(True)
      else:
         self.pushButton_DelAngle.setEnabled(False)
         self.listView_AdditionalAngles.setEnabled(False)


   def ButtonNewAngle(self):
      self.checkBox_AdditionaltAngles.setChecked(True)
      self.CheckAdditionalAngles()
      
      while True:
         # restituisce (valore, True o False a seconda del tasto OK o Cancel)
         res = QInputDialog.getDouble(self, 
                                      QadMsg.translate("DSettings_Dialog", "QAD - Additional angle"), \
                                      QadMsg.translate("DSettings_Dialog", "New angle:"), \
                                      0, -360, 360, 8)
         if res[1] == False:
            return
         newAngle = res[0]
         reAsk = False
         # controllo che l'angolo non sia già presente
         model = self.listView_AdditionalAngles.model()
         for row in range(0, model.rowCount()):
            index = model.index(row, 0)
            angle = qad_utils.str2float(index.data())
            if newAngle == angle:
               QMessageBox.critical(self, QadMsg.getQADTitle(), \
                                    QadMsg.translate("DSettings_Dialog", "Angle already in list"))
               reAsk = True
               break
            if newAngle < angle:
               item = QStandardItem(qad_utils.numToStringFmt(newAngle))
               item.setEditable(False)
               model.insertRow(row, item)
               return
         
         if reAsk == False:
            item = QStandardItem(qad_utils.numToStringFmt(newAngle))
            item.setEditable(False)
            model.appendRow(item)
            return                                   


   def ButtonDelAngle(self):
      # cancello le righe selezionate (devo ordinarle in modo inverso)
      indexes = self.listView_AdditionalAngles.selectedIndexes()
      for index in reversed(sorted(indexes)):
         self.listView_AdditionalAngles.model().removeRow(index.row())
      


   ######################################
   # TAB che riguarda l'input dinamico
   def init_dynamic_input_tab(self):
      # Inizializzazione del TAB che riguarda l'input dinamico
      
      # Memorizzo il valore di DYNMODE = Attiva e disattiva le funzioni di input dinamico
      dynMode = QadVariables.get(QadMsg.translate("Environment variables", "DYNMODE"))
      self.checkBox_DI_EnableInputPointer.setChecked(abs(dynMode) & 1)
      self.checkBox_DI_EnableDimPointer.setChecked(abs(dynMode) & 2)
            
      # Memorizzo il valore di DYNPROMPT = Controlla la visualizzazione dei messaggi di richiesta nelle descrizioni di input dinamico
      dynPrompt = QadVariables.get(QadMsg.translate("Environment variables", "DYNPROMPT"))
      self.checkBox_DI_ShowPrompt.setChecked(dynPrompt == 1)


   def Button_DI_DimensionInputSettings_Pressed(self):
      Form = QadDIMINPUTDialog(self.plugIn, self)
      Form.exec_()

   
   def Button_DI_PointerInputSettings_Pressed(self):
      Form = QadPOINTERINPUTDialog(self.plugIn, self)
      Form.exec_()


   def Button_DI_TootipAppearance_Pressed(self):
      Form = QadTOOLTIPAPPEARANCEDialog(self.plugIn, self)
      Form.exec_()


   def accept_dynamic_input_tab(self):
      # Memorizzo il valore di DYNMODE = Attiva e disattiva le funzioni di input dinamico
      dynMode = 0
      if self.checkBox_DI_EnableInputPointer.checkState() == Qt.Checked:
         dynMode = dynMode + 1
      if self.checkBox_DI_EnableDimPointer.checkState() == Qt.Checked:
         dynMode = dynMode + 2
      
      if QadVariables.get(QadMsg.translate("Environment variables", "DYNMODE")) < 0:
         dynMode = -dynMode
      QadVariables.set(QadMsg.translate("Environment variables", "DYNMODE"), dynMode)
            
      # Memorizzo il valore di DYNPROMPT = Controlla la visualizzazione dei messaggi di richiesta nelle descrizioni di input dinamico
      dynPrompt = 1 if self.checkBox_DI_ShowPrompt.checkState() == Qt.Checked else 0
      QadVariables.set(QadMsg.translate("Environment variables", "DYNPROMPT"), dynPrompt)


   ######################################
   # Funzioni generiche
   def eventFilter(self, obj, event):
      if event is not None:
         if event.type() == QEvent.FocusOut:
            if obj == self.lineEdit_ProgrDistance:
               return not self.lineEdit_ProgrDistance_Validation()
            elif obj == self.comboBox_increment_angle:
               return not self.comboBox_increment_angle_Validation()            

      # standard event processing
      return QObject.eventFilter(self, obj, event);


   def ButtonBOX_Accepted(self):
      self.accept_osnap_tab() # salvo i valori del tab "object snap"
      self.accept_polar_tab() # salvo i valori del tab "polar tracking"
      self.accept_dynamic_input_tab() # salvo i valori del tab "dynamic input"
      
      QadVariables.save()

      self.plugIn.dsettingsLastUsedTabIndex = self.tabWidget.currentIndex()
      
      QDialog.accept(self)


   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "DSETTINGS"))


#######################################################################################
# Classe che gestisce l'interfaccia grafica dei settaggi dell'input di quota
class QadDIMINPUTDialog(QDialog, QObject, qad_dimensioninput_settings_ui.Ui_DimInput_Settings_Dialog):
   def __init__(self, plugIn, parent):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self, parent)

      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      
      # Inizializzazione della finestra
      self.init()

      
   def init(self):
      # Memorizzo il valore di DYNDIVIS = Controlla il numero di quote dinamiche visualizzate durante la modifica dello stiramento dei grip
      dynDiVis = QadVariables.get(QadMsg.translate("Environment variables", "DYNDIVIS"))
      if dynDiVis == 0:
         self.radioShow1Dim.setChecked(True)
         self.radioShow2Dim.setChecked(False)
         self.radioShowMoreDim.setChecked(False)
      elif dynDiVis == 1:
         self.radioShow1Dim.setChecked(False)
         self.radioShow2Dim.setChecked(True)
         self.radioShowMoreDim.setChecked(False)
      elif dynDiVis == 2:
         self.radioShow1Dim.setChecked(False)
         self.radioShow2Dim.setChecked(False)
         self.radioShowMoreDim.setChecked(True)
         
      # Memorizzo il valore di DYNDIGRIP = Controlla la visualizzazione delle quote dinamiche durante la modifica dello stiramento dei grip
      dynDiGrip = QadVariables.get(QadMsg.translate("Environment variables", "DYNDIGRIP"))
      if dynDiGrip & 1:
         self.checkResultingDim.setChecked(True)
      if dynDiGrip & 2:
         self.checkLengthChange.setChecked(True)
      if dynDiGrip & 4:
         self.checkAbsoluteAngle.setChecked(True)
      if dynDiGrip & 8:
         self.checkAngleChange.setChecked(True)
         
      self.radioShowMoreDimChecked()


   def refreshOnRadioShowDimChecked(self):
      value = True if self.radioShowMoreDim.isChecked() else False 
      self.checkResultingDim.setEnabled(value)
      self.checkLengthChange.setEnabled(value)
      self.checkAbsoluteAngle.setEnabled(value)
      self.checkAngleChange.setEnabled(value)


   def radioShow1DimChecked(self):
      self.refreshOnRadioShowDimChecked()


   def radioShow2DimChecked(self):
      self.refreshOnRadioShowDimChecked()


   def radioShowMoreDimChecked(self):
      self.refreshOnRadioShowDimChecked()


   def ButtonBOX_Accepted(self):
      # Memorizzo il valore di DYNDIVIS = Controlla il numero di quote dinamiche visualizzate durante la modifica dello stiramento dei grip
      if self.radioShow1Dim.isChecked():
         dynDiVis = 0
      elif self.radioShow2Dim.isChecked():
         dynDiVis = 1
      elif self.radioShowMoreDim.isChecked():
         dynDiVis = 2
      
      QadVariables.set(QadMsg.translate("Environment variables", "DYNDIVIS"), dynDiVis)

      # Memorizzo il valore di DYNDIGRIP = Controlla la visualizzazione delle quote dinamiche durante la modifica dello stiramento dei grip
      dynDiGrip = 0
      if self.checkResultingDim.checkState() == Qt.Checked:
         dynDiGrip = dynDiGrip + 1
      if self.checkLengthChange.checkState() == Qt.Checked:
         dynDiGrip = dynDiGrip + 2
      if self.checkAbsoluteAngle.checkState() == Qt.Checked:
         dynDiGrip = dynDiGrip + 4
      if self.checkAngleChange.checkState() == Qt.Checked:
         dynDiGrip = dynDiGrip + 8
      QadVariables.set(QadMsg.translate("Environment variables", "DYNDIGRIP"), dynDiGrip)
      
      QadVariables.save()
      QDialog.accept(self)


   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "DSETTINGS"))


#######################################################################################
# Classe che gestisce l'interfaccia grafica dei settaggi dell'input di quota
class QadPOINTERINPUTDialog(QDialog, QObject, qad_pointerinput_settings_ui.Ui_PointerInput_Settings_Dialog):
   def __init__(self, plugIn, parent):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()

      QDialog.__init__(self, parent)

      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      
      # Inizializzazione della finestra
      self.init()


   def init(self):
      # Memorizzo il valore di DYNPIFORMAT = Determina se l'input del puntatore utilizza un formato polare o cartesiano per le coordinate
      dynPiFormat = QadVariables.get(QadMsg.translate("Environment variables", "DYNPIFORMAT"))
      if dynPiFormat == 0:
         self.radioPolarFmt.setChecked(True)
         self.radioCartesianFmt.setChecked(False)
      elif dynPiFormat == 1:
         self.radioPolarFmt.setChecked(False)
         self.radioCartesianFmt.setChecked(True)
         
      # Memorizzo il valore di DYNPICOORDS = Determina se l'input del puntatore utilizza un formato relativo o assoluto per le coordinate
      dynPiCoords = QadVariables.get(QadMsg.translate("Environment variables", "DYNPICOORDS"))
      if dynPiCoords == 0:
         self.radioRelativeCoord.setChecked(True)
         self.radioAbsoluteCoord.setChecked(False)
      elif dynPiCoords == 1:
         self.radioRelativeCoord.setChecked(False)
         self.radioAbsoluteCoord.setChecked(True)

      # Memorizzo il valore di DYNPIVIS = Controlla quando è visualizzato l'input puntatore
      dynPiVis = QadVariables.get(QadMsg.translate("Environment variables", "DYNPIVIS"))
      if dynPiVis == 0:
         # caso da implementare
         self.radioVisWhenAsksPt.setChecked(False)
         self.radioVisAlways.setChecked(False)
      elif dynPiVis == 1:
         self.radioVisWhenAsksPt.setChecked(True)
         self.radioVisAlways.setChecked(False)
      elif dynPiVis == 2:
         self.radioVisWhenAsksPt.setChecked(False)
         self.radioVisAlways.setChecked(True)


   def ButtonBOX_Accepted(self):
      # Memorizzo il valore di DYNPIFORMAT = Determina se l'input del puntatore utilizza un formato polare o cartesiano per le coordinate
      if self.radioPolarFmt.isChecked():
         dynPiFormat = 0
      elif self.radioCartesianFmt.isChecked():
         dynPiFormat = 1
      QadVariables.set(QadMsg.translate("Environment variables", "DYNPIFORMAT"), dynPiFormat)

      # Memorizzo il valore di DYNPICOORDS = Determina se l'input del puntatore utilizza un formato relativo o assoluto per le coordinate
      if self.radioRelativeCoord.isChecked():
         dynPiCoords = 0
      elif self.radioAbsoluteCoord.isChecked():
         dynPiCoords = 1
      QadVariables.set(QadMsg.translate("Environment variables", "DYNPICOORDS"), dynPiCoords)

      # Memorizzo il valore di DYNPIVIS = Controlla quando è visualizzato l'input puntatore
      if self.radioVisWhenAsksPt.isChecked():
         dynPiVis = 1
      elif self.radioVisAlways.isChecked():
         dynPiVis = 2
      QadVariables.set(QadMsg.translate("Environment variables", "DYNPIVIS"), dynPiVis)
      
      QadVariables.save()
      QDialog.accept(self)


   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "DSETTINGS"))


#######################################################################################
# Classe che gestisce l'interfaccia grafica dei settaggi dell'aspetto dei tooltip
class QadTOOLTIPAPPEARANCEDialog(QDialog, QObject, qad_tooltip_appearance_ui.Ui_ToolTipAppearance_Dialog):
   def __init__(self, plugIn, parent):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()
      self.preview = None
      self.ColorVariables = [] # lista delle variabili di ambiente modificate dalla finestra QadWindowColorDialog

      QDialog.__init__(self, parent)

      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())
      
      # Inizializzazione della finestra
      self.init()

      # aggiungo il QWidget chiamato QadPreview
      # che eredita la posizione di widget_Preview (che viene nascosto)
      self.widget_Preview.setHidden(True)
      self.preview = QadPreview(self.plugIn, self.widget_Preview.parent(), \
                                qad_utils.str2int(self.edit_size.text()), \
                                qad_utils.str2int(self.edit_transparency.text()))
      self.preview.setGeometry(self.widget_Preview.geometry())
      self.preview.setObjectName("preview")


   def init(self):
      # Memorizzo il valore di TOOLTIPSIZE = dimensione del testo di tooltip.
      var = QadVariables.getVariable(QadMsg.translate("Environment variables", "TOOLTIPSIZE"))
      self.edit_size.setText(str(var.value))
      self.edit_size.setValidator(QIntValidator(self.edit_size))
      self.edit_size.installEventFilter(self)
      self.slider_size.setMinimum(var.minNum)
      self.slider_size.setMaximum(var.maxNum)
      self.slider_size.setValue(var.value)
      
      # Memorizzo il valore di TOOLTIPTRANSPARENCY = Imposta la trasparenza della finestra di input dinamico.
      var = QadVariables.getVariable(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      self.edit_transparency.setText(str(var.value))
      self.edit_transparency.setValidator(QIntValidator(self.edit_transparency))
      self.edit_transparency.installEventFilter(self)
      self.slider_transparency.setMinimum(var.minNum)
      self.slider_transparency.setMaximum(var.maxNum)
      self.slider_transparency.setValue(var.value)
         
      # Memorizzo il valore di DYNTOOLTIPS = Determina su quali tooltip hanno effetto le impostazioni dell'aspetto delle descrizioni.
      dynTooltips = QadVariables.get(QadMsg.translate("Environment variables", "DYNTOOLTIPS"))
      if dynTooltips == 0:
         self.radio_for_all_tooltips.setChecked(False)
         self.radio_for_DI_tooltips.setChecked(True)
      elif dynTooltips == 1:
         self.radio_for_all_tooltips.setChecked(True)
         self.radio_for_DI_tooltips.setChecked(False)

   def slider_size_moved(self):
      self.edit_size.setText(str(self.slider_size.value()))
      if self.preview is not None:
         self.preview.refresh(self.slider_size.value(), qad_utils.str2int(self.edit_transparency.text())) # forzo il disegno del preview
      

   def edit_size_textChanged(self):
      value = qad_utils.str2int(self.edit_size.text())
      if value is not None:
         self.slider_size.setValue(value)
         if self.preview is not None:
            self.preview.refresh(value, qad_utils.str2int(self.edit_transparency.text())) # forzo il disegno del preview


   def lineEdit_TOOLTIPSIZE_Validation(self):
      varName = QadMsg.translate("Environment variables", "TOOLTIPSIZE")
      var = QadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.intLineEditWidgetValidation(self.edit_size, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid tooltip size"))


   def slider_transparency_moved(self):
      self.edit_transparency.setText(str(self.slider_transparency.value()))
      if self.preview is not None:
         self.preview.refresh(qad_utils.str2int(self.edit_size.text()), self.slider_transparency.value()) # forzo il disegno del preview

      
   def edit_transparency_textChanged(self):
      value = qad_utils.str2int(self.edit_transparency.text())
      if value is not None:
         self.slider_transparency.setValue(value)
         if self.preview is not None:
            self.preview.refresh(qad_utils.str2int(self.edit_size.text()), value) # forzo il disegno del preview

   
   def lineEdit_TOOLTIPTRANSPARENCY_Validation(self):
      varName = QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY")
      var = QadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.intLineEditWidgetValidation(self.edit_transparency, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid transparency value"))


   def eventFilter(self, obj, event):
      if event is not None:
         if event.type() == QEvent.FocusOut:
            if obj == self.edit_size:
               return not self.lineEdit_TOOLTIPSIZE_Validation()
            elif obj == self.edit_transparency:
               return not self.lineEdit_TOOLTIPTRANSPARENCY_Validation()

      # standard event processing
      return QObject.eventFilter(self, obj, event);


   def Button_TooltipColors_Pressed(self):
      Form = QadWindowColorDialog(self.plugIn, self, QadColorContextEnum.MODEL_SPACE_2D, QadColorElementEnum.DI_COMMAND_DESCR)
      
      if Form.exec_() == QDialog.Accepted:
         # copio i valori dei colori in QadVariables
         self.ColorVariables = Form.getSysVariableList()

   
   # ============================================================================
   # getSysVariableList
   # ============================================================================
   def getSysVariableList(self):
      # ritorna una lista di variabili gestite da questa finestra
      variables = list(self.ColorVariables) # copio la lista ColorVariables
      
      variable = QadVariables.getVariable(QadMsg.translate("Environment variables", "TOOLTIPSIZE"))
      varValue = qad_utils.str2int(self.edit_size.text())
      variables.append(QadVariable(variable.name, varValue, variable.typeValue))

      variable = QadVariables.getVariable(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      varValue = qad_utils.str2int(self.edit_transparency.text())
      variables.append(QadVariable(variable.name, varValue, variable.typeValue))

      variable = QadVariables.getVariable(QadMsg.translate("Environment variables", "DYNTOOLTIPS"))
      if self.radio_for_all_tooltips.isChecked():
         variables.append(QadVariable(variable.name, 1, variable.typeValue))
      elif self.radio_for_DI_tooltips.isChecked():
         variables.append(QadVariable(variable.name, 0, variable.typeValue))

      return variables

   
   def ButtonBOX_Accepted(self):
      variables = self.getSysVariableList() # lista delle variabili modificate
      for variable in variables:
         QadVariables.set(variable.name, variable.value)
            
      QadVariables.save()
      
      QDialog.accept(self)


   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "DSETTINGS"))


# ===============================================================================
# QadPreview class.
# ===============================================================================
class QadPreview(QWidget):
   def __init__(self, plugIn, parent, size, transparency, windowFlags = Qt.Widget):
      self.plugIn = plugIn
      self.size = size
      self.transparency = transparency
      QWidget.__init__(self, parent, windowFlags)
      
      self.edit1 = QTextEdit(self)
      self.edit1.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.edit1.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.edit1.insertPlainText("12.3456")
      self.edit1.setReadOnly(True)
      
      self.edit2 = QTextEdit(self)
      self.edit2.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.edit2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
      self.edit2.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)      
      self.edit2.insertPlainText("78.9012")
      self.edit2.setReadOnly(True)


   def refresh(self, size, transparency):
      self.size = size
      self.transparency = transparency
      self.update() # forzo il disegno del preview


   def paintEvent(self, event):
      self.paint_preview()


   def setEdit(self, editWidget, foregroundColor, backGroundColor, borderColor, \
               selectionColor, selectionBackGroundColor, opacity):
      # se i colori sono None allora non vengono alterati
      # caso particolare per borderColor = "" non viene disegnato
      # opacity = 0-100      
      oldFmt = self.styleSheet().split(";")
      fmt = "rgba({0},{1},{2},{3}%)"
      
      c = QColor(foregroundColor)
      rgbStrForeColor = "color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
            
      c = QColor(backGroundColor)
      rgbStrBackColor = "background-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"

      c = QColor(borderColor)
      rgbStrBorderColor = "border-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"
      fmtBorder = "border:1px;border-style:solid;"

      c = QColor(selectionColor)
      rgbStrSelectionColor = "selection-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"

      c = QColor(selectionBackGroundColor)
      rgbStrSelectionBackColor = "selection-background-color: " + fmt.format(str(c.red()), str(c.green()), str(c.blue()), str(opacity)) + ";"

      fontSize = 8 + self.size
      
      fmt = rgbStrForeColor + \
            rgbStrBackColor + \
            fmtBorder + \
            rgbStrBorderColor + \
            rgbStrSelectionColor + \
            rgbStrSelectionBackColor + \
            "font-size: " + str(fontSize) + "pt;"
            
      editWidget.setStyleSheet(fmt)
      
      
   def paint_preview(self):
      rect = self.rect()
      painter = QPainter(self)
      painter.fillRect(rect, self.plugIn.canvas.canvasColor())
      painter.setRenderHint(QPainter.Antialiasing)
      
      foregroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      backGroundColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
      borderColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBORDERCOLOR")))      
      opacity = 100 - self.transparency
      font_size = 8 + self.size
      height = font_size + 15

      selectionColor = QColor(Qt.white)
      selectionBackGroundColor = QColor(51, 153, 255) # azzurro (R=51 G=153 B=255)
      self.setEdit(self.edit1, foregroundColor, backGroundColor, borderColor, selectionColor, selectionBackGroundColor, opacity)
      fm = QFontMetrics(self.edit1.currentFont())
      width1 = fm.width(self.edit1.toPlainText() + "__") + 2

      self.edit1.resize(width1, height)
      self.edit1.selectAll() # seleziono tutto il testo

      self.setEdit(self.edit2, foregroundColor, backGroundColor, borderColor, backGroundColor, foregroundColor, opacity)
      fm = QFontMetrics(self.edit2.currentFont())
      width2 = fm.width(self.edit2.toPlainText() + "__") + 2
      self.edit2.resize(width2, height)
      
      offset = int(height / 3)
      x = int((rect.width() - (width1 + offset + width2)) / 2)
      y = int((rect.height() - height) / 2)
      self.edit1.move(x, y)
      self.edit2.move(x + width1 + offset, y)
