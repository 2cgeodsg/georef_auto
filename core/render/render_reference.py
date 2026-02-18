# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from ...dependencies import numpy as np
from ...dependencies import cv2
from ...dependencies import rasterio
from datetime import datetime
from typing import Tuple, Optional

from rasterio.transform import from_bounds

from qgis.core import (
    QgsRectangle,
    QgsMapSettings,
    QgsMapRendererCustomPainterJob,
    QgsCoordinateTransform,
    QgsProject,
    QgsGeometry,
)
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtCore import QSize, Qt

import traceback
from ...utils.logger import logger

from ..config import GeoreferencingConfig


def _salvar_geotiff_temporario(
    img_clahe: np.ndarray,
    bounds: QgsRectangle,
    layer_crs_authid: str,
    width: int,
    height: int,
    debug_output_dir: Optional[str] = None,
) -> str:
    """
    Salva a imagem processada (grayscale/CLAHE) como GeoTIFF temporário georreferenciado.
    """
    # Mantém compatibilidade com seu caminho atual, mas permite sobrescrever por argumento.
    if debug_output_dir is None:
        debug_output_dir = r"C:\logsgeoref"
    os.makedirs(debug_output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_filename = f"wms_ref_{timestamp}.tif"
    debug_path = os.path.join(debug_output_dir, debug_filename)

    transform = from_bounds(
        bounds.xMinimum(), bounds.yMinimum(),
        bounds.xMaximum(), bounds.yMaximum(),
        width, height
    )

    with rasterio.open(
        debug_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=img_clahe.dtype,
        crs=layer_crs_authid,
        transform=transform,
        compress='LZW'
    ) as dst:
        dst.write(img_clahe, 1)

    logger.info(f"GeoTIFF da referência salvo em: {debug_path}")
    return debug_path


def _transformar_poligono_para_crs_da_layer(polygon_geom: QgsGeometry, layer) -> QgsGeometry:
    """
    Reprojeta o polígono do CRS do projeto para o CRS da layer (se necessário).
    """
    layer_crs = layer.crs()
    proj_crs = QgsProject.instance().crs()

    if layer_crs.authid() == proj_crs.authid():
        return QgsGeometry(polygon_geom)  # cópia

    xform = QgsCoordinateTransform(proj_crs, layer_crs, QgsProject.instance().transformContext())
    poly = QgsGeometry(polygon_geom)
    poly.transform(xform)  # in-place
    return poly


def _qimage_to_bgr(img: QImage) -> np.ndarray:
    """
    Converte QImage para np.ndarray BGR de forma segura:
    - normaliza para RGB888 (3 bytes/px),
    - respeita bytesPerLine (stride),
    - retorna C-contíguo com memória própria (copy).
    """
    img2 = img.convertToFormat(QImage.Format_RGB888)
    w, h = img2.width(), img2.height()
    stride = img2.bytesPerLine()  # pode ser > w*3 por padding

    ptr = img2.bits()
    ptr.setsize(stride * h)

    # buffer -> (h, stride) -> corta padding -> (h, w, 3)
    arr = np.frombuffer(ptr, np.uint8).reshape(h, stride)
    rgb = arr[:, : w * 3].reshape(h, w, 3)

    # converte para BGR e faz cópia para memória própria, C-contíguo
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr.copy()


def render_reference_image(
    layer,
    polygon_geom: QgsGeometry,
    config: GeoreferencingConfig,
    debug_output_dir: Optional[str] = None
) -> Tuple[Optional[np.ndarray], Optional[QgsRectangle], Optional[str], Optional[str]]:
    """
    Renderiza a seção da layer definida pelo polígono para uma imagem BGR (np.ndarray),
    retornando também o bounding box (QgsRectangle), o EPSG (string sem 'EPSG:') e o
    caminho do GeoTIFF temporário salvo (com CLAHE), para depuração.

    Retorna: (rgb_bgr, bounds_layer_crs, epsg_code, debug_geotiff_path)
    Em caso de erro: (None, None, None, None)
    """
    try:
        if not layer or not layer.isValid():
            raise ValueError("Camada de referência inválida.")
        if not polygon_geom or polygon_geom.isEmpty():
            raise ValueError("Geometria do polígono inválida.")

        # 1) Garante que o polígono está no CRS da layer
        poly_layer_crs = _transformar_poligono_para_crs_da_layer(polygon_geom, layer)

        # 2) Extensão no CRS da layer
        bounds = poly_layer_crs.boundingBox()
        if bounds.isEmpty() or bounds.width() == 0 or bounds.height() == 0:
            raise ValueError("Extensão (bounding box) do polígono inválida ou com dimensão zero.")

        # 3) Dimensões de saída
        target_width_px = max(1, int(config.render_width_px))
        target_height_px = max(1, int(round((bounds.height() / bounds.width()) * target_width_px)))

        logger.info(
            "Renderizando área de referência: %s para %dx%d pixels.",
            bounds.toString(), target_width_px, target_height_px
        )

        # 4) Configura o render
        map_settings = QgsMapSettings()
        map_settings.setLayers([layer])
        map_settings.setExtent(bounds)
        map_settings.setOutputSize(QSize(target_width_px, target_height_px))
        map_settings.setDestinationCrs(layer.crs())

        img = QImage(target_width_px, target_height_px, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        painter = QPainter(img)

        job = QgsMapRendererCustomPainterJob(map_settings, painter)
        job.start()
        job.waitForFinished()
        painter.end()

        # 5) Converte para BGR (np.ndarray)
        bgr = _qimage_to_bgr(img)
        if bgr is None or bgr.size == 0:
            raise ValueError("Falha ao converter imagem renderizada para array NumPy.")

        # 6) Cria uma versão grayscale+CLAHE apenas para salvar GeoTIFF de depuração
        img_gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        img_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img_gray)

        debug_path = _salvar_geotiff_temporario(
            img_clahe,
            bounds,
            layer.crs().authid(),
            target_width_px,
            target_height_px,
            debug_output_dir=debug_output_dir
        )

        epsg_code = layer.crs().authid().replace("EPSG:", "")
        return bgr, bounds, epsg_code, debug_path

    except Exception as e:
        logger.error(f"Erro ao renderizar imagem de referência: {e}")
        logger.error(traceback.format_exc())
        return None, None, None, None
