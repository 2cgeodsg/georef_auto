import logging
import os
from typing import Callable, Tuple

from ..dependencies import rasterio

from ..dependencies import cv2
from cv2.gapi import div

from qgis.core import QgsGeometry, QgsRectangle

from .georeferencing import render
from .config import GeoreferencingConfig
from .detectors import RootSIFTDetector
from .matchers.flann_matcher import FLANNMatcher
from ..utils.process_logger import ProcessLogger


def carregarImagem(
    image_path: str,
    p_log: ProcessLogger|None=None
):
    if p_log: p_log.start("load_input")
    img_original_color = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if p_log: p_log.end("load_input")
    if img_original_color is None:
        raise ValueError(f"Não foi possível carregar a imagem não georreferenciada: {image_path}")
    return cv2.cvtColor(img_original_color, cv2.COLOR_BGR2GRAY)


def isPossibleLocation(
    image_path: str,
    polygon_geom: QgsGeometry,
    reference_layer,
    log_dir: str = "C:/logsgeoref/preprocessing",
    progress_callback=None,
    config: GeoreferencingConfig = GeoreferencingConfig(),
    wasCanceled=None
):
    """
    Pipeline: render → detectar → match → retornar.
    Todos os parâmetros operacionais vêm de `config`. 
    """

    if wasCanceled and wasCanceled(): return False

    # 1) Render da referência (usa config.render_width_px)
    if progress_callback: progress_callback(10, "Renderizando área de referência...")
    img_ref_crop, bounds_crop, epsg, path_ref_geotiff = render(
        polygon_geom,
        reference_layer,
        None,
        config=config,
        debug_output_dir=log_dir
    )
    img_ref_gray = cv2.cvtColor(img_ref_crop, cv2.COLOR_BGR2GRAY)

    if wasCanceled and wasCanceled(): return False
    
    # 2) Carregar imagem fonte
    if progress_callback: progress_callback(20, "Carregando imagem de entrada...")
    img_original_gray = carregarImagem(image_path)

    if wasCanceled and wasCanceled(): return False

    # 4) Detectar/Descrever
    if progress_callback: progress_callback(40, "Detectando características (RootSIFT)...")
    detector = RootSIFTDetector()
    kp1, desc1 = detector.detect_and_compute(img_original_gray)
    kp2, desc2 = detector.detect_and_compute(img_ref_gray)

    if desc1 is None or desc2 is None or len(kp1) < config.min_features or len(kp2) < config.min_features:
        raise ValueError(f"Descritores insuficientes: kp_src={len(kp1 or [])}, kp_ref={len(kp2 or [])}, "
                        f"min_features={config.min_features}.")

    if wasCanceled and wasCanceled(): return False

    # 5) Matching
    if progress_callback: progress_callback(80, "Correspondendo características (FLANN)...")
    matcher = FLANNMatcher()
    desc_type = detector.descriptor_type
    desc1 = desc1.astype(desc_type)
    desc2 = desc2.astype(desc_type)
    good_matches, raw_matches = matcher.match(desc1, desc2, kp1, kp2)

    if wasCanceled and wasCanceled(): return False

    if progress_callback: progress_callback(100, "Pronto")
    return len(good_matches) >= config.search_min_features



def divideWithMetricSuperposition(
    bbox: QgsRectangle,
    superposition: Tuple[float, float],
    progress_callback: Callable[[int, str], None]|None = None,
    config: GeoreferencingConfig = GeoreferencingConfig(),
):
    if progress_callback: progress_callback(0, "Calculating divisions...")
    sX, sY = superposition
    divs = config.search_division
    assert divs >= 1, "config.search_division DEVE ser maior ou igual 1. (Não dividir por zero, por favor.)"

    dX = (sX * (divs - 1) + bbox.xMaximum() - bbox.xMinimum()) / divs
    dY = (sY * (divs - 1) + bbox.yMaximum() - bbox.yMinimum()) / divs

    pX = [(dX - sX) * n for n in range(divs)]
    pY = [(dY - sY) * n for n in range(divs)]

    return [QgsRectangle(pX[i], pY[j], pX[i] + dX, pY[j] + dY) for i in range(divs) for j in range(divs)]