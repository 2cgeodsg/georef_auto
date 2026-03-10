from typing import List
from qgis.core import QgsRectangle

from ...dependencies import numpy as np


class Reference:
    idx: int
    def __init__(self, boundingBox: QgsRectangle, descriptors, keypoints) -> None:
        self.boundingBox = boundingBox
        self.descriptors = descriptors
        self.keypoints = keypoints