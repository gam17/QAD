# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni varie di utilità
 
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

from qgis.PyQt.QtCore import QVariant, QDir
from qgis.PyQt.QtGui  import QCursor, QPixmap, QColor, QFont, QPalette
from qgis.PyQt.QtWidgets import QToolTip, QMessageBox, QApplication
from qgis.core import *
import qgis.utils
 
              
import os
import math
import sys
from gettext import find
import configparser
import time
import uuid, re

from .qad_variables import QadVariables
from .qad_msg import QadMsg


# Modulo che gestisce varie funzionalità di QAD


def getMacAddress():
   return ':'.join(re.findall('..', '%012x' % uuid.getnode())).upper()


def criptPlainText(strValue):
   mytable = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz -./0123456789:;<=>?@"', \
                           'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9:;<=>?@" -./012345678')
   return strValue.translate(mytable)


def decriptPlainText(strValue):
   mytable = str.maketrans('NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9:;<=>?@" -./012345678', \
                           'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz -./0123456789:;<=>?@"')
   return strValue.translate(mytable)


#===============================================================================
# FUNZIONI GENERICHE PER LE OPZIONI DEI COMANDI - INIZIO
#===============================================================================


def extractUpperCaseSubstr(str):
   # estraggo la parte maiuscola della stringa
   upperPart = ""
   for letter in str:
      if letter.isupper():
         upperPart = upperPart + letter
      elif len(upperPart) > 0:
         break
   return upperPart


def evaluateCmdKeyWords(cmd, keyWordList):
   # Riceve un comando e la lista delle parole chiave delle opzioni di un comando
   # La funzione ritorna la keyword del comando seguito da un eventuale messaggio di errore se la keyword = None
   
   # The required portion of the keyword is specified in uppercase characters, 
   # and the remainder of the keyword is specified in lowercase characters.
   # The uppercase abbreviation can be anywhere in the keyword
   if cmd == "": # se cmd = "" la funzione find ritorna 0 (no comment)
      return None, None
   upperCmd = cmd.upper()
   selectedKeyWords = []
   for keyWord in keyWordList:
      # estraggo la parte maiuscola della parola chiave
      upperPart = extractUpperCaseSubstr(keyWord)
      
      if upperPart.find(upperCmd) == 0: # se la parte maiuscola della parola chiave inizia per upperCmd
         if upperPart == upperCmd: # Se uguale
            return keyWord, None
         else:
            selectedKeyWords.append(keyWord)
      elif keyWord.upper().find(upperCmd) == 0: # se la parola chiave inizia per cmd (insensitive)
         if keyWord.upper() == upperCmd: # Se uguale
            return keyWord, None
         else:
            selectedKeyWords.append(keyWord)

   selectedKeyWordsLen = len(selectedKeyWords)
   if selectedKeyWordsLen == 0:
      return None, None
   elif selectedKeyWordsLen == 1:
      return selectedKeyWords[0], None
   else:
      Msg = QadMsg.translate("QAD", "\nAmbiguous answer: specify with more clarity...")
      ambiguousMsg = ""
      for keyWord in selectedKeyWords:
         if ambiguousMsg == "":
            ambiguousMsg = keyWord
         else:
            ambiguousMsg = ambiguousMsg + QadMsg.translate("QAD", " or ") + keyWord

      Msg = Msg + "\n" + ambiguousMsg + QadMsg.translate("QAD", " ?\n")
      
   return None, Msg


#===============================================================================
# FUNZIONI GENERICHE PER LE OPZIONI DEI COMANDI - FINE
# FUNZIONI GENERICHE PER I WIDGET - INIZIO
#===============================================================================


#===============================================================================
# setMapCanvasToolTip
#===============================================================================
# visualizza il testo della tooltip del mapCanvas con l'aspetto determinato da DYNTOOLTIPS
def setMapCanvasToolTip(msg):
   canvas = qgis.utils.iface.mapCanvas()
   pt = canvas.mapToGlobal(canvas.mouseLastXY())
   
   if QadVariables.get(QadMsg.translate("Environment variables", "DYNTOOLTIPS")) == 1:
      font_size = 8 + QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPSIZE"))

      #opacity = 100 - QadVariables.get(QadMsg.translate("Environment variables", "TOOLTIPTRANSPARENCY"))
      #fc.setAlphaF(opacity/100.0) # non va
      
      fColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITFORECOLOR")))
      bColor = QColor(QadVariables.get(QadMsg.translate("Environment variables", "DYNEDITBACKCOLOR")))
   else:
      font_size = QFont().pointSize()
      p = QPalette()
      fColor = p.color(QPalette.Inactive, QPalette.ToolTipText)
      bColor = p.color(QPalette.Inactive, QPalette.ToolTipBase)

   toolTipFont = QToolTip.font()
   if toolTipFont.pointSize() != font_size:
      toolTipFont.setPointSize(font_size)
      QToolTip.setFont(toolTipFont)

   toolTipPalette = QToolTip.palette()
   if toolTipPalette.color(QPalette.Inactive, QPalette.ToolTipText) != fColor or \
      toolTipPalette.color(QPalette.Inactive, QPalette.ToolTipBase) != bColor:
      toolTipPalette.setColor(QPalette.Inactive, QPalette.ToolTipText, fColor)
      toolTipPalette.setColor(QPalette.Inactive, QPalette.ToolTipBase, bColor)
      QToolTip.setPalette(toolTipPalette)

   QToolTip.showText(pt, msg)
   
   return


#===============================================================================
# floatLineEditWidgetValidation
#===============================================================================
# controlla che il valore di un widget di tipo line edit soddisfi l'intervallo ammesso per la variabile di ambiente
def intLineEditWidgetValidation(widget, var, msg):
   err = False
   string = widget.text()
   if str2int(string) is None:
      err = True
   else:
      if var.minNum is not None:
         if str2int(string) < var.minNum:
            err = True
      if var.maxNum is not None:
         if str2int(string) > var.maxNum:
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
      QMessageBox.critical(None, QadMsg.getQADTitle(), msg)
      widget.setFocus()
      widget.selectAll()
      return False
   return True


#===============================================================================
# floatLineEditWidgetValidation
#===============================================================================
# controlla che il valore di un widget di tipo line edit soddisfi l'intervallo ammesso per la variabile di ambiente
def floatLineEditWidgetValidation(widget, var, msg):
   err = False
   string = widget.text()
   if str2float(string) is None:
      err = True
   else:
      if var.minNum is not None:
         if str2float(string) < var.minNum:
            err = True
      if var.maxNum is not None:
         if str2float(string) > var.maxNum:
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
      QMessageBox.critical(None, QadMsg.getQADTitle(), msg)
      widget.setFocus()
      widget.selectAll()
      return False
   return True


#===============================================================================
# FUNZIONI GENERICHE PER I WIDGET - FINE
#===============================================================================


#===============================================================================
# isNumericField
#===============================================================================
def isNumericField(field):
   """
   La funzione verifica che il campo di tipo QgsField sia numerico
   """
   fldType = field.type()
   if fldType == QVariant.Double or fldType == QVariant.LongLong or fldType == QVariant.Int or \
      fldType == QVariant.ULongLong or fldType == QVariant.UInt:
      return True
   else:
      return False


#===============================================================================
# checkUniqueNewName
#===============================================================================
def checkUniqueNewName(newName, nameList, prefix = None, suffix = None, caseSensitive = True):
   """
   La funzione verifica che il nuovo nome non esistà già nella lista <nameList>.
   Se nella lista dovesse già esistere allora aggiunge un prefisso (se <> None) o un suffisso (se <> None)
   finchè il nome non è più presnete nella lista
   """
   ok = False
   result = newName 
   while ok == False:
      ok = True
      for name in nameList:
         if caseSensitive == True:
            if name == result:
               ok = False
               break
         else:
            if name.upper() == result.upper():
               ok = False
               break
        
      if ok == True:
         return result
      if prefix is not None:
         result = prefix + result
      else:
         if suffix is not None:
            result = result + suffix
   
   return None

#===============================================================================
# wildCard2regularExpr
#===============================================================================
def wildCard2regularExpr(wildCard, ignoreCase = True):
   """
   Ritorna la conversione di una stringa con wildcards (es. "gas*")
   in forma di regular expression (es. "[g][a][s].*")
   """
   # ? -> .
   # * -> .*
   # altri caratteri -> [carattere]
   regularExpr = "" 
   for ch in wildCard:
      if ch == "?":
         regularExpr = regularExpr + "."
      elif ch == "*":
         regularExpr = regularExpr + ".*"
      else:
         if ignoreCase:
            regularExpr = regularExpr + "[" + ch.upper() + ch.lower() + "]"
         else:
            regularExpr = regularExpr + "[" + ch + "]"         

   return regularExpr


#===============================================================================
# str2float
#===============================================================================
def str2float(s):
   """
   Ritorna la conversione di una stringa in numero reale
   """  
   try:
      n = float(s)
      return n
   except ValueError:
      return None


#===============================================================================
# str2long
#===============================================================================
def str2long(s):
   """
   Ritorna la conversione di una stringa in numero lungo
   """  
   try:
      n = long(s)
      return n
   except ValueError:
      return None


#===============================================================================
# str2int
#===============================================================================
def str2int(s):
   """
   Ritorna la conversione di una stringa in numero intero
   """  
   try:
      n = int(s)
      return n
   except ValueError:
      return None


#===============================================================================
# str2bool
#===============================================================================
def str2bool(s):
   """
   Ritorna la conversione di una stringa in bool
   """  
   try:
      upperS = s.upper()
      # 16 = "N", 17 = "NO"
      # "F" "FALSO" 
      if upperS == "0" or \
         upperS == QadMsg.translate("QAD", "N") or \
         upperS == QadMsg.translate("QAD", "NO") or \
         upperS == QadMsg.translate("QAD", "F") or \
         upperS == QadMsg.translate("QAD", "FALSE") or \
         upperS == "FALSE":
         return False
      else:
         return True
   except ValueError:
      return None


