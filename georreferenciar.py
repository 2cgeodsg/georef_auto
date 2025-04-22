import cv2
import numpy as np
import os
import rasterio
from rasterio.transform import from_bounds
from qgis.PyQt.QtWidgets import QMessageBox

from .recorte_referencia import recortar_imagem_referencia
from .dependencias import verificar_dependencias

verificar_dependencias()

def root_sift_detect_and_compute(image_gray):
    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(image_gray, None)

    if descriptors is None or len(descriptors) == 0:
        return keypoints, None

    # RootSIFT normalization
    descriptors /= (descriptors.sum(axis=1, keepdims=True) + 1e-7)
    descriptors = np.sqrt(descriptors)

    return keypoints, descriptors

def georreferenciar(imagem_nao_geo_path, poligono_geom, layer_referencia, saida_path):
    try:
        imagem_ref_crop, bounds_crop, epsg = recortar_imagem_referencia(layer_referencia, poligono_geom)

        img_original = cv2.imread(imagem_nao_geo_path, cv2.IMREAD_GRAYSCALE)
        img_ref = imagem_ref_crop

        if img_original is None or img_ref is None:
            raise ValueError("Não foi possível carregar as imagens.")

        kp1, desc1 = root_sift_detect_and_compute(img_original)
        kp2, desc2 = root_sift_detect_and_compute(img_ref)

        if desc1 is None or desc2 is None:
            raise ValueError("Não foi possível extrair descritores.")

        # FLANN-based matcher
        index_params = dict(algorithm=1, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        raw_matches = flann.knnMatch(desc1, desc2, k=2)

        good_matches = []
        for m, n in raw_matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        if len(good_matches) < 4:
            raise ValueError("Poucos matches válidos encontrados para estimar homografia.")

        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC)

        if H is None:
            raise ValueError("Homografia não pôde ser estimada.")

        h, w = img_ref.shape[:2]
        img_warped = cv2.warpPerspective(cv2.imread(imagem_nao_geo_path), H, (w, h))

        transform = from_bounds(*bounds_crop, w, h)

        with rasterio.open(
            saida_path,
            'w',
            driver='GTiff',
            height=h,
            width=w,
            count=3,
            dtype=img_warped.dtype,
            crs=f"EPSG:{epsg}",
            transform=transform,
        ) as dst:
            if img_warped.ndim == 3:
                for i in range(3):
                    dst.write(img_warped[:, :, i], i + 1)
            else:
                dst.write(img_warped, 1)

        QMessageBox.information(None, "Sucesso", "Georreferenciamento concluído com sucesso.")

    except Exception as e:
        QMessageBox.critical(None, "Erro ao georreferenciar", str(e))
