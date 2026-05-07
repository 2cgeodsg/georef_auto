from ...dependencies import cv2
from ...dependencies import numpy as np
from typing import Tuple, List, Optional
from .base_detector import BaseDetector
from ...utils.logger import logger


class ORBDetector(BaseDetector):

    def detect_and_compute(self, image_gray: np.ndarray) -> Tuple[List, Optional[np.ndarray]]:
        try:
            orb = cv2.ORB_create(nfeatures=10000)
            keypoints, descriptors = orb.detectAndCompute(image_gray, None)

            if descriptors is None or len(descriptors) == 0:
                logger.warning("ORB: Nenhum descritor encontrado.")
                return keypoints, None

            descriptors = np.float32(descriptors)

            logger.info(f"ORB: {len(keypoints)} keypoints detectados.")
            return keypoints, descriptors

        except Exception as e:
            logger.error(f"Erro no ORB: {e}")
            return [], None

    @property
    def descriptor_type(self) -> str:
        return 'float32'