#===============================================================================
# str2QgsPoint
#===============================================================================
def str2QgsPoint(s, lastPoint = None, currenPoint = None, oneNumberAllowed = True):
   """
   Ritorna la conversione di una stringa in punto QgsPointXY
   se <oneNumberAllowed> = False significa che s non può essere un solo numero
   che rappresenterebbe la distanza dall'ultimo punto con angolo in base al punto corrente
   (questo viene vietato quando si vuole accettare un numero o un punto)
   lastPoint viene usato solo per le espressioni tipo @10<45 (dall'ultimo punto, lunghezza 10, angolo 45 gradi)
   o @ (dall'ultimo punto)
   o @10,20 (dall'ultimo punto, + 10 per la X e + 20 per la Y)
   o 100 (dall'ultimo punto, distanza 100, angolo in base al punto corrente)
   """   
   expression = s.strip() # senza spazi iniziali e finali
   if len(expression) == 0:
      return None

   if expression[0] == "@": # coordinate relative a lastpoint
      if lastPoint is None:
         return None
      
      if len(expression) == 1:
         return lastPoint
      
      expression = expression[1:] # scarto il primo carattere "@"
      coords = expression.split(",")
      if len(coords) == 2:
         OffSetX = str2float(coords[0].strip())
         OffSetY = str2float(coords[1].strip())
         if (OffSetX is None) or (OffSetY is None):
            return None
         return QgsPointXY(lastPoint.x() + OffSetX, lastPoint.y() + OffSetY)
      else:
         if len(coords) != 1:
            return None
         # verifico se si sta usando la coordinata polare
         expression = coords[0].strip()
         values = expression.split("<")
         if len(values) != 2: 
            return None
         dist = str2float(values[0].strip())
         angle = str2float(values[1].strip())
         if (dist is None) or (angle is None):
            return None     
         coords = getPolarPointByPtAngle(lastPoint, math.radians(angle), dist)     
         return QgsPointXY(coords[0], coords[1])
   else:
      # verifico se è specificato un CRS
      CRS, newExpr = strFindCRS(expression)
      if CRS is not None:
         if CRS.isGeographic():
            pt = strLatLon2QgsPoint(newExpr)
         else:               
            coords = newExpr.split(",")
            if len(coords) != 2:
               return None
            x = str2float(coords[0].strip())
            y = str2float(coords[1].strip())
            if (x is None) or (y is None):
               return None
            pt = QgsPointXY(x, y)
            
         if pt is not None:
            destCRS = qgis.utils.iface.mapCanvas().mapSettings().destinationCrs() # CRS corrente
            return QgsCoordinateTransform(CRS, destCRS, QgsProject.instance()).transform(pt) # trasformo le coord


      coords = expression.split(",")
      if len(coords) == 2:  # coordinate assolute
         x = str2float(coords[0].strip())
         y = str2float(coords[1].strip())
         if (x is None) or (y is None):
            return None
         return QgsPointXY(x, y)
      else:
         if oneNumberAllowed == False: # vietato che la stringa sia un solo numero
            return None
         
         dist = str2float(expression)

         if (dist is None) or (lastPoint is None) or (currenPoint is None):
            return None
         
         angle = getAngleBy2Pts(lastPoint, currenPoint)
         coords = getPolarPointByPtAngle(lastPoint, angle, dist)     
         return QgsPointXY(coords[0], coords[1])


#===============================================================================
# pointToStringFmt
#===============================================================================
def pointToStringFmt(pt):
   """
   Ritorna la conversione di un punto QgsPointXY in stringa formattata
   """
   return numToStringFmt(pt.x()) + "," + numToStringFmt(pt.y())


#===============================================================================
# numToStringFmt
#===============================================================================
def numToStringFmt(n, textDecimals = 4, textDecimalSep = '.', \
                      textSuppressLeadingZeros = False, textDecimalZerosSuppression = True,
                      textPrefix = "", textSuffix = ""):
   """
   Restituisce la conversione di un numero (int o float) in stringa formattata
   """
   strIntPart, strDecPart = getStrIntDecParts(round(n, textDecimals)) # numero di decimali
   
   if strIntPart == "0" and textSuppressLeadingZeros == True: # per sopprimere o meno gli zero all'inizio del testo
      strIntPart = ""
   
   for i in range(0, textDecimals - len(strDecPart), 1):  # aggiunge "0" per arrivare al numero di decimali
      strDecPart = strDecPart + "0"
      
   if textDecimalZerosSuppression == True: # per sopprimere gli zero finali nei decimali
      strDecPart = strDecPart.rstrip("0")
   
   formattedText = "-" if n < 0 else "" # segno
   formattedText = formattedText + strIntPart # parte intera
   if len(strDecPart) > 0: # parte decimale
      formattedText = formattedText + textDecimalSep + strDecPart # Separatore dei decimali
   # aggiungo prefisso e suffisso per il testo della quota
   return textPrefix + formattedText + textSuffix


#===============================================================================
# strLatLon2QgsPoint
#===============================================================================
def strFindCRS(s):
   """
   Cerca il sistema di coordinate in una stringa indicante un punto (usa authid).
   Il sistema di coordinate va espresso in qualsiasi punto della stringa e deve essere
   racchiuso tra parentesi tonde (es "111,222 (EPSG:3003)")
   Ritorna il SR e la stringa depurata del SR (es "111,222")
   """
   initial = s.find("(")
   if initial == -1:
      return None, s
   final = s.find(")")
   if initial > final:
      return None, s
   authId = s[initial+1:final]
   authId = authId.strip() # senza spazi iniziali e finali
   return QgsCoordinateReferenceSystem(authId), s.replace(s[initial:final+1], "")


#===============================================================================
# strLatLon2QgsPoint
#===============================================================================
def strLatLon2QgsPoint(s):
   """
   Ritorna la conversione di una stringa contenente una coordinata in latitudine longitudine
   in punto QgsPointXY.
   
   Sono supportati i seguenti formati:
   DDD gradi decimali (49.11675S o S49.11675 o 49.11675 S o S 49.11675 o -49.1167)
   DMS gradi minuti secondi (49 7 20.06)
   DMM gradi minuti con secondi decimali (49 7.0055)
   
   Sintassi latitudine longitudine:
   Il separatore può essere uno spazio, puoi anche usare ' per i minuti e " per i secondi (47 7'20.06")
   La notazione di direzione è N, S, E, W maiuscolo o minuscolo prima o dopo la coordinata
   ("N 37 24 23.3" o "N37 24 23.3" o "37 24 23.3 N" o "37 24 23.3N")
   Puoi usare anche le coordinate negative per l'ovest e il sud.
   
   La prima coordinata viene interpretata come latitudine a meno che specifichi una lettera di direzione (E o W)
   ("122 05 08.40 W 37 25 19.07 N")
   Puoi usare uno spazio, una virgola o una barra per delimitare le coppie di valori
   ("37.7 N 122.2 W" o "37.7 N,122.2 W" o "37.7 N/122.2 W") 
   """
   expression = s.strip() # senza spazi iniziali e finali
   if len(expression) == 0:
      return None
   
   numbers = []
   directions = []
   word = ""
   for ch in s:
      if ch.isnumeric() or ch == "." or ch == "-":
         word += ch
      else:
         if len(word) > 0:
            n = str2float(word)
            if n is None:
               return None
            numbers.append(n)
            word = ""
         if ch == "N" or ch == "n" or ch == "S" or ch == "s" or ch == "E" or ch == "e" or ch == "W" or ch == "w":
            directions.append(ch.upper())
            word = ""

   directions_len = len(directions)
   if directions_len != 0 and directions_len != 2:
      return None

   numbers_len = len(numbers)
   if numbers_len == 2: # DDD
      lat = numbers[0]
      lon = numbers[1]
   elif numbers_len == 4: # DMM 
      degrees = numbers[0]
      minutes = numbers[1]
      lat = degrees + minutes / 60
      degrees = numbers[2]
      minutes = numbers[3]
      lon = degrees + minutes / 60
   elif numbers_len == 6: # DMS
      degrees = numbers[0]
      minutes = numbers[1]
      seconds = numbers[2]
      lat = degrees + minutes / 60 + seconds / 3600
      degrees = numbers[3]
      minutes = numbers[4]
      seconds = numbers[5]
      lon = degrees + minutes / 60 + seconds / 3600
   else:
      return None
   
   if directions_len == 2:
      if lat < 0 or lon < 0:
         return None
      if directions[0] == "N" or directions[0] == "S": # latitude first
         if directions[0] == "S":
            lat = -lat
      elif directions[0] == "E" or directions[0] == "W": # longitude first
         dummy = lat
         lat = lon if directions[0] == "E" else -lon
         lon = dummy if directions[1] == "S" else -value2
      else:
         return None
         
      return QgsPointXY(lon, lat)
   else: # latitude first
      return QgsPointXY(lon, lat)


#===============================================================================
# strip
#===============================================================================
def strip(s, stripList):
   """
   Rimuove dalla stringa <s> tutte le stringhe nella lista <stripList> che sono 
   all'inizio e anche alla fine della stringa <s>
   """
   for item in stripList:
      s = s.strip(item) # rimuovo prima e dopo
   return s


#===============================================================================
# findFile
#===============================================================================
def findFile(fileName):
   """
   Cerca il file indicato usando i percorsi indicati dalla variabile "SUPPORTPATH" 
   più il percorso locale di QAD. Ritorna il percorso del file in caso di successo
   oppure "" in caso di file non trovato
   """
   path = QadVariables.get(QadMsg.translate("Environment variables", "SUPPORTPATH"))
   if len(path) > 0:
      path += ";"        
   path += QgsApplication.qgisSettingsDirPath() + "python/plugins/qad/"
   # lista di directory separate da ";"
   dirList = path.strip().split(";")
   for _dir in dirList:
      _dir = QDir.cleanPath(_dir)
      if _dir != "":
         if _dir.endswith("/") == False:
            _dir = _dir + "/"
         _dir = _dir + fileName
         
         if os.path.exists(_dir):
            return _dir

   return ""

   return s


#===============================================================================
# getQADPath
#===============================================================================
def getQADPath():
   """
   Restituisce la path di installazione di QAD
   """
   return os.path.dirname(os.path.realpath(__file__))


#===============================================================================
# toRadians
#===============================================================================
def toRadians(angle):
   """
   Converte da gradi a radianti
   """
   return math.radians(angle)


#===============================================================================
# toDegrees
#===============================================================================
def toDegrees(angle):
   """
   Converte da radianti a gradi 
   """
   return math.degrees(angle)


