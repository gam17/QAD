# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire gli alias dei comandi
 
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
from qgis.PyQt.QtCore import *
import os.path
import codecs
from qgis.core import *


from . import qad_utils


# Classe che gestisce gli alias dei comandi di Qad
class QadCommandAliasesClass():
   
   def __init__(self):   
      self.__commandAliases = dict()  # dizionario degli alias dei comandi
   
   def getCommandAliasDict(self,):
      """
      Restituisce il dizionario degli alias 
      """
      return self.__commandAliases

   # ============================================================================
   # getCommandName
   # ============================================================================
   def getCommandName(self, alias):
      """
      Dato l'alias restituisce il nome del comando 
      """
      if type(alias) == str or type(alias) == unicode: 
         return self.__commandAliases.get(alias.upper())
      else:
         return self.__commandAliases.get(alias.toUpper())


   # ============================================================================
   # load
   # ============================================================================
   def load(self, Path = "", exceptionList = None):
      """
      Carica la lista degli alias dei comandi da file
      Ritorna True in caso di successo, false in caso di errore
      """
      # svuoto il dizionario e lo reimposto con i valori di default
      self.__commandAliases.clear()
      
      if Path == "":
         # Se la path non é indicata uso il file "qad.pgp" in lingua locale
         userLocaleList = QSettings().value("locale/userLocale").split("_")
         language = userLocaleList[0]
         region = userLocaleList[1] if len(userLocaleList) > 1 else ""
      
         fileName = "qad" + "_" + language + "_" + region + ".pgp "# provo a caricare la lingua e la regione selezionate
         Path = qad_utils.findFile(fileName)
         if Path == "": # se file non trovato
            fileName = "qad" + "_" + language + ".pgp " # provo a caricare la lingua
            Path = qad_utils.findFile(fileName)
            if Path == "": # se file non trovato
               return True
      else:
         if not os.path.exists(Path):
            return True
         
      file = codecs.open(unicode(Path), "r", encoding='utf-8') # apre il file in lettura in modalità unicode utf-8
      
      for line in file:
         line = qad_utils.strip(line, [" ", "\t", "\r\n"]) # rimuovo gli spazi e i tab prima e dopo
         if len(line) == 0:
            continue
         # se la riga inizia per ; allora é una riga commentata
         if line[0] == ";":
            continue

         # leggo il nome dell'alias + il nome del comando (es "alias, *comando")
         sep = line.find(",")
         if sep <= 0:
            continue
         alias = line[0:sep]
         alias = qad_utils.strip(alias, [" ", "\t", "\r\n"]) # rimuovo gli spazi e i tab prima e dopo
         if len(alias) == 0:
            continue
         
         command = line[sep+1:]
         command = qad_utils.strip(command, [" ", "\t", "\r\n"]) # rimuovo gli spazi e i tab prima e dopo
         if len(command) <= 1:
            continue
         # se il comando non inizia per * allora non é un alias
         if command[0] != "*":
            continue
         command = command[1:]
         # il comando non può contenere spazi
         sep = command.find(" ")
         if sep > 0:
            continue
         
         if exceptionList is None:
            self.__commandAliases[alias.upper()] = command.upper()
         else:
            if alias.upper() not in exceptionList: 
               self.__commandAliases[alias.upper()] = command.upper()

      file.close()
      
      return True
