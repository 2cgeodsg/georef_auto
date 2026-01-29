import numpy as np
import cv2
from typing import Optional
from ...utils.logger import logger
from ..evaluators.match_evaluator import MatchEvaluator


class HomographyTransform:
    def __init__(self):
        self.H: Optional[np.ndarray] = None
        self.mask: Optional[np.ndarray] = None
        self.valid: bool = False

    def estimate(self, pts1: np.ndarray, pts2: np.ndarray) -> bool:
        """
        Estima a matriz de homografia entre dois conjuntos de pontos com RANSAC.
        """
        try:
            if pts1.shape[0] < 4 or pts2.shape[0] < 4:
                logger.warning("Pontos insuficientes para estimar homografia.")
                return False

            self.H, self.mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)

            if self.H is not None and self.mask is not None:
                inliers = int(np.sum(self.mask))
                self.valid = inliers >= 4
                logger.info(f"Homografia estimada com {inliers} inliers.")
            else:
                self.valid = False
                logger.warning("Homografia não pôde ser estimada.")

            return self.valid

        except Exception as e:
            logger.error(f"Erro ao estimar homografia: {e}")
            return False

    def get_matrix(self) -> Optional[np.ndarray]:
        return self.H

    def apply(self, image: np.ndarray, dsize: tuple) -> np.ndarray:
        """
        Aplica a transformação de homografia à imagem original.
        """
        if self.H is None:
            raise ValueError("Homografia não estimada.")

        return cv2.warpPerspective(image, self.H, dsize)

    def quality_metrics(self) -> dict:
        """
        Retorna métricas de qualidade da transformação.
        """
        return {
            "inliers": int(np.sum(self.mask)) if self.mask is not None else 0,
            "valid": self.valid
        }