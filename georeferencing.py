# -*- coding: utf-8 -*-
"""Module for georeferencing logic, merging georef_auto2's working method with georef_auto_new's structure."""

import cv2
import numpy as np
import rasterio
import rasterio.warp # Adicionado
import rasterio.transform # Adicionado
import os
# from rasterio.transform import from_origin # Removido/Comentado
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
from typing import Tuple, List, Optional, Dict

# Configurações (mantidas da versão nova onde aplicável)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
MAX_POLYGON_AREA = 3050.0  # km²
MIN_FEATURES = 4 # Minimum matches for homography (from old version)
RENDER_WIDTH_PX = 2000 # Width for rendering reference image (increased from old version's 1500)

# --- Funções Auxiliares (mantidas/adaptadas da versão nova) ---

def is_geographic_crs(epsg_code: str) -> bool:
    """Verifica se o CRS é geográfico (graus)."""
    try:
        crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg_code}")
        return crs.isGeographic()
    except Exception as e:
        logging.error(f"Erro ao verificar CRS: {e}")
        return False

def get_area_in_square_km(geometry: QgsGeometry, crs_authid: str) -> float:
    """Calcula área em km² com tratamento para CRS geográficos."""
    try:
        crs = QgsCoordinateReferenceSystem(crs_authid)
        if not crs.isValid():
            logging.warning(f"CRS inválido para cálculo de área: {crs_authid}")
            return 0.0

        # Use QgsDistanceArea for projected CRS
        if not crs.isGeographic():
            area = QgsDistanceArea()
            area.setSourceCrs(crs, QgsProject.instance().transformContext())
            area.setEllipsoid(crs.ellipsoidAcronym())
            return area.measureArea(geometry) / 1e6  # m² → km²
        else:
            # Approximate for geographic CRS (less accurate, but avoids complex reprojection)
            # Consider warning the user about potential inaccuracy for large geographic areas
            logging.warning("Calculando área aproximada para CRS geográfico.")
            bbox = geometry.boundingBox()
            # Rough approximation: 1 degree latitude ~ 111km, 1 degree longitude varies
            center_lat = bbox.center().y()
            km_per_lon_degree = 111.32 * np.cos(np.radians(center_lat))
            width_km = bbox.width() * km_per_lon_degree
            height_km = bbox.height() * 111.1 # More constant
            return width_km * height_km

    except Exception as e:
        logging.error(f"Erro no cálculo de área: {e}")
        return 0.0

# --- Lógica de Georreferenciamento (baseada na versão antiga georef_auto2) ---

def root_sift_detect_and_compute(image_gray):
    """Detect SIFT features and compute RootSIFT descriptors."""
    try:
        sift = cv2.SIFT_create() # Requires opencv-contrib-python
        keypoints, descriptors = sift.detectAndCompute(image_gray, None)
        if descriptors is None or len(descriptors) == 0:
            logging.warning("RootSIFT: Nenhum descritor encontrado.")
            return keypoints, None
        # Apply RootSIFT normalization
        descriptors /= (descriptors.sum(axis=1, keepdims=True) + 1e-7)
        descriptors = np.sqrt(descriptors)
        logging.info(f"RootSIFT: {len(keypoints)} keypoints detectados.")
        return keypoints, descriptors
    except Exception as e:
        logging.error(f"Erro no RootSIFT: {e}")
        # Check if SIFT is available (common issue if opencv-contrib-python is missing)
        if not hasattr(cv2, 'SIFT_create'):
             logging.error("cv2.SIFT_create() não encontrado. Verifique se 'opencv-contrib-python' está instalado.")
        raise

