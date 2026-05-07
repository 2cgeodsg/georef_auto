from ..dependencies import numpy as np
from ..dependencies import cv2

def reprojection_stats(H, pares, mask):
    pts_src = np.float32([[p.origem.x, p.origem.y] for p in pares]).reshape(-1,1,2)
    pts_dst = np.float32([[p.referencia.x, p.referencia.y] for p in pares]).reshape(-1,1,2)
    proj = cv2.perspectiveTransform(pts_src, H)
    err = np.linalg.norm((proj - pts_dst).reshape(-1,2), axis=1)  # px
    if mask is not None:
        m = np.asarray(mask).ravel().astype(bool)
        err = err[m]
    return {
        "count": int(err.size),
        "rms": float(np.sqrt(np.mean(err**2))) if err.size else None,
        "median": float(np.median(err)) if err.size else None,
        "p95": float(np.percentile(err, 95)) if err.size else None,
    }
