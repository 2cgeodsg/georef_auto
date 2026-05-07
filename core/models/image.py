from typing import List

from ...dependencies import numpy as np


class Image:
    idx: int
    def __init__(self, path: str, descriptors, keypoints) -> None:
        self.path = path
        self.descriptors = descriptors
        self.keypoints = keypoints
   
   