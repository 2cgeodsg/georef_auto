from typing import List, Tuple
import cv2
from .base_matcher import BaseMatcher
from ...utils.logger import logger

class BFMatcher(BaseMatcher):

    def __init__(self, cross_check=True):
        self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=cross_check)

    def match(self, desc1, desc2, kp1, kp2, ratio_threshold=0.75) -> Tuple[List[cv2.DMatch], List[cv2.DMatch]]:
        raw_matches = self.matcher.match(desc1, desc2)
        raw_matches = sorted(raw_matches, key=lambda x: x.distance)
        good_matches = [m for m in raw_matches if m.distance < ratio_threshold * raw_matches[-1].distance]

        logger.info(f"BFMatcher: {len(good_matches)} bons matches encontrados.")
        return good_matches, raw_matches

    @property
    def matcher_name(self) -> str:
        return "BF"