def render_reference_image(layer, polygon_geom, target_width_px=RENDER_WIDTH_PX) -> Tuple[Optional[np.ndarray], Optional[QgsRectangle], Optional[str]]:
    """Renders the reference layer section defined by the polygon to an image array."""
    try:
        if not layer or not layer.isValid():
            raise ValueError("Camada de referência inválida")
        if not polygon_geom or polygon_geom.isEmpty():
            raise ValueError("Geometria do polígono inválida")

        bounds = polygon_geom.boundingBox()
        if bounds.isEmpty() or bounds.width() == 0 or bounds.height() == 0:
             raise ValueError("Extensão (bounding box) do polígono inválida ou com dimensão zero.")

        # Calculate height based on aspect ratio
        target_height_px = int((bounds.height() / bounds.width()) * target_width_px)
        if target_height_px <= 0:
             raise ValueError(f"Altura calculada para renderização é inválida: {target_height_px}")

        logging.info(f"Renderizando área de referência: {bounds.toString()} para {target_width_px}x{target_height_px} pixels.")

        map_settings = QgsMapSettings()
        map_settings.setLayers([layer])
        map_settings.setExtent(bounds)
        map_settings.setOutputSize(QSize(target_width_px, target_height_px))
        # Use layer CRS for rendering
        map_settings.setDestinationCrs(layer.crs())
        # map_settings.setOutputDpi(96) # DPI might not be critical here

        # Create QImage and QPainter
        img = QImage(target_width_px, target_height_px, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent) # Use transparent background
        painter = QPainter(img)

        # Render using QgsMapRendererCustomPainterJob
        job = QgsMapRendererCustomPainterJob(map_settings, painter)
        job.start()
        job.waitForFinished() # Wait for rendering to complete
        painter.end()

        # Convert QImage to NumPy array (handle potential format differences)
        # Based on https://stackoverflow.com/questions/61281351/convert-qimage-to-numpy-array
        img_format = img.format()
        if img_format == QImage.Format_ARGB32_Premultiplied or img_format == QImage.Format_ARGB32:
            ptr = img.constBits()
            ptr.setsize(img.sizeInBytes())
            arr = np.array(ptr).reshape(target_height_px, target_width_px, 4) # BGRA
            # Convert BGRA to BGR (standard for OpenCV)
            rgb = arr[..., :3][..., ::-1] # Select BGR, reverse order
        elif img_format == QImage.Format_RGB32:
            ptr = img.constBits()
            ptr.setsize(img.sizeInBytes())
            arr = np.array(ptr).reshape(target_height_px, target_width_px, 4) # BGRA (or RGBA? depends on system endianness)
            rgb = arr[..., :3][..., ::-1] # Assume BGRA, convert to BGR
        elif img_format == QImage.Format_RGB888:
            ptr = img.constBits()
            ptr.setsize(img.sizeInBytes())
            arr = np.array(ptr).reshape(target_height_px, target_width_px, 3) # RGB
            rgb = arr[..., ::-1] # Convert RGB to BGR
        else:
            # Fallback: convert to a known format first
            logging.warning(f"Formato QImage não suportado diretamente: {img_format}. Tentando conversão.")
            img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
            ptr = img.constBits()
            ptr.setsize(img.sizeInBytes())
            arr = np.array(ptr).reshape(target_height_px, target_width_px, 4) # BGRA
            rgb = arr[..., :3][..., ::-1] # Select BGR, reverse order

        if rgb is None or rgb.size == 0:
            raise ValueError("Falha ao converter imagem renderizada para array NumPy.")

        epsg_code = layer.crs().authid().replace("EPSG:", "")
        logging.info(f"Renderização da referência concluída. CRS: EPSG:{epsg_code}")
        return rgb, bounds, epsg_code

    except Exception as e:
        logging.error(f"Erro ao renderizar imagem de referência: {e}")
        logging.error(traceback.format_exc())
        return None, None, None

