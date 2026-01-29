import cv2
import numpy as np
from typing import Tuple, Optional
from .base_transform import BaseTransform
from ...utils.logger import logger

class ThinPlateSplineTransform(BaseTransform):
    def __init__(self):
        self.tps: Optional[cv2.detail_TransformEstimator] = None
        self.src_points: Optional[np.ndarray] = None
        self.dst_points: Optional[np.ndarray] = None
        self.reprojection_error: float = float('inf')

    def estimate(self, pts1: np.ndarray, pts2: np.ndarray) -> bool:
        if pts1.shape[0] < 3 or pts2.shape[0] < 3:
            logger.warning("ThinPlateSplineTransform: pontos insuficientes para estimar TPS.")
            return False

        try:
            self.src_points = pts1.reshape(-1, 2).astype(np.float32)
            self.dst_points = pts2.reshape(-1, 2).astype(np.float32)
            self.tps = cv2.createThinPlateSplineShapeTransformer()
            matches = [cv2.DMatch(i, i, 0) for i in range(len(self.src_points))]
            self.tps.estimateTransformation(self.dst_points, self.src_points, matches)

            warped_src = self.src_points.reshape(-1, 1, 2).copy()
            warped_dst = self.tps.applyTransformation(warped_src)

            self.reprojection_error = float(np.mean(np.linalg.norm(warped_dst.reshape(-1, 2) - self.dst_points, axis=1)))

            logger.info(f"ThinPlateSplineTransform: transformação estimada com erro médio de reprojeção {self.reprojection_error:.2f}.")
            return True

        except Exception as e:
            logger.error(f"ThinPlateSplineTransform: erro ao estimar TPS - {e}")
            self.tps = None
            return False

    def apply(self, image: np.ndarray, output_shape: Tuple[int, int]) -> np.ndarray:
        if self.tps is None:
            raise ValueError("ThinPlateSplineTransform: transformação não definida.")

        h, w = output_shape[1], output_shape[0]
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        grid = np.stack([grid_x, grid_y], axis=-1).astype(np.float32).reshape(-1, 1, 2)

        transformed = self.tps.applyTransformation(grid).reshape(h, w, 2)
        map_x = transformed[:, :, 0].astype(np.float32)
        map_y = transformed[:, :, 1].astype(np.float32)

        return cv2.remap(image, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    def get_matrix(self) -> Optional[np.ndarray]:
        return None  # TPS não possui matriz explícita

    def quality_metrics(self) -> dict:
        return {
            "valid": self.tps is not None,
            "reprojection_error": self.reprojection_error
        }
