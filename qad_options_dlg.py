# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 comando OPTIONS per opzioni di QAD
 
                              -------------------
        begin                : 2016-10-02
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
from qgis.PyQt.QtWidgets import QDialog, QWidget, QDialogButtonBox
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.utils import *


from .qad_options_ui import Ui_Options_Dialog


from .qad_variables import *
from .qad_msg import QadMsg, qadShowPluginPDFHelp
from . import qad_utils
from .qad_gripcolor_dlg import QadGripColorDialog
from .qad_windowcolor_dlg import QadColorContextEnum, QadColorElementEnum, QadWindowColorDialog
from .qad_dsettings_dlg import QadTOOLTIPAPPEARANCEDialog
from .qad_rightclick_dlg import QadRightClickDialog


# ===============================================================================
# QadOPTIONSTabIndexEnum class.
# ===============================================================================
class QadOPTIONSTabIndexEnum():
   DISPLAY          = 0
   USER_PREFERENCES = 1
   DRAFTING         = 2
   SELECTION        = 3


#######################################################################################
# Classe che gestisce l'interfaccia grafica del comando OPTIONS
class QadOPTIONSDialog(QDialog, QObject, Ui_Options_Dialog):
   def __init__(self, plugIn, optionsTabIndex = None):
      self.plugIn = plugIn
      self.iface = self.plugIn.iface.mainWindow()
      
      QDialog.__init__(self)
      # non passo il parent perchè altrimenti il font e la sua dimensione verrebbero ereditati dalla dialog scombinando tutto 
      #QDialog.__init__(self, self.iface)
      
      self.previewAutoSnapMarker = None
      
      self.setupUi(self)
      self.setWindowTitle(QadMsg.getQADTitle() + " - " + self.windowTitle())

      self.tempQadVariables = QadVariablesClass()
      QadVariables.copyTo(self.tempQadVariables)
      
      # Inizializzazione del TAB "display"
      self.init_display_tab()
      
      # Inizializzazione del TAB "user preferences"
      self.init_user_preferences_tab()
      
      # Inizializzazione del TAB "drafting"
      self.init_drafting_tab()
      
      # Inizializzazione del TAB "selection"
      self.init_selection_tab()
      
      if optionsTabIndex is not None:
         self.tabWidget.setCurrentIndex(optionsTabIndex)
      else:
         if self.plugIn.optionsLastUsedTabIndex == -1: # non inizializzato
            self.plugIn.optionsLastUsedTabIndex = QadOPTIONSTabIndexEnum.DISPLAY
         self.tabWidget.setCurrentIndex(self.plugIn.optionsLastUsedTabIndex)
            

   ######################################
   # TAB "display"
   def init_display_tab(self):
      # Inizializzazione del TAB "display"
      
      # SHOWTEXTWINDOW
      self.checkBox_SHOWTEXTWINDOW.setChecked(self.tempQadVariables.get(QadMsg.translate("Environment variables", "SHOWTEXTWINDOW")))
      
      # CMDINPUTHISTORYMAX
      historyMax = self.tempQadVariables.get(QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX"))
      self.lineEdit_CMDINPUTHISTORYMAX.setText(str(historyMax))
      self.lineEdit_CMDINPUTHISTORYMAX.setValidator(QIntValidator(self.lineEdit_CMDINPUTHISTORYMAX))
      self.lineEdit_CMDINPUTHISTORYMAX.installEventFilter(self)
      
      # Memorizzo il valore dell'INPUTSEARCHOPTIONS
      inputSearchOptions = self.tempQadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"))
      self.checkBox_INPUTSEARCHOPTIONS_ON.setChecked(inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.ON)
      self.checkBox_INPUTSEARCHOPTIONS_AUTOCOMPLETE.setChecked(inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.AUTOCOMPLETE)
      self.checkBox_INPUTSEARCHOPTIONS_DISPLAY_LIST.setChecked(inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_LIST)
      self.checkBox_INPUTSEARCHOPTIONS_DISPLAY_ICON.setChecked(inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.DISPLAY_ICON)
      self.checkBox_INPUTSEARCHOPTIONS_EXCLUDE_SYS_VAR.setChecked(inputSearchOptions & QadINPUTSEARCHOPTIONSEnum.EXCLUDE_SYS_VAR)

      # Memorizzo il valore di INPUTSEARCHDELAY
      inputSearchDelay = self.tempQadVariables.get(QadMsg.translate("Environment variables", "INPUTSEARCHDELAY"))
      self.lineEdit_INPUTSEARCHDELAY.setText(str(inputSearchDelay))
      self.lineEdit_INPUTSEARCHDELAY.setValidator(QIntValidator(self.lineEdit_INPUTSEARCHDELAY))
      self.lineEdit_INPUTSEARCHDELAY.installEventFilter(self)

      # Memorizzo il valore di TOLERANCE2COINCIDENT
      tolerance2Coindident = self.tempQadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
      self.lineEdit_TOLERANCE2COINCIDENT.setText(str(tolerance2Coindident))
      self.lineEdit_TOLERANCE2COINCIDENT.setValidator(QDoubleValidator(self.lineEdit_TOLERANCE2COINCIDENT))
      self.lineEdit_TOLERANCE2COINCIDENT.installEventFilter(self)

      # Memorizzo il valore di ARCMINSEGMENTQTY
      arcMinSegmentQty = self.tempQadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"))
      self.lineEdit_ARCMINSEGMENTQTY.setText(str(arcMinSegmentQty))
      self.lineEdit_ARCMINSEGMENTQTY.setValidator(QIntValidator(self.lineEdit_ARCMINSEGMENTQTY))
      self.lineEdit_ARCMINSEGMENTQTY.installEventFilter(self)

      # Memorizzo il valore di CIRCLEMINSEGMENTQTY
      circleMinSegmentQty = self.tempQadVariables.get(QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY"))
      self.lineEdit_CIRCLEMINSEGMENTQTY.setText(str(circleMinSegmentQty))
      self.lineEdit_CIRCLEMINSEGMENTQTY.setValidator(QIntValidator(self.lineEdit_CIRCLEMINSEGMENTQTY))
      self.lineEdit_CIRCLEMINSEGMENTQTY.installEventFilter(self)

      # Memorizzo il valore di ELLIPSEARCMINSEGMENTQTY
      ellipseArcMinSegmentQty = self.tempQadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"))
      self.lineEdit_ELLIPSEARCMINSEGMENTQTY.setText(str(ellipseArcMinSegmentQty))
      self.lineEdit_ELLIPSEARCMINSEGMENTQTY.setValidator(QIntValidator(self.lineEdit_ELLIPSEARCMINSEGMENTQTY))
      self.lineEdit_ELLIPSEARCMINSEGMENTQTY.installEventFilter(self)

      # Memorizzo il valore di ELLIPSEMINSEGMENTQTY
      circleMinSegmentQty = self.tempQadVariables.get(QadMsg.translate("Environment variables", "ELLIPSEMINSEGMENTQTY"))
      self.lineEdit_ELLIPSEMINSEGMENTQTY.setText(str(circleMinSegmentQty))
      self.lineEdit_ELLIPSEMINSEGMENTQTY.setValidator(QIntValidator(self.lineEdit_ELLIPSEMINSEGMENTQTY))
      self.lineEdit_ELLIPSEMINSEGMENTQTY.installEventFilter(self)

      # Memorizzo il valore di TOLERANCE2APPROXCURVE
      tolerance2ApproxCurve = self.tempQadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"))
      self.lineEdit_TOLERANCE2APPROXCURVE.setText(str(tolerance2ApproxCurve))
      self.lineEdit_TOLERANCE2APPROXCURVE.setValidator(QDoubleValidator(self.lineEdit_TOLERANCE2APPROXCURVE))
      self.lineEdit_TOLERANCE2APPROXCURVE.installEventFilter(self)

      # Memorizzo il valore di CURSORSIZE
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", "CURSORSIZE"))
      self.lineEdit_CURSORSIZE.setText(str(var.value))
      self.lineEdit_CURSORSIZE.setValidator(QIntValidator(self.lineEdit_CURSORSIZE))
      self.lineEdit_CURSORSIZE.installEventFilter(self)
      self.horizontalSlider_CURSORSIZE.setMinimum(var.minNum)
      self.horizontalSlider_CURSORSIZE.setMaximum(var.maxNum)
      self.horizontalSlider_CURSORSIZE.setValue(var.value)

      self.checkBox_INPUTSEARCHOPTIONS_ON_clicked()


   def accept_display_tab(self):
      # Memorizzo il valore di SHOWTEXTWINDOW
      newSHOWTEXTWINDOW = True if self.checkBox_SHOWTEXTWINDOW.checkState() == Qt.Checked else False
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "SHOWTEXTWINDOW"), newSHOWTEXTWINDOW)

      # Memorizzo il valore di CMDINPUTHISTORYMAX
      SHistoryMax = self.lineEdit_CMDINPUTHISTORYMAX.text()
      historyMax = qad_utils.str2int(SHistoryMax)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX"), historyMax)

      # Memorizzo il valore di INPUTSEARCHOPTIONS
      newInputSearchOptions = 0
      if self.checkBox_INPUTSEARCHOPTIONS_ON.checkState() == Qt.Checked:
         newInputSearchOptions = newInputSearchOptions | QadINPUTSEARCHOPTIONSEnum.ON
      if self.checkBox_INPUTSEARCHOPTIONS_AUTOCOMPLETE.checkState() == Qt.Checked:
         newInputSearchOptions = newInputSearchOptions | QadINPUTSEARCHOPTIONSEnum.AUTOCOMPLETE
      if self.checkBox_INPUTSEARCHOPTIONS_DISPLAY_LIST.checkState() == Qt.Checked:
         newInputSearchOptions = newInputSearchOptions | QadINPUTSEARCHOPTIONSEnum.DISPLAY_LIST
      if self.checkBox_INPUTSEARCHOPTIONS_DISPLAY_ICON.checkState() == Qt.Checked:
         newInputSearchOptions = newInputSearchOptions | QadINPUTSEARCHOPTIONSEnum.DISPLAY_ICON
      if self.checkBox_INPUTSEARCHOPTIONS_EXCLUDE_SYS_VAR.checkState() == Qt.Checked:
         newInputSearchOptions = newInputSearchOptions | QadINPUTSEARCHOPTIONSEnum.EXCLUDE_SYS_VAR
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "INPUTSEARCHOPTIONS"), newInputSearchOptions)

      # Memorizzo il valore di INPUTSEARCHDELAY
      SInputSearchDelay = self.lineEdit_INPUTSEARCHDELAY.text()
      InputSearchDelay = qad_utils.str2int(SInputSearchDelay)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "INPUTSEARCHDELAY"), InputSearchDelay)

      # Memorizzo il valore di TOLERANCE2COINCIDENT
      STolerance2Coincident = self.lineEdit_TOLERANCE2COINCIDENT.text()
      Tolerance2Coincident = qad_utils.str2float(STolerance2Coincident)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"), Tolerance2Coincident)

      # Memorizzo il valore di ARCMINSEGMENTQTY
      SArcMinSegmentQty = self.lineEdit_ARCMINSEGMENTQTY.text()
      ArcMinSegmentQty = qad_utils.str2int(SArcMinSegmentQty)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), ArcMinSegmentQty)

      # Memorizzo il valore di CIRCLEMINSEGMENTQTY
      SCircleMinSegmentQty = self.lineEdit_CIRCLEMINSEGMENTQTY.text()
      CircleMinSegmentQty = qad_utils.str2int(SCircleMinSegmentQty)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY"), CircleMinSegmentQty)

      # Memorizzo il valore di ELLIPSEARCMINSEGMENTQTY
      SEllipseArcMinSegmentQty = self.lineEdit_ELLIPSEARCMINSEGMENTQTY.text()
      EllipseArcMinSegmentQty = qad_utils.str2int(SEllipseArcMinSegmentQty)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY"), EllipseArcMinSegmentQty)

      # Memorizzo il valore di ELLIPSEMINSEGMENTQTY
      SEllipseMinSegmentQty = self.lineEdit_ELLIPSEMINSEGMENTQTY.text()
      EllipseMinSegmentQty = qad_utils.str2int(SEllipseMinSegmentQty)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "ELLIPSEMINSEGMENTQTY"), EllipseMinSegmentQty)

      # Memorizzo il valore di TOLERANCE2APPROXCURVE
      STolerance2ApproxCurve = self.lineEdit_TOLERANCE2APPROXCURVE.text()
      Tolerance2ApproxCurve = qad_utils.str2float(STolerance2ApproxCurve)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE"), Tolerance2ApproxCurve)

      # Memorizzo il valore di CURSORSIZE
      SCursorSize = self.lineEdit_CURSORSIZE.text()
      CursorSize = qad_utils.str2int(SCursorSize)
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "CURSORSIZE"), CursorSize)


   def checkBox_INPUTSEARCHOPTIONS_ON_clicked(self):
      value = True if self.checkBox_INPUTSEARCHOPTIONS_ON.checkState() == Qt.Checked else False
      self.checkBox_INPUTSEARCHOPTIONS_AUTOCOMPLETE.setEnabled(value)
      self.checkBox_INPUTSEARCHOPTIONS_DISPLAY_LIST.setEnabled(value)
      self.checkBox_INPUTSEARCHOPTIONS_DISPLAY_ICON.setEnabled(value)
      self.checkBox_INPUTSEARCHOPTIONS_EXCLUDE_SYS_VAR.setEnabled(value)
      self.lineEdit_INPUTSEARCHDELAY.setEnabled(value)
      self.label_INPUTSEARCHDELAY.setEnabled(value)
      

   def horizontalSlider_CURSORSIZE_moved(self):
      self.lineEdit_CURSORSIZE.setText(str(self.horizontalSlider_CURSORSIZE.value()))

      
   def lineEdit_CURSORSIZE_textChanged(self):
      value = qad_utils.str2int(self.lineEdit_CURSORSIZE.text())
      self.horizontalSlider_CURSORSIZE.setValue(value)
      
      
   def lineEdit_CMDINPUTHISTORYMAX_Validation(self):
      varName = QadMsg.translate("Environment variables", "CMDINPUTHISTORYMAX")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_CMDINPUTHISTORYMAX, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid maximum command history length"))


   def lineEdit_INPUTSEARCHDELAY_Validation(self):
      varName = QadMsg.translate("Environment variables", "INPUTSEARCHDELAY")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_INPUTSEARCHDELAY, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid delay time"))


   def lineEdit_TOLERANCE2COINCIDENT_Validation(self):
      varName = QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.floatLineEditWidgetValidation(self.lineEdit_TOLERANCE2COINCIDENT, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid tolerance value"))

   
   def lineEdit_ARCMINSEGMENTQTY_Validation(self):
      varName = QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_ARCMINSEGMENTQTY, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid minimum number of segments in an arc"))


   def lineEdit_CIRCLEMINSEGMENTQTY_Validation(self):
      varName = QadMsg.translate("Environment variables", "CIRCLEMINSEGMENTQTY")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_CIRCLEMINSEGMENTQTY, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid minimum number of segments in a circle"))


   def lineEdit_ELLIPSEARCMINSEGMENTQTY_Validation(self):
      varName = QadMsg.translate("Environment variables", "ELLIPSEARCMINSEGMENTQTY")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))      
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_ELLIPSEARCMINSEGMENTQTY, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid minimum number of segments in an arc of ellipse"))


   def lineEdit_ELLIPSEMINSEGMENTQTY_Validation(self):
      varName = QadMsg.translate("Environment variables", "ELLIPSEMINSEGMENTQTY")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_ELLIPSEMINSEGMENTQTY, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid minimum number of segments in an ellipse"))


   def lineEdit_TOLERANCE2APPROXCURVE_Validation(self):
      varName = QadMsg.translate("Environment variables", "TOLERANCE2APPROXCURVE")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))
      return qad_utils.floatLineEditWidgetValidation(self.lineEdit_TOLERANCE2APPROXCURVE, \
                                                     var, \
                                                     QadMsg.translate("Options_Dialog", "Invalid tolerance between real and segmented curve"))


   def lineEdit_CURSORSIZE_Validation(self):
      varName = QadMsg.translate("Environment variables", "CURSORSIZE")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_CURSORSIZE, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid crosshair size"))


   def Button_TextWindowColor_clicked(self):
      Form = QadWindowColorDialog(self.plugIn, self, QadColorContextEnum.COMMAND_LINE, QadColorElementEnum.COMMAND_HISTORY_BACKGROUND)
      
      if Form.exec_() == QDialog.Accepted:
         # copio i valori dei colori in self.tempQadVariables
         variables = Form.getSysVariableList()
         for variable in variables:
            self.tempQadVariables.set(variable.name, variable.value)

         self.refreshPreviewColor()


   ######################################
   # TAB "user preferences"
   def init_user_preferences_tab(self):
      # Inizializzazione del TAB "user preferences"
      
      # SHORTCUTMENU
      shortcutmenu = self.tempQadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENU"))
      if shortcutmenu == 0:                                         
         self.checkBox_shortcutmenu.setChecked(False)
      else:
         self.checkBox_shortcutmenu.setChecked(True)
      self.checkBox_shortcutmenu_clicked()

   def checkBox_shortcutmenu_clicked(self):
      if self.checkBox_shortcutmenu.checkState() == Qt.Checked:
         self.button_rightclick.setEnabled(True)
      else:
         self.button_rightclick.setEnabled(False)

   
   def button_rightclick_clicked(self):
      Form = QadRightClickDialog(self.plugIn, self)
      if Form.exec_() == QDialog.Accepted:
         # copio i valori dei colori in self.tempQadVariables
         variables = Form.getSysVariableList()
         for variable in variables:
            self.tempQadVariables.set(variable.name, variable.value)
         self.init_user_preferences_tab()


   def accept_user_preferences_tab(self):
      if self.checkBox_shortcutmenu.checkState() == Qt.Unchecked:
         self.tempQadVariables.set(QadMsg.translate("Environment variables", "SHORTCUTMENU"), 0)
      elif self.tempQadVariables.get(QadMsg.translate("Environment variables", "SHORTCUTMENU")) == 0:
         self.tempQadVariables.set(QadMsg.translate("Environment variables", "SHORTCUTMENU"), 11) # inizializzo questo default


   ######################################
   # TAB "drafting"
   def init_drafting_tab(self):
      # Inizializzazione del TAB "drafting"
      
      # AUTOSNAP
      autoSnap = self.tempQadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))
      self.checkBox_AUTOSNAP_DISPLAY_MARK.setChecked(autoSnap & QadAUTOSNAPEnum.DISPLAY_MARK)
      self.checkBox_AUTOSNAP_MAGNET.setChecked(autoSnap & QadAUTOSNAPEnum.MAGNET)
      self.checkBox_AUTOSNAP_DISPLAY_TOOLTIPS.setChecked(autoSnap & QadAUTOSNAPEnum.DISPLAY_TOOLTIPS)
      
      # APBOX
      apBox = False if self.tempQadVariables.get(QadMsg.translate("Environment variables", "APBOX")) == 0 else True
      self.checkBox_APBOX.setChecked(apBox)

      # AUTOSNAPSIZE
      # aggiungo il QWidget chiamato QadPreviewAutoSnapMarker
      # che eredita la posizione di widget_AUTOSNAPSIZE (che viene nascosto)
      self.widget_AUTOSNAPSIZE.setHidden(True)
      autoSnapColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPCOLOR")))
      self.previewAutoSnapMarker = QadPreviewAutoSnapMarker(self.plugIn, autoSnapColor, self.widget_AUTOSNAPSIZE.parent())
      self.previewAutoSnapMarker.setGeometry(self.widget_AUTOSNAPSIZE.geometry())
      self.previewAutoSnapMarker.setObjectName("previewAutoSnapMarker")
           
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", "AUTOSNAPSIZE"))
      self.horizontalSlider_AUTOSNAPSIZE.setMinimum(var.minNum)
      #self.horizontalSlider_AUTOSNAPSIZE.setMaximum(var.maxNum)
      self.horizontalSlider_AUTOSNAPSIZE.setMaximum(20) # oltre i 20 non ci sta nel riquadro
      self.horizontalSlider_AUTOSNAPSIZE.setValue(var.value)
      
      # POLARMODE
      polarMode = self.tempQadVariables.get(QadMsg.translate("Environment variables", "POLARMODE"))
      if polarMode & QadPOLARMODEnum.SHIFT_TO_ACQUIRE:
         self.radioButton_POLARMODE_SHIFT_TO_ACQUIRE.setChecked(True)
      else:
         self.radioButton_POLARMODE_AUTO_ACQUIRE.setChecked(True)

      # APERTURE
      # aggiungo il QWidget chiamato QadPreviewAperture
      # che eredita la posizione di widget_APERTURESIZE (che viene nascosto)
      self.widget_APERTURESIZE.setHidden(True)
      apertureColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
      cursorColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "CURSORCOLOR")))
      self.previewAperture = QadPreviewAperture(self.plugIn, apertureColor, cursorColor, self.widget_APERTURESIZE.parent())
      self.previewAperture.setGeometry(self.widget_APERTURESIZE.geometry())
      self.previewAperture.setObjectName("previewAperture")

      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", "APERTURE"))
      self.horizontalSlider_APERTURE.setMinimum(var.minNum)
      #self.horizontalSlider_APERTURE.setMaximum(var.maxNum)
      self.horizontalSlider_APERTURE.setMaximum(20) # oltre i 20 non ci sta nel riquadro
      self.horizontalSlider_APERTURE.setValue(var.value)


   def button_DraftingTooltipSettings_clicked(self):
      Form = QadTOOLTIPAPPEARANCEDialog(self.plugIn, self)
      if Form.exec_() == QDialog.Accepted:
         # copio i valori dei colori in self.tempQadVariables
         variables = Form.getSysVariableList()
         for variable in variables:
            self.tempQadVariables.set(variable.name, variable.value)
      
      
   def accept_drafting_tab(self):
      # AUTOSNAP
      autoSnap = self.tempQadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAP"))
      
      if self.checkBox_AUTOSNAP_DISPLAY_MARK.checkState() == Qt.Checked:
         autoSnap = autoSnap | QadAUTOSNAPEnum.DISPLAY_MARK # aggiungo i bit
      else:
         autoSnap = autoSnap &~ QadAUTOSNAPEnum.DISPLAY_MARK # tolgo il bit
      
      if self.checkBox_AUTOSNAP_MAGNET.checkState() == Qt.Checked:
         autoSnap = autoSnap | QadAUTOSNAPEnum.MAGNET # aggiungo i bit
      else:
         autoSnap = autoSnap &~ QadAUTOSNAPEnum.MAGNET # tolgo il bit
      
      if self.checkBox_AUTOSNAP_DISPLAY_TOOLTIPS.checkState() == Qt.Checked:
         autoSnap = autoSnap | QadAUTOSNAPEnum.DISPLAY_TOOLTIPS # aggiungo i bit
      else:
         autoSnap = autoSnap &~ QadAUTOSNAPEnum.DISPLAY_TOOLTIPS # tolgo il bit

      self.tempQadVariables.set(QadMsg.translate("Environment variables", "AUTOSNAP"), autoSnap)
      
      # APBOX
      newAPBOX = 1 if self.checkBox_APBOX.checkState() == Qt.Checked else 0
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "APBOX"), newAPBOX)

      # AUTOSNAPSIZE
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "AUTOSNAPSIZE"), self.horizontalSlider_AUTOSNAPSIZE.value())
      
      # POLARMODE
      polarMode = self.tempQadVariables.get(QadMsg.translate("Environment variables", "POLARMODE"))
      
      if self.radioButton_POLARMODE_SHIFT_TO_ACQUIRE.isChecked():
         polarMode = polarMode | QadPOLARMODEnum.SHIFT_TO_ACQUIRE # aggiungo i bit
      else:
         polarMode = polarMode &~ QadPOLARMODEnum.SHIFT_TO_ACQUIRE # tolgo il bit
      
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "POLARMODE"), polarMode)
      
      # APERTURE
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "APERTURE"), self.horizontalSlider_APERTURE.value())


   def horizontalSlider_AUTOSNAPSIZE_changed(self):
      if self.previewAutoSnapMarker is not None:
         self.previewAutoSnapMarker.size = self.horizontalSlider_AUTOSNAPSIZE.value()
         self.previewAutoSnapMarker.update() # forzo il disegno del preview


   def horizontalSlider_APERTURE_changed(self):
      if self.previewAperture is not None:
         self.previewAperture.size = self.horizontalSlider_APERTURE.value()
         self.previewAperture.update() # forzo il disegno del preview


   def Button_AutoSnapWindowColor_clicked(self):
      Form = QadWindowColorDialog(self.plugIn, self, QadColorContextEnum.MODEL_SPACE_2D, QadColorElementEnum.AUTOSNAP_MARKER)
      
      if Form.exec_() == QDialog.Accepted:
         # copio i valori dei colori in self.tempQadVariables
         variables = Form.getSysVariableList()
         for variable in variables:
            self.tempQadVariables.set(variable.name, variable.value)

         self.refreshPreviewColor()


   ######################################
   # TAB "selection"
   def init_selection_tab(self):
      # Inizializzazione del TAB "selection"
      
      # PICKBOX
      # aggiungo il QWidget chiamato QadPreviewPickBox
      # che eredita la posizione di widget_PICKBOX (che viene nascosto)
      self.widget_PICKBOX.setHidden(True)
      pickBoxColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
      self.previewPickBox = QadPreviewPickBox(self.plugIn, pickBoxColor, self.widget_PICKBOX.parent())
      self.previewPickBox.setGeometry(self.widget_PICKBOX.geometry())
      self.previewPickBox.setObjectName("previewPickBox")
           
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", "PICKBOX"))
      self.horizontalSlider_PICKBOX.setMinimum(var.minNum)
      #self.horizontalSlider_PICKBOX.setMaximum(var.maxNum)
      self.horizontalSlider_PICKBOX.setMaximum(20) # oltre i 20 non ci sta nel riquadro
      self.horizontalSlider_PICKBOX.setValue(var.value)
      
      # PICKFIRST
      pickFirst = False if self.tempQadVariables.get(QadMsg.translate("Environment variables", "PICKFIRST")) == 0 else True
      self.checkBox_PICKFIRST.setChecked(pickFirst)
      
      # PICKADD
      pickAdd = self.tempQadVariables.get(QadMsg.translate("Environment variables", "PICKADD"))
      if pickAdd == 0:
         self.checkBox_PICKADD.setChecked(True)
      else:
         self.checkBox_PICKADD.setChecked(False)

      # GRIPSIZE
      # aggiungo il QWidget chiamato QadPreviewGripSize
      # che eredita la posizione di widget_GRIPSIZE (che viene nascosto)
      self.widget_GRIPSIZE.setHidden(True)
      fillColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPCOLOR")))
      borderColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPCONTOUR")))
      self.previewGripSize = QadPreviewGripSize(self.plugIn, fillColor, borderColor, self.widget_GRIPSIZE.parent())
      self.previewGripSize.setGeometry(self.widget_GRIPSIZE.geometry())
      self.previewGripSize.setObjectName("previewGripSize")
           
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", "GRIPSIZE"))
      self.horizontalSlider_GRIPSIZE.setMinimum(var.minNum)
      #self.horizontalSlider_PGRIPSIZE.setMaximum(var.maxNum)
      self.horizontalSlider_GRIPSIZE.setMaximum(20) # oltre i 20 non ci sta nel riquadro
      self.horizontalSlider_GRIPSIZE.setValue(var.value)
      
      # GRIPS
      grips = False if self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPS")) == 0 else True
      self.checkBox_GRIPS.setChecked(grips)
      
      # GRIPMULTIFUNCTIONAL
      gripMultiFunctional = self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPMULTIFUNCTIONAL"))
      self.checkBox_GRIPMULTIFUNCTIONAL_ON_DYNAMIC_MENU_AND_HOT_GRIPT.setChecked(gripMultiFunctional & QadGRIPMULTIFUNCTIONALEnum.ON_DYNAMIC_MENU_AND_HOT_GRIPT)

      # GRIPOBJLIMIT
      gripObjLimit = self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPOBJLIMIT"))
      self.lineEdit_GRIPOBJLIMIT.setText(str(gripObjLimit))
      self.lineEdit_GRIPOBJLIMIT.setValidator(QIntValidator(self.lineEdit_GRIPOBJLIMIT))
      self.lineEdit_GRIPOBJLIMIT.installEventFilter(self)

      self.checkBox_GRIPS_ON_clicked()
      

   def accept_selection_tab(self):
      # PICKBOX
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "PICKBOX"), self.horizontalSlider_PICKBOX.value())

      # PICKFIRST
      pickFirst = 1 if self.checkBox_PICKFIRST.checkState() == Qt.Checked else 0
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "PICKFIRST"), pickFirst)

      # PICKADD
      pickAdd = 0 if self.checkBox_PICKADD.checkState() == Qt.Checked else 1
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "PICKADD"), pickAdd)

      # GRIPSIZE
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPSIZE"), self.horizontalSlider_GRIPSIZE.value())

      # GRIPS
      grips = 1 if self.checkBox_GRIPS.checkState() == Qt.Checked else 0
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPS"), grips)

      # GRIPMULTIFUNCTIONAL
      gripMultiFunctional = self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPMULTIFUNCTIONAL"))
      if self.checkBox_GRIPMULTIFUNCTIONAL_ON_DYNAMIC_MENU_AND_HOT_GRIPT.checkState() == Qt.Checked:
         gripMultiFunctional = gripMultiFunctional | QadGRIPMULTIFUNCTIONALEnum.ON_DYNAMIC_MENU_AND_HOT_GRIPT # aggiungo i bit
      else:
         gripMultiFunctional = gripMultiFunctional &~ QadGRIPMULTIFUNCTIONALEnum.ON_DYNAMIC_MENU_AND_HOT_GRIPT # tolgo i bit
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPMULTIFUNCTIONAL"), gripMultiFunctional)

      # GRIPOBJLIMIT
      gripObjLimit = qad_utils.str2int(self.lineEdit_GRIPOBJLIMIT.text())
      self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPOBJLIMIT"), gripObjLimit)


   def checkBox_GRIPS_ON_clicked(self):
      value = True if self.checkBox_GRIPS.checkState() == Qt.Checked else False
      self.checkBox_GRIPMULTIFUNCTIONAL_ON_DYNAMIC_MENU_AND_HOT_GRIPT.setEnabled(value)
      self.lineEdit_GRIPOBJLIMIT.setEnabled(value)
      self.label_GRIPOBJLIMIT.setEnabled(value)


   def horizontalSlider_PICKBOX_changed(self):
      if self.previewPickBox is not None:
         self.previewPickBox.size = self.horizontalSlider_PICKBOX.value()
         self.previewPickBox.update() # forzo il disegno del preview


   def horizontalSlider_GRIPSIZE_changed(self):
      if self.previewGripSize is not None:
         self.previewGripSize.size = self.horizontalSlider_GRIPSIZE.value()
         self.previewGripSize.update() # forzo il disegno del preview


   def lineEdit_GRIPOBJLIMIT_Validation(self):
      varName = QadMsg.translate("Environment variables", "GRIPOBJLIMIT")
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))
      return qad_utils.intLineEditWidgetValidation(self.lineEdit_GRIPOBJLIMIT, \
                                                   var, \
                                                   QadMsg.translate("Options_Dialog", "Invalid object selection limit for display of grips"))


   def button_GripColor_clicked(self):
      Form = QadGripColorDialog(self.plugIn, self, \
                                self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPCOLOR")), \
                                self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPHOT")), \
                                self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPHOVER")), \
                                self.tempQadVariables.get(QadMsg.translate("Environment variables", "GRIPCONTOUR")))
      
      if Form.exec_() == QDialog.Accepted:
         self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPCOLOR"), Form.gripColor)
         self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPHOT"), Form.gripHot)
         self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPHOVER"), Form.gripHover)
         self.tempQadVariables.set(QadMsg.translate("Environment variables", "GRIPCONTOUR"), Form.gripContour)

         self.previewGripSize.fillColor = QColor(Form.gripColor)
         self.previewGripSize.borderColor = QColor(Form.gripContour)


   ######################################
   # Funzioni generiche
   def intLineEditWidgetValidation(self, widget, varName, msg):
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))

      err = False
      string = widget.text()
      if qad_utils.str2int(string) is None:
         err = True
      else:
         if var.minNum is not None:
            if qad_utils.str2int(string) < var.minNum:
               err = True
         if var.maxNum is not None:
            if qad_utils.str2int(string) > var.maxNum:
               err = True
      
      if err:
         msg = msg + QadMsg.translate("QAD", ": enter a number")
         if var.minNum is not None:
            msg = msg + QadMsg.translate("QAD", " >= {0}").format(str(var.minNum))
         if var.maxNum is not None:
            if var.minNum is not None:
               msg = msg + QadMsg.translate("QAD", " and")
            msg = msg + QadMsg.translate("QAD", " <= {0}").format(str(var.maxNum))
         msg = msg + "."
         QMessageBox.critical(self, QadMsg.getQADTitle(), msg)
         widget.setFocus()
         widget.selectAll()
         return False
      return True
   

   def floatLineEditWidgetValidation(self, widget, varName, msg):
      var = self.tempQadVariables.getVariable(QadMsg.translate("Environment variables", varName))

      err = False
      string = widget.text()
      if qad_utils.str2float(string) is None:
         err = True
      else:
         if var.minNum is not None:
            if qad_utils.str2float(string) < var.minNum:
               err = True
         if var.maxNum is not None:
            if qad_utils.str2float(string) > var.maxNum:
               err = True
      
      if err:
         msg = msg + QadMsg.translate("QAD", ": enter a number")
         if var.minNum is not None:
            minValMsg = msg + QadMsg.translate("QAD", " > {0}").format(str(var.minNum))
         else:
            minValMsg = ""
         if var.maxNum is not None:
            if len(minValMsg) > 0:
               msg = msg + QadMsg.translate("QAD", " and")
            msg = msg + QadMsg.translate("QAD", " < {0}").format(str(var.maxNum))
         msg = msg + "."
         QMessageBox.critical(self, QadMsg.getQADTitle(), msg)
         widget.setFocus()
         widget.selectAll()
         return False
      return True
   
   def eventFilter(self, obj, event):
      if event is not None:
         if event.type() == QEvent.FocusOut:
            if obj == self.lineEdit_CMDINPUTHISTORYMAX:
               return not self.lineEdit_CMDINPUTHISTORYMAX_Validation()
            elif obj == self.lineEdit_INPUTSEARCHDELAY:
               return not self.lineEdit_INPUTSEARCHDELAY_Validation()
            elif obj == self.lineEdit_TOLERANCE2COINCIDENT:
               return not self.lineEdit_TOLERANCE2COINCIDENT_Validation()
            elif obj == self.lineEdit_ARCMINSEGMENTQTY:
               return not self.lineEdit_ARCMINSEGMENTQTY_Validation()
            elif obj == self.lineEdit_CIRCLEMINSEGMENTQTY:
               return not self.lineEdit_CIRCLEMINSEGMENTQTY_Validation()
            elif obj == self.lineEdit_ELLIPSEARCMINSEGMENTQTY:
               return not self.lineEdit_ELLIPSEARCMINSEGMENTQTY_Validation()
            elif obj == self.lineEdit_ELLIPSEMINSEGMENTQTY:
               return not self.lineEdit_ELLIPSEMINSEGMENTQTY_Validation()
            elif obj == self.lineEdit_TOLERANCE2APPROXCURVE:
               return not self.lineEdit_TOLERANCE2APPROXCURVE_Validation()
            elif obj == self.lineEdit_CURSORSIZE:
               return not self.lineEdit_CURSORSIZE_Validation()
            elif obj == self.lineEdit_GRIPOBJLIMIT:
               return not self.lineEdit_GRIPOBJLIMIT_Validation()

      # standard event processing
      return QObject.eventFilter(self, obj, event);


   # ============================================================================
   # refreshPreviewColor
   # ============================================================================
   def refreshPreviewColor(self):
      pickBoxColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
      self.previewPickBox.color = pickBoxColor
      autoSnapColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "AUTOSNAPCOLOR")))
      self.previewAutoSnapMarker.color = autoSnapColor
      apertureColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
      cursorColor = QColor(self.tempQadVariables.get(QadMsg.translate("Environment variables", "CURSORCOLOR")))
      self.previewAperture.color = apertureColor
      self.previewAperture.cursorColor = cursorColor


   def ButtonBOX_Accepted(self):
      self.apply()
      QDialog.accept(self)


   def ButtonBOX_Apply(self, button):
      if self.buttonBox.standardButton(button) == QDialogButtonBox.Apply:
         self.apply()
      elif self.buttonBox.standardButton(button) == QDialogButtonBox.Cancel:
         self.close()
      
      return True


   def apply(self):
      self.accept_display_tab()
      self.accept_user_preferences_tab()
      self.accept_drafting_tab()
      self.accept_selection_tab()
      
      self.tempQadVariables.copyTo(QadVariables)
      QadVariables.save()
      self.plugIn.UpdatedVariablesEvent()

      self.plugIn.optionsLastUsedTabIndex = self.tabWidget.currentIndex()
      

   def ButtonHELP_Pressed(self):
      qadShowPluginPDFHelp(QadMsg.translate("Help", "OPTIONS"))