#===============================================================================
# normalizeAngle
#===============================================================================
def normalizeAngle(angle, norm = math.pi * 2):
   """
   Normalizza un angolo a da [0 - 2pi] o da [0 - pi].
   Così, ad esempio, se un angolo é più grande di 2pi viene ridotto all'angolo giusto 
   (il raffronto in gradi sarebbe da 380 a 20 gradi) o se é negativo diventa positivo
   (il raffronto in gradi sarebbe da -90 a 270 gradi)  
   """
   if angle == 0:
      return 0
   if angle > 0:
      return angle % norm
   else:
      return norm - ((-angle) % norm)


#===============================================================================
# getStrIntDecParts
#===============================================================================
def getStrIntDecParts(n):
   """
   Restituisce due stringhe rappresentanti la parte intera senza segno e la parte decimale di un numero
   """
   if type(n) == int or type(n) == long or type(n) == float:
      nStr = str(n)
      if "." in nStr:
         parts = nStr.split(".")
         return str(abs(int(parts[0]))), parts[1]
      else:
         return nStr, ""
   else:
      return None
   

#===============================================================================
# distMapToLayerCoordinates
#===============================================================================
def distMapToLayerCoordinates(dist, canvas, layer):
   # trovo il punto centrale dello schermo  
   boundBox = canvas.extent()
   x = (boundBox.xMinimum() + boundBox.xMaximum()) / 2
   y = (boundBox.yMinimum() + boundBox.yMaximum()) / 2
   pt1 = QgsPointXY(x, y)
   pt2 = QgsPointXY(x + dist, y)
   transformedPt1 = canvas.mapSettings().mapToLayerCoordinates(layer, pt1)
   transformedPt2 = canvas.mapSettings().mapToLayerCoordinates(layer, pt2)
   return getDistance(transformedPt1, transformedPt2)
         

#===============================================================================
# filterFeaturesByType
#===============================================================================
def filterFeaturesByType(features, filterByGeomType):
   """
   Riceve una lista di features e la tipologia di geometria che deve essere filtrata.
   La funzione modifica la lista <features> depurandola dalle geometrie di tipo diverso
   da <filterByGeomType>.   
   Restituisce 3 liste rispettivamente di punti, linee e poligoni.
   La lista del tipo indicato dal parametro <filterByGeomType> sarà vuota, le altre
   due liste conterranno geometrie.
   """
   resultPoint = []
   resultLine = []
   resultPolygon = []

   for i in range(len(features) - 1, -1, -1): 
      f = features[i]
      g = f.geometry()
      geomType = g.type()
      if geomType != filterByGeomType:
         if geomType == QgsWkbTypes.PointGeometry:      
            resultPoint.append(QgsGeometry(g))
            
         elif geomType == QgsWkbTypes.LineGeometry:      
            resultLine.append(QgsGeometry(g))
            
         elif geomType == QgsWkbTypes.PolygonGeometry:      
            resultPolygon.append(QgsGeometry(g))
            
         del features[i]

   return resultPoint, resultLine, resultPolygon
         

#===============================================================================
# filterGeomsByType
#===============================================================================
def filterGeomsByType(geoms, filterByGeomType):
   """
   Riceve una lista di geometrie e la tipologia di geometria che deve essere filtrata.
   La funzine modifica la lista <geoms> depurandola dalle geometrie di tipo diverso
   da <filterByGeomType>.   
   Restituisce 3 liste rispettivamente di punti, linee e poligoni.
   La lista del tipo indicato dal parametro <filterByGeomType> sarà vuota, le altre
   due liste conterranno geometrie.
   """
   resultPoint = []
   resultLine = []
   resultPolygon = []

   for i in range(len(geoms) - 1, -1, -1): 
      g = geoms[i]
      geomType = g.type()
      if geomType != filterByGeomType:            
         if geomType == QgsWkbTypes.PointGeometry:      
            resultPoint.append(QgsGeometry(g))
            
         elif geomType == QgsWkbTypes.LineGeometry:      
            resultLine.append(QgsGeometry(g))
            
         elif geomType == QgsWkbTypes.PolygonGeometry:      
            resultPolygon.append(QgsGeometry(g))
            
         del geoms[i]

   return resultPoint, resultLine, resultPolygon


