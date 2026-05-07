# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Tuple
from ...dependencies import numpy as np
import logging

logger = logging.getLogger(__name__)

def recortar_bordas_pretas(
    img_bgr: np.ndarray,
    valor_borda: Tuple[int, int, int] = (0, 0, 0)
) -> Tuple[np.ndarray, int, int, int, int]:
    """
    Remove bordas pretas (ou valor especificado) de uma imagem BGR.

    Retorna a imagem recortada e (y_min, x_min, y_max, x_max) no espaço da imagem original.

    Se a imagem inteira for “borda”, retorna a imagem original e o retângulo total.

    Mantém SRP: não conhece CRS nem Rasterio; só pixels.
    """
    if img_bgr.ndim != 3 or img_bgr.shape[2] != 3:
        raise ValueError("Esperada imagem BGR (H,W,3).")

    mask_valida = np.any(img_bgr != valor_borda, axis=2)
    coords = np.argwhere(mask_valida)

    if coords.size == 0:
        logger.warning("Imagem warpada parece vazia; retornando sem recorte.")
        h, w = img_bgr.shape[:2]
        return img_bgr, 0, 0, h - 1, w - 1

    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)
    img_crop = img_bgr[y_min:y_max+1, x_min:x_max+1]
    logger.info("Recorte aplicado: x=[%d,%d], y=[%d,%d], tam=%dx%d",
                x_min, x_max, y_min, y_max, img_crop.shape[1], img_crop.shape[0])
    return img_crop, int(y_min), int(x_min), int(y_max), int(x_max)
