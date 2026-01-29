# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Tuple, Optional, List
import numpy as np
import cv2

from ..detectors import RootSIFTDetector
from ..matchers.flann_matcher import FLANNMatcher
from ..estimators.homography_base import ParCorrespondencia, Ponto2D
from ..estimators.homography_ransac import RansacHomographyEstimator
from ..evaluators.match_quality import HomographyQualityEvaluator, RegrasQualidadeHomografia
from .config import MosaicConfig
from ...utils.logger import logger  # seu logger

_MIN_PTS_RANSAC = 4  # mínimo matemático

def _match_flann(desc_q: np.ndarray, desc_t: np.ndarray,
                 kp_q, kp_t, ratio: float) -> Tuple[List[cv2.DMatch], List[cv2.DMatch]]:
    """
    FLANN do seu projeto: passa ratio na chamada .match(..., ratio_threshold=ratio)
    Observação: 'q' = query (alvo), 't' = train (base)
    """
    matcher = FLANNMatcher()  # sem argumentos no __init__
    good, raw = matcher.match(
        desc_q, desc_t, kp_q, kp_t,
        ratio_threshold=ratio
    )
    return good, raw

def _match_bf_l2(desc_q: np.ndarray, desc_t: np.ndarray, ratio: float) -> Tuple[List[cv2.DMatch], List[cv2.DMatch]]:
    """
    Fallback BFMatcher (L2) com KNN+ratio test.
    """
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    knn = bf.knnMatch(desc_q, desc_t, k=2)
    good: List[cv2.DMatch] = []
    raw: List[cv2.DMatch] = []
    for pair in knn:
        if len(pair) < 2:
            continue
        m, n = pair
        raw.append(m)
        if m.distance < ratio * n.distance:
            good.append(m)
    logger.info(f"MOSAICO BF-L2: bons={len(good)} raw={len(raw)} (ratio={ratio:.2f})")
    return good, raw

def _pares_from_matches(good: List[cv2.DMatch], kp_q, kp_t) -> List[ParCorrespondencia]:
    return [
        ParCorrespondencia(
            origem=Ponto2D(*kp_q[m.queryIdx].pt),      # pontos da imagem 'alvo'
            referencia=Ponto2D(*kp_t[m.trainIdx].pt)   # pontos da imagem 'base'
        ) for m in good
    ]

def _undo_resize(pares: List[ParCorrespondencia], inv_scale: float) -> None:
    if inv_scale == 1.0:
        return
    for p in pares:
        p.origem.x     *= inv_scale
        p.origem.y     *= inv_scale
        p.referencia.x *= inv_scale
        p.referencia.y *= inv_scale

def _ran_homography(pares: List[ParCorrespondencia], thr: float, conf: float):
    est = RansacHomographyEstimator(reproj_threshold_px=thr, confidence=conf)
    res = est.estimate(pares)
    return res