#===============================================================================
# getEntSelCursor
#===============================================================================
def getEntSelCursor():
   """
   Ritorna l'immagine del cursore per la selezione di un'entità
   """
   
   size = 1 + QadVariables.get(QadMsg.translate("Environment variables", "PICKBOX")) * 2
   # <width/cols> <height/rows> <colors> <char on pixel>
   row = str(size) + " " + str(size) + " 2 1"
   xpm = [row]
   # <Colors> 
   xpm.append("  c None")
   xpm.append("+ c " + QadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
   # <Pixels>
   # es . "+++++",
   # es . "+   +",
   # es . "+   +",
   # es . "+   +",
   # es . "+++++",
   xpm.append("+" * size)
   if size > 1:
      row = "+" + " " * (size - 2) + "+"
      for i in range(size - 2): # da 0
         xpm.append(row)
      xpm.append("+" * size)
      
   return QCursor(QPixmap(xpm))


def getGetPointCursor():
   """
   Ritorna l'immagine del cursore per la selezione di un punto 
   """
   pickBox = QadVariables.get(QadMsg.translate("Environment variables", "CURSORSIZE"))
   size = 1 + pickBox * 2
   # <width/cols> <height/rows> <colors> <char on pixel>
   row = str(size) + " " + str(size) + " 2 1"
   xpm = [row]
   # <Colors> 
   xpm.append("  c None")
   xpm.append("+ c " + QadVariables.get(QadMsg.translate("Environment variables", "PICKBOXCOLOR")))
   # <Pixels>
   # es . "  +  ",
   # es . "  +  ",
   # es . "+++++",
   # es . "  +  ",
   # es . "  +  ",
   row = (" " * pickBox) + "+" + (" " * pickBox) 
   xpm.append(row)
   if size > 1:
      for i in range(pickBox - 1): # da 0
         xpm.append(row)
      xpm.append("+" * (size))
      for i in range(pickBox - 1): # da 0
         xpm.append(row)
      
   return QCursor(QPixmap(xpm))

   
#===============================================================================
# getFeatureRequest
#===============================================================================
def getFeatureRequest(fetchAttributes = [], fetchGeometry = True, \
                      rect = None, useIntersect = False):
   # PER ORA <fetchGeometry> NON VIENE USATO PERCHE' NON SO FARE IL CAST in QgsFeatureRequest.Flags
   # restituisce un oggetto QgsFeatureRequest per interrogare un layer
   # It can get 4 arguments, all of them are optional:
   # fetchAttributes: List of attributes which should be fetched.
   #                  None = disable fetching attributes, Empty list means that all attributes are used.
   #                  default: empty list
   # fetchGeometry: Whether geometry of the feature should be fetched. Default: True
   # rect: Spatial filter by rectangle.
   #       None = nessuna ricerca spaziale, empty rect means (QgsRectangle()), all features are fetched.
   #       Default: none
   # useIntersect: When using spatial filter, this argument says whether accurate test for intersection 
   # should be done or whether test on bounding box suffices.
   # This is needed e.g. for feature identification or selection. Default: False
      
   request = QgsFeatureRequest()
   
   #flag = QgsFeatureRequest.NoFlags
        
#    if fetchGeometry == False:
#       flag = flag | QgsFeatureRequest.NoGeometry
             
   if rect is not None:
      r = QgsRectangle(rect)
      
        # non serve più
#       # Se il rettangolo é schiacciato in verticale o in orizzontale
#       # risulta una linea e la funzione fa casino, allora in questo caso lo allargo un pochino
#       if doubleNear(r.xMinimum(), r.xMaximum(), 1.e-6):
#          r.setXMaximum(r.xMaximum() + 1.e-6)
#          r.setXMinimum(r.xMinimum() - 1.e-6)
#       if doubleNear(r.yMinimum(), r.yMaximum(), 1.e-6):
#          r.setYMaximum(r.yMaximum() + 1.e-6)
#          r.setYMinimum(r.yMinimum() - 1.e-6)
         
      request.setFilterRect(r)

      if useIntersect == True:
         request.setFlags(QgsFeatureRequest.ExactIntersect)   

   if fetchAttributes is None:
      request.setSubsetOfAttributes([])
   else:
      if len(fetchAttributes) > 0:
         request.setSubsetOfAttributes(fetchAttributes)

   return request


#===============================================================================
# getVisibleVectorLayers
#===============================================================================
def getVisibleVectorLayers(canvas):
   # Tutti i layer vettoriali visibili
   layers = canvas.layers()
   for i in range(len(layers) - 1, -1, -1):
      # se il layer non è vettoriale o non è visibile a questa scala
      if layers[i].type() != QgsMapLayer.VectorLayer or \
         layers[i].hasScaleBasedVisibility() and \
         (canvas.mapSettings().scale() > layers[i].minimumScale() or canvas.mapSettings().scale() < layers[i].maximumScale()):
         del layers[i]
   return layers


#===============================================================================
# getSnappableVectorLayers
#===============================================================================
def getSnappableVectorLayers(canvas):
   # make QAD honor QGIS's snap settings (ALL LAYERS, ACTIVE LAYER, ADVANCED).
   # proposed by Oliver Dalang
   enabled = canvas.snappingUtils().config().enabled()
   mode = canvas.snappingUtils().config().mode()

   if enabled and mode == QgsSnappingConfig.ActiveLayer:
      if qgis.utils.iface.activeLayer() is None:
         layers = []
      else:
         layers = [qgis.utils.iface.activeLayer()]
   elif enabled and mode == QgsSnappingConfig.AdvancedConfiguration:
      layers = list(cfg.layer for cfg in canvas.snappingUtils().layers())
   else: # mode == QgsSnappingConfig.AllLayers:
      layers = canvas.layers()
         
   # Solo i layer vettoriali visibili
   for i in range(len(layers) - 1, -1, -1):
      # se il layer non è vettoriale o non è visibile a questa scala
      if layers[i].type() != QgsMapLayer.VectorLayer or \
         layers[i].hasScaleBasedVisibility() and \
         (canvas.mapSettings().scale() > layers[i].minimumScale() or canvas.mapSettings().scale() < layers[i].maximumScale()):
         del layers[i]         
   return layers


#===============================================================================
# getEntSel
#===============================================================================
def getEntSel(point, mQgsMapTool, boxSize, \
              layersToCheck = None, checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
              onlyBoundary = True, onlyEditableLayers = False, \
              firstLayerToCheck = None, layerCacheGeomsDict = None, returnFeatureCached = False):
   """
   dato un punto (in screen coordinates) e un QgsMapTool, 
   la funzione cerca la prima entità dentro il quadrato
   di dimensioni <boxSize> (in pixel) centrato sul punto <point>
   layersToCheck = opzionale, lista dei layer in cui cercare
   checkPointLayer = opzionale, considera i layer di tipo punto
   checkLineLayer = opzionale, considera i layer di tipo linea
   checkPolygonLayer = opzionale, considera i layer di tipo poligono
   onlyBoundary = serve per considerare solo il bordo dei poligoni o anche il loro interno
   onlyEditableLayers = per cercare solo nei layer modificabili
   firstLayerToCheck = per ottimizzare la ricerca, primo layer da controllare
   layerCacheGeomsDict = per ottimizzare la ricerca, è una chache delle geometrie dei layer
   returnFeatureCached = per ottimizzare, ritorna la featura letta dalla cache (quando interessa solo la geometria)
   
   Restituisce una lista composta da una QgsFeature e il suo layer e il punto di selezione 
   in caso di successo altrimenti None 
   """           
   
   if checkPointLayer == False and checkLineLayer == False and checkPolygonLayer == False:
      return None
      
   #QApplication.setOverrideCursor(Qt.WaitCursor)
   
   if layersToCheck is None:
      # Tutti i layer vettoriali visibili
      _layers = getVisibleVectorLayers(mQgsMapTool.canvas) # Tutti i layer vettoriali visibili
   else:
      # solo la lista passata come parametro
      _layers = layersToCheck

   # se il processo può essere ottimizzato con il primo layer in cui cercare
   if firstLayerToCheck is not None:
      # considero solo se layer vettoriale visibile che è filtrato per tipo
      if firstLayerToCheck.type() == QgsMapLayer.VectorLayer and \
         (onlyEditableLayers == False or firstLayerToCheck.isEditable()) and \
         (firstLayerToCheck.hasScaleBasedVisibility() == False or \
          (mQgsMapTool.canvas.mapSettings().scale() <= firstLayerToCheck.minimumScale() and mQgsMapTool.canvas.mapSettings().scale() >= firstLayerToCheck.maximumScale())) and \
         ((firstLayerToCheck.geometryType() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
          (firstLayerToCheck.geometryType() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
          (firstLayerToCheck.geometryType() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)):
         # restituisce feature, point
         res = getEntSelOnLayer(point, mQgsMapTool, boxSize, firstLayerToCheck, onlyBoundary, layerCacheGeomsDict, returnFeatureCached)
         if res is not None:
            return res[0], firstLayerToCheck, res[1]
      
   for layer in _layers: # ciclo sui layer
      # se il processo può essere ottimizzato con il primo layer in cui cercare lo salto in questo ciclo
      if (firstLayerToCheck is not None) and firstLayerToCheck.id() == layer.id():
         continue;
      
      # considero solo i layer vettoriali che sono filtrati per tipo
      if layer.type() == QgsMapLayer.VectorLayer and \
          (onlyEditableLayers == False or layer.isEditable()) and \
          ((layer.geometryType() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
           (layer.geometryType() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
           (layer.geometryType() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)):
         # restituisce feature, point
         res = getEntSelOnLayer(point, mQgsMapTool, boxSize, layer, onlyBoundary, layerCacheGeomsDict, returnFeatureCached)
         if res is not None:
            return res[0], layer, res[1]

   #QApplication.restoreOverrideCursor()
   return None


#===============================================================================
# getEntSelOnLayer
#===============================================================================
def getEntSelOnLayer(point, mQgsMapTool, boxSize, layer, onlyBoundary = True, \
                     layerCacheGeomsDict = None, returnFeatureCached = False):
   """
   dato un punto (in screen coordinates) e un QgsMapTool,
   la funzione cerca la prima entità del layer dentro il quadrato
   di dimensioni <boxSize> (in pixel) centrato sul punto <point>
   onlyBoundary = serve per considerare solo il bordo dei poligoni o anche il loro interno
   layerCacheGeomsDict = per ottimizzare la ricerca, è una chache delle geometrie dei layer
   
   Restituisce una lista composta da una QgsFeature e il punto di selezione 
   in caso di successo altrimenti None 
   """           
   layerCoords = mQgsMapTool.toLayerCoordinates(layer, point)
   ToleranceInMapUnits = QgsTolerance.toleranceInMapUnits(boxSize, layer, \
                                                          mQgsMapTool.canvas.mapSettings(), \
                                                          QgsTolerance.Pixels) / 2

   selectRect = QgsRectangle(layerCoords.x() - ToleranceInMapUnits, layerCoords.y() - ToleranceInMapUnits, \
                             layerCoords.x() + ToleranceInMapUnits, layerCoords.y() + ToleranceInMapUnits)

   # se il processo può essere ottimizzato con la cache
   if layerCacheGeomsDict is not None:
      cachedFeatures = layerCacheGeomsDict.getFeatures(layer, selectRect)
      
      featureRequest = QgsFeatureRequest()
      featureRequest.setSubsetOfAttributes([])
      
      for cachedFeature in cachedFeatures:
         # se é un layer contenente poligoni allora verifico se considerare solo i bordi
         if onlyBoundary == False or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            if cachedFeature.geometry().intersects(selectRect):
               if returnFeatureCached: # ritorna la feature della cache
                  return cachedFeature, point
               # ottengo la feature del layer
               featureRequest.setFilterFid(cachedFeature.attribute("index"))
               featureIterator = layer.getFeatures(featureRequest)      
               for feature in featureIterator:
                  return feature, point
         else:
            # considero solo i bordi delle geometrie e non lo spazio interno dei poligoni
            # Riduco le geometrie in point o polyline
            geoms = asPointOrPolyline(cachedFeature.geometry())
            for g in geoms:
               #start = time.time() # test
               #for i in range(1, 10):
               if g.intersects(selectRect):
                  if returnFeatureCached: # ritorna la feature della cache
                     return cachedFeature, point
                  
                  # ottengo la feature del layer
                  featureRequest.setFilterFid(cachedFeature.attribute("index"))
                  featureIterator = layer.getFeatures(featureRequest)      
                  for feature in featureIterator:
                     return feature, point
               #tempo = ((time.time() - start) * 1000) # test
               #tempo += 0 # test
   else:
      featureIterator = layer.getFeatures(getFeatureRequest([], True, selectRect, True))
      feature = QgsFeature()
   
      # se é un layer contenente poligoni allora verifico se considerare solo i bordi
      if onlyBoundary == False or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
         for feature in featureIterator:
            return feature, point
      else:
         # considero solo i bordi delle geometrie e non lo spazio interno dei poligoni
         for feature in featureIterator:
            # Riduco le geometrie in point o polyline
            geoms = asPointOrPolyline(feature.geometry())
            for g in geoms:
               if g.intersects(selectRect):
                  return feature, point

   return None


#===============================================================================
# getFeatureById
#===============================================================================
def getFeatureById(layer, id):
   """
   Ricava una feature dal suo id.
   """
   feature = QgsFeature()
   if layer.getFeatures(QgsFeatureRequest().setFilterFid(id)).nextFeature(feature):
      return feature
   else:
      return None

   
#===============================================================================
# isGeomInBox
#===============================================================================
def isGeomInBox(point, mQgsMapTool, geom, boxSize, crs = None, \
                checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
                onlyBoundary = True):
   """
   dato un punto (in screen coordinates) e un QgsMapTool, 
   la funzione verifica se la geometria é dentro il quadrato
   di dimensioni boxSize (in pixel) centrato sul punto
   geom = geometria da verificare
   crs = sistema di coordinate della geometria (se = NON significa in map coordinates)
   checkPointLayer = opzionale, considera la geometria di tipo punto
   checkLineLayer = opzionale, considera la geometria di tipo linea
   checkPolygonLayer = opzionale, considera la geometria di tipo poligono
   onlyBoundary = serve per considerare solo il bordo dei poligoni o anche il loro interno
   Restituisce True se la geometria é nel quadrato di dimensione boxSize in (pixel) altrimenti False 
   """   
   if geom is None:
      return False
   if checkPointLayer == False and checkLineLayer == False and checkPolygonLayer == False:
      return False
   
   # considero solo la geometria filtrata per tipo
   if ((geom.type() == QgsWkbTypes.PointGeometry and checkPointLayer == True) or \
       (geom.type() == QgsWkbTypes.LineGeometry and checkLineLayer == True) or \
       (geom.type() == QgsWkbTypes.PolygonGeometry and checkPolygonLayer == True)):      
      mapPoint = mQgsMapTool.toMapCoordinates(point)
      mapGeom = QgsGeometry(geom)
      if crs is not None and mQgsMapTool.canvas.mapSettings().destinationCrs() != crs:
         # trasformo le coord della geometria in map coordinates
         coordTransform = QgsCoordinateTransform(crs, mQgsMapTool.canvas.mapSettings().destinationCrs(), QgsProject.instance())          
         mapGeom.transform(coordTransform)      
         
      ToleranceInMapUnits = boxSize * mQgsMapTool.canvas.mapSettings().mapUnitsPerPixel()
      selectRect = QgsRectangle(mapPoint.x() - ToleranceInMapUnits, mapPoint.y() - ToleranceInMapUnits, \
                                mapPoint.x() + ToleranceInMapUnits, mapPoint.y() + ToleranceInMapUnits)
                                           
      # se é una geometria poligono allora verifico se considerare solo i bordi
      if onlyBoundary == False or geom.type() != QgsWkbTypes.PolygonGeometry:
         if mapGeom.intersects(selectRect):
            return True
      else:
         # considero solo i bordi della geometria e non lo spazio interno del poligono
         # Riduco la geometria in point o polyline
         geoms = asPointOrPolyline(mapGeom)
         for g in geoms:
            if g.intersects(selectRect):
               return True
   
   return False

   
#===============================================================================
# getGeomInBox
#===============================================================================
def getGeomInBox(point, mQgsMapTool, geoms, boxSize, crs = None, \
                 checkPointLayer = True, checkLineLayer = True, checkPolygonLayer = True,
                 onlyBoundary = True):
   """
   dato un punto (in screen coordinates) e un QgsMapTool, 
   la funzione cerca la prima geometria dentro il quadrato
   di dimensioni boxSize (in pixel) centrato sul punto
   geoms = lista di geometrie da verificare
   crs = sistema di coordinate della geometria (se = NON significa in map coordinates)
   checkPointLayer = opzionale, considera la geometria di tipo punto
   checkLineLayer = opzionale, considera la geometria di tipo linea
   checkPolygonLayer = opzionale, considera la geometria di tipo poligono
   onlyBoundary = serve per considerare solo il bordo dei poligoni o anche il loro interno
   Restituisce la geometria che é nel quadrato di dimensini boxSize altrimenti None 
   """   
   if geoms is None:
      return False
   for geom in geoms:
      if isGeomInBox(point, mQgsMapTool, geom, boxSize, crs, checkPointLayer, checkLineLayer, checkPolygonLayer, onlyBoundary):
         return geom
   return None


#===============================================================================
# getActualSingleSelection
#===============================================================================
def getActualSingleSelection(layers):
   """
   la funzione cerca se esiste una sola entità selezionata tra i layer
   Restituisce un QgsFeature e il suo layer in caso di successo altrimenti None 
   """
   selFeature = []

   for layer in layers: # ciclo sui layer
      if (layer.type() == QgsMapLayer.VectorLayer):
         selectedFeatureCount = layer.selectedFeaturCount()
         if selectedFeatureCount == 1:
            selFeature = layer.selectedFeatures()
            selLayer = Layer
         elif selectedFeatureCount > 1:
            del selFeature[:] # svuoto la lista
            break
      
   if len(selFeature) == 1: # se c'era solo una entità selezionata
      return selFeature[0], selLayer
  
   return None


def deselectAll(layers):
   """
   la funzione deseleziona tutte le entità selezionate nei layer
   """
   for layer in layers: # ciclo sui layer
      if (layer.type() == QgsMapLayer.VectorLayer):
         layer.removeSelection()


#===============================================================================
# appendUniquePointToList
#===============================================================================
def appendUniquePointToList(pointList, point):
   """
   Aggiunge un punto alla lista verificando che non sia già presente.
   Resituisce True se l'inserimento é avvenuto False se il punto c'era già.
   """
   for iPoint in pointList:
      if ptNear(iPoint, point):
         return False

   pointList.append(point)
   return True


#===============================================================================
# getPerpendicularPointOnInfinityLine
#===============================================================================
def getPerpendicularPointOnInfinityLine(p1, p2, pt):
   """
   la funzione ritorna il punto di proiezione perpendicolare di pt 
   alla linea passante per p1-p2.
   """
   
   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()
                          
   if doubleNear(diffX, 0): # se la retta passante per p1 e p2 é verticale
      return QgsPointXY(p1.x(), pt.y())
   elif doubleNear(diffY, 0): # se la retta passante per p1 e p2 é orizzontale
      return QgsPointXY(pt.x(), p1.y())
   else:
      coeff = diffY / diffX
      x = (coeff * p1.x() - p1.y() + pt.x() / coeff + pt.y()) / (coeff + 1 / coeff)
      y = coeff * (x - p1.x()) + p1.y()
      
      return QgsPointXY(x, y)


#===============================================================================
# getInfinityLinePerpOnMiddle
#===============================================================================
def getInfinityLinePerpOnMiddle(pt1, pt2):
   """
   dato un segmento pt1-pt2, la funzione trova una linea perpendicolare al segmento
   che passa per il suo punto medio. La funzione restituisce 2 punti della linea.
   """
   ptMiddle = getMiddlePoint(pt1, pt2)
   dist = getDistance(pt1, ptMiddle)
   if dist == 0:
      return None
   angle = getAngleBy2Pts(pt1, pt2) + math.pi / 2
   pt2Middle = getPolarPointByPtAngle(ptMiddle, angle, dist)
   return ptMiddle, pt2Middle


#===============================================================================
# getMiddleAngle
#===============================================================================
def getMiddleAngle(angle1, angle2):
   """
   dati 2 angoli, la funzione restituisce l'angolo medio. 
   """
   a1 = normalizeAngle(angle1)
   a2 = normalizeAngle(angle2)
   if a2 < a1: a2 = (math.pi * 2) + a2
   return normalizeAngle((a2 + a1) / 2)


#===============================================================================
# getBisectorInfinityLine
#===============================================================================
def getBisectorInfinityLine(pt1, pt2, pt3, acuteMode = True):
   """
   dato un angolo definito da 3 punti il cui secondo punto é vertice dell'angolo,
   la funzione restituisce la linea bisettrice dell'angolo attraverso 2 punti 
   della linea (il vertice dell'angolo e un altro punto calcolato distante quanto
   la distanza di pt1 da pt2).
   acuteMode = True considera l'angolo acuto, acuteMode = False l'angolo ottuso 
   """   
   angle1 = getAngleBy2Pts(pt2, pt1)
   angle2 = getAngleBy2Pts(pt2, pt3)
   angle = (angle1 + angle2) / 2 # angolo medio
#   return pt2, getPolarPointByPtAngle(pt2, angle, 10)
   
   dist = getDistance(pt1, pt2)
   ptProj = getPolarPointByPtAngle(pt2, angle, dist)
   ptInverseProj = getPolarPointByPtAngle(pt2, angle - math.pi, dist)
   if getDistance(pt1, ptProj) < getDistance(pt1, ptInverseProj):
      if acuteMode == True:
         return pt2, ptProj
      else:
         return pt2, ptInverseProj
   else:
      if acuteMode == True:
         return pt2, ptInverseProj
      else:
         return pt2, ptProj


#===============================================================================
# getXOnInfinityLine
#===============================================================================
def getXOnInfinityLine(p1, p2, y):
   """
   data la coordinata Y di un punto la funzione ritorna la coordinata X dello stesso
   sulla linea passante per p1-p2 
   """
   
   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()
                          
   if doubleNear(diffX, 0): # se la retta passante per p1 e p2 é verticale
      return p1.x()
   elif doubleNear(diffY, 0): # se la retta passante per p1 e p2 é orizzontale
      return None # infiniti punti
   else:
      coeff = diffY / diffX
      return p1.x() + (y - p1.y()) / coeff


#===============================================================================
# getYOnInfinityLine
#===============================================================================
def getYOnInfinityLine(p1, p2, x):
   """
   data la coordinata Y di un punto la funzione ritorna la coordinata X dello stesso
   sulla linea passante per p1-p2 
   """
   
   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()
                          
   if doubleNear(diffX, 0): # se la retta passante per p1 e p2 é verticale
      return None # infiniti punti
   elif doubleNear(diffY, 0): # se la retta passante per p1 e p2 é orizzontale
      return p1.y()
   else:
      coeff = diffY / diffX
      return p1.y() + (x - p1.x()) * coeff


#===============================================================================
# getSqrDistance
#===============================================================================
def getSqrDistance(p1, p2):
   """
   la funzione ritorna la distanza al quadrato tra 2 punti (QgsPointXY)
   """
   dx = p2.x() - p1.x()
   dy = p2.y() - p1.y()
   
   return dx * dx + dy * dy


#===============================================================================
# getDistance
#===============================================================================
def getDistance(p1, p2):
   """
   la funzione ritorna la distanza tra 2 punti (QgsPointXY)
   """
   return math.sqrt(getSqrDistance(p1, p2))


#===============================================================================
# getMinDistancePtBetweenSegmentAndPt
#===============================================================================
def getMinDistancePtBetweenSegmentAndPt(p1, p2, pt):
   """
   la funzione ritorna il punto di distanza minima e la distanza minima tra un segmento ed un punto
   (<punto di distanza minima><distanza minima>)
   """
   if isPtOnSegment(p1, p2, pt) == True:
      return [pt, 0]
   perpPt = getPerpendicularPointOnInfinityLine(p1, p2, pt)
   if perpPt is not None:
      if isPtOnSegment(p1, p2, perpPt) == True:
         return [perpPt, getDistance(perpPt, pt)]

   distFromP1 = getDistance(p1, pt)
   distFromP2 = getDistance(p2, pt)
   if distFromP1 < distFromP2:
      return [p1, distFromP1]
   else:
      return [p2, distFromP2]


#===============================================================================
# getMiddlePoint
#===============================================================================
def getMiddlePoint(p1, p2):
   """
   la funzione ritorna il punto medio tra 2 punti (QgsPointXY)
   """
   x = (p1.x() + p2.x()) / 2
   y = (p1.y() + p2.y()) / 2
   
   return QgsPointXY(x, y)


#===============================================================================
# getAngleBy2Pts
#===============================================================================
def getAngleBy2Pts(p1, p2, tolerance = None):
   """
   la funzione ritorna l'angolo in radianti della retta passante per p1 e p2
   """
   diffX = p2.x() - p1.x()
   diffY = p2.y() - p1.y()
   if doubleNear(diffX, 0, tolerance): # se la retta passante per p1 e p2 é verticale
      if p1.y() < p2.y():
         angle = math.pi / 2
      else :
         angle = math.pi * 3 / 2
   elif doubleNear(diffY, 0, tolerance): # se la retta passante per p1 e p2 é orizzontale
      if p1.x() <= p2.x():
         angle = 0.0
      else:
         angle = math.pi
   else:
      angle = math.atan(diffY / diffX)
      if diffX < 0:
         angle = math.pi + angle
      else:
         if diffY < 0:
            angle = 2 * math.pi + angle

   return angle


#===============================================================================
# getAngleBy3Pts
#===============================================================================
def getAngleBy3Pts(p1, vertex, p2, clockWise):
   """
   la funzione ritorna l'angolo in radianti dell'angolo che parte da <p1> 
   per arrivare a <p2> con vertice <vertex> nella direzione <clockWise> (oraria o antioraria)
   """
   angle1 = getAngleBy2Pts(p1, vertex)   
   angle2 = getAngleBy2Pts(p2, vertex)
   if clockWise: # senso orario
      if angle2 > angle1:
         return (2 * math.pi) - (angle2 - angle1)      
      else:
         return angle1 - angle2      
   else: # senso anti-orario
      if angle2 < angle1:
         return (2 * math.pi) - (angle1 - angle2)      
      else:
         return angle2 - angle1


#===============================================================================
# isAngleBetweenAngles
#===============================================================================
def isAngleBetweenAngles(startAngle, endAngle, angle):
   """
   la funzione ritorna True se l'angolo si trova entro l'angolo di partenza e quello finale
   estremi compresi
   """
   _angle = angle % (math.pi * 2) # modulo
      
   if startAngle < endAngle:
      if (_angle > startAngle or doubleNear(_angle, startAngle)) and \
         (_angle < endAngle or doubleNear(_angle, endAngle)):
         return True      
   else:
      if (_angle > 0 or doubleNear(_angle, 0)) and \
         (_angle < endAngle or doubleNear(_angle, endAngle)):
         return True      

      if (_angle < (math.pi * 2) or doubleNear(_angle, (math.pi * 2))) and \
         (_angle > startAngle or doubleNear(_angle, startAngle)):
         return True      
   
   return False


def getPolarPointBy2Pts(p1, p2, dist):
   """
   la funzione ritorna il punto sulla retta passante per p1 e p2 che
   dista da p1 verso p2 <dist>.
   """
   angle = getAngleBy2Pts(p1, p2)
         
   return getPolarPointByPtAngle(p1, angle, dist)


#===============================================================================
# isPtOnSegment
#===============================================================================
def isPtOnSegment(p1, p2, point):
   """
   la funzione ritorna true se il punto é sul segmento (estremi compresi).
   p1, p2 e point sono QgsPointXY.
   """
   if p1.x() < p2.x():
      xMin = p1.x()
      xMax = p2.x()
   else:
      xMax = p1.x()
      xMin = p2.x()
	  
   # verifico se il punto può essere sul segmento 22/07/2017
   if doubleSmaller(point.x(), xMin) or doubleGreater(point.x(), xMax): return False
      
   if p1.y() < p2.y():
      yMin = p1.y()
      yMax = p2.y()
   else:
      yMax = p1.y()
      yMin = p2.y()

   # verifico se il punto può essere sul segmento 22/07/2017
   if doubleSmaller(point.y(), yMin) or doubleGreater(point.y(), yMax): return False
	  
   y = getYOnInfinityLine(p1, p2, point.x())
   if y is None: # il segmento p1-p2 é verticale
      return True
   else:
      # se il punto é sulla linea infinita che passa da p1-p2
      if doubleNear(point.y(), y):
         return True
         
   return False  


#===============================================================================
# getIntersectionPointOn2InfinityLines
#===============================================================================
def getIntersectionPointOn2InfinityLines(line1P1, line1P2, line2P1, line2P2):
   """
   la funzione ritorna il punto di intersezione tra la linea passante per line1P1-line1P2 e
   la linea passante per line2P1-line2P2.
   """
   line1DiffX = line1P2.x() - line1P1.x()
   line1DiffY = line1P2.y() - line1P1.y()

   line2DiffX = line2P2.x() - line2P1.x()
   line2DiffY = line2P2.y() - line2P1.y()   
   
   if doubleNear(line1DiffX, 0) and doubleNear(line2DiffX, 0): # se la retta1 e la retta2 sono verticale
      return None # sono parallele
   elif doubleNear(line1DiffY, 0) and doubleNear(line2DiffY, 0): # se la retta1 e la retta2 sono orizzontali
      return None # sono parallele

   if doubleNear(line1DiffX, 0): # se la retta1 é verticale
      return QgsPointXY(line1P2.x(), getYOnInfinityLine(line2P1, line2P2, line1P2.x()))
   if doubleNear(line1DiffY, 0): # se la retta1 é orizzontale
      return QgsPointXY(getXOnInfinityLine(line2P1, line2P2, line1P2.y()), line1P2.y())
   if doubleNear(line2DiffX, 0): # se la retta2 é verticale
      return QgsPointXY(line2P2.x(), getYOnInfinityLine(line1P1, line1P2, line2P2.x()))
   if doubleNear(line2DiffY, 0): # se la retta2 é orizzontale
      return QgsPointXY(getXOnInfinityLine(line1P1, line1P2, line2P2.y()), line2P2.y())

   line1Coeff = line1DiffY / line1DiffX
   line2Coeff = line2DiffY / line2DiffX

   if line1Coeff == line2Coeff: # sono parallele
      return None
     
   D = line1Coeff - line2Coeff
   # se D é così vicino a zero 
   if doubleNear(D, 0.0):
      return None   
   x = line1P1.x() * line1Coeff - line1P1.y() - line2P1.x() * line2Coeff + line2P1.y()
   x = x / D
   y = (x - line1P1.x()) * line1Coeff + line1P1.y()
   
   return QgsPointXY(x, y)


#===============================================================================
# getNearestPoints
#===============================================================================
def getNearestPoints(point, points, tolerance = 0):
   """
   Ritorna una lista di punti più vicino a point.
   """   
   result = []   
   minDist = sys.float_info.max
   
   if tolerance == 0: # solo il punto più vicino
      for pt in points:
         dist = getDistance(point, pt)
         if dist < minDist:
            minDist = dist
            nearestPoint = pt

      if minDist != sys.float_info.max: # trovato
         result.append(nearestPoint)
   else:
      nearest = getNearestPoints(point, points) # punto più vicino
      nearestPoint = nearest[0]
      
      for pt in points:
         dist = getDistance(nearestPoint, pt)
         if dist <= tolerance:
            result.append(pt)

   return result


#===============================================================================
# getPolarPointByPtAngle
#===============================================================================
def getPolarPointByPtAngle(p1, angle, dist):
   """
   la funzione ritorna il punto sulla retta passante per p1 con angolo <angle> che
   dista da p1 <dist>.
   """
   y = dist * math.sin(angle)
   x = dist * math.cos(angle)
   return QgsPointXY(p1.x() + x, p1.y() + y)


#===============================================================================
# asPointOrPolyline
#===============================================================================
def asPointOrPolyline(geom):
   """
   la funzione ritorna una lista di geometrie di punti e/o polilinee in cui viene trasformata la geometria. 
   """
   # Trasformo le geometrie in point o polyline
   result = []
   for g in geom.asGeometryCollection():
      gType = g.type()
      if g.isMultipart() == False:
         if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
            result.append(g)
            
         elif gType == QgsWkbTypes.PolygonGeometry:
            lineList = g.asPolygon() # vettore di linee    
            for line in lineList:
               _g = QgsGeometry.fromPolylineXY(line)
               result.append(_g) 
                          
      else: # multi
         if gType == QgsWkbTypes.PointGeometry:
            pointList = g.asMultiPoint() # vettore di punti
            for point in pointList:
               _g = QgsGeometry.fromPointXY(point)
               result.append(_g)
               
         elif gType == QgsWkbTypes.LineGeometry:
            lineList = g.asMultiPolyline() # vettore di linee
            for line in lineList:
               _g = QgsGeometry.fromPolylineXY(line)
               result.append(_g)   
                        
         elif gType == QgsWkbTypes.PolygonGeometry:
            polygonList = g.asMultiPolygon() # vettore di poligoni
            for polygon in polygonList:
               for line in polygon:
                  _g = QgsGeometry.fromPolylineXY(line)
                  result.append(_g)
               
   return result


#===============================================================================
# leftOfLineCoords
#===============================================================================
# usare qad_line
def leftOfLineCoords(x, y, x1, y1, x2, y2):
   """
   la funzione ritorna una numero < 0 se il punto x,y é alla sinistra della linea x1,y1 -> x2,y2
   """
   f1 = x - x1
   f2 = y2 - y1
   f3 = y - y1
   f4 = x2 - x1
   return f1*f2 - f3*f4

# usare qad_line
def leftOfLine(pt, pt1, pt2):
   return leftOfLineCoords(pt.x(), pt.y(), pt1.x(), pt1.y(), pt2.x(), pt2.y())


#===============================================================================
# get a and b for line equation (y = ax + b) 
#===============================================================================
# usare qad_line
def get_A_B_LineEquation(x1, y1, x2, y2):
   # dati 2 punti vengono calcolati a e b dell'equazione della retta passante per i due punti (y = ax + b)
   a = (y2 - y1) / (x2 - x1)
   # y = ax + b -> b = y - ax
   b = y1 - (a * x1)
   
   return a, b


#===============================================================================
# radice cubica
#===============================================================================
def cbrt(x):
   # https://stackoverflow.com/questions/28014241/how-to-find-cube-root-using-python
   if x>0:
      return x**(1.0 / 3.0)
   else:
      return -((-x)**(1.0 / 3.0))


#===============================================================================
# ptNear
#===============================================================================
def ptNear(pt1, pt2, tolerance = None):
   """
   la funzione compara 2 punti (ma permette una tolleranza)
   """
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance
   
   return getDistance(pt1, pt2) <= myTolerance


#===============================================================================
# doubleNear
#===============================================================================
def doubleNear(a, b, tolerance = None):
   """
   la funzione compara 2 float (ma permette una tolleranza)
   """
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance
   
   diff = a - b
   return diff >= -myTolerance and diff <= myTolerance


#===============================================================================
# doubleGreater
#===============================================================================
def doubleGreater(a, b, tolerance = None):
   """
   la funzione compara 2 float (ma permette una tolleranza)
   """
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance
   
   return a > b and not doubleNear(a, b, myTolerance)


#===============================================================================
# doubleGreaterOrEquals
#===============================================================================
def doubleGreaterOrEquals(a, b, tolerance = None):
   """
   la funzione compara 2 float (ma permette una tolleranza)
   """
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance
   
   return a > b or doubleNear(a, b, myTolerance)


#===============================================================================
# doubleSmaller
#===============================================================================
def doubleSmaller(a, b, tolerance = None):
   """
   la funzione compara 2 float (ma permette una tolleranza)
   """
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance
   
   return a < b and not doubleNear(a, b, myTolerance)

   
#===============================================================================
# doubleSmallerOrEquals
#===============================================================================
def doubleSmallerOrEquals(a, b, tolerance = None):
   """
   la funzione compara 2 float (ma permette una tolleranza)
   """
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance
   
   return a < b or doubleNear(a, b, myTolerance)

   
#===============================================================================
# TanDirectionNear
#===============================================================================
def TanDirectionNear(a, b, tolerance = None):
   """
   la funzione compara 2 direzioni di tangenti (ma permette una tolleranza)
   """
   if tolerance is None:
      myTolerance = QadVariables.get(QadMsg.translate("Environment variables", "TOLERANCE2COINCIDENT"))
   else:
      myTolerance = tolerance
   
   a1 = normalizeAngle(a)
   b1 = normalizeAngle(b)
   if a1 > b1:
      diff1 = a1 - b1
      diff2 = (2 * math.pi + b1) - a1
   else:
      diff1 = b1 - a1
      diff2 = (2 * math.pi + a1) - b1
      
   return diff1 <= myTolerance or diff2 <= myTolerance


#===============================================================================
# numericListAvg
#===============================================================================
def numericListAvg(dblList):
   """
   la funzione calcola la media di una lista di numeri
   """
   if (dblList is None) or len(dblList) == 0:
      return None
   sum = 0
   for num in dblList:
      sum = sum + num
      
   return sum / len(dblList)


#===============================================================================
# sqrDistToSegment
#===============================================================================
# usare qad_line fino qui
def sqrDistToSegment(point, x1, y1, x2, y2, epsilon):
   """
   la funzione ritorna una lista con 
   (<minima distanza al quadrato>
    <punto più vicino>)
   """
   minDistPoint = QgsPointXY()
   
   if x1 == x2 and y1 == y2:
      minDistPoint.setX(x1)
      minDistPoint.setY(y1)
   else:
      nx = y2 - y1
      ny = -( x2 - x1 )
   
      t = (point.x() * ny - point.y() * nx - x1 * ny + y1 * nx ) / (( x2 - x1 ) * ny - ( y2 - y1 ) * nx )
   
      if t < 0.0:
         minDistPoint.setX(x1)
         minDistPoint.setY(y1)
      elif t > 1.0:
         minDistPoint.setX(x2)
         minDistPoint.setY(y2)
      else:
         minDistPoint.setX( x1 + t *( x2 - x1 ) )
         minDistPoint.setY( y1 + t *( y2 - y1 ) )

   dist = point.sqrDist(minDistPoint)
   # prevent rounding errors if the point is directly on the segment 
   if doubleNear( dist, 0.0, epsilon ):
      minDistPoint.setX( point.x() )
      minDistPoint.setY( point.y() )
      return (0.0, minDistPoint)
  
   return (dist, minDistPoint)


#===============================================================================
# closestSegmentWithContext
#===============================================================================
def closestSegmentWithContext(point, geom, epsilon = 1.e-15):
   """
   la funzione ritorna una lista con 
   (<minima distanza al quadrato>
    <punto più vicino>
    <indice vertice successivo del segmento più vicino (nel caso la geom fosse linea o poligono)>
    <"a sinistra di" se il punto é alla sinista del segmento (< 0 -> sinistra, > 0 -> destra)
   """
   minDistPoint = QgsPointXY()
   closestSegmentIndex = 0
   sqrDist = sys.float_info.max

   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry:
         minDistPoint = geom.asPoint()
         point.sqrDist(minDistPoint)
         return (point.sqrDist(minDistPoint), minDistPoint, None, None)
      
      elif gType == QgsWkbTypes.LineGeometry:
         points = geom.asPolyline() # vettore di punti
         index = 0
         for pt in points:
            if index > 0:
               prevX = thisX
               prevY = thisY
              
            thisX = pt.x()
            thisY = pt.y()
   
            if index > 0:
               result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
               testdist = result[0]
               distPoint = result[1] 
                         
               if testdist < sqrDist:
                  closestSegmentIndex = index
                  sqrDist = testdist
                  minDistPoint = distPoint
                  
            index = index + 1
   
         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)
      
      elif gType == QgsWkbTypes.PolygonGeometry:
         lines = geom.asPolygon() # lista di linee    
         index = 0
         for line in lines:
            prevX = 0
            prevY = 0
   
            for pt in line: # lista di punti
               thisX = pt.x()
               thisY = pt.y()
   
               if prevX and prevY:
                  result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
                  testdist = result[0]
                  distPoint = result[1] 
   
                  if testdist < sqrDist:
                     closestSegmentIndex = index
                     sqrDist = testdist
                     minDistPoint = distPoint
   
               prevX = thisX
               prevY = thisY
               index = index + 1
               
         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)
      
   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         minDistPoint = getNearestPoints(point, geom.asMultiPoint())[0] # vettore di punti
         return (point.sqrDist(minDistPoint), minDistPoint, None, None)
      
      elif gType == QgsWkbTypes.LineGeometry:
         lines = geom.asMultiPolyline() # lista di linee
         pointindex = 0
         for line in lines:
            prevX = 0
            prevY = 0
           
            for pt in line: # lista di punti
               thisX = pt.x()
               thisY = pt.y()
             
               if prevX and prevY:
                  result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
                  testdist = result[0]
                  distPoint = result[1] 
   
                  if testdist < sqrDist:
                     closestSegmentIndex = pointindex
                     sqrDist = testdist
                     minDistPoint = distPoint
   
               prevX = thisX
               prevY = thisY
               pointindex = pointindex + 1
            
         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))         
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)
      
      elif gType == QgsWkbTypes.PolygonGeometry:
         polygons = geom.asMultiPolygon() # vettore di poligoni
         pointindex = 0
         for polygon in polygons:
            for line in polygon: # lista di linee
               prevX = 0
               prevY = 0
            
               for pt in line: # lista di punti
                  thisX = pt.x()
                  thisY = pt.y()
      
                  if prevX and prevY:
                     result = sqrDistToSegment(point, prevX, prevY, thisX, thisY, epsilon)
                     testdist = result[0]
                     distPoint = result[1] 
      
                     if testdist < sqrDist:
                        closestSegmentIndex = pointindex
                        sqrDist = testdist
                        minDistPoint = distPoint
      
                  prevX = thisX
                  prevY = thisY
                  pointindex = pointindex + 1
         
         leftOf = leftOfLine(point, geom.vertexAt(closestSegmentIndex - 1), geom.vertexAt(closestSegmentIndex))
         return (sqrDist, minDistPoint, closestSegmentIndex, leftOf)

   return (-1, None, None, None)


