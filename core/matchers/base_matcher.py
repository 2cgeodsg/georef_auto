from abc import ABC, abstractmethod
from typing import List, Tuple
from ...dependencies import cv2

class BaseMatcher(ABC):

    @abstractmethod
    def match(self, desc1, desc2, kp1, kp2) -> Tuple[List[cv2.DMatch], List[cv2.DMatch]]:
        pass

    @property
    @abstractmethod
    def matcher_name(self) -> str:
        pass
