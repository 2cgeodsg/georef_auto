# -*- coding: utf-8 -*-
"""Module for georeferencing logic, merging georef_auto2's working method with georef_auto_new's structure."""

import cv2
import numpy as np
import rasterio
import rasterio.warp # Adicionado
import rasterio.transform # Adicionado
from .render.render_reference import render_reference_image
import os
from .detectors import  RootSIFTDetector
from .matchers.flann_matcher import FLANNMatcher

from .estimators.homography_ransac import RansacHomographyEstimator
from .estimators.homography_base import ParCorrespondencia, Ponto2D
from .evaluators.match_quality import HomographyQualityEvaluator, RegrasQualidadeHomografia

from ..core.image_processing import (
    aplicar_warp_perspective,
    recortar_bordas_pretas,
    calcular_resolucao_ref,
    calcular_extensao_recorte,
    ReamostragemConfig,
    reamostrar_e_salvar_geotiff,
    nome_interpolacao
)

from qgis.PyQt.QtWidgets import QMessageBox, QProgressDialog, QApplication
from qgis.core import (
    QgsRectangle, QgsMapSettings, QgsMapRendererCustomPainterJob,
    QgsCoordinateReferenceSystem, QgsDistanceArea, QgsCoordinateTransform,
    QgsProject, QgsUnitTypes, QgsGeometry, QgsPointXY, QgsMapLayerType
)
from PyQt5.QtGui import QImage, QPainter, QColor
from PyQt5.QtCore import QSize, Qt
import traceback
import logging
from ..utils.process_logger import ProcessLogger
from ..utils.reprojection_stats import reprojection_stats

from typing import Tuple, List, Optional, Dict

# Configurações
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from .config import GeoreferencingConfig



# --- Funções Auxiliares ---

def is_geographic_crs(epsg_code: str) -> bool:
    """Verifica se o CRS é geográfico (graus)."""
    try:
        crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg_code}")
        return crs.isGeographic()
    except Exception as e:
        logging.error(f"Erro ao verificar CRS: {e}")
        return False

# def get_area_in_square_km(geometry: QgsGeometry, crs_authid: str) -> float:
#     """Calcula área em km² com tratamento para CRS geográficos."""
#     try:
#         crs = QgsCoordinateReferenceSystem(crs_authid)
#         if not crs.isValid():
#             logging.warning(f"CRS inválido para cálculo de área: {crs_authid}")
#             return 0.0

#         # Use QgsDistanceArea for projected CRS
#         if not crs.isGeographic():
#             area = QgsDistanceArea()
#             area.setSourceCrs(crs, QgsProject.instance().transformContext())
#             area.setEllipsoid(crs.ellipsoidAcronym())
#             return area.measureArea(geometry) / 1e6  # m² → km²
#         else:
#             # Approximate for geographic CRS (less accurate, but avoids complex reprojection)
#             # Consider warning the user about potential inaccuracy for large geographic areas
#             logging.warning("Calculando área aproximada para CRS geográfico.")
#             bbox = geometry.boundingBox()
#             # Rough approximation: 1 degree latitude ~ 111km, 1 degree longitude varies
#             center_lat = bbox.center().y()
#             km_per_lon_degree = 111.32 * np.cos(np.radians(center_lat))
#             width_km = bbox.width() * km_per_lon_degree
#             height_km = bbox.height() * 111.1 # More constant
#             return width_km * height_km

#     except Exception as e:
#         logging.error(f"Erro no cálculo de área: {e}")
#         return 0.0