#===============================================================================
# rotatePoint
#===============================================================================
def rotatePoint(point, basePt, angle):
   """
   la funzione ruota un punto QgsPointXY secondo un punto base <basePt> e un angolo <angle> in radianti 
   """
   return getPolarPointByPtAngle(basePt, getAngleBy2Pts(basePt, point) + angle, getDistance(basePt, point))


#===============================================================================
# scalePoint
#===============================================================================
def scalePoint(point, basePt, scale):
   """
   la funzione scala un punto QgsPointXY secondo un punto base <basePt> e un fattore di scala
   """
   return getPolarPointByPtAngle(basePt, getAngleBy2Pts(basePt, point), getDistance(basePt, point) * scale)


#===============================================================================
# movePoint
#===============================================================================
def movePoint(point, offsetX, offsetY):
   """
   la funzione sposta un punto QgsPointXY secondo un offset X e uno Y
   """
   return QgsPointXY(point.x() + offsetX, point.y() + offsetY)


#===============================================================================
# mirrorPoint
#===============================================================================
def mirrorPoint(point, mirrorPt, mirrorAngle):
   """
   la funzione sposta un punto QgsPointXY secondo una linea speculare passante per un 
   un punto <mirrorPt> ed avente angolo <mirrorAngle>
   """
   pointAngle = getAngleBy2Pts(mirrorPt, point)
   dist = getDistance(mirrorPt, point)
    
   return getPolarPointByPtAngle(mirrorPt, mirrorAngle + (mirrorAngle - pointAngle), dist)


