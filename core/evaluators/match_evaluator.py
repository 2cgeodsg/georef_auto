from ...dependencies import numpy as np
from ...dependencies import cv2
from typing import List, Tuple
from ...utils.logger import logger

class MatchEvaluator:
    @staticmethod
    def compute_inlier_ratio(mask: np.ndarray) -> float:
        if mask is None or len(mask) == 0:
            return 0.0
        return float(np.sum(mask)) / len(mask)

    @staticmethod
    def compute_reprojection_error(pts1_transformed: np.ndarray, pts2: np.ndarray) -> float:
        try:
            return float(np.mean(np.linalg.norm(
                pts1_transformed.reshape(-1, 2) - pts2.reshape(-1, 2), axis=1
            )))
        except Exception as e:
            logger.error(f"Erro ao calcular erro de reprojeção: {e}")
            return float('inf')

    @staticmethod
    def compute_spatial_dispersion(points: np.ndarray) -> float:
        try:
            centroid = np.mean(points, axis=0)
            distances = np.linalg.norm(points - centroid, axis=1)
            dispersion = float(np.std(distances))
            return dispersion
        except Exception as e:
            logger.error(f"Erro ao calcular dispersão espacial: {e}")
            return float('inf')

    @staticmethod
    def extract_match_points(good_matches: List[cv2.DMatch], 
                             kp1: List[cv2.KeyPoint], 
                             kp2: List[cv2.KeyPoint]) -> Tuple[np.ndarray, np.ndarray]:
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
        return pts1, pts2
