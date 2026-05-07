from ...dependencies import cv2
from ...dependencies import numpy as np
from typing import Tuple, Optional
from .base_transform import BaseTransform
from ...utils.logger import logger

class AffineTransform(BaseTransform):
    def __init__(self):
        self.M: Optional[np.ndarray] = None
        self.reprojection_error: float = float('inf')
        self.condition_number: float = float('inf')

    def estimate(self, pts1: np.ndarray, pts2: np.ndarray) -> bool:
        if pts1.shape[0] < 3 or pts2.shape[0] < 3:
            logger.warning("AffineTransform: pontos insuficientes para estimar transformação afim.")
            return False

        try:
            pts1_flat = pts1.reshape(-1, 2)
            pts2_flat = pts2.reshape(-1, 2)
            self.M = cv2.estimateAffine2D(pts1_flat, pts2_flat)[0]

            if self.M is None:
                logger.warning("AffineTransform: falha ao estimar matriz afim.")
                return False

            pts1_transformed = cv2.transform(pts1.reshape(-1, 1, 2), self.M)
            self.reprojection_error = float(np.mean(np.linalg.norm(pts1_transformed.reshape(-1, 2) - pts2.reshape(-1, 2), axis=1)))
            self.condition_number = float(np.linalg.cond(np.vstack([self.M, [0, 0, 1]])))

            logger.info(f"AffineTransform: M estimada, erro={self.reprojection_error:.2f}, cond={self.condition_number:.2f}")
            return True

        except Exception as e:
            logger.error(f"AffineTransform: erro ao estimar M - {e}")
            self.M = None
            return False

    def apply(self, image: np.ndarray, output_shape: Tuple[int, int]) -> np.ndarray:
        if self.M is None:
            raise ValueError("AffineTransform: matriz afim não definida.")
        return cv2.warpAffine(image, self.M, output_shape)

    def get_matrix(self) -> Optional[np.ndarray]:
        return self.M

    def quality_metrics(self) -> dict:
        return {
            "valid": self.M is not None,
            "reprojection_error": self.reprojection_error,
            "condition_number": self.condition_number
        }
