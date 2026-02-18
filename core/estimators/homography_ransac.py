from __future__ import annotations
from typing import Sequence, Tuple
from ...dependencies import numpy as np
from ...dependencies import cv2
import logging

from .homography_base import (
    HomographyEstimator, ParCorrespondencia, ResultadoHomografia
)

logger = logging.getLogger(__name__)

class RansacHomographyEstimator(HomographyEstimator):
    """
    Estimador de Homografia com cv2.findHomography(RANSAC).

    Parâmetros
    ----------
    reproj_threshold_px : float
        Limiar do erro de reprojeção em pixels (define inlier).
    confidence : float
        Confiança (0-1) para o RANSAC.
    """
    def __init__(self, reproj_threshold_px: float = 5.0, confidence: float = 0.995):
        self.reproj_threshold_px = float(reproj_threshold_px)
        self.confidence = float(confidence)

    def _to_arrays(self, pares: Sequence[ParCorrespondencia]) -> Tuple[np.ndarray, np.ndarray]:
        pts_src = np.float32([[p.origem.x,     p.origem.y]     for p in pares]).reshape(-1, 1, 2)
        pts_dst = np.float32([[p.referencia.x, p.referencia.y] for p in pares]).reshape(-1, 1, 2)
        return pts_src, pts_dst

    def estimate(self, pares: Sequence[ParCorrespondencia]) -> ResultadoHomografia:
        n = len(pares)
        if n < 4:
            msg = f"Necessário >=4 correspondências; recebido: {n}."
            logger.warning(msg)
            return ResultadoHomografia(
                H=None, mascara_inliers=None, n_inliers=0, n_corresp=n,
                metodo="RANSAC", reproj_thresh=self.reproj_threshold_px,
                confidence=self.confidence, mensagem=msg
            )

        pts_src, pts_dst = self._to_arrays(pares)
        H, mask = cv2.findHomography(
            pts_src, pts_dst,
            method=cv2.RANSAC,
            ransacReprojThreshold=self.reproj_threshold_px,
            confidence=self.confidence
        )

        if H is None or mask is None:
            msg = "Homografia não pôde ser estimada com RANSAC."
            logger.warning(msg)
            return ResultadoHomografia(
                H=None, mascara_inliers=None, n_inliers=0, n_corresp=n,
                metodo="RANSAC", reproj_thresh=self.reproj_threshold_px,
                confidence=self.confidence, mensagem=msg
            )

        n_inliers = int(mask.sum())
        msg_ok = f"Homografia estimada. Inliers: {n_inliers}/{n} (thr={self.reproj_threshold_px}px; conf={self.confidence})."
        logger.info(msg_ok)
        return ResultadoHomografia(
            H=H, mascara_inliers=mask, n_inliers=n_inliers, n_corresp=n,
            metodo="RANSAC", reproj_thresh=self.reproj_threshold_px,
            confidence=self.confidence, mensagem=msg_ok
        )
