# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per comando SPEZZA per tagliare un oggetto
 
                              -------------------
        begin                : 2019-08-08
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


from .qad_multi_geom import getQadGeomAt, isLinearQadGeom
from .qad_geom_relations import *
           

# ===============================================================================
# breakQadGeometry
# ===============================================================================
def breakQadGeometry(qadGeom, firstPt, secondPt):
   """
   la funzione spezza la geometria in un punto (se <secondPt> = None) o in due punti 
   come fa il trim.
   <qadGeom> = geometria da tagliare
   <firstPt> = primo punto di divisione
   <secondPt> = secondo punto di divisione
   """
   if qadGeom is None: return None
   
   gType = qadGeom.whatIs()
   if gType == "POINT" or gType == "MULTI_POINT":
      return None

   # la funzione ritorna una lista con 
   # (<minima distanza>
   # <punto più vicino>
   # <indice della geometria più vicina>
   # <indice della sotto-geometria più vicina>
   # <indice della parte della sotto-geometria più vicina>
   # <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
   # -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
   # -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
   # )
   result = getQadGeomClosestPart(qadGeom, firstPt)
   myFirstPt = result[1]
   atGeom = result[2]
   atSubGeom = result[3]
   subQadGeom = getQadGeomAt(qadGeom, atGeom, atSubGeom).copy()

   mySecondPt = None
   if secondPt is not None:
      # la funzione ritorna una lista con 
      # (<minima distanza>
      # <punto più vicino>
      # <indice della geometria più vicina>
      # <indice della sotto-geometria più vicina>
      # <indice della parte della sotto-geometria più vicina>
      # <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
      # -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
      # -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
      # )
      result = getQadGeomClosestPart(qadGeom, secondPt)
      mySecondPt = result[1]
      atGeom = result[2]
      atSubGeom = result[3]
      # se le sottogeometrie sono diverse
      if result[2] != atGeom or result[3] != atSubGeom:  return None
   
   if mySecondPt is None or qad_utils.ptNear(myFirstPt, mySecondPt):      
      # divido la polilinea in 2
      if isLinearQadGeom(subQadGeom) == False: return None
      
      dummy = subQadGeom.breakOnPts(myFirstPt, None)
      if dummy is None: return None
      return [dummy[0], dummy[1], atGeom, atSubGeom]
   else: # c'é anche il secondo punto di divisione
      gType = subQadGeom.whatIs()
      if gType == "CIRCLE":
         endAngle = qad_utils.getAngleBy2Pts(subQadGeom.center, myFirstPt)
         startAngle = qad_utils.getAngleBy2Pts(subQadGeom.center, mySecondPt)
         arc = QadArc().set(subQadGeom.center, subQadGeom.radius, startAngle, endAngle)
         return [arc, None, atGeom, atSubGeom]

      elif gType == "ELLIPSE":
         endAngle = qad_utils.getAngleBy3Pts(subQadGeom.majorAxisFinalPt, subQadGeom.center, myFirstPt, False)
         startAngle = qad_utils.getAngleBy3Pts(subQadGeom.majorAxisFinalPt, subQadGeom.center, mySecondPt, False)         
         ellipseArc = QadEllipseArc().set(subQadGeom.center, subQadGeom.majorAxisFinalPt, subQadGeom.axisRatio, startAngle, endAngle)
         return [ellipseArc, None, atGeom, atSubGeom]

      else:
         dummy = subQadGeom.breakOnPts(myFirstPt, mySecondPt)
         return [dummy[0], dummy[1], atGeom, atSubGeom]
         
