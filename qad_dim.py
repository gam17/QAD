# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin ok

 classe per la gestione delle quote
 
                              -------------------
        begin                : 2014-02-20
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
from qgis.PyQt.QtGui  import *
from qgis.core import *
from qgis.gui import *
import qgis.utils

import os
import codecs
import math
import sys


from .qad_msg import QadMsg
from . import qad_utils
from .qad_line import getBoundingPtsOnOnInfinityLine, QadLine
from .qad_arc import QadArc
from .qad_geom_relations import *
from . import qad_stretch_fun
from . import qad_layer
from . import qad_label
from .qad_entity import *
from .qad_variables import QadVariables
from .qad_multi_geom import fromQgsGeomToQadGeom, fromQadGeomToQgsGeom


"""
La classe quotatura é composta da tre layer: testo, linea, simbolo con lo stesso sistema di coordinate.

Il layer testo deve avere tutte le caratteristiche del layer testo di QAD ed in più:
- il posizionamento dell'etichetta con modalita "Intorno al punto" con distanza = 0 
  (che vuol dire punto di inserimento in basso a sx)
- la dimensione del testo in unità mappa (la dimensione varia a seconda dello zoom).
- dimStyleFieldName = "dim_style"; nome del campo che contiene il nome dello stile di quota (opzionale)
- dimTypeFieldName = "dim_type"; nome del campo che contiene il tipo dello stile di quota (opzionale)
- l'opzione "Mostra etichette capovolte" deve essere su "sempre" nel tab "Etichette"->"Visualizzazione"
- rotFieldName = "rot"; nome del campo che contiene la rotazione del testo
- la rotazione deve essere letta dal campo indicato da rotFieldName
- idFieldName = "id"; nome del campo che contiene il codice della quota (opzionale)
- la rotazione deve essere derivata dal campo rotFieldName
- il font del carattere può essere derivata da un campo
- la dimensione del carattere può essere derivata da un campo
- il colore del testo può essere derivato da un campo (opzionale)


Il layer simbolo deve avere tutte le caratteristiche del layer simbolo di QAD ed in più:
- il simbolo freccia con rotazione 0 deve essere orizzontale con la freccia rivolta verso destra
  ed il suo punto di inserimento deve essere sulla punta della freccia
- la dimensione del simbolo in unità mappa (la dimensione varia a seconda dello zoom),
  impostare la dimensione del simbolo in modo che la larghezza della freccia sia 1 unità di mappa.
- componentFieldName = "type"; nome del campo che contiene il tipo di componente della quota (vedi QadDimComponentEnum) (opzionale)
- symbolFieldName = "block"; nome del campo che contiene il nome del simbolo (opzionale)
- idParentFieldName = "id_parent"; nome del campo che contiene il codice del testo della quota (opzionale)
- scaleFieldName = "scale"; nome del campo che contiene il fattore di scala del simbolo (opzionale)
  se usato usare lo stile "singolo simbolo" (unico che consente di impostare la scala come diametro scala)
  la scala deve essere impostata su attraverso Stile->avanzato->campo di dimensione della scala-><nome del campo scala>
  la modalità di scala deve essere impostata su attraverso Stile->avanzato->campo di dimensione della scala->diametro scala
- rotFieldName = "rot"; nome del campo che contiene la rotazione del simbolo 
  la rotazione deve essere letta dal campo indicato da rotFieldName (360-rotFieldName)

Il layer linea deve avere tutte le caratteristiche del layer linea ed in più:
- componentFieldName = "type"; nome del campo che contiene il tipo di componente della quota (vedi QadDimComponentEnum) (opzionale)
- lineTypeFieldName = "line_type"; nome del campo che contiene il tipolinea (opzionale)
- colorFieldName = "color"; nome del campo che contiene il colore 'r,g,b,alpha'; alpha é opzionale (0=trasparente, 255=opaco) (opzionale)
- idParentFieldName = "id_parent"; nome del campo che contiene il codice del testo della quota (opzionale)

"""


# ===============================================================================
# QadDimTypeEnum class.   
# ===============================================================================
class QadDimTypeEnum():
   ALIGNED    = "AL" # quota lineare allineata ai punti di origine delle linee di estensione
   ANGULAR    = "AN" # quota angolare, misura l'angolo tra i 3 punti o tra gli oggetti selezionati
   BASE_LINE  = "BL" # quota lineare, angolare o coordinata a partire dalla linea di base della quota precedente o di una quota selezionata
   DIAMETER   = "DI" # quota per il diametro di un cerchio o di un arco
   LEADER     = "LD" # crea una linea che consente di collegare un'annotazione ad una lavorazione
   LINEAR     = "LI" # quota lineare con una linea di quota orizzontale o verticale
   RADIUS     = "RA" # quota radiale, misura il raggio di un cerchio o di un arco selezionato e visualizza il testo di quota con un simbolo di raggio davanti
   ARC_LENTGH = "AR" # quota per la lunghezza di un arco


# ===============================================================================
# QadDimComponentEnum class.
# ===============================================================================
class QadDimComponentEnum():
   DIM_LINE1 = "D1" # linea di quota ("Dimension line 1")
   DIM_LINE2 = "D2" # linea di quota ("Dimension line 2")
   DIM_LINE_EXT1 = "X1" # estensione della linea di quota ("Dimension line eXtension 1")
   DIM_LINE_EXT2 = "X2" # estensione della linea di quota ("Dimension line eXtension 2")
   EXT_LINE1 = "E1" # prima linea di estensione ("Extension line 1")
   EXT_LINE2 = "E2" # seconda linea di estensione ("Extension line 2")
   LEADER_LINE = "L" # linea porta quota usata quando il testo é fuori dalla quota ("Leader")
   ARC_LEADER_LINE = "AL" # linea porta quota usata per collegare il testo di quota con l'arco da quotare (vedi "dimarc" opzione "leader")
   BLOCK1 = "B1" # primo blocco della freccia ("Block 1")
   BLOCK2 = "B2" # secondo blocco della freccia ("Block 2")
   LEADER_BLOCK = "LB" # blocco della freccia nel caso leader ("Leader Block")
   ARC_BLOCK = "AB" # simbolo dell'arco ("Arc Block")
   DIM_PT1 = "D1" # primo punto da quotare ("Dimension point 1")
   DIM_PT2 = "D2" # secondo punto da quotare ("Dimension point 2")
   TEXT_PT = "T" # punto del testo di quota ("Text")
   CENTER_MARKER_LINE = "CL" # linea che definisce il marcatore del centro di un arco o di un cerchio


# ===============================================================================
# QadDimStyleAlignmentEnum class.
# ===============================================================================
class QadDimStyleAlignmentEnum():
   HORIZONTAL      = 0 # orizzontale
   VERTICAL        = 1 # verticale
   ALIGNED         = 2 # allineata
   FORCED_ROTATION = 3 # rotazione forzata


# ===============================================================================
# QadDimStyleTxtVerticalPosEnum class.
# ===============================================================================
class QadDimStyleTxtVerticalPosEnum():
   CENTERED_LINE = 0 # testo centrato alla linea di quota
   ABOVE_LINE    = 1 # testo sopra alla linea di quota ma nel caso la linea di quota non sia orizzontale 
                     # e il testo sia dentro le linee di estensione e forzato orizzontale allora il testo diventa centrato
   EXTERN_LINE   = 2 # testo posizionato nella parte opposta ai punti di quotatura 
   BELOW_LINE    = 4 # testo sotto alla linea di quota ma nel caso la linea di quota non sia orizzontale 
                     # e il testo sia dentro le linee di estensione e forzato orizzontale allora il testo diventa centrato


# ===============================================================================
# QadDimStyleTxtHorizontalPosEnum class.
# ===============================================================================
class QadDimStyleTxtHorizontalPosEnum():
   CENTERED_LINE      = 0 # testo centrato alla linea di quota
   FIRST_EXT_LINE     = 1 # testo vicino alla prima linea di estensione
   SECOND_EXT_LINE    = 2 # testo vicino alla seconda linea di estensione
   FIRST_EXT_LINE_UP  = 3 # testo sopra e allineato alla prima linea di estensione
   SECOND_EXT_LINE_UP = 4 # testo sopra e allineato alla seconda linea di estensione


# ===============================================================================
# QadDimStyleTxtRotEnum class.
# ===============================================================================
class QadDimStyleTxtRotModeEnum():
   HORIZONTAL      = 0 # testo orizzontale
   ALIGNED_LINE    = 1 # testo allineato con la linea di quota
   ISO             = 2 # testo allineato con la linea di quota se tra le linee di estensione,
                       # altrimenti testo orizzontale
   FORCED_ROTATION = 3 # testo con rotazione forzata


# ===============================================================================
# QadDimStyleArcSymbolPosEnum class.
# ===============================================================================
class QadDimStyleArcSymbolPosEnum():
   BEFORE_TEXT = 0 # simbolo prima del testo
   ABOVE_TEXT  = 1 # simbolo sopra il testo
   NONE        = 2 # niente simbolo


# ===============================================================================
# QadDimStyleArcSymbolPosEnum class.
# ===============================================================================
class QadDimStyleTxtDirectionEnum():
   SX_TO_DX = 0 # da sinistra a destra
   DX_TO_SX = 1 # da destra a sinistra 


# ===============================================================================
# QadDimStyleTextBlocksAdjustEnum class.
# ===============================================================================
class QadDimStyleTextBlocksAdjustEnum():
   BOTH_OUTSIDE_EXT_LINES = 0 # sposta testo e frecce fuori dalle linee di estensione
   FIRST_BLOCKS_THEN_TEXT = 1 # sposta prima le frecce poi, se non basta, anche il testo
   FIRST_TEXT_THEN_BLOCKS = 2 # sposta prima il testo poi, se non basta, anche le frecce
   WHICHEVER_FITS_BEST    = 3 # Sposta indistintamente il testo o le frecce (l'oggetto che si adatta meglio)


