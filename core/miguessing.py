from os import stat
from typing import Callable, List, Tuple

from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry, QgsRectangle

from ..dependencies import numpy as np
from ..dependencies import cv2

from .models.image import Image
from .models.reference import Reference
from .config import GeoreferencingConfig
from .detectors import RootSIFTDetector
from .matchers.flann_matcher import FLANNMatcher
from ..utils.process_logger import ProcessLogger
from .render.render_reference import render_reference_image_to_size, render_reference_image_to_spatial_resolution
from .estimators.homography_base import ParCorrespondencia, Ponto2D
from .estimators.homography_ransac import RansacHomographyEstimator
from .evaluators.match_quality import HomographyQualityEvaluator, RegrasQualidadeHomografia
from ..utils.reprojection_stats import reprojection_stats


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

def zoom_to_spatial_res(zoom: int):
    return 156416.0 / pow(2, zoom)

def render(
    polygon_geom: QgsGeometry,
    reference_layer,
    zoom_level: int,
    p_log: ProcessLogger|None=None,
    debug_output_dir: str = "C:/logsgeoref"
):
    if p_log: p_log.start("render_ref")
    # img_ref_crop, bounds_crop, epsg, path_ref_geotiff = render_reference_image_to_spatial_resolution(
    #     reference_layer,
    #     polygon_geom,
    #     spatial_resolution=zoom_to_spatial_res(zoom_level),
    #     spatial_resolution_crs=QgsCoordinateReferenceSystem("EPSG:3857"),
    #     debug_output_dir=debug_output_dir
    # )
    img_ref_crop, bounds_crop, epsg, path_ref_geotiff = render_reference_image_to_size(
        reference_layer,
        polygon_geom,
        width=2000,
        debug_output_dir=debug_output_dir
    )
    if p_log: p_log.end("render_ref")
    if img_ref_crop is None or bounds_crop is None or epsg is None or path_ref_geotiff is None:
        raise ValueError("Falha ao renderizar a imagem de referência.")
    
    if img_ref_crop is None:
        raise ValueError("Imagem de referência nula retornada do render.")

    if img_ref_crop.ndim != 3 or img_ref_crop.shape[2] != 3:
        raise ValueError(f"Imagem de referência com formato inesperado: shape={img_ref_crop.shape}")

    if img_ref_crop.dtype != np.uint8:
        img_ref_crop = img_ref_crop.astype(np.uint8, copy=False)

    # garante buffer próprio e C-contíguo (evita access violation)
    if (not img_ref_crop.flags['C_CONTIGUOUS']) or (img_ref_crop.base is not None):
        img_ref_crop = np.ascontiguousarray(img_ref_crop.copy())
    
    return img_ref_crop, bounds_crop, epsg, path_ref_geotiff


def descImg(
    image_path: str,
    progress_callback=None,
    config: GeoreferencingConfig = GeoreferencingConfig(),
    wasCanceled=None
):
    """Calcula os desc e kp da imagem."""
    # 1) Carregar imagem fonte
    if wasCanceled and wasCanceled(): return
    if progress_callback: progress_callback(0, "Carregando imagem de entrada...")
    img_original_gray = carregarImagem(image_path)

    # 2) Detectar/Descrever
    if wasCanceled and wasCanceled(): return
    if progress_callback: progress_callback(10, "Detectando características da entrada (RootSIFT)...")
    detector = RootSIFTDetector()
    kp, desc = detector.detect_and_compute(img_original_gray)

    if desc is None or len(kp) < config.min_features:
        return
    
    # 3) Casting?
    if wasCanceled and wasCanceled(): return
    if progress_callback: progress_callback(90, "Casting")
    desc_type = detector.descriptor_type
    desc = desc.astype(desc_type)
    
    image = Image(image_path, desc, kp)
    return image


def descRef(
    polygon_geom: QgsGeometry,
    reference_layer,
    zoom: int,
    log_dir: str = "C:/logsgeoref/preprocessing",
    progress_callback=None,
    config: GeoreferencingConfig = GeoreferencingConfig(),
    wasCanceled=None
):
    """Calcula os desc e kp da referência."""
    # 1) Render da referência
    if wasCanceled and wasCanceled(): return
    if progress_callback: progress_callback(0, "Renderizando área de referência...")
    img_ref_crop, bounds_crop, epsg, path_ref_geotiff = render(
        polygon_geom,
        reference_layer,
        zoom,
        debug_output_dir=log_dir
    )
    img_ref_gray = cv2.cvtColor(img_ref_crop, cv2.COLOR_BGR2GRAY)

    # 2) Detectar/Descrever
    if wasCanceled and wasCanceled(): return
    if progress_callback: progress_callback(10, "Detectando características (RootSIFT)...")
    detector = RootSIFTDetector()
    kp, desc = detector.detect_and_compute(img_ref_gray)

    if desc is None or len(kp) < config.min_features:
        return

    # 3) Casting?
    if wasCanceled and wasCanceled(): return
    if progress_callback: progress_callback(90, "Casting")
    desc_type = detector.descriptor_type
    desc = desc.astype(desc_type)

    ref = Reference(polygon_geom.boundingBox(), desc, kp)
    return ref



def check(
    image: Image,
    reference: Reference,
    progress_callback=None,
    config: GeoreferencingConfig = GeoreferencingConfig(),
    wasCanceled=None
):
    """
    Pipeline: render → detectar → match → retornar.
    Todos os parâmetros operacionais vêm de `config`. 
    """
    try:
        # 3) Matching
        if wasCanceled and wasCanceled(): return
        if progress_callback: progress_callback(0, "Correspondendo características (FLANN)...")
        matcher = FLANNMatcher()
        good_matches, raw_matches = matcher.match(
            image.descriptors, 
            reference.descriptors, 
            image.keypoints, 
            reference.keypoints
        )


        # 4) Estimar Homografia (Strategy com parâmetros da config)
        if wasCanceled and wasCanceled(): return
        if progress_callback: progress_callback(50, "Estimando transformação (Homografia via Strategy)...")

        pares: List[ParCorrespondencia] = [
            ParCorrespondencia(
                origem=Ponto2D(*image.keypoints[m.queryIdx].pt),
                referencia=Ponto2D(*reference.keypoints[m.trainIdx].pt)
            ) for m in good_matches
        ]

        estimador = RansacHomographyEstimator(
            reproj_threshold_px=config.ransac_reproj_thresh_px,
            confidence=config.ransac_confidence
        )
        resultado = estimador.estimate(pares)

        # 5) Qualidade
        avaliador = HomographyQualityEvaluator(
                RegrasQualidadeHomografia(min_inliers=config.min_features, min_inlier_ratio=config.min_inlier_ratio)
            )
        aceito = avaliador.is_acceptable(resultado.n_inliers, resultado.n_corresp)
        
        # 6) Stats
        mask = resultado.mascara_inliers
        try:
            stats = reprojection_stats(resultado.H, pares, mask)
        except:
            stats = {}
        inliers = int(np.asarray(mask).ravel().sum()) if mask is not None else 0

        if resultado.H is None: return

        if progress_callback: progress_callback(100, "Pronto")
        return aceito, resultado, pares, stats, inliers
    except:
        return



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

    pX = [bbox.xMinimum() + (dX - sX) * n for n in range(divs)]
    pY = [bbox.yMinimum() + (dY - sY) * n for n in range(divs)]

    return [QgsRectangle(pX[i], pY[j], pX[i] + dX, pY[j] + dY) for i in range(divs) for j in range(divs)]