# ===============================================================================
# QadPreviewAutoSnapMarker class.
# ===============================================================================
class QadPreviewAutoSnapMarker(QWidget):
   def __init__(self, plugIn, color, parent = None, windowFlags = Qt.Widget):
      self.plugIn = plugIn
      self.color = color
      self.size = 0
      QWidget.__init__(self, parent, windowFlags)

   def paintEvent(self, event):
      rect = self.rect()
      painter = QPainter(self)
      painter.fillRect(rect, self.plugIn.canvas.canvasColor())
      if self.size == 0:
         return
      size = rect.width()/2 if self.size > rect.width()/2 else self.size # oltre non ci sta nel riquadro
      center = rect.center()
      x1 = center.x() - size
      y1 = center.y() - size
      dblSize = size * 2 + 1
      painter.setRenderHint(QPainter.Antialiasing)
      painter.setPen(QPen(self.color, 2))
      #painter.setPen(QPen(self.color, 12, Qt.DashDotLine, Qt.RoundCap))
      #painter.drawLine(x1, y1, x2, y2)
      painter.drawRect(x1, y1, dblSize, dblSize)


# ===============================================================================
# QadPreviewAperture class.
# ===============================================================================
class QadPreviewAperture(QWidget):
   def __init__(self, plugIn, color, cursorColor, parent = None, windowFlags = Qt.Widget):
      self.plugIn = plugIn
      self.color = color
      self.cursorColor = cursorColor
      self.size = 0
      QWidget.__init__(self, parent, windowFlags)

   def paintEvent(self, event):
      rect = self.rect()
      painter = QPainter(self)
      painter.fillRect(rect, self.plugIn.canvas.canvasColor())
      if self.size == 0:
         return
      size = rect.width()/2 if self.size > rect.width()/2 else self.size # oltre non ci sta nel riquadro
      center = rect.center()
      x1 = center.x() - size
      y1 = center.y() - size
      dblSize = size * 2 + 1
      painter.setRenderHint(QPainter.Antialiasing)
      painter.setPen(QPen(self.cursorColor, 1))
      painter.drawLine(center.x(), 0, center.x(), rect.height())
      painter.drawLine(0, center.y(), rect.width(), center.y())
      painter.setPen(QPen(self.color, 1, Qt.DotLine))
      painter.drawRect(x1, y1, dblSize, dblSize)