def render(
    polygon_geom: QgsGeometry,
    reference_layer,
    p_log: ProcessLogger|None=None,
    config: GeoreferencingConfig = GeoreferencingConfig(),
    debug_output_dir: str = "C:/logsgeoref"
):
    if p_log: p_log.start("render_ref")
    img_ref_crop, bounds_crop, epsg, path_ref_geotiff = render_reference_image(
        reference_layer,
        polygon_geom,
        config=config,
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

def georeference_image(
    image_path: str,
    polygon_geom: QgsGeometry,
    reference_layer,
    output_path: str,
    progress_callback=None,
    config: GeoreferencingConfig = GeoreferencingConfig(),
) -> Tuple[bool, str]:
    """
    Pipeline: render → detectar → match → estimar H (Strategy) → avaliar → warp → recorte → extensão → reamostrar/salvar.
    Todos os parâmetros operacionais vêm de `config`.
    """
    p_log = ProcessLogger(log_directory="C:/logsgeoref")
    p_log.attach_python_logging(level=logging.INFO)

    path_ref_geotiff = None
    try:
        p_log.set_context(
            image=os.path.basename(image_path),
            output=os.path.basename(output_path),
            epsg_ref=str(reference_layer.crs().authid()) if hasattr(reference_layer, "crs") else "desconhecido",
            opencv_version=cv2.__version__,
            rasterio_version=getattr(rasterio, "__version__", "unknown"),
            cfg=vars(config),
        )

        # 1) Render da referência (usa config.render_width_px)
        if progress_callback: progress_callback(5, "Renderizando área de referência...")
        p_log.start("render_ref")
        img_ref_crop, bounds_crop, epsg, path_ref_geotiff = render(
            polygon_geom,
            reference_layer,
            p_log,
            config=config,
            debug_output_dir="C:/logsgeoref"
        )

        # 2) Carregar imagem fonte
        if progress_callback: progress_callback(15, "Carregando imagem de entrada...")
        p_log.start("load_input")
        img_original_color = cv2.imread(image_path, cv2.IMREAD_COLOR)
        p_log.end("load_input")
        if img_original_color is None:
            raise ValueError(f"Não foi possível carregar a imagem não georreferenciada: {image_path}")

        # 3) Pré-processamento
        img_original_gray = cv2.cvtColor(img_original_color, cv2.COLOR_BGR2GRAY)
        img_ref_gray      = cv2.cvtColor(img_ref_crop, cv2.COLOR_BGR2GRAY)

        # 4) Detectar/Descrever
        if progress_callback: progress_callback(25, "Detectando características (RootSIFT)...")
        p_log.start("detect_describe")
        detector = RootSIFTDetector()
        kp1, desc1 = detector.detect_and_compute(img_original_gray)
        kp2, desc2 = detector.detect_and_compute(img_ref_gray)
        p_log.end("detect_describe")
        p_log.log_kv(kp_src=len(kp1 or []), kp_ref=len(kp2 or []), detector="RootSIFT")

        if desc1 is None or desc2 is None or len(kp1) < config.min_features or len(kp2) < config.min_features:
            raise ValueError(f"Descritores insuficientes: kp_src={len(kp1 or [])}, kp_ref={len(kp2 or [])}, "
                            f"min_features={config.min_features}.")

        # 5) Matching
        if progress_callback: progress_callback(50, "Correspondendo características (FLANN)...")
        p_log.start("matching")
        matcher = FLANNMatcher()
        desc_type = detector.descriptor_type
        desc1 = desc1.astype(desc_type)
        desc2 = desc2.astype(desc_type)
        good_matches, raw_matches = matcher.match(desc1, desc2, kp1, kp2)
        p_log.end("matching")
        p_log.log_kv(matches_raw=len(raw_matches), matches_good=len(good_matches), matcher="FLANN")

        if len(good_matches) < config.min_features:
            raise ValueError(f"Poucos matches válidos ({len(good_matches)}) para homografia "
                            f"(mínimo: {config.min_features}).")

        # 6) Estimar Homografia (Strategy com parâmetros da config)
        if progress_callback: progress_callback(70, "Estimando transformação (Homografia via Strategy)...")
        p_log.start("estimate_h")

        pares: List[ParCorrespondencia] = [
            ParCorrespondencia(
                origem=Ponto2D(*kp1[m.queryIdx].pt),
                referencia=Ponto2D(*kp2[m.trainIdx].pt)
            ) for m in good_matches
        ]

        estimador = RansacHomographyEstimator(
            reproj_threshold_px=config.ransac_reproj_thresh_px,
            confidence=config.ransac_confidence
        )
        resultado = estimador.estimate(pares)
        p_log.end("estimate_h")

        # método usado (detector + matcher + estimador)
        p_log.set_method_used("RootSIFT", "FLANN", "RANSAC")
        p_log.log_kv(
            inliers=resultado.n_inliers,
            correspondencias=resultado.n_corresp,
            reproj_thresh=resultado.reproj_thresh,
            confidence=resultado.confidence
        )

        if resultado.H is None:
            raise ValueError(resultado.mensagem)

        # 7) Avaliação de qualidade
        avaliador = HomographyQualityEvaluator(
            RegrasQualidadeHomografia(min_inliers=config.min_features, min_inlier_ratio=config.min_inlier_ratio)
        )
        if not avaliador.is_acceptable(resultado.n_inliers, resultado.n_corresp):
            raise ValueError(avaliador.build_fail_message(resultado.n_inliers, resultado.n_corresp))

        logging.info(
            "Homografia %s aceita: inliers=%d/%d; thr=%.2fpx; conf=%.3f",
            resultado.metodo, resultado.n_inliers, resultado.n_corresp,
            resultado.reproj_thresh, resultado.confidence
        )

        H    = resultado.H
        mask = resultado.mascara_inliers

        # Métricas de reprojeção (px)
        stats = reprojection_stats(H, pares, mask)
        p_log.log_kv(reproj_rms=stats["rms"], reproj_med=stats["median"], reproj_p95=stats["p95"])

        # 8) Inliers finais
        inliers = int(np.asarray(mask).ravel().sum()) if mask is not None else 0
        p_log.log_kv(inliers_confirm=inliers)
        logging.info("Homografia estimada com %d inliers de %d matches.", inliers, len(good_matches))
        if inliers <  config.min_features:
            raise ValueError(f"Poucos inliers ({inliers}) após RANSAC (mínimo: {config.min_features}).")

        # 9) Warp na grade da referência
        if progress_callback: progress_callback(85, "Aplicando transformação (warp)...")
        p_log.start("warp")
        h_ref, w_ref = img_ref_crop.shape[:2]
        interpolacao = config.warp_interpolation  # ex.: cv2.INTER_CUBIC (3)

        img_warped_full = aplicar_warp_perspective(
            imagem_bgr=img_original_color,
            H_3x3=H,
            largura_ref_px=w_ref,
            altura_ref_px=h_ref,
            interpolacao=interpolacao,
            borda_valor=(0, 0, 0),
        )
        p_log.log_kv(warp_ref_w=w_ref, warp_ref_h=h_ref, warp_interp=nome_interpolacao(interpolacao))
        p_log.end("warp")

        # 10) Recorte de bordas pretas
        p_log.start("crop")
        img_recortada, y_min, x_min, y_max, x_max = recortar_bordas_pretas(img_warped_full, (0, 0, 0))
        p_log.end("crop")
        nova_altura, nova_largura = img_recortada.shape[:2]
        p_log.log_kv(crop_xmin=x_min, crop_ymin=y_min, crop_xmax=x_max, crop_ymax=y_max,
                     crop_w=nova_largura, crop_h=nova_altura)

        if nova_altura <= 0 or nova_largura <= 0:
            raise ValueError("Dimensões da imagem recortada são inválidas.")

        # 11) Extensão geográfica do recorte
        p_log.start("geo_extent")
        x_res_ref, y_res_ref = calcular_resolucao_ref(bounds_crop, w_ref, h_ref)
        ext_geo = calcular_extensao_recorte(
            bounds_crop=bounds_crop,
            x_min_px=x_min, y_min_px=y_min, x_max_px=x_max, y_max_px=y_max,
            x_res_ref=x_res_ref, y_res_ref=y_res_ref,
        )
        p_log.end("geo_extent")
        p_log.log_kv(x_res_ref=x_res_ref, y_res_ref=y_res_ref,
                     xmin=ext_geo.xmin, ymin=ext_geo.ymin, xmax=ext_geo.xmax, ymax=ext_geo.ymax)

        # 12) Reamostrar e salvar GeoTIFF (usa config.target_resolution/resampling/clamp_upsampling)
        if progress_callback: progress_callback(95, "Salvando imagem georreferenciada...")
        p_log.start("save_geotiff")

        native_min_res = min(x_res_ref, y_res_ref)  # m/px da referência
        if config.clamp_upsampling:
            res_alvo = max(config.target_resolution, native_min_res)  # nunca menor que a nativa
        else:
            res_alvo = config.target_resolution

        cfg = ReamostragemConfig(
            resolucao_alvo=res_alvo,
            metodo=config.resampling,
            compress="JPEG",
            jpeg_quality=85,
            photometric="YCBCR",
            build_overviews=True,                
            overview_levels=(2,4,8,16),          
            overview_resampling="nearest",       
        )

        largura_final, altura_final = reamostrar_e_salvar_geotiff(
            img_crop_bgr=img_recortada,
            extensao_geo=ext_geo,
            crs_epsg=f"EPSG:{epsg}",
            x_res_ref=x_res_ref,
            y_res_ref=y_res_ref,
            caminho_saida=output_path,
            cfg=cfg,
        )
        p_log.end("save_geotiff")
        p_log.log_kv(final_w=largura_final, final_h=altura_final, resolucao_alvo=cfg.resolucao_alvo)

        msg_ok = (f"Georreferenciamento concluído (resolução ~{cfg.resolucao_alvo}): "
                  f"{os.path.basename(output_path)}")
        logging.info(msg_ok)

        # 13) Persistir log físico do processo
        log_path = p_log.write_to_file(output_path)
        logging.info("Log de processo salvo em: %s", log_path)
        return True, msg_ok

    except Exception as e:
        err_msg = f"Falha: {e}"
        logging.error(err_msg)
        logging.error(traceback.format_exc())
        p_log.log(err_msg)
        p_log.log(traceback.format_exc())
        try:
            log_path = p_log.write_to_file(output_path)
            logging.info("Log de falha salvo em: %s", log_path)
        except Exception:
            pass
        if "SIFT" in str(e) and not hasattr(cv2, 'SIFT_create'):
            return False, "Erro: SIFT não disponível. Instale 'opencv-contrib-python'."
        return False, f"Erro inesperado: {str(e)}"

    finally:
        p_log.detach_python_logging()
        if path_ref_geotiff and os.path.exists(path_ref_geotiff):
            try:
                os.remove(path_ref_geotiff)
                logging.info(f"GeoTIFF temporário removido: {path_ref_geotiff}")
            except Exception as e2:
                logging.warning(f"Não foi possível remover o GeoTIFF temporário: {e2}")
  

# --- Função de Lote (mantida da versão nova, chama a nova georeference_image) ---

def batch_georeference(image_paths: List[str], polygon_geom: QgsGeometry,
                      reference_layer, dialog_instance) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Processamento em lote com relatório."""
    successful = []
    failed = []
    total = len(image_paths)

    # Use o dialog_instance (GeorefAutoDialog) como parent para o QProgressDialog
    progress = QProgressDialog("Georreferenciando imagens...", "Cancelar", 0, total * 100, dialog_instance)
    progress.setWindowModality(Qt.WindowModal)
    progress.setWindowTitle("Progresso do Georreferenciamento")
    progress.setValue(0)
    QApplication.processEvents() # Ensure dialog shows up

    for i, img_path in enumerate(image_paths):
        if progress.wasCanceled():
            logging.info("Processo cancelado pelo usuário.")
            break

        current_progress_base = i * 100
        progress.setValue(current_progress_base)
        progress.setLabelText(f"Processando {i+1}/{total}: {os.path.basename(img_path)}")
        QApplication.processEvents()

        # Define output path based on dialog's batch_output_dir
        output_filename = f"{os.path.splitext(os.path.basename(img_path))[0]}_georef.tif"
        output_path = os.path.join(dialog_instance.batch_output_dir, output_filename)

        # Define the progress callback function for this image
        def report_progress(percentage, message):
            progress.setValue(current_progress_base + percentage)
            progress.setLabelText(f"Processando {i+1}/{total}: {os.path.basename(img_path)} - {message}")
            QApplication.processEvents()

        # Chama a função de georreferenciamento principal (a nova, baseada na antiga)
        success, message = georeference_image(
            img_path, polygon_geom, reference_layer, output_path,
            progress_callback=report_progress
        )

        if success:
            successful.append(output_path)
        else:
            failed.append((os.path.basename(img_path), message))

        # Ensure progress bar reaches 100 for this item if successful
        if success and not progress.wasCanceled():
             progress.setValue(current_progress_base + 100)
             QApplication.processEvents()

    progress.setValue(total * 100) # Mark as complete
    progress.close() # Close the progress dialog

    return successful, failed
