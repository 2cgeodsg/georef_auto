from ..dependencies import cv2
from ..dependencies import numpy as np
from .logger import logger

def apply_clahe(image_gray, clip_limit=3.0, tile_grid=(8, 8)):
    """Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to a grayscale image."""
    try:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
        return clahe.apply(image_gray)
    except Exception as e:
        logger.error(f"Erro ao aplicar CLAHE: {e}")
        return image_gray

def suppress_low_texture(image_gray):
    """Suppresses low-texture areas in a grayscale image using Canny edge detection."""
    try:
        edges = cv2.Canny(image_gray, 50, 150)
        dilated = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)
        masked = cv2.bitwise_and(image_gray, image_gray, mask=dilated)
        return masked
    except Exception as e:
        logger.error(f"Erro ao suprimir baixa textura: {e}")
        return image_gray

def are_matches_too_clustered(matches, threshold_ratio=0.1):
    """Checks if a set of matches are too clustered in an image."""
    if len(matches) < 2:
        return True

    pts = np.float32([m[0].pt for m in matches])
    x_range = pts[:, 0].max() - pts[:, 0].min()
    y_range = pts[:, 1].max() - pts[:, 1].min()

    # If dispersion occupies less than 10% of width/height, it's considered concentrated
    return x_range < threshold_ratio * 1000 or y_range < threshold_ratio * 1000