# ===============================================================================
# QadPreviewPickBox class.
# ===============================================================================
class QadPreviewPickBox(QWidget):
   def __init__(self, plugIn, color, parent = None, windowFlags = Qt.Widget):
      self.plugIn = plugIn
      self.color = color
      self.size = 0
      QWidget.__init__(self, parent, windowFlags)

   def paintEvent(self, event):
      rect = self.rect()
      painter = QPainter(self)
      painter.fillRect(rect, self.plugIn.canvas.canvasColor())
      if self.size == 0:
         return
      size = rect.width()/2 if self.size > rect.width()/2 else self.size # oltre non ci sta nel riquadro
      center = rect.center()
      x1 = center.x() - size
      y1 = center.y() - size
      dblSize = size * 2 + 1
      
      painter.setRenderHint(QPainter.Antialiasing)
      painter.setPen(QPen(self.color, 1))
      painter.drawRect(x1, y1, dblSize, dblSize)


# ===============================================================================
# QadPreviewGripSize class.
# ===============================================================================
class QadPreviewGripSize(QWidget):
   def __init__(self, plugIn, fillColor, borderColor, parent = None, windowFlags = Qt.Widget):
      self.plugIn = plugIn
      self.fillColor = fillColor
      self.borderColor = borderColor
      self.size = 0
      QWidget.__init__(self, parent, windowFlags)

   def paintEvent(self, event):
      rect = self.rect()
      painter = QPainter(self)
      painter.fillRect(rect, self.plugIn.canvas.canvasColor())
      if self.size == 0:
         return
      size = rect.width()/2 if self.size > rect.width()/2 else self.size # oltre non ci sta nel riquadro
      center = rect.center()
      x1 = center.x() - size
      y1 = center.y() - size
      dblSize = size * 2 + 1
      
      painter.setRenderHint(QPainter.Antialiasing)
      painter.fillRect(x1, y1, dblSize, dblSize, self.fillColor)
      painter.setPen(QPen(self.borderColor, 1))
      painter.drawRect(x1, y1, dblSize, dblSize)
      