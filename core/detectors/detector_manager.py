from typing import Tuple, List, Optional
import numpy as np
from .detectors import ORBDetector, RootSIFTDetector, AKAZEDetector
from ..utils.logger import logger
from .base_detector import BaseDetector

MIN_FEATURES = 4

class DetectorManager:
    def __init__(self):
        self.detector_matcher_pairs = [
            (RootSIFTDetector(), 'FLANN'),
            (ORBDetector(), 'BF'),
            (AKAZEDetector(), 'BF')
        ]

    def detect_features_with_fallback(self, image_gray: np.ndarray) -> Tuple[List, Optional[np.ndarray], str, str]:
        for detector, matcher_type in self.detector_matcher_pairs:
            try:
                keypoints, descriptors = detector.detect_and_compute(image_gray)
                if descriptors is not None and len(keypoints) >= MIN_FEATURES:
                    logger.info(f"{detector.__class__.__name__} com sucesso: {len(keypoints)} features.")
                    return keypoints, descriptors, detector.descriptor_type, matcher_type
                else:
                    logger.warning(f"{detector.__class__.__name__} não encontrou features suficientes.")
            except Exception as e:
                logger.error(f"Falha no detector {detector.__class__.__name__}: {e}")

        raise ValueError("Nenhum detector conseguiu encontrar descritores suficientes.")
