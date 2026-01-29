# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class MosaicConfig:
    # Detecção/Matching
    resize_factor: float = 1.0
    lowe_ratio: float = 0.80             # primário (FLANN)
    lowe_ratio_boost: float = 0.85       # segunda tentativa (mais permissivo)

    # RANSAC
    min_inliers: int = 12
    ransac_reproj_thresh_px: float = 6.0
    ransac_confidence: float = 0.995
    ransac_reproj_thresh_boost_px: float = 8.0   # fallback se inliers baixos

    # Aceite brando (evitar separar grupos)
    fallback_min_inliers: int = 10
    fallback_min_inlier_ratio: float = 0.02      # 2% de correspondências

    # Fallbacks de matching
    enable_bf_fallback: bool = True              # tentar BF(L2) se FLANN falhar
    safety_margin: float = 0.50          # fração da RAM livre usada no pré-voo
    max_megapix_canvas: float = 120.0    # CAP duro por par (MP); ajuste conforme sua RAM