# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per la gestione delle scorciatoie
 
                              -------------------
        begin                : 2020-04-23
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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import QKeySequence
from qgis.gui import QgsGui
import string


# ===============================================================================
# QadShortcuts class
# ===============================================================================
class QadShortcuts():
   
   def __init__(self):
      self.sManager = QgsGui.shortcutsManager()
      self.objList = [] # lista di coppie (shortcut KeySequence) o (action KeySequence)
      
   
   def __del__(self):
      self.registerForPrintable()    
      del self.objList[:] # svuoto la lista


   def registerForPrintableAndQadFKeys(self):
      # setta una lista di shortcut e una di action
      for item in self.objList:
         self.sManager.setObjectKeySequence(item[0], item[1].toString())
            
      return


   def unregisterForPrintableAndQadFKeys(self):
      # rimuove gli shortcut e le action relative ai caratteri stampabili
      # e li memorizza in 2 liste interne: una per gi shortcut ed una per le action che sono state rimosse                                
      del self.objList[:] # svuoto la lista
      s = string.printable
      for i in range(0, len(s)):
         seq = QKeySequence(s[i])
         obj = self.sManager.objectForSequence(seq)
         if obj is not None:
            self.objList.append([obj, seq])
            self.sManager.setObjectKeySequence(obj, QKeySequence().toString()) # lo annulla

      # rimuove gli shortcut e le action relative ai caratteri F2, F3, F8, F12, ESC
      seq = QKeySequence(Qt.Key_F2)
      obj = self.sManager.objectForSequence(seq)
      if obj is not None:
         self.objList.append([obj, seq])
         self.sManager.setObjectKeySequence(obj, QKeySequence().toString()) # lo annulla

      seq = QKeySequence(Qt.Key_F3)
      obj = self.sManager.objectForSequence(seq)
      if obj is not None:
         self.objList.append([obj, seq])
         self.sManager.setObjectKeySequence(obj, QKeySequence().toString()) # lo annulla
           
      seq = QKeySequence(Qt.Key_F8)
      obj = self.sManager.objectForSequence(seq)
      if obj is not None:
         self.objList.append([obj, seq])
         self.sManager.setObjectKeySequence(obj, QKeySequence().toString()) # lo annulla

      seq = QKeySequence(Qt.Key_F12)
      obj = self.sManager.objectForSequence(seq)
      if obj is not None:
         self.objList.append([obj, seq])
         self.sManager.setObjectKeySequence(obj, QKeySequence().toString()) # lo annulla

      seq = QKeySequence(Qt.Key_Escape)
      obj = self.sManager.objectForSequence(seq)
      if obj is not None:
         self.objList.append([obj, seq])
         self.sManager.setObjectKeySequence(obj, QKeySequence().toString()) # lo annulla

      return                            