#===============================================================================
# getSubGeomAtVertex
#===============================================================================
def getSubGeomAtVertex(geom, atVertex):
   # ritorna la sotto-geometria al vertice <atVertex> e la sua posizione nella geometria (0-based)
   # la posizione é espressa con una lista (<index ogg. princ> [<index ogg. sec.>])
   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry:
         if atVertex == 0:
            return QgsGeometry(geom), [0]
         
      elif gType == QgsWkbTypes.LineGeometry:
         pts = geom.asPolyline() # lista di punti
         if atVertex > len(pts) - 1:
            return None, None
         else:
            return QgsGeometry(geom), [0]
         
      elif gType == QgsWkbTypes.PolygonGeometry:
         lines = geom.asPolygon() # lista di linee
         if len(lines) > 0:
            i = 0
            iRing = -1
            for line in lines:
               lineLen = len(line)
               if atVertex >= i and atVertex < i + lineLen: # il numero di vertice ricade in questa linea
                  if iRing == -1: # si tratta della parte più esterna
                     return QgsGeometry.fromPolylineXY(line), [0] # parte <0>, ring <0>
                  else:
                     return QgsGeometry.fromPolylineXY(line), [0, iRing] # parte <0>, ring <iRing>
               i = i + lineLen 
               iRing = iRing + 1
         return None, None
      
   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         pts = geom.asMultiPoint() # lista di punti
         if atVertex > len(pts) - 1:
            return None, None
         else:
            return QgsGeometry.fromPointXY(pts[atVertex]), [atVertex]
         
      elif gType == QgsWkbTypes.LineGeometry:
         # cerco in quale linea é il vertice <atVertex>
         i = 0
         iLine = 0
         lines = geom.asMultiPolyline() # lista di linee
         for line in lines:
            lineLen = len(line)
            if atVertex >= i and atVertex < i + lineLen:
               return QgsGeometry.fromPolylineXY(line), [iLine]
            i = i + lineLen 
            iLine = iLine + 1
         return None, None
      
      elif gType == QgsWkbTypes.PolygonGeometry:
         i = 0
         iPolygon = 0
         polygons = geom.asMultiPolygon() # lista di poligoni
         for polygon in polygons:
            iRing = -1
            for line in polygon:
               lineLen = len(line)
               if atVertex >= i and atVertex < i + lineLen: # il numero di vertice ricade in questa linea
                  if iRing == -1: # si tratta della parte più esterna
                     return QgsGeometry.fromPolylineXY(line), [iPolygon] # parte <iPolygon>
                  else:
                     return QgsGeometry.fromPolylineXY(line), [iPolygon, iRing] # parte <iPolygon>, ring <iRing>
               
               i = i + lineLen 
               iRing = iRing + 1
            iPolygon = iPolygon + 1   

   return None, None