# ===============================================================================
# QadDim dimension style class
# ===============================================================================
class QadDimStyle():
          
   def __init__(self, dimStyle = None):
      self.name = "standard" # nome dello stile
      self.description = ""
      self.path = "" # percorso e nome del file in cui è stato salvato/caricato
      self.dimType = QadDimTypeEnum.ALIGNED # tipo di quotatura
      
      # testo di quota
      self.textPrefix = "" # prefisso per il testo della quota
      self.textSuffix = "" # suffisso per il testo della quota
      self.textSuppressLeadingZeros = False # per sopprimere o meno gli zero all'inizio del testo
      self.textDecimalZerosSuppression = True # per sopprimere gli zero finali nei decimali
      self.textHeight = 1.0 # altezza testo (DIMTXT) in unità di mappa
      self.textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE # posizione verticale del testo rispetto la linea di quota (DIMTAD)
      self.textHorizontalPos = QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE # posizione orizzontale del testo rispetto la linea di quota (DIMTAD)
      self.textOffsetDist = 0.5 # distanza aggiunta intorno al testo quando per inserirlo viene spezzata la linea di quota (DIMGAP)
      self.textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE # modalità di rotazione del testo (DIMTIH e DIMTOH)
      self.textForcedRot = 0.0 # rotazione forzata del testo
      self.textDecimals = 2 # numero di decimali (DIMDEC)
      self.textDecimalSep = "." # Separatore dei decimali (DIMDSEP)
      self.textFont = "Arial" # nome del font di testo (DIMTXSTY)
      self.textColor = "255,255,255,255" # Colore per i testi della quota (DIMCLRT); bianco con opacità totale
      self.textDirection = QadDimStyleTxtDirectionEnum.SX_TO_DX # specifica la direzione del testo di quota (DIMTXTDIRECTION) 0 = da sx a dx, 1 = da dx a sx
      self.arcSymbPos = QadDimStyleArcSymbolPosEnum.BEFORE_TEXT # disegna o meno il simbolo dell'arco con DIMARC (DIMARCSYM). 
      
      # linee di quota
      self.dimLine1Show = True # Mostra o nasconde la prima linea di quota (DIMSD1)
      self.dimLine2Show = True # Mostra o nasconde la seconda linea di quota (DIMSD2)
      self.dimLineLineType = "continuous" # Tipo di linea per le linee di quota (DIMLTYPE)
      self.dimLineColor = "255,255,255,255" # Colore per le linee di quota (DIMCLRD); bianco con opacità totale
      self.dimLineSpaceOffset = 3.75 # Controlla la spaziatura delle linee di quota nelle quote da linea di base (DIMDLI)
      self.dimLineOffsetExtLine = 0.0 # distanza della linea di quota oltre la linea di estensione (DIMDLE)
   
   
      # simboli per linee di quota
      # il blocco per la freccia é una freccia verso destra con il punto di inserimento sulla punta della freccia 
      self.block1Name = "triangle2" # nome del simbolo da usare come punta della freccia sulla prima linea di quota (DIMBLK1)
      self.block2Name = "triangle2"  # nome del simbolo da usare come punta della freccia sulla seconda linea di quota (DIMBLK2)
      self.blockLeaderName = "triangle2" # nome del simbolo da usare come punta della freccia sulla linea della direttrice (DIMLDRBLK)
      self.blockWidth = 0.5 # larghezza del simbolo (in orizzontale) quando la dimensione in unità di mappa = 1 (vedi "triangle2")
      self.blockScale = 1.0 # scala della dimensione del simbolo (DIMASZ)
      self.centerMarkSize = 0.0 # disegna o meno il marcatore di centro o le linee d'asse per le quote create con
                                # DIMCENTER, DIMDIAMETER, e DIMRADIUS (DIMCEN).
                                # 0 = niente, > 0 dimensione marcatore di centro, < 0 dimensione linee d'asse
   
      # adattamento del testo e delle frecce
      self.textBlockAdjust = QadDimStyleTextBlocksAdjustEnum.WHICHEVER_FITS_BEST # (DIMATFIT)
      self.blockSuppressionForNoSpace = False # Sopprime le punte della frecce se non c'é spazio sufficiente all'interno delle linee di estensione (DIMSOXD)
      
      # linee di estensione
      self.extLine1Show = True # Mostra o nasconde la prima linea di estensione (DIMSE1)
      self.extLine2Show = True # Mostra o nasconde la seconda linea di estensione (DIMSE2)
      self.extLine1LineType = "continuous" # Tipo di linea per la prima linea di estensione (DIMLTEX1)
      self.extLine2LineType = "continuous" # Tipo di linea per la seconda linea di estensione (DIMLTEX2)
      self.extLineColor = "255,255,255,255" # Colore per le linee di estensione (DIMCLRE); bianco con opacità totale
      self.extLineOffsetDimLine = 0.0 # distanza della linea di estensione oltre la linea di quota (DIMEXE)
      self.extLineOffsetOrigPoints = 0.0 # distanza della linea di estensione dai punti da quotare (DIMEXO)
      self.extLineIsFixedLen = False # Attiva lunghezza fissa delle line di estensione (DIMFXLON)
      self.extLineFixedLen = 1.0 # lunghezza fissa delle line di estensione (DIMFXL) dalla linea di quota 
                                 # al punto da quotare spostato di extLineOffsetOrigPoints
                                 # (la linea di estensione non va oltre il punto da quotare)

      # layer e loro caratteristiche
      # devo allocare i campi a livello di classe QadDimStyle perché QgsFeature.setFields usa solo il puntatore alla lista fields
      # che, se allocata privatamente in qualsiasi funzione, all'uscita della funzione verrebbe distrutta 
      self.textualLayerName = None    # nome layer per memorizzare il testo della quota
      self.__textualLayer = None        # layer per memorizzare il testo della quota
      self.__textFields = None
      self.__textualFeaturePrototype = None
   
      self.linearLayerName = None    # nome layer per memorizzare le linee della quota
      self.__linearLayer = None        # layer per memorizzare le linee della quota
      self.__lineFields = None
      self.__linearFeaturePrototype = None
   
      self.symbolLayerName = None  # nome layer per memorizzare i blocchi delle frecce della quota
      self.__symbolLayer = None      # layer per memorizzare i blocchi delle frecce della quota
      self.__symbolFields = None
      self.__symbolFeaturePrototype = None
      
      self.componentFieldName = "type"      # nome del campo che contiene il tipo di componente della quota (vedi QadDimComponentEnum)
      self.lineTypeFieldName = "line_type"  # nome del campo che contiene il tipolinea
      self.colorFieldName = "color"         # nome del campo che contiene il colore 'r,g,b,alpha'; alpha é opzionale (0=trasparente, 255=opaco)
      self.idFieldName = "id"               # nome del campo che contiene il codice del della quota nel layer di tipo testo
      self.idParentFieldName = "id_parent"  # nome del campo che contiene il codice della quota nei layer simbolo e linea 
      self.dimStyleFieldName = "dim_style"  # nome del campo che contiene il nome dello stile di quota
      self.dimTypeFieldName = "dim_type"    # nome del campo che contiene il tipo dello stile di quota   
      self.symbolFieldName = "block"        # nome del campo che contiene il nome del simbolo
      self.scaleFieldName = "scale"         # nome del campo che contiene la dimensione
      self.rotFieldName = "rot"             # nome del campo che contiene rotazione in gradi
      
      if dimStyle is None:
         return
      self.set(dimStyle)


   # ============================================================================
   # FUNZIONI GENERICHE - INIZIO
   # ============================================================================

   def set(self, dimStyle):
      self.name = dimStyle.name
      self.description = dimStyle.description
      self.path = dimStyle.path
      self.dimType = dimStyle.dimType
      
      # testo di quota
      self.textPrefix = dimStyle.textPrefix
      self.textSuffix = dimStyle.textSuffix
      self.textSuppressLeadingZeros = dimStyle.textSuppressLeadingZeros
      self.textDecimaZerosSuppression = dimStyle.textDecimalZerosSuppression
      self.textHeight = dimStyle.textHeight
      self.textVerticalPos = dimStyle.textVerticalPos
      self.textHorizontalPos = dimStyle.textHorizontalPos
      self.textOffsetDist = dimStyle.textOffsetDist
      self.textRotMode = dimStyle.textRotMode
      self.textForcedRot = dimStyle.textForcedRot
      self.textDecimals = dimStyle.textDecimals
      self.textDecimalSep = dimStyle.textDecimalSep
      self.textFont = dimStyle.textFont
      self.textColor = dimStyle.textColor
      self.textDirection = dimStyle.textDirection
      self.arcSymbPos = dimStyle.arcSymbPos
      
      # linee di quota
      self.dimLine1Show = dimStyle.dimLine1Show
      self.dimLine2Show = dimStyle.dimLine2Show
      self.dimLineLineType = dimStyle.dimLineLineType
      self.dimLineColor = dimStyle.dimLineColor
      self.dimLineSpaceOffset = dimStyle.dimLineSpaceOffset
      self.dimLineOffsetExtLine = dimStyle.dimLineOffsetExtLine
   
      # simboli per linee di quota
      self.block1Name = dimStyle.block1Name
      self.block2Name = dimStyle.block2Name
      self.blockLeaderName = dimStyle.blockLeaderName
      self.blockWidth = dimStyle.blockWidth
      self.blockScale = dimStyle.blockScale
      self.blockSuppressionForNoSpace = dimStyle.blockSuppressionForNoSpace
      self.centerMarkSize = dimStyle.centerMarkSize
   
      # adattamento del testo e delle frecce
      self.textBlockAdjust = dimStyle.textBlockAdjust
      
      # linee di estensione
      self.extLine1Show = dimStyle.extLine1Show
      self.extLine2Show = dimStyle.extLine2Show
      self.extLine1LineType = dimStyle.extLine1LineType
      self.extLine2LineType = dimStyle.extLine2LineType
      self.extLineColor = dimStyle.extLineColor
      self.extLineOffsetDimLine = dimStyle.extLineOffsetDimLine
      self.extLineOffsetOrigPoints = dimStyle.extLineOffsetOrigPoints
      self.extLineIsFixedLen = dimStyle.extLineIsFixedLen
      self.extLineFixedLen = dimStyle.extLineFixedLen
      
      # layer e loro caratteristiche
      self.textualLayerName = dimStyle.textualLayerName
      self.__textualLayer = dimStyle.__textualLayer
      self.__textFields = dimStyle.__textFields
      self.__textualFeaturePrototype = dimStyle.__textualFeaturePrototype   
      self.linearLayerName = dimStyle.linearLayerName
      self.__linearLayer = dimStyle.__linearLayer
      self.__lineFields = dimStyle.__lineFields
      self.__linearFeaturePrototype = dimStyle.__linearFeaturePrototype   
      self.symbolLayerName = dimStyle.symbolLayerName
      self.__symbolLayer = dimStyle.__symbolLayer
      self.__symbolFields = dimStyle.__symbolFields
      self.__symbolFeaturePrototype = dimStyle.__symbolFeaturePrototype   

      self.componentFieldName = dimStyle.componentFieldName
      self.symbolFieldName = dimStyle.symbolFieldName
      self.lineTypeFieldName = dimStyle.lineTypeFieldName
      self.colorFieldName = dimStyle.colorFieldName
      self.idFieldName = dimStyle.idFieldName
      self.idParentFieldName = dimStyle.idParentFieldName
      self.dimStyleFieldName = dimStyle.dimStyleFieldName
      self.dimTypeFieldName = dimStyle.dimTypeFieldName
      self.scaleFieldName = dimStyle.scaleFieldName
      self.rotFieldName = dimStyle.rotFieldName


   # ============================================================================
   # getPropList
   # ============================================================================
   def getPropList(self):
      proplist = dict() # dizionario di nome con lista [descrizione, valore]
      propDescr = QadMsg.translate("Dimension", "Name")
      proplist["name"] = [propDescr, self.name]
      propDescr = QadMsg.translate("Dimension", "Description")
      proplist["description"] = [propDescr, self.description]
      propDescr = QadMsg.translate("Dimension", "File path")
      proplist["path"] = [propDescr, self.path]
      
      # testo di quota
      value = self.textPrefix
      if len(self.textPrefix) > 0:
         value += "<>"
      value += self.textSuffix
      propDescr = QadMsg.translate("Dimension", "Text prefix and suffix")
      proplist["textPrefix"] = [propDescr, value]
      propDescr = QadMsg.translate("Dimension", "Leading zero suppression")
      proplist["textSuppressLeadingZeros"] = [propDescr, self.textSuppressLeadingZeros]
      propDescr = QadMsg.translate("Dimension", "Trailing zero suppression")
      proplist["textDecimalZerosSuppression"] = [propDescr, self.textDecimalZerosSuppression]
      propDescr = QadMsg.translate("Dimension", "Text height")
      proplist["textHeight"] = [propDescr, self.textHeight]
      propDescr = QadMsg.translate("Dimension", "Vertical text position")
      proplist["textVerticalPos"] = [propDescr, self.textVerticalPos]
      propDescr = QadMsg.translate("Dimension", "Horizontal text position")
      proplist["textHorizontalPos"] = [propDescr, self.textHorizontalPos]
      propDescr = QadMsg.translate("Dimension", "Text offset")
      proplist["textOffsetDist"] = [propDescr, self.textOffsetDist]
      propDescr = QadMsg.translate("Dimension", "Text alignment")
      proplist["textRotMode"] = [propDescr, self.textRotMode]
      propDescr = QadMsg.translate("Dimension", "Fixed text rotation")
      proplist["textForcedRot"] = [propDescr, self.textForcedRot]
      propDescr = QadMsg.translate("Dimension", "Precision")
      proplist["textDecimals"] = [propDescr, self.textDecimals]
      propDescr = QadMsg.translate("Dimension", "Decimal separator")
      proplist["textDecimalSep"] = [propDescr, self.textDecimalSep]
      propDescr = QadMsg.translate("Dimension", "Text font")
      proplist["textFont"] = [propDescr, self.textFont]
      propDescr = QadMsg.translate("Dimension", "Text color")
      proplist["textColor"] = [propDescr, self.textColor]
      if self.textDirection == QadDimStyleTxtDirectionEnum.SX_TO_DX:
         value = QadMsg.translate("Dimension", "From left to right")
      else:
         value = QadMsg.translate("Dimension", "From right to left")
      propDescr = QadMsg.translate("Dimension", "Text direction")
      proplist["textDirection"] = [propDescr, value]
      propDescr = QadMsg.translate("Dimension", "Arc len. symbol")
      proplist["arcSymbPos"] = [propDescr, self.arcSymbPos]
      
      # linee di quota
      propDescr = QadMsg.translate("Dimension", "Dim line 1 visible")
      proplist["dimLine1Show"] = [propDescr, self.dimLine1Show]
      propDescr = QadMsg.translate("Dimension", "Dim line 2 visible")
      proplist["dimLine2Show"] = [propDescr, self.dimLine2Show]
      propDescr = QadMsg.translate("Dimension", "Dim line linetype")
      proplist["dimLineLineType"] = [propDescr, self.dimLineLineType]
      propDescr = QadMsg.translate("Dimension", "Dim line color")
      proplist["dimLineColor"] = [propDescr, self.dimLineColor]
      propDescr = QadMsg.translate("Dimension", "Offset from origin")
      proplist["dimLineSpaceOffset"] = [propDescr, self.dimLineSpaceOffset]
      propDescr = QadMsg.translate("Dimension", "Dim line extension")
      proplist["dimLineOffsetExtLine"] = [propDescr, self.dimLineOffsetExtLine]
   
      # simboli per linee di quota
      propDescr = QadMsg.translate("Dimension", "Arrow 1")
      proplist["block1Name"] = [propDescr, self.block1Name]
      propDescr = QadMsg.translate("Dimension", "Arrow 2")
      proplist["block2Name"] = [propDescr, self.block2Name]
      propDescr = QadMsg.translate("Dimension", "Leader arrow")
      proplist["blockLeaderName"] = [propDescr, self.blockLeaderName]
      propDescr = QadMsg.translate("Dimension", "Arrowhead width")
      proplist["blockWidth"] = [propDescr, self.blockWidth]
      propDescr = QadMsg.translate("Dimension", "Arrowhead scale")
      proplist["blockScale"] = [propDescr, self.blockScale]
      propDescr = QadMsg.translate("Dimension", "Center mark size")
      proplist["centerMarkSize"] = [propDescr, self.centerMarkSize]
   
      # adattamento del testo e delle frecce
      propDescr = QadMsg.translate("Dimension", "Fit: arrows and text")
      proplist["textBlockAdjust"] = [propDescr, self.textBlockAdjust]
      propDescr = QadMsg.translate("Dimension", "Suppress arrows for lack of space")
      proplist["blockSuppressionForNoSpace"] = [propDescr, self.blockSuppressionForNoSpace]
      
      # linee di estensione
      propDescr = QadMsg.translate("Dimension", "Ext. line 1 visible")
      proplist["extLine1Show"] = [propDescr, self.extLine1Show]
      propDescr = QadMsg.translate("Dimension", "Ext. line 2 visible")
      proplist["extLine2Show"] = [propDescr, self.extLine2Show]
      propDescr = QadMsg.translate("Dimension", "Ext. line 1 linetype")
      proplist["extLine1LineType"] = [propDescr, self.extLine1LineType]
      propDescr = QadMsg.translate("Dimension", "Ext. line 2 linetype")
      proplist["extLine2LineType"] = [propDescr, self.extLine2LineType]
      propDescr = QadMsg.translate("Dimension", "Ext. line color")
      proplist["extLineColor"] = [propDescr, self.extLineColor]
      propDescr = QadMsg.translate("Dimension", "Ext. line extension")
      proplist["extLineOffsetDimLine"] = [propDescr, self.extLineOffsetDimLine]
      propDescr = QadMsg.translate("Dimension", "Ext. line offset")
      proplist["extLineOffsetOrigPoints"] = [propDescr, self.extLineOffsetOrigPoints]
      propDescr = QadMsg.translate("Dimension", "Fixed length ext. line activated")
      proplist["extLineIsFixedLen"] = [propDescr, self.extLineIsFixedLen]
      propDescr = QadMsg.translate("Dimension", "Fixed length ext. line")
      proplist["extLineFixedLen"] = [propDescr, self.extLineFixedLen]
      
      # layer e loro caratteristiche
      propDescr = QadMsg.translate("Dimension", "Layer for dim texts")
      proplist["textualLayerName"] = [propDescr, self.textualLayerName]
      propDescr = QadMsg.translate("Dimension", "Layer for dim lines")
      proplist["linearLayerName"] = [propDescr, self.linearLayerName]
      propDescr = QadMsg.translate("Dimension", "Layer for dim arrows")
      proplist["symbolLayerName"] = [propDescr, self.symbolLayerName]
     
      propDescr = QadMsg.translate("Dimension", "Field for component type")
      proplist["componentFieldName"] = [propDescr, self.componentFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for linetype")
      proplist["lineTypeFieldName"] = [propDescr, self.lineTypeFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for color")
      proplist["colorFieldName"] = [propDescr, self.colorFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim ID in texts")
      proplist["idFieldName"] = [propDescr, self.idFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim ID in lines and arrows")
      proplist["idParentFieldName"] = [propDescr, self.idParentFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim style name")
      proplist["dimStyleFieldName"] = [propDescr, self.dimStyleFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for dim type")
      proplist["dimTypeFieldName"] = [propDescr, self.dimTypeFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for symbol name")
      proplist["symbolFieldName"] = [propDescr, self.symbolFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for arrows scale")
      proplist["scaleFieldName"] = [propDescr, self.scaleFieldName]
      propDescr = QadMsg.translate("Dimension", "Field for arrows rotation")
      proplist["rotFieldName"] = [propDescr, self.rotFieldName]
      
      return proplist


   # ============================================================================
   # getLayer
   # ============================================================================
   def getLayer(self, layerName):
      if layerName is not None:
         layerList = QgsProject.instance().mapLayersByName(layerName)
         if len(layerList) == 1:
            return layerList[0]
      return None


   # ============================================================================
   # layer testuale
   def getTextualLayer(self):
      if self.__textualLayer is None:
         self.__textualLayer = self.getLayer(self.textualLayerName)
      return self.__textualLayer
         
   def getTextualLayerFields(self):
      if self.__textFields is None:
         self.__textFields = None if self.getTextualLayer() is None else self.getTextualLayer().fields()
      return self.__textFields

   def getTextualFeaturePrototype(self):
      if self.__textualFeaturePrototype is None:
         if self.getTextualLayerFields() is not None:
            self.__textualFeaturePrototype = QgsFeature(self.getTextualLayerFields())                       
            self.initFeatureToDefautlValues(self.getTextualLayer(), self.__textualFeaturePrototype)
      return self.__textualFeaturePrototype


   # ============================================================================
   # layer lineare
   def getLinearLayer(self):
      if self.__linearLayer is None:
         self.__linearLayer = self.getLayer(self.linearLayerName)
      return self.__linearLayer
         
   def getLinearLayerFields(self):
      if self.__lineFields is None:
         self.__lineFields = None if self.getLinearLayer() is None else self.getLinearLayer().fields()
      return self.__lineFields

   def getLinearFeaturePrototype(self):
      if self.__linearFeaturePrototype is None:
         if self.getLinearLayerFields() is not None:
            self.__linearFeaturePrototype = QgsFeature(self.getLinearLayerFields())                       
            self.initFeatureToDefautlValues(self.getLinearLayer(), self.__linearFeaturePrototype)
      return self.__linearFeaturePrototype


   # ============================================================================
   # layer simbolo
   def getSymbolLayer(self):
      if self.__symbolLayer is None:
         self.__symbolLayer = self.getLayer(self.symbolLayerName)
      return self.__symbolLayer
         
   def getSymbolLayerFields(self):
      if self.__symbolFields is None:
         self.__symbolFields = None if self.getSymbolLayer() is None else self.getSymbolLayer().fields()
      return self.__symbolFields

   def getSymbolFeaturePrototype(self):
      if self.__symbolFeaturePrototype is None:
         if self.getSymbolLayerFields() is not None:
            self.__symbolFeaturePrototype = QgsFeature(self.getSymbolLayerFields())                       
            self.initFeatureToDefautlValues(self.getSymbolLayer(), self.__symbolFeaturePrototype)
      return self.__symbolFeaturePrototype
      
      
   # ============================================================================
   # initFeatureToDefautlValues
   # ============================================================================
   def initFeatureToDefautlValues(self, layer, f):
      # assegno i valori di default
      provider = layer.dataProvider()
      fields = f.fields()
      for field in fields.toList():
         i = fields.indexFromName(field.name())
         f[field.name()] = provider.defaultValue(i)


   # ============================================================================
   # getDefaultDimFilePath
   # ============================================================================
   def getDefaultDimFilePath(self):
      # ottiene il percorso automatico dove salvare/caricare il file della quotatura
      # se esiste un progetto caricato il percorso è quello del progetto
      prjFileInfo = QFileInfo(QgsProject.instance().fileName())
      path = prjFileInfo.absolutePath()
      if len(path) == 0:
         # se non esiste un progetto caricato uso il percorso di installazione di qad
         path = QDir.cleanPath(QgsApplication.qgisSettingsDirPath() + "python/plugins/qad")
      return path + "/"

   
   # ============================================================================
   # save
   # ============================================================================
   def save(self, path = "", overwrite = True):
      """
      Salva le impostazioni dello stile di quotatura in un file.
      """
      if path == "" and self.path != "":
         _path = self.path
      else:         
         dir, base = os.path.split(path) # ritorna percorso e nome file con estensione
         if dir == "":
            dir = self.getDefaultDimFilePath()
         else:
            dir = QDir.cleanPath(dir) + "/"
         
         name, ext = os.path.splitext(base)
         if name == "":
            name = self.name
         
         if ext == "": # se non c'è estensione la aggiungo
            ext = ".dim"
         
         _path = dir + name + ext
      
      if overwrite == False: # se non si vuole sovrascrivere
         if os.path.exists(_path):
            return False
      
      dir = QFileInfo(_path).absoluteDir() 
      if not dir.exists():
         os.makedirs(dir.absolutePath())

      config = qad_utils.QadRawConfigParser(allow_no_value=True)
      config.add_section("dimension_options")
      config.set("dimension_options", "name", str(self.name))
      config.set("dimension_options", "description", self.description)
      config.set("dimension_options", "dimType", str(self.dimType))
                           
      # testo di quota
      config.set("dimension_options", "textPrefix", str(self.textPrefix))
      config.set("dimension_options", "textSuffix", str(self.textSuffix))
      config.set("dimension_options", "textSuppressLeadingZeros", str(self.textSuppressLeadingZeros))
      config.set("dimension_options", "textDecimalZerosSuppression", str(self.textDecimalZerosSuppression))
      config.set("dimension_options", "textHeight", str(self.textHeight))
      config.set("dimension_options", "textVerticalPos", str(self.textVerticalPos))
      config.set("dimension_options", "textHorizontalPos", str(self.textHorizontalPos))
      config.set("dimension_options", "textOffsetDist", str(self.textOffsetDist))
      config.set("dimension_options", "textRotMode", str(self.textRotMode))
      config.set("dimension_options", "textForcedRot", str(self.textForcedRot))
      config.set("dimension_options", "textDecimals", str(self.textDecimals))
      config.set("dimension_options", "textDecimalSep", str(self.textDecimalSep))
      config.set("dimension_options", "textFont", str(self.textFont))
      config.set("dimension_options", "textColor", str(self.textColor))
      config.set("dimension_options", "textDirection", str(self.textDirection))
      config.set("dimension_options", "arcSymbPos", str(self.arcSymbPos))

      # linee di quota
      config.set("dimension_options", "dimLine1Show", str(self.dimLine1Show))
      config.set("dimension_options", "dimLine2Show", str(self.dimLine2Show))
      config.set("dimension_options", "dimLineLineType", str(self.dimLineLineType))
      config.set("dimension_options", "dimLineColor", str(self.dimLineColor))
      config.set("dimension_options", "dimLineSpaceOffset", str(self.dimLineSpaceOffset))
      config.set("dimension_options", "dimLineOffsetExtLine", str(self.dimLineOffsetExtLine))
          
      # simboli per linee di quota
      config.set("dimension_options", "block1Name", str(self.block1Name))
      config.set("dimension_options", "block2Name", str(self.block2Name))
      config.set("dimension_options", "blockLeaderName", str(self.blockLeaderName))
      config.set("dimension_options", "blockWidth", str(self.blockWidth))
      config.set("dimension_options", "blockScale", str(self.blockScale))
      config.set("dimension_options", "blockSuppressionForNoSpace", str(self.blockSuppressionForNoSpace))
      config.set("dimension_options", "centerMarkSize", str(self.centerMarkSize))

      # adattamento del testo e delle frecce
      config.set("dimension_options", "textBlockAdjust", str(self.textBlockAdjust))

      # linee di estensione
      config.set("dimension_options", "extLine1Show", str(self.extLine1Show))
      config.set("dimension_options", "extLine2Show", str(self.extLine2Show))
      config.set("dimension_options", "extLine1LineType", str(self.extLine1LineType))
      config.set("dimension_options", "extLine2LineType", str(self.extLine2LineType))
      config.set("dimension_options", "extLineColor", str(self.extLineColor))
      config.set("dimension_options", "extLineOffsetDimLine", str(self.extLineOffsetDimLine))
      config.set("dimension_options", "extLineOffsetOrigPoints", str(self.extLineOffsetOrigPoints))
      config.set("dimension_options", "extLineIsFixedLen", str(self.extLineIsFixedLen))
      config.set("dimension_options", "extLineFixedLen", str(self.extLineFixedLen))

      # layer e loro caratteristiche
      config.set("dimension_options", "textualLayerName", "" if self.textualLayerName is None else self.textualLayerName)
      config.set("dimension_options", "linearLayerName", "" if self.linearLayerName is None else self.linearLayerName)
      config.set("dimension_options", "symbolLayerName", "" if self.symbolLayerName is None else self.symbolLayerName)
      config.set("dimension_options", "componentFieldName", str(self.componentFieldName))
      config.set("dimension_options", "symbolFieldName", str(self.symbolFieldName))
      config.set("dimension_options", "lineTypeFieldName", str(self.lineTypeFieldName))
      config.set("dimension_options", "colorFieldName", str(self.colorFieldName))
      config.set("dimension_options", "idFieldName", str(self.idFieldName))
      config.set("dimension_options", "idParentFieldName", str(self.idParentFieldName))
      config.set("dimension_options", "dimStyleFieldName", str(self.dimStyleFieldName))
      config.set("dimension_options", "dimTypeFieldName", str(self.dimTypeFieldName))
      config.set("dimension_options", "scaleFieldName", str(self.scaleFieldName))
      config.set("dimension_options", "rotFieldName", str(self.rotFieldName))

      with codecs.open(_path, 'w', 'utf-8') as configFile: 
          config.write(configFile)
          
      self.path = _path
      
      return True

   
   # ============================================================================
   # load
   # ============================================================================
   def load(self, path):
      """
      Carica le impostazioni dello stile di quotatura da un file.
      """
      if path is None or path == "":
         return False
            
      if os.path.dirname(path) == "": # path contiene solo il nome del file (senza dir)
         _path = self.getDefaultDimFilePath()
         _path = _path + path
      else:
         _path = path
         
      if not os.path.exists(_path):
         return False

      config = qad_utils.QadRawConfigParser(allow_no_value=True)
      file = codecs.open(_path, "r", "utf-8")
      config.read_file(file)
      file.close()
      #config.read(_path)

      value = config.get("dimension_options", "name")
      if value is not None:
         self.name = value
      value = config.get("dimension_options", "description")
      if value is not None:
         self.description = value
      value = config.get("dimension_options", "dimType")
      if value is not None:
         self.dimType = value
                           
      # testo di quota
      value = config.get("dimension_options", "textPrefix")
      if value is not None:
         self.textPrefix = value
      value = config.get("dimension_options", "textSuffix")
      if value is not None:
         self.textSuffix = value
      value = config.getboolean("dimension_options", "textSuppressLeadingZeros")
      if value is not None:
         self.textSuppressLeadingZeros = value
      value = config.getboolean("dimension_options", "textDecimalZerosSuppression")
      if value is not None:
         self.textDecimalZerosSuppression = value
      value = config.getfloat("dimension_options", "textHeight")
      if value is not None:
         self.textHeight = value
      value = config.getint("dimension_options", "textVerticalPos")
      if value is not None:
         self.textVerticalPos = value
      value = config.getint("dimension_options", "textHorizontalPos")
      if value is not None:
         self.textHorizontalPos = value
      value = config.getfloat("dimension_options", "textOffsetDist")
      if value is not None:
         self.textOffsetDist = value
      value = config.getint("dimension_options", "textRotMode")
      if value is not None:
         self.textRotMode = value
      value = config.getfloat("dimension_options", "textForcedRot")
      if value is not None:
         self.textForcedRot = value
      value = config.getint("dimension_options", "textDecimals")
      if value is not None:
         self.textDecimals = value
      value = config.get("dimension_options", "textDecimalSep")
      if value is not None:
         self.textDecimalSep = value
      value = config.get("dimension_options", "textFont")
      if value is not None:
         self.textFont = value
      value = config.get("dimension_options", "textColor")
      if value is not None:
         self.textColor = value
      value = config.getint("dimension_options", "textDirection")
      if value is not None:
         self.textDirection = value
      value = config.getint("dimension_options", "arcSymbPos")
      if value is not None:
         self.arcSymbPos = value

      # linee di quota
      value = config.getboolean("dimension_options", "dimLine1Show")
      if value is not None:
         self.dimLine1Show = value
      value = config.getboolean("dimension_options", "dimLine2Show")
      if value is not None:
         self.dimLine2Show = value
      value = config.get("dimension_options", "dimLineLineType")
      if value is not None:
         self.dimLineLineType = value
      value = config.get("dimension_options", "dimLineColor")
      if value is not None:
         self.dimLineColor = value
      value = config.getfloat("dimension_options", "dimLineSpaceOffset")
      if value is not None:
         self.dimLineSpaceOffset = value
      value = config.getfloat("dimension_options", "dimLineOffsetExtLine")
      if value is not None:
         self.dimLineOffsetExtLine = value

      # simboli per linee di quota
      value = config.get("dimension_options", "block1Name")
      if value is not None:
         self.block1Name = value
      value = config.get("dimension_options", "block2Name")
      if value is not None:
         self.block2Name = value
      value = config.get("dimension_options", "blockLeaderName")
      if value is not None:
         self.blockLeaderName = value
      value = config.getfloat("dimension_options", "blockWidth")
      if value is not None:
         self.blockWidth = value
      value = config.getfloat("dimension_options", "blockScale")
      if value is not None:
         self.blockScale = value
      value = config.getboolean("dimension_options", "blockSuppressionForNoSpace")
      if value is not None:
         self.blockSuppressionForNoSpace = value
      value = config.getfloat("dimension_options", "centerMarkSize")
      if value is not None:
         self.centerMarkSize = value

      # adattamento del testo e delle frecce
      value = config.getint("dimension_options", "textBlockAdjust")
      if value is not None:
         self.textBlockAdjust = value

      # linee di estensione
      value = config.getboolean("dimension_options", "extLine1Show")
      if value is not None:
         self.extLine1Show = value
      value = config.getboolean("dimension_options", "extLine2Show")
      if value is not None:
         self.extLine2Show = value
      value = config.get("dimension_options", "extLine1LineType")
      if value is not None:
         self.extLine1LineType = value
      value = config.get("dimension_options", "extLine2LineType")
      if value is not None:
         self.extLine2LineType = value
      value = config.get("dimension_options", "extLineColor")
      if value is not None:
         self.extLineColor = value
      value = config.getfloat("dimension_options", "extLineOffsetDimLine")
      if value is not None:
         self.extLineOffsetDimLine = value
      value = config.getfloat("dimension_options", "extLineOffsetOrigPoints")
      if value is not None:
         self.extLineOffsetOrigPoints = value
      value = config.getboolean("dimension_options", "extLineIsFixedLen")
      if value is not None:
         self.extLineIsFixedLen = value
      value = config.getfloat("dimension_options", "extLineFixedLen")
      if value is not None:
         self.extLineFixedLen = value

      # layer e loro caratteristiche
      value = config.get("dimension_options", "textualLayerName")
      if value is not None:
         self.textualLayerName = value
      value = config.get("dimension_options", "linearLayerName")
      if value is not None:
         self.linearLayerName = value
      value = config.get("dimension_options", "symbolLayerName")
      if value is not None:
         self.symbolLayerName = value
            
      value = config.get("dimension_options", "componentFieldName")
      if value is not None:
         self.componentFieldName = value
      value = config.get("dimension_options", "symbolFieldName")
      if value is not None:
         self.symbolFieldName = value
      value = config.get("dimension_options", "lineTypeFieldName")
      if value is not None:
         self.lineTypeFieldName = value
      value = config.get("dimension_options", "colorFieldName")
      if value is not None:
         self.colorFieldName = value
      value = config.get("dimension_options", "idFieldName")
      if value is not None:
         self.idFieldName = value
      value = config.get("dimension_options", "idParentFieldName")
      if value is not None:
         self.idParentFieldName = value
      value = config.get("dimension_options", "dimStyleFieldName")
      if value is not None:
         self.dimStyleFieldName = value
      value = config.get("dimension_options", "dimTypeFieldName")
      if value is not None:
         self.dimTypeFieldName = value
      value = config.get("dimension_options", "scaleFieldName")
      if value is not None:
         self.scaleFieldName = value
      value = config.get("dimension_options", "rotFieldName")
      if value is not None:
         self.rotFieldName = value
      
      self.path = _path
      
      return True


   # ============================================================================
   # remove
   # ============================================================================
   def remove(self):
      """
      Cancella il file delle impostazioni dello stile di quotatura.
      """
      currDimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      if self.name == currDimStyleName: # lo stile da cancellare è quello corrente
         return False
      
      if self.path is not None and self.path != "":
         if os.path.exists(self.path):
            try:
               os.remove(self.path)
            except:
               return False
            
      return True

   # ============================================================================
   # rename
   # ============================================================================
   def rename(self, newName):
      """
      Rinomina il nome dello stile e del file delle impostazioni dello stile di quotatura.
      """
      if newName == self.name: # nome uguale
         return True
      oldName = self.name
      
      if self.path is not None or self.path != "":
         if os.path.exists(self.path):
            try:
               dir, base = os.path.split(self.path)
               dir = QDir.cleanPath(dir) + "/"
               
               name, ext = os.path.splitext(base)
               newPath = dir + "/" + newName + ext
               
               os.rename(self.path, newPath)
               self.path = newPath
               self.name = newName
               self.save()
            except:
               return False
      else:
         self.name = newName

      currDimStyleName = QadVariables.get(QadMsg.translate("Environment variables", "DIMSTYLE"))
      if oldName == currDimStyleName: # lo stile da rinominare è quello corrente
         QadVariables.set(QadMsg.translate("Environment variables", "DIMSTYLE"), newName)

      self.name = newName
      return True


   # ============================================================================
   # getInValidErrMsg
   # ============================================================================
   def getInValidErrMsg(self):
      """
      Verifica se lo stile di quotatura é invalido e in caso affermativo ritorna il messaggio di errore.
      Se la quotatura é valida ritorna None.
      """
      prefix = QadMsg.translate("Dimension", "\nThe dimension style \"{0}\" ").format(self.name)
      
      if self.getTextualLayer() is None:
         return prefix + QadMsg.translate("Dimension", "has not the textual layer for dimension.\n")
      if qad_layer.isTextLayer(self.getTextualLayer()) == False:
         errPartial = QadMsg.translate("Dimension", "has the textual layer for dimension ({0}) which is not a textual layer.")
         errMsg = prefix + errPartial.format(self.getTextualLayer().name())
         errMsg = errMsg + QadMsg.translate("QAD", "\nA textual layer is a vector punctual layer having a label and the symbol transparency no more than 10%.\n")
         return errMsg

      if self.getSymbolLayer() is None:
         return prefix + QadMsg.translate("Dimension", "has not the symbol layer for dimension.\n")
      if qad_layer.isSymbolLayer(self.getSymbolLayer()) == False:
         errPartial = QadMsg.translate("Dimension", "has the symbol layer for dimension ({0}) which is not a symbol layer.")
         errMsg = prefix + errPartial.format(self.getSymbolLayer().name())
         errMsg = errMsg + QadMsg.translate("QAD", "\nA symbol layer is a vector punctual layer without label.\n")
         return errMsg

      if self.getLinearLayer() is None:
         return prefix + QadMsg.translate("Dimension", "has not the linear layer for dimension.\n")
      # deve essere un VectorLayer di tipo linea
      if (self.getLinearLayer().type() != QgsMapLayer.VectorLayer) or (self.getLinearLayer().geometryType() != QgsWkbTypes.LineGeometry):
         errPartial = QadMsg.translate("Dimension", "has the linear layer for dimension ({0}) which is not a linear layer.")
         errMsg = prefix + errPartial.format(self.getSymbolLayer().name())
         return errMsg
      # i layer devono avere lo stesso sistema di coordinate
      if not (self.getTextualLayer().crs() == self.getLinearLayer().crs() and self.getLinearLayer().crs() == self.getSymbolLayer().crs()):
         errMsg = prefix + QadMsg.translate("Dimension", "has not the layers with the same coordinate reference system.")         
         return errMsg
         
      return None

   
   # ============================================================================
   # isValid
   # ============================================================================
   def isValid(self):
      """
      Verifica se lo stile di quotatura é valido e in caso affermativo ritorna True.
      Se la quotatura non é valida ritorna False.
      """
      return True if self.getInValidErrMsg() is None else False
   
   
   # ===============================================================================
   # getNotGraphEditableErrMsg
   # ===============================================================================
   def getNotGraphEditableErrMsg(self):
      """
      Verifica se i layer dello stile di quotatura sono in sola lettura e in caso affermativo ritorna il messaggio di errore.
      Se i layer dello stile di quotatura sono modificabili ritorna None.
      """
      prefix = QadMsg.translate("Dimension", "\nThe dimension style \"{0}\" ").format(self.name)
      
      # layer dei testi
      textualLayer = self.getTextualLayer()
      if textualLayer is None:
         errPartial = QadMsg.translate("Dimension", "hasn't the textual layer ({0}).")
         return prefix + errPartial.format(self.textualLayerName)
         
      provider = textualLayer.dataProvider()
      if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
         errPartial = QadMsg.translate("Dimension", "has the textual layer ({0}) not editable.")
         return prefix + errPartial.format(self.textualLayerName)
      if not textualLayer.isEditable():
         errPartial = QadMsg.translate("Dimension", "has the textual layer ({0}) not editable.")
         return prefix + errPartial.format(self.textualLayerName)

      # layer dei simboli
      symbolLayer = self.getSymbolLayer()
      if symbolLayer is None:
         errPartial = QadMsg.translate("Dimension", "hasn't the symbol layer ({0}).")
         return prefix + errPartial.format(self.symbolLayerName)
      
      provider = symbolLayer.dataProvider()
      if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
         errPartial = QadMsg.translate("Dimension", "has the symbol layer ({0}) not editable.")
         return prefix + errPartial.format(self.symbolLayerName)
      if not symbolLayer.isEditable():
         errPartial = QadMsg.translate("Dimension", "has the symbol layer ({0}) not editable.")
         return prefix + errPartial.format(self.symbolLayerName)
      
      # layer delle linee
      linearLayer = self.getLinearLayer()
      if linearLayer is None:
         errPartial = QadMsg.translate("Dimension", "hasn't the symbol layer ({0}).")
         return prefix + errPartial.format(self.linearLayerName)

      provider = linearLayer.dataProvider()
      if not (provider.capabilities() & QgsVectorDataProvider.EditingCapabilities):
         errPartial = QadMsg.translate("Dimension", "has the linear layer ({0}) not editable.")
         return prefix + errPartial.format(self.linearLayerName)
      if not linearLayer.isEditable():
         errPartial = QadMsg.translate("Dimension", "has the linear layer ({0}) not editable.")
         return prefix + errPartial.format(self.linearLayerName)
      
      return None
   
    
   # ============================================================================
   # adjustLineAccordingTextRect
   # ============================================================================
   def adjustLineAccordingTextRect(self, textRect, line, textLinearDimComponentOn):
      """
      Data una linea, che tipo di componente di quota rappresenta (textLinearDimComponentOn)
      e un rettangolo che rappresenta l'occupazione del testo di quota (sottoforma di una QadPolyline),
      la funzione restituisce 2 linee (possono essere None) in modo che il testo non si sovrapponga alla linea e che le 
      impostazioni di quota siano rispettate (dimLine1Show, dimLine2Show, extLine1Show, extLine2Show)
      """   
      line1 = None
      line2 = None
      # Restituisce i punti di intersezione tra il rettangolo <textRect> (QadPolyline) che rappresenta il testo
      # e un segmento <line>. La lista é ordinata per distanza dal punto iniziale di line.
      intPts = QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(textRect, line, True)[0] # orderByStartPtOfLinearObject = True
      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # linea di quota ("Dimension line")
         if len(intPts) == 2: # il rettangolo é sulla linea
            if self.dimLine1Show:
               line1 = QadLine().set(line.getStartPt(), intPts[0])
            if self.dimLine2Show:
               line2 = QadLine().set(intPts[1], line.getEndPt())
         else: # il rettangolo non é sulla linea            
            if self.dimLine1Show and self.dimLine2Show:
               line1 = line.copy()
            else:
               space1, space2 = self.getSpaceForBlock1AndBlock2OnLine(textRect, line)
               rot = qad_utils.getAngleBy2Pts(line.getStartPt(), line.getEndPt()) # angolo della linea di quota
               intPt1 = qad_utils.getPolarPointByPtAngle(line.getStartPt(), rot, space1)   
               intPt2 = qad_utils.getPolarPointByPtAngle(line.getEndPt(), rot - math.pi, space2)

               if self.dimLine1Show:
                  line1 = QadLine().set(line.getStartPt(), intPt2)
               elif self.dimLine2Show:
                  line2 = QadLine().set(line.getEndPt(), intPt1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # prima linea di estensione ("Extension line 1")
         if self.extLine1Show:
            if len(intPts) > 0:
               line1 = QadLine().set(line.getStartPt(), intPts[0])
            else:
               line1 = line.copy()
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # seconda linea di estensione ("Extension line 2")
         if self.extLine2Show:
            if len(intPts) > 0:
               line1 = QadLine().set(line.getStartPt(), intPts[0])
            else:
               line1 = line.copy()
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # linea porta quota usata quando il testo é fuori dalla quota ("Leader")
         if len(intPts) > 0:
            line1 = QadLine().set(line.getEndPt(), intPts[0])
         else:
            line1 = line.copy()

      return line1, line2
   
    
   # ============================================================================
   # adjustArcAccordingTextRect
   # ============================================================================
   def adjustArcAccordingTextRect(self, textRect, arc, textLinearDimComponentOn):
      """
      Data un arco (<arc>), che tipo di componente di quota rappresenta (textLinearDimComponentOn)
      e un rettangolo che rappresenta l'occupazione del testo di quota, la funzione restituisce
      due archi (possono essere None) in modo che il testo non si sovrapponga all'arco e che le 
      impostazioni di quota siano rispettate (dimLine1Show, dimLine2Show, extLine1Show, extLine2Show)
      """
      intPts =  QadIntersections.getOrderedPolylineIntersectionPtsWithBasicGeom(textRect, arc, True)[0] # orderByStartPtOfPart = True
      arc1 = None
      arc2 = None
      
      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # linea di quota ("Dimension line")
         if len(intPts) >= 2: # il rettangolo é sulla linea
            if self.dimLine1Show:
               arc1 = QadArc(arc)
               arc1.setEndAngleByPt(intPts[0])
            if self.dimLine2Show:
               arc2 = QadArc(arc)
               arc2.setStartAngleByPt(intPts[-1])# ultimo punto
         else: # il rettangolo non é sulla linea
            if self.dimLine1Show and self.dimLine2Show:
               arc1 = QadArc(arc)
            else:
               space1, space2 = self.getSpaceForBlock1AndBlock2OnArc(textRect, arc)

               if self.dimLine1Show:
                  arc1 = QadArc(arc)
                  pt, dummyTg = arc1.getPointFromStart(space1)
                  arc1.setEndAngleByPt(pt)
               elif self.dimLine2Show:
                  arc2 = QadArc(arc)
                  pt, dummyTg = arc2.getPointFromStart(arc2.length() - space2)
                  arc2.setStartAngleByPt(pt)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # prima linea di estensione ("Extension line 1")
         if self.extLine1Show:
            if len(intPts) > 0:
               arc1 = QadArc(arc)
               arc1.setEndAngleByPt(intPts[0])
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # seconda linea di estensione ("Extension line 2")
         if self.extLine2Show:
            if len(intPts) > 0:
               arc1 = QadArc(arc)
               arc1.setEndAngleByPt(intPts[0])
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # linea porta quota usata quando il testo é fuori dalla quota ("Leader")
         if len(intPts) > 0:
            arc1 = QadArc(arc)
            arc1.setEndAngleByPt(intPts[0])

      return arc1, arc2

   
   # ============================================================================
   # setDimId
   # ============================================================================
   def setDimId(self, dimId, features, parentId = False):
      """
      Setta tutte le feature passate nella lista <features> con il codice della quota.
      """
      fieldName = self.idParentFieldName if parentId else self.idFieldName
         
      if len(fieldName) == 0:
         return True

      i = 0
      tot = len(features)
      while i < tot:
         try:
            f = features[i]
            if f is not None:
               # imposto il codice della quota
               f.setAttribute(fieldName, dimId)
         except:
            return False
         i = i + 1
      return True        


   # ============================================================================
   # recodeDimIdOnFeatures
   # ============================================================================
   def recodeDimIdOnFeatures(self, oldDimId, newDimId, features, parentId = False):
      """
      Cerca tutte le feature passate nella lista <features> con il codice della 
      quota oldDimId e le ricodifica con newDimId.
      """
      fieldName = self.idParentFieldName if parentId else self.idFieldName
         
      if len(fieldName) == 0:
         return True
      
      i = 0
      tot = len(features)
      while i < tot:
         try:
            f = features[i]
            if f is not None:
               if f.attribute(fieldName) == oldDimId:
                  # imposto il codice della quota
                  f.setAttribute(fieldName, newDimId)
         except:
            return False
         i = i + 1
      return True        


   def textCommitChangesOnSave(self, plugIn):
      """
      Salva i testi delle quote per ottenere i nuovi ID 
      e richiamare updateTextReferencesOnSave tramite il segnale committedFeaturesAdded.
      """
      # salvo i testi per avere la codifica definitiva
      if self.getTextualLayer() is not None:
         # segno che questo layer è salvato da QAD
         plugIn.layerStatusList.setStatus(self.getTextualLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         res = self.getTextualLayer().commitChanges()
         if res == False:
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getTextualLayer().id())
         return res
      else:
         return False


   # ============================================================================
   # updateTextReferencesOnSave
   # ============================================================================
   def updateTextReferencesOnSave(self, plugIn, textAddedEntitySet):
      """
      Aggiorna e salva i reference delle entità dello stile di quotatura contenuti in textAddedEntitySet.
      """
      if textAddedEntitySet.isEmpty() == True:
         return True
      if self.startEditing() == False:
         return False     
      
      plugIn.beginEditCommand("Dimension recoded", [self.getSymbolLayer(), self.getLinearLayer(), self.getTextualLayer()])
      
      entity = QadEntity()
      entityIterator = textAddedEntitySet.getEntities()
      
      for entity in entityIterator:
         oldDimId = entity.getAttribute(self.idFieldName)
         newDimId = entity.getFeature().id()
         if oldDimId is None or self.recodeDimId(plugIn, oldDimId, newDimId) == False:
            return False

      plugIn.endEditCommand()
     
      return True


   # ============================================================================
   # startEditing
   # ============================================================================
   def startEditing(self):
      if self.getTextualLayer() is not None and self.getTextualLayer().isEditable() == False:
         if self.getTextualLayer().startEditing() == False:
            return False     
      if self.getLinearLayer() is not None and self.getLinearLayer().isEditable() == False:
         if self.getLinearLayer().startEditing() == False:
            return False         
      if self.getSymbolLayer() is not None and self.getSymbolLayer().isEditable() == False:
         if self.getSymbolLayer().startEditing() == False:
            return False         


   # ============================================================================
   # commitChanges
   # ============================================================================
   def commitChanges(self, plugIn):
      if self.startEditing() == False:
         return False     
      
      excludedLayer = plugIn.beforeCommitChangesDimLayer
      
      if (excludedLayer is None) or excludedLayer.id() != self.getTextualLayer().id():
         # segno che questo layer è salvato da QAD
         plugIn.layerStatusList.setStatus(self.getTextualLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         # salvo le entità testuali
         if self.getTextualLayer().commitChanges(False) == False: # By setting stopEditing to false, the layer will stay in editing mode.
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getTextualLayer().id())
         
      if (excludedLayer is None) or excludedLayer.id() != self.getLinearLayer().id():
         # segno che questo layer è salvato da QAD
         plugIn.layerStatusList.setStatus(self.getLinearLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         # salvo le entità lineari
         if self.getLinearLayer().commitChanges(False) == False: # By setting stopEditing to false, the layer will stay in editing mode.
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getLinearLayer().id())
         
      if (excludedLayer is None) or excludedLayer.id() != self.getSymbolLayer().id():
         # segno che questo layer è salvato da QAD
         plugIn.layerStatusList.setStatus(self.getSymbolLayer().id(), qad_layer.QadLayerStatusEnum.COMMIT_BY_INTERNAL)
         # salvo le entità puntuali
         if self.getSymbolLayer().commitChanges(False) == False: # By setting stopEditing to false, the layer will stay in editing mode.
            errors = self.getTextualLayer().commitErrors()
         plugIn.layerStatusList.remove(self.getSymbolLayer().id())
   

   # ============================================================================
   # recodeDimId
   # ============================================================================
   def getEntitySet(self, dimId):
      """
      Ricava un QadEntitySet con tutte le feature della quota dimId.
      """
      result = QadEntitySet()
      if len(self.idFieldName) == 0 or len(self.idParentFieldName) == 0:
         return result

      if self.isValid() == False: return result;
      
      layerEntitySet = QadLayerEntitySet()
      
      # ricerco l'entità testo
      expression = "\"" + self.idFieldName + "\"=" + str(dimId)
      featureIter = self.getTextualLayer().getFeatures(QgsFeatureRequest().setFilterExpression(expression))
      layerEntitySet.set(self.getTextualLayer())
      layerEntitySet.addFeatures(featureIter)
      result.addLayerEntitySet(layerEntitySet)

      expression = "\"" + self.idParentFieldName + "\"=" + str(dimId)   

      # ricerco le entità linea
      layerEntitySet.clear()
      featureIter = self.getLinearLayer().getFeatures(QgsFeatureRequest().setFilterExpression(expression))
      layerEntitySet.set(self.getLinearLayer())
      layerEntitySet.addFeatures(featureIter)
      result.addLayerEntitySet(layerEntitySet)

      # ricerco e setto id_parent per le entità puntuali
      layerEntitySet.clear()
      featureIter = self.getSymbolLayer().getFeatures(QgsFeatureRequest().setFilterExpression(expression))      
      layerEntitySet.set(self.getSymbolLayer())
      layerEntitySet.addFeatures(featureIter)
      result.addLayerEntitySet(layerEntitySet)

      return result
   
   
   # ============================================================================
   # recodeDimId
   # ============================================================================
   def recodeDimId(self, plugIn, oldDimId, newDimId):
      """
      Ricodifica tutte le feature della quota oldDimId con il nuovo codice newDimId.
      """
      if len(self.idFieldName) == 0 or len(self.idParentFieldName) == 0:
         return True
      
      entitySet = self.getEntitySet(oldDimId)

      # setto l'entità testo
      layerEntitySet = entitySet.findLayerEntitySet(self.getTextualLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         if self.setDimId(newDimId, features, False) == False:
            return False
         # plugIn, layer, features, refresh, check_validity
         if qad_layer.updateFeaturesToLayer(plugIn, self.getTextualLayer(), features, False, False) == False:
            return False
      
      # setto id_parent per le entità linea
      layerEntitySet = entitySet.findLayerEntitySet(self.getLinearLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         if self.setDimId(newDimId, features, True) == False:
            return False
         # plugIn, layer, features, refresh, check_validity
         if qad_layer.updateFeaturesToLayer(plugIn, self.getLinearLayer(), features, False, False) == False:
            return False
      
      # setto id_parent per le entità puntuali
      layerEntitySet = entitySet.findLayerEntitySet(self.getSymbolLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         if self.setDimId(newDimId, features, True) == False:
            return False
         # plugIn, layer, features, refresh, check_validity
         if qad_layer.updateFeaturesToLayer(plugIn, self.getSymbolLayer(), features, False, False) == False:
            return False

      return True

   
   # ============================================================================
   # addDimEntityToLayers
   # ============================================================================
   def addDimEntityToLayers(self, plugIn, dimEntity):
      """
      Aggiunge un'entità quota ai layer di pertinenza ricodificando i componenti.
      """
      if dimEntity is None:
         return False
      
      plugIn.beginEditCommand("Dimension added", [self.getSymbolLayer(), self.getLinearLayer(), self.getTextualLayer()])

      # prima di tutto inserisco il testo di quota
      # plugIn, layer, feature, coordTransform, refresh, check_validity
      if qad_layer.addFeatureToLayer(plugIn, self.getTextualLayer(), dimEntity.textualFeature, None, False, False, False) == False:
         plugIn.destroyEditCommand()
         return False
      
      dimId = dimEntity.textualFeature.id()
      
      if self.setDimId(dimId, [dimEntity.textualFeature], False) == True: # setto id
         # plugIn, layer, feature, refresh, check_validity
         if qad_layer.updateFeatureToLayer(plugIn, self.getTextualLayer(), dimEntity.textualFeature, False, False) == False:
            plugIn.destroyEditCommand()
            return False
         
      # features puntuali
      self.setDimId(dimId, dimEntity.symbolFeatures, True) # setto id_parent
      # plugIn, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getSymbolLayer(), dimEntity.symbolFeatures, None, False, False) == False:
         plugIn.destroyEditCommand()
         return False
      
      # features lineari
      self.setDimId(dimId, dimEntity.linearFeatures, True) # setto id_parent
      # plugIn, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getLinearLayer(), dimEntity.linearFeatures, None, False, False) == False:
         plugIn.destroyEditCommand()
         return False

      plugIn.endEditCommand()
      
      return True


   # ============================================================================
   # getDimIdByEntity
   # ============================================================================
   def getDimIdByEntity(self, entity):
      """
      La funzione, data un'entità, verifica se fa parte dello stile di quotatura e,
      in caso di successo, restituisce il codice della quotatura altrimenti None.
      In più, la funzione, setta il tipo di quotatura se é possibile.
      """
      if entity.layer.name() == self.textualLayerName:
         dimId = entity.getAttribute(self.idFieldName)
         if dimId is None:
            return None
         f = entity.getFeature()
      elif entity.layer.name() == self.linearLayerName or \
           entity.layer.name() == self.symbolLayerName:
         textualLayer = self.getTextualLayer()
         if textualLayer is None: return None
         
         dimId = entity.getAttribute(self.idParentFieldName)
         if dimId is None:
            return None
         # ricerco l'entità testo
         expression = "\"" + self.idFieldName + "\"=" + str(dimId)
         f = QgsFeature()
         if textualLayer.getFeatures(QgsFeatureRequest().setFilterExpression(expression)).nextFeature(f) == False:
            return None
      else:
         return None

      try:
         # leggo il nome dello stile di quotatura
         dimName = f.attribute(self.dimStyleFieldName)
         if dimName != self.name:
            return None      
      except:
         return None
      
      try:
         # leggo il tipo dello stile di quotatura
         self.dimType = f.attribute(self.dimTypeFieldName)
      except:
         pass
      
      return dimId
         

   # ============================================================================
   # isDimLayer
   # ============================================================================
   def isDimLayer(self, layer):
      """
      La funzione, dato un layer, verifica se fa parte dello stile di quotatura.
      """
      if layer.name() == self.textualLayerName or \
         layer.name() == self.linearLayerName or \
         layer.name() == self.symbolLayerName:
         return True
      else:
         return False


   # ============================================================================
   # getFilteredLayerEntitySet
   # ============================================================================
   def getFilteredLayerEntitySet(self, layerEntitySet):
      """
      La funzione, dato un QadLayerEntitySet, filtra e restituisce solo quelle appartenenti allo stile di quotatura.
      """
      result = QadLayerEntitySet()
      entity = QadEntity()
      entityIterator = layerEntitySet.getEntities()

      for entity in entityIterator:
         if self.getDimIdByEntity(entity) is not None:
            result.addEntity(entity)
      
      return result




   # ============================================================================
   # FUNZIONI PER I BLOCCHI - INIZIO
   # ============================================================================

   
   # ============================================================================
   # getBlock1Size
   # ============================================================================
   def getBlock1Size(self):
      """
      Restituisce la dimensione del blocco 1 delle frecce in unità di mappa.
      """
      return 0 if self.block1Name == "" else self.blockWidth * self.blockScale


   # ============================================================================
   # getBlock2Size
   # ============================================================================
   def getBlock2Size(self):
      """
      Restituisce la dimensione del blocco 2 delle frecce in unità di mappa.
      """
      # blockWidth = larghezza del simbolo (in orizzontale) quando la dimensione in unità di mappa = 1 (vedi "triangle2")
      # blockScale = scala della dimensione del simbolo (DIMASZ)
      return 0 if self.block2Name == "" else self.blockWidth * self.blockScale


   # ============================================================================
   # getBlocksRotOnLine
   # ============================================================================
   def getBlocksRotOnLine(self, dimLine, inside):
      """
      Restituisce una lista di 2 elementi che descrivono le rotazioni dei due blocchi:
      - il primo elemento é la rotazione del blocco 1
      - il secondo elemento é la rotazione del blocco 2
      
      dimLine = linea di quota
      inside = flag di modo, se = true le frecce sono interne altrimenti sono esterne
      """
      rot = dimLine.getTanDirectionOnPt() # angolo della linea di quota
      if inside:
         rot1 = rot + math.pi
         rot2 = rot
      else:
         rot1 = rot
         rot2 = rot + math.pi
         
      return qad_utils.normalizeAngle(rot1), qad_utils.normalizeAngle(rot2)


   # ============================================================================
   # getBlocksRotOnArc
   # ============================================================================
   def getBlocksRotOnArc(self, dimLineArc, inside):
      """
      Restituisce una lista di 2 elementi che descrivono le rotazioni dei due blocchi:
      - il primo elemento é la rotazione del blocco 1
      - il secondo elemento é la rotazione del blocco 2
      
      dimLineArc = arco rappresentante la linea di quota (QadArc)
      inside = flag di modo, se = true le frecce sono interne altrimenti sono esterne
      """
      rot1 = dimLineArc.getTanDirectionOnPt(dimLineArc.getStartPt()) # angolo della linea di quota all'inizio dell'arco
      rot2 = dimLineArc.getTanDirectionOnPt(dimLineArc.getEndPt()) # angolo della linea di quota alla fine dell'arco
      if inside:
         rot1 = rot1 + math.pi
      else:
         rot2 = rot2 + math.pi
         
      return qad_utils.normalizeAngle(rot1), qad_utils.normalizeAngle(rot2)


   # ============================================================================
   # getSpaceForBlock1AndBlock2OnLine
   # ============================================================================
   def getSpaceForBlock1AndBlock2OnLineAuxiliary(self, dimLine, rectCorner):
      # calcolo la proiezione di un vertice del rettangolo sulla linea dimLine
      perpPt = QadPerpendicularity.fromPointToInfinityLine(rectCorner, dimLine)
      # se la proiezione non é nel segmento      
      if dimLine.containsPt(perpPt) == False:
         # se la proiezione ricade oltre il punto iniziale di dimLine
         if qad_utils.getDistance(dimLine.getStartPt(), perpPt) < qad_utils.getDistance(dimLine.getEndPt(), perpPt):
            return 0, dimLine.length()        
         else: # se la proiezione ricade oltre il punto finale di dimLine
            return dimLine.length(), 0
      else:
         return qad_utils.getDistance(dimLine.getStartPt(), perpPt), qad_utils.getDistance(dimLine.getEndPt(), perpPt)
      
   def getSpaceForBlock1AndBlock2OnLine(self, txtRect, dimLine):
      """
      txtRect = rettangolo di occupazione del testo (QadPolyline) o None se non c'é il testo
      dimLine = linea di quotatura
      Restituisce lo spazio disponibile per i blocchi 1 e 2 considerando il rettangolo (QadPolyline) che rappresenta il testo
      e la linea di quota dimLine.
      """
      if txtRect is None: # se non c'é il testo (é stato spostato fuori dalla linea di quota)
         spaceForBlock1 = dimLine.length() / 2
         spaceForBlock2 = spaceForBlock1
      else:
         # calcolo la proiezione dei quattro vertici del rettangolo sulla linea dimLine
         linearObject = txtRect.getLinearObjectAt(0)
         partial1SpaceForBlock1, partial1SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         linearObject = txtRect.getLinearObjectAt(1)
         partial2SpaceForBlock1, partial2SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         spaceForBlock1 = partial1SpaceForBlock1 if partial1SpaceForBlock1 < partial2SpaceForBlock1 else partial2SpaceForBlock1
         spaceForBlock2 = partial1SpaceForBlock2 if partial1SpaceForBlock2 < partial2SpaceForBlock2 else partial2SpaceForBlock2
          
         linearObject = txtRect.getLinearObjectAt(2)
         partial3SpaceForBlock1, partial3SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         if partial3SpaceForBlock1 < spaceForBlock1:
            spaceForBlock1 = partial3SpaceForBlock1
         if partial3SpaceForBlock2 < spaceForBlock2:
            spaceForBlock2 = partial3SpaceForBlock2
         
         linearObject = txtRect.getLinearObjectAt(3)
         partial4SpaceForBlock1, partial4SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLineAuxiliary(dimLine, \
                                                                                                         linearObject.getStartPt())
         if partial4SpaceForBlock1 < spaceForBlock1:
            spaceForBlock1 = partial4SpaceForBlock1
         if partial4SpaceForBlock2 < spaceForBlock2:
            spaceForBlock2 = partial4SpaceForBlock2

      return spaceForBlock1, spaceForBlock2


   # ============================================================================
   # getSpaceForBlock1AndBlock2OnArc
   # ============================================================================
   def getSpaceForBlock1AndBlock2OnArcAuxiliary(self, dimLineArc, rectCorner):
      # calcolo la proiezione di un vertice del rettangolo sull'arco dimLineArc
      angle = qad_utils.getAngleBy2Pts(dimLineArc.center, rectCorner)
      perpPt = qad_utils.getPolarPointByPtAngle(dimLineArc.center, angle, dimLineArc.radius)
      startPt = dimLineArc.getStartPt()
      endPt = dimLineArc.getEndPt()
      # se la proiezione non é nell'arco
      if dimLineArc.containsPt(perpPt) == False:
         # se la proiezione ricade oltre il punto startPt (uso le corde)
         if qad_utils.getDistance(startPt, perpPt) < qad_utils.getDistance(endPt, perpPt):
            return 0, dimLineArc.length()
         else: # se la proiezione ricade oltre il punto endPt
            return dimLineArc.length(), 0
      else:
         arc1 = QadArc(dimLineArc)
         arc1.setEndAngleByPt(perpPt)
         arc2 = QadArc(dimLineArc)
         arc2.setStartAngleByPt(perpPt)
         return arc1.length(), arc2.length()
      
   def getSpaceForBlock1AndBlock2OnArc(self, txtRect, dimLineArc):
      """
      txtRect = rettangolo di occupazione del testo o None se non c'é il testo
      dimLineArc = arco rappresentante la linea di quotatura
      Restituisce lo spazio disponibile per i blocchi 1 e 2 considerando il rettangolo (QadPolyline) che rappresenta il testo
      e la linea di quota dimLineArc.
      """
      if txtRect is None: # se non c'é il testo (é stato spostato fuori dalla linea di quota)
         spaceForBlock1 = dimLineArc.length() / 2
         spaceForBlock2 = spaceForBlock1
      else:
         # rettangolo del testo
         p1 = txtRect.getLinearObjectAt(0).getStartPt()
         p2 = txtRect.getLinearObjectAt(1).getStartPt()
         p3 = txtRect.getLinearObjectAt(2).getStartPt()
         p4 = txtRect.getLinearObjectAt(3).getStartPt()
         rect1 = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])
         # quadrato del primo blocco
         pt = dimLineArc.getStartPt()
         lineRot = dimLineArc.getTanDirectionOnPt(pt)
         p1 = qad_utils.getPolarPointByPtAngle(pt, lineRot + math.pi / 2, self.getBlock1Size() / 2)
         p2 = qad_utils.getPolarPointByPtAngle(p1, lineRot, self.getBlock1Size())
         p3 = qad_utils.getPolarPointByPtAngle(p2, lineRot - math.pi / 2, self.getBlock1Size())
         p4 = qad_utils.getPolarPointByPtAngle(p3, lineRot, - self.getBlock1Size())
         rect2 = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])
         
         if rect1.intersects(rect2):
            spaceForBlock1 = 0
         else:
            spaceForBlock1 = dimLineArc.length() / 2
            
         # quadrato del primo blocco
         pt = dimLineArc.getEndPt()
         lineRot = dimLineArc.getTanDirectionOnPt(pt) - 2 * math.pi
         p1 = qad_utils.getPolarPointByPtAngle(pt, lineRot + math.pi / 2, self.getBlock2Size() / 2)
         p2 = qad_utils.getPolarPointByPtAngle(p1, lineRot, self.getBlock2Size())
         p3 = qad_utils.getPolarPointByPtAngle(p2, lineRot - math.pi / 2, self.getBlock2Size())
         p4 = qad_utils.getPolarPointByPtAngle(p3, lineRot - 2 * math.pi, self.getBlock2Size())
         rect2 = QgsGeometry.fromPolygonXY([[p1, p2, p3, p4, p1]])

         if rect1.intersects(rect2):
            spaceForBlock2 = 0
         else:
            spaceForBlock2 = dimLineArc.length() / 2
            
         
#          # calcolo la proiezione dei quattro vertici del rettangolo sulla linea dimLinePt1, dimLinePt2
#          linearObject = txtRect.getLinearObjectAt(0)
#          partial1SpaceForBlock1, partial1SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          linearObject = txtRect.getLinearObjectAt(1)
#          partial2SpaceForBlock1, partial2SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          spaceForBlock1 = partial1SpaceForBlock1 if partial1SpaceForBlock1 < partial2SpaceForBlock1 else partial2SpaceForBlock1
#          spaceForBlock2 = partial1SpaceForBlock2 if partial1SpaceForBlock2 < partial2SpaceForBlock2 else partial2SpaceForBlock2
#           
#          linearObject = txtRect.getLinearObjectAt(2)
#          partial3SpaceForBlock1, partial3SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          if partial3SpaceForBlock1 < spaceForBlock1:
#             spaceForBlock1 = partial3SpaceForBlock1
#          if partial3SpaceForBlock2 < spaceForBlock2:
#             spaceForBlock2 = partial3SpaceForBlock2
#          
#          linearObject = txtRect.getLinearObjectAt(3)
#          partial4SpaceForBlock1, partial4SpaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArcAuxiliary(dimLineArc, \
#                                                                                                         linearObject.getStartPt())
#          if partial4SpaceForBlock1 < spaceForBlock1:
#             spaceForBlock1 = partial4SpaceForBlock1
#          if partial4SpaceForBlock2 < spaceForBlock2:
#             spaceForBlock2 = partial4SpaceForBlock2

      return spaceForBlock1, spaceForBlock2


   # ============================================================================
   # getSymbolFeature
   # ============================================================================
   def getSymbolFeature(self, insPt, rot, isBlock1, textLinearDimComponentOn):
      """
      Restituisce la feature per il simbolo delle frecce.
      insPt = punto di inserimento
      rot = rotazione espressa in radianti
      isBlock1 = se True si tratta del blocco1 altrimenti del blocco2
      textLinearDimComponentOn = indica il componente della quota dove é situato il testo di quota (QadDimComponentEnum)
      """            
      # se non c'é il simbolo di quota
      if insPt is None or rot is None:
         return None     
      # se si tratta del simbolo 1
      if isBlock1 == True:
         # se non deve essere mostrata la linea 1 di quota (vale solo se il testo é sulla linea di quota)
         if self.dimLine1Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None
      else: # se si tratta del simbolo 2
         # se non deve essere mostrata la linea 2 di quota (vale solo se il testo é sulla linea di quota)
         if self.dimLine2Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None
      
      f = QgsFeature(self.getSymbolFeaturePrototype())
      g = fromQadGeomToQgsGeom(QadPoint().set(insPt), self.getSymbolLayer())
      f.setGeometry(g)

      # imposto la scala del blocco
      try:
         if len(self.scaleFieldName) > 0:
            f.setAttribute(self.scaleFieldName, self.blockScale)
      except:
         pass

      # imposto la rotazione
      try:
         if len(self.rotFieldName) > 0:
            f.setAttribute(self.rotFieldName, qad_utils.toDegrees(rot)) # Converte da radianti a gradi
      except:
         pass

      # imposto il colore
      try:
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)         
      except:
         pass
             
      # imposto il tipo di componente della quotatura
      if self.dimType == QadDimTypeEnum.RADIUS: # se quotatura tipo raggio
         try:
            if len(self.componentFieldName) > 0:
               f.setAttribute(self.componentFieldName, QadDimComponentEnum.LEADER_BLOCK)
         except:
            pass
         
         try:
            if len(self.symbolFieldName) > 0:
               f.setAttribute(self.symbolFieldName, self.blockLeaderName)
         except:
            pass            
      else:
         try:
            if len(self.componentFieldName) > 0:
               f.setAttribute(self.componentFieldName, QadDimComponentEnum.BLOCK1 if isBlock1 else QadDimComponentEnum.BLOCK2)
         except:
            pass            

         try:
            if len(self.symbolFieldName) > 0:
               f.setAttribute(self.symbolFieldName, self.block1Name if isBlock1 else self.block2Name)
         except:
            pass

      return f


   # ============================================================================
   # getDimPointFeature
   # ============================================================================
   def getDimPointFeature(self, insPt, isDimPt1):
      """
      Restituisce la feature per il punto di quotatura.
      insPt = punto di inserimento
      isDimPt1 = se True si tratta del punto di quotatura 1 altrimenti del punto di quotatura 2
      """
      symbolFeaturePrototype = self.getSymbolFeaturePrototype()
      if symbolFeaturePrototype is None:
         return None
      f = QgsFeature(symbolFeaturePrototype)
      g = fromQadGeomToQgsGeom(QadPoint().set(insPt), self.getSymbolLayer()) # trasformo la geometria
      f.setGeometry(g)
        
      # imposto il tipo di componente della quotatura
      try:
         f.setAttribute(self.componentFieldName, QadDimComponentEnum.DIM_PT1 if isDimPt1 else QadDimComponentEnum.DIM_PT2)
      except:
         pass

      try:
         # imposto il colore
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)         
      except:
         pass

      return f


   # ============================================================================
   # getLeaderSymbolFeature
   # ============================================================================
   def getLeaderSymbolFeature(self, insPt, rot):
      """
      Restituisce la feature per il simbolo delle frecce per la linea direttrice.
      insPt = punto di inserimento
      rot = rotazione espressa in radianti
      """            
      # se non c'é il simbolo di quota
      if insPt is None or rot is None:
         return None     
      
      f = QgsFeature(self.getSymbolFeaturePrototype())
      g = fromQadGeomToQgsGeom(QadPoint().set(insPt), self.getSymbolLayer()) # trasformo la geometria
      f.setGeometry(g)

      # imposto la scala del blocco
      try:
         if len(self.scaleFieldName) > 0:
            f.setAttribute(self.scaleFieldName, self.blockScale)
      except:
         pass

      # imposto la rotazione
      try:
         if len(self.rotFieldName) > 0:
            f.setAttribute(self.rotFieldName, qad_utils.toDegrees(rot)) # Converte da radianti a gradi
      except:
         pass

      # imposto il colore
      try:
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)         
      except:
         pass
             
      # imposto il tipo di componente della quotatura
      try:
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.LEADER_BLOCK)
      except:
         pass
         
      try:
         if len(self.symbolFieldName) > 0:
            f.setAttribute(self.symbolFieldName, self.blockLeaderName)
      except:
         pass            

      return f


   # ============================================================================
   # getArcSymbolLineFeature
   # ============================================================================
   def getArcSymbolLineFeature(self, arc):
      """
      Restituisce la feature per il simbolo dell'arco.
      arc = arco
      """
      # se non c'é l'arco
      if arc is None:
         return None
               
      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(arc, self.getLinearLayer()) # trasformo la geometria
      f.setGeometry(g)
         
      try:
         # imposto il tipo di componente della quotatura
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.ARC_BLOCK)
      except:
         pass

      try:
         # imposto il tipo di linea
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)         
      except:
         pass

      try:
         # imposto il colore
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)         
      except:
         pass

      return f


   # ============================================================================
   # FUNZIONI PER I BLOCCHI - FINE
   # FUNZIONI PER IL TESTO - INIZIO
   # ============================================================================


   # ============================================================================
   # getFormattedText
   # ============================================================================
   def getFormattedText(self, measure):
      """
      Restituisce il testo della misura della quota formattato
      """
      if type(measure) == int or type(measure) == float:
         return qad_utils.numToStringFmt(measure, self.textDecimals, self.textDecimalSep, \
                                         self.textSuppressLeadingZeros, self.textDecimalZerosSuppression, \
                                         self.textPrefix, self.textSuffix)
      elif type(measure) == unicode or type(measure) == str:
         return measure
      else:
         return ""


   # ============================================================================
   # getNumericText
   # ============================================================================
   def getNumericText(self, text):
      """
      Restituisce il valore numerico del testo della misura della quota formattato
      """
      textToConvert = text.lstrip(self.textPrefix)
      textToConvert = textToConvert.rstrip(self.textSuffix)
      textToConvert = textToConvert.replace(self.textDecimalSep, ".")

      return qad_utils.str2float(textToConvert)

   
   # ============================================================================
   # textRectToQadPolyline
   # ============================================================================
   def textRectToQadPolyline(self, ptBottomLeft, textWidth, textHeight, rot):
      """
      Restituisce il rettangolo che rappresenta il testo sotto forma di una QadPolyline.
      <2>----width----<3>
       |               |
     height          height
       |               |
      <1>----width----<4>      
      """
      pt2 = qad_utils.getPolarPointByPtAngle(ptBottomLeft, rot + (math.pi / 2), textHeight)   
      pt3 = qad_utils.getPolarPointByPtAngle(pt2, rot, textWidth)   
      pt4 = qad_utils.getPolarPointByPtAngle(ptBottomLeft, rot , textWidth)
      res = QadPolyline()
      res.fromPolyline([ptBottomLeft, pt2, pt3, pt4, ptBottomLeft])
      return res


   # ============================================================================
   # getBoundingPointsTextRectProjectedToLine
   # ============================================================================
   def getBoundingPointsTextRectProjectedToLine(self, line, textRect):
      """
      Restituisce una lista di 2 punti che sono i punti estremi della proiezione dei 4 angoli del rettangolo
      sulla linea <line>.
      """
      rectCorners = textRect.asPolyline()
      # calcolo la proiezione degli angoli del rettangolo sulla linea pt1-pt2
      perpPts = []
      
      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[0], line)
      qad_utils.appendUniquePointToList(perpPts, p)
      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[1], line)
      qad_utils.appendUniquePointToList(perpPts, p)
      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[2], line)
      qad_utils.appendUniquePointToList(perpPts, p)
      p = QadPerpendicularity.fromPointToInfinityLine(rectCorners[3], line)
      qad_utils.appendUniquePointToList(perpPts, p)
         
      return getBoundingPtsOnOnInfinityLine(perpPts)
   

   # ============================================================================
   # getTextPositionOnLine
   # ============================================================================
   def getTextPositionOnLine(self, pt1, pt2, textWidth, textHeight, horizontalPos, verticalPos, rotMode):
      """
      pt1 = primo punto della linea
      pt2 = secondo punto della linea
      textWidth = larghezza testo
      textHeight = altezza testo
      
      Restituisce il punto di inserimento e la rotazione del testo lungo la linea pt1-pt2 con le modalità:
      horizontalPos = QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE (centrato alla linea)
                      QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE (vicino al punto pt1)
                      QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE (vicino al punto pt2)
      verticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE (centrato alla linea)
                    QadDimStyleTxtVerticalPosEnum.ABOVE_LINE (sopra alla linea)
                    QadDimStyleTxtVerticalPosEnum.BELOW_LINE (sotto alla linea)
      rotMode = QadDimStyleTxtRotModeEnum.HORIZONTAL (testo orizzontale)
                QadDimStyleTxtRotModeEnum.ALIGNED_LINE (testo allineato con la linea)
                QadDimStyleTxtRotModeEnum.FORCED_ROTATION (testo con rotazione forzata)
      """
      lineRot = qad_utils.getAngleBy2Pts(pt1, pt2) # angolo della linea
      
      if (lineRot > math.pi * 3 / 2 and lineRot <= math.pi * 2) or \
          (lineRot >= 0 and lineRot <= math.pi / 2): # da sx a dx
         textInsPtCloseToPt1 = True
      else: # da dx a sx
         textInsPtCloseToPt1 = False
      
      if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # testo allineato alla linea   
         if lineRot > (math.pi / 2) and lineRot <= math.pi * 3 / 2: # se il testo é capovolto lo giro
            textRot = lineRot - math.pi
         else:
            textRot = lineRot
         
         # allineamento orizzontale
         # =========================
         if horizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE: # testo centrato alla linea
            middlePt = qad_utils.getMiddlePoint(pt1, pt2)
            if textInsPtCloseToPt1: # il punto di inserimento del testo é vicino a pt1
               insPt = qad_utils.getPolarPointByPtAngle(middlePt, lineRot - math.pi, textWidth / 2)                              
            else: # il punto di inserimento del testo é vicino a pt2
               insPt = qad_utils.getPolarPointByPtAngle(middlePt, lineRot, textWidth / 2)
               
         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE: # testo vicino a pt1
            # uso 2 volte textOffsetDist perché una volta é la distanza dal punto pt1 + un offset intorno al testo
            if textInsPtCloseToPt1: # il punto di inserimento del testo é vicino a pt1
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, self.textOffsetDist + self.textOffsetDist)
            else: # il punto di inserimento del testo é vicino a pt2
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, textWidth + self.textOffsetDist + self.textOffsetDist)

         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE: # testo vicino a pt2
            # uso 2 volte textOffsetDist perché una volta é la distanza dal punto pt1 + un offset intorno al testo
            lineLen = qad_utils.getDistance(pt1, pt2)
            if textInsPtCloseToPt1: # il punto di inserimento del testo é vicino a pt1
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, lineLen - textWidth - (self.textOffsetDist + self.textOffsetDist))
            else: # il punto di inserimento del testo é vicino a pt2
               insPt = qad_utils.getPolarPointByPtAngle(pt1, lineRot, lineLen - (self.textOffsetDist + self.textOffsetDist))         

         # allineamento verticale
         # =========================
         if verticalPos == QadDimStyleTxtVerticalPosEnum.CENTERED_LINE: # testo centrato alla linea
            if textInsPtCloseToPt1: # il punto di inserimento del testo é vicino a pt1
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot - math.pi / 2, textHeight / 2)
            else: # il punto di inserimento del testo é vicino a pt2
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot + math.pi / 2, textHeight / 2)
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # sopra alla linea
            # uso 2 volte textOffsetDist perché una volta é la distanza dalla linea + un offset intorno al testo
            if textInsPtCloseToPt1: # il punto di inserimento del testo é vicino a pt1
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot + math.pi / 2, self.textOffsetDist + self.textOffsetDist)
            else: # il punto di inserimento del testo é vicino a pt2
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot - math.pi / 2, self.textOffsetDist + self.textOffsetDist)
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # sotto alla linea
            # uso 2 volte textOffsetDist perché una volta é la distanza dalla linea + un offset intorno al testo
            if textInsPtCloseToPt1: # il punto di inserimento del testo é vicino a pt1
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot - math.pi / 2, textHeight + (self.textOffsetDist + self.textOffsetDist))
            else: # il punto di inserimento del testo é vicino a pt2
               insPt = qad_utils.getPolarPointByPtAngle(insPt, lineRot + math.pi / 2, textHeight + (self.textOffsetDist + self.textOffsetDist))
      
      # testo orizzontale o testo con rotazione forzata
      elif rotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL or rotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
         
         lineLen = qad_utils.getDistance(pt1, pt2) # lunghezza della linea
         textRot = 0.0 if rotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL else self.textForcedRot
         
         # cerco qual'é l'angolo del rettangolo più vicino alla linea
         #  <2>----width----<3>
         #   |               |
         # height          height
         #   |               |
         #  <1>----width----<4>
         # ricavo il rettangolo che racchiude il testo e lo posiziono con il suo angolo in basso a sinistra sul punto pt1
         textRect = self.textRectToQadPolyline(pt1, textWidth, textHeight, textRot)
         # ottengo i punti estremi della proiezione del rettangolo sulla linea
         pts = self.getBoundingPointsTextRectProjectedToLine(QadLine().set(pt1, pt2), textRect)
         projectedTextWidth = qad_utils.getDistance(pts[0], pts[1])

         # allineamento orizzontale
         # =========================
         if horizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE: # testo centrato alla linea
            closestPtToPt1 = qad_utils.getPolarPointByPtAngle(pt1, lineRot, (lineLen - projectedTextWidth) / 2)
            
         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE: # testo vicino a pt1
            closestPtToPt1 = qad_utils.getPolarPointByPtAngle(pt1, lineRot, self.textOffsetDist)
                           
         elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE: # testo vicino a pt2
            closestPtToPt1 = qad_utils.getPolarPointByPtAngle(pt1, lineRot, lineLen - self.textOffsetDist - projectedTextWidth)
         
         # se la linea ha una angolo tra (0-90] gradi (primo quadrante)
         if lineRot > 0 and lineRot <= math.pi / 2:
            # il punto più vicino a pt1 corrisponde all'angolo in basso a sinistra del rettangolo che racchiude il testo
            # mi ricavo il punto di inserimento del testo (angolo in basso a sinistra)            
            insPt = QgsPointXY(closestPtToPt1)
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()
            
            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # sopra alla linea
               # l'angolo 4 deve essere sopra la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[3]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # sotto alla linea
               # l'angolo 2 deve essere sotto la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[1]
           
         # se la linea ha una angolo tra (90-180] gradi (secondo quadrante)
         elif lineRot > math.pi / 2 and lineRot <= math.pi:
            # il punto più vicino a pt1 corrisponde all'angolo in basso a destra del rettangolo che racchiude il testo
            # mi ricavo il punto di inserimento del testo (angolo in basso a sinistra)            
            insPt = QgsPointXY(closestPtToPt1.x() - textWidth, closestPtToPt1.y())
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()
            
            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # sopra alla linea
               # l'angolo 1 deve essere sopra la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[0]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # sotto alla linea
               # l'angolo 3 deve essere sotto la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[2]
               
         # se la linea ha una angolo tra (180-270] gradi (terzo quadrante)
         elif lineRot > math.pi and lineRot <= math.pi * 3 / 2:
            # il punto più vicino a pt1 corrisponde all'angolo in alto a destra del rettangolo che racchiude il testo
            # mi ricavo il punto di inserimento del testo (angolo in basso a sinistra)            
            insPt = QgsPointXY(closestPtToPt1.x() - textWidth, closestPtToPt1.y() - textHeight)
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()

            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # sopra alla linea
               # l'angolo 4 deve essere sopra la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[3]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # sotto alla linea
               # l'angolo 2 deve essere sotto la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[1]
               
         # se la linea ha una angolo tra (270-360] gradi (quarto quadrante)
         elif (lineRot > math.pi * 3 / 2 and lineRot <= 360) or lineRot == 0:
            # il punto più vicino a pt1 corrisponde all'angolo in alto a destra del rettangolo che racchiude il testo
            # mi ricavo il punto di inserimento del testo (angolo in alto a sinistra)            
            insPt = QgsPointXY(closestPtToPt1.x(), closestPtToPt1.y() - textHeight)
            textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
            rectCorners = textRect.asPolyline()
            
            # allineamento verticale
            # =========================
            if verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # sopra alla linea
               # l'angolo 1 deve essere sopra la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[0]
            elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # sotto alla linea
               # l'angolo 3 deve essere sotto la linea distante self.textOffsetDist dalla stessa
               rectPt = rectCorners[2]

         # allineamento verticale
         # =========================         
         if verticalPos == QadDimStyleTxtVerticalPosEnum.CENTERED_LINE: # testo centrato alla linea
            # il centro del rettangolo deve essere sulla linea
            centerPt = qad_utils.getPolarPointByPtAngle(rectCorners[0], \
                                                        qad_utils.getAngleBy2Pts(rectCorners[0], rectCorners[2]), \
                                                        qad_utils.getDistance(rectCorners[0], rectCorners[2]) / 2)            
            perpPt = qad_utils.getPerpendicularPointOnInfinityLine(pt1, pt2, centerPt)
            offsetAngle = qad_utils.getAngleBy2Pts(centerPt, perpPt)
            offsetDist = qad_utils.getDistance(centerPt, perpPt)                                                 
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # sopra alla linea
            # l'angolo deve essere sopra la linea distante self.textOffsetDist dalla stessa
            perpPt = qad_utils.getPerpendicularPointOnInfinityLine(pt1, pt2, rectPt)
            # se la linea ha una angolo tra (90-270] gradi
            if lineRot > math.pi / 2 and lineRot <= math.pi * 3 / 2:
               offsetAngle = lineRot - math.pi / 2
            else: # se la linea ha una angolo tra (270-90] gradi
               offsetAngle = lineRot + math.pi / 2
            offsetDist = qad_utils.getDistance(rectPt, perpPt) + self.textOffsetDist
         elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # sotto alla linea
            # l'angolo deve essere sotto la linea distante self.textOffsetDist dalla stessa
            perpPt = qad_utils.getPerpendicularPointOnInfinityLine(pt1, pt2, rectPt)
            # se la linea ha una angolo tra (90-270] gradi
            if lineRot > math.pi / 2 and lineRot <= math.pi * 3 / 2:
               offsetAngle = lineRot + math.pi / 2
            else: # se la linea ha una angolo tra (270-90] gradi
               offsetAngle = lineRot - math.pi / 2
            offsetDist = qad_utils.getDistance(rectPt, perpPt) + self.textOffsetDist
             
         # traslo il rettangolo
         insPt = qad_utils.getPolarPointByPtAngle(insPt, offsetAngle, offsetDist)
         textRect = self.textRectToQadPolyline(insPt, textWidth, textHeight, textRot)
         
      return insPt, textRot
   

   # ============================================================================
   # getTextPositionOnArc
   # ============================================================================
   def getTextPositionOnArc(self, arc, textWidth, textHeight, horizontalPos, verticalPos, rotMode):
      """
      arc = oggetto QadArc
      textWidth = larghezza testo compreso l'offset (2 volte offset, davanti e dietro il testo)
      textHeight = altezza testo compreso l'offset (2 volte offset, sopra e sotto il testo)
      
      Restituisce il punto di inserimento e la rotazione del testo lungo l'arco <arc> con le modalità:
      horizontalPos = QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE (centrato alla linea)
                      QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE (vicino al punto pt1)
                      QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE (vicino al punto pt2)
      verticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE (centrato alla linea)
                    QadDimStyleTxtVerticalPosEnum.ABOVE_LINE (sopra alla linea)
                    QadDimStyleTxtVerticalPosEnum.BELOW_LINE (sotto alla linea)
      rotMode = QadDimStyleTxtRotModeEnum.HORIZONTAL (testo orizzontale)
                QadDimStyleTxtRotModeEnum.ALIGNED_LINE (testo allineato con la linea)
                QadDimStyleTxtRotModeEnum.FORCED_ROTATION (testo con rotazione forzata)
      """
      arcLength = arc.length()

      # calcolo lo sviluppo della lunghezza del testo (con gli offset) sull'arco (il testo è una linea retta)
      myArc = QadArc()
      if myArc.fromStartCenterPtsChord(arc.getStartPt(), arc.center, textWidth):
         TextWidthOnArc = myArc.length()
      else:
         TextWidthOnArc = textWidth
      # calcolo lo sviluppo della lunghezza dell'offset sull'arco (il testo è una linea retta)
      if myArc.fromStartCenterPtsChord(arc.getStartPt(), arc.center, self.textOffsetDist):
         textOffsetDistOnArc = myArc.length()
      else:
         textOffsetDistOnArc = self.textOffsetDist
      
      if rotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL: # testo orizzontale
         textRot = 0.0
      elif rotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION: # testo con rotazione forzata
         textRot = self.textForcedRot

      
      # allineamento orizzontale
      # =========================
      if horizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE: # testo centrato alla linea
         insPtCenterTxt = arc.getMiddlePt()
         lineRot = arc.getTanDirectionOnPt(insPtCenterTxt)

         if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # testo allineato alla linea
            textRot = lineRot
            if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # se il testo é capovolto lo giro
               textRot = textRot - math.pi


      elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE: # testo vicino a pt1
         # uso 2 volte textOffsetDist perché una volta é la distanza dal punto pt1 + un offset intorno al testo
         insPtCenterTxt, dummyTg = arc.getPointFromStart(textOffsetDistOnArc + textOffsetDistOnArc + TextWidthOnArc / 2)
         
         lineRot = arc.getTanDirectionOnPt(insPtCenterTxt)
         
         if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # testo allineato alla linea
            textRot = lineRot
            if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # se il testo é capovolto lo giro
               textRot = textRot - math.pi


      elif horizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE: # testo vicino a pt2
         # uso 2 volte textOffsetDist perché una volta é la distanza dal punto pt1 + un offset intorno al testo
         insPtCenterTxt, dummyTg = arc.getPointFromStart(arcLength - TextWidthOnArc / 2 - textOffsetDistOnArc - textOffsetDistOnArc)
         lineRot = arc.getTanDirectionOnPt(insPtCenterTxt)

         if rotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # testo allineato alla linea
            textRot = lineRot
            if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # se il testo é capovolto lo giro
               textRot = textRot - math.pi

      # angolo della linea che congiunge il centro dell'arco con il centro del testo
      angleOnCenterTxt = qad_utils.getAngleBy2Pts(arc.center, insPtCenterTxt)
      # normalizzo l'angolo
      textRot = qad_utils.normalizeAngle(textRot)
      if (textRot > math.pi * 3 / 2 and textRot <= math.pi * 2) or \
         (textRot >= 0 and textRot < math.pi / 2): # da sx a dx
         insPt = qad_utils.getPolarPointByPtAngle(insPtCenterTxt, textRot, -textWidth / 2)
      else:
         insPt = qad_utils.getPolarPointByPtAngle(insPtCenterTxt, textRot, textWidth / 2)


      # allineamento verticale
      # =========================
      angleOnCenterTxt = qad_utils.getAngleBy2Pts(arc.center, insPtCenterTxt)
      
      if verticalPos == QadDimStyleTxtVerticalPosEnum.CENTERED_LINE: # testo centrato alla linea
         if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # se il testo é capovolto
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # il testo va verso il punto finale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, textHeight / 2)
            else: # il testo va verso il punto iniziale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -textHeight / 2)
         else: # il testo è dritto
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # il testo va verso il punto iniziale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -textHeight / 2)
            else: # il testo va verso il punto finale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, textHeight / 2)
               
               
      elif verticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE: # sopra alla linea
         if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # se il testo é capovolto
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # il testo va verso il punto finale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -self.textOffsetDist)
            else: # il testo va verso il punto iniziale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, self.textOffsetDist)
         else: # il testo è dritto
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # il testo va verso il punto iniziale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, self.textOffsetDist)
            else: # il testo va verso il punto finale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -self.textOffsetDist)


      elif verticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE: # sotto alla linea
         if textRot > (math.pi / 2) and textRot <= math.pi * 3 / 2: # se il testo é capovolto
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # il testo va verso il punto finale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, (textHeight + self.textOffsetDist))
            else: # il testo va verso il punto iniziale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -(textHeight + self.textOffsetDist))
         else: # il testo è dritto
            if (angleOnCenterTxt > 0 and angleOnCenterTxt <= math.pi): # il testo va verso il punto iniziale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, -(textHeight + self.textOffsetDist))
            else: # il testo va verso il punto finale dell'arco
               insPt = qad_utils.getPolarPointByPtAngle(insPt, angleOnCenterTxt, (textHeight + self.textOffsetDist))


      return insPt, textRot


   # ============================================================================
   # getTextPosAndLinesOutOfDimLines
   # ============================================================================
   def getTextPosAndLinesOutOfDimLines(self, dimLinePt1, dimLinePt2, textWidth, textHeight):
      """      
      Restituisce una lista di 3 elementi nel caso il testo venga spostato fuori dalle linee 
      di estensione perché era troppo grosso:
      - il primo elemento é il punto di inserimento
      - il secondo elemento é la rotazione del testo 
      - il terzo elemento é una lista di linee da usare come porta quota
      
      La funzione lo posizione a lato della linea di estensione 2. 
      dimLinePt1 = primo punto della linea di quota (QgsPointXY)
      dimLinePt2 = secondo punto della linea di quota (QgsPointXY)
      textWidth = larghezza testo
      textHeight = altezza testo
      """
      # Ottengo le linee porta quota per il testo esterno
      lines = self.getLeaderLinesOnLine(dimLinePt1, dimLinePt2, textWidth, textHeight)
      # considero l'ultima che é quella che si riferisce al testo
      line = lines.getLinearObjectAt(-1)
      
      if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
         textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
      else:
         textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE
      
      textInsPt, textRot = self.getTextPositionOnLine(line.getStartPt(), line.getEndPt(), textWidth, textHeight, \
                                                      QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                      self.textVerticalPos, textRotMode)
      return textInsPt, textRot, lines


   # ============================================================================
   # getTextPosAndLinesOutOfDimArc
   # ============================================================================
   def getTextPosAndLinesOutOfDimArc(self, dimLineArc, textWidth, textHeight):
      """      
      Restituisce una lista di 3 elementi nel caso il testo venga spostato fuori dalle linee 
      di estensione perché era troppo grosso:
      - il primo elemento é il punto di inserimento del testo
      - il secondo elemento é la rotazione del testo 
      - il terzo elemento é una lista di linee da usare come porta quota
      
      La funzione lo posizione a lato della linea di estensione 2. 
      getTextPosAndLinesOutOfDimArc = arco rappresentante la linea di quota (QadArc)
      textWidth = larghezza testo
      textHeight = altezza testo
      """
      # Ottengo le linee porta quota per il testo esterno
      lines = self.getLeaderLinesOnArc(dimLineArc, textWidth, textHeight)
      # considero l'ultima che é quella che si riferisce al testo
      line = lines.getLinearObjectAt(-1)
      
      if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
         textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
      else:
         textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE
      
      textInsPt, textRot = self.getTextPositionOnLine(line.getStartPt(), line.getEndPt(), textWidth, textHeight, \
                                                      QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                      self.textVerticalPos, textRotMode)
      return textInsPt, textRot, lines


   # ============================================================================
   # getLinearTextAndBlocksPosition
   # ============================================================================
   def getLinearTextAndBlocksPosition(self, dimPt1, dimPt2, dimLine, textWidth, textHeight):
      """
      dimPt1 = primo punto da quotare
      dimPt2 = secondo punto da quotare
      dimLine = linea di quota (QadLine)
      textWidth  = larghezza testo
      textHeight = altezza testo
      
      Restituisce una lista di 4 elementi:
      - il primo elemento é una lista con il punto di inserimento del testo della quota e la sua rotazione
      - il secondo elemento é una lista con flag che indica il tipo della linea sulla quale é stato messo il testo; vedi QadDimComponentEnum
                            e una lista di linee "leader" nel caso il testo sia all'esterno della quota
      - il terzo elemento é la rotazione del primo blocco delle frecce; può essere None se non visibile
      - il quarto elemento é la rotazione del secondo blocco delle frecce; può essere None se non visibile   
      """      
      textInsPt                = None # punto di inserimento del testo
      textRot                  = None # rotazione del testo
      textLinearDimComponentOn = None # codice del componente lineare sul quale é posizionato il testo
      txtLeaderLines           = None # lista di linee "leader" nel caso il testo sia all'esterno della quota
      block1Rot                = None # rotazione del primo blocco delle frecce
      block2Rot                = None # rotazione del secondo blocco delle frecce
                     
      # se il testo é tra le linee di estensione della quota
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE:

         dimLineRot = qad_utils.getAngleBy2Pts(dimLine.getStartPt(), dimLine.getEndPt()) # angolo della linea di quota
         
         # cambio gli estremi della linea di quota per considerare lo spazio occupato dai blocchi
         dimLinePt1Offset = qad_utils.getPolarPointByPtAngle(dimLine.getStartPt(), dimLineRot, self.getBlock1Size())
         dimLinePt2Offset = qad_utils.getPolarPointByPtAngle(dimLine.getEndPt(), dimLineRot + math.pi, self.getBlock2Size())
    
         # testo sopra o sotto alla linea di quota nel caso la linea di quota non sia orizzontale 
         # e il testo sia dentro le linee di estensione e forzato orizzontale allora il testo diventa centrato
         if (self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE or self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE) and \
            (dimLineRot != 0 and dimLineRot != math.pi) and self.textRotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL:            
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE
         # testo posizionato nella parte opposta ai punti di quotatura
         elif self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            # angolo dal primo punto di quota al primo punto della linea di quota
            dimPtToDimLinePt_rot = qad_utils.getAngleBy2Pts(dimPt1, dimLine.getStartPt())
            if dimPtToDimLinePt_rot > 0 and \
               (dimPtToDimLinePt_rot < math.pi or qad_utils.doubleNear(dimPtToDimLinePt_rot,  math.pi)):
               textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
            else:
               textVerticalPos = QadDimStyleTxtVerticalPosEnum.BELOW_LINE
         else:
            textVerticalPos = self.textVerticalPos
         
         if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
            textInsPt, textRot = self.getTextPositionOnLine(dimLinePt1Offset, dimLinePt2Offset, textWidth, textHeight, \
                                                            self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
         else:
            textInsPt, textRot = self.getTextPositionOnLine(dimLinePt1Offset, dimLinePt2Offset, textWidth, textHeight, \
                                                            self.textHorizontalPos, textVerticalPos, self.textRotMode)
         
         rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)
                  
         # se lo spazio non é sufficiente per inserire testo e simboli all'interno delle linee di estensione,
         # uso qad_utils.doubleSmaller perché a volte i due numeri sono quasi uguali 
         if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
            qad_utils.doubleSmaller(spaceForBlock1, self.getBlock1Size() + self.textOffsetDist) or \
            qad_utils.doubleSmaller(spaceForBlock2, self.getBlock2Size() + self.textOffsetDist):
            if self.blockSuppressionForNoSpace: # sopprime i simboli se non c'é spazio sufficiente all'interno delle linee di estensione
               block1Rot = None
               block2Rot = None
               
               # considero il testo senza frecce
               if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                  textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), textWidth, textHeight, \
                                                                  self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
               else:
                  textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), textWidth, textHeight, \
                                                                  self.textHorizontalPos, textVerticalPos, self.textRotMode)
               
               rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
               spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)
               # se non c'é spazio neanche per il testo senza le frecce
               if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                  spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:           
                  # sposta testo fuori dalle linee di estensione
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                            textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
               else:
                  textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1                
            else: # non devo sopprimere i simboli
               # la prima cosa da spostare all'esterno é :
               if self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.BOTH_OUTSIDE_EXT_LINES:
                  # sposta testo e frecce fuori dalle linee di estensione
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                            textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE 
                  block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne 
               # sposta prima le frecce poi, se non basta, anche il testo
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_BLOCKS_THEN_TEXT:
                  block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne 
                  # considero il testo senza frecce
                  if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                     textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                     textWidth, textHeight, \
                                                                     self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                  else:
                     textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                     textWidth, textHeight, \
                                                                     self.textHorizontalPos, textVerticalPos, self.textRotMode)
                  
                  rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                  spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)
                  # se non c'é spazio neanche per il testo senza le frecce
                  if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                     spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:                
                     # sposta testo fuori dalle linee di estensione
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                               textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  else:
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1 
               # sposta prima il testo poi, se non basta, anche le frecce
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_TEXT_THEN_BLOCKS:
                  # sposto il testo fuori dalle linee di estensione
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                            textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE 
                  # se non ci stanno neanche le frecce
                  if dimLine.length() <= self.getBlock1Size() + self.getBlock2Size():
                     block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne 
                  else:
                     block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne
               # Sposta indistintamente il testo o le frecce (l'oggetto che si adatta meglio)
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.WHICHEVER_FITS_BEST:
                  # sposto il più ingombrante
                  if self.getBlock1Size() + self.getBlock2Size() > textWidth: # le frecce sono più ingombranti del testo
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
                     block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne
                     
                     # considero il testo senza frecce
                     if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:                     
                        textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                        textWidth, textHeight, \
                                                                        self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                     else:
                        textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                        textWidth, textHeight, \
                                                                        self.textHorizontalPos, textVerticalPos, self.textRotMode)
                     
                     rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                     spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(rect, dimLine)
                     # se non c'é spazio neanche per il testo senza le frecce
                     if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                        spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:                
                        # sposta testo fuori dalle linee di estensione
                        textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                                  textWidth, textHeight)
                        textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                     else:
                        textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1 
                  else: # il testo é più ingombrante dei simboli
                     # sposto il testo fuori dalle linee di estensione
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimLines(dimLine.getStartPt(), dimLine.getEndPt(), \
                                                                                               textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE 
                     # se non ci stanno neanche le frecce
                     if dimLine.length() <= self.getBlock1Size() + self.getBlock2Size():
                        block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False) # frecce esterne 
                     else:
                        block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne
         else: # se lo spazio é sufficiente per inserire testo e simboli all'interno delle linee di estensione,
            textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
            block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne
      
      # il testo é sopra e allineato alla prima linea di estensione         
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE_UP:
         # angolo della linea che va dal punto di quota all'inizio della linea di quota
         rotLine = qad_utils.getAngleBy2Pts(dimPt1, dimLine.getStartPt())
         pt = qad_utils.getPolarPointByPtAngle(dimLine.getStartPt(), rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos
         
         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE
            
         textInsPt, textRot = self.getTextPositionOnLine(dimLine.getStartPt(), pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE1 
         
         # calcolo lo spazio dei blocchi in assenza del testo
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(None, dimLine)
         # se non c'é spazio per i blocchi
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # sposto le frecce all'esterno
               block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False)
         else: # c'é spazio per i blocchi
            block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne
               
      # il testo é sopra e allineato alla seconda linea di estensione         
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE_UP:
         # angolo della linea che va dal punto di quota all'inizio della linea di quota
         rotLine = qad_utils.getAngleBy2Pts(dimPt2, dimLine.getEndPt())
         pt = qad_utils.getPolarPointByPtAngle(dimLine.getEndPt(), rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos
            
         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE
            
         textInsPt, textRot = self.getTextPositionOnLine(dimLine.getEndPt(), pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE2 
         
         # calcolo lo spazio dei blocchi in assenza del testo
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnLine(None, dimLine)
         # se non c'é spazio per i blocchi
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # sposto le frecce all'esterno
               block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, False)
         else: # c'é spazio per i blocchi
            block1Rot, block2Rot = self.getBlocksRotOnLine(dimLine, True) # frecce interne
      
      if self.textDirection == QadDimStyleTxtDirectionEnum.DX_TO_SX:
         # il punto di inserimento diventa l'angolo in alto a destra del rettangolo
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, textHeight)
         # la rotazione viene capovolta
         textRot = qad_utils.normalizeAngle(textRot + math.pi)
   
      return [[textInsPt, textRot], [textLinearDimComponentOn, txtLeaderLines], block1Rot, block2Rot]
            

   # ============================================================================
   # getArcTextAndBlocksPosition
   # ============================================================================
   def getArcTextAndBlocksPosition(self, dimArc, dimLineArc, textWidth, textHeight):
      """
      dimArc = arco da quotare
      dimLineArc = linea di quota in forma di arco
      textWidth  = larghezza testo
      textHeight = altezza testo
      
      Restituisce una lista di 4 elementi:
      - il primo elemento é una lista con il punto di inserimento del testo della quota e la sua rotazione
      - il secondo elemento é una lista con flag che indica il tipo della linea sulla quale é stato messo il testo; vedi QadDimComponentEnum
                            e una lista di linee "leader" nel caso il testo sia all'esterno della quota
      - il terzo elemento é la rotazione del primo blocco delle frecce; può essere None se non visibile
      - il quarto elemento é la rotazione del secondo blocco delle frecce; può essere None se non visibile   
      """      
      textInsPt                = None # punto di inserimento del testo
      textRot                  = None # rotazione del testo
      textLinearDimComponentOn = None # codice del componente lineare sul quale é posizionato il testo
      txtLeaderLines           = None # lista di linee "leader" nel caso il testo sia all'esterno della quota
      block1Rot                = None # rotazione del primo blocco delle frecce
      block2Rot                = None # rotazione del secondo blocco delle frecce

      dimLineArcPt1 = dimLineArc.getStartPt()
      dimLineArcPt2 = dimLineArc.getEndPt()
      dimLineArcLen = dimLineArc.length()
      # se il testo é tra le linee di estensione della quota
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.CENTERED_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE or \
         self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE:
         
         dimLineArcMiddlePt = dimLineArc.getMiddlePt()
         dimLineRot = dimLineArc.getTanDirectionOnPt(dimLineArcMiddlePt) # angolo nel punto medio dell'arco
         
         dimLineArcPt1Offset, dummyTg = dimLineArc.getPointFromStart(self.getBlock1Size())
         dimLineArcPt2Offset, dummyTg = dimLineArc.getPointFromStart(dimLineArcLen - self.getBlock2Size())
            
         # testo sopra o sotto alla linea di quota nel caso la linea di quota non sia orizzontale 
         # e il testo sia dentro le linee di estensione e forzato orizzontale allora il testo diventa centrato
         if (self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.ABOVE_LINE or self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.BELOW_LINE) and \
            (dimLineRot != 0 and dimLineRot != math.pi) and self.textRotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL:            
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE
         # testo posizionato nella parte opposta ai punti di quotatura
         elif self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            # temporaneamento lo imposto centrato solo per averela posizione del testo 
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.CENTERED_LINE
         else:
            textVerticalPos = self.textVerticalPos
         
         if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
            textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                           self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
         else:
            textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                           self.textHorizontalPos, textVerticalPos, self.textRotMode)

         # testo posizionato nella parte opposta ai punti di quotatura
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            # punto centrale del testo di quota
            insPtCenterTxt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth / 2)
            # angolo dal centro dell'arco al punto centrale del testo di quota
            dimCenterToTextInsPt_rot = qad_utils.getAngleBy2Pts(dimArc.center, insPtCenterTxt)
            if dimCenterToTextInsPt_rot > 0 and \
               (dimCenterToTextInsPt_rot <= math.pi or qad_utils.doubleNear(dimCenterToTextInsPt_rot, math.pi)):
               if dimLineArc.radius >= dimArc.radius:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
               else:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.BELOW_LINE
            else:
               if dimLineArc.radius >= dimArc.radius:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.BELOW_LINE
               else:
                  textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE

            if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
               textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                              self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
            else:
               textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                              self.textHorizontalPos, textVerticalPos, self.textRotMode)

         rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)
                  
         # se lo spazio non é sufficiente per inserire testo e simboli all'interno delle linee di estensione,
         # uso qad_utils.doubleSmaller perché a volte i due numeri sono quasi uguali 
         if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
            qad_utils.doubleSmaller(spaceForBlock1, self.getBlock1Size() + self.textOffsetDist) or \
            qad_utils.doubleSmaller(spaceForBlock2, self.getBlock2Size() + self.textOffsetDist):
            if self.blockSuppressionForNoSpace: # sopprime i simboli se non c'é spazio sufficiente all'interno delle linee di estensione
               block1Rot = None
               block2Rot = None
               
               # considero il testo senza frecce
               if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                  textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                 self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
               else:
                  textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                 self.textHorizontalPos, textVerticalPos, self.textRotMode)
               
               rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
               spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)
               # se non c'é spazio neanche per il testo senza le frecce
               if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                  spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:           
                  # sposta testo fuori dalle linee di estensione
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
               else:
                  textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1                
            else: # non devo sopprimere i simboli
               # la prima cosa da spostare all'esterno é :
               if self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.BOTH_OUTSIDE_EXT_LINES:
                  # sposta testo e frecce fuori dalle linee di estensione
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE 
                  block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne 
               # sposta prima le frecce poi, se non basta, anche il testo
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_BLOCKS_THEN_TEXT:
                  block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne 
                  # considero il testo senza frecce
                  if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
                     textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                    self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                  else:
                     textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                    self.textHorizontalPos, textVerticalPos, self.textRotMode)
                  
                  rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                  spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)
                  # se non c'é spazio neanche per il testo senza le frecce
                  if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                     spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:                
                     # sposta testo fuori dalle linee di estensione
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                  else:
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1 
               # sposta prima il testo poi, se non basta, anche le frecce
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.FIRST_TEXT_THEN_BLOCKS:
                  # sposto il testo fuori dalle linee di estensione
                  textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                  textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE 
                  # se non ci stanno neanche le frecce
                  if dimLineArcLen <= self.getBlock1Size() + self.getBlock2Size():
                     block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne 
                  else:
                     block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne
               # Sposta indistintamente il testo o le frecce (l'oggetto che si adatta meglio)
               elif self.textBlockAdjust == QadDimStyleTextBlocksAdjustEnum.WHICHEVER_FITS_BEST:
                  # sposto il più ingombrante
                  if self.getBlock1Size() + self.getBlock2Size() > textWidth: # le frecce sono più ingombranti del testo
                     textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
                     block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne
                     
                     # considero il testo senza frecce
                     if self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:                     
                        textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                       self.textHorizontalPos, textVerticalPos, QadDimStyleTxtRotModeEnum.ALIGNED_LINE)
                     else:
                        textInsPt, textRot = self.getTextPositionOnArc(dimLineArc, textWidth, textHeight, \
                                                                       self.textHorizontalPos, textVerticalPos, self.textRotMode)
                     
                     rect = self.textRectToQadPolyline(textInsPt, textWidth, textHeight, textRot)
                     spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(rect, dimLineArc)
                     # se non c'é spazio neanche per il testo senza le frecce
                     if spaceForBlock1 == 0 or spaceForBlock2 == 0 or \
                        spaceForBlock1 < self.textOffsetDist or spaceForBlock2 < self.textOffsetDist:                
                        # sposta testo fuori dalle linee di estensione
                        textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                        textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE
                     else:
                        textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1 
                  else: # il testo é più ingombrante dei simboli
                     # sposto il testo fuori dalle linee di estensione
                     textInsPt, textRot, txtLeaderLines = self.getTextPosAndLinesOutOfDimArc(dimLineArc, textWidth, textHeight)
                     textLinearDimComponentOn = QadDimComponentEnum.LEADER_LINE 
                     # se non ci stanno neanche le frecce
                     if dimLineArcLen <= self.getBlock1Size() + self.getBlock2Size():
                        block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False) # frecce esterne 
                     else:
                        block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne
         else: # se lo spazio é sufficiente per inserire testo e simboli all'interno delle linee di estensione,
            textLinearDimComponentOn = QadDimComponentEnum.DIM_LINE1
            block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne
      
      # il testo é sopra e allineato alla prima linea di estensione         
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE_UP:
         # angolo della linea che va dal punto di quota all'inizio della linea di quota
         if dimArc.startAngle == dimLineArc.startAngle:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getStartPt(), dimLineArcPt1)
         else:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getEndPt(), dimLineArcPt1)
            
         pt = qad_utils.getPolarPointByPtAngle(dimLineArcPt1, rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos
         
         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE
            
         textInsPt, textRot = self.getTextPositionOnLine(dimLineArcPt1, pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE1 
         
         # calcolo lo spazio dei blocchi in assenza del testo
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(None, dimLineArc)
         # se non c'é spazio per i blocchi
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # sposto le frecce all'esterno
               block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False)
         else: # c'é spazio per i blocchi
            block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne
               
      # il testo é sopra e allineato alla seconda linea di estensione         
      elif self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.SECOND_EXT_LINE_UP:
         # angolo della linea che va dal punto di quota all'inizio della linea di quota
         # angolo della linea che va dal punto di quota all'inizio della linea di quota
         if dimArc.startAngle == dimLineArc.startAngle:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getEndPt(), dimLineArcPt2)
         else:
            rotLine = qad_utils.getAngleBy2Pts(dimArc.getStartPt(), dimLineArcPt2)
         
         pt = qad_utils.getPolarPointByPtAngle(dimLineArcPt2, rotLine, self.textOffsetDist + textWidth)
         if self.textVerticalPos == QadDimStyleTxtVerticalPosEnum.EXTERN_LINE:
            textVerticalPos = QadDimStyleTxtVerticalPosEnum.ABOVE_LINE
         else:
            textVerticalPos = self.textVerticalPos
            
         if self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION:
            textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         else:
            textRotMode = QadDimStyleTxtRotModeEnum.ALIGNED_LINE
            
         textInsPt, textRot = self.getTextPositionOnLine(dimLineArcPt2, pt, textWidth, textHeight, \
                                                         QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE, \
                                                         textVerticalPos, textRotMode)
         textLinearDimComponentOn = QadDimComponentEnum.EXT_LINE2 
         
         # calcolo lo spazio dei blocchi in assenza del testo
         spaceForBlock1, spaceForBlock2 = self.getSpaceForBlock1AndBlock2OnArc(None, dimLineArc)
         # se non c'é spazio per i blocchi
         if spaceForBlock1 < self.getBlock1Size() or spaceForBlock2 < self.getBlock2Size():
            if self.blockSuppressionForNoSpace: # i blocchi sono soppressi
               block1Rot = None
               block2Rot = None
            else: # sposto le frecce all'esterno
               block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, False)
         else: # c'é spazio per i blocchi
            block1Rot, block2Rot = self.getBlocksRotOnArc(dimLineArc, True) # frecce interne
      
      if self.textDirection == QadDimStyleTxtDirectionEnum.DX_TO_SX:
         # il punto di inserimento diventa l'angolo in alto a destra del rettangolo
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, textHeight)
         # la rotazione viene capovolta
         textRot = qad_utils.normalizeAngle(textRot + math.pi)
   
      return [[textInsPt, textRot], [textLinearDimComponentOn, txtLeaderLines], block1Rot, block2Rot]


   # ============================================================================
   # getRadiusTextAndBlocksPosition
   # ============================================================================
   def getRadiusTextAndBlocksPosition(self, dimLine, textWidth, textHeight):
      """
      dimLine = linea di quota (QadLine)
      textWidth  = larghezza testo
      textHeight = altezza testo
      
      Restituisce una lista di 4 elementi:
      - il primo elemento é una lista con il punto di inserimento del testo della quota e la sua rotazione
      - il secondo elemento é una lista con flag che indica il tipo della linea sulla quale é stato messo il testo; vedi QadDimComponentEnum
                            e una lista di linee "leader" nel caso il testo sia all'esterno della quota
      - il terzo elemento é la rotazione del primo blocco delle frecce; può essere None se non visibile
      - il quarto elemento é la rotazione del secondo blocco delle frecce; può essere None se non visibile   
      """      
      textInsPt                = None # punto di inserimento del testo
      textRot                  = None # rotazione del testo
      textLinearDimComponentOn = None # codice del componente lineare sul quale é posizionato il testo
      txtLeaderLines           = None # lista di linee "leader" nel caso il testo sia all'esterno della quota

      # cambio alcui parametri di quotatura
      block1Name = self.block1Name
      self.block1Name = "" # nessuna freccia al punto 1 di quotatura
      block2Name = self.block2Name
      self.block2Name = "" # nessuna freccia al punto 2 di quotatura
      textBlockAdjust = self.textBlockAdjust
      self.textBlockAdjust = QadDimStyleTextBlocksAdjustEnum.FIRST_TEXT_THEN_BLOCKS # se il testo non ci sta va fuori dalla linea di quotatura
      textHorizontalPos = self.textHorizontalPos
      self.textHorizontalPos = QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE
      
      res = self.getLinearTextAndBlocksPosition(dimLine.getStartPt(), dimLine.getEndPt(), dimLine, textWidth, textHeight)
      
      # ripristino i valori originali
      self.block1Name = block1Name
      self.block2Name = block2Name
      self.textBlockAdjust = textBlockAdjust
      self.textHorizontalPos = textHorizontalPos
      
      return res

   
   # ============================================================================
   # getTextFeature
   # ============================================================================
   def getTextFeature(self, measure, pt = None, rot = None):
      """
      Restituisce la feature per il testo della quota.
      La rotazione é espressa in radianti.
      """
      _pt = QgsPointXY(0,0) if pt is None else pt
      _rot = 0 if rot is None else rot
      
      textualFeaturePrototype = self.getTextualFeaturePrototype()
      if textualFeaturePrototype is None:
         return None
      f = QgsFeature(textualFeaturePrototype)
      g = fromQadGeomToQgsGeom(QadPoint().set(_pt), self.getTextualLayer()) # trasformo la geometria
      f.setGeometry(g)

      # se il testo dipende da un solo campo 
      labelFieldNames = qad_label.get_labelFieldNames(self.getTextualLayer())
      if len(labelFieldNames) == 1 and len(labelFieldNames[0]) > 0:
         f.setAttribute(labelFieldNames[0], self.getFormattedText(measure))

      # se l'altezza testo dipende da un solo campo 
      sizeFldNames = qad_label.get_labelSizeFieldNames(self.getTextualLayer())
      if len(sizeFldNames) == 1 and len(sizeFldNames[0]) > 0:
         f.setAttribute(sizeFldNames[0], self.textHeight) # altezza testo
         
      # se la rotazione dipende da un solo campo
      rotFldNames = qad_label.get_labelRotationFieldNames(self.getTextualLayer())
      if len(rotFldNames) == 1 and len(rotFldNames[0]) > 0:
         f.setAttribute(rotFldNames[0], qad_utils.toDegrees(_rot)) # Converte da radianti a gradi
   
      # se il font dipende da un solo campo
      fontFamilyFldNames = qad_label.get_labelFontFamilyFieldNames(self.getTextualLayer())
      if len(fontFamilyFldNames) == 1 and len(fontFamilyFldNames[0]) > 0:
         f.setAttribute(fontFamilyFldNames[0], self.textFont) # nome del font di testo      
      
      # imposto il colore
      try:
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.textColor)
      except:
         pass
      
      # imposto lo stile di quotatura
      try:
         if len(self.dimStyleFieldName) > 0:
            f.setAttribute(self.dimStyleFieldName, self.name)         
         if len(self.dimTypeFieldName) > 0:
            f.setAttribute(self.dimTypeFieldName, self.dimType)         
      except:
         pass
      
      return f  

             
   # ============================================================================
   # FUNZIONI PER IL TESTO - FINE
   # FUNZIONI PER LA LINEA DI LEADER - INIZIO
   # ============================================================================


   # ============================================================================
   # getAuxiliarySecondLeaderLine
   # ============================================================================
   def getAuxiliarySecondLeaderLine(self, pt1, rotLine, textWidth, textHeight):
      """
      Funzione interna di ausilio per le successive che si occupano di leader line.
      Restituisce la seconda linea porta quota (quella più vicina al testo).
      pt1 = punto da cui iniziare la linea (QgsPointXY)
      rotLine = angolo della prima linea porta quota (QgsPointXY)
      textWidth = larghezza testo
      textHeight = altezza testo
      """
      # modalità di rotazione del testo orizzontale o
      # testo allineato con la linea di quota se tra le linee di estensione, altrimenti testo orizzontale
      if self.textRotMode == QadDimStyleTxtRotModeEnum.HORIZONTAL or \
         self.textRotMode == QadDimStyleTxtRotModeEnum.ISO:
         if qad_utils.doubleNear(rotLine, math.pi / 2): # verticale dal basso verso l'alto
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, 0, self.textOffsetDist + textWidth)
         elif qad_utils.doubleNear(rotLine, math.pi * 3 / 2): # verticale dall'alto verso il basso 
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, math.pi, self.textOffsetDist + textWidth)
         elif (rotLine > math.pi * 3 / 2 and rotLine <= math.pi * 2) or \
              (rotLine >= 0 and rotLine < math.pi / 2): # da sx a dx
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, 0, self.textOffsetDist + textWidth)
         else: # da dx a sx
            pt2 = qad_utils.getPolarPointByPtAngle(pt1, math.pi, self.textOffsetDist + textWidth)
      elif self.textRotMode == QadDimStyleTxtRotModeEnum.ALIGNED_LINE: # testo allineato con la linea di quota
         pt2 = qad_utils.getPolarPointByPtAngle(pt1, rotLine, self.textOffsetDist + textWidth)
      elif self.textRotMode == QadDimStyleTxtRotModeEnum.FORCED_ROTATION: # testo con rotazione forzata
         pt2 = qad_utils.getPolarPointByPtAngle(pt1, self.textForcedRot, self.textOffsetDist + textWidth)

      return QadLine().set(pt1, pt2)


   # ============================================================================
   # getLeaderLinesOnLine
   # ============================================================================
   def getLeaderLinesOnLine(self, dimLinePt1, dimLinePt2, textWidth, textHeight):
      """
      Restituisce una polilinea (QadPolyline) che forma il porta quota nel caso il testo venga spostato
      fuori dalle linee di estensione perché era troppo grosso.
      dimLinePt1 = primo punto della linea di quota (QgsPointXY)
      dimLinePt2 = secondo punto della linea di quota (QgsPointXY)
      textWidth = larghezza testo
      textHeight = altezza testo
      """
      res = QadPolyline()
      # le linee sono a lato della linea di estensione 1
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE:
         rotLine = qad_utils.getAngleBy2Pts(dimLinePt2, dimLinePt1) # angolo della linea porta quota
         pt1 = qad_utils.getPolarPointByPtAngle(dimLinePt1, rotLine, self.getBlock1Size())
         res.append(QadLine().set(dimLinePt1, pt1))
      # le linee sono a lato della linea di estensione 2
      else:
         rotLine = qad_utils.getAngleBy2Pts(dimLinePt1, dimLinePt2) # angolo della linea porta quota
         pt1 = qad_utils.getPolarPointByPtAngle(dimLinePt2, rotLine, self.getBlock2Size())
         res.append(QadLine().set(dimLinePt2, pt1))
      
      # ricavo la seconda linea di porta quota
      line2 = self.getAuxiliarySecondLeaderLine(pt1, rotLine, textWidth, textHeight)
      res.append(line2)
         
      return res


   # ============================================================================
   # getLeaderLinesOnArc
   # ============================================================================
   def getLeaderLinesOnArc(self, dimLineArc, textWidth, textHeight):
      """
      Restituisce una polilinea (QadPolyline) che forma il porta quota nel caso il testo venga spostato
      fuori dalle linee di estensione perché era troppo grosso.
      dimLineArc = arco rappresentante l'arco di quota (QadArc)
      textWidth = larghezza testo
      textHeight = altezza testo
      """
      res = QadPolyline()
      # le linee sono a lato della linea di estensione 1
      if self.textHorizontalPos == QadDimStyleTxtHorizontalPosEnum.FIRST_EXT_LINE:
         startPt = dimLineArc.getStartPt()
         rotLine = dimLineArc.getTanDirectionOnPt(startPt) + math.pi # angolo della linea porta quota sul punto iniziale
         pt1 = qad_utils.getPolarPointByPtAngle(startPt, rotLine, self.getBlock1Size())
         res.append(QadLine().set(startPt, pt1))
      # le linee sono a lato della linea di estensione 2
      else:
         endPt = dimLineArc.getEndPt()
         rotLine = dimLineArc.getTanDirectionOnPt(endPt) # angolo della linea porta quota sul punto finale
         pt1 = qad_utils.getPolarPointByPtAngle(endPt, rotLine, self.getBlock2Size())
         res.append(QadLine().set(endPt, pt1))
         
      # ricavo la seconda linea di porta quota
      line2 = self.getAuxiliarySecondLeaderLine(pt1, rotLine, textWidth, textHeight)
      res.append(line2)
      
      return res


   # ============================================================================
   # getLeaderFeature
   # ============================================================================
   def getLeaderFeature(self, leaderLines, leaderLineType = QadDimComponentEnum.LEADER_LINE):
      """
      Restituisce la feature per la linea di estensione.
      leaderLines = polilinea leader (QadPolyline)
      leaderLineType = tipo di linea porta quota (LEADER_LINE, ARC_LEADER_LINE, ...)
      """
      if leaderLines is None:
         return None

      linearFeaturePrototype = self.getLinearFeaturePrototype()
      if linearFeaturePrototype is None:
         return None
      f = QgsFeature(linearFeaturePrototype)
      g = fromQadGeomToQgsGeom(leaderLines, self.getLinearLayer())
      f.setGeometry(g)
         
      try:
         # imposto il tipo di componente della quotatura
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, leaderLineType)
      except:
         pass

      try:
         # imposto il tipo di linea
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)         
      except:
         pass

      try:
         # imposto il colore
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)         
      except:
         pass

      return f
      

   # ============================================================================
   # getArcLeaderLine
   # ============================================================================
   def getArcLeaderLine(self, pt, arc):
      """
      Restituisce la linea che congiunge il testo all'arco da quotare.
      """
      intPts = QadIntersections.infinityLineWithArc(QadLine().set(pt, arc.center), arc)
      if len(intPts) == 1:
         return [pt, intPts[0]]
      elif len(intPts) == 2:
         # scelgo il più vicino
         if qad_utils.getDistance(pt, intPts[0]) < qad_utils.getDistance(pt, intPts[1]):
            return QadLine().set(pt, intPts[0])
         else:
            return QadLine().set(pt, intPts[1])
      else:
         return None
      
      
   # ============================================================================
   # FUNZIONI PER LA LINEA DI LEADER - FINE
   # FUNZIONI PER LE LINEE DI ESTENSIONE - INIZIO
   # ============================================================================


   # ============================================================================
   # getExtLine
   # ============================================================================
   def getExtLine(self, dimPt, dimLinePt):
      """
      dimPt     = punto da quotare
      dimLinePt = corrispondente punto della linea di quotatura
      
      ritorna una linea di estensione modificata secondo lo stile di quotatura
      il primo punto é vicino alla linea di quota, il secondo al punto da quotare
      """

      angle = qad_utils.getAngleBy2Pts(dimPt, dimLinePt)
      # distanza della linea di estensione oltre la linea di quota
      pt1 = qad_utils.getPolarPointByPtAngle(dimLinePt, angle, self.extLineOffsetDimLine)
      # distanza della linea di estensione dai punti da quotare
      pt2 = qad_utils.getPolarPointByPtAngle(dimPt, angle, self.extLineOffsetOrigPoints)        

      if self.extLineIsFixedLen == True: # attivata lunghezza fissa delle line di estensione      
         if qad_utils.getDistance(pt1, pt2) > self.extLineFixedLen:
            # lunghezza fissa delle line di estensione (DIMFXL) dalla linea di quota 
            # al punto da quotare spostato di extLineOffsetOrigPoints
            # (la linea di estensione non va oltre il punto da quotare)
            d = qad_utils.getDistance(dimLinePt, dimPt)
            if d > self.extLineFixedLen:
               d = self.extLineFixedLen
            pt2 = qad_utils.getPolarPointByPtAngle(dimLinePt, angle + math.pi, d)        

      return QadLine().set(pt1, pt2)


   # ============================================================================
   # getExtArc
   # ============================================================================
   def getExtArc(self, arc, linePosPt):
      """
      arc     = arco da quotare
      linePosPt = punto corrispondente a dove posizionare la quotatura
      
      Ritorna un arco di estensione per la quotatura DIMRADIUS
      """
      # se il punto è all'interno dell'arco
      angle = qad_utils.getAngleBy2Pts(arc.center, linePosPt)
      if qad_utils.isAngleBetweenAngles(arc.startAngle, arc.endAngle, angle) == True:
         return None

      myArc = QadArc()
      pt = qad_utils.getPolarPointByPtAngle(arc.center, angle, arc.radius) # punto sulla curva
      # dalla parte del punto iniziale dell'arco
      if qad_utils.getDistance(pt, arc.getStartPt()) < qad_utils.getDistance(pt, arc.getEndPt()):
         myArc.set(arc.center, arc.radius, angle, arc.startAngle)
         if myArc.length() <= self.extLineOffsetOrigPoints:
            return None
         
         myArc.setStartAngleByPt(pt)
         dummyPt, dummyTg = myArc.getPointFromStart(-self.extLineOffsetDimLine)
         myArc.setStartAngleByPt(dummyPt)
         dummyPt, dummyTg = arc.getPointFromStart(-self.extLineOffsetOrigPoints)
         myArc.setEndAngleByPt(dummyPt) # cambio punto finale
      else: # dalla parte del punto finale dell'arco
         myArc.set(arc.center, arc.radius, arc.endAngle, angle)
         if myArc.length() <= self.extLineOffsetOrigPoints:
            return None
         dummyPt, dummyTg = arc.getPointFromEnd(self.extLineOffsetOrigPoints)
         myArc.setStartAngleByPt(dummyPt) # cambio punto iniziale
         myArc.setEndAngleByPt(pt)
         dummyPt, dummyTg = myArc.getPointFromEnd(self.extLineOffsetDimLine)
         myArc.setEndAngleByPt(dummyPt)
      
      return myArc


   # ============================================================================
   # getExtLineFeature
   # ============================================================================
   def getExtLineFeature(self, extLine, isExtLine1):
      """
      Restituisce la feature per la linea di estensione.
      extLine = linea di estensione QadLine o QadArc
      isExtLine1 = se True si tratta della linea di estensione 1 altrimenti della linea di estensione 2
      """
      if (isExtLine1 == True and self.extLine1Show == False) or \
         (isExtLine1 == False and self.extLine2Show == False):
         return None
      
      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(extLine, self.getLinearLayer()) # trasformo la geometria
      f.setGeometry(g)
                  
      try:
         # imposto il tipo di componente della quotatura
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.EXT_LINE1 if isExtLine1 else QadDimComponentEnum.EXT_LINE2)
      except:
         pass

      try:
         # imposto il tipo di linea
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.extLine1LineType if isExtLine1 else self.extLine2LineType)         
      except:
         pass

      try:
         # imposto il colore
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.extLineColor) 
      except:
         pass

      return f

             
   # ============================================================================
   # FUNZIONI PER LE LINEE DI ESTENSIONE - FINE
   # FUNZIONI PER LA LINEA DI QUOTA - INIZIO
   # ============================================================================


   # ============================================================================
   # getDimLine
   # ============================================================================
   def getDimLine(self, dimPt1, dimPt2, linePosPt, preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL,
                  dimLineRotation = 0.0):
      """
      Restituisce la linea di quotatura entro le linee di estensione (eventuali estensioni saranno calcolate 
      dalla funzione: getDimLineExtensions)

      dimPt1 = primo punto da quotare
      dimPt2 = secondo punto da quotare
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota
      preferredAlignment = indica se ci si deve allineare ai punti di quota in modo orizzontale o verticale
                           (se i punti di quota formano una linea obliqua). Usato solo per le quotature lineari 
      dimLineRotation = angolo della linea di quotatura (default = 0). Usato solo per le quotature lineari 
      """      
      if self.dimType == QadDimTypeEnum.ALIGNED:
         # calcolo la proiezione perpendicolare del punto <linePosPt> sulla linea che congiunge <dimPt1> a <dimPt2>
         ptPerp = qad_utils.getPerpendicularPointOnInfinityLine(dimPt1, dimPt2, linePosPt)
         d = qad_utils.getDistance(linePosPt, ptPerp)
   
         angle = qad_utils.getAngleBy2Pts(dimPt1, dimPt2)
         if qad_utils.leftOfLine(linePosPt, dimPt1, dimPt2) < 0: # a sinistra della linea che congiunge <dimPt1> a <dimPt2>
            angle = angle + (math.pi / 2)
         else:
            angle = angle - (math.pi / 2)
   
         return QadLine().set(qad_utils.getPolarPointByPtAngle(dimPt1, angle, d), \
                              qad_utils.getPolarPointByPtAngle(dimPt2, angle, d))
      elif self.dimType == QadDimTypeEnum.LINEAR:
         if preferredAlignment == QadDimStyleAlignmentEnum.HORIZONTAL:
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt1, dimLineRotation + math.pi / 2, 1)
            pt1 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt1, ptDummy, linePosPt)
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt2, dimLineRotation + math.pi / 2, 1)
            pt2 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt2, ptDummy, linePosPt)
 
            return QadLine().set(pt1, pt2)
         elif preferredAlignment == QadDimStyleAlignmentEnum.VERTICAL:
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt1, dimLineRotation, 1)
            pt1 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt1, ptDummy, linePosPt)
            ptDummy = qad_utils.getPolarPointByPtAngle(dimPt2, dimLineRotation, 1)
            pt2 = qad_utils.getPerpendicularPointOnInfinityLine(dimPt2, ptDummy, linePosPt)
 
            return QadLine().set(pt1, pt2)


   # ============================================================================
   # getDimLineForArc
   # ============================================================================
   def getDimLineForArc(self, arc, linePosPt):
      """
      Restituisce la linea di quotatura (sottoforma di un arco) per la l'ampiezza di un arco + 
      un flag per avvisare se l'arco è stato invertito
      Restituisce la linea di quotatura entro le linee di estensione (eventuali estensioni saranno calcolate 
      dalla funzione: getDimArcExtensions)

      arc = oggetto arco QadArc (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota
      """
      if self.dimType == QadDimTypeEnum.ARC_LENTGH:
         myArc = QadArc(arc)
         # calcolo la distanza tra <linePosPt> e il centro dell'arco
         d = qad_utils.getDistance(linePosPt, myArc.center)
         myArc.radius = d # cambio il raggio
         
         # se il punto non è all'interno dell'arco considero l'inverso dell'arco
         angle = qad_utils.getAngleBy2Pts(myArc.center, linePosPt)
         if qad_utils.isAngleBetweenAngles(myArc.startAngle, myArc.endAngle, angle) == False:
            myArc.inverseAngles()
         return myArc
      
      return None


   # ============================================================================
   # getDimLineFeature
   # ============================================================================
   def getDimLineFeature(self, dimLine, isDimLine1, textLinearDimComponentOn):
      """
      Restituisce la feature per la linea di quota.
      dimLine = linea di quota (QadLine o QadArc)
      isDimLine1 = se True si tratta della linea di quota 1 altrimenti della linea di quota 2
      textLinearDimComponentOn = indica il componente della quota dove é situato il testo di quota (QadDimComponentEnum)
     """
            
      # se non c'é la linea di quota
      if dimLine is None:
         return None
      if isDimLine1 == True: # se si tratta della linea di quota 1
         # se la linea di quota 1 deve essere invisibile (vale solo se il testo é sulla linea di quota)
         if self.dimLine1Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None
      else: # se si tratta della linea di quota 2
         # se la linea di quota 2 deve essere invisibile (vale solo se il testo é sulla linea di quota)
         if self.dimLine2Show == False and \
           (textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1 or textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE2):
            return None
               
      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(dimLine, self.getLinearLayer()) # trasformo la geometria
      f.setGeometry(g)
         
      try:
         # imposto il tipo di componente della quotatura
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.DIM_LINE1 if isDimLine1 else QadDimComponentEnum.DIM_LINE2)
      except:
         pass

      try:
         # imposto il tipo di linea
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)         
      except:
         pass

      try:
         # imposto il colore
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.dimLineColor)         
      except:
         pass

      return f


   # ============================================================================
   # FUNZIONI PER LA LINEA DI QUOTA - FINE
   # FUNZIONI PER LE ESTENSIONI DELLA LINEA DI QUOTATURA - INIZIO
   # ============================================================================


   # ============================================================================
   # getDimLineExtensions
   # ============================================================================
   def getDimLineExtensions(self, dimLine1, dimLine2):
      """
      Restituisce le estensioni delle linee di quotatura a inizio e fine (vedi variabile dimLineOffsetExtLine)
      """
      # se non è maggiore di 0 oppure se non ci sono linee di dimensione
      if self.dimLineOffsetExtLine <= 0 or (dimLine1 is None and dimLine2 is None):
         return None, None
      
      extDimLine1 = None
      extDimLine2 = None
      # imposto le linee nello stesso verso della linea di dimensione
      rot = qad_utils.getAngleBy2Pts(dimLine1.getStartPt(), dimLine1.getEndPt())
      if dimLine1 is not None:
         # cambio punto iniziale
         extDimLine1 = QadLine().set(qad_utils.getPolarPointByPtAngle(dimLine1.getStartPt(), rot + math.pi, self.dimLineOffsetExtLine), \
                                     dimLine1.getStartPt())
         if dimLine2 is None: # se la linea di quotatura è composta solo di una linea
            # cambio punto finale
            extDimLine2 = QadLine().set(dimLine1.getEndPt(), \
                                        qad_utils.getPolarPointByPtAngle(dimLine1.getEndPt(), rot, self.dimLineOffsetExtLine))

      if dimLine2 is not None:
         rot = qad_utils.getAngleBy2Pts(dimLine2.getStartPt(), dimLine2.getEndPt())
         # cambio punto finale
         extDimLine2 = QadLine().set(dimLine2.getEndPt(), \
                                     qad_utils.getPolarPointByPtAngle(dimLine2.getEndPt(), rot, self.dimLineOffsetExtLine))

      return extDimLine1, extDimLine2


   # ============================================================================
   # getDimArcExtension
   # ============================================================================
   def getDimArcExtensions(self, dimLineArc1, dimLineArc2):
      """
      Restituisce le estensioni degli archi di quotatura applicando a inizio e fine (vedi variabile dimLineOffsetExtLine)
      """
      # se non è maggiore di 0 oppure se non ci sono linee di dimensione
      if self.dimLineOffsetExtLine <= 0 or (dimLineArc1 is None and dimLineArc2 is None):
         return None, None
      
      extDimArc1 = None
      extDimArc2 = None
      if dimLineArc1 is not None:
         extDimArc1 = QadArc(dimLineArc1)
         extDimArc1.endAngle = dimLineArc1.startAngle
         dummyPt, dummyTg = dimLineArc1.getPointFromStart(-self.dimLineOffsetExtLine)
         extDimArc1.setStartAngleByPt(dummyPt) # cambio punto iniziale
         if dimLineArc2 is None: # se la linea di quotatura è composta solo di un arco
            extDimArc2 = QadArc(dimLineArc1)
            extDimArc2.startAngle = dimLineArc1.endAngle
            dummyPt, dummtTg = dimLineArc1.getPointFromEnd(self.dimLineOffsetExtLine)
            extDimArc2.setEndAngleByPt(dummyPt) # cambio punto finale

      if dimLineArc2 is not None:
         extDimArc2 = QadArc(dimLineArc2)
         extDimArc2.startAngle = dimLineArc1.endAngle
         dummyPt, dummtTg = dimLineArc2.getPointFromEnd(self.dimLineOffsetExtLine)
         dimLineArc2.setEndAngleByPt(dummyPt) # cambio punto finale
            
      return extDimArc1, extDimArc2


   # ============================================================================
   # getDimLineExtFeature
   # ============================================================================
   def getDimLineExtFeature(self, extLine, isExtLine1):
      """
      Restituisce la feature per l'estensione della linea di quotatura.
      extLine = linea di estensione (QadLine o QadArc)
      isExtLine1 = se True si tratta della estensione della linea di quotatura 1 altrimenti della linea di quotatura 2
      """
      if extLine is None:
         return None
      
      f = QgsFeature(self.getLinearFeaturePrototype())
      g = fromQadGeomToQgsGeom(extLine, self.getLinearLayer()) # trasformo la geometria
      f.setGeometry(g)
                  
      try:
         # imposto il tipo di componente della quotatura
         if len(self.componentFieldName) > 0:
            f.setAttribute(self.componentFieldName, QadDimComponentEnum.DIM_LINE_EXT1 if isExtLine1 else QadDimComponentEnum.DIM_LINE_EXT2)
      except:
         pass

      try:
         # imposto il tipo di linea
         if len(self.lineTypeFieldName) > 0:
            f.setAttribute(self.lineTypeFieldName, self.extLine1LineType if isExtLine1 else self.extLine2LineType)         
      except:
         pass

      try:
         # imposto il colore
         if len(self.colorFieldName) > 0:
            f.setAttribute(self.colorFieldName, self.extLineColor) 
      except:
         pass

      return f


   # ============================================================================
   # FUNZIONI PER LE ESTENSIONI DELLA LINEA DI QUOTATURA - FINE
   # FUNZIONI PER LA QUOTATURA LINEARE - INIZIO
   # ============================================================================


   # ============================================================================
   # getLinearDimFeatures
   # ============================================================================
   def getLinearDimFeatures(self, canvas, dimPt1, dimPt2, linePosPt, measure = None, \
                            preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL, \
                            dimLineRotation = 0.0):
      """
      dimPt1 = primo punto da quotare (in unita di mappa)
      dimPt2 = secondo punto da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      measure = indica se la misura é predeterminata oppure (se = None) deve essere calcolata
      preferredAlignment = se lo stile di quota é lineare, indica se ci si deve allienare ai punti di quota
                           in modo orizzontale o verticale (se i punti di quota formano una linea obliqua)      
      dimLineRotation = angolo della linea di quotatura (default = 0) 
      
      # quota lineare con una linea di quota orizzontale o verticale
      # ritorna una lista di elementi che descrivono la geometria della quota:
      # 1 lista = feature del primo e del secondo punto di quota; QgsFeature 1, QgsFeature 2
      # 2 lista = feature della prima e della seconda linea di quota (quest'ultima può essere None); QgsFeature 1, QgsFeature 2
      # 3 lista = feature del punto del testo di quota e geometria del rettangolo di occupazione; QgsFeature, QgsGeometry
      # 4 lista = feature del primo e del secondo simbolo per la linea di quota (possono essere None); QgsFeature 1, QgsFeature 2
      # 5 lista = feature della prima e della seconda linea di estensione (possono essere None); QgsFeature 1, QgsFeature 2
      # 6 elemento = feature della linea di leader (può essere None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.LINEAR
      
      # punti di quotatura
      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = primo punto di quotatura
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = secondo punto di quotatura   
               
      # linea di quota entro le linee di estensione
      dimLine1 = self.getDimLine(dimPt1, dimPt2, linePosPt, preferredAlignment, dimLineRotation)
      dimLine2 = None
               
      # testo e blocchi
      if measure is None:
         textValue = dimLine1.length()
      else:
         textValue = unicode(measure)
         
      textFeature = self.getTextFeature(textValue)
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)
               
      # creo un rettangolo intorno al testo con un buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2

      # Restituisce una lista di 4 elementi:
      # - il primo elemento é una lista con il punto di inserimento del testo della quota e la sua rotazione
      # - il secondo elemento é una lista con flag che indica il tipo della linea sulla quale é stato messo il testo; vedi QadDimComponentEnum
      #                       e una lista di linee "leader" nel caso il testo sia all'esterno della quota
      # - il terzo elemento é la rotazione del primo blocco delle frecce; può essere None se non visibile
      # - il quarto elemento é la rotazione del secondo blocco delle frecce; può essere None se non visibile      
      dummy1, dummy2, block1Rot, block2Rot = self.getLinearTextAndBlocksPosition(dimPt1, dimPt2, \
                                                                                 dimLine1, \
                                                                                 textWidthOffset, textHeightOffset)
               
      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # trovo il vero punto di inserimento del testo tenendo conto del buffer intorno      
      textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
      textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)
               
      # testo
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)
               
      # blocchi frecce
      block1Feature = self.getSymbolFeature(dimLine1.getStartPt(), block1Rot, True, textLinearDimComponentOn) # True = primo punto di quotatura
      block2Feature = self.getSymbolFeature(dimLine1.getEndPt(), block2Rot, False, textLinearDimComponentOn) # False = secondo punto di quotatura   
               
      extLine1 = self.getExtLine(dimPt1, dimLine1.getStartPt())
      extLine2 = self.getExtLine(dimPt2, dimLine1.getEndPt())
      
      # creo un rettangolo intorno al testo con un offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)
               
      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # linea di quota ("Dimension line")
         dimLine1, dimLine2 = self.adjustLineAccordingTextRect(textOffsetRect, dimLine1, QadDimComponentEnum.DIM_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # prima linea di estensione ("Extension line 1")
         if extLine1 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt1, dimLine1.getStartPt())
            extLine1 = self.getExtLine(dimPt1, qad_utils.getPolarPointByPtAngle(dimLine1.getStartPt(), extLineRot, textWidth + self.textOffsetDist))
            # cambio il verso della linea perché getExtLine restituisce una linea dalla linea di quota verso il punto di quotatura
            reverseExtLine1 = extLine1.copy().reverse()
            extLine1, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine1, QadDimComponentEnum.EXT_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # seconda linea di estensione ("Extension line 2")
         if extLine2 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt2, dimLine1.getEndPt())
            extLine2 = self.getExtLine(dimPt2, qad_utils.getPolarPointByPtAngle(dimLine1.getEndPt(), extLineRot, textWidth + self.textOffsetDist))            
            # cambio il verso della linea perché getExtLine restituisce una linea dalla linea di quota verso il punto di quotatura       
            reverseExtLine2 = extLine2.copy().reverse()
            extLine2, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine2, QadDimComponentEnum.EXT_LINE2)
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # linea porta quota usata quando il testo é fuori dalla quota ("Leader")
         lastLine = txtLeaderLines.getLinearObjectAt(-1)
         lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
         txtLeaderLines.remove(-1) # sostituisco l'ultimo elemento
         txtLeaderLines.append(lastLine)
               
      # linee di quota
      dimLine1Feature = self.getDimLineFeature(dimLine1, True, textLinearDimComponentOn) # True = prima linea di quota
      dimLine2Feature = self.getDimLineFeature(dimLine2, False, textLinearDimComponentOn) # False = seconda linea di quota
      
      # estensioni delle linee di quota
      dimLineExt1, dimLineExt2 = self.getDimLineExtensions(dimLine1, dimLine2)
      dimLineExt1Feature = self.getDimLineExtFeature(dimLineExt1, True)
      dimLineExt2Feature = self.getDimLineExtFeature(dimLineExt2, False)

      # linee di estensione
      extLine1Feature = self.getExtLineFeature(extLine1, True)  # True = prima linea di estensione
      extLine2Feature = self.getExtLineFeature(extLine2, False) # False = seconda linea di estensione
   
      # linea di leader
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines)

      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLine1Feature is not None:
         dimEntity.linearFeatures.append(dimLine1Feature)
      if dimLine2Feature is not None:
         dimEntity.linearFeatures.append(dimLine2Feature)

      if dimLineExt1Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt1Feature)
      if dimLineExt2Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt2Feature)
         
      if extLine1Feature is not None:
         dimEntity.linearFeatures.append(extLine1Feature)
      if extLine2Feature is not None:
         dimEntity.linearFeatures.append(extLine2Feature)
         
      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if block1Feature is not None:
         dimEntity.symbolFeatures.append(block1Feature)
      if block2Feature is not None:
         dimEntity.symbolFeatures.append(block2Feature)
      
      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addLinearDimToLayers
   # ============================================================================
   def addLinearDimToLayers(self, plugIn, dimPt1, dimPt2, linePosPt, measure = None, \
                            preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL, \
                            dimLineRotation = 0.0):
      """
      Aggiunge ai layers le features che compongono una quota lineare.
      """
      dimEntity, textOffsetRect = self.getLinearDimFeatures(plugIn.canvas, \
                                                            dimPt1, \
                                                            dimPt2, \
                                                            linePosPt, \
                                                            measure, \
                                                            preferredAlignment, \
                                                            dimLineRotation)
      
      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNZIONI PER LA QUOTATURA LINEARE - FINE
   # FUNZIONI PER LA QUOTATURA ALLINEATA - INIZIO
   # ============================================================================
   

   # ============================================================================
   # getAlignedDimFeatures
   # ============================================================================
   def getAlignedDimFeatures(self, canvas, dimPt1, dimPt2, linePosPt, measure = None):
      """
      dimPt1 = primo punto da quotare (in unita di mappa)
      dimPt2 = secondo punto da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      measure = indica se la misura é predeterminata oppure (se = None) deve essere calcolata
      
      # quota lineare con una linea di quota orizzontale o verticale
      # ritorna una lista di elementi che descrivono la geometria della quota:
      # 1 lista = feature del primo e del secondo punto di quota; QgsFeature 1, QgsFeature 2
      # 2 lista = feature della prima e della seconda linea di quota (quest'ultima può essere None); QgsFeature 1, QgsFeature 2
      # 3 lista = feature del punto del testo di quota e geometria del rettangolo di occupazione; QgsFeature, QgsGeometry
      # 4 lista = feature del primo e del secondo simbolo per la linea di quota (possono essere None); QgsFeature 1, QgsFeature 2
      # 5 lista = feature della prima e della seconda linea di estensione (possono essere None); QgsFeature 1, QgsFeature 2
      # 6 elemento = feature della linea di leader (può essere None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.ALIGNED
      
      # punti di quotatura
      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = primo punto di quotatura
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = secondo punto di quotatura   
               
      # linea di quota entro le linee di estensione
      dimLine1 = self.getDimLine(dimPt1, dimPt2, linePosPt)
      dimLine2 = None
      
      # testo e blocchi
      if measure is None:
         textValue = dimLine1.length()
      else:
         textValue = unicode(measure)
         
      textFeature = self.getTextFeature(textValue)      
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)

      # creo un rettangolo intorno al testo con un buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2

      # Restituisce una lista di 4 elementi:
      # - il primo elemento é una lista con il punto di inserimento del testo della quota e la sua rotazione
      # - il secondo elemento é una lista con flag che indica il tipo della linea sulla quale é stato messo il testo; vedi QadDimComponentEnum
      #                       e una lista di linee "leader" nel caso il testo sia all'esterno della quota
      # - il terzo elemento é la rotazione del primo blocco delle frecce; può essere None se non visibile
      # - il quarto elemento é la rotazione del secondo blocco delle frecce; può essere None se non visibile      
      dummy1, dummy2, block1Rot, block2Rot = self.getLinearTextAndBlocksPosition(dimPt1, dimPt2, \
                                                                                 dimLine1, \
                                                                                 textWidthOffset, textHeightOffset)
      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # trovo il vero punto di inserimento del testo tenendo conto del buffer intorno      
      textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
      textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)

      # testo
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)

      # blocchi frecce
      block1Feature = self.getSymbolFeature(dimLine1.getStartPt(), block1Rot, True, textLinearDimComponentOn) # True = primo punto di quotatura
      block2Feature = self.getSymbolFeature(dimLine1.getEndPt(), block2Rot, False, textLinearDimComponentOn) # False = secondo punto di quotatura   
            
      extLine1 = self.getExtLine(dimPt1, dimLine1.getStartPt())
      extLine2 = self.getExtLine(dimPt2, dimLine1.getEndPt())
      
      # creo un rettangolo intorno al testo con un offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)
      
      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # linea di quota ("Dimension line")
         dimLine1, dimLine2 = self.adjustLineAccordingTextRect(textOffsetRect, dimLine1, QadDimComponentEnum.DIM_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # prima linea di estensione ("Extension line 1")
         if extLine1 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt1, dimLine1.getStartPt())
            extLine1 = self.getExtLine(dimPt1, qad_utils.getPolarPointByPtAngle(dimLine1.getStartPt(), extLineRot, textWidth + self.textOffsetDist))
            # cambio il verso della linea perché getExtLine restituisce una linea dalla linea di quota verso il punto di quotatura       
            reverseExtLine1 = extLine1.copy().reverse()
            extLine1, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine1, QadDimComponentEnum.EXT_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # seconda linea di estensione ("Extension line 2")
         if extLine2 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt2, dimLine1.getEndPt())
            extLine2 = self.getExtLine(dimPt2, qad_utils.getPolarPointByPtAngle(dimLine1.getEndPt(), extLineRot, textWidth + self.textOffsetDist))            
            # cambio il verso della linea perché getExtLine restituisce una linea dalla linea di quota verso il punto di quotatura       
            reverseExtLine2 = extLine2.copy().reverse()
            extLine2, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine2, QadDimComponentEnum.EXT_LINE2)
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # linea porta quota usata quando il testo é fuori dalla quota ("Leader")
         lastLine = txtLeaderLines.getLinearObjectAt(-1)
         lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
         txtLeaderLines.remove(-1) # sostituisco l'ultimo elemento
         txtLeaderLines.append(lastLine)
      
      # linee di quota
      dimLine1Feature = self.getDimLineFeature(dimLine1, True, textLinearDimComponentOn) # True = prima linea di quota
      dimLine2Feature = self.getDimLineFeature(dimLine2, False, textLinearDimComponentOn) # False = seconda linea di quota

      # estensioni delle linee di quota
      dimLineExt1, dimLineExt2 = self.getDimLineExtensions(dimLine1, dimLine2)
      dimLineExt1Feature = self.getDimLineExtFeature(dimLineExt1, True)
      dimLineExt2Feature = self.getDimLineExtFeature(dimLineExt2, False)

      # linee di estensione
      extLine1Feature = self.getExtLineFeature(extLine1, True)  # True = prima linea di estensione
      extLine2Feature = self.getExtLineFeature(extLine2, False) # False = seconda linea di estensione

      # linea di leader
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines)
   
      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLine1Feature is not None:
         dimEntity.linearFeatures.append(dimLine1Feature)
      if dimLine2Feature is not None:
         dimEntity.linearFeatures.append(dimLine2Feature)

      if dimLineExt1Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt1Feature)
      if dimLineExt2Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt2Feature)
         
      if extLine1Feature is not None:
         dimEntity.linearFeatures.append(extLine1Feature)
      if extLine2Feature is not None:
         dimEntity.linearFeatures.append(extLine2Feature)
         
      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if block1Feature is not None:
         dimEntity.symbolFeatures.append(block1Feature)
      if block2Feature is not None:
         dimEntity.symbolFeatures.append(block2Feature)
      
      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addAlignedDimToLayers
   # ============================================================================
   def addAlignedDimToLayers(self, plugIn, dimPt1, dimPt2, linePosPt, measure = None, \
                            preferredAlignment = QadDimStyleAlignmentEnum.HORIZONTAL, \
                            dimLineRotation = 0.0):
      """
      dimPt1 = primo punto da quotare (in unita di mappa)
      dimPt2 = secondo punto da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      measure = indica se la misura é predeterminata oppure (se = None) deve essere calcolata
      preferredAlignment = se lo stile di quota é lineare, indica se ci si deve allienare ai punti di quota
                           in modo orizzontale o verticale (se i punti di quota formano una linea obliqua)      
      dimLineRotation = angolo della linea di quotatura (default = 0) 

      Aggiunge ai layers le features che compongono una quota allineata.
      """
      dimEntity, textOffsetRect = self.getAlignedDimFeatures(plugIn.canvas, \
                                                             dimPt1, \
                                                             dimPt2, \
                                                             linePosPt, \
                                                             measure)

      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNZIONI PER LA QUOTATURA ALLINEATA - FINE
   # FUNZIONI PER LA QUOTATURA ARCO - INIZIO
   # ============================================================================
   

   # ============================================================================
   # getArcDimFeatures
   # ============================================================================
   def getArcDimFeatures(self, canvas, dimArc, linePosPt, measure = None, arcLeader = None):
      """
      dimArc = oggetto arco QadArc da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      measure = indica se la misura é predeterminata oppure (se = None) deve essere calcolata
      arcLeader = indica se si deve disegnare la linea direttrice dalla quota all'arco
      
      # quota arco per misurare la lunghezza di un arco o parte di esso
      # ritorna una lista di elementi che descrivono la geometria della quota:
      # 1 lista = feature del primo e del secondo punto di quota; QgsFeature 1, QgsFeature 2
      # 2 lista = feature della prima e della seconda linea di quota (quest'ultima può essere None); QgsFeature 1, QgsFeature 2
      # 3 lista = feature del punto del testo di quota e geometria del rettangolo di occupazione; QgsFeature, QgsGeometry
      # 4 lista = feature del primo e del secondo simbolo per la linea di quota (possono essere None); QgsFeature 1, QgsFeature 2
      # 5 lista = feature della prima e della seconda linea di estensione (possono essere None); QgsFeature 1, QgsFeature 2
      # 6 elemento = feature della linea di leader (può essere None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.ARC_LENTGH
      
      # linea di quota sottoforma di arco
      dimLineArc1 = self.getDimLineForArc(dimArc, linePosPt)
      dimLineArc1StartPt = dimLineArc1.getStartPt()
      dimLineArc1EndPt = dimLineArc1.getEndPt()
      dimLineArc2 = None

      dimPt1 = dimArc.getStartPt()
      dimPt2 = dimArc.getEndPt()

      # punti di quotatura
      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = primo punto di quotatura
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = secondo punto di quotatura   
      
      # testo e blocchi
      if measure is None:
         textValue = dimArc.length()
      else:
         textValue = unicode(measure)
         
      textFeature = self.getTextFeature(textValue)      
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)

      # creo un rettangolo intorno al testo con un buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2
      
      arcSymbRadius = textHeight * 2 / 4
      if self.arcSymbPos == QadDimStyleArcSymbolPosEnum.BEFORE_TEXT:
         textWidthOffset = textWidthOffset + self.textOffsetDist + 2 * arcSymbRadius
      elif self.arcSymbPos == QadDimStyleArcSymbolPosEnum.ABOVE_TEXT:
         textHeightOffset = textHeightOffset + self.textOffsetDist + arcSymbRadius

      # Restituisce una lista di 4 elementi:
      # - il primo elemento é una lista con il punto di inserimento del testo della quota e la sua rotazione
      # - il secondo elemento é una lista con flag che indica il tipo della linea sulla quale é stato messo il testo; vedi QadDimComponentEnum
      #                       e una lista di linee "leader" nel caso il testo sia all'esterno della quota
      # - il terzo elemento é la rotazione del primo blocco delle frecce; può essere None se non visibile
      # - il quarto elemento é la rotazione del secondo blocco delle frecce; può essere None se non visibile      
      dummy1, dummy2, block1Rot, block2Rot = self.getArcTextAndBlocksPosition(dimArc, dimLineArc1, \
                                                                              textWidthOffset, textHeightOffset)
      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # trovo il vero punto di inserimento del testo tenendo conto del buffer intorno
      if self.arcSymbPos == QadDimStyleArcSymbolPosEnum.BEFORE_TEXT:
         textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist + self.textOffsetDist + 2 * arcSymbRadius)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)
      else:
         textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
         textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)

      # testo
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)

      # blocchi frecce
      block1Feature = self.getSymbolFeature(dimLineArc1StartPt, block1Rot, True, textLinearDimComponentOn) # True = primo punto di quotatura
      block2Feature = self.getSymbolFeature(dimLineArc1EndPt, block2Rot, False, textLinearDimComponentOn) # False = secondo punto di quotatura   
            
      extLine1 = self.getExtLine(dimPt1, dimLineArc1StartPt)
      extLine2 = self.getExtLine(dimPt2, dimLineArc1EndPt)
      
      # creo un rettangolo intorno al testo con un offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)
      
      if textLinearDimComponentOn == QadDimComponentEnum.DIM_LINE1: # linea di quota ("Dimension line")
         dimLineArc1, dimLineArc2 = self.adjustArcAccordingTextRect(textOffsetRect, dimLineArc1, QadDimComponentEnum.DIM_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE1: # prima linea di estensione ("Extension line 1")
         if extLine1 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt1, dimLineArc1StartPt)
            extLine1 = self.getExtLine(dimPt1, qad_utils.getPolarPointByPtAngle(dimLineArc1StartPt, extLineRot, textWidth + self.textOffsetDist))
            # cambio il verso della linea perché getExtLine restituisce una linea dalla linea di quota verso il punto di quotatura       
            reverseExtLine1 = extLine1.copy().reverse()            
            extLine1, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine1, QadDimComponentEnum.EXT_LINE1)
      elif textLinearDimComponentOn == QadDimComponentEnum.EXT_LINE2: # seconda linea di estensione ("Extension line 2")
         if extLine2 is not None:
            extLineRot = qad_utils.getAngleBy2Pts(dimPt2, dimLineArc1EndPt)
            extLine2 = self.getExtLine(dimPt2, qad_utils.getPolarPointByPtAngle(dimLineArc1EndPt, extLineRot, textWidth + self.textOffsetDist))            
            # cambio il verso della linea perché getExtLine restituisce una linea dalla linea di quota verso il punto di quotatura
            reverseExtLine2 = extLine2.copy().reverse()
            extLine2, dummy = self.adjustLineAccordingTextRect(textOffsetRect, reverseExtLine2, QadDimComponentEnum.EXT_LINE2)
      elif textLinearDimComponentOn == QadDimComponentEnum.LEADER_LINE: # linea porta quota usata quando il testo é fuori dalla quota ("Leader")
         lastLine = txtLeaderLines.getLinearObjectAt(-1)
         lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
         txtLeaderLines.remove(-1) # sostituisco l'ultimo elemento
         txtLeaderLines.append(lastLine)
      
      # linee di quota
      if dimLineArc1 is None:
         dimLine1Feature = None
      else:
         dimLine1Feature = self.getDimLineFeature(dimLineArc1, True, textLinearDimComponentOn) # True = prima linea di quota

      if dimLineArc2 is None:
         dimLine2Feature = None
      else:
         dimLine2Feature = self.getDimLineFeature(dimLineArc2, False, textLinearDimComponentOn) # False = seconda linea di quota

      # estensioni delle linee di quota
      dimArcExt1, dimArcExt2 = self.getDimArcExtensions(dimLineArc1, dimLineArc2)
      if dimArcExt1 is None:
         dimLineExt1Feature = None
      else:
         dimLineExt1Feature = self.getDimLineExtFeature(dimArcExt1, True)

      if dimArcExt2 is None:
         dimLineExt2Feature = None
      else:
         dimLineExt2Feature = self.getDimLineExtFeature(dimArcExt2, False)      

      # linee di estensione
      extLine1Feature = self.getExtLineFeature(extLine1, True)  # True = prima linea di estensione
      extLine2Feature = self.getExtLineFeature(extLine2, False) # False = seconda linea di estensione

      # linea di leader
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines, QadDimComponentEnum.ARC_LEADER_LINE)


      # linea di arc leader
      arcLeaderLineFeature  = None
      arcLeaderBlockFeature = None
      if arcLeader: # se si vuole la linea che congiunge il testo all'arco da quotare
         arcLeaderLine = self.getArcLeaderLine(textOffsetRectInsPt, dimArc)
         if arcLeaderLine is not None:
            arcLeaderLines = QadPolyline()
            arcLeaderLines.append(arcLeaderLine)
            arcLeaderLineFeature = self.getLeaderFeature(arcLeaderLines)
            arcLeaderBlockFeature = self.getLeaderSymbolFeature(arcLeaderLine.getEndPt(), \
                                                                arcLeaderLine.getTanDirectionOnPt())
      # simbolo dell'arco
      arcSymbolLineFeature = None
      if self.arcSymbPos == QadDimStyleArcSymbolPosEnum.BEFORE_TEXT:
         arc = QadArc()
         arcPt1 = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, - self.textOffsetDist)
         arcCenter = qad_utils.getPolarPointByPtAngle(arcPt1, textRot, - arcSymbRadius)
         arcPt2 = qad_utils.getPolarPointByPtAngle(arcCenter, textRot, - arcSymbRadius)
         arc.fromStartCenterEndPts(arcPt1, arcCenter, arcPt2)
         arcSymbolLineFeature = self.getArcSymbolLineFeature(arc)
      elif self.arcSymbPos == QadDimStyleArcSymbolPosEnum.ABOVE_TEXT:
         arc = QadArc()
         arcCenter = qad_utils.getPolarPointByPtAngle(textInsPt, textRot, textWidth / 2)
         arcCenter = qad_utils.getPolarPointByPtAngle(arcCenter, textRot + math.pi / 2, arcSymbRadius + self.textOffsetDist)
         arcPt1 = qad_utils.getPolarPointByPtAngle(arcCenter, textRot, arcSymbRadius)
         arcPt2 = qad_utils.getPolarPointByPtAngle(arcCenter, textRot, - arcSymbRadius)
         arc.fromStartCenterEndPts(arcPt1, arcCenter, arcPt2)
         arcSymbolLineFeature = self.getArcSymbolLineFeature(arc)
      
      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLine1Feature is not None:
         dimEntity.linearFeatures.append(dimLine1Feature)
      if dimLine2Feature is not None:
         dimEntity.linearFeatures.append(dimLine2Feature)
         
      if dimLineExt1Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt1Feature)
      if dimLineExt2Feature is not None:
         dimEntity.linearFeatures.append(dimLineExt2Feature)
         
      if extLine1Feature is not None:
         dimEntity.linearFeatures.append(extLine1Feature)
      if extLine2Feature is not None:
         dimEntity.linearFeatures.append(extLine2Feature)
         
      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      if arcLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(arcLeaderLineFeature)
      if arcSymbolLineFeature is not None:
         dimEntity.linearFeatures.append(arcSymbolLineFeature)         
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if block1Feature is not None:
         dimEntity.symbolFeatures.append(block1Feature)
      if block2Feature is not None:
         dimEntity.symbolFeatures.append(block2Feature)
      if arcLeaderBlockFeature is not None:
         dimEntity.symbolFeatures.append(arcLeaderBlockFeature)
      
      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addArcDimToLayers
   # ============================================================================
   def addArcDimToLayers(self, plugIn, dimArc, linePosPt, measure = None, arcLeader = False):
      """
      dimArc = arco da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      measure = indica se la misura é predeterminata oppure (se = None) deve essere calcolata
      arcLeader = indica se si deve disegnare la linea direttrice dalla quota all'arco

      Aggiunge ai layers le features che compongono una quota allineata.
      """
      dimEntity, textOffsetRect = self.getArcDimFeatures(plugIn.canvas, \
                                                         dimArc, \
                                                         linePosPt, \
                                                         measure, \
                                                         arcLeader)

      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNZIONI PER LA QUOTATURA ARCO - FINE
   # FUNZIONI PER LA QUOTATURA RAGGIO - INIZIO
   # ============================================================================


   # ============================================================================
   # getCenterMarkerLinesFeature
   # ============================================================================
   def getCenterMarkerLinesFeature(self, canvas, dimObj, linePosPt):
      """
      center = punto del centro dell'arco o del cerchio da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      Restituisce una lista di feature che rappresentano del linee di marker del centro
      """
      if self.centerMarkSize == 0.0: # 0 = niente
         return []
      # se linePosPos è < del raggio non si deve inserire il marker del centro
      if qad_utils.getDistance(dimObj.center , linePosPt) < dimObj.radius:
         return []

      geoms = []
      if self.centerMarkSize > 0.0: # dimensione marcatore di centro
         horizLine = QadLine().set(QgsPointXY(dimObj.center.x() - self.centerMarkSize, dimObj.center.y()), \
                                   QgsPointXY(dimObj.center.x() + self.centerMarkSize, dimObj.center.y()))
         geoms.append(horizLine)
         
         vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() - self.centerMarkSize), \
                                  QgsPointXY(dimObj.center.x(), dimObj.center.y() + self.centerMarkSize))
         geoms.append(vertLine)
      else: # dimensione linee d'asse
         centerMarkSize = -self.centerMarkSize
         
         horizLine = QadLine().set(QgsPointXY(dimObj.center.x() - centerMarkSize, dimObj.center.y()), \
                                   QgsPointXY(dimObj.center.x() + centerMarkSize, dimObj.center.y()))
         geoms.append(horizLine)
         
         vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() - centerMarkSize), \
                                  QgsPointXY(dimObj.center.x(), dimObj.center.y() + centerMarkSize))
         geoms.append(vertLine)
         
         if (2 * centerMarkSize) < dimObj.radius:
            horizLine = QadLine().set(QgsPointXY(dimObj.center.x() - (2 * centerMarkSize), dimObj.center.y()), \
                                      QgsPointXY(dimObj.center.x() - dimObj.radius - centerMarkSize, dimObj.center.y()))
            geoms.append(horizLine)
            
            horizLine = QadLine().set(QgsPointXY(dimObj.center.x() + (2 * centerMarkSize), dimObj.center.y()), \
                                      QgsPointXY(dimObj.center.x() + dimObj.radius + centerMarkSize, dimObj.center.y()))
            geoms.append(horizLine)

            vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() - (2 * centerMarkSize)), \
                                     QgsPointXY(dimObj.center.x(), dimObj.center.y() - dimObj.radius - centerMarkSize))
            geoms.append(vertLine)

            vertLine = QadLine().set(QgsPointXY(dimObj.center.x(), dimObj.center.y() + (2 * centerMarkSize)), \
                                     QgsPointXY(dimObj.center.x(), dimObj.center.y() + dimObj.radius + centerMarkSize))
            geoms.append(vertLine)

      features = []
      for g in geoms:
         f = QgsFeature(self.getLinearFeaturePrototype())
         f.setGeometry(fromQadGeomToQgsGeom(g, self.getLinearLayer())) # trasformo la geometria

         try:
            # imposto il tipo di componente della quotatura
            if len(self.componentFieldName) > 0:
               f.setAttribute(self.componentFieldName, QadDimComponentEnum.CENTER_MARKER_LINE)
         except:
            pass
       
         try:
            # imposto il tipo di linea
            if len(self.lineTypeFieldName) > 0:
               f.setAttribute(self.lineTypeFieldName, self.dimLineLineType)         
         except:
            pass

         try:
            # imposto il colore
            if len(self.colorFieldName) > 0:
               f.setAttribute(self.colorFieldName, self.dimLineColor)         
         except:
            pass

         features.append(f)
      
      return features


   # ============================================================================
   # getRadiusDimFeatures
   # ============================================================================
   def getRadiusDimFeatures(self, canvas, dimObj, linePosPt, measure = None):
      """
      dimObj = oggetto arco circle da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      measure = indica se la misura é predeterminata oppure (se = None) deve essere calcolata
      
      # quota raggio per misurare la lunghezza di un raggio di arco o di cerchio
      # ritorna una lista di elementi che descrivono la geometria della quota:
      # 1 lista = feature del primo e del secondo punto di quota; QgsFeature 1, QgsFeature 2
      # 2 lista = feature della prima e della seconda linea di quota (quest'ultima può essere None); QgsFeature 1, QgsFeature 2
      # 3 lista = feature del punto del testo di quota e geometria del rettangolo di occupazione; QgsFeature, QgsGeometry
      # 4 lista = feature del primo e del secondo simbolo per la linea di quota (possono essere None); QgsFeature 1, QgsFeature 2
      # 5 lista = feature della prima e della seconda linea di estensione (possono essere None); QgsFeature 1, QgsFeature 2
      # 6 elemento = feature della linea di leader (può essere None); QgsFeature
      """
      self.dimType = QadDimTypeEnum.RADIUS

      # marker del centro
      dimCenterMarkers = self.getCenterMarkerLinesFeature(canvas, dimObj, linePosPt)

      # punti di quotatura
      dimPt1 = dimObj.center
      angle = qad_utils.getAngleBy2Pts(dimPt1, linePosPt) 
      dimPt2 = qad_utils.getPolarPointByPtAngle(dimPt1, angle, dimObj.radius) # punto sulla curva

      dimPt1Feature = self.getDimPointFeature(dimPt1, True) # True = primo punto di quotatura
      dimPt2Feature = self.getDimPointFeature(dimPt2, False) # False = secondo punto di quotatura   

      # se il blocco di quota 1 e il blocco di quota 2 sono visibili
      if self.block1Name != "" and self.block1Name != "":
         blockRot = qad_utils.getAngleBy2Pts(linePosPt, dimPt2)
         if qad_utils.getDistance(linePosPt, dimPt2) <= 2 * self.getBlock2Size():
            linePosPt = qad_utils.getPolarPointByPtAngle(dimPt2, blockRot + math.pi, 2 * self.getBlock2Size())
         # blocco freccia
         blockFeature = self.getSymbolFeature(dimPt2, blockRot, \
                                              True if self.block1Name != "" else False, \
                                              QadDimComponentEnum.LEADER_LINE)
      else:
         blockFeature = None

      # linea di quota
      dimLine = QadLine().set(linePosPt, dimPt2)
      # la linea di quota 1 o la linea di quota 2 devono essere visibile
      if self.dimLine1Show == True or self.dimLine2Show == True:
         dimLineFeature = self.getDimLineFeature(dimLine, self.dimLine1Show, QadDimComponentEnum.LEADER_LINE)
      else: # la linea di quota è invisibile
         dimLineFeature = None

      # linea di estensione
      extLineFeature = None
      if dimObj.whatIs() == "ARC":
         extArc = self.getExtArc(dimObj, linePosPt)
         # linee di estensione
         if extArc is not None:
            extLineFeature = self.getExtLineFeature(extArc, True)  # True = prima linea di estensione

      # testo e blocchi
      if measure is None:
         textValue = QadMsg.translate("Command_DIM", "R") + self.getFormattedText(dimObj.radius) # antepongo la R di Radius
      else:
         textValue = unicode(measure)

      textFeature = self.getTextFeature(textValue)
      textWidth, textHeight = qad_label.calculateLabelSize(self.getTextualLayer(), textFeature, canvas)

      # creo un rettangolo intorno al testo con un buffer = self.textOffsetDist
      textWidthOffset  = textWidth + self.textOffsetDist * 2
      textHeightOffset = textHeight + self.textOffsetDist * 2

      # creo una linea fittizia per il posizionamento del testo
      # la creo lunga metà della lunghezza del testo per forzare il testo fuori dalla linea fittizia
      pt = qad_utils.getPolarPointByPtAngle(linePosPt, angle + math.pi, textWidthOffset / 2)
 
      # Restituisce una lista di 4 elementi:
      # - il primo elemento é una lista con il punto di inserimento del testo della quota e la sua rotazione
      # - il secondo elemento é una lista con flag che indica il tipo della linea sulla quale é stato messo il testo; vedi QadDimComponentEnum
      #                       e una lista di linee "leader" nel caso il testo sia all'esterno della quota
      dummy1, dummy2, block1Rot, block2Rot = self.getRadiusTextAndBlocksPosition(QadLine().set(linePosPt, pt), \
                                                                                 textWidthOffset, textHeightOffset)
      textOffsetRectInsPt = dummy1[0]
      textRot             = dummy1[1]
      textLinearDimComponentOn = dummy2[0]
      txtLeaderLines           = dummy2[1]

      # trovo il vero punto di inserimento del testo tenendo conto del buffer intorno      
      textInsPt = qad_utils.getPolarPointByPtAngle(textOffsetRectInsPt, textRot, self.textOffsetDist)
      textInsPt = qad_utils.getPolarPointByPtAngle(textInsPt, textRot + math.pi / 2, self.textOffsetDist)

      # testo
      textGeom = QgsGeometry.fromPointXY(textInsPt)
      textFeature = self.getTextFeature(textValue, textInsPt, textRot)
      
      # creo un rettangolo intorno al testo con un offset
      textOffsetRect = self.textRectToQadPolyline(textOffsetRectInsPt, textWidthOffset, textHeightOffset, textRot)
      
      lastLine = txtLeaderLines.getLinearObjectAt(-1)
      lastLine, dummy = self.adjustLineAccordingTextRect(textOffsetRect, lastLine, QadDimComponentEnum.LEADER_LINE)
      txtLeaderLines.remove(-1) # sostituisco l'ultimo elemento
      txtLeaderLines.append(lastLine)
      
      # linea di leader
      txtLeaderLineFeature = self.getLeaderFeature(txtLeaderLines)
   
      dimEntity = QadDimEntity()
      dimEntity.dimStyle = self
      # features testuali
      dimEntity.textualFeature = textFeature
      # features lineari
      if dimLineFeature is not None:
         dimEntity.linearFeatures.append(dimLineFeature)
      if extLineFeature is not None:
         dimEntity.linearFeatures.append(extLineFeature)
      if txtLeaderLineFeature is not None:
         dimEntity.linearFeatures.append(txtLeaderLineFeature)
      for dimCenterMarker in dimCenterMarkers:
         dimEntity.linearFeatures.append(dimCenterMarker)
      # features puntuali
      dimEntity.symbolFeatures.extend([dimPt1Feature, dimPt2Feature])
      if blockFeature is not None:
         dimEntity.symbolFeatures.append(blockFeature)
      
      return dimEntity, QgsGeometry.fromPolygonXY([textOffsetRect.asPolyline()])


   # ============================================================================
   # addRadiusDimToLayers
   # ============================================================================
   def addRadiusDimToLayers(self, plugIn, dimObj, linePosPt, measure = None):
      """
      dimObj = oggetto arco circle da quotare (in unita di mappa)
      linePosPt = punto per indicare dove deve essere posizionata la linea di quota (in unita di mappa)
      measure = indica se la misura é predeterminata oppure (se = None) deve essere calcolata

      Aggiunge ai layers le features che compongono una quota allineata.
      """
      dimEntity, textOffsetRect = self.getRadiusDimFeatures(plugIn.canvas, \
                                                            dimObj, \
                                                            linePosPt, \
                                                            measure)

      return self.addDimEntityToLayers(plugIn, dimEntity)


   # ============================================================================
   # FUNZIONI PER LA QUOTATURA RAGGIO - FINE
   # ============================================================================


# ===============================================================================
# QadDimStylesClass list of dimension styles
# ===============================================================================
class QadDimStylesClass():
   
   def __init__(self, dimStyleList = None):
      if dimStyleList is None:
         self.dimStyleList = []
      else:
         self.set(dimStyleList)


   def __del__(self):
      if dimStyleList is None:
         del self.dimStyleList[:]

         
   def isEmpty(self):
      return True if self.count() == 0 else False

         
   def count(self):
      return len(self.dimStyleList)
   

   def clear(self):
      del self.dimStyleList[:] 


   def findDimStyle(self, dimStyleName):
      """
      La funzione, dato un nome di stile di quotatura, lo cerca nella lista e,
      in caso di successo, restituisce lo stile di quotatura.
      """
      for dimStyle in self.dimStyleList:
         if dimStyle.name == dimStyleName:
            return dimStyle
      return None


   def addDimStyle(self, dimStyle, toFile = False, filePath = ""):
      d = self.findDimStyle(dimStyle)
      if d is None: 
         self.dimStyleList.append(QadDimStyle(dimStyle))
         if toFile:
            if dimStyle.save(filePath, False) == False: # senza sovrascrivere file
               return False
         return True
            
      return False     
         

   # ============================================================================
   # removeDimStyle
   # ============================================================================
   def removeDimStyle(self, dimStyleName, toFile = False):
      i = 0
      for dimStyle in self.dimStyleList:
         if dimStyle.name == dimStyleName:
            del self.dimStyleList[i]
            if toFile:
               dimStyle.remove()
            return True
         else:
            i = i + 1
            
      return False
      
      
   # ============================================================================
   # renameDimStyle
   # ============================================================================
   def renameDimStyle(self, dimStyleName, newDimStyleName):
      if dimStyleName == newDimStyleName: # nome uguale
         return True

      if self.findDimStyle(newDimStyleName) is not None:
         return False
      dimStyle = self.findDimStyle(dimStyleName)
      if dimStyle is None:
         return False
      return dimStyle.rename(newDimStyleName)

      
   # ============================================================================
   # load
   # ============================================================================
   def load(self, dir = None, append = False):
      """
      Carica le impostazioni di tutti gli stili di quotatura presenti nella directory indicata.
      se dir = None se esiste un progetto caricato il percorso è quello del progetto altrimenti + il percorso locale di qad
      """
      if dir is None:
         if append == False:
            self.clear()
        
         # se esiste un progetto caricato il percorso è quello del progetto
         prjFileInfo = QFileInfo(QgsProject.instance().fileName())
         path = prjFileInfo.absolutePath()
         if len(path) > 0:
            path += "/;"
         path += QgsApplication.qgisSettingsDirPath() + "python/plugins/qad/"
        
         # lista di directory separate da ";"
         dirList = path.strip().split(";")
         for _dir in dirList:
            self.load(_dir, True) # in append
      else:
         _dir = QDir.cleanPath(dir)
         if _dir == "":
            return False
            
         if _dir.endswith("/") == False:
            _dir = _dir + "/"
            
         if not os.path.exists(_dir):
            return False
         
         if append == False:
            self.clear()
         dimStyle = QadDimStyle()
               
         fileNames = os.listdir(_dir)
         for fileName in fileNames:
            if fileName.endswith(".dim"):
               path = _dir + fileName            
               if dimStyle.load(path) == True:
                  if self.findDimStyle(dimStyle.name) is None:              
                     self.addDimStyle(dimStyle)
               
      return True


   # ============================================================================
   # getDimIdByEntity
   # ============================================================================
   def getDimIdByEntity(self, entity):
      """
      La funzione, data un'entità, verifica se fa parte di uno stile di quotatura della lista e,
      in caso di successo, restituisce lo stile di quotatura e il codice della quotatura altrimenti None, None.
      """
      for dimStyle in self.dimStyleList:
         dimId = dimStyle.getDimIdByEntity(entity)
         if dimId is not None:
            return dimStyle, dimId
      return None, None


   # ============================================================================
   # isDimEntity
   # ============================================================================
   def isDimEntity(self, entity):
      """
      La funzione, data un'entità, verifica se fa parte di uno stile di quotatura della lista e,
      in caso di successo, restituisce true altrimenti False.
      """
      dimStyle, dimId = self.getDimIdByEntity(entity)
      if dimStyle is None or dimId is None:
         return False
      else:
         return True


   # ============================================================================
   # getDimEntity
   # ============================================================================
   def getDimEntity(self, layer, fid = None):
      """
         la funzione può essere richiamata in 2 modi:
         con un solo parametro di tipo QadEntity
         con due parametri, il primo QgsVectorLayer e il secondo l'id della feature
      """
      # verifico se l'entità appartiene ad uno stile di quotatura
      if type(layer) == QgsVectorLayer:
         entity = QadEntity()
         entity.set(layer, fid)
         dimStyle, dimId = self.getDimIdByEntity(entity)
      else: # il parametro layer puo essere un oggetto QadEntity
         dimStyle, dimId = self.getDimIdByEntity(layer)
      
      if (dimStyle is None) or (dimId is None):
         return None
         
      dimEntity = QadDimEntity()
      if dimEntity.initByDimId(dimStyle, dimId) == False:
         return None

      return dimEntity


   # ============================================================================
   # getDimListByLayer
   # ============================================================================
   def getDimListByLayer(self, layer):
      """
      La funzione, dato un layer, verifica se fa parte di uno o più stili di quotatura della lista e,
      in caso di successo, restituisce la lista degli stili di quotatura di appartenenza.
      """
      result = []
      for dimStyle in self.dimStyleList:
         if dimStyle.isDimLayer(layer):
            if dimStyle not in result:
               result.append(dimStyle)

      return result


   # ============================================================================
   # addAllDimComponentsToEntitySet
   # ============================================================================
   def addAllDimComponentsToEntitySet(self, entitySet, onlyEditableLayers):
      """
      La funzione verifica se le entità che fanno parte di un entitySet sono anche parte di quotatura e,
      in caso affermativo, aggiunge tutti i componenti della quotatura all'entitySet.
      """
      elaboratedDimEntitySet = QadEntitySet() # lista delle entità di quota elaborate
      entity = QadEntity()
      for layerEntitySet in entitySet.layerEntitySetList:
         # verifico se il layer appartiene ad uno o più stili di quotatura
         dimStyleList = self.getDimListByLayer(layerEntitySet.layer)
         for dimStyle in dimStyleList: # per tutti gli stili di quotatura
            if dimStyle is not None:
               remove = False
               if onlyEditableLayers == True:
                  # se anche un solo layer non é modificabile 
                  if dimStyle.getTextualLayer().isEditable() == False or \
                     dimStyle.getSymbolLayer().isEditable() == False or \
                     dimStyle.getLinearLayer().isEditable() == False:
                     remove = True
               features = layerEntitySet.getFeatureCollection()
               for feature in features:
                  entity.set(layerEntitySet.layer, feature.id())
                  if not elaboratedDimEntitySet.containsEntity(entity):                  
                     dimId = dimStyle.getDimIdByEntity(entity)
                     if dimId is not None:
                        dimEntitySet = dimStyle.getEntitySet(dimId)
                        if remove == False:
                           entitySet.unite(dimEntitySet)
                        else:
                           entitySet.subtract(dimEntitySet)
                        
                        elaboratedDimEntitySet.unite(dimEntitySet)


   # ============================================================================
   # removeAllDimLayersFromEntitySet
   # ============================================================================
   def removeAllDimLayersFromEntitySet(self, entitySet):
      """
      La funzione rimuove tutte le entità che fanno parte di quotature dall'entitySet.
      """
      for dimStyle in self.dimStyleList:
         entitySet.removeLayerEntitySet(dimStyle.getTextualLayer())
         entitySet.removeLayerEntitySet(dimStyle.getSymbolLayer())
         entitySet.removeLayerEntitySet(dimStyle.getLinearLayer())


# ===============================================================================
# QadDimEntity dimension entity class
# ===============================================================================
class QadDimEntity():

   # ============================================================================
   # __init__
   # ============================================================================
   def __init__(self, dimEntity = None):
      self.dimStyle = None
      self.textualFeature = None
      self.linearFeatures = []
      self.symbolFeatures = []
      
      if dimEntity is not None:
         self.set(dimEntity)

         
   def whatIs(self):
      return "DIMENTITY"


   def isInitialized(self):
      if (self.dimStyle is None) or (self.textualFeature is None):
         return False
      else:
         return True


   def __eq__(self, dimEntity):
      """self == other"""
      if self.isInitialized() == False or dimEntity.isInitialized() == False :
         return False

      if self.getTextualLayer() == dimEntity.getTextualLayer() and self.getDimId() == dimEntity.getDimId():
         return True
      else:
         return False    


   # ============================================================================
   # isValid
   # ============================================================================
   def isValid(self):
      """
      Verifica se lo stile di quotatura é valido e in caso affermativo ritorna True.
      Se la quotatura non é valida ritorna False.
      """
      if self.dimStyle is None:
         return False
      return self.dimStyle.isValid()


   # ============================================================================
   # getTextualLayer
   # ============================================================================
   def getTextualLayer(self):
      if self.dimStyle is None:
         return None
      return self.dimStyle.getTextualLayer()
         
                  
   # ============================================================================
   # getLinearLayer
   # ============================================================================
   def getLinearLayer(self):
      if self.dimStyle is None:
         return None
      return self.dimStyle.getLinearLayer()
         
                  
   # ============================================================================
   # getSymbolLayer
   # ============================================================================
   def getSymbolLayer(self):
      if self.dimStyle is None:
         return None
      return self.dimStyle.getSymbolLayer()
         
      
   # ============================================================================
   # set
   # ============================================================================
   def set(self, dimEntity):
      self.dimStyle = QadDimStyle(dimEntity.dimStyle)
      
      self.textualFeature = QgsFeature(dimEntity.textualFeature)

      del self.linearFeatures[:]
      for f in dimEntity.linearFeatures:
         self.linearFeatures.append(QgsFeature(f))

      del self.symbolFeatures[:]
      for f in dimEntity.symbolFeatures:
         self.symbolFeatures.append(QgsFeature(f))


   # ============================================================================
   # getLinearGeometryCollection
   # ============================================================================
   def getLinearGeometryCollection(self):
      result = []
      for f in self.linearFeatures:
         result.append(f.geometry())
      return result

         
   # ============================================================================
   # getSymbolGeometryCollection
   # ============================================================================
   def getSymbolGeometryCollection(self):
      result = []
      for f in self.symbolFeatures:
         result.append(f.geometry())
      return result


   # ============================================================================
   # getDimId
   # ============================================================================
   def getDimId(self):
      """
      La funzione restituisce il codice della quotatura altrimenti None.
      """
      try:
         return self.textualFeature.attribute(self.idFieldName)
      except:
         return None      


   def recodeDimIdToFeature(self, newDimId):
      try:
         # imposto il codice della quota
         self.textualFeature.setAttribute(self.dimStyle.idFieldName, newDimId)
         for f in self.linearFeatures:
            f.setAttribute(self.dimStyle.idParentFieldName, newDimId)
         for f in self.symbolFeatures:
            f.setAttribute(self.dimStyle.idParentFieldName, newDimId)
      except:
         return False

      return True
   
   
   # ============================================================================
   # addToLayers
   # ============================================================================
   def addToLayers(self, plugIn):
      # prima di tutto inserisco il testo di quota per ricodificare la quotatura
      # plugIn, layer, feature, coordTransform, refresh, check_validity
      if qad_layer.addFeatureToLayer(plugIn, self.getTextualLayer(), self.textualFeature, None, False, False, False) == False:
         return False
      newDimId = self.textualFeature.id()
         
      if self.recodeDimIdToFeature(newDimId) == False:
         return False

      # plugIn, layer, feature, refresh, check_validity
      if qad_layer.updateFeatureToLayer(plugIn, self.getTextualLayer(), self.textualFeature, False, False) == False:
         return False
      # plugIn, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getLinearLayer(), self.linearFeatures, None, False, False) == False:  
         return False
      # plugIn, layer, features, coordTransform, refresh, check_validity
      if qad_layer.addFeaturesToLayer(plugIn, self.getSymbolLayer(), self.symbolFeatures, None, False, False) == False:  
         return False
      
      return True
   
   
   # ============================================================================
   # deleteToLayers
   # ============================================================================
   def deleteToLayers(self, plugIn):
      ids =[]

      # plugIn, layer, featureId, refresh
      if qad_layer.deleteFeatureToLayer(plugIn, self.getTextualLayer(), self.textualFeature.id(), False) == False:
         return False
      
      for f in self.linearFeatures:
         ids.append(f.id())
      # plugIn, layer, featureIds, refresh
      if qad_layer.deleteFeaturesToLayer(plugIn, self.getLinearLayer(), ids, False) == False:
         return False
      
      del ids[:]
      for f in self.symbolFeatures:
         ids.append(f.id())
      # plugIn, layer, featureIds, refresh
      if qad_layer.deleteFeaturesToLayer(plugIn, self.getSymbolLayer(), ids, False) == False:
         return False
      
      return True
      
      
   # ============================================================================
   # initByEntity
   # ============================================================================
   def initByEntity(self, dimStyle, entity):
      dimId = dimStyle.getDimIdByEntity(entity)
      if dimId is None:
         return False
      return self.initByDimId(dimStyle, dimId)


   # ============================================================================
   # initByDimId
   # ============================================================================
   def initByDimId(self, dimStyle, dimId):      
      self.dimStyle = QadDimStyle(dimStyle)
      entitySet = self.dimStyle.getEntitySet(dimId)
      if entitySet.count() == 0: return False

      self.textualFeature = None
      layerEntitySet = entitySet.findLayerEntitySet(self.getTextualLayer())
      if layerEntitySet is not None:
         features = layerEntitySet.getFeatureCollection()
         self.textualFeature = features[0]
      
      # entità lineari
      layerEntitySet = entitySet.findLayerEntitySet(self.getLinearLayer())
      del self.linearFeatures[:] # svuoto la lista
      if layerEntitySet is not None:
         self.linearFeatures = layerEntitySet.getFeatureCollection()
      
      # entità puntuali
      layerEntitySet = entitySet.findLayerEntitySet(self.getSymbolLayer())
      del self.symbolFeatures[:] # svuoto la lista
      if layerEntitySet is not None:
         self.symbolFeatures = layerEntitySet.getFeatureCollection()
   
      return True


   # ============================================================================
   # getEntitySet
   # ============================================================================
   def getEntitySet(self):      
      result = QadEntitySet()
      
      if self.isValid() == False: return result;

      layerEntitySet = QadLayerEntitySet()
      layerEntitySet.set(self.getTextualLayer(), [self.textualFeature])
      result.addLayerEntitySet(layerEntitySet)

      layerEntitySet = QadLayerEntitySet()
      layerEntitySet.set(self.getLinearLayer(), self.linearFeatures)
      result.addLayerEntitySet(layerEntitySet)
      
      layerEntitySet = QadLayerEntitySet()
      layerEntitySet.set(self.getSymbolLayer(), self.symbolFeatures)
      result.addLayerEntitySet(layerEntitySet)
      
      return result
   

   # ============================================================================
   # selectOnLayer
   # ============================================================================
   def selectOnLayer(self, incremental = True):
      self.getEntitySet().selectOnLayer(incremental)
   

   # ============================================================================
   # deselectOnLayer
   # ============================================================================
   def deselectOnLayer(self):
      self.getEntitySet().deselectOnLayer()

   
   # ============================================================================
   # getDimPts
   # ============================================================================
   def getDimPts(self, destinationCrs = None):
      """
      destinationCrs = sistema di coordinate in cui verrà restituito il risultato
      """
            
      dimPt1 = None
      dimPt2 = None

      if len(self.dimStyle.componentFieldName) > 0:
         # cerco tra gli elementi puntuali
         for f in self.symbolFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               if value == QadDimComponentEnum.DIM_PT1: # primo punto da quotare ("Dimension point 1")
                  g = f.geometry()
                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                        destinationCrs,
                                                        QgsProject.instance())) # trasformo la geometria in map coordinate
                  
                  dimPt1 = g.asPoint()
               elif value == QadDimComponentEnum.DIM_PT2: # secondo punto da quotare ("Dimension point 2")
                  g = f.geometry()
                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                         destinationCrs,
                                                         QgsProject.instance())) # trasformo la geometria in map coordinate
                  
                  dimPt2 = g.asPoint()
            except:
               return None, None

      return QadPoint(dimPt1), QadPoint(dimPt2)      


   # ============================================================================
   # getDimLinePts
   # ============================================================================
   def getDimLinePts(self, destinationCrs = None):
      """
      destinationCrs = sistema di coordinate in cui verrà restituito il risultato
      """
      dimLinePt1 = None
      dimLinePt2 = None
      # cerco i punti iniziale-finale della linea di quota
      if len(self.dimStyle.componentFieldName) > 0:
         # prima cerco tra gli elementi lineari
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               # primo punto da quotare ("Dimension point 1") o secondo punto da quotare ("Dimension point 2")
               if value == QadDimComponentEnum.DIM_LINE1 or value == QadDimComponentEnum.DIM_LINE2:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getLinearLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # trasformo la geometria in map coordinate

                  pts = qad_utils.asPointOrPolyline(g)[0].asPolyline()
                  if value == QadDimComponentEnum.DIM_LINE1:
                     dimLinePt1 = pts[0]
                  else:
                     dimLinePt2 = pts[-1]
                  
            except:
               return None, None
         
         if dimLinePt1 is None or dimLinePt2 is None:
            # poi cerco tra gli elementi puntuali
            for f in self.symbolFeatures:
               try:
                  value = f.attribute(self.dimStyle.componentFieldName)
                  # primo blocco della freccia ("Block 1")
                  if dimLinePt1 is None and value == QadDimComponentEnum.BLOCK1:
                     g = f.geometry()
   
                     if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                        g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                           destinationCrs, \
                                                           QgsProject.instance())) # trasformo la geometria in map coordinate
                     
                     dimLinePt1 = g.asPoint()
                     
                  # secondo blocco della freccia ("Block 2")
                  if dimLinePt2 is None and value == QadDimComponentEnum.BLOCK2:
                     g = f.geometry()
   
                     if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                        g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                           destinationCrs, \
                                                           QgsProject.instance())) # trasformo la geometria in map coordinate
                     
                     dimLinePt2 = g.asPoint()
                     
               except:
                  return None, None

      return dimLinePt1, dimLinePt2


   # ============================================================================
   # getDimArc
   # ============================================================================
   def getDimArc(self, destinationCrs = None):
      """
      destinationCrs = sistema di coordinate in cui verrà restituito il risultato
      """
      # cerco i punti di quotatura
      dimPt1, dimPt2 = self.getDimPts(destinationCrs)
      if dimPt1 is None or dimPt2 is None: return None

      # cerco il punto iniziale e finale della linea di quota
      dimLinePt1, dimLinePt2 = self.getDimLinePts(destinationCrs)
      if dimLinePt1 is None or dimLinePt2 is None: return None

      ang1 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(dimPt1, dimLinePt1))
      ang2 = qad_utils.normalizeAngle(qad_utils.getAngleBy2Pts(dimLinePt2, dimPt2))
      if qad_utils.TanDirectionNear(ang1, ang2) == True: # arco di 180 gradi
         ptCenter = qad_utils.getMiddlePoint(dimPt1, dimPt2)
      else:
         ptCenter = qad_utils.getIntersectionPointOn2InfinityLines(dimPt1, dimLinePt1, dimPt2, dimLinePt2)
      
      arc = QadArc()
      if arc.fromStartCenterEndPts(dimPt1, ptCenter, dimPt2) == False:
         return None
      
      return arc


   # ============================================================================
   # getDimLeaderLine
   # ============================================================================
   def getDimLeaderLine(self, leaderLineType = None, destinationCrs = None):
      """
      Trova la linea porta quota del tipo indicato (in destinationCrs tipicamente = map coordinate)
      destinationCrs = sistema di coordinate in cui è espresso containerGeom e in cui verrà restituito il risultato
      """
      if len(self.dimStyle.componentFieldName) > 0:
         # prima cerco tra gli elementi lineari
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               if value == leaderLineType:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getLinearLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # trasformo la geometria in map coordinate

                  return qad_utils.asPointOrPolyline(g)[0].asPolyline()
            except:
               return None
            
      return None


   # ============================================================================
   # getDimLinePosPt
   # ============================================================================
   def getDimLinePosPt(self, containerGeom = None, destinationCrs = None):
      """
      Trova fra i vari punti possibili un punto che indichi dove si trova la linea di quota (in destinationCrs tipicamente = map coordinate)
      se containerGeom <> None il punto deve essere contenuto in containerGeom
      containerGeom = può essere una QgsGeometry rappresentante un poligono (in destinationCrs tipicamente = map coordinate) contenente i punti di geom da stirare
                      oppure una lista dei punti da stirare (in destinationCrs tipicamente = map coordinate)
      destinationCrs = sistema di coordinate in cui è espresso containerGeom e in cui verrà restituito il risultato
      """
      
      if len(self.dimStyle.componentFieldName) > 0:
         # prima cerco tra gli elementi lineari
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               # primo punto da quotare ("Dimension point 1") o secondo punto da quotare ("Dimension point 2")
               if value == QadDimComponentEnum.DIM_LINE1 or value == QadDimComponentEnum.DIM_LINE2:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getLinearLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # trasformo la geometria in map coordinate

                  pts = qad_utils.asPointOrPolyline(g)[0].asPolyline()
                  if containerGeom is not None: # verifico che il punto iniziale sia interno a containerGeom
                     if type(containerGeom) == QgsGeometry: # geometria   
                        if containerGeom.contains(pts[0]) == True:
                           return QadPoint(pts[0])
                        else:
                           # verifico che il punto finale sia interno a containerGeom
                           if containerGeom.contains(pts[-1]) == True:
                              return QadPoint(pts[-1])
                     elif type(containerGeom) == list: # lista di punti
                        for containerPt in containerGeom:
                           if qad_utils.ptNear(containerPt, pts[0]): # se i punti sono sufficientemente vicini
                              return QadPoint(pts[0])
                           else:
                              # verifico il punto finale
                              if qad_utils.ptNear(containerPt,pts[-1]):
                                 return QadPoint(pts[-1])
                  else:
                     return QadPoint(pts[0]) # punto iniziale
            except:
               return None
            
         # poi cerco tra gli elementi puntuali
         for f in self.symbolFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               # primo blocco della freccia ("Block 1") o secondo blocco della freccia ("Block 2")
               if value == QadDimComponentEnum.BLOCK1 or value == QadDimComponentEnum.BLOCK2:
                  g = f.geometry()

                  if (destinationCrs is not None) and destinationCrs != self.getSymbolLayer().crs():
                     g.transform(QgsCoordinateTransform(self.getSymbolLayer().crs(), \
                                                        destinationCrs, \
                                                        QgsProject.instance())) # trasformo la geometria in map coordinate
                  
                  dimLinePosPt = g.asPoint()
                  if containerGeom is not None: # verifico che il punto sia interno a containerGeom
                     if type(containerGeom) == QgsGeometry: # geometria   
                        if containerGeom.contains(dimLinePosPt) == True:
                           return QadPoint(dimLinePosPt)
                     elif type(containerGeom) == list: # lista di punti
                        for containerPt in containerGeom:
                           if ptNear(containerPt, dimLinePosPt): # se i punti sono sufficientemente vicini
                              return QadPoint(dimLinePosPt)
                  else:
                     return QadPoint(dimLinePosPt)
            except:
               return None

      return None


   # ============================================================================
   # getDimLinearAlignment
   # ============================================================================
   def getDimLinearAlignment(self):
      dimLinearAlignment = None
      dimLineRotation = None
      Pts = []
   
      if len(self.dimStyle.componentFieldName) > 0:
         # prima cerco tra gli elementi lineari
         for f in self.linearFeatures:
            try:
               value = f.attribute(self.dimStyle.componentFieldName)
               if value == QadDimComponentEnum.DIM_LINE1: # primo punto da quotare ("Dimension point 1")
                  Pts = qad_utils.asPointOrPolyline(f.geometry())[0].asPolyline()
                  break
               elif value == QadDimComponentEnum.DIM_LINE2: # secondo punto da quotare ("Dimension point 2")
                  Pts = qad_utils.asPointOrPolyline(f.geometry())[0].asPolyline()
                  break
            except:
               return None, None

         if Pts is None:
            # poi cerco tra gli elementi puntuali
            for f in self.symbolFeatures:
               try:
                  value = f.attribute(self.dimStyle.componentFieldName)
                  if value == QadDimComponentEnum.BLOCK1: # primo blocco della freccia ("Block 1")
                     Pts.append(f.geometry().asPoint())
                  elif value == QadDimComponentEnum.BLOCK2: # secondo blocco della freccia ("Block 1")
                     Pts.append(f.geometry().asPoint())
               except:
                  return None, None
      
      if len(Pts) > 1: # almeno 2 punti     
         if qad_utils.doubleNear(Pts[0].x(), Pts[-1].x()): # linea verticale (stessa x)
            dimLinearAlignment = QadDimStyleAlignmentEnum.VERTICAL
            dimLineRotation = 0
         elif qad_utils.doubleNear(Pts[0].y(), Pts[-1].y()): # linea orizzontale (stessa y)
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            dimLineRotation = 0
         else:
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            dimLineRotation = qad_utils.getAngleBy2Pts(Pts[0], Pts[-1])
            
      
      return dimLinearAlignment, dimLineRotation


   # ============================================================================
   # getDimCircle
   # ============================================================================
   def getDimCircle(self, destinationCrs = None):
      """
      destinationCrs = sistema di coordinate in cui verrà restituito il risultato
      Ritorna un cerchio a cui si riferisce la quotatura DIMRADIUS
      """      
      # cerco i punti di quotatura
      dimPt1, dimPt2 = self.getDimPts(destinationCrs)
      if dimPt1 is None or dimPt2 is None: return None

      circle = QadCircle()
      circle.center = dimPt1
      circle.radius = qad_utils.getDistance(dimPt1, dimPt2)
      
      return circle


   # ============================================================================
   # getTextRot
   # ============================================================================
   def getTextRot(self):
      textRot = None
   
      if len(self.dimStyle.rotFieldName) > 0:
         try:
            textRot = self.textualFeature.attribute(self.dimStyle.rotFieldName)
         except:
            return None

      return qad_utils.toRadians(textRot)


   # ============================================================================
   # getTextValue
   # ============================================================================
   def getTextValue(self):
      textValue = None

      if self.dimStyle.getTextualLayer() is None:
         return None;

      # se il testo dipende da un solo campo
      labelFieldNames = qad_label.get_labelFieldNames(self.dimStyle.getTextualLayer())
      if len(labelFieldNames) == 1 and len(labelFieldNames[0]) > 0:
         try:
            textValue = self.textualFeature.attribute(labelFieldNames[0])
         except:
            return None

      return textValue


   # ============================================================================
   # getTextPt
   # ============================================================================
   def getTextPt(self, destinationCrs = None):
      # destinationCrs = sistema di coordinate in cui verrà restituito il risultato
      g = self.textualFeature.geometry()
      if (destinationCrs is not None) and destinationCrs != self.getTextualLayer().crs():
         g.transform(QgsCoordinateTransform(self.getTextualLayer().crs(), \
                                            destinationCrs,
                                            QgsProject.instance())) # trasformo la geometria in map coordinate
      
      return g.asPoint()


   # ============================================================================
   # isCalculatedText
   # ============================================================================
   def isCalculatedText(self):
      # la funzione verifica se il testo della quota è calcolato dalla grafica o se è stato forzato un testo diverso
      measure = self.getTextValue()
      
      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # quota lineare allineata ai punti di origine delle linee di estensione
         dimPt1, dimPt2 = self.getDimPts()     
         return measure == self.dimStyle.getFormattedText(qad_utils.getDistance(dimPt1, dimPt2))
      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # quota lineare con una linea di quota orizzontale o verticale
         dimPt1, dimPt2 = self.getDimPts()
         linePosPt = self.getDimLinePosPt()
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()
 
         # linea di quota entro le linee di estensione
         dimLine = self.dimStyle.getDimLine(dimPt1, dimPt2, linePosPt, preferredAlignment, dimLineRotation)
         if dimLine is None: return False
         return measure == self.dimStyle.getFormattedText(dimLine.length())
      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # quota per la lunghezza di un arco
         dimArc = self.getDimArc()
         if dimArc is None: return False
         return measure == self.dimStyle.getFormattedText(dimArc.length())
      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # quota radiale, misura il raggio di un cerchio o di un arco
         dimPt1, dimPt2 = self.getDimPts()
         return measure == self.dimStyle.getFormattedText(qad_utils.getDistance(dimPt1, dimPt2))

      return True


   # ============================================================================
   # isCalculatedTextRot
   # ============================================================================
   def isCalculatedTextRot(self):
      # la funzione verifica se la rotazione del testo della quota è calcolato dalla grafica o se è stato forzato una rotazione diversa
      measure = self.getTextValue()
      txtRot = self.getTextRot()
      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # quota lineare allineata ai punti di origine delle linee di estensione
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            return txtRot == dimEntity.getTextRot()
         
      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # quota lineare con una linea di quota orizzontale o verticale
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (dimLinearAlignment is not None) and (dimLineRotation is not None):

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            
            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            return txtRot == dimEntity.getTextRot()
         
      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # quota per la lunghezza di un arco
         dimArc = self.getDimArc()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimArc is not None) and (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, dimArc, linePosPt, measure)
            return txtRot == dimEntity.getTextRot()

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # quota radiale, misura il raggio di un cerchio o di un arco
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            return txtRot == dimEntity.getTextRot()

      return True


   # ============================================================================
   # move
   # ============================================================================
   def move(self, offsetX, offsetY):
      # offsetX = spostamento X in map coordinate
      # offsetY = spostamento Y in map coordinate
      if self.isValid() == False: return False;

      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()
      
      g = self.textualFeature.geometry()
      qadGeom = fromQgsGeomToQadGeom(g, self.getTextualLayer().crs())
      qadGeom.move(offsetX, offsetY)
      g = fromQadGeomToQgsGeom(qadGeom, self.getTextualLayer())
      self.textualFeature.setGeometry(g)

      for f in self.linearFeatures:
         g = f.geometry()
         qadGeom = fromQgsGeomToQadGeom(g, self.getLinearLayer().crs())
         qadGeom.move(offsetX, offsetY)
         g = fromQadGeomToQgsGeom(qadGeom, self.getLinearLayer())
         f.setGeometry(g)

      for f in self.symbolFeatures:
         g = f.geometry()
         qadGeom = fromQgsGeomToQadGeom(g, self.getSymbolLayer().crs())
         qadGeom.move(offsetX, offsetY)
         g = fromQadGeomToQgsGeom(qadGeom, self.getSymbolLayer())
         f.setGeometry(g)
      
      return False

      
   # ============================================================================
   # rotate
   # ============================================================================
   def rotate(self, basePt, angle):
      # basePt = punto base espresso in map coordinate
      if self.isValid() == False: return False;
      
      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()
      
      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()
      
      if textRot is not None: # se la rotazione era forzata allora la imposto
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot
      
      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # quota lineare allineata ai punti di origine delle linee di estensione
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimPt1 = qad_utils.rotatePoint(dimPt1, basePt, angle)
            dimPt2 = qad_utils.rotatePoint(dimPt2, basePt, angle)              
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)

            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)
            
      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # quota lineare con una linea di quota orizzontale o verticale
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (preferredAlignment is not None) and (dimLineRotation is not None):
            dimPt1 = qad_utils.rotatePoint(dimPt1, basePt, angle)
            dimPt2 = qad_utils.rotatePoint(dimPt2, basePt, angle)              
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)              
            dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            dimLineRotation = dimLineRotation + angle
            
            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # quota per la lunghezza di un arco
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimArc is not None) and (linePosPt is not None):
            dimArc.rotate(basePt, angle)
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # quota radiale, misura il raggio di un cerchio o di un arco
         # non si può fare perchè non si può sapere se la quota si riferiva ad un cerchio o ad un arco
         # al momento ipotizzo si riferisca sempre ad un cerchio
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimCircle.rotate(basePt, angle)
            linePosPt = qad_utils.rotatePoint(linePosPt, basePt, angle)
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # ripristino la situazione precedente

      return True
   

   # ============================================================================
   # scale
   # ============================================================================
   def scale(self, basePt, scale):
      # basePt = punto base espresso in map coordinate
      if self.isValid() == False: return False;
      
      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()
      
      if textRot is not None: # se la rotazione era forzata allora la imposto
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot
      
      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # quota lineare allineata ai punti di origine delle linee di estensione
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimPt1 = qad_utils.scalePoint(dimPt1, basePt, scale)
            dimPt2 = qad_utils.scalePoint(dimPt2, basePt, scale)              
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)
                          
            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)
            
      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # quota lineare con una linea di quota orizzontale o verticale
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (preferredAlignment is not None) and (dimLineRotation is not None):
            textForcedRot = self.getTextRot()
            if textForcedRot is not None:
               self.dimStyle.textForcedRot = textForcedRot

            dimPt1 = qad_utils.scalePoint(dimPt1, basePt, scale)
            dimPt2 = qad_utils.scalePoint(dimPt2, basePt, scale)              
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)              
            dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL

            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # quota per la lunghezza di un arco
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimArc is not None) and \
            (linePosPt is not None):
            dimArc.scale(basePt, scale)
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # quota radiale, misura il raggio di un cerchio o di un arco
         # non si può fare perchè non si può sapere se la quota si riferiva ad un cerchio o ad un arco
         # al momento ipotizzo si riferisca sempre ad un cerchio
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimCircle.scale(basePt, scale)
            linePosPt = qad_utils.scalePoint(linePosPt, basePt, scale)
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # ripristino la situazione precedente

      return True
   
   
   # ============================================================================
   # mirror
   # ============================================================================
   def mirror(self, mirrorPt, mirrorAngle):
      # mirrorPt = punto base espresso in map coordinate
      if self.isValid() == False: return False;
      
      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()

      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()
      
      if textRot is not None: # se la rotazione era forzata allora la imposto
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot
            
      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # quota lineare allineata ai punti di origine delle linee di estensione
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimPt1 = qad_utils.mirrorPoint(dimPt1, mirrorPt, mirrorAngle)
            dimPt2 = qad_utils.mirrorPoint(dimPt2, mirrorPt, mirrorAngle)              
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)
                          
            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)
            
      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # quota lineare con una linea di quota orizzontale o verticale
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         preferredAlignment, dimLineRotation = self.getDimLinearAlignment()
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (preferredAlignment is not None) and (dimLineRotation is not None):
            textForcedRot = self.getTextRot()
            if textForcedRot is not None:
               self.dimStyle.textForcedRot = textForcedRot

            dimPt1 = qad_utils.mirrorPoint(dimPt1, mirrorPt, mirrorAngle)
            dimPt2 = qad_utils.mirrorPoint(dimPt2, mirrorPt, mirrorAngle)              
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)              
            dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()

            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            
            ptDummy = qad_utils.getPolarPointByPtAngle(mirrorPt, dimLineRotation, 1)
            ptDummy = qad_utils.mirrorPoint(ptDummy, mirrorPt, mirrorAngle)
            dimLineRotation = qad_utils.getAngleBy2Pts(mirrorPt, ptDummy)            

            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # quota per la lunghezza di un arco
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(None, destinationCrs)
         if (dimArc is not None) and \
            (linePosPt is not None):
            dimArc.mirror(mirrorPt, mirrorAngle)
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # quota radiale, misura il raggio di un cerchio o di un arco
         # non si può fare perchè non si può sapere se la quota si riferiva ad un cerchio o ad un arco
         # al momento ipotizzo si riferisca sempre ad un cerchio
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(None, destinationCrs)

         if (dimCircle is not None) and (linePosPt is not None):
            dimCircle.mirror(mirrorPt, mirrorAngle)
            linePosPt = qad_utils.mirrorPoint(linePosPt, mirrorPt, mirrorAngle)
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # ripristino la situazione precedente

      return True
   
   
   # ============================================================================
   # stretch
   # ============================================================================
   def stretch(self, containerGeom, offsetX, offsetY):
      """
      containerGeom = può essere una QgsGeometry rappresentante un poligono contenente i punti di geom da stirare
                      oppure una lista dei punti da stirare espressi in map coordinate
      offsetX = spostamento X in map coordinate
      offsetY = spostamento Y in map coordinate
      """
      if self.isValid() == False: return False;
      
      canvas = qgis.utils.iface.mapCanvas()
      destinationCrs = canvas.mapSettings().destinationCrs()
      
      measure = None if self.isCalculatedText() else self.getTextValue()
      textRot = None if self.isCalculatedTextRot() else self.getTextRot()
      
      if textRot is not None: # se la rotazione era forzata allora la imposto
         prevTextRotMode = self.dimStyle.textRotMode
         self.dimStyle.textRotMode = QadDimStyleTxtRotModeEnum.FORCED_ROTATION
         self.dimStyle.textForcedRot = textRot
            
      if self.dimStyle.dimType == QadDimTypeEnum.ALIGNED: # quota lineare allineata ai punti di origine delle linee di estensione
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)
         
         if dimPt1 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt1, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt1 = newPt
         
         if dimPt2 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt2, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt2 = newPt

         if linePosPt is not None:
            newPt = qad_stretch_fun.stretchPoint(linePosPt, containerGeom, offsetX, offsetY)
            if newPt is not None:
               linePosPt = newPt
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # verifico se è stato coinvolto il testo della quota
            if qad_stretch_fun.isPtContainedForStretch(self.getTextPt(destinationCrs), containerGeom):
               if linePosPt is not None:
                  linePosPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)
         
         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getAlignedDimFeatures(canvas, \
                                                                            dimPt1, \
                                                                            dimPt2, \
                                                                            linePosPt, \
                                                                            measure)
            self.set(dimEntity)
            
      elif self.dimStyle.dimType == QadDimTypeEnum.LINEAR: # quota lineare con una linea di quota orizzontale o verticale
         dimPt1, dimPt2 = self.getDimPts(destinationCrs)
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)
         
         dimLinearAlignment, dimLineRotation = self.getDimLinearAlignment()
         
         if dimPt1 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt1, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt1 = newPt
               
         if dimPt2 is not None:
            newPt = qad_stretch_fun.stretchPoint(dimPt2, containerGeom, offsetX, offsetY)
            if newPt is not None:
               dimPt2 = newPt

         if linePosPt is not None:
            newPt = qad_stretch_fun.stretchPoint(linePosPt, containerGeom, offsetX, offsetY)
            if newPt is not None:
               linePosPt = newPt
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # verifico se è stato coinvolto il testo della quota
            if qad_stretch_fun.isPtContainedForStretch(self.getTextPt(destinationCrs), containerGeom):
               if linePosPt is not None:
                  linePosPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)

         if (dimPt1 is not None) and (dimPt2 is not None) and \
            (linePosPt is not None) and \
            (dimLinearAlignment is not None) and (dimLineRotation is not None):
            if dimLinearAlignment == QadDimStyleAlignmentEnum.VERTICAL:
               dimLineRotation = math.pi / 2
            dimLinearAlignment = QadDimStyleAlignmentEnum.HORIZONTAL
            
            dimEntity, textOffsetRect = self.dimStyle.getLinearDimFeatures(canvas, \
                                                                           dimPt1, \
                                                                           dimPt2, \
                                                                           linePosPt, \
                                                                           measure, \
                                                                           dimLinearAlignment, \
                                                                           dimLineRotation)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.ARC_LENTGH: # quota per la lunghezza di un arco
         dimArc = self.getDimArc(destinationCrs)
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)
         
         if dimArc is not None:
            dimArc = qad_stretch_fun.stretchQadGeometry(dimArc, containerGeom, \
                                                        offsetX, offsetY)

         if linePosPt is not None:
            newPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)
            linePosPt = qad_utils.getPolarPointBy2Pts(dimArc.center, linePosPt, qad_utils.getDistance(dimArc.center, newPt))
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # verifico se è stato coinvolto il testo della quota
            textPt = self.getTextPt(destinationCrs)
            if qad_stretch_fun.isPtContainedForStretch(textPt, containerGeom):
               if linePosPt is not None:
                  newPt = qad_utils.movePoint(textPt, offsetX, offsetY)
                  linePosPt = qad_utils.getPolarPointBy2Pts(dimArc.center, linePosPt, qad_utils.getDistance(dimArc.center, newPt))
      
         if (dimArc is not None) and \
            (linePosPt is not None):
            arcLeader = True if self.getDimLeaderLine(QadDimComponentEnum.ARC_LEADER_LINE) is not None else False

            dimEntity, textOffsetRect = self.dimStyle.getArcDimFeatures(canvas, \
                                                                        dimArc, \
                                                                        linePosPt, \
                                                                        measure, \
                                                                        arcLeader)
            self.set(dimEntity)

      elif self.dimStyle.dimType == QadDimTypeEnum.RADIUS: # quota radiale, misura il raggio di un cerchio o di un arco
         # non si può fare perchè non si può sapere se la quota si riferiva ad un cerchio o ad un arco
         # al momento ipotizzo si riferisca sempre ad un cerchio
         dimCircle = self.getDimCircle()
         linePosPt = self.getDimLinePosPt(containerGeom, destinationCrs)
         
         if type(containerGeom) == list: # lista di punti
            for containerPt in containerGeom:
               # whereIsPt ritorna -1 se il punto è interno, 0 se è sulla circonferenza, 1 se è esterno
               if dimCircle.whereIsPt(containerPt) == 0:
                  linePosPt = None # sposto il punto che era sulla circonferenza
         
         if dimCircle is not None:
            dimCircle = qad_stretch_fun.stretchQadGeometry(dimCircle, containerGeom, \
                                                           offsetX, offsetY)

         if linePosPt is not None:
            newPt = qad_utils.movePoint(linePosPt, offsetX, offsetY)
            linePosPt = qad_utils.getPolarPointBy2Pts(dimCircle.center, linePosPt, qad_utils.getDistance(dimCircle.center, newPt))
         else:
            linePosPt = self.getDimLinePosPt(None, destinationCrs)
            # verifico se è stato coinvolto il testo della quota
            textPt = self.getTextPt(destinationCrs)
            if qad_stretch_fun.isPtContainedForStretch(textPt, containerGeom):
               if linePosPt is not None:
                  newPt = qad_utils.movePoint(textPt, offsetX, offsetY)
                  linePosPt = qad_utils.getPolarPointBy2Pts(dimCircle.center, linePosPt, qad_utils.getDistance(dimCircle.center, newPt))

         if (dimCircle is not None) and (linePosPt is not None):
            dimEntity, textOffsetRect = self.dimStyle.getRadiusDimFeatures(canvas, dimCircle, linePosPt, measure)
            self.set(dimEntity)

      if textRot is not None:
         self.dimStyle.textRotMode = prevTextRotMode # ripristino la situazione precedente

      return True;


   # ============================================================================
   # getDimComponentByEntity
   # ============================================================================
   def getDimComponentByEntity(self, entity):
      """
      La funzione, data un'entità, restituisce il componente della quotatura.
      """
      if entity.layer == self.getTextualLayer():
         return QadDimComponentEnum.TEXT_PT
      elif entity.layer == self.getLinearLayer() or \
           entity.layer == self.getSymbolLayer():
         try:
            return entity.getFeature().attribute(self.dimStyle.componentFieldName)
         except:
            return None
         
      return None


# ============================================================================
# appendDimEntityIfNotExisting
# ============================================================================
def appendDimEntityIfNotExisting(dimEntityList, dimEntity):
   """
   La funzione è di utilità nei comandi per evitare di elaborare più volte oggetti appartenenti a quotatura
   dimEntityList è da dichiarare come una lista semplice (es. dimElaboratedList = [])
   La funzione cerca in dimEntityList se esiste dimEntity, in caso affermativo ritorna False 
   altrimenti aggiunge alla lista dimEntity e ritorna True
   """
   for item in dimEntityList:
      if item == dimEntity: return False
   dimEntityList.append(dimEntity)
   return True


# ===============================================================================
#  = variabile globale
# ===============================================================================

QadDimStyles = QadDimStylesClass()                 # lista degli stili di quotatura caricati