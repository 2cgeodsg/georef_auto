from ...dependencies import cv2
from ...dependencies import numpy as np
from typing import Tuple, List, Optional
from .base_detector import BaseDetector
from ...utils.logger import logger


class AKAZEDetector(BaseDetector):

    def detect_and_compute(self, image_gray: np.ndarray) -> Tuple[List, Optional[np.ndarray]]:
        try:
            akaze = cv2.AKAZE_create()
            keypoints, descriptors = akaze.detectAndCompute(image_gray, None)

            if len(keypoints) > 10000:
                keypoints = keypoints[:10000]
                descriptors = descriptors[:10000]

            if descriptors is None or len(descriptors) == 0:
                logger.warning("AKAZE: Nenhum descritor encontrado.")
                return keypoints, None

            logger.info(f"AKAZE: {len(keypoints)} keypoints detectados.")
            return keypoints, descriptors

        except Exception as e:
            logger.error(f"Erro no AKAZE: {e}")
            return [], None

    @property
    def descriptor_type(self) -> str:
        return 'float32'