def estimar_homografia(
    img_base_bgr: np.ndarray,
    img_alvo_bgr: np.ndarray,
    cfg: MosaicConfig
) -> Tuple[Optional[np.ndarray], int, int]:
    """
    Retorna (H, n_inliers, n_corresp) mapeando 'alvo' -> 'base'.
    Reaproveita RootSIFTDetector + FLANNMatcher + RANSAC do core.
    Com fallbacks: (a) ratio boost, (b) BF-L2, (c) RANSAC thr boost.
    """
    # 1) escala opcional
    b_gray = cv2.cvtColor(img_base_bgr, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(img_alvo_bgr, cv2.COLOR_BGR2GRAY)
    scale_inv = 1.0
    if cfg.resize_factor != 1.0:
        rf = cfg.resize_factor
        a_gray = cv2.resize(a_gray, None, fx=rf, fy=rf, interpolation=cv2.INTER_AREA)
        b_gray = cv2.resize(b_gray, None, fx=rf, fy=rf, interpolation=cv2.INTER_AREA)
        scale_inv = 1.0 / rf

    # 2) detecção/descrição com RootSIFT
    detector = RootSIFTDetector()
    kp_b, desc_b = detector.detect_and_compute(b_gray)
    kp_a, desc_a = detector.detect_and_compute(a_gray)

    if desc_b is None or desc_a is None or len(kp_b) < _MIN_PTS_RANSAC or len(kp_a) < _MIN_PTS_RANSAC:
        logger.info(f"MOSAICO DETECT: descritores insuficientes (base={len(kp_b or [])}, alvo={len(kp_a or [])})")
        return None, 0, 0

    desc_b = desc_b.astype(detector.descriptor_type, copy=False)
    desc_a = desc_a.astype(detector.descriptor_type, copy=False)

    # 3) Matching primário: FLANN @ lowe_ratio
    good, raw = _match_flann(desc_a, desc_b, kp_a, kp_b, cfg.lowe_ratio)

    # 3.1) Poucos bons? Tentar FLANN com ratio boost
    if len(good) < _MIN_PTS_RANSAC and cfg.lowe_ratio_boost > cfg.lowe_ratio:
        logger.info(f"MOSAICO FLANN boost: poucos bons={len(good)} → tentando ratio={cfg.lowe_ratio_boost:.2f}")
        good, raw = _match_flann(desc_a, desc_b, kp_a, kp_b, cfg.lowe_ratio_boost)

    # 3.2) Ainda poucos? Fallback BF-L2
    if len(good) < _MIN_PTS_RANSAC and cfg.enable_bf_fallback:
        logger.info("MOSAICO fallback BF-L2: FLANN insuficiente.")
        good, raw = _match_bf_l2(desc_a, desc_b, cfg.lowe_ratio_boost)

    if len(good) < _MIN_PTS_RANSAC:
        logger.info(f"MOSAICO MATCH: bons insuficientes={len(good)} (raw={len(raw)})")
        return None, 0, len(raw)

    # 4) Pares e desfazer escala
    pares = _pares_from_matches(good, kp_a, kp_b)
    _undo_resize(pares, scale_inv)

    # 5) RANSAC (primeira tentativa)
    res = _ran_homography(pares, cfg.ransac_reproj_thresh_px, cfg.ransac_confidence)
    if res.H is None or res.mascara_inliers is None:
        logger.info("MOSAICO RANSAC: falhou na 1ª tentativa.")
        return None, 0, len(good)

    n_in = int(res.mascara_inliers.sum())
    n_tot = res.n_corresp
    logger.info(f"MOSAICO RANSAC: inliers={n_in}/{n_tot} thr={res.reproj_thresh:.2f}")

    # 5.1) RANSAC boost se poucos inliers
    if n_in < cfg.min_inliers and cfg.ransac_reproj_thresh_boost_px > cfg.ransac_reproj_thresh_px:
        res2 = _ran_homography(pares, cfg.ransac_reproj_thresh_boost_px, cfg.ransac_confidence)
        if res2.H is not None and res2.mascara_inliers is not None:
            n_in2 = int(res2.mascara_inliers.sum())
            logger.info(f"MOSAICO RANSAC boost: inliers={n_in2}/{res2.n_corresp} thr={res2.reproj_thresh:.2f}")
            if n_in2 >= n_in:  # fica com o melhor
                res = res2
                n_in = n_in2
                n_tot = res2.n_corresp

    # 6) Avaliação principal
    avaliador = HomographyQualityEvaluator(
        RegrasQualidadeHomografia(min_inliers=cfg.min_inliers, min_inlier_ratio=0.05)
    )
    if avaliador.is_acceptable(n_in, n_tot):
        return res.H, n_in, n_tot

    # 7) Aceite brando (evita separar em grupos quando há “quase lá”)
    inlier_ratio = (n_in / max(n_tot, 1)) if n_tot else 0.0
    if n_in >= cfg.fallback_min_inliers and inlier_ratio >= cfg.fallback_min_inlier_ratio:
        logger.info(f"MOSAICO ACEITE BRANDO: inliers={n_in}, ratio={inlier_ratio:.3f}")
        return res.H, n_in, n_tot

    logger.info(f"MOSAICO REPROVADO: inliers={n_in}, ratio={inlier_ratio:.3f} "
                f"(min={cfg.min_inliers}, fb={cfg.fallback_min_inliers}/{cfg.fallback_min_inlier_ratio:.2f})")
    return None, n_in, n_tot
