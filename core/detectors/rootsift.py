from ...dependencies import cv2
from ...dependencies import numpy as np
from typing import Tuple, List, Optional
from .base_detector import BaseDetector
from ...utils.logger import logger


class RootSIFTDetector(BaseDetector):

    def detect_and_compute(self, image_gray: np.ndarray) -> Tuple[List, Optional[np.ndarray]]:
        try:
            sift = cv2.SIFT_create(nfeatures=5000, contrastThreshold=0.01)
            keypoints, descriptors = sift.detectAndCompute(image_gray, None)

            if descriptors is None or len(descriptors) == 0:
                logger.warning("RootSIFT: Nenhum descritor encontrado.")
                return keypoints, None

            # Normalização L1 com estabilidade numérica
            norms = np.linalg.norm(descriptors, ord=1, axis=1, keepdims=True)
            descriptors = descriptors / (norms + 1e-7)
            descriptors = np.sqrt(descriptors)

            logger.info(f"RootSIFT: {len(keypoints)} keypoints detectados.")
            return keypoints, descriptors

        except Exception as e:
            logger.error(f"Erro no RootSIFT: {e}")
            if not hasattr(cv2, 'SIFT_create'):
                logger.error("cv2.SIFT_create() não encontrado. Verifique se 'opencv-contrib-python' está instalado.")
            raise

    @property
    def descriptor_type(self) -> str:
        return 'float32'