def georeference_image(image_path: str, polygon_geom: QgsGeometry,
                      reference_layer, output_path: str,
                      progress_callback=None) -> Tuple[bool, str]:
    """Função principal de georreferenciamento usando a lógica da versão antiga."""
    try:
        if progress_callback:
            progress_callback(5, "Renderizando área de referência...")

        # 1. Renderizar imagem de referência
        img_ref_crop, bounds_crop, epsg = render_reference_image(reference_layer, polygon_geom)
        if img_ref_crop is None or bounds_crop is None or epsg is None:
            raise ValueError("Falha ao renderizar a imagem de referência.")

        if progress_callback:
            progress_callback(15, "Carregando imagem de entrada...")

        # 2. Carregar imagem de entrada
        img_original_color = cv2.imread(image_path)
        if img_original_color is None:
            raise ValueError(f"Não foi possível carregar a imagem não georreferenciada: {image_path}")

        # 3. Converter para escala de cinza
        img_original_gray = cv2.cvtColor(img_original_color, cv2.COLOR_BGR2GRAY)
        img_ref_gray = cv2.cvtColor(img_ref_crop, cv2.COLOR_BGR2GRAY)

        if progress_callback:
            progress_callback(25, "Detectando características (RootSIFT)...")

        # 4. Detectar características e descritores (RootSIFT)
        kp1, desc1 = root_sift_detect_and_compute(img_original_gray)
        kp2, desc2 = root_sift_detect_and_compute(img_ref_gray)

        if desc1 is None or desc2 is None or len(kp1) < MIN_FEATURES or len(kp2) < MIN_FEATURES:
            raise ValueError("Não foi possível extrair descritores suficientes com RootSIFT em uma ou ambas as imagens.")

        if progress_callback:
            progress_callback(50, "Correspondendo características (FLANN)...")

        # 5. Corresponder características (FLANN)
        index_params = dict(algorithm=1, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        # Ensure descriptors are float32
        desc1 = np.float32(desc1)
        desc2 = np.float32(desc2)
        raw_matches = flann.knnMatch(desc1, desc2, k=2)

        # Filter matches using Lowe's ratio test
        good_matches = []
        for m, n in raw_matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        logging.info(f"FLANN: {len(raw_matches)} matches brutos, {len(good_matches)} matches bons após filtro de razão.")

        if len(good_matches) < MIN_FEATURES:
            raise ValueError(f"Poucos matches válidos ({len(good_matches)}) encontrados para estimar homografia (mínimo: {MIN_FEATURES}).")

        if progress_callback:
            progress_callback(70, "Estimando transformação (Homografia)...")

        # 6. Estimar Homografia (RANSAC)
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0) # 5.0 pixel reprojection error threshold
        if H is None:
            raise ValueError("Homografia não pôde ser estimada com RANSAC.")

        # Count inliers
        inliers = np.sum(mask)
        logging.info(f"Homografia estimada com {inliers} inliers de {len(good_matches)} matches.")
        if inliers < MIN_FEATURES:
             raise ValueError(f"Poucos inliers ({inliers}) após RANSAC para homografia (mínimo: {MIN_FEATURES}).")

        if progress_callback:
            progress_callback(85, "Aplicando transformação (warp)...")

        # 7. Aplicar Warp Perspective
        h_ref, w_ref = img_ref_crop.shape[:2]
        img_warped_full = cv2.warpPerspective(img_original_color, H, (w_ref, h_ref))

        # 8. Recorte final após warp (para remover bordas pretas)
        # Use a máscara para encontrar a área válida
        mask_valid = np.any(img_warped_full != [0, 0, 0], axis=2)
        coords = np.argwhere(mask_valid)

        if coords.size == 0:
            # Se a imagem resultante for toda preta, use a imagem warpada completa
            logging.warning("A imagem transformada parece estar vazia (toda preta). Usando a imagem completa sem recorte.")
            img_recortada = img_warped_full
            y_min, x_min = 0, 0
            nova_altura, nova_largura = img_recortada.shape[:2]
        else:
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            img_recortada = img_warped_full[y_min:y_max+1, x_min:x_max+1]
            nova_altura, nova_largura = img_recortada.shape[:2]
            logging.info(f"Imagem recortada para remover bordas: {nova_largura}x{nova_altura} pixels.")

        if nova_altura <= 0 or nova_largura <= 0:
            raise ValueError("Dimensões da imagem recortada são inválidas.")

        if progress_callback:
            progress_callback(95, "Salvando imagem georreferenciada...")

