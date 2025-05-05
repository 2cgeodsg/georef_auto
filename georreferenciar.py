import cv2
import numpy as np
import rasterio
from rasterio.transform import from_origin
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsRectangle, QgsMapSettings, QgsMapRendererCustomPainterJob
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtCore import QSize

from .dependencias import verificar_dependencias
verificar_dependencias()

def root_sift_detect_and_compute(image_gray):
    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(image_gray, None)
    if descriptors is None or len(descriptors) == 0:
        return keypoints, None
    descriptors /= (descriptors.sum(axis=1, keepdims=True) + 1e-7)
    descriptors = np.sqrt(descriptors)
    return keypoints, descriptors

def renderizar_imagem_referencia(layer, poligono_geom, largura_px=1500):
    bounds = poligono_geom.boundingBox()
    altura_px = int((bounds.height() / bounds.width()) * largura_px)

    map_settings = QgsMapSettings()
    map_settings.setLayers([layer])
    map_settings.setExtent(bounds)
    map_settings.setOutputSize(QSize(largura_px, altura_px))
    map_settings.setOutputDpi(96)

    img = QImage(largura_px, altura_px, QImage.Format_RGB32)
    img.fill(0)
    painter = QPainter(img)

    job = QgsMapRendererCustomPainterJob(map_settings, painter)
    job.start()
    job.waitForFinished()
    painter.end()

    ptr = img.bits()
    ptr.setsize(img.byteCount())
    arr = np.array(ptr).reshape((altura_px, largura_px, 4))

    rgb = arr[:, :, :3]  # descarta canal alfa
    return rgb, bounds, layer.crs().authid().replace("EPSG:", "")

def georreferenciar(imagem_nao_geo_path, poligono_geom, layer_referencia, saida_path):
    try:
        imagem_ref_crop, bounds_crop, epsg = renderizar_imagem_referencia(layer_referencia, poligono_geom)

        img_original_color = cv2.imread(imagem_nao_geo_path)
        if img_original_color is None:
            raise ValueError("Não foi possível carregar a imagem não georreferenciada.")

        img_original = cv2.cvtColor(img_original_color, cv2.COLOR_BGR2GRAY)
        img_ref_gray = cv2.cvtColor(imagem_ref_crop, cv2.COLOR_BGR2GRAY)

        kp1, desc1 = root_sift_detect_and_compute(img_original)
        kp2, desc2 = root_sift_detect_and_compute(img_ref_gray)

        if desc1 is None or desc2 is None:
            raise ValueError("Não foi possível extrair descritores com RootSIFT.")

        index_params = dict(algorithm=1, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        raw_matches = flann.knnMatch(desc1, desc2, k=2)
        good_matches = [m for m, n in raw_matches if m.distance < 0.75 * n.distance]

        if len(good_matches) < 4:
            raise ValueError("Poucos matches válidos encontrados para estimar homografia.")

        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC)
        if H is None:
            raise ValueError("Homografia não pôde ser estimada.")

        h, w = img_original_color.shape[:2]
        img_warped_full = cv2.warpPerspective(img_original_color, H, (imagem_ref_crop.shape[1], imagem_ref_crop.shape[0]))

        # Recorte final após warp
        mask_valid = np.any(img_warped_full != [0, 0, 0], axis=2)
        coords = np.argwhere(mask_valid)

        if coords.size == 0:
            raise ValueError("A imagem georreferenciada está vazia (apenas pixels pretos).")

        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)

        img_recortada = img_warped_full[y_min:y_max+1, x_min:x_max+1]
        nova_altura, nova_largura = img_recortada.shape[:2]

        # Transform original da imagem renderizada
        x_res = bounds_crop.width() / imagem_ref_crop.shape[1]
        y_res = bounds_crop.height() / imagem_ref_crop.shape[0]
        nova_xmin = bounds_crop.xMinimum() + x_min * x_res
        nova_ymax = bounds_crop.yMaximum() - y_min * y_res
        novo_transform = from_origin(nova_xmin, nova_ymax, x_res, y_res)

        with rasterio.open(
            saida_path,
            'w',
            driver='GTiff',
            height=nova_altura,
            width=nova_largura,
            count=3,
            dtype=img_recortada.dtype,
            crs=f"EPSG:{epsg}",
            transform=novo_transform,
        ) as dst:
            for i in range(3):
                dst.write(img_recortada[:, :, i], i + 1)

        QMessageBox.information(None, "Sucesso", "Georreferenciamento concluído com sucesso.")

    except Exception as e:
        QMessageBox.critical(None, "Erro ao georreferenciar", str(e))
