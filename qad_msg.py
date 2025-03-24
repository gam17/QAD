# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per le traduzioni dei messaggi
 
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


from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui  import * # for QDesktopServices
import os.path
import sys

import urllib.parse
import platform
#from plotly.graph_objs.bar.marker.colorbar import title
import webbrowser


# traduction class.
class QadMsgClass():


   def __init__(self):
      pass
      

   # ============================================================================
   # translate
   # ============================================================================
   def translate(self, context, sourceText, disambiguation = None, n = -1):
      # da usare in una riga senza accoppiarla ad altre chiamate ad esempio (per lupdate.exe che altrimenti non le trova):
      # NON VA BENE
      #     proplist["blockScale"] = [QadMsg.translate("Dimension", "Scala frecce"), \
      #                               self.blockScale]
      # VA BENE
      #     msg = QadMsg.translate("Dimension", "Scala frecce")
      #     proplist["blockScale"] = [msg, self.blockScale]
 
      # contesti:
      # "QAD" per traduzioni generali
      # "Popup_menu_graph_window" per il menu popup nella finestra grafica
      # "Text_window" per la finestra testuale
      # "Command_list" per nomi di comandi
      # "Command_<nome comando in inglese>" per traduzioni di un comando specifico (es. "Command_PLINE")
      # "Snap" per i tipi di snap
      # finestre varie (es. "DSettings_Dialog", DimStyle_Dialog, ...)
      # "Dimension" per le quotature
      # "Environment variables" per i nomi delle variabili di ambiente
      # "Help" per i titoli dei capitoli del manuale che servono da section nel file html di help
      return QCoreApplication.translate(context, sourceText, disambiguation, n)



   # ===============================================================================
   # getQADTitle
   # ===============================================================================
   def getQADTitle(self, sponsorWith = False):
      title = QadMsg.translate("QAD", "QAD")
      if sponsorWith == True:
         title += " (supported by "
         title +=  QadMsg.translate("SUPPORTER", "SUPPORTER WANTED")
         title += ")"
         
      return title


# ===============================================================================
# qadShowPluginHelp
# ===============================================================================
def qadShowPluginPDFHelp(section = "", filename = "QAD"):
   """
   Apre il file di help in formato PDF alla sezione nota.
   per conoscere la sezione/pagina del file html usare internet explorer,
   selezionare nella finestra di destra la voce di interesse e leggerne l'indirizzo dalla casella in alto.
   Questo perché internet explorer inserisce tutti i caratteri di spaziatura e tab che gli altri browser non fanno.
   """   
   basepath = os.path.dirname(os.path.realpath(__file__))
   
   # initialize locale
   userLocaleList = QSettings().value("locale/userLocale").split("_")
   language = userLocaleList[0]
   region = userLocaleList[1] if len(userLocaleList) > 1 else ""

   path = QDir.cleanPath(basepath + "/help")
   helpfile = os.path.join(path, filename + "_" + language + "_" + region + ".pdf") # provo a caricare la lingua e la regione selezionate
   
   if not os.path.exists(helpfile):
      helpfile = os.path.join(path, filename + "_" + language + ".pdf")  # provo a caricare la lingua
      if not os.path.exists(helpfile):
         helpfile = os.path.join(path, filename + "_en" + ".pdf") # provo a caricare la lingua inglese
         if not os.path.exists(helpfile):
            return
      
   if section != "":
      helpfile = helpfile + "#" + urllib.parse.quote(section.encode('utf-8').decode('utf-8'))

   webbrowser.open_new(helpfile)
   

# ===============================================================================
# qadShowPluginHelp
# ===============================================================================
def qadShowPluginHelp(section = "", filename = "index", packageName = None):
   """
   show a help in the user's html browser.
   per conoscere la sezione/pagina del file html usare internet explorer,
   selezionare nella finestra di destra la voce di interesse e leggerne l'indirizzo dalla casella in alto.
   Questo perché internet explorer inserisce tutti i caratteri di spaziatura e tab che gli altri browser non fanno.
   """   
   try:
      basepath = ""
      if packageName is None:
         basepath = os.path.dirname(os.path.realpath(__file__))
      else:
         basepath = os.path.dirname(os.path.realpath(sys.modules[packageName].__file__))
   except:
      return

   # initialize locale
   userLocaleList = QSettings().value("locale/userLocale").split("_")
   language = userLocaleList[0]
   region = userLocaleList[1] if len(userLocaleList) > 1 else ""

   path = QDir.cleanPath(basepath + "/help/help")
   helpPath = path + "_" + language + "_" + region # provo a caricare la lingua e la regione selezionate
   
   if not os.path.exists(helpPath):
      helpPath = path + "_" + language # provo a caricare la lingua
      if not os.path.exists(helpPath):
         helpPath = path + "_en" # provo a caricare la lingua inglese
         if not os.path.exists(helpPath):
            return
      
   helpfile = os.path.join(helpPath, filename + ".html")
   if os.path.exists(helpfile):
      url = "file:///"+helpfile

      if section != "":
         url = url + "#" + urllib.parse.quote(section.encode('utf-8').decode('utf-8'))

      # la funzione QDesktopServices.openUrl in windows non apre la sezione
      if platform.system() == "Windows":
         import subprocess
         from winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, OpenKey, QueryValue
         
         try: # provo a livello di utente
            with OpenKey(HKEY_CURRENT_USER, r"Software\Classes\http\shell\open\command") as key:
               cmd = QueryValue(key, None)
         except: # se non c'era a livello di utente provo a livello di macchina
            with OpenKey(HKEY_LOCAL_MACHINE, r"Software\Classes\http\shell\open\command") as key:
               cmd = QueryValue(key, None)
   
         if cmd.find("\"%1\"") >= 0:
            subprocess.Popen(cmd.replace("%1", url))
         else:    
            if cmd.find("%1") >= 0:
               subprocess.Popen(cmd.replace("%1", "\"" + url + "\""))       
            else:
               subprocess.Popen(cmd + " \"" + url + "\"")
      else:
         QDesktopServices.openUrl(QUrl(url))           
   
   
# ===============================================================================
# qadShowSupportersPage
# ===============================================================================
def qadShowSupportersPage():
   """
   show the supporter members page in the user's html browser.
   """   
   try:
      webbrowser.open_new("https://qadplugin.wordpress.com/donations")
   except:
      return

   
# ===============================================================================
# QadMsg = variabile globale
# ===============================================================================

QadMsg = QadMsgClass()
