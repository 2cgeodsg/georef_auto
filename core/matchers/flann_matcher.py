from typing import List, Tuple
import cv2
import numpy as np
from .base_matcher import BaseMatcher
from ...utils.logger import logger

class FLANNMatcher(BaseMatcher):

    def __init__(self):
        index_params = dict(algorithm=1, trees=5)  # FLANN_INDEX_KDTREE
        search_params = dict(checks=50)
        self.matcher = cv2.FlannBasedMatcher(index_params, search_params)

    def match(self, desc1, desc2, kp1, kp2, ratio_threshold=0.75) -> Tuple[List[cv2.DMatch], List[cv2.DMatch]]:
        matches = self.matcher.knnMatch(desc1, desc2, k=2)
        good_matches = []
        raw_matches = []

        for m, n in matches:
            raw_matches.append(m)
            if m.distance < ratio_threshold * n.distance:
                good_matches.append(m)

        logger.info(f"FLANNMatcher: {len(good_matches)} bons matches encontrados.")
        return good_matches, raw_matches

    @property
    def matcher_name(self) -> str:
        return "FLANN"
