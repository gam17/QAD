# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QAD Quantum Aided Design plugin

 classe per gestire il map tool in ambito del comando fillet ok
 
                              -------------------
        begin                : 2014-01-31
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


from qgis.core import QgsWkbTypes, QgsGeometry


from .. import qad_utils
from ..qad_snapper import QadSnapTypeEnum
from ..qad_getpoint import QadGetPoint, QadGetPointSelectionModeEnum, QadGetPointDrawModeEnum
from ..qad_rubberband import QadRubberBand
from ..qad_dim import QadDimStyles
from ..qad_fillet_fun import fillet2QadGeometries, filletAllPartsQadPolyline, filletQadPolyline
from ..qad_multi_geom import fromQadGeomToQgsGeom, getQadGeomAt, setQadGeomAt
from ..qad_geom_relations import getQadGeomClosestPart


# ===============================================================================
# Qad_fillet_maptool_ModeEnum class.
# ===============================================================================
class Qad_fillet_maptool_ModeEnum():
   # si richiede la selezione del primo oggetto
   ASK_FOR_FIRST_LINESTRING = 1     
   # si richiede la selezione del secondo oggetto
   ASK_FOR_SECOND_LINESTRING = 2    
   # non si richiede niente
   NONE = 3
   # si richiede la selezione della polilinea
   ASK_FOR_POLYLINE = 4     