#===============================================================================
# getSubGeomAt
#===============================================================================
def getSubGeomAt(geom, atSubGeom):
   # ritorna la sotto-geometria la cui posizione
   # é espressa con una lista (<index ogg. princ> [<index ogg. sec.>])
   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
         if atSubGeom[0] == 0:
            return QgsGeometry(geom)
      
      elif gType == QgsWkbTypes.PolygonGeometry:
         if atSubGeom[0] == 0:
            lines = geom.asPolygon() # lista di linee
            if len(atSubGeom) == 1: # si tratta della parte più esterna
               return QgsGeometry.fromPolylineXY(lines[0])
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  return QgsGeometry.fromPolylineXY(lines[iRing + 1])
      
   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         nPoint = atSubGeom[0]
         return QgsGeometry(geom.vertexAt(nPoint))
      
      elif gType == QgsWkbTypes.LineGeometry:
         nLine = atSubGeom[0]
         lines = geom.asMultiPolyline() # lista di linee
         if nLine < len(lines):
            return QgsGeometry.fromPolylineXY(lines[nLine])
      
      elif gType == QgsWkbTypes.PolygonGeometry:   
         nPolygon = atSubGeom[0]
         polygons = geom.asMultiPolygon() # lista di poligoni
         if nPolygon < len(polygons):
            lines = polygons[nPolygon]
            if len(atSubGeom) == 1: # si tratta della parte più esterna
               return QgsGeometry.fromPolylineXY(lines[0])
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  return QgsGeometry.fromPolylineXY(lines[iRing + 1])
         
   return None