# 9. Calcular transformação final e reamostrar para resolução desejada
        from rasterio.warp import reproject, Resampling
        import rasterio.transform

        target_resolution = 1.0 # Resolução desejada em metros/unidade do CRS
        logging.info(f"Resolução alvo definida para: {target_resolution} unidades do CRS.")

        # Calcular resolução da imagem de referência renderizada (necessária para coordenadas)
        x_res_ref = bounds_crop.width() / w_ref
        y_res_ref = bounds_crop.height() / h_ref

        # Calcular coordenadas geográficas do retângulo da imagem recortada (img_recortada)
        # x_min, y_min, x_max, y_max são os índices de pixel em img_warped_full
        nova_xmin = bounds_crop.xMinimum() + x_min * x_res_ref
        nova_ymax = bounds_crop.yMaximum() - y_min * y_res_ref
        nova_xmax = bounds_crop.xMinimum() + (x_max + 1) * x_res_ref # Canto superior direito X
        nova_ymin = bounds_crop.yMaximum() - (y_max + 1) * y_res_ref # Canto inferior esquerdo Y

        geo_width = nova_xmax - nova_xmin
        geo_height = nova_ymax - nova_ymin

        # Calcular dimensões em pixels para a resolução alvo
        final_width = max(1, round(geo_width / target_resolution))
        final_height = max(1, round(geo_height / target_resolution))

        logging.info(f"Calculadas dimensões finais: {final_width}x{final_height} pixels para resolução {target_resolution}.")

        # Definir propriedades da fonte (imagem recortada como está)
        # A imagem recortada (img_recortada) tem pixels que correspondem à grade da referência
        src_transform = rasterio.transform.from_origin(nova_xmin, nova_ymax, x_res_ref, y_res_ref)
        src_crs = f"EPSG:{epsg}"
        # img_recortada tem shape (nova_altura, nova_largura, 3) e ordem BGR

        # Definir propriedades do destino (nova grade com resolução alvo)
        dst_transform = rasterio.transform.from_origin(nova_xmin, nova_ymax, target_resolution, target_resolution)
        dst_crs = src_crs
        destination_array = np.zeros((3, final_height, final_width), dtype=img_recortada.dtype) # Formato CHW

        # Reamostrar cada banda de BGR (OpenCV) para RGB (Rasterio) e para a nova grade/resolução
        # Banda 0 (B) -> destination_array[2]
        # Banda 1 (G) -> destination_array[1]
        # Banda 2 (R) -> destination_array[0]
        source_bands_rgb_order = [img_recortada[:, :, 2], img_recortada[:, :, 1], img_recortada[:, :, 0]] # R, G, B

        logging.info("Iniciando reamostragem com Resampling.cubic...")
        for i in range(3):
             reproject(
                 source=source_bands_rgb_order[i], # Banda fonte (R, G ou B)
                 destination=destination_array[i],  # Banda destino correspondente
                 src_transform=src_transform,
                 src_crs=src_crs,
                 src_nodata=0, # Assumir que pixels pretos na imagem recortada são nodata
                 dst_transform=dst_transform,
                 dst_crs=dst_crs,
                 dst_nodata=0, # Manter nodata como 0 no destino
                 resampling=Resampling.cubic # Usar cúbico para melhor qualidade visual
             )
        logging.info("Reamostragem concluída.")

        # Salvar o array reamostrado
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=final_height,
            width=final_width,
            count=3,
            dtype=destination_array.dtype,
            crs=dst_crs,
            transform=dst_transform,
            nodata=0, # Definir valor nodata no metadado
            compress='JPEG',
            jpeg_quality=85, # Qualidade JPEG (75-95 é um bom intervalo)
            photometric='YCBCR' # Necessário para compressão JPEG em GeoTIFF
        ) as dst:
            dst.write(destination_array) # Escrever array (CHW)

        logging.info(f"Imagem georreferenciada e reamostrada salva com sucesso em: {output_path}")
        return True, f"Georreferenciamento concluído com sucesso (resolução ~{target_resolution}m): {os.path.basename(output_path)}"

    except ValueError as ve:
        logging.error(f"Erro de valor durante georreferenciamento: {ve}")
        logging.error(traceback.format_exc())
        return False, str(ve)
    except ImportError as ie:
         logging.error(f"Erro de importação: {ie}. Verifique as dependências (ex: opencv-contrib-python, rasterio).")
         return False, f"Erro de dependência: {ie}"
    except Exception as e:
        logging.error(f"Erro inesperado durante georreferenciamento: {e}")
        logging.error(traceback.format_exc())
        # Check for common OpenCV/SIFT issues
        if "SIFT" in str(e) and not hasattr(cv2, 'SIFT_create'):
             msg = "Erro: SIFT não disponível. Instale 'opencv-contrib-python'."
             logging.error(msg)
             return False, msg
        return False, f"Erro inesperado: {str(e)}"

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

# --- Funções removidas da versão nova (não funcionais ou substituídas) ---
# estimate_image_resolution, calculate_adaptive_scale, match_features (versão WMS), etc.

