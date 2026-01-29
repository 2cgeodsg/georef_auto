# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Tuple
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)

def aplicar_warp_perspective(
    imagem_bgr: np.ndarray,
    H_3x3: np.ndarray,
    largura_ref_px: int,
    altura_ref_px: int,
    interpolacao: int = cv2.INTER_CUBIC,
    borda_valor: Tuple[int, int, int] = (0, 0, 0)
) -> np.ndarray:
    """
    Aplica warpPerspective usando a homografia H na grade da imagem de referência.

    Parâmetros
    ----------
    imagem_bgr : np.ndarray
        Imagem fonte (BGR, uint8).
    H_3x3 : np.ndarray
        Matriz de homografia 3x3.
    largura_ref_px, altura_ref_px : int
        Dimensões alvo (grade da referência).
    interpolacao : int
        Interpolação OpenCV (ex.: cv2.INTER_CUBIC).
    borda_valor : Tuple[int,int,int]
        Valor de preenchimento nas áreas sem dado (BGR).

    Retorna
    -------
    np.ndarray
        Imagem warpada na grade de referência (BGR).
    """
    if H_3x3 is None or H_3x3.shape != (3, 3):
        raise ValueError("H_3x3 inválida para warpPerspective (esperado 3x3).")

    logger.info("Aplicando warpPerspective: ref=%dx%d, interp=%s",
                largura_ref_px, altura_ref_px, interpolacao)
    img_warp = cv2.warpPerspective(
        imagem_bgr, H_3x3,
        (largura_ref_px, altura_ref_px),
        flags=interpolacao,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=borda_valor
    )
    return img_warp

def nome_interpolacao(flag:int) -> str:
    nomes = {
        cv2.INTER_NEAREST: "nearest",
        cv2.INTER_LINEAR: "bilinear",
        cv2.INTER_CUBIC: "cubic",
        cv2.INTER_LANCZOS4: "lanczos4",
    }
    return nomes.get(flag, str(flag))
