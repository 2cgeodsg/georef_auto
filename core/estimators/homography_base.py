from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Sequence, Tuple, Optional
import numpy as np
import cv2

@dataclass(frozen=True)
class Ponto2D:
    x: float
    y: float

@dataclass(frozen=True)
class ParCorrespondencia:
    """Par de pontos correspondentes (imagem_origem -> imagem_referencia)."""
    origem: Ponto2D
    referencia: Ponto2D

@dataclass(frozen=True)
class ResultadoHomografia:
    H: Optional[np.ndarray]                # (3x3) ou None
    mascara_inliers: Optional[np.ndarray]  # shape (N,1) de 0/1
    n_inliers: int
    n_corresp: int
    metodo: str                            # ex.: "RANSAC"
    reproj_thresh: float                   # limiar usado (px)
    confidence: float 
    mensagem: str                          # log amigável

class HomographyEstimator(Protocol):
    """Contrato para estimadores de homografia."""
    def estimate(self, correspondencias: Sequence[ParCorrespondencia]) -> ResultadoHomografia:
        ...
