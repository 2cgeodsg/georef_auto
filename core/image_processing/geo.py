# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ExtensaoGeo:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

def calcular_resolucao_ref(bounds_crop, largura_ref_px: int, altura_ref_px: int) -> Tuple[float, float]:
    """
    Calcula a resolução da referência (unidade CRS/pixel) a partir do QgsRectangle de recorte.
    """
    x_res = bounds_crop.width() / float(largura_ref_px)
    y_res = bounds_crop.height() / float(altura_ref_px)
    logger.debug("Resolução ref: x_res=%.6f, y_res=%.6f", x_res, y_res)
    return x_res, y_res

def calcular_extensao_recorte(
    bounds_crop,
    x_min_px: int, y_min_px: int, x_max_px: int, y_max_px: int,
    x_res_ref: float, y_res_ref: float
) -> ExtensaoGeo:
    """
    Converte o retângulo de recorte (em pixels da grade de referência) para extensão geográfica (CRS da referência).
    O referencial do raster é: origem no canto superior esquerdo.
    """
    nova_xmin = bounds_crop.xMinimum() + x_min_px * x_res_ref
    nova_xmax = bounds_crop.xMinimum() + (x_max_px + 1) * x_res_ref  # +1 por “inclusive”
    nova_ymax = bounds_crop.yMaximum() - y_min_px * y_res_ref
    nova_ymin = bounds_crop.yMaximum() - (y_max_px + 1) * y_res_ref

    ext = ExtensaoGeo(xmin=nova_xmin, ymin=nova_ymin, xmax=nova_xmax, ymax=nova_ymax)
    logger.info("Extensão geo recorte: xmin=%.6f ymin=%.6f xmax=%.6f ymax=%.6f",
                ext.xmin, ext.ymin, ext.xmax, ext.ymax)
    return ext
