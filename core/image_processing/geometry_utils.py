import numpy as np
from typing import Tuple


def compute_crop_bounds(mask: np.ndarray) -> Tuple[int, int, int, int]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return 0, 0, mask.shape[0], mask.shape[1]
    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)
    return y_min, x_min, y_max, x_max

def mask_valid_pixels(image: np.ndarray) -> np.ndarray:
    return np.any(image != [0, 0, 0], axis=2)
