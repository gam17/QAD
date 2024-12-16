# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 funzioni per stirare oggetti grafici
 
                              -------------------
        begin                : 2013-11-11
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
from qgis.PyQt.QtGui  import *
from qgis.core import *


from . import qad_utils
from .qad_msg import QadMsg
from .qad_variables import QadVariables
from .qad_multi_geom import *


# ===============================================================================
# buffer
# ===============================================================================
def buffer(qadGeom, distance):
   """
   Returns a buffer region around this geometry having the given distance.
   """
   g = qadGeom.asGeom()
   nSegments = QadVariables.get(QadMsg.translate("Environment variables", "ARCMINSEGMENTQTY"), 12)
   bufferedGeom = g.buffer(distance, nSegments)
   if bufferedGeom.isEmpty(): return None
   return fromQgsGeomToQadGeom(bufferedGeom)
   