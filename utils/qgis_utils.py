from qgis.core import (
    QgsRectangle, QgsMapSettings, QgsMapRendererCustomPainterJob,
    QgsCoordinateReferenceSystem, QgsDistanceArea,
    QgsCoordinateTransform, QgsRasterLayer, QgsProject,
    QgsUnitTypes, QgsGeometry, QgsPointXY,
    QgsMapLayerType, QgsVectorLayer,
    QgsFeatureRequest, QgsCoordinateTransformContext
)
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QImage, QPainter, QColor, QPixmap
import os
import logging
from ..dependencies import numpy as np

from .logger import logger

def is_geographic_crs(epsg_code: str) -> bool:
    try:
        crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg_code}")
        return crs.isGeographic()
    except Exception as e:
        logger.error(f"Erro ao verificar CRS: {e}")
        return False

def get_area_in_square_km(geometry: QgsGeometry, crs_authid: str) -> float:
    """
    Retorna a área do 'geometry' em km², de forma consistente:
      - CRS projetado: área planar (metros²) → km²
      - CRS geográfico: área elipsoidal (precisa) → km²
    Sem aproximações via bbox.

    Params
    ------
    geometry : QgsGeometry (espera polígono/multipolígono, mas mede o que vier)
    crs_authid : str, ex: "EPSG:3857" ou "EPSG:4326"

    Returns
    -------
    float : área em km² (0.0 em caso de erro/geometry vazio)
    """
    try:
        crs = QgsCoordinateReferenceSystem(crs_authid)
        if not crs.isValid():
            logging.warning(f"CRS inválido para cálculo de área: {crs_authid}")
            return 0.0
        if not crs.isGeographic():
            area = QgsDistanceArea()
            area.setSourceCrs(crs, QgsProject.instance().transformContext())
            area.setEllipsoid(crs.ellipsoidAcronym())
            return area.measureArea(geometry) / 1e6
        else:
            logging.warning("Calculando área aproximada para CRS geográfico.")
            bbox = geometry.boundingBox()
            center_lat = bbox.center().y()
            km_per_lon_degree = 111.32 * np.cos(np.radians(center_lat))
            width_km = bbox.width() * km_per_lon_degree
            height_km = bbox.height() * 111.1
            return width_km * height_km
    except Exception as e:
        logging.error(f"Erro no cálculo de área: {e}")
        return 0.0




def add_raster_layer_to_qgis(file_path: str, layer_name: str):
    """Adds a raster layer to QGIS."""
    if not os.path.exists(file_path):
        logger.error(f"Arquivo não encontrado: {file_path}")
        return False

    rlayer = QgsRasterLayer(file_path, layer_name)

    if not rlayer.isValid():
        logger.error(f"Camada raster inválida: {layer_name} ({file_path})")
        return False

    QgsProject.instance().addMapLayer(rlayer)
    logger.info(f"Camada raster adicionada: {layer_name}")
    return True


def get_qgis_layers():
    """Returns a list of all valid QGIS map layers."""
    return [layer for layer in QgsProject.instance().mapLayers().values() if layer.isValid()]


def is_layer_suitable_for_reference(layer):
    """
    Check if a layer is suitable to be used as a reference layer.
    
    Args:
        layer: The layer to check
        
    Returns:
        bool: True if the layer is suitable, False otherwise
    """
    if not layer or not layer.isValid():
        return False
        
    layer_type = layer.type()
    
    if layer_type == QgsMapLayerType.RasterLayer:
        return True
        
    if layer_type == QgsMapLayerType.VectorLayer:
        if layer.crs().isValid():
            return True
        else:
            return False
            
    return False