# ===============================================================================
# Qad_fillet_maptool class
# ===============================================================================
class Qad_fillet_maptool(QadGetPoint):
    
   def __init__(self, plugIn):
      QadGetPoint.__init__(self, plugIn)

      self.filletMode = 1 # modalità di raccordo; 1=Taglia-estendi, 2=Non taglia-estendi
      self.radius = 0.0
      
      self.layer = None
      self.entity1 = None
      self.atGeom1 = None
      self.atSubGeom1 = None
      self.partAt1 = None
      self.pointAt1 = None

      self.__rubberBand = QadRubberBand(self.canvas)


   def hidePointMapToolMarkers(self):
      QadGetPoint.hidePointMapToolMarkers(self)
      self.__rubberBand.hide()

   def showPointMapToolMarkers(self):
      QadGetPoint.showPointMapToolMarkers(self)
      self.__rubberBand.show()
                             
   def clear(self):
      QadGetPoint.clear(self)
      self.__rubberBand.reset()
      self.mode = None

   def setEntityInfo(self, entity, atGeom, atSubGeom, partAt, pointAt):
      """
      Setta self.entity1, elf.atGeom1, self.atSubGeom1, self.partAt1, self.pointAt1
      """
      self.entity1 = entity
      self.atGeom1 = atGeom
      self.atSubGeom1 = atSubGeom
      self.partAt1 = partAt
      self.pointAt1 = pointAt


   def canvasMoveEvent(self, event):
      QadGetPoint.canvasMoveEvent(self, event)
      
      self.__rubberBand.reset()
      newQadGeom = None
       
      # si richiede la selezione del secondo oggetto
      if self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_SECOND_LINESTRING:
         if self.tmpEntity.isInitialized():
            tmpQadGeom = self.tmpEntity.getQadGeom()
            """
            la funzione ritorna una lista con 
            (<minima distanza>
             <punto più vicino>
             <indice della geometria più vicina>
             <indice della sotto-geometria più vicina>
             <indice della parte della sotto-geometria più vicina>
             <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
             -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
             -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
             )
            """
            res = getQadGeomClosestPart(tmpQadGeom, self.tmpPoint)
            tmpPointAt = res[1]
            tmpAtGeom = res[2]
            tmpAtSubGeom = res[3]
            tmpPartAt = res[4]

            # stessa entità e stessa parte
            if self.entity1.layer.id() == self.tmpEntity.layer.id() and \
               self.entity1.featureId == self.tmpEntity.featureId and \
               self.atGeom1 == tmpAtGeom and self.atSubGeom1 == tmpAtSubGeom:
               # se anche stessa parte
               if self.partAt1 == tmpPartAt: return
               subQadGeom = getQadGeomAt(self.entity1.getQadGeom(),self.atGeom1, self.atSubGeom1)
               if subQadGeom.whatIs() != "POLYLINE": return
               
               if self.tmpShiftKey == True: # tasto shift premuto durante il movimento del mouse
                  # filletMode = 1 # modalità di raccordo; 1=Taglia-estendi
                  # raggio = 0
                  newQadGeom = filletQadPolyline(subQadGeom, self.partAt1, self.pointAt1, tmpPartAt, tmpPointAt, \
                                                 1, 0)
               else:               
                  newQadGeom = filletQadPolyline(subQadGeom, self.partAt1, self.pointAt1, tmpPartAt, tmpPointAt, \
                                                 self.filletMode, self.radius)
      
            # geometrie diverse      
            else:
               if self.tmpShiftKey == True: # tasto shift premuto durante il movimento del mouse
                  # filletMode = 1 # modalità di raccordo; 1=Taglia-estendi
                  # raggio = 0
                  res = fillet2QadGeometries(self.entity1.getQadGeom(), self.atGeom1, self.atSubGeom1, self.partAt1, self.pointAt1, \
                                             tmpQadGeom, tmpAtGeom, tmpAtSubGeom, tmpPartAt, tmpPointAt, \
                                             1, 0)
               else:               
                  res = fillet2QadGeometries(self.entity1.getQadGeom(), self.atGeom1, self.atSubGeom1, self.partAt1, self.pointAt1, \
                                             tmpQadGeom, tmpAtGeom, tmpAtSubGeom, tmpPartAt, tmpPointAt, \
                                             self.filletMode, self.radius)
               if res is None: # raccordo non possibile
                  return
               
               newQadGeom = res[0]
                        
      # si richiede la selezione della polilinea
      elif self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_POLYLINE:
         if self.tmpEntity.isInitialized():
            tmpQadGeom = self.tmpEntity.getQadGeom()
            """
            la funzione ritorna una lista con 
            (<minima distanza>
             <punto più vicino>
             <indice della geometria più vicina>
             <indice della sotto-geometria più vicina>
             <indice della parte della sotto-geometria più vicina>
             <"a sinistra di" se il punto é alla sinista della parte con i seguenti valori:
             -   < 0 = sinistra (per linea, arco o arco di ellisse) o interno (per cerchi, ellissi)
             -   > 0 = destra (per linea, arco o arco di ellisse) o esterno (per cerchi, ellissi)
             )
            """
            res = getQadGeomClosestPart(tmpQadGeom, self.tmpPoint)
            tmpAtGeom = res[2]
            tmpAtSubGeom = res[3]
            tmpSubQadGeom = getQadGeomAt(tmpQadGeom, tmpAtGeom, tmpAtSubGeom).copy()
            if filletAllPartsQadPolyline(tmpSubQadGeom, self.radius):
               newQadGeom = setQadGeomAt(tmpQadGeom, tmpSubQadGeom, tmpAtGeom, tmpAtSubGeom)

      if newQadGeom is not None:
         self.__rubberBand.addGeometry(fromQadGeomToQgsGeom(newQadGeom, self.tmpEntity.layer), self.tmpEntity.layer)
      
    
   def activate(self):
      QadGetPoint.activate(self)            
      self.__rubberBand.show()          

   def deactivate(self):
      try: # necessario perché se si chiude QGIS parte questo evento nonostante non ci sia più l'oggetto maptool !
         QadGetPoint.deactivate(self)
         self.__rubberBand.hide()
      except:
         pass

   def setMode(self, mode):
      self.mode = mode

      # si richiede la selezione del primo oggetto
      # si richiede la selezione del secondo oggetto
      if self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_FIRST_LINESTRING or \
         self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_SECOND_LINESTRING:
         
         if self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_FIRST_LINESTRING:
            self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION)
         else:
            self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)

         # solo layer lineari editabili che non appartengano a quote
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
            if layer.geometryType() == QgsWkbTypes.LineGeometry and layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.setSnapType(QadSnapTypeEnum.DISABLE)
      # non si richiede niente
      elif self.mode == Qad_fillet_maptool_ModeEnum.NONE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.POINT_SELECTION)   
         self.setDrawMode(QadGetPointDrawModeEnum.NONE)
      # si richiede la selezione della polilinea
      elif self.mode == Qad_fillet_maptool_ModeEnum.ASK_FOR_POLYLINE:
         self.setSelectionMode(QadGetPointSelectionModeEnum.ENTITY_SELECTION_DYNAMIC)

         # solo layer lineari o poligono editabili che non appartengano a quote
         layerList = []
         for layer in qad_utils.getVisibleVectorLayers(self.plugIn.canvas): # Tutti i layer vettoriali visibili
            if (layer.geometryType() == QgsWkbTypes.LineGeometry or layer.geometryType() == QgsWkbTypes.PolygonGeometry) and \
               layer.isEditable():
               if len(QadDimStyles.getDimListByLayer(layer)) == 0:
                  layerList.append(layer)
         
         self.layersToCheck = layerList
         self.setSnapType(QadSnapTypeEnum.DISABLE)