#===============================================================================
# setSubGeom
#===============================================================================
def setSubGeom(geom, subGeom, atSubGeom):
   # restituisce una geometria con la sotto-geometria alla posizione <atSubGeom> 
   # sostituita da <subGeom>
   gType = geom.type()
   subGType = subGeom.type()
   ndx = 0

   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
         if atSubGeom[0] == 0:
            if subGeom.isMultipart() == False and (subGType == QgsWkbTypes.PointGeometry or subGType == QgsWkbTypes.LineGeometry):
               return QgsGeometry(SubGeom)
            
      elif gType == QgsWkbTypes.PolygonGeometry:
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.LineGeometry:
            if atSubGeom[0] == 0:
               lines = geom.asPolygon() # lista di linee
               if len(atSubGeom) == 1: # si tratta della parte più esterna
                  del lines[0]
                  lines.insert(0, SubGeom.asPolyline())
                  # per problemi di approssimazione con LL il primo punto e l'ultimo non sono uguali quindi lo forzo
                  lines[0][-1].set(lines[0][0].x(), lines[0][0].y())
                  return QgsGeometry.fromPolygonXY(lines)
               else:
                  iRing = atSubGeom[1]
                  if iRing + 1 < len(lines):
                     del lines[iRing + 1]
                     lines.insert(iRing + 1, SubGeom.asPolyline())
                     # per problemi di approssimazione con LL il primo punto e l'ultimo non sono uguali quindi lo forzo
                     lines[iRing + 1][-1].set(lines[iRing + 1][0].x(), lines[iRing + 1][0].y())
                     return QgsGeometry.fromPolygonXY(lines)
      
   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         nPoint = atSubGeom[0]
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.PointGeometry:
            result = QgsGeometry(geom)
            pt = SubGeom.asPoint()
            if result.moveVertex(pt.x, pt.y(), nPoint) == True:
               return result
      
      elif gType == QgsWkbTypes.LineGeometry:
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.LineGeometry:
            nLine = atSubGeom[0]
            lines = geom.asMultiPolyline() # lista di linee
            if nLine < len(lines) and nLine >= -len(lines):
               del lines[nLine]
               lines.insert(nLine, SubGeom.asPolyline())
               return QgsGeometry.fromMultiPolylineXY(lines)
      
      elif gType == QgsWkbTypes.PolygonGeometry:   
         if subGeom.isMultipart() == False and subGType == QgsWkbTypes.LineGeometry:
            nPolygon = atSubGeom[0]
            polygons = geom.asMultiPolygon() # lista di poligoni
            if nPolygon < len(polygons):
               lines = polygons[nPolygon]
               if len(atSubGeom) == 1: # si tratta della parte più esterna
                  del lines[0]
                  lines.insert(0, SubGeom.asPolyline())
                  # per problemi di approssimazione con LL il primo punto e l'ultimo non sono uguali quindi lo forzo
                  lines[0][-1].set(lines[0][0].x(), lines[0][0].y())
                  return QgsGeometry.fromMultiPolygonXY(polygons)
               else:
                  iRing = atSubGeom[1]
                  if iRing + 1 < len(lines):
                     del lines[iRing + 1]
                     lines.insert(iRing + 1, SubGeom.asPolyline())
                     # per problemi di approssimazione con LL il primo punto e l'ultimo non sono uguali quindi lo forzo
                     lines[iRing + 1][-1].set(lines[iRing + 1][0].x(), lines[iRing + 1][0].y())
                     return QgsGeometry.fromMultiPolygonXY(polygons)
         elif subGeom.isMultipart() == False and subGType == QgsWkbTypes.PolygonGeometry:
            nPolygon = atSubGeom[0]
            polygons = geom.asMultiPolygon() # lista di poligoni
            if nPolygon < len(polygons):
               del polygons[nPolygon]
               polygons.insert(nPolygon, SubGeom.asPolygon())
               return QgsGeometry.fromMultiPolygonXY(polygons)
         
   return None


#===============================================================================
# delSubGeom
#===============================================================================
def delSubGeom(geom, atSubGeom):
   # Cancella la sotto-geometria alla posizione <atSubGeom> dalla geometria
   gType = geom.type()
   if geom.isMultipart() == False:
      if gType == QgsWkbTypes.PointGeometry or gType == QgsWkbTypes.LineGeometry:
         return None
            
      elif gType == QgsWkbTypes.PolygonGeometry:
         if atSubGeom[0] == 0:
            lines = geom.asPolygon() # lista di linee
            if len(atSubGeom) == 1: # si tratta della parte più esterna
               del lines[0]
               return QgsGeometry() # geometria vuota perchè il poligono è stato cancellato
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  del lines[iRing + 1]
                  return QgsGeometry.fromPolygonXY(lines)
      
   else: # multi
      if gType == QgsWkbTypes.PointGeometry:
         nPoint = atSubGeom[0]
         result = QgsGeometry(geom)
         pt = SubGeom.asPoint()
         if result.deleteVertex(nPoint) == True:
            return result
      
      elif gType == QgsWkbTypes.LineGeometry:
         nLine = atSubGeom[0]
         lines = geom.asMultiPolyline() # lista di linee
         if nLine < len(lines) and nLine >= -len(lines):
            del lines[nLine]
            return QgsGeometry.fromMultiPolylineXY(lines)
      
      elif gType == QgsWkbTypes.PolygonGeometry:   
         nPolygon = atSubGeom[0]
         polygons = geom.asMultiPolygon() # lista di poligoni
         if nPolygon < len(polygons):
            lines = polygons[nPolygon]
            if len(atSubGeom) == 1: # si tratta della parte più esterna
               del polygons[nPolygon]
               return QgsGeometry.fromMultiPolygonXY(polygons)
            else:
               iRing = atSubGeom[1]
               if iRing + 1 < len(lines):
                  del lines[iRing + 1]
                  return QgsGeometry.fromMultiPolygonXY(polygons)   

   return None


#===============================================================================
# getAdjustedRubberBandVertex
#===============================================================================
def getAdjustedRubberBandVertex(vertexBefore, vertex):
   adjustedVertex = QgsPointXY(vertex)
         
   # per un baco non ancora capito in QGIS: se la linea ha solo 2 vertici e 
   # hanno la stessa x o y (linea orizzontale o verticale) 
   # la linea non viene disegnata perciò sposto un pochino la x o la y
   # del secondo vertice
   # 1.e-7 è derivato dal fatto che l'operatore == di QgsPointXY ha una tolleranza di 1E-8      
   if vertexBefore.x() == vertex.x():
      adjustedVertex.setX(vertex.x() + 1.e-7)
   if vertexBefore.y() == vertex.y():
      adjustedVertex.setY(vertex.y() + 1.e-7)
      
   return adjustedVertex


#============================================================================
# QadRawConfigParser class suppporting unicode
#============================================================================
class QadRawConfigParser(configparser.RawConfigParser):

   def __init__(self, defaults=None, dict_type=configparser._default_dict,
                 allow_no_value=False):
      configparser.RawConfigParser.__init__(self, defaults, dict_type, allow_no_value)
      
   def get(self, section, option, default = None):
      try:
         return configparser.RawConfigParser.get(self, section, option)
      except:
         return default

   def getint(self, section, option, default = None):
      try:
         return configparser.RawConfigParser.getint(self, section, option)
      except:
         return default

   def getfloat(self, section, option, default = None):
      try:
         return configparser.RawConfigParser.getfloat(self, section, option)
      except:
         return default

   def getboolean(self, section, option, default = None):
      try:
         return configparser.RawConfigParser.getboolean(self, section, option)
      except:
         return default

   def write(self, fp):
      """Fixed for Unicode output"""
      if self._defaults:
         fp.write("[%s]\n" % DEFAULTSECT)
         for (key, value) in self._defaults.items():
            fp.write("%s = %s\n" % (key, unicode(value).replace('\n', '\n\t')))
         fp.write("\n")
      for section in self._sections:
         fp.write("[%s]\n" % section)
         for (key, value) in self._sections[section].items():
            if key != "__name__":
               fp.write("%s = %s\n" % (key, unicode(value).replace('\n','\n\t')))
         fp.write("\n")
 

#===============================================================================
# Timer class for profiling
#===============================================================================
class Timer(object):
   # da usare:
   # with Timer() as t:
   #    ...
   # elasped = t.secs
   def __init__(self, verbose=False):
      self.verbose = verbose

   def __enter__(self):
      self.start = time.time()
      return self

   def __exit__(self, *args):
      self.end = time.time()
      self.secs = self.end - self.start
      self.msecs = self.secs * 1000  # millisecs
      if self.verbose:
         print ('elapsed time: %f ms' % self.msecs